"""Tester for `ui.dialog_overlay` base class og Fase 3 C3-2 stub-dialoger.

Base class kontrakt:
- Panel-bygging med riktige dimensjoner og farger
- ESC setter want_close
- Up/Down navigasjon med wrap-around
- Ingen navigasjon ved n_entries=0 (ESC konsumeres fortsatt)
- balance tick_id cache-invalidation via _balance_changed()

Stub-dialoger (TavernDayDialog, TavernNightDialog, HarbormasterDialog,
CacheSubDialog, ScoreOverlay):
- Instansierer uten feil
- `_build_entries()` returnerer []
- `draw()` kjører uten crash
- ESC setter want_close
"""

from __future__ import annotations

import pygame
import pytest

import constants
from state import GameState
from systems import balance as bal
from ui.cache_dialog import CacheSubDialog
from ui.dialog_overlay import (
    DEFAULT_PANEL_H,
    DEFAULT_PANEL_W,
    DialogOverlay,
)
from ui.harbormaster_dialog import HarbormasterDialog
from ui.score_overlay import ScoreOverlay
from ui.tavern_dialog import TavernDayDialog, TavernNightDialog


@pytest.fixture(scope="module", autouse=True)
def _pygame_setup():
    """Initialiser pygame display og font for hele modulen."""
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
def game_state() -> GameState:
    return GameState()


def _keydown(key: int, mod: int = 0) -> pygame.event.Event:
    return pygame.event.Event(pygame.KEYDOWN, {"key": key, "mod": mod})


# -----------------------------------------------------------------------------
# Base class: panel
# -----------------------------------------------------------------------------


class TestPanelConstruction:
    def test_default_panel_size(self, font):
        d = DialogOverlay(font)
        # Fase 2.6: panel skalert fra 480×240 til 360×180 for 480×270-render.
        assert d._panel_w == DEFAULT_PANEL_W == 360
        assert d._panel_h == DEFAULT_PANEL_H == 180
        assert d._panel_surface.get_size() == (360, 180)

    def test_custom_panel_size(self, font):
        d = DialogOverlay(font, panel_w=320, panel_h=180)
        assert d._panel_w == 320
        assert d._panel_h == 180
        assert d._panel_surface.get_size() == (320, 180)

    def test_panel_centered_on_render_surface(self, font):
        d = DialogOverlay(font)
        # Fase 2.6: 480-360 = 120, halv = 60. 270-180 = 90, halv = 45.
        assert d._panel_x == 60
        assert d._panel_y == 45

    def test_panel_has_stone_dark_fill(self, font):
        panel = DialogOverlay.build_panel_surface(360, 180)
        # Innenfor rammen — pixel på (50, 50) skal være stone-dark-rødaktig
        inner_pixel = panel.get_at((50, 50))
        # COLOR_STONE_DARK = (31, 37, 56) med alpha 242
        assert inner_pixel[0] == 31
        assert inner_pixel[1] == 37
        assert inner_pixel[2] == 56
        assert inner_pixel[3] == 242

    def test_panel_has_stone_lit_outer_border(self, font):
        panel = DialogOverlay.build_panel_surface(360, 180)
        # Pixel på (0, 0) er yttre rammen — COLOR_STONE_LIT = (107, 139, 199)
        border = panel.get_at((0, 0))
        assert border[0] == 107
        assert border[1] == 139
        assert border[2] == 199

    def test_draw_panel_blits_at_computed_position(self, font):
        d = DialogOverlay(font)
        import constants
        surf = pygame.Surface(
            (constants.RENDER_WIDTH, constants.RENDER_HEIGHT), pygame.SRCALPHA,
        )
        surf.fill((0, 0, 0, 0))
        d._draw_panel(surf)
        # Fase 2.6: panel-hjørne (60, 45) skal nå inneholde stone-lit ramme.
        pixel = surf.get_at((60, 45))
        assert pixel[0] == 107  # stone_lit


# -----------------------------------------------------------------------------
# Base class: navigation
# -----------------------------------------------------------------------------


