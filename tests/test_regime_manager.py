"""Tester for RegimeManager – Markov-overganger og dagsklokke."""

from __future__ import annotations

import random

import pytest

from systems.regime_manager import (
    MAX_REGIME_DAYS,
    MIN_REGIME_DAYS,
    REGIMES,
    HISTORY_WINDOW,
    RegimeManager,
    RegimeState,
)


def _seeded_manager(seed: int = 42) -> RegimeManager:
    return RegimeManager(rng=random.Random(seed))


class TestInitialization:
    def test_initialize_sets_stable_for_all(self):
        mgr = _seeded_manager()
        regimes = mgr.initialize_regimes(["sugar", "rum"])
        assert regimes["sugar"].current == "stable"
        assert regimes["rum"].current == "stable"

    def test_initialize_sets_days_in_valid_range(self):
        mgr = _seeded_manager()
        regimes = mgr.initialize_regimes(["sugar", "rum"])
        for state in regimes.values():
            assert MIN_REGIME_DAYS <= state.days_remaining <= MAX_REGIME_DAYS

    def test_initialize_empty_history(self):
        mgr = _seeded_manager()
        regimes = mgr.initialize_regimes(["sugar"])
        assert regimes["sugar"].history == []


class TestDayDecrement:
    def test_days_remaining_decreases(self):
        mgr = _seeded_manager()
        regimes = {"sugar": RegimeState(current="stable", days_remaining=5)}
        mgr.on_new_day(regimes)
        assert regimes["sugar"].days_remaining == 4

    def test_no_change_until_expiry(self):
        mgr = _seeded_manager()
        regimes = {"sugar": RegimeState(current="rising", days_remaining=3)}
        changed = mgr.on_new_day(regimes)
        assert changed == []
        assert regimes["sugar"].current == "rising"
        assert regimes["sugar"].days_remaining == 2

    def test_change_on_expiry(self):
        mgr = _seeded_manager()
        regimes = {"sugar": RegimeState(current="stable", days_remaining=1)}
        changed = mgr.on_new_day(regimes)
        assert changed == ["sugar"]
        assert regimes["sugar"].current in REGIMES
        # Nytt regime faar ny levetid innen gyldig omraade
        assert MIN_REGIME_DAYS <= regimes["sugar"].days_remaining <= MAX_REGIME_DAYS

    def test_history_recieves_old_regime(self):
        mgr = _seeded_manager()
        regimes = {"sugar": RegimeState(current="rising", days_remaining=1)}
        mgr.on_new_day(regimes)
        assert regimes["sugar"].history == ["rising"]


class TestMultipleCommodities:
    def test_independent_clocks(self):
        mgr = _seeded_manager()
        regimes = {
            "sugar": RegimeState(current="stable", days_remaining=1),
            "rum": RegimeState(current="rising", days_remaining=5),
        }
        changed = mgr.on_new_day(regimes)
        assert "sugar" in changed
        assert "rum" not in changed
        assert regimes["rum"].days_remaining == 4


class TestMarkovTransitions:
    def test_three_in_a_row_blocked(self):
        """Hvis siste to regimer i historien er like, kan ikke det velges igjen."""
        mgr = _seeded_manager(seed=1)
        # Tving en situasjon der history er [rising, rising] og regimet
        # er utloept. Neste skal ikke kunne bli "rising".
        regimes = {
            "sugar": RegimeState(
                current="rising",
                days_remaining=1,
                history=["rising", "rising"],
            )
        }
        # Kjør mange ganger med ulike seeds for å være trygg
        for seed in range(50):
            mgr = _seeded_manager(seed=seed)
            r = {
                "sugar": RegimeState(
                    current="rising",
                    days_remaining=1,
                    history=["rising", "rising"],
                )
            }
            mgr.on_new_day(r)
            assert r["sugar"].current != "rising", (
                f"Seed {seed}: tre-paa-rad av 'rising' ble tillatt"
            )

    def test_pick_next_regime_returns_valid(self):
        mgr = _seeded_manager()
        for seed in range(20):
            mgr = _seeded_manager(seed=seed)
            chosen = mgr._pick_next_regime(history=[])
            assert chosen in REGIMES

    def test_stable_bias_after_volatile(self):
        """Etter et volatilt regime er stable ~2x saa sannsynlig.

        Over mange kjoeringer skal stable dominere blant de som velges.
        Vi fordrer ikke eksakt 2x (smaa tall-effekter + 1/3-base-vekt),
        men at stable er klart mer enn 1/3 (jevn fordeling).
        """
        counts = {r: 0 for r in REGIMES}
        for seed in range(1000):
            mgr = _seeded_manager(seed=seed)
            chosen = mgr._pick_next_regime(history=["rising"])
            counts[chosen] += 1
        total = sum(counts.values())
        stable_ratio = counts["stable"] / total
        # Jevn fordeling = 1/3 = 0.333. Med stable=2x vekt blir det 2/4=0.5.
        # Tillater noe slakk; men det skal klart vaere mer enn 0.4.
        assert stable_ratio > 0.40, (
            f"Stable-ratio etter volatilt regime var {stable_ratio:.3f}; "
            f"forventet > 0.40. Fordeling: {counts}"
        )


