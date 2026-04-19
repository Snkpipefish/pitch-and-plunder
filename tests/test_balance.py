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
    """Returner en gyldig balance-dict som tester kan mutere."""
    payload = {
        "version": 1,
        "economy": {
            "starting_gold": 300,
            "transaction_fee": 5,
            "ship_starting_cargo_capacity": 40,
        },
        "time": {
            "seconds_per_day_in_port": 180.0,
            "seconds_per_day_at_sea": 75.0,
        },
        "pitch_lake": {
            "production_per_day": 2,
            "upkeep_per_day": 8,
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
    """load() returnerer Balance med feltene fra balance.json."""
    path = tmp_path / "balance.json"
    _write_json(path, _valid_payload())
    b = bal.load_from_path(str(path))

    assert b.version == 1
    assert b.economy.starting_gold == 300
    assert b.economy.transaction_fee == 5
    assert b.economy.ship_starting_cargo_capacity == 40
    assert b.time.seconds_per_day_in_port == 180.0
    assert b.time.seconds_per_day_at_sea == 75.0
    assert b.pitch_lake.production_per_day == 2
    assert b.pitch_lake.upkeep_per_day == 8
    assert b.regimes.drift_pct_rising == (2.0, 4.0)
    assert b.regimes.drift_pct_stable == (0.0, 0.0)
    assert b.regimes.drift_pct_falling == (-4.0, -2.0)
    assert b.regimes.noise_pct == 1.0
    assert b.observed.stale_threshold_days == 5
    assert "port_royal-tortuga" in b.travel.routes
    assert b.travel.routes["port_royal-tortuga"].days == 2
    assert b.travel.routes["port_royal-tortuga"].gold == 10


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
