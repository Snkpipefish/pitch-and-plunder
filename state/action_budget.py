"""ActionBudget — handlings-drevet tids-modell (Fase 3 C3-1).

Håndterer handlings-budsjett per dag (dag-timer + natt-timer). Metoder
(`consume`, `progress_fraction`) er definert i C3-1, men ennå IKKE
koblet til noen scene eller input-logikk — eksisterende PortVillageScene
bruker fortsatt GameClock.update(dt) for real-time dag-progresjon.
Wiring skjer i senere commits når dialoger kaller `consume()` for sine
handlinger (C3-3 ff.).

Semantikk (FASE_3.md §1.3, implementert i C3-1):

- `phase == "day"`: handlinger trekkes fra `hours_used_today`. Når
  `hours_used_today >= day_budget_hours` → automatisk overgang til
  natt (`phase = "night"`). Verdien `hours_used_today` nullstilles
  IKKE ved phase-change — den settes til `day_budget_hours` slik at
  `progress_fraction` kan utlede visuell state under natt-fasen.
- `phase == "night"`: handlinger trekkes fra `hours_used_tonight`.
  Når `hours_used_tonight >= night_budget_hours` → neste dag:
  `hours_used_today = 0`, `hours_used_tonight = 0`, `phase = "day"`.
  Det er *caller* som har ansvar for å øke `GameClock.day` og kalle
  `Market.on_dawn`/`RegimeManager`/`PitchLake.on_new_day` — denne
  klassen signaliserer kun overgangen via `"new_day"`-event.

`consume(hours)` er rekursiv nok til å spenne over flere faser og
flere dager i ett kall. Dette er nødvendig for flerdagers-reise der
én handling (start_voyage) forbruker N×24 timer og utløser N
`new_day`-hendelser (FASE_3.md §1.4).

`progress_fraction()` returnerer 0.0→1.0 som lineær progress gjennom
et døgn. Mapping (valgt så døgnet blir symmetrisk og enkelt å teste):
- `phase == "day"`:  [0.0, 0.5] basert på hours_used_today / day_budget
- `phase == "night"`: [0.5, 1.0] basert på hours_used_tonight / night_budget
Celestial/DayCycle-adapteren (renderer-side) kan remappe til
sunrise/day/sunset/night-vinduene fra `systems/day_cycle.py` når
wiring lander i senere commit. ActionBudget selv forblir rendering-
agnostisk.
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

    C3-1: metoder implementert, men ikke wiret fra game loop ennå.
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

    def consume(self, hours: float) -> list[str]:
        """Forbruk `hours` fra budsjettet. Returnér hendelses-strings.

        Hendelser kan være `"phase_changed"` (dag → natt innenfor samme
        dag) og `"new_day"` (natt → ny dag; kan skje flere ganger i ett
        kall hvis `hours` spenner flere døgn, typisk under seiling).

        Semantikk per §1.3 i FASE_3.md:
        - Negative eller null hours → ingen effekt, tom hendelses-liste.
        - Verdi som fyller dag-budsjettet eksakt (hours_used_today
          når day_budget_hours) → fase flipper til night umiddelbart.
        - Verdi som fyller natt-budsjettet eksakt → ny dag starter.
        - Eventuell rest etter fase-flip forbrukes i neste fase (som
          kan utløse enda flere events).

        Budsjett-grenser klampes mot negative verdier i state: hvis en
        caller manuelt setter hours_used_today > day_budget_hours, kan
        available bli negativ — vi klamper tiL 0 for å unngå uendelig
        loop.
        """
        if hours <= 0:
            return []
        events: list[str] = []
        remaining = hours
        # Defensivt: maks 100 fase-overganger per kall (≈50 døgn) for å
        # fange bugs som ellers ville loopet uendelig. Normalt
        # bruksmønster: maks noen få phase_changed + 1–5 new_day ved
        # flerdagers reise.
        safety = 100
        while remaining > 0 and safety > 0:
            safety -= 1
            if self.phase == "day":
                available = max(
                    0.0, self.day_budget_hours - self.hours_used_today
                )
                if remaining < available:
                    self.hours_used_today += remaining
                    remaining = 0.0
                else:
                    # Forbruk resten av dagen, flip til natt
                    self.hours_used_today = self.day_budget_hours
                    remaining -= available
                    self.phase = "night"
                    # hours_used_tonight er 0 ved inngang til natt; hvis
                    # tidligere rest skulle ligge der er det caller-bug,
                    # men vi nullstiller defensivt.
                    self.hours_used_tonight = 0.0
                    events.append("phase_changed")
            else:  # night
                available = max(
                    0.0, self.night_budget_hours - self.hours_used_tonight
                )
                if remaining < available:
                    self.hours_used_tonight += remaining
                    remaining = 0.0
                else:
                    # Forbruk resten av natten, flip til ny dag
                    remaining -= available
                    self.hours_used_today = 0.0
                    self.hours_used_tonight = 0.0
                    self.phase = "day"
                    events.append("new_day")
        return events

    def progress_fraction(self) -> float:
        """Returnér 0.0→1.0 progress gjennom døgnet.

        Mapping:
        - phase == "day": [0.0, 0.5] lineært etter hours_used_today
        - phase == "night": [0.5, 1.0] lineært etter hours_used_tonight

        Dette er en enkel, rendering-agnostisk modell. Senere wiring
        (adapter mot systems/day_cycle.py) kan remappe til sunrise/
        daylight/sunset/moonlit-vinduer hvis ønsket.

        Ugyldige budsjett-verdier (≤0) returnerer fase-grense-verdien
        (0.0 for dag, 0.5 for natt).
        """
        if self.phase == "day":
            if self.day_budget_hours <= 0.0:
                return 0.0
            frac = self.hours_used_today / self.day_budget_hours
            frac = max(0.0, min(1.0, frac))
            return frac * 0.5
        # night
        if self.night_budget_hours <= 0.0:
            return 0.5
        frac = self.hours_used_tonight / self.night_budget_hours
        frac = max(0.0, min(1.0, frac))
        return 0.5 + frac * 0.5
