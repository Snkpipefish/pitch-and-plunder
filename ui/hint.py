"""Hint-tekst nederst på skjermen.

En `HintIndicator` holder to pre-rendrede tekstsurfaces (far/near) og
viser den som passer til gjeldende spilletilstand. Teksten rendres kun
én gang ved konstruksjon; `draw()` gjør en enkelt blit uten allokering.

Trukket ut av `scenes/village.py` i Fase 2A / Commit 1 for å samle spredt
hint-logikk på ett sted og forenkle scene-filen.
"""

from __future__ import annotations

import pygame


class HintIndicator:
    """To-tilstand hint-tekst: "far" når spilleren ikke kan interagere,
    "near" når hun kan. Begge surfaces pre-rendres i `__init__`.
    """

    def __init__(
        self,
        font: pygame.font.Font,
        far_text: str,
        near_text: str,
        far_color: tuple[int, int, int],
        near_color: tuple[int, int, int],
        pos: tuple[int, int],
    ) -> None:
        self._far = font.render(far_text, False, far_color).convert_alpha()
        self._near = font.render(near_text, False, near_color).convert_alpha()
        self._pos = pos

    def draw(self, surface: pygame.Surface, show_near: bool) -> None:
        """Blit riktig hint-variant til `surface`."""
        surface.blit(self._near if show_near else self._far, self._pos)
