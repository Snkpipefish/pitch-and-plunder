"""Generisk toast-system: midlertidige tekst-varsler med fadeout.

Brukes for daggry-varsler (Commit 5E), bek-produksjonsvarsler (Commit 6),
og senere pris-/mistanke-varsler i Fase 3/5.

Designvalg:
- **Pre-rendret tekst i `__init__`**. Ingen font.render per frame.
- **Per-surface alpha** for fade-out. Unngår per-pixel-blit per frame.
  (pygame-ce 2.5.7 har en issue med `set_alpha(None)` på convert_alpha-
  surfaces; vi bruker kun int-verdier — se `entities/celestial.py`.)
- **Fade-vindu**: alpha holder 255 frem til `fade_start` sekunder igjen,
  deretter lineært til 0. Default fade_start = 1/3 av duration.
- **Stateless kø**: `ToastQueue` holder liste, oppdaterer og rydder selv.
"""

from __future__ import annotations

import pygame


#: Default fade-start som brøk av duration (siste 1/3 av levetiden fader ut).
DEFAULT_FADE_FRACTION = 1.0 / 3.0


class Toast:
    """Én midlertidig tekst-visning med fadeout."""

    def __init__(
        self,
        font: pygame.font.Font,
        text: str,
        color: tuple[int, int, int],
        duration: float = 3.0,
        fade_start: float | None = None,
    ) -> None:
        """`fade_start` er antall sekunder igjen når alpha starter å falle.
        Default er `duration * DEFAULT_FADE_FRACTION`.
        """
        self._surf = font.render(text, False, color).convert_alpha()
        self._duration = duration
        self._remaining = duration
        if fade_start is None:
            fade_start = duration * DEFAULT_FADE_FRACTION
        self._fade_start = max(0.0, fade_start)

    @property
    def is_alive(self) -> bool:
        return self._remaining > 0.0

    @property
    def width(self) -> int:
        return self._surf.get_width()

    @property
    def height(self) -> int:
        return self._surf.get_height()

    def update(self, dt: float) -> None:
        """Reduser resterende levetid. Fjern fra kø når `is_alive` er False."""
        self._remaining -= dt

    def current_alpha(self) -> int:
        """Returner gjeldende alpha (0–255) basert på `_remaining`."""
        if self._remaining <= 0.0:
            return 0
        if self._remaining >= self._fade_start:
            return 255
        if self._fade_start <= 0.0:
            return 0
        return max(0, min(255, int(255 * self._remaining / self._fade_start)))

    def draw(
        self,
        surface: pygame.Surface,
        pos: tuple[int, int],
    ) -> None:
        """Blit toast med gjeldende alpha. No-op hvis utløpt."""
        if self._remaining <= 0.0:
            return
        self._surf.set_alpha(self.current_alpha())
        surface.blit(self._surf, pos)


class ToastQueue:
    """Stack av aktive toasts. Nyeste vises nederst, eldre stables oppover.

    Alle toasts sentreres horisontalt om `center_x`. Nederste toast tegnes
    med sin øvre kant ved `baseline_y`; neste tegnes 2 px over den, osv.
    """

    def __init__(self, baseline_y: int, center_x: int) -> None:
        self._toasts: list[Toast] = []
        self._baseline_y = baseline_y
        self._center_x = center_x

    @property
    def count(self) -> int:
        return len(self._toasts)

    def push(self, toast: Toast) -> None:
        self._toasts.append(toast)

    def update(self, dt: float) -> None:
        for toast in self._toasts:
            toast.update(dt)
        # Fjern utløpte (ryddig + stabil rekkefølge)
        self._toasts = [t for t in self._toasts if t.is_alive]

    def draw(self, surface: pygame.Surface) -> None:
        # Tegn nyeste nederst, eldre over
        y = self._baseline_y
        for toast in reversed(self._toasts):
            y_top = y - toast.height
            x = self._center_x - toast.width // 2
            toast.draw(surface, (x, y_top))
            y = y_top - 2
