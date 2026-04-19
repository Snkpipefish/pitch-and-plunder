"""Tester for ObservedPrice-helpers (Fase 2B C8).

Dekker days_since-klamping og is_stale-grense-oppførsel. Selve
serialiseringen er testet via test_save_v5_migration round-trip
(asdict-sammenligning fanger alle felter).
"""

from __future__ import annotations

from state.observed_price import ObservedPrice


class TestDaysSince:
    def test_standard_delta(self):
        obs = ObservedPrice(price=42.0, day_seen=3)
        assert obs.days_since(current_day=10) == 7

    def test_same_day_returns_zero(self):
        obs = ObservedPrice(price=42.0, day_seen=5)
        assert obs.days_since(current_day=5) == 0

    def test_future_day_seen_clamps_to_zero(self):
        """Defensive — kan skje ved korrupt save eller test med
        tilbakestilt klokke. Negativ days_since gir misvisende UI."""
        obs = ObservedPrice(price=42.0, day_seen=10)
        assert obs.days_since(current_day=5) == 0

    def test_large_gap(self):
        obs = ObservedPrice(price=42.0, day_seen=1)
        assert obs.days_since(current_day=365) == 364


class TestIsStale:
    def test_below_threshold_is_fresh(self):
        obs = ObservedPrice(price=42.0, day_seen=1)
        # 1 day passed, threshold=5
        assert obs.is_stale(current_day=2, threshold_days=5) is False

    def test_at_threshold_is_fresh(self):
        """Per spec §8.3: stale = `days_since > threshold` (strikt
        større). Akkurat ved threshold er fortsatt fersk."""
        obs = ObservedPrice(price=42.0, day_seen=1)
        # 5 days passed, threshold=5 → fersk
        assert obs.is_stale(current_day=6, threshold_days=5) is False

    def test_above_threshold_is_stale(self):
        obs = ObservedPrice(price=42.0, day_seen=1)
        # 6 days passed, threshold=5 → stale
        assert obs.is_stale(current_day=7, threshold_days=5) is True

    def test_zero_days_passed_never_stale(self):
        obs = ObservedPrice(price=42.0, day_seen=10)
        assert obs.is_stale(current_day=10, threshold_days=0) is False
