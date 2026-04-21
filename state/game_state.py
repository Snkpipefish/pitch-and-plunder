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
    #: Fase 3 C3-11: Sett av event-kode-handler (shipwreck, sickness)
    #: ved dødelig utfall. Konsumeres av C3-12 score-overlay som trigger
    #: "død"-slutt. Samme top-level-mønster som `arrested`. `death_cause`
    #: er en event-id eller kort nøkkel for UI-visning.
    dead: bool = False
    death_cause: str = ""

    def get_game_over_reason(self) -> str | None:
        """Returnér game-over-årsak hvis spillet er over, ellers None.

        Fase 3 C3-12. Prioritert rekkefølge:
        - "arrested": spilleren ble tatt av guvernøren (suspicion ≥ threshold)
        - f"dead:{death_cause}": spilleren døde (forlis/sykdom/osv)
        - "completed": 100-dagers løpet er fullført (clock.day > 100)
        - None: spillet pågår

        Derived property — ingen state-felt-duplikasjon. Score-overlay
        og pause-meny bruker denne som eneste sannhetskilde for
        game-over-state. FASE_3.md §1.1: "100-dagers løp med score".
        """
        if self.arrested:
            return "arrested"
        if self.dead:
            return f"dead:{self.death_cause}"
        if self.world_state.clock.day > 100:
            return "completed"
        return None

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
