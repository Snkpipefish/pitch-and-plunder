"""Tester for `systems.pitch_lake` med nested GameState (Fase 2B C1b + Fase 3 C3-6).

C3-6-tilpasning: Alle eksisterende tester konstruerer et PitchLakeState
via `_pl()`-helperen som setter `purchased=True`. Gaten i
`PitchLake.on_new_day` krever purchased for å produsere, og Fase 2B-
adferden testes nå under aksjonen "etter kjøp". Tester for purchased=
False-gate finnes i egne klasser (TestPurchasedGate / TestMigrationFlow).
"""

from __future__ import annotations

from entities.commodity import InventoryItem
from state import GameState, PitchLakeState
from state.ship_state import ShipState
from systems.game_clock import GameClock
from systems.pitch_lake import PITCH_ID, PitchLake


def _pl(**kwargs) -> PitchLakeState:
    """Helper: PitchLakeState med `purchased=True` default (Fase 3 C3-6).

    Tester som utrykkelig vil teste purchased=False-gaten setter det
    selv (se TestPurchasedGate).
    """
    kwargs.setdefault("purchased", True)
    return PitchLakeState(**kwargs)


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
        pl = _pl(production_per_day=2, upkeep_per_day=8)
        produced, paid = PitchLake.on_new_day(pl, state)
        assert produced == 2
        assert paid == 8
        assert state.player_state.gold == 300 - 8
        assert state.player_state.inventory[PITCH_ID].quantity == 2
        assert state.player_state.inventory[PITCH_ID].avg_cost == 0.0

    def test_total_produced_accumulates(self):
        state = _fresh_state(gold=1000)
        pl = _pl(production_per_day=2, upkeep_per_day=8)
        PitchLake.on_new_day(pl, state)
        state.world_state.clock.day = 2
        PitchLake.on_new_day(pl, state)
        state.world_state.clock.day = 3
        PitchLake.on_new_day(pl, state)
        assert pl.total_produced == 6

    def test_last_production_day_set_when_produced(self):
        state = _fresh_state(clock_day=7, gold=300)
        pl = _pl(production_per_day=2, upkeep_per_day=8)
        PitchLake.on_new_day(pl, state)
        assert pl.last_production_day == 7

    def test_gold_decrements_each_day(self):
        state = _fresh_state(gold=100)
        pl = _pl(production_per_day=2, upkeep_per_day=8)
        for _ in range(5):
            PitchLake.on_new_day(pl, state)
        assert state.player_state.gold == 100 - 40


# -----------------------------------------------------------------------------
# Upkeep-betaling
# -----------------------------------------------------------------------------

class TestUpkeepPayment:
    def test_exact_gold_for_upkeep_produces_normally(self):
        state = _fresh_state(gold=8)
        pl = _pl(production_per_day=2, upkeep_per_day=8)
        produced, paid = PitchLake.on_new_day(pl, state)
        assert produced == 2
        assert paid == 8
        assert state.player_state.gold == 0

    def test_insufficient_gold_drains_and_produces_zero(self):
        state = _fresh_state(gold=5)
        pl = _pl(production_per_day=2, upkeep_per_day=8)
        produced, paid = PitchLake.on_new_day(pl, state)
        assert produced == 0
        assert paid == 5
        assert state.player_state.gold == 0

    def test_zero_gold_no_production_no_payment(self):
        state = _fresh_state(gold=0)
        pl = _pl(production_per_day=2, upkeep_per_day=8)
        produced, paid = PitchLake.on_new_day(pl, state)
        assert produced == 0
        assert paid == 0
        assert state.player_state.gold == 0

    def test_no_production_does_not_update_last_production_day(self):
        state = _fresh_state(clock_day=7, gold=0)
        pl = _pl(production_per_day=2, upkeep_per_day=8)
        pl.last_production_day = 3
        PitchLake.on_new_day(pl, state)
        assert pl.last_production_day == 3

    def test_failed_production_does_not_increment_total_produced(self):
        state = _fresh_state(gold=5)
        pl = _pl(
            production_per_day=2, upkeep_per_day=8, total_produced=10
        )
        PitchLake.on_new_day(pl, state)
        assert pl.total_produced == 10

    def test_custom_upkeep_cost(self):
        state = _fresh_state(gold=100)
        pl = _pl(production_per_day=2, upkeep_per_day=20)
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
        pl = _pl(production_per_day=2, upkeep_per_day=8)
        PitchLake.on_new_day(pl, state)
        pitch = state.player_state.inventory[PITCH_ID]
        assert pitch.quantity == 7
        assert abs(pitch.avg_cost - 28.57) < 0.01

    def test_zero_existing_inventory_avg_stays_zero(self):
        state = _fresh_state(gold=300)
        pl = _pl(production_per_day=2, upkeep_per_day=8)
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
        pl = _pl(production_per_day=2, upkeep_per_day=8)
        produced, paid = PitchLake.on_new_day(pl, state)
        assert produced == 0
        assert paid == 8
        assert state.player_state.gold == 300 - 8
        assert state.player_state.inventory[PITCH_ID].quantity == 0

    def test_partial_space_produces_partial(self):
        state = _fresh_state(cargo_cap=40, gold=300)
        state.player_state.inventory["sugar"] = InventoryItem(quantity=39)
        pl = _pl(production_per_day=2, upkeep_per_day=8)
        produced, _ = PitchLake.on_new_day(pl, state)
        assert produced == 1
        assert state.player_state.inventory[PITCH_ID].quantity == 1


