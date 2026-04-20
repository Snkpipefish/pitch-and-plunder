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
    #: Fase 3 C3-7: Sett til True av `systems.suspicion.check_threshold`
    #: når mistanke når `balance.suspicion.threshold`. Konsumeres av
    #: C3-12 score-overlay som trigger "arrestert"-slutt. Idempotent:
    #: en gang True, forblir True til game-over.
    arrested: bool = False

    def get_score(self) -> int:
        """Returnér spillerens nåværende score (Fase 3 C3-5).

        Score = gull i Tortuga-cachen. Andre havner-caches teller IKKE
        (låst til havnen, spilleren er ikke der ved game-over). Gull
        på hånden teller heller ikke (kan tapes ved arrest).

        Tortuga-cachen er samme entitet som "Tortuga-kista" i design-
        dokumentet (FASE_3.md §1.2/§1.9); samme slot i `port_caches`,
        navngitt dobbelt i UI: "Gullkiste" for Tortuga, "Cache" for
        andre havner, men mekanisk identisk.

        Brukes av C3-12 score-overlay ved game-over. IKKE vist i HUD
        før da (presisering C3-5 #2 — score forblir usynlig under
        normal spilling).
        """
        return self.player_state.port_caches.get("tortuga", 0)
