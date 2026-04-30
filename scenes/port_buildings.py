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
    Alley, FillBuilding, NatureElement, PortConfig, PortProps,
    SignatureBuilding,
)
from entities import fill_buildings as fill_buildings_module
from entities import nature as nature_module
from entities import port_props as props_module


#: Colorkey for transparente områder på gameplay-laget. Fortsatt i bruk
#: her (gameplay-lag som har store transparente regioner over bygningene);
#: IKKE brukt på fg-laget som beholder SRCALPHA per C3b-funn.
COLORKEY = (255, 0, 255)


# -----------------------------------------------------------------------------
# Dag/natt-hjelpefunksjoner (C2.5-8b)
#
# Hver bygnings-bake-funksjon som har tennbart lys tar en `night_lights: bool`-
# parameter. `_nl(night_lights, lit, dark)` returnerer `lit`-farge om natten,
# `dark`-farge om dagen. Dette gir to bygnings-varianter fra samme funksjon
# uten å duplisere strukturkoden.
# -----------------------------------------------------------------------------

def _nl(
    night_lights: bool,
    lit_color: tuple[int, int, int],
    dark_color: tuple[int, int, int],
) -> tuple[int, int, int]:
    """Velg lit_color ved natt, dark_color ved dag.

    Brukes for vindus-fyll, dør-glød, skilt-bakgrunn, alter-lys osv. —
    alle elementer som "tennes" om kvelden. Strukturelle elementer
    (vegger, tak, søyler, rammer, dør-åpnings-kanter) bruker samme
    farge i begge varianter og trenger ikke gå gjennom denne helperen.
    """
    return lit_color if night_lights else dark_color


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
    # Kister (Nassau) — kaotisk stablede.
    for stack in props.chest_stacks:
        props_module.bake_chest_stack(
            surface, stack.x, ground_top_y, stack.count,
        )
    # Bål (Nassau) — statisk i C2.5-4, palette-cycling i C2.5-6.
    # Tegnes før lanterner slik at lanterne-glimt kan overlappe.
    for fire in props.campfires:
        props_module.bake_campfire(surface, fire.x, ground_top_y)
    # Bambus-lanterne-stenger (Nassau — improviserte).
    for bl in props.bamboo_lanterns:
        props_module.bake_bamboo_lantern(surface, bl.x, ground_top_y)
    for lantern in props.lanterns:
        props_module.bake_lantern_post(surface, lantern.x, ground_top_y)


