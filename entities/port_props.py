"""Rekvisita-bake-helpers for havn-gaten (Fase 2.5).

Funksjonene her genererer pixel-art for gategulv-teksturer, lanterne-
stolper, markedsboder og stablede tønner. Alle bakes én gang inn i
havnens gameplay-surface ved scene-init — ingen runtime-kost per frame.

Spec-referanse: `FASE_2_5.md §2.1` (Tortuga rekvisita-lag).

Palett-disiplin: kun master-farger fra `constants.py`. Ingen nye
hex-koder.
"""

from __future__ import annotations

import pygame

import constants


#: Gyldige gategulv-teksturer.
VALID_GROUND_TEXTURES: frozenset[str] = frozenset({
    "wood_dark",          # Eksisterende — beholdes som default for ikke-Tortuga
    "cobblestone_wet",    # Tortuga — våte flekker, smugler-atmosfære
    "cobblestone_dry",    # Port Royal — tørr ordnet brostein, kolonial orden
    "stone_slab",         # Havana — lyse varme heller, solvarme lagret i steinen
    "sand",               # Nassau — lovløs strand, fotspor, usorterte flekker
})


# --- Gategulv-teksturer ---

def bake_wood_dark_ground(surface: pygame.Surface, ground_top_y: int) -> None:
    """Eksisterende Tortuga-standard før C2.5-1. Bevart for ikke-Tortuga-
    havner i denne commiten (de får egne teksturer i C2.5-2/3/4).
    """
    width = surface.get_width()
    ground_bottom_y = constants.RENDER_HEIGHT
    pygame.draw.rect(
        surface,
        constants.COLOR_WOOD_DARKEST,
        (0, ground_top_y, width, ground_bottom_y - ground_top_y),
    )
    pygame.draw.rect(
        surface,
        constants.COLOR_WOOD_DARK,
        (200, ground_top_y + 2, width - 400, ground_bottom_y - ground_top_y - 2),
    )
    for x in range(260, width - 260, 80):
        pygame.draw.rect(
            surface, constants.COLOR_WOOD_MID, (x, ground_top_y + 4, 8, 1)
        )


def bake_cobblestone_wet_ground(
    surface: pygame.Surface, ground_top_y: int,
) -> None:
    """Tortuga: våt brostein med subtile høylys.

    Deler bakken i to vertikale bånd:
    - Øverst (2 px): mørk fuge mot bygnings-baselinjen
    - Hoveddel: STONE_DARK (kjølig grunnfarge — brosteinens våte overflate)
      med WOOD_MID-flekker (våte områder, gjenreflekterer natt-himmelen) og
      enkelte STONE_LIT-høylys (stjernelys på pytter).

    Palett-mix gir tekstur uten å bruke mer enn 4 farger — rene
    rektangler, ingen noise.
    """
    width = surface.get_width()
    ground_bottom_y = constants.RENDER_HEIGHT
    # 1) Mørk hovedbase: STONE_DARK (#1f2538) — kald våt brostein
    pygame.draw.rect(
        surface,
        constants.COLOR_STONE_DARK,
        (0, ground_top_y, width, ground_bottom_y - ground_top_y),
    )
    # 2) Øvre fuge (1 px STONE_DARKEST) — skiller bakken fra bygningene
    pygame.draw.rect(
        surface,
        constants.COLOR_STONE_DARKEST,
        (0, ground_top_y, width, 1),
    )
    # 3) Brostein-mønster: små STONE_MID-rektangler (2×1) spredt deterministisk
    #    Mønster: hver 12 px horisontalt, offset avhengig av rad.
    for row in range(2):
        y = ground_top_y + 3 + row * 8
        x_offset = 4 if row % 2 == 0 else 10
        for x in range(x_offset, width - 4, 12):
            pygame.draw.rect(
                surface, constants.COLOR_STONE_MID, (x, y, 2, 1)
            )
    # 4) Våte flekker: WOOD_MID-rektangler (6×2) på noen utvalgte steder.
    #    Deterministisk plassering for reproduserbarhet — hver 160 px.
    wet_ys = [ground_top_y + 7, ground_top_y + 13]
    for i, x in enumerate(range(80, width - 80, 160)):
        y = wet_ys[i % 2]
        pygame.draw.rect(
            surface, constants.COLOR_WOOD_MID, (x, y, 6, 2)
        )
    # 5) Sjeldne høylys: STONE_LIT prikker (1×1) — stjernelys-refleksjoner.
    #    1 prikk per 80 px.
    for x in range(40, width - 40, 80):
        y = ground_top_y + 5 + (x % 7)
        pygame.draw.rect(
            surface, constants.COLOR_STONE_LIT, (x, y, 1, 1)
        )


