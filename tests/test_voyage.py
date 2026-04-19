"""Tester for `systems.voyage`-helpers (Fase 2B C7b).

Dekker:
- route_key (alfabetisk konvensjon)
- get_route (oppslag + missing)
- compute_heading (4 retninger + diagonal-tie + same-pos)
- compute_progress (start, midt, slutt, overskridelse, same-day defensiv)
- interpolate_position (start, midt, slutt)
- start_voyage (suksess: VoyageState, clock, observed-snapshot, gull uendret)
- start_voyage (None ved ukjent rute, None ved allerede aktiv voyage)
- complete_voyage (suksess + no-op ved ingen voyage)
"""

from __future__ import annotations

from state.voyage_state import VoyageState
from systems import balance, save as save_module, voyage
from systems.game_clock import GameClock


# -----------------------------------------------------------------------------
# route_key + get_route
# -----------------------------------------------------------------------------


class TestRouteKey:
    def test_alphabetical_order_consistent(self):
        assert voyage.route_key("tortuga", "havana") == "havana-tortuga"
        assert voyage.route_key("havana", "tortuga") == "havana-tortuga"

    def test_lexicographic_with_underscores(self):
        # "port_royal" < "tortuga" leksikografisk
        assert voyage.route_key("port_royal", "tortuga") == "port_royal-tortuga"
        assert voyage.route_key("tortuga", "port_royal") == "port_royal-tortuga"

    def test_get_route_resolves_from_balance(self):
        bal = balance.get()
        route = voyage.get_route(bal, "tortuga", "port_royal")
        assert route is not None
        assert route.days == 2
        assert route.gold == 10  # gull-felt finnes men brukes ikke i C7

    def test_get_route_returns_none_for_unknown(self):
        bal = balance.get()
        assert voyage.get_route(bal, "atlantis", "tortuga") is None
        assert voyage.get_route(bal, "tortuga", "tortuga") is None


# -----------------------------------------------------------------------------
# compute_heading
# -----------------------------------------------------------------------------


class TestComputeHeading:
    def test_north_when_target_above(self):
        # Pygame y-akse: nedover positivt → over = lavere y
        assert voyage.compute_heading((100, 200), (100, 50)) == "N"

    def test_south_when_target_below(self):
        assert voyage.compute_heading((100, 50), (100, 200)) == "S"

    def test_east_when_target_right(self):
        assert voyage.compute_heading((100, 100), (300, 100)) == "E"

    def test_west_when_target_left(self):
        assert voyage.compute_heading((300, 100), (100, 100)) == "V"

    def test_diagonal_tie_picks_horizontal(self):
        # |dx|=|dy|=100, horisontal vinner per konvensjon
        assert voyage.compute_heading((0, 0), (100, 100)) == "E"
        assert voyage.compute_heading((100, 100), (0, 0)) == "V"

    def test_dominant_axis_picked(self):
        # Vertikalt dominant
        assert voyage.compute_heading((0, 0), (10, 100)) == "S"
        # Horisontalt dominant
        assert voyage.compute_heading((0, 0), (100, 10)) == "E"

    def test_same_position_returns_north(self):
        assert voyage.compute_heading((100, 100), (100, 100)) == "N"


# -----------------------------------------------------------------------------
# compute_progress
# -----------------------------------------------------------------------------


def _voyage_2_days(depart_day: int = 5) -> VoyageState:
    return VoyageState(
        from_port="tortuga",
        to_port="port_royal",
        depart_day=depart_day,
        arrival_day=depart_day + 2,
        progress=0.0,
    )


