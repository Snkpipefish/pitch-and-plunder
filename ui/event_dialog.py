"""EventDialog — Fase 3 C3-11.

Modal notifikasjons-dialog som viser et random event til spilleren.
Pure notifikasjon: ingen valg, ingen mutasjon. Effektene er allerede
applyert av `systems.events.resolve()` før dialogen åpnes — dialogen
viser bare tittel + body og lukkes med Enter/Space/Esc.

Binære valg-varianter kan komme senere (C3-13 stretch). I C3-11 er
dialogen en ren "tap på skulderen".

Layout:
- Tittel (moon core) øverst
- Body (fog) wrappet over flere linjer
- Hint "Enter lukk" nederst
"""

from __future__ import annotations

import pygame

import constants
from ui.dialog_overlay import DEFAULT_PANEL_H, DEFAULT_PANEL_W, DialogOverlay


_TITLE_Y_OFFSET = 14
_BODY_Y_OFFSET = 44
_BODY_LINE_HEIGHT = 14
_LABEL_X_OFFSET = 24
_BODY_MAX_WIDTH = DEFAULT_PANEL_W - 2 * _LABEL_X_OFFSET
_HINT_Y_OFFSET_FROM_BOTTOM = 22

_TITLE_COLOR = constants.COLOR_MOON_CORE
_BODY_COLOR = constants.COLOR_FOG
_HINT_COLOR = constants.COLOR_STONE_LIT


def _wrap_text(
    font: pygame.font.Font, text: str, max_width: int,
) -> list[str]:
    """Enkel ord-wrap: bryter på mellomrom. Ord lengre enn max_width
    beholdes som egen linje (ingen hard-break)."""
    words = text.split()
    if not words:
        return [""]
    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        candidate = current + " " + word
        if font.size(candidate)[0] <= max_width:
            current = candidate
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


class EventDialog(DialogOverlay):
    """Modal event-notifikasjon. Enter/Space/Esc lukker."""

    def __init__(
        self,
        font: pygame.font.Font,
        title: str,
        body: str,
    ) -> None:
        super().__init__(font, panel_w=DEFAULT_PANEL_W, panel_h=DEFAULT_PANEL_H)
        self._title_text = title
        self._body_text = body
        self._title_surf: pygame.Surface | None = None
        self._body_surfs: list[pygame.Surface] = []
        self._hint_surf: pygame.Surface | None = None

    def _ensure_title(self) -> None:
        if self._title_surf is None:
            self._title_surf = self._font.render(
                self._title_text, False, _TITLE_COLOR,
            ).convert_alpha()

    def _ensure_body(self) -> None:
        if not self._body_surfs:
            lines = _wrap_text(self._font, self._body_text, _BODY_MAX_WIDTH)
            self._body_surfs = [
                self._font.render(line, False, _BODY_COLOR).convert_alpha()
                for line in lines
            ]

    def _ensure_hint(self) -> None:
        if self._hint_surf is None:
            self._hint_surf = self._font.render(
                "Enter lukk", False, _HINT_COLOR,
            ).convert_alpha()

    def handle_event(self, event: pygame.event.Event) -> None:
        """Enter/Space/Esc lukker. Ingen andre keys har effekt."""
        if event.type != pygame.KEYDOWN:
            return
        if event.key in (
            pygame.K_RETURN, pygame.K_SPACE, pygame.K_ESCAPE,
        ):
            self._want_close = True

    def draw(self, surface: pygame.Surface) -> None:
        self._ensure_title()
        self._ensure_body()
        self._ensure_hint()

        self._draw_panel(surface)
        px, py = self._panel_x, self._panel_y
        w, h = self._panel_w, self._panel_h

        assert self._title_surf is not None
        surface.blit(self._title_surf, (px + _LABEL_X_OFFSET, py + _TITLE_Y_OFFSET))

        for i, body_surf in enumerate(self._body_surfs):
            surface.blit(
                body_surf,
                (px + _LABEL_X_OFFSET, py + _BODY_Y_OFFSET + i * _BODY_LINE_HEIGHT),
            )

        assert self._hint_surf is not None
        surface.blit(
            self._hint_surf,
            (px + _LABEL_X_OFFSET, py + h - _HINT_Y_OFFSET_FROM_BOTTOM),
        )
