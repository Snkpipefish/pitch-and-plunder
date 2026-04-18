"""Parallax-lag-system.

Hvert lag er en pre-rendret `pygame.Surface` med en farts-multiplikator som
styrer hvor fort det scroller relativt til kameraet:

- `speed` < 1.0 : langsommere enn kamera (bakgrunn, fjerne fjell, himmel)
- `speed` == 1.0 : følger kamera (gameplay-plan der spilleren står)
- `speed` > 1.0 : raskere enn kamera (forgrunn, palmeblader)

Alle lag pre-rendres én gang ved scene-init. Kun blit-operasjoner skjer per
frame, alle med heltalls-offset for å unngå sub-pixel-blending.

Breddeberegning
---------------
For at et lag skal dekke skjermen over hele kamera-intervallet [0, max_cam]
må surfaken være minst:

    RENDER_WIDTH + ceil(max_cam * speed)

`required_layer_width()` gjør denne beregningen.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import ceil

import pygame


@dataclass
class ParallaxLayer:
    """Ett parallax-lag: en pre-rendret Surface + farts-multiplikator."""

    surface: pygame.Surface
    speed: float


class ParallaxRenderer:
    """Tegner flere parallax-lag med heltalls-offset.

    Bruker `fblits` for å batche alle lag-blittene i én SDL-kall. Det gir
    en liten ytelsesgevinst på svak CPU (T4200) fordi pygame-CE hopper over
    per-element type-sjekk.
    """

    def __init__(self, layers: list[ParallaxLayer]) -> None:
        self._layers = layers

    @property
    def layers(self) -> list[ParallaxLayer]:
        return self._layers

    def draw(
        self,
        target: pygame.Surface,
        camera_x: float,
        start: int = 0,
        stop: int | None = None,
    ) -> None:
        """Tegn et sammenhengende lagintervall [start, stop) til `target`.

        Uten argumenter tegnes alle lag. `start`/`stop` lar kalleren splitte
        tegningen i to rundt entiteter som skal ligge *mellom* lagene (f.eks.
        spiller og NPC skal ligge over gameplay-laget men bak forgrunnen).
        """
        if stop is None:
            stop = len(self._layers)
        batch = [
            (self._layers[i].surface, (int(-camera_x * self._layers[i].speed), 0))
            for i in range(start, stop)
        ]
        target.fblits(batch)


def required_layer_width(
    world_width: int, render_width: int, speed: float
) -> int:
    """Minste surface-bredde som dekker skjermen over hele kameraintervallet.

    >>> required_layer_width(1600, 640, 0.2)
    833
    >>> required_layer_width(1600, 640, 1.0)
    1601
    >>> required_layer_width(1600, 640, 1.3)
    1889
    """
    max_camera_x = world_width - render_width
    return render_width + ceil(max_camera_x * speed) + 1


class Camera:
    """Enkel horisontal kamera med klamping til verdensbredde."""

    def __init__(self, world_width: int, render_width: int) -> None:
        self._min_x = 0.0
        self._max_x = float(max(0, world_width - render_width))
        self.x: float = 0.0

    def move(self, dx: float) -> None:
        self.x = max(self._min_x, min(self._max_x, self.x + dx))

    def set_x(self, x: float) -> None:
        self.x = max(self._min_x, min(self._max_x, x))

    @property
    def max_x(self) -> float:
        return self._max_x