class TestHistoryWindow:
    def test_history_truncates_to_window(self):
        mgr = _seeded_manager()
        regimes = {
            "sugar": RegimeState(
                current="stable",
                days_remaining=1,
                history=["stable"] * HISTORY_WINDOW,
            )
        }
        mgr.on_new_day(regimes)
        assert len(regimes["sugar"].history) == HISTORY_WINDOW
        # Eldste skal ha falt ut
        assert regimes["sugar"].history[-1] == "stable"


class TestEmptyRegimesNoop:
    def test_empty_regimes_returns_empty_changed(self):
        mgr = _seeded_manager()
        changed = mgr.on_new_day({})
        assert changed == []


# -----------------------------------------------------------------------------
# sample_regimes_from_weights (Fase 2B C2)
# -----------------------------------------------------------------------------

class TestSampleRegimesFromWeights:
    def _port_royal(self):
        from config import port_config
        return port_config.get("port_royal")

    def test_samples_all_four_commodities(self):
        from systems.regime_manager import sample_regimes_from_weights
        result = sample_regimes_from_weights(
            self._port_royal(), rng=random.Random(1)
        )
        assert set(result.keys()) == {"sugar", "rum", "tobacco", "pitch"}

    def test_sampled_regimes_are_valid(self):
        from systems.regime_manager import sample_regimes_from_weights
        result = sample_regimes_from_weights(
            self._port_royal(), rng=random.Random(2)
        )
        for cid, regime in result.items():
            assert regime.current in ("rising", "stable", "falling")
            assert 3 <= regime.days_remaining <= 5
            assert regime.history == []

    def test_deterministic_given_seed(self):
        from systems.regime_manager import sample_regimes_from_weights
        port = self._port_royal()
        a = sample_regimes_from_weights(port, rng=random.Random(42))
        b = sample_regimes_from_weights(port, rng=random.Random(42))
        for cid in a:
            assert a[cid].current == b[cid].current
            assert a[cid].days_remaining == b[cid].days_remaining

    def test_different_seeds_yield_different_samples(self):
        """Pragmatisk avhengighetstest: to ulike seeds gir ikke identiske
        samplinger over alle 4 varer."""
        from systems.regime_manager import sample_regimes_from_weights
        port = self._port_royal()
        a = sample_regimes_from_weights(port, rng=random.Random(1))
        b = sample_regimes_from_weights(port, rng=random.Random(999))
        identical = all(
            a[cid].current == b[cid].current
            and a[cid].days_remaining == b[cid].days_remaining
            for cid in a
        )
        assert not identical

    def test_respects_weights_distribution(self):
        """Nassau.pitch har {rising: 0.20, stable: 0.40, falling: 0.40}.
        Over 1000 samplinger skal rising være merkbart mindre enn begge
        de andre.
        """
        from config import port_config
        from systems.regime_manager import sample_regimes_from_weights
        nassau = port_config.get("nassau")
        counts = {"rising": 0, "stable": 0, "falling": 0}
        rng = random.Random(12345)
        for _ in range(1000):
            result = sample_regimes_from_weights(nassau, rng=rng)
            counts[result["pitch"].current] += 1
        # Forventet: rising ~200, stable ~400, falling ~400. Stor margin:
        assert counts["rising"] < 300
        assert counts["stable"] > 300
        assert counts["falling"] > 300


class TestPerPortIsolation:
    def test_on_new_day_one_port_does_not_affect_another(self):
        from systems.regime_manager import RegimeManager
        mgr = RegimeManager(rng=random.Random(0))
        tortuga_regimes = {
            "sugar": RegimeState(current="rising", days_remaining=1, history=[]),
        }
        port_royal_regimes = {
            "sugar": RegimeState(current="stable", days_remaining=5, history=[]),
        }
        mgr.on_new_day(tortuga_regimes)
        assert port_royal_regimes["sugar"].current == "stable"
        assert port_royal_regimes["sugar"].days_remaining == 5

    def test_sampled_regimes_distinct_instances(self):
        from config import port_config
        from systems.regime_manager import sample_regimes_from_weights
        a = sample_regimes_from_weights(
            port_config.get("port_royal"), rng=random.Random(7)
        )
        b = sample_regimes_from_weights(
            port_config.get("havana"), rng=random.Random(7)
        )
        a["sugar"].current = "__mutated__"
        assert b["sugar"].current != "__mutated__"
