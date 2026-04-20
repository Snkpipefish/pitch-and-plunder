"""Tester for v5 → v6-migrering (Fase 3 C3-1).

v6 formaliserer Fase 3-stub-feltene som ble innført i C3-0 uten
versjon-bump. Hovedsak:
- `pitch_lake_state.purchased = True` for eksisterende v5-dev-saves
  (bakoverkompatibilitet — bevarer aktiv bek-produksjon)
- Ny save starter med `purchased = False` (spilleren må kjøpe anlegget
  via tavern-dag-meny i Tortuga i C3-6)
- `world_state.action_budget` initialiseres fra balance-defaults
- Øvrige stubs (suspicion, rest, port_caches, active_rumors,
  pending_sabotages, pending_rumor_impacts) får nøytrale init-verdier
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from state.game_state import CURRENT_SAVE_VERSION
from systems.save import (
    load,
    migrate_to_latest,
    migrate_v5_to_v6,
    save,
)


def _minimal_v5_payload() -> dict:
    """En komplett, minimal v5-save uten noen av Fase 3-stubene."""
    return {
        "version": 5,
        "player_state": {
            "position_x": 320.0,
            "gold": 250,
            "inventory": {
                "sugar": {"quantity": 3, "avg_cost": 40.0},
                "rum": {"quantity": 0, "avg_cost": 0.0},
                "tobacco": {"quantity": 0, "avg_cost": 0.0},
                "pitch": {"quantity": 7, "avg_cost": 0.0},
            },
        },
        "world_state": {
            "current_port": "tortuga",
            "clock": {
                "day": 12,
                "seconds_into_day": 45.5,
                "seconds_per_day": 180.0,
            },
            "ship": {
                "class_id": "sloop",
                "name": "Sjarken",
                "cargo_capacity": 40,
            },
            "voyage": None,
        },
        "economy_state": {
            "markets": {
                "tortuga": {
                    "commodities": {
                        "sugar": {"current_price": 42.0, "price_history": []}
                    },
                    "tick_id": 0,
                }
            },
            "regimes": {},
            "observed": {},
        },
        "pitch_lake_state": {
            "home_port": "tortuga",
            "production_per_day": 2,
            "upkeep_per_day": 8,
            "pending_units": 0,
            "total_produced": 24,
            "last_production_day": 11,
        },
    }


# -----------------------------------------------------------------------------
# migrate_v5_to_v6 direkte tester (dict-level)
# -----------------------------------------------------------------------------


def test_migrate_sets_version_to_6() -> None:
    v5 = _minimal_v5_payload()
    v6 = migrate_v5_to_v6(v5)
    assert v6["version"] == 6


def test_migrate_sets_purchased_true_for_existing_save() -> None:
    """v5-save uten purchased-felt → migrert til purchased=True."""
    v5 = _minimal_v5_payload()
    assert "purchased" not in v5["pitch_lake_state"]

    v6 = migrate_v5_to_v6(v5)
    assert v6["pitch_lake_state"]["purchased"] is True


def test_migrate_overrides_purchased_false_to_true() -> None:
    """Eksplisitt purchased=False i v5-save overskrives til True ved migrering.

    Scenariet: en save skrevet under C3-0 (før versjon-bump) kan ha
    `purchased=False` serialisert. v5→v6 vil fortsatt gi True siden
    migreringen er kun for eksisterende dev-saves (som HADDE aktiv bek-
    produksjon i Fase 2B/2.5). Nye v6-saves skrives direkte via
    new_game_state med purchased=False.
    """
    v5 = _minimal_v5_payload()
    v5["pitch_lake_state"]["purchased"] = False

    v6 = migrate_v5_to_v6(v5)
    assert v6["pitch_lake_state"]["purchased"] is True


def test_migrate_initializes_action_budget_from_balance() -> None:
    v5 = _minimal_v5_payload()
    v6 = migrate_v5_to_v6(v5)
    ab = v6["world_state"]["action_budget"]
    assert ab["day_budget_hours"] == 12.0
    assert ab["night_budget_hours"] == 12.0
    assert ab["hours_used_today"] == 0.0
    assert ab["hours_used_tonight"] == 0.0
    assert ab["phase"] == "day"


def test_migrate_preserves_existing_action_budget() -> None:
    """Hvis world_state.action_budget allerede finnes i v5-save (fra C3-0-
    era skriving), bevares det."""
    v5 = _minimal_v5_payload()
    v5["world_state"]["action_budget"] = {
        "day_budget_hours": 10.0,
        "night_budget_hours": 14.0,
        "hours_used_today": 4.5,
        "hours_used_tonight": 0.0,
        "phase": "day",
    }
    v6 = migrate_v5_to_v6(v5)
    ab = v6["world_state"]["action_budget"]
    assert ab["day_budget_hours"] == 10.0
    assert ab["hours_used_today"] == 4.5


def test_migrate_sets_player_stubs() -> None:
    v5 = _minimal_v5_payload()
    v6 = migrate_v5_to_v6(v5)
    ps = v6["player_state"]
    assert ps["suspicion"] == 0.0
    assert ps["rest"] == 1.0  # balance.rest.default_start
    assert ps["port_caches"] == {}
    assert ps["active_rumors"] == []


def test_migrate_sets_economy_stubs() -> None:
    v5 = _minimal_v5_payload()
    v6 = migrate_v5_to_v6(v5)
    es = v6["economy_state"]
    assert es["pending_sabotages"] == []
    assert es["pending_rumor_impacts"] == []


def test_migrate_preserves_core_v5_data() -> None:
    """v5-data (gull, inventar, klokke, markeder) må bevares nøyaktig."""
    v5 = _minimal_v5_payload()
    v6 = migrate_v5_to_v6(v5)
    assert v6["player_state"]["gold"] == 250
    assert v6["player_state"]["inventory"]["sugar"]["quantity"] == 3
    assert v6["player_state"]["inventory"]["pitch"]["quantity"] == 7
    assert v6["world_state"]["clock"]["day"] == 12
    assert v6["world_state"]["clock"]["seconds_into_day"] == 45.5
    assert v6["world_state"]["ship"]["cargo_capacity"] == 40
    assert v6["pitch_lake_state"]["total_produced"] == 24
    assert v6["pitch_lake_state"]["last_production_day"] == 11


def test_migrate_handles_missing_substructures() -> None:
    """v5-save uten world_state eller economy_state (ekstremt defekt) →
    migreringen fyller inn stubs uten crash."""
    v5 = {
        "version": 5,
        "player_state": {"position_x": 320.0, "gold": 100, "inventory": {}},
        # MANGLER: world_state, economy_state, pitch_lake_state
    }
    v6 = migrate_v5_to_v6(v5)
    assert v6["version"] == 6
    assert v6["world_state"]["action_budget"]["phase"] == "day"
    assert v6["economy_state"]["pending_sabotages"] == []
    assert v6["pitch_lake_state"]["purchased"] is True


# -----------------------------------------------------------------------------
# migrate_to_latest kjede-tester
# -----------------------------------------------------------------------------


def test_chain_v5_reaches_v6() -> None:
    v5 = _minimal_v5_payload()
    result = migrate_to_latest(v5)
    assert result["version"] == 6
    assert result["pitch_lake_state"]["purchased"] is True


def test_chain_v4_reaches_v6() -> None:
    """v4 → v5 → v6 i én kjede."""
    v4 = {
        "version": 4,
        "gold": 300,
        "inventory": {
            "sugar": {"quantity": 0, "avg_cost": 0.0},
            "rum": {"quantity": 0, "avg_cost": 0.0},
            "tobacco": {"quantity": 0, "avg_cost": 0.0},
            "pitch": {"quantity": 0, "avg_cost": 0.0},
        },
        "current_scene": "village",
        "player_position": [320.0, 0.0],
        "clock": {"day": 3, "seconds_into_day": 10.0, "seconds_per_day": 180.0},
        "commodities_state": {},
        "cargo_capacity": 40,
        "regimes": {},
        "pitch_lake": {
            "production_per_day": 2,
            "daily_upkeep_cost": 8,
            "total_produced": 6,
            "last_production_day": 2,
        },
    }
    result = migrate_to_latest(v4)
    assert result["version"] == 6
    # v4-dev-save skal også få purchased=True
    assert result["pitch_lake_state"]["purchased"] is True
    # Handlings-budsjett lagt til
    assert result["world_state"]["action_budget"]["phase"] == "day"


# -----------------------------------------------------------------------------
# Ende-til-ende load()-tester
# -----------------------------------------------------------------------------


def test_load_v5_save_ends_at_v6_with_purchased(tmp_path: Path) -> None:
    v5 = _minimal_v5_payload()
    path = tmp_path / "v5.json"
    path.write_text(json.dumps(v5), encoding="utf-8")

    loaded = load(str(path))
    assert loaded is not None
    assert loaded.version == CURRENT_SAVE_VERSION == 6
    assert loaded.pitch_lake_state.purchased is True
    # Stubs populert
    assert loaded.player_state.suspicion == 0.0
    assert loaded.player_state.rest == 1.0
    assert loaded.player_state.port_caches == {}
    assert loaded.player_state.active_rumors == []
    assert loaded.economy_state.pending_sabotages == []
    assert loaded.economy_state.pending_rumor_impacts == []
    # Kjerne-data bevart
    assert loaded.player_state.gold == 250
    assert loaded.world_state.clock.day == 12


def test_load_v5_save_roundtrip_to_v6(tmp_path: Path) -> None:
    """v5 → load → save → load: andre load skal lese som ren v6."""
    v5 = _minimal_v5_payload()
    path = tmp_path / "rt.json"
    path.write_text(json.dumps(v5), encoding="utf-8")

    loaded_once = load(str(path))
    assert loaded_once is not None
    assert save(loaded_once, str(path)) is True

    # Verifisér at filen nå er v6 på disken
    with open(path) as fh:
        raw = json.load(fh)
    assert raw["version"] == 6
    assert raw["pitch_lake_state"]["purchased"] is True

    # Andre load skal lese direkte uten migrering
    loaded_twice = load(str(path))
    assert loaded_twice is not None
    assert loaded_twice.version == 6
    assert loaded_twice.pitch_lake_state.purchased is True


def test_new_game_state_has_purchased_false() -> None:
    """Fresh save (ikke migrert) starter med purchased=False — spilleren må
    kjøpe anlegget i tavern-dag-meny i Tortuga (C3-6 gate-logikk)."""
    from systems.save import new_game_state

    state = new_game_state()
    assert state.version == 6
    assert state.pitch_lake_state.purchased is False
    # Action budget fra balance
    assert state.world_state.action_budget.day_budget_hours == 12.0
    assert state.world_state.action_budget.phase == "day"
