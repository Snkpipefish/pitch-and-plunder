"""Tester for systems.rest + integrasjon med dialog-handlere + HUD.

Fase 3 C3-8. Pure-function-tester på rest-mutasjon, samt verifikasjon
at hver tids-kostbar handler kaller consume_for_action med riktig
timer-mengde.
"""

from __future__ import annotations

import pygame
import pytest

import constants
from state.game_state import GameState
from state.market_state import MarketState
from systems import balance as _balance
from systems import rest
from systems import save as save_module


def _state_with_rest(value: float = 1.0) -> GameState:
    s = save_module.new_game_state()
    s.player_state.rest = value
    return s


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


# -----------------------------------------------------------------------------
# consume_for_action — decay-formel
# -----------------------------------------------------------------------------


class TestConsumeForAction:
    def test_standard_1h_action_decays_default(self):
        """1.0 h handling × decay_per_action (0.05) = 0.05 decay."""
        state = _state_with_rest(1.0)
        rest.consume_for_action(state, 1.0)
        assert state.player_state.rest == pytest.approx(0.95)

    def test_quarter_hour_proportional(self):
        """0.25 h × 0.05 = 0.0125 decay."""
        state = _state_with_rest(1.0)
        rest.consume_for_action(state, 0.25)
        assert state.player_state.rest == pytest.approx(0.9875)

    def test_two_hour_action_double_decay(self):
        """2.0 h (sabotasje) × 0.05 = 0.10 decay."""
        state = _state_with_rest(1.0)
        rest.consume_for_action(state, 2.0)
        assert state.player_state.rest == pytest.approx(0.90)

    def test_20_standard_actions_reach_zero(self):
        """20 × 1h × 0.05 = 1.0 total drain → rest = 0."""
        state = _state_with_rest(1.0)
        for _ in range(20):
            rest.consume_for_action(state, 1.0)
        assert state.player_state.rest == pytest.approx(0.0)

    def test_clamp_at_zero(self):
        state = _state_with_rest(0.02)
        rest.consume_for_action(state, 5.0)  # would try to go negative
        assert state.player_state.rest == 0.0

    def test_zero_hours_noop(self):
        state = _state_with_rest(0.5)
        rest.consume_for_action(state, 0.0)
        assert state.player_state.rest == 0.5

    def test_negative_hours_noop(self):
        state = _state_with_rest(0.5)
        rest.consume_for_action(state, -1.0)
        assert state.player_state.rest == 0.5


# -----------------------------------------------------------------------------
# consume_for_voyage — sleep-at-sea-modell
# -----------------------------------------------------------------------------


class TestConsumeForVoyage:
    def test_1_day_voyage_consumes_2_effective_hours(self):
        """1 dag × 2h effektivt = 2 × 0.05 = 0.10 decay."""
        state = _state_with_rest(1.0)
        rest.consume_for_voyage(state, 1)
        assert state.player_state.rest == pytest.approx(0.90)

    def test_2_day_voyage_0_20_decay(self):
        state = _state_with_rest(1.0)
        rest.consume_for_voyage(state, 2)
        assert state.player_state.rest == pytest.approx(0.80)

    def test_5_day_voyage_half_drain(self):
        """5 dager × 2h × 0.05 = 0.50 decay."""
        state = _state_with_rest(1.0)
        rest.consume_for_voyage(state, 5)
        assert state.player_state.rest == pytest.approx(0.50)

    def test_10_day_voyage_full_drain(self):
        """Hypotetisk lang reise klampes til 0."""
        state = _state_with_rest(1.0)
        rest.consume_for_voyage(state, 10)
        assert state.player_state.rest == pytest.approx(0.0)

    def test_zero_days_noop(self):
        state = _state_with_rest(0.5)
        rest.consume_for_voyage(state, 0)
        assert state.player_state.rest == 0.5

    def test_negative_days_noop(self):
        state = _state_with_rest(0.5)
        rest.consume_for_voyage(state, -2)
        assert state.player_state.rest == 0.5


# -----------------------------------------------------------------------------
# restore — rom-kjøp
# -----------------------------------------------------------------------------


class TestRestore:
    def test_restore_from_zero(self):
        state = _state_with_rest(0.0)
        rest.restore(state)
        assert state.player_state.rest == 1.0

    def test_restore_from_half(self):
        state = _state_with_rest(0.5)
        rest.restore(state)
        assert state.player_state.rest == 1.0

    def test_restore_idempotent_at_full(self):
        state = _state_with_rest(1.0)
        rest.restore(state)
        assert state.player_state.rest == 1.0


