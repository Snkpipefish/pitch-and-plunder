"""ScoreOverlay — Fase 3 C3-2 stub.

Game-over-overlay som vises ved:
- Dag 101 starter (dag 100 ferdig)
- Mistanke ≥ terskel (arrest)
- Random event med death-flagg (forlis / sykdom)

Arver fra DialogOverlay. Ingen navigerbare entries (`_build_entries()`
returnerer tom liste). `draw()` viser statisk panel med score-sammendrag.
C3-12 fyller inn:

- Score: `player_state.port_caches.get("tortuga", 0)` gull
- Dager overlevd
- Årsak (dag 100 / arrest / død-<type>)
- Slutt-mistanke
- Info-linjer: antall sabotasjer, falske rykter, reiser
- "Enter/Esc for å avslutte"

ESC og Enter setter begge `_want_close=True`; scene-eieren (main.py)
poller flagget og avslutter spillet (ingen restart-flyt i Fase 3).

IKKE en scene — overlay. Main-loop fortsetter å oppdatere
PortVillageScene under (celestial, partikler) mens overlayet står.
"""

from __future__ import annotations

import pygame

from state import GameState
from ui.dialog_overlay import DialogOverlay


class ScoreOverlay(DialogOverlay):
    """Game-over score-overlay. Stub — C3-12 fyller inn."""

    def __init__(
        self,
        font,
        game_state: GameState,
        cause: str = "day_100",
    ) -> None:
        super().__init__(font)
        self._state = game_state
        self._cause = cause  # "day_100" | "arrest" | "death_<type>"

    def _build_entries(self) -> list:
        """Ingen navigerbare oppføringer — kun statisk info."""
        return []

    def handle_event(self, event) -> None:
        """Enter eller Esc setter want_close (main avslutter).

        C3-12 utvider ev. med mer info-toggling.
        """
        # ESC håndteres av base via _handle_navigation.
        if self._handle_navigation(event, 0):
            return
        # Enter gir samme effekt som Esc: lukk og avslutt.
        if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
            self._want_close = True

    def draw(self, surface) -> None:
        """C3-12: render score + årsak + info-linjer."""
        self._draw_panel(surface)
