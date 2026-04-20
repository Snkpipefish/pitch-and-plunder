"""Natur-sprites for havn-livfullhet (Fase 2.5 C2.5-7).

Palmer, fugler, blomster, ugress, sand-drift. Bakes direkte inn i
gameplay-surfacen ved scene-init. Ingen per-frame-kost.

Palett-begrensning: master-paletten har ingen grønn. For "mose",
"løv", "ugress" brukes nærmeste tilgjengelige farge:
- Palme-kroner: WOOD_MID (brun, antydet grønn i natt-palett)
- Mose/lav: STONE_LIT (blå-grå, leses som "salt-grønn" mot stein)
- Blomster: EMBER/LANTERN (oker/rød bougainvillea)

Design-prinsipp: "silhuetter mot natthimmel" — ingen forsøk på
realistisk plante-rendering. Natt-palettet støtter silhuett-
estetikk der alt er redusert til former mot mørk bakgrunn.
"""

from __future__ import annotations

import pygame

import constants


# ============================================================================
# Palmer (flere varianter per havn-karakter)
# ============================================================================

def bake_palm(
    surface: pygame.Surface,
    x: int,
    ground_top_y: int,
    *,
    height: int = 48,
    lean: int = 0,
    crown_spread: int = 12,
) -> None:
    """Silhuett av palme. `lean` = -2 til +2 gir skjev stamme.

    `height` 32-60 px bestemmer total høyde. `crown_spread` gir kron-
    bredde; mindre for unge palmer, større for modne.

    Stamme: WOOD_DARKEST (jordmørk mot natthimmel).
    Krone: WOOD_MID-silhuett.
    """
    trunk_top_y = ground_top_y - height
    trunk_w = 2
    cx = x
    # Stamme — segmentert med subtile horizontal "noder"
    for i, dy in enumerate(range(0, height - 8, 4)):
        # Lean interpolering: øvre del forskyves
        t = i / max(1, (height - 8) // 4)
        shift = int(lean * t)
        pygame.draw.rect(
            surface, constants.COLOR_WOOD_DARKEST,
            (cx + shift, ground_top_y - dy - 4, trunk_w, 4),
        )
        # Nodal ring
        pygame.draw.rect(
            surface, constants.COLOR_WOOD_DARK,
            (cx + shift - 1, ground_top_y - dy - 4, trunk_w + 2, 1),
        )
    # Krone-senter (toppen av stammen)
    crown_cx = cx + lean
    crown_cy = trunk_top_y
    # Krone-blad — 5 vifte-segmenter i WOOD_MID
    fronds = [
        (-crown_spread, 2, -1),
        (-crown_spread // 2, -3, 0),
        (0, -5, 0),
        (crown_spread // 2, -3, 0),
        (crown_spread, 2, 1),
    ]
    for dx_offset, dy_offset, tip_off in fronds:
        # Frond er en lav linje fra sentrum til tip
        tip_x = crown_cx + dx_offset
        tip_y = crown_cy + dy_offset
        # Tegn et par piksler langs "skaftet"
        steps = max(3, abs(dx_offset))
        for s in range(steps + 1):
            t = s / steps
            px = int(crown_cx + (tip_x - crown_cx) * t)
            py = int(crown_cy + (tip_y - crown_cy) * t)
            pygame.draw.rect(
                surface, constants.COLOR_WOOD_MID, (px, py, 1, 1)
            )
        # Tip-prikk (litt lysere for silhuett-ende)
        pygame.draw.rect(
            surface, constants.COLOR_WOOD_MID, (tip_x, tip_y, 1, 1)
        )
    # Kokos-antydning under krona (2 mørke prikker)
    pygame.draw.rect(
        surface, constants.COLOR_WOOD_DARKEST, (crown_cx - 1, crown_cy + 1, 1, 1)
    )
    pygame.draw.rect(
        surface, constants.COLOR_WOOD_DARKEST, (crown_cx + 1, crown_cy + 2, 1, 1)
    )


# ============================================================================
# Fugler (silhuetter på master/tårn)
# ============================================================================

def bake_seagull(
    surface: pygame.Surface, x: int, y: int,
) -> None:
    """Måke-silhuett, 5x3. Står på mast eller stolpe.

    Silhuett-form: hode + lav kropp + hale-antydning. MOON_HALO-hvitt
    for måke-farge mot mørk bakgrunn.
    """
    # Kropp
    pygame.draw.rect(surface, constants.COLOR_MOON_HALO, (x, y + 1, 5, 2))
    # Hode
    pygame.draw.rect(surface, constants.COLOR_MOON_HALO, (x + 3, y, 2, 1))
    # Svart nebb-prikk
    pygame.draw.rect(surface, constants.COLOR_HAT, (x + 4, y + 1, 1, 1))
    # Ben-antydning
    pygame.draw.rect(surface, constants.COLOR_HAT, (x + 1, y + 3, 1, 1))


def bake_dove(
    surface: pygame.Surface, x: int, y: int,
) -> None:
    """Due-silhuett, 4x3. Sitter på katedral-tak eller -tårn.

    Mindre enn måke, mer kompakt. STONE_LIT for "by-due-grå".
    """
    pygame.draw.rect(surface, constants.COLOR_STONE_LIT, (x, y + 1, 4, 2))
    pygame.draw.rect(surface, constants.COLOR_STONE_LIT, (x + 2, y, 2, 1))
    pygame.draw.rect(surface, constants.COLOR_HAT, (x + 3, y + 1, 1, 1))


def bake_pelican(
    surface: pygame.Surface, x: int, y: int,
) -> None:
    """Pelikan-silhuett, 7x5. Nassau-signatur.

    Større fugl med lang nebb. STONE_LIGHT + WOOD_DARK for
    "karibisk brun pelikan".
    """
    # Kropp (større enn måke)
    pygame.draw.rect(surface, constants.COLOR_STONE_LIGHT, (x, y + 2, 5, 3))
    # Vingekant
    pygame.draw.rect(surface, constants.COLOR_WOOD_DARK, (x + 1, y + 4, 4, 1))
    # Hode
    pygame.draw.rect(surface, constants.COLOR_STONE_LIGHT, (x + 3, y, 2, 2))
    # Lang nebb (pelikan-signatur)
    pygame.draw.rect(surface, constants.COLOR_LANTERN, (x + 5, y + 1, 2, 1))
    pygame.draw.rect(surface, constants.COLOR_EMBER, (x + 5, y + 2, 2, 1))
    # Ben
    pygame.draw.rect(surface, constants.COLOR_HAT, (x + 2, y + 5, 1, 1))


# ============================================================================
# Vegetasjon (Havana-blomster, ugress, hengeplanter)
# ============================================================================

def bake_bougainvillea(
    surface: pygame.Surface,
    x: int,
    y_top: int,
    *,
    length: int = 14,
) -> None:
    """Bougainvillea-ranke hengende fra balkong/vegg.

    Lilla-oransje blomster i paletten blir EMBER (rødlig) og
    LANTERN_BRIGHT-antydning for "lysere blomster". Stengel i
    WOOD_DARKEST.
    """
    # Stengel (vertikal, WOOD_DARKEST)
    pygame.draw.rect(
        surface, constants.COLOR_WOOD_DARKEST, (x, y_top, 1, length)
    )
    # Blomster-klynger langs stengelen (EMBER)
    for dy in range(2, length, 3):
        # Alternere venstre/høyre side
        side = -1 if (dy // 3) % 2 == 0 else 1
        pygame.draw.rect(
            surface, constants.COLOR_EMBER,
            (x + side, y_top + dy, 1, 1),
        )
        # Lys-aksent
        if dy % 6 == 2:
            pygame.draw.rect(
                surface, constants.COLOR_LANTERN_BRIGHT,
                (x + side * 2, y_top + dy, 1, 1),
            )
    # Tip (slutten) — liten klynge
    pygame.draw.rect(
        surface, constants.COLOR_EMBER, (x - 1, y_top + length, 1, 1)
    )
    pygame.draw.rect(
        surface, constants.COLOR_EMBER, (x + 1, y_top + length, 1, 1)
    )


def bake_weeds(
    surface: pygame.Surface,
    x: int,
    ground_top_y: int,
    *,
    width: int = 10,
) -> None:
    """Ugress-lapp i gate-sprekker eller smug-kanter.

    WOOD_DARKEST-stilker i variable høyder (2-5 px).
    """
    # Variable stilkhøyder (deterministisk via x-posisjon)
    heights = [(x * 7 + i * 13) % 4 + 2 for i in range(width // 2)]
    for i, h in enumerate(heights):
        wx = x + i * 2
        wy = ground_top_y - h
        pygame.draw.rect(
            surface, constants.COLOR_WOOD_DARKEST, (wx, wy, 1, h)
        )
    # Topp-spredning (mørkt-grønt antyding — vi har ingen grønn)
    for i in range(width // 3):
        wx = x + i * 3 + 1
        pygame.draw.rect(
            surface, constants.COLOR_WOOD_DARK, (wx, ground_top_y - 1, 1, 1)
        )


def bake_moss_patch(
    surface: pygame.Surface,
    x: int,
    y: int,
    *,
    width: int = 8,
) -> None:
    """Mose-patch på bygnings-tak eller vegg.

    Palett-begrensning: ingen grønn i master. STONE_LIT nærmere
    "salt-grønn" mot stein; WOOD_MID nærmere "våt-grønn" mot tre.
    Funksjonen bruker blanding av disse for å antyde liv.
    """
    # STONE_LIT base (salt-grønn-aktig)
    pygame.draw.rect(
        surface, constants.COLOR_STONE_LIT, (x, y, width, 1)
    )
    # Uregelmessig kant (fjern noen piksler)
    for i in (0, 3, 7):
        if i < width:
            pygame.draw.rect(surface, constants.COLOR_WOOD_MID, (x + i, y, 1, 1))
    # Undre skygge-kant
    pygame.draw.rect(
        surface, constants.COLOR_WOOD_DARKEST, (x + 2, y + 1, width - 4, 1)
    )


def bake_hanging_plant(
    surface: pygame.Surface,
    x: int,
    y_top: int,
    *,
    length: int = 8,
) -> None:
    """Hengeplante fra balkong/arkade (Havana).

    Mer diskret enn bougainvillea — hovedsakelig WOOD_MID-blad-
    silhuett uten blomster.
    """
    # Vertikale blader
    for dy in range(length):
        pygame.draw.rect(
            surface, constants.COLOR_WOOD_MID, (x, y_top + dy, 1, 1)
        )
        # Spredning annenhver rad
        if dy % 2 == 0:
            pygame.draw.rect(
                surface, constants.COLOR_WOOD_DARK, (x + 1, y_top + dy, 1, 1)
            )
        else:
            pygame.draw.rect(
                surface, constants.COLOR_WOOD_DARK, (x - 1, y_top + dy, 1, 1)
            )


# ============================================================================
# Sand-drift + tang
# ============================================================================

def bake_sand_drift(
    surface: pygame.Surface,
    x: int,
    ground_top_y: int,
    *,
    width: int = 16,
) -> None:
    """Sand-drift-haug (Nassau smug-innhold eller kaotisk gate-element).

    WOOD_LIGHT høyde-antydet haug med WOOD_DARK-skyggekant.
    """
    # Bølge-form: høyere i midten, lavere ved kantene
    max_h = 5
    for i in range(width):
        # Parabel-h = maks-h ved midten
        t = abs(i - width / 2) / (width / 2)
        h = max(1, int(max_h * (1 - t * t)))
        pygame.draw.rect(
            surface, constants.COLOR_WOOD_LIGHT,
            (x + i, ground_top_y - h, 1, h),
        )
    # Topp-høylys
    mid = x + width // 2
    pygame.draw.rect(
        surface, constants.COLOR_SHIRT, (mid - 1, ground_top_y - max_h, 2, 1)
    )
    # Skygge på øst-siden
    for i in range(width // 2, width):
        t = (i - width / 2) / (width / 2)
        h = max(1, int(max_h * (1 - t * t)))
        pygame.draw.rect(
            surface, constants.COLOR_WOOD_DARK,
            (x + i, ground_top_y - 1, 1, 1),
        )


def bake_seaweed(
    surface: pygame.Surface,
    x: int,
    ground_top_y: int,
) -> None:
    """Tang-antydning ved kaikant (Tortuga).

    Små WOOD_DARKEST-piksler i sjølinje-mønster.
    """
    for dx, dy in ((0, 0), (2, 1), (4, 0), (6, 1), (8, 0)):
        pygame.draw.rect(
            surface, constants.COLOR_WOOD_DARKEST,
            (x + dx, ground_top_y - dy, 1, 1),
        )


# ============================================================================
# Dispatch — nature-element per kind
# ============================================================================

#: Gyldige natur-kinds. Utvides ved behov.
VALID_NATURE_KINDS: frozenset[str] = frozenset({
    "palm",
    "palm_tall",
    "palm_leaning",
    "seagull",
    "dove",
    "pelican",
    "bougainvillea",
    "weeds",
    "moss_patch",
    "hanging_plant",
    "sand_drift",
    "seaweed",
})


def bake_nature_element(
    surface: pygame.Surface,
    kind: str,
    x: int,
    y: int,
    ground_top_y: int,
) -> None:
    """Dispatch til riktig bake-funksjon.

    `y` tolkes kontekst-avhengig:
    - Fugler: eksplisitt y (der de sitter)
    - Palmer: ignoreres (funksjonen bruker ground_top_y for bunn)
    - Bougainvillea/hanging_plant: y_top for hengestart
    - Weeds/moss_patch/seaweed: y_top brukt direkte hvor relevant
    - Sand_drift: bruker ground_top_y
    """
    if kind == "palm":
        bake_palm(surface, x, ground_top_y, height=40)
    elif kind == "palm_tall":
        bake_palm(surface, x, ground_top_y, height=56, crown_spread=14)
    elif kind == "palm_leaning":
        bake_palm(surface, x, ground_top_y, height=44, lean=2)
    elif kind == "seagull":
        bake_seagull(surface, x, y)
    elif kind == "dove":
        bake_dove(surface, x, y)
    elif kind == "pelican":
        bake_pelican(surface, x, y)
    elif kind == "bougainvillea":
        bake_bougainvillea(surface, x, y, length=14)
    elif kind == "hanging_plant":
        bake_hanging_plant(surface, x, y, length=10)
    elif kind == "weeds":
        bake_weeds(surface, x, ground_top_y)
    elif kind == "moss_patch":
        bake_moss_patch(surface, x, y)
    elif kind == "sand_drift":
        bake_sand_drift(surface, x, ground_top_y)
    elif kind == "seaweed":
        bake_seaweed(surface, x, ground_top_y)
    else:
        raise ValueError(
            f"Ukjent nature-kind: {kind!r} "
            f"(gyldige: {sorted(VALID_NATURE_KINDS)})"
        )