def bake_cobblestone_dry_ground(
    surface: pygame.Surface, ground_top_y: int,
) -> None:
    """Port Royal: tørr, ordnet brostein.

    Forskjell fra Tortugas `cobblestone_wet`:
    - Ingen WOOD_MID-våte flekker (tørr)
    - Regelmessig grid i STONE_MID (ordnet, ikke naturlig spredt)
    - Lysere base (STONE_MID i stedet for STONE_DARK) — kolonial orden
    - Subtile STONE_DARKEST-fugerlinjer mellom steinene

    Signaliserer "britisk institusjonell orden" mot Tortugas kaos.
    """
    width = surface.get_width()
    ground_bottom_y = constants.RENDER_HEIGHT
    # 1) Hovedbase — STONE_DARK (mørk natt-tone for kolonial brostein)
    pygame.draw.rect(
        surface,
        constants.COLOR_STONE_DARK,
        (0, ground_top_y, width, ground_bottom_y - ground_top_y),
    )
    # 2) Øvre fuge
    pygame.draw.rect(
        surface,
        constants.COLOR_STONE_DARKEST,
        (0, ground_top_y, width, 1),
    )
    # 3) Regelmessig brostein-grid — STONE_MID-brikker 8×3,
    #    tight spacing (6 px) for ordnet utseende
    for row in range(2):
        y = ground_top_y + 3 + row * 7
        for x in range(2, width - 2, 10):
            # Offset hver andre rad (slik ekte brostein legges)
            xo = x if row % 2 == 0 else x + 5
            if xo < width - 8:
                pygame.draw.rect(
                    surface, constants.COLOR_STONE_MID, (xo, y, 8, 3)
                )
                # Fuge-kant (1 px under)
                pygame.draw.rect(
                    surface, constants.COLOR_STONE_DARKEST,
                    (xo, y + 3, 8, 1),
                )


def bake_stone_slab_ground(
    surface: pygame.Surface, ground_top_y: int,
) -> None:
    """Havana: lyse varme steinheller.

    Varmeste gategulv av alle 4 havner. WOOD_LIGHT-base antyder
    solvarme lagret i stein; STONE_LIGHT-fuger mellom hellene.
    Ingen våte flekker (spansk tropisk klima — bakken tørker raskt).

    Signaliserer "spansk kolonial prakt" — store ordnede heller,
    ikke små brostein som Port Royal.
    """
    width = surface.get_width()
    ground_bottom_y = constants.RENDER_HEIGHT
    # 1) Hovedbase — WOOD_LIGHT (varm okerkebeige-brun for sol-heller)
    pygame.draw.rect(
        surface,
        constants.COLOR_WOOD_LIGHT,
        (0, ground_top_y, width, ground_bottom_y - ground_top_y),
    )
    # 2) Øvre fuge (1 px WOOD_DARKEST for skille mot bygninger)
    pygame.draw.rect(
        surface,
        constants.COLOR_WOOD_DARKEST,
        (0, ground_top_y, width, 1),
    )
    # 3) Heller: store 20x6 blokker med STONE_LIGHT-fuger — ordnet,
    #    annerledes enn Port Royals tettpakkede brostein
    slab_w = 20
    slab_gap = 2
    # Rad 1 — forskjøvet 0
    y = ground_top_y + 2
    for x in range(2, width - slab_w, slab_w + slab_gap):
        # Hellene — STONE_LIGHT høylys på venstre kant (sol-slør)
        pygame.draw.rect(
            surface, constants.COLOR_STONE_LIGHT, (x, y, 1, 5),
        )
        # Høylys-striper på toppen av noen heller
        pygame.draw.rect(
            surface, constants.COLOR_LANTERN, (x + 1, y, slab_w - 2, 1),
        )
    # Rad 2 — forskjøvet med halve bredden (ekte helle-legging)
    y = ground_top_y + 9
    x_start = 2 + (slab_w + slab_gap) // 2
    for x in range(x_start, width - slab_w, slab_w + slab_gap):
        pygame.draw.rect(
            surface, constants.COLOR_STONE_LIGHT, (x, y, 1, 5),
        )
        pygame.draw.rect(
            surface, constants.COLOR_LANTERN, (x + 1, y, slab_w - 2, 1),
        )


