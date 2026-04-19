"""Tester for save/load og versjonsmigrering v1/v2/v3 → v5 (Fase 2B C1b).

v4→v5-migrering har egen fil: `tests/test_save_v5_migration.py` med 7 tester
per spec §5.2, inkludert round-trip på disk.
"""

from __future__ import annotations

import json
from pathlib import Path

from state import GameState
from state.game_state import CURRENT_SAVE_VERSION
from systems.game_clock import GameClock
from systems.save import load, save


def _write_json(path: Path, data: dict) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh)


class TestVersionConstants:
    def test_current_version_is_5(self):
        assert CURRENT_SAVE_VERSION == 5

    def test_default_state_has_current_version(self):
        assert GameState().version == CURRENT_SAVE_VERSION


class TestCurrentVersionRoundTrip:
    def test_save_emits_v5_nested_structure(self, tmp_path: Path):
        path = tmp_path / "save.json"
        state = GameState()
        state.world_state.clock = GameClock(day=10, seconds_into_day=42.0)
        save(state, str(path))

        with open(path) as fh:
            raw = json.load(fh)
        assert raw["version"] == CURRENT_SAVE_VERSION
        assert "player_state" in raw
        assert "world_state" in raw
        assert "economy_state" in raw
        assert "pitch_lake_state" in raw
        assert raw["world_state"]["clock"]["day"] == 10
        assert raw["world_state"]["clock"]["seconds_into_day"] == 42.0
        # Flatt skjema skal være borte
        assert "gold" not in raw
        assert "clock" not in raw

    def test_save_then_load_preserves_basic_fields(self, tmp_path: Path):
        path = tmp_path / "save.json"
        state = GameState()
        state.player_state.gold = 432
        state.world_state.clock = GameClock(day=7, seconds_into_day=23.5)
        state.world_state.ship.cargo_capacity = 50

        assert save(state, str(path)) is True
        loaded = load(str(path))

        assert loaded is not None
        assert loaded.version == CURRENT_SAVE_VERSION
        assert loaded.player_state.gold == 432
        assert loaded.world_state.clock.day == 7
        assert loaded.world_state.clock.seconds_into_day == 23.5
        assert loaded.world_state.ship.cargo_capacity == 50


class TestV2Migration:
    def _v2_payload(self, **overrides) -> dict:
        base = {
            "version": 2,
            "gold": 500,
            "inventory": {
                "sugar": {"quantity": 3, "avg_cost": 40.0},
                "rum": {"quantity": 0, "avg_cost": 0.0},
                "tobacco": {"quantity": 0, "avg_cost": 0.0},
                "pitch": {"quantity": 0, "avg_cost": 0.0},
            },
            "current_scene": "village",
            "player_position": [1200.0, 320.0],
            "day": 12,
            "commodities_state": {},
        }
        base.update(overrides)
        return base

    def test_v2_loads_as_v5(self, tmp_path: Path):
        path = tmp_path / "v2.json"
        _write_json(path, self._v2_payload())
        loaded = load(str(path))
        assert loaded is not None
        assert loaded.version == CURRENT_SAVE_VERSION

    def test_v2_day_becomes_clock_day(self, tmp_path: Path):
        path = tmp_path / "v2.json"
        _write_json(path, self._v2_payload(day=12))
        loaded = load(str(path))
        assert loaded.world_state.clock.day == 12
        assert loaded.world_state.clock.seconds_into_day == 0.0

    def test_v2_inventory_preserved(self, tmp_path: Path):
        path = tmp_path / "v2.json"
        _write_json(path, self._v2_payload())
        loaded = load(str(path))
        assert loaded.player_state.inventory["sugar"].quantity == 3
        assert loaded.player_state.inventory["sugar"].avg_cost == 40.0

    def test_v2_resave_writes_current_version(self, tmp_path: Path):
        path = tmp_path / "v2.json"
        _write_json(path, self._v2_payload())
        loaded = load(str(path))
        assert loaded is not None
        save(loaded, str(path))
        with open(path) as fh:
            raw = json.load(fh)
        assert raw["version"] == CURRENT_SAVE_VERSION
        # v5 nested-felter skal finnes; flatt day ikke
        assert "world_state" in raw
        assert "day" not in raw


