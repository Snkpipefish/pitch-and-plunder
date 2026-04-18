"""Tester for `systems.day_cycle`. Alle tester bruker eksplisitt
`seconds_per_day` slik at de ikke kobles mot `constants.SECONDS_PER_DAY`.
"""

from __future__ import annotations

import constants
from systems.day_cycle import (
    DAY_END,
    MOON_X,
    MORNING_END,
    SUN_X_DAWN,
    SUN_X_DUSK,
    DayCycle,
    DaySnapshot,
)
from systems.game_clock import GameClock


def _clock_at(t: float, seconds_per_day: float = 180.0) -> GameClock:
    return GameClock(day=1, seconds_into_day=t, seconds_per_day=seconds_per_day)


class TestPhaseBoundaries:
    def test_t_zero_is_morning(self):
        snap = DayCycle.compute_snapshot(_clock_at(0.0))
        assert snap.phase == "morning"

    def test_t_mid_morning_is_morning(self):
        # t = 15 s av 180 = 1/12, klart i morning (som slutter 1/6)
        snap = DayCycle.compute_snapshot(_clock_at(15.0))
        assert snap.phase == "morning"

    def test_morning_end_transitions_to_day(self):
        snap = DayCycle.compute_snapshot(_clock_at(30.0))
        assert snap.phase == "day"

    def test_mid_day_is_day(self):
        snap = DayCycle.compute_snapshot(_clock_at(90.0))
        assert snap.phase == "day"

    def test_day_end_transitions_to_night(self):
        snap = DayCycle.compute_snapshot(_clock_at(150.0))
        assert snap.phase == "night"

    def test_late_night_still_night(self):
        snap = DayCycle.compute_snapshot(_clock_at(179.9))
        assert snap.phase == "night"


class TestProportionalPhaseLengths:
    def test_short_day_keeps_same_structure(self):
        # Med seconds_per_day=60, morning slutter ved t=10 (1/6 av 60)
        snap = DayCycle.compute_snapshot(_clock_at(9.0, seconds_per_day=60.0))
        assert snap.phase == "morning"
        snap = DayCycle.compute_snapshot(_clock_at(10.0, seconds_per_day=60.0))
        assert snap.phase == "day"
        snap = DayCycle.compute_snapshot(_clock_at(50.0, seconds_per_day=60.0))
        assert snap.phase == "night"

    def test_long_day_keeps_same_structure(self):
        # Med seconds_per_day=600, morning slutter ved t=100
        snap = DayCycle.compute_snapshot(_clock_at(99.0, seconds_per_day=600.0))
        assert snap.phase == "morning"
        snap = DayCycle.compute_snapshot(_clock_at(100.0, seconds_per_day=600.0))
        assert snap.phase == "day"

    def test_degenerated_clock_safe(self):
        # seconds_per_day = 0 gir progress_fraction = 0 → morning
        clock = GameClock(day=1, seconds_into_day=0.0, seconds_per_day=0.0)
        snap = DayCycle.compute_snapshot(clock)
        assert snap.phase == "morning"


class TestSkyColorInterpolation:
    def test_sky_starts_at_night_palette(self):
        snap = DayCycle.compute_snapshot(_clock_at(0.0))
        assert snap.sky_top_color == constants.COLOR_SKY_DEEP
        assert snap.sky_horizon_color == constants.COLOR_SKY_HORIZON

    def test_sky_glides_through_morning(self):
        # Ved slutten av morgen skal himmelen være omtrent dag-palett
        snap_end = DayCycle.compute_snapshot(_clock_at(29.9))
        # Nær dag-palett, men ikke eksakt (floating point lerp)
        assert abs(snap_end.sky_top_color[0] - constants.COLOR_SKY_DAY_TOP[0]) < 3
        assert abs(snap_end.sky_top_color[1] - constants.COLOR_SKY_DAY_TOP[1]) < 3

    def test_sky_day_first_half_stays_day_palette(self):
        # Første halvdel av dag: holdes i dag-palett (ingen glidning ennå)
        snap = DayCycle.compute_snapshot(_clock_at(45.0))  # tidlig i dag
        assert snap.sky_top_color == constants.COLOR_SKY_DAY_TOP

    def test_sky_day_second_half_glides_toward_dusk(self):
        # Midt i dag-fase andre halvdel: himmel skal være på vei mot skumring
        snap_mid = DayCycle.compute_snapshot(_clock_at(120.0))  # 3/4 inn i dag
        assert snap_mid.sky_top_color != constants.COLOR_SKY_DAY_TOP
        # Skal ligge mellom dag og dusk
        top = snap_mid.sky_top_color
        assert (
            min(constants.COLOR_SKY_DAY_TOP[0], constants.COLOR_SKY_DUSK_TOP[0])
            <= top[0]
            <= max(constants.COLOR_SKY_DAY_TOP[0], constants.COLOR_SKY_DUSK_TOP[0])
        )

    def test_night_late_is_full_dark(self):
        snap = DayCycle.compute_snapshot(_clock_at(170.0))
        assert snap.sky_top_color == constants.COLOR_SKY_DEEP