class TestNavigation:
    def test_esc_sets_want_close(self, font):
        d = DialogOverlay(font)
        assert d.want_close is False
        consumed = d._handle_navigation(_keydown(pygame.K_ESCAPE), n_entries=3)
        assert consumed is True
        assert d.want_close is True

    def test_down_advances_selected(self, font):
        d = DialogOverlay(font)
        assert d.selected == 0
        d._handle_navigation(_keydown(pygame.K_DOWN), n_entries=3)
        assert d.selected == 1
        d._handle_navigation(_keydown(pygame.K_s), n_entries=3)
        assert d.selected == 2

    def test_up_decrements_selected(self, font):
        d = DialogOverlay(font)
        d._selected = 1
        d._handle_navigation(_keydown(pygame.K_UP), n_entries=3)
        assert d.selected == 0

    def test_up_wraps_to_last(self, font):
        d = DialogOverlay(font)
        d._selected = 0
        d._handle_navigation(_keydown(pygame.K_UP), n_entries=3)
        assert d.selected == 2

    def test_down_wraps_to_first(self, font):
        d = DialogOverlay(font)
        d._selected = 2
        d._handle_navigation(_keydown(pygame.K_DOWN), n_entries=3)
        assert d.selected == 0

    def test_zero_entries_ignores_up_down(self, font):
        d = DialogOverlay(font)
        consumed = d._handle_navigation(_keydown(pygame.K_DOWN), n_entries=0)
        assert consumed is False
        assert d.selected == 0

    def test_zero_entries_still_accepts_esc(self, font):
        d = DialogOverlay(font)
        consumed = d._handle_navigation(_keydown(pygame.K_ESCAPE), n_entries=0)
        assert consumed is True
        assert d.want_close is True

    def test_non_keydown_event_not_consumed(self, font):
        d = DialogOverlay(font)
        ev = pygame.event.Event(pygame.KEYUP, {"key": pygame.K_DOWN, "mod": 0})
        consumed = d._handle_navigation(ev, n_entries=3)
        assert consumed is False

    def test_unknown_key_not_consumed(self, font):
        d = DialogOverlay(font)
        consumed = d._handle_navigation(_keydown(pygame.K_x), n_entries=3)
        assert consumed is False

    def test_selected_persistent_across_calls(self, font):
        """Seleksjon bevares mellom events og draw-kall."""
        d = DialogOverlay(font)
        d._handle_navigation(_keydown(pygame.K_DOWN), n_entries=5)
        d._handle_navigation(_keydown(pygame.K_DOWN), n_entries=5)
        d._handle_navigation(_keydown(pygame.K_DOWN), n_entries=5)
        assert d.selected == 3


# -----------------------------------------------------------------------------
# Base class: balance hot-reload cache-invalidation
# -----------------------------------------------------------------------------


class TestBalanceHotReload:
    def test_balance_changed_false_initially(self, font):
        d = DialogOverlay(font)
        # Right after construction: tick_id matcher sist sett
        assert d._balance_changed() is False

    def test_balance_changed_after_reload_returns_true_once(self, font, tmp_path):
        import json
        bal._reset_for_tests()
        try:
            path = tmp_path / "balance.json"
            # Bygg minimal v2-payload via test_balance helper? Enklere:
            # les data/balance.json fra prosjekt-rota og bruk den som base.
            import os
            from pathlib import Path as _P
            root = _P(__file__).resolve().parent.parent
            src = root / "data" / "balance.json"
            content = src.read_text(encoding="utf-8")
            path.write_text(content, encoding="utf-8")
            bal.init(str(path))

            d = DialogOverlay(font)
            assert d._balance_changed() is False

            # Trigger reload med en endring
            data = json.loads(content)
            data["economy"]["transaction_fee"] += 1
            path.write_text(json.dumps(data), encoding="utf-8")
            result = bal.reload()
            assert result.success is True

            # Første kall etter reload → True
            assert d._balance_changed() is True
            # Andre kall → False (tick_id har blitt oppdatert)
            assert d._balance_changed() is False
        finally:
            bal._reset_for_tests()
            # Re-init fra prosjekt-defaults for resten av testene i modulen
            from pathlib import Path as _P
            root = _P(__file__).resolve().parent.parent
            bal.init(str(root / "data" / "balance.json"))

    def test_multiple_dialogs_track_tick_id_independently(self, font, tmp_path):
        """To dialoger opprettet før reload: begge ser True første gang
        etter reload, så False."""
        import json
        bal._reset_for_tests()
        try:
            from pathlib import Path as _P
            root = _P(__file__).resolve().parent.parent
            src = root / "data" / "balance.json"
            content = src.read_text(encoding="utf-8")
            path = tmp_path / "balance.json"
            path.write_text(content, encoding="utf-8")
            bal.init(str(path))

            d1 = DialogOverlay(font)
            d2 = DialogOverlay(font)

            # Reload
            data = json.loads(content)
            data["economy"]["transaction_fee"] += 5
            path.write_text(json.dumps(data), encoding="utf-8")
            bal.reload()

            # Begge ser reload én gang
            assert d1._balance_changed() is True
            assert d2._balance_changed() is True
            assert d1._balance_changed() is False
            assert d2._balance_changed() is False
        finally:
            bal._reset_for_tests()
            from pathlib import Path as _P
            root = _P(__file__).resolve().parent.parent
            bal.init(str(root / "data" / "balance.json"))


