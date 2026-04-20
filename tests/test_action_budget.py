"""Tester for ActionBudget.consume() og progress_fraction() — Fase 3 C3-1.

consume() er semantisk hjerte av handlings-tid-modellen:
- Partielt forbruk innen dag-/natt-budsjett: ingen events
- Grense overskridelse: phase_changed (dag→natt) eller new_day (natt→neste dag)
- Multi-dag forbruk (seiling): flere new_day events sekvensielt
- Negative/null timer: ingen effekt

progress_fraction() returnerer 0.0→1.0 og brukes senere av day_cycle-
adapteren. Semantikken er enkel lineær mapping (dag → [0, 0.5], natt →
[0.5, 1.0]).

ActionBudget er IKKE wiret til noen scene eller game loop i C3-1 —
disse testene verifiserer kun klassens egen semantikk, uavhengig av
rendering.
"""

from __future__ import annotations

import pytest

from state.action_budget import ActionBudget


# -----------------------------------------------------------------------------
# Konstruktor / defaults
# -----------------------------------------------------------------------------


def test_default_construction() -> None:
    ab = ActionBudget()
    assert ab.day_budget_hours == 12.0
    assert ab.night_budget_hours == 12.0
    assert ab.hours_used_today == 0.0
    assert ab.hours_used_tonight == 0.0
    assert ab.phase == "day"


def test_new_default_reads_balance() -> None:
    ab = ActionBudget.new_default()
    # balance.json v2 har 12.0/12.0 som default
    assert ab.day_budget_hours == 12.0
    assert ab.night_budget_hours == 12.0
    assert ab.phase == "day"


# -----------------------------------------------------------------------------
# consume() — grunnleggende semantikk
# -----------------------------------------------------------------------------


def test_consume_zero_is_noop() -> None:
    ab = ActionBudget.new_default()
    events = ab.consume(0.0)
    assert events == []
    assert ab.hours_used_today == 0.0
    assert ab.phase == "day"


def test_consume_negative_is_noop() -> None:
    ab = ActionBudget.new_default()
    events = ab.consume(-5.0)
    assert events == []
    assert ab.hours_used_today == 0.0
    assert ab.phase == "day"


def test_consume_partial_day_no_events() -> None:
    """Forbruk godt innenfor dag-budsjett → ingen events."""
    ab = ActionBudget.new_default()
    events = ab.consume(3.0)
    assert events == []
    assert ab.hours_used_today == 3.0
    assert ab.phase == "day"


def test_consume_multiple_partial_day_accumulates() -> None:
    ab = ActionBudget.new_default()
    assert ab.consume(2.0) == []
    assert ab.consume(3.5) == []
    assert ab.consume(1.5) == []
    assert ab.hours_used_today == 7.0
    assert ab.phase == "day"


# -----------------------------------------------------------------------------
# consume() — dag → natt overgang
# -----------------------------------------------------------------------------


def test_consume_exact_day_budget_flips_to_night() -> None:
    """Eksakt dag-budsjett → phase_changed, ingen rest til natt."""
    ab = ActionBudget.new_default()
    events = ab.consume(12.0)
    assert events == ["phase_changed"]
    assert ab.phase == "night"
    assert ab.hours_used_today == 12.0
    assert ab.hours_used_tonight == 0.0


def test_consume_over_day_budget_spills_to_night() -> None:
    """Mer enn dag-budsjett → phase_changed, rest til natt."""
    ab = ActionBudget.new_default()
    events = ab.consume(15.0)
    assert events == ["phase_changed"]
    assert ab.phase == "night"
    assert ab.hours_used_today == 12.0
    assert ab.hours_used_tonight == 3.0


def test_consume_after_partial_day_flip() -> None:
    """Forbruk partielt dag, deretter total som spiller over til natt."""
    ab = ActionBudget.new_default()
    ab.consume(8.0)  # hours_used_today=8, phase=day
    events = ab.consume(6.0)  # passer 4 inn i dag, 2 til natt
    assert events == ["phase_changed"]
    assert ab.phase == "night"
    assert ab.hours_used_today == 12.0
    assert ab.hours_used_tonight == 2.0


# -----------------------------------------------------------------------------
# consume() — natt → ny dag overgang
# -----------------------------------------------------------------------------


def test_consume_exact_night_budget_new_day() -> None:
    ab = ActionBudget(phase="night", hours_used_today=12.0)
    events = ab.consume(12.0)
    assert events == ["new_day"]
    assert ab.phase == "day"
    assert ab.hours_used_today == 0.0
    assert ab.hours_used_tonight == 0.0


def test_consume_night_partial_no_event() -> None:
    ab = ActionBudget(phase="night", hours_used_today=12.0)
    events = ab.consume(5.0)
    assert events == []
    assert ab.phase == "night"
    assert ab.hours_used_tonight == 5.0


def test_consume_over_night_budget_spills_to_next_day() -> None:
    ab = ActionBudget(phase="night", hours_used_today=12.0)
    events = ab.consume(15.0)
    assert events == ["new_day"]
    assert ab.phase == "day"
    assert ab.hours_used_today == 3.0
    assert ab.hours_used_tonight == 0.0


# -----------------------------------------------------------------------------
# consume() — multi-event i én call
# -----------------------------------------------------------------------------


def test_consume_spans_day_and_night_and_new_day() -> None:
    """Én consume som tar oss fra dag via natt til ny dag.

    Fra starten av dag-1: 24 timer = fyller dag-budsjett og natt-budsjett,
    lander på dag-2 start.
    """
    ab = ActionBudget.new_default()
    events = ab.consume(24.0)
    assert events == ["phase_changed", "new_day"]
    assert ab.phase == "day"
    assert ab.hours_used_today == 0.0
    assert ab.hours_used_tonight == 0.0


