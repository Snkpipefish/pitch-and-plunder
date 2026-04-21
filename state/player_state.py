"""PlayerState — spillerens posisjon, gull, inventar, og Fase 3-felt.

`position_x` er kun X-koordinat per spec §2.1. Y gjenopprettes scene-
spesifikt fra VillageScene.GROUND_TOP_Y (eller tilsvarende scene-konstant).
Dette kan bli per-havn i C4 når bygnings-plasseringer flytter til
`data/ports.json` og scener kan ha ulik bakke-høyde.

`inventory: dict[str, InventoryItem]` beholder `avg_cost` fra 2A Commit 7.
Spec §2.1 viste `dict[str, int]` illustrativt, men avg_cost er en reell
2A-feature brukt i exchange-overlayet.

`cargo_capacity` er IKKE her — det er skipets (ShipState.cargo_capacity).

Fase 3 (v2-schema, C3-0 stubs — disse er IKKE koblet til noe system
før respektive commits):
- `suspicion`: float [0.0, threshold]. C3-7 wiring.
- `rest`: float [0.0, 1.0]. C3-8 wiring.
- `port_caches`: per-havn gull-lager. Tortuga-entry er score-telleren.
  C3-5 wiring.
- `active_rumors`: spillerens kjøpte lytte-rykter. C3-9 wiring.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from entities.commodity import InventoryItem
from state.rumor_state import ActiveRumor


def _default_inventory() -> dict[str, InventoryItem]:
    return {
        "sugar": InventoryItem(),
        "rum": InventoryItem(),
        "tobacco": InventoryItem(),
        "pitch": InventoryItem(),
    }


@dataclass
class PlayerState:
    position_x: float = 320.0
    gold: int = 0
    inventory: dict[str, InventoryItem] = field(default_factory=_default_inventory)
    # Fase 3 (v2-schema, C3-0 stubs — ikke koblet enda)
    suspicion: float = 0.0
    rest: float = 1.0
    port_caches: dict[str, int] = field(default_factory=dict)
    active_rumors: list[ActiveRumor] = field(default_factory=list)
    # Fase 3 C3-12: løp-statistikk for score-overlay. Inkrementeres i
    # handlerne ved suksessfull handling (etter gull-trekk OK).
    total_sabotages: int = 0
    total_false_rumors: int = 0
    total_voyages: int = 0
