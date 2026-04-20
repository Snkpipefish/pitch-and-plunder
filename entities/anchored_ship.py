"""Ankrede skip-silhuetter for havn-scener (Fase 2.5 C2.5-5).

Skip bakes inn i SRCALPHA foreground-variantene ved scene-init — én
gang per havn × dag-fase. Per-frame-kost er uendret siden forgrunns-
variantene allerede blittes hver frame; skipene er bare del av samme
surface.

Skip-typer per FASE_2_5.md §2.3/2.4:
- smuggler  — Tortuga, liten mørk skuter
- frigate   — Port Royal, britisk med flagg
- galleon   — Havana, spansk imperiell
- small     — Havana, mindre spansk skip
- pirate    — Nassau, ragget liten skute (kan skråstilles)

Skip tegnes direkte på surface; fargene holder seg innenfor master-
paletten. Ingen `convert_alpha()` på sprites (de blittes direkte til
forgrunnen som allerede er SRCALPHA).
"""

from __future__ import annotations

import pygame

import constants


#: Colorkey for sprite-fabrikker som bruker opak surface + colorkey-
#: transparens før blit til forgrunn. `draw_anchored_ship` tegner
#: imidlertid direkte på en SRCALPHA-surface via pygame.draw.*-kall,
#: så fabrikkene er her ikke nødvendige. Beholdt for fremtidig utvidelse
#: (f.eks. hvis skip skal kunne animeres via palette-cycling i C2.5-6).
_CK = (255, 0, 255)


#: Gyldige skip-typer. Validering skjer i `config/port_config.py`-parser.
VALID_SHIP_KINDS: frozenset[str] = frozenset({
    "smuggler", "frigate", "galleon", "small", "pirate",
})


def _draw_smuggler(
    surface: pygame.Surface, x: int, y: int, flipped: bool = False,
) -> None:
    """Tortuga smugler-skuter — liten, mørk, ett seil.

    Dimensjoner: 18×14 (inkludert mast).
    `y` er bunn av skroget (vannlinjen).
    Palett: WOOD_DARK skrog, WOOD_DARKEST detaljer, WOOD_MID seil (mørkt).
    """
    # Skrog (lite og lavt, WOOD_DARK)
    hull_y = y - 4
    pygame.draw.rect(
        surface, constants.COLOR_WOOD_DARK, (x, hull_y, 18, 3),
    )
    # Buen (spisset front)
    bow_x = x + 18 if not flipped else x - 2
    pygame.draw.rect(
        surface, constants.COLOR_WOOD_DARK, (bow_x - (1 if flipped else 0), hull_y + 1, 2, 1),
    )
    # Skygge under skroget
    pygame.draw.rect(
        surface, constants.COLOR_WOOD_DARKEST, (x, hull_y + 2, 18, 1),
    )
    # Mast
    mast_x = x + 10 if not flipped else x + 7
    pygame.draw.rect(
        surface, constants.COLOR_WOOD_DARKEST, (mast_x, hull_y - 9, 1, 9),
    )
    # Trekantet seil — WOOD_MID (mørkt, smuglersignal)
    if not flipped:
        seil_pts = [
            (mast_x, hull_y - 9),
            (mast_x, hull_y - 1),
            (mast_x - 6, hull_y - 1),
        ]
    else:
        seil_pts = [
            (mast_x, hull_y - 9),
            (mast_x, hull_y - 1),
            (mast_x + 6, hull_y - 1),
        ]
    pygame.draw.polygon(surface, constants.COLOR_WOOD_MID, seil_pts)
    # Seil-kant
    pygame.draw.line(
        surface, constants.COLOR_WOOD_DARKEST,
        seil_pts[0], seil_pts[2], 1,
    )


