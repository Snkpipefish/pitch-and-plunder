"""Tester for HarbormasterDialog — Fase 3 C3-4.

Verifiserer:
- Entry-lister (3 fast-travel + cache-stub + vis-kart)
- Per-havn rute-oppslag fra balance.travel.routes
- Fast-travel: Enter → voyage.start_voyage, requested_next_scene="voyage"
- Insufficient gold: ingen voyage startet, toast-feilhint
- Vis kart: requested_next_scene="world_map"
- Cache-stub: ikke navigerbar, ikke aktiverbar
- ESC og rendering-robusthet
"""

from __future__ import annotations

import pygame
import pytest

import constants
from config import port_config
from state import GameState
from state.ship_state import ShipState
from systems import save as save_module
from ui.harbormaster_dialog import (
    ACTION_CACHE,
    ACTION_SHOW_MAP,
    ACTION_TRAVEL_PREFIX,
    HarbormasterDialog,
)
from ui.toast import ToastQueue


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


@pytest.fixture
def state() -> GameState:
    """Fresh game state med bias-initialiserte markeder + gull."""
    s = save_module.new_game_state()
    s.player_state.gold = 100  # nok til alle ruter fra Tortuga (max 20)
    return s


@pytest.fixture
def toasts(font) -> ToastQueue:
    return ToastQueue(baseline_y=340, center_x=320)


def _keydown(key: int) -> pygame.event.Event:
    return pygame.event.Event(pygame.KEYDOWN, {"key": key, "mod": 0})


# -----------------------------------------------------------------------------
# Entry-lister
# -----------------------------------------------------------------------------


class TestEntries:
    def test_tortuga_has_3_travel_entries(self, font, state):
        """Fra Tortuga: 3 andre havner + cache + vis-kart = 5 entries."""
        d = HarbormasterDialog(font, state, port_id="tortuga")
        entries = d._build_entries()
        assert len(entries) == 5
        action_ids = [e.action_id for e in entries]
        travel_ids = [a for a in action_ids if a.startswith(ACTION_TRAVEL_PREFIX)]
        assert len(travel_ids) == 3
        assert ACTION_CACHE in action_ids
        assert ACTION_SHOW_MAP in action_ids

    def test_current_port_not_in_travel_list(self, font, state):
        d = HarbormasterDialog(font, state, port_id="havana")
        entries = d._build_entries()
        dest_ids = [e.dest_port_id for e in entries if e.dest_port_id]
        assert "havana" not in dest_ids

    def test_all_three_other_ports_present(self, font, state):
        d = HarbormasterDialog(font, state, port_id="havana")
        entries = d._build_entries()
        dest_ids = {e.dest_port_id for e in entries if e.dest_port_id}
        assert dest_ids == {"tortuga", "nassau", "port_royal"}

    def test_travel_entries_include_route_cost(self, font, state):
        """cost_label inneholder dager og gull per balance.travel.routes."""
        d = HarbormasterDialog(font, state, port_id="tortuga")
        entries = d._build_entries()
        # port_royal-tortuga: 2d, 10 gull
        pr_entry = next(
            e for e in entries if e.dest_port_id == "port_royal"
        )
        assert "2" in pr_entry.cost_label  # days
        assert "10" in pr_entry.cost_label  # gold

    def test_show_map_entry_active(self, font, state):
        d = HarbormasterDialog(font, state, port_id="tortuga")
        entries = d._build_entries()
        show_map = next(e for e in entries if e.action_id == ACTION_SHOW_MAP)
        assert show_map.active is True

    def test_cache_entry_inactive_with_stub_tag(self, font, state):
        d = HarbormasterDialog(font, state, port_id="tortuga")
        entries = d._build_entries()
        cache = next(e for e in entries if e.action_id == ACTION_CACHE)
        assert cache.active is False
        assert "kommer i C3-5" in cache.cost_label

    def test_travel_entries_active_regardless_of_affordability(
        self, font, state
    ):
        """Fast-travel-entries er alltid aktive. Affordability sjekkes
        ved aktivering (toast-feilhint, ikke greying)."""
        state.player_state.gold = 0  # kan ikke råd noe som helst
        d = HarbormasterDialog(font, state, port_id="tortuga")
        entries = d._build_entries()
        travel_entries = [
            e for e in entries if e.action_id.startswith(ACTION_TRAVEL_PREFIX)
        ]
        assert all(e.active for e in travel_entries)