class TestComputeProgress:
    def test_progress_zero_at_departure(self):
        bal = balance.get()
        v = _voyage_2_days()
        clock = GameClock(day=5, seconds_into_day=0.0)
        assert voyage.compute_progress(v, clock, bal) == 0.0

    def test_progress_half_at_one_day_in(self):
        bal = balance.get()
        v = _voyage_2_days()
        clock = GameClock(day=6, seconds_into_day=0.0)
        # Halvveis gjennom 2-dagers reise
        assert abs(voyage.compute_progress(v, clock, bal) - 0.5) < 1e-9

    def test_progress_one_at_arrival_day(self):
        bal = balance.get()
        v = _voyage_2_days()
        clock = GameClock(day=7, seconds_into_day=0.0)
        assert voyage.compute_progress(v, clock, bal) == 1.0

    def test_progress_clamped_to_one_after_arrival(self):
        bal = balance.get()
        v = _voyage_2_days()
        clock = GameClock(day=10, seconds_into_day=50.0)
        assert voyage.compute_progress(v, clock, bal) == 1.0

    def test_progress_uses_seconds_into_day(self):
        bal = balance.get()
        v = _voyage_2_days()
        spd = bal.time.seconds_per_day_at_sea
        # Halvveis i dag 0 av 2: clock=5, sec_into_day = spd/2
        clock = GameClock(day=5, seconds_into_day=spd / 2)
        # 0.5 * spd / (2 * spd) = 0.25
        assert abs(voyage.compute_progress(v, clock, bal) - 0.25) < 1e-9

    def test_same_day_voyage_returns_one_defensive(self):
        bal = balance.get()
        v = VoyageState(
            from_port="a", to_port="b",
            depart_day=5, arrival_day=5, progress=0.0,
        )
        clock = GameClock(day=5, seconds_into_day=0.0)
        assert voyage.compute_progress(v, clock, bal) == 1.0


# -----------------------------------------------------------------------------
# interpolate_position
# -----------------------------------------------------------------------------


class TestInterpolatePosition:
    def test_start_at_progress_zero(self):
        assert voyage.interpolate_position((10, 20), (110, 120), 0.0) == (10, 20)

    def test_end_at_progress_one(self):
        assert voyage.interpolate_position((10, 20), (110, 120), 1.0) == (110, 120)

    def test_midpoint_at_progress_half(self):
        assert voyage.interpolate_position((10, 20), (110, 120), 0.5) == (60, 70)


# -----------------------------------------------------------------------------
# start_voyage
# -----------------------------------------------------------------------------


class TestStartVoyage:
    def test_success_creates_voyage_with_correct_arrival(self):
        state = save_module.new_game_state()
        state.world_state.clock.day = 5
        bal = balance.get()
        v = voyage.start_voyage(state, bal, "tortuga", "port_royal")
        assert v is not None
        assert v.from_port == "tortuga"
        assert v.to_port == "port_royal"
        assert v.depart_day == 5
        assert v.arrival_day == 5 + 2  # rute er 2 dager
        assert v.progress == 0.0
        # Lagret i state
        assert state.world_state.voyage is v

    def test_success_switches_clock_to_at_sea_tempo(self):
        state = save_module.new_game_state()
        bal = balance.get()
        before_spd = state.world_state.clock.seconds_per_day
        assert before_spd == bal.time.seconds_per_day_in_port

        voyage.start_voyage(state, bal, "tortuga", "havana")
        assert state.world_state.clock.seconds_per_day == bal.time.seconds_per_day_at_sea

    def test_success_deducts_route_gold(self):
        """C9: start_voyage trekker route.gold fra player.gold ved
        suksess. Tortuga→Port Royal er 10 gull per balance.json.
        Atomisk med voyage-state-opprettelsen.
        """
        state = save_module.new_game_state()
        state.player_state.gold = 250
        bal = balance.get()
        voyage.start_voyage(state, bal, "tortuga", "port_royal")
        assert state.player_state.gold == 240  # 250 - 10

    def test_success_writes_observed_for_from_port(self):
        """Spilleren har akkurat vært i børsen i from_port — prisene skal
        registreres som observerte før avreise.
        """
        state = save_module.new_game_state()
        state.world_state.clock.day = 3
        # Endre Tortuga-pris så vi kan verifisere at snapshotet leser
        # current_price (ikke gammel observed-verdi)
        state.economy_state.markets["tortuga"].commodities["sugar"].current_price = 99.0
        bal = balance.get()
        voyage.start_voyage(state, bal, "tortuga", "havana")
        observed_sugar = state.economy_state.observed["tortuga"]["sugar"]
        assert observed_sugar.price == 99.0
        assert observed_sugar.day_seen == 3

    def test_returns_none_for_unknown_route(self):
        state = save_module.new_game_state()
        bal = balance.get()
        v = voyage.start_voyage(state, bal, "atlantis", "tortuga")
        assert v is None
        # Ingen state-mutasjon
        assert state.world_state.voyage is None
        assert state.world_state.clock.seconds_per_day == bal.time.seconds_per_day_in_port

    def test_returns_none_when_voyage_already_active(self):
        state = save_module.new_game_state()
        bal = balance.get()
        first = voyage.start_voyage(state, bal, "tortuga", "havana")
        assert first is not None
        # Andre forsøk på en ny voyage skal feile uten å overskrive
        second = voyage.start_voyage(state, bal, "tortuga", "port_royal")
        assert second is None
        assert state.world_state.voyage is first  # første voyage uendret