def _draw_frigate(
    surface: pygame.Surface, x: int, y: int, flipped: bool = False,
) -> None:
    """Port Royal britisk fregatt — større, ordnet, hvitkalket + flagg.

    Dimensjoner: 30×22 (inkludert master).
    Palett: WOOD_LIGHT skrog (britisk hvitkalket), SHIRT seil, EMBER flagg.
    """
    hull_y = y - 5
    # Hull (WOOD_LIGHT — lysere britisk skrog)
    pygame.draw.rect(
        surface, constants.COLOR_WOOD_LIGHT, (x, hull_y, 30, 4),
    )
    # Hvit stripe (klassisk britisk)
    pygame.draw.rect(
        surface, constants.COLOR_SHIRT, (x, hull_y + 1, 30, 1),
    )
    # Kanon-porter (3 små mørke rektangler)
    for dx in (5, 14, 23):
        pygame.draw.rect(
            surface, constants.COLOR_WOOD_DARKEST,
            (x + dx, hull_y + 2, 2, 1),
        )
    # Buen
    pygame.draw.rect(
        surface, constants.COLOR_WOOD_LIGHT,
        (x + (30 if not flipped else -2), hull_y + 1, 2, 2),
    )
    # Akter (bakkastell)
    stern_x = x - 2 if not flipped else x + 30
    pygame.draw.rect(
        surface, constants.COLOR_WOOD_LIGHT,
        (stern_x, hull_y - 2, 4, 3),
    )
    pygame.draw.rect(
        surface, constants.COLOR_WOOD_MID,
        (stern_x, hull_y - 2, 4, 1),
    )
    # Skygge under skroget
    pygame.draw.rect(
        surface, constants.COLOR_WOOD_DARKEST, (x, hull_y + 3, 30, 1),
    )

    # To master (for-mast og storm-mast)
    mast_xs = [x + 8, x + 20]
    for i, mx in enumerate(mast_xs):
        mast_h = 13 if i == 1 else 11  # Storm-masten litt høyere
        pygame.draw.rect(
            surface, constants.COLOR_WOOD_DARKEST,
            (mx, hull_y - mast_h, 1, mast_h),
        )
        # Fulle seil (rektangulære britiske)
        sail_w = 8
        sail_h = mast_h - 2
        sx = mx - sail_w // 2
        pygame.draw.rect(
            surface, constants.COLOR_SHIRT,
            (sx, hull_y - mast_h + 1, sail_w, sail_h),
        )
        # Seil-kant
        pygame.draw.rect(
            surface, constants.COLOR_STONE_LIGHT,
            (sx, hull_y - mast_h + 1, sail_w, 1),
        )
        pygame.draw.rect(
            surface, constants.COLOR_STONE_LIGHT,
            (sx, hull_y - mast_h + 1, 1, sail_h),
        )
    # Britisk flagg på storm-mast (EMBER — rødt "Red Ensign"-signal)
    flag_mast = mast_xs[1]
    flag_y = hull_y - 13
    pygame.draw.rect(
        surface, constants.COLOR_EMBER, (flag_mast + 1, flag_y, 4, 2),
    )
    # Hvit lin (MOON_HALO for kant)
    pygame.draw.rect(
        surface, constants.COLOR_MOON_HALO, (flag_mast + 1, flag_y, 1, 1),
    )


