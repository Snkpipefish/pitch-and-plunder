"""Tester for ui.event_dialog — Fase 3 C3-11."""

from __future__ import annotations

import os

import pygame
import pytest

from ui.event_dialog import EventDialog


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


def test_event_dialog_enter_closes(font) -> None:
    d = EventDialog(font=font, title="Storm", body="En voldsom storm.")
    assert d.want_close is False
    d.handle_event(_keydown(pygame.K_RETURN))
    assert d.want_close is True


def test_event_dialog_space_closes(font) -> None:
    d = EventDialog(font=font, title="Storm", body="En voldsom storm.")
    d.handle_event(_keydown(pygame.K_SPACE))
    assert d.want_close is True


def test_event_dialog_esc_closes(font) -> None:
    d = EventDialog(font=font, title="Storm", body="En voldsom storm.")
    d.handle_event(_keydown(pygame.K_ESCAPE))
    assert d.want_close is True


def test_event_dialog_ignores_other_keys(font) -> None:
    d = EventDialog(font=font, title="Storm", body="En voldsom storm.")
    d.handle_event(_keydown(pygame.K_a))
    d.handle_event(_keydown(pygame.K_UP))
    assert d.want_close is False


def test_event_dialog_draw_no_crash(font) -> None:
    d = EventDialog(
        font=font,
        title="Lengre tittel her",
        body="En lang body-tekst som bør wrappes over flere linjer i panelet.",
    )
    surface = pygame.Surface((640, 360))
    d.draw(surface)
    d.draw(surface)  # second draw uses cached surfaces
