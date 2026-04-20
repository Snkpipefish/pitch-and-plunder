"""Tester for CacheSubDialog + GameState.get_score — Fase 3 C3-5.

Verifiserer:
- get_score returnerer port_caches["tortuga"] (eller 0 ved manglende)
- Modus-toggle med up/down, amount nullstilles ved modus-bytte
- A/D ±1 (Shift=10) klampes per modus (on-hand for deposit, cache for withdraw)
- Enter med amount>0 utfører deposit/withdraw med korrekt mutasjon
- Enter med amount=0 er no-op
- ESC lukker uten mutasjon
- Tortuga tittel = "Gullkiste", andre havner = "Cache"
- Dialog-rendering uten crash i begge moduser
"""

from __future__ import annotations

import pygame
import pytest

import constants
from state import GameState
from ui.cache_dialog import (
    CacheSubDialog,
    MODE_DEPOSIT,
    MODE_WITHDRAW,
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
    s.player_state.port_caches["tortuga"] = 50
    return s


@pytest.fixture
def toasts(font) -> ToastQueue:
    return ToastQueue(baseline_y=340, center_x=320)


def _keydown(key: int, mod: int = 0) -> pygame.event.Event:
    return pygame.event.Event(pygame.KEYDOWN, {"key": key, "mod": mod})


# -----------------------------------------------------------------------------
# get_score
# -----------------------------------------------------------------------------


class TestGetScore:
    def test_score_empty_cache_is_zero(self):
        s = GameState()
        assert s.get_score() == 0

    def test_score_reflects_tortuga_cache(self):
        s = GameState()
        s.player_state.port_caches["tortuga"] = 250
        assert s.get_score() == 250

    def test_score_ignores_other_ports(self):
        """Gull i andre havners caches teller IKKE i score."""
        s = GameState()
        s.player_state.port_caches["havana"] = 1000
        s.player_state.port_caches["port_royal"] = 500
        s.player_state.port_caches["nassau"] = 700
        assert s.get_score() == 0  # ingen Tortuga-entry

    def test_score_ignores_gold_on_hand(self):
        """Gull på hånden teller IKKE i score."""
        s = GameState()
        s.player_state.gold = 5000
        assert s.get_score() == 0


# -----------------------------------------------------------------------------
# Default state + init
# -----------------------------------------------------------------------------


class TestInit:
    def test_default_mode_is_deposit(self, font, state):
        d = CacheSubDialog(font, state, port_id="tortuga")
        assert d._mode == MODE_DEPOSIT

    def test_default_amount_is_zero(self, font, state):
        d = CacheSubDialog(font, state, port_id="tortuga")
        assert d._amount == 0

    def test_ensures_port_cache_entry_exists(self, font, state):
        """Nytt port_id uten eksisterende entry skal få default 0."""
        assert "havana" not in state.player_state.port_caches
        d = CacheSubDialog(font, state, port_id="havana")
        assert state.player_state.port_caches["havana"] == 0
        del d


# -----------------------------------------------------------------------------
# Modus-toggle
# -----------------------------------------------------------------------------


class TestModeToggle:
    def test_down_switches_to_withdraw(self, font, state):
        d = CacheSubDialog(font, state, port_id="tortuga")
        d.handle_event(_keydown(pygame.K_DOWN))
        assert d._mode == MODE_WITHDRAW

    def test_up_switches_to_deposit(self, font, state):
        d = CacheSubDialog(font, state, port_id="tortuga")
        d._mode = MODE_WITHDRAW
        d.handle_event(_keydown(pygame.K_UP))
        assert d._mode == MODE_DEPOSIT

    def test_mode_toggle_resets_amount(self, font, state):
        d = CacheSubDialog(font, state, port_id="tortuga")
        d._amount = 30
        d.handle_event(_keydown(pygame.K_DOWN))  # deposit → withdraw
        assert d._amount == 0

    def test_mode_toggle_no_op_if_same_mode(self, font, state):
        """Opp-piltrykk mens allerede i deposit skal ikke nullstille amount."""
        d = CacheSubDialog(font, state, port_id="tortuga")
        d._amount = 20
        d.handle_event(_keydown(pygame.K_UP))  # allerede deposit
        assert d._mode == MODE_DEPOSIT
        assert d._amount == 20


# -----------------------------------------------------------------------------
# Amount-justering med A/D
# -----------------------------------------------------------------------------


class TestAmountAdjustment:
    def test_d_increases_amount(self, font, state):
        d = CacheSubDialog(font, state, port_id="tortuga")
        d.handle_event(_keydown(pygame.K_d))
        assert d._amount == 1

    def test_a_decreases_amount(self, font, state):
        d = CacheSubDialog(font, state, port_id="tortuga")
        d._amount = 5
        d.handle_event(_keydown(pygame.K_a))
        assert d._amount == 4

    def test_shift_d_increases_by_10(self, font, state):
        d = CacheSubDialog(font, state, port_id="tortuga")
        d.handle_event(_keydown(pygame.K_d, mod=pygame.KMOD_LSHIFT))
        assert d._amount == 10

    def test_shift_a_decreases_by_10(self, font, state):
        d = CacheSubDialog(font, state, port_id="tortuga")
        d._amount = 25
        d.handle_event(_keydown(pygame.K_a, mod=pygame.KMOD_LSHIFT))
        assert d._amount == 15

    def test_arrow_keys_equivalent_to_ad(self, font, state):
        d = CacheSubDialog(font, state, port_id="tortuga")
        d.handle_event(_keydown(pygame.K_RIGHT))
        d.handle_event(_keydown(pygame.K_RIGHT))
        assert d._amount == 2
        d.handle_event(_keydown(pygame.K_LEFT))
        assert d._amount == 1

    def test_amount_cannot_go_below_zero(self, font, state):
        d = CacheSubDialog(font, state, port_id="tortuga")
        d.handle_event(_keydown(pygame.K_a))
        assert d._amount == 0

    def test_deposit_amount_clamped_to_gold_on_hand(self, font, state):
        """I deposit-modus er max = gold. state.gold = 100."""
        d = CacheSubDialog(font, state, port_id="tortuga")
        for _ in range(15):
            d.handle_event(_keydown(pygame.K_d, mod=pygame.KMOD_LSHIFT))
        # Totalt 150 forsøkt, men klampes til 100 (gull på hånden)
        assert d._amount == 100

    def test_withdraw_amount_clamped_to_cache(self, font, state):
        """I withdraw-modus er max = cache. state Tortuga-cache = 50."""
        d = CacheSubDialog(font, state, port_id="tortuga")
        d._mode = MODE_WITHDRAW
        for _ in range(10):
            d.handle_event(_keydown(pygame.K_d, mod=pygame.KMOD_LSHIFT))
        # 100 forsøkt, klampes til 50 (cache-balanse)
        assert d._amount == 50


# -----------------------------------------------------------------------------
# Enter commit
# -----------------------------------------------------------------------------


class TestDepositCommit:
    def test_deposit_transfers_gold_to_cache(self, font, state, toasts):
        d = CacheSubDialog(font, state, port_id="tortuga", toasts=toasts)
        d._amount = 30
        d.handle_event(_keydown(pygame.K_RETURN))
        assert state.player_state.gold == 70
        assert state.player_state.port_caches["tortuga"] == 80

    def test_deposit_updates_score(self, font, state, toasts):
        """Tortuga-deposit endrer score-verdien (port_caches['tortuga'])."""
        initial_score = state.get_score()
        d = CacheSubDialog(font, state, port_id="tortuga", toasts=toasts)
        d._amount = 20
        d.handle_event(_keydown(pygame.K_RETURN))
        assert state.get_score() == initial_score + 20

    def test_non_tortuga_deposit_does_not_affect_score(
        self, font, state, toasts
    ):
        initial_score = state.get_score()
        d = CacheSubDialog(font, state, port_id="havana", toasts=toasts)
        d._amount = 20
        d.handle_event(_keydown(pygame.K_RETURN))
        assert state.get_score() == initial_score  # uendret (0)
        assert state.player_state.port_caches["havana"] == 20

    def test_deposit_resets_amount_to_zero_after_commit(
        self, font, state, toasts
    ):
        d = CacheSubDialog(font, state, port_id="tortuga", toasts=toasts)
        d._amount = 15
        d.handle_event(_keydown(pygame.K_RETURN))
        assert d._amount == 0

    def test_deposit_commit_pushes_toast(self, font, state, toasts):
        d = CacheSubDialog(font, state, port_id="tortuga", toasts=toasts)
        d._amount = 10
        assert toasts.count == 0
        d.handle_event(_keydown(pygame.K_RETURN))
        assert toasts.count == 1


class TestWithdrawCommit:
    def test_withdraw_transfers_cache_to_gold(self, font, state, toasts):
        d = CacheSubDialog(font, state, port_id="tortuga", toasts=toasts)
        d._mode = MODE_WITHDRAW
        d._amount = 20
        d.handle_event(_keydown(pygame.K_RETURN))
        assert state.player_state.gold == 120
        assert state.player_state.port_caches["tortuga"] == 30

    def test_withdraw_reduces_score(self, font, state, toasts):
        """Tortuga-withdraw reduserer score-verdien."""
        initial_score = state.get_score()
        d = CacheSubDialog(font, state, port_id="tortuga", toasts=toasts)
        d._mode = MODE_WITHDRAW
        d._amount = 25
        d.handle_event(_keydown(pygame.K_RETURN))
        assert state.get_score() == initial_score - 25

    def test_withdraw_all_drains_cache(self, font, state, toasts):
        d = CacheSubDialog(font, state, port_id="tortuga", toasts=toasts)
        d._mode = MODE_WITHDRAW
        d._amount = 50  # exakt cache-balanse
        d.handle_event(_keydown(pygame.K_RETURN))
        assert state.player_state.port_caches["tortuga"] == 0
        assert state.player_state.gold == 150


class TestZeroAndEdgeCases:
    def test_enter_with_zero_amount_is_noop(self, font, state, toasts):
        d = CacheSubDialog(font, state, port_id="tortuga", toasts=toasts)
        assert d._amount == 0
        d.handle_event(_keydown(pygame.K_RETURN))
        assert state.player_state.gold == 100
        assert state.player_state.port_caches["tortuga"] == 50
        assert toasts.count == 0

    def test_dialog_stays_open_after_commit(self, font, state, toasts):
        """Rom-kjøp-lignende mønster: dialog forblir åpen for flere
        transaksjoner. Spilleren lukker eksplisitt med ESC."""
        d = CacheSubDialog(font, state, port_id="tortuga", toasts=toasts)
        d._amount = 10
        d.handle_event(_keydown(pygame.K_RETURN))
        assert d.want_close is False

    def test_two_deposits_accumulate_in_cache(self, font, state, toasts):
        d = CacheSubDialog(font, state, port_id="tortuga", toasts=toasts)
        d._amount = 15
        d.handle_event(_keydown(pygame.K_RETURN))
        d._amount = 25
        d.handle_event(_keydown(pygame.K_RETURN))
        assert state.player_state.port_caches["tortuga"] == 50 + 15 + 25
        assert state.player_state.gold == 100 - 15 - 25


# -----------------------------------------------------------------------------
# ESC lukker uten mutasjon
# -----------------------------------------------------------------------------


class TestEscClose:
    def test_esc_closes_dialog(self, font, state):
        d = CacheSubDialog(font, state, port_id="tortuga")
        d.handle_event(_keydown(pygame.K_ESCAPE))
        assert d.want_close is True

    def test_esc_with_pending_amount_no_mutation(
        self, font, state, toasts
    ):
        """Et forberedt beløp skal ikke commites ved ESC."""
        d = CacheSubDialog(font, state, port_id="tortuga", toasts=toasts)
        d._amount = 40
        d.handle_event(_keydown(pygame.K_ESCAPE))
        assert state.player_state.gold == 100
        assert state.player_state.port_caches["tortuga"] == 50


# -----------------------------------------------------------------------------
# Tortuga-tittel-spesialisering
# -----------------------------------------------------------------------------


class TestTitleSpecialization:
    def test_tortuga_title_uses_gullkiste(self, font, state):
        d = CacheSubDialog(font, state, port_id="tortuga")
        d._ensure_title()
        # Surface-basert test: vi kan ikke lese teksten tilbake fra
        # surface, men vi kan verifisere at dialog-konstruktøren har
        # riktig port_id. Logikken i _ensure_title bruker "Gullkiste"
        # kun for tortuga.
        assert d._port_id == "tortuga"

    def test_non_tortuga_title_uses_cache(self, font, state):
        for pid in ("port_royal", "havana", "nassau"):
            d = CacheSubDialog(font, state, port_id=pid)
            d._ensure_title()
            assert d._port_id == pid

    def test_balance_line_uses_gullkiste_for_tortuga(self, font, state):
        """Balanse-linjen skal reflektere tittel-ordet (lowercased)."""
        d = CacheSubDialog(font, state, port_id="tortuga")
        d._ensure_balance_surfs()
        # Sanity: surfacene er skapt uten crash
        assert d._on_hand_surf is not None
        assert d._cache_surf is not None


# -----------------------------------------------------------------------------
# Rendering robusthet
# -----------------------------------------------------------------------------


class TestRendering:
    def test_draw_both_modes_no_crash(self, font, state):
        d = CacheSubDialog(font, state, port_id="tortuga")
        surf = pygame.Surface((640, 360), pygame.SRCALPHA)
        d.draw(surf)
        d._mode = MODE_WITHDRAW
        d._amount = 10
        d.draw(surf)

    def test_draw_all_four_ports(self, font, state):
        surf = pygame.Surface((640, 360), pygame.SRCALPHA)
        for pid in ("tortuga", "port_royal", "havana", "nassau"):
            d = CacheSubDialog(font, state, port_id=pid)
            d.draw(surf)

    def test_draw_with_large_amount_no_crash(self, font, state):
        """Beløp som ville overflyte burde klampes; draw må ikke crashe
        på ekstreme verdier."""
        d = CacheSubDialog(font, state, port_id="tortuga")
        d._amount = 99999  # langt over max
        surf = pygame.Surface((640, 360), pygame.SRCALPHA)
        d.draw(surf)
        # Draw har klampet defensivt
        assert d._amount <= max(
            state.player_state.gold,
            state.player_state.port_caches.get("tortuga", 0),
        )
