"""Tester for `systems.game_clock.GameClock`."""

from __future__ import annotations

import constants
from systems.game_clock import GameClock


class TestDefaults:
    def test_starts_at_day_1(self):
        clock = GameClock()
        assert clock.day == 1
        assert clock.seconds_into_day == 0.0

    def test_default_seconds_per_day_matches_constants(self):
        clock = GameClock()
        assert clock.seconds_per_day == constants.SECONDS_PER_DAY

    def test_progress_fraction_zero_at_start(self):
        assert GameClock().progress_fraction() == 0.0


class TestUpdateWithinDay:
    def test_no_event_when_dt_small(self):
        clock = GameClock(seconds_per_day=60.0)
        events = clock.update(10.0)
        assert events == []
        assert clock.day == 1
        assert clock.seconds_into_day == 10.0

    def test_progress_fraction_tracks_seconds(self):
        clock = GameClock(seconds_per_day=60.0)
        clock.update(15.0)
        assert clock.progress_fraction() == 0.25
        clock.update(30.0)
        assert clock.progress_fraction() == 0.75

    def test_multiple_small_updates_accumulate(self):
        clock = GameClock(seconds_per_day=60.0)
        for _ in range(10):
            clock.update(1.0)
        assert clock.day == 1
        assert clock.seconds_into_day == 10.0


class TestDayRollover:
    def test_single_rollover_emits_new_day(self):
        clock = GameClock(seconds_per_day=60.0)
        events = clock.update(60.0)
        assert events == ["new_day"]
        assert clock.day == 2
        assert clock.seconds_into_day == 0.0

    def test_rollover_preserves_remainder(self):
        clock = GameClock(seconds_per_day=60.0)
        events = clock.update(72.5)
        assert events == ["new_day"]
        assert clock.day == 2
        assert abs(clock.seconds_into_day - 12.5) < 1e-9

    def test_accumulated_small_updates_cross_boundary(self):
        clock = GameClock(seconds_per_day=60.0)
        # 59.5 s innen dag 1 – ingen hendelse
        events = clock.update(59.5)
        assert events == []
        # 1.0 s mer krysser dagen
        events = clock.update(1.0)
        assert events == ["new_day"]
        assert clock.day == 2
        assert abs(clock.seconds_into_day - 0.5) < 1e-9


class TestMultipleRollovers:
    def test_two_days_in_one_update(self):
        clock = GameClock(seconds_per_day=60.0)
        events = clock.update(120.0)
        assert events == ["new_day", "new_day"]
        assert clock.day == 3
        assert clock.seconds_into_day == 0.0

    def test_three_days_plus_remainder(self):
        clock = GameClock(seconds_per_day=60.0)
        events = clock.update(180.5)
        assert events == ["new_day", "new_day", "new_day"]
        assert clock.day == 4
        assert abs(clock.seconds_into_day - 0.5) < 1e-9

    def test_many_days(self):
        clock = GameClock(seconds_per_day=60.0)
        events = clock.update(60.0 * 10)
        assert len(events) == 10
        assert all(e == "new_day" for e in events)
        assert clock.day == 11


class TestCustomSecondsPerDay:
    def test_short_day_for_fast_test(self):
        clock = GameClock(seconds_per_day=2.0)
        events = clock.update(5.5)
        # 5.5 / 2.0 = 2 full dager + 1.5 s rest
        assert events == ["new_day", "new_day"]
        assert clock.day == 3
        assert abs(clock.seconds_into_day - 1.5) < 1e-9

    def test_zero_seconds_per_day_safe_progress(self):
        # Degenerated config – progress_fraction skal ikke dele på 0
        clock = GameClock(seconds_per_day=0.0)
        assert clock.progress_fraction() == 0.0


class TestStateCarry:
    def test_preexisting_day_preserved_through_update(self):
        clock = GameClock(day=42, seconds_into_day=0.0, seconds_per_day=60.0)
        clock.update(30.0)
        assert clock.day == 42
        assert clock.seconds_into_day == 30.0

    def test_preexisting_seconds_into_day_continues(self):
        clock = GameClock(day=5, seconds_into_day=50.0, seconds_per_day=60.0)
        events = clock.update(15.0)
        assert events == ["new_day"]
        assert clock.day == 6
        assert abs(clock.seconds_into_day - 5.0) < 1e-9

    def test_negative_dt_noop(self):
        # Ikke et realistisk scenario, men vi vil iallfall ikke krasje eller
        # gå bakover i dager. Nåværende implementasjon flytter
        # seconds_into_day negativt uten å ruse til forrige dag.
        clock = GameClock(day=1, seconds_into_day=10.0, seconds_per_day=60.0)
        events = clock.update(-5.0)
        assert events == []
        assert clock.day == 1
        assert clock.seconds_into_day == 5.0
