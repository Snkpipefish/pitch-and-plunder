"""Bake-funksjoner for verdenskart-bakgrunn (Fase 2B C5, utvidet i C5.1).

Bygger 4 fase-varianter (noon/dawn/dusk/night) av 640×360 kart-
bakgrunnen. Hver variant inkluderer:
- Himmel-band topp (fase-avhengig gradient)
- Hav-gradient (3 striper)
- §8.4 skyggedybde — lysere SEA_MID i coastal_radius rundt hver øy
- §8.1 øy-silhuetter med topp-kant-belysning (fase-spesifikk farge)
- §8.2 horisont-bånd med alpha-gradient (fase-spesifikk farge)
- §5 bølge-prikker (sjekkerbrett, 20% EMBER ved dawn/dusk)

Per `FASE_2B_VISUELL_REFERANSE.md` §8 (v1.2) som er bindende over §1-§6
der de kolliderer.

C5.1 bruker kun "noon"-varianten ved runtime; alle 4 pre-renderes slik
at C10 kan aktivere cross-fade uten å endre scene-init.
"""

from __future__ import annotations

import logging
import random

import pygame

import constants
from config.port_config import PortConfig


log = logging.getLogger(__name__)


#: Horisont-y: havet starter her. 10% av skjermen er himmel på kartet
#: (topp-ned-perspektiv — mindre himmel enn sideview-scener).
_HORIZON_Y = int(constants.RENDER_HEIGHT * 0.10)

#: Antall bølge-prikker spredt over hav-regionen.
_WAVE_DOTS = 50

#: Andel av bølge-prikker som bytter til EMBER ved dawn/dusk.
_WARM_GLIMT_FRACTION = 0.20

#: §8.2 — horisont-bånd-høyde i pixler. Startverdi 4; kan økes til 6
#: hvis 4 viser seg for subtilt. Ikke høyere (8+ gir konstant skumring
#: per spec-veiledning).
_HORIZON_BAND_HEIGHT = 4

#: §8.4 — coastal shading radius. Test-rekkefølge 12 → 10 → 8 → drop,
#: eller 12 → 16. Valgt verdi logges ved scene-init.
_COASTAL_RADIUS_DEFAULT = 12
_COASTAL_RADIUS_MIN = 8
_COASTAL_RADIUS_MAX = 16


#: Fase-konfig — per §8.5 (kant) + §8.2 (horisont) + §5 (wave-dots).
#: C10 utvider med sky/sea-base-farge-variasjon; C5.1 holder disse
#: på noon-tint for alle faser (kun edge/horizon/waves differensierer).
_PHASE_STYLES: dict[str, dict] = {
    "noon": {
        "edge_color": constants.COLOR_STONE_DARK,
        "horizon_color": constants.COLOR_STONE_BRIGHT,
        "horizon_alpha_peak": 180,  # synlig men ikke dramatisk
        "wave_warm": False,
    },
    "dawn": {
        "edge_color": constants.COLOR_STONE_DARK,
        "horizon_color": constants.COLOR_EMBER,
        "horizon_alpha_peak": 200,  # varm horisont tydeligere ved dawn
        "wave_warm": True,
    },
    "dusk": {
        "edge_color": constants.COLOR_MOON_HALO,
        "horizon_color": constants.COLOR_EMBER,
        "horizon_alpha_peak": 200,
        "wave_warm": True,
    },
    "night": {
        "edge_color": constants.COLOR_MOON_HALO,
        "horizon_color": constants.COLOR_MOON_HALO,
        "horizon_alpha_peak": 100,  # §8.2: 30–40% → ~100/255 ≈ 39%
        "wave_warm": False,
    },
}


KNOWN_PHASES: tuple[str, ...] = ("noon", "dawn", "dusk", "night")


# -----------------------------------------------------------------------------
# Grunn-tegn-funksjoner
# -----------------------------------------------------------------------------

