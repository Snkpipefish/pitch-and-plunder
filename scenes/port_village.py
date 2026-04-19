"""Havn-scene (port village) — parameterisert over PortConfig.

Refactored fra VillageScene (Tortuga-spesifikk) i Fase 2B C4: scenen
tar nå et PortConfig-objekt og bygger layout fra `port_config.buildings`.
Én scene-klasse betjener alle 4 havner i 2B; kun Tortuga har buildings
i C4 (de andre får layout i C6).

Scene-orchestrerer: eier verdens-state (Player, NPC-er, Market, Partikler,
Lys, Kamera, Overlay) og delegerer rendering til `PortVillageRenderer`.
Pre-rendrede lag og bake-hjelpere bor i `scenes/parallax_backdrops.py` og
`scenes/port_buildings.py`. Hint-teksten bor i `ui/hint.py`.

Market er stateless i C4: én Market-instans opererer på alle havners
MarketState via eksplisitt parameter. Ingen dobbel-representasjon.
"""

from __future__ import annotations

import json
import logging
import os
import random

import pygame

import constants
from config import port_config
from config.port_config import PortConfig
from entities.celestial import Celestial
from entities.npc import NPC
from entities.player import Player
from scenes.base_scene import BaseScene
from scenes.exchange import ExchangeOverlay
from scenes.parallax_backdrops import (
    build_backdrop_variants,
    build_empty_layer,
    build_foreground_variants,
)
from scenes.port_buildings import build_port_gameplay_layer
from scenes.port_village_renderer import PortVillageRenderer
from state import GameState
from state.market_state import MarketState
from systems import save as save_module
from systems.day_cycle import DayCycle
from systems.dev_mode import is_dev_mode as _is_dev_mode
from systems.economy import Market, load_base_prices
from systems.lighting import Light, LightingSystem
from systems.parallax import Camera, ParallaxLayer, ParallaxRenderer
from systems.particles import ParticleSystem
from systems.pitch_lake import PitchLake
from systems.regime_manager import RegimeManager
from ui.hint import HintIndicator
from ui.hud import Hud
from ui.toast import Toast, ToastQueue


# Sprite-høyde for Player — brukt til å sette player_y relativt til
# `port_config.buildings.ground_top_y`. Hvis det senere blir nødvendig
# med per-havn-justering, flytter vi denne til PortBuildings.
_PLAYER_SPRITE_HEIGHT = 20


def _load_npcs(path: str = os.path.join(constants.DATA_DIR, "npcs.json")) -> dict:
    """Les `data/npcs.json` og returner et dict indeksert på NPC-id."""
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    return {entry["id"]: entry for entry in data.get("npcs", [])}


