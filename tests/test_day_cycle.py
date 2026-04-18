"""Tester for `systems.day_cycle`. Alle tester bruker eksplisitt
`seconds_per_day=180.0` slik at dag-fraksjonene tilsvarer brukt spec
(0.00 midnatt, 0.17 daggry, 0.50 middag, 0.83 solnedgang).
"""

from __future__ import annotations

import constants
from systems.day_cycle import (
    DAY_END,
    MOON_FADE_IN_END,
    MOON_FADE_IN_START,
    MOON_FADE_OUT_END,
    MOON_FADE_OUT_START,
    MOON_X,
    MOON_Y,
    MORNING_END,
    SUN_COLOR_DUSK_START,
    SUN_COLOR_WARM_END,
    SUN_FADE_OUT_END,
    SUN_FADE_OUT_START,
    SUN_VISIBLE_START,
    SUN_X_DAWN,
    SUN_X_DUSK,
    DayCycle,
)
from systems.game_clock import GameClock

# Vi tester med seconds_per_day = 180 slik at 1 sekund = 1/180 av dagen.
# Da blir anker-fraksjoner lett å regne om til sekunder.
_SECONDS_PER_DAY = 180.0


def _clock_at_fraction(frac: float, seconds_per_day: float = _SECONDS_PER_DAY) -> GameClock:
    return GameClock(
        day=1,
        seconds_into_day=frac * seconds_per_day,
        seconds_per_day=seconds_per_day,
    )


def _clock_at(t: float, seconds_per_day: float = _SECONDS_PER_DAY) -> GameClock:
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
        snap = DayCycle.compute_snapshot(_clock_at(99.0, seconds_per_day=600.0))
        assert snap.phase == "morning"
        snap = DayCycle.compute_snapshot(_clock_at(100.0, seconds_per_day=600.0))
        assert snap.phase == "day"

    def test_degenerated_clock_safe(self):
        clock = GameClock(day=1, seconds_into_day=0.0, seconds_per_day=0.0)
        snap = DayCycle.compute_snapshot(clock)
        assert snap.phase == "morning"


class TestSkyBrightnessMonotonic:
    """Sanitetssjekk: sky_top skal monotont lysne fra midnatt til middag."""

    def test_morning_sky_monotonically_brightens(self):
        # Perseptuell lyshet (Y-component) skal være monotont stigende
        fractions = [0.00, 0.05, 0.10, 0.15]
        ys = []
        for frac in fractions:
            snap = DayCycle.compute_snapshot(_clock_at_fraction(frac))
            r, g, b = snap.sky_top_color
            ys.append(0.299 * r + 0.587 * g + 0.114 * b)
        for i in range(1, len(ys)):
            assert ys[i] > ys[i - 1] - 1e-6, (
                f"Morgen-sky mørknet: fractions={fractions}, Y={ys}"
            )

    def test_sky_starts_at_night_palette(self):
        snap = DayCycle.compute_snapshot(_clock_at(0.0))
        assert snap.sky_top_color == constants.COLOR_SKY_DEEP

    def test_sky_day_first_half_stays_day_palette(self):
        snap = DayCycle.compute_snapshot(_clock_at(45.0))
        assert snap.sky_top_color == constants.COLOR_SKY_DAY_TOP

    def test_sky_day_second_half_glides_toward_dusk(self):
        snap_mid = DayCycle.compute_snapshot(_clock_at(120.0))
        assert snap_mid.sky_top_color != constants.COLOR_SKY_DAY_TOP
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
        snap = DayCycle.compute_snapshot(_clock_at(15.0))
        assert abs(snap.star_alpha - 0.5) < 0.01

    def test_day_has_no_stars(self):
        snap = DayCycle.compute_snapshot(_clock_at(90.0))
        assert snap.star_alpha == 0.0

    def test_night_fades_stars_in(self):
        snap_early = DayCycle.compute_snapshot(_clock_at(150.0))
        assert snap_early.star_alpha < 1e-6
        snap_mid = DayCycle.compute_snapshot(_clock_at(157.5))
        assert 0.4 < snap_mid.star_alpha < 0.6
        snap_late = DayCycle.compute_snapshot(_clock_at(170.0))
        assert snap_late.star_alpha == 1.0


