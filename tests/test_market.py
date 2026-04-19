"""Tester for `Market.on_dawn`, `compute_trend`, `clamp_to_price_bounds`.

Oppdatert i Fase 2B C4 til stateless Market-signatur: alle mutasjoner
opererer på `market_state: MarketState` som eksplisitt parameter.
"""

from __future__ import annotations

import random

from entities.commodity import (
    PRICE_HISTORY_WINDOW,
    Commodity,
    compute_trend,
)
from state.market_state import CommodityMarket, MarketState
from systems import balance as _balance
from systems.economy import (
    PRICE_MAX_MULT,
    PRICE_MIN_MULT,
    Market,
)
from systems.regime_manager import RegimeState


def _daily_magnitude_max() -> float:
    """Øvre grense for rising-drift som fraksjon. Leses fra balance."""
    return _balance.get().regimes.drift_pct_rising[1] / 100.0


def _market_and_state(seed: int = 42) -> tuple[Market, MarketState]:
    """Bygger Market-katalog + MarketState med start-priser = base_price."""
    catalog = [
        Commodity(
            id="sugar", name="Sukker", base_price=40.0,
            current_price=40.0, volatility=0.15,
        ),
        Commodity(
            id="rum", name="Rom", base_price=80.0,
            current_price=80.0, volatility=0.20,
        ),
    ]
    state = MarketState(commodities={
        "sugar": CommodityMarket(current_price=40.0),
        "rum":   CommodityMarket(current_price=80.0),
    })
    return Market(catalog, rng=random.Random(seed)), state


def _regimes(current: str = "stable") -> dict[str, RegimeState]:
    return {
        "sugar": RegimeState(current=current, days_remaining=5),
        "rum": RegimeState(current=current, days_remaining=5),
    }


# -----------------------------------------------------------------------------
# Market.on_dawn
# -----------------------------------------------------------------------------

class TestOnDawnRegimeDirection:
    def test_rising_accumulates_upward_over_5_days(self):
        m, ms = _market_and_state()
        regs = _regimes("rising")
        start_sugar = ms.commodities["sugar"].current_price
        for _ in range(5):
            m.on_dawn(ms, regs)
        end_sugar = ms.commodities["sugar"].current_price
        assert end_sugar > start_sugar * 1.05, (
            f"Rising-regime: pris {start_sugar} → {end_sugar} steg ikke nok"
        )

    def test_falling_accumulates_downward_over_5_days(self):
        m, ms = _market_and_state(seed=17)
        regs = _regimes("falling")
        start = ms.commodities["sugar"].current_price
        for _ in range(5):
            m.on_dawn(ms, regs)
        end = ms.commodities["sugar"].current_price
        assert end < start * 0.95, (
            f"Falling-regime: pris {start} → {end} falt ikke nok"
        )

    def test_stable_stays_within_bounds_over_5_days(self):
        m, ms = _market_and_state(seed=3)
        regs = _regimes("stable")
        start = ms.commodities["sugar"].current_price
        for _ in range(5):
            m.on_dawn(ms, regs)
        end = ms.commodities["sugar"].current_price
        ratio = end / start
        assert 0.95 < ratio < 1.05, (
            f"Stable-regime: pris {start} → {end} drev for mye ({ratio})"
        )


class TestOnDawnClamp:
    def test_price_cannot_fall_below_base_times_min_mult(self):
        m, ms = _market_and_state(seed=7)
        regs = _regimes("falling")
        for _ in range(100):
            m.on_dawn(ms, regs)
        for c in m.commodities:
            cm = ms.commodities[c.id]
            assert cm.current_price >= c.base_price * PRICE_MIN_MULT - 0.01

    def test_price_cannot_rise_above_base_times_max_mult(self):
        m, ms = _market_and_state(seed=11)
        regs = _regimes("rising")
        for _ in range(100):
            m.on_dawn(ms, regs)
        for c in m.commodities:
            cm = ms.commodities[c.id]
            assert cm.current_price <= c.base_price * PRICE_MAX_MULT + 0.01


class TestOnDawnHistoryWindow:
    def test_price_history_grows_up_to_window(self):
        m, ms = _market_and_state()
        regs = _regimes("stable")
        for _ in range(5):
            m.on_dawn(ms, regs)
        for cm in ms.commodities.values():
            assert len(cm.price_history) == 5

    def test_price_history_caps_at_window(self):
        m, ms = _market_and_state()
        regs = _regimes("stable")
        for _ in range(20):
            m.on_dawn(ms, regs)
        for cm in ms.commodities.values():
            assert len(cm.price_history) == PRICE_HISTORY_WINDOW

    def test_history_last_element_matches_current_price(self):
        m, ms = _market_and_state()
        regs = _regimes("rising")
        for _ in range(3):
            m.on_dawn(ms, regs)
        for cm in ms.commodities.values():
            assert cm.price_history[-1] == cm.current_price


class TestOnDawnTickId:
    def test_tick_id_increments_per_dawn(self):
        m, ms = _market_and_state()
        regs = _regimes()
        assert ms.tick_id == 0
        m.on_dawn(ms, regs)
        assert ms.tick_id == 1
        m.on_dawn(ms, regs)
        assert ms.tick_id == 2