# -----------------------------------------------------------------------------
# complete_voyage
# -----------------------------------------------------------------------------


class TestCompleteVoyage:
    def test_clears_voyage_and_sets_current_port(self):
        state = save_module.new_game_state()
        bal = balance.get()
        voyage.start_voyage(state, bal, "tortuga", "havana")
        # Simuler at klokken har avansert til ankomst
        state.world_state.clock.day = state.world_state.voyage.arrival_day

        new_port = voyage.complete_voyage(state, bal)
        assert new_port == "havana"
        assert state.world_state.current_port == "havana"
        assert state.world_state.voyage is None

    def test_resets_clock_to_in_port_tempo(self):
        state = save_module.new_game_state()
        bal = balance.get()
        voyage.start_voyage(state, bal, "tortuga", "nassau")
        assert state.world_state.clock.seconds_per_day == bal.time.seconds_per_day_at_sea
        voyage.complete_voyage(state, bal)
        assert state.world_state.clock.seconds_per_day == bal.time.seconds_per_day_in_port

    def test_noop_when_no_active_voyage(self):
        state = save_module.new_game_state()
        bal = balance.get()
        # Ingen voyage aktiv
        assert state.world_state.voyage is None
        original_port = state.world_state.current_port
        result = voyage.complete_voyage(state, bal)
        assert result == original_port  # returnerer current_port uendret
        assert state.world_state.voyage is None
        # Klokke uendret (ingen tempo-bytte fordi ingenting å fullføre)
        assert state.world_state.clock.seconds_per_day == bal.time.seconds_per_day_in_port


# -----------------------------------------------------------------------------
# Round-trip save med aktiv voyage (flyttet fra C7c per brukerens regi)
# -----------------------------------------------------------------------------


class TestVoyageRoundTrip:
    def test_save_load_preserves_active_voyage(self, tmp_path):
        """Save mid-voyage → load → voyage og clock.seconds_per_day
        gjenopprettes nøyaktig. Dette er voyage-resume-fundamentet
        spec §10 C7 krever; tester her i C7b uten scene-kompleksitet
        slik at en fremtidig regresjon kan attribueres til save eller
        scene, ikke begge på en gang.
        """
        state = save_module.new_game_state()
        state.world_state.clock.day = 5
        state.world_state.clock.seconds_into_day = 42.0
        bal = balance.get()
        v = voyage.start_voyage(state, bal, "tortuga", "havana")
        assert v is not None
        # Simuler at klokken har tikket inn i reisen
        state.world_state.clock.day = 6
        state.world_state.clock.seconds_into_day = 30.0
        # progress på dette tidspunktet skal samsvare med clock
        progress_before = voyage.compute_progress(
            v, state.world_state.clock, bal
        )

        save_path = tmp_path / "voyage_save.json"
        assert save_module.save(state, str(save_path)) is True

        loaded = save_module.load(str(save_path))
        assert loaded is not None
        # Voyage-felter eksakt bevart
        assert loaded.world_state.voyage is not None
        lv = loaded.world_state.voyage
        assert lv.from_port == "tortuga"
        assert lv.to_port == "havana"
        assert lv.depart_day == 5
        assert lv.arrival_day == 5 + 3  # havana-tortuga-rute er 3 dager
        # Clock-tempo bevart (at_sea, ikke in_port)
        assert loaded.world_state.clock.seconds_per_day == bal.time.seconds_per_day_at_sea
        assert loaded.world_state.clock.day == 6
        assert loaded.world_state.clock.seconds_into_day == 30.0
        # Progress reproduseres deterministisk fra clock-state
        progress_after = voyage.compute_progress(
            lv, loaded.world_state.clock, bal
        )
        assert abs(progress_after - progress_before) < 1e-9
