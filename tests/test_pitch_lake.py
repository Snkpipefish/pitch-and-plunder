"""Tester for `systems.pitch_lake` og v3→v4 save-migrering."""

from __future__ import annotations

import json
from pathlib import Path

import constants
from entities.commodity import InventoryItem
from systems.game_clock import GameClock
from systems.pitch_lake import PITCH_ID, PitchLake, PitchLakeState
from systems.save import CURRENT_SAVE_VERSION, GameState, load, save


def _fresh_state(
    clock_day: int = 1,
    cargo_cap: int = 40,
    gold: int = 300,
) -> GameState:
    state = GameState()
    state.gold = gold
    state.clock = GameClock(day=clock_day, seconds_into_day=0.0)
    state.cargo_capacity = cargo_cap
    return state


def _write_json(path: Path, data: dict) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh)


# -----------------------------------------------------------------------------
# PitchLake.on_new_day – normal produksjon med upkeep
# -----------------------------------------------------------------------------

class TestNormalProduction:
    def test_empty_inventory_produces_full_amount(self):
        state = _fresh_state(gold=300)
        pl = PitchLakeState()
        produced, paid = PitchLake.on_new_day(pl, state)
        assert produced == 2
        assert paid == 8
        assert state.gold == 300 - 8  # 292
        assert state.inventory[PITCH_ID].quantity == 2
        assert state.inventory[PITCH_ID].avg_cost == 0.0

    def test_total_produced_accumulates(self):
        state = _fresh_state(gold=1000)
        pl = PitchLakeState()
        PitchLake.on_new_day(pl, state)
        state.clock.day = 2
        PitchLake.on_new_day(pl, state)
        state.clock.day = 3
        PitchLake.on_new_day(pl, state)
        assert pl.total_produced == 6

    def test_last_production_day_set_when_produced(self):
        state = _fresh_state(clock_day=7, gold=300)
        pl = PitchLakeState()
        PitchLake.on_new_day(pl, state)
        assert pl.last_production_day == 7

    def test_gold_decrements_each_day(self):
        state = _fresh_state(gold=100)
        pl = PitchLakeState()
        for _ in range(5):
            PitchLake.on_new_day(pl, state)
        # 5 dager × 8 = 40 upkeep
        assert state.gold == 100 - 40


# -----------------------------------------------------------------------------
# Upkeep-betaling
# -----------------------------------------------------------------------------

class TestUpkeepPayment:
    def test_exact_gold_for_upkeep_produces_normally(self):
        # Gull akkurat på upkeep-verdien: drift går, men gull tømmes
        state = _fresh_state(gold=8)
        pl = PitchLakeState()
        produced, paid = PitchLake.on_new_day(pl, state)
        assert produced == 2
        assert paid == 8
        assert state.gold == 0

    def test_insufficient_gold_drains_and_produces_zero(self):
        state = _fresh_state(gold=5)
        pl = PitchLakeState()
        produced, paid = PitchLake.on_new_day(pl, state)
        assert produced == 0
        assert paid == 5
        assert state.gold == 0

    def test_zero_gold_no_production_no_payment(self):
        state = _fresh_state(gold=0)
        pl = PitchLakeState()
        produced, paid = PitchLake.on_new_day(pl, state)
        assert produced == 0
        assert paid == 0
        assert state.gold == 0

    def test_no_production_does_not_update_last_production_day(self):
        state = _fresh_state(clock_day=7, gold=0)
        pl = PitchLakeState()
        pl.last_production_day = 3  # Siste gang det gikk
        PitchLake.on_new_day(pl, state)
        # Siden produksjon feilet skal last_production_day IKKE endres
        assert pl.last_production_day == 3

    def test_failed_production_does_not_increment_total_produced(self):
        state = _fresh_state(gold=5)
        pl = PitchLakeState(total_produced=10)
        PitchLake.on_new_day(pl, state)
        assert pl.total_produced == 10

    def test_custom_upkeep_cost(self):
        state = _fresh_state(gold=100)
        pl = PitchLakeState(daily_upkeep_cost=20)
        produced, paid = PitchLake.on_new_day(pl, state)
        assert paid == 20
        assert state.gold == 80
        assert produced == 2


# -----------------------------------------------------------------------------
# Vektet snitt
# -----------------------------------------------------------------------------

class TestWeightedAverage:
    def test_existing_pitch_inventory_dilutes_avg_cost(self):
        # 5 bek @ snitt 40.0 eksisterer. 2 nye produsert (kost 0).
        # Nytt snitt: (5*40 + 2*0) / 7 = 200/7 ≈ 28.57
        state = _fresh_state(gold=300)
        state.inventory[PITCH_ID] = InventoryItem(quantity=5, avg_cost=40.0)
        pl = PitchLakeState()
        PitchLake.on_new_day(pl, state)
        assert state.inventory[PITCH_ID].quantity == 7
        assert abs(state.inventory[PITCH_ID].avg_cost - 28.57) < 0.01

    def test_zero_existing_inventory_avg_stays_zero(self):
        state = _fresh_state(gold=300)
        pl = PitchLakeState()
        PitchLake.on_new_day(pl, state)
        assert state.inventory[PITCH_ID].avg_cost == 0.0


