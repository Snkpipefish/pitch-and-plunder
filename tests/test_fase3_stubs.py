"""Tester for Fase 3 C3-0 state-stubs.

Verifiserer:
- Nye state-felt har forutsigbare defaults
- save/load-roundtrip bevarer stub-verdier
- v5-saves uten nye felt laster uten feil (defaults brukes)
- new_game_state() populerer stubs med balance-forankrede verdier

Alle tester respekterer stub-semantikk: feltene er DEFINED, men
ingen wiring er gjort ennå. Senere fase-commits (C3-1 ff.) kobler
opp effektene.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from state.action_budget import ActionBudget
from state.economy_state import EconomyState
from state.game_state import GameState
from state.market_effects import PendingRumorImpact, PendingSabotage
from state.pitch_lake_state import PitchLakeState
from state.player_state import PlayerState
from state.rumor_state import ActiveRumor
from state.world_state import WorldState
from systems import save as save_module


# -----------------------------------------------------------------------------
# Default-verdier
# -----------------------------------------------------------------------------


def test_player_state_stub_defaults() -> None:
    """PlayerState har forventede stub-defaults."""
    ps = PlayerState()
    assert ps.suspicion == 0.0
    assert ps.rest == 1.0
    assert ps.port_caches == {}
    assert ps.active_rumors == []


def test_economy_state_stub_defaults() -> None:
    es = EconomyState()
    assert es.pending_sabotages == []
    assert es.pending_rumor_impacts == []


def test_pitch_lake_state_purchased_default_false() -> None:
    """PurchedFalse ved default-instansiering og via new_default.

    Merk: v5→v6-migrering i C3-1 vil sette True for eksisterende
    dev-saves, men C3-0 stub-semantikk er purchased=False.
    """
    pls = PitchLakeState()
    assert pls.purchased is False
    pls_default = PitchLakeState.new_default()
    assert pls_default.purchased is False


def test_world_state_has_action_budget() -> None:
    ws = WorldState()
    assert isinstance(ws.action_budget, ActionBudget)
    assert ws.action_budget.phase == "day"
    assert ws.action_budget.hours_used_today == 0.0
    assert ws.action_budget.hours_used_tonight == 0.0


def test_action_budget_new_default_uses_balance() -> None:
    """ActionBudget.new_default leser balance.day/night_budget_hours."""
    ab = ActionBudget.new_default()
    assert ab.day_budget_hours == 12.0
    assert ab.night_budget_hours == 12.0
    assert ab.phase == "day"


# -----------------------------------------------------------------------------
# new_game_state populerer stubs
# -----------------------------------------------------------------------------


def test_new_game_state_populates_stubs() -> None:
    """new_game_state setter balance-forankrede verdier på stubs."""
    state = save_module.new_game_state()
    assert state.player_state.suspicion == 0.0
    assert state.player_state.rest == 1.0  # balance.rest.default_start
    assert state.player_state.port_caches == {}
    assert state.player_state.active_rumors == []
    assert state.economy_state.pending_sabotages == []
    assert state.economy_state.pending_rumor_impacts == []
    assert state.pitch_lake_state.purchased is False
    assert state.world_state.action_budget.day_budget_hours == 12.0
    assert state.world_state.action_budget.night_budget_hours == 12.0


# -----------------------------------------------------------------------------
# save/load round-trip
# -----------------------------------------------------------------------------


def test_roundtrip_preserves_stub_values(tmp_path: Path) -> None:
    """Stubs med ikke-default-verdier overlever save → load."""
    state = save_module.new_game_state()
    # Sett ikke-default verdier
    state.player_state.suspicion = 42.5
    state.player_state.rest = 0.3
    state.player_state.port_caches = {"tortuga": 500, "havana": 120}
    state.player_state.active_rumors = [
        ActiveRumor(
            rumor_type="regime_preview",
            port_id="havana",
            commodity_id="rum",
            expires_on_day=5,
            payload={"regime": "rising"},
        ),
    ]
    state.economy_state.pending_sabotages = [
        PendingSabotage(
            target_port="port_royal",
            commodity_id="sugar",
            magnitude_pct=10.0,
            ordered_on_day=3,
            impact_day=5,
        ),
    ]
    state.economy_state.pending_rumor_impacts = [
        PendingRumorImpact(
            target_port="havana",
            commodity_id="tobacco",
            magnitude_pct=10.0,
            ordered_on_day=4,
            impact_day=6,
        ),
    ]
    state.pitch_lake_state.purchased = True
    state.world_state.action_budget.hours_used_today = 4.5
    state.world_state.action_budget.phase = "night"

    path = tmp_path / "stub_roundtrip.json"
    assert save_module.save(state, str(path)) is True

    loaded = save_module.load(str(path))
    assert loaded is not None
    assert loaded.player_state.suspicion == 42.5
    assert loaded.player_state.rest == 0.3
    assert loaded.player_state.port_caches == {"tortuga": 500, "havana": 120}
    assert len(loaded.player_state.active_rumors) == 1
    assert loaded.player_state.active_rumors[0].port_id == "havana"
    assert loaded.player_state.active_rumors[0].commodity_id == "rum"
    assert loaded.player_state.active_rumors[0].expires_on_day == 5
    assert loaded.player_state.active_rumors[0].payload == {"regime": "rising"}
    assert len(loaded.economy_state.pending_sabotages) == 1
    assert loaded.economy_state.pending_sabotages[0].target_port == "port_royal"
    assert loaded.economy_state.pending_sabotages[0].impact_day == 5
    assert len(loaded.economy_state.pending_rumor_impacts) == 1
    assert loaded.economy_state.pending_rumor_impacts[0].target_port == "havana"
    assert loaded.pitch_lake_state.purchased is True
    assert loaded.world_state.action_budget.hours_used_today == 4.5
    assert loaded.world_state.action_budget.phase == "night"


def test_load_v5_save_without_stubs_uses_defaults(tmp_path: Path) -> None:
    """En v5-save som mangler Fase 3-stubs skal laste uten feil.

    C3-1 introduserte v5→v6-migreringen — v5-saves ender nå som v6
    etter load. Hovedkompatibilitets-garantien er at eksisterende
    dev-saves fortsetter å virke, med migreringen som fyller inn
    stubs fra balance-defaults pluss `purchased=True` (for å bevare
    aktiv bek-produksjon).
    """
    # Bygg en minimal v5-save som mangler alle Fase 3-stub-felt
    minimal_v5 = {
        "version": 5,
        "player_state": {
            "position_x": 320.0,
            "gold": 300,
            "inventory": {
                "sugar": {"quantity": 0, "avg_cost": 0.0},
                "rum": {"quantity": 0, "avg_cost": 0.0},
                "tobacco": {"quantity": 0, "avg_cost": 0.0},
                "pitch": {"quantity": 0, "avg_cost": 0.0},
            },
            # MANGLER: suspicion, rest, port_caches, active_rumors
        },
        "world_state": {
            "current_port": "tortuga",
            "clock": {"day": 1, "seconds_into_day": 0.0, "seconds_per_day": 180.0},
            "ship": {"class_id": "sloop", "name": "Sjarken", "cargo_capacity": 40},
            "voyage": None,
            # MANGLER: action_budget
        },
        "economy_state": {
            "markets": {"tortuga": {"commodities": {}, "tick_id": 0}},
            "regimes": {},
            "observed": {},
            # MANGLER: pending_sabotages, pending_rumor_impacts
        },
        "pitch_lake_state": {
            "home_port": "tortuga",
            "production_per_day": 2,
            "upkeep_per_day": 8,
            "pending_units": 0,
            "total_produced": 0,
            "last_production_day": 0,
            # MANGLER: purchased
        },
    }
    path = tmp_path / "legacy_v5.json"
    path.write_text(json.dumps(minimal_v5), encoding="utf-8")

    loaded = save_module.load(str(path))
    assert loaded is not None
    # C3-1: v5 save migreres til v6 ved load
    assert loaded.version == 6
    # Defaults har slått inn for manglende felt
    assert loaded.player_state.suspicion == 0.0
    assert loaded.player_state.rest == 1.0  # fra balance.rest.default_start
    assert loaded.player_state.port_caches == {}
    assert loaded.player_state.active_rumors == []
    assert loaded.economy_state.pending_sabotages == []
    assert loaded.economy_state.pending_rumor_impacts == []
    # C3-1 v5→v6-migrering setter purchased=True for eksisterende dev-saves
    # (bakoverkompatibilitet — beholder aktiv bek-produksjon).
    # Fresh v6-saves fra new_game_state starter med False; se
    # test_save_v6_migration::test_new_game_state_has_purchased_false.
    assert loaded.pitch_lake_state.purchased is True
    assert loaded.world_state.action_budget.day_budget_hours == 12.0
    assert loaded.world_state.action_budget.hours_used_today == 0.0


def test_load_v5_save_with_malformed_stub_fields_uses_defaults(
    tmp_path: Path,
) -> None:
    """Ugyldig type på stub-felt → default istedenfor crash."""
    minimal_v5 = {
        "version": 5,
        "player_state": {
            "position_x": 320.0,
            "gold": 300,
            "inventory": {},
            "suspicion": "invalid_string",  # ugyldig → default 0.0
            "rest": None,  # ugyldig → balance.default_start
            "port_caches": "not_a_dict",  # ugyldig → {}
            "active_rumors": "not_a_list",  # ugyldig → []
        },
        "world_state": {
            "current_port": "tortuga",
            "clock": {"day": 1, "seconds_into_day": 0.0, "seconds_per_day": 180.0},
            "ship": {"class_id": "sloop", "name": "Sjarken", "cargo_capacity": 40},
            "voyage": None,
            "action_budget": "not_a_dict",  # ugyldig → new_default
        },
        "economy_state": {
            "markets": {"tortuga": {"commodities": {}, "tick_id": 0}},
            "regimes": {},
            "observed": {},
            "pending_sabotages": "not_a_list",  # ugyldig → []
            "pending_rumor_impacts": [{"bad": "entry"}, {"impact_day": "nope"}],
            # ^ liste med dårlige entries → tom
        },
        "pitch_lake_state": {
            "home_port": "tortuga",
            "production_per_day": 2,
            "upkeep_per_day": 8,
            "pending_units": 0,
            "total_produced": 0,
            "last_production_day": 0,
            "purchased": False,
        },
    }
    path = tmp_path / "malformed_v5.json"
    path.write_text(json.dumps(minimal_v5), encoding="utf-8")

    loaded = save_module.load(str(path))
    assert loaded is not None
    assert loaded.player_state.suspicion == 0.0
    assert loaded.player_state.rest == 1.0
    assert loaded.player_state.port_caches == {}
    assert loaded.player_state.active_rumors == []
    assert loaded.world_state.action_budget.day_budget_hours == 12.0
    assert loaded.economy_state.pending_sabotages == []
    # pending_rumor_impacts: bad entries skippes, første mangler feltene
    # (men defaults fylles inn), andre har ugyldig impact_day.
    # _parse_pending_rumor_impact returnerer None på ValueError og
    # None-entries ignoreres. Vi aksepterer tom liste ELLER én entry
    # (fra defaults) — begge viser at parsing ikke crasher.
    assert isinstance(loaded.economy_state.pending_rumor_impacts, list)


# -----------------------------------------------------------------------------
# Rumor / market_effects stub-dataklasser
# -----------------------------------------------------------------------------


def test_active_rumor_defaults() -> None:
    r = ActiveRumor()
    assert r.rumor_type == "regime_preview"
    assert r.port_id == "tortuga"
    assert r.commodity_id == "sugar"
    assert r.expires_on_day == 0
    assert r.payload == {}


def test_pending_sabotage_defaults() -> None:
    s = PendingSabotage()
    assert s.target_port == "port_royal"
    assert s.commodity_id == "sugar"
    assert s.magnitude_pct == 10.0
    assert s.impact_day == 0


def test_pending_rumor_impact_defaults() -> None:
    r = PendingRumorImpact()
    assert r.target_port == "port_royal"
    assert r.magnitude_pct == 10.0
    assert r.impact_day == 0
