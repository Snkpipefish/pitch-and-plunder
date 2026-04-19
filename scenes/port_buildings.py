"""Generiske bake-funksjoner for havn-bygninger og gateplan.

Refaktorert fra `scenes/village_buildings.py` i Fase 2B C4: ingen
hardkodede posisjons-konstanter lenger. Alle bake-funksjoner tar
x/y/w/h (og ground_top_y der relevant) som argumenter. Konfig-drevne
verdier kommer fra `config.port_config.PortConfig.buildings`.

Tortugas komposisjon (som referanse):

    world x:  0 .. 20   | 20 .. 220  | 220 .. 1380 | 1380 .. 1580 | 1580 ..
              kant      | TAVERNA    | ÅPEN GATE   | BØRSHUS      | kant

Vertikalt (for ground_top_y=340):
    y = 0 .. 208    bakgrunn (himmel + måne + stjerner)  – separat lag
    y = 208 .. 340  bygnings-sone (tavernaen og børshuset okkluderer
                    sjø/horisont fra bakgrunnen)
    y = 340 .. 360  gateplan (full bredde, bakt inn i gameplay-laget)
"""

from __future__ import annotations

import pygame

import constants
from config.port_config import PortConfig


#: Colorkey for transparente områder på gameplay-laget. Fortsatt i bruk
#: her (gameplay-lag som har store transparente regioner over bygningene);
#: IKKE brukt på fg-laget som beholder SRCALPHA per C3b-funn.
COLORKEY = (255, 0, 255)


def _bake_ground(surface: pygame.Surface, ground_top_y: int) -> None:
    """Mørkt tre-/brostein-belte langs hele verdens bredde."""
    width = surface.get_width()
    ground_bottom_y = constants.RENDER_HEIGHT
    # Hovedstripe (mørkest)
    pygame.draw.rect(
        surface,
        constants.COLOR_WOOD_DARKEST,
        (0, ground_top_y, width, ground_bottom_y - ground_top_y),
    )
    # Lysere midt-stripe (litt mindre, sentrert) for variasjon
    pygame.draw.rect(
        surface,
        constants.COLOR_WOOD_DARK,
        (200, ground_top_y + 2, width - 400, ground_bottom_y - ground_top_y - 2),
    )
    # Små bjelke-detaljer (spare prikker)
    for x in range(260, width - 260, 80):
        pygame.draw.rect(
            surface, constants.COLOR_WOOD_MID, (x, ground_top_y + 4, 8, 1)
        )


def _bake_tavern(
    surface: pygame.Surface,
    x: int, y: int, w: int, h: int,
    ground_top_y: int,
) -> None:
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
    door_y = ground_top_y - door_h
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
    glow_rect = pygame.Rect(door_x - 8, ground_top_y, door_w + 16, 4)
    pygame.draw.rect(surface, constants.COLOR_EMBER, glow_rect)


def _bake_exchange(
    surface: pygame.Surface,
    x: int, y: int, w: int, h: int,
    ground_top_y: int,
) -> None:
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
    door_y = ground_top_y - door_h
    pygame.draw.rect(surface, constants.COLOR_STONE_DARKEST, (door_x, door_y, door_w, door_h))
    pygame.draw.rect(surface, constants.COLOR_STONE_MID, (door_x + 3, door_y + 3, door_w - 6, door_h - 6))
    # Svak kald "spill-over"-glød på trapp
    pygame.draw.rect(
        surface, constants.COLOR_STONE_LIGHT,
        (door_x - 4, ground_top_y, door_w + 8, 3),
    )


def build_port_gameplay_layer(port_config: PortConfig) -> pygame.Surface:
    """Pre-render gateplan + bygninger for hele verdens bredde i en havn.

    Leser layout fra `port_config.buildings`. Kaster ValueError hvis havnen
    ikke har buildings-felt ennå (ikke-Tortuga før C6).

    Returnerer en `convert()`-et Surface med COLORKEY satt slik at
    transparente områder (himmel over bygningene) vises gjennom.
    """
    if port_config.buildings is None:
        raise ValueError(
            f"Port '{port_config.id}' has no buildings layout — "
            f"cannot build gameplay layer"
        )
    b = port_config.buildings
    surf = pygame.Surface(
        (port_config.world_width, constants.RENDER_HEIGHT)
    ).convert()
    surf.fill(COLORKEY)
    _bake_ground(surf, b.ground_top_y)
    _bake_tavern(
        surf, b.tavern.x, b.tavern.y, b.tavern.w, b.tavern.h,
        b.ground_top_y,
    )
    _bake_exchange(
        surf, b.exchange.x, b.exchange.y, b.exchange.w, b.exchange.h,
        b.ground_top_y,
    )
    surf.set_colorkey(COLORKEY)
    return surf
