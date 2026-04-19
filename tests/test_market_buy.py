"""Tester for Market.buy() og sell() — lagerbegrensning og gebyr.

Oppdatert i Fase 2B C4 til stateless Market-signatur: hver transaksjons-
metode tar `market_state: MarketState` som eksplisitt parameter.
"""

from __future__ import annotations

from entities.commodity import Commodity, InventoryItem
from state.market_state import CommodityMarket, MarketState
from systems.economy import Market


def _market_and_state() -> tuple[Market, MarketState]:
    """Bygger Market-katalog + MarketState med samme current_price som
    base_price for forutsigbare pris-beregninger.
    """
    catalog = [
        Commodity(id="sugar", name="Sukker", base_price=40.0,
                  current_price=40.0, volatility=0.0),
        Commodity(id="rum", name="Rom", base_price=80.0,
                  current_price=80.0, volatility=0.0),
    ]
    state = MarketState(commodities={
        "sugar": CommodityMarket(current_price=40.0),
        "rum":   CommodityMarket(current_price=80.0),
    })
    return Market(catalog), state


def _empty_inv() -> dict[str, InventoryItem]:
    return {"sugar": InventoryItem(), "rum": InventoryItem()}


class TestBuyWithoutCargoLimit:
    def test_buy_without_cargo_capacity_arg_is_backward_compat(self):
        m, ms = _market_and_state()
        inv = _empty_inv()
        new_gold, new_inv, bought = m.buy(ms, "sugar", 5, gold=1000, inventory=inv)
        assert bought == 5
        assert new_inv["sugar"].quantity == 5

    def test_gold_constraint_still_works(self):
        m, ms = _market_and_state()
        inv = _empty_inv()
        # Kjøp-pris = 40 * 1.02 = 40.8 → avrundet til 41. Gebyr = 5.
        # Med 100 gull: (100 - 5) / 41 = 2.32 → 2 enheter. Total: 82 + 5 = 87.
        new_gold, new_inv, bought = m.buy(
            ms, "sugar", 10, gold=100, inventory=inv
        )
        assert bought == 2
        assert new_gold == 100 - 2 * 41 - 5  # 13


class TestBuyWithCargoLimit:
    def test_empty_cargo_allows_full_purchase(self):
        m, ms = _market_and_state()
        inv = _empty_inv()
        _, new_inv, bought = m.buy(
            ms, "sugar", 10, gold=10_000, inventory=inv, cargo_capacity=40
        )
        assert bought == 10
        assert new_inv["sugar"].quantity == 10

    def test_partial_cargo_clamps_to_available_space(self):
        m, ms = _market_and_state()
        inv = {"sugar": InventoryItem(quantity=35), "rum": InventoryItem()}
        _, new_inv, bought = m.buy(
            ms, "rum", 20, gold=10_000, inventory=inv, cargo_capacity=40
        )
        # 40-35 = 5 ledige plasser; forsøk på 20 → kun 5 kjøpt
        assert bought == 5
        assert new_inv["rum"].quantity == 5
        assert new_inv["sugar"].quantity == 35

    def test_full_cargo_blocks_purchase(self):
        m, ms = _market_and_state()
        inv = {"sugar": InventoryItem(quantity=40), "rum": InventoryItem()}
        gold_before = 10_000
        new_gold, new_inv, bought = m.buy(
            ms, "rum", 5, gold=gold_before, inventory=inv, cargo_capacity=40
        )
        assert bought == 0
        assert new_gold == gold_before
        assert new_inv["rum"].quantity == 0
        assert new_inv["sugar"].quantity == 40

    def test_cargo_limit_tighter_than_gold_wins(self):
        m, ms = _market_and_state()
        inv = {"sugar": InventoryItem(quantity=38), "rum": InventoryItem()}
        # Gull nok til 100 enheter sukker, men bare 2 ledige plasser
        _, new_inv, bought = m.buy(
            ms, "sugar", 100, gold=100_000, inventory=inv, cargo_capacity=40
        )
        assert bought == 2
        assert new_inv["sugar"].quantity == 40

    def test_gold_limit_tighter_than_cargo_wins(self):
        m, ms = _market_and_state()
        inv = _empty_inv()
        # Cargo 40 ledig, men gull kun til 2 enheter (inkl. 5 gebyr)
        _, new_inv, bought = m.buy(
            ms, "sugar", 100, gold=100, inventory=inv, cargo_capacity=40
        )
        # (100 - 5) / 41 = 2 enheter, total 82+5=87
        assert bought == 2

    def test_total_across_commodities_counts(self):
        m, ms = _market_and_state()
        # Begge varer teller mot samme total
        inv = {
            "sugar": InventoryItem(quantity=20),
            "rum": InventoryItem(quantity=15),
        }
        # Totalt = 35, 5 plasser ledig
        _, new_inv, bought = m.buy(
            ms, "rum", 10, gold=10_000, inventory=inv, cargo_capacity=40
        )
        assert bought == 5
        assert new_inv["rum"].quantity == 20