def _draw_galleon(
    surface: pygame.Surface, x: int, y: int, flipped: bool = False,
) -> None:
    """Havana spansk galleon — stor, imperiell, 3 master.

    Dimensjoner: 40×26 (inkludert master).
    Palett: WOOD_MID skrog, LANTERN gull-kant (spansk imperiell ornamentikk),
    SHIRT seil med LANTERN-høylys, EMBER spansk flagg.
    """
    hull_y = y - 6
    # Hull (WOOD_MID)
    pygame.draw.rect(
        surface, constants.COLOR_WOOD_MID, (x, hull_y, 40, 5),
    )
    # Gyllen kant (LANTERN — spansk ornamentikk)
    pygame.draw.rect(
        surface, constants.COLOR_LANTERN, (x, hull_y, 40, 1),
    )
    # Kanon-porter
    for dx in range(4, 38, 6):
        pygame.draw.rect(
            surface, constants.COLOR_WOOD_DARKEST,
            (x + dx, hull_y + 2, 3, 1),
        )
    # Buen (spisset)
    pygame.draw.rect(
        surface, constants.COLOR_WOOD_MID,
        (x + (40 if not flipped else -3), hull_y + 1, 3, 3),
    )
    # Akter-kastell (stort, svulmende)
    stern_x = x - 4 if not flipped else x + 40
    pygame.draw.rect(
        surface, constants.COLOR_WOOD_MID,
        (stern_x, hull_y - 4, 6, 5),
    )
    pygame.draw.rect(
        surface, constants.COLOR_LANTERN,
        (stern_x, hull_y - 4, 6, 1),
    )
    # Akter-vindu (lite LANTERN-BRIGHT-glimt)
    pygame.draw.rect(
        surface, constants.COLOR_LANTERN_BRIGHT,
        (stern_x + 2, hull_y - 2, 2, 2),
    )
    # Skygge
    pygame.draw.rect(
        surface, constants.COLOR_WOOD_DARKEST, (x, hull_y + 4, 40, 1),
    )

    # Tre master
    mast_xs = [x + 10, x + 22, x + 32]
    mast_hs = [14, 16, 12]  # Stor-masten er høyest
    for mx, mh in zip(mast_xs, mast_hs):
        pygame.draw.rect(
            surface, constants.COLOR_WOOD_DARKEST,
            (mx, hull_y - mh, 1, mh),
        )
        # Svulmende seil (høylys på toppen)
        sail_w = 10
        sail_h = mh - 3
        sx = mx - sail_w // 2
        pygame.draw.rect(
            surface, constants.COLOR_SHIRT,
            (sx, hull_y - mh + 1, sail_w, sail_h),
        )
        # Seil-høylys (LANTERN — sunlit spansk seil)
        pygame.draw.rect(
            surface, constants.COLOR_LANTERN,
            (sx, hull_y - mh + 1, sail_w, 1),
        )
        # Seil-skygge under
        pygame.draw.rect(
            surface, constants.COLOR_WOOD_MID,
            (sx, hull_y - 3, sail_w, 1),
        )
    # Spansk flagg på stor-mast (EMBER + LANTERN — gul/rød)
    flag_mx = mast_xs[1]
    flag_y = hull_y - 16
    pygame.draw.rect(
        surface, constants.COLOR_EMBER, (flag_mx + 1, flag_y, 5, 1),
    )
    pygame.draw.rect(
        surface, constants.COLOR_LANTERN_BRIGHT, (flag_mx + 1, flag_y + 1, 5, 1),
    )
    pygame.draw.rect(
        surface, constants.COLOR_EMBER, (flag_mx + 1, flag_y + 2, 5, 1),
    )


def _draw_small(
    surface: pygame.Surface, x: int, y: int, flipped: bool = False,
) -> None:
    """Havana mindre spansk handelsskip — mellom smuggler og galleon.

    Dimensjoner: 22×16 (inkludert mast).
    Palett: WOOD_MID skrog, LANTERN-kant (spansk), SHIRT seil.
    """
    hull_y = y - 4
    # Hull (WOOD_MID)
    pygame.draw.rect(
        surface, constants.COLOR_WOOD_MID, (x, hull_y, 22, 3),
    )
    # Gyllen stripe
    pygame.draw.rect(
        surface, constants.COLOR_LANTERN, (x, hull_y, 22, 1),
    )
    # Skygge
    pygame.draw.rect(
        surface, constants.COLOR_WOOD_DARKEST, (x, hull_y + 2, 22, 1),
    )
    # Buen
    pygame.draw.rect(
        surface, constants.COLOR_WOOD_MID,
        (x + (22 if not flipped else -2), hull_y + 1, 2, 1),
    )
    # 2 master
    mast_xs = [x + 7, x + 15]
    for mx in mast_xs:
        pygame.draw.rect(
            surface, constants.COLOR_WOOD_DARKEST,
            (mx, hull_y - 10, 1, 10),
        )
        # Seil
        sail_w = 6
        sx = mx - sail_w // 2
        pygame.draw.rect(
            surface, constants.COLOR_SHIRT,
            (sx, hull_y - 9, sail_w, 8),
        )
        # Seil-topp
        pygame.draw.rect(
            surface, constants.COLOR_LANTERN,
            (sx, hull_y - 9, sail_w, 1),
        )


