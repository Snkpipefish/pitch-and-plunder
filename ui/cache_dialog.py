"""CacheSubDialog — Fase 3 C3-2 stub.

Underdialog åpnet fra HarbormasterDialog for gull-deponering/uttak i
havnens cache. Arver fra DialogOverlay. `_build_entries()` returnerer
tom liste; C3-5 fyller inn per FASE_3.md §1.12:

- "Legg inn N gull" (N velges — trinnstørrelse tbd, sannsynligvis 50
  med Shift = 500)
- "Ta ut N gull"
- "Saldo: N gull" info-linje
- "Lukk" (eller ESC)

Tortuga-cachen er spesiell: `port_caches["tortuga"]` er score-telleren
(`GameState.get_score()`) som C3-5 eksponerer. Andre havner fungerer
identisk mekanisk men teller ikke i score.

Låst til current_port — det fysiske depositet kan ikke overføres mellom
havner. Spilleren må seile tilbake for å ta ut gullet.
"""

from __future__ import annotations

from state import GameState
from ui.dialog_overlay import DialogOverlay


class CacheSubDialog(DialogOverlay):
    """Per-havn gull-cache legg-inn/ta-ut. Stub — C3-5 wirer inn."""

    def __init__(self, font, game_state: GameState, port_id: str) -> None:
        super().__init__(font)
        self._state = game_state
        self._port_id = port_id

    def _build_entries(self) -> list:
        """C3-5: liste av deposit/withdraw-verdier + saldo + lukk."""
        return []

    def handle_event(self, event) -> None:
        """C3-5: Enter for valgt handling."""
        entries = self._build_entries()
        if self._handle_navigation(event, len(entries)):
            return
        # C3-5: activation-logic

    def draw(self, surface) -> None:
        """C3-5: render saldo + handlinger + hint."""
        self._draw_panel(surface)
