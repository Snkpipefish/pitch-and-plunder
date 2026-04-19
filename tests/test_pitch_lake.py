"""Tester for `systems.pitch_lake` med nested GameState v5 (Fase 2B C1b)."""

from __future__ import annotations

from entities.commodity import InventoryItem
from state import GameState, PitchLakeState
from state.ship_state import ShipState
from systems.game_clock import GameClock
from systems.pitch_lake import PITCH_ID, PitchLake


def _fresh_state(
    clock_day: int = 1,
    cargo_cap: int = 40,
    gold: int = 300,
) -> GameState:
    state = GameState()
    state.player_state.gold = gold
    state.world_state.clock = GameClock(day=clock_day, seconds_into_day=0.0)
    state.world_state.ship = ShipState(cargo_capacity=cargo_cap)
    return state


# -----------------------------------------------------------------------------
# PitchLake.on_new_day – normal produksjon med upkeep
# -----------------------------------------------------------------------------

class TestNormalProduction:
    def test_empty_inventory_produces_full_amount(self):
        state = _fresh_state(gold=300)
        pl = PitchLakeState(production_per_day=2, upkeep_per_day=8)
        produced, paid = PitchLake.on_new_day(pl, state)
        assert produced == 2
        assert paid == 8
        assert state.player_state.gold == 300 - 8
        assert state.player_state.inventory[PITCH_ID].quantity == 2
        assert state.player_state.inventory[PITCH_ID].avg_cost == 0.0

    def test_total_produced_accumulates(self):
        state = _fresh_state(gold=1000)
        pl = PitchLakeState(production_per_day=2, upkeep_per_day=8)
        PitchLake.on_new_day(pl, state)
        state.world_state.clock.day = 2
        PitchLake.on_new_day(pl, state)
        state.world_state.clock.day = 3
        PitchLake.on_new_day(pl, state)
        assert pl.total_produced == 6

    def test_last_production_day_set_when_produced(self):
        state = _fresh_state(clock_day=7, gold=300)
        pl = PitchLakeState(production_per_day=2, upkeep_per_day=8)
        PitchLake.on_new_day(pl, state)
        assert pl.last_production_day == 7

    def test_gold_decrements_each_day(self):
        state = _fresh_state(gold=100)
        pl = PitchLakeState(production_per_day=2, upkeep_per_day=8)
        for _ in range(5):
            PitchLake.on_new_day(pl, state)
        assert state.player_state.gold == 100 - 40


# -----------------------------------------------------------------------------
# Upkeep-betaling
# -----------------------------------------------------------------------------

class TestUpkeepPayment:
    def test_exact_gold_for_upkeep_produces_normally(self):
        state = _fresh_state(gold=8)
        pl = PitchLakeState(production_per_day=2, upkeep_per_day=8)
        produced, paid = PitchLake.on_new_day(pl, state)
        assert produced == 2
        assert paid == 8
        assert state.player_state.gold == 0

    def test_insufficient_gold_drains_and_produces_zero(self):
        state = _fresh_state(gold=5)
        pl = PitchLakeState(production_per_day=2, upkeep_per_day=8)
        produced, paid = PitchLake.on_new_day(pl, state)
        assert produced == 0
        assert paid == 5
        assert state.player_state.gold == 0

    def test_zero_gold_no_production_no_payment(self):
        state = _fresh_state(gold=0)
        pl = PitchLakeState(production_per_day=2, upkeep_per_day=8)
        produced, paid = PitchLake.on_new_day(pl, state)
        assert produced == 0
        assert paid == 0
        assert state.player_state.gold == 0

    def test_no_production_does_not_update_last_production_day(self):
        state = _fresh_state(clock_day=7, gold=0)
        pl = PitchLakeState(production_per_day=2, upkeep_per_day=8)
        pl.last_production_day = 3
        PitchLake.on_new_day(pl, state)
        assert pl.last_production_day == 3

    def test_failed_production_does_not_increment_total_produced(self):
        state = _fresh_state(gold=5)
        pl = PitchLakeState(
            production_per_day=2, upkeep_per_day=8, total_produced=10
        )
        PitchLake.on_new_day(pl, state)
        assert pl.total_produced == 10

    def test_custom_upkeep_cost(self):
        state = _fresh_state(gold=100)
        pl = PitchLakeState(production_per_day=2, upkeep_per_day=20)
        produced, paid = PitchLake.on_new_day(pl, state)
        assert paid == 20
        assert state.player_state.gold == 80
        assert produced == 2


# -----------------------------------------------------------------------------
# Vektet snitt
# -----------------------------------------------------------------------------

class TestWeightedAverage:
    def test_existing_pitch_inventory_dilutes_avg_cost(self):
        # 5 bek @ snitt 40.0 eksisterer. 2 nye produsert (kost 0).
        # Nytt snitt: (5*40 + 2*0) / 7 = 200/7 ≈ 28.57
        state = _fresh_state(gold=300)
        state.player_state.inventory[PITCH_ID] = InventoryItem(
            quantity=5, avg_cost=40.0
        )
        pl = PitchLakeState(production_per_day=2, upkeep_per_day=8)
        PitchLake.on_new_day(pl, state)
        pitch = state.player_state.inventory[PITCH_ID]
        assert pitch.quantity == 7
        assert abs(pitch.avg_cost - 28.57) < 0.01

    def test_zero_existing_inventory_avg_stays_zero(self):
        state = _fresh_state(gold=300)
        pl = PitchLakeState(production_per_day=2, upkeep_per_day=8)
        PitchLake.on_new_day(pl, state)
        assert state.player_state.inventory[PITCH_ID].avg_cost == 0.0


# -----------------------------------------------------------------------------
# Lasterom-grense
# -----------------------------------------------------------------------------

class TestCargoLimit:
    def test_full_cargo_produces_zero_but_pays_upkeep(self):
        state = _fresh_state(cargo_cap=40, gold=300)
        state.player_state.inventory["sugar"] = InventoryItem(
            quantity=40, avg_cost=50.0
        )
        pl = PitchLakeState(production_per_day=2, upkeep_per_day=8)
        produced, paid = PitchLake.on_new_day(pl, state)
        assert produced == 0
        assert paid == 8
        assert state.player_state.gold == 300 - 8
        assert state.player_state.inventory[PITCH_ID].quantity == 0

    def test_partial_space_produces_partial(self):
        state = _fresh_state(cargo_cap=40, gold=300)
        state.player_state.inventory["sugar"] = InventoryItem(quantity=39)
        pl = PitchLakeState(production_per_day=2, upkeep_per_day=8)
        produced, _ = PitchLake.on_new_day(pl, state)
        assert produced == 1
        assert state.player_state.inventory[PITCH_ID].quantity == 1


# -----------------------------------------------------------------------------
# Custom production
# -----------------------------------------------------------------------------

class TestCustomProduction:
    def test_zero_production_per_day(self):
        state = _fresh_state(gold=300)
        pl = PitchLakeState(production_per_day=0, upkeep_per_day=8)
        produced, paid = PitchLake.on_new_day(pl, state)
        assert produced == 0
        assert paid == 8
        assert state.player_state.inventory[PITCH_ID].quantity == 0

    def test_higher_production_per_day(self):
        state = _fresh_state(gold=300)
        pl = PitchLakeState(production_per_day=5, upkeep_per_day=8)
        produced, _ = PitchLake.on_new_day(pl, state)
        assert produced == 5
