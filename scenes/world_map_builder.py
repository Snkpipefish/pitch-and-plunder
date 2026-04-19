"""Bake-funksjoner for verdenskart-bakgrunn (Fase 2B C5).

Én 640×360 pre-rendret bakgrunn med:
- Himmel-band topp
- Hav-gradient (3 striper)
- Øy-silhuetter (STONE_DARKEST-polygoner med 1-px skimmer-linje
  for natt-leselighet — brukes først når dag/natt-varianter aktiveres)
- Bølge-prikker (sjekkerbrett-spredt, varme glimt EMBER i 20% når
  fasen er dawn/dusk)

Per FASE_2B_VISUELL_REFERANSE.md §§1, 5, 6.

Dag/natt-varianter (§6) er utsatt til C10 polish-fasen. C5 bygger
kun ÉN bakgrunn med noon-tint — alle 4 havner, statisk palett.
Fasens navn ("noon") bevares i API-et for å forenkle C10-utvidelse.
"""

from __future__ import annotations

import random

import pygame

import constants
from config.port_config import PortConfig


#: Horisont-y: havet starter her. 10% av skjermen er himmel på kartet
#: (topp-ned-perspektiv — mindre himmel enn sideview-scener).
_HORIZON_Y = int(constants.RENDER_HEIGHT * 0.10)

#: Antall bølge-prikker spredt over hav-regionen.
_WAVE_DOTS = 50

#: Andel av bølge-prikker som bytter til EMBER ved dawn/dusk.
_WARM_GLIMT_FRACTION = 0.20


def _draw_sky_band(surf: pygame.Surface, phase: str) -> None:
    """Tegn et himmel-band i topp av kartet. C5 bruker noon; dawn/dusk/
    night mappes til samme noon-band her (full dag/natt landet i C10).
    """
    width = surf.get_width()
    # Noon: lys blå gradient fra STONE_LIT topp til STONE_BRIGHT horisont
    # (matcher sideview-scenen). Noon-only for C5.
    pygame.draw.rect(
        surf, constants.COLOR_STONE_LIT, (0, 0, width, _HORIZON_Y // 2)
    )
    pygame.draw.rect(
        surf, constants.COLOR_STONE_BRIGHT,
        (0, _HORIZON_Y // 2, width, (_HORIZON_Y + 1) // 2),
    )


def _draw_sea_gradient(surf: pygame.Surface) -> None:
    """Tegn hav-gradient i 3 horisontale striper under horisonten."""
    width = surf.get_width()
    sea_height = constants.RENDER_HEIGHT - _HORIZON_Y
    # Stripe 1 (rett under horisont): SEA_MID — reflektert himmel-lys
    stripe_1_h = sea_height // 3
    # Stripe 2 (midten): SEA_DEEP — dypere vann
    stripe_2_h = sea_height // 3
    # Stripe 3 (bunn): SEA_DEEP — dypt vann

    pygame.draw.rect(
        surf, constants.COLOR_SEA_MID,
        (0, _HORIZON_Y, width, stripe_1_h),
    )
    pygame.draw.rect(
        surf, constants.COLOR_SEA_DEEP,
        (0, _HORIZON_Y + stripe_1_h, width, sea_height - stripe_1_h),
    )


def _draw_island_silhouette(
    surf: pygame.Surface,
    center: tuple[int, int],
    size: int,
) -> None:
    """Tegn en enkel øy-silhuett som polygon i STONE_DARKEST.

    Øyer er 'skygger på hav' — ingen indre detalj. Formen er lett
    irregulær via hardkodede offsets (ikke random) slik at samme
    geografiske layout rendres hver gang.
    """
    cx, cy = center
    # Enkel 6-punkt irregulær polygon.
    poly = [
        (cx - size,       cy),
        (cx - size // 2,  cy - size // 2),
        (cx,              cy - size // 2 - 2),
        (cx + size // 2 + 2, cy - size // 3),
        (cx + size,       cy + 1),
        (cx + size // 3,  cy + size // 2),
        (cx - size // 3,  cy + size // 2 - 1),
    ]
    pygame.draw.polygon(surf, constants.COLOR_STONE_DARKEST, poly)


def _draw_wave_dots(
    surf: pygame.Surface,
    phase: str,
    rng: random.Random,
) -> None:
    """Spredte 1-px prikker i øvre halvdel av hav-regionen.

    Per fase: 100% STONE_BRIGHT ved noon/night. Ved dawn/dusk byttes
    ~20% til EMBER for å antyde sol-refleksjoner mot horisonten.

    `rng` gir deterministisk plassering for tester. Plasseringen er
    konstant innenfor én scene-session; fargen varierer med fase.
    """
    width = surf.get_width()
    # Begrenset til øvre halvdel av hav-regionen (nærmest horisont)
    sea_top = _HORIZON_Y
    sea_mid = _HORIZON_Y + (constants.RENDER_HEIGHT - _HORIZON_Y) // 2

    use_warm_glimt = phase in ("dawn", "dusk")

    for _ in range(_WAVE_DOTS):
        x = rng.randint(0, width - 1)
        y = rng.randint(sea_top, sea_mid - 1)
        warm = use_warm_glimt and rng.random() < _WARM_GLIMT_FRACTION
        color = constants.COLOR_EMBER if warm else constants.COLOR_STONE_BRIGHT
        surf.set_at((x, y), color)


def build_world_map_background(
    ports: dict[str, PortConfig],
    phase: str = "noon",
    rng: random.Random | None = None,
) -> pygame.Surface:
    """Bygg 640×360 kart-bakgrunn med himmel + hav + øyer + bølge-prikker.

    `ports` gir world_map_position per havn — brukt til å plassere øy-
    silhuetter. `phase` er "noon" i C5; "dawn"/"dusk"/"night" tas i bruk
    i C10 (per FASE_2B_VISUELL_REFERANSE.md §6).

    `rng=None` gir ikke-deterministisk bølge-prikke-spredning (friskt
    ved hver scene-session). Tester passer seed for reproduserbarhet.
    """
    r = rng or random.Random()

    surf = pygame.Surface(
        (constants.RENDER_WIDTH, constants.RENDER_HEIGHT)
    ).convert()

    _draw_sky_band(surf, phase)
    _draw_sea_gradient(surf)

    # Øy-silhuetter per havn. Størrelse 24–32 px avhengig av world_width
    # for å antyde hvor "stor" havnen er, men dette er kun kosmetisk.
    for port in ports.values():
        island_size = 24 if port.world_width < 1400 else 30
        _draw_island_silhouette(surf, port.world_map_position, island_size)

    _draw_wave_dots(surf, phase, r)

    return surf
