"""Tester for `Market.on_dawn` og `compute_trend` (Fase 2A Commit 5C).

`test_market_buy.py` dekker buy/sell-transaksjoner; her fokuserer vi på
daglig pris-drift og trend-indikator.
"""

from __future__ import annotations

import random

from entities.commodity import (
    PRICE_HISTORY_WINDOW,
    Commodity,
    compute_trend,
)
from systems.economy import (
    DAILY_MAGNITUDE_MAX,
    PRICE_MAX_MULT,
    PRICE_MIN_MULT,
    Market,
)
from systems.regime_manager import RegimeState


def _market(seed: int = 42) -> Market:
    return Market(
        [
            Commodity(
                id="sugar",
                name="Sukker",
                base_price=40.0,
                current_price=40.0,
                volatility=0.15,
            ),
            Commodity(
                id="rum",
                name="Rom",
                base_price=80.0,
                current_price=80.0,
                volatility=0.20,
            ),
        ],
        rng=random.Random(seed),
    )


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
        # Med "rising" regime skal prisen stige målbart over 5 dager.
        # direction=+1, magnitude ∈ [0.02, 0.04], noise ∈ [-0.01, 0.01]
        # → per-dag-endring i [0.01, 0.05]. Over 5 dager minst +5%.
        m = _market()
        regs = _regimes("rising")
        start_sugar = m.get("sugar").current_price
        for _ in range(5):
            m.on_dawn(regs)
        end_sugar = m.get("sugar").current_price
        # Forventet: minst +5% etter 5 dager rising (worst-case noise)
        assert end_sugar > start_sugar * 1.05, (
            f"Rising-regime: pris {start_sugar} → {end_sugar} steg ikke nok"
        )

    def test_falling_accumulates_downward_over_5_days(self):
        m = _market(seed=17)
        regs = _regimes("falling")
        start = m.get("sugar").current_price
        for _ in range(5):
            m.on_dawn(regs)
        end = m.get("sugar").current_price
        assert end < start * 0.95, (
            f"Falling-regime: pris {start} → {end} falt ikke nok"
        )

    def test_stable_stays_within_bounds_over_5_days(self):
        # Stable har direction=0, så kun ±1% noise per dag. Over 5 dager
        # skal totalt avvik være ≤ 5% (rett random walk-bound).
        m = _market(seed=3)
        regs = _regimes("stable")
        start = m.get("sugar").current_price
        for _ in range(5):
            m.on_dawn(regs)
        end = m.get("sugar").current_price
        ratio = end / start
        assert 0.95 < ratio < 1.05, (
            f"Stable-regime: pris {start} → {end} drev for mye ({ratio})"
        )


class TestOnDawnClamp:
    def test_price_cannot_fall_below_base_times_min_mult(self):
        # Tving falling over 100 dager; pris skal klampes mot 0.5 × base.
        m = _market(seed=7)
        regs = _regimes("falling")
        for _ in range(100):
            m.on_dawn(regs)
        for c in m.commodities:
            assert c.current_price >= c.base_price * PRICE_MIN_MULT - 0.01

    def test_price_cannot_rise_above_base_times_max_mult(self):
        # Tving rising over 100 dager; pris skal klampes mot 2.0 × base.
        m = _market(seed=11)
        regs = _regimes("rising")
        for _ in range(100):
            m.on_dawn(regs)
        for c in m.commodities:
            assert c.current_price <= c.base_price * PRICE_MAX_MULT + 0.01


class TestOnDawnHistoryWindow:
    def test_price_history_grows_up_to_window(self):
        m = _market()
        regs = _regimes("stable")
        # Etter 5 dager: history = 5 elementer (< WINDOW=14)
        for _ in range(5):
            m.on_dawn(regs)
        for c in m.commodities:
            assert len(c.price_history) == 5

    def test_price_history_caps_at_window(self):
        m = _market()
        regs = _regimes("stable")
        # Etter 20 dager: history = PRICE_HISTORY_WINDOW=14 (eldste falt ut)
        for _ in range(20):
            m.on_dawn(regs)
        for c in m.commodities:
            assert len(c.price_history) == PRICE_HISTORY_WINDOW

    def test_history_last_element_matches_current_price(self):
        m = _market()
        regs = _regimes("rising")
        for _ in range(3):
            m.on_dawn(regs)
        for c in m.commodities:
            assert c.price_history[-1] == c.current_price


class TestOnDawnTickId:
    def test_tick_id_increments_per_dawn(self):
        m = _market()
        regs = _regimes()
        assert m.tick_id == 0
        m.on_dawn(regs)
        assert m.tick_id == 1
        m.on_dawn(regs)
        assert m.tick_id == 2


class TestOnDawnWithoutRegimes:
    def test_no_regimes_treated_as_stable(self):
        # Ingen regimes → ingen retning, kun ±1% noise per dag
        m = _market(seed=5)
        start = m.get("sugar").current_price
        for _ in range(5):
            m.on_dawn(regimes=None)
        end = m.get("sugar").current_price
        assert 0.95 < end / start < 1.05