# -----------------------------------------------------------------------------
# Lasterom-grense
# -----------------------------------------------------------------------------

class TestCargoLimit:
    def test_full_cargo_produces_zero_but_pays_upkeep(self):
        # Upkeep trekkes likevel — drift går, pitchen har bare ingen plass.
        state = _fresh_state(cargo_cap=40, gold=300)
        state.inventory["sugar"] = InventoryItem(quantity=40, avg_cost=50.0)
        pl = PitchLakeState()
        produced, paid = PitchLake.on_new_day(pl, state)
        assert produced == 0
        assert paid == 8
        assert state.gold == 300 - 8
        assert state.inventory[PITCH_ID].quantity == 0

    def test_partial_space_produces_partial(self):
        state = _fresh_state(cargo_cap=40, gold=300)
        state.inventory["sugar"] = InventoryItem(quantity=39)
        pl = PitchLakeState()
        produced, _ = PitchLake.on_new_day(pl, state)
        assert produced == 1
        assert state.inventory[PITCH_ID].quantity == 1


# -----------------------------------------------------------------------------
# Custom production
# -----------------------------------------------------------------------------

class TestCustomProduction:
    def test_zero_production_per_day(self):
        state = _fresh_state(gold=300)
        pl = PitchLakeState(production_per_day=0)
        produced, paid = PitchLake.on_new_day(pl, state)
        assert produced == 0
        assert paid == 8  # upkeep betales uansett
        assert state.inventory[PITCH_ID].quantity == 0

    def test_higher_production_per_day(self):
        state = _fresh_state(gold=300)
        pl = PitchLakeState(production_per_day=5)
        produced, _ = PitchLake.on_new_day(pl, state)
        assert produced == 5


# -----------------------------------------------------------------------------
# Save/load og migrering v3 → v4
# -----------------------------------------------------------------------------

class TestSaveV4RoundTrip:
    def test_current_version_is_4(self):
        assert CURRENT_SAVE_VERSION == 4

    def test_fresh_state_save_has_pitch_lake_with_upkeep(self, tmp_path: Path):
        path = tmp_path / "save.json"
        state = GameState()
        save(state, str(path))
        with open(path) as fh:
            raw = json.load(fh)
        assert raw["version"] == 4
        assert "pitch_lake" in raw
        assert raw["pitch_lake"]["production_per_day"] == 2
        assert raw["pitch_lake"]["daily_upkeep_cost"] == 8
        assert raw["pitch_lake"]["total_produced"] == 0

    def test_load_preserves_pitch_lake(self, tmp_path: Path):
        path = tmp_path / "save.json"
        state = GameState()
        state.pitch_lake = PitchLakeState(
            production_per_day=3,
            daily_upkeep_cost=12,
            total_produced=42,
            last_production_day=21,
        )
        save(state, str(path))
        loaded = load(str(path))
        assert loaded is not None
        assert loaded.pitch_lake.production_per_day == 3
        assert loaded.pitch_lake.daily_upkeep_cost == 12
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
        assert loaded.pitch_lake.daily_upkeep_cost == 8
        assert loaded.pitch_lake.total_produced == 0
        assert loaded.pitch_lake.last_production_day == 0

    def test_v3_resave_writes_v4(self, tmp_path: Path):
        path = tmp_path / "v3.json"
        _write_json(path, self._v3_payload())
        loaded = load(str(path))
        save(loaded, str(path))
        with open(path) as fh:
            raw = json.load(fh)
        assert raw["version"] == 4
        assert "pitch_lake" in raw


class TestV4PreUpkeepMigration:
    """v4-saves fra Commit 6 har pitch_lake uten daily_upkeep_cost.
    Ved load skal feltet defaulte til 8 (ingen versjons-bump).
    """

    def _v4_without_upkeep(self) -> dict:
        return {
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
            "pitch_lake": {
                "production_per_day": 2,
                "total_produced": 10,
                "last_production_day": 5,
                # daily_upkeep_cost mangler
            },
        }

    def test_missing_upkeep_defaults_to_eight(self, tmp_path: Path):
        path = tmp_path / "v4_no_upkeep.json"
        _write_json(path, self._v4_without_upkeep())
        loaded = load(str(path))
        assert loaded is not None
        assert loaded.pitch_lake.daily_upkeep_cost == 8
        # Eksisterende felt bevart
        assert loaded.pitch_lake.production_per_day == 2
        assert loaded.pitch_lake.total_produced == 10
        assert loaded.pitch_lake.last_production_day == 5


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
                "pitch_lake": {
                    "production_per_day": "nei",
                    "daily_upkeep_cost": "tolv",
                    "total_produced": None,
                },
            },
        )
        loaded = load(str(path))
        assert loaded is not None
        # Korrupte verdier → defaults
        assert loaded.pitch_lake.production_per_day == 2
        assert loaded.pitch_lake.daily_upkeep_cost == 8
        assert loaded.pitch_lake.total_produced == 0
