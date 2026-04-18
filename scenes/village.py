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
from entities.npc import NPC
from entities.player import Player
from scenes.base_scene import BaseScene
from scenes.exchange import ExchangeOverlay
from scenes.parallax_backdrops import build_background_layer, build_empty_layer
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
from systems.economy import Market
from systems.lighting import Light, LightingSystem
from systems.parallax import Camera, ParallaxLayer, ParallaxRenderer
from systems.particles import ParticleSystem
from systems.save import GameState
from ui.hint import HintIndicator
from ui.hud import Hud


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
        fresh: bool = True,
    ) -> None:
        super().__init__()
        self._font = font
        self._state = state

        # Parallax-lag. Bakgrunn og tom forgrunn deles med parallax_test.
        bg_layer = ParallaxLayer(build_background_layer(), speed=0.2)
        gameplay_layer = ParallaxLayer(build_village_gameplay_layer(), speed=1.0)
        fg_layer = ParallaxLayer(build_empty_layer(1.3), speed=1.3)
        parallax_renderer = ParallaxRenderer([bg_layer, gameplay_layer, fg_layer])

        self._camera = Camera(constants.WORLD_WIDTH, constants.RENDER_WIDTH)

        # Spilleren: føttene hviler på GROUND_TOP_Y.
        # Ved fresh start bruker vi spec-verdien "midt paa gaten foran
        # Borshuset" (ignorerer GameState-defaultet 320/280 som er for en
        # generisk scene); ved lastet save bruker vi lagret x, men snapper
        # y til gatenivaa for robusthet.
        player_y = GROUND_TOP_Y - 20  # sprite-høyde 20
        if fresh:
            player_x = PLAYER_START_X
        else:
            player_x = float(state.player_position[0])
        self._player = Player(player_x, float(player_y))
        self._player_min_x = 8.0
        self._player_max_x = float(constants.WORLD_WIDTH - self._player.width - 8)
        # Klamp lastet x til lovlig intervall
        if self._player.x < self._player_min_x:
            self._player.x = self._player_min_x
        elif self._player.x > self._player_max_x:
            self._player.x = self._player_max_x

        # Kamera skal følge spilleren fra start
        self._center_camera_on_player()

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
        # current_price per vare hvis tilgjengelig.
        self._market = Market.from_json(
            os.path.join(constants.DATA_DIR, "commodities.json")
        )
        self._market.day = state.day
        for cid, saved in state.commodities_state.items():
            try:
                cp = float(saved.get("current_price"))
            except (TypeError, ValueError, AttributeError):
                continue
            try:
                self._market.get(cid).current_price = cp
            except KeyError:
                continue
        self._market_tick_timer: float = 0.0

        # HUD (oeverst venstre: sted / gull / dag)
        self._hud = Hud(
            font, place="Tortuga", gold=state.gold, day=state.day
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

        # Render-komposisjon (parallax + entiteter + lys + partikler + hint)
        self._renderer = VillageRenderer(parallax_renderer, hint)

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
        # Markedet ticker uansett — fremdeles drift i prisene mens overlayet
        # er aapent. Dette gjor det mulig aa se "markedet beveger seg" live.
        self._market_tick_timer += dt
        if self._market_tick_timer >= constants.MARKET_TICK_INTERVAL_SEC:
            self._market.tick()
            self._market_tick_timer -= constants.MARKET_TICK_INTERVAL_SEC

        # Lanterne-swing og andre tidsavhengige effekter gaar videre ogsaa.
        self._elapsed += dt
        self._particles.update(dt)

        # HUD – settere er no-ops hvis verdien ikke har endret seg
        self._hud.set_gold(self._state.gold)
        self._hud.set_day(self._market.day)

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

    def _center_camera_on_player(self) -> None:
        # Kamera sentrerer spilleren horisontalt; klamping gjøres av Camera
        target = self._player.x - (constants.RENDER_WIDTH - self._player.width) / 2
        self._camera.set_x(target)

    # --- Rendering ---

    def draw(self, surface: pygame.Surface) -> None:
        # Verdens-laget (bakgrunn → forgrunn) tegnes av renderen.
        self._renderer.draw(
            surface=surface,
            cam_x=self._camera.x,
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
        # HUD (oeverst venstre) og eventuell bors-overlay tegnes over alt.
        self._hud.draw(surface)
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
        self._state.day = self._market.day
        self._state.commodities_state = {
            c.id: {"current_price": float(c.current_price)}
            for c in self._market.commodities
        }
        # gold og inventory er allerede lagret i self._state – direkte mutert
        # av ExchangeOverlay, saa ingen ekstra sync der.

    def autosave(self) -> None:
        """Synk tilstand og skriv save-fil. Kalles fra main ved QUIT og
        fra scene selv ved overlay-aapning/lukking og scene-bytte."""
        self._sync_state()
        save_module.save(self._state)

    def on_exit(self) -> None:
        self.autosave()
