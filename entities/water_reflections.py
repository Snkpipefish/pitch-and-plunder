"""Vann-refleksjoner fra bygnings-lys (Fase 2.5 C2.5-8c).

Andre forsøk etter C2.5-8/C2.5-8a revert. Bygget på C2.5-8b
dag/natt-infrastruktur: refleksjoner bakes KUN inn i night-
variant-gameplay-surface, før bygninger. Bygningene tegnes over og
okkluderer refleksjoner der de overlapper. Ved day-variant er
surfacen uten refleksjoner, så dag/natt-gating følger automatisk.

## Designkrav løst

1. **Vann-region**: refleksjoner starter ved `water_y_top` (rett under
   horisont-silhuetten, ca y=214), aldri ved lyskildens y. Strekker
   seg nedover til `water_y_bottom` eller `length`-grensen.
2. **Dag/natt-gating**: via C2.5-8b night_surface-bytte. Refleksjonene
   er del av night-variant, fraværende i day-variant.
3. **Bygnings-okklusjon**: bygninger bakes ETTER refleksjoner i samme
   surface. Bygnings-piksler overskriver refleksjons-piksler der de
   overlapper.
4. **Brede og levende**: width 4-8 px per kilde, wobble 2-3 px
   amplitude, 4-steg palett-gradient fra kilde-farge til mørk.

## Palett-disiplin

Kun master-palett-farger. 4 gradienter for forskjellige lys-typer:
- lantern: gul-oker (vindus-lys, lanterner)
- flame: rød-oker (dør-glød, bål)
- ember: mørkere rød (sekundære varme kilder)
- stone_lit: kald-blå (STONE-familien, britisk institusjonell)

Bunn-farge i alle gradienter er mørk — SEA_DEEP eller STONE_DARKEST
— for å blende mot havets mørke blå.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import pygame

import constants


#: Vann-regionens topp-y (rett under fjell-silhuettens bunn).
#: Foreground-laget har hav-fyll fra horizon_y=208 og nedover, men
#: fjellene okkluderer til y ~214 (horizon + 6 px silhouette-dybde).
WATER_Y_TOP: int = 214


#: Palett-gradienter per refleksjons-type.
#: Topp (lys) → Bunn (mørk, fader mot hav). 4 steg.
_GRADIENTS: dict[str, tuple[tuple[int, int, int], ...]] = {
    "lantern": (
        constants.COLOR_LANTERN_BRIGHT,  # Topp — sterkest
        constants.COLOR_LANTERN,
        constants.COLOR_EMBER,
        constants.COLOR_WOOD_DARK,       # Bunn — mørk mot hav
    ),
    "flame": (
        constants.COLOR_FLAME,
        constants.COLOR_EMBER,
        constants.COLOR_WOOD_DARK,
        constants.COLOR_WOOD_DARKEST,
    ),
    "ember": (
        constants.COLOR_EMBER,
        constants.COLOR_WOOD_DARK,
        constants.COLOR_WOOD_DARKEST,
        constants.COLOR_STONE_DARKEST,
    ),
    "stone_lit": (
        constants.COLOR_STONE_LIT,
        constants.COLOR_STONE_MID,
        constants.COLOR_STONE_DARK,
        constants.COLOR_STONE_DARKEST,
    ),
}

#: Gyldige palett-nøkler — brukt av tester.
VALID_PALETTES: frozenset[str] = frozenset(_GRADIENTS.keys())


@dataclass(frozen=True)
class ReflectionSource:
    """Én refleksjons-kilde.

    `x` er verdens-x (gameplay-lag-koordinater). `palette_key` er en
    av `VALID_PALETTES`. `width` er horisontal bredde (4-10 px),
    `length` er vertikal lengde i vannet (15-30 px).

    `wobble_amp` gir horisontal sinus-forskyvning per y-linje for
    bølge-antydning.
    """
    x: int
    palette_key: str
    width: int = 6
    length: int = 24
    wobble_amp: int = 2


def bake_reflection_source(
    surface: pygame.Surface,
    src: ReflectionSource,
    water_y_top: int,
    water_y_bottom: int,
) -> None:
    """Tegn én refleksjon fra water_y_top ned.

    Refleksjonen STARTER alltid ved water_y_top (ikke ved lyskildens y).
    Dette plasserer alle refleksjoner i vann-regionen, uansett hvor
    høyt oppe lyskilden er på bygningen.

    Lengden er begrenset av `src.length` og `water_y_bottom`. Bygninger
    som okkluderer refleksjonen håndteres automatisk (de tegnes etter
    denne funksjonen og overskriver refleksjons-piksler).

    Bredde: sentrum har lys farge (gradient[0-1]), kanter har
    mørkere farge (gradient[1-2]) — gir "fuzzy" kant.

    Wobble: hver y-linje får horisontal forskyvning ved sinus +
    svakere andre-frekvens for mindre kunstig mønster.
    """
    if src.palette_key not in _GRADIENTS:
        raise ValueError(
            f"Ukjent reflection palette_key: {src.palette_key!r} "
            f"(gyldige: {sorted(VALID_PALETTES)})"
        )
    gradient = _GRADIENTS[src.palette_key]
    max_length = min(src.length, water_y_bottom - water_y_top)
    if max_length <= 0:
        return

    surf_w = surface.get_width()
    half_w = src.width // 2

    for dy in range(max_length):
        y = water_y_top + dy
        if y >= water_y_bottom:
            break
        # Gradient-indeks basert på dybde: 0 øverst, 3 nederst
        t = dy / max(1, max_length - 1)
        base_idx = min(3, int(t * 4))
        # Dybde-intensitet faller raskere nær bunnen (ikke-lineær)
        # ved å bruke t^1.5 for steg-valg
        bottom_bias = t ** 1.5
        accelerated_idx = min(3, int(bottom_bias * 4))
        step = max(base_idx, accelerated_idx)

        # Wobble: sinus + svakere høyere-frekvens + delvis støy-likt
        wobble = int(
            src.wobble_amp * math.sin(2 * math.pi * dy / 5.0)
            + 0.4 * src.wobble_amp * math.sin(2 * math.pi * dy / 2.3)
        )
        cx = src.x + wobble

        # Bredde-fill: sentrum bruker step, kanter bruker step+1
        for dx in range(-half_w, half_w + 1):
            edge_factor = 1.0 - abs(dx) / (half_w + 1)
            if edge_factor > 0.55:
                color = gradient[step]  # Sentrum
            else:
                color = gradient[min(3, step + 1)]  # Kant — en tonenedsatt
            px = cx + dx
            if 0 <= px < surf_w:
                surface.set_at((px, y), color)


def bake_all_reflections(
    surface: pygame.Surface,
    sources: list[ReflectionSource],
    water_y_top: int = WATER_Y_TOP,
    water_y_bottom: int = 340,
) -> int:
    """Bake alle refleksjons-kilder i surface. Returnerer antall bakte."""
    for src in sources:
        bake_reflection_source(surface, src, water_y_top, water_y_bottom)
    return len(sources)


def generate_port_reflections(port_config) -> list[ReflectionSource]:
    """Auto-generer refleksjons-kilder fra port_config.

    Heuristikk per havn:
    - Tavern: 4 kilder (lanterne, dør, 2 vinduer)
    - Exchange/signatur-bygninger: per-havn-logikk
    - Signatur-bygnings-vindu/dør/porter
    - Nassau-bål
    - IKKE måne (det er C2.5-8d)

    Antall kilder per havn holdes moderat (6-12) for å unngå visuell
    overfylt vann-region.
    """
    sources: list[ReflectionSource] = []
    b = port_config.buildings
    if b is None:
        return sources

    # --- Tavern (alle havner) ---
    tavern = b.tavern
    tavern_cx = tavern.x + tavern.w // 2
    # Tavern-lanterne — sterkeste lantern-kilde
    sources.append(ReflectionSource(
        x=tavern_cx, palette_key="lantern", width=8, length=26, wobble_amp=2,
    ))
    # Tavern-dør — flame-glød, bredest
    sources.append(ReflectionSource(
        x=tavern_cx, palette_key="flame", width=10, length=28, wobble_amp=3,
    ))
    # Tavern venstre + høyre vindu
    window_w = 24
    sources.append(ReflectionSource(
        x=tavern.x + 40 + window_w // 2,
        palette_key="lantern", width=6, length=22, wobble_amp=2,
    ))
    sources.append(ReflectionSource(
        x=tavern.x + tavern.w - 40 - window_w // 2,
        palette_key="lantern", width=6, length=22, wobble_amp=2,
    ))

    # --- Exchange-bbox (havn-spesifikk) ---
    exchange = b.exchange
    ex_cx = exchange.x + exchange.w // 2

    pid = port_config.id
    if pid == "tortuga":
        # Klassisk børshus — kaldt midtre vindu
        sources.append(ReflectionSource(
            x=ex_cx, palette_key="stone_lit", width=6, length=20, wobble_amp=2,
        ))
    elif pid == "port_royal":
        # Customs House — bred kald dør-lys
        sources.append(ReflectionSource(
            x=ex_cx, palette_key="stone_lit", width=8, length=24, wobble_amp=2,
        ))
        # Klokketårn-vindu + rum-magasin 3 porter
        for sb in b.signature_buildings:
            if sb.kind == "church_tower":
                cx = sb.placement.x + sb.placement.w // 2
                sources.append(ReflectionSource(
                    x=cx, palette_key="lantern", width=5, length=18, wobble_amp=2,
                ))
            elif sb.kind == "rum_warehouse":
                for i in range(3):
                    port_x = (sb.placement.x + 20
                              + int(i * (sb.placement.w - 40) / 2))
                    sources.append(ReflectionSource(
                        x=port_x, palette_key="ember",
                        width=5, length=16, wobble_amp=2,
                    ))
    elif pid == "havana":
        # Trade house — 3 arkade-glimt
        for i in range(3):
            arc_x = exchange.x + 24 + int(i * (exchange.w - 48) / 2)
            sources.append(ReflectionSource(
                x=arc_x, palette_key="lantern",
                width=5, length=18, wobble_amp=2,
            ))
        # Katedral + palass
        for sb in b.signature_buildings:
            if sb.kind == "cathedral":
                cx = sb.placement.x + sb.placement.w // 2
                # Stor FLAME-portal — dominerende
                sources.append(ReflectionSource(
                    x=cx, palette_key="flame",
                    width=10, length=30, wobble_amp=3,
                ))
                # Katedralens to klokketårn-vinduer
                tower_cx_left = sb.placement.x + 15
                tower_cx_right = sb.placement.x + sb.placement.w - 15
                sources.append(ReflectionSource(
                    x=tower_cx_left, palette_key="lantern",
                    width=5, length=16, wobble_amp=2,
                ))
                sources.append(ReflectionSource(
                    x=tower_cx_right, palette_key="lantern",
                    width=5, length=16, wobble_amp=2,
                ))
            elif sb.kind == "governor_palace":
                # 3 arkade-refleksjoner
                for i in range(3):
                    arc_x = (sb.placement.x + 30
                             + int(i * (sb.placement.w - 60) / 2))
                    sources.append(ReflectionSource(
                        x=arc_x, palette_key="lantern",
                        width=5, length=16, wobble_amp=2,
                    ))
    elif pid == "nassau":
        # Markedsplass — varm LANTERN
        sources.append(ReflectionSource(
            x=ex_cx, palette_key="lantern", width=8, length=24, wobble_amp=3,
        ))
        # Teach's hus 3 fargede vinduer
        for sb in b.signature_buildings:
            if sb.kind == "teachs_house":
                sources.append(ReflectionSource(
                    x=sb.placement.x + 22, palette_key="lantern",
                    width=6, length=20, wobble_amp=2,
                ))
                sources.append(ReflectionSource(
                    x=sb.placement.x + sb.placement.w - 22,
                    palette_key="flame",
                    width=6, length=20, wobble_amp=2,
                ))
                sources.append(ReflectionSource(
                    x=sb.placement.x + sb.placement.w // 2,
                    palette_key="flame",
                    width=5, length=16, wobble_amp=2,
                ))
        # Bål-refleksjoner (FLAME, bredest + lengst)
        if b.props is not None:
            for fire in b.props.campfires:
                sources.append(ReflectionSource(
                    x=fire.x + 7, palette_key="flame",
                    width=10, length=30, wobble_amp=3,
                ))

    return sources