def _draw_sky_band(surf: pygame.Surface) -> None:
    """Tegn himmel-band i topp av kartet. Noon-tint for alle faser
    i C5.1; C10 utvider til per-fase-sky-farger."""
    width = surf.get_width()
    pygame.draw.rect(
        surf, constants.COLOR_STONE_LIT, (0, 0, width, _HORIZON_Y // 2)
    )
    pygame.draw.rect(
        surf, constants.COLOR_STONE_BRIGHT,
        (0, _HORIZON_Y // 2, width, (_HORIZON_Y + 1) // 2),
    )


def _draw_sea_gradient(surf: pygame.Surface) -> None:
    """Tegn hav-gradient i striper under horisonten."""
    width = surf.get_width()
    sea_height = constants.RENDER_HEIGHT - _HORIZON_Y
    stripe_1_h = sea_height // 3
    # Stripe 1 (rett under horisont): SEA_MID — reflektert himmel-lys
    pygame.draw.rect(
        surf, constants.COLOR_SEA_MID,
        (0, _HORIZON_Y, width, stripe_1_h),
    )
    # Resten: SEA_DEEP — dypt åpent vann
    pygame.draw.rect(
        surf, constants.COLOR_SEA_DEEP,
        (0, _HORIZON_Y + stripe_1_h, width, sea_height - stripe_1_h),
    )


# -----------------------------------------------------------------------------
# §8.4 Coastal shading
# -----------------------------------------------------------------------------

def _check_coastal_overlap(
    ports: dict[str, PortConfig],
    coastal_radius: int,
    island_half_size: int = 32,
) -> bool:
    """Sjekk om to havner er så nær at deres coastal-soner overlapper.

    `island_half_size` er konservativ overestimat av øy-silhuetters
    "radius" (største øy er ~30 px diameter fra senter). Overlapp
    oppstår hvis avstand mellom sentra < 2 * (island_half_size +
    coastal_radius).
    """
    positions = list(ports.values())
    threshold_sq = (2 * (island_half_size // 2 + coastal_radius)) ** 2
    for i, pa in enumerate(positions):
        for pb in positions[i + 1:]:
            dx = pa.world_map_position[0] - pb.world_map_position[0]
            dy = pa.world_map_position[1] - pb.world_map_position[1]
            if dx * dx + dy * dy < threshold_sq:
                return True
    return False


def _paint_coastal_sea(
    surf: pygame.Surface,
    ports: dict[str, PortConfig],
    coastal_radius: int,
) -> None:
    """Bytt SEA_DEEP → SEA_MID innenfor `coastal_radius` av hver øy.

    Hard overgang (ingen gradient) — pixel-estetikk. Påvirker KUN
    SEA_DEEP-piksler (ikke øy-silhuetter eller SEA_MID-stripa rett
    under horisonten).
    """
    width = surf.get_width()
    height = surf.get_height()
    r_sq = coastal_radius * coastal_radius
    for port in ports.values():
        cx, cy = port.world_map_position
        for dy in range(-coastal_radius, coastal_radius + 1):
            y = cy + dy
            if not (_HORIZON_Y <= y < height):
                continue
            for dx in range(-coastal_radius, coastal_radius + 1):
                if dx * dx + dy * dy > r_sq:
                    continue
                x = cx + dx
                if not (0 <= x < width):
                    continue
                pix = surf.get_at((x, y))
                if (pix[0], pix[1], pix[2]) == constants.COLOR_SEA_DEEP:
                    surf.set_at((x, y), constants.COLOR_SEA_MID)


def _resolve_coastal_radius(ports: dict[str, PortConfig]) -> int | None:
    """Returnerer valgt radius per §8.4 test-rekkefølge, eller None
    hvis alle størrelser innenfor søkesonen ville gi overlapp.
    """
    # Test 12 først (default); hvis overlapp, ned til 10, 8
    for r in (_COASTAL_RADIUS_DEFAULT, 10, _COASTAL_RADIUS_MIN):
        if not _check_coastal_overlap(ports, r):
            return r
    return None  # drop effekten


# -----------------------------------------------------------------------------
# §8.1 Topp-kant-belysning på øy-silhuetter
# -----------------------------------------------------------------------------

def _draw_island_silhouette(
    surf: pygame.Surface,
    center: tuple[int, int],
    size: int,
) -> pygame.Rect:
    """Tegn en øy-silhuett som polygon i STONE_DARKEST. Returnerer
    polygonens bounding-rect for senere top-edge-behandling.

    Øyer er "skygger på hav" — ingen indre detalj.
    """
    cx, cy = center
    poly = [
        (cx - size,             cy),
        (cx - size // 2,        cy - size // 2),
        (cx,                    cy - size // 2 - 2),
        (cx + size // 2 + 2,    cy - size // 3),
        (cx + size,             cy + 1),
        (cx + size // 3,        cy + size // 2),
        (cx - size // 3,        cy + size // 2 - 1),
    ]
    pygame.draw.polygon(surf, constants.COLOR_STONE_DARKEST, poly)
    # Returner bounding box for topp-kant-behandling
    xs = [p[0] for p in poly]
    ys = [p[1] for p in poly]
    return pygame.Rect(
        min(xs), min(ys),
        max(xs) - min(xs) + 1, max(ys) - min(ys) + 1,
    )


def _paint_top_edge(
    surf: pygame.Surface,
    rect: pygame.Rect,
    edge_color: tuple[int, int, int],
) -> None:
    """§8.1 — tegn 1-px kant KUN på silhuettens topp.

    For hver x-kolonne i `rect`, finn øverste STONE_DARKEST-pixel og
    mal pixelen RETT OVER den (y-1) i `edge_color`. Sider og bunn av
    silhuetten forblir uendret.
    """
    width = surf.get_width()
    for x in range(max(0, rect.left), min(width, rect.right)):
        for y in range(max(0, rect.top), min(surf.get_height(), rect.bottom)):
            pix = surf.get_at((x, y))
            if (pix[0], pix[1], pix[2]) == constants.COLOR_STONE_DARKEST:
                # Funnet øverste silhuett-pixel i denne kolonnen
                if y > 0:
                    surf.set_at((x, y - 1), edge_color)
                break  # ferdig med kolonnen


# -----------------------------------------------------------------------------
# §8.2 Horisont-bånd med alpha-gradient
# -----------------------------------------------------------------------------

def _paint_horizon_band(
    surf: pygame.Surface,
    band_color: tuple[int, int, int],
    alpha_peak: int,
    band_height: int = _HORIZON_BAND_HEIGHT,
) -> None:
    """Tegn 4-px horisont-bånd med alpha-gradient (100% i sentrum, 0%
    ved øvre/nedre kant).

    `alpha_peak` er maks alpha (0-255). Brukes for night-fase hvor
    båndet er sub-synlig (100/255 ≈ 39% per §8.2).

    Implementasjon: SRCALPHA-surface bygges som 2*band_height høy
    stripe med alpha avtakende mot kantene, blit-es på bakgrunnen.
    Pygame-blit håndterer alpha-blend til 24-bit target.
    """
    width = surf.get_width()
    total_h = band_height * 2
    band_surf = pygame.Surface((width, total_h), pygame.SRCALPHA)
    # Alpha-gradient: maks i sentrum, 0 på ytterkantene
    for dy in range(total_h):
        # distance_from_center: 0.5 for radene nærmest sentrum
        distance = abs(dy - band_height + 0.5)
        t = distance / band_height  # 0..1
        alpha = int(max(0.0, (1.0 - t)) * alpha_peak)
        pygame.draw.rect(band_surf, (*band_color, alpha), (0, dy, width, 1))
    surf.blit(band_surf, (0, _HORIZON_Y - band_height))


# -----------------------------------------------------------------------------
# §5 Bølge-prikker
# -----------------------------------------------------------------------------

def _draw_wave_dots(
    surf: pygame.Surface,
    wave_warm: bool,
    rng: random.Random,
) -> None:
    """Spredte 1-px prikker i øvre halvdel av hav-regionen.

    100% STONE_BRIGHT ved noon/night; ~20% EMBER ved dawn/dusk
    (`wave_warm=True`).

    Plasseringen er deterministisk gitt rng-seed; samme seed over
    faser gir identiske prikke-koordinater slik at C10 cross-fade
    ikke blinker.
    """
    width = surf.get_width()
    sea_top = _HORIZON_Y
    sea_mid = _HORIZON_Y + (constants.RENDER_HEIGHT - _HORIZON_Y) // 2

    for _ in range(_WAVE_DOTS):
        x = rng.randint(0, width - 1)
        y = rng.randint(sea_top, sea_mid - 1)
        warm = wave_warm and rng.random() < _WARM_GLIMT_FRACTION
        color = constants.COLOR_EMBER if warm else constants.COLOR_STONE_BRIGHT
        surf.set_at((x, y), color)


# -----------------------------------------------------------------------------
# Public API
# -----------------------------------------------------------------------------

def build_world_map_background(
    ports: dict[str, PortConfig],
    phase: str = "noon",
    rng: random.Random | None = None,
) -> pygame.Surface:
    """Bygg 640×360 kart-bakgrunn for gitt fase.

    Render-rekkefølge (viktig — senere lag tegnes OVER tidligere):
    1. Himmel-band (noon-gradient for alle faser i C5.1)
    2. Hav-gradient (SEA_MID under horisont, SEA_DEEP dypere)
    3. §8.4 coastal shading (SEA_DEEP → SEA_MID i radius)
    4. §5 bølge-prikker (sprer over ferdig hav)
    5. §8.1 øy-silhuetter + topp-kant-belysning
    6. §8.2 horisont-bånd (overlayer horisont-linjen sist)

    `phase` må være i `KNOWN_PHASES`. Ukjente faser faller til "noon".
    """
    r = rng or random.Random()
    style = _PHASE_STYLES.get(phase, _PHASE_STYLES["noon"])

    surf = pygame.Surface(
        (constants.RENDER_WIDTH, constants.RENDER_HEIGHT)
    ).convert()

    _draw_sky_band(surf)
    _draw_sea_gradient(surf)

    # §8.4 coastal shading — test-rekkefølge for radius
    coastal_radius = _resolve_coastal_radius(ports)
    if coastal_radius is not None:
        _paint_coastal_sea(surf, ports, coastal_radius)

    # §5 bølge-prikker
    _draw_wave_dots(surf, style["wave_warm"], r)

    # §8.1 Øyer + topp-kant
    for port in ports.values():
        island_size = 24 if port.world_width < 1400 else 30
        rect = _draw_island_silhouette(
            surf, port.world_map_position, island_size
        )
        _paint_top_edge(surf, rect, style["edge_color"])

    # §8.2 horisont-bånd (sist: overlayer både himmel-band og hav-topp)
    _paint_horizon_band(
        surf, style["horizon_color"], style["horizon_alpha_peak"]
    )

    return surf


def build_all_phase_variants(
    ports: dict[str, PortConfig],
    rng_seed: int | None = None,
) -> dict[str, pygame.Surface]:
    """Bygg alle 4 fase-varianter med konsistent bølge-prikke-
    plassering (samme seed over faser) slik at C10 cross-fade ikke
    vil blinke.

    C5.1 bruker kun "noon"-varianten. C10 aktiverer cross-fade.
    """
    result: dict[str, pygame.Surface] = {}
    for phase in KNOWN_PHASES:
        # Samme seed per fase → samme prikke-koordinater
        r = random.Random(rng_seed) if rng_seed is not None else random.Random(0xC5C5)
        result[phase] = build_world_map_background(ports, phase=phase, rng=r)

    # Logg valgt coastal-radius (eller drop) én gang per scene-init
    coastal = _resolve_coastal_radius(ports)
    if coastal is None:
        log.info("WorldMap coastal shading: dropped (overlap in all radii)")
    else:
        log.info("WorldMap coastal shading: radius=%d px", coastal)

    return result
