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
from config.port_config import (
    PortConfig, PortProps, SignatureBuilding,
)
from entities import port_props as props_module


#: Colorkey for transparente områder på gameplay-laget. Fortsatt i bruk
#: her (gameplay-lag som har store transparente regioner over bygningene);
#: IKKE brukt på fg-laget som beholder SRCALPHA per C3b-funn.
COLORKEY = (255, 0, 255)


def _bake_ground(
    surface: pygame.Surface,
    ground_top_y: int,
    texture: str = "wood_dark",
) -> None:
    """Gategulv med havn-spesifikk tekstur.

    `texture` dispatches til `entities.port_props.bake_ground`. Default
    "wood_dark" bevarer eksisterende Tortuga-oppførsel før C2.5-1 og
    brukes av stub-havnene (Port Royal/Havana/Nassau) i denne commiten
    — de får egne teksturer i C2.5-2/3/4.
    """
    props_module.bake_ground(surface, ground_top_y, texture)


def _bake_props(
    surface: pygame.Surface,
    props: PortProps,
    ground_top_y: int,
) -> None:
    """Bake rekvisita-lag (boder, tønner, lanterne-stolper) inn i gameplay-
    surfacen.

    Rekvisita-rekkefølgen per `FASE_2_5.md §2.1` rendering-lag:
    1. Gategulv (allerede bakt av _bake_ground)
    2. Markedsboder (bakerst — tegnes bak tønner hvis de overlapper)
    3. Stablede tønner
    4. Lanterne-stolper (forrest — tegnes OVER andre props)

    NPC-silhuetter er ikke her; de tegnes runtime som entiteter
    (bevarer prinsippet "NPC-er skal være sprites i samme palett
    som spiller og Hawkins" per spec).
    """
    for stall in props.market_stalls:
        props_module.bake_market_stall(
            surface, stall.x, ground_top_y, stall.w,
        )
    for stack in props.barrel_stacks:
        props_module.bake_barrel_stack(
            surface, stack.x, ground_top_y, stack.count,
        )
    # Jerngjerder (Port Royal): tegnes før lanterne-stolpene slik at
    # eventuelle overlapp ikke skjuler lyset fra stolpens halo.
    for fence in props.iron_fences:
        props_module.bake_iron_fence(
            surface, fence.x, ground_top_y, fence.length,
        )
    # Fontener (Havana) — statiske i C2.5-3; C2.5-6 legger til
    # palette-cycling på vann-piksler.
    for fountain in props.fountains:
        props_module.bake_fountain(surface, fountain.x, ground_top_y)
    # Plantere/busker (Havana) — tegnes etter fontenene slik at
    # nærme busker kan skjære over basseng-skygger.
    for planter in props.planters:
        props_module.bake_planter(surface, planter.x, ground_top_y)
    for lantern in props.lanterns:
        props_module.bake_lantern_post(surface, lantern.x, ground_top_y)


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


