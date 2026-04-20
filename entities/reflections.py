"""Vann-refleksjoner for havn-scener (Fase 2.5 C2.5-8).

Per FASE_2_5.md §1.5: vannet var tom plass før C2.5-8. Refleksjoner
av lyskilder gir havnene atmosfærisk dybde og Kingdom Two Crowns-
kvalitet.

## Teknisk tilnærming

**Bakes i gameplay-laget** (speed 1.0) — samme parallax-hastighet
som lyskildene (vinduer, dører, måne via Celestial). Ingen drift
mellom kilde og refleksjon ved kamera-bevegelse.

**Rekkefølge i bake-pipelinen:** refleksjoner tegnes mellom
`_bake_ground` og `_bake_fill_buildings`. Bygningene dekker senere
over eventuelt overlapp, slik at refleksjonene kun vises i vann-
regionen (y=horizon..bygning_y, typisk y=208..258 for tavern-kanten
eller y=208..ground_top_y i åpen gate).

**Palett-disiplin:** kun master-palett-farger. Hver refleksjons-type
bruker en 3-fargs gradient fra topp (nær horisont, lys) til bunn
(dyp vann, mørkt). Siden master-paletten har begrensede dempede
varianter, grupperer vi kilde-farger i 5 "kinds":

- `lantern`  — gul/oker vindus-lys (LANTERN → EMBER → WOOD_MID)
- `flame`    — varm dør-glød (FLAME → EMBER → WOOD_DARK)
- `moon`     — hvit månelys (MOON_HALO → STONE_LIT → STONE_DARK)
- `cold`     — blått stein-lys (STONE_LIT → STONE_DARK → STONE_DARKEST)
- `ship`     — seilduk-refleksjon (SHIRT → WOOD_LIGHT → WOOD_DARK)

**Wobble:** hver y-linje i refleksjonen får en horisontal sinus-
forskyvning for "bølge-antydning" per spec §1.5. Amplitude 1-2 px.

**Ytelse:** bakes én gang ved on_enter. 10-15 refleksjons-striper
per havn = ~150-400 `set_at`-kall totalt per scene-init. Måler
neglisjerbar kost.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import pygame

import constants

if False:  # TYPE_CHECKING-avoid
    from config.port_config import PortConfig


#: Horisont-linjen i gameplay-lag-koordinater. Matcher foreground-lagets
#: horizon_y (0.58 * RENDER_HEIGHT = 208).
HORIZON_Y: int = 208


@dataclass(frozen=True)
class ReflectionSource:
    """Én refleksjons-kilde.

    `x` er gameplay-lag-koordinater (world-x i speed 1.0). `kind`
    bestemmer farge-gradient. `length` er strekkens høyde under
    horisontlinjen. `width` > 1 gir bred strek (månen).
    """
    x: int
    kind: str
    length: int = 12
    width: int = 1
    wobble_amp: int = 1


#: Palett-disiplinerte 3-fargs gradienter per refleksjons-type.
#: Topp (nær horisont, lys) → Midt → Bunn (dyp vann, mørk).
_GRADIENTS: dict[str, tuple[tuple[int, int, int], ...]] = {
    "lantern": (
        constants.COLOR_LANTERN,
        constants.COLOR_EMBER,
        constants.COLOR_WOOD_MID,
    ),
    "flame": (
        constants.COLOR_FLAME,
        constants.COLOR_EMBER,
        constants.COLOR_WOOD_DARK,
    ),
    "moon": (
        constants.COLOR_MOON_HALO,
        constants.COLOR_STONE_LIT,
        constants.COLOR_STONE_DARK,
    ),
    "cold": (
        constants.COLOR_STONE_LIT,
        constants.COLOR_STONE_DARK,
        constants.COLOR_STONE_DARKEST,
    ),
    "ship": (
        constants.COLOR_SHIRT,
        constants.COLOR_WOOD_LIGHT,
        constants.COLOR_WOOD_DARK,
    ),
}

#: Gyldige reflection-kinds. Brukes av tester for validering.
VALID_REFLECTION_KINDS: frozenset[str] = frozenset(_GRADIENTS.keys())


def bake_reflection_stripe(
    surface: pygame.Surface,
    src: ReflectionSource,
    horizon_y: int = HORIZON_Y,
    wobble_period: int = 5,
) -> None:
    """Tegn vertikal refleksjons-strek med wobble fra horisontlinjen.

    Hver y-linje får en x-forskyvning basert på sinus-kurve. Fargen
    går fra lys (topp) til mørk (bunn) i 3 trinn for å simulere dybde.

    Skriver kun i gameplay-lagets vann-region. Kaller `set_at`
    direkte (ikke `fblits`) siden dette er én-gang-baking, ikke
    per-frame-rendering.
    """
    if src.kind not in _GRADIENTS:
        raise ValueError(
            f"Ukjent reflection-kind: {src.kind!r} "
            f"(gyldige: {sorted(VALID_REFLECTION_KINDS)})"
        )
    gradient = _GRADIENTS[src.kind]
    half_width = src.width // 2
    surf_w = surface.get_width()
    surf_h = surface.get_height()
    for dy in range(src.length):
        y = horizon_y + dy
        if y >= surf_h:
            break
        # Farge-gradient basert på relativ dybde (3 trinn)
        t = dy / max(1, src.length)
        if t < 0.33:
            color = gradient[0]  # Lys topp
        elif t < 0.67:
            color = gradient[1]  # Midt
        else:
            color = gradient[2]  # Mørk bunn
        # Horisontal wobble (sinus)
        wobble = int(
            src.wobble_amp * math.sin(2 * math.pi * dy / wobble_period)
        )
        cx = src.x + wobble
        # Bredde (symmetrisk rundt cx)
        for dx in range(-half_width, half_width + 1):
            px = cx + dx
            if 0 <= px < surf_w:
                surface.set_at((px, y), color)


def generate_port_reflections(port_config) -> list[ReflectionSource]:
    """Auto-generer refleksjons-kilder fra port_config.

    Utleder kilder fra eksisterende buildings + signature_buildings +
    props, slik at vi ikke trenger nye data-felt i ports.json.
    Refleksjons-tematikk per havn matcher FASE_2_5.md §1.5.

    Antall kilder per havn (typisk 10-15 per spec):
    - Tortuga: 6 (tavern 4 + exchange 1 + måne 1)
    - Port Royal: 8 (tavern 4 + customs 1 + klokke 1 + rum 3 + måne 1)
    - Havana: 12 (tavern 4 + katedral 2 + palass 3 + handelshus 3 +
      måne 1)
    - Nassau: 10 (tavern 4 + markedsplass 1 + Teach 3 + bål 2 + måne 1)

    Skip-master-refleksjoner er utelatt i C2.5-8: skipene er på
    foreground-lag (speed 0.2) mens refleksjonene er på gameplay-
    lag (speed 1.0); de ville driftet fra hverandre. Skip-
    refleksjoner kan legges inn i foreground-bake i en senere runde.
    """
    sources: list[ReflectionSource] = []
    b = port_config.buildings
    if b is None:
        return sources

    # --- Tavern (alle havner) ---
    tavern = b.tavern
    tavern_cx = tavern.x + tavern.w // 2
    # Tavern-lanterne (over skiltet, lys-kilde "lantern")
    sources.append(ReflectionSource(
        x=tavern_cx, kind="lantern", length=14,
    ))
    # Tavern-dør (flame — sterkeste varme)
    sources.append(ReflectionSource(
        x=tavern_cx, kind="flame", length=20, wobble_amp=2,
    ))
    # Tavern venstre + høyre vindu
    window_w = 24
    sources.append(ReflectionSource(
        x=tavern.x + 40 + window_w // 2, kind="lantern", length=10,
    ))
    sources.append(ReflectionSource(
        x=tavern.x + tavern.w - 40 - window_w // 2, kind="lantern",
        length=10,
    ))

    # --- Exchange-bbox (havn-spesifikk) ---
    exchange = b.exchange
    ex_cx = exchange.x + exchange.w // 2

    pid = port_config.id
    if pid == "tortuga":
        # Klassisk børshus — midtre kaldt vindu
        sources.append(ReflectionSource(x=ex_cx, kind="cold", length=16))

    elif pid == "port_royal":
        # Customs House — kaldt stort dør-lys
        sources.append(ReflectionSource(x=ex_cx, kind="cold", length=18))
        # Klokketårn-vindu og rum-magasin-porter
        for sb in b.signature_buildings:
            if sb.kind == "church_tower":
                cx = sb.placement.x + sb.placement.w // 2
                sources.append(ReflectionSource(
                    x=cx, kind="lantern", length=12,
                ))
            elif sb.kind == "rum_warehouse":
                # 3 porter jevnt fordelt i rum-magasin
                for i in range(3):
                    port_x = (sb.placement.x + 20
                              + int(i * (sb.placement.w - 40) / 2))
                    sources.append(ReflectionSource(
                        x=port_x, kind="flame", length=10,
                    ))

    elif pid == "havana":
        # Trade house arkader — 3 refleksjoner
        for i in range(3):
            arc_x = exchange.x + 24 + int(i * (exchange.w - 48) / 2)
            sources.append(ReflectionSource(
                x=arc_x, kind="lantern", length=9,
            ))
        # Katedral (portal + rose-vindu) + palass arkader
        for sb in b.signature_buildings:
            if sb.kind == "cathedral":
                cx = sb.placement.x + sb.placement.w // 2
                # Stor portal (flame) — dominerende
                sources.append(ReflectionSource(
                    x=cx, kind="flame", length=24, wobble_amp=2,
                ))
                # Rose-vindu (lantern)
                sources.append(ReflectionSource(
                    x=cx + 4, kind="lantern", length=14,
                ))
            elif sb.kind == "governor_palace":
                # 3 arkade-refleksjoner
                for i in range(3):
                    arc_x = (sb.placement.x + 30
                             + int(i * (sb.placement.w - 60) / 2))
                    sources.append(ReflectionSource(
                        x=arc_x, kind="lantern", length=8,
                    ))

    elif pid == "nassau":
        # Åpen markedsplass — varm LANTERN (per C2.5-4 lys-valg)
        sources.append(ReflectionSource(
            x=ex_cx, kind="lantern", length=16,
        ))
        # Teach's hus 3 vinduer (distinkt per C2.5-7 lys-karakter)
        for sb in b.signature_buildings:
            if sb.kind == "teachs_house":
                sources.append(ReflectionSource(
                    x=sb.placement.x + 22, kind="lantern", length=12,
                ))
                sources.append(ReflectionSource(
                    x=sb.placement.x + sb.placement.w - 22,
                    kind="flame", length=12,
                ))
                sources.append(ReflectionSource(
                    x=sb.placement.x + sb.placement.w // 2,
                    kind="flame", length=8,
                ))
        # Bål-refleksjoner (C2.5-4 campfires)
        if b.props is not None:
            for fire in b.props.campfires:
                sources.append(ReflectionSource(
                    x=fire.x + 7, kind="flame", length=14, wobble_amp=2,
                ))

    # --- Måne (alle havner, sist for å være bredeste) ---
    moon_cx = port_config.celestial.moon_worldx
    sources.append(ReflectionSource(
        x=moon_cx, kind="moon", length=32, width=3, wobble_amp=2,
    ))

    return sources


def bake_all_reflections(
    surface: pygame.Surface,
    port_config,
    horizon_y: int = HORIZON_Y,
) -> int:
    """Bake alle refleksjoner for en havn. Returnerer antall kilder.

    Kaster ingen feil hvis `port_config.buildings` er None (edge-case;
    nåværende ports.json har buildings for alle havner).
    """
    sources = generate_port_reflections(port_config)
    for src in sources:
        bake_reflection_stripe(surface, src, horizon_y=horizon_y)
    return len(sources)
