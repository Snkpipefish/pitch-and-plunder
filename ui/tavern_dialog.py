"""TavernDayDialog og TavernNightDialog — Fase 3 C3-2 stubs.

Arver fra DialogOverlay. `_build_entries()` returnerer tom liste; C3-3
fyller inn faktiske oppføringer per FASE_3.md §1.6:

**TavernDayDialog**:
- Rom-kjøp (room_cost_gold + room_cost_hours)
- `rumor_listen` gratis-tier (tilfeldig havn/vare preview)
- Bek-anlegg-kjøp — KUN i Tortuga, KUN før `PitchLakeState.purchased=True`
  (C3-6 gate-logikk)

**TavernNightDialog**:
- Rom-kjøp (samme som dag-meny)
- `rumor_listen` betalt-tier (spilleren velger havn + vare)
- `order_sabotage` (pris-spike i target-havn, +mistanke 15)
- `spread_false_rumor` (pris-dump i target-havn, +mistanke 8)
- Smugler-kontakter (stub — kan bli Fase 4+ hook)

Begge tar game_state i __init__ slik at de kan lese balance, port-id,
inventar og gull ved draw. Wiring inn i PortVillageScene kommer i C3-3.
"""

from __future__ import annotations

from state import GameState
from ui.dialog_overlay import DialogOverlay


class TavernDayDialog(DialogOverlay):
    """Tavern dag-meny. Stub — C3-3 fyller inn oppføringer."""

    def __init__(self, font, game_state: GameState, port_id: str) -> None:
        super().__init__(font)
        self._state = game_state
        self._port_id = port_id

    def _build_entries(self) -> list:
        """C3-3: vil returnere rom/rumor_listen/bek-anlegg (Tortuga)."""
        return []

    def handle_event(self, event) -> None:
        """C3-3: Enter for å aktivere valgt oppføring."""
        entries = self._build_entries()
        if self._handle_navigation(event, len(entries)):
            return
        # C3-3: activation-logic

    def draw(self, surface) -> None:
        """C3-3: render tittel + oppføringer + hint-linje."""
        self._draw_panel(surface)


class TavernNightDialog(DialogOverlay):
    """Tavern natt-meny. Stub — C3-3 fyller inn oppføringer."""

    def __init__(self, font, game_state: GameState, port_id: str) -> None:
        super().__init__(font)
        self._state = game_state
        self._port_id = port_id

    def _build_entries(self) -> list:
        """C3-3: rom, rumor_listen (betalt), order_sabotage,
        spread_false_rumor, smuggler-contact."""
        return []

    def handle_event(self, event) -> None:
        entries = self._build_entries()
        if self._handle_navigation(event, len(entries)):
            return
        # C3-3: activation-logic

    def draw(self, surface) -> None:
        self._draw_panel(surface)
