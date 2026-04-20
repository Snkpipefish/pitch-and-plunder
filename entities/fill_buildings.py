"""Fyll-bygninger for havn-scener (Fase 2.5 C2.5-6a/6b).

Per-havn bake-funksjoner for bystruktur-bygninger (fiskerhytter,
borgerhus, pakkhus osv) utover signatur-bygningene. Bygningene
holder seg innenfor silhuett-hierarki per FASE_2_5.md §1.4:

| Nivå      | Høyde   | Hvem                              |
|-----------|---------|-----------------------------------|
| Dominant  | 96-108  | tavern/katedral (ikke her)        |
| Signatur  | 72-84   | rum-magasin/palass (ikke her)     |
| Fyll-høy  | 48-60   | borgerhus, offisersbolig          |
| Fyll-lav  | 32-44   | fiskerhytter, verksteder          |

Fyll-bygninger bakes FØR signatur-bygningene i pipeline-en
(`scenes/port_buildings.py`), slik at signatur dekker ved overlapp.

C2.5-6a leverer Tortuga (5) + Nassau (4) = 9 fabrikker + 1
dispatch. C2.5-6b vil legge til Port Royal + Havana i samme
mønster.

Havn-spesifikk stil:
- Tortuga: WOOD_DARK/MID dominerende, skjeve vinduer, ingen formell
  arkitektur, lite LANTERN (utenom smie-unntak)
- Nassau: WOOD_LIGHT + LANTERN varme, lappverks-planker (5-13 px
  bredder), skjeve vinkler, seilduk-tak, ingen rette linjer
"""

from __future__ import annotations

import pygame

import constants


# ============================================================================
# Tortuga fyll-bygninger
# Stil: WOOD_DARK/MID, skjevt, uformelt, lite LANTERN
# ============================================================================

def bake_tortuga_fishers_hut(
    surface: pygame.Surface,
    x: int, w: int, h: int,
    ground_top_y: int,
    style_variant: int = 0,
) -> None:
    """Fiskerhytte med tørke-nett hengende foran. 32-40 px høy.

    WOOD_DARKEST base med WOOD_MID-skråtak. Tørke-nett er
    kryssmønster foran veggen.
    """
    y_top = ground_top_y - h
    # Vegg
    pygame.draw.rect(surface, constants.COLOR_WOOD_DARKEST, (x, y_top, w, h))
    # Skråtak (trekantet — antydet med to rektangler)
    pygame.draw.rect(
        surface, constants.COLOR_WOOD_MID, (x - 2, y_top - 2, w + 4, 3)
    )
    pygame.draw.rect(
        surface, constants.COLOR_WOOD_DARK, (x + 4, y_top - 5, w - 8, 3)
    )
    # Pipe (fisk-røyking)
    pipe_x = x + w - 10
    pygame.draw.rect(
        surface, constants.COLOR_STONE_DARKEST, (pipe_x, y_top - 8, 3, 6)
    )
    # Lite skjevt vindu
    win_w, win_h = 8, 7
    win_x = x + 8
    win_y = y_top + 6
    pygame.draw.rect(
        surface, constants.COLOR_WOOD_DARKEST, (win_x, win_y, win_w, win_h)
    )
    pygame.draw.rect(
        surface, constants.COLOR_LANTERN, (win_x + 1, win_y + 1, win_w - 2, win_h - 2)
    )
    # Dør (mørk åpning)
    door_w, door_h = 8, 14
    door_x = x + w - 14
    door_y = ground_top_y - door_h
    pygame.draw.rect(
        surface, constants.COLOR_STONE_DARKEST, (door_x, door_y, door_w, door_h)
    )
    # Tørke-nett: 8 horisontale + 4 vertikale streker
    net_x1, net_x2 = x + 20, x + w - 16
    net_y1, net_y2 = y_top + 4, y_top + h - 4
    net_w = net_x2 - net_x1
    net_h = net_y2 - net_y1
    if net_w > 6 and net_h > 6:
        # Rammen
        pygame.draw.rect(
            surface, constants.COLOR_WOOD_MID, (net_x1, net_y1, net_w, 1)
        )
        pygame.draw.rect(
            surface, constants.COLOR_WOOD_MID, (net_x1, net_y2, net_w, 1)
        )
        # Kryss (sparse)
        for cy in range(net_y1 + 2, net_y2, 3):
            for cx in range(net_x1, net_x2, 3):
                pygame.draw.rect(
                    surface, constants.COLOR_WOOD_MID, (cx, cy, 1, 1)
                )


