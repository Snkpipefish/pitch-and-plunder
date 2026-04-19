"""Tester for `tick_all_ports_dawn` og `write_observed_for_port`
(Fase 2B C7a — fellesfunksjoner ekstrahert fra PortVillageScene/save).

Dekker:
- `tick_all_ports_dawn`: muterer alle 4 markeder per kall (tick_id-bumps)
- `write_observed_for_port`: skriver alle catalog-varer med korrekt
  day_seen, overskriver eksisterende oppføringer, no-op ved tomt marked
- new_game_state har observed["tortuga"] populert
- v4→v5-migrering bevarer observed["tortuga"]-priser etter helper-bytte
"""

from __future__ import annotations

import json
import random
from pathlib import Path

from state.market_state import CommodityMarket, MarketState
from state.observed_price import ObservedPrice
from systems import save as save_module
from systems.economy import (
    Market,
    tick_all_ports_dawn,
    write_observed_for_port,
)
from systems.regime_manager import RegimeManager


FIXTURE_V4 = Path(__file__).parent / "fixtures" / "save_v4.json"


# -----------------------------------------------------------------------------
# tick_all_ports_dawn
# -----------------------------------------------------------------------------


def test_tick_all_ports_dawn_bumps_tick_id_for_all_four_ports() -> None:
    """Per kall: alle 4 havners MarketState.tick_id må inkrementeres
    (Market.on_dawn ansvar). Verifiserer at modul-funksjonen itererer
    over alle havner i port_config.
    """
    state = save_module.new_game_state()
    market = Market.from_json("data/commodities.json")
    regime_manager = RegimeManager(rng=random.Random(0))

    before = {
        pid: ms.tick_id
        for pid, ms in state.economy_state.markets.items()
    }

    tick_all_ports_dawn(state, market, regime_manager)

    after = {
        pid: ms.tick_id
        for pid, ms in state.economy_state.markets.items()
    }
    assert set(after.keys()) == {"tortuga", "port_royal", "havana", "nassau"}
    for pid in after:
        assert after[pid] == before[pid] + 1, (
            f"tick_id for {pid}: {before[pid]} → {after[pid]}"
        )


def test_tick_all_ports_dawn_advances_regimes_per_port() -> None:
    """Hver havns regime-dict skal få sin `days_remaining` dekrementert
    (regime_manager.on_new_day ansvar). Verifiser at funksjonen kaller
    on_new_day per havn ved å sjekke dekremenrt.
    """
    state = save_module.new_game_state()
    # Sett alle regimers days_remaining til en kjent verdi
    for pid, regimes in state.economy_state.regimes.items():
        for regime in regimes.values():
            regime.days_remaining = 5

    market = Market.from_json("data/commodities.json")
    regime_manager = RegimeManager(rng=random.Random(0))
    tick_all_ports_dawn(state, market, regime_manager)

    for pid, regimes in state.economy_state.regimes.items():
        for cid, regime in regimes.items():
            assert regime.days_remaining == 4, (
                f"{pid}.{cid}: days_remaining {regime.days_remaining}"
            )


# -----------------------------------------------------------------------------
# write_observed_for_port
# -----------------------------------------------------------------------------


def test_write_observed_writes_all_catalog_commodities() -> None:
    """Alle commodities i markedet for port_id skal få ObservedPrice-
    oppføring med matching pris og clock.day.
    """
    state = save_module.new_game_state()
    state.world_state.clock.day = 7
    state.economy_state.observed.clear()  # bevisst tom utgangspunkt

    write_observed_for_port(state, "port_royal")

    pr_observed = state.economy_state.observed["port_royal"]
    pr_market = state.economy_state.markets["port_royal"]
    assert set(pr_observed.keys()) == set(pr_market.commodities.keys())
    for cid, obs in pr_observed.items():
        assert isinstance(obs, ObservedPrice)
        assert obs.price == pr_market.commodities[cid].current_price
        assert obs.day_seen == 7


def test_write_observed_overwrites_existing_entries() -> None:
    """Andre kall til samme port_id skal overskrive prisene fra forrige
    snapshot — ferskere data vinner alltid.
    """
    state = save_module.new_game_state()
    state.world_state.clock.day = 3
    write_observed_for_port(state, "tortuga")
    first = dict(state.economy_state.observed["tortuga"])

    # Endre marked-prisene og dagen, snapshot på nytt
    sugar = state.economy_state.markets["tortuga"].commodities["sugar"]
    sugar.current_price = 999.0
    state.world_state.clock.day = 12
    write_observed_for_port(state, "tortuga")

    second = state.economy_state.observed["tortuga"]
    assert second["sugar"].price == 999.0
    assert second["sugar"].day_seen == 12
    # Andre commodities også oppdatert til day=12
    for cid in second:
        assert second[cid].day_seen == 12
    # Verdiene er forskjellige fra første snapshot
    assert second["sugar"].day_seen != first["sugar"].day_seen


