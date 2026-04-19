"""Tester for `systems.pitch_lake` og v3→v4 save-migrering."""

from __future__ import annotations

import json
from pathlib import Path

import constants
from entities.commodity import InventoryItem
from systems.game_clock import GameClock
from systems.pitch_lake import PITCH_ID, PitchLake, PitchLakeState
from systems.save import CURRENT_SAVE_VERSION, GameState, load, save


def _fresh_state(clock_day: int = 1, cargo_cap: int = 40) -> GameState:
    state = GameState()
    state.clock = GameClock(day=clock_day, seconds_into_day=0.0)
    state.cargo_capacity = cargo_cap
    return state


def _write_json(path: Path, data: dict) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh)


# -----------------------------------------------------------------------------
# PitchLake.on_new_day
# -----------------------------------------------------------------------------

class TestNormalProduction:
    def test_empty_inventory_produces_full_amount(self):
        state = _fresh_state()
        pl = PitchLakeState()
        produced = PitchLake.on_new_day(pl, state)
        assert produced == 2
        assert state.inventory[PITCH_ID].quantity == 2
        # Produksjon er gratis → avg_cost=0 (startet på 0)
        assert state.inventory[PITCH_ID].avg_cost == 0.0

    def test_total_produced_accumulates(self):
        state = _fresh_state()
        pl = PitchLakeState()
        PitchLake.on_new_day(pl, state)
        state.clock.day = 2
        PitchLake.on_new_day(pl, state)
        state.clock.day = 3
        PitchLake.on_new_day(pl, state)
        assert pl.total_produced == 6

    def test_last_production_day_updated(self):
        state = _fresh_state(clock_day=7)
        pl = PitchLakeState()
        PitchLake.on_new_day(pl, state)
        assert pl.last_production_day == 7


class TestWeightedAverage:
    def test_existing_pitch_inventory_dilutes_avg_cost(self):
        # 5 bek @ snitt 40.0 eksisterer. 2 nye produsert (kost 0).
        # Nytt snitt: (5*40 + 2*0) / 7 = 200/7 ≈ 28.57
        state = _fresh_state()
        state.inventory[PITCH_ID] = InventoryItem(quantity=5, avg_cost=40.0)
        pl = PitchLakeState()
        PitchLake.on_new_day(pl, state)
        assert state.inventory[PITCH_ID].quantity == 7
        assert abs(state.inventory[PITCH_ID].avg_cost - 28.57) < 0.01

    def test_zero_existing_inventory_avg_stays_zero(self):
        state = _fresh_state()
        pl = PitchLakeState()
        PitchLake.on_new_day(pl, state)
        assert state.inventory[PITCH_ID].avg_cost == 0.0


class TestCargoLimit:
    def test_full_cargo_produces_zero(self):
        state = _fresh_state(cargo_cap=40)
        state.inventory["sugar"] = InventoryItem(quantity=40, avg_cost=50.0)
        pl = PitchLakeState()
        produced = PitchLake.on_new_day(pl, state)
        assert produced == 0
        # Pitch-inventar skal være uendret
        assert state.inventory[PITCH_ID].quantity == 0

    def test_partial_space_produces_partial(self):
        state = _fresh_state(cargo_cap=40)
        state.inventory["sugar"] = InventoryItem(quantity=39)
        pl = PitchLakeState()
        produced = PitchLake.on_new_day(pl, state)
        # Kun 1 plass ledig → 1 bek produsert (ikke 2)
        assert produced == 1
        assert state.inventory[PITCH_ID].quantity == 1

    def test_full_cargo_still_updates_last_production_day(self):
        state = _fresh_state(clock_day=5, cargo_cap=40)
        state.inventory["sugar"] = InventoryItem(quantity=40)
        pl = PitchLakeState()
        PitchLake.on_new_day(pl, state)
        assert pl.last_production_day == 5
        # total_produced skal IKKE øke når ingenting produseres
        assert pl.total_produced == 0


class TestCustomProduction:
    def test_zero_production_per_day(self):
        # Hvis production_per_day=0 (fremtidig: oppgraderingsfjerning)
        state = _fresh_state()
        pl = PitchLakeState(production_per_day=0)
        produced = PitchLake.on_new_day(pl, state)
        assert produced == 0
        assert state.inventory[PITCH_ID].quantity == 0

    def test_higher_production_per_day(self):
        # Fremtidig oppgradering: 5 bek/dag
        state = _fresh_state()
        pl = PitchLakeState(production_per_day=5)
        produced = PitchLake.on_new_day(pl, state)
        assert produced == 5


