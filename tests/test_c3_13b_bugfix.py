"""Tester for C3-13b bug-fikser.

Bug 1: Input-state-lekkasje etter dialog-åpning. KEYUP-events for D/A
    går til dialogen, så Player-movement-flags forblir satt etter
    dialog-close. Løsning: PortVillageScene.update() nullstiller
    player.press(0) hver frame så lenge en dialog er åpen.

Bug 2: Siste-dag-voyage-event rekker ikke å rendre før complete_voyage
    scene-switcher. Løsning: arrival-detection i VoyageScene.update()
    returnerer tidlig hvis event-dialog er åpen.
"""

from __future__ import annotations

import os

import pygame
import pytest

from config import port_config
from state import GameState
from state.voyage_state import VoyageState
from systems import balance, save as save_module


@pytest.fixture(scope="module", autouse=True)
def _pygame_setup():
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


@pytest.fixture
def state() -> GameState:
    return save_module.new_game_state()


# -----------------------------------------------------------------------------
# Bug 1: Input-state-lekkasje
# -----------------------------------------------------------------------------


class TestInputLeakFix:
    def _scene(self, font, state):
        from scenes.port_village import PortVillageScene
        scene = PortVillageScene(
            font, state, port_config.get(state.world_state.current_port),
        )
        scene.on_enter(state, from_scene=None)
        return scene

    def _is_moving_right(self, scene) -> bool:
        return scene._player._right_pressed

    def _is_moving_left(self, scene) -> bool:
        return scene._player._left_pressed

    def test_open_tavern_clears_movement_on_next_update(self, font, state):
        """Spiller holder D, åpner tavern, update() nullstiller flagget."""
        scene = self._scene(font, state)
        scene._player.press(+1)
        assert self._is_moving_right(scene) is True
        scene._open_tavern()
        # Dialog åpner — update() fires og skal nullstille.
        scene.update(0.016)
        assert self._is_moving_right(scene) is False
        assert self._is_moving_left(scene) is False

    def test_pending_event_dialog_clears_movement(self, font, state):
        """Random event-dialog åpnes via pending_event_id. Movement-
        flags skal nullstilles."""
        scene = self._scene(font, state)
        scene._player.press(+1)
        state.world_state.pending_event_id = "storm"
        scene.update(0.016)  # triggers _maybe_open_pending_event
        assert scene._event_dialog is not None
        assert self._is_moving_right(scene) is False

    def test_score_overlay_clears_movement(self, font, state):
        """Game-over trigger via completed. Overlay åpnes. Movement cleared."""
        scene = self._scene(font, state)
        scene._player.press(-1)  # venstre holdt
        state.world_state.clock.day = 101  # trigger "completed"
        scene.update(0.016)
        assert scene._score_overlay is not None
        assert self._is_moving_left(scene) is False

    def test_dialog_close_does_not_retrigger_movement(self, font, state):
        """Dialog lukkes; neste update fortsatt med flagget som False."""
        scene = self._scene(font, state)
        scene._player.press(+1)
        scene._open_tavern()
        scene.update(0.016)  # clears due to dialog open
        assert self._is_moving_right(scene) is False
        # Simuler at dialogen lukkes
        scene._tavern_dialog._want_close = True
        scene.update(0.016)  # lifecycle clears dialog
        assert scene._tavern_dialog is None
        # Neste update skal IKKE reaktivere movement-flagg fra før.
        scene.update(0.016)
        assert self._is_moving_right(scene) is False
        assert self._is_moving_left(scene) is False

    def test_any_dialog_open_helper_covers_all_dialogs(self, font, state):
        """Sanity: _any_dialog_open() dekker alle dialog-felter."""
        scene = self._scene(font, state)
        assert scene._any_dialog_open() is False
        scene._open_tavern()
        assert scene._any_dialog_open() is True
        scene._tavern_dialog = None
        scene._open_harbormaster()
        assert scene._any_dialog_open() is True
        scene._harbormaster_dialog = None
        assert scene._any_dialog_open() is False


# -----------------------------------------------------------------------------
# Bug 2: Voyage-arrival race med event-dialog
# -----------------------------------------------------------------------------


