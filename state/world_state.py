"""WorldState — hvilken havn spilleren er i, klokken, skipet, pågående reise.

Endres av scene-bytter, seiling, og klokke-tikking.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from state.ship_state import ShipState
from state.voyage_state import VoyageState
from systems.game_clock import GameClock


@dataclass
class WorldState:
    current_port: str = "tortuga"
    clock: GameClock = field(default_factory=GameClock)
    ship: ShipState = field(default_factory=ShipState)
    voyage: Optional[VoyageState] = None