# -----------------------------------------------------------------------------
# Navigasjon
# -----------------------------------------------------------------------------


class TestNavigation:
    def test_initial_selection_on_first_active(self, font, state):
        """Rekkefølge (via get_all_port_ids): [havana, nassau, port_royal,
        cache, show_map] fra Tortuga. Cache er inaktiv; første aktiv = 0."""
        d = HarbormasterDialog(font, state, port_id="tortuga")
        assert d.selected == 0  # havana (første fast-travel)

    def test_navigation_skips_cache(self, font, state):
        """Down fra siste travel-entry (port_royal = index 2) skal skippe
        cache (index 3) og lande på vis-kart (index 4)."""
        d = HarbormasterDialog(font, state, port_id="tortuga")
        d._selected = 2  # port_royal
        d.handle_event(_keydown(pygame.K_DOWN))
        assert d.selected == 4  # vis-kart (skip cache)

    def test_wrap_around_from_show_map_to_first_travel(
        self, font, state
    ):
        d = HarbormasterDialog(font, state, port_id="tortuga")
        d._selected = 4  # vis-kart
        d.handle_event(_keydown(pygame.K_DOWN))
        assert d.selected == 0  # wrap til havana


# -----------------------------------------------------------------------------
# Fast-travel aktivering
# -----------------------------------------------------------------------------


class TestFastTravel:
    def test_enter_starts_voyage(self, font, state, toasts):
        """Enter på aktivert fast-travel setter voyage + close + transisjon."""
        initial_gold = state.player_state.gold
        d = HarbormasterDialog(
            font, state, port_id="tortuga", toasts=toasts
        )
        # Velg første fast-travel (havana, 15 gull, 3 dager)
        d._selected = 0
        entries = d._build_entries()
        assert entries[0].dest_port_id == "havana"

        d.handle_event(_keydown(pygame.K_RETURN))

        # Voyage startet
        assert state.world_state.voyage is not None
        assert state.world_state.voyage.from_port == "tortuga"
        assert state.world_state.voyage.to_port == "havana"
        # Gull trukket
        assert state.player_state.gold == initial_gold - 15
        # Dialog lukket + transisjon signalert
        assert d.want_close is True
        assert d.requested_next_scene == "voyage"

    def test_insufficient_gold_shows_toast_no_voyage(
        self, font, state, toasts
    ):
        state.player_state.gold = 5  # < 10 for port_royal-rute
        d = HarbormasterDialog(
            font, state, port_id="tortuga", toasts=toasts
        )
        # Velg port_royal (10 gull, 2 dager) — index 2 (havana, nassau, port_royal)
        entries = d._build_entries()
        pr_index = next(
            i for i, e in enumerate(entries)
            if e.dest_port_id == "port_royal"
        )
        d._selected = pr_index

        assert toasts.count == 0
        d.handle_event(_keydown(pygame.K_RETURN))

        # Ingen voyage, ingen gull-endring, toast pushet
        assert state.world_state.voyage is None
        assert state.player_state.gold == 5
        assert toasts.count == 1
        assert d.want_close is False  # dialog fortsatt åpen
        assert d.requested_next_scene is None

    def test_no_voyage_when_voyage_already_active(
        self, font, state, toasts
    ):
        """Defensive — hvis dialog åpnes mens voyage er aktiv (skal ikke
        skje i scene-owner) så blokkerer start_voyage."""
        from state.voyage_state import VoyageState
        state.world_state.voyage = VoyageState(
            from_port="tortuga", to_port="nassau",
            depart_day=1, arrival_day=5, progress=0.0,
        )
        initial_gold = state.player_state.gold
        d = HarbormasterDialog(
            font, state, port_id="tortuga", toasts=toasts
        )
        d._selected = 0  # havana
        d.handle_event(_keydown(pygame.K_RETURN))
        # Ingen ny voyage startet, ingen gull trukket
        assert state.world_state.voyage.to_port == "nassau"  # den gamle
        assert state.player_state.gold == initial_gold
        assert d.requested_next_scene is None


# -----------------------------------------------------------------------------
# Vis kart aktivering
# -----------------------------------------------------------------------------


class TestShowMap:
    def test_enter_on_show_map_requests_world_map(self, font, state):
        d = HarbormasterDialog(font, state, port_id="tortuga")
        # Vis-kart er siste entry (index 4 for Tortuga)
        entries = d._build_entries()
        sm_index = next(
            i for i, e in enumerate(entries) if e.action_id == ACTION_SHOW_MAP
        )
        d._selected = sm_index
        d.handle_event(_keydown(pygame.K_RETURN))
        assert d.want_close is True
        assert d.requested_next_scene == "world_map"


