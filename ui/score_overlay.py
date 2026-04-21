"""ScoreOverlay — Fase 3 C3-12.

Game-over-overlay som vises når `game_state.get_game_over_reason()`
returnerer ikke-None verdi:
- "arrested": mistanke nådde terskel
- "dead:<event_id>": random event trigget død
- "completed": dag 101 er nådd (100-dagers-løp ferdig)

Viser score + info-linjer om kjørt løp. Main-loop poller
`want_quit` og `want_restart` for avslutning eller nytt løp.

Input:
- Enter / Esc → want_quit (avslutt spillet)
- F6 → want_restart (start nytt løp)

IKKE en scene — overlay. PortVillageScene åpner den via
`_maybe_open_score_overlay` i update-loopen.
"""

from __future__ import annotations

import pygame

import constants
from state import GameState
from ui.dialog_overlay import (
    DEFAULT_PANEL_H,
    DEFAULT_PANEL_W,
    DialogOverlay,
)


_TITLE_Y_OFFSET = 14
_SCORE_Y_OFFSET = 40
_INFO_START_Y_OFFSET = 70
_INFO_LINE_HEIGHT = 14
_LABEL_X_OFFSET = 24
_VALUE_X_FROM_RIGHT = 24
_HINT_Y_OFFSET_FROM_BOTTOM = 22

_TITLE_COLOR = constants.COLOR_MOON_CORE
_SCORE_COLOR = constants.COLOR_LANTERN_BRIGHT
_LABEL_COLOR = constants.COLOR_STONE_LIT
_VALUE_COLOR = constants.COLOR_FOG
_HINT_COLOR = constants.COLOR_STONE_LIT


#: Presentasjonsnavn for death-cause → body-tekst i overlayet.
_DEATH_NAMES: dict[str, str] = {
    "shipwreck": "Forlis",
    "sickness": "Sykdom",
}


def _format_reason(reason: str) -> str:
    """Konverter reason-kode til norsk presentasjon."""
    if reason == "arrested":
        return "Arrestert av guvernøren"
    if reason == "completed":
        return "100 dager overlevd"
    if reason.startswith("dead:"):
        cause = reason[len("dead:"):]
        return f"Død ({_DEATH_NAMES.get(cause, cause)})"
    return reason


class ScoreOverlay(DialogOverlay):
    """Game-over-overlay. Viser score + info-linjer. Fase 3 C3-12."""

    def __init__(
        self,
        font: pygame.font.Font,
        game_state: GameState,
        reason: str,
    ) -> None:
        super().__init__(font, panel_w=DEFAULT_PANEL_W, panel_h=DEFAULT_PANEL_H)
        self._state = game_state
        self._reason = reason
        #: Sett av F6; main-loop poller og starter nytt løp.
        self.want_restart = False
        #: Sett av Enter/Esc; main-loop poller (via want_quit) og
        #: avslutter spillet.
        self._title_surf: pygame.Surface | None = None
        self._score_surf: pygame.Surface | None = None
        self._info_surfs: list[tuple[pygame.Surface, pygame.Surface]] = []
        self._hint_surf: pygame.Surface | None = None

    def _ensure_title(self) -> None:
        if self._title_surf is None:
            self._title_surf = self._font.render(
                "Spillet er slutt", False, _TITLE_COLOR,
            ).convert_alpha()

    def _ensure_score(self) -> None:
        if self._score_surf is None:
            score = self._state.get_score()
            self._score_surf = self._font.render(
                f"Score: {score} gull i gullkista", False, _SCORE_COLOR,
            ).convert_alpha()

    def _ensure_info(self) -> None:
        if self._info_surfs:
            return
        ps = self._state.player_state
        day = self._state.world_state.clock.day
        # "completed" = dag 101+; "overlevd" vises som min(day, 100)
        days_survived = min(day, 100)
        lines: list[tuple[str, str]] = [
            ("Dager overlevd", f"{days_survived}"),
            ("\u00C5rsak", _format_reason(self._reason)),
            ("Slutt-mistanke", f"{int(ps.suspicion)}"),
            ("Sabotasjer", f"{ps.total_sabotages}"),
            ("Falske rykter", f"{ps.total_false_rumors}"),
            ("Reiser", f"{ps.total_voyages}"),
        ]
        self._info_surfs = [
            (
                self._font.render(label, False, _LABEL_COLOR).convert_alpha(),
                self._font.render(value, False, _VALUE_COLOR).convert_alpha(),
            )
            for label, value in lines
        ]

    def _ensure_hint(self) -> None:
        if self._hint_surf is None:
            self._hint_surf = self._font.render(
                "Enter/Esc avslutter. F6 starter nytt l\u00F8p.",
                False, _HINT_COLOR,
            ).convert_alpha()

    def handle_event(self, event: pygame.event.Event) -> None:
        """Input: Enter/Esc avslutter, F6 starter nytt løp."""
        if event.type != pygame.KEYDOWN:
            return
        if event.key in (pygame.K_RETURN, pygame.K_ESCAPE):
            self._want_close = True
        elif event.key == pygame.K_F6:
            self.want_restart = True
            self._want_close = True

    def draw(self, surface: pygame.Surface) -> None:
        self._ensure_title()
        self._ensure_score()
        self._ensure_info()
        self._ensure_hint()

        self._draw_panel(surface)
        px, py = self._panel_x, self._panel_y
        w, h = self._panel_w, self._panel_h

        assert self._title_surf is not None
        surface.blit(self._title_surf, (px + _LABEL_X_OFFSET, py + _TITLE_Y_OFFSET))
        assert self._score_surf is not None
        surface.blit(self._score_surf, (px + _LABEL_X_OFFSET, py + _SCORE_Y_OFFSET))

        for i, (label_surf, value_surf) in enumerate(self._info_surfs):
            row_y = py + _INFO_START_Y_OFFSET + i * _INFO_LINE_HEIGHT
            surface.blit(label_surf, (px + _LABEL_X_OFFSET, row_y))
            value_x = px + w - _VALUE_X_FROM_RIGHT - value_surf.get_width()
            surface.blit(value_surf, (value_x, row_y))

        assert self._hint_surf is not None
        surface.blit(
            self._hint_surf,
            (px + _LABEL_X_OFFSET, py + h - _HINT_Y_OFFSET_FROM_BOTTOM),
        )