class TestVoyageArrivalWaitsForEventDialog:
    def _scene(self, font, state, depart_day=1, days=2):
        from scenes.voyage import VoyageScene
        state.world_state.voyage = VoyageState(
            from_port="tortuga", to_port="port_royal",
            depart_day=depart_day,
            arrival_day=depart_day + days,
            progress=0.0,
        )
        state.world_state.clock.day = depart_day
        state.world_state.clock.seconds_into_day = 0.0
        return VoyageScene(font, state)

    def test_event_on_arrival_day_does_not_scene_switch(
        self, font, state, monkeypatch,
    ):
        """Event samples på siste dag: dialog åpner, ingen scene-switch.

        Bruker `pirates_raid` som ikke endrer arrival_day (storm gjør det
        via voyage_delay_days-effekt — ville ugyldiggjøre testen).
        """
        from systems import events as _events
        scene = self._scene(font, state, depart_day=1, days=2)
        monkeypatch.setattr(
            _events, "sample_voyage_event", lambda *a, **kw: "pirates_raid"
        )

        # Avanser clock til arrival_day (dag 3), kjør update.
        state.world_state.clock.day = 3
        scene.update(0.016)

        # Event-dialog skal være åpen, scene-switch skal IKKE ha skjedd.
        assert scene._event_dialog is not None, (
            "Event-dialog skal være åpen når event samples på arrival-dag"
        )
        assert scene.next_scene is None, (
            "Scene skal IKKE ha switchet til port_village før dialog er lukket"
        )
        # Voyage-state er ennå aktiv (complete_voyage ikke kalt).
        assert state.world_state.voyage is not None

    def test_arrival_triggers_after_event_dialog_closes(
        self, font, state, monkeypatch,
    ):
        """Etter dialog-close skal neste update trigger complete_voyage.

        Event samples kun én gang (første dawn-tick); etterfølgende
        dawn-ticks returnerer None. Uten denne one-shot-logikken
        ville C3-13b.1-fiksen triggere nytt event på dag 2's dawn-
        tick (days-processed økning får loopen til å faktisk kjøre
        videre) og arrival ville aldri nås.
        """
        from systems import events as _events
        scene = self._scene(font, state, depart_day=1, days=2)
        call_count = {"n": 0}
        def sample_once(*a, **kw):
            call_count["n"] += 1
            return "pirates_raid" if call_count["n"] == 1 else None
        monkeypatch.setattr(_events, "sample_voyage_event", sample_once)
        state.world_state.clock.day = 3
        scene.update(0.016)
        assert scene._event_dialog is not None

        # Simuler at spiller trykker Enter på dialogen
        scene._event_dialog._want_close = True
        # Pause-branchen i update() clearer dialogen, returnerer tidlig.
        scene.update(0.016)
        assert scene._event_dialog is None

        # Tredje update: dialog er None, dag 2's dawn-tick kjører
        # (C3-13b.1), arrival-detection fires etter.
        scene.update(0.016)
        assert scene.next_scene == "port_village", (
            "Scene-switch skal skje etter at event-dialogen er lukket"
        )
        assert state.world_state.voyage is None, (
            "complete_voyage skal ha ryddet voyage-state"
        )

    def test_no_event_sampled_arrival_works_normally(
        self, font, state, monkeypatch,
    ):
        """Regresjons-guard: uten event samples fungerer arrival som før."""
        from systems import events as _events
        scene = self._scene(font, state, depart_day=1, days=2)
        monkeypatch.setattr(
            _events, "sample_voyage_event", lambda *a, **kw: None
        )
        state.world_state.clock.day = 3
        scene.update(0.016)
        assert scene._event_dialog is None
        assert scene.next_scene == "port_village"
        assert state.world_state.voyage is None


# -----------------------------------------------------------------------------
# Bug 1b (C3-13b.1): Dawn-tick-loop taper ikke dager ved event-break
# -----------------------------------------------------------------------------


