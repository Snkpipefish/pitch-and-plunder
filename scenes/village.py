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
from scenes.parallax_test import (
    _build_background_layer,
    _build_empty_layer,
)
from systems.parallax import Camera, ParallaxLayer, ParallaxRenderer


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
    """Tortuga-gate med taverna til venstre og børshus til høyre."""

    def __init__(self, font: pygame.font.Font) -> None:
        super().__init__()
        self._font = font

        # Parallax-lag (bakgrunn og forgrunn gjenbrukes fra parallax_test)
        bg_layer = ParallaxLayer(_build_background_layer(), speed=0.2)
        gameplay_layer = ParallaxLayer(_build_village_gameplay_layer(), speed=1.0)
        fg_layer = ParallaxLayer(_build_empty_layer(1.3), speed=1.3)
        self._renderer = ParallaxRenderer([bg_layer, gameplay_layer, fg_layer])

        self._camera = Camera(constants.WORLD_WIDTH, constants.RENDER_WIDTH)

        # Spilleren: føttene hviler på GROUND_TOP_Y
        player_y = GROUND_TOP_Y - 20  # sprite-høyde 20
        self._player = Player(PLAYER_START_X, float(player_y))
        self._player_min_x = 8.0
        self._player_max_x = float(constants.WORLD_WIDTH - self._player.width - 8)

        # Kamera skal følge spilleren fra start
        self._center_camera_on_player()

        # NPC-er
        npc_db = _load_npcs()
        self._npcs: list[NPC] = [
            NPC.from_data(npc_db["hawkins"], HAWKINS_X, float(player_y)),
        ]

        # Hint-tekst (cachet)
        self._hint = font.render(
            "A/D gaa  F11 fullskjerm  ESC avslutt",
            False,
            constants.COLOR_STONE_LIT,
        ).convert_alpha()
        self._hint_pos = (8, constants.RENDER_HEIGHT - 12)

    # --- Input ---

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            if event.key in constants.KEY_MENU:
                self.want_quit = True
            elif event.key in constants.KEY_LEFT:
                self._player.press(-1)
            elif event.key in constants.KEY_RIGHT:
                self._player.press(+1)
        elif event.type == pygame.KEYUP:
            if event.key in constants.KEY_LEFT:
                self._player.release(-1)
            elif event.key in constants.KEY_RIGHT:
                self._player.release(+1)

    # --- Logikk ---

    def update(self, dt: float) -> None:
        self._player.update(dt, self._player_min_x, self._player_max_x)
        self._center_camera_on_player()

    def _center_camera_on_player(self) -> None:
        # Kamera sentrerer spilleren horisontalt; klamping gjøres av Camera
        target = self._player.x - (constants.RENDER_WIDTH - self._player.width) / 2
        self._camera.set_x(target)

    # --- Rendering ---

    def draw(self, surface: pygame.Surface) -> None:
        cam_x = self._camera.x
        # Bakgrunn + gameplay-lag
        self._renderer.draw(surface, cam_x, start=0, stop=2)
        # Entiteter (spiller og NPC-er) i verdens-koordinater.
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
        # Forgrunnslag
        self._renderer.draw(surface, cam_x, start=2, stop=3)
        # Hint
        surface.blit(self._hint, self._hint_pos)