# -----------------------------------------------------------------------------
# effective_cost — tired-penalty (pure function)
# -----------------------------------------------------------------------------


class TestEffectiveCost:
    def test_normal_rest_returns_base_hours(self):
        state = _state_with_rest(0.5)
        assert rest.effective_cost(state, 1.0) == 1.0
        assert rest.effective_cost(state, 0.25) == 0.25

    def test_rest_at_threshold_no_penalty(self):
        """rest = 0.01 (nøyaktig på grensen) → ingen penalty."""
        state = _state_with_rest(0.01)
        assert rest.effective_cost(state, 1.0) == 1.0

    def test_rest_below_threshold_doubles(self):
        """rest < 0.01 → penalty (default 2.0×)."""
        state = _state_with_rest(0.005)
        assert rest.effective_cost(state, 1.0) == 2.0
        assert rest.effective_cost(state, 0.25) == 0.5

    def test_rest_at_zero_doubles(self):
        state = _state_with_rest(0.0)
        assert rest.effective_cost(state, 2.0) == 4.0

    def test_no_state_mutation(self):
        """effective_cost er pure — rest skal ikke endres av oppslag."""
        state = _state_with_rest(0.5)
        initial_rest = state.player_state.rest
        rest.effective_cost(state, 1.0)
        assert state.player_state.rest == initial_rest


# -----------------------------------------------------------------------------
# is_exhausted
# -----------------------------------------------------------------------------


class TestIsExhausted:
    def test_full_rest_not_exhausted(self):
        state = _state_with_rest(1.0)
        assert rest.is_exhausted(state) is False

    def test_half_rest_not_exhausted(self):
        state = _state_with_rest(0.5)
        assert rest.is_exhausted(state) is False

    def test_at_threshold_not_exhausted(self):
        state = _state_with_rest(0.01)
        assert rest.is_exhausted(state) is False

    def test_below_threshold_exhausted(self):
        state = _state_with_rest(0.005)
        assert rest.is_exhausted(state) is True

    def test_zero_exhausted(self):
        state = _state_with_rest(0.0)
        assert rest.is_exhausted(state) is True


# -----------------------------------------------------------------------------
# Integrasjon: TavernDialog rom-kjøp (restore) og bek-kjøp (consume)
# -----------------------------------------------------------------------------


class TestTavernRoomPurchaseRestoresRest:
    def test_room_purchase_sets_rest_to_one(self, font):
        from ui.tavern_dialog import TavernDayDialog
        from ui.toast import ToastQueue
        state = _state_with_rest(0.3)
        state.player_state.gold = 100
        toasts = ToastQueue(baseline_y=340, center_x=320)
        d = TavernDayDialog(font, state, port_id="tortuga", toasts=toasts)
        d._selected = 0  # rom
        d.handle_event(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_RETURN, "mod": 0}))
        assert state.player_state.rest == 1.0
        assert state.player_state.gold == 90  # room_cost_gold=10


class TestTavernBekPurchaseConsumesRest:
    def test_bek_purchase_reduces_rest_by_1h_decay(self, font):
        from ui.tavern_dialog import (
            TavernDayDialog, ACTION_PITCH_LAKE_PURCHASE,
        )
        from ui.toast import ToastQueue
        state = _state_with_rest(1.0)
        state.player_state.gold = 1000
        toasts = ToastQueue(baseline_y=340, center_x=320)
        d = TavernDayDialog(font, state, port_id="tortuga", toasts=toasts)
        entries = d._build_entries()
        bek_idx = next(
            i for i, e in enumerate(entries)
            if e.action_id == ACTION_PITCH_LAKE_PURCHASE
        )
        d._selected = bek_idx
        d.handle_event(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_RETURN, "mod": 0}))
        # 1.0 h × 0.05 decay_per_action = 0.05 reduksjon
        assert state.player_state.rest == pytest.approx(0.95)

    def test_bek_purchase_insufficient_gold_no_rest_change(self, font):
        from ui.tavern_dialog import (
            TavernDayDialog, ACTION_PITCH_LAKE_PURCHASE,
        )
        from ui.toast import ToastQueue
        state = _state_with_rest(1.0)
        state.player_state.gold = 100  # < 500
        toasts = ToastQueue(baseline_y=340, center_x=320)
        d = TavernDayDialog(font, state, port_id="tortuga", toasts=toasts)
        entries = d._build_entries()
        bek_idx = next(
            i for i, e in enumerate(entries)
            if e.action_id == ACTION_PITCH_LAKE_PURCHASE
        )
        d._selected = bek_idx
        d.handle_event(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_RETURN, "mod": 0}))
        # Kjøp feilet → ingen rest-mutation
        assert state.player_state.rest == 1.0


