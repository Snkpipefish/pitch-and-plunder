"""Tortuga-landsbyens gate.

Scene-orchestrerer: eier verdens-state (Player, NPC-er, Market, Partikler,
Lys, Kamera, Overlay) og delegerer rendering til `VillageRenderer`.
Pre-rendrede lag og bake-hjelpere bor i `scenes/parallax_backdrops.py` og
`scenes/village_buildings.py`. Hint-teksten bor i `ui/hint.py`.

Komposisjon og verdenstall: se docstrings i `village_buildings.py`.
"""

from __future__ import annotations

import json
import os

import pygame

import constants
from entities.celestial import Celestial
from entities.npc import NPC
from entities.player import Player
from scenes.base_scene import BaseScene
from scenes.exchange import ExchangeOverlay
from scenes.parallax_backdrops import build_backdrop_variants, build_empty_layer
from scenes.village_buildings import (
    EXCHANGE_CENTER_X,
    EXCHANGE_W,
    EXCHANGE_X,
    EXCHANGE_Y,
    GROUND_TOP_Y,
    TAVERN_W,
    TAVERN_X,
    TAVERN_Y,
    build_village_gameplay_layer,
)
from scenes.village_renderer import VillageRenderer
from systems import save as save_module
from systems.day_cycle import DayCycle
from systems.economy import Market
from systems.lighting import Light, LightingSystem
from systems.parallax import Camera, ParallaxLayer, ParallaxRenderer
from systems.particles import ParticleSystem
from systems.pitch_lake import PitchLake
from systems.regime_manager import RegimeManager
from systems.save import GameState
from ui.hint import HintIndicator
from ui.hud import Hud
from ui.toast import Toast, ToastQueue


# Startposisjon: midt på gaten foran Børshuset (jfr. PROSJEKT.md §8)
PLAYER_START_X = 1340.0
# Hawkins står rett foran Børshusets trapp
HAWKINS_X = 1470.0


def _load_npcs(path: str = os.path.join(constants.DATA_DIR, "npcs.json")) -> dict:
    """Les `data/npcs.json` og returner et dict indeksert på NPC-id."""
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    return {entry["id"]: entry for entry in data.get("npcs", [])}