class TestOnDawnPerCommodityMagnitude:
    def test_per_dag_change_within_expected_bounds(self):
        # Én dag rising skal aldri gi mer enn (DAILY_MAGNITUDE_MAX + noise_max)
        # = 0.04 + 0.01 = 0.05 pris-endring.
        m = _market(seed=23)
        regs = _regimes("rising")
        start = m.get("sugar").current_price
        m.on_dawn(regs)
        end = m.get("sugar").current_price
        # Pris-ratio skal være innenfor [1 - noise_max, 1 + magnitude_max + noise_max]
        ratio = end / start
        assert 1.0 - 0.011 < ratio < 1.0 + DAILY_MAGNITUDE_MAX + 0.011


# -----------------------------------------------------------------------------
# compute_trend
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
        # 100 → 105 = +5%, over 3% terskel
        assert compute_trend([100.0, 102.0, 105.0]) == "\u2191"

    def test_clear_falling_returns_down_arrow(self):
        assert compute_trend([100.0, 98.0, 96.0]) == "\u2193"

    def test_flat_returns_horizontal_arrow(self):
        assert compute_trend([100.0, 100.0, 100.0]) == "\u2192"

    def test_noise_under_threshold_is_flat(self):
        # +2% endring < 3% terskel → flat
        assert compute_trend([100.0, 100.0, 102.0]) == "\u2192"

    def test_small_drop_under_threshold_is_flat(self):
        # -2% endring < 3% terskel → flat
        assert compute_trend([100.0, 100.0, 98.0]) == "\u2192"

    def test_uses_only_last_three(self):
        # Lang historikk med trend i starten, flatt mot slutten → flat
        history = [50.0, 60.0, 70.0, 100.0, 100.0, 100.0]
        assert compute_trend(history) == "\u2192"

    def test_longer_history_still_picks_recent_rising(self):
        # Fall i starten, stigning i siste 3 → stigende
        history = [100.0, 95.0, 90.0, 85.0, 92.0, 100.0]
        assert compute_trend(history) == "\u2191"


class TestComputeTrendEdgeCases:
    def test_zero_start_returns_flat(self):
        # Defensive: start=0 unngår division by zero
        assert compute_trend([0.0, 10.0, 20.0]) == "\u2192"

    def test_exactly_at_threshold_is_flat(self):
        # Eksakt 3% stigning → ikke over terskel
        assert compute_trend([100.0, 100.0, 103.0]) == "\u2192"

    def test_just_over_threshold_is_rising(self):
        # 3.01% stigning → over terskel
        assert compute_trend([100.0, 100.0, 103.1]) == "\u2191"


# -----------------------------------------------------------------------------
# Commit 5D: bek base_price 40 og clamp_to_price_bounds
# -----------------------------------------------------------------------------

class TestBekBasePrice:
    def test_fresh_market_bek_starts_at_40(self):
        # commodities.json skal ha pitch base_price = 40 (Commit 5D).
        import os
        import constants
        m = Market.from_json(
            os.path.join(constants.DATA_DIR, "commodities.json")
        )
        bek = m.get("pitch")
        assert bek.base_price == 40.0
        assert bek.current_price == 40.0

    def test_fresh_market_prices_buy_sell(self):
        # Buy/sell spread = 2%; bek base 40 → buy 41 (40*1.02=40.8 → 41),
        # sell 39 (40*0.98=39.2 → 39).
        import os
        import constants
        m = Market.from_json(
            os.path.join(constants.DATA_DIR, "commodities.json")
        )
        assert m.buy_price("pitch") == 41
        assert m.sell_price("pitch") == 39


class TestClampToPriceBounds:
    def test_high_price_clamped_to_max(self):
        # Simuler en loaded save med bek-pris 120 (fra Fase 1 base=55 × 2.18).
        # Ny clamp: base=40, max=80 → skal klampes til 80.
        m = _market()
        m.get("sugar").current_price = 120.0
        m.clamp_to_price_bounds("sugar")
        assert m.get("sugar").current_price == 80.0  # base 40 × 2.0

    def test_low_price_clamped_to_min(self):
        m = _market()
        m.get("sugar").current_price = 5.0
        m.clamp_to_price_bounds("sugar")
        assert m.get("sugar").current_price == 20.0  # base 40 × 0.5

    def test_in_range_price_unchanged(self):
        m = _market()
        m.get("sugar").current_price = 45.0
        m.clamp_to_price_bounds("sugar")
        assert m.get("sugar").current_price == 45.0

    def test_history_clamped(self):
        m = _market()
        m.get("sugar").price_history = [10.0, 120.0, 45.0, 200.0]
        m.clamp_to_price_bounds("sugar")
        # base 40 → [20, 80]
        assert m.get("sugar").price_history == [20.0, 80.0, 45.0, 80.0]

    def test_empty_history_stays_empty(self):
        m = _market()
        m.get("sugar").price_history = []
        m.clamp_to_price_bounds("sugar")
        assert m.get("sugar").price_history == []
