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


#: Gyldige gategulv-teksturer. Utvides per-havn i senere commits:
#: "stone_slab" (Havana), "sand" (Nassau).
VALID_GROUND_TEXTURES: frozenset[str] = frozenset({
    "wood_dark",          # Eksisterende — beholdes som default for ikke-Tortuga
    "cobblestone_wet",    # Tortuga — våte flekker, smugler-atmosfære
    "cobblestone_dry",    # Port Royal — tørr ordnet brostein, kolonial orden
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
    height: int = 40,
) -> None:
    """Jernstolpe med lanterne på toppen.

    Glødet er BAKT (statisk), ikke dynamisk lys — dette holder oss
    innenfor 4-lys-budsjettet (taverna-lanterne + taverna-dør +
    børs-vindu = 3 eksisterende dynamiske lys). Alpha-pulsering
    vurderes i C2.5-6.

    Form (bredde 7, høyde `height` inkl. lanterne):
    - Stolpe: 1×(height-6) vertikal stripe, sentrert på `x`
    - Base: 3×1 ved bakken
    - Lanterne: 5×5 boks på toppen med LANTERN_BRIGHT-kjerne
    - Statisk halo: 7×7 EMBER-ring med én pixel transparent hjørne-dropoff
    """
    post_w = 1
    post_h = height - 6
    lantern_w, lantern_h = 5, 5
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
    # Arm (tverrstag rett under lanterna)
    top_y = ground_top_y - height
    pygame.draw.rect(
        surface,
        constants.COLOR_STONE_DARKEST,
        (cx - 1, top_y + lantern_h, 3, 1),
    )
    # Lanterne-boks
    lbox_x = cx - lantern_w // 2
    pygame.draw.rect(
        surface,
        constants.COLOR_WOOD_DARKEST,
        (lbox_x, top_y, lantern_w, lantern_h),
    )
    # Lanterne-flamme (varm kjerne)
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
    # Statisk halo: 3 EMBER-prikker rundt lanterne (antyder glød-spredning)
    halo = [
        (lbox_x - 1, top_y + 2),
        (lbox_x + lantern_w, top_y + 2),
        (lbox_x + lantern_w // 2, top_y - 1),
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