# -----------------------------------------------------------------------------
# Integrasjon: HarbormasterDialog fast-travel
# -----------------------------------------------------------------------------


class TestHarbormasterVoyageConsumesRest:
    def test_voyage_consumes_rest_per_route_days(self, font):
        from ui.harbormaster_dialog import HarbormasterDialog, ACTION_TRAVEL_PREFIX
        from ui.toast import ToastQueue
        state = _state_with_rest(1.0)
        state.player_state.gold = 200  # nok til hvilken som helst rute
        toasts = ToastQueue(baseline_y=340, center_x=320)
        d = HarbormasterDialog(font, state, port_id="tortuga", toasts=toasts)
        entries = d._build_entries()
        # Velg port_royal (2-dagers rute fra Tortuga)
        pr_idx = next(
            i for i, e in enumerate(entries)
            if e.dest_port_id == "port_royal"
        )
        d._selected = pr_idx
        d.handle_event(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_RETURN, "mod": 0}))
        # 2 dager × 2 effektive h × 0.05 decay = 0.20
        assert state.player_state.rest == pytest.approx(0.80)

    def test_voyage_insufficient_gold_no_rest_change(self, font):
        from ui.harbormaster_dialog import HarbormasterDialog
        from ui.toast import ToastQueue
        state = _state_with_rest(1.0)
        state.player_state.gold = 5  # ikke nok
        toasts = ToastQueue(baseline_y=340, center_x=320)
        d = HarbormasterDialog(font, state, port_id="tortuga", toasts=toasts)
        entries = d._build_entries()
        pr_idx = next(
            i for i, e in enumerate(entries)
            if e.dest_port_id == "port_royal"
        )
        d._selected = pr_idx
        d.handle_event(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_RETURN, "mod": 0}))
        # Voyage feilet — ingen rest-mutation
        assert state.player_state.rest == 1.0

    def test_long_voyage_drains_more(self, font):
        from ui.harbormaster_dialog import HarbormasterDialog
        from ui.toast import ToastQueue
        state = _state_with_rest(1.0)
        state.player_state.gold = 500
        toasts = ToastQueue(baseline_y=340, center_x=320)
        d = HarbormasterDialog(font, state, port_id="tortuga", toasts=toasts)
        entries = d._build_entries()
        # Nassau er 4-dagers rute
        nassau_idx = next(
            i for i, e in enumerate(entries)
            if e.dest_port_id == "nassau"
        )
        d._selected = nassau_idx
        d.handle_event(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_RETURN, "mod": 0}))
        # 4 dager × 2h × 0.05 = 0.40 decay
        assert state.player_state.rest == pytest.approx(0.60)


# -----------------------------------------------------------------------------
# Integrasjon: CacheSubDialog commit
# -----------------------------------------------------------------------------