def bake_tortuga_boarding_house(
    surface: pygame.Surface,
    x: int, w: int, h: int,
    ground_top_y: int,
    style_variant: int = 0,
) -> None:
    """Boarding-hus, 2 etasjer. 48-56 px høy.

    4 små skjeve vinduer (2 etasjer × 2 vinduer). LANTERN bare over
    døren.
    """
    y_top = ground_top_y - h
    # Vegg
    pygame.draw.rect(surface, constants.COLOR_WOOD_DARK, (x, y_top, w, h))
    # Plank-linjer
    for dy in (10, 22, 34):
        if dy < h:
            pygame.draw.rect(
                surface, constants.COLOR_WOOD_DARKEST, (x, y_top + dy, w, 1)
            )
    # Tak-kant
    pygame.draw.rect(
        surface, constants.COLOR_WOOD_DARKEST, (x - 3, y_top - 3, w + 6, 3)
    )
    # Etasje-skille (horisontal bjelke)
    mid_y = y_top + h // 2
    pygame.draw.rect(
        surface, constants.COLOR_WOOD_DARKEST, (x, mid_y, w, 2)
    )
    # 4 vinduer (2x2 grid), små og skjeve
    win_w, win_h = 10, 7
    # Øvre rad
    for wx_off, wy_off_skew in (
        (8, 0), (w - 18, 1),
    ):
        wx = x + wx_off
        wy = y_top + 4 + wy_off_skew
        pygame.draw.rect(
            surface, constants.COLOR_WOOD_DARKEST, (wx, wy, win_w, win_h)
        )
        pygame.draw.rect(
            surface, constants.COLOR_LANTERN, (wx + 1, wy + 1, win_w - 2, win_h - 2)
        )
    # Nedre rad
    for wx_off, wy_off_skew in (
        (8, 1), (w - 18, 0),
    ):
        wx = x + wx_off
        wy = mid_y + 4 + wy_off_skew
        pygame.draw.rect(
            surface, constants.COLOR_WOOD_DARKEST, (wx, wy, win_w, win_h)
        )
        pygame.draw.rect(
            surface, constants.COLOR_LANTERN, (wx + 1, wy + 1, win_w - 2, win_h - 2)
        )
    # Dør med LANTERN over
    door_w, door_h = 10, 16
    door_x = x + w // 2 - door_w // 2
    door_y = ground_top_y - door_h
    pygame.draw.rect(
        surface, constants.COLOR_STONE_DARKEST, (door_x, door_y, door_w, door_h)
    )
    pygame.draw.rect(
        surface, constants.COLOR_WOOD_LIGHT,
        (door_x + 2, door_y + 2, door_w - 4, door_h - 4),
    )
    # LANTERN over døren
    pygame.draw.rect(
        surface, constants.COLOR_LANTERN_BRIGHT,
        (door_x + door_w // 2 - 1, door_y - 3, 2, 2),
    )


def bake_tortuga_lumber_warehouse(
    surface: pygame.Surface,
    x: int, w: int, h: int,
    ground_top_y: int,
    style_variant: int = 0,
) -> None:
    """Tømmerpakkhus: stort lavt bygg, åpen port.

    36-44 px høy. Tømmerstokker stablet utenfor. Ingen vinduer,
    bare stor åpen port.
    """
    y_top = ground_top_y - h
    # Vegg
    pygame.draw.rect(surface, constants.COLOR_WOOD_MID, (x, y_top, w, h))
    # Horisontale stokk-linjer
    for dy in range(6, h, 6):
        pygame.draw.rect(
            surface, constants.COLOR_WOOD_DARKEST, (x, y_top + dy, w, 1)
        )
    # Tak (flatt med kant)
    pygame.draw.rect(
        surface, constants.COLOR_WOOD_DARKEST, (x - 4, y_top - 3, w + 8, 3)
    )
    # Stor åpen port (mørk åpning)
    port_w, port_h = 24, h - 4
    port_x = x + w // 2 - port_w // 2
    port_y = ground_top_y - port_h
    pygame.draw.rect(
        surface, constants.COLOR_STONE_DARKEST, (port_x, port_y, port_w, port_h)
    )
    # Tømmerstokker stablet utenfor (antydet med 3 horisontale striper)
    log_x = x + 4
    log_y = ground_top_y - 6
    for i in range(3):
        pygame.draw.rect(
            surface, constants.COLOR_WOOD_LIGHT, (log_x, log_y - i * 2, 12, 1)
        )
        pygame.draw.rect(
            surface, constants.COLOR_WOOD_DARKEST, (log_x, log_y - i * 2 + 1, 12, 1)
        )
    # Stokk på høyre side også
    log_x2 = x + w - 16
    for i in range(2):
        pygame.draw.rect(
            surface, constants.COLOR_WOOD_LIGHT, (log_x2, log_y - i * 2, 12, 1)
        )


def bake_tortuga_field_hospital(
    surface: pygame.Surface,
    x: int, w: int, h: int,
    ground_top_y: int,
    style_variant: int = 0,
) -> None:
    """Lite felt-hospital/barbeskjær. 40 px høy.

    WOOD_DARK base. Hvit kors-skilt over døren. Pipe-røyk-antydning
    på taket.
    """
    y_top = ground_top_y - h
    # Vegg
    pygame.draw.rect(surface, constants.COLOR_WOOD_DARK, (x, y_top, w, h))
    # Tak
    pygame.draw.rect(
        surface, constants.COLOR_WOOD_DARKEST, (x - 3, y_top - 2, w + 6, 2)
    )
    # Pipe + røyk
    pipe_x = x + w - 12
    pygame.draw.rect(
        surface, constants.COLOR_STONE_DARKEST, (pipe_x, y_top - 6, 3, 6)
    )
    pygame.draw.rect(
        surface, constants.COLOR_FOG, (pipe_x, y_top - 10, 3, 4)
    )
    # Lite vindu
    win_w, win_h = 10, 8
    pygame.draw.rect(
        surface, constants.COLOR_WOOD_DARKEST, (x + 6, y_top + 6, win_w, win_h)
    )
    pygame.draw.rect(
        surface, constants.COLOR_STONE_LIT, (x + 7, y_top + 7, win_w - 2, win_h - 2)
    )
    # Dør
    door_w, door_h = 10, 16
    door_x = x + w // 2 - door_w // 2 + 6
    door_y = ground_top_y - door_h
    pygame.draw.rect(
        surface, constants.COLOR_STONE_DARKEST, (door_x, door_y, door_w, door_h)
    )
    pygame.draw.rect(
        surface, constants.COLOR_WOOD_MID,
        (door_x + 1, door_y + 1, door_w - 2, door_h - 2),
    )
    # Kors-skilt over dør (STONE_BRIGHT)
    cross_cx = door_x + door_w // 2
    cross_y = door_y - 6
    pygame.draw.rect(surface, constants.COLOR_STONE_BRIGHT, (cross_cx - 2, cross_y, 5, 2))
    pygame.draw.rect(surface, constants.COLOR_STONE_BRIGHT, (cross_cx - 1, cross_y - 2, 3, 2))
    pygame.draw.rect(surface, constants.COLOR_STONE_BRIGHT, (cross_cx - 1, cross_y + 2, 3, 2))


def bake_tortuga_smithy(
    surface: pygame.Surface,
    x: int, w: int, h: int,
    ground_top_y: int,
    style_variant: int = 0,
) -> None:
    """Smed-verksted med glødende kull. 36-44 px høy.

    Tematisk unntak fra "lite LANTERN"-regel: glødende kull (FLAME/
    EMBER) inne i esse-åpning er smedens signatur.
    """
    y_top = ground_top_y - h
    # Vegg
    pygame.draw.rect(surface, constants.COLOR_WOOD_DARKEST, (x, y_top, w, h))
    # Vertikal plank-struktur
    for dx in range(8, w, 10):
        pygame.draw.rect(
            surface, constants.COLOR_WOOD_DARK, (x + dx, y_top, 1, h)
        )
    # Tak
    pygame.draw.rect(
        surface, constants.COLOR_WOOD_DARKEST, (x - 2, y_top - 2, w + 4, 2)
    )
    # Stor pipe (esse-pipe)
    pipe_x = x + 6
    pygame.draw.rect(
        surface, constants.COLOR_STONE_DARKEST, (pipe_x, y_top - 10, 5, 10)
    )
    # Røyk
    pygame.draw.rect(surface, constants.COLOR_FOG, (pipe_x + 1, y_top - 14, 3, 4))
    # Esse-åpning (stor, med glødende kull)
    esse_w, esse_h = 18, 18
    esse_x = x + w - esse_w - 4
    esse_y = ground_top_y - esse_h
    pygame.draw.rect(
        surface, constants.COLOR_STONE_DARKEST, (esse_x, esse_y, esse_w, esse_h)
    )
    # Glødende kull — FLAME kjerne + EMBER ring + LANTERN lys
    pygame.draw.rect(
        surface, constants.COLOR_EMBER,
        (esse_x + 2, esse_y + esse_h - 8, esse_w - 4, 6),
    )
    pygame.draw.rect(
        surface, constants.COLOR_FLAME,
        (esse_x + 4, esse_y + esse_h - 6, esse_w - 8, 3),
    )
    pygame.draw.rect(
        surface, constants.COLOR_LANTERN_BRIGHT,
        (esse_x + 6, esse_y + esse_h - 5, esse_w - 12, 1),
    )
    # Ambolt (liten WOOD_DARKEST-silhuett foran)
    anvil_x = x + 2
    anvil_y = ground_top_y - 4
    pygame.draw.rect(
        surface, constants.COLOR_STONE_DARKEST, (anvil_x, anvil_y - 3, 10, 3)
    )
    pygame.draw.rect(
        surface, constants.COLOR_STONE_DARKEST, (anvil_x + 3, anvil_y, 4, 1)
    )


# ============================================================================
# Nassau fyll-bygninger
# Stil: WOOD_LIGHT + LANTERN varme, lappverks-planker, skjeve vinkler,
# seilduk-tak, ingen rette linjer
# ============================================================================

def bake_nassau_tavern_small(
    surface: pygame.Surface,
    x: int, w: int, h: int,
    ground_top_y: int,
    style_variant: int = 0,
) -> None:
    """Liten taverne (del av cluster). 24-32 px høy.

    `style_variant` 0 og 1 gir speilvendte/fargevariante versjoner
    slik at cluster ikke er identiske taverner.
    """
    y_top = ground_top_y - h
    # Vegg — WOOD_DARK/WOOD_MID alternering mellom variants
    wall_color = (
        constants.COLOR_WOOD_DARK if style_variant == 0
        else constants.COLOR_WOOD_MID
    )
    pygame.draw.rect(surface, wall_color, (x, y_top, w, h))
    # Lappverk-planker (variable bredder 5-13 px)
    plank_widths = [7, 5, 9, 4, 8, 3] if style_variant == 0 else [6, 8, 4, 10, 5]
    plank_x = x
    for i, pw in enumerate(plank_widths):
        if plank_x + pw > x + w:
            break
        # Alternere mellom WOOD_DARK og WOOD_DARKEST for variasjon
        color = constants.COLOR_WOOD_DARKEST if i % 2 == 0 else constants.COLOR_WOOD_DARK
        pygame.draw.rect(surface, color, (plank_x + pw - 1, y_top, 1, h))
        plank_x += pw
    # Seilduk-tak (SHIRT)
    pygame.draw.rect(
        surface, constants.COLOR_SHIRT, (x - 1, y_top - 3, w + 2, 3)
    )
    pygame.draw.rect(
        surface, constants.COLOR_STONE_DARK, (x - 1, y_top - 3, w + 2, 1)
    )
    # Lite vindu (LANTERN — varm taverne)
    win_w, win_h = 6, 6
    win_x = x + 4 if style_variant == 0 else x + w - 10
    win_y = y_top + 6
    pygame.draw.rect(
        surface, constants.COLOR_WOOD_DARKEST, (win_x, win_y, win_w, win_h)
    )
    pygame.draw.rect(
        surface, constants.COLOR_LANTERN, (win_x + 1, win_y + 1, win_w - 2, win_h - 2)
    )
    pygame.draw.rect(
        surface, constants.COLOR_LANTERN_BRIGHT,
        (win_x + 2, win_y + 2, win_w - 4, win_h - 4),
    )
    # Liten skjev dør
    door_w, door_h = 6, 12
    door_x = (
        x + w - 10 if style_variant == 0 else x + 4
    )
    door_y = ground_top_y - door_h
    pygame.draw.rect(
        surface, constants.COLOR_STONE_DARKEST, (door_x, door_y, door_w, door_h)
    )
    # Varm glød fra døren
    pygame.draw.rect(
        surface, constants.COLOR_EMBER,
        (door_x + 1, door_y + 1, door_w - 2, door_h - 2),
    )


def bake_nassau_improvised_warehouse(
    surface: pygame.Surface,
    x: int, w: int, h: int,
    ground_top_y: int,
    style_variant: int = 0,
) -> None:
    """Improvisert pakkhus. 28-36 px høy.

    Åpen front, varer synlige. Seil som tak-trekk. Lappverks-
    planker.
    """
    y_top = ground_top_y - h
    # Vegg-base med variable plank-bredder
    pygame.draw.rect(surface, constants.COLOR_WOOD_MID, (x, y_top, w, h))
    # Lappverks-planker (vertikale striper med variabel bredde)
    plank_widths = [8, 5, 11, 6, 9, 4, 7]
    plank_x = x
    for i, pw in enumerate(plank_widths):
        if plank_x + pw > x + w:
            break
        color = (
            constants.COLOR_WOOD_DARK if i % 2 == 0
            else constants.COLOR_WOOD_LIGHT
        )
        pygame.draw.rect(
            surface, color, (plank_x, y_top + 4, pw - 1, h - 4)
        )
        plank_x += pw
    # Seilduk-tak (skrått)
    pygame.draw.rect(
        surface, constants.COLOR_SHIRT, (x - 2, y_top - 3, w + 4, 4)
    )
    pygame.draw.rect(
        surface, constants.COLOR_STONE_DARK, (x - 2, y_top - 3, w + 4, 1)
    )
    # Mast som holder seil (liten)
    mast_cx = x + w // 2
    pygame.draw.rect(
        surface, constants.COLOR_WOOD_DARKEST, (mast_cx - 1, y_top - 6, 2, 4)
    )
    # Åpen front (mørk åpning viser "varer")
    front_w, front_h = w - 12, h - 10
    front_x = x + 6
    front_y = ground_top_y - front_h
    pygame.draw.rect(
        surface, constants.COLOR_STONE_DARKEST, (front_x, front_y, front_w, front_h)
    )
    # Antyd kister/tønner inne (mørke prikker)
    for kx in range(front_x + 3, front_x + front_w - 2, 5):
        pygame.draw.rect(
            surface, constants.COLOR_WOOD_MID,
            (kx, ground_top_y - 6, 3, 4),
        )
        pygame.draw.rect(
            surface, constants.COLOR_LANTERN,
            (kx + 1, ground_top_y - 4, 1, 1),
        )


def bake_nassau_patchwork_hut(
    surface: pygame.Surface,
    x: int, w: int, h: int,
    ground_top_y: int,
    style_variant: int = 0,
) -> None:
    """Lappverks-hytte. 32-40 px høy.

    Variable WOOD-farger i helt uordnet lappverk. Skjeve vinduer på
    ulik høyde. Ingen rette linjer.
    """
    y_top = ground_top_y - h
    # Vegg-base
    pygame.draw.rect(surface, constants.COLOR_WOOD_DARK, (x, y_top, w, h))
    # Lappverks-fargeskjold (4-5 plank-grupper med forskjellig farge)
    patches = [
        (0, 14, 6, constants.COLOR_WOOD_MID),
        (14, 10, 4, constants.COLOR_WOOD_DARKEST),
        (24, 13, 8, constants.COLOR_WOOD_LIGHT),
        (37, 5, 5, constants.COLOR_WOOD_MID),
    ]
    # Noen horisontale også (slitasje-mønster)
    for px, pw, ph, color in patches:
        if x + px + pw <= x + w:
            pygame.draw.rect(
                surface, color,
                (x + px, y_top + 3, pw, min(ph, h - 3)),
            )
    # Seilduk-tak (skjev)
    pygame.draw.rect(
        surface, constants.COLOR_WOOD_DARKEST, (x - 3, y_top - 3, w + 6, 3)
    )
    # Små skjeve vinduer på ulik høyde
    win_positions = [
        (6, 8, 7, 6),    # lavere vindu
        (w - 14, 4, 6, 6),   # høyere vindu
    ]
    for wx_off, wy_off, win_w, win_h in win_positions:
        wx = x + wx_off
        wy = y_top + wy_off
        if wx + win_w > x + w:
            continue
        pygame.draw.rect(
            surface, constants.COLOR_WOOD_DARKEST, (wx, wy, win_w, win_h)
        )
        pygame.draw.rect(
            surface, constants.COLOR_LANTERN, (wx + 1, wy + 1, win_w - 2, win_h - 2)
        )
    # Skjev dør
    door_w, door_h = 8, 14
    door_x = x + w // 2 - door_w // 2 + 2
    door_y = ground_top_y - door_h
    # Skjev: døren starter 1 px til høyre nederst
    pygame.draw.rect(
        surface, constants.COLOR_STONE_DARKEST, (door_x, door_y, door_w, door_h)
    )
    pygame.draw.rect(
        surface, constants.COLOR_EMBER,
        (door_x + 2, door_y + 2, door_w - 3, door_h - 4),
    )


def bake_nassau_rope_workshop(
    surface: pygame.Surface,
    x: int, w: int, h: int,
    ground_top_y: int,
    style_variant: int = 0,
) -> None:
    """Tauverks-verksted. 24-32 px høy.

    WOOD_DARK base. Tauverks-ruller stablet foran. Åpen-side design
    (én side mangler vegg).
    """
    y_top = ground_top_y - h
    # Vegg (kun venstre + topp + bak — åpen på høyre side)
    pygame.draw.rect(surface, constants.COLOR_WOOD_DARK, (x, y_top, w, h))
    # Tak
    pygame.draw.rect(
        surface, constants.COLOR_WOOD_DARKEST, (x - 2, y_top - 2, w + 4, 2)
    )
    # "Åpen side" — dekk høyre halvdel med mørk (innvendig skygge)
    open_x = x + w // 2
    pygame.draw.rect(
        surface, constants.COLOR_STONE_DARKEST, (open_x, y_top + 2, w // 2, h - 2)
    )
    # Støtte-bjelke i åpningen
    pygame.draw.rect(
        surface, constants.COLOR_WOOD_DARKEST, (open_x, y_top, 1, h)
    )
    # Tauverks-ruller foran (WOOD_LIGHT sirkler via rektangler)
    rope_xs = [x + 2, x + 12]
    for i, rx in enumerate(rope_xs):
        ry = ground_top_y - 5
        # Rull-base
        pygame.draw.rect(
            surface, constants.COLOR_WOOD_LIGHT, (rx, ry, 7, 5)
        )
        pygame.draw.rect(
            surface, constants.COLOR_WOOD_DARK, (rx, ry, 7, 1)
        )
        # Rull-midtpunkt
        pygame.draw.rect(
            surface, constants.COLOR_WOOD_DARKEST, (rx + 3, ry + 2, 1, 1)
        )
    # Tau hengende fra taket i åpningen
    rope_drop_x = open_x + w // 4
    pygame.draw.rect(
        surface, constants.COLOR_WOOD_LIGHT, (rope_drop_x, y_top + 2, 1, h - 6)
    )


# ============================================================================
# Dispatch-tabell + bake-entry-point
# ============================================================================

#: Dispatch-tabell: kind → bake-funksjon.
_FILL_BUILDING_BAKERS = {
    # Tortuga (C2.5-6a)
    "tortuga_fishers_hut": bake_tortuga_fishers_hut,
    "tortuga_boarding_house": bake_tortuga_boarding_house,
    "tortuga_lumber_warehouse": bake_tortuga_lumber_warehouse,
    "tortuga_field_hospital": bake_tortuga_field_hospital,
    "tortuga_smithy": bake_tortuga_smithy,
    # Nassau (C2.5-6a)
    "nassau_tavern_small": bake_nassau_tavern_small,
    "nassau_improvised_warehouse": bake_nassau_improvised_warehouse,
    "nassau_patchwork_hut": bake_nassau_patchwork_hut,
    "nassau_rope_workshop": bake_nassau_rope_workshop,
    # C2.5-6b utvider med port_royal_* og havana_*
}

#: Gyldige fyll-bygning-kinds. Brukes av port_config-parser.
VALID_FILL_BUILDING_KINDS: frozenset[str] = frozenset(_FILL_BUILDING_BAKERS.keys())

#: Maks-høyde for fyll-bygninger per silhuett-hierarki (FASE_2_5 §1.4).
#: Fyll-høy-tier er 48-60 px. Fyll-bygninger må aldri overstige dette.
MAX_FILL_BUILDING_HEIGHT: int = 60


def bake_fill_building(
    surface: pygame.Surface,
    kind: str,
    x: int,
    w: int,
    h: int,
    ground_top_y: int,
    style_variant: int = 0,
) -> None:
    """Dispatch til riktig bake-funksjon basert på `kind`.

    Kaster `ValueError` hvis `kind` er ukjent eller `h` overstiger
    `MAX_FILL_BUILDING_HEIGHT` (silhuett-hierarki-regel).
    """
    if h > MAX_FILL_BUILDING_HEIGHT:
        raise ValueError(
            f"Fyll-bygning {kind!r} har høyde {h} > maks "
            f"{MAX_FILL_BUILDING_HEIGHT} (silhuett-hierarki-brudd)"
        )
    baker = _FILL_BUILDING_BAKERS.get(kind)
    if baker is None:
        raise ValueError(
            f"Ukjent fill_building.kind={kind!r} "
            f"(gyldige: {sorted(VALID_FILL_BUILDING_KINDS)})"
        )
    baker(surface, x, w, h, ground_top_y, style_variant)
