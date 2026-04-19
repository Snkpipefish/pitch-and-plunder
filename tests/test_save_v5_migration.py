"""7 tester for v4→v5-migrering (spec FASE_2B.md §5.2).

Fixture: `tests/fixtures/save_v4.json` er en ekte v4-save fra brukerens
spilltest. Ingen syntetisk v4 i test-kode — reelle float-presisjoner og
felt-rekkefølger fanger edge cases syntetiske fixtures ikke gjør.

Test #7 (round-trip) skriver til disk og leser tilbake — fanger tupler→
lister, enum→streng, float-drift og nested-dataclass-default som
in-memory-tester ikke vil se.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

import pytest

from state.economy_state import KNOWN_PORTS
from state.game_state import CURRENT_SAVE_VERSION
from state.market_state import MarketState
from state.observed_price import ObservedPrice
from systems.game_clock import GameClock
from systems.save import load, save


FIXTURE_V4 = Path(__file__).parent / "fixtures" / "save_v4.json"


@pytest.fixture
def v4_raw() -> dict:
    """Rå v4-dict fra fixture — uendret JSON-data som referanse."""
    with open(FIXTURE_V4, "r", encoding="utf-8") as fh:
        return json.load(fh)


@pytest.fixture
def v4_fixture_path(tmp_path: Path) -> Path:
    """Kopi av v4-fixture i tmp_path slik at testen ikke muterer kilden."""
    dst = tmp_path / "save_v4.json"
    dst.write_text(FIXTURE_V4.read_text(encoding="utf-8"), encoding="utf-8")
    return dst


# -----------------------------------------------------------------------------
# Test 1: Load v4 save → v5 uten feil
# -----------------------------------------------------------------------------

def test_1_v4_loads_without_error(v4_fixture_path: Path) -> None:
    loaded = load(str(v4_fixture_path))
    assert loaded is not None
    assert loaded.version == CURRENT_SAVE_VERSION == 5


# -----------------------------------------------------------------------------
# Test 2: Tortuga-data bevart nøyaktig
# -----------------------------------------------------------------------------

def test_2_tortuga_data_preserved(
    v4_fixture_path: Path, v4_raw: dict
) -> None:
    loaded = load(str(v4_fixture_path))
    assert loaded is not None

    # Gull og inventar
    assert loaded.player_state.gold == v4_raw["gold"]
    for cid, v4_inv in v4_raw["inventory"].items():
        loaded_item = loaded.player_state.inventory[cid]
        assert loaded_item.quantity == v4_inv["quantity"]
        assert loaded_item.avg_cost == v4_inv["avg_cost"]

    # Tortuga-marked: current_price og price_history per vare
    tortuga_market = loaded.economy_state.markets["tortuga"]
    for cid, v4_c in v4_raw["commodities_state"].items():
        c = tortuga_market.commodities[cid]
        assert c.current_price == v4_c["current_price"]
        assert c.price_history == v4_c["price_history"]

    # Regimer for Tortuga
    tortuga_regimes = loaded.economy_state.regimes["tortuga"]
    for cid, v4_r in v4_raw["regimes"].items():
        r = tortuga_regimes[cid]
        assert r.current == v4_r["current"]
        assert r.days_remaining == v4_r["days_remaining"]
        assert r.history == v4_r["history"]


# -----------------------------------------------------------------------------
# Test 3: Andre havner har korrekt struktur (bias-init kommer i C2)
# -----------------------------------------------------------------------------

def test_3_other_ports_have_empty_market_and_regimes(
    v4_fixture_path: Path,
) -> None:
    loaded = load(str(v4_fixture_path))
    assert loaded is not None

    # Alle 4 havner er nøkler i markets og regimes
    for pid in KNOWN_PORTS:
        assert pid in loaded.economy_state.markets
        assert pid in loaded.economy_state.regimes

    # Tortuga har innhold; de andre er tomme (C2 fyller med bias-initiert data)
    assert loaded.economy_state.markets["tortuga"].commodities
    for pid in ("port_royal", "havana", "nassau"):
        assert loaded.economy_state.markets[pid] == MarketState()
        assert loaded.economy_state.regimes[pid] == {}


# -----------------------------------------------------------------------------
# Test 4: Observed-dict har kun Tortuga-oppføring
# -----------------------------------------------------------------------------

def test_4_observed_has_only_tortuga(
    v4_fixture_path: Path, v4_raw: dict
) -> None:
    loaded = load(str(v4_fixture_path))
    assert loaded is not None

    observed = loaded.economy_state.observed
    assert "tortuga" in observed
    assert "port_royal" not in observed
    assert "havana" not in observed
    assert "nassau" not in observed

    # Observed-priser for Tortuga matcher v4 current_price
    v4_day = v4_raw["clock"]["day"]
    for cid, v4_c in v4_raw["commodities_state"].items():
        obs = observed["tortuga"][cid]
        assert isinstance(obs, ObservedPrice)
        assert obs.price == v4_c["current_price"]
        assert obs.day_seen == v4_day


# -----------------------------------------------------------------------------
# Test 5: Skip default "Sjarken"/"sloop", cargo_capacity fra v4
# -----------------------------------------------------------------------------

def test_5_ship_defaults_and_cargo_from_v4(
    v4_fixture_path: Path, v4_raw: dict
) -> None:
    loaded = load(str(v4_fixture_path))
    assert loaded is not None

    ship = loaded.world_state.ship
    assert ship.class_id == "sloop"
    assert ship.name == "Sjarken"
    # cargo_capacity = v4-verdi, ikke balance-default (hvis de skiller seg)
    assert ship.cargo_capacity == v4_raw["cargo_capacity"]


# -----------------------------------------------------------------------------
# Test 6: v3 → v5 via kjeden
# -----------------------------------------------------------------------------

def test_6_v3_migrates_through_chain_to_v5(tmp_path: Path) -> None:
    """Syntetisk v3 basert på faktisk v3-schema (git show 893fe03:systems/save.py):
    version=3, gold, inventory (dict[str, {quantity, avg_cost}]),
    current_scene, player_position[x,y], clock{day,seconds_into_day,
    seconds_per_day}, commodities_state.
    Ingen cargo_capacity, regimes eller pitch_lake (lagt til i v4).
    """
    v3 = {
        "version": 3,
        "gold": 275,
        "inventory": {
            "sugar":   {"quantity": 3, "avg_cost": 40.0},
            "rum":     {"quantity": 0, "avg_cost": 0.0},
            "tobacco": {"quantity": 2, "avg_cost": 90.0},
            "pitch":   {"quantity": 0, "avg_cost": 0.0},
        },
        "current_scene": "village",
        "player_position": [1200.0, 320.0],
        "clock": {"day": 5, "seconds_into_day": 12.5, "seconds_per_day": 180.0},
        "commodities_state": {
            "sugar": {"current_price": 41.0, "price_history": [40.0, 41.0]},
        },
    }
    path = tmp_path / "v3.json"
    path.write_text(json.dumps(v3), encoding="utf-8")

    loaded = load(str(path))
    assert loaded is not None
    # Endte på v5 — ikke direkte parsing fra v3.
    assert loaded.version == CURRENT_SAVE_VERSION == 5
    # Klokke og spiller-felter bevart gjennom kjeden
    assert loaded.world_state.clock.day == 5
    assert loaded.world_state.clock.seconds_into_day == 12.5
    assert loaded.player_state.gold == 275
    assert loaded.player_state.inventory["sugar"].quantity == 3
    assert loaded.player_state.inventory["tobacco"].avg_cost == 90.0
    assert loaded.player_state.position_x == 1200.0
    # Tortuga-marked populert fra v3 commodities_state
    sugar = loaded.economy_state.markets["tortuga"].commodities["sugar"]
    assert sugar.current_price == 41.0
    assert sugar.price_history == [40.0, 41.0]
    # Andre havner er tomme placeholders
    assert loaded.economy_state.markets["port_royal"].commodities == {}
    # v3-save hadde ingen cargo_capacity → v3→v4 ga balance-default
    # (40); v4→v5 bar den videre til ship.cargo_capacity.
    assert loaded.world_state.ship.cargo_capacity == 40


# -----------------------------------------------------------------------------
# Test 7: Round-trip på disk — fanger tupler→lister, float-drift osv.
# -----------------------------------------------------------------------------

def test_7_roundtrip_on_disk(
    v4_fixture_path: Path, tmp_path: Path
) -> None:
    """Last v4 → migrer til v5 GameState → skriv v5 til disk →
    les tilbake fra disk → sammenlign som rekursive dicts.

    Fanger:
    - Tupler som blir lister etter json.dump/load (ingen tupler forventet
      i GameState v5; denne testen låser det kravet)
    - Enum-verdier som blir strenger (ikke i bruk ennå, men lås kontrakten)
    - Float-presisjon som drifter (skal være eksakt siden vi ikke runder)
    - Default-verdier i nested dataclasses som trigges fordi feltet
      manglet i JSON (asdict skal alltid emittere alle felter)
    """
    # Ledd 1: v4 → v5 via load()
    migrated = load(str(v4_fixture_path))
    assert migrated is not None

    # Ledd 2: skriv v5 til disk (reell JSON-fil, ikke in-memory)
    roundtrip_path = tmp_path / "roundtrip.json"
    assert save(migrated, str(roundtrip_path)) is True
    assert roundtrip_path.exists()

    # Ledd 3: les tilbake fra disk
    reloaded = load(str(roundtrip_path))
    assert reloaded is not None
    assert reloaded.version == CURRENT_SAVE_VERSION

    # Ledd 4: sammenlign som rekursive dicts (asdict håndterer alle nested
    # dataclass-strukturer, dict-felter og lister). Hvis en tuple har
    # sneket seg inn i v5 ville asdict(migrated) og asdict(reloaded) ikke
    # matche (migrated har tuple, reloaded har list fra JSON).
    migrated_dict = asdict(migrated)
    reloaded_dict = asdict(reloaded)
    assert migrated_dict == reloaded_dict


# -----------------------------------------------------------------------------
# Tilleggstester — gjenoppretter dekning fra 4 tester fjernet i C1b-refactor
# -----------------------------------------------------------------------------


def test_new_game_state_has_pitch_lake_defaults_from_balance() -> None:
    """save.new_game_state() skal lese pitch-lake-defaults fra balance
    singleton (ikke hardkodede tall). Gjenoppretter dekning fra tidligere
    `test_fresh_state_save_has_pitch_lake_with_upkeep`.
    """
    from systems import balance, save

    gs = save.new_game_state()
    bal = balance.get()
    assert gs.pitch_lake_state.production_per_day == bal.pitch_lake.production_per_day
    assert gs.pitch_lake_state.upkeep_per_day == bal.pitch_lake.upkeep_per_day
    assert gs.pitch_lake_state.total_produced == 0
    assert gs.pitch_lake_state.last_production_day == 0
    assert gs.pitch_lake_state.pending_units == 0
    assert gs.pitch_lake_state.home_port == "tortuga"


def test_v3_migration_fills_pitch_lake_with_balance_defaults(
    tmp_path: Path,
) -> None:
    """v3-save (uten pitch_lake-felt) skal etter v3→v4→v5-kjeden ha
    pitch_lake_state med balance-defaults. Gjenoppretter dekning fra
    tidligere `test_v3_loads_with_default_pitch_lake`.
    """
    from systems import balance

    v3 = {
        "version": 3,
        "gold": 300,
        "inventory": {
            "sugar":   {"quantity": 0, "avg_cost": 0.0},
            "rum":     {"quantity": 0, "avg_cost": 0.0},
            "tobacco": {"quantity": 0, "avg_cost": 0.0},
            "pitch":   {"quantity": 0, "avg_cost": 0.0},
        },
        "current_scene": "village",
        "player_position": [320.0, 280.0],
        "clock": {"day": 5, "seconds_into_day": 0.0, "seconds_per_day": 180.0},
        "commodities_state": {},
        # Ingen cargo_capacity, regimes eller pitch_lake — v3-minimum.
    }
    path = tmp_path / "v3.json"
    path.write_text(json.dumps(v3), encoding="utf-8")

    loaded = load(str(path))
    assert loaded is not None
    bal = balance.get()
    assert loaded.pitch_lake_state.production_per_day == bal.pitch_lake.production_per_day
    assert loaded.pitch_lake_state.upkeep_per_day == bal.pitch_lake.upkeep_per_day
    assert loaded.pitch_lake_state.total_produced == 0
    assert loaded.pitch_lake_state.last_production_day == 0


def test_v4_missing_upkeep_field_gets_balance_default(tmp_path: Path) -> None:
    """v4-save fra tidlig Commit 6 har pitch_lake uten daily_upkeep_cost.
    Migrering skal fylle fra balance.pitch_lake.upkeep_per_day.
    Gjenoppretter dekning fra tidligere `test_missing_upkeep_defaults_to_eight`.
    """
    from systems import balance

    v4_no_upkeep = {
        "version": 4,
        "gold": 300,
        "inventory": {
            "sugar":   {"quantity": 0, "avg_cost": 0.0},
            "rum":     {"quantity": 0, "avg_cost": 0.0},
            "tobacco": {"quantity": 0, "avg_cost": 0.0},
            "pitch":   {"quantity": 0, "avg_cost": 0.0},
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
            # daily_upkeep_cost mangler eksplisitt
        },
    }
    path = tmp_path / "v4_no_upkeep.json"
    path.write_text(json.dumps(v4_no_upkeep), encoding="utf-8")

    loaded = load(str(path))
    assert loaded is not None
    bal = balance.get()
    # Manglende upkeep → fra balance
    assert loaded.pitch_lake_state.upkeep_per_day == bal.pitch_lake.upkeep_per_day
    # Eksisterende felt bevart gjennom migreringen
    assert loaded.pitch_lake_state.production_per_day == 2
    assert loaded.pitch_lake_state.total_produced == 10
    assert loaded.pitch_lake_state.last_production_day == 5


def test_corrupt_pitch_lake_fields_fall_back_to_defaults(
    tmp_path: Path,
) -> None:
    """v5-save med ugyldige strings i pitch_lake_state-felter skal falle
    tilbake til balance-defaults via _parse_pitch_lake_state sin try/except.
    load() skal returnere et gyldig GameState, ikke None.

    Gjenoppretter dekning fra tidligere
    `test_corrupt_pitch_lake_falls_back_to_default`.
    """
    from systems import balance

    corrupt = {
        "version": 5,
        "player_state": {
            "position_x": 320.0,
            "gold": 100,
            "inventory": {
                "sugar":   {"quantity": 0, "avg_cost": 0.0},
                "rum":     {"quantity": 0, "avg_cost": 0.0},
                "tobacco": {"quantity": 0, "avg_cost": 0.0},
                "pitch":   {"quantity": 0, "avg_cost": 0.0},
            },
        },
        "world_state": {
            "current_port": "tortuga",
            "clock": {"day": 1, "seconds_into_day": 0.0, "seconds_per_day": 180.0},
            "ship": {"class_id": "sloop", "name": "Sjarken", "cargo_capacity": 40},
            "voyage": None,
        },
        "economy_state": {
            "markets": {"tortuga": {"commodities": {}}},
            "regimes": {"tortuga": {}},
            "observed": {},
        },
        "pitch_lake_state": {
            "home_port": "tortuga",
            "production_per_day": "nei",
            "upkeep_per_day": "tolv",
            "pending_units": None,
            "total_produced": None,
            "last_production_day": "aldri",
        },
    }
    path = tmp_path / "corrupt_pl.json"
    path.write_text(json.dumps(corrupt), encoding="utf-8")

    loaded = load(str(path))
    assert loaded is not None  # Skal IKKE bli None — defensiv fallback
    bal = balance.get()
    # Alle korrupte felter → defaults
    assert loaded.pitch_lake_state.production_per_day == bal.pitch_lake.production_per_day
    assert loaded.pitch_lake_state.upkeep_per_day == bal.pitch_lake.upkeep_per_day
    assert loaded.pitch_lake_state.pending_units == 0
    assert loaded.pitch_lake_state.total_produced == 0
    assert loaded.pitch_lake_state.last_production_day == 0
