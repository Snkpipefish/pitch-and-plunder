"""PlayerState — spillerens posisjon, gull og inventar.

`position_x` er kun X-koordinat per spec §2.1. Y gjenopprettes scene-
spesifikt fra VillageScene.GROUND_TOP_Y (eller tilsvarende scene-konstant).
Dette kan bli per-havn i C4 når bygnings-plasseringer flytter til
`data/ports.json` og scener kan ha ulik bakke-høyde.

`inventory: dict[str, InventoryItem]` beholder `avg_cost` fra 2A Commit 7.
Spec §2.1 viste `dict[str, int]` illustrativt, men avg_cost er en reell
2A-feature brukt i exchange-overlayet.

`cargo_capacity` er IKKE her — det er skipets (ShipState.cargo_capacity).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from entities.commodity import InventoryItem


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