class TestStarAlpha:
    def test_morning_start_stars_full(self):
        snap = DayCycle.compute_snapshot(_clock_at(0.0))
        assert snap.star_alpha == 1.0

    def test_morning_mid_stars_halved(self):
        snap = DayCycle.compute_snapshot(_clock_at(15.0))  # halvveis i morgen
        assert abs(snap.star_alpha - 0.5) < 0.01

    def test_day_has_no_stars(self):
        snap = DayCycle.compute_snapshot(_clock_at(90.0))
        assert snap.star_alpha == 0.0

    def test_night_fades_stars_in(self):
        # Ved t=150.0 eksakt er vi pa fase-grensen; floating-point kan gi
        # en minimal verdi istedenfor 0.0.
        snap_early = DayCycle.compute_snapshot(_clock_at(150.0))
        assert snap_early.star_alpha < 1e-6
        snap_mid = DayCycle.compute_snapshot(_clock_at(157.5))  # halvveis i første halvdel
        assert 0.4 < snap_mid.star_alpha < 0.6
        snap_late = DayCycle.compute_snapshot(_clock_at(170.0))
        assert snap_late.star_alpha == 1.0


class TestCelestialMotion:
    def test_morning_sun_rises_from_right(self):
        snap_start = DayCycle.compute_snapshot(_clock_at(0.0))
        snap_end = DayCycle.compute_snapshot(_clock_at(29.9))
        # Sol stiger: x går fra 0.9 nedover, y går fra 0.15 oppover
        assert snap_start.celestial_x == SUN_X_DAWN
        assert snap_start.celestial_y < snap_end.celestial_y
        assert snap_end.celestial_x < snap_start.celestial_x

    def test_sun_travels_across_sky_through_day(self):
        snap_morning_end = DayCycle.compute_snapshot(_clock_at(30.0))
        snap_noon = DayCycle.compute_snapshot(_clock_at(90.0))
        snap_evening = DayCycle.compute_snapshot(_clock_at(149.9))
        # x går fra høyre (~0.8) mot venstre (~0.2)
        assert snap_morning_end.celestial_x > snap_noon.celestial_x
        assert snap_noon.celestial_x > snap_evening.celestial_x
        # y har maks ved middag (parabel)
        assert snap_noon.celestial_y > snap_morning_end.celestial_y
        assert snap_noon.celestial_y > snap_evening.celestial_y

    def test_night_shows_moon_not_sun(self):
        snap = DayCycle.compute_snapshot(_clock_at(165.0))
        assert snap.celestial_is_sun is False
        assert snap.celestial_color == constants.COLOR_MOON_CORE
        assert snap.celestial_x == MOON_X

    def test_morning_shows_sun_not_moon(self):
        snap = DayCycle.compute_snapshot(_clock_at(10.0))
        assert snap.celestial_is_sun is True

    def test_day_shows_sun(self):
        snap = DayCycle.compute_snapshot(_clock_at(90.0))
        assert snap.celestial_is_sun is True


class TestCelestialColor:
    def test_dawn_warm(self):
        snap = DayCycle.compute_snapshot(_clock_at(0.0))
        assert snap.celestial_color == constants.COLOR_SUN_DAWN

    def test_noon_white(self):
        # Middag-slutten-av-dag-fasen holder COLOR_SUN_DAY nær senter
        snap = DayCycle.compute_snapshot(_clock_at(30.0))
        # Her starter day-fasen, sol-farge er COLOR_SUN_DAY
        assert snap.celestial_color == constants.COLOR_SUN_DAY

    def test_dusk_burns(self):
        snap = DayCycle.compute_snapshot(_clock_at(149.9))
        # Helt mot slutten av dag-fase, farge skal være nær COLOR_SUN_DUSK
        assert abs(snap.celestial_color[0] - constants.COLOR_SUN_DUSK[0]) < 3

    def test_moon_is_moon_core(self):
        snap = DayCycle.compute_snapshot(_clock_at(170.0))
        assert snap.celestial_color == constants.COLOR_MOON_CORE


class TestSnapshotImmutable:
    def test_snapshot_is_frozen(self):
        snap = DayCycle.compute_snapshot(_clock_at(0.0))
        import pytest
        with pytest.raises(Exception):
            snap.phase = "day"  # type: ignore[misc]


class TestFractionConstants:
    def test_morning_end_is_one_sixth(self):
        assert abs(MORNING_END - 1.0 / 6.0) < 1e-9

    def test_day_end_is_five_sixths(self):
        assert abs(DAY_END - 5.0 / 6.0) < 1e-9
