"""Dynamisk lyssystem med aggressiv caching.

Alle radiale gradienter pre-rendres én gang når de etterspørres første
gang, og lagres i en cache på `LightingSystem`. De tegnes per frame med
`fblits` + `BLEND_RGB_ADD` slik at lyset legger seg additivt oppå gameplay-
laget og entitetene som allerede er tegnet.

Prinsipper
----------
- **Aldri** generer gradient i game loop.
- **Aldri** bruk alpha-blending – bare ren RGB-addisjon. Gradientene er
  svarte i kantene (adderer 0) og sterkere mot sentrum.
- Lys-objekter eier *ikke* en surface. Surface-en hentes fra systemets
  cache ved tegning, slik at to lys med samme radius+farge deler surface.

Gradient-form
-------------
Kvadratisk falloff: `intensity = (1 - d/r) ** 2`. Gir en mykere, mer
"lanterne-aktig" profil enn lineær avtaking. Ved d=r/2 er intensiteten
25% – ganske lite. Det meste av lyset er konsentrert i sentrum.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import pygame


def _create_radial_gradient(radius: int, color: tuple[int, int, int]) -> pygame.Surface:
    """Bygg en radial gradient-surface egnet for `BLEND_RGB_ADD`.

    Sentrum har full farge, kantene er svarte. Tegnes ved å fylle
    konsentriske sirkler fra ytterste (svarte) til innerste (lyse) –
    hver ring overskriver forrige i sentrumsområdet.
    """
    size = radius * 2 + 1
    surf = pygame.Surface((size, size)).convert()
    surf.fill((0, 0, 0))
    # Ytterste til innerste: hver iterasjon fyller en disk som er 1 px
    # mindre og litt lysere enn forrige.
    for r in range(radius, 0, -1):
        t = 1.0 - (r / radius)  # 0 ved ytterkant, 1 ved sentrum
        intensity = t * t
        c = (
            int(color[0] * intensity),
            int(color[1] * intensity),
            int(color[2] * intensity),
        )
        pygame.draw.circle(surf, c, (radius, radius), r)
    return surf


@dataclass
class Light:
    """Ett dynamisk lys med verdensposisjon, radius og farge.

    `swing_amplitude` og `swing_period` gir valgfri horisontal sinus-
    svingning (lanterneswing). `swing_period <= 0` betyr statisk.
    """

    x: float
    y: float
    radius: int
    color: tuple[int, int, int]
    swing_amplitude: float = 0.0
    swing_period: float = 0.0
    # Individuell faseforskjell gjør det lett å variere flere lanterner
    # uten at de svinger synkront.
    swing_phase: float = 0.0
    # Cache: settes av LightingSystem første gang lyset tegnes, slik at
    # gradient-oppslaget bare skjer en gang.
    _gradient: pygame.Surface | None = field(default=None, repr=False)

    def horizontal_offset(self, elapsed: float) -> float:
        if self.swing_period <= 0.0:
            return 0.0
        phase = (2.0 * math.pi * elapsed / self.swing_period) + self.swing_phase
        return self.swing_amplitude * math.sin(phase)


class LightingSystem:
    """Cacher pre-rendrede radiale gradienter og tegner lys i batch."""

    def __init__(self) -> None:
        self._cache: dict[tuple[int, tuple[int, int, int]], pygame.Surface] = {}

    def get_gradient(self, radius: int, color: tuple[int, int, int]) -> pygame.Surface:
        key = (radius, color)
        grad = self._cache.get(key)
        if grad is None:
            grad = _create_radial_gradient(radius, color)
            self._cache[key] = grad
        return grad

    def prewarm(self, specs: list[tuple[int, tuple[int, int, int]]]) -> None:
        """Bygg alle gradienter som trengs for en scene én gang ved init."""
        for radius, color in specs:
            self.get_gradient(radius, color)

    def draw(
        self,
        target: pygame.Surface,
        lights: list[Light],
        camera_x: float,
        elapsed: float,
        night_factor: float = 1.0,
    ) -> None:
        """Tegn alle lys med `BLEND_RGB_ADD` i én fblits-batch.

        `night_factor` (C2.5-8b) gater lysene etter dag/natt-syklusen:
        - 1.0 (full natt): alle lys tegnes
        - 0.0 (full dag): ingen lys tegnes
        - Delvis (sunset/sunrise): threshold 0.5 for snap-on/off

        Threshold-modellen er pragmatisk MVP — BLEND_RGB_ADD støtter
        ikke enkel alpha-skalering uten intermediate surface. En
        smooth-fade-implementering (cached dimmed gradients) kan
        legges til i senere polish hvis snap er synlig plagsom.
        Sunset/sunrise-perioden er ~8% av dagen (ca 14 sek på 180 s/
        dag), så snap vil være over på et øyeblikk.
        """
        if not lights or night_factor < 0.5:
            return
        batch: list[tuple[pygame.Surface, tuple[int, int]]] = []
        for light in lights:
            if light._gradient is None:
                light._gradient = self.get_gradient(light.radius, light.color)
            grad = light._gradient
            offset = light.horizontal_offset(elapsed)
            screen_x = int(light.x - camera_x + offset) - light.radius
            screen_y = int(light.y) - light.radius
            batch.append((grad, (screen_x, screen_y)))
        target.fblits(batch, pygame.BLEND_RGB_ADD)

    @property
    def cached_count(self) -> int:
        return len(self._cache)