def bake_sand_ground(
    surface: pygame.Surface, ground_top_y: int,
) -> None:
    """Nassau: sand-gate.

    Ikke stein, ikke brostein — Nassau er en pirat-republikk bygd
    på strand. Palett: WOOD_LIGHT (sollys-beige) med uordnede
    WOOD_MID-flekker (sandgraver, fotspor) og enkelte WOOD_DARK-
    mørkere flekker (hvor noen har helt rom eller lignende —
    "brukt strand").
    """
    width = surface.get_width()
    ground_bottom_y = constants.RENDER_HEIGHT
    # 1) Hovedbase — WOOD_LIGHT (sollys-beige sand)
    pygame.draw.rect(
        surface,
        constants.COLOR_WOOD_LIGHT,
        (0, ground_top_y, width, ground_bottom_y - ground_top_y),
    )
    # 2) Øvre fuge (1 px WOOD_DARK)
    pygame.draw.rect(
        surface,
        constants.COLOR_WOOD_DARK,
        (0, ground_top_y, width, 1),
    )
    # 3) Uordnede sandgraver (WOOD_MID) — deterministisk pseudo-random
    #    via x*prime mod konstruksjon
    import hashlib  # For deterministisk "kaos" på tvers av kjøringer
    for x in range(10, width - 10, 14):
        # Deterministisk hash for y-offset og bredde
        h = int(hashlib.md5(str(x).encode()).hexdigest()[:4], 16)
        y_off = (h % 6) + 2
        w_off = (h % 5) + 3
        pygame.draw.rect(
            surface, constants.COLOR_WOOD_MID,
            (x, ground_top_y + y_off, w_off, 1),
        )
    # 4) Mørke flekker (spilt rom, kull-rester) — sparse
    for x in range(40, width - 40, 80):
        h = int(hashlib.md5(f"dark_{x}".encode()).hexdigest()[:4], 16)
        y_off = (h % 8) + 2
        pygame.draw.rect(
            surface, constants.COLOR_WOOD_DARK,
            (x, ground_top_y + y_off, 2, 1),
        )
    # 5) Fotspor-antydning (små STONE_DARKEST-par) — sparse
    for x in range(70, width - 50, 120):
        h = int(hashlib.md5(f"step_{x}".encode()).hexdigest()[:4], 16)
        y_off = (h % 6) + 5
        pygame.draw.rect(
            surface, constants.COLOR_STONE_DARKEST,
            (x, ground_top_y + y_off, 1, 1),
        )
        pygame.draw.rect(
            surface, constants.COLOR_STONE_DARKEST,
            (x + 3, ground_top_y + y_off + 2, 1, 1),
        )


def bake_ground(
    surface: pygame.Surface,
    ground_top_y: int,
    texture: str,
) -> None:
    """Dispatch til riktig bake-funksjon basert på tekstur-navn.

    Kaster `ValueError` for ukjent tekstur.
    """
    if texture == "wood_dark":
        bake_wood_dark_ground(surface, ground_top_y)
    elif texture == "cobblestone_wet":
        bake_cobblestone_wet_ground(surface, ground_top_y)
    elif texture == "cobblestone_dry":
        bake_cobblestone_dry_ground(surface, ground_top_y)
    elif texture == "stone_slab":
        bake_stone_slab_ground(surface, ground_top_y)
    elif texture == "sand":
        bake_sand_ground(surface, ground_top_y)
    else:
        raise ValueError(
            f"Ukjent ground_texture: {texture!r} "
            f"(gyldige: {sorted(VALID_GROUND_TEXTURES)})"
        )


# --- Rekvisita ---