def test_consume_spans_multiple_days_voyage_scenario() -> None:
    """3-dagers reise: forbruker 3 × 24 = 72 timer.

    Start: dag 1, phase=day, hours_used_today=0.
    Slutt: dag 4 (etter 3 dag-skift), phase=day, hours_used_today=0.

    Forventer 3 new_day-hendelser (og 3 phase_changed for dag→natt).
    Rekkefølgen er phase_changed, new_day, phase_changed, new_day,
    phase_changed, new_day.
    """
    ab = ActionBudget.new_default()
    events = ab.consume(72.0)
    # 3 komplette døgn = 3 phase_changed + 3 new_day, sekvensielt
    assert events.count("phase_changed") == 3
    assert events.count("new_day") == 3
    assert len(events) == 6
    # Riktig rekkefølge: PC, ND, PC, ND, PC, ND
    assert events == [
        "phase_changed", "new_day",
        "phase_changed", "new_day",
        "phase_changed", "new_day",
    ]
    assert ab.phase == "day"
    assert ab.hours_used_today == 0.0
    assert ab.hours_used_tonight == 0.0


def test_consume_spans_2_5_days_ends_in_night() -> None:
    """60 timer = 2 nye dager + dag-budsjett av tredje.

    24 h fyller dag(12) + natt(12) og utløser 1 × phase_changed + 1 × new_day.
    48 h = 2 fulle døgn = 2 × [phase_changed, new_day], ender phase=day 0/0.
    60 h = 48 + 12: de neste 12 fyller dag-budsjett og utløser et siste
    phase_changed uten new_day. Sluttilstand: phase=night, today=12, tonight=0.
    """
    ab = ActionBudget.new_default()
    events = ab.consume(60.0)
    # 2 komplette døgn + 12 dag-timer på tredje → tredje phase_changed
    assert events == [
        "phase_changed", "new_day",
        "phase_changed", "new_day",
        "phase_changed",
    ]
    assert ab.phase == "night"
    assert ab.hours_used_today == 12.0
    assert ab.hours_used_tonight == 0.0


# -----------------------------------------------------------------------------
# consume() — grense-situasjoner
# -----------------------------------------------------------------------------


def test_consume_exact_boundary_through_tiny_steps() -> None:
    ab = ActionBudget.new_default()
    # Fyll opp dag-budsjett i mange små steg
    for _ in range(47):  # 47 × 0.25 = 11.75 h
        ab.consume(0.25)
    assert ab.hours_used_today == pytest.approx(11.75)
    assert ab.phase == "day"
    # Siste step krysser grensen
    events = ab.consume(0.25)  # 11.75 + 0.25 = 12.0 → flip
    assert events == ["phase_changed"]
    assert ab.phase == "night"
    assert ab.hours_used_today == 12.0


def test_consume_mid_night_partial_no_event() -> None:
    ab = ActionBudget(
        phase="night", hours_used_today=12.0, hours_used_tonight=3.0
    )
    events = ab.consume(2.0)
    assert events == []
    assert ab.hours_used_tonight == 5.0
    assert ab.phase == "night"


# -----------------------------------------------------------------------------
# progress_fraction()
# -----------------------------------------------------------------------------


def test_progress_fraction_start_of_day() -> None:
    ab = ActionBudget.new_default()
    assert ab.progress_fraction() == 0.0


def test_progress_fraction_mid_day() -> None:
    ab = ActionBudget.new_default()
    ab.hours_used_today = 6.0  # halfway through 12-h day
    # Mapping: day [0, 0.5] → halvveis = 0.25
    assert ab.progress_fraction() == pytest.approx(0.25)


def test_progress_fraction_end_of_day() -> None:
    ab = ActionBudget.new_default()
    ab.hours_used_today = 12.0  # fullt dag-budsjett, enda dag-fase
    # Mapping: 1.0 × 0.5 = 0.5 (fase-grense)
    assert ab.progress_fraction() == pytest.approx(0.5)


def test_progress_fraction_start_of_night() -> None:
    ab = ActionBudget(phase="night", hours_used_today=12.0)
    # Natt-start: 0.5 + 0/12 × 0.5 = 0.5
    assert ab.progress_fraction() == pytest.approx(0.5)


def test_progress_fraction_mid_night() -> None:
    ab = ActionBudget(
        phase="night", hours_used_today=12.0, hours_used_tonight=6.0
    )
    # Midt i natt: 0.5 + 0.5 × 0.5 = 0.75
    assert ab.progress_fraction() == pytest.approx(0.75)


def test_progress_fraction_end_of_night() -> None:
    ab = ActionBudget(
        phase="night", hours_used_today=12.0, hours_used_tonight=12.0
    )
    # Slutten av natten (før new_day): 0.5 + 1.0 × 0.5 = 1.0
    assert ab.progress_fraction() == pytest.approx(1.0)


def test_progress_fraction_clamped_to_day_boundary() -> None:
    """Overflyt i hours_used_today klampes ved 0.5."""
    ab = ActionBudget(hours_used_today=20.0)  # > day_budget_hours
    # Uten eksplisitt phase-flip: verdi klampes ved 0.5
    assert ab.progress_fraction() == pytest.approx(0.5)


def test_progress_fraction_zero_budgets_edge_case() -> None:
    """Budget=0 bør ikke crashe — returnér fase-grense."""
    ab = ActionBudget(day_budget_hours=0.0)
    assert ab.progress_fraction() == 0.0
    ab2 = ActionBudget(phase="night", night_budget_hours=0.0)
    assert ab2.progress_fraction() == 0.5
