"""Tortuga-landsbyens gate (Commit 4).

Komposisjon i verdensrommet (1600 px bredt):

    world x:  0 .. 20   | 20 .. 220  | 220 .. 1380 | 1380 .. 1580 | 1580 ..
              kant      | TAVERNA    | ÅPEN GATE   | BØRSHUS      | kant

Vertikalt:
    y = 0 .. 208    bakgrunn (himmel + måne + stjerner)  – separat lag
    y = 208 .. 340  bygnings-sone (tavernaen og børshuset okkluderer
                    sjø/horisont fra bakgrunnen)
    y = 340 .. 360  gateplan (full bredde, bakt inn i gameplay-laget)

Gameplay-laget er 1600×360 og pre-rendres én gang i `on_enter` / `__init__`.
Alt som ikke er bygning/gate er colorkey-transparent slik at bakgrunnen
vises gjennom.
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
from scenes.parallax_test import (
    _build_background_layer,
    _build_empty_layer,
)
from systems import save as save_module
from systems.economy import Market
from systems.lighting import Light, LightingSystem
from systems.parallax import Camera, ParallaxLayer, ParallaxRenderer
from systems.particles import ParticleSystem
from systems.save import GameState
from ui.hud import Hud


# Gateplan-tall (i intern render-oppløsning)
GROUND_TOP_Y = 340
GROUND_BOTTOM_Y = 360

# Bygningsposisjoner (verdens-x, topp-y, bredde, høyde)
TAVERN_X = 20
TAVERN_Y = 258
TAVERN_W = 200
TAVERN_H = GROUND_TOP_Y - TAVERN_Y  # 82

EXCHANGE_X = 1380
EXCHANGE_Y = 248
EXCHANGE_W = 200
EXCHANGE_H = GROUND_TOP_Y - EXCHANGE_Y  # 92

# Startposisjon: midt på gaten foran Børshuset (jfr. PROSJEKT.md §8)
PLAYER_START_X = 1340.0
# Hawkins står rett foran Børshusets trapp
HAWKINS_X = 1470.0
# Midt-x paa Borshuset, brukes for INTERACTION_DISTANCE-sjekk paa E
EXCHANGE_CENTER_X = EXCHANGE_X + EXCHANGE_W / 2  # 1480

# Colorkey for transparente områder på gameplay-laget
_COLORKEY = (255, 0, 255)


def _bake_ground(surface: pygame.Surface) -> None:
    """Mørkt tre-/brostein-belte langs hele verdens bredde."""
    width = surface.get_width()
    # Hovedstripe (mørkest)
    pygame.draw.rect(
        surface,
        constants.COLOR_WOOD_DARKEST,
        (0, GROUND_TOP_Y, width, GROUND_BOTTOM_Y - GROUND_TOP_Y),
    )
    # Lysere midt-stripe (litt mindre, sentrert) for variasjon
    pygame.draw.rect(
        surface,
        constants.COLOR_WOOD_DARK,
        (200, GROUND_TOP_Y + 2, width - 400, GROUND_BOTTOM_Y - GROUND_TOP_Y - 2),
    )
    # Små bjelke-detaljer (spare prikker)
    for x in range(260, width - 260, 80):
        pygame.draw.rect(
            surface, constants.COLOR_WOOD_MID, (x, GROUND_TOP_Y + 4, 8, 1)
        )


def _bake_tavern(surface: pygame.Surface, x: int, y: int, w: int, h: int) -> None:
    """Tavernaen: varmt tre med 2 opplyste vinduer, dør med varm gulv-glød."""
    # Veggen
    pygame.draw.rect(surface, constants.COLOR_WOOD_DARK, (x, y, w, h))
    # Horisontale plank-linjer
    for dy in (12, 30, 50, 70):
        pygame.draw.rect(
            surface, constants.COLOR_WOOD_DARKEST, (x, y + dy, w, 1)
        )
    # Tak-overheng (litt mørkere)
    pygame.draw.rect(
        surface, constants.COLOR_WOOD_DARKEST, (x - 8, y - 6, w + 16, 6)
    )
    pygame.draw.rect(
        surface, constants.COLOR_WOOD_MID, (x - 6, y - 6, w + 12, 1)
    )

    # To opplyste vinduer (bakt varm glød – Commit 5 legger på dynamisk lys)
    window_w, window_h = 24, 28
    window_y = y + 14
    for wx in (x + 40, x + w - 40 - window_w):
        pygame.draw.rect(
            surface,
            constants.COLOR_LANTERN,
            (wx, window_y, window_w, window_h),
        )
        pygame.draw.rect(
            surface,
            constants.COLOR_LANTERN_BRIGHT,
            (wx + 2, window_y + 2, window_w - 4, window_h - 4),
        )
        # Vindus-kors
        pygame.draw.rect(
            surface, constants.COLOR_WOOD_DARKEST,
            (wx + window_w // 2 - 1, window_y, 2, window_h),
        )
        pygame.draw.rect(
            surface, constants.COLOR_WOOD_DARKEST,
            (wx, window_y + window_h // 2 - 1, window_w, 2),
        )

    # Skilt mellom vinduene
    sign_x, sign_y, sign_w, sign_h = x + w // 2 - 26, y + 16, 52, 10
    pygame.draw.rect(
        surface, constants.COLOR_WOOD_LIGHT, (sign_x, sign_y, sign_w, sign_h)
    )
    pygame.draw.rect(
        surface, constants.COLOR_WOOD_MID, (sign_x + 1, sign_y + 1, sign_w - 2, sign_h - 2)
    )

    # Dør (åpen dør: varm glød-rektangel "fra innsiden")
    door_w, door_h = 24, 36
    door_x = x + w // 2 - door_w // 2
    door_y = GROUND_TOP_Y - door_h
    pygame.draw.rect(
        surface, constants.COLOR_WOOD_DARKEST, (door_x, door_y, door_w, door_h)
    )
    pygame.draw.rect(
        surface, constants.COLOR_FLAME, (door_x + 4, door_y + 8, door_w - 8, door_h - 8)
    )
    pygame.draw.rect(
        surface, constants.COLOR_LANTERN_BRIGHT,
        (door_x + 6, door_y + 10, door_w - 12, door_h - 14),
    )
    # Svak varm "teppe" av lys på gaten rett foran døren (baked, ikke dynamisk)
    glow_rect = pygame.Rect(door_x - 8, GROUND_TOP_Y, door_w + 16, 4)
    pygame.draw.rect(surface, constants.COLOR_EMBER, glow_rect)


def _bake_exchange(surface: pygame.Surface, x: int, y: int, w: int, h: int) -> None:
    """Børshuset: kald stein med 3 vinduer, 4 søyler og trekantgavl."""
    # Base
    pygame.draw.rect(surface, constants.COLOR_STONE_DARK, (x, y + 10, w, h - 10))
    # Gulv-stripe (mørk)
    pygame.draw.rect(
        surface, constants.COLOR_STONE_DARKEST, (x, y + 10, w, 1)
    )
    # Trekantgavl (pediment)
    pediment = [
        (x - 6, y + 12),
        (x + w + 6, y + 12),
        (x + w // 2, y - 10),
    ]
    pygame.draw.polygon(surface, constants.COLOR_STONE_DARKEST, pediment)
    # Frise/arkitrav
    pygame.draw.rect(surface, constants.COLOR_STONE_MID, (x - 4, y + 12, w + 8, 6))

    # Søyler (4 stk) – lit på venstre side
    col_w = 10
    col_h = h - 30
    col_y = y + 20
    col_xs = [x + 12, x + 60, x + w - 70, x + w - 22]
    for cx in col_xs:
        pygame.draw.rect(surface, constants.COLOR_STONE_MID, (cx, col_y, col_w, col_h))
        pygame.draw.rect(
            surface, constants.COLOR_STONE_LIGHT, (cx, col_y, 2, col_h)
        )
        pygame.draw.rect(
            surface, constants.COLOR_STONE_DARKEST, (cx + col_w - 1, col_y, 1, col_h)
        )
        # Kapitel og basis
        pygame.draw.rect(
            surface, constants.COLOR_STONE_LIGHT, (cx - 2, col_y, col_w + 4, 2)
        )
        pygame.draw.rect(
            surface, constants.COLOR_STONE_DARKEST, (cx - 2, col_y + col_h - 2, col_w + 4, 2)
        )

    # Tre kalde vinduer mellom søylene
    window_w, window_h = 18, 26
    window_y = y + 30
    window_centers = [x + 36, x + w // 2, x + w - 36]
    for wx in window_centers:
        wx0 = wx - window_w // 2
        pygame.draw.rect(
            surface, constants.COLOR_STONE_LIT, (wx0, window_y, window_w, window_h)
        )
        pygame.draw.rect(
            surface,
            constants.COLOR_STONE_BRIGHT,
            (wx0 + 2, window_y + 2, window_w - 4, window_h - 4),
        )
        pygame.draw.rect(
            surface, constants.COLOR_STONE_DARK,
            (wx0 + window_w // 2 - 1, window_y, 2, window_h),
        )

    # Stor dør (midtstilt)
    door_w, door_h = 26, 40
    door_x = x + w // 2 - door_w // 2
    door_y = GROUND_TOP_Y - door_h
    pygame.draw.rect(surface, constants.COLOR_STONE_DARKEST, (door_x, door_y, door_w, door_h))
    pygame.draw.rect(surface, constants.COLOR_STONE_MID, (door_x + 3, door_y + 3, door_w - 6, door_h - 6))
    # Svak kald "spill-over"-glød på trapp
    pygame.draw.rect(
        surface, constants.COLOR_STONE_LIGHT,
        (door_x - 4, GROUND_TOP_Y, door_w + 8, 3),
    )


def _build_village_gameplay_layer() -> pygame.Surface:
    """Pre-render gateplan + bygninger for hele verdens bredde."""
    surf = pygame.Surface((constants.WORLD_WIDTH, constants.RENDER_HEIGHT)).convert()
    surf.fill(_COLORKEY)
    _bake_ground(surf)
    _bake_tavern(surf, TAVERN_X, TAVERN_Y, TAVERN_W, TAVERN_H)
    _bake_exchange(surf, EXCHANGE_X, EXCHANGE_Y, EXCHANGE_W, EXCHANGE_H)
    surf.set_colorkey(_COLORKEY)
    return surf


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

        # Parallax-lag (bakgrunn og forgrunn gjenbrukes fra parallax_test)
        bg_layer = ParallaxLayer(_build_background_layer(), speed=0.2)
        gameplay_layer = ParallaxLayer(_build_village_gameplay_layer(), speed=1.0)
        fg_layer = ParallaxLayer(_build_empty_layer(1.3), speed=1.3)
        self._renderer = ParallaxRenderer([bg_layer, gameplay_layer, fg_layer])

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

        # Hint-tekst (cachet). Endres naar spilleren er ved borshuset.
        self._hint_far = font.render(
            "A/D gaa  F11 fullskjerm  ESC avslutt",
            False,
            constants.COLOR_STONE_LIT,
        ).convert_alpha()
        self._hint_near = font.render(
            "E aapne bors  A/D gaa  F11 fullskjerm  ESC avslutt",
            False,
            constants.COLOR_LANTERN_BRIGHT,
        ).convert_alpha()
        self._hint_pos = (8, constants.RENDER_HEIGHT - 12)

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
        cam_x = self._camera.x
        # 1) Bakgrunn + gameplay-lag
        self._renderer.draw(surface, cam_x, start=0, stop=2)
        # 2) Entiteter (spiller og NPC-er) i verdens-koordinater.
        # Bruk fblits for én batch; ingen overlap-sortering er nødvendig
        # i Fase 1 siden alle står på samme gatenivå.
        cx = int(cam_x)
        batch: list[tuple[pygame.Surface, tuple[int, int]]] = []
        for npc in self._npcs:
            batch.append((npc.sprite, (int(npc.x) - cx, int(npc.y))))
        batch.append(
            (self._player.sprite, (int(self._player.x) - cx, int(self._player.y)))
        )
        surface.fblits(batch)
        # 3) Dynamiske lys (BLEND_RGB_ADD) – legger seg over bygninger og
        # entiteter slik at lyset "faller på" spilleren.
        self._lighting.draw(surface, self._lights, cam_x, self._elapsed)
        # 4) Partikler: taake (normal blit) + ildfluer (BLEND_RGB_ADD).
        # Taake tegnes ETTER lysene slik at tavernaens varme gloed ikke
        # vasker taaken oransje – taaken forblir kald og atmosfaerisk.
        # Ildfluene tegnes til slutt i systemet siden de er "naerere" og
        # skal stikke gjennom taaken.
        self._particles.draw(surface, cam_x)
        # 5) Hint-linje
        hint_surf = (
            self._hint_near
            if self._player_can_interact_with_exchange() and self._overlay is None
            else self._hint_far
        )
        surface.blit(hint_surf, self._hint_pos)
        # 6) Forgrunnslag
        self._renderer.draw(surface, cam_x, start=2, stop=3)
        # 7) HUD (oeverst venstre)
        self._hud.draw(surface)
        # 8) Overlay (borsen) — over alt
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