class TestCelestialWindows:
    """Celestial er bestemt av global day_fraction og deler dagen i:
    moon windows, sun window, og gap windows.
    """

    def test_midnight_shows_moon(self):
        # fraction 0.00 – måne skal være oppe på full styrke
        snap = DayCycle.compute_snapshot(_clock_at_fraction(0.00))
        assert snap.celestial_is_sun is False
        assert snap.celestial_alpha == 1.0
        assert snap.celestial_color == constants.COLOR_MOON_CORE

    def test_early_dawn_shows_moon(self):
        # fraction 0.05 – før moon fade-out start (0.08)
        snap = DayCycle.compute_snapshot(_clock_at_fraction(0.05))
        assert snap.celestial_is_sun is False
        assert snap.celestial_alpha == 1.0

    def test_moon_fades_out_after_008(self):
        # fraction 0.10 – halvveis gjennom fade-out (0.08 → 0.12)
        snap = DayCycle.compute_snapshot(_clock_at_fraction(0.10))
        assert snap.celestial_is_sun is False
        assert 0.4 < snap.celestial_alpha < 0.6

    def test_gap_before_sunrise_has_no_celestial(self):
        # fraction 0.14 – gap mellom måne-set og sol-opp
        snap = DayCycle.compute_snapshot(_clock_at_fraction(0.14))
        assert snap.celestial_alpha == 0.0

    def test_sunrise_start_shows_sun_at_full_alpha(self):
        # fraction 0.17 – sol akkurat kommet opp
        snap = DayCycle.compute_snapshot(_clock_at_fraction(0.17))
        assert snap.celestial_is_sun is True
        assert snap.celestial_alpha == 1.0

    def test_midday_shows_sun(self):
        snap = DayCycle.compute_snapshot(_clock_at_fraction(0.50))
        assert snap.celestial_is_sun is True
        assert snap.celestial_alpha == 1.0

    def test_sun_fading_out_at_085(self):
        # fraction 0.85 – halvveis gjennom sol-fade (0.83 → 0.88)
        snap = DayCycle.compute_snapshot(_clock_at_fraction(0.85))
        assert snap.celestial_is_sun is True
        assert 0.35 < snap.celestial_alpha < 0.65

    def test_sun_fully_gone_at_fade_end(self):
        # Like før 0.88: sol-alpha nær 0
        snap = DayCycle.compute_snapshot(_clock_at_fraction(0.879))
        assert snap.celestial_alpha < 0.05

    def test_moon_fades_in_at_090(self):
        # fraction 0.90 – halvveis gjennom fade-in (0.88 → 0.92)
        snap = DayCycle.compute_snapshot(_clock_at_fraction(0.90))
        assert snap.celestial_is_sun is False
        assert 0.4 < snap.celestial_alpha < 0.6

    def test_late_night_moon_full(self):
        # fraction 0.95 – måne på full styrke, godt inn i natten
        snap = DayCycle.compute_snapshot(_clock_at_fraction(0.95))
        assert snap.celestial_is_sun is False
        assert snap.celestial_alpha == 1.0


class TestCelestialMotion:
    def test_sun_travels_right_to_left(self):
        snap_start = DayCycle.compute_snapshot(_clock_at_fraction(0.17))
        snap_noon = DayCycle.compute_snapshot(_clock_at_fraction(0.50))
        snap_end = DayCycle.compute_snapshot(_clock_at_fraction(0.82))
        assert snap_start.celestial_x > snap_noon.celestial_x > snap_end.celestial_x
        # Parabolsk y: noon høyest
        assert snap_noon.celestial_y > snap_start.celestial_y
        assert snap_noon.celestial_y > snap_end.celestial_y

    def test_sun_starts_at_right_edge(self):
        snap = DayCycle.compute_snapshot(_clock_at_fraction(0.17))
        assert snap.celestial_x == SUN_X_DAWN

    def test_sun_ends_near_left_edge_at_fade_start(self):
        # Ved SUN_FADE_OUT_START (0.83) er solen på sin laveste posisjon
        # før den fader ut.
        snap = DayCycle.compute_snapshot(_clock_at_fraction(0.82))
        assert snap.celestial_x < 0.2

    def test_sun_position_frozen_during_fade(self):
        # Under fade-out holdes posisjonen slik at solen ikke driver
        # videre mens den fader.
        snap_at_fade_start = DayCycle.compute_snapshot(_clock_at_fraction(0.83))
        snap_mid_fade = DayCycle.compute_snapshot(_clock_at_fraction(0.855))
        assert snap_at_fade_start.celestial_x == snap_mid_fade.celestial_x
        assert snap_at_fade_start.celestial_y == snap_mid_fade.celestial_y

    def test_moon_position_is_static(self):
        snap_midnight = DayCycle.compute_snapshot(_clock_at_fraction(0.00))
        snap_late = DayCycle.compute_snapshot(_clock_at_fraction(0.95))
        assert snap_midnight.celestial_x == MOON_X
        assert snap_late.celestial_x == MOON_X
        assert snap_midnight.celestial_y == MOON_Y