def _draw_pirate(
    surface: pygame.Surface, x: int, y: int,
    flipped: bool = False,
    tilted: bool = False,
) -> None:
    """Nassau pirat-skip — ragget, lite, evt. skråstilt.

    Dimensjoner: 16×14 (inkludert mast).
    Palett: WOOD_DARK skrog med patch-planker (WOOD_MID-flekker),
    WOOD_MID-seil (slitt), EMBER mini-Jolly Roger.

    `tilted` tegner skroget 1 px skjevt for "dårlig forankret"-antydning.
    """
    tilt = 1 if tilted else 0
    hull_y = y - 4
    # Hull — base i WOOD_DARK
    pygame.draw.rect(
        surface, constants.COLOR_WOOD_DARK, (x, hull_y, 16, 3),
    )
    # Patch-planker (variert skygge)
    pygame.draw.rect(
        surface, constants.COLOR_WOOD_MID, (x + 4, hull_y, 3, 3),
    )
    pygame.draw.rect(
        surface, constants.COLOR_WOOD_DARKEST, (x + 9, hull_y, 2, 3),
    )
    # Skjevt skygge under (tilted skip har "taktløs" skygge)
    pygame.draw.rect(
        surface, constants.COLOR_WOOD_DARKEST,
        (x - tilt, hull_y + 3, 16, 1),
    )
    # Bu
    pygame.draw.rect(
        surface, constants.COLOR_WOOD_DARK,
        (x + (16 if not flipped else -1), hull_y + 1, 1, 1),
    )
    # Mast (skeiv hvis tilted)
    mast_x = x + 8
    for dy in range(9):
        # Skjev mast: øvre del forskyves 1 px
        dx_shift = tilt if dy < 5 else 0
        pygame.draw.rect(
            surface, constants.COLOR_WOOD_DARKEST,
            (mast_x + dx_shift, hull_y - 9 + dy, 1, 1),
        )
    # Slitt seil (WOOD_MID, ikke hvit)
    sail_y = hull_y - 8
    # Seil med "hull" (liten transparent fuge midt i)
    pygame.draw.rect(
        surface, constants.COLOR_WOOD_MID,
        (mast_x - 4 + tilt, sail_y, 8, 3),
    )
    pygame.draw.rect(
        surface, constants.COLOR_WOOD_DARK,
        (mast_x - 4 + tilt, sail_y + 3, 8, 4),
    )
    # Seil-"hull" (damage)
    pygame.draw.rect(
        surface, constants.COLOR_WOOD_DARKEST,
        (mast_x - 1 + tilt, sail_y + 3, 2, 1),
    )
    # Mini Jolly Roger (EMBER mini-flagg + svart)
    flag_y = hull_y - 10
    pygame.draw.rect(
        surface, constants.COLOR_HAT,
        (mast_x + 1 + tilt, flag_y, 3, 2),
    )
    # Hvit skalle-prikk
    pygame.draw.rect(
        surface, constants.COLOR_MOON_HALO,
        (mast_x + 2 + tilt, flag_y, 1, 1),
    )


#: Dispatch-tabell: kind → tegn-funksjon.
_SHIP_DRAWERS = {
    "smuggler": _draw_smuggler,
    "frigate": _draw_frigate,
    "galleon": _draw_galleon,
    "small": _draw_small,
    "pirate": _draw_pirate,
}


def draw_anchored_ship(
    surface: pygame.Surface,
    x: int,
    y: int,
    kind: str,
    *,
    flipped: bool = False,
    tilted: bool = False,
) -> None:
    """Tegn skip-silhuett direkte på `surface` ved (x, y).

    Brukes av `build_foreground_variants_for_port` under scene-init for
    å bake skip inn i forgrunns-SRCALPHA-variantene. Kaller rett inn
    i dispatch-tabellen; `tilted` ignoreres for kinds som ikke støtter
    det (kun `pirate` skråstilles i C2.5-5).
    """
    drawer = _SHIP_DRAWERS.get(kind)
    if drawer is None:
        raise ValueError(
            f"Ukjent anchored_ship.kind={kind!r} "
            f"(gyldige: {sorted(VALID_SHIP_KINDS)})"
        )
    if kind == "pirate":
        drawer(surface, x, y, flipped=flipped, tilted=tilted)
    else:
        drawer(surface, x, y, flipped=flipped)
