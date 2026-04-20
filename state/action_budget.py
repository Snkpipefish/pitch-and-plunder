"""ActionBudget — handlings-drevet tids-modell (Fase 3 C3-0 stub).

STUB i C3-0: dataklassen er definert, men ikke koblet til noe system.
Eksisterende GameClock driver fortsatt tid i PortVillageScene. C3-1
refaktorerer til at handlinger konsumerer tid-budsjett her.

Semantikk (planlagt i C3-1):
- `phase == "day"`: spilleren er i dag-modus; handlinger trekkes fra
  `hours_used_today`. Når `hours_used_today >= day_budget_hours` →
  automatisk overgang til natt (`phase = "night"`, hours_used_today
  nullstilles ikke; brukes fortsatt som visuell progress-fraction).
- `phase == "night"`: handlinger trekkes fra `hours_used_tonight`.
  Når `hours_used_tonight >= night_budget_hours` → neste dag
  (`GameClock.day += 1`, begge hours_used nullstilles,
  `phase = "day"`, og Market.on_dawn/RegimeManager/PitchLake.on_new_day
  kalles).

`consume(hours: float) -> list[str]` returnerer hendelses-strings
(`"phase_changed"`, `"new_day"`; flere elementer mulig hvis én
handling spenner over både dag→natt og natt→ny dag).

`progress_fraction() -> float` computes day_cycle-input 0.0→1.0.
Implementeres i C3-1.
"""

from __future__ import annotations

from dataclasses import dataclass

from systems import balance as _balance


def _default_day_budget() -> float:
    return _balance.get().actions.day_budget_hours


def _default_night_budget() -> float:
    return _balance.get().actions.night_budget_hours


@dataclass
class ActionBudget:
    """Handlings-drevet tid per dag.

    C3-0 stub: felt definerte, metoder (consume, progress_fraction)
    legges til i C3-1 sammen med wiring mot GameClock og scene-input.
    """

    day_budget_hours: float = 12.0
    night_budget_hours: float = 12.0
    hours_used_today: float = 0.0
    hours_used_tonight: float = 0.0
    phase: str = "day"  # "day" | "night"

    @classmethod
    def new_default(cls) -> "ActionBudget":
        """Bygg ActionBudget med defaults fra balance.

        Egen klassemetode (ikke field(default_factory)) fordi asdict
        skal gi forutsigbare save-verdier — ved ny save kalles denne
        eksplisitt; ved load brukes lagrede verdier.
        """
        return cls(
            day_budget_hours=_default_day_budget(),
            night_budget_hours=_default_night_budget(),
            hours_used_today=0.0,
            hours_used_tonight=0.0,
            phase="day",
        )
