"""Tester for VoyageScene-tempo-akselerasjon — Fase 3 C3-9.5.

Dekker:
- Tempo-scaling ved scene-init (seconds_per_day = animation_sec / days_remaining)
- Skip-to-arrival via Enter/Space/ESC
- Dawn-tick-loop kjøres fortsatt N ganger etter skip
- Save/load-resume med akselerert tempo
- Balance-felt parses og er SESSION-kategori
"""

from __future__ import annotations

import json
from pathlib import Path

import pygame
import pytest

import constants
from state.game_state import GameState
from state.voyage_state import VoyageState
from systems import balance as _balance
from systems import save as save_module
from systems.game_clock import GameClock


@pytest.fixture(scope="module", autouse=True)
def _pygame_setup():
    import os
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    pygame.display.init()
    pygame.font.init()
    pygame.display.set_mode((640, 360), pygame.HIDDEN)
    yield
    pygame.display.quit()
    pygame.font.quit()


@pytest.fixture
def font():
    return pygame.font.SysFont(None, 12)


def _state_with_voyage(days: int = 3, current_day_offset: int = 0) -> GameState:
    """GameState med aktiv voyage fra Tortuga til Havana.

    `days`: route-lengde (arrival_day = depart_day + days).
    `current_day_offset`: hvor langt inn i reisen (0 = fresh, <days = resume).
    """
    state = save_module.new_game_state()
    depart = 1
    state.world_state.voyage = VoyageState(
        from_port="tortuga",
        to_port="havana",
        depart_day=depart,
        arrival_day=depart + days,
        progress=0.0,
    )
    state.world_state.clock = GameClock(
        day=depart + current_day_offset,
        seconds_into_day=0.0,
        seconds_per_day=_balance.get().time.seconds_per_day_at_sea,
    )
    return state


def _keydown(key: int, mod: int = 0) -> pygame.event.Event:
    return pygame.event.Event(pygame.KEYDOWN, {"key": key, "mod": mod})


# -----------------------------------------------------------------------------
# Balance-felt
# -----------------------------------------------------------------------------


class TestBalanceField:
    def test_voyage_animation_seconds_in_default_balance(self):
        bal = _balance.get()
        assert bal.time.voyage_animation_seconds == 5.0

    def test_is_session_category(self):
        """voyage_animation_seconds er SESSION (slår inn neste scene-init)."""
        assert "time.voyage_animation_seconds" in _balance.SESSION_FIELDS
        assert "time.voyage_animation_seconds" not in _balance.LIVE_FIELDS
        assert "time.voyage_animation_seconds" not in _balance.NEWGAME_FIELDS

    def test_hot_reload_detects_change_as_session(self, tmp_path):
        _balance._reset_for_tests()
        try:
            from pathlib import Path as _P
            root = _P(__file__).resolve().parent.parent
            content = json.loads(
                (root / "data" / "balance.json").read_text(encoding="utf-8")
            )
            path = tmp_path / "balance.json"
            path.write_text(json.dumps(content), encoding="utf-8")
            _balance.init(str(path))
            # Modify
            content["time"]["voyage_animation_seconds"] = 3.0
            path.write_text(json.dumps(content), encoding="utf-8")
            result = _balance.reload()
            assert result.success
            assert "time.voyage_animation_seconds" in result.session_changes
        finally:
            _balance._reset_for_tests()
            from pathlib import Path as _P
            root = _P(__file__).resolve().parent.parent
            _balance.init(str(root / "data" / "balance.json"))


# -----------------------------------------------------------------------------
# Tempo-scaling ved scene-init
# -----------------------------------------------------------------------------


