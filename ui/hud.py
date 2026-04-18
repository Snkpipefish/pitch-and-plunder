"""HUD for village-scenen: Tortuga / gull / dag, oeverst venstre.

Fargekoding er bevisst:
- Sted   (moon-halo  ) : "dette er et sted"
- Gull   (lantern     ) : varmt, tied til rikdom og tavernaens verden
- Dag    (stone-lit   ) : kaldt, tied til institusjonell tid / Borshuset

Tekst-surfaces caches og re-rendres bare naar verdien endrer seg – settere
er no-ops hvis input er likt forrige verdi.
"""

from __future__ import annotations

import pygame

import constants


PADDING = 4
LINE_HEIGHT = 10  # 8 px glyff + 2 px linjeavstand


class Hud:
    """Statisk HUD-widget for Fase 1: sted, gull, dag."""

    def __init__(
        self,
        font: pygame.font.Font,
        place: str,
        gold: int,
        day: int,
    ) -> None:
        self._font = font
        self._place: str | None = None
        self._gold: int | None = None
        self._day: int | None = None
        self._place_surf: pygame.Surface | None = None
        self._gold_surf: pygame.Surface | None = None
        self._day_surf: pygame.Surface | None = None
        self.set_place(place)
        self.set_gold(gold)
        self.set_day(day)

    def set_place(self, place: str) -> None:
        if place == self._place:
            return
        self._place = place
        self._place_surf = self._font.render(
            place, False, constants.COLOR_MOON_HALO
        ).convert_alpha()

    def set_gold(self, gold: int) -> None:
        if gold == self._gold:
            return
        self._gold = gold
        self._gold_surf = self._font.render(
            f"{gold} d.", False, constants.COLOR_LANTERN
        ).convert_alpha()

    def set_day(self, day: int) -> None:
        if day == self._day:
            return
        self._day = day
        self._day_surf = self._font.render(
            f"Dag {day}", False, constants.COLOR_STONE_LIT
        ).convert_alpha()

    def draw(self, surface: pygame.Surface) -> None:
        assert self._place_surf is not None
        assert self._gold_surf is not None
        assert self._day_surf is not None
        surface.blit(self._place_surf, (PADDING, PADDING))
        surface.blit(self._gold_surf, (PADDING, PADDING + LINE_HEIGHT))
        surface.blit(self._day_surf, (PADDING, PADDING + 2 * LINE_HEIGHT))
