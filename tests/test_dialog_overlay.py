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
        assert d._panel_w == DEFAULT_PANEL_W == 480
        assert d._panel_h == DEFAULT_PANEL_H == 240
        assert d._panel_surface.get_size() == (480, 240)

    def test_custom_panel_size(self, font):
        d = DialogOverlay(font, panel_w=320, panel_h=180)
        assert d._panel_w == 320
        assert d._panel_h == 180
        assert d._panel_surface.get_size() == (320, 180)

    def test_panel_centered_on_render_surface(self, font):
        d = DialogOverlay(font)
        # 640-480 = 160, halv = 80. 360-240 = 120, halv = 60.
        assert d._panel_x == 80
        assert d._panel_y == 60

    def test_panel_has_stone_dark_fill(self, font):
        panel = DialogOverlay.build_panel_surface(480, 240)
        # Innenfor rammen — pixel på (50, 50) skal være stone-dark-rødaktig
        inner_pixel = panel.get_at((50, 50))
        # COLOR_STONE_DARK = (31, 37, 56) med alpha 242
        assert inner_pixel[0] == 31
        assert inner_pixel[1] == 37
        assert inner_pixel[2] == 56
        assert inner_pixel[3] == 242

    def test_panel_has_stone_lit_outer_border(self, font):
        panel = DialogOverlay.build_panel_surface(480, 240)
        # Pixel på (0, 0) er yttre rammen — COLOR_STONE_LIT = (107, 139, 199)
        border = panel.get_at((0, 0))
        assert border[0] == 107
        assert border[1] == 139
        assert border[2] == 199

    def test_draw_panel_blits_at_computed_position(self, font):
        d = DialogOverlay(font)
        surf = pygame.Surface((640, 360), pygame.SRCALPHA)
        surf.fill((0, 0, 0, 0))
        d._draw_panel(surf)
        # Panel-hjørne (80, 60) skal nå inneholde stone-lit ramme
        pixel = surf.get_at((80, 60))
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
    def test_instantiates(self, font, game_state):
        d = HarbormasterDialog(font, game_state, port_id="tortuga")
        assert d is not None

    def test_build_entries_empty(self, font, game_state):
        d = HarbormasterDialog(font, game_state, port_id="tortuga")
        assert d._build_entries() == []

    def test_draw_no_crash(self, font, game_state):
        d = HarbormasterDialog(font, game_state, port_id="tortuga")
        surf = pygame.Surface((640, 360), pygame.SRCALPHA)
        d.draw(surf)

    def test_esc_sets_want_close(self, font, game_state):
        d = HarbormasterDialog(font, game_state, port_id="tortuga")
        d.handle_event(_keydown(pygame.K_ESCAPE))
        assert d.want_close is True


class TestCacheSubDialog:
    def test_instantiates(self, font, game_state):
        d = CacheSubDialog(font, game_state, port_id="tortuga")
        assert d is not None

    def test_build_entries_empty(self, font, game_state):
        d = CacheSubDialog(font, game_state, port_id="havana")
        assert d._build_entries() == []

    def test_draw_no_crash(self, font, game_state):
        d = CacheSubDialog(font, game_state, port_id="tortuga")
        surf = pygame.Surface((640, 360), pygame.SRCALPHA)
        d.draw(surf)


class TestScoreOverlay:
    def test_instantiates_with_default_cause(self, font, game_state):
        d = ScoreOverlay(font, game_state)
        assert d is not None
        assert d._cause == "day_100"

    def test_instantiates_with_custom_cause(self, font, game_state):
        d = ScoreOverlay(font, game_state, cause="arrest")
        assert d._cause == "arrest"

    def test_build_entries_empty(self, font, game_state):
        d = ScoreOverlay(font, game_state)
        assert d._build_entries() == []

    def test_draw_no_crash(self, font, game_state):
        d = ScoreOverlay(font, game_state)
        surf = pygame.Surface((640, 360), pygame.SRCALPHA)
        d.draw(surf)

    def test_esc_sets_want_close(self, font, game_state):
        d = ScoreOverlay(font, game_state)
        d.handle_event(_keydown(pygame.K_ESCAPE))
        assert d.want_close is True

    def test_enter_sets_want_close(self, font, game_state):
        """Score-overlay har ingen navigerbare entries; Enter avslutter."""
        d = ScoreOverlay(font, game_state)
        d.handle_event(_keydown(pygame.K_RETURN))
        assert d.want_close is True
