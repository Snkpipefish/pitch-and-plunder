"""Sentral tids-autoritet.

`GameClock` er den eneste autoriteten på hva dagen er og hvor langt på dagen
vi er. Alle systemer som responderer på tid (Market, RegimeManager,
PitchLake, dag/natt-syklus senere) abonnerer ved å sjekke hendelses-lista
fra `update()`.

Design:
- `seconds_per_day` er per-instans felt med initial verdi fra
  `balance.time.seconds_per_day_in_port`. Verdien er cachet innenfor
  klokke-instansen — `update()` re-leser ALDRI balance, slik at
  akselererte test-klokker og pågående dager ikke hopper.
- Hot-reload av seconds_per_day er "session-applicable" per spec §4.4.
  main.py fanger F5-hendelsen, reloader balance, og synkroniserer
  `state.clock.seconds_per_day` på neste new_day-event — ikke mid-day.
- `update(dt)` returnerer liste av hendelses-strings (foreløpig kun
  `"new_day"`). Flere dag-skift i én update (om dt er stor) gir flere
  elementer, slik at abonnenter kan prosessere hvert skifte.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from systems import balance as _balance


def _default_seconds_per_day() -> float:
    """Hentes fra balance; brukes som default for nye GameClock-instanser."""
    return _balance.get().time.seconds_per_day_in_port


@dataclass
class GameClock:
    """Hold dag-teller og fremdrift i gjeldende dag."""

    day: int = 1
    seconds_into_day: float = 0.0
    seconds_per_day: float = field(default_factory=_default_seconds_per_day)

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