class PortVillageScene(BaseScene):
    """Havn-gate parameterisert over PortConfig.

    Eier `GameState` via referanse. All pris/inventar/gull-endring muterer
    tilstanden direkte. Autosave skjer ved QUIT, scene-bytte og ved
    åpning/lukking av børs-overlay.

    Krever at `port_config.buildings` er satt — Port Royal, Havana og
    Nassau får layout i C6 og kan ikke instansieres før det.
    """

    def __init__(
        self,
        font: pygame.font.Font,
        state: GameState,
        port: PortConfig,
    ) -> None:
        super().__init__()
        self._font = font
        self._state = state
        self._port = port
        if port.buildings is None:
            raise ValueError(
                f"Port '{port.id}' has no buildings layout — "
                f"cannot instantiate PortVillageScene"
            )
        self._buildings = port.buildings  # non-None fra her

        # Parallax-lag. Bakgrunnen er nå dynamisk (6 varianter med cross-
        # fade styrt av DayCycle); ParallaxRenderer håndterer kun gameplay
        # og parallax-forgrunn. Himmel- og fg-backdrop-rendering skjer i
        # PortVillageRenderer. Fg-varianter (fjell + hav) ble skilt ut fra
        # himmel-variantene i Commit 7.2 slik at celestial kan tegnes
        # mellom dem og bli okkludert av fjell/hav ved horisont.
        self._backdrops = build_backdrop_variants()
        self._foregrounds = build_foreground_variants()
        gameplay_layer = ParallaxLayer(
            build_port_gameplay_layer(port), speed=1.0
        )
        fg_layer = ParallaxLayer(build_empty_layer(1.3), speed=1.3)
        parallax_renderer = ParallaxRenderer([gameplay_layer, fg_layer])
        self._celestial = Celestial()

        self._camera = Camera(port.world_width, constants.RENDER_WIDTH)

        # Spilleren: føttene hviler på buildings.ground_top_y. Plasseres ved
        # buildings.player_start_x som trygt utgangspunkt; on_enter
        # overskriver x basert på from_scene og lagret tilstand.
        player_y = self._buildings.ground_top_y - _PLAYER_SPRITE_HEIGHT
        self._player = Player(
            float(self._buildings.player_start_x), float(player_y)
        )
        self._player_min_x = 8.0
        self._player_max_x = float(port.world_width - self._player.width - 8)

        # NPC-er fra ports.json buildings.npcs
        npc_db = _load_npcs()
        self._npcs: list[NPC] = []
        for npc_id, npc_x in self._buildings.npcs.items():
            if npc_id not in npc_db:
                continue
            self._npcs.append(
                NPC.from_data(npc_db[npc_id], float(npc_x), float(player_y))
            )

        # Dynamisk lyssystem. 3 lys, 3 unike gradienter.
        self._lighting = LightingSystem()
        tavern = self._buildings.tavern
        exchange = self._buildings.exchange
        # Tavern-svingende lanterne (over skiltet, rett under tak-overhenget)
        lantern_x = tavern.x + tavern.w / 2
        lantern_y = tavern.y + 10
        # Tavern-dør-glød (midten av døråpningen)
        tavern_door_x = tavern.x + tavern.w / 2
        tavern_door_y = self._buildings.ground_top_y - 16
        # Børshusets midtvindu
        exchange_window_x = exchange.x + exchange.w / 2
        exchange_window_y = exchange.y + 42
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

        # Økonomi — Market er stateless katalog (C4). Én instans opererer
        # på alle havners MarketState via parameter. Klamp gjør Tortuga-
        # sjekk ved init for å rydde gamle saves med priser utenfor nye
        # bounds (se Fase 2A Commit 5D).
        self._market = Market.from_json(
            os.path.join(constants.DATA_DIR, "commodities.json")
        )
        current_market_state: MarketState = state.economy_state.markets.setdefault(
            port.id, MarketState()
        )
        for cid in list(current_market_state.commodities.keys()):
            self._market.clamp_to_price_bounds(current_market_state, cid)

        # Regime-system. Initialiser manglende regimer for current port.
        self._regime_manager = RegimeManager()
        current_regimes = state.economy_state.regimes.setdefault(port.id, {})
        missing_ids = [
            c.id for c in self._market.commodities if c.id not in current_regimes
        ]
        if missing_ids:
            current_regimes.update(
                self._regime_manager.initialize_regimes(missing_ids)
            )
        # Dag-skift-sporing: når clock.day overstiger denne, varsle
        # RegimeManager for hver dag som har passert.
        self._last_seen_day = state.world_state.clock.day

        # Base-priser caches for referanse (ikke lenger trengt for drift
        # siden Market.on_dawn nå inkluderer klamp intern). Beholdes for
        # eventuelt fremtidig bruk; billig oppslag uansett.
        self._base_prices = load_base_prices(
            os.path.join(constants.DATA_DIR, "commodities.json")
        )
        # Cache port_ids (stabil rekkefølge, current port først).
        self._port_ids = port_config.get_all_port_ids()

        # HUD (øverst venstre: sted / gull / dag / bek-drift).
        # DEV-markør nederst til høyre aktiveres via dev-mode-flagg.
        from systems.dev_mode import is_dev_mode
        self._hud = Hud(
            font,
            place=port.name,
            gold=state.player_state.gold,
            day=state.world_state.clock.day,
            pitch_per_day=state.pitch_lake_state.production_per_day,
            pitch_upkeep=state.pitch_lake_state.upkeep_per_day,
            pitch_halted=self._compute_pitch_halted(),
            dev_mode=is_dev_mode(),
        )

        # Partikler: tåke på gata + ildfluer rundt tavernaen.
        # Tavernaens "levende midt" ligger litt foran døra og over gulvet.
        self._particles = ParticleSystem(
            tavern_center=(
                tavern.x + tavern.w / 2,
                self._buildings.ground_top_y - 22,
            ),
            world_width=port.world_width,
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
        self._renderer = PortVillageRenderer(
            backdrops=self._backdrops,
            foregrounds=self._foregrounds,
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

    @property
    def toasts(self) -> ToastQueue:
        """Eksponer toast-køen slik at eksterne systemer kan pushe varsler.

        Brukes av main.py sin F5-hot-reload-handler i dev-mode.
        """
        return self._toasts

    # --- Input ---

    def handle_event(self, event: pygame.event.Event) -> None:
        # Når børsen er åpen konsumerer overlayet all input.
        if self._overlay is not None:
            self._overlay.handle_event(event, self._current_market_state())
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
            abs(player_center_x - (self._buildings.exchange.x + self._buildings.exchange.w / 2))
            < constants.INTERACTION_DISTANCE
        )

    def _open_exchange(self) -> None:
        # Slipp eventuelle holdte tastetrykk slik at spilleren ikke fortsetter
        # å gå når overlayet lukkes.
        self._player.press(0)
        self._overlay = ExchangeOverlay(
            self._font, self._market, self._state,
            toasts=self._toasts, port_name=self._port.name,
        )
        # Autosave ved åpning slik at overgang til børs alltid kan trygges
        self.autosave()

    def _current_market_state(self) -> MarketState:
        """Hent MarketState for havnen scenen er i nå.

        Passes per call til ExchangeOverlay (ingen __init__-lagring av
        market_state — C4-direktiv). Når C5+ legger til havn-bytte, vil
        overlayet automatisk følge aktiv havn.
        """
        return self._state.economy_state.markets.setdefault(
            self._port.id, MarketState()
        )

    # --- Logikk ---

    def update(self, dt: float) -> None:
        # Dag-skift: ved daggry settes nye priser for ALLE 4 havner, og
        # regime-klokkene tikkes. Rekkefølgen er viktig: on_dawn først
        # slik at "siste dag" av et regime fortsatt har sin retnings-
        # effekt; regime_manager.on_new_day etterpå for overgang.
        #
        # Market er stateless (C4): samme instans opererer på hver havns
        # MarketState via parameter. `_tick_all_ports_dawn` itererer
        # over port_ids og kjører on_dawn per havn.
        curr_day = self._state.world_state.clock.day
        if curr_day != self._last_seen_day:
            days_passed = max(0, curr_day - self._last_seen_day)
            for _ in range(days_passed):
                self._tick_all_ports_dawn()
                # Upkeep trekkes uansett om produksjon lykkes. Returverdien
                # ignoreres her — HUD leser pitch_lake_state direkte for
                # halted-detektering, og toasts er fjernet (Commit 6.1).
                PitchLake.on_new_day(
                    self._state.pitch_lake_state, self._state
                )
            self._last_seen_day = curr_day

        # Lanterne-swing og andre tidsavhengige effekter gaar videre ogsaa.
        self._elapsed += dt
        self._particles.update(dt)
        self._toasts.update(dt)

        # HUD – settere er no-ops hvis verdien ikke har endret seg
        self._hud.set_gold(self._state.player_state.gold)
        self._hud.set_day(self._state.world_state.clock.day)
        self._hud.set_pitch_status(
            pitch_per_day=self._state.pitch_lake_state.production_per_day,
            upkeep=self._state.pitch_lake_state.upkeep_per_day,
            halted=self._compute_pitch_halted(),
        )

        if self._overlay is not None:
            self._overlay.update(dt, self._current_market_state())
            if self._overlay.want_close:
                self._overlay = None
                # Autosave også ved lukking slik at brukeren kan quit-e
                # umiddelbart etter handel uten risiko for tap.
                self.autosave()
            return
        # Kun naar overlayet er lukket kan spilleren bevege seg.
        self._player.update(dt, self._player_min_x, self._player_max_x)
        self._center_camera_on_player()

    def _tick_all_ports_dawn(self) -> None:
        """Prosesser daggry-overgang for alle 4 havner.

        Market er stateless (C4): samme Market-instans kjører `on_dawn`
        mot hver havns MarketState i tur. Regime-manager oppdateres per
        havns regime-dict.

        Dev-mode: logger én linje per havn med regime-snapshot etter
        overgang.
        """
        econ = self._state.economy_state
        day = self._state.world_state.clock.day
        dev = _is_dev_mode()

        for port_id in self._port_ids:
            market_state = econ.markets.setdefault(port_id, MarketState())
            port_regimes = econ.regimes.setdefault(port_id, {})
            # Market.on_dawn muterer market_state (inkluderer price,
            # price_history, tick_id) og tikker regimer.
            self._market.on_dawn(market_state, port_regimes)
            self._regime_manager.on_new_day(port_regimes)
            if dev:
                self._log_port_regimes(port_id, port_regimes, day)

    @staticmethod
    def _log_port_regimes(port_id: str, regimes: dict, day: int) -> None:
        """Dev-mode: logg regime-snapshot for én havn etter dawn-overgang.

        Format: 'Dawn day=N <port_id> sugar=<regime> rum=... tobacco=... pitch=...'
        """
        parts = [
            f"{cid}={reg.current}"
            for cid, reg in regimes.items()
        ]
        logging.getLogger("ports_regime").info(
            "Dawn day=%d %s %s", day, port_id, " ".join(parts)
        )

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
            self._state.pitch_lake_state.last_production_day
            < self._state.world_state.clock.day - 1
        )

    def _center_camera_on_player(self) -> None:
        # Kamera sentrerer spilleren horisontalt; klamping gjøres av Camera
        target = self._player.x - (constants.RENDER_WIDTH - self._player.width) / 2
        self._camera.set_x(target)

    # --- Rendering ---

    def draw(self, surface: pygame.Surface) -> None:
        # Beregn dag-natt-snapshot én gang per frame og send til renderen.
        # DayCycle er stateless, så dette er billig (~5 μs).
        # Celestial-config hentes fra port_config for nåværende havn (C3a).
        # Tortuga er eneste spillbare havn i C3; C5+ vil endre current_port.
        celestial_cfg = port_config.get(
            self._state.world_state.current_port
        ).celestial
        snapshot = DayCycle.compute_snapshot(
            self._state.world_state.clock, celestial_cfg
        )
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
            self._overlay.draw(surface, self._current_market_state())

    # --- Lifecycle / save ---

    def _sync_state(self) -> None:
        """Kopier scene-lokal spiller-posisjon inn i GameState for lagring.

        player_state.position_x er den eneste koordinaten som lagres;
        y gjenopprettes fra port_config.buildings.ground_top_y i on_enter.

        Market-tilstand trenger IKKE sync i C4+: Market er stateless og
        opererer direkte på state.economy_state.markets[port_id]. Gull og
        inventar muteres direkte av ExchangeOverlay. world_state.clock
        oppdateres kontinuerlig av main.run() via clock.update(dt).
        """
        self._state.player_state.position_x = float(self._player.x)

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

        - `from_scene=None` + player_state.position_x er GameState-default
          (320.0): fersk spillstart → buildings.player_start_x for havnen.
        - Ellers: player_state.position_x er autoritativ (lagret fra
          forrige økt eller synket av forrige scene ved bytte).

        Y-koordinaten gjenopprettes fra `port.buildings.ground_top_y` —
        per-havn bakke-høyde (C4).
        """
        GAMESTATE_DEFAULT_X = 320.0
        if (
            from_scene is None
            and game_state.player_state.position_x == GAMESTATE_DEFAULT_X
        ):
            self._player.x = float(self._buildings.player_start_x)
        else:
            self._player.x = float(game_state.player_state.position_x)
        # Klamp mot lovlig intervall (guard for korrupte saves)
        if self._player.x < self._player_min_x:
            self._player.x = self._player_min_x
        elif self._player.x > self._player_max_x:
            self._player.x = self._player_max_x
        # Y-koordinat fra per-havn ground_top_y
        self._player.y = float(
            self._buildings.ground_top_y - _PLAYER_SPRITE_HEIGHT
        )
        self._center_camera_on_player()

    def on_exit(self, to_scene: str | None = None) -> None:
        self.autosave()