# -----------------------------------------------------------------------------
# Custom production
# -----------------------------------------------------------------------------

class TestCustomProduction:
    def test_zero_production_per_day(self):
        state = _fresh_state(gold=300)
        pl = _pl(production_per_day=0, upkeep_per_day=8)
        produced, paid = PitchLake.on_new_day(pl, state)
        assert produced == 0
        assert paid == 8
        assert state.player_state.inventory[PITCH_ID].quantity == 0

    def test_higher_production_per_day(self):
        state = _fresh_state(gold=300)
        pl = _pl(production_per_day=5, upkeep_per_day=8)
        produced, _ = PitchLake.on_new_day(pl, state)
        assert produced == 5


# -----------------------------------------------------------------------------
# Pending-units når spilleren er BORTE fra home_port (Fase 2B C7b)
# -----------------------------------------------------------------------------

class TestPendingUnitsAway:
    """Per spec §2.3: når current_port != home_port (eller voyage aktiv),
    skal produksjon gå til state.pending_units i stedet for inventar.
    Bekken lagres på kaia og venter på spillerens retur."""

    def test_under_voyage_routes_to_pending(self):
        from state.voyage_state import VoyageState
        state = _fresh_state(gold=300)
        # Sett aktiv voyage — spilleren er ikke i havn
        state.world_state.voyage = VoyageState(
            from_port="tortuga", to_port="havana",
            depart_day=1, arrival_day=4,
        )
        pl = _pl(
            home_port="tortuga", production_per_day=2, upkeep_per_day=8,
        )
        produced, paid = PitchLake.on_new_day(pl, state)
        assert produced == 2
        assert paid == 8  # upkeep trekkes som normalt
        assert pl.pending_units == 2
        # Inventar uendret — bekken er på kaia
        assert state.player_state.inventory.get(PITCH_ID, InventoryItem()).quantity == 0

    def test_in_non_home_port_routes_to_pending(self):
        state = _fresh_state(gold=300)
        # Ingen voyage, men current_port != home_port
        state.world_state.current_port = "port_royal"
        pl = _pl(
            home_port="tortuga", production_per_day=2, upkeep_per_day=8,
        )
        produced, _ = PitchLake.on_new_day(pl, state)
        assert produced == 2
        assert pl.pending_units == 2
        assert state.player_state.inventory.get(PITCH_ID, InventoryItem()).quantity == 0

    def test_pending_accumulates_over_days(self):
        from state.voyage_state import VoyageState
        state = _fresh_state(gold=1000)
        state.world_state.voyage = VoyageState(
            from_port="tortuga", to_port="nassau",
            depart_day=1, arrival_day=5,
        )
        pl = _pl(
            home_port="tortuga", production_per_day=2, upkeep_per_day=8,
        )
        for day in range(1, 5):
            state.world_state.clock.day = day
            PitchLake.on_new_day(pl, state)
        assert pl.pending_units == 8  # 4 dager × 2/dag
        assert pl.total_produced == 8

    def test_pending_path_does_not_lose_to_full_cargo(self):
        """I hjemme-stien tapes overskudd ved full last (cargo-klamp).
        I borte-stien akkumuleres alt til pending uten klamp — bekken
        venter til kapasitet finnes ved retur."""
        from state.voyage_state import VoyageState
        state = _fresh_state(cargo_cap=5, gold=300)
        # Fyll inventar nesten helt
        state.player_state.inventory["sugar"] = InventoryItem(quantity=5, avg_cost=40.0)
        state.world_state.voyage = VoyageState(
            from_port="tortuga", to_port="havana",
            depart_day=1, arrival_day=4,
        )
        pl = _pl(
            home_port="tortuga", production_per_day=2, upkeep_per_day=8,
        )
        produced, _ = PitchLake.on_new_day(pl, state)
        # Selv om cargo er fullt: pending vokser, ingenting tapt
        assert produced == 2
        assert pl.pending_units == 2

    def test_last_production_day_set_in_pending_path(self):
        """HUD halted-deteksjon (last_production_day < clock.day - 1) skal
        IKKE feilaktig vise halted under reise — produksjonen HAR skjedd,
        bare lagret på kaia."""
        from state.voyage_state import VoyageState
        state = _fresh_state(clock_day=12, gold=300)
        state.world_state.voyage = VoyageState(
            from_port="tortuga", to_port="havana",
            depart_day=10, arrival_day=13,
        )
        pl = _pl(
            home_port="tortuga", production_per_day=2, upkeep_per_day=8,
            last_production_day=0,
        )
        PitchLake.on_new_day(pl, state)
        assert pl.last_production_day == 12