def test_write_observed_noop_for_empty_market() -> None:
    """Hvis port_id mangler eller har tom commodities-dict, skal
    funksjonen være no-op (ingen port-key opprettes).
    """
    state = save_module.new_game_state()
    state.economy_state.markets["tortuga"] = MarketState()  # tøm
    state.economy_state.observed.clear()

    write_observed_for_port(state, "tortuga")
    assert "tortuga" not in state.economy_state.observed

    # Ukjent port_id: ingen krasj, ingen mutasjon
    write_observed_for_port(state, "atlantis")
    assert "atlantis" not in state.economy_state.observed


def test_write_observed_only_affects_target_port() -> None:
    """C8-presisering: write_observed_for_port skal IKKE røre andre
    havners observed-data. Defensivt mot eventuell shared-mutation.
    """
    state = save_module.new_game_state()
    state.world_state.clock.day = 5
    # Snapshot to havner
    write_observed_for_port(state, "tortuga")
    write_observed_for_port(state, "port_royal")
    pr_before = {
        cid: (obs.price, obs.day_seen)
        for cid, obs in state.economy_state.observed["port_royal"].items()
    }

    # Endre dag og snapshot bare Tortuga på nytt
    state.world_state.clock.day = 12
    write_observed_for_port(state, "tortuga")

    # Tortuga er oppdatert til dag 12
    for cid, obs in state.economy_state.observed["tortuga"].items():
        assert obs.day_seen == 12
    # Port Royal er UENDRET — fortsatt dag 5
    for cid, obs in state.economy_state.observed["port_royal"].items():
        assert obs.day_seen == pr_before[cid][1]
        assert obs.price == pr_before[cid][0]


# -----------------------------------------------------------------------------
# new_game_state-integrasjon
# -----------------------------------------------------------------------------


def test_new_game_state_has_tortuga_observed_populated() -> None:
    """save.new_game_state skal kalle write_observed_for_port for
    Tortuga (spilleren spawn-er der), slik at startposisjon har
    observed-data uten å måtte besøke børsen først.
    """
    state = save_module.new_game_state()
    assert "tortuga" in state.economy_state.observed
    tortuga_observed = state.economy_state.observed["tortuga"]
    assert set(tortuga_observed.keys()) == {
        "sugar", "rum", "tobacco", "pitch"
    }
    # day_seen = 1 (fersk klokke)
    for cid, obs in tortuga_observed.items():
        assert obs.day_seen == 1
        # Pris matcher market_state.current_price (bias × base)
        market_price = state.economy_state.markets["tortuga"].commodities[cid].current_price
        assert obs.price == market_price


def test_new_game_state_has_no_observed_for_other_ports() -> None:
    """Bare Tortuga spawn-er observert; andre havner forblir 'aldri besøkt'
    inntil spilleren faktisk reiser dit (C7c-arrival).
    """
    state = save_module.new_game_state()
    for pid in ("port_royal", "havana", "nassau"):
        assert pid not in state.economy_state.observed


# -----------------------------------------------------------------------------
# v4→v5-migrering bevarer observed["tortuga"] etter refactor
# -----------------------------------------------------------------------------


def test_v4_migration_observed_tortuga_matches_market_prices(tmp_path) -> None:
    """Etter C7a-refactor bygges observed["tortuga"] post-parse via
    write_observed_for_port. Den skal fortsatt matche v4 current_price
    nøyaktig (siden write_observed leser fra parsed market, som ble
    fylt fra v4 commodities_state).
    """
    fixture_copy = tmp_path / "save_v4.json"
    fixture_copy.write_text(
        FIXTURE_V4.read_text(encoding="utf-8"), encoding="utf-8"
    )
    with open(FIXTURE_V4, "r", encoding="utf-8") as fh:
        v4_raw = json.load(fh)

    loaded = save_module.load(str(fixture_copy))
    assert loaded is not None

    observed_tortuga = loaded.economy_state.observed["tortuga"]
    v4_day = v4_raw["clock"]["day"]
    for cid, v4_c in v4_raw["commodities_state"].items():
        obs = observed_tortuga[cid]
        assert obs.price == v4_c["current_price"], (
            f"{cid}: observed={obs.price}, v4={v4_c['current_price']}"
        )
        assert obs.day_seen == v4_day
