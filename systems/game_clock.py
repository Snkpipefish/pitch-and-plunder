"""Sentral tids-autoritet.

`GameClock` er den eneste autoriteten på hva dagen er og hvor langt på dagen
vi er. Alle systemer som responderer på tid (Market, RegimeManager,
PitchLake, dag/natt-syklus senere) abonnerer ved å sjekke hendelses-lista
fra `update()`.

Design:
- `seconds_per_day` er per-instans felt slik at tester kan akselerere tiden
  og saves bevarer ratio hvis balanse-konstanten endres mellom spillversjoner.
  Default-verdi hentes fra `constants.SECONDS_PER_DAY`.
- `update(dt)` returnerer liste av hendelses-strings (foreløpig kun
  `"new_day"`). Listen kan være tom.
- Flere dag-skift i én update (om dt er stor) gir flere `"new_day"`-elementer
  i listen, slik at abonnenter kan prosessere hvert skifte.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import constants


@dataclass
class GameClock:
    """Hold dag-teller og fremdrift i gjeldende dag."""

    day: int = 1
    seconds_into_day: float = 0.0
    seconds_per_day: float = field(
        default_factory=lambda: constants.SECONDS_PER_DAY
    )

    def update(self, dt: float) -> list[str]:
        """Oppdater klokken med `dt` sekunder.

        Returnerer liste av hendelses-strings som skjedde denne oppdateringen.
        Foreløpig bare `"new_day"` (én per dag-skift; flere elementer hvis
        `dt` spenner over flere dager).
        """
        self.seconds_into_day += dt
        events: list[str] = []
        while self.seconds_into_day >= self.seconds_per_day:
            self.seconds_into_day -= self.seconds_per_day
            self.day += 1
            events.append("new_day")
        return events

    def progress_fraction(self) -> float:
        """0.0 ved daggry, 1.0 ved midnatt. Til dag/natt-syklus senere."""
        if self.seconds_per_day <= 0.0:
            return 0.0
        return self.seconds_into_day / self.seconds_per_day