class TestV1Migration:
    def _v1_payload(self, **overrides) -> dict:
        # v1 hadde inventar som int per vare (ingen avg_cost)
        base = {
            "version": 1,
            "gold": 300,
            "inventory": {"sugar": 5, "rum": 2, "tobacco": 0, "pitch": 0},
            "current_scene": "village",
            "player_position": [320.0, 280.0],
            "day": 3,
            "commodities_state": {},
        }
        base.update(overrides)
        return base

    def test_v1_loads_as_current_version(self, tmp_path: Path):
        path = tmp_path / "v1.json"
        _write_json(path, self._v1_payload())
        loaded = load(str(path))
        assert loaded is not None
        assert loaded.version == CURRENT_SAVE_VERSION
        assert loaded.world_state.clock.day == 3

    def test_v1_int_inventory_becomes_inventory_item(self, tmp_path: Path):
        path = tmp_path / "v1.json"
        _write_json(path, self._v1_payload())
        loaded = load(str(path))
        assert loaded.player_state.inventory["sugar"].quantity == 5
        assert loaded.player_state.inventory["sugar"].avg_cost == 0.0
        assert loaded.player_state.inventory["rum"].quantity == 2


class TestCorruptInput:
    def test_missing_file_returns_none(self, tmp_path: Path):
        assert load(str(tmp_path / "does_not_exist.json")) is None

    def test_invalid_json_returns_none(self, tmp_path: Path):
        path = tmp_path / "bad.json"
        path.write_text("{not valid json", encoding="utf-8")
        assert load(str(path)) is None

    def test_unknown_version_returns_none(self, tmp_path: Path):
        path = tmp_path / "future.json"
        _write_json(path, {"version": 99, "gold": 100})
        assert load(str(path)) is None

    def test_corrupt_clock_falls_back_to_default(self, tmp_path: Path):
        path = tmp_path / "corrupt_clock.json"
        _write_json(
            path,
            {
                "version": 3,
                "gold": 100,
                "inventory": {
                    "sugar": {"quantity": 0, "avg_cost": 0.0},
                    "rum": {"quantity": 0, "avg_cost": 0.0},
                    "tobacco": {"quantity": 0, "avg_cost": 0.0},
                    "pitch": {"quantity": 0, "avg_cost": 0.0},
                },
                "current_scene": "village",
                "player_position": [320.0, 280.0],
                "clock": {"day": "ikke et tall", "seconds_into_day": None},
                "commodities_state": {},
            },
        )
        loaded = load(str(path))
        assert loaded is not None
        assert loaded.world_state.clock.day == 1
        assert loaded.world_state.clock.seconds_into_day == 0.0

    def test_corrupt_player_position_falls_back(self, tmp_path: Path):
        path = tmp_path / "corrupt_pos.json"
        _write_json(
            path,
            {
                "version": 3,
                "gold": 100,
                "inventory": {
                    "sugar": {"quantity": 0, "avg_cost": 0.0},
                    "rum": {"quantity": 0, "avg_cost": 0.0},
                    "tobacco": {"quantity": 0, "avg_cost": 0.0},
                    "pitch": {"quantity": 0, "avg_cost": 0.0},
                },
                "current_scene": "village",
                "player_position": "not a tuple",
                "clock": {"day": 1, "seconds_into_day": 0.0, "seconds_per_day": 60.0},
                "commodities_state": {},
            },
        )
        loaded = load(str(path))
        assert loaded is not None
        # Faller tilbake til default position_x
        assert loaded.player_state.position_x == 320.0