# -----------------------------------------------------------------------------
# Cache-stub
# -----------------------------------------------------------------------------


class TestCacheStub:
    def test_cache_enter_is_noop(self, font, state):
        """Manuelt sett _selected til cache — Enter skal ikke aktivere."""
        d = HarbormasterDialog(font, state, port_id="tortuga")
        entries = d._build_entries()
        cache_index = next(
            i for i, e in enumerate(entries) if e.action_id == ACTION_CACHE
        )
        d._selected = cache_index
        d.handle_event(_keydown(pygame.K_RETURN))
        # Ingen transisjon, ingen close
        assert d.want_close is False
        assert d.requested_next_scene is None


# -----------------------------------------------------------------------------
# ESC og rendering
# -----------------------------------------------------------------------------


class TestEscAndRender:
    def test_esc_closes_without_transition(self, font, state):
        d = HarbormasterDialog(font, state, port_id="tortuga")
        d.handle_event(_keydown(pygame.K_ESCAPE))
        assert d.want_close is True
        assert d.requested_next_scene is None

    def test_draw_no_crash(self, font, state):
        d = HarbormasterDialog(font, state, port_id="tortuga")
        surf = pygame.Surface((640, 360), pygame.SRCALPHA)
        d.draw(surf)

    def test_draw_from_each_port(self, font, state):
        """Alle 4 havner skal kunne vises uten crash."""
        surf = pygame.Surface((640, 360), pygame.SRCALPHA)
        for pid in ("tortuga", "port_royal", "havana", "nassau"):
            state.world_state.current_port = pid
            d = HarbormasterDialog(font, state, port_id=pid)
            d.draw(surf)


# -----------------------------------------------------------------------------
# Port-config validering (nye overlap-regler)
# -----------------------------------------------------------------------------


class TestPortConfigValidation:
    def test_all_4_ports_have_harbormaster_in_default_config(self):
        for pid in ("tortuga", "port_royal", "havana", "nassau"):
            p = port_config.get(pid)
            assert p.buildings.harbormaster is not None

    def test_harbormaster_does_not_overlap_tavern_anywhere(self):
        for pid in ("tortuga", "port_royal", "havana", "nassau"):
            p = port_config.get(pid)
            hm = p.buildings.harbormaster
            tav = p.buildings.tavern
            assert hm is not None
            # Ingen x-overlap
            assert hm.x >= tav.x + tav.w or hm.x + hm.w <= tav.x, (
                f"{pid}: harbormaster overlapper tavern (bbox-kollisjon)"
            )

    def test_harbormaster_does_not_overlap_exchange_anywhere(self):
        for pid in ("tortuga", "port_royal", "havana", "nassau"):
            p = port_config.get(pid)
            hm = p.buildings.harbormaster
            exch = p.buildings.exchange
            assert hm is not None
            assert hm.x >= exch.x + exch.w or hm.x + hm.w <= exch.x, (
                f"{pid}: harbormaster overlapper exchange (bbox-kollisjon)"
            )

    def test_harbormaster_center_safe_interact_distance_from_tavern(self):
        """Senter-avstand ≥ 2 × INTERACTION_DISTANCE = 80 px sikrer at
        interact-range ikke overlapper tavern."""
        for pid in ("tortuga", "port_royal", "havana", "nassau"):
            p = port_config.get(pid)
            hm = p.buildings.harbormaster
            tav = p.buildings.tavern
            assert hm is not None
            hm_cx = hm.x + hm.w / 2
            tav_cx = tav.x + tav.w / 2
            assert abs(hm_cx - tav_cx) >= 2 * constants.INTERACTION_DISTANCE, (
                f"{pid}: harbormaster-senter for nær tavern-senter"
            )

    def test_harbormaster_center_safe_interact_distance_from_exchange(self):
        for pid in ("tortuga", "port_royal", "havana", "nassau"):
            p = port_config.get(pid)
            hm = p.buildings.harbormaster
            exch = p.buildings.exchange
            assert hm is not None
            hm_cx = hm.x + hm.w / 2
            exch_cx = exch.x + exch.w / 2
            assert abs(hm_cx - exch_cx) >= 2 * constants.INTERACTION_DISTANCE, (
                f"{pid}: harbormaster-senter for nær exchange-senter"
            )