class TestAvgCostPreservedUnderCargoClamp:
    def test_avg_cost_calculated_on_actual_bought_amount(self):
        m, ms = _market_and_state()
        inv = {"sugar": InventoryItem(quantity=35, avg_cost=50.0),
               "rum": InventoryItem()}
        # Kun 5 plasser ledige; snitt regnes på 5 nye enheter
        _, new_inv, bought = m.buy(
            ms, "sugar", 10, gold=10_000, inventory=inv, cargo_capacity=40
        )
        assert bought == 5
        # Gammel: 35 @ 50.0. Nye 5 @ 41 (kjøp-pris). Ny snitt:
        # (35*50 + 5*41) / 40 = (1750 + 205) / 40 = 48.875
        expected = (35 * 50.0 + 5 * 41) / 40
        assert abs(new_inv["sugar"].avg_cost - expected) < 1e-6


class TestEdgeCases:
    def test_cargo_capacity_zero_blocks_everything(self):
        m, ms = _market_and_state()
        _, _, bought = m.buy(
            ms, "sugar", 10, gold=10_000, inventory=_empty_inv(), cargo_capacity=0
        )
        assert bought == 0

    def test_zero_amount_returns_zero(self):
        m, ms = _market_and_state()
        _, _, bought = m.buy(
            ms, "sugar", 0, gold=10_000, inventory=_empty_inv(), cargo_capacity=40
        )
        assert bought == 0

    def test_negative_amount_returns_zero(self):
        m, ms = _market_and_state()
        _, _, bought = m.buy(
            ms, "sugar", -5, gold=10_000, inventory=_empty_inv(), cargo_capacity=40
        )
        assert bought == 0


# -----------------------------------------------------------------------------
# Commit 7: Transaksjonsgebyr
# -----------------------------------------------------------------------------

class TestTransactionFeeBuy:
    def test_fee_deducted_from_gold_on_buy(self):
        m, ms = _market_and_state()
        inv = _empty_inv()
        # 5 enheter sugar @ 41 = 205, + 5 gebyr = 210.
        new_gold, _, bought = m.buy(ms, "sugar", 5, gold=1000, inventory=inv)
        assert bought == 5
        assert new_gold == 1000 - 5 * 41 - 5  # 790

    def test_fee_prevents_buy_when_gold_covers_price_but_not_fee(self):
        # Pris 41, gebyr 5 → trenger 46. Med 45 gull skal kjøp blokkeres.
        m, ms = _market_and_state()
        new_gold, _, bought = m.buy(
            ms, "sugar", 1, gold=45, inventory=_empty_inv()
        )
        assert bought == 0
        assert new_gold == 45  # gull uendret

    def test_fee_allows_buy_when_gold_covers_price_plus_fee(self):
        # 46 gull = akkurat til 1 enhet + gebyr
        m, ms = _market_and_state()
        new_gold, _, bought = m.buy(
            ms, "sugar", 1, gold=46, inventory=_empty_inv()
        )
        assert bought == 1
        assert new_gold == 0

    def test_fee_not_charged_on_failed_buy(self):
        # Gull under minimum → ingen kjøp, ingen gebyr trukket
        m, ms = _market_and_state()
        new_gold, _, bought = m.buy(
            ms, "sugar", 10, gold=10, inventory=_empty_inv()
        )
        assert bought == 0
        assert new_gold == 10  # uendret, ingen gebyr

    def test_fee_is_flat_not_per_unit(self):
        # 2 enheter: én flat 5-gebyr. 10 enheter: samme flate 5-gebyr.
        m, ms = _market_and_state()
        _, _, bought_2 = m.buy(ms, "sugar", 2, gold=100, inventory=_empty_inv())
        # Med 100 gull skal vi få 2 enheter (87), ikke begrenset av flere gebyrer
        assert bought_2 == 2

    def test_fee_does_not_affect_avg_cost(self):
        # Gebyret er en transaksjonskost, ikke en varekost
        m, ms = _market_and_state()
        _, new_inv, _ = m.buy(
            ms, "sugar", 3, gold=1000, inventory=_empty_inv()
        )
        assert new_inv["sugar"].avg_cost == 41.0


class TestTransactionFeeSell:
    def test_fee_deducted_from_sell_proceeds(self):
        # Sell-pris sukker = 40 * 0.98 = 39.2 → 39.
        # Selge 5: 5*39 = 195 - 5 gebyr = 190.
        m, ms = _market_and_state()
        inv = {"sugar": InventoryItem(quantity=10, avg_cost=40.0),
               "rum": InventoryItem()}
        new_gold, _, sold = m.sell(ms, "sugar", 5, gold=100, inventory=inv)
        assert sold == 5
        assert new_gold == 100 + 5 * 39 - 5  # 290

    def test_fee_refuses_sell_if_proceeds_negative(self):
        # Edge case: sell-pris 0 (umulig i praksis, men defensivt).
        m = Market(
            [Commodity(id="free", name="Gratis", base_price=1.0,
                       current_price=0.0, volatility=0.0)],
        )
        ms = MarketState(commodities={
            "free": CommodityMarket(current_price=0.0),
        })
        inv = {"free": InventoryItem(quantity=3, avg_cost=0.0)}
        new_gold, _, sold = m.sell(ms, "free", 1, gold=0, inventory=inv)
        # 1*0 - 5 = -5 → refuser
        assert sold == 0
        assert new_gold == 0

    def test_fee_not_charged_on_zero_amount(self):
        m, ms = _market_and_state()
        inv = {"sugar": InventoryItem(quantity=5, avg_cost=40.0),
               "rum": InventoryItem()}
        new_gold, _, sold = m.sell(ms, "sugar", 0, gold=100, inventory=inv)
        assert sold == 0
        assert new_gold == 100
