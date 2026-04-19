"""Tester for Tortuga-sync: state.markets["tortuga"] skal alltid matche
self._market etter mutasjoner (Fase 2B C2).

Siden Market og state.economy_state.markets["tortuga"] er dobbeltrepresenta-
sjon av Tortugas markedsdata, må disse holdes i synk via `sync_market_to_state`
etter hver mutasjon i Market. Denne test-filen verifiserer kontrakten.

Mutasjonspunkter (dokumentert på Market-klassen):
- on_dawn: pris-drift (prices endres)
- buy: ingen pris-endring (kun inventory/gold)
- sell: ingen pris-endring (kun inventory/gold)
- clamp_to_price_bounds: kan endre priser
- direkte ekstern mutasjon (via commodity.current_price = ...): ved hydration
"""

from __future__ import annotations

import random

from entities.commodity import Commodity, InventoryItem
from state.market_state import CommodityMarket, MarketState
from systems.economy import Market, sync_market_to_state
from systems.regime_manager import RegimeState


def _market() -> Market:
    return Market(
        [
            Commodity(
                id="sugar", name="Sukker", base_price=40.0,
                current_price=40.0, volatility=0.15,
            ),
            Commodity(
                id="rum", name="Rom", base_price=75.0,
                current_price=75.0, volatility=0.20,
            ),
            Commodity(
                id="tobacco", name="Tobakk", base_price=90.0,
                current_price=90.0, volatility=0.10,
            ),
            Commodity(
                id="pitch", name="Bek", base_price=40.0,
                current_price=40.0, volatility=0.25,
            ),
        ],
        rng=random.Random(42),
    )


def _assert_in_sync(market: Market, state: MarketState) -> None:
    """Alle commodities i Market skal matche state eksakt."""
    for c in market.commodities:
        cm = state.commodities[c.id]
        assert cm.current_price == c.current_price, (
            f"{c.id}: state={cm.current_price} market={c.current_price}"
        )
        assert cm.price_history == c.price_history, (
            f"{c.id} history: state={cm.price_history} market={c.price_history}"
        )


class TestSyncHelper:
    def test_sync_copies_all_commodities(self):
        m = _market()
        state = MarketState()
        sync_market_to_state(m, state)
        assert set(state.commodities.keys()) == {"sugar", "rum", "tobacco", "pitch"}
        _assert_in_sync(m, state)

    def test_sync_overwrites_previous_state(self):
        m = _market()
        state = MarketState(commodities={
            "sugar": CommodityMarket(current_price=999.0, price_history=[1.0]),
        })
        sync_market_to_state(m, state)
        assert state.commodities["sugar"].current_price == 40.0
        assert state.commodities["sugar"].price_history == []


class TestTortugaMarketSyncsToStateOnDawnBuySell:
    """Verifiser at state.markets["tortuga"] holdes i synk etter hver
    Market-operasjon som scenen kjører: on_dawn (priser endres) og
    buy/sell (priser uendret, men kontrakten holder).
    """

    def test_initial_sync_matches(self):
        m = _market()
        state = MarketState()
        sync_market_to_state(m, state)
        _assert_in_sync(m, state)

    def test_sync_after_on_dawn(self):
        m = _market()
        state = MarketState()
        sync_market_to_state(m, state)
        # Dawn endrer priser
        regimes = {
            "sugar":   RegimeState(current="rising",  days_remaining=3),
            "rum":     RegimeState(current="stable",  days_remaining=3),
            "tobacco": RegimeState(current="falling", days_remaining=3),
            "pitch":   RegimeState(current="rising",  days_remaining=3),
        }
        m.on_dawn(regimes)
        # Før sync: state har gamle priser, Market har nye — ut av synk.
        # Dette er den kritiske invarianten scenen må opprettholde:
        sync_market_to_state(m, state)
        _assert_in_sync(m, state)
        # price_history skal også være synket etter dawn
        assert len(state.commodities["sugar"].price_history) == 1

    def test_sync_preserved_after_buy(self):
        """buy endrer ikke priser, men sync er fortsatt trygg."""
        m = _market()
        state = MarketState()
        sync_market_to_state(m, state)
        # Kjøp sugar — priser uendret, kun inventory og gold
        m.buy("sugar", 5, gold=1000, inventory={})
        # State skal fortsatt matche Market (trivielt for pris;
        # kontrakts-bekreftelse)
        _assert_in_sync(m, state)

    def test_sync_preserved_after_sell(self):
        m = _market()
        state = MarketState()
        sync_market_to_state(m, state)
        inventory = {"sugar": InventoryItem(quantity=10, avg_cost=40.0)}
        m.sell("sugar", 3, gold=100, inventory=inventory)
        _assert_in_sync(m, state)

    def test_sync_after_multiple_dawns(self):
        """Flere dawns etter hverandre: hver sync skal bringe state opp
        til dato med Market, og price_history akkumuleres korrekt.
        """
        m = _market()
        state = MarketState()
        sync_market_to_state(m, state)
        regimes = {
            "sugar":   RegimeState(current="rising",  days_remaining=10),
            "rum":     RegimeState(current="stable",  days_remaining=10),
            "tobacco": RegimeState(current="falling", days_remaining=10),
            "pitch":   RegimeState(current="rising",  days_remaining=10),
        }
        for _ in range(5):
            m.on_dawn(regimes)
            sync_market_to_state(m, state)
        _assert_in_sync(m, state)
        assert len(state.commodities["sugar"].price_history) == 5
