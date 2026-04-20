"""HarbormasterDialog — Fase 3 C3-2 stub.

Arver fra DialogOverlay. `_build_entries()` returnerer tom liste; C3-4
fyller inn faktiske oppføringer per FASE_3.md §1.6:

- Fast-travel: én oppføring per havn (unntatt current_port), med kost
  (gull + dager) fra `balance.travel.routes`
- Cache-oppføring (lokal cache for current_port — åpner CacheSubDialog)
- `Vis kart` (åpner WorldMapScene som alternativ visualisering)

Kaller `voyage.start_voyage` ved fast-travel-aktivering — samme
infrastruktur som WorldMapScene sin VoyageConfirmDialog i 2B.

Flerdagers-reise: dawn-tick kalles N ganger sekvensielt (FASE_3.md §1.4
presisering 2). C3-10 (sabotasje) og C3-11 (events) legger til impacts
som kan lande mellom reise-dager.
"""

from __future__ import annotations

from state import GameState
from ui.dialog_overlay import DialogOverlay


class HarbormasterDialog(DialogOverlay):
    """Havnekontor-dialog: fast-travel + cache + vis-kart. Stub — C3-4."""

    def __init__(self, font, game_state: GameState, port_id: str) -> None:
        super().__init__(font)
        self._state = game_state
        self._port_id = port_id

    def _build_entries(self) -> list:
        """C3-4: liste av destinasjoner + cache + vis-kart."""
        return []

    def handle_event(self, event) -> None:
        """C3-4: Enter for å aktivere valgt (fast-travel/cache/kart)."""
        entries = self._build_entries()
        if self._handle_navigation(event, len(entries)):
            return
        # C3-4: activation-logic

    def draw(self, surface) -> None:
        """C3-4: render rute-liste + cache-oppføring + hint."""
        self._draw_panel(surface)