class TestOnDawnWithoutRegimes:
    def test_no_regimes_treated_as_stable(self):
        m, ms = _market_and_state(seed=5)
        start = ms.commodities["sugar"].current_price
        for _ in range(5):
            m.on_dawn(ms, regimes=None)
        end = ms.commodities["sugar"].current_price
        assert 0.95 < end / start < 1.05


class TestOnDawnPerCommodityMagnitude:
    def test_per_dag_change_within_expected_bounds(self):
        m, ms = _market_and_state(seed=23)
        regs = _regimes("rising")
        start = ms.commodities["sugar"].current_price
        m.on_dawn(ms, regs)
        end = ms.commodities["sugar"].current_price
        ratio = end / start
        assert 1.0 - 0.011 < ratio < 1.0 + _daily_magnitude_max() + 0.011


# -----------------------------------------------------------------------------
# compute_trend (uendret siden Fase 2A — opererer på list[float])
# -----------------------------------------------------------------------------

class TestComputeTrendEmptyCases:
    def test_empty_history_returns_empty_string(self):
        assert compute_trend([]) == ""

    def test_one_element_returns_empty_string(self):
        assert compute_trend([100.0]) == ""

    def test_two_elements_returns_empty_string(self):
        assert compute_trend([100.0, 105.0]) == ""


class TestComputeTrendArrows:
    def test_clear_rising_returns_up_arrow(self):
        assert compute_trend([100.0, 102.0, 105.0]) == "\u2191"

    def test_clear_falling_returns_down_arrow(self):
        assert compute_trend([100.0, 98.0, 96.0]) == "\u2193"

    def test_flat_returns_horizontal_arrow(self):
        assert compute_trend([100.0, 100.0, 100.0]) == "\u2192"

    def test_noise_under_threshold_is_flat(self):
        assert compute_trend([100.0, 100.0, 102.0]) == "\u2192"

    def test_small_drop_under_threshold_is_flat(self):
        assert compute_trend([100.0, 100.0, 98.0]) == "\u2192"

    def test_uses_only_last_three(self):
        history = [50.0, 60.0, 70.0, 100.0, 100.0, 100.0]
        assert compute_trend(history) == "\u2192"

    def test_longer_history_still_picks_recent_rising(self):
        history = [100.0, 95.0, 90.0, 85.0, 92.0, 100.0]
        assert compute_trend(history) == "\u2191"


class TestComputeTrendEdgeCases:
    def test_zero_start_returns_flat(self):
        assert compute_trend([0.0, 10.0, 20.0]) == "\u2192"

    def test_exactly_at_threshold_is_flat(self):
        assert compute_trend([100.0, 100.0, 103.0]) == "\u2192"

    def test_just_over_threshold_is_rising(self):
        assert compute_trend([100.0, 100.0, 103.1]) == "\u2191"


# -----------------------------------------------------------------------------
# Commit 5D: bek base_price 40 og clamp_to_price_bounds
# -----------------------------------------------------------------------------

class TestBekBasePrice:
    def test_fresh_market_bek_starts_at_40(self):
        """commodities.json skal ha pitch base_price = 40 (Commit 5D)."""
        import os
        import constants
        m = Market.from_json(
            os.path.join(constants.DATA_DIR, "commodities.json")
        )
        assert m.base_price("pitch") == 40.0

    def test_fresh_market_prices_buy_sell(self):
        """Buy/sell spread = 2%; bek base 40 → buy 41, sell 39."""
        import os
        import constants
        m = Market.from_json(
            os.path.join(constants.DATA_DIR, "commodities.json")
        )
        # Start-state: current_price == base_price for bek = 40.
        ms = MarketState(commodities={
            "pitch": CommodityMarket(current_price=40.0),
        })
        assert m.buy_price(ms, "pitch") == 41
        assert m.sell_price(ms, "pitch") == 39


class TestClampToPriceBounds:
    def test_high_price_clamped_to_max(self):
        m, ms = _market_and_state()
        ms.commodities["sugar"].current_price = 120.0
        m.clamp_to_price_bounds(ms, "sugar")
        assert ms.commodities["sugar"].current_price == 80.0  # base 40 × 2.0

    def test_low_price_clamped_to_min(self):
        m, ms = _market_and_state()
        ms.commodities["sugar"].current_price = 5.0
        m.clamp_to_price_bounds(ms, "sugar")
        assert ms.commodities["sugar"].current_price == 20.0  # base 40 × 0.5

    def test_in_range_price_unchanged(self):
        m, ms = _market_and_state()
        ms.commodities["sugar"].current_price = 45.0
        m.clamp_to_price_bounds(ms, "sugar")
        assert ms.commodities["sugar"].current_price == 45.0

    def test_history_clamped(self):
        m, ms = _market_and_state()
        ms.commodities["sugar"].price_history = [10.0, 120.0, 45.0, 200.0]
        m.clamp_to_price_bounds(ms, "sugar")
        # base 40 → [20, 80]
        assert ms.commodities["sugar"].price_history == [20.0, 80.0, 45.0, 80.0]

    def test_empty_history_stays_empty(self):
        m, ms = _market_and_state()
        ms.commodities["sugar"].price_history = []
        m.clamp_to_price_bounds(ms, "sugar")
        assert ms.commodities["sugar"].price_history == []
