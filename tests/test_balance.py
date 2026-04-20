"""Tester for systems/balance.py."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from systems import balance as bal


@pytest.fixture(autouse=True)
def _reset_balance():
    """Tøm singleton både før og etter hver test for isolasjon."""
    bal._reset_for_tests()
    yield
    bal._reset_for_tests()


def _write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data), encoding="utf-8")


def _valid_payload(**overrides) -> dict:
    """Returner en gyldig v2 balance-dict som tester kan mutere.

    v2 (Fase 3 C3-0) la til game, actions, suspicion, rest, rumors,
    sabotage, events. pitch_lake utvidet med purchase_cost_gold.
    """
    payload = {
        "version": 2,
        "game": {
            "total_days": 100,
            "starting_port": "tortuga",
        },
        "economy": {
            "starting_gold": 300,
            "transaction_fee": 5,
            "ship_starting_cargo_capacity": 40,
        },
        "time": {
            "seconds_per_day_in_port": 180.0,
            "seconds_per_day_at_sea": 75.0,
        },
        "actions": {
            "day_budget_hours": 12.0,
            "night_budget_hours": 12.0,
            "cost_hours_per_action": {
                "walk_across_port": 0.25,
                "exchange_trade": 0.5,
                "buy_room": 1.0,
            },
        },
        "suspicion": {
            "threshold": 100.0,
            "daily_decay": 2.0,
            "rumor_increase": 0.0,
            "arrest_on_threshold": True,
        },
        "rest": {
            "default_start": 1.0,
            "decay_per_action": 0.05,
            "tired_penalty_multiplier": 2.0,
            "room_cost_gold": 10,
            "room_cost_hours": 1.0,
        },
        "rumors": {
            "cost_gold": 20,
            "cost_hours": 1.0,
            "ttl_days": 3,
            "regime_preview_enabled": True,
            "price_spike_warning_enabled": True,
        },
        "sabotage": {
            "base_cost_gold": 50,
            "impact_delay_days": 2,
            "magnitude_pct": 10.0,
            "false_rumor_base_cost_gold": 40,
            "false_rumor_magnitude_pct": 10.0,
            "suspicion_increase_sabotage": 15.0,
            "suspicion_increase_false_rumor": 8.0,
        },
        "events": {
            "voyage_frequency_per_day": 0.5,
            "port_frequency_per_day_start": 0.2,
            "positive_ratio": 0.3,
        },
        "pitch_lake": {
            "production_per_day": 2,
            "upkeep_per_day": 8,
            "purchase_cost_gold": 500,
        },
        "travel": {
            "routes": {
                "port_royal-tortuga": {"days": 2, "gold": 10},
            }
        },
        "regimes": {
            "drift_pct_rising": [2.0, 4.0],
            "drift_pct_stable": [0.0, 0.0],
            "drift_pct_falling": [-4.0, -2.0],
            "noise_pct": 1.0,
        },
        "observed": {"stale_threshold_days": 5},
    }
    for key, val in overrides.items():
        # Enkel top-level overstyring for nøkler som trengs
        payload[key] = val
    return payload


def test_load_default_matches_spec(tmp_path: Path) -> None:
    """load() returnerer Balance med feltene fra balance.json (v2)."""
    path = tmp_path / "balance.json"
    _write_json(path, _valid_payload())
    b = bal.load_from_path(str(path))

    assert b.version == 2
    assert b.economy.starting_gold == 300
    assert b.economy.transaction_fee == 5
    assert b.economy.ship_starting_cargo_capacity == 40
    assert b.time.seconds_per_day_in_port == 180.0
    assert b.time.seconds_per_day_at_sea == 75.0
    assert b.pitch_lake.production_per_day == 2
    assert b.pitch_lake.upkeep_per_day == 8
    assert b.pitch_lake.purchase_cost_gold == 500
    assert b.regimes.drift_pct_rising == (2.0, 4.0)
    assert b.regimes.drift_pct_stable == (0.0, 0.0)
    assert b.regimes.drift_pct_falling == (-4.0, -2.0)
    assert b.regimes.noise_pct == 1.0
    assert b.observed.stale_threshold_days == 5
    assert "port_royal-tortuga" in b.travel.routes
    assert b.travel.routes["port_royal-tortuga"].days == 2
    assert b.travel.routes["port_royal-tortuga"].gold == 10
    # Fase 3 (v2) seksjoner
    assert b.game.total_days == 100
    assert b.game.starting_port == "tortuga"
    assert b.actions.day_budget_hours == 12.0
    assert b.actions.night_budget_hours == 12.0
    assert b.actions.cost_hours_per_action["exchange_trade"] == 0.5
    assert b.suspicion.threshold == 100.0
    assert b.suspicion.daily_decay == 2.0
    assert b.suspicion.arrest_on_threshold is True
    assert b.rest.default_start == 1.0
    assert b.rest.decay_per_action == 0.05
    assert b.rest.tired_penalty_multiplier == 2.0
    assert b.rumors.cost_gold == 20
    assert b.rumors.ttl_days == 3
    assert b.rumors.regime_preview_enabled is True
    assert b.sabotage.base_cost_gold == 50
    assert b.sabotage.magnitude_pct == 10.0
    assert b.sabotage.false_rumor_base_cost_gold == 40
    assert b.sabotage.suspicion_increase_sabotage == 15.0
    assert b.sabotage.suspicion_increase_false_rumor == 8.0
    assert b.events.voyage_frequency_per_day == 0.5
    assert b.events.positive_ratio == 0.3


def test_init_sets_singleton(tmp_path: Path) -> None:
    path = tmp_path / "balance.json"
    _write_json(path, _valid_payload())
    assert not bal.is_initialized()
    b1 = bal.init(str(path))
    assert bal.is_initialized()
    b2 = bal.get()
    assert b1 is b2


def test_get_without_init_raises() -> None:
    with pytest.raises(RuntimeError):
        bal.get()


def test_init_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        bal.init(str(tmp_path / "does_not_exist.json"))


def test_init_invalid_json_raises(tmp_path: Path) -> None:
    path = tmp_path / "balance.json"
    path.write_text("{not valid json", encoding="utf-8")
    with pytest.raises(ValueError):
        bal.init(str(path))


def test_init_missing_field_raises(tmp_path: Path) -> None:
    path = tmp_path / "balance.json"
    bad = _valid_payload()
    del bad["economy"]["transaction_fee"]
    _write_json(path, bad)
    with pytest.raises(ValueError):
        bal.init(str(path))


def test_reload_live_change_categorized(tmp_path: Path) -> None:
    """Endre transaction_fee → kategoriseres som live."""
    path = tmp_path / "balance.json"
    _write_json(path, _valid_payload())
    b = bal.init(str(path))
    assert b.economy.transaction_fee == 5

    modified = _valid_payload()
    modified["economy"]["transaction_fee"] = 7
    _write_json(path, modified)

    result = bal.reload()
    assert result.success is True
    assert result.error is None
    assert "economy.transaction_fee" in result.live_changes
    assert result.session_changes == []
    assert result.newgame_changes == []
    # In-place swap: eksisterende referanse ser ny verdi
    assert b.economy.transaction_fee == 7
    assert bal.get().economy.transaction_fee == 7


def test_reload_session_change_categorized(tmp_path: Path) -> None:
    """Endre seconds_per_day_in_port → kategoriseres som session."""
    path = tmp_path / "balance.json"
    _write_json(path, _valid_payload())
    bal.init(str(path))

    modified = _valid_payload()
    modified["time"]["seconds_per_day_in_port"] = 120.0
    _write_json(path, modified)

    result = bal.reload()
    assert result.success is True
    assert "time.seconds_per_day_in_port" in result.session_changes
    assert result.live_changes == []


def test_reload_newgame_change_categorized(tmp_path: Path) -> None:
    """Endre starting_gold → kategoriseres som newgame."""
    path = tmp_path / "balance.json"
    _write_json(path, _valid_payload())
    bal.init(str(path))

    modified = _valid_payload()
    modified["economy"]["starting_gold"] = 999
    _write_json(path, modified)

    result = bal.reload()
    assert result.success is True
    assert "economy.starting_gold" in result.newgame_changes


def test_reload_invalid_keeps_old(tmp_path: Path) -> None:
    """Ødelagt fil → reload feiler uten å ødelegge singletonen."""
    path = tmp_path / "balance.json"
    _write_json(path, _valid_payload())
    b = bal.init(str(path))
    assert b.economy.transaction_fee == 5

    path.write_text("{broken json", encoding="utf-8")
    result = bal.reload()
    assert result.success is False
    assert result.error is not None
    # Gammel verdi bevart
    assert bal.get().economy.transaction_fee == 5


def test_reload_multiple_categories(tmp_path: Path) -> None:
    path = tmp_path / "balance.json"
    _write_json(path, _valid_payload())
    bal.init(str(path))

    modified = _valid_payload()
    modified["economy"]["transaction_fee"] = 6       # live
    modified["time"]["seconds_per_day_in_port"] = 90  # session
    modified["economy"]["starting_gold"] = 500        # newgame
    _write_json(path, modified)

    result = bal.reload()
    assert result.success is True
    assert "economy.transaction_fee" in result.live_changes
    assert "time.seconds_per_day_in_port" in result.session_changes
    assert "economy.starting_gold" in result.newgame_changes


# --- Fase 3 (v2) kategori-tester ---


def test_reload_v2_sabotage_live(tmp_path: Path) -> None:
    """Sabotasje-felt er LIVE — endres umiddelbart."""
    path = tmp_path / "balance.json"
    _write_json(path, _valid_payload())
    bal.init(str(path))

    modified = _valid_payload()
    modified["sabotage"]["base_cost_gold"] = 75
    modified["sabotage"]["suspicion_increase_sabotage"] = 20.0
    _write_json(path, modified)

    result = bal.reload()
    assert result.success is True
    assert "sabotage.base_cost_gold" in result.live_changes
    assert "sabotage.suspicion_increase_sabotage" in result.live_changes
    assert result.session_changes == []
    assert result.newgame_changes == []
    assert bal.get().sabotage.base_cost_gold == 75


def test_reload_v2_action_budget_session(tmp_path: Path) -> None:
    """Action-budsjett-felt er SESSION (neste dawn)."""
    path = tmp_path / "balance.json"
    _write_json(path, _valid_payload())
    bal.init(str(path))

    modified = _valid_payload()
    modified["actions"]["day_budget_hours"] = 10.0
    modified["suspicion"]["threshold"] = 120.0
    _write_json(path, modified)

    result = bal.reload()
    assert result.success is True
    assert "actions.day_budget_hours" in result.session_changes
    assert "suspicion.threshold" in result.session_changes
    assert result.live_changes == []


def test_reload_v2_newgame_fields(tmp_path: Path) -> None:
    """game.total_days og pitch_lake.purchase_cost_gold er NEWGAME."""
    path = tmp_path / "balance.json"
    _write_json(path, _valid_payload())
    bal.init(str(path))

    modified = _valid_payload()
    modified["game"]["total_days"] = 50
    modified["pitch_lake"]["purchase_cost_gold"] = 800
    modified["rest"]["default_start"] = 0.8
    _write_json(path, modified)

    result = bal.reload()
    assert result.success is True
    assert "game.total_days" in result.newgame_changes
    assert "pitch_lake.purchase_cost_gold" in result.newgame_changes
    assert "rest.default_start" in result.newgame_changes


def test_reload_v2_actions_cost_live(tmp_path: Path) -> None:
    """actions.cost_hours_per_action er LIVE (dict-diff)."""
    path = tmp_path / "balance.json"
    _write_json(path, _valid_payload())
    bal.init(str(path))

    modified = _valid_payload()
    modified["actions"]["cost_hours_per_action"]["order_sabotage"] = 3.0
    _write_json(path, modified)

    result = bal.reload()
    assert result.success is True
    assert "actions.cost_hours_per_action" in result.live_changes


# --- Fase 3 C3-2: tick_id for hot-reload-cache-invalidation ---


def test_tick_id_starts_at_zero_after_reset() -> None:
    """Etter _reset_for_tests skal tick_id være 0."""
    # _reset_balance fixture kaller _reset_for_tests før testen
    assert bal.tick_id() == 0


def test_tick_id_unchanged_by_init(tmp_path: Path) -> None:
    """init() endrer ikke tick_id — kun reload() bumper."""
    path = tmp_path / "balance.json"
    _write_json(path, _valid_payload())
    assert bal.tick_id() == 0
    bal.init(str(path))
    assert bal.tick_id() == 0


def test_tick_id_bumps_on_successful_reload(tmp_path: Path) -> None:
    """Hver vellykkede reload() øker tick_id med 1."""
    path = tmp_path / "balance.json"
    _write_json(path, _valid_payload())
    bal.init(str(path))
    assert bal.tick_id() == 0

    # Første reload (selv uten endringer) bumper tick_id
    result1 = bal.reload()
    assert result1.success is True
    assert bal.tick_id() == 1

    # Andre reload bumper igjen
    modified = _valid_payload()
    modified["economy"]["transaction_fee"] = 7
    _write_json(path, modified)
    result2 = bal.reload()
    assert result2.success is True
    assert bal.tick_id() == 2


def test_tick_id_not_bumped_on_failed_reload(tmp_path: Path) -> None:
    """Failed reload (ødelagt fil) bumper IKKE tick_id."""
    path = tmp_path / "balance.json"
    _write_json(path, _valid_payload())
    bal.init(str(path))

    # Ødelegg filen
    path.write_text("{broken json", encoding="utf-8")
    result = bal.reload()
    assert result.success is False
    # Singleton uendret, og tick_id uendret
    assert bal.tick_id() == 0