class TestDawnTicksNotDroppedByEventBreak:
    def _scene(self, font, state, depart_day=1, days=3):
        from scenes.voyage import VoyageScene
        state.world_state.voyage = VoyageState(
            from_port="tortuga", to_port="havana",
            depart_day=depart_day,
            arrival_day=depart_day + days,
            progress=0.0,
        )
        state.world_state.clock.day = depart_day
        state.world_state.clock.seconds_into_day = 0.0
        return VoyageScene(font, state)

    def test_dawn_ticks_process_all_days_across_event_break(
        self, font, state, monkeypatch,
    ):
        """3-dagers reise, event samples kun på første dawn-tick.
        Spiller skipper resten. BÅDE dag 2 OG dag 3 dawn-tick skal
        ha kjørt før complete_voyage.

        Verifisering: MarketState.tick_id bumpes én gang per dawn-tick
        per havn. Før update: 0. Etter 3 dawn-ticks: 3 per havn.
        """
        from systems import events as _events
        scene = self._scene(font, state, depart_day=1, days=3)

        # Event kun på første dawn-tick, så None etterpå.
        call_count = {"n": 0}
        def sample_once(*a, **kw):
            call_count["n"] += 1
            return "pirates_raid" if call_count["n"] == 1 else None
        monkeypatch.setattr(_events, "sample_voyage_event", sample_once)

        before_tick_ids = {
            pid: ms.tick_id
            for pid, ms in state.economy_state.markets.items()
        }

        # Avanser clock til arrival (dag 4) → 3 dawn-ticks skal kjøre.
        state.world_state.clock.day = 4
        scene.update(0.016)  # iteration 1 kjører dawn-tick for dag 2, event → break

        # Én dawn-tick er prosessert, _last_seen_day skal være 2.
        assert scene._last_seen_day == 2, (
            f"Etter ett dawn-tick-break: _last_seen_day skal være 2, "
            f"fikk {scene._last_seen_day}"
        )
        assert scene._event_dialog is not None

        # Lukk dialogen, kjør neste update — resterende 2 dawn-ticks skal fire.
        scene._event_dialog._want_close = True
        scene.update(0.016)  # dialog close, return
        assert scene._event_dialog is None

        # Tredje update: dawn-loop fortsetter fra dag 3 til dag 4.
        scene.update(0.016)

        # Alle 3 dawn-ticks skal ha fyrt — tick_id bumpet 3 ganger per havn.
        for pid, ms in state.economy_state.markets.items():
            assert ms.tick_id == before_tick_ids[pid] + 3, (
                f"{pid}: forventet +3 dawn-ticks totalt, "
                f"fikk {ms.tick_id - before_tick_ids[pid]}"
            )

        # Voyage skal være fullført.
        assert state.world_state.voyage is None
        assert scene.next_scene == "port_village"

    def test_event_on_first_day_multi_day_route_preserves_second_dawn(
        self, font, state, monkeypatch,
    ):
        """Enklere 2-dagers case: event på dag 1, verifiser at dag 2
        dawn-tick kjører før complete_voyage."""
        from systems import events as _events
        scene = self._scene(font, state, depart_day=1, days=2)

        call_count = {"n": 0}
        def sample_once(*a, **kw):
            call_count["n"] += 1
            return "pirates_raid" if call_count["n"] == 1 else None
        monkeypatch.setattr(_events, "sample_voyage_event", sample_once)

        before_tick_ids = {
            pid: ms.tick_id
            for pid, ms in state.economy_state.markets.items()
        }

        state.world_state.clock.day = 3  # arrival
        scene.update(0.016)  # event break på dag 2 dawn-tick

        assert scene._last_seen_day == 2
        scene._event_dialog._want_close = True
        scene.update(0.016)
        scene.update(0.016)

        for pid, ms in state.economy_state.markets.items():
            assert ms.tick_id == before_tick_ids[pid] + 2, (
                f"{pid}: forventet +2 dawn-ticks, "
                f"fikk {ms.tick_id - before_tick_ids[pid]}"
            )
        assert state.world_state.voyage is None

    def test_no_event_all_days_processed_in_one_update(
        self, font, state, monkeypatch,
    ):
        """Regresjons-guard: uten event kjører alle dawn-ticks i ett update."""
        from systems import events as _events
        scene = self._scene(font, state, depart_day=1, days=3)
        monkeypatch.setattr(
            _events, "sample_voyage_event", lambda *a, **kw: None,
        )
        before_tick_ids = {
            pid: ms.tick_id
            for pid, ms in state.economy_state.markets.items()
        }
        state.world_state.clock.day = 4
        scene.update(0.016)
        for pid, ms in state.economy_state.markets.items():
            assert ms.tick_id == before_tick_ids[pid] + 3
        assert scene._last_seen_day == 4
