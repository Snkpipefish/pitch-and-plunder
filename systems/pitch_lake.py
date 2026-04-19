"""Passiv bek-produksjon fra Pitch Lake på Trinidad.

Spilleren "arver" Pitch Lake ved spillstart. Lakeren produserer 2 bek
per dag automatisk ved daggry, mot en daglig drifts-kostnad på 8
dubloner (arbeiderlønn, transport, leie). Hvis spilleren ikke har råd
til drift den dagen blir ingen bek produsert, og tilgjengelig gull
trekkes til 0.

Produksjon tapes også hvis lasterom er fullt – pitchen flyter bort,
selv om drift ble betalt.

Interaktiv utvinning med rør og pumper kommer i Fase 4 (se FASE_2A.md
"Fremtidige utvidelser").

Designvalg:
- `PitchLakeState` er ren dataholder (dataclass) som lagres i GameState.
  `total_produced` og `last_production_day` overlever saves for stats
  og UI-status-detektering.
- `PitchLake.on_new_day` er en statisk metode. Ingen instansvariabler,
  deterministisk — men muterer både `state` og `game_state` direkte
  (gold, inventory, total_produced, last_production_day).
- Produsert bek får `avg_cost=0` (gratis fra spillerens synspunkt –
  drift-kostnaden er allerede trukket separat fra gull).
- `last_production_day` settes kun når `produced > 0` slik at HUD kan
  detektere "ingen drift"-state via `clock.day - last_production_day > 1`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from entities.commodity import InventoryItem

if TYPE_CHECKING:
    from systems.save import GameState


#: Vare-id for bek i commodities.json.
PITCH_ID = "pitch"


@dataclass
class PitchLakeState:
    """Serialiserbar state for Pitch Lake-produksjonen."""

    production_per_day: int = 2
    daily_upkeep_cost: int = 8
    total_produced: int = 0
    last_production_day: int = 0


class PitchLake:
    """Statisk produksjons-kalkulator. Muterer state og game_state direkte."""

    @staticmethod
    def on_new_day(
        state: PitchLakeState,
        game_state: "GameState",
    ) -> tuple[int, int]:
        """Kalles ved daggry.

        Returnerer `(produced, paid_upkeep)`.

        Flyt:
        1. Trekk upkeep fra gull. `paid_upkeep = min(upkeep, gold)`.
           gold settes til `gold - paid_upkeep` (kan bli 0 men ikke negativ).
        2. Hvis `paid_upkeep < upkeep` (ikke råd til full lønn) → produced=0.
        3. Ellers: produced = min(production_per_day, ledig lasterom).
           Tom produksjon tapes (full last) – det gir fortsatt produced=0.
        4. `last_production_day` oppdateres KUN hvis `produced > 0`, slik
           at HUD kan vise "ingen drift" etter mer enn én dag uten
           produksjon.
        """
        upkeep = max(0, state.daily_upkeep_cost)
        paid_upkeep = min(upkeep, max(0, game_state.gold))
        game_state.gold -= paid_upkeep

        if paid_upkeep < upkeep:
            # Ikke råd til full drift i dag – ingen produksjon.
            return 0, paid_upkeep

        # Drift betalt: forsøk produksjon begrenset av lasterom.
        current_total = sum(
            item.quantity for item in game_state.inventory.values()
        )
        available_space = max(
            0, game_state.cargo_capacity - current_total
        )
        produced = min(state.production_per_day, available_space)

        if produced > 0:
            pitch = game_state.inventory.setdefault(
                PITCH_ID, InventoryItem()
            )
            old_qty = pitch.quantity
            new_qty = old_qty + produced
            if new_qty > 0:
                # Vektet snitt: produsert bek har kost 0, trekker snittet ned.
                new_avg = (old_qty * pitch.avg_cost) / new_qty
                pitch.avg_cost = round(new_avg, 2)
            pitch.quantity = new_qty
            state.total_produced += produced
            state.last_production_day = game_state.clock.day

        return produced, paid_upkeep
