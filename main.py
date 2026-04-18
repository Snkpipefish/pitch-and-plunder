"""Entry point for Pitch & Plunder.

Ansvar:
- Sette SDL env vars (via import av constants) FØR pygame initialiseres
- Opprette vindu med pygame.SCALED og 640x360 intern render-surface
- Blokkere unødvendige events
- Kjøre hovedløkke med Clock.tick(TARGET_FPS) (IKKE tick_busy_loop)
- Holde styr på scene-bytter
- F11 toggler fullskjerm
"""

from __future__ import annotations

import logging
import sys
from typing import Callable

import constants  # Setter env vars som MÅ være satt før pygame importeres
import pygame

from scenes.base_scene import BaseScene
from scenes.parallax_test import ParallaxTestScene


log = logging.getLogger("pitch_and_plunder")


class PlaceholderScene(BaseScene):
    """Midlertidig scene som kun fyller skjermen med himmelfargen.

    Erstattes av village-scenen i Commit 4. Finnes for å gi oss en kjørbar
    hovedløkke og noe å benchmarke mot.
    """

    def __init__(self, font: pygame.font.Font) -> None:
        super().__init__()
        self._bg_color = constants.COLOR_SKY_DEEP
        # Pre-rendrede tekst-surfaces (cache: aldri re-render per frame)
        self._title = font.render(
            "Pitch & Plunder", False, constants.COLOR_MOON_CORE
        ).convert_alpha()
        self._hint = font.render(
            "F11 fullskjerm  ESC avslutt", False, constants.COLOR_STONE_LIT
        ).convert_alpha()
        self._title_pos = (
            (constants.RENDER_WIDTH - self._title.get_width()) // 2,
            constants.RENDER_HEIGHT // 2 - 20,
        )
        self._hint_pos = (
            (constants.RENDER_WIDTH - self._hint.get_width()) // 2,
            constants.RENDER_HEIGHT // 2 + 10,
        )

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN and event.key in constants.KEY_MENU:
            self.want_quit = True

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill(self._bg_color)
        surface.blit(self._title, self._title_pos)
        surface.blit(self._hint, self._hint_pos)


SceneFactory = Callable[[], BaseScene]


class SceneManager:
    """Holder aktiv scene og utfører bytter mellom dem."""

    def __init__(self, factories: dict[str, SceneFactory], initial: str) -> None:
        self._factories = factories
        self._current_name = initial
        self._current: BaseScene = factories[initial]()
        self._current.on_enter()

    @property
    def current(self) -> BaseScene:
        return self._current

    @property
    def current_name(self) -> str:
        return self._current_name

    def maybe_switch(self) -> None:
        """Utfør scene-bytte hvis aktiv scene har bedt om det."""
        target = self._current.next_scene
        if target is None:
            return
        if target not in self._factories:
            log.warning("Ukjent scene: %s", target)
            self._current.next_scene = None
            return
        self._current.on_exit()
        self._current = self._factories[target]()
        self._current_name = target
        self._current.on_enter()


def _create_display(fullscreen: bool) -> pygame.Surface:
    """Opprett pygame display.

    Vi bruker `pygame.SCALED` slik at vi kan tegne direkte i logisk 640x360-
    oppløsning, og lar SDL skalere opp til ønsket vindusstørrelse med
    nearest-neighbor. Hvis SCALED ikke er tilgjengelig (f.eks. gamle SDL-
    byggd eller rare driver-kombinasjoner), fallbacker vi til et større
    software-vindu og skalerer manuelt.

    Returnerer surface som scenen skal tegne på (alltid 640x360).
    """
    flags = pygame.SCALED
    if fullscreen:
        flags |= pygame.FULLSCREEN
    try:
        window = pygame.display.set_mode(
            (constants.RENDER_WIDTH, constants.RENDER_HEIGHT), flags
        )
        log.info("Display: pygame.SCALED %dx%d fullscreen=%s",
                 constants.RENDER_WIDTH, constants.RENDER_HEIGHT, fullscreen)
        return window
    except pygame.error as exc:
        log.warning("SCALED feilet (%s) – bruker software fallback", exc)
        flags = pygame.FULLSCREEN if fullscreen else 0
        pygame.display.set_mode(constants.DEFAULT_WINDOW_SIZE, flags)
        # Returner en intern render-surface; main-løkken skalerer manuelt
        return pygame.Surface(
            (constants.RENDER_WIDTH, constants.RENDER_HEIGHT)
        ).convert()


def _load_font(size: int) -> pygame.font.Font:
    """Last Public Pixel-fonten. Fallback til SysFont hvis den mangler."""
    path = "assets/fonts/PublicPixel.ttf"
    try:
        font = pygame.font.Font(path, size)
        log.info("Lastet pixel font: %s (size=%d)", path, size)
        return font
    except (pygame.error, FileNotFoundError) as exc:
        log.warning("Kunne ikke laste %s (%s) – bruker SysFont", path, exc)
        return pygame.font.SysFont(None, size)


def run() -> int:
    """Start hovedløkken. Returnerer exit-kode."""
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )

    # IKKE pygame.init() – vi unngår mixer-subsystemet i Fase 1.
    pygame.display.init()
    pygame.font.init()
    pygame.event.set_blocked(constants.BLOCKED_EVENTS)
    pygame.display.set_caption("Pitch & Plunder")

    fullscreen = False
    render_surface = _create_display(fullscreen)
    # Når SCALED fungerer er render_surface == window, og pygame håndterer
    # skaleringen. I software-fallback er render_surface en separat surface
    # og vi må blit-e + skalere manuelt til display-vinduet.
    window = pygame.display.get_surface()
    needs_manual_scale = render_surface is not window

    font_small = _load_font(8)

    manager = SceneManager(
        factories={
            "placeholder": lambda: PlaceholderScene(font_small),
            "parallax_test": lambda: ParallaxTestScene(font_small),
        },
        initial="parallax_test",
    )

    clock = pygame.time.Clock()
    running = True
    while running:
        dt = clock.tick(constants.TARGET_FPS) / 1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                break
            if event.type == pygame.KEYDOWN and event.key in constants.KEY_FULLSCREEN:
                fullscreen = not fullscreen
                render_surface = _create_display(fullscreen)
                window = pygame.display.get_surface()
                needs_manual_scale = render_surface is not window
                continue
            manager.current.handle_event(event)

        if manager.current.want_quit:
            running = False
            break

        manager.current.update(dt)
        manager.current.draw(render_surface)

        if needs_manual_scale:
            pygame.transform.scale(render_surface, window.get_size(), window)
        pygame.display.flip()

        manager.maybe_switch()

    pygame.display.quit()
    pygame.font.quit()
    return 0


if __name__ == "__main__":
    sys.exit(run())