class TestCacheCommitConsumesRest:
    def test_deposit_commit_consumes_0_25h(self, font):
        from ui.cache_dialog import CacheSubDialog, MODE_DEPOSIT
        from ui.toast import ToastQueue
        state = _state_with_rest(1.0)
        state.player_state.gold = 100
        state.player_state.port_caches["tortuga"] = 0
        toasts = ToastQueue(baseline_y=340, center_x=320)
        d = CacheSubDialog(font, state, port_id="tortuga", toasts=toasts)
        d._mode = MODE_DEPOSIT
        d._amount = 30
        d.handle_event(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_RETURN, "mod": 0}))
        # 0.25 h × 0.05 = 0.0125 decay
        assert state.player_state.rest == pytest.approx(0.9875)

    def test_zero_amount_no_rest_change(self, font):
        from ui.cache_dialog import CacheSubDialog
        from ui.toast import ToastQueue
        state = _state_with_rest(1.0)
        state.player_state.gold = 100
        toasts = ToastQueue(baseline_y=340, center_x=320)
        d = CacheSubDialog(font, state, port_id="tortuga", toasts=toasts)
        assert d._amount == 0
        d.handle_event(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_RETURN, "mod": 0}))
        # Zero-amount commit er no-op → ingen rest-mutation
        assert state.player_state.rest == 1.0

    def test_multiple_commits_accumulate_decay(self, font):
        from ui.cache_dialog import CacheSubDialog, MODE_DEPOSIT
        from ui.toast import ToastQueue
        state = _state_with_rest(1.0)
        state.player_state.gold = 100
        state.player_state.port_caches["tortuga"] = 0
        toasts = ToastQueue(baseline_y=340, center_x=320)
        d = CacheSubDialog(font, state, port_id="tortuga", toasts=toasts)
        # 3 × deposit commit = 3 × 0.0125 = 0.0375 decay
        for _ in range(3):
            d._mode = MODE_DEPOSIT
            d._amount = 10
            d.handle_event(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_RETURN, "mod": 0}))
        assert state.player_state.rest == pytest.approx(1.0 - 3 * 0.0125)


# -----------------------------------------------------------------------------
# HUD-fargebånd
# -----------------------------------------------------------------------------


class TestHudRestColorBands:
    def test_100pct_stone_bright(self, font):
        from ui.hud import Hud
        assert Hud._rest_color(100) == constants.COLOR_STONE_BRIGHT

    def test_50pct_stone_bright(self, font):
        from ui.hud import Hud
        assert Hud._rest_color(50) == constants.COLOR_STONE_BRIGHT

    def test_49pct_lantern(self, font):
        from ui.hud import Hud
        assert Hud._rest_color(49) == constants.COLOR_LANTERN

    def test_20pct_lantern(self, font):
        from ui.hud import Hud
        assert Hud._rest_color(20) == constants.COLOR_LANTERN

    def test_19pct_ember(self, font):
        from ui.hud import Hud
        assert Hud._rest_color(19) == constants.COLOR_EMBER

    def test_1pct_ember(self, font):
        from ui.hud import Hud
        assert Hud._rest_color(1) == constants.COLOR_EMBER

    def test_0pct_flame(self, font):
        from ui.hud import Hud
        assert Hud._rest_color(0) == constants.COLOR_FLAME


class TestHudRestCache:
    def _hud(self, font):
        from ui.hud import Hud
        return Hud(font, "Tortuga", 100, 1)

    def test_initial_value_is_100pct(self, font):
        hud = self._hud(font)
        assert hud._rest_pct == 100

    def test_setter_noop_for_same_pct(self, font):
        hud = self._hud(font)
        hud.set_rest(0.5)
        surf_before = hud._rest_surf
        hud.set_rest(0.504)  # samme int-pct (50)
        assert hud._rest_surf is surf_before

    def test_setter_rebuilds_on_pct_change(self, font):
        hud = self._hud(font)
        hud.set_rest(0.5)
        surf_before = hud._rest_surf
        hud.set_rest(0.49)  # 49% < 50% → band-bytte
        assert hud._rest_surf is not surf_before

    def test_setter_clamps_to_0_100(self, font):
        hud = self._hud(font)
        hud.set_rest(1.5)  # klamp til 100%
        assert hud._rest_pct == 100
        hud.set_rest(-0.5)  # klamp til 0%
        assert hud._rest_pct == 0


class TestHudDrawWithRest:
    def test_draw_no_crash_with_rest_linje(self, font):
        from ui.hud import Hud
        hud = Hud(font, "Tortuga", 100, 1)
        hud.set_rest(0.5)
        surf = pygame.Surface((640, 360))
        hud.draw(surf)

    def test_draw_with_all_lines_visible(self, font):
        from ui.hud import Hud
        hud = Hud(
            font, "Tortuga", 100, 1,
            pitch_per_day=2, pitch_upkeep=8, pitch_halted=False,
        )
        hud.set_suspicion(50)
        hud.set_rest(0.3)
        surf = pygame.Surface((640, 360))
        hud.draw(surf)

    def test_draw_exhausted_rest(self, font):
        from ui.hud import Hud
        hud = Hud(font, "Tortuga", 100, 1)
        hud.set_rest(0.0)
        surf = pygame.Surface((640, 360))
        hud.draw(surf)