class TestTempoScaling:
    def test_fresh_2_day_voyage_sets_tempo(self, font):
        """2-dagers reise: seconds_per_day = 5.0 / 2 = 2.5."""
        from scenes.voyage import VoyageScene
        state = _state_with_voyage(days=2)
        VoyageScene(font, state)
        assert state.world_state.clock.seconds_per_day == pytest.approx(2.5)

    def test_fresh_5_day_voyage_sets_tempo(self, font):
        """5-dagers reise: seconds_per_day = 5.0 / 5 = 1.0. Total animation
        = 5.0 sek wall-clock."""
        from scenes.voyage import VoyageScene
        state = _state_with_voyage(days=5)
        VoyageScene(font, state)
        assert state.world_state.clock.seconds_per_day == pytest.approx(1.0)

    def test_resume_mid_voyage_recomputes_tempo(self, font):
        """5-dagers reise, 3 dager gått: 2 dager igjen → 5.0 / 2 = 2.5."""
        from scenes.voyage import VoyageScene
        state = _state_with_voyage(days=5, current_day_offset=3)
        VoyageScene(font, state)
        # days_remaining = (1+5) - (1+3) = 2
        assert state.world_state.clock.seconds_per_day == pytest.approx(2.5)

    def test_scene_init_resets_seconds_into_day(self, font):
        """seconds_into_day nullstilles ved scene-init (sub-day-progress
        tapes ved resume — akseptabelt trade-off)."""
        from scenes.voyage import VoyageScene
        state = _state_with_voyage(days=3)
        state.world_state.clock.seconds_into_day = 40.0  # midt-i-dag
        VoyageScene(font, state)
        assert state.world_state.clock.seconds_into_day == 0.0

    def test_arrival_already_reached_no_divide_by_zero(self, font):
        """Edge case: scene konstrueres når clock.day == arrival_day
        (alle dager passert). Defensive: ingen divide-by-zero, tempo
        urørt."""
        from scenes.voyage import VoyageScene
        state = _state_with_voyage(days=3, current_day_offset=3)
        initial_tempo = state.world_state.clock.seconds_per_day
        VoyageScene(font, state)
        # days_remaining = 0 → ingen endring
        assert state.world_state.clock.seconds_per_day == initial_tempo


# -----------------------------------------------------------------------------
# Skip-to-arrival
# -----------------------------------------------------------------------------


class TestSkipToArrival:
    def test_enter_sets_clock_to_arrival_day(self, font):
        from scenes.voyage import VoyageScene
        state = _state_with_voyage(days=3)
        scene = VoyageScene(font, state)
        voyage = state.world_state.voyage
        assert voyage is not None
        scene.handle_event(_keydown(pygame.K_RETURN))
        assert state.world_state.clock.day == voyage.arrival_day
        assert state.world_state.clock.seconds_into_day == 0.0

    def test_space_skips_to_arrival(self, font):
        from scenes.voyage import VoyageScene
        state = _state_with_voyage(days=4)
        scene = VoyageScene(font, state)
        voyage = state.world_state.voyage
        scene.handle_event(_keydown(pygame.K_SPACE))
        assert state.world_state.clock.day == voyage.arrival_day

    def test_escape_skips_to_arrival(self, font):
        from scenes.voyage import VoyageScene
        state = _state_with_voyage(days=5)
        scene = VoyageScene(font, state)
        voyage = state.world_state.voyage
        scene.handle_event(_keydown(pygame.K_ESCAPE))
        assert state.world_state.clock.day == voyage.arrival_day

    def test_other_key_does_not_skip(self, font):
        from scenes.voyage import VoyageScene
        state = _state_with_voyage(days=3)
        scene = VoyageScene(font, state)
        day_before = state.world_state.clock.day
        scene.handle_event(_keydown(pygame.K_a))  # vilkårlig
        scene.handle_event(_keydown(pygame.K_e))
        assert state.world_state.clock.day == day_before

    def test_skip_triggers_all_remaining_dawn_ticks(self, font):
        """Presisering C3-9.5 #1: dawn-tick-loopen må kjøres N ganger.

        Verifiserer via observering av markeds-`tick_id` og pitch_lake
        total_produced etter skip + update."""
        from scenes.voyage import VoyageScene
        state = _state_with_voyage(days=3)
        # Aktiver bek-produksjon slik at dawn-ticks gir målbar effekt
        state.pitch_lake_state.purchased = True
        state.pitch_lake_state.production_per_day = 2
        state.pitch_lake_state.upkeep_per_day = 8
        state.player_state.gold = 1000  # nok til upkeep
        tortuga_market = state.economy_state.markets["tortuga"]
        initial_tick_id = tortuga_market.tick_id
        initial_total = state.pitch_lake_state.total_produced

        scene = VoyageScene(font, state)
        scene.handle_event(_keydown(pygame.K_RETURN))
        scene.update(0.016)  # lar update() kjøre dawn-loopen

        # Markedet har tikket 3 ganger (én per dag som passerte)
        assert tortuga_market.tick_id == initial_tick_id + 3
        # Bek produsert i 3 dager × 2/dag = 6 (hvis spilleren er hjemme
        # eller pending). Her er spilleren på reise, så går til pending.
        produced_delta = (
            state.pitch_lake_state.total_produced - initial_total
        )
        assert produced_delta == 6

    def test_skip_triggers_complete_voyage(self, font):
        from scenes.voyage import VoyageScene
        state = _state_with_voyage(days=2)
        scene = VoyageScene(font, state)
        scene.handle_event(_keydown(pygame.K_RETURN))
        scene.update(0.016)
        # complete_voyage setter current_port = to_port, voyage = None
        assert state.world_state.voyage is None
        assert state.world_state.current_port == "havana"
        assert scene.next_scene == "port_village"

    def test_skip_preserves_suspicion_decay(self, font):
        """Suspicion-decay skjer i dawn-pipelinen. Skip må respektere
        alle decay-stegene."""
        from scenes.voyage import VoyageScene
        state = _state_with_voyage(days=3)
        state.player_state.suspicion = 50.0
        scene = VoyageScene(font, state)
        scene.handle_event(_keydown(pygame.K_RETURN))
        scene.update(0.016)
        # Suspicion decay = 2/dag × 3 dager = 6
        assert state.player_state.suspicion == pytest.approx(44.0)

    def test_skip_at_arrival_is_noop(self, font):
        """Kalles skip når clock.day allerede == arrival_day →
        ingen endring (defensive)."""
        from scenes.voyage import VoyageScene
        state = _state_with_voyage(days=3, current_day_offset=3)
        scene = VoyageScene(font, state)
        day_before = state.world_state.clock.day
        scene.handle_event(_keydown(pygame.K_RETURN))
        assert state.world_state.clock.day == day_before