# -----------------------------------------------------------------------------
# Save/load migrering v3 → v4
# -----------------------------------------------------------------------------

class TestSaveV4RoundTrip:
    def test_current_version_is_4(self):
        assert CURRENT_SAVE_VERSION == 4

    def test_fresh_state_save_has_pitch_lake(self, tmp_path: Path):
        path = tmp_path / "save.json"
        state = GameState()
        save(state, str(path))
        with open(path) as fh:
            raw = json.load(fh)
        assert raw["version"] == 4
        assert "pitch_lake" in raw
        assert raw["pitch_lake"]["production_per_day"] == 2
        assert raw["pitch_lake"]["total_produced"] == 0

    def test_load_preserves_pitch_lake(self, tmp_path: Path):
        path = tmp_path / "save.json"
        state = GameState()
        state.pitch_lake = PitchLakeState(
            production_per_day=3,
            total_produced=42,
            last_production_day=21,
        )
        save(state, str(path))
        loaded = load(str(path))
        assert loaded is not None
        assert loaded.pitch_lake.production_per_day == 3
        assert loaded.pitch_lake.total_produced == 42
        assert loaded.pitch_lake.last_production_day == 21


class TestV3ToV4Migration:
    def _v3_payload(self) -> dict:
        return {
            "version": 3,
            "gold": 300,
            "inventory": {
                "sugar": {"quantity": 0, "avg_cost": 0.0},
                "rum": {"quantity": 0, "avg_cost": 0.0},
                "tobacco": {"quantity": 0, "avg_cost": 0.0},
                "pitch": {"quantity": 0, "avg_cost": 0.0},
            },
            "current_scene": "village",
            "player_position": [320.0, 280.0],
            "clock": {"day": 5, "seconds_into_day": 0.0, "seconds_per_day": 60.0},
            "commodities_state": {},
            "cargo_capacity": 40,
            "regimes": {},
        }

    def test_v3_loads_with_default_pitch_lake(self, tmp_path: Path):
        path = tmp_path / "v3.json"
        _write_json(path, self._v3_payload())
        loaded = load(str(path))
        assert loaded is not None
        assert loaded.version == 4
        assert loaded.pitch_lake.production_per_day == 2
        assert loaded.pitch_lake.total_produced == 0
        assert loaded.pitch_lake.last_production_day == 0

    def test_v3_gold_and_inventory_preserved(self, tmp_path: Path):
        path = tmp_path / "v3.json"
        data = self._v3_payload()
        data["gold"] = 450
        data["inventory"]["sugar"]["quantity"] = 3
        _write_json(path, data)
        loaded = load(str(path))
        assert loaded.gold == 450
        assert loaded.inventory["sugar"].quantity == 3

    def test_v3_resave_writes_v4(self, tmp_path: Path):
        path = tmp_path / "v3.json"
        _write_json(path, self._v3_payload())
        loaded = load(str(path))
        save(loaded, str(path))
        with open(path) as fh:
            raw = json.load(fh)
        assert raw["version"] == 4
        assert "pitch_lake" in raw


class TestCorruptPitchLake:
    def test_corrupt_pitch_lake_falls_back_to_default(self, tmp_path: Path):
        path = tmp_path / "corrupt.json"
        _write_json(
            path,
            {
                "version": 4,
                "gold": 300,
                "inventory": {
                    "sugar": {"quantity": 0, "avg_cost": 0.0},
                    "rum": {"quantity": 0, "avg_cost": 0.0},
                    "tobacco": {"quantity": 0, "avg_cost": 0.0},
                    "pitch": {"quantity": 0, "avg_cost": 0.0},
                },
                "current_scene": "village",
                "player_position": [320.0, 280.0],
                "clock": {"day": 1, "seconds_into_day": 0.0, "seconds_per_day": 180.0},
                "commodities_state": {},
                "cargo_capacity": 40,
                "regimes": {},
                "pitch_lake": {"production_per_day": "nei", "total_produced": None},
            },
        )
        loaded = load(str(path))
        assert loaded is not None
        # Korrupte verdier → defaults
        assert loaded.pitch_lake.production_per_day == 2
        assert loaded.pitch_lake.total_produced == 0