class TestSunColorThreeStage:
    """Sol-farge holdes hvit midt på dagen og interpolerer varm/dusk
    kun ved start/slutt av sol-vinduet.
    """

    def test_sunrise_starts_warm(self):
        snap = DayCycle.compute_snapshot(_clock_at_fraction(0.17))
        assert snap.celestial_color == constants.COLOR_SUN_DAWN

    def test_warm_period_ends_at_025(self):
        # Like før fraction 0.25 skal vi nesten være på SUN_DAY
        snap = DayCycle.compute_snapshot(_clock_at_fraction(0.249))
        for i in range(3):
            assert (
                abs(snap.celestial_color[i] - constants.COLOR_SUN_DAY[i]) < 5
            )

    def test_midday_is_white_at_030(self):
        # Fraction 0.30 skal være innenfor SUN_DAY-hold-vinduet
        snap = DayCycle.compute_snapshot(_clock_at_fraction(0.30))
        assert snap.celestial_color == constants.COLOR_SUN_DAY

    def test_midday_is_white_at_050(self):
        snap = DayCycle.compute_snapshot(_clock_at_fraction(0.50))
        assert snap.celestial_color == constants.COLOR_SUN_DAY

    def test_midday_is_white_at_064(self):
        # Like før dusk-overgang (0.65)
        snap = DayCycle.compute_snapshot(_clock_at_fraction(0.64))
        assert snap.celestial_color == constants.COLOR_SUN_DAY

    def test_dusk_period_starts_at_065(self):
        # Eksakt på 0.65 er vi ved start av dusk-interpolering
        snap = DayCycle.compute_snapshot(_clock_at_fraction(0.65))
        # Skal være identisk med SUN_DAY (k=0 i interpolering)
        assert snap.celestial_color == constants.COLOR_SUN_DAY

    def test_sunset_approaches_dusk_color(self):
        snap = DayCycle.compute_snapshot(_clock_at_fraction(0.82))
        # Nær SUN_DUSK. Flerkanals-avvik kan være opptil ~12 pga int-lerp.
        for i in range(3):
            assert (
                abs(snap.celestial_color[i] - constants.COLOR_SUN_DUSK[i]) <= 12
            )

    def test_fade_start_color_matches_sun_at_083(self):
        # Under fade-out (fra 0.83) skal solfargen være festet til fargen
        # ved 0.83 (ikke drift videre via _sun_state).
        snap_0_83 = DayCycle.compute_snapshot(_clock_at_fraction(0.83))
        snap_mid_fade = DayCycle.compute_snapshot(_clock_at_fraction(0.855))
        assert snap_0_83.celestial_color == snap_mid_fade.celestial_color


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

    def test_celestial_window_constants_match_spec(self):
        assert MOON_FADE_OUT_START == 0.08
        assert MOON_FADE_OUT_END == 0.12
        assert SUN_VISIBLE_START == 0.17
        assert SUN_FADE_OUT_START == 0.83
        assert SUN_FADE_OUT_END == 0.88
        assert MOON_FADE_IN_START == 0.88
        assert MOON_FADE_IN_END == 0.92

    def test_sun_color_stage_constants_match_spec(self):
        assert SUN_COLOR_WARM_END == 0.25
        assert SUN_COLOR_DUSK_START == 0.65


class TestDayFraction:
    def test_day_fraction_matches_clock_progress(self):
        snap = DayCycle.compute_snapshot(_clock_at_fraction(0.37))
        assert abs(snap.day_fraction - 0.37) < 1e-9

    def test_day_fraction_at_zero(self):
        snap = DayCycle.compute_snapshot(_clock_at(0.0))
        assert snap.day_fraction == 0.0
