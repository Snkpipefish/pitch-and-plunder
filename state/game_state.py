"""GameState v5 — nested orkestrator.

Versjons-bump fra v4 per FASE_2B.md §2. Migreringskode i
`systems/save.py` konverterer v1..v4 via chained
`migrate_vN_to_vN+1`-funksjoner.

Hvert system eier ett felt (spec §2.2):
- PlayerState: endres av inventar-kjøp, bevegelse, gull-transaksjoner
- WorldState: endres av scene-bytter, seiling, klokke
- EconomyState: endres av RegimeManager, Market, observasjonslogikk
- PitchLakeState: endres av PitchLake on_new_day
"""

from __future__ import annotations

from dataclasses import dataclass, field

from state.economy_state import EconomyState
from state.pitch_lake_state import PitchLakeState
from state.player_state import PlayerState
from state.world_state import WorldState


CURRENT_SAVE_VERSION = 5


@dataclass
class GameState:
    version: int = CURRENT_SAVE_VERSION
    player_state: PlayerState = field(default_factory=PlayerState)
    world_state: WorldState = field(default_factory=WorldState)
    economy_state: EconomyState = field(default_factory=EconomyState)
    pitch_lake_state: PitchLakeState = field(default_factory=PitchLakeState)
