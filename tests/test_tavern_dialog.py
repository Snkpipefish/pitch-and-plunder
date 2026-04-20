"""Tester for TavernDayDialog + TavernNightDialog — Fase 3 C3-3.

Verifiserer:
- Entry-lister (antall, aktive/inaktive)
- Navigasjon skipper inaktive oppføringer
- Rom-kjøp: trekker gull, setter rest=1.0, toast-feedback
- Gull-guard: insufficient gold → ingen mutasjon, toast-feilhint
- Bek-anlegg-entry (stubbed) vises kun i Tortuga før purchased=True
- Navigasjon uten aktive oppføringer er no-op
- ESC setter want_close
"""

from __future__ import annotations

import pygame
import pytest

import constants
from state import GameState
from ui.tavern_dialog import (
    ACTION_BUY_ROOM,
    ACTION_ORDER_SABOTAGE,
    ACTION_PITCH_LAKE_PURCHASE,
    ACTION_RUMOR_LISTEN_FREE,
    ACTION_RUMOR_LISTEN_PAID,
    ACTION_SPREAD_FALSE_RUMOR,
    TavernDayDialog,
    TavernNightDialog,
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
    s = GameState()
    s.player_state.gold = 100
    s.player_state.rest = 0.5
    return s


@pytest.fixture
def toasts(font) -> ToastQueue:
    return ToastQueue(baseline_y=340, center_x=320)


def _keydown(key: int) -> pygame.event.Event:
    return pygame.event.Event(pygame.KEYDOWN, {"key": key, "mod": 0})


# -----------------------------------------------------------------------------
# Entry-lister
# -----------------------------------------------------------------------------


class TestDayEntries:
    def test_tortuga_fresh_save_has_three_entries(self, font, state):
        """Tortuga før bek-anlegg-kjøp: rom + rykter-stub + bek-stub."""
        assert state.pitch_lake_state.purchased is False
        d = TavernDayDialog(font, state, port_id="tortuga")
        entries = d._build_entries()
        assert len(entries) == 3
        assert entries[0].action_id == ACTION_BUY_ROOM
        assert entries[0].active is True
        assert entries[1].action_id == ACTION_RUMOR_LISTEN_FREE
        assert entries[1].active is False
        assert entries[2].action_id == ACTION_PITCH_LAKE_PURCHASE
        assert entries[2].active is False

    def test_tortuga_after_purchase_hides_pitch_entry(self, font, state):
        """Etter purchased=True skjules bek-anlegg-entry."""
        state.pitch_lake_state.purchased = True
        d = TavernDayDialog(font, state, port_id="tortuga")
        entries = d._build_entries()
        action_ids = [e.action_id for e in entries]
        assert ACTION_PITCH_LAKE_PURCHASE not in action_ids
        assert len(entries) == 2  # rom + rykter-stub

    def test_non_tortuga_hides_pitch_entry(self, font, state):
        """Port Royal har ingen bek-entry uansett purchased-status."""
        d = TavernDayDialog(font, state, port_id="port_royal")
        entries = d._build_entries()
        action_ids = [e.action_id for e in entries]
        assert ACTION_PITCH_LAKE_PURCHASE not in action_ids
        assert len(entries) == 2

    def test_only_rom_is_active(self, font, state):
        """C3-3: rom-kjøp er eneste aktive handling i dag-menyen."""
        d = TavernDayDialog(font, state, port_id="tortuga")
        entries = d._build_entries()
        active_ids = [e.action_id for e in entries if e.active]
        assert active_ids == [ACTION_BUY_ROOM]


class TestNightEntries:
    def test_five_entries_fixed_order(self, font, state):
        d = TavernNightDialog(font, state, port_id="tortuga")
        entries = d._build_entries()
        assert len(entries) == 5
        assert [e.action_id for e in entries] == [
            ACTION_BUY_ROOM,
            ACTION_RUMOR_LISTEN_PAID,
            ACTION_ORDER_SABOTAGE,
            ACTION_SPREAD_FALSE_RUMOR,
            "smuggler_contact",
        ]

    def test_only_rom_is_active(self, font, state):
        """C3-3: rom-kjøp er eneste aktive handling i natt-menyen.

        Sabotasje (C3-10), rumor_listen_paid (C3-9), spread_false_rumor
        (C3-10) og smuggler_contact (senere fase) er stubbed.
        """
        d = TavernNightDialog(font, state, port_id="tortuga")
        entries = d._build_entries()
        active_ids = [e.action_id for e in entries if e.active]
        assert active_ids == [ACTION_BUY_ROOM]

    def test_cost_label_includes_stub_tag(self, font, state):
        d = TavernNightDialog(font, state, port_id="tortuga")
        entries = d._build_entries()
        # Inaktive entries har "(kommer i ...)"-tag i cost_label
        inactive = [e for e in entries if not e.active]
        assert all(
            "kommer i" in e.cost_label or "senere fase" in e.cost_label
            for e in inactive
        )


# -----------------------------------------------------------------------------
# Navigasjon: skip inaktive
# -----------------------------------------------------------------------------


class TestNavigationSkipsInactive:
    def test_initial_selection_on_first_active(self, font, state):
        d = TavernDayDialog(font, state, port_id="tortuga")
        # rom-entry på index 0, som er aktiv
        assert d.selected == 0

    def test_down_skips_inactive_to_next_active(self, font, state):
        """I TavernDayDialog er bare rom (index 0) aktiv. Down skal wrap
        tilbake til rom."""
        d = TavernDayDialog(font, state, port_id="tortuga")
        d.handle_event(_keydown(pygame.K_DOWN))
        assert d.selected == 0  # wrap-around siden ingen andre er aktive

    def test_up_skips_inactive_to_prev_active(self, font, state):
        d = TavernDayDialog(font, state, port_id="tortuga")
        d.handle_event(_keydown(pygame.K_UP))
        assert d.selected == 0  # samme, wrap

    def test_night_navigation_only_rom(self, font, state):
        d = TavernNightDialog(font, state, port_id="tortuga")
        assert d.selected == 0
        d.handle_event(_keydown(pygame.K_DOWN))
        assert d.selected == 0
        d.handle_event(_keydown(pygame.K_DOWN))
        assert d.selected == 0


# -----------------------------------------------------------------------------
# Rom-kjøp aktivering
# -----------------------------------------------------------------------------


class TestRoomPurchase:
    def test_buy_room_deducts_gold_and_sets_rest(
        self, font, state, toasts
    ):
        assert state.player_state.gold == 100
        assert state.player_state.rest == 0.5
        d = TavernDayDialog(font, state, port_id="tortuga", toasts=toasts)
        d.handle_event(_keydown(pygame.K_RETURN))
        # room_cost_gold = 10 i default balance.json
        assert state.player_state.gold == 90
        assert state.player_state.rest == 1.0

    def test_buy_room_pushes_success_toast(self, font, state, toasts):
        d = TavernDayDialog(font, state, port_id="tortuga", toasts=toasts)
        assert toasts.count == 0
        d.handle_event(_keydown(pygame.K_RETURN))
        assert toasts.count == 1

    def test_buy_room_keeps_dialog_open(self, font, state, toasts):
        """Rom-kjøp lukker IKKE dialog — spilleren lukker eksplisitt."""
        d = TavernDayDialog(font, state, port_id="tortuga", toasts=toasts)
        d.handle_event(_keydown(pygame.K_RETURN))
        assert d.want_close is False

    def test_buy_room_night_menu_also_works(self, font, state, toasts):
        d = TavernNightDialog(font, state, port_id="tortuga", toasts=toasts)
        d.handle_event(_keydown(pygame.K_RETURN))
        assert state.player_state.gold == 90
        assert state.player_state.rest == 1.0

    def test_buy_room_without_toasts_no_crash(self, font, state):
        """Dialog instansiert uten ToastQueue skal ikke crashe ved kjøp."""
        d = TavernDayDialog(font, state, port_id="tortuga", toasts=None)
        d.handle_event(_keydown(pygame.K_RETURN))
        assert state.player_state.gold == 90


class TestRoomPurchaseGoldGuard:
    def test_insufficient_gold_no_mutation(self, font, state, toasts):
        state.player_state.gold = 5  # < 10 room_cost_gold
        state.player_state.rest = 0.3
        d = TavernDayDialog(font, state, port_id="tortuga", toasts=toasts)
        d.handle_event(_keydown(pygame.K_RETURN))
        # Ingen mutasjon
        assert state.player_state.gold == 5
        assert state.player_state.rest == 0.3

    def test_insufficient_gold_pushes_error_toast(
        self, font, state, toasts
    ):
        state.player_state.gold = 5
        d = TavernDayDialog(font, state, port_id="tortuga", toasts=toasts)
        d.handle_event(_keydown(pygame.K_RETURN))
        assert toasts.count == 1

    def test_exact_gold_is_sufficient(self, font, state, toasts):
        """Gull == room_cost_gold → kjøp går gjennom."""
        state.player_state.gold = 10
        d = TavernDayDialog(font, state, port_id="tortuga", toasts=toasts)
        d.handle_event(_keydown(pygame.K_RETURN))
        assert state.player_state.gold == 0
        assert state.player_state.rest == 1.0


# -----------------------------------------------------------------------------
# Inaktive entries blokkerer aktivering
# -----------------------------------------------------------------------------


class TestInactiveEntriesBlocked:
    def test_selection_cannot_land_on_inactive(self, font, state):
        """Selv om vi forsøker å manipulere _selected direkte til en
        inaktiv entry, så blokkerer activation-sjekken."""
        d = TavernDayDialog(font, state, port_id="tortuga")
        # Manuelt flytt til inaktiv entry (rykter = index 1)
        d._selected = 1
        # Enter skal ikke ha noen effekt
        d.handle_event(_keydown(pygame.K_RETURN))
        assert state.player_state.gold == 100
        assert state.player_state.rest == 0.5


# -----------------------------------------------------------------------------
# ESC og rendering
# -----------------------------------------------------------------------------


class TestEscAndRender:
    def test_esc_sets_want_close(self, font, state):
        d = TavernDayDialog(font, state, port_id="tortuga")
        d.handle_event(_keydown(pygame.K_ESCAPE))
        assert d.want_close is True

    def test_draw_does_not_crash_with_active_entry(self, font, state):
        d = TavernDayDialog(font, state, port_id="tortuga")
        surf = pygame.Surface((640, 360), pygame.SRCALPHA)
        d.draw(surf)

    def test_draw_does_not_crash_with_no_active_entries(self, font, state):
        """Syntetisk dialog der alle entries er inaktive — draw må ikke
        krasje på manglende cursor-position."""
        d = TavernDayDialog(font, state, port_id="tortuga")
        # Overskriv _build_entries på denne instansen til å returnere
        # kun inaktive oppføringer.
        from ui.tavern_dialog import TavernEntry

        def _all_inactive():
            return [
                TavernEntry(
                    action_id="stub",
                    label="Stub",
                    cost_label="(kommer)",
                    active=False,
                )
            ]
        d._build_entries = _all_inactive  # type: ignore[assignment]
        d._entries_cached = None  # tving rebuild
        surf = pygame.Surface((640, 360), pygame.SRCALPHA)
        d.draw(surf)  # skal ikke crashe

    def test_night_factor_agnostic_rendering(self, font, state):
        """Begge dialoger kan tegnes uansett night_factor-tilstand."""
        day = TavernDayDialog(font, state, port_id="tortuga")
        night = TavernNightDialog(font, state, port_id="tortuga")
        surf = pygame.Surface((640, 360), pygame.SRCALPHA)
        day.draw(surf)
        night.draw(surf)
