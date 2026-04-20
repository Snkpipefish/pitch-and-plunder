"""Palette-cycling for subtile lys-animasjoner (Fase 2.5 C2.5-9).

Billig Monkey Island-teknikk: overskriv en liten piksel-region på
gameplay-surfacen per frame med en farge fra en syklisk palett.
Med få piksler per kilde (budsjett 25 per havn), er per-frame-
kosten neglisjerbar.

## Designvalg

**Muterer gameplay-surface direkte.** Hver cycling-kilde har et
fast rektangel (x, y, w, h) som fylles med current frame-farge
per frame. Siden vi alltid skriver over de samme pikslene med en
ny farge fra paletten, vil regionen visuelt "sykle" gjennom
fargene. Strukturelle piksler rundt (vindus-rammer, stolper etc)
er uendret.

**Krav til cycling-region:** må være et "clean rect" — ingen
strukturelle piksler innenfor som skal bevares. Typisk kjerne av
flamme, lanterne-glimt, alter-lys-senter.

## Gating

- `permanent=True`: cycling kjører 24/7 (smithy-esse, bål,
  artisan-verksted). Ikke påvirket av night_factor.
- `permanent=False`: cycling gates av night_factor >= 0.5 (samme
  threshold som LightingSystem). Om dagen: rektangel fylles med
  en off-state-farge (spesifisert eller siste palett-farge som
  proxy for "slukket").

## Alpha-pulsering er IKKE implementert i C2.5-9

Planlagt men nedprioritert for scope-kontroll. Palette-cycling
alene gir tilstrekkelig liv i havnene. Alpha-pulsering dokumenteres
som Fase 3-arbeid hvis brukertest ber om det.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import pygame

import constants


#: Mapping fra palett-navn i JSON til faktisk farge. Brukes av parser
#: og `apply_palette_cycles`.
PALETTE_NAMES: dict[str, tuple[int, int, int]] = {
    "LANTERN": constants.COLOR_LANTERN,
    "LANTERN_BRIGHT": constants.COLOR_LANTERN_BRIGHT,
    "EMBER": constants.COLOR_EMBER,
    "FLAME": constants.COLOR_FLAME,
    "STONE_LIT": constants.COLOR_STONE_LIT,
    "STONE_BRIGHT": constants.COLOR_STONE_BRIGHT,
    "STONE_MID": constants.COLOR_STONE_MID,
    "STONE_DARK": constants.COLOR_STONE_DARK,
    "WOOD_DARK": constants.COLOR_WOOD_DARK,
    "WOOD_MID": constants.COLOR_WOOD_MID,
    "WOOD_LIGHT": constants.COLOR_WOOD_LIGHT,
    "WOOD_DARKEST": constants.COLOR_WOOD_DARKEST,
    "FOG": constants.COLOR_FOG,
}


@dataclass(frozen=True)
class PaletteCycleSource:
    """Én palette-cycling-kilde.

    Rektangulær region (x, y, w, h) på gameplay-surface fylles med
    en syklisk sekvens av palett-farger. `fps` bestemmer bytte-
    frekvens; lavere = langsommere.

    `palette`: liste av palett-navn (oppslagssvarer i
    `PALETTE_NAMES`). Minst 2 farger.

    `permanent=True`: kjører 24/7. `False`: gates av night_factor.
    """
    x: int
    y: int
    w: int
    h: int
    palette: tuple[str, ...]
    fps: float = 6.0
    permanent: bool = False


def compute_cycle_frame_index(
    elapsed_seconds: float, fps: float, num_frames: int,
) -> int:
    """Returner frame-index (0..num_frames-1) for gitt elapsed-tid.

    Deterministisk: ved elapsed=0 returneres 0. Ved fps=6 roterer
    indeksen 6 ganger per sekund.
    """
    if num_frames <= 0:
        return 0
    if fps <= 0:
        return 0
    # Frame-tick: elapsed * fps, modulo num_frames
    tick = int(math.floor(elapsed_seconds * fps))
    return tick % num_frames


def apply_palette_cycles(
    surface: pygame.Surface,
    sources: list[PaletteCycleSource],
    elapsed_seconds: float,
    night_factor: float,
) -> int:
    """Overskriv cycling-regioner på surface med frame-farger.

    Muterer surface direkte. Returnerer antall sources som faktisk
    ble tegnet (ekskluderer gated-off ved dag).

    Strategi: for hver source, beregn current frame-index og fyll
    regionen med `palette[idx]`. For gated sources ved dag, fyll
    regionen med siste palett-farge (typisk mørkeste — "off-state").
    """
    drawn = 0
    is_night = night_factor >= 0.5
    for src in sources:
        if not src.palette:
            continue
        if not src.permanent and not is_night:
            # Gated og det er dag: off-state (siste palett-farge)
            color_name = src.palette[-1]
        else:
            idx = compute_cycle_frame_index(
                elapsed_seconds, src.fps, len(src.palette),
            )
            color_name = src.palette[idx]
        color = PALETTE_NAMES.get(color_name)
        if color is None:
            continue
        pygame.draw.rect(surface, color, (src.x, src.y, src.w, src.h))
        drawn += 1
    return drawn