def _bake_customs_house(
    surface: pygame.Surface,
    x: int, y: int, w: int, h: int,
    ground_top_y: int,
) -> None:
    """Port Royal: Customs House — erstatter Tortuga-børshuset (C2.5-2).

    Arkitektonisk signatur per FASE_2_5.md §2.2:
    - Kolonnet portal (flere søyler enn Tortuga-børshuset for
      institusjonell autoritet — 6 mot Tortugas 4)
    - Hvitkalket kolonial-orden (STONE_MID som hovedvegg — lysere
      enn Tortuga-børshusets STONE_DARK)
    - Pediment med krone-detalj (britisk ordens-signal)

    HUD viser fortsatt "Port Royal Børs — Dag N"; kun visuelt
    forskjellig fra Tortuga-exchange-spriten. Bounding-boks er samme
    som `exchange`-feltet i ports.json slik at E-interaksjon og
    dock-avstand er uendret.
    """
    # Hvitkalket base (STONE_MID som hovedfarge — britisk kolonial-
    # tradisjon av hvitkalk over stein)
    pygame.draw.rect(surface, constants.COLOR_STONE_MID, (x, y + 10, w, h - 10))
    # Gulv-stripe
    pygame.draw.rect(
        surface, constants.COLOR_STONE_DARKEST, (x, y + 10, w, 1)
    )
    # Trekantgavl (pediment) — bredere og lysere enn Tortugas for
    # britisk klassisk-revival-signal
    pediment = [
        (x - 8, y + 12),
        (x + w + 8, y + 12),
        (x + w // 2, y - 12),
    ]
    pygame.draw.polygon(surface, constants.COLOR_STONE_DARK, pediment)
    # Pediment-kant
    pygame.draw.lines(
        surface, constants.COLOR_STONE_LIGHT, False,
        [(x - 8, y + 12), (x + w // 2, y - 12), (x + w + 8, y + 12)], 1,
    )
    # Krone-ornament midt i pediment (liten britisk ordens-prikk i
    # LANTERN_BRIGHT — "Crown & Anchor"-antydning)
    pygame.draw.rect(
        surface, constants.COLOR_LANTERN_BRIGHT,
        (x + w // 2 - 2, y - 2, 4, 3),
    )
    pygame.draw.rect(
        surface, constants.COLOR_LANTERN,
        (x + w // 2 - 1, y - 4, 2, 2),
    )

    # Arkitrav over søyler
    pygame.draw.rect(surface, constants.COLOR_STONE_DARK, (x - 6, y + 12, w + 12, 6))
    pygame.draw.rect(surface, constants.COLOR_STONE_LIGHT, (x - 6, y + 12, w + 12, 1))

    # 6 søyler (mot Tortugas 4) — høyere og slankere
    col_w = 8
    col_h = h - 30
    col_y = y + 20
    col_count = 6
    # Jevnt fordelt med marg
    margin = 10
    span = w - 2 * margin
    step = (span - col_w) / (col_count - 1)
    col_xs = [x + margin + int(i * step) for i in range(col_count)]
    for cx in col_xs:
        pygame.draw.rect(
            surface, constants.COLOR_STONE_LIGHT, (cx, col_y, col_w, col_h)
        )
        # Lit-kant (venstre)
        pygame.draw.rect(
            surface, constants.COLOR_STONE_BRIGHT, (cx, col_y, 2, col_h)
        )
        # Skygge (høyre)
        pygame.draw.rect(
            surface, constants.COLOR_STONE_DARK,
            (cx + col_w - 1, col_y, 1, col_h),
        )
        # Kapitel + basis
        pygame.draw.rect(
            surface, constants.COLOR_STONE_BRIGHT, (cx - 2, col_y, col_w + 4, 2)
        )
        pygame.draw.rect(
            surface, constants.COLOR_STONE_DARK,
            (cx - 2, col_y + col_h - 2, col_w + 4, 2),
        )

    # Mellom-søyle-vinduer: 2 kalde vinduer i intervallene mellom 2-3 og 4-5
    # (sentrumsvinduet kuttes — der går døren)
    window_w, window_h = 14, 22
    window_y = y + 32
    window_gap_indexes = [(1, 2), (3, 4)]  # Midt mellom søyle 1-2 og 3-4
    for a, b in window_gap_indexes:
        mid_x = (col_xs[a] + col_xs[b]) // 2 + col_w // 2
        wx0 = mid_x - window_w // 2
        pygame.draw.rect(
            surface, constants.COLOR_STONE_LIT, (wx0, window_y, window_w, window_h)
        )
        pygame.draw.rect(
            surface, constants.COLOR_STONE_BRIGHT,
            (wx0 + 2, window_y + 2, window_w - 4, window_h - 4),
        )
        pygame.draw.rect(
            surface, constants.COLOR_STONE_DARK,
            (wx0 + window_w // 2 - 1, window_y, 2, window_h),
        )

    # Midtstilt stor dør — bredere enn Tortugas for "kolonial port"-effekt
    door_w, door_h = 32, 46
    door_x = x + w // 2 - door_w // 2
    door_y = ground_top_y - door_h
    pygame.draw.rect(
        surface, constants.COLOR_STONE_DARKEST, (door_x, door_y, door_w, door_h)
    )
    pygame.draw.rect(
        surface, constants.COLOR_STONE_MID,
        (door_x + 3, door_y + 3, door_w - 6, door_h - 6),
    )
    # Vertikal split (dobbel-dør)
    pygame.draw.rect(
        surface, constants.COLOR_STONE_DARKEST,
        (door_x + door_w // 2 - 1, door_y + 3, 2, door_h - 6),
    )
    # Trapp-antydning
    pygame.draw.rect(
        surface, constants.COLOR_STONE_LIGHT,
        (door_x - 6, ground_top_y, door_w + 12, 3),
    )
    pygame.draw.rect(
        surface, constants.COLOR_STONE_BRIGHT,
        (door_x - 6, ground_top_y, door_w + 12, 1),
    )


def _bake_church_tower(
    surface: pygame.Surface,
    x: int, y: int, w: int, h: int,
    ground_top_y: int,
) -> None:
    """Port Royal: klokketårn-kirke — smalt og høyt.

    Signaliserer kolonial orden + kontrast til Tortugas kaos. Klokke
    synlig i åpning, kors på toppen, månelys-opplyst vindu lavere ned.
    """
    # Tårn-kropp — STONE_MID (hvitkalket stein)
    pygame.draw.rect(surface, constants.COLOR_STONE_MID, (x, y, w, h))
    # Ytre kanter (STONE_DARK ramme)
    pygame.draw.rect(surface, constants.COLOR_STONE_DARK, (x, y, w, 1))
    pygame.draw.rect(surface, constants.COLOR_STONE_DARK, (x, y + h - 1, w, 1))
    pygame.draw.rect(surface, constants.COLOR_STONE_DARK, (x, y, 1, h))
    pygame.draw.rect(surface, constants.COLOR_STONE_DARK, (x + w - 1, y, 1, h))
    # Subtil vertikal pilar-linje venstre (arkitektur-detalj)
    pygame.draw.rect(
        surface, constants.COLOR_STONE_LIGHT, (x + 1, y + 2, 1, h - 4)
    )

    # Spir på toppen — trekant i STONE_DARKEST, rager 14 px over tårnet
    spire_top_y = y - 14
    spire_pts = [
        (x - 2, y + 1),
        (x + w + 2, y + 1),
        (x + w // 2, spire_top_y),
    ]
    pygame.draw.polygon(surface, constants.COLOR_STONE_DARKEST, spire_pts)

    # Kors på toppen av spiret — STONE_BRIGHT
    cross_x = x + w // 2
    pygame.draw.rect(
        surface, constants.COLOR_STONE_BRIGHT,
        (cross_x - 1, spire_top_y - 4, 2, 5),
    )
    pygame.draw.rect(
        surface, constants.COLOR_STONE_BRIGHT,
        (cross_x - 2, spire_top_y - 2, 4, 1),
    )

    # Klokke-åpning (øvre del av tårnet) — mørk boks
    bell_w, bell_h = max(6, w - 6), 12
    bell_x = x + (w - bell_w) // 2
    bell_y = y + 8
    pygame.draw.rect(
        surface, constants.COLOR_STONE_DARKEST, (bell_x, bell_y, bell_w, bell_h)
    )
    # Klokke — LANTERN (bronze-gylden mot mørk åpning)
    bell_core_x = bell_x + 1
    bell_core_y = bell_y + 2
    bell_core_w = bell_w - 2
    bell_core_h = bell_h - 4
    pygame.draw.rect(
        surface, constants.COLOR_LANTERN,
        (bell_core_x, bell_core_y, bell_core_w, bell_core_h),
    )
    # Klokke-høylys
    pygame.draw.rect(
        surface, constants.COLOR_LANTERN_BRIGHT,
        (bell_core_x + 1, bell_core_y + 1, bell_core_w - 2, 1),
    )
    # Klokke-opphengsbøyle
    pygame.draw.rect(
        surface, constants.COLOR_STONE_DARK,
        (x + w // 2 - 1, bell_y, 2, 2),
    )

    # Lavere vindu (spissbuet antydet med en fylt firkant + pil på toppen)
    win_y = y + h - 24
    win_w, win_h = max(4, w - 10), 14
    win_x = x + (w - win_w) // 2
    # Ramme
    pygame.draw.rect(
        surface, constants.COLOR_STONE_DARKEST, (win_x, win_y, win_w, win_h)
    )
    # Lys (svak månelys-refleksjon gjennom farget glass)
    pygame.draw.rect(
        surface, constants.COLOR_STONE_LIT,
        (win_x + 1, win_y + 1, win_w - 2, win_h - 2),
    )
    # Varm kjerne (alterlys) — LANTERN glimt gjennom farget glass
    pygame.draw.rect(
        surface, constants.COLOR_LANTERN,
        (win_x + win_w // 2 - 1, win_y + win_h // 2, 2, 2),
    )


def _bake_rum_warehouse(
    surface: pygame.Surface,
    x: int, y: int, w: int, h: int,
    ground_top_y: int,
) -> None:
    """Port Royal: rum-magasin — lang, lav bygning i WOOD-familien.

    Eneste varme bygning i havnens ellers kalde palett. Tematisk
    knytting til rum-bias (0.85). Åpne porter med tønner inne viser
    glimt av lantern-lys.
    """
    # Veggen — WOOD_MID for mørkt tjæret tre
    pygame.draw.rect(surface, constants.COLOR_WOOD_MID, (x, y, w, h))
    # Horisontale plank-linjer
    for dy in range(8, h, 12):
        pygame.draw.rect(
            surface, constants.COLOR_WOOD_DARK, (x, y + dy, w, 1)
        )
    # Lys-høylys på øvre kant
    pygame.draw.rect(surface, constants.COLOR_WOOD_LIGHT, (x, y, w, 1))

    # Tak (mørkt tre, litt bredere enn vegg)
    pygame.draw.rect(
        surface, constants.COLOR_WOOD_DARKEST, (x - 4, y - 4, w + 8, 4)
    )
    pygame.draw.rect(
        surface, constants.COLOR_STONE_DARK, (x - 4, y - 5, w + 8, 1)
    )

    # Åpne porter — 3 stk, lavere halvdel av bygningen
    port_count = 3
    port_w, port_h = 24, 28
    # Fordel jevnt; første margin 12
    total_ports = port_count * port_w
    gap = max(0, (w - total_ports - 24) // (port_count + 1))
    start_offset = 12 + gap
    for i in range(port_count):
        px = x + start_offset + i * (port_w + gap)
        py = ground_top_y - port_h
        # Port-ramme (mørk)
        pygame.draw.rect(
            surface, constants.COLOR_WOOD_DARKEST, (px, py, port_w, port_h)
        )
        # Mørk innside
        pygame.draw.rect(
            surface, constants.COLOR_STONE_DARKEST,
            (px + 2, py + 2, port_w - 4, port_h - 4),
        )
        # Lite tønne-silhuett inne (antyder innhold uten å kreve sprite)
        barrel_x = px + port_w // 2 - 4
        barrel_y = py + port_h - 16
        pygame.draw.rect(
            surface, constants.COLOR_WOOD_MID, (barrel_x, barrel_y, 8, 10)
        )
        pygame.draw.rect(
            surface, constants.COLOR_WOOD_DARKEST,
            (barrel_x, barrel_y, 8, 1),
        )
        pygame.draw.rect(
            surface, constants.COLOR_WOOD_DARKEST,
            (barrel_x, barrel_y + 4, 8, 1),
        )
        # EMBER-glimt ved port (antyder lantern-lys inne)
        pygame.draw.rect(
            surface, constants.COLOR_EMBER,
            (px + 2, py + port_h - 4, port_w - 4, 1),
        )


def _bake_trade_house(
    surface: pygame.Surface,
    x: int, y: int, w: int, h: int,
    ground_top_y: int,
) -> None:
    """Havana: Handelshus — erstatter Tortuga-børshus-spriten (C2.5-3).

    Arkade-fasade (gjenspeiler guvernørpalasset), åpen side mot
    havnen. Tunge vekter symbolsk synlige ved porten. Tematisk
    knytting til tobakk-bias (0.75).

    Palett: WOOD-familien dominerer (oker/varm) — spanske
    handelsbygg var tradisjonelt hvitkalket over tre/murstein, men
    for Havana-palettet vektes dette mot LANTERN/WOOD over STONE.
    """
    # Hovedfasade — WOOD_LIGHT (sol-belyst spansk stukk)
    pygame.draw.rect(surface, constants.COLOR_WOOD_LIGHT, (x, y + 10, w, h - 10))
    # Skygge-base (under arkaden, mørkere)
    pygame.draw.rect(
        surface, constants.COLOR_WOOD_MID,
        (x, y + h - 24, w, 16),
    )
    # Topp-kant (tak)
    pygame.draw.rect(
        surface, constants.COLOR_WOOD_DARKEST, (x - 4, y + 6, w + 8, 4)
    )
    pygame.draw.rect(
        surface, constants.COLOR_EMBER, (x - 4, y + 6, w + 8, 1)
    )
    # Tak-topprand (dyp oker som glede overgang mot himmel)
    pygame.draw.rect(
        surface, constants.COLOR_WOOD_DARK, (x - 2, y + 4, w + 4, 2)
    )

    # 5 arkade-buer (åpen arkade — buene er vei-inn til handelshuset)
    arch_count = 5
    arch_w = 16
    # Jevnt fordelt med marg
    margin = 12
    span = w - 2 * margin
    step = (span - arch_w) / (arch_count - 1)
    arch_xs = [x + margin + int(i * step) for i in range(arch_count)]
    for ax in arch_xs:
        arch_y = y + h - 30
        # Åpning (mørk)
        pygame.draw.rect(
            surface, constants.COLOR_STONE_DARKEST, (ax, arch_y, arch_w, 18)
        )
        # Buet topp (enkel halvsirkel-antydning via 3 steg)
        pygame.draw.rect(
            surface, constants.COLOR_STONE_DARKEST, (ax + 1, arch_y - 2, arch_w - 2, 2)
        )
        pygame.draw.rect(
            surface, constants.COLOR_STONE_DARKEST, (ax + 3, arch_y - 4, arch_w - 6, 2)
        )
        # Arkade-ramme (WOOD_MID)
        pygame.draw.rect(
            surface, constants.COLOR_WOOD_MID, (ax - 1, arch_y + 18, arch_w + 2, 1)
        )
        # Varm glimt inne i buen (LANTERN — antyder lantern-lys inne)
        pygame.draw.rect(
            surface, constants.COLOR_EMBER, (ax + 2, arch_y + 14, arch_w - 4, 1)
        )

    # Vekter-signatur (symbolsk vekt-symbol på sentralt felt) —
    # LANTERN (gyllen bronsevekt)
    balance_x = x + w // 2
    balance_y = y + 16
    # Vekt-stokk
    pygame.draw.rect(
        surface, constants.COLOR_LANTERN, (balance_x - 5, balance_y, 10, 1)
    )
    # Vekt-skåler (to prikker)
    pygame.draw.rect(
        surface, constants.COLOR_LANTERN_BRIGHT, (balance_x - 5, balance_y + 1, 3, 1)
    )
    pygame.draw.rect(
        surface, constants.COLOR_LANTERN_BRIGHT, (balance_x + 3, balance_y + 1, 3, 1)
    )
    # Vekt-henging (vertikal stokk)
    pygame.draw.rect(
        surface, constants.COLOR_LANTERN, (balance_x, balance_y - 3, 1, 3)
    )


def _bake_cathedral(
    surface: pygame.Surface,
    x: int, y: int, w: int, h: int,
    ground_top_y: int,
) -> None:
    """Havana: Katedral med to klokketårn — dominerende silhuett.

    Per FASE_2_5.md §2.3: "Mest imponerende bygning av alle 4 havner".
    Barokk fasade antydet ved kurvede taklinjer og sentral rose-
    åpning. To klokketårn i hver ende (bredere enn Port Royals
    enslige klokketårn — adresserer tetthets-observasjonen).

    Palett: WOOD_LIGHT-fasade (hvitkalket, sol-farget) med
    STONE_DARKEST-aksenter og LANTERN-glimt fra kirkevinduer.
    """
    # Hoveddel — bred, WOOD_LIGHT hvitkalket
    pygame.draw.rect(surface, constants.COLOR_WOOD_LIGHT, (x, y + 20, w, h - 20))
    # Skygge-aksent på høyre side (dybde-signal)
    pygame.draw.rect(
        surface, constants.COLOR_WOOD_MID, (x + w - 2, y + 20, 2, h - 20)
    )

    # To klokketårn — bredere enn Port Royal (30 px hver) for
    # proporsjonal balanse mot katedralens bredde
    tower_w = 30
    tower_h = h + 20
    left_tower_x = x
    right_tower_x = x + w - tower_w
    for tx in (left_tower_x, right_tower_x):
        top_y = y - 20
        # Tårn-kropp
        pygame.draw.rect(
            surface, constants.COLOR_WOOD_LIGHT,
            (tx, top_y, tower_w, tower_h),
        )
        # Skygge-kant høyre (dybde)
        pygame.draw.rect(
            surface, constants.COLOR_WOOD_MID,
            (tx + tower_w - 2, top_y, 2, tower_h),
        )
        # Horisontal etasje-skille
        for dy in (16, 36, 56):
            if dy < tower_h:
                pygame.draw.rect(
                    surface, constants.COLOR_WOOD_DARK,
                    (tx, top_y + dy, tower_w, 1),
                )
        # Klokke-åpning (øvre del)
        bell_x = tx + 6
        bell_y = top_y + 6
        bell_w, bell_h = tower_w - 12, 14
        pygame.draw.rect(
            surface, constants.COLOR_STONE_DARKEST,
            (bell_x, bell_y, bell_w, bell_h),
        )
        # Buet toppen av klokkeåpning (barokk)
        pygame.draw.rect(
            surface, constants.COLOR_STONE_DARKEST,
            (bell_x + 2, bell_y - 2, bell_w - 4, 2),
        )
        # Klokke (LANTERN — gyllen bronse)
        pygame.draw.rect(
            surface, constants.COLOR_LANTERN,
            (bell_x + 3, bell_y + 2, bell_w - 6, bell_h - 6),
        )
        # Klokke-høylys
        pygame.draw.rect(
            surface, constants.COLOR_LANTERN_BRIGHT,
            (bell_x + 4, bell_y + 3, bell_w - 8, 2),
        )
        # Barokk kuppel på toppen — trekant-antydning + kors
        dome_pts = [
            (tx - 1, top_y),
            (tx + tower_w + 1, top_y),
            (tx + tower_w // 2, top_y - 10),
        ]
        pygame.draw.polygon(surface, constants.COLOR_WOOD_DARKEST, dome_pts)
        # Kors
        cross_x = tx + tower_w // 2
        pygame.draw.rect(
            surface, constants.COLOR_LANTERN_BRIGHT,
            (cross_x - 1, top_y - 14, 2, 5),
        )
        pygame.draw.rect(
            surface, constants.COLOR_LANTERN_BRIGHT,
            (cross_x - 2, top_y - 12, 4, 1),
        )

    # Senteret (mellom tårnene): barokk taklinje
    center_x = x + tower_w
    center_w = w - 2 * tower_w
    # Buet takfront (2 buer på taktopp — barokk signatur)
    roof_y = y + 8
    pygame.draw.rect(
        surface, constants.COLOR_WOOD_DARKEST,
        (center_x, roof_y, center_w, 12),
    )
    # Midt-kule/topp (barokk ornament)
    cx = center_x + center_w // 2
    pygame.draw.rect(
        surface, constants.COLOR_WOOD_DARKEST,
        (cx - 6, roof_y - 6, 12, 6),
    )
    # Mini-kors på midten
    pygame.draw.rect(
        surface, constants.COLOR_LANTERN_BRIGHT,
        (cx - 1, roof_y - 12, 2, 6),
    )
    pygame.draw.rect(
        surface, constants.COLOR_LANTERN_BRIGHT,
        (cx - 2, roof_y - 10, 4, 1),
    )

    # Rose-vindu sentralt (sirkulær åpning)
    rose_y = y + 26
    rose_r = 8
    # Rammen
    pygame.draw.circle(
        surface, constants.COLOR_STONE_DARKEST, (cx, rose_y + rose_r), rose_r + 1
    )
    pygame.draw.circle(
        surface, constants.COLOR_LANTERN, (cx, rose_y + rose_r), rose_r - 1
    )
    # Sentrum-glimt
    pygame.draw.circle(
        surface, constants.COLOR_LANTERN_BRIGHT, (cx, rose_y + rose_r), 2
    )
    # Kors-ribber inne i rosen (4 linjer)
    pygame.draw.rect(
        surface, constants.COLOR_WOOD_DARK,
        (cx - rose_r + 1, rose_y + rose_r, rose_r * 2 - 2, 1),
    )
    pygame.draw.rect(
        surface, constants.COLOR_WOOD_DARK,
        (cx, rose_y + 1, 1, rose_r * 2 - 2),
    )

    # Hovedportal midt i senteret — stor bue
    portal_w, portal_h = 28, 44
    portal_x = cx - portal_w // 2
    portal_y = ground_top_y - portal_h
    pygame.draw.rect(
        surface, constants.COLOR_STONE_DARKEST,
        (portal_x, portal_y, portal_w, portal_h),
    )
    # Buet topp
    pygame.draw.rect(
        surface, constants.COLOR_STONE_DARKEST,
        (portal_x + 2, portal_y - 2, portal_w - 4, 2),
    )
    pygame.draw.rect(
        surface, constants.COLOR_STONE_DARKEST,
        (portal_x + 4, portal_y - 4, portal_w - 8, 2),
    )
    # Dør (åpen — varm glød fra inne)
    pygame.draw.rect(
        surface, constants.COLOR_EMBER,
        (portal_x + 3, portal_y + 3, portal_w - 6, portal_h - 6),
    )
    pygame.draw.rect(
        surface, constants.COLOR_FLAME,
        (portal_x + 6, portal_y + 8, portal_w - 12, portal_h - 14),
    )
    # Trapp
    pygame.draw.rect(
        surface, constants.COLOR_WOOD_MID,
        (portal_x - 6, ground_top_y, portal_w + 12, 3),
    )


def _bake_governor_palace(
    surface: pygame.Surface,
    x: int, y: int, w: int, h: int,
    ground_top_y: int,
) -> None:
    """Havana: Guvernørpalass — bredt med arkade langs fronten.

    Spansk kolonial-arkitektur. Arkade signal er sentralt (buene
    gjentas i handelshuset for visuell enhet). Palass er bredere
    enn handelshuset og har dekor-balkong midt på andre etasje.
    """
    # Hovedvegg — WOOD_LIGHT
    pygame.draw.rect(surface, constants.COLOR_WOOD_LIGHT, (x, y, w, h))
    # Skygge-base (nedre del)
    pygame.draw.rect(
        surface, constants.COLOR_WOOD_MID,
        (x, y + h - 10, w, 10),
    )
    # Tak-overheng (bred)
    pygame.draw.rect(
        surface, constants.COLOR_WOOD_DARKEST,
        (x - 5, y - 4, w + 10, 4),
    )
    pygame.draw.rect(
        surface, constants.COLOR_EMBER, (x - 5, y - 4, w + 10, 1)
    )

    # Arkade på gatenivå (4 buer)
    arch_count = 4
    arch_w = 18
    margin = 10
    span = w - 2 * margin
    step = (span - arch_w) / (arch_count - 1)
    for i in range(arch_count):
        ax = x + margin + int(i * step)
        arch_y = y + h - 28
        # Åpning (mørk)
        pygame.draw.rect(
            surface, constants.COLOR_STONE_DARKEST,
            (ax, arch_y, arch_w, 22),
        )
        # Buet topp
        pygame.draw.rect(
            surface, constants.COLOR_STONE_DARKEST,
            (ax + 1, arch_y - 2, arch_w - 2, 2),
        )
        pygame.draw.rect(
            surface, constants.COLOR_STONE_DARKEST,
            (ax + 3, arch_y - 4, arch_w - 6, 2),
        )
        # Ramme (søyle skygge-skille)
        pygame.draw.rect(
            surface, constants.COLOR_WOOD_MID,
            (ax - 1, arch_y, 1, 22),
        )
        pygame.draw.rect(
            surface, constants.COLOR_WOOD_MID,
            (ax + arch_w, arch_y, 1, 22),
        )
        # Varm glimt inne (lantern-lys)
        pygame.draw.rect(
            surface, constants.COLOR_EMBER,
            (ax + 2, arch_y + 18, arch_w - 4, 1),
        )

    # Andre etasje-vinduer (4 — over arkadene)
    for i in range(arch_count):
        ax = x + margin + int(i * step)
        win_y = y + 8
        win_w, win_h = arch_w - 4, 10
        wx0 = ax + 2
        pygame.draw.rect(
            surface, constants.COLOR_STONE_DARKEST,
            (wx0, win_y, win_w, win_h),
        )
        pygame.draw.rect(
            surface, constants.COLOR_LANTERN,
            (wx0 + 1, win_y + 1, win_w - 2, win_h - 2),
        )
        pygame.draw.rect(
            surface, constants.COLOR_LANTERN_BRIGHT,
            (wx0 + 2, win_y + 2, win_w - 4, win_h - 6),
        )

    # Sentral balkong (mellom midt-vinduene)
    balcony_x = x + w // 2 - 14
    balcony_y = y + 20
    # Rekkverk
    pygame.draw.rect(
        surface, constants.COLOR_STONE_DARKEST,
        (balcony_x, balcony_y, 28, 1),
    )
    # Balkong-plate
    pygame.draw.rect(
        surface, constants.COLOR_WOOD_DARK,
        (balcony_x - 2, balcony_y + 1, 32, 2),
    )
    # Balusterstenger
    for bx in range(balcony_x + 2, balcony_x + 28, 4):
        pygame.draw.rect(
            surface, constants.COLOR_STONE_DARKEST, (bx, balcony_y, 1, 2)
        )


#: Dispatch-tabell: port_id → bake-funksjon for exchange-bbox.
#: Tortuga bruker `_bake_exchange` (klassisk børshus).
#: Port Royal (C2.5-2) bruker `_bake_customs_house`.
#: Havana (C2.5-3) bruker `_bake_trade_house` (spansk arkade).
#: Nassau (C2.5-4) får `_bake_open_market` senere.
#: Default (ikke-matchet id) faller tilbake til `_bake_exchange`.
_EXCHANGE_BAKERS = {
    "tortuga": _bake_exchange,
    "port_royal": _bake_customs_house,
    "havana": _bake_trade_house,
}

#: Dispatch-tabell: signature_building.kind → bake-funksjon.
_SIGNATURE_BUILDING_BAKERS = {
    "church_tower": _bake_church_tower,
    "rum_warehouse": _bake_rum_warehouse,
    "cathedral": _bake_cathedral,
    "governor_palace": _bake_governor_palace,
}


def _bake_signature_buildings(
    surface: pygame.Surface,
    signature_buildings: tuple[SignatureBuilding, ...],
    ground_top_y: int,
) -> None:
    """Bake per-havn signatur-bygninger (klokketårn, rum-magasin, osv)
    inn i gameplay-surfacen.

    Rekkefølgen er deklarert rekkefølge i `ports.json`. Hvis to bygninger
    overlapper, vil den som er senere i listen tegnes over.
    """
    for sig in signature_buildings:
        baker = _SIGNATURE_BUILDING_BAKERS.get(sig.kind)
        if baker is None:
            raise ValueError(
                f"Ukjent signature_building.kind={sig.kind!r} "
                f"(gyldige: {sorted(_SIGNATURE_BUILDING_BAKERS.keys())})"
            )
        p = sig.placement
        baker(surface, p.x, p.y, p.w, p.h, ground_top_y)


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
    # Gategulv-tekstur kommer fra props hvis den finnes; ellers eksisterende
    # "wood_dark" (beholder backward-kompatibilitet for havner uten props).
    texture = b.props.ground_texture if b.props is not None else "wood_dark"
    _bake_ground(surf, b.ground_top_y, texture=texture)
    _bake_tavern(
        surf, b.tavern.x, b.tavern.y, b.tavern.w, b.tavern.h,
        b.ground_top_y,
    )
    # Exchange-bbox-bake-routing (C2.5-2): per-havn signatur-bygning
    # over samme bounding-boks. HUD og E-interaksjon er uendret; kun
    # visuelt utseende endres.
    exchange_baker = _EXCHANGE_BAKERS.get(port_config.id, _bake_exchange)
    exchange_baker(
        surf, b.exchange.x, b.exchange.y, b.exchange.w, b.exchange.h,
        b.ground_top_y,
    )
    # Havn-spesifikke signatur-bygninger utover tavern + exchange
    # (klokketårn, rum-magasin, katedral, etc).
    if b.signature_buildings:
        _bake_signature_buildings(surf, b.signature_buildings, b.ground_top_y)
    # Rekvisita bakes sist slik at gjerder og lanterne-stolper havner
    # øverst i gameplay-laget. NPC-silhuetter er runtime-entiteter
    # (tegnes over gameplay-laget av PortVillageRenderer).
    if b.props is not None:
        _bake_props(surf, b.props, b.ground_top_y)
    surf.set_colorkey(COLORKEY)
    return surf
