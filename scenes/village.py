"""Tortuga-landsbyens gate.

Scene-orchestrerer: eier verdens-state (Player, NPC-er, Market, Partikler,
Lys, Kamera, Overlay) og delegerer rendering til `VillageRenderer`.
Pre-rendrede lag og bake-hjelpere bor i `scenes/parallax_backdrops.py` og
`scenes/village_buildings.py`. Hint-teksten bor i `ui/hint.py`.

Komposisjon og verdenstall: se docstrings i `village_buildings.py`.
"""

from __future__ import annotations

import json
import logging
import os

import pygame

import constants
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
import random

from config import port_config
from state import GameState
from state.market_state import CommodityMarket, MarketState
from systems import save as save_module
from systems.day_cycle import DayCycle
from systems.dev_mode import is_dev_mode as _is_dev_mode
from systems.economy import (
    Market,
    apply_regime_drift_to_market_state,
    load_base_prices,
    sync_market_to_state,
)
from systems.lighting import Light, LightingSystem
from systems.parallax import Camera, ParallaxLayer, ParallaxRenderer
from systems.particles import ParticleSystem
from systems.pitch_lake import PitchLake
from systems.regime_manager import RegimeManager
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
        # og parallax-forgrunn. Himmel- og fg-backdrop-rendering skjer i
        # VillageRenderer. Fg-varianter (fjell + hav) ble skilt ut fra
        # himmel-variantene i Commit 7.2 slik at celestial kan tegnes
        # mellom dem og bli okkludert av fjell/hav ved horisont.
        self._backdrops = build_backdrop_variants()
        self._foregrounds = build_foreground_variants()
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
        # current_price og price_history fra Tortugas MarketState.
        # Dag-telleren eies av world_state.clock (GameClock), ikke Market.
        self._market = Market.from_json(
            os.path.join(constants.DATA_DIR, "commodities.json")
        )
        tortuga_market: MarketState = state.economy_state.markets.setdefault(
            "tortuga", MarketState()
        )
        for cid, saved in tortuga_market.commodities.items():
            try:
                commodity = self._market.get(cid)
            except KeyError:
                continue
            commodity.current_price = float(saved.current_price)
            commodity.price_history = list(saved.price_history)
            # Klamp loaded verdier mot gjeldende pris-grenser. Fase 2A
            # Commit 5D endret bek base_price 55 → 40 og klamp-forholdet
            # fra [0.3, 3.0] til [0.5, 2.0]; eksisterende saves kan ha
            # priser utenfor nye grenser (spesielt bek rundt 120+).
            self._market.clamp_to_price_bounds(cid)
        # Sync Market → state.markets["tortuga"] etter hydration-og-klamp
        # slik at state speiler Market eksakt (klamp kan ha endret priser).
        sync_market_to_state(self._market, tortuga_market)

        # Regime-system. Initialiser manglende regimer for Tortuga.
        self._regime_manager = RegimeManager()
        tortuga_regimes = state.economy_state.regimes.setdefault("tortuga", {})
        missing_ids = [
            c.id for c in self._market.commodities if c.id not in tortuga_regimes
        ]
        if missing_ids:
            tortuga_regimes.update(
                self._regime_manager.initialize_regimes(missing_ids)
            )
        # Dag-skift-sporing: naar clock.day overstiger denne, varsle
        # RegimeManager for hver dag som har passert.
        self._last_seen_day = state.world_state.clock.day

        # Base-priser caches for per-havn-drift av ikke-Tortuga-markeder.
        self._base_prices = load_base_prices(
            os.path.join(constants.DATA_DIR, "commodities.json")
        )
        # RNG for drift/noise på ikke-Tortuga-havner. Tortugas Market har
        # sin egen intern RNG.
        self._ports_rng = random.Random()
        # Cache port_ids (stabil rekkefølge, Tortuga først).
        self._port_ids = port_config.get_all_port_ids()

        # HUD (oeverst venstre: sted / gull / dag / bek-drift).
        # DEV-markør nederst til høyre aktiveres via dev-mode-flagg.
        from systems.dev_mode import is_dev_mode
        self._hud = Hud(
            font,
            place="Tortuga",
            gold=state.player_state.gold,
            day=state.world_state.clock.day,
            pitch_per_day=state.pitch_lake_state.production_per_day,
            pitch_upkeep=state.pitch_lake_state.upkeep_per_day,
            pitch_halted=self._compute_pitch_halted(),
            dev_mode=is_dev_mode(),
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
        self._overlay = ExchangeOverlay(
            self._font, self._market, self._state, toasts=self._toasts
        )
        # Autosave ved aapning slik at overgang til bors alltid kan trygges
        self.autosave()

    # --- Logikk ---

    def update(self, dt: float) -> None:
        # Dag-skift: ved daggry settes nye priser for ALLE 4 havner, og
        # regime-klokkene tikkes. Rekkefølgen er viktig: on_dawn først
        # slik at "siste dag" av et regime fortsatt har sin retnings-
        # effekt; regime_manager.on_new_day etterpå for overgang.
        #
        # Tortuga: Market.on_dawn (som holder aktiv Commodity-katalog for
        # rendering) + sync til state.markets["tortuga"].
        # Ikke-Tortuga: apply_regime_drift_to_market_state direkte på
        # state.markets[pid] (ingen Market-klasse per havn — se tech-debt-
        # note på Market i economy.py).
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

    def _tick_all_ports_dawn(self) -> None:
        """Prosesser daggry-overgang for alle 4 havner.

        Tortuga:
        - `Market.on_dawn(regimes)` oppdaterer aktiv Commodity-katalog
          (som rendres i exchange og brukes av buy/sell).
        - `regime_manager.on_new_day(regimes)` tikker regime-klokken.
        - `sync_market_to_state` kopierer Market → state.markets["tortuga"]
          slik at save/observed leser fersk data.

        Ikke-Tortuga:
        - `apply_regime_drift_to_market_state` muterer state.markets[pid]
          direkte (ingen Market-klasse; bias-initialisert fra port_config).
        - `regime_manager.on_new_day` på state.regimes[pid].

        Dev-mode: logger én linje per havn med regime-snapshot etter
        overgang.
        """
        econ = self._state.economy_state
        regimes_tortuga = econ.regimes.setdefault("tortuga", {})
        markets_tortuga = econ.markets.setdefault("tortuga", MarketState())
        day = self._state.world_state.clock.day
        dev = _is_dev_mode()

        # Tortuga — via Market-klassen + sync etter mutasjon
        self._market.on_dawn(regimes_tortuga)
        self._regime_manager.on_new_day(regimes_tortuga)
        sync_market_to_state(self._market, markets_tortuga)
        if dev:
            self._log_port_regimes("tortuga", regimes_tortuga, day)

        # Ikke-Tortuga — pure drift på state
        for port_id in self._port_ids:
            if port_id == "tortuga":
                continue
            market_state = econ.markets.setdefault(port_id, MarketState())
            port_regimes = econ.regimes.setdefault(port_id, {})
            apply_regime_drift_to_market_state(
                market_state, port_regimes, self._base_prices, self._ports_rng
            )
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
            self._overlay.draw(surface)

    # --- Lifecycle / save ---

    def _sync_state(self) -> None:
        """Kopier gjeldende scene-tilstand inn i GameState for lagring.

        player_state.position_x er den eneste koordinaten som lagres;
        y gjenopprettes fra scene-konstant (GROUND_TOP_Y - 20) på
        on_enter. Dette kan bli per-havn i C4.

        Tortuga-markedet synkes også her som defensiv fallback — det
        synkes allerede eksplisitt etter hver Market.on_dawn i
        `_tick_all_ports_dawn`, men sync-på-save beskytter mot
        scenarier der state har gått ut av synk uten dawn (bør ikke
        skje, men billig forsikring).
        """
        self._state.player_state.position_x = float(self._player.x)
        tortuga_market = self._state.economy_state.markets.setdefault(
            "tortuga", MarketState()
        )
        sync_market_to_state(self._market, tortuga_market)
        # gold og inventory er allerede lagret i self._state.player_state –
        # direkte mutert av ExchangeOverlay, saa ingen ekstra sync der.
        # world_state.clock oppdateres kontinuerlig av main.run() via
        # clock.update(dt), saa ingen sync her.

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

        - `from_scene=None` + player_state.position_x er default (320.0):
          fersk spillstart → PLAYER_START_X.
        - Ellers: player_state.position_x er autoritativ (lagret fra
          forrige oekt eller synket av forrige scene ved bytte).

        Y-koordinaten gjenopprettes fra scene-konstant (GROUND_TOP_Y).
        Per-havn bakke-høyde kan bli variabel i C4 når bygnings-
        plasseringer flytter til data/ports.json.
        """
        GAMESTATE_DEFAULT_X = 320.0
        if (
            from_scene is None
            and game_state.player_state.position_x == GAMESTATE_DEFAULT_X
        ):
            self._player.x = PLAYER_START_X
        else:
            self._player.x = float(game_state.player_state.position_x)
        # Klamp mot lovlig intervall (guard for korrupte saves)
        if self._player.x < self._player_min_x:
            self._player.x = self._player_min_x
        elif self._player.x > self._player_max_x:
            self._player.x = self._player_max_x
        self._center_camera_on_player()

    def on_exit(self, to_scene: str | None = None) -> None:
        self.autosave()
