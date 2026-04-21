"""Tester for ScoreOverlay, PauseMenuDialog, ConfirmNewGameDialog,
game_over_reason og restart-flyt — Fase 3 C3-12."""

from __future__ import annotations

import os
from pathlib import Path

import pygame
import pytest

from state import GameState
from systems import save as save_module
from ui.pause_menu_dialog import ConfirmNewGameDialog, PauseMenuDialog
from ui.score_overlay import ScoreOverlay


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


def _keydown(key: int) -> pygame.event.Event:
    return pygame.event.Event(pygame.KEYDOWN, {"key": key})


# -----------------------------------------------------------------------------
# GameState.get_game_over_reason
# -----------------------------------------------------------------------------


def test_game_over_reason_none_by_default() -> None:
    gs = GameState()
    assert gs.get_game_over_reason() is None


def test_game_over_reason_arrested_takes_priority() -> None:
    gs = GameState()
    gs.arrested = True
    gs.dead = True
    gs.death_cause = "shipwreck"
    gs.world_state.clock.day = 101
    assert gs.get_game_over_reason() == "arrested"


def test_game_over_reason_dead_before_completed() -> None:
    gs = GameState()
    gs.dead = True
    gs.death_cause = "sickness"
    gs.world_state.clock.day = 101
    assert gs.get_game_over_reason() == "dead:sickness"


def test_game_over_reason_completed_at_day_101() -> None:
    gs = GameState()
    gs.world_state.clock.day = 100
    assert gs.get_game_over_reason() is None
    gs.world_state.clock.day = 101
    assert gs.get_game_over_reason() == "completed"


# -----------------------------------------------------------------------------
# Counters
# -----------------------------------------------------------------------------


def test_counters_default_zero() -> None:
    gs = GameState()
    assert gs.player_state.total_sabotages == 0
    assert gs.player_state.total_false_rumors == 0
    assert gs.player_state.total_voyages == 0


def test_counters_persist_via_save_load(tmp_path: Path) -> None:
    state = save_module.new_game_state()
    state.player_state.total_sabotages = 3
    state.player_state.total_false_rumors = 5
    state.player_state.total_voyages = 7
    path = tmp_path / "save.json"
    assert save_module.save(state, str(path)) is True
    loaded = save_module.load(str(path))
    assert loaded is not None
    assert loaded.player_state.total_sabotages == 3
    assert loaded.player_state.total_false_rumors == 5
    assert loaded.player_state.total_voyages == 7


def test_counters_defensive_parse_missing_field(tmp_path: Path) -> None:
    """Legacy save uten tellere → defaults til 0."""
    import json
    legacy = {
        "version": 6,
        "player_state": {
            "position_x": 320.0, "gold": 300,
            "inventory": {
                "sugar": {"quantity": 0, "avg_cost": 0.0},
                "rum": {"quantity": 0, "avg_cost": 0.0},
                "tobacco": {"quantity": 0, "avg_cost": 0.0},
                "pitch": {"quantity": 0, "avg_cost": 0.0},
            },
        },
        "world_state": {
            "current_port": "tortuga",
            "clock": {"day": 1, "seconds_into_day": 0.0, "seconds_per_day": 180.0},
            "ship": {"class_id": "sloop", "name": "Sjarken", "cargo_capacity": 40},
            "voyage": None,
        },
        "economy_state": {"markets": {}, "regimes": {}, "observed": {}},
        "pitch_lake_state": {
            "home_port": "tortuga", "production_per_day": 2,
            "upkeep_per_day": 8, "pending_units": 0,
            "total_produced": 0, "last_production_day": 0,
            "purchased": True,
        },
    }
    p = tmp_path / "legacy.json"
    p.write_text(json.dumps(legacy), encoding="utf-8")
    loaded = save_module.load(str(p))
    assert loaded is not None
    assert loaded.player_state.total_sabotages == 0
    assert loaded.player_state.total_false_rumors == 0
    assert loaded.player_state.total_voyages == 0


def test_voyage_counter_increments_on_start(tmp_path: Path) -> None:
    from systems import balance as _balance
    from systems import voyage as _voy
    state = save_module.new_game_state()
    assert state.player_state.total_voyages == 0
    # Start en voyage — must have affordable route + enough gold
    # Tortuga → Port Royal = 2d/10g
    state.player_state.gold = 100
    v = _voy.start_voyage(state, _balance.get(), "tortuga", "port_royal")
    assert v is not None
    assert state.player_state.total_voyages == 1


# -----------------------------------------------------------------------------
# ScoreOverlay
# -----------------------------------------------------------------------------


def test_score_overlay_enter_sets_want_close(font) -> None:
    gs = GameState()
    d = ScoreOverlay(font, gs, reason="completed")
    d.handle_event(_keydown(pygame.K_RETURN))
    assert d.want_close is True
    assert d.want_restart is False


def test_score_overlay_esc_sets_want_close(font) -> None:
    gs = GameState()
    d = ScoreOverlay(font, gs, reason="completed")
    d.handle_event(_keydown(pygame.K_ESCAPE))
    assert d.want_close is True
    assert d.want_restart is False


