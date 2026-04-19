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

Designvalg (Fase 2B C1b):
- `PitchLakeState` lever i `state/pitch_lake_state.py`. `upkeep_per_day`
  erstatter `daily_upkeep_cost`-navnet fra 2A (matcher balance.json).
- `PitchLake.on_new_day` er en statisk metode som muterer `state` og
  `game_state` direkte (gold, inventory i `player_state`, total_produced,
  last_production_day).
- `last_production_day` settes kun når `produced > 0` slik at HUD kan
  detektere "ingen drift"-state via `clock.day - last_production_day > 1`.
- `pending_units` (C1b) buffrer produksjon når spilleren er vekk fra
  home_port — realiseres ved retur i C7 (ikke wired ennå).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from entities.commodity import InventoryItem
from state.pitch_lake_state import PitchLakeState

if TYPE_CHECKING:
    from state.game_state import GameState


#: Vare-id for bek i commodities.json.
PITCH_ID = "pitch"


class PitchLake:
    """Statisk produksjons-kalkulator. Muterer state og game_state direkte."""

    @staticmethod
    def on_new_day(
        state: PitchLakeState,
        game_state: "GameState",
    ) -> tuple[int, int]:
        """Kalles ved daggry.

        Returnerer `(produced, paid_upkeep)`.

        Leser upkeep/production fra `state`. Hot-reload av balance.json
        slår inn fordi F5-handleren (main.py) synkroniserer
        state.pitch_lake_state med balance etter vellykket reload —
        live-applicable per spec §4.4.

        Flyt:
        1. Trekk upkeep fra gull. `paid_upkeep = min(upkeep, gold)`.
           gold settes til `gold - paid_upkeep` (kan bli 0 men ikke negativ).
        2. Hvis `paid_upkeep < upkeep` (ikke råd til full lønn) → produced=0.
        3. Ellers: produced = min(production_per_day, ledig lasterom).
           Tom produksjon tapes (full last) – det gir fortsatt produced=0.
        4. `last_production_day` oppdateres KUN hvis `produced > 0`.
        """
        player = game_state.player_state
        ship = game_state.world_state.ship
        clock = game_state.world_state.clock

        upkeep = max(0, state.upkeep_per_day)
        paid_upkeep = min(upkeep, max(0, player.gold))
        player.gold -= paid_upkeep

        if paid_upkeep < upkeep:
            # Ikke råd til full drift i dag – ingen produksjon.
            return 0, paid_upkeep

        # Drift betalt: forsøk produksjon begrenset av lasterom.
        current_total = sum(item.quantity for item in player.inventory.values())
        available_space = max(0, ship.cargo_capacity - current_total)
        produced = min(state.production_per_day, available_space)

        if produced > 0:
            pitch = player.inventory.setdefault(PITCH_ID, InventoryItem())
            old_qty = pitch.quantity
            new_qty = old_qty + produced
            if new_qty > 0:
                # Vektet snitt: produsert bek har kost 0, trekker snittet ned.
                new_avg = (old_qty * pitch.avg_cost) / new_qty
                pitch.avg_cost = round(new_avg, 2)
            pitch.quantity = new_qty
            state.total_produced += produced
            state.last_production_day = clock.day

        return produced, paid_upkeep
