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
import os
import random

import pygame

import constants
from config import port_config
from config.port_config import PortConfig
from entities.celestial import Celestial
from entities.npc import NPC
from entities.npc_silhouette import NPCSilhouette, build_silhouette
from entities.player import Player
from scenes.base_scene import BaseScene
from scenes.exchange import ExchangeOverlay
from ui.cache_dialog import CacheSubDialog
from ui.harbormaster_dialog import HarbormasterDialog
from ui.rumors_dialog import RumorsDialog
from ui.tavern_dialog import TavernDayDialog, TavernDialog, TavernNightDialog
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
from systems.animations import PaletteCycleSource, apply_palette_cycles
from systems.day_cycle import DayCycle, compute_night_factor
from systems.economy import Market, load_base_prices, tick_all_ports_dawn
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

# Spiller-posisjon ved retur fra verdenskart — plasseres rett innenfor
# dock-region. Samme for alle havner siden dock er venstre verdens-kant.
# Dock-sprite og eventuelt per-havn dock_return_x flyttes til
# port_config.buildings i C7 sammen med voyage-arbeidet.
_DOCK_RETURN_X = 60.0


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
        # Forgrunns-variantene får nå havn-spesifikke ankrede skip-
        # silhuetter bakt inn (C2.5-5). 4 havner × 6 dag-faser = 24
        # pre-rendringer ved init; per-frame-blit er uendret.
        self._foregrounds = build_foreground_variants(port)
        # C2.5-8b: build_port_gameplay_layer returnerer (day, night)-tuple.
        # PortVillageScene holder begge og bytter mellom dem hver frame
        # basert på night_factor (threshold 0.5 — MVP-snap). Cross-fade-
        # tilstanden vises under kort sunrise/sunset-overgang (~1 sek
        # på 180 s/dag ved threshold 0.5).
        (
            self._gameplay_day_surface,
            self._gameplay_night_surface,
        ) = build_port_gameplay_layer(port)
        self._gameplay_layer = ParallaxLayer(
            self._gameplay_night_surface, speed=1.0
        )
        # C2.5-9 palette-cycling — konverter PaletteCycle-config til
        # PaletteCycleSource-runtime-objekter. Cycling muterer
        # gameplay-night-surfacen per frame (billig for <25 px totalt).
        # Permanent-cycles (smithy-esse, bål) gjelder også day-surface
        # siden disse er 24/7-lys.
        self._palette_cycles: list[PaletteCycleSource] = []
        self._palette_cycles_permanent: list[PaletteCycleSource] = []
        if self._buildings.animations.palette_cycles:
            for pc in self._buildings.animations.palette_cycles:
                src = PaletteCycleSource(
                    x=pc.x, y=pc.y, w=pc.w, h=pc.h,
                    palette=pc.palette, fps=pc.fps,
                    permanent=pc.permanent,
                )
                self._palette_cycles.append(src)
                if pc.permanent:
                    self._palette_cycles_permanent.append(src)
        fg_layer = ParallaxLayer(build_empty_layer(1.3), speed=1.3)
        parallax_renderer = ParallaxRenderer([self._gameplay_layer, fg_layer])
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

        # Rekvisita-silhuetter (Fase 2.5 C2.5-1). Statiske, ikke-
        # interaktive sprites som fyller gaten mellom tavernaen og
        # børshuset. Bakt ved init; tegnes i samme fblits-batch som
        # NPC-er av PortVillageRenderer.
        self._silhouettes: list[NPCSilhouette] = []
        if self._buildings.props is not None:
            for placement in self._buildings.props.silhouettes:
                self._silhouettes.append(
                    build_silhouette(
                        placement.kind,
                        placement.x,
                        self._buildings.ground_top_y,
                    )
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
        # Børshusets midtvindu (ev. åpen markedsplass for Nassau).
        # Nassau har ingen børs-BYGNING — lyset må være varmt bål/
        # lantern-glow som tematisk matcher markedsplassen, ikke
        # kaldt vindu-lys som antyder stein-bygning. Per FASE_2_5.md
        # §2.4: "Ingen kald institusjonell farge".
        exchange_window_x = exchange.x + exchange.w / 2
        if port.id == "nassau":
            # Plassering over markedsplassens midterste bord (vekt-stokk
            # og bål-stemning). Warm LANTERN-glow radius 55 (litt mindre
            # enn børs-vindu fordi det er "lokal belysning", ikke et
            # lite opplyst institusjonelt fasade).
            exchange_window_y = self._buildings.ground_top_y - 14
            exchange_window_color = constants.COLOR_LANTERN
            exchange_window_radius = 55
        else:
            exchange_window_y = exchange.y + 42
            exchange_window_color = constants.COLOR_STONE_LIT
            exchange_window_radius = 60
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
                radius=exchange_window_radius,
                color=exchange_window_color,
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
        # Tavern-dialog (C3-3) — None naar lukket. Mutually eksklusiv med
        # børs-overlay (hver kommer fra forskjellig bbox-interact).
        # Type er TavernDialog (base); instantieres som Day eller Night
        # basert på night_factor ved åpning.
        self._tavern_dialog: TavernDialog | None = None
        # Havnekontor-dialog (C3-4) — None naar lukket. Mutually eksklusiv
        # med exchange og tavern. Kan starte voyage eller transisjon til
        # WorldMapScene via `requested_next_scene`, eller signalere at
        # CacheSubDialog skal åpnes via `open_cache` (C3-5).
        self._harbormaster_dialog: HarbormasterDialog | None = None
        # Cache-subdialog (C3-5) — None naar lukket. Peer til
        # HarbormasterDialog (ikke nested) per design. Åpnes etter at
        # HarbormasterDialog lukkes med `open_cache=True`.
        self._cache_dialog: CacheSubDialog | None = None
        # Rykte-dialog (C3-9) — åpnes med R-tast, viser aktive rykter.
        # Kun les-visning. Lukkes med ESC.
        self._rumors_dialog: RumorsDialog | None = None

        # Hint-indikator (multi-tilstand). "near" er børs-hint (2A-kompat);
        # "near_dock" er kart-hint (C5); "near_tavern" er tavern-hint (C3-3).
        hint = HintIndicator(
            font=font,
            far_text="A/D gå   F11 fullskjerm   Esc avslutt",
            near_text="E åpne børs   A/D gå   F11 fullskjerm   Esc avslutt",
            far_color=constants.COLOR_STONE_LIT,
            near_color=constants.COLOR_LANTERN_BRIGHT,
            pos=(8, constants.RENDER_HEIGHT - 12),
        )
        hint.add_state(
            "near_dock",
            "E åpne verdenskart   A/D gå   F11 fullskjerm   Esc avslutt",
            constants.COLOR_LANTERN_BRIGHT,
        )
        hint.add_state(
            "near_tavern",
            "E åpne tavern   A/D gå   F11 fullskjerm   Esc avslutt",
            constants.COLOR_LANTERN_BRIGHT,
        )
        hint.add_state(
            "near_harbormaster",
            "E åpne havnekontor   A/D gå   F11 fullskjerm   Esc avslutt",
            constants.COLOR_LANTERN_BRIGHT,
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
        # Tavern-dialog konsumerer også all input når åpen.
        if self._tavern_dialog is not None:
            self._tavern_dialog.handle_event(event)
            return
        # Havnekontor-dialog (C3-4) — samme input-konsumpsjon.
        if self._harbormaster_dialog is not None:
            self._harbormaster_dialog.handle_event(event)
            return
        # Cache-subdialog (C3-5) — samme mønster.
        if self._cache_dialog is not None:
            self._cache_dialog.handle_event(event)
            return
        # Rykte-dialog (C3-9) — samme mønster.
        if self._rumors_dialog is not None:
            self._rumors_dialog.handle_event(event)
            return
        if event.type == pygame.KEYDOWN:
            if event.key in constants.KEY_MENU:
                self.want_quit = True
            elif event.key in constants.KEY_RUMORS:
                # Fase 3 C3-9: R åpner RumorsDialog (rykte-liste).
                self._open_rumors_dialog()
            elif event.key in constants.KEY_INTERACT:
                # Prioritet: exchange > tavern > harbormaster > dock.
                # Bygningene står på distinkte x-regioner (verifisert
                # ved ports.json-load via _validate_harbormaster_placement);
                # normalt kun én interaksjon tilgjengelig om gangen.
                if self._player_can_interact_with_exchange():
                    self._open_exchange()
                elif self._player_can_interact_with_tavern():
                    self._open_tavern()
                elif self._player_can_interact_with_harbormaster():
                    self._open_harbormaster()
                elif self._player_can_interact_with_dock():
                    self._open_world_map()
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

    def _player_can_interact_with_tavern(self) -> bool:
        """True hvis spilleren står innen INTERACTION_DISTANCE av
        tavern-senteret (Fase 3 C3-3).

        Tavern-bbox kommer fra `port_config.buildings.tavern`. Samme
        avstands-mål (INTERACTION_DISTANCE) som for exchange og dock.
        """
        player_center_x = self._player.x + self._player.width / 2
        tavern = self._buildings.tavern
        return (
            abs(player_center_x - (tavern.x + tavern.w / 2))
            < constants.INTERACTION_DISTANCE
        )

    def _player_can_interact_with_harbormaster(self) -> bool:
        """True hvis spilleren står innen INTERACTION_DISTANCE av
        harbormaster-senteret (Fase 3 C3-4).

        Havnekontor-bbox kommer fra `port_config.buildings.harbormaster`.
        None-bbox (havn uten havnekontor) → alltid False.
        """
        if self._buildings.harbormaster is None:
            return False
        player_center_x = self._player.x + self._player.width / 2
        hm = self._buildings.harbormaster
        return (
            abs(player_center_x - (hm.x + hm.w / 2))
            < constants.INTERACTION_DISTANCE
        )

    def _player_can_interact_with_dock(self) -> bool:
        """True hvis spiller er i dock-region (venstre verdens-kant).

        Per FASE_2B.md §3.3: spilleren går til havn-kant-sprite, trykker
        E → åpner verdenskart. Range leses fra port.buildings.
        dock_interaction_range — flyttet fra modul-konstanter i C6.
        """
        player_center_x = self._player.x + self._player.width / 2
        dock_min, dock_max = self._buildings.dock_interaction_range
        return dock_min <= player_center_x <= dock_max

    def _open_world_map(self) -> None:
        """Åpne verdenskart (instant cut — fade kommer i C7)."""
        self._player.press(0)
        self.autosave()
        self.next_scene = "world_map"

    def _compute_hint_state(self) -> str:
        """Velg hint-tilstand basert på spiller-posisjon og overlay-state.

        Prioritet: exchange > tavern > harbormaster > dock > far. Åpen
        dialog/overlay → far (ingen hint mens spilleren handler).
        """
        if (
            self._overlay is not None
            or self._tavern_dialog is not None
            or self._harbormaster_dialog is not None
            or self._cache_dialog is not None
            or self._rumors_dialog is not None
        ):
            return "far"
        if self._player_can_interact_with_exchange():
            return "near_exchange"
        if self._player_can_interact_with_tavern():
            return "near_tavern"
        if self._player_can_interact_with_harbormaster():
            return "near_harbormaster"
        if self._player_can_interact_with_dock():
            return "near_dock"
        return "far"

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

    def _open_tavern(self) -> None:
        """Åpne tavern-dialog (dag eller natt basert på night_factor).

        Threshold 0.5 matcher sprite-variant-snap — spilleren ser samme
        visuell dag/natt-tilstand som menyen de får.

        Dag-vs-natt-bytte: ved terskel-krysning UNDER åpen dialog byttes
        ikke dialogen dynamisk. Spilleren må lukke og åpne på nytt.
        Dette er konsistent med at menyen opplever dagens eller nattens
        tavern-atmosfære — ikke en hybrid-tilstand midt i overgangen.

        Fase 3 C3-3: dag/natt drives av GameClock/night_factor, IKKE
        ActionBudget. ActionBudget-cutover kommer i senere commit
        (C3-7/C3-8) når mistanke/rom-systemer wires til scene-tid.
        """
        self._player.press(0)
        celestial_cfg = port_config.get(
            self._state.world_state.current_port
        ).celestial
        snapshot = DayCycle.compute_snapshot(
            self._state.world_state.clock, celestial_cfg
        )
        night_factor = compute_night_factor(snapshot.day_fraction)
        dialog_cls = (
            TavernNightDialog if night_factor >= 0.5 else TavernDayDialog
        )
        self._tavern_dialog = dialog_cls(
            self._font,
            self._state,
            port_id=self._port.id,
            toasts=self._toasts,
        )
        self.autosave()

    def _open_rumors_dialog(self) -> None:
        """Åpne rykte-liste (Fase 3 C3-9). R-tast.

        Kun les-visning — dialogen muterer ikke state, så ingen autosave
        ved åpning/lukking. Ignorert hvis en annen dialog er åpen (R
        gir da ingen effekt, siden handle_event sender events til den
        åpne dialogen først).
        """
        self._player.press(0)
        self._rumors_dialog = RumorsDialog(self._font, self._state)

    def _open_cache_dialog(self) -> None:
        """Åpne CacheSubDialog for gjeldende havn (Fase 3 C3-5).

        Kalt fra update() etter at HarbormasterDialog lukkes med
        `open_cache=True`. Ingen direkte interaksjon via E — cache
        nås kun via havnekontor-dialogen.
        """
        self._cache_dialog = CacheSubDialog(
            self._font,
            self._state,
            port_id=self._port.id,
            toasts=self._toasts,
        )

    def _open_harbormaster(self) -> None:
        """Åpne havnekontor-dialog (Fase 3 C3-4).

        Dialogen eksponerer fast-travel-ruter + cache-stub (C3-5) +
        "Vis kart"-snarvei. Aktivering av reise → dialog setter
        `requested_next_scene="voyage"`; scene-owner leser dette ved
        close og utfører transisjon.
        """
        self._player.press(0)
        self._harbormaster_dialog = HarbormasterDialog(
            self._font,
            self._state,
            port_id=self._port.id,
            toasts=self._toasts,
        )
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
        # Fase 3 C3-7: mistanke-linje. Oppdateres per frame (no-op hvis
        # int-value uendret). Verdien endres kun ved dawn-decay eller
        # eksplisitt suspicion.increase-kall fra dialog-handlinger.
        self._hud.set_suspicion(self._state.player_state.suspicion)
        # Fase 3 C3-8: rom-linje. Oppdateres per frame (no-op hvis
        # pct-int uendret). Verdien endres via rest.consume_for_*-
        # kall fra dialog-handlerne (bek-kjøp, fast-travel, cache-
        # commit) og rest.restore fra rom-kjøp.
        self._hud.set_rest(self._state.player_state.rest)
        # Fase 3 C3-9: rykter-linje. Teller aktive rykter (skjules ved 0).
        self._hud.set_rumor_count(
            len(self._state.player_state.active_rumors)
        )

        if self._overlay is not None:
            self._overlay.update(dt, self._current_market_state())
            if self._overlay.want_close:
                self._overlay = None
                # Autosave også ved lukking slik at brukeren kan quit-e
                # umiddelbart etter handel uten risiko for tap.
                self.autosave()
            return
        if self._tavern_dialog is not None:
            # Tavern-dialog har ingen `update` (ingen tidsdrevet logikk
            # internt — balance hot-reload sjekkes i draw via
            # `_balance_changed`). Bare poll want_close og lukk.
            if self._tavern_dialog.want_close:
                self._tavern_dialog = None
                self.autosave()
            return
        if self._harbormaster_dialog is not None:
            # Havnekontor-dialog — samme close-mønster. Kan signalere:
            # (a) scene-transisjon via requested_next_scene (voyage/map),
            # (b) åpning av CacheSubDialog via open_cache (C3-5).
            # Transisjonen skjer etter autosave slik at state er
            # persistert før ny scene/dialog instansieres.
            if self._harbormaster_dialog.want_close:
                requested = self._harbormaster_dialog.requested_next_scene
                open_cache = self._harbormaster_dialog.open_cache
                self._harbormaster_dialog = None
                self.autosave()
                if requested is not None:
                    self.next_scene = requested
                elif open_cache:
                    self._open_cache_dialog()
            return
        if self._cache_dialog is not None:
            if self._cache_dialog.want_close:
                self._cache_dialog = None
                self.autosave()
            return
        if self._rumors_dialog is not None:
            if self._rumors_dialog.want_close:
                self._rumors_dialog = None
                # Ingen autosave — rykte-dialogen muterer ikke state.
            return
        # Kun naar overlayet er lukket kan spilleren bevege seg.
        self._player.update(dt, self._player_min_x, self._player_max_x)
        self._center_camera_on_player()

    def _tick_all_ports_dawn(self) -> None:
        """Tynn delegasjon til `economy.tick_all_ports_dawn` (C7a-refactor).

        Behold som scene-metode slik at update-løkken er uendret.
        Dev-mode-loggingen lever i modul-funksjonen.
        """
        tick_all_ports_dawn(self._state, self._market, self._regime_manager)

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
        # C2.5-8b: dag/natt-lys-gating. Bytt gameplay-lag-surface basert
        # på night_factor. Threshold 0.5 gir snap-overgang i løpet av
        # ~1 sekund midt i sunrise/sunset. De 3 dynamiske lysene (taverna-
        # lanterne/dør/exchange-vindu) får samme gating via
        # LightingSystem.draw's night_factor-parameter.
        night_factor = compute_night_factor(snapshot.day_fraction)
        self._gameplay_layer.surface = (
            self._gameplay_night_surface
            if night_factor >= 0.5
            else self._gameplay_day_surface
        )
        # C2.5-9 palette-cycling — muterer valgt gameplay-surface per
        # frame. I natt-surface: alle cycles (gated + permanent). I
        # day-surface: kun permanent (smithy-esse, bål brenner 24/7).
        if night_factor >= 0.5:
            apply_palette_cycles(
                self._gameplay_night_surface,
                self._palette_cycles,
                self._elapsed,
                night_factor,
            )
        elif self._palette_cycles_permanent:
            apply_palette_cycles(
                self._gameplay_day_surface,
                self._palette_cycles_permanent,
                self._elapsed,
                night_factor,
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
            hint_state=self._compute_hint_state(),
            silhouettes=self._silhouettes,
            night_factor=night_factor,
        )
        # HUD (oeverst venstre) og toasts (bunn-sentrert) tegnes over
        # verden men under bors-overlay.
        self._hud.draw(surface)
        self._toasts.draw(surface)
        if self._overlay is not None:
            self._overlay.draw(surface, self._current_market_state())
        elif self._tavern_dialog is not None:
            self._tavern_dialog.draw(surface)
        elif self._harbormaster_dialog is not None:
            self._harbormaster_dialog.draw(surface)
        elif self._cache_dialog is not None:
            self._cache_dialog.draw(surface)
        elif self._rumors_dialog is not None:
            self._rumors_dialog.draw(surface)

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
        """Plasser spilleren og sentrer kamera. Kjør ankomst-rituale
        ved retur fra reise (C7c).

        - `from_scene="voyage"`: spilleren har akkurat ankommet etter
          en sjøreise. Kjør write_observed_for_port (target-havnens
          priser registreres som ferskt sett), realize_pending_units
          hvis dette er home_port, og push ankomst-toast. Plasser ved
          dock (samme som "world_map"-stien).
        - `from_scene="world_map"`: spilleren kommer tilbake fra kartet
          uten reise — plasseres ved dock-retur-x.
        - `from_scene=None` + player_state.position_x er GameState-default
          (320.0): fersk spillstart → buildings.player_start_x for havnen.
        - Ellers: player_state.position_x er autoritativ (lagret fra
          forrige økt eller synket av forrige scene ved bytte).

        Y-koordinaten gjenopprettes fra `port.buildings.ground_top_y` —
        per-havn bakke-høyde (C4).
        """
        # Ankomst-rituale (C7c). VoyageScene har allerede kalt
        # complete_voyage så current_port er to_port og clock er
        # in_port-tempo. Vi behøver kun observed-snapshot, pending-
        # realisering og toast.
        if from_scene == "voyage":
            self._handle_voyage_arrival()
        else:
            # C8: snapshot observed for current_port på alle andre
            # scene-inngangs-stier (initial spawn, retur fra kart,
            # debug-teleport). Idempotent — overskriver eksisterende
            # observed for current_port med dagens pris. Dette dekker
            # tilfellet "spilleren åpner spillet og forventer å se
            # ferskt observed-data" uten å vente på første dawn.
            from systems.economy import write_observed_for_port
            write_observed_for_port(self._state, self._port.id)

        GAMESTATE_DEFAULT_X = 320.0
        if from_scene in ("world_map", "voyage"):
            self._player.x = _DOCK_RETURN_X
        elif (
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

    def _handle_voyage_arrival(self) -> None:
        """Ankomst-rituale (C7c). Kalles fra on_enter når from_scene
        er "voyage".

        Forutsetning: VoyageScene.update har allerede kalt
        voyage.complete_voyage, så `state.world_state.voyage` er None,
        `current_port` er to_port og clock-tempo er in_port. Vi rører
        ikke disse her — ankomst-rituale handler kun om observed-
        snapshot, pending-realisering og brukervarsel.
        """
        from systems.economy import write_observed_for_port
        from systems.pitch_lake import PitchLake

        port_id = self._port.id
        # Snapshot priser i ny havn — dette er ferskt observert data
        # (spilleren ser priser umiddelbart ved ankomst). Stale-logikk
        # i C8 vil sammenligne mot clock.day.
        write_observed_for_port(self._state, port_id)

        # Realiser pending bek hvis vi ankommer home_port (typisk
        # Tortuga). Pending som ikke får plass forblir for neste retur.
        pl_state = self._state.pitch_lake_state
        if port_id == pl_state.home_port and pl_state.pending_units > 0:
            realized = PitchLake.realize_pending_units(
                pl_state, self._state,
            )
            if realized > 0:
                self._toasts.push(Toast(
                    font=self._font,
                    text=f"Hentet {realized} bek fra kaia",
                    color=constants.COLOR_LANTERN_BRIGHT,
                ))

        # Ankomst-toast
        self._toasts.push(Toast(
            font=self._font,
            text=f"Ankommet {self._port.name}",
            color=constants.COLOR_MOON_CORE,
        ))

    def on_exit(self, to_scene: str | None = None) -> None:
        self.autosave()