def test_score_overlay_f6_sets_want_restart(font) -> None:
    gs = GameState()
    d = ScoreOverlay(font, gs, reason="completed")
    d.handle_event(_keydown(pygame.K_F6))
    assert d.want_close is True
    assert d.want_restart is True


def test_score_overlay_ignores_other_keys(font) -> None:
    gs = GameState()
    d = ScoreOverlay(font, gs, reason="completed")
    d.handle_event(_keydown(pygame.K_a))
    d.handle_event(_keydown(pygame.K_UP))
    assert d.want_close is False


def test_score_overlay_draw_all_reasons(font) -> None:
    gs = GameState()
    gs.player_state.total_sabotages = 2
    gs.player_state.total_voyages = 4
    surface = pygame.Surface((640, 360))
    for reason in ("completed", "arrested", "dead:shipwreck", "dead:sickness"):
        d = ScoreOverlay(font, gs, reason=reason)
        d.draw(surface)


# -----------------------------------------------------------------------------
# PauseMenuDialog
# -----------------------------------------------------------------------------


def test_pause_menu_continue_closes(font) -> None:
    d = PauseMenuDialog(font)
    # Default selected = 0 ("Fortsett")
    d.handle_event(_keydown(pygame.K_RETURN))
    assert d.want_close is True
    assert d.want_restart_confirm is False
    assert d.want_quit_game is False


def test_pause_menu_nytt_lop_requests_confirm(font) -> None:
    d = PauseMenuDialog(font)
    # Naviger til "Nytt løp" (indeks 1)
    d.handle_event(_keydown(pygame.K_DOWN))
    d.handle_event(_keydown(pygame.K_RETURN))
    assert d.want_close is True
    assert d.want_restart_confirm is True
    assert d.want_quit_game is False


def test_pause_menu_avslutt_quits(font) -> None:
    d = PauseMenuDialog(font)
    # Naviger til "Avslutt" (indeks 2)
    d.handle_event(_keydown(pygame.K_DOWN))
    d.handle_event(_keydown(pygame.K_DOWN))
    d.handle_event(_keydown(pygame.K_RETURN))
    assert d.want_close is True
    assert d.want_quit_game is True


def test_pause_menu_esc_closes_without_effect(font) -> None:
    d = PauseMenuDialog(font)
    d.handle_event(_keydown(pygame.K_ESCAPE))
    assert d.want_close is True
    assert d.want_restart_confirm is False
    assert d.want_quit_game is False


def test_pause_menu_navigation_wraps(font) -> None:
    d = PauseMenuDialog(font)
    assert d.selected == 0
    d.handle_event(_keydown(pygame.K_UP))  # wrap to last
    assert d.selected == 2
    d.handle_event(_keydown(pygame.K_DOWN))  # wrap to first
    assert d.selected == 0


def test_pause_menu_draw_no_crash(font) -> None:
    d = PauseMenuDialog(font)
    surface = pygame.Surface((640, 360))
    d.draw(surface)


# -----------------------------------------------------------------------------
# ConfirmNewGameDialog
# -----------------------------------------------------------------------------


def test_confirm_default_is_avbryt(font) -> None:
    """Trygg default: Enter på default velger Avbryt (ingen restart)."""
    d = ConfirmNewGameDialog(font)
    d.handle_event(_keydown(pygame.K_RETURN))
    assert d.want_close is True
    assert d.want_restart is False


def test_confirm_bekreft_triggers_restart(font) -> None:
    d = ConfirmNewGameDialog(font)
    d.handle_event(_keydown(pygame.K_DOWN))  # to Bekreft
    d.handle_event(_keydown(pygame.K_RETURN))
    assert d.want_close is True
    assert d.want_restart is True


def test_confirm_esc_closes_without_restart(font) -> None:
    d = ConfirmNewGameDialog(font)
    d.handle_event(_keydown(pygame.K_ESCAPE))
    assert d.want_close is True
    assert d.want_restart is False


def test_confirm_draw_no_crash(font) -> None:
    d = ConfirmNewGameDialog(font)
    surface = pygame.Surface((640, 360))
    d.draw(surface)


# -----------------------------------------------------------------------------
# Restart helper (main._apply_restart)
# -----------------------------------------------------------------------------


def test_apply_restart_resets_state_in_place(monkeypatch) -> None:
    """main._apply_restart muterer state-feltene in-place."""
    from dataclasses import fields
    from systems import save as _save

    # Blokker save-to-disk under testen
    monkeypatch.setattr(_save, "save", lambda *a, **kw: True)

    state = save_module.new_game_state()
    # Muter noen felter for å simulere et pågående spill
    state.player_state.gold = 9999
    state.player_state.total_voyages = 42
    state.arrested = True
    state.dead = True
    state.death_cause = "shipwreck"
    state.world_state.clock.day = 77
    old_id = id(state)

    import main
    main._apply_restart(state)

    # Samme objekt-id (in-place mutasjon)
    assert id(state) == old_id
    # Felt tilbake til new-game-defaults
    assert state.arrested is False
    assert state.dead is False
    assert state.death_cause == ""
    assert state.player_state.total_voyages == 0
    assert state.player_state.total_sabotages == 0
    assert state.world_state.clock.day == 1
    # Fresh gold fra balance.economy.starting_gold
    from systems import balance as _balance
    assert state.player_state.gold == _balance.get().economy.starting_gold
