"""Tester for Market.buy() – spesielt lagerbegrensning (Fase 2A Commit 4).

Selger-testen er dekket implisitt siden Market.sell ikke aendret seg i
Commit 4; vi tester primaert nye cargo_capacity-invarianter.
"""

from __future__ import annotations

from entities.commodity import Commodity, InventoryItem
from systems.economy import Market


def _market() -> Market:
    return Market(
        [
            Commodity(id="sugar", name="Sukker", base_price=40.0,
                      current_price=40.0, volatility=0.0),
            Commodity(id="rum", name="Rom", base_price=80.0,
                      current_price=80.0, volatility=0.0),
        ]
    )


def _empty_inv() -> dict[str, InventoryItem]:
    return {"sugar": InventoryItem(), "rum": InventoryItem()}


class TestBuyWithoutCargoLimit:
    def test_buy_without_cargo_capacity_arg_is_backward_compat(self):
        m = _market()
        inv = _empty_inv()
        new_gold, new_inv, bought = m.buy("sugar", 5, gold=1000, inventory=inv)
        assert bought == 5
        assert new_inv["sugar"].quantity == 5

    def test_gold_constraint_still_works(self):
        m = _market()
        inv = _empty_inv()
        # Kjop-pris = 40 * 1.02 = 40.8 → avrundet til 41
        # Med 100 gull kan man kjope 2 enheter (82), ikke 3 (123)
        new_gold, new_inv, bought = m.buy(
            "sugar", 10, gold=100, inventory=inv
        )
        assert bought == 2
        assert new_gold == 100 - 2 * 41


class TestBuyWithCargoLimit:
    def test_empty_cargo_allows_full_purchase(self):
        m = _market()
        inv = _empty_inv()
        _, new_inv, bought = m.buy(
            "sugar", 10, gold=10_000, inventory=inv, cargo_capacity=40
        )
        assert bought == 10
        assert new_inv["sugar"].quantity == 10

    def test_partial_cargo_clamps_to_available_space(self):
        m = _market()
        inv = {"sugar": InventoryItem(quantity=35), "rum": InventoryItem()}
        _, new_inv, bought = m.buy(
            "rum", 20, gold=10_000, inventory=inv, cargo_capacity=40
        )
        # 40-35 = 5 ledige plasser; forsoek paa 20 → kun 5 kjopt
        assert bought == 5
        assert new_inv["rum"].quantity == 5
        assert new_inv["sugar"].quantity == 35

    def test_full_cargo_blocks_purchase(self):
        m = _market()
        inv = {"sugar": InventoryItem(quantity=40), "rum": InventoryItem()}
        gold_before = 10_000
        new_gold, new_inv, bought = m.buy(
            "rum", 5, gold=gold_before, inventory=inv, cargo_capacity=40
        )
        assert bought == 0
        assert new_gold == gold_before
        assert new_inv["rum"].quantity == 0
        assert new_inv["sugar"].quantity == 40

    def test_cargo_limit_tighter_than_gold_wins(self):
        m = _market()
        inv = {"sugar": InventoryItem(quantity=38), "rum": InventoryItem()}
        # Gull nok til 100 enheter sukker, men bare 2 ledige plasser
        _, new_inv, bought = m.buy(
            "sugar", 100, gold=100_000, inventory=inv, cargo_capacity=40
        )
        assert bought == 2
        assert new_inv["sugar"].quantity == 40

    def test_gold_limit_tighter_than_cargo_wins(self):
        m = _market()
        inv = _empty_inv()
        # Cargo 40 ledig, men gull kun til 2 enheter
        _, new_inv, bought = m.buy(
            "sugar", 100, gold=100, inventory=inv, cargo_capacity=40
        )
        assert bought == 2  # 2 * 41 = 82 <= 100, men 3 * 41 = 123 > 100

    def test_total_across_commodities_counts(self):
        m = _market()
        # Begge varer teller mot samme total
        inv = {
            "sugar": InventoryItem(quantity=20),
            "rum": InventoryItem(quantity=15),
        }
        # Totalt = 35, 5 plasser ledig
        _, new_inv, bought = m.buy(
            "rum", 10, gold=10_000, inventory=inv, cargo_capacity=40
        )
        assert bought == 5
        assert new_inv["rum"].quantity == 20


class TestAvgCostPreservedUnderCargoClamp:
    def test_avg_cost_calculated_on_actual_bought_amount(self):
        m = _market()
        inv = {"sugar": InventoryItem(quantity=35, avg_cost=50.0),
               "rum": InventoryItem()}
        # Kun 5 plasser ledige; snitt regnes paa 5 nye enheter
        _, new_inv, bought = m.buy(
            "sugar", 10, gold=10_000, inventory=inv, cargo_capacity=40
        )
        assert bought == 5
        # Gammel: 35 @ 50.0. Nye 5 @ 41 (kjop-pris). Ny snitt:
        # (35*50 + 5*41) / 40 = (1750 + 205) / 40 = 48.875
        expected = (35 * 50.0 + 5 * 41) / 40
        assert abs(new_inv["sugar"].avg_cost - expected) < 1e-6


class TestEdgeCases:
    def test_cargo_capacity_zero_blocks_everything(self):
        m = _market()
        _, _, bought = m.buy(
            "sugar", 10, gold=10_000, inventory=_empty_inv(), cargo_capacity=0
        )
        assert bought == 0

    def test_zero_amount_returns_zero(self):
        m = _market()
        _, _, bought = m.buy(
            "sugar", 0, gold=10_000, inventory=_empty_inv(), cargo_capacity=40
        )
        assert bought == 0

    def test_negative_amount_returns_zero(self):
        m = _market()
        _, _, bought = m.buy(
            "sugar", -5, gold=10_000, inventory=_empty_inv(), cargo_capacity=40
        )
        assert bought == 0