def bake_lantern_post(
    surface: pygame.Surface,
    x: int,
    ground_top_y: int,
    *,
    height: int = 52,
) -> None:
    """Jernstolpe med lanterne på toppen.

    Fase 2.6: bumpet fra 40→52 px høyde og 5×5→7×8 lanterne for å
    matche ny 24×40 sprite-skala (480×270 oppløsning). Tydeligere
    silhuett mot natthimmel; ekstra hengende-arm-detalj.

    Glødet er BAKT (statisk), ikke dynamisk lys — dette holder oss
    innenfor 12-lys-budsjettet i v2.7. Alpha-pulsering vurderes
    senere.

    Form:
    - Stolpe: 1×(height-7) vertikal stripe, sentrert på `x`
    - Base: 3×1 ved bakken
    - Hengende arm: 5×1 sideveis (krullet jern-arm-antydning)
    - Lanterne: 7×8 boks på toppen med LANTERN_BRIGHT-kjerne
    - Statisk halo: 5 EMBER-piksler rundt lanterne
    """
    post_w = 1
    lantern_w, lantern_h = 7, 8
    post_h = height - lantern_h - 1
    cx = x  # Stolpens vertikale akse
    # Base (fot på bakken)
    pygame.draw.rect(
        surface,
        constants.COLOR_STONE_DARKEST,
        (cx - 1, ground_top_y - 1, 3, 1),
    )
    # Stolpe (vertikal) — STONE_DARKEST for jern-silhuett
    pygame.draw.rect(
        surface,
        constants.COLOR_STONE_DARKEST,
        (cx, ground_top_y - post_h, post_w, post_h),
    )
    top_y = ground_top_y - height
    # Krullet hengende-arm (jern-ornament som holder lanterne)
    pygame.draw.rect(
        surface,
        constants.COLOR_STONE_DARKEST,
        (cx - 2, top_y + lantern_h, 5, 1),
    )
    pygame.draw.rect(
        surface,
        constants.COLOR_STONE_DARKEST,
        (cx - 2, top_y + lantern_h - 1, 1, 1),
    )
    pygame.draw.rect(
        surface,
        constants.COLOR_STONE_DARKEST,
        (cx + 2, top_y + lantern_h - 1, 1, 1),
    )
    # Lanterne-boks (bredere boks, mørk ramme)
    lbox_x = cx - lantern_w // 2
    pygame.draw.rect(
        surface,
        constants.COLOR_WOOD_DARKEST,
        (lbox_x, top_y, lantern_w, lantern_h),
    )
    # Lanterne-flamme: 3 lag for dybde (LANTERN → LANTERN_BRIGHT kjerne)
    pygame.draw.rect(
        surface,
        constants.COLOR_LANTERN,
        (lbox_x + 1, top_y + 1, lantern_w - 2, lantern_h - 2),
    )
    pygame.draw.rect(
        surface,
        constants.COLOR_LANTERN_BRIGHT,
        (lbox_x + 2, top_y + 2, lantern_w - 4, lantern_h - 4),
    )
    # Mørke topp-/bunn-aksenter (ramme-detalj)
    pygame.draw.rect(
        surface,
        constants.COLOR_WOOD_DARKEST,
        (lbox_x + 1, top_y + lantern_h - 2, lantern_w - 2, 1),
    )
    # Krone-topp på lanterne (liten dekorativ stikk)
    pygame.draw.rect(
        surface,
        constants.COLOR_STONE_DARKEST,
        (cx, top_y - 1, 1, 1),
    )
    # Statisk halo: 5 EMBER-piksler i kors-mønster rundt lanterne
    halo = [
        (lbox_x - 1, top_y + 3),                  # venstre
        (lbox_x + lantern_w, top_y + 3),          # høyre
        (lbox_x + lantern_w // 2, top_y - 1),     # over
        (lbox_x + 1, top_y + lantern_h),          # under-venstre
        (lbox_x + lantern_w - 2, top_y + lantern_h),  # under-høyre
    ]
    for hx, hy in halo:
        pygame.draw.rect(surface, constants.COLOR_EMBER, (hx, hy, 1, 1))


def bake_market_stall(
    surface: pygame.Surface,
    x: int,
    ground_top_y: int,
    w: int = 80,
    *,
    height: int = 36,
) -> None:
    """Lukket markedsbod: presenning på reisverk.

    Spec §2.1 c: "Lukket for natten (det er tross alt natt-scene)".
    Derfor er denne en silhuett, ingen varer synlige, ingen interaksjon.

    Form:
    - Reisverk: 4 vertikale stolper (WOOD_DARKEST), høyde `height`
    - Presenning-tak: triangulært overheng (WOOD_DARK) med WOOD_MID-kant
    - Front: rullet presenning (WOOD_DARK-stripe nedover)
    """
    top_y = ground_top_y - height
    # Reisverk-stolper
    post_xs = [x, x + w - 1]
    for px in post_xs:
        pygame.draw.rect(
            surface,
            constants.COLOR_WOOD_DARKEST,
            (px, top_y + 3, 1, height - 3),
        )
    # Tak — trekant-silhuett via to rektangler (lavpoly)
    # Nedre rad (bredest)
    pygame.draw.rect(
        surface,
        constants.COLOR_WOOD_DARK,
        (x - 2, top_y + 4, w + 4, 4),
    )
    # Øvre rad (smalere — trekant-antydning)
    pygame.draw.rect(
        surface,
        constants.COLOR_WOOD_DARK,
        (x + 4, top_y, w - 8, 4),
    )
    # Kant på toppen (WOOD_MID-høylys, antyder månelys på presenning)
    pygame.draw.rect(
        surface,
        constants.COLOR_WOOD_MID,
        (x + 4, top_y, w - 8, 1),
    )
    # Lukket front (vertikal-stripete presenning). 3 striper som
    # går ned til bakken, med gap som antyder sammenrullet duk.
    front_y = top_y + 8
    front_h = height - 8
    stripe_xs = [x + 6, x + w // 2 - 2, x + w - 10]
    for sx in stripe_xs:
        pygame.draw.rect(
            surface,
            constants.COLOR_WOOD_DARK,
            (sx, front_y, 6, front_h),
        )
        # Skygge-aksent på hver strimmel
        pygame.draw.rect(
            surface,
            constants.COLOR_WOOD_DARKEST,
            (sx, front_y, 1, front_h),
        )


def bake_barrel_stack(
    surface: pygame.Surface,
    x: int,
    ground_top_y: int,
    count: int = 2,
    *,
    barrel_w: int = 10,
    barrel_h: int = 12,
) -> None:
    """Stablede tønner.

    `count` er antall tønner ved siden av hverandre på første rad.
    Hvis `count >= 3`, legges én ekstra tønne på toppen (mellom de to
    midtre) for å bryte horisontlinjen. Tønner har WOOD_MID-fyll med
    WOOD_DARKEST-bånd (metallringer på pirat-tønner).
    """
    count = max(1, min(count, 4))
    base_y = ground_top_y - barrel_h
    for i in range(count):
        bx = x + i * (barrel_w + 1)
        _draw_barrel(surface, bx, base_y, barrel_w, barrel_h)
    if count >= 3:
        # Stablet tønne på toppen
        top_x = x + (count // 2 - 1) * (barrel_w + 1) + (barrel_w + 1) // 2
        top_y = base_y - barrel_h
        _draw_barrel(surface, top_x, top_y, barrel_w, barrel_h)


def bake_iron_fence(
    surface: pygame.Surface,
    x: int,
    ground_top_y: int,
    length: int = 60,
    *,
    height: int = 14,
) -> None:
    """Jerngjerde-seksjon.

    Signatur for Port Royal: institusjonell avgrensning. Tynne
    vertikale stenger med horisontale bar-seksjoner. Alt i
    STONE_DARKEST for jern-silhuett mot mørk brostein.
    """
    top_y = ground_top_y - height
    # Topp-bar (med spisse stenger på toppen)
    pygame.draw.rect(
        surface, constants.COLOR_STONE_DARKEST, (x, top_y + 2, length, 1)
    )
    # Midt-bar
    pygame.draw.rect(
        surface,
        constants.COLOR_STONE_DARKEST,
        (x, top_y + height // 2 + 1, length, 1),
    )
    # Bunn-bar (mot bakken)
    pygame.draw.rect(
        surface,
        constants.COLOR_STONE_DARKEST,
        (x, ground_top_y - 1, length, 1),
    )
    # Vertikale stenger — hver 5 px, litt høyere enn bar-toppen
    # for spisse-topp-antydning
    for sx in range(x, x + length, 5):
        pygame.draw.rect(
            surface, constants.COLOR_STONE_DARKEST,
            (sx, top_y, 1, height),
        )


def bake_fountain(
    surface: pygame.Surface,
    x: int,
    ground_top_y: int,
    *,
    width: int = 32,
    height: int = 20,
) -> None:
    """Torgfontene (Havana) — sirkulær basseng-silhuett med vann.

    C2.5-3: statisk vann-surface (STONE_LIT-kjerne med LANTERN-
    sol-glimt). C2.5-6 vil legge til palette-cycling på vann-
    pikslene slik at den får Monkey Island-refleksjons-effekten.

    Plassering: `x` er venstre kant, fontenen står på bakken (top
    av bassenget er ved ground_top_y - height).
    """
    top_y = ground_top_y - height
    # Bassenget (ytre ring)
    pygame.draw.rect(
        surface, constants.COLOR_STONE_LIGHT, (x, top_y + height - 8, width, 2)
    )
    pygame.draw.rect(
        surface, constants.COLOR_STONE_DARKEST,
        (x, top_y + height - 8, width, 1),
    )
    # Bassenget (nedre del — høyere rand)
    pygame.draw.rect(
        surface, constants.COLOR_WOOD_MID,
        (x, top_y + height - 6, width, 5),
    )
    pygame.draw.rect(
        surface, constants.COLOR_WOOD_DARKEST,
        (x, top_y + height - 1, width, 1),
    )
    # Vann-overflate — sentrert i bassenget (STONE_LIT mørk-blå)
    water_x = x + 4
    water_y = top_y + height - 7
    water_w = width - 8
    water_h = 3
    pygame.draw.rect(
        surface, constants.COLOR_STONE_LIT, (water_x, water_y, water_w, water_h)
    )
    # Sol-glimt på vannet (statisk i C2.5-3; palette-cycling i C2.5-6)
    glimt_y = water_y + 1
    for gx in range(water_x + 2, water_x + water_w - 2, 4):
        pygame.draw.rect(
            surface, constants.COLOR_LANTERN_BRIGHT, (gx, glimt_y, 1, 1)
        )

    # Sentral søyle/tut (spansk barokk — vertikal stein-pilar)
    pillar_w = 4
    pillar_h = height - 8
    pillar_x = x + width // 2 - pillar_w // 2
    pillar_y = top_y
    pygame.draw.rect(
        surface, constants.COLOR_STONE_LIGHT,
        (pillar_x, pillar_y, pillar_w, pillar_h),
    )
    pygame.draw.rect(
        surface, constants.COLOR_STONE_DARK,
        (pillar_x + pillar_w - 1, pillar_y, 1, pillar_h),
    )
    # Topp-kappe (ornament)
    pygame.draw.rect(
        surface, constants.COLOR_STONE_LIGHT,
        (pillar_x - 1, pillar_y, pillar_w + 2, 2),
    )
    # Vann som renner ut (små dråper — LANTERN for "sunlit vann")
    for i in range(2):
        pygame.draw.rect(
            surface, constants.COLOR_LANTERN,
            (pillar_x - 1 + i * (pillar_w + 1), pillar_y + 3, 1, 2),
        )


def bake_planter(
    surface: pygame.Surface,
    x: int,
    ground_top_y: int,
    *,
    width: int = 10,
    height: int = 14,
) -> None:
    """Lav busk/plante i potte (Havana — ved palasset).

    Mørk silhuett mot lyse heller. Busken er WOOD_DARKEST med
    WOOD_DARK-høylys; potten er STONE_DARK.
    """
    # Potten
    pot_h = 4
    pot_y = ground_top_y - pot_h
    pygame.draw.rect(surface, constants.COLOR_STONE_DARK, (x, pot_y, width, pot_h))
    pygame.draw.rect(
        surface, constants.COLOR_STONE_DARKEST, (x, pot_y, width, 1)
    )
    # Busk — organisk klump (WOOD_DARKEST mot natt-himmel)
    bush_y = pot_y - (height - pot_h)
    pygame.draw.rect(
        surface, constants.COLOR_WOOD_DARKEST,
        (x + 1, bush_y + 2, width - 2, height - pot_h - 2),
    )
    # Toppen (smalere)
    pygame.draw.rect(
        surface, constants.COLOR_WOOD_DARKEST,
        (x + 2, bush_y, width - 4, 2),
    )
    # Subtile høylys (WOOD_DARK — antyder blad-struktur)
    pygame.draw.rect(
        surface, constants.COLOR_WOOD_DARK,
        (x + 2, bush_y + 1, 1, 3),
    )
    pygame.draw.rect(
        surface, constants.COLOR_WOOD_DARK,
        (x + width - 3, bush_y + 2, 1, 3),
    )


def bake_bamboo_lantern(
    surface: pygame.Surface,
    x: int,
    ground_top_y: int,
    *,
    height: int = 34,
) -> None:
    """Nassau: improvisert lanterne på bambus-stang / skipsmast-rest.

    Forskjell fra Tortugas jern-lantern-post:
    - Tynnere stolpe (WOOD_MID i stedet for STONE_DARKEST)
    - Skeiv (ikke helt vertikal — 1 px forskyvning)
    - Enklere lanterne (hengende, ikke boks)
    - Antyder "improvisert av det man har"
    """
    post_h = height - 6
    top_y = ground_top_y - height
    # Stolpe — WOOD_MID for bambus/tre. Skeivt (1 px forskyvning i toppen)
    for dy in range(0, post_h):
        # Skeivt: øvre del er 1 px til venstre
        offset = -1 if dy < post_h // 3 else 0
        pygame.draw.rect(
            surface,
            constants.COLOR_WOOD_MID,
            (x + offset, ground_top_y - post_h + dy, 1, 1),
        )
    # Base (fot på bakken — stabel av småstein?)
    pygame.draw.rect(
        surface, constants.COLOR_STONE_DARKEST,
        (x - 1, ground_top_y - 1, 3, 1),
    )
    # Horisontalt tverrstag
    pygame.draw.rect(
        surface,
        constants.COLOR_WOOD_DARK,
        (x - 2, top_y + 5, 5, 1),
    )
    # Hengende lanterne (enkelt hull)
    lantern_x = x - 1
    lantern_y = top_y + 6
    pygame.draw.rect(
        surface, constants.COLOR_WOOD_DARKEST, (lantern_x, lantern_y, 3, 5)
    )
    # Varm kjerne
    pygame.draw.rect(
        surface, constants.COLOR_LANTERN,
        (lantern_x, lantern_y + 1, 3, 3),
    )
    pygame.draw.rect(
        surface, constants.COLOR_LANTERN_BRIGHT,
        (lantern_x + 1, lantern_y + 2, 1, 1),
    )
    # Enkelt EMBER-glimt rundt
    pygame.draw.rect(
        surface, constants.COLOR_EMBER, (lantern_x - 1, lantern_y + 2, 1, 1)
    )
    pygame.draw.rect(
        surface, constants.COLOR_EMBER, (lantern_x + 3, lantern_y + 2, 1, 1)
    )


def bake_campfire(
    surface: pygame.Surface,
    x: int,
    ground_top_y: int,
    *,
    width: int = 14,
) -> None:
    """Nassau: åpent bål på gaten.

    Spec §3.1: palette-cycling på flammepiksler kommer i C2.5-6
    (tre FLAME/EMBER-varianter som roterer hvert 200 ms). I C2.5-4
    bakes en statisk "fasit"-flamme (LANTERN_BRIGHT-kjerne, FLAME-
    ytring, EMBER-kanter) slik at plasseringen er riktig og
    C2.5-6 kun trenger å erstatte pikslene.
    """
    # Vedhaug-base: stokker i kryss (WOOD_DARKEST)
    stack_w = width
    stack_y = ground_top_y - 4
    # To horisontale stokker
    pygame.draw.rect(
        surface, constants.COLOR_WOOD_DARKEST,
        (x, stack_y + 2, stack_w, 2),
    )
    # Kryss-stokker (2 stk vertikalt skåret gjennom)
    pygame.draw.rect(
        surface, constants.COLOR_WOOD_MID,
        (x + stack_w // 3, stack_y, 2, 4),
    )
    pygame.draw.rect(
        surface, constants.COLOR_WOOD_MID,
        (x + 2 * stack_w // 3, stack_y, 2, 4),
    )
    # Glør (EMBER) på toppen av vedhaugen
    pygame.draw.rect(
        surface, constants.COLOR_EMBER, (x + 2, stack_y, stack_w - 4, 1)
    )

    # Flamme (statisk "fasit") — 3 lag, LANTERN_BRIGHT i kjernen
    flame_bottom_y = stack_y - 1
    cx = x + stack_w // 2
    # EMBER-base (nederst, bredest)
    pygame.draw.rect(
        surface, constants.COLOR_EMBER,
        (cx - 4, flame_bottom_y - 4, 8, 4),
    )
    # FLAME midten
    pygame.draw.rect(
        surface, constants.COLOR_FLAME,
        (cx - 3, flame_bottom_y - 6, 6, 4),
    )
    # LANTERN-ring
    pygame.draw.rect(
        surface, constants.COLOR_LANTERN,
        (cx - 2, flame_bottom_y - 8, 4, 4),
    )
    # LANTERN_BRIGHT kjerne
    pygame.draw.rect(
        surface, constants.COLOR_LANTERN_BRIGHT,
        (cx - 1, flame_bottom_y - 9, 2, 4),
    )
    # Øvre tunge (smalest)
    pygame.draw.rect(
        surface, constants.COLOR_FLAME,
        (cx, flame_bottom_y - 11, 1, 2),
    )


def bake_chest_stack(
    surface: pygame.Surface,
    x: int,
    ground_top_y: int,
    count: int = 1,
    *,
    chest_w: int = 14,
    chest_h: int = 9,
) -> None:
    """Nassau: kaotisk stablede kister.

    Antall 1-3. Hver kiste har WOOD_DARK-kropp med LANTERN-lås
    og LANTERN_BRIGHT-høylys på låsen. Stablingen er LITT skjev
    (2 px x-forskyvning mellom lag) for å antyde kaos.
    """
    count = max(1, min(count, 3))
    for i in range(count):
        # Skeivstacking: hvert lag forskjøvet 2 px i forskjellig retning
        dx = (i % 2) * 2 - (1 if i > 0 else 0)
        cy = ground_top_y - (i + 1) * chest_h
        cx = x + dx * (i > 0)
        _draw_chest(surface, cx, cy, chest_w, chest_h)


def _draw_chest(
    surface: pygame.Surface,
    x: int,
    y: int,
    w: int,
    h: int,
) -> None:
    """Én kiste: WOOD_DARK-kropp, WOOD_DARKEST-bånd, LANTERN-lås."""
    # Kropp
    pygame.draw.rect(surface, constants.COLOR_WOOD_DARK, (x, y, w, h))
    # Topp-lokk (delt horisontalt) — WOOD_MID
    pygame.draw.rect(surface, constants.COLOR_WOOD_MID, (x, y, w, 3))
    # Skygge-kant høyre
    pygame.draw.rect(surface, constants.COLOR_WOOD_DARKEST, (x + w - 1, y, 1, h))
    # Lys-kant venstre
    pygame.draw.rect(surface, constants.COLOR_WOOD_LIGHT, (x, y, 1, h))
    # Bånd (WOOD_DARKEST) — vertikale + horisontal lokk-linje
    pygame.draw.rect(surface, constants.COLOR_WOOD_DARKEST, (x + 3, y, 1, h))
    pygame.draw.rect(
        surface, constants.COLOR_WOOD_DARKEST, (x + w - 4, y, 1, h)
    )
    pygame.draw.rect(surface, constants.COLOR_WOOD_DARKEST, (x, y + 3, w, 1))
    # Lås (LANTERN, midtstilt, lokk-linje-høyde)
    lock_x = x + w // 2 - 1
    pygame.draw.rect(
        surface, constants.COLOR_LANTERN, (lock_x, y + 2, 2, 3)
    )
    # Høylys på låsen
    pygame.draw.rect(
        surface, constants.COLOR_LANTERN_BRIGHT, (lock_x, y + 2, 1, 1)
    )


def _draw_barrel(
    surface: pygame.Surface,
    x: int,
    y: int,
    w: int,
    h: int,
) -> None:
    """Én tønne: WOOD_MID-fyll, WOOD_DARKEST-bånd topp/midt/bunn."""
    # Hoved-fyll
    pygame.draw.rect(surface, constants.COLOR_WOOD_MID, (x, y, w, h))
    # Skygge-aksent (høyre kant)
    pygame.draw.rect(
        surface, constants.COLOR_WOOD_DARK, (x + w - 1, y, 1, h)
    )
    # Lys-aksent (venstre kant)
    pygame.draw.rect(
        surface, constants.COLOR_WOOD_LIGHT, (x, y + 1, 1, h - 2)
    )
    # Bånd: topp, midt, bunn
    pygame.draw.rect(surface, constants.COLOR_WOOD_DARKEST, (x, y, w, 1))
    pygame.draw.rect(
        surface, constants.COLOR_WOOD_DARKEST, (x, y + h // 2, w, 1)
    )
    pygame.draw.rect(
        surface, constants.COLOR_WOOD_DARKEST, (x, y + h - 1, w, 1)
    )