class VillageScene(BaseScene):
    """Tortuga-gate med taverna til venstre og børshus til høyre.

    Eier `GameState` via referanse. All pris/inventar/gull-endring muterer
    tilstanden direkte. Autosave skjer ved QUIT, scene-bytte og ved
    aapning/lukking av bors-overlay.
    """

    def __init__(
        self,
        font: pygame.font.Font,
        state: GameState,
    ) -> None:
        super().__init__()
        self._font = font
        self._state = state

        # Parallax-lag. Bakgrunnen er nå dynamisk (6 varianter med cross-
        # fade styrt av DayCycle); ParallaxRenderer håndterer kun gameplay
        # og forgrunn. Backdrop-rendering skjer i VillageRenderer.
        self._backdrops = build_backdrop_variants()
        gameplay_layer = ParallaxLayer(build_village_gameplay_layer(), speed=1.0)
        fg_layer = ParallaxLayer(build_empty_layer(1.3), speed=1.3)
        parallax_renderer = ParallaxRenderer([gameplay_layer, fg_layer])
        self._celestial = Celestial()

        self._camera = Camera(constants.WORLD_WIDTH, constants.RENDER_WIDTH)

        # Spilleren: føttene hviler på GROUND_TOP_Y. Plasseres ved
        # PLAYER_START_X som trygt utgangspunkt; on_enter overskriver x
        # basert paa from_scene og lagret tilstand.
        player_y = GROUND_TOP_Y - 20  # sprite-høyde 20
        self._player = Player(PLAYER_START_X, float(player_y))
        self._player_min_x = 8.0
        self._player_max_x = float(constants.WORLD_WIDTH - self._player.width - 8)

        # NPC-er
        npc_db = _load_npcs()
        self._npcs: list[NPC] = [
            NPC.from_data(npc_db["hawkins"], HAWKINS_X, float(player_y)),
        ]

        # Dynamisk lyssystem. 3 lys, 3 unike gradienter.
        self._lighting = LightingSystem()
        # Tavern-svingende lanterne (over skiltet, rett under tak-overhenget)
        lantern_x = TAVERN_X + TAVERN_W / 2
        lantern_y = TAVERN_Y + 10
        # Tavern-dør-glød (midten av doeraapningen)
        tavern_door_x = TAVERN_X + TAVERN_W / 2
        tavern_door_y = GROUND_TOP_Y - 16
        # Børshusets midtvindu
        exchange_window_x = EXCHANGE_X + EXCHANGE_W / 2
        exchange_window_y = EXCHANGE_Y + 42
        self._lights: list[Light] = [
            Light(
                x=lantern_x,
                y=lantern_y,
                radius=40,
                color=constants.COLOR_LANTERN_BRIGHT,
                swing_amplitude=3.0,
                swing_period=2.0,
            ),
            Light(
                x=tavern_door_x,
                y=tavern_door_y,
                radius=70,
                color=constants.COLOR_FLAME,
            ),
            Light(
                x=exchange_window_x,
                y=exchange_window_y,
                radius=60,
                color=constants.COLOR_STONE_LIT,
            ),
        ]
        self._lighting.prewarm(
            [(light.radius, light.color) for light in self._lights]
        )
        self._elapsed: float = 0.0

        # Økonomi – Market lastes fra JSON, deretter applieres lagrede
        # current_price og price_history per vare hvis tilgjengelig.
        # Dag-telleren eies av state.clock (GameClock), ikke Market.
        self._market = Market.from_json(
            os.path.join(constants.DATA_DIR, "commodities.json")
        )
        for cid, saved in state.commodities_state.items():
            if not isinstance(saved, dict):
                continue
            try:
                commodity = self._market.get(cid)
            except KeyError:
                continue
            try:
                commodity.current_price = float(saved.get("current_price"))
            except (TypeError, ValueError):
                pass
            raw_history = saved.get("price_history", [])
            if isinstance(raw_history, list):
                try:
                    commodity.price_history = [float(p) for p in raw_history]
                except (TypeError, ValueError):
                    pass
            # Klamp loaded verdier mot gjeldende pris-grenser. Fase 2A
            # Commit 5D endret bek base_price 55 → 40 og klamp-forholdet
            # fra [0.3, 3.0] til [0.5, 2.0]; eksisterende saves kan ha
            # priser utenfor nye grenser (spesielt bek rundt 120+).
            self._market.clamp_to_price_bounds(cid)

        # Regime-system. Initialiser manglende regimer for kjente varer
        # (first boot, eller save uten regime-dict).
        self._regime_manager = RegimeManager()
        missing_ids = [
            c.id
            for c in self._market.commodities
            if c.id not in state.regimes
        ]
        if missing_ids:
            state.regimes.update(
                self._regime_manager.initialize_regimes(missing_ids)
            )
        # Dag-skift-sporing: naar state.clock.day overstiger denne, varsle
        # RegimeManager for hver dag som har passert.
        self._last_seen_day = state.clock.day

        # HUD (oeverst venstre: sted / gull / dag / bek-drift)
        self._hud = Hud(
            font,
            place="Tortuga",
            gold=state.gold,
            day=state.clock.day,
            pitch_per_day=state.pitch_lake.production_per_day,
            pitch_upkeep=state.pitch_lake.daily_upkeep_cost,
            pitch_halted=self._compute_pitch_halted(),
        )

        # Partikler: taake paa gata + ildfluer rundt tavernaen.
        # Tavernaens "levende midt" ligger litt foran doera og over gulvet.
        self._particles = ParticleSystem(
            tavern_center=(TAVERN_X + TAVERN_W / 2, GROUND_TOP_Y - 22),
            world_width=constants.WORLD_WIDTH,
        )

        # Overlay (børs) — None naar lukket
        self._overlay: ExchangeOverlay | None = None

        # Hint-indikator (to pre-rendrede tekstsurfaces)
        hint = HintIndicator(
            font=font,
            far_text="A/D gå   F11 fullskjerm   Esc avslutt",
            near_text="E åpne børs   A/D gå   F11 fullskjerm   Esc avslutt",
            far_color=constants.COLOR_STONE_LIT,
            near_color=constants.COLOR_LANTERN_BRIGHT,
            pos=(8, constants.RENDER_HEIGHT - 12),
        )

        # Render-komposisjon (backdrops + celestial + parallax + entiteter +
        # lys + partikler + hint)
        self._renderer = VillageRenderer(
            backdrops=self._backdrops,
            parallax_renderer=parallax_renderer,
            celestial=self._celestial,
            hint=hint,
        )

        # Toast-kø for daggry-varsel (Commit 5E) og senere bek-produksjon
        # (Commit 6) + feilhint (Commit 7). Baseline like over hint-linja.
        self._toasts = ToastQueue(
            baseline_y=constants.RENDER_HEIGHT - 18,
            center_x=constants.RENDER_WIDTH // 2,
        )

    # --- Input ---

    def handle_event(self, event: pygame.event.Event) -> None:
        # Nar borsen er aapen konsumerer overlayet all input.
        if self._overlay is not None:
            self._overlay.handle_event(event)
            return
        if event.type == pygame.KEYDOWN:
            if event.key in constants.KEY_MENU:
                self.want_quit = True
            elif event.key in constants.KEY_INTERACT:
                if self._player_can_interact_with_exchange():
                    self._open_exchange()
            elif event.key in constants.KEY_LEFT:
                self._player.press(-1)
            elif event.key in constants.KEY_RIGHT:
                self._player.press(+1)
        elif event.type == pygame.KEYUP:
            if event.key in constants.KEY_LEFT:
                self._player.release(-1)
            elif event.key in constants.KEY_RIGHT:
                self._player.release(+1)

    def _player_can_interact_with_exchange(self) -> bool:
        player_center_x = self._player.x + self._player.width / 2
        return (
            abs(player_center_x - EXCHANGE_CENTER_X) < constants.INTERACTION_DISTANCE
        )

    def _open_exchange(self) -> None:
        # Slipp eventuelle holdte tastetrykk slik at spilleren ikke fortsetter
        # aa gaa naar overlayet lukkes.
        self._player.press(0)
        self._overlay = ExchangeOverlay(self._font, self._market, self._state)
        # Autosave ved aapning slik at overgang til bors alltid kan trygges
        self.autosave()

    # --- Logikk ---

    def update(self, dt: float) -> None:
        # Dag-skift: ved daggry settes nye priser (Market.on_dawn bruker
        # dagens regime-retning) og deretter tikker regime-klokken (kan
        # skifte til et annet regime fra neste dag). Rekkefølgen er viktig:
        # on_dawn først slik at "siste dag" av et regime fortsatt har sin
        # retnings-effekt; regime_manager.on_new_day etterpå for overgang.
        curr_day = self._state.clock.day
        if curr_day != self._last_seen_day:
            days_passed = max(0, curr_day - self._last_seen_day)
            for _ in range(days_passed):
                self._market.on_dawn(self._state.regimes)
                self._regime_manager.on_new_day(self._state.regimes)
                # Upkeep trekkes uansett om produksjon lykkes. Returverdien
                # ignoreres her — HUD leser state.pitch_lake direkte for
                # halted-detektering, og toasts er fjernet (Commit 6.1).
                PitchLake.on_new_day(self._state.pitch_lake, self._state)
            self._last_seen_day = curr_day

        # Lanterne-swing og andre tidsavhengige effekter gaar videre ogsaa.
        self._elapsed += dt
        self._particles.update(dt)
        self._toasts.update(dt)

        # HUD – settere er no-ops hvis verdien ikke har endret seg
        self._hud.set_gold(self._state.gold)
        self._hud.set_day(self._state.clock.day)
        self._hud.set_pitch_status(
            pitch_per_day=self._state.pitch_lake.production_per_day,
            upkeep=self._state.pitch_lake.daily_upkeep_cost,
            halted=self._compute_pitch_halted(),
        )

        if self._overlay is not None:
            self._overlay.update(dt)
            if self._overlay.want_close:
                self._overlay = None
                # Autosave ogsaa ved lukking slik at brukeren kan quit-e
                # umiddelbart etter handel uten risiko for tap.
                self.autosave()
            return
        # Kun naar overlayet er lukket kan spilleren bevege seg.
        self._player.update(dt, self._player_min_x, self._player_max_x)
        self._center_camera_on_player()

    def _compute_pitch_halted(self) -> bool:
        """Returner True hvis Pitch Lake-produksjon har stoppet.

        Definisjon: mer enn én dag siden siste faktiske produksjon
        (`last_production_day < clock.day - 1`). Én missed dag aksepteres
        som budsjettering; to eller flere signaliserer at driften står.
        Ved fresh start er `last_production_day=0` og `clock.day=1`, som
        gir 0 < 0 = False — HUD viser dermed "kjører" inntil første
        faktiske daggry-forsøk.
        """
        return (
            self._state.pitch_lake.last_production_day
            < self._state.clock.day - 1
        )

    def _center_camera_on_player(self) -> None:
        # Kamera sentrerer spilleren horisontalt; klamping gjøres av Camera
        target = self._player.x - (constants.RENDER_WIDTH - self._player.width) / 2
        self._camera.set_x(target)

    # --- Rendering ---

    def draw(self, surface: pygame.Surface) -> None:
        # Beregn dag-natt-snapshot én gang per frame og send til renderen.
        # DayCycle er stateless, så dette er billig (~5 μs).
        snapshot = DayCycle.compute_snapshot(self._state.clock)
        # Verdens-laget (bakgrunn → forgrunn) tegnes av renderen.
        self._renderer.draw(
            surface=surface,
            cam_x=self._camera.x,
            snapshot=snapshot,
            player=self._player,
            npcs=self._npcs,
            lighting=self._lighting,
            lights=self._lights,
            elapsed=self._elapsed,
            particles=self._particles,
            show_near_hint=(
                self._player_can_interact_with_exchange()
                and self._overlay is None
            ),
        )
        # HUD (oeverst venstre) og toasts (bunn-sentrert) tegnes over
        # verden men under bors-overlay.
        self._hud.draw(surface)
        self._toasts.draw(surface)
        if self._overlay is not None:
            self._overlay.draw(surface)

    # --- Lifecycle / save ---

    def _sync_state(self) -> None:
        """Kopier gjeldende scene-tilstand inn i GameState for lagring."""
        self._state.current_scene = "village"
        self._state.player_position = (
            float(self._player.x),
            float(self._player.y),
        )
        self._state.commodities_state = {
            c.id: {
                "current_price": float(c.current_price),
                "price_history": list(c.price_history),
            }
            for c in self._market.commodities
        }
        # gold og inventory er allerede lagret i self._state – direkte mutert
        # av ExchangeOverlay, saa ingen ekstra sync der. state.clock oppdateres
        # kontinuerlig av main.run() via clock.update(dt), saa ingen sync her.

    def autosave(self) -> None:
        """Synk tilstand og skriv save-fil. Kalles fra main ved QUIT og
        fra scene selv ved overlay-aapning/lukking og scene-bytte."""
        self._sync_state()
        save_module.save(self._state)

    def on_enter(
        self,
        game_state: GameState,
        from_scene: str | None = None,
    ) -> None:
        """Plasser spilleren og sentrer kamera.

        - `from_scene=None` + state.player_position == GameState-default
          (320.0, 280.0): fersk spillstart → PLAYER_START_X.
        - Ellers: state.player_position er autoritativ (enten lagret fra
          forrige oekt, eller synket av forrige scene ved bytte).
        """
        # GameState-default (tilstand uten save). Hvis player_position er
        # dette eksakte tuplet, har state aldri blitt synket fra village –
        # scene-spesifikk start gjelder.
        GAMESTATE_DEFAULT_POS = (320.0, 280.0)
        if from_scene is None and game_state.player_position == GAMESTATE_DEFAULT_POS:
            self._player.x = PLAYER_START_X
        else:
            self._player.x = float(game_state.player_position[0])
        # Klamp mot lovlig intervall (guard for korrupte saves)
        if self._player.x < self._player_min_x:
            self._player.x = self._player_min_x
        elif self._player.x > self._player_max_x:
            self._player.x = self._player_max_x
        self._center_camera_on_player()

    def on_exit(self, to_scene: str | None = None) -> None:
        self.autosave()
