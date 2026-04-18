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
"""

from __future__ import annotations

import random

import pygame

import constants
from scenes.base_scene import BaseScene
from systems.parallax import Camera, ParallaxLayer, ParallaxRenderer, required_layer_width


# Transparent colorkey-farge (skal aldri vises, brukes kun for tomme lag).
_COLORKEY_MAGENTA = (255, 0, 255)


def _build_sky_gradient(width: int, height: int, horizon_y: int) -> pygame.Surface:
    """Vertikal gradient fra himmel-dyp topp til horisont, sjø-dyp nedenfor."""
    surf = pygame.Surface((width, height)).convert()
    # Himmel: interpoler i to trinn for en mykere overgang
    for y in range(horizon_y):
        t = y / horizon_y
        if t < 0.6:
            k = t / 0.6
            a, b = constants.COLOR_SKY_DEEP, constants.COLOR_SKY_MID
        else:
            k = (t - 0.6) / 0.4
            a, b = constants.COLOR_SKY_MID, constants.COLOR_SKY_HORIZON
        r = int(a[0] * (1 - k) + b[0] * k)
        g = int(a[1] * (1 - k) + b[1] * k)
        bl = int(a[2] * (1 - k) + b[2] * k)
        pygame.draw.line(surf, (r, g, bl), (0, y), (width - 1, y))
    # Sjø-bånd under horisonten – mørk indigo
    pygame.draw.rect(
        surf,
        constants.COLOR_SEA_DEEP,
        (0, horizon_y, width, height - horizon_y),
    )
    return surf


def _bake_stars(surf: pygame.Surface, horizon_y: int, seed: int = 42) -> None:
    """Streng stjerner i øvre del av himmelen (deterministisk via seed)."""
    rng = random.Random(seed)
    width = surf.get_width()
    for _ in range(14):
        x = rng.randint(4, width - 5)
        y = rng.randint(4, horizon_y - 30)
        radius = rng.choice([1, 1, 1, 2])
        pygame.draw.circle(surf, constants.COLOR_MOON_CORE, (x, y), radius)


def _bake_distant_islands(surf: pygame.Surface, horizon_y: int) -> None:
    """Bølget silhuett som antyder fjerne øyer rett over horisontlinjen."""
    width = surf.get_width()
    # Lag en bølget polygon i mørk stein-tone
    points = [(0, horizon_y)]
    x = 0
    rng = random.Random(7)
    while x <= width:
        x += rng.randint(40, 90)
        dip = rng.randint(-14, -4)  # opp over horisonten
        points.append((min(x, width), horizon_y + dip))
    points.append((width, horizon_y))
    points.append((width, horizon_y + 6))
    points.append((0, horizon_y + 6))
    pygame.draw.polygon(surf, constants.COLOR_STONE_DARKEST, points)


def _bake_moon(surf: pygame.Surface, cx: int, cy: int) -> None:
    """Mål og bak halo-ringer med fallende lysstyrke + månekjerne.

    Ingen per-pixel alpha – kun konsentriske pygame.draw.circle-kall som
    overskriver hverandre. Dette bakes inn i bakgrunnen ved scene-init.
    """
    halo_rings = [
        (42, (22, 26, 62)),    # svakt lysere enn sky_mid
        (34, (36, 44, 92)),
        (26, (70, 78, 130)),
        (20, (140, 138, 160)),
        (14, constants.COLOR_MOON_HALO),
        (11, constants.COLOR_MOON_CORE),
    ]
    for r, color in halo_rings:
        pygame.draw.circle(surf, color, (cx, cy), r)
    # Et par diskrete "krater"-prikker
    pygame.draw.circle(surf, constants.COLOR_MOON_HALO, (cx + 3, cy - 3), 2)
    pygame.draw.circle(surf, constants.COLOR_MOON_HALO, (cx - 4, cy + 3), 1)


def _build_background_layer() -> pygame.Surface:
    """Pre-render hele bakgrunnslaget (sky + måne + stjerner + øyer)."""
    speed = 0.2
    width = required_layer_width(constants.WORLD_WIDTH, constants.RENDER_WIDTH, speed)
    height = constants.RENDER_HEIGHT
    horizon_y = int(height * 0.58)  # ≈ 209 (matcher SVG-referansens horisont)

    surf = _build_sky_gradient(width, height, horizon_y)
    _bake_stars(surf, horizon_y, seed=42)
    _bake_distant_islands(surf, horizon_y)
    # Måne plassert rundt 70% av bakgrunnens bredde (høyre for senter) ved y=75
    moon_cx = int(width * 0.70)
    moon_cy = 75
    _bake_moon(surf, moon_cx, moon_cy)
    return surf


def _build_empty_layer(speed: float) -> pygame.Surface:
    """Tom, transparent surface på riktig bredde for lagets parallax-speed."""
    width = required_layer_width(constants.WORLD_WIDTH, constants.RENDER_WIDTH, speed)
    surf = pygame.Surface((width, constants.RENDER_HEIGHT)).convert()
    surf.fill(_COLORKEY_MAGENTA)
    surf.set_colorkey(_COLORKEY_MAGENTA)
    return surf


class ParallaxTestScene(BaseScene):
    """Kameratest for 3-lags parallax. A/D beveger kameraet."""

    def __init__(self, font: pygame.font.Font) -> None:
        super().__init__()
        self._camera = Camera(constants.WORLD_WIDTH, constants.RENDER_WIDTH)
        self._renderer = ParallaxRenderer(
            [
                ParallaxLayer(_build_background_layer(), speed=0.2),
                ParallaxLayer(_build_empty_layer(1.0), speed=1.0),
                ParallaxLayer(_build_empty_layer(1.3), speed=1.3),
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