# -----------------------------------------------------------------------------
# C3-10.5 harmoniserte helpers: _push_toast + _try_deduct_gold
# -----------------------------------------------------------------------------


class TestPushToastBase:
    """_push_toast flyttet til DialogOverlay-base fra duplikerte lokale
    helpere i Tavern/Harbormaster/Cache."""

    def test_none_toasts_is_noop(self, font):
        """DialogOverlay uten toasts-parameter skal ikke crashe."""
        d = DialogOverlay(font)
        # Skulle ikke crashe; ingen observerbar effekt
        d._push_toast("hei", constants.COLOR_LANTERN)
        assert d._toasts is None

    def test_toasts_configured_via_init(self, font):
        from ui.toast import ToastQueue
        toasts = ToastQueue(baseline_y=340, center_x=320)
        d = DialogOverlay(font, toasts=toasts)
        assert d._toasts is toasts

    def test_push_with_toasts_appends(self, font):
        from ui.toast import ToastQueue
        toasts = ToastQueue(baseline_y=340, center_x=320)
        d = DialogOverlay(font, toasts=toasts)
        assert toasts.count == 0
        d._push_toast("test", constants.COLOR_LANTERN)
        assert toasts.count == 1

    def test_push_default_duration(self, font):
        """Default duration = 2.0 (matcher tidligere eksplisitte
        kall fra subklassene)."""
        from ui.toast import ToastQueue
        toasts = ToastQueue(baseline_y=340, center_x=320)
        d = DialogOverlay(font, toasts=toasts)
        d._push_toast("test", constants.COLOR_LANTERN)
        # Hent siste toast — ToastQueue har ikke pek-API, men
        # duration-persistence sikres via duration-parameter.
        # Her verifiserer vi kun at kallet ikke krasjer med default.

    def test_push_custom_duration(self, font):
        from ui.toast import ToastQueue
        toasts = ToastQueue(baseline_y=340, center_x=320)
        d = DialogOverlay(font, toasts=toasts)
        d._push_toast("test", constants.COLOR_LANTERN, duration=5.0)
        assert toasts.count == 1


class TestTryDeductGoldBase:
    """_try_deduct_gold konsoliderer gold-guard-mønsteret fra 6
    tavern-handlere. Semantikk: True + trekk ved suksess, False +
    feilhint-toast ved insufficient."""

    def _dialog_with_state(self, font, gold: int = 100):
        """Helper: bygg DialogOverlay med state og toasts."""
        from ui.toast import ToastQueue
        toasts = ToastQueue(baseline_y=340, center_x=320)
        d = DialogOverlay(font, toasts=toasts)
        d._state = GameState()
        d._state.player_state.gold = gold
        return d, toasts

    def test_returns_true_when_gold_sufficient(self, font):
        d, _ = self._dialog_with_state(font, gold=100)
        result = d._try_deduct_gold(50)
        assert result is True

    def test_deducts_gold_on_success(self, font):
        d, _ = self._dialog_with_state(font, gold=100)
        d._try_deduct_gold(30)
        assert d._state.player_state.gold == 70

    def test_returns_false_when_insufficient(self, font):
        d, _ = self._dialog_with_state(font, gold=10)
        result = d._try_deduct_gold(50)
        assert result is False

    def test_no_deduction_on_failure(self, font):
        d, _ = self._dialog_with_state(font, gold=10)
        d._try_deduct_gold(50)
        assert d._state.player_state.gold == 10

    def test_pushes_error_toast_on_failure(self, font):
        d, toasts = self._dialog_with_state(font, gold=10)
        assert toasts.count == 0
        d._try_deduct_gold(50)
        assert toasts.count == 1

    def test_exact_amount_succeeds(self, font):
        """Grense-tilfelle: gull == cost skal trekke til 0."""
        d, _ = self._dialog_with_state(font, gold=50)
        assert d._try_deduct_gold(50) is True
        assert d._state.player_state.gold == 0

    def test_no_state_returns_false_defensive(self, font):
        """DialogOverlay uten _state satt (feilbruk) skal returnere
        False uten å crashe."""
        d = DialogOverlay(font)
        assert d._state is None
        assert d._try_deduct_gold(50) is False

    def test_zero_cost_always_succeeds(self, font):
        """Kost = 0 → alltid OK (trekker 0)."""
        d, _ = self._dialog_with_state(font, gold=0)
        assert d._try_deduct_gold(0) is True
        assert d._state.player_state.gold == 0


