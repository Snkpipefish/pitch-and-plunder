"""Bake-funksjoner for Tortuga-landsbyens bygninger og gateplan.

Trekket ut av `scenes/village.py` i Fase 2A / Commit 1. Alt her er rene
bake-hjelpere som kalles én gang ved scene-innlasting for å produsere et
pre-rendret gameplay-lag. Ingen state, ingen per-frame-arbeid.

Komposisjon i verdensrommet (1600 px bredt):

    world x:  0 .. 20   | 20 .. 220  | 220 .. 1380 | 1380 .. 1580 | 1580 ..
              kant      | TAVERNA    | ÅPEN GATE   | BØRSHUS      | kant

Vertikalt:
    y = 0 .. 208    bakgrunn (himmel + måne + stjerner)  – separat lag
    y = 208 .. 340  bygnings-sone (tavernaen og børshuset okkluderer
                    sjø/horisont fra bakgrunnen)
    y = 340 .. 360  gateplan (full bredde, bakt inn i gameplay-laget)
"""

from __future__ import annotations

import pygame

import constants


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

# Midt-x på Børshuset, brukes for INTERACTION_DISTANCE-sjekk på E.
EXCHANGE_CENTER_X = EXCHANGE_X + EXCHANGE_W / 2  # 1480

# Colorkey for transparente områder på gameplay-laget.
COLORKEY = (255, 0, 255)


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


def build_village_gameplay_layer() -> pygame.Surface:
    """Pre-render gateplan + bygninger for hele verdens bredde.

    Returnerer en `convert()`-et Surface med COLORKEY satt slik at
    transparente områder (himmel over bygningene) vises gjennom.
    """
    surf = pygame.Surface((constants.WORLD_WIDTH, constants.RENDER_HEIGHT)).convert()
    surf.fill(COLORKEY)
    _bake_ground(surf)
    _bake_tavern(surf, TAVERN_X, TAVERN_Y, TAVERN_W, TAVERN_H)
    _bake_exchange(surf, EXCHANGE_X, EXCHANGE_Y, EXCHANGE_W, EXCHANGE_H)
    surf.set_colorkey(COLORKEY)
    return surf
