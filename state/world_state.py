"""WorldState — hvilken havn spilleren er i, klokken, skipet, pågående reise.

Endres av scene-bytter, seiling, og klokke-tikking.

Fase 3 (v2-schema, C3-0 stub):
- `action_budget`: handlings-drevet tids-budsjett (C3-1 wirer inn).
  Default-instans opprettes via `ActionBudget()`; i new_game_state skal
  `ActionBudget.new_default()` kalles for balance-forankrede verdier.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from state.action_budget import ActionBudget
from state.ship_state import ShipState
from state.voyage_state import VoyageState
from systems.game_clock import GameClock


@dataclass
class WorldState:
    current_port: str = "tortuga"
    clock: GameClock = field(default_factory=GameClock)
    ship: ShipState = field(default_factory=ShipState)
    voyage: Optional[VoyageState] = None
    # Fase 3 (v2-schema, C3-0 stub — ikke koblet enda)
    action_budget: ActionBudget = field(default_factory=ActionBudget)