# -----------------------------------------------------------------------------
# Stub dialog-klasser
# -----------------------------------------------------------------------------


class TestTavernDayDialog:
    """Sanity-tester for instansiering. Detaljert meny/rom-kjøp-adferd
    ligger i tests/test_tavern_dialog.py (C3-3)."""

    def test_instantiates(self, font, game_state):
        d = TavernDayDialog(font, game_state, port_id="tortuga")
        assert d is not None
        assert d.want_close is False

    def test_draw_no_crash(self, font, game_state):
        d = TavernDayDialog(font, game_state, port_id="tortuga")
        surf = pygame.Surface((640, 360), pygame.SRCALPHA)
        d.draw(surf)

    def test_esc_sets_want_close(self, font, game_state):
        d = TavernDayDialog(font, game_state, port_id="tortuga")
        d.handle_event(_keydown(pygame.K_ESCAPE))
        assert d.want_close is True


class TestTavernNightDialog:
    """Sanity-tester for instansiering. Detaljert adferd i test_tavern_dialog.py."""

    def test_instantiates(self, font, game_state):
        d = TavernNightDialog(font, game_state, port_id="tortuga")
        assert d is not None

    def test_draw_no_crash(self, font, game_state):
        d = TavernNightDialog(font, game_state, port_id="tortuga")
        surf = pygame.Surface((640, 360), pygame.SRCALPHA)
        d.draw(surf)

    def test_esc_sets_want_close(self, font, game_state):
        d = TavernNightDialog(font, game_state, port_id="tortuga")
        d.handle_event(_keydown(pygame.K_ESCAPE))
        assert d.want_close is True


class TestHarbormasterDialog:
    """Sanity-tester for instansiering. Detaljert fast-travel-adferd
    ligger i tests/test_harbormaster_dialog.py (C3-4)."""

    def test_instantiates(self, font, game_state):
        d = HarbormasterDialog(font, game_state, port_id="tortuga")
        assert d is not None

    def test_draw_no_crash(self, font, game_state):
        d = HarbormasterDialog(font, game_state, port_id="tortuga")
        surf = pygame.Surface((640, 360), pygame.SRCALPHA)
        d.draw(surf)

    def test_esc_sets_want_close(self, font, game_state):
        d = HarbormasterDialog(font, game_state, port_id="tortuga")
        d.handle_event(_keydown(pygame.K_ESCAPE))
        assert d.want_close is True


class TestCacheSubDialog:
    """Sanity-tester for instansiering. Detaljert deposit/withdraw-adferd
    ligger i tests/test_cache_dialog.py (C3-5)."""

    def test_instantiates(self, font, game_state):
        d = CacheSubDialog(font, game_state, port_id="tortuga")
        assert d is not None

    def test_draw_no_crash(self, font, game_state):
        d = CacheSubDialog(font, game_state, port_id="tortuga")
        surf = pygame.Surface((640, 360), pygame.SRCALPHA)
        d.draw(surf)

    def test_esc_sets_want_close(self, font, game_state):
        d = CacheSubDialog(font, game_state, port_id="tortuga")
        d.handle_event(_keydown(pygame.K_ESCAPE))
        assert d.want_close is True


class TestScoreOverlay:
    def test_instantiates_with_reason(self, font, game_state):
        """C3-12: ScoreOverlay krever `reason` — stub-default er fjernet."""
        d = ScoreOverlay(font, game_state, reason="completed")
        assert d is not None
        assert d._reason == "completed"

    def test_instantiates_with_arrested_reason(self, font, game_state):
        d = ScoreOverlay(font, game_state, reason="arrested")
        assert d._reason == "arrested"

    def test_build_entries_empty(self, font, game_state):
        d = ScoreOverlay(font, game_state, reason="completed")
        assert d._build_entries() == []

    def test_draw_no_crash(self, font, game_state):
        d = ScoreOverlay(font, game_state, reason="completed")
        surf = pygame.Surface((640, 360), pygame.SRCALPHA)
        d.draw(surf)

    def test_esc_sets_want_close(self, font, game_state):
        d = ScoreOverlay(font, game_state, reason="completed")
        d.handle_event(_keydown(pygame.K_ESCAPE))
        assert d.want_close is True

    def test_enter_sets_want_close(self, font, game_state):
        """Score-overlay har ingen navigerbare entries; Enter avslutter."""
        d = ScoreOverlay(font, game_state, reason="completed")
        d.handle_event(_keydown(pygame.K_RETURN))
        assert d.want_close is True
