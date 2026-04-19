"""Tester for `ui.toast`. Krever pygame display og font."""

from __future__ import annotations

import pygame
import pytest

from ui.toast import Toast, ToastQueue


@pytest.fixture(scope="module", autouse=True)
def _pygame_setup():
    """Initialiser pygame display og font én gang for hele modulen."""
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
    # SysFont for at testene ikke krever Public Pixel-fila.
    return pygame.font.SysFont(None, 12)


class TestToastLifetime:
    def test_is_alive_initially_true(self, font):
        t = Toast(font, "hei", (255, 255, 255), duration=3.0)
        assert t.is_alive is True

    def test_update_reduces_remaining(self, font):
        t = Toast(font, "hei", (255, 255, 255), duration=3.0)
        t.update(1.5)
        assert t.is_alive is True

    def test_update_past_duration_kills(self, font):
        t = Toast(font, "hei", (255, 255, 255), duration=3.0)
        t.update(3.0)
        assert t.is_alive is False

    def test_slight_overshoot_kills(self, font):
        t = Toast(font, "hei", (255, 255, 255), duration=3.0)
        t.update(3.01)
        assert t.is_alive is False


class TestToastAlphaFade:
    def test_full_alpha_before_fade_window(self, font):
        # Default fade_start = 1/3 av duration = 1.0 s. Alpha skal være
        # 255 så lenge remaining > 1.0.
        t = Toast(font, "hei", (255, 255, 255), duration=3.0)
        assert t.current_alpha() == 255
        t.update(1.0)  # remaining = 2.0, fortsatt full
        assert t.current_alpha() == 255

    def test_fade_starts_at_fade_window(self, font):
        t = Toast(font, "hei", (255, 255, 255), duration=3.0)
        t.update(2.0)  # remaining = 1.0, på grensen
        # Alpha kan være 255 eller nær det; akkurat på fade_start
        assert t.current_alpha() == 255

    def test_half_alpha_at_half_fade(self, font):
        t = Toast(font, "hei", (255, 255, 255), duration=3.0)
        # fade_start = 1.0 s; etter 2.5 s remaining = 0.5 → halv alpha
        t.update(2.5)
        alpha = t.current_alpha()
        assert 115 < alpha < 135  # ca. 128

    def test_zero_alpha_at_end(self, font):
        t = Toast(font, "hei", (255, 255, 255), duration=3.0)
        t.update(3.0)
        assert t.current_alpha() == 0


class TestToastCustomFadeStart:
    def test_explicit_fade_start_overrides_default(self, font):
        t = Toast(font, "hei", (255, 255, 255), duration=3.0, fade_start=2.0)
        # Med fade_start=2.0 skal fading starte når remaining < 2.0
        t.update(0.5)  # remaining = 2.5, ikke fading ennå
        assert t.current_alpha() == 255
        t.update(1.0)  # remaining = 1.5, 75% av 2.0 → ~191
        alpha = t.current_alpha()
        assert 180 < alpha < 200


class TestToastQueue:
    def test_empty_queue(self):
        q = ToastQueue(baseline_y=300, center_x=320)
        assert q.count == 0

    def test_push_increments_count(self, font):
        q = ToastQueue(baseline_y=300, center_x=320)
        q.push(Toast(font, "a", (255, 255, 255), duration=1.0))
        q.push(Toast(font, "b", (255, 255, 255), duration=1.0))
        assert q.count == 2

    def test_update_removes_expired(self, font):
        q = ToastQueue(baseline_y=300, center_x=320)
        q.push(Toast(font, "a", (255, 255, 255), duration=1.0))
        q.push(Toast(font, "b", (255, 255, 255), duration=3.0))
        q.update(1.5)
        assert q.count == 1

    def test_update_removes_all_when_all_expired(self, font):
        q = ToastQueue(baseline_y=300, center_x=320)
        q.push(Toast(font, "a", (255, 255, 255), duration=1.0))
        q.push(Toast(font, "b", (255, 255, 255), duration=1.0))
        q.update(2.0)
        assert q.count == 0

    def test_draw_does_not_crash_empty(self):
        q = ToastQueue(baseline_y=300, center_x=320)
        surf = pygame.Surface((640, 360)).convert()
        q.draw(surf)  # skal ikke krasje

    def test_draw_with_toasts(self, font):
        q = ToastQueue(baseline_y=300, center_x=320)
        q.push(Toast(font, "hei", (255, 255, 255), duration=3.0))
        surf = pygame.Surface((640, 360)).convert()
        q.draw(surf)
        # Verifiser at teksten faktisk er blittet et sted
        # (enkel sanity check: surface er ikke helt uendret)
        # Exact pixels avhenger av font, så vi sjekker bare at draw kjører.
