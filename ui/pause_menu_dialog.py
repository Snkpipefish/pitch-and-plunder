"""PauseMenuDialog + ConfirmNewGameDialog — Fase 3 C3-12.

Åpnes via ESC i PortVillageScene når ingen annen dialog er aktiv.
Tre oppføringer:
- "Fortsett": lukker dialogen (ingen effekt)
- "Nytt løp": åpner ConfirmNewGameDialog — ved bekreft settes
  `want_restart=True` som main-loop poller
- "Avslutt": setter `want_quit=True`

ConfirmNewGameDialog er en egen binær dialog — "Bekreft" og "Avbryt"
som bestemmer om vi setter `want_restart`.

Begge dialoger er peer til øvrige DialogOverlay-subklasser og lukkes
med ESC (tilsvarer "Avbryt"/"Fortsett"-tilbakefall).
"""

from __future__ import annotations

import pygame

import constants
from ui.dialog_overlay import DialogOverlay


_PANEL_W = 280
_PANEL_H = 130
_TITLE_Y_OFFSET = 14
_ENTRIES_START_Y_OFFSET = 40
_ENTRY_HEIGHT = 16
_LABEL_X_OFFSET = 24
_HINT_Y_OFFSET_FROM_BOTTOM = 22

_TITLE_COLOR = constants.COLOR_MOON_CORE
_ENTRY_COLOR = constants.COLOR_STONE_LIT
_SELECTED_COLOR = constants.COLOR_LANTERN_BRIGHT
_HINT_COLOR = constants.COLOR_FOG


class PauseMenuDialog(DialogOverlay):
    """Pause-meny med tre valg. Fase 3 C3-12."""

    ENTRIES = ("Fortsett", "Nytt l\u00F8p", "Avslutt")

    def __init__(self, font: pygame.font.Font) -> None:
        super().__init__(font, panel_w=_PANEL_W, panel_h=_PANEL_H)
        # Sett av caller etter activation; main-loop poller dem.
        self.want_restart_confirm = False  # be PortVillageScene åpne confirm
        self.want_quit_game = False
        self._title_surf: pygame.Surface | None = None
        self._entry_surfs: list[tuple[pygame.Surface, pygame.Surface]] = []
        self._hint_surf: pygame.Surface | None = None

    def _ensure_surfaces(self) -> None:
        if self._title_surf is None:
            self._title_surf = self._font.render(
                "Pause", False, _TITLE_COLOR,
            ).convert_alpha()
        if not self._entry_surfs:
            for entry in self.ENTRIES:
                self._entry_surfs.append((
                    self._font.render(entry, False, _ENTRY_COLOR).convert_alpha(),
                    self._font.render(entry, False, _SELECTED_COLOR).convert_alpha(),
                ))
        if self._hint_surf is None:
            self._hint_surf = self._font.render(
                "Pil/W,S velg   Enter bekreft   Esc fortsett",
                False, _HINT_COLOR,
            ).convert_alpha()

    def _build_entries(self) -> list:
        return list(self.ENTRIES)

    def handle_event(self, event: pygame.event.Event) -> None:
        entries = self._build_entries()
        if self._handle_navigation(event, len(entries)):
            return
        if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
            choice = entries[self._selected]
            if choice == "Fortsett":
                self._want_close = True
            elif choice == "Nytt l\u00F8p":
                # Signaliser til PortVillageScene at confirm-dialog skal åpnes.
                self.want_restart_confirm = True
                self._want_close = True
            elif choice == "Avslutt":
                self.want_quit_game = True
                self._want_close = True

    def draw(self, surface: pygame.Surface) -> None:
        self._ensure_surfaces()
        self._draw_panel(surface)
        px, py = self._panel_x, self._panel_y
        h = self._panel_h

        assert self._title_surf is not None
        surface.blit(self._title_surf, (px + _LABEL_X_OFFSET, py + _TITLE_Y_OFFSET))

        for i, (normal, selected) in enumerate(self._entry_surfs):
            row_y = py + _ENTRIES_START_Y_OFFSET + i * _ENTRY_HEIGHT
            surf = selected if i == self._selected else normal
            surface.blit(surf, (px + _LABEL_X_OFFSET, row_y))

        assert self._hint_surf is not None
        surface.blit(
            self._hint_surf,
            (px + _LABEL_X_OFFSET, py + h - _HINT_Y_OFFSET_FROM_BOTTOM),
        )


class ConfirmNewGameDialog(DialogOverlay):
    """Bekreftelses-dialog for nytt løp. Fase 3 C3-12.

    To oppføringer: "Bekreft" og "Avbryt". Valg av "Bekreft" setter
    `want_restart=True`, "Avbryt" eller ESC lukker uten effekt.
    """

    ENTRIES = ("Avbryt", "Bekreft")  # Avbryt som første → tryggere default

    def __init__(self, font: pygame.font.Font) -> None:
        super().__init__(font, panel_w=_PANEL_W + 40, panel_h=_PANEL_H)
        self.want_restart = False
        self._title_surf: pygame.Surface | None = None
        self._body_surf: pygame.Surface | None = None
        self._entry_surfs: list[tuple[pygame.Surface, pygame.Surface]] = []
        self._hint_surf: pygame.Surface | None = None

    def _ensure_surfaces(self) -> None:
        if self._title_surf is None:
            self._title_surf = self._font.render(
                "Start nytt l\u00F8p?", False, _TITLE_COLOR,
            ).convert_alpha()
        if self._body_surf is None:
            self._body_surf = self._font.render(
                "N\u00E5v\u00E6rende fremgang g\u00E5r tapt.",
                False, _HINT_COLOR,
            ).convert_alpha()
        if not self._entry_surfs:
            for entry in self.ENTRIES:
                self._entry_surfs.append((
                    self._font.render(entry, False, _ENTRY_COLOR).convert_alpha(),
                    self._font.render(entry, False, _SELECTED_COLOR).convert_alpha(),
                ))
        if self._hint_surf is None:
            self._hint_surf = self._font.render(
                "Pil/W,S velg   Enter   Esc avbryt",
                False, _HINT_COLOR,
            ).convert_alpha()

    def _build_entries(self) -> list:
        return list(self.ENTRIES)

    def handle_event(self, event: pygame.event.Event) -> None:
        entries = self._build_entries()
        if self._handle_navigation(event, len(entries)):
            return
        if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
            choice = entries[self._selected]
            if choice == "Bekreft":
                self.want_restart = True
            self._want_close = True

    def draw(self, surface: pygame.Surface) -> None:
        self._ensure_surfaces()
        self._draw_panel(surface)
        px, py = self._panel_x, self._panel_y
        h = self._panel_h

        assert self._title_surf is not None
        surface.blit(self._title_surf, (px + _LABEL_X_OFFSET, py + _TITLE_Y_OFFSET))
        assert self._body_surf is not None
        surface.blit(
            self._body_surf,
            (px + _LABEL_X_OFFSET, py + _TITLE_Y_OFFSET + _ENTRY_HEIGHT),
        )

        entries_y_start = _ENTRIES_START_Y_OFFSET + _ENTRY_HEIGHT + 4
        for i, (normal, selected) in enumerate(self._entry_surfs):
            row_y = py + entries_y_start + i * _ENTRY_HEIGHT
            surf = selected if i == self._selected else normal
            surface.blit(surf, (px + _LABEL_X_OFFSET, row_y))

        assert self._hint_surf is not None
        surface.blit(
            self._hint_surf,
            (px + _LABEL_X_OFFSET, py + h - _HINT_Y_OFFSET_FROM_BOTTOM),
        )
