"""Test-scene for parallax-systemet (Commit 3).

Kun bakgrunnslaget har innhold:
- Himmel-gradient (COLOR_SKY_DEEP → COLOR_SKY_MID → COLOR_SKY_HORIZON)
- 14 strødde stjerner
- Fjerne øyer som bølget silhuett
- Månen med bakte halo-ringer

Gameplay-laget og forgrunns-laget er tomme transparente surfaces i Commit 3;
de fylles ut i Commit 4 (bygninger, spiller) og Commit 8 (forgrunns-props).

A/D flytter kameraet. Månen drifter svakt (speed 0.2) mens spilleren
beveger seg fra ende til ende av verden.

Bake-funksjonene bor i `scenes/parallax_backdrops.py` slik at både denne
scenen og produksjons-scenen kan bruke dem uten kryss-import.
"""

from __future__ import annotations

import pygame

import constants
from scenes.base_scene import BaseScene
from scenes.parallax_backdrops import build_background_layer, build_empty_layer
from systems.parallax import Camera, ParallaxLayer, ParallaxRenderer


class ParallaxTestScene(BaseScene):
    """Kameratest for 3-lags parallax. A/D beveger kameraet."""

    def __init__(self, font: pygame.font.Font) -> None:
        super().__init__()
        self._camera = Camera(constants.WORLD_WIDTH, constants.RENDER_WIDTH)
        self._renderer = ParallaxRenderer(
            [
                ParallaxLayer(build_background_layer(), speed=0.2),
                ParallaxLayer(build_empty_layer(1.0), speed=1.0),
                ParallaxLayer(build_empty_layer(1.3), speed=1.3),
            ]
        )
        self._left_pressed = False
        self._right_pressed = False

        # Cached HUD-tekst (re-rendres kun når kamera-verdi endres merkbart)
        self._font = font
        self._last_cam_int = -1
        self._hud: pygame.Surface | None = None
        self._hint = font.render(
            "A/D flytter kamera  F11 fullskjerm  ESC avslutt",
            False,
            constants.COLOR_STONE_LIT,
        ).convert_alpha()
        self._hint_pos = (8, constants.RENDER_HEIGHT - 14)

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            if event.key in constants.KEY_MENU:
                self.want_quit = True
            elif event.key in constants.KEY_LEFT:
                self._left_pressed = True
            elif event.key in constants.KEY_RIGHT:
                self._right_pressed = True
        elif event.type == pygame.KEYUP:
            if event.key in constants.KEY_LEFT:
                self._left_pressed = False
            elif event.key in constants.KEY_RIGHT:
                self._right_pressed = False

    def update(self, dt: float) -> None:
        # Kameraet beveger seg selv når A/D holdes nede
        direction = (1 if self._right_pressed else 0) - (1 if self._left_pressed else 0)
        if direction != 0:
            self._camera.move(direction * constants.PLAYER_WALK_SPEED * dt)

    def _ensure_hud(self) -> None:
        cam_int = int(self._camera.x)
        if cam_int == self._last_cam_int and self._hud is not None:
            return
        self._last_cam_int = cam_int
        text = f"cam {cam_int:4d} / {int(self._camera.max_x)}"
        self._hud = self._font.render(
            text, False, constants.COLOR_MOON_CORE
        ).convert_alpha()

    def draw(self, surface: pygame.Surface) -> None:
        self._renderer.draw(surface, self._camera.x)
        self._ensure_hud()
        assert self._hud is not None
        surface.blit(self._hud, (8, 6))
        surface.blit(self._hint, self._hint_pos)