# -----------------------------------------------------------------------------
# Save/load-resume
# -----------------------------------------------------------------------------


class TestSaveLoadResume:
    def test_save_during_voyage_preserves_voyage_state(
        self, font, tmp_path
    ):
        from scenes.voyage import VoyageScene
        state = _state_with_voyage(days=5)
        VoyageScene(font, state)  # setter akselerert tempo
        path = tmp_path / "voyage_save.json"
        save_module.save(state, str(path))

        loaded = save_module.load(str(path))
        assert loaded is not None
        assert loaded.world_state.voyage is not None
        assert loaded.world_state.voyage.to_port == "havana"
        assert loaded.world_state.voyage.arrival_day == 6  # 1 + 5

    def test_resume_recomputes_tempo(self, font, tmp_path):
        """Load under voyage + nytt VoyageScene-init → tempo recomputed
        basert på days_remaining ved load-tidspunktet."""
        from scenes.voyage import VoyageScene
        # Fresh voyage: 5 dager
        state1 = _state_with_voyage(days=5)
        VoyageScene(font, state1)
        # Simuler 3 dager passert i spill-tid
        state1.world_state.clock.day = 4  # depart=1, så +3 dager
        # Lagre
        path = tmp_path / "mid_voyage.json"
        save_module.save(state1, str(path))

        # Load + ny scene-init
        state2 = save_module.load(str(path))
        assert state2 is not None
        VoyageScene(font, state2)
        # 2 dager remaining (arrival=6, current=4) → 5.0/2 = 2.5
        assert state2.world_state.clock.seconds_per_day == pytest.approx(2.5)

    def test_resume_then_skip_still_completes_voyage(
        self, font, tmp_path
    ):
        """End-to-end: save mid-voyage → load → skip → complete_voyage."""
        from scenes.voyage import VoyageScene
        state1 = _state_with_voyage(days=4)
        VoyageScene(font, state1)
        state1.world_state.clock.day = 3  # depart=1, 2 dager gått
        path = tmp_path / "resume_skip.json"
        save_module.save(state1, str(path))

        state2 = save_module.load(str(path))
        scene = VoyageScene(font, state2)
        scene.handle_event(_keydown(pygame.K_RETURN))
        scene.update(0.016)
        assert state2.world_state.current_port == "havana"
        assert state2.world_state.voyage is None
