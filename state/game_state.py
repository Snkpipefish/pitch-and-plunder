"""GameState v6 — nested orkestrator.

v5 (Fase 2B C1b): nested felter per system. v6 (Fase 3 C3-1): Fase 3
stub-felt ble innført i C3-0 uten versjon-bump; C3-1 bumper til v6
for å markere at `PitchLakeState.purchased`, `WorldState.action_budget`,
og `PlayerState`/`EconomyState`-stubs nå er en del av det offisielle
skjemaet. v5→v6-migrering i `systems/save.py` setter `purchased=True`
for eksisterende dev-saves (bakoverkompatibilitet for aktive bek-
produksjoner) og initialiserer ActionBudget fra balance.

Hvert system eier ett felt (spec §2.2):
- PlayerState: endres av inventar-kjøp, bevegelse, gull-transaksjoner,
  mistanke/rom/caches/rumor_listen (Fase 3)
- WorldState: endres av scene-bytter, seiling, klokke, handlings-tid
  (Fase 3)
- EconomyState: endres av RegimeManager, Market, observasjonslogikk,
  sabotasje/rumor_spread-impacts (Fase 3)
- PitchLakeState: endres av PitchLake on_new_day; `purchased`-flagg
  gates produksjon (Fase 3 C3-6)
"""

from __future__ import annotations

from dataclasses import dataclass, field

from state.economy_state import EconomyState
from state.pitch_lake_state import PitchLakeState
from state.player_state import PlayerState
from state.world_state import WorldState


CURRENT_SAVE_VERSION = 6


@dataclass
class GameState:
    version: int = CURRENT_SAVE_VERSION
    player_state: PlayerState = field(default_factory=PlayerState)
    world_state: WorldState = field(default_factory=WorldState)
    economy_state: EconomyState = field(default_factory=EconomyState)
    pitch_lake_state: PitchLakeState = field(default_factory=PitchLakeState)
