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

Designvalg (Fase 2B C1b/C7b):
- `PitchLakeState` lever i `state/pitch_lake_state.py`. `upkeep_per_day`
  erstatter `daily_upkeep_cost`-navnet fra 2A (matcher balance.json).
- `PitchLake.on_new_day` er en statisk metode som muterer `state` og
  `game_state` direkte (gold, inventory i `player_state`, total_produced,
  last_production_day).
- `last_production_day` settes kun når `produced > 0` slik at HUD kan
  detektere "ingen drift"-state via `clock.day - last_production_day > 1`.
- `pending_units` (C7b): når spilleren er BORTE fra home_port (under
  voyage ELLER current_port != home_port), går produksjon hit i stedet
  for inventar. Spec §2.3: "bekken lagres på kaia". Upkeep trekkes som
  normalt; halted-deteksjon fungerer fortsatt via last_production_day.
- `realize_pending_units` (C7b) flytter pending → inventar opp til
  ledig cargo-plass. Kalles eksplisitt av ankomst-flyten i C7c (når
  spilleren ankommer home_port). Pending-overskudd som ikke får plass
  forblir i pending — neste salg gir mer plass.
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
        3. Ellers: produced = `production_per_day`.
           - Hvis spilleren er HJEMME (ingen voyage OG current_port == home_port):
             flyt direkte til inventar opp til ledig cargo-plass. Overskudd
             tapes (full last).
           - Hvis BORTE (voyage aktiv ELLER current_port != home_port):
             flyt til `pending_units`. Ingen tap her — bekken lagres på kaia
             og venter på spillerens retur (realize_pending_units i C7c).
        4. `last_production_day` oppdateres KUN hvis `produced > 0`,
           uavhengig av om bek havner i inventar eller pending — produksjonen
           HAR skjedd.
        """
        player = game_state.player_state
        world = game_state.world_state
        ship = world.ship
        clock = world.clock

        upkeep = max(0, state.upkeep_per_day)
        paid_upkeep = min(upkeep, max(0, player.gold))
        player.gold -= paid_upkeep

        if paid_upkeep < upkeep:
            # Ikke råd til full drift i dag – ingen produksjon.
            return 0, paid_upkeep

        produced = state.production_per_day
        if produced <= 0:
            return 0, paid_upkeep

        is_home = (
            world.voyage is None
            and world.current_port == state.home_port
        )
        if is_home:
            # Hjemme: direkte til inventar, klampet av cargo-plass.
            current_total = sum(
                item.quantity for item in player.inventory.values()
            )
            available_space = max(0, ship.cargo_capacity - current_total)
            actual = min(produced, available_space)
            if actual > 0:
                pitch = player.inventory.setdefault(PITCH_ID, InventoryItem())
                old_qty = pitch.quantity
                new_qty = old_qty + actual
                if new_qty > 0:
                    # Vektet snitt: produsert bek har kost 0.
                    new_avg = (old_qty * pitch.avg_cost) / new_qty
                    pitch.avg_cost = round(new_avg, 2)
                pitch.quantity = new_qty
                state.total_produced += actual
                state.last_production_day = clock.day
            return actual, paid_upkeep
        else:
            # Borte: bufret som pending, ingen tap.
            state.pending_units += produced
            state.total_produced += produced
            state.last_production_day = clock.day
            return produced, paid_upkeep

    @staticmethod
    def realize_pending_units(
        state: PitchLakeState,
        game_state: "GameState",
    ) -> int:
        """Flytt pending_units til inventar opp til ledig cargo-plass.

        Returnerer antall enheter realisert. Resten forblir i
        `pending_units` til neste forsøk (typisk: spilleren selger litt
        bek, kommer tilbake til Tortuga senere — funksjonen kalles igjen).

        avg_cost-håndtering: pending-bekken har kost 0 (samme som passiv
        produksjon). Vektet snitt trekkes ned tilsvarende.

        Ingen effekt hvis pending=0, eller hvis cargo allerede er fullt.
        """
        if state.pending_units <= 0:
            return 0
        player = game_state.player_state
        ship = game_state.world_state.ship
        current_total = sum(item.quantity for item in player.inventory.values())
        available_space = max(0, ship.cargo_capacity - current_total)
        if available_space <= 0:
            return 0
        realized = min(state.pending_units, available_space)
        pitch = player.inventory.setdefault(PITCH_ID, InventoryItem())
        old_qty = pitch.quantity
        new_qty = old_qty + realized
        if new_qty > 0:
            new_avg = (old_qty * pitch.avg_cost) / new_qty
            pitch.avg_cost = round(new_avg, 2)
        pitch.quantity = new_qty
        state.pending_units -= realized
        return realized
