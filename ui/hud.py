"""HUD for village-scenen: Tortuga / gull / dag / bek-drift, øverst venstre.

Fargekoding er bevisst:
- Sted         (moon-halo ) : "dette er et sted"
- Gull         (lantern   ) : varmt, tied til rikdom og tavernaens verden
- Dag          (stone-lit ) : kaldt, tied til institusjonell tid / Børshuset
- Bek (drift)  (ember     ) : varm-rød, tied til Pitch Lake og råvare-strøm
- Bek (stopp)  (fog       ) : nøytral dempet, signaliserer manglende drift

Tekst-surfaces caches og re-rendres bare når verdien endrer seg – settere
er no-ops hvis input er likt forrige verdi.
"""

from __future__ import annotations

import pygame

import constants


PADDING = 4
LINE_HEIGHT = 10  # 8 px glyff + 2 px linjeavstand


class Hud:
    """HUD-widget: sted, gull, dag, og bek-produksjonsstatus."""

    def __init__(
        self,
        font: pygame.font.Font,
        place: str,
        gold: int,
        day: int,
        pitch_per_day: int = 0,
        pitch_upkeep: int = 0,
        pitch_halted: bool = False,
    ) -> None:
        self._font = font
        self._place: str | None = None
        self._gold: int | None = None
        self._day: int | None = None
        self._pitch_key: tuple[int, int, bool] | None = None
        self._place_surf: pygame.Surface | None = None
        self._gold_surf: pygame.Surface | None = None
        self._day_surf: pygame.Surface | None = None
        # pitch_surf er None når produksjon er 0 OG ikke halted (skjuler linja).
        self._pitch_surf: pygame.Surface | None = None
        self.set_place(place)
        self.set_gold(gold)
        self.set_day(day)
        self.set_pitch_status(pitch_per_day, pitch_upkeep, pitch_halted)

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

    def set_pitch_status(
        self,
        pitch_per_day: int,
        upkeep: int,
        halted: bool,
    ) -> None:
        """Oppdater bek-linja basert på produksjons-status.

        - halted=True → "Bek: ingen drift" i dempet COLOR_FOG.
        - ellers pitch_per_day>0 → "Bek: +X/dag (-Y d.)" i COLOR_EMBER.
        - ellers (per_day=0, ikke halted) → ingen linje (skjult).
        """
        key = (pitch_per_day, upkeep, halted)
        if key == self._pitch_key:
            return
        self._pitch_key = key
        if halted:
            self._pitch_surf = self._font.render(
                "Bek: ingen drift", False, constants.COLOR_FOG
            ).convert_alpha()
        elif pitch_per_day > 0:
            self._pitch_surf = self._font.render(
                f"Bek: +{pitch_per_day}/dag (-{upkeep} d.)",
                False,
                constants.COLOR_EMBER,
            ).convert_alpha()
        else:
            self._pitch_surf = None

    def draw(self, surface: pygame.Surface) -> None:
        assert self._place_surf is not None
        assert self._gold_surf is not None
        assert self._day_surf is not None
        surface.blit(self._place_surf, (PADDING, PADDING))
        surface.blit(self._gold_surf, (PADDING, PADDING + LINE_HEIGHT))
        surface.blit(self._day_surf, (PADDING, PADDING + 2 * LINE_HEIGHT))
        if self._pitch_surf is not None:
            surface.blit(
                self._pitch_surf, (PADDING, PADDING + 3 * LINE_HEIGHT)
            )