def _bake_tavern(
    surface: pygame.Surface,
    x: int, y: int, w: int, h: int,
    ground_top_y: int,
    night_lights: bool = True,
) -> None:
    """Tavernaen: varmt tre med 2 opplyste vinduer, dør med varm gulv-glød.

    `night_lights=True` (natt): vinduer har LANTERN-fyll, silhuetter
    inne, dør har FLAME-glød. `False` (dag): vinduer er mørke
    WOOD_DARKEST-rektangler, dør er WOOD_DARKEST-sprekke uten varme.
    """
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
    # Skorstein (Fase 2.6: ChimneySmoke-systemet sender opp røyk fra
    # akkurat denne posisjonen — eksakt match mot smoke-source x).
    chimney_x = x + w - 30
    chimney_top_y = y - 14
    pygame.draw.rect(
        surface, constants.COLOR_STONE_DARKEST,
        (chimney_x, chimney_top_y, 6, 8),
    )
    # Brun mursteins-aksent på toppen
    pygame.draw.rect(
        surface, constants.COLOR_WOOD_DARKEST,
        (chimney_x - 1, chimney_top_y, 8, 1),
    )

    # To opplyste vinduer (natt: bakt varm glød; dag: mørke rektangler)
    window_w, window_h = 24, 28
    window_y = y + 14
    for wi, wx in enumerate((x + 40, x + w - 40 - window_w)):
        # Vindus-fyll: LANTERN ved natt, WOOD_DARKEST ved dag
        pygame.draw.rect(
            surface,
            _nl(night_lights, constants.COLOR_LANTERN, constants.COLOR_WOOD_DARKEST),
            (wx, window_y, window_w, window_h),
        )
        pygame.draw.rect(
            surface,
            _nl(night_lights, constants.COLOR_LANTERN_BRIGHT, constants.COLOR_WOOD_DARK),
            (wx + 2, window_y + 2, window_w - 4, window_h - 4),
        )
        # Vindus-kors (alltid samme farge — strukturell)
        pygame.draw.rect(
            surface, constants.COLOR_WOOD_DARKEST,
            (wx + window_w // 2 - 1, window_y, 2, window_h),
        )
        pygame.draw.rect(
            surface, constants.COLOR_WOOD_DARKEST,
            (wx, window_y + window_h // 2 - 1, window_w, 2),
        )
        # Silhuett inne i vindu (KUN natt — livfullhet er et natt-fenomen;
        # om dagen er folk ute på jobb i havnen).
        if night_lights:
            if wi == 0:
                # Tricorn-hatt
                pygame.draw.rect(
                    surface, constants.COLOR_HAT,
                    (wx + 6, window_y + window_h // 2 + 4, 12, 3),
                )
                pygame.draw.rect(
                    surface, constants.COLOR_HAT,
                    (wx + 8, window_y + window_h // 2 + 2, 8, 3),
                )
            else:
                # Spillekort-rektangler (to stk på rad)
                pygame.draw.rect(
                    surface, constants.COLOR_SHIRT,
                    (wx + 6, window_y + window_h // 2 + 4, 4, 6),
                )
                pygame.draw.rect(
                    surface, constants.COLOR_SHIRT,
                    (wx + 14, window_y + window_h // 2 + 4, 4, 6),
                )
                pygame.draw.rect(
                    surface, constants.COLOR_EMBER,
                    (wx + 7, window_y + window_h // 2 + 5, 2, 1),
                )

    # Mose-patch på taket (C2.5-7 slitasje — Tortuga funksjonelt
    # forfall). STONE_LIT-antydning ved venstre side av taket.
    pygame.draw.rect(
        surface, constants.COLOR_STONE_LIT,
        (x + 12, y - 5, 6, 1),
    )
    pygame.draw.rect(
        surface, constants.COLOR_WOOD_MID,
        (x + 14, y - 4, 2, 1),
    )

    # Hengende skilt mellom vinduene (Fase 2.6 polish): jern-brakett
    # ut fra taket, kjede ned til selve skiltet, skiltet svinger ikke
    # men har varm tone som leder oeyet til doera.
    sign_w, sign_h = 52, 14
    sign_x = x + w // 2 - sign_w // 2
    bracket_y = y - 1
    bracket_w = sign_w + 6
    # Jern-brakett (horisontal stang under tak-overheng)
    pygame.draw.rect(
        surface, constants.COLOR_WOOD_DARKEST,
        (sign_x - 3, bracket_y, bracket_w, 1),
    )
    # Hengende kjeder (to vertikale stripper ned til skiltet)
    chain_top_y = bracket_y + 1
    chain_h = 3
    pygame.draw.rect(
        surface, constants.COLOR_WOOD_DARKEST,
        (sign_x + 4, chain_top_y, 1, chain_h),
    )
    pygame.draw.rect(
        surface, constants.COLOR_WOOD_DARKEST,
        (sign_x + sign_w - 5, chain_top_y, 1, chain_h),
    )
    # Selve skiltet — bredt, varmt tre med innskreven ramme
    sign_y = chain_top_y + chain_h
    pygame.draw.rect(
        surface, constants.COLOR_WOOD_DARKEST,
        (sign_x, sign_y, sign_w, sign_h),
    )
    pygame.draw.rect(
        surface, constants.COLOR_WOOD_LIGHT,
        (sign_x + 1, sign_y + 1, sign_w - 2, sign_h - 2),
    )
    pygame.draw.rect(
        surface, constants.COLOR_WOOD_MID,
        (sign_x + 2, sign_y + 2, sign_w - 4, sign_h - 4),
    )
    # "Krus"-ikon til venstre (lanterne-gull antydning)
    pygame.draw.rect(
        surface, constants.COLOR_LANTERN,
        (sign_x + 5, sign_y + 4, 6, 6),
    )
    pygame.draw.rect(
        surface, constants.COLOR_LANTERN_BRIGHT,
        (sign_x + 6, sign_y + 5, 4, 4),
    )
    # Tekst-stripper (ulesbare paa avstand, men antyder skrift)
    pygame.draw.rect(
        surface, constants.COLOR_WOOD_DARKEST,
        (sign_x + 14, sign_y + 5, 32, 1),
    )
    pygame.draw.rect(
        surface, constants.COLOR_WOOD_DARKEST,
        (sign_x + 14, sign_y + 8, 28, 1),
    )

    # Dør (natt: varm glød fra innsiden; dag: lukket, bare mørk åpning)
    door_w, door_h = 24, 36
    door_x = x + w // 2 - door_w // 2
    door_y = ground_top_y - door_h
    pygame.draw.rect(
        surface, constants.COLOR_WOOD_DARKEST, (door_x, door_y, door_w, door_h)
    )
    if night_lights:
        pygame.draw.rect(
            surface, constants.COLOR_FLAME,
            (door_x + 4, door_y + 8, door_w - 8, door_h - 8),
        )
        pygame.draw.rect(
            surface, constants.COLOR_LANTERN_BRIGHT,
            (door_x + 6, door_y + 10, door_w - 12, door_h - 14),
        )
        # Svak varm "teppe" av lys på gaten rett foran døren
        glow_rect = pygame.Rect(door_x - 8, ground_top_y, door_w + 16, 4)
        pygame.draw.rect(surface, constants.COLOR_EMBER, glow_rect)
    # (Dag: ingen glød, ingen gulv-teppe — stengt dør)


def _bake_exchange(
    surface: pygame.Surface,
    x: int, y: int, w: int, h: int,
    ground_top_y: int,
    night_lights: bool = True,
) -> None:
    """Børshuset: kald stein med 3 vinduer, 4 søyler og trekantgavl.

    `night_lights=True`: vinduer glitrer STONE_LIT/STONE_BRIGHT (kaldt
    institusjonelt lys). `False`: vinduer er STONE_DARKEST-sprekker.
    """
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
            surface,
            _nl(night_lights, constants.COLOR_STONE_LIT, constants.COLOR_STONE_DARKEST),
            (wx0, window_y, window_w, window_h),
        )
        pygame.draw.rect(
            surface,
            _nl(night_lights, constants.COLOR_STONE_BRIGHT, constants.COLOR_STONE_DARK),
            (wx0 + 2, window_y + 2, window_w - 4, window_h - 4),
        )
        pygame.draw.rect(
            surface, constants.COLOR_STONE_DARK,
            (wx0 + window_w // 2 - 1, window_y, 2, window_h),
        )

    # Stor dør (midtstilt) med dobbelt-fløy + håndtak (Fase 2.6 polish).
    door_w, door_h = 26, 40
    door_x = x + w // 2 - door_w // 2
    door_y = ground_top_y - door_h
    pygame.draw.rect(surface, constants.COLOR_STONE_DARKEST, (door_x, door_y, door_w, door_h))
    pygame.draw.rect(surface, constants.COLOR_STONE_MID, (door_x + 3, door_y + 3, door_w - 6, door_h - 6))
    # Vertikal midt-skille som markerer dobbelt-fløy
    pygame.draw.rect(
        surface, constants.COLOR_STONE_DARKEST,
        (door_x + door_w // 2 - 1, door_y + 3, 2, door_h - 6),
    )
    # Håndtak (sølv, ett på hver fløy)
    pygame.draw.rect(
        surface, constants.COLOR_STONE_BRIGHT,
        (door_x + door_w // 2 - 5, door_y + door_h // 2, 1, 2),
    )
    pygame.draw.rect(
        surface, constants.COLOR_STONE_BRIGHT,
        (door_x + door_w // 2 + 4, door_y + door_h // 2, 1, 2),
    )
    # Trapp opp til døra (3 trinn, smal-bred-bredere) — autoritær approach
    step_y = ground_top_y
    pygame.draw.rect(
        surface, constants.COLOR_STONE_MID,
        (door_x - 4, step_y, door_w + 8, 1),
    )
    pygame.draw.rect(
        surface, constants.COLOR_STONE_DARK,
        (door_x - 8, step_y + 1, door_w + 16, 1),
    )
    pygame.draw.rect(
        surface, constants.COLOR_STONE_DARKEST,
        (door_x - 12, step_y + 2, door_w + 24, 1),
    )
    # Klokke i gavl (kald STONE_LIT urskiver med STONE_BRIGHT-ramme).
    # Sentrert på pediment-toppen rett under apex.
    clock_cx = x + w // 2
    clock_cy = y - 1   # litt ned fra apex
    clock_r = 5
    pygame.draw.circle(surface, constants.COLOR_STONE_BRIGHT, (clock_cx, clock_cy), clock_r)
    pygame.draw.circle(surface, constants.COLOR_STONE_DARK, (clock_cx, clock_cy), clock_r - 2)
    # Klokke-visere (12 og 3)
    pygame.draw.rect(surface, constants.COLOR_STONE_BRIGHT,
                     (clock_cx, clock_cy - 2, 1, 2))  # tim-viser opp
    pygame.draw.rect(surface, constants.COLOR_STONE_BRIGHT,
                     (clock_cx, clock_cy, 3, 1))      # min-viser høyre
    # Svak kald "spill-over"-glød på trapp — kun ved natt
    if night_lights:
        pygame.draw.rect(
            surface, constants.COLOR_STONE_LIGHT,
            (door_x - 4, ground_top_y - 1, door_w + 8, 1),
        )


def _bake_customs_house(
    surface: pygame.Surface,
    x: int, y: int, w: int, h: int,
    ground_top_y: int,
    night_lights: bool = True,
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
    # C2.5-7 slitasje — flassende hvitkalk: STONE_DARK-flekker der
    # STONE_MID har falt av. "Pompøs nedslitthet" per Port Royal-
    # karakter. Deterministiske posisjoner (ikke randomisert).
    for fx_off, fy_off, fw in (
        (20, 18, 8),
        (60, 32, 6),
        (110, 22, 10),
        (w - 50, 40, 7),
        (w - 90, 20, 5),
    ):
        pygame.draw.rect(
            surface, constants.COLOR_STONE_DARK,
            (x + fx_off, y + fy_off, fw, 2),
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

    # Mellom-søyle-vinduer: 2 kalde vinduer (tennes om natten)
    window_w, window_h = 14, 22
    window_y = y + 32
    window_gap_indexes = [(1, 2), (3, 4)]
    for a, b in window_gap_indexes:
        mid_x = (col_xs[a] + col_xs[b]) // 2 + col_w // 2
        wx0 = mid_x - window_w // 2
        pygame.draw.rect(
            surface,
            _nl(night_lights, constants.COLOR_STONE_LIT, constants.COLOR_STONE_DARKEST),
            (wx0, window_y, window_w, window_h),
        )
        pygame.draw.rect(
            surface,
            _nl(night_lights, constants.COLOR_STONE_BRIGHT, constants.COLOR_STONE_DARK),
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
    # Sølv-haandtak paa hver flоy (Fase 2.6 polish — match Tortuga)
    pygame.draw.rect(
        surface, constants.COLOR_STONE_BRIGHT,
        (door_x + door_w // 2 - 6, door_y + door_h // 2, 1, 2),
    )
    pygame.draw.rect(
        surface, constants.COLOR_STONE_BRIGHT,
        (door_x + door_w // 2 + 5, door_y + door_h // 2, 1, 2),
    )
    # 3-trinns trapp (smal->bred->bredere — kolonial autoritet)
    step_y = ground_top_y
    pygame.draw.rect(
        surface, constants.COLOR_STONE_BRIGHT,
        (door_x - 6, step_y, door_w + 12, 1),
    )
    pygame.draw.rect(
        surface, constants.COLOR_STONE_LIGHT,
        (door_x - 10, step_y + 1, door_w + 20, 1),
    )
    pygame.draw.rect(
        surface, constants.COLOR_STONE_MID,
        (door_x - 14, step_y + 2, door_w + 28, 1),
    )


def _bake_church_tower(
    surface: pygame.Surface,
    x: int, y: int, w: int, h: int,
    ground_top_y: int,
    night_lights: bool = True,
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
    # Ramme (strukturelt)
    pygame.draw.rect(
        surface, constants.COLOR_STONE_DARKEST, (win_x, win_y, win_w, win_h)
    )
    # Lys i glasset (tennbart)
    pygame.draw.rect(
        surface,
        _nl(night_lights, constants.COLOR_STONE_LIT, constants.COLOR_STONE_DARK),
        (win_x + 1, win_y + 1, win_w - 2, win_h - 2),
    )
    if night_lights:
        # Alter-lys-glimt (bare om natten)
        pygame.draw.rect(
            surface, constants.COLOR_LANTERN,
            (win_x + win_w // 2 - 1, win_y + win_h // 2, 2, 2),
        )


def _bake_rum_warehouse(
    surface: pygame.Surface,
    x: int, y: int, w: int, h: int,
    ground_top_y: int,
    night_lights: bool = True,
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
        # EMBER-glimt ved port (antyder lantern-lys inne) — kun om natten
        if night_lights:
            pygame.draw.rect(
                surface, constants.COLOR_EMBER,
                (px + 2, py + port_h - 4, port_w - 4, 1),
            )


def _bake_trade_house(
    surface: pygame.Surface,
    x: int, y: int, w: int, h: int,
    ground_top_y: int,
    night_lights: bool = True,
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
        # Varm glimt inne i buen — kun om natten
        if night_lights:
            pygame.draw.rect(
                surface, constants.COLOR_EMBER,
                (ax + 2, arch_y + 14, arch_w - 4, 1),
            )

    # Vekter-signatur (symbolsk vekt-symbol på sentralt felt) —
    # LANTERN (gyllen bronsevekt) — metall-ornament, synlig dag og natt
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
    night_lights: bool = True,
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
        # Klokke (LANTERN bronse — metall-ornament, synlig dag og natt)
        pygame.draw.rect(
            surface, constants.COLOR_LANTERN,
            (bell_x + 3, bell_y + 2, bell_w - 6, bell_h - 6),
        )
        # Klokke-høylys (metall-refleks, behold dag)
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
    # Rose-vindu glass: tennbart. Om natten glød-LANTERN og mosaikk-
    # farger. Om dagen: STONE_DARK-fyll (dempet glass mot mørke).
    pygame.draw.circle(
        surface,
        _nl(night_lights, constants.COLOR_LANTERN, constants.COLOR_STONE_DARK),
        (cx, rose_y + rose_r), rose_r - 1,
    )
    if night_lights:
        # Glass-mosaikk-antydning (katolsk varme via farget glass)
        mosaic_cy = rose_y + rose_r
        pygame.draw.rect(
            surface, constants.COLOR_EMBER, (cx - 4, mosaic_cy - 2, 2, 2)
        )
        pygame.draw.rect(
            surface, constants.COLOR_FLAME, (cx + 2, mosaic_cy - 3, 2, 2)
        )
        pygame.draw.rect(
            surface, constants.COLOR_SHIRT, (cx - 3, mosaic_cy + 1, 2, 2)
        )
        pygame.draw.rect(
            surface, constants.COLOR_STONE_LIT, (cx + 1, mosaic_cy + 2, 2, 2)
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
    # Dør (natt: varm glød fra inne; dag: mørk bue med kun antydning)
    if night_lights:
        pygame.draw.rect(
            surface, constants.COLOR_EMBER,
            (portal_x + 3, portal_y + 3, portal_w - 6, portal_h - 6),
        )
        pygame.draw.rect(
            surface, constants.COLOR_FLAME,
            (portal_x + 6, portal_y + 8, portal_w - 12, portal_h - 14),
        )
    else:
        pygame.draw.rect(
            surface, constants.COLOR_STONE_DARK,
            (portal_x + 3, portal_y + 3, portal_w - 6, portal_h - 6),
        )
    # Trapp (strukturelt)
    pygame.draw.rect(
        surface, constants.COLOR_WOOD_MID,
        (portal_x - 6, ground_top_y, portal_w + 12, 3),
    )


def _bake_governor_palace(
    surface: pygame.Surface,
    x: int, y: int, w: int, h: int,
    ground_top_y: int,
    night_lights: bool = True,
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
        # Varm glimt inne (lantern-lys) — kun natt
        if night_lights:
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
            surface,
            _nl(night_lights, constants.COLOR_LANTERN, constants.COLOR_STONE_DARK),
            (wx0 + 1, win_y + 1, win_w - 2, win_h - 2),
        )
        if night_lights:
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


def _bake_open_market(
    surface: pygame.Surface,
    x: int, y: int, w: int, h: int,
    ground_top_y: int,
    night_lights: bool = True,
) -> None:
    """Nassau: åpen markedsplass — erstatter børs-BYGNING med en
    rekvisita-cluster.

    Per FASE_2_5.md §2.4: "INGEN bygning ... Teltduker, vekter på
    bord, kister og bytte-stabler". Fraværet av vegger er designet.

    Element-plassering i bbox (200x92 for Nassau):
    - 3 tent-kledde bord fordelt over bredden
    - En stor vekt-stokk (LANTERN) sentralt
    - Kaotisk plasserte tønner/kister ved fot
    - Presenning i forgrunn for "tak"-antydning men IKKE vegger
    """
    # Ingen vegg! Kun base-linje av presenning-duker som antyder
    # "her er handels-senteret" uten å være en bygning.

    # 3 bord-silhuetter fordelt jevnt
    bord_count = 3
    bord_w = 32
    margin = 16
    span = w - 2 * margin
    step = (span - bord_w) / (bord_count - 1) if bord_count > 1 else 0
    for i in range(bord_count):
        bx = x + margin + int(i * step)
        by = ground_top_y - 18
        # Bord-plate (WOOD_MID, flat)
        pygame.draw.rect(
            surface, constants.COLOR_WOOD_MID, (bx, by, bord_w, 3)
        )
        pygame.draw.rect(
            surface, constants.COLOR_WOOD_DARK, (bx, by + 2, bord_w, 1)
        )
        # Bein (2 stk)
        pygame.draw.rect(
            surface, constants.COLOR_WOOD_DARKEST,
            (bx + 3, by + 3, 2, 15),
        )
        pygame.draw.rect(
            surface, constants.COLOR_WOOD_DARKEST,
            (bx + bord_w - 5, by + 3, 2, 15),
        )
        # Skrå støtte-stenger
        pygame.draw.rect(
            surface, constants.COLOR_WOOD_DARK,
            (bx + bord_w // 2 - 1, by + 4, 2, 8),
        )

        # Presenning-tak over bordet (varierer i vinkel per bord for kaos)
        canopy_h = 6
        canopy_y = by - canopy_h - 2
        # Skeivt presenning — varierer per i
        lean = (-1) ** i * 2
        pygame.draw.rect(
            surface, constants.COLOR_WOOD_DARK,
            (bx - 2 + lean, canopy_y, bord_w + 4, canopy_h),
        )
        # Høylys-linje på toppen (WOOD_MID)
        pygame.draw.rect(
            surface, constants.COLOR_WOOD_MID,
            (bx - 2 + lean, canopy_y, bord_w + 4, 1),
        )
        # Presenning-kanter henger ned
        pygame.draw.rect(
            surface, constants.COLOR_WOOD_DARKEST,
            (bx - 2 + lean, canopy_y + canopy_h, 2, 3),
        )
        pygame.draw.rect(
            surface, constants.COLOR_WOOD_DARKEST,
            (bx + bord_w + lean, canopy_y + canopy_h, 2, 3),
        )
        # Stenger som holder presenning opp
        pygame.draw.rect(
            surface, constants.COLOR_WOOD_DARKEST,
            (bx, canopy_y + canopy_h, 1, by - (canopy_y + canopy_h)),
        )
        pygame.draw.rect(
            surface, constants.COLOR_WOOD_DARKEST,
            (bx + bord_w - 1, canopy_y + canopy_h, 1,
             by - (canopy_y + canopy_h)),
        )

    # Sentral vekt-stokk på midterste bord (LANTERN — gylden bronse)
    mid_bord_x = x + margin + int(1 * step)
    by_mid = ground_top_y - 18
    bal_x = mid_bord_x + bord_w // 2
    pygame.draw.rect(
        surface, constants.COLOR_LANTERN,
        (bal_x - 6, by_mid - 4, 12, 1),
    )
    # Vertikal henger
    pygame.draw.rect(
        surface, constants.COLOR_LANTERN,
        (bal_x, by_mid - 7, 1, 3),
    )
    # To skåler
    pygame.draw.rect(
        surface, constants.COLOR_LANTERN_BRIGHT,
        (bal_x - 6, by_mid - 3, 3, 1),
    )
    pygame.draw.rect(
        surface, constants.COLOR_LANTERN_BRIGHT,
        (bal_x + 4, by_mid - 3, 3, 1),
    )
    # "Vare" oppå et av bordene (venstre bord) — antyder kiste/pose
    left_bord_x = x + margin
    pygame.draw.rect(
        surface, constants.COLOR_WOOD_DARK,
        (left_bord_x + 4, by_mid - 5, 8, 5),
    )
    pygame.draw.rect(
        surface, constants.COLOR_LANTERN,
        (left_bord_x + 7, by_mid - 3, 2, 1),
    )
    # "Vare" på høyre bord — antyder tobakkspakker
    right_bord_x = x + margin + int(2 * step)
    pygame.draw.rect(
        surface, constants.COLOR_WOOD_MID,
        (right_bord_x + 6, by_mid - 4, 10, 4),
    )
    pygame.draw.rect(
        surface, constants.COLOR_WOOD_DARKEST,
        (right_bord_x + 6, by_mid - 4, 10, 1),
    )


def _bake_teachs_house(
    surface: pygame.Surface,
    x: int, y: int, w: int, h: int,
    ground_top_y: int,
    night_lights: bool = True,
) -> None:
    """Nassau: Teach's hus — romslig trehus, lappverk-arkitektur.

    Per FASE_2_5.md §2.4: "IKKE monumentalt — pirat-demokrati,
    ikke konge. Lappverk-arkitektur: rest-tre fra skipsvrak".

    Designvalg:
    - Forskjellige planke-bredder (antyder skipsvrak-rest)
    - Skeive vinduer (ikke rettvinklet)
    - Seil som tak-trekk (skip-rest)
    - Ingen pediment/klassisk form
    - Dør er bare en åpning, ingen formell portal
    """
    # Vegg — WOOD_MID base
    pygame.draw.rect(surface, constants.COLOR_WOOD_MID, (x, y, w, h))
    # Lappverk-planker: variable bredder
    plank_widths = [8, 12, 6, 10, 9, 11, 7, 10, 8, 13, 5, 12]
    plank_x = x
    for pw in plank_widths:
        if plank_x + pw > x + w:
            pw = x + w - plank_x
            if pw <= 0:
                break
        # Alternere litt mellom WOOD_DARK og WOOD_MID for variasjon
        color = (constants.COLOR_WOOD_DARK if (plank_x // 7) % 2 == 0
                 else constants.COLOR_WOOD_MID)
        pygame.draw.rect(surface, color, (plank_x, y, pw, 1))
        # Mellom-fuge
        pygame.draw.rect(
            surface, constants.COLOR_WOOD_DARKEST,
            (plank_x + pw - 1, y, 1, h),
        )
        plank_x += pw
    # Horisontale planker (skipsrest-plattform) — WOOD_DARK med variasjoner
    for dy in (14, 28, 42):
        if dy >= h:
            break
        pygame.draw.rect(
            surface, constants.COLOR_WOOD_DARKEST, (x, y + dy, w, 1)
        )

    # Skeive vinduer — to stk, forskyvet i høyde (C2.5-7 flimrende kaos)
    # Natt: ulike fargepalletter per vindu. Dag: alle vinduer mørke
    # WOOD_DARKEST (Teach er ikke hjemme, aktiviteten er på sjøen).
    win_w, win_h = 16, 12
    # Venstre vindu (litt høyere) — LANTERN gul ved natt
    left_wx = x + 14
    left_wy = y + 10
    pygame.draw.rect(
        surface, constants.COLOR_WOOD_DARKEST,
        (left_wx, left_wy, win_w, win_h),
    )
    pygame.draw.rect(
        surface,
        _nl(night_lights, constants.COLOR_LANTERN, constants.COLOR_WOOD_DARK),
        (left_wx + 1, left_wy + 1, win_w - 2, win_h - 2),
    )
    if night_lights:
        pygame.draw.rect(
            surface, constants.COLOR_LANTERN_BRIGHT,
            (left_wx + 2, left_wy + 2, win_w - 4, 3),
        )
    pygame.draw.rect(
        surface, constants.COLOR_WOOD_DARKEST,
        (left_wx + win_w // 2 - 1, left_wy, 2, win_h),
    )

    # Høyre vindu — EMBER rød-tonet ved natt
    right_wx = x + w - 14 - win_w
    right_wy = y + 14
    pygame.draw.rect(
        surface, constants.COLOR_WOOD_DARKEST,
        (right_wx, right_wy, win_w, win_h),
    )
    pygame.draw.rect(
        surface,
        _nl(night_lights, constants.COLOR_EMBER, constants.COLOR_WOOD_DARK),
        (right_wx + 1, right_wy + 1, win_w - 2, win_h - 2),
    )
    if night_lights:
        pygame.draw.rect(
            surface, constants.COLOR_FLAME,
            (right_wx + 2, right_wy + 2, win_w - 4, 3),
        )
    pygame.draw.rect(
        surface, constants.COLOR_WOOD_DARKEST,
        (right_wx + win_w // 2 - 1, right_wy, 2, win_h),
    )

    # Lite tredje vindu — FLAME orange ved natt
    mid_wx = x + w // 2 - 3
    mid_wy = y + 24
    pygame.draw.rect(
        surface, constants.COLOR_WOOD_DARKEST,
        (mid_wx, mid_wy, 6, 6),
    )
    if night_lights:
        pygame.draw.rect(
            surface, constants.COLOR_FLAME,
            (mid_wx + 1, mid_wy + 1, 4, 4),
        )
        pygame.draw.rect(
            surface, constants.COLOR_LANTERN,
            (mid_wx + 2, mid_wy + 2, 2, 1),
        )

    # C2.5-7 slitasje — "tre som vokser mellom planker":
    # MOSS_DAMP-lapper (STONE_LIT-antydning) på lappverks-strukturen
    pygame.draw.rect(
        surface, constants.COLOR_STONE_LIT, (x + 50, y + 40, 3, 1)
    )
    pygame.draw.rect(
        surface, constants.COLOR_WOOD_MID, (x + 50, y + 41, 3, 1)
    )
    pygame.draw.rect(
        surface, constants.COLOR_STONE_LIT, (x + w - 30, y + 50, 4, 1)
    )

    # Tak-trekk: seilstoff (SHIRT lys-farge — antyder skipsseil)
    sail_y = y - 5
    # Seilduk er skeiv — tre trekantete rektangler
    pygame.draw.rect(
        surface, constants.COLOR_SHIRT, (x - 4, sail_y, w + 8, 5)
    )
    # Seilets reer (mørk kant — STONE_DARK ligner tau)
    pygame.draw.rect(
        surface, constants.COLOR_STONE_DARK, (x - 4, sail_y, w + 8, 1)
    )
    pygame.draw.rect(
        surface, constants.COLOR_STONE_DARK, (x - 4, sail_y + 4, w + 8, 1)
    )
    # Seilbue antydet via 3 mørke prikker (hengepunkter)
    for dx in (16, w // 2, w - 16):
        pygame.draw.rect(
            surface, constants.COLOR_WOOD_DARK, (x + dx, sail_y + 1, 1, 3)
        )
    # Mast-stolpe midt på taket
    mast_x = x + w // 2
    pygame.draw.rect(
        surface, constants.COLOR_WOOD_DARKEST, (mast_x - 1, sail_y - 10, 2, 10)
    )
    # Liten improvisert flagg på masten (EMBER — "piratleder her")
    pygame.draw.rect(
        surface, constants.COLOR_EMBER, (mast_x + 1, sail_y - 10, 5, 3)
    )
    pygame.draw.rect(
        surface, constants.COLOR_STONE_DARKEST, (mast_x + 1, sail_y - 10, 5, 1)
    )

    # Dør (bare åpning, ingen portal-stil)
    door_w, door_h = 18, 28
    door_x = x + w // 2 - door_w // 2 - 6  # Litt off-center (pirat-demokrati)
    door_y = ground_top_y - door_h
    pygame.draw.rect(
        surface, constants.COLOR_STONE_DARKEST,
        (door_x, door_y, door_w, door_h),
    )
    # Varm innvendig glød — kun natt
    if night_lights:
        pygame.draw.rect(
            surface, constants.COLOR_EMBER,
            (door_x + 2, door_y + 2, door_w - 4, door_h - 4),
        )
        pygame.draw.rect(
            surface, constants.COLOR_LANTERN,
            (door_x + 4, door_y + 4, door_w - 8, door_h - 8),
        )


def _bake_shipyard(
    surface: pygame.Surface,
    x: int, y: int, w: int, h: int,
    ground_top_y: int,
    night_lights: bool = True,
) -> None:
    """Nassau: skipsverft i det fri.

    Per FASE_2_5.md §2.4: "Halvferdige skipsskrog på stranden.
    Stablede skipsplanker, rep-ruller. Dette er Nassaus
    produksjons-lokalitet".

    Ingen vegger — bare en åpen arbeidsplass med:
    - 2 halvferdige skrog (forskjellig stadium)
    - Stablede planker
    - En kraftig mast-støtte (skrog-byggende rigg)
    """
    # Ingen vegger — verftet er åpent.
    # Stor skrog-silhuett (WOOD_MID) — øvre halvdel er ferdig, nedre
    # mangler bunn-planker (viser nedre stativ)
    hull1_x = x
    hull1_w = w * 2 // 3
    hull1_base_y = ground_top_y - 4
    # Skroget som en bøyd "kikkert"-form (bueformet over stativ)
    # Øvre hvelv — WOOD_LIGHT (utsatt sol-del)
    pygame.draw.rect(
        surface, constants.COLOR_WOOD_LIGHT,
        (hull1_x + 4, hull1_base_y - 18, hull1_w - 8, 12),
    )
    # Nedre (mangler — plankene går ikke helt sammen)
    pygame.draw.rect(
        surface, constants.COLOR_WOOD_MID,
        (hull1_x + 2, hull1_base_y - 10, hull1_w - 4, 6),
    )
    # Skyggelinjer (planker)
    for dy in (0, 4, 8):
        pygame.draw.rect(
            surface, constants.COLOR_WOOD_DARKEST,
            (hull1_x + 4, hull1_base_y - 18 + dy, hull1_w - 8, 1),
        )
    # Kjøl — spisst mot bak
    pygame.draw.rect(
        surface, constants.COLOR_WOOD_DARK,
        (hull1_x + hull1_w // 3, hull1_base_y - 4, hull1_w // 3, 2),
    )
    # Stativ (kryss-støtter)
    for sx in (hull1_x + 6, hull1_x + hull1_w // 2, hull1_x + hull1_w - 6):
        pygame.draw.rect(
            surface, constants.COLOR_WOOD_DARKEST,
            (sx, hull1_base_y - 4, 2, 4),
        )
    # Mast-stilas (høyt kryss)
    mast_x = hull1_x + hull1_w // 2
    pygame.draw.rect(
        surface, constants.COLOR_WOOD_DARKEST,
        (mast_x - 1, hull1_base_y - 42, 2, 28),
    )
    # Horisontalt stag
    pygame.draw.rect(
        surface, constants.COLOR_WOOD_DARKEST,
        (mast_x - 10, hull1_base_y - 30, 20, 1),
    )
    # Tau-ruller på stativet
    pygame.draw.rect(
        surface, constants.COLOR_WOOD_LIGHT,
        (mast_x - 8, hull1_base_y - 32, 3, 2),
    )

    # Stablede planker til høyre for skroget
    plank_x = x + hull1_w + 8
    plank_w = w - hull1_w - 12
    plank_base_y = ground_top_y - 8
    for i in range(4):
        py = plank_base_y - i * 2
        # Alternerende WOOD_MID / WOOD_DARK for plank-lag
        color = (constants.COLOR_WOOD_LIGHT if i % 2 == 0
                 else constants.COLOR_WOOD_MID)
        pygame.draw.rect(
            surface, color, (plank_x, py, plank_w, 2),
        )
        pygame.draw.rect(
            surface, constants.COLOR_WOOD_DARKEST,
            (plank_x, py, plank_w, 1),
        )

    # En liten rep-rulle på toppen
    rope_x = plank_x + plank_w // 2
    rope_y = plank_base_y - 10
    pygame.draw.rect(
        surface, constants.COLOR_WOOD_LIGHT, (rope_x - 3, rope_y, 6, 4)
    )
    pygame.draw.rect(
        surface, constants.COLOR_WOOD_DARK, (rope_x - 3, rope_y, 6, 1)
    )
    # Rull-sentrum
    pygame.draw.rect(
        surface, constants.COLOR_WOOD_DARKEST, (rope_x - 1, rope_y + 1, 2, 2)
    )


#: Dispatch-tabell: port_id → bake-funksjon for exchange-bbox.
#: Tortuga bruker `_bake_exchange` (klassisk børshus).
#: Port Royal (C2.5-2) bruker `_bake_customs_house`.
#: Havana (C2.5-3) bruker `_bake_trade_house` (spansk arkade).
#: Nassau (C2.5-4) bruker `_bake_open_market` — INGEN bygning,
#: bare rekvisita (tematisk: pirat-republikk har ingen institusjonell
#: handel).
#: Default (ikke-matchet id) faller tilbake til `_bake_exchange`.
_EXCHANGE_BAKERS = {
    "tortuga": _bake_exchange,
    "port_royal": _bake_customs_house,
    "havana": _bake_trade_house,
    "nassau": _bake_open_market,
}

#: Dispatch-tabell: signature_building.kind → bake-funksjon.
_SIGNATURE_BUILDING_BAKERS = {
    "church_tower": _bake_church_tower,
    "rum_warehouse": _bake_rum_warehouse,
    "cathedral": _bake_cathedral,
    "governor_palace": _bake_governor_palace,
    "teachs_house": _bake_teachs_house,
    "shipyard": _bake_shipyard,
}


def _bake_alley_contents(
    surface: pygame.Surface,
    alleys: tuple[Alley, ...],
    ground_top_y: int,
) -> None:
    """Bake smug-innhold (C2.5-7).

    Rekvisita/natur i midten av smug per havn-karakter:
    - ropes: WOOD_LIGHT tau-sirkel (Tortuga)
    - barrels: liten tønne (Tortuga)
    - weeds: ugress-lapp (Port Royal)
    - flower_pot: blomster-potte (Havana)
    - palm: liten palme (Nassau)
    - sand_drift: sand-haug (Nassau)
    """
    for alley in alleys:
        if alley.contents is None:
            continue
        cx = alley.x + alley.w // 2
        if alley.contents == "ropes":
            # Tau-sirkel: WOOD_LIGHT på bakken
            pygame.draw.rect(
                surface, constants.COLOR_WOOD_LIGHT,
                (cx - 3, ground_top_y - 3, 6, 3),
            )
            pygame.draw.rect(
                surface, constants.COLOR_WOOD_DARKEST,
                (cx - 3, ground_top_y - 3, 6, 1),
            )
            pygame.draw.rect(
                surface, constants.COLOR_WOOD_DARK, (cx - 1, ground_top_y - 2, 2, 1)
            )
        elif alley.contents == "barrels":
            # Én liten tønne
            props_module.bake_barrel_stack(surface, cx - 5, ground_top_y, count=1)
        elif alley.contents == "weeds":
            nature_module.bake_weeds(surface, cx - 4, ground_top_y)
        elif alley.contents == "flower_pot":
            # Potte + EMBER-blomster
            pot_y = ground_top_y - 5
            pygame.draw.rect(
                surface, constants.COLOR_WOOD_LIGHT, (cx - 3, pot_y, 6, 4)
            )
            pygame.draw.rect(
                surface, constants.COLOR_WOOD_DARKEST, (cx - 3, pot_y, 6, 1)
            )
            # Blomster
            for dx, color in (
                (-2, constants.COLOR_EMBER),
                (0, constants.COLOR_LANTERN_BRIGHT),
                (2, constants.COLOR_EMBER),
            ):
                pygame.draw.rect(
                    surface, color, (cx + dx, pot_y - 2, 1, 2),
                )
        elif alley.contents == "palm":
            nature_module.bake_palm(surface, cx, ground_top_y, height=28, crown_spread=8)
        elif alley.contents == "sand_drift":
            nature_module.bake_sand_drift(surface, cx - 8, ground_top_y, width=16)


def _bake_nature_elements(
    surface: pygame.Surface,
    nature_elements: tuple[NatureElement, ...],
    ground_top_y: int,
) -> None:
    """Bake natur-elementer (palmer, fugler, blomster, ugress).

    C2.5-7 livfullhet. Tegnes sist i pipelinen (etter signatur-
    bygninger) slik at fugler på tak/mast og blomster på balkonger
    havner over bygnings-silhuettene.
    """
    for ne in nature_elements:
        nature_module.bake_nature_element(
            surface, ne.kind, ne.x, ne.y, ground_top_y,
        )


def _bake_fill_buildings(
    surface: pygame.Surface,
    fill_buildings: tuple[FillBuilding, ...],
    ground_top_y: int,
    night_lights: bool = True,
) -> None:
    """Bake per-havn fyll-bygninger (C2.5-6a/6b).

    `night_lights` (C2.5-8b) propageres til hver bygning slik at
    vindus-lys/dør-glød tennes kun om natten.
    """
    for fb in fill_buildings:
        fill_buildings_module.bake_fill_building(
            surface, fb.kind, fb.x, fb.w, fb.h,
            ground_top_y, fb.style_variant, night_lights,
        )


def _bake_signature_buildings(
    surface: pygame.Surface,
    signature_buildings: tuple[SignatureBuilding, ...],
    ground_top_y: int,
    night_lights: bool = True,
) -> None:
    """Bake per-havn signatur-bygninger med dag/natt-lys-gating."""
    for sig in signature_buildings:
        baker = _SIGNATURE_BUILDING_BAKERS.get(sig.kind)
        if baker is None:
            raise ValueError(
                f"Ukjent signature_building.kind={sig.kind!r} "
                f"(gyldige: {sorted(_SIGNATURE_BUILDING_BAKERS.keys())})"
            )
        p = sig.placement
        baker(surface, p.x, p.y, p.w, p.h, ground_top_y, night_lights)


def _bake_single_gameplay_layer(
    port_config: PortConfig,
    night_lights: bool,
) -> pygame.Surface:
    """Bygger én gameplay-surface for oppgitt lys-state.

    `night_lights=True`: alle lys tennes (natt-variant).
    `night_lights=False`: bygnings-vinduer, dører og skilt er dempet
    (dag-variant — mørke rektangler i stedet for LANTERN/FLAME-glød).
    Strukturelle elementer (vegger, tak, fasader), smug-innhold,
    natur-elementer og props er identiske i begge varianter.

    Permanente lys (Tortuga smed-esse, Nassau-bål, katedralens alter
    via dekorative varme mosaikk-rammer, metall-ornamenter som klokker
    og kors) lyser 24/7 per spec-beslutning.
    """
    b = port_config.buildings
    surf = pygame.Surface(
        (port_config.world_width, constants.RENDER_HEIGHT)
    ).convert()
    surf.fill(COLORKEY)
    texture = b.props.ground_texture if b.props is not None else "wood_dark"
    _bake_ground(surf, b.ground_top_y, texture=texture)
    if b.fill_buildings:
        _bake_fill_buildings(
            surf, b.fill_buildings, b.ground_top_y, night_lights,
        )
    _bake_tavern(
        surf, b.tavern.x, b.tavern.y, b.tavern.w, b.tavern.h,
        b.ground_top_y, night_lights,
    )
    exchange_baker = _EXCHANGE_BAKERS.get(port_config.id, _bake_exchange)
    exchange_baker(
        surf, b.exchange.x, b.exchange.y, b.exchange.w, b.exchange.h,
        b.ground_top_y, night_lights,
    )
    if b.signature_buildings:
        _bake_signature_buildings(
            surf, b.signature_buildings, b.ground_top_y, night_lights,
        )
    if b.props is not None:
        _bake_props(surf, b.props, b.ground_top_y)
    if b.alleys:
        _bake_alley_contents(surf, b.alleys, b.ground_top_y)
    if b.nature_elements:
        _bake_nature_elements(surf, b.nature_elements, b.ground_top_y)
    surf.set_colorkey(COLORKEY)
    return surf


def build_port_gameplay_layer(
    port_config: PortConfig,
) -> tuple[pygame.Surface, pygame.Surface]:
    """Pre-render gameplay-lag i to dag/natt-varianter (C2.5-8b).

    Returnerer `(day_surface, night_surface)`. PortVillageScene holder
    begge og cross-fader basert på night_factor per frame.

    Leser layout fra `port_config.buildings`. Kaster ValueError hvis
    havnen ikke har buildings-felt ennå (edge-case i tidlige faser).
    """
    if port_config.buildings is None:
        raise ValueError(
            f"Port '{port_config.id}' has no buildings layout — "
            f"cannot build gameplay layer"
        )
    day_surface = _bake_single_gameplay_layer(port_config, night_lights=False)
    night_surface = _bake_single_gameplay_layer(port_config, night_lights=True)
    return day_surface, night_surface
