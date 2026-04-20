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
# Port Royal fyll-bygninger (C2.5-6b)
# Stil: murstein, jerngelénder, kolonial orden, identiske vindusrekker,
# STONE-familien dominerer, LANTERN sparsomt
# ============================================================================

def bake_port_royal_officers_residence(
    surface: pygame.Surface,
    x: int, w: int, h: int,
    ground_top_y: int,
    style_variant: int = 0,
) -> None:
    """Offisersbolig, murstein + jerngelénder. 48-56 px høy.

    2 etasjer. Murstein-mønster på fasaden. Jerngelénder-balkong i
    andre etasje. Uniformert kolonial utseende.
    """
    y_top = ground_top_y - h
    # Murstein-base (STONE_DARK)
    pygame.draw.rect(surface, constants.COLOR_STONE_DARK, (x, y_top, w, h))
    # Murstein-mønster (STONE_DARKEST horisontale fuger hver 4 px)
    for dy in range(3, h, 4):
        pygame.draw.rect(
            surface, constants.COLOR_STONE_DARKEST, (x, y_top + dy, w, 1)
        )
    # Vertikale fuger (forskjøvet for mursteinmønster)
    for row in range(h // 4 + 1):
        y = y_top + row * 4
        offset = 0 if row % 2 == 0 else 4
        for vx in range(offset, w, 8):
            pygame.draw.rect(
                surface, constants.COLOR_STONE_DARKEST,
                (x + vx, y, 1, 4),
            )
    # Tak (britisk skifer — mørkt)
    pygame.draw.rect(
        surface, constants.COLOR_STONE_DARKEST, (x - 3, y_top - 3, w + 6, 3)
    )
    # Etasje-skille
    mid_y = y_top + h // 2
    pygame.draw.rect(
        surface, constants.COLOR_STONE_LIGHT, (x, mid_y, w, 1)
    )
    # Jerngelénder-balkong (andre etasje)
    balc_y = mid_y + 2
    pygame.draw.rect(
        surface, constants.COLOR_STONE_DARKEST, (x + 2, balc_y, w - 4, 1)
    )
    # Balusterstenger
    for bx in range(x + 4, x + w - 2, 4):
        pygame.draw.rect(
            surface, constants.COLOR_STONE_DARKEST, (bx, balc_y - 2, 1, 2)
        )
    # Vinduer — symmetriske (2 pr etasje)
    win_w, win_h = 10, 10
    for is_upper in (False, True):
        wy = (y_top + 6) if is_upper else (mid_y + 6)
        for wx_off in (8, w - 18):
            wx = x + wx_off
            pygame.draw.rect(
                surface, constants.COLOR_STONE_DARKEST, (wx, wy, win_w, win_h)
            )
            pygame.draw.rect(
                surface, constants.COLOR_STONE_LIT,
                (wx + 1, wy + 1, win_w - 2, win_h - 2),
            )
            # Vindus-kors
            pygame.draw.rect(
                surface, constants.COLOR_STONE_DARK,
                (wx + win_w // 2 - 1, wy, 1, win_h),
            )
    # Dør (formell, stor)
    door_w, door_h = 10, 14
    door_x = x + w // 2 - door_w // 2
    door_y = ground_top_y - door_h
    pygame.draw.rect(
        surface, constants.COLOR_STONE_DARKEST, (door_x, door_y, door_w, door_h)
    )
    pygame.draw.rect(
        surface, constants.COLOR_WOOD_MID,
        (door_x + 1, door_y + 1, door_w - 2, door_h - 2),
    )


def bake_port_royal_east_india_company(
    surface: pygame.Surface,
    x: int, w: int, h: int,
    ground_top_y: int,
    style_variant: int = 0,
) -> None:
    """East India Co.-kontor med skilt. 48-56 px høy.

    Bredere enn offisersbolig. STONE_LIGHT hvitkalket base. Stort
    skilt over døren (LANTERN-kantet).
    """
    y_top = ground_top_y - h
    # Hvitkalket base
    pygame.draw.rect(surface, constants.COLOR_STONE_LIGHT, (x, y_top, w, h))
    # Mursten-kant synlig langs topp
    pygame.draw.rect(
        surface, constants.COLOR_STONE_DARK, (x, y_top, w, 2)
    )
    # Tak
    pygame.draw.rect(
        surface, constants.COLOR_STONE_DARKEST, (x - 4, y_top - 3, w + 8, 3)
    )
    # Skilt over døren (horisontalt rektangel, LANTERN-kantet)
    sign_w, sign_h = 32, 8
    sign_x = x + w // 2 - sign_w // 2
    sign_y = y_top + 10
    pygame.draw.rect(
        surface, constants.COLOR_WOOD_DARKEST, (sign_x, sign_y, sign_w, sign_h)
    )
    pygame.draw.rect(
        surface, constants.COLOR_LANTERN, (sign_x + 1, sign_y + 1, sign_w - 2, sign_h - 2)
    )
    # "EIC" antydet med 3 prikker på skilt
    for i, dx in enumerate((8, 14, 22)):
        pygame.draw.rect(
            surface, constants.COLOR_HAT, (sign_x + dx, sign_y + 3, 2, 3)
        )
    # Vinduer (4 stk, symmetriske)
    win_w, win_h = 10, 12
    win_y = y_top + 22
    for wx_off in (6, 22, w - 32, w - 16):
        wx = x + wx_off
        pygame.draw.rect(
            surface, constants.COLOR_STONE_DARKEST, (wx, win_y, win_w, win_h)
        )
        pygame.draw.rect(
            surface, constants.COLOR_STONE_BRIGHT, (wx + 1, win_y + 1, win_w - 2, win_h - 2)
        )
        # Vindus-kors
        pygame.draw.rect(
            surface, constants.COLOR_STONE_DARK,
            (wx + win_w // 2 - 1, win_y, 1, win_h),
        )
        pygame.draw.rect(
            surface, constants.COLOR_STONE_DARK,
            (wx, win_y + win_h // 2 - 1, win_w, 1),
        )
    # Dør (dobbel, formell)
    door_w, door_h = 16, 16
    door_x = x + w // 2 - door_w // 2
    door_y = ground_top_y - door_h
    pygame.draw.rect(
        surface, constants.COLOR_STONE_DARKEST, (door_x, door_y, door_w, door_h)
    )
    pygame.draw.rect(
        surface, constants.COLOR_WOOD_DARK,
        (door_x + 2, door_y + 2, door_w - 4, door_h - 4),
    )
    pygame.draw.rect(
        surface, constants.COLOR_STONE_DARKEST,
        (door_x + door_w // 2, door_y + 2, 1, door_h - 4),
    )


def bake_port_royal_soldier_barracks(
    surface: pygame.Surface,
    x: int, w: int, h: int,
    ground_top_y: int,
    style_variant: int = 0,
) -> None:
    """Soldat-arbeidsbrakke med identisk vindusrekke. 40-48 px høy.

    Institusjonell regelmessighet: 5 identiske vinduer i perfekt
    rekke. Ingen ornamentikk — rent militært.
    """
    y_top = ground_top_y - h
    # Vegg (STONE_DARK)
    pygame.draw.rect(surface, constants.COLOR_STONE_DARK, (x, y_top, w, h))
    # Tak — flat kolonial
    pygame.draw.rect(
        surface, constants.COLOR_STONE_DARKEST, (x - 2, y_top - 2, w + 4, 2)
    )
    # Topp-kant
    pygame.draw.rect(
        surface, constants.COLOR_STONE_LIGHT, (x, y_top + 1, w, 1)
    )
    # Identisk vindusrekke — 5 vinduer, jevnt fordelt
    count = 5
    win_w, win_h = 7, 10
    margin = 4
    span = w - 2 * margin
    step = (span - win_w) // (count - 1)
    win_y = y_top + 6
    # C2.5-7 statisk lys-karakter — Port Royal "kald overvåking":
    # 4 av 5 vinduer kaldt STONE_LIT (institusjonelt), 1 LANTERN-
    # varmt (midterste — "lone guard on duty").
    lone_guard_idx = count // 2
    for i in range(count):
        wx = x + margin + i * step
        pygame.draw.rect(
            surface, constants.COLOR_STONE_DARKEST, (wx, win_y, win_w, win_h)
        )
        if i == lone_guard_idx:
            # Varm guard-vindu
            pygame.draw.rect(
                surface, constants.COLOR_LANTERN,
                (wx + 1, win_y + 1, win_w - 2, win_h - 2),
            )
            pygame.draw.rect(
                surface, constants.COLOR_LANTERN_BRIGHT,
                (wx + 2, win_y + 2, win_w - 4, 2),
            )
        else:
            pygame.draw.rect(
                surface, constants.COLOR_STONE_LIT,
                (wx + 1, win_y + 1, win_w - 2, win_h - 2),
            )
    # Dør (enkel, sentrert)
    door_w, door_h = 8, 14
    door_x = x + w // 2 - door_w // 2
    door_y = ground_top_y - door_h
    pygame.draw.rect(
        surface, constants.COLOR_STONE_DARKEST, (door_x, door_y, door_w, door_h)
    )
    pygame.draw.rect(
        surface, constants.COLOR_WOOD_MID,
        (door_x + 1, door_y + 1, door_w - 2, door_h - 2),
    )


def bake_port_royal_civil_warehouse(
    surface: pygame.Surface,
    x: int, w: int, h: int,
    ground_top_y: int,
    style_variant: int = 0,
) -> None:
    """Sivilt pakkhus ved kaia. 36-44 px høy.

    Murstein + tre. Enkel funksjonell bygning. Port-åpning på fronten.
    """
    y_top = ground_top_y - h
    # Hoveddel murstein (STONE_DARK)
    pygame.draw.rect(surface, constants.COLOR_STONE_DARK, (x, y_top, w, h - 12))
    # Nedre del — tre-overbygging (WOOD_DARK)
    pygame.draw.rect(
        surface, constants.COLOR_WOOD_DARK, (x, y_top + h - 12, w, 12)
    )
    # Horisontale plank-linjer på tre-del
    for dy in range(y_top + h - 10, y_top + h, 4):
        pygame.draw.rect(
            surface, constants.COLOR_WOOD_DARKEST, (x, dy, w, 1)
        )
    # Tak
    pygame.draw.rect(
        surface, constants.COLOR_STONE_DARKEST, (x - 2, y_top - 2, w + 4, 2)
    )
    # Liten vindu
    win_w, win_h = 8, 7
    pygame.draw.rect(
        surface, constants.COLOR_STONE_DARKEST, (x + 6, y_top + 6, win_w, win_h)
    )
    pygame.draw.rect(
        surface, constants.COLOR_STONE_LIT, (x + 7, y_top + 7, win_w - 2, win_h - 2)
    )
    # Stor port
    port_w, port_h = 14, h - 4
    port_x = x + w - port_w - 6
    port_y = ground_top_y - port_h
    pygame.draw.rect(
        surface, constants.COLOR_STONE_DARKEST, (port_x, port_y, port_w, port_h)
    )
    # Mørk innside med antydning av varer
    pygame.draw.rect(
        surface, constants.COLOR_WOOD_DARKEST,
        (port_x + 1, port_y + 1, port_w - 2, port_h - 2),
    )


def bake_port_royal_merchants_house(
    surface: pygame.Surface,
    x: int, w: int, h: int,
    ground_top_y: int,
    style_variant: int = 0,
) -> None:
    """Handelsmannsbolig, 2 etasjer rik fasade. 48-60 px høy.

    Overklasse britisk. Hvitkalket + vindusporsjoner + pilaster-
    antydning på hjørnene.
    """
    y_top = ground_top_y - h
    # Hvitkalket fasade
    pygame.draw.rect(surface, constants.COLOR_STONE_LIGHT, (x, y_top, w, h))
    # Hjørne-pilaster (STONE_MID)
    pygame.draw.rect(
        surface, constants.COLOR_STONE_MID, (x, y_top + 2, 2, h - 2)
    )
    pygame.draw.rect(
        surface, constants.COLOR_STONE_MID, (x + w - 2, y_top + 2, 2, h - 2)
    )
    # Tak (skifer)
    pygame.draw.rect(
        surface, constants.COLOR_STONE_DARKEST, (x - 3, y_top - 3, w + 6, 3)
    )
    # Frisen-stripe (LANTERN subtil)
    pygame.draw.rect(
        surface, constants.COLOR_LANTERN, (x + 2, y_top + 2, w - 4, 1)
    )
    # Etasje-skille (horisontal list)
    mid_y = y_top + h // 2
    pygame.draw.rect(
        surface, constants.COLOR_STONE_MID, (x, mid_y, w, 1)
    )
    # Vinduer — 2 vinduer pr etasje, formelle
    win_w, win_h = 12, 12
    for is_upper in (True, False):
        wy = (y_top + 6) if is_upper else (mid_y + 6)
        for wx_off in (6, w - 18):
            wx = x + wx_off
            pygame.draw.rect(
                surface, constants.COLOR_STONE_DARKEST, (wx, wy, win_w, win_h)
            )
            pygame.draw.rect(
                surface, constants.COLOR_STONE_LIT,
                (wx + 1, wy + 1, win_w - 2, win_h - 2),
            )
            # Kryss
            pygame.draw.rect(
                surface, constants.COLOR_STONE_DARK,
                (wx + win_w // 2 - 1, wy, 1, win_h),
            )
            pygame.draw.rect(
                surface, constants.COLOR_STONE_DARK,
                (wx, wy + win_h // 2 - 1, win_w, 1),
            )
    # Formell dør med portal
    door_w, door_h = 12, 14
    door_x = x + w // 2 - door_w // 2
    door_y = ground_top_y - door_h
    # Portal-ramme
    pygame.draw.rect(
        surface, constants.COLOR_STONE_MID,
        (door_x - 2, door_y - 2, door_w + 4, door_h + 2),
    )
    pygame.draw.rect(
        surface, constants.COLOR_STONE_DARKEST, (door_x, door_y, door_w, door_h)
    )
    pygame.draw.rect(
        surface, constants.COLOR_WOOD_MID,
        (door_x + 2, door_y + 2, door_w - 4, door_h - 4),
    )


def bake_port_royal_apothecary(
    surface: pygame.Surface,
    x: int, w: int, h: int,
    ground_top_y: int,
    style_variant: int = 0,
) -> None:
    """Legekontor/apotek med skilt. 40-48 px høy.

    Murstein-base, skilt med morter-symbol (LANTERN + STONE).
    """
    y_top = ground_top_y - h
    # Vegg
    pygame.draw.rect(surface, constants.COLOR_STONE_DARK, (x, y_top, w, h))
    # Tak
    pygame.draw.rect(
        surface, constants.COLOR_STONE_DARKEST, (x - 2, y_top - 2, w + 4, 2)
    )
    # Hengende skilt (over dør, til venstre)
    sign_w, sign_h = 14, 10
    sign_x = x + w // 2 - sign_w - 6
    sign_y = y_top + 6
    # Skilt-kant
    pygame.draw.rect(
        surface, constants.COLOR_WOOD_DARKEST, (sign_x, sign_y, sign_w, sign_h)
    )
    pygame.draw.rect(
        surface, constants.COLOR_STONE_LIGHT, (sign_x + 1, sign_y + 1, sign_w - 2, sign_h - 2)
    )
    # Morter-symbol (LANTERN-gul + skygge)
    mx = sign_x + sign_w // 2
    my = sign_y + 3
    pygame.draw.rect(surface, constants.COLOR_LANTERN, (mx - 3, my, 6, 4))
    pygame.draw.rect(surface, constants.COLOR_EMBER, (mx - 2, my + 4, 4, 1))
    # Opphengsstreng
    pygame.draw.rect(
        surface, constants.COLOR_WOOD_DARKEST, (sign_x + sign_w // 2, y_top + 2, 1, 4)
    )
    # Vinduer (2)
    win_w, win_h = 10, 10
    for wx_off in (6, w - 16):
        wx = x + wx_off
        wy = y_top + 20
        pygame.draw.rect(
            surface, constants.COLOR_STONE_DARKEST, (wx, wy, win_w, win_h)
        )
        pygame.draw.rect(
            surface, constants.COLOR_STONE_LIT,
            (wx + 1, wy + 1, win_w - 2, win_h - 2),
        )
    # Dør
    door_w, door_h = 10, 14
    door_x = x + w // 2 + 4
    door_y = ground_top_y - door_h
    pygame.draw.rect(
        surface, constants.COLOR_STONE_DARKEST, (door_x, door_y, door_w, door_h)
    )
    pygame.draw.rect(
        surface, constants.COLOR_WOOD_DARK,
        (door_x + 1, door_y + 1, door_w - 2, door_h - 2),
    )


# ============================================================================
# Havana fyll-bygninger (C2.5-6b)
# Stil: balkonger, arkader, spansk-barokk, WOOD_LIGHT/LANTERN varme,
# blomster-aksenter
# ============================================================================

def bake_havana_borger_house(
    surface: pygame.Surface,
    x: int, w: int, h: int,
    ground_top_y: int,
    style_variant: int = 0,
) -> None:
    """Borgerhus, 2 etasjer rik fasade. 56-60 px høy.

    WOOD_LIGHT hvitkalket, balkong med jerngelénder (spansk stil —
    mer ornamentert enn Port Royals strenge britiske), blomstrende
    plantering.
    """
    y_top = ground_top_y - h
    # Hvitkalket base
    pygame.draw.rect(surface, constants.COLOR_WOOD_LIGHT, (x, y_top, w, h))
    # Tak med dyp oker kant
    pygame.draw.rect(
        surface, constants.COLOR_WOOD_DARKEST, (x - 4, y_top - 3, w + 8, 3)
    )
    pygame.draw.rect(
        surface, constants.COLOR_EMBER, (x - 4, y_top - 3, w + 8, 1)
    )
    # Øvre-etasje-balkong
    mid_y = y_top + h // 2
    balc_y = mid_y - 1
    # Balkong-plate (LANTERN gyllen)
    pygame.draw.rect(
        surface, constants.COLOR_LANTERN, (x + 4, balc_y, w - 8, 2)
    )
    # Balusterstenger (ornamentell — alternerende)
    for bx in range(x + 6, x + w - 4, 3):
        pygame.draw.rect(
            surface, constants.COLOR_STONE_DARKEST, (bx, balc_y - 3, 1, 3)
        )
    # Blomstrende plantering (EMBER blomster)
    for bx in range(x + 8, x + w - 6, 8):
        pygame.draw.rect(
            surface, constants.COLOR_EMBER, (bx, balc_y - 1, 2, 1)
        )
        pygame.draw.rect(
            surface, constants.COLOR_WOOD_DARK, (bx, balc_y, 2, 1)
        )
    # Vinduer — 2 pr etasje, formelle
    win_w, win_h = 12, 10
    for is_upper in (True, False):
        wy = (y_top + 8) if is_upper else (mid_y + 6)
        for wx_off in (6, w - 18):
            wx = x + wx_off
            pygame.draw.rect(
                surface, constants.COLOR_WOOD_DARKEST, (wx, wy, win_w, win_h)
            )
            pygame.draw.rect(
                surface, constants.COLOR_LANTERN,
                (wx + 1, wy + 1, win_w - 2, win_h - 2),
            )
            pygame.draw.rect(
                surface, constants.COLOR_LANTERN_BRIGHT,
                (wx + 2, wy + 2, win_w - 4, 2),
            )
    # Barokk dør-portal
    door_w, door_h = 12, 14
    door_x = x + w // 2 - door_w // 2
    door_y = ground_top_y - door_h
    # Portal-ramme (EMBER — varm aksent)
    pygame.draw.rect(
        surface, constants.COLOR_EMBER,
        (door_x - 2, door_y - 2, door_w + 4, door_h + 2),
    )
    pygame.draw.rect(
        surface, constants.COLOR_WOOD_DARKEST, (door_x, door_y, door_w, door_h)
    )
    pygame.draw.rect(
        surface, constants.COLOR_FLAME,
        (door_x + 1, door_y + 1, door_w - 2, door_h - 2),
    )


def bake_havana_cloister_annex(
    surface: pygame.Surface,
    x: int, w: int, h: int,
    ground_top_y: int,
    style_variant: int = 0,
) -> None:
    """Kloster-anneks knyttet til katedralen. 48-56 px høy.

    STONE_LIGHT fasade (katedral-konsistens). Arkade langs fronten
    (3 små buer). Kors på taket.
    """
    y_top = ground_top_y - h
    # Fasade (matcher katedralens WOOD_LIGHT)
    pygame.draw.rect(surface, constants.COLOR_WOOD_LIGHT, (x, y_top, w, h))
    # Tak
    pygame.draw.rect(
        surface, constants.COLOR_WOOD_DARKEST, (x - 2, y_top - 3, w + 4, 3)
    )
    # Lite kors på taket (kloster-signatur)
    cross_cx = x + w // 2
    cross_y = y_top - 7
    pygame.draw.rect(surface, constants.COLOR_LANTERN_BRIGHT, (cross_cx - 1, cross_y, 2, 4))
    pygame.draw.rect(surface, constants.COLOR_LANTERN_BRIGHT, (cross_cx - 2, cross_y + 1, 4, 1))
    # 3 små arkade-buer langs fronten (nederste del)
    arch_count = 3
    arch_w = 10
    margin = 4
    span = w - 2 * margin
    step = (span - arch_w) // (arch_count - 1) if arch_count > 1 else 0
    arch_y = y_top + h - 18
    for i in range(arch_count):
        ax = x + margin + i * step
        pygame.draw.rect(
            surface, constants.COLOR_STONE_DARKEST, (ax, arch_y, arch_w, 14)
        )
        # Buet topp
        pygame.draw.rect(
            surface, constants.COLOR_STONE_DARKEST,
            (ax + 1, arch_y - 1, arch_w - 2, 1),
        )
        # EMBER-glimt inne
        pygame.draw.rect(
            surface, constants.COLOR_EMBER,
            (ax + 2, arch_y + 10, arch_w - 4, 1),
        )
    # Små vinduer øverst
    win_w, win_h = 6, 6
    for wx_off in (6, w - 12):
        wx = x + wx_off
        wy = y_top + 4
        pygame.draw.rect(
            surface, constants.COLOR_WOOD_DARKEST, (wx, wy, win_w, win_h)
        )
        pygame.draw.rect(
            surface, constants.COLOR_LANTERN,
            (wx + 1, wy + 1, win_w - 2, win_h - 2),
        )


def bake_havana_merchants_house(
    surface: pygame.Surface,
    x: int, w: int, h: int,
    ground_top_y: int,
    style_variant: int = 0,
) -> None:
    """Handelsmannshus med balkong og blomster. 48-60 px høy.

    Mer ornamentell enn borger_house. Stor balkong med rike blomster
    (EMBER og LANTERN), tung WOOD_MID base.
    """
    y_top = ground_top_y - h
    # Base
    pygame.draw.rect(surface, constants.COLOR_WOOD_MID, (x, y_top, w, h))
    # Tak
    pygame.draw.rect(
        surface, constants.COLOR_WOOD_DARKEST, (x - 3, y_top - 3, w + 6, 3)
    )
    pygame.draw.rect(
        surface, constants.COLOR_LANTERN, (x - 3, y_top - 3, w + 6, 1)
    )
    # Balkong på 2/3 høyde — bred og ornamentell
    balc_y = y_top + h // 3 * 2
    # Balkong-plate
    pygame.draw.rect(
        surface, constants.COLOR_WOOD_DARKEST, (x + 2, balc_y, w - 4, 2)
    )
    pygame.draw.rect(
        surface, constants.COLOR_LANTERN, (x + 2, balc_y, w - 4, 1)
    )
    # Støtte-bjelker under balkong
    for bx in range(x + 6, x + w - 4, 6):
        pygame.draw.rect(
            surface, constants.COLOR_WOOD_DARKEST, (bx, balc_y + 2, 1, 2)
        )
    # Jerngelénder (vertikale)
    for bx in range(x + 4, x + w - 2, 2):
        pygame.draw.rect(
            surface, constants.COLOR_STONE_DARKEST, (bx, balc_y - 4, 1, 4)
        )
    # Blomster i potter (EMBER + LANTERN)
    for bx in range(x + 6, x + w - 6, 10):
        pygame.draw.rect(
            surface, constants.COLOR_EMBER, (bx, balc_y - 6, 3, 2)
        )
        pygame.draw.rect(
            surface, constants.COLOR_LANTERN_BRIGHT, (bx + 1, balc_y - 6, 1, 1)
        )
    # Vinduer
    win_w, win_h = 10, 10
    # Øvre etasje (over balkong)
    for wx_off in (6, w - 16):
        wx = x + wx_off
        wy = y_top + 6
        pygame.draw.rect(
            surface, constants.COLOR_WOOD_DARKEST, (wx, wy, win_w, win_h)
        )
        pygame.draw.rect(
            surface, constants.COLOR_LANTERN,
            (wx + 1, wy + 1, win_w - 2, win_h - 2),
        )
    # Nedre etasje: én stor dør sentralt
    door_w, door_h = 14, 16
    door_x = x + w // 2 - door_w // 2
    door_y = ground_top_y - door_h
    pygame.draw.rect(
        surface, constants.COLOR_EMBER,
        (door_x - 2, door_y - 2, door_w + 4, door_h + 2),
    )
    pygame.draw.rect(
        surface, constants.COLOR_WOOD_DARKEST, (door_x, door_y, door_w, door_h)
    )
    pygame.draw.rect(
        surface, constants.COLOR_FLAME,
        (door_x + 2, door_y + 2, door_w - 4, door_h - 4),
    )


def bake_havana_artisans_workshop(
    surface: pygame.Surface,
    x: int, w: int, h: int,
    ground_top_y: int,
    style_variant: int = 0,
) -> None:
    """Gesellene-verksted med bronse-smie. 40-48 px høy.

    Mindre enn Tortugas smithy, mer ornamentert. Bronse-glimt
    (LANTERN) i åpen dør.
    """
    y_top = ground_top_y - h
    # Base (WOOD_MID)
    pygame.draw.rect(surface, constants.COLOR_WOOD_MID, (x, y_top, w, h))
    # Tak
    pygame.draw.rect(
        surface, constants.COLOR_WOOD_DARKEST, (x - 2, y_top - 2, w + 4, 2)
    )
    # Pipe
    pipe_x = x + 6
    pygame.draw.rect(
        surface, constants.COLOR_STONE_DARKEST, (pipe_x, y_top - 8, 4, 8)
    )
    # Røyk
    pygame.draw.rect(
        surface, constants.COLOR_FOG, (pipe_x + 1, y_top - 12, 3, 4)
    )
    # Vindu
    win_w, win_h = 8, 8
    pygame.draw.rect(
        surface, constants.COLOR_WOOD_DARKEST, (x + 4, y_top + 10, win_w, win_h)
    )
    pygame.draw.rect(
        surface, constants.COLOR_LANTERN, (x + 5, y_top + 11, win_w - 2, win_h - 2)
    )
    # Stor åpen dør (smie-åpning)
    door_w, door_h = 16, 20
    door_x = x + w - door_w - 4
    door_y = ground_top_y - door_h
    pygame.draw.rect(
        surface, constants.COLOR_STONE_DARKEST, (door_x, door_y, door_w, door_h)
    )
    # Bronse-glimt (LANTERN + EMBER inside — gelsene sjekker metall)
    pygame.draw.rect(
        surface, constants.COLOR_EMBER, (door_x + 2, door_y + 4, door_w - 4, door_h - 8)
    )
    pygame.draw.rect(
        surface, constants.COLOR_LANTERN, (door_x + 4, door_y + 8, door_w - 8, 4)
    )
    pygame.draw.rect(
        surface, constants.COLOR_LANTERN_BRIGHT, (door_x + 6, door_y + 10, door_w - 12, 1)
    )


def bake_havana_guard_house(
    surface: pygame.Surface,
    x: int, w: int, h: int,
    ground_top_y: int,
    style_variant: int = 0,
) -> None:
    """Spansk vakthus, lite militært. 40-48 px høy.

    Stein (STONE_DARK) — avviker fra Havanas varme palett, men
    tematisk riktig: spansk militær. Én soldat-skulder-silhuett i
    vinduet.
    """
    y_top = ground_top_y - h
    # Stein-base
    pygame.draw.rect(surface, constants.COLOR_STONE_DARK, (x, y_top, w, h))
    # Tak (buet/takrenne — spansk teglstein)
    pygame.draw.rect(
        surface, constants.COLOR_EMBER, (x - 2, y_top - 3, w + 4, 3)
    )
    pygame.draw.rect(
        surface, constants.COLOR_WOOD_DARKEST, (x - 2, y_top - 3, w + 4, 1)
    )
    # Vaktvindu — stort kvadrat
    win_w, win_h = 12, 12
    win_x = x + w // 2 - win_w // 2
    win_y = y_top + 10
    pygame.draw.rect(
        surface, constants.COLOR_STONE_DARKEST, (win_x, win_y, win_w, win_h)
    )
    pygame.draw.rect(
        surface, constants.COLOR_LANTERN,
        (win_x + 1, win_y + 1, win_w - 2, win_h - 2),
    )
    # Soldat-silhuett i vinduet (HAT + skygge)
    pygame.draw.rect(
        surface, constants.COLOR_HAT, (win_x + 4, win_y + 3, 4, 2)
    )
    pygame.draw.rect(
        surface, constants.COLOR_EMBER, (win_x + 3, win_y + 5, 6, 3)
    )
    # Spansk skilt (EMBER + LANTERN — oker/rød)
    pygame.draw.rect(
        surface, constants.COLOR_EMBER, (x + 4, y_top + 4, w - 8, 3)
    )
    pygame.draw.rect(
        surface, constants.COLOR_LANTERN_BRIGHT, (x + w // 2 - 2, y_top + 5, 4, 1)
    )
    # Dør
    door_w, door_h = 8, 12
    door_x = x + w // 2 - door_w // 2
    door_y = ground_top_y - door_h
    pygame.draw.rect(
        surface, constants.COLOR_STONE_DARKEST, (door_x, door_y, door_w, door_h)
    )
    pygame.draw.rect(
        surface, constants.COLOR_WOOD_DARK,
        (door_x + 1, door_y + 1, door_w - 2, door_h - 2),
    )


def bake_havana_tobacco_warehouse(
    surface: pygame.Surface,
    x: int, w: int, h: int,
    ground_top_y: int,
    style_variant: int = 0,
) -> None:
    """Tobakks-pakkhus, stort lavt. 40-48 px høy.

    WOOD_MID base med tobakkbrune aksenter. Åpen port viser stablede
    tobakksballer inne (antydet via WOOD_DARK-prikker).
    """
    y_top = ground_top_y - h
    # Base
    pygame.draw.rect(surface, constants.COLOR_WOOD_MID, (x, y_top, w, h))
    # Horisontale planklinjer
    for dy in range(6, h, 6):
        pygame.draw.rect(
            surface, constants.COLOR_WOOD_DARK, (x, y_top + dy, w, 1)
        )
    # Tak
    pygame.draw.rect(
        surface, constants.COLOR_WOOD_DARKEST, (x - 2, y_top - 2, w + 4, 2)
    )
    # Stort tegn over inngangen (tobakksblad-symbol — EMBER)
    sign_w, sign_h = 12, 5
    sign_x = x + w // 2 - sign_w // 2
    sign_y = y_top + 3
    pygame.draw.rect(
        surface, constants.COLOR_WOOD_DARKEST, (sign_x, sign_y, sign_w, sign_h)
    )
    pygame.draw.rect(
        surface, constants.COLOR_EMBER, (sign_x + 1, sign_y + 1, sign_w - 2, sign_h - 2)
    )
    pygame.draw.rect(
        surface, constants.COLOR_LANTERN_BRIGHT,
        (sign_x + sign_w // 2 - 1, sign_y + 1, 1, sign_h - 2),
    )
    # Åpen port
    port_w, port_h = 16, h - 12
    port_x = x + w // 2 - port_w // 2
    port_y = ground_top_y - port_h
    pygame.draw.rect(
        surface, constants.COLOR_STONE_DARKEST, (port_x, port_y, port_w, port_h)
    )
    # Tobakksballer inne (WOOD_DARK)
    for i, dx in enumerate((2, 8)):
        pygame.draw.rect(
            surface, constants.COLOR_WOOD_DARK,
            (port_x + dx, port_y + port_h - 6, 5, 4),
        )


def bake_havana_chapel_small(
    surface: pygame.Surface,
    x: int, w: int, h: int,
    ground_top_y: int,
    style_variant: int = 0,
) -> None:
    """Lite daglig-kapell. 48-56 px høy.

    WOOD_LIGHT fasade. Smal + buet topp med kors. Varm alter-glød
    gjennom dør.
    """
    y_top = ground_top_y - h
    # Base
    pygame.draw.rect(surface, constants.COLOR_WOOD_LIGHT, (x, y_top, w, h))
    # Spiss topp-gavl (halv-trekant)
    gavl_pts = [
        (x - 1, y_top),
        (x + w + 1, y_top),
        (x + w // 2, y_top - 8),
    ]
    pygame.draw.polygon(surface, constants.COLOR_WOOD_DARKEST, gavl_pts)
    # Kors på toppen
    cross_cx = x + w // 2
    cross_y = y_top - 14
    pygame.draw.rect(
        surface, constants.COLOR_LANTERN_BRIGHT,
        (cross_cx - 1, cross_y, 2, 6),
    )
    pygame.draw.rect(
        surface, constants.COLOR_LANTERN_BRIGHT,
        (cross_cx - 2, cross_y + 1, 4, 1),
    )
    # Rund-vindu (lite rose-vindu)
    win_r = 4
    win_cx = x + w // 2
    win_cy = y_top + 10
    pygame.draw.circle(
        surface, constants.COLOR_WOOD_DARKEST, (win_cx, win_cy), win_r + 1
    )
    pygame.draw.circle(
        surface, constants.COLOR_LANTERN, (win_cx, win_cy), win_r
    )
    pygame.draw.circle(
        surface, constants.COLOR_LANTERN_BRIGHT, (win_cx, win_cy), 1
    )
    # Buet dør med alter-glød
    door_w, door_h = 10, 18
    door_x = x + w // 2 - door_w // 2
    door_y = ground_top_y - door_h
    pygame.draw.rect(
        surface, constants.COLOR_STONE_DARKEST, (door_x, door_y, door_w, door_h)
    )
    # Buet topp
    pygame.draw.rect(
        surface, constants.COLOR_STONE_DARKEST,
        (door_x + 1, door_y - 1, door_w - 2, 1),
    )
    # Varm alter-glød
    pygame.draw.rect(
        surface, constants.COLOR_EMBER,
        (door_x + 1, door_y + 1, door_w - 2, door_h - 2),
    )
    pygame.draw.rect(
        surface, constants.COLOR_FLAME,
        (door_x + 2, door_y + 4, door_w - 4, door_h - 8),
    )
    pygame.draw.rect(
        surface, constants.COLOR_LANTERN_BRIGHT,
        (door_x + door_w // 2 - 1, door_y + 6, 2, 3),
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
    # Port Royal (C2.5-6b) — murstein, jerngelénder, kolonial orden
    "port_royal_officers_residence": bake_port_royal_officers_residence,
    "port_royal_east_india_company": bake_port_royal_east_india_company,
    "port_royal_soldier_barracks": bake_port_royal_soldier_barracks,
    "port_royal_civil_warehouse": bake_port_royal_civil_warehouse,
    "port_royal_merchants_house": bake_port_royal_merchants_house,
    "port_royal_apothecary": bake_port_royal_apothecary,
    # Havana (C2.5-6b) — balkonger, arkader, spansk-barokk
    "havana_borger_house": bake_havana_borger_house,
    "havana_cloister_annex": bake_havana_cloister_annex,
    "havana_merchants_house": bake_havana_merchants_house,
    "havana_artisans_workshop": bake_havana_artisans_workshop,
    "havana_guard_house": bake_havana_guard_house,
    "havana_tobacco_warehouse": bake_havana_tobacco_warehouse,
    "havana_chapel_small": bake_havana_chapel_small,
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