# -----------------------------------------------------------------------------
# realize_pending_units (Fase 2B C7b)
# -----------------------------------------------------------------------------

class TestRealizePendingUnits:
    def test_moves_pending_to_inventory_up_to_capacity(self):
        state = _fresh_state(cargo_cap=10, gold=100)
        pl = _pl(
            home_port="tortuga", production_per_day=2, upkeep_per_day=8,
            pending_units=5,
        )
        realized = PitchLake.realize_pending_units(pl, state)
        assert realized == 5
        assert state.player_state.inventory[PITCH_ID].quantity == 5
        assert pl.pending_units == 0

    def test_partial_realization_when_cargo_constrained(self):
        state = _fresh_state(cargo_cap=10, gold=100)
        # 7 enheter allerede i lasterom — kun 3 plasser ledig
        state.player_state.inventory["sugar"] = InventoryItem(quantity=7, avg_cost=40.0)
        pl = _pl(
            home_port="tortuga", production_per_day=2, upkeep_per_day=8,
            pending_units=8,
        )
        realized = PitchLake.realize_pending_units(pl, state)
        assert realized == 3
        assert state.player_state.inventory[PITCH_ID].quantity == 3
        # Resten venter videre i pending
        assert pl.pending_units == 5

    def test_noop_when_pending_zero(self):
        state = _fresh_state(cargo_cap=10, gold=100)
        pl = _pl(
            home_port="tortuga", production_per_day=2, upkeep_per_day=8,
            pending_units=0,
        )
        realized = PitchLake.realize_pending_units(pl, state)
        assert realized == 0
        assert state.player_state.inventory[PITCH_ID].quantity == 0

    def test_noop_when_cargo_full(self):
        state = _fresh_state(cargo_cap=5, gold=100)
        state.player_state.inventory["sugar"] = InventoryItem(quantity=5, avg_cost=40.0)
        pl = _pl(
            home_port="tortuga", production_per_day=2, upkeep_per_day=8,
            pending_units=10,
        )
        realized = PitchLake.realize_pending_units(pl, state)
        assert realized == 0
        assert pl.pending_units == 10  # alt forblir på kaia
