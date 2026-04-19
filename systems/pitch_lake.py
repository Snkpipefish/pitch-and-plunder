"""Passiv bek-produksjon fra Pitch Lake på Trinidad (Fase 2A Commit 6).

Spilleren "arver" Pitch Lake ved spillstart. Lakeren produserer 2 bek
per dag automatisk ved daggry. Produksjon tapes hvis lasterom er fullt –
pitchen flyter bort, spilleren må aktivt kvitte seg med last for å
ikke miste inntekt.

Interaktiv utvinning med rør og pumper kommer i Fase 4.

Designvalg:
- `PitchLakeState` er ren dataholder (dataclass) som lagres i GameState
  slik at `total_produced` og `last_production_day` overlever saves. Gir
  stats-støtte for senere achievements.
- `PitchLake.on_new_day` er en statisk metode (ren funksjon på state).
  Ingen instansvariabler, ingen RNG — deterministisk produksjon.
- Produsert bek får `avg_cost=0` (gratis produksjon). Dette trekker ned
  vektet gjennomsnitt for eksisterende bek-inventar, slik at spilleren
  ser en lavere snittpris over tid. Det er bevisst: produksjons-bek er
  "gratis" fra spillerens synspunkt.
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
    total_produced: int = 0
    last_production_day: int = 0


class PitchLake:
    """Statisk produksjons-kalkulator. Muterer state og game_state direkte."""

    @staticmethod
    def on_new_day(
        state: PitchLakeState,
        game_state: "GameState",
    ) -> int:
        """Kalles ved daggry. Returnerer antall bek faktisk produsert.

        - Hvis lasterom har plass: produserer `state.production_per_day`
          (eller hva som får plass om det er mindre).
        - Hvis lasterom er fullt: `produced == 0` og pitchen går tapt.
          `total_produced` og `last_production_day` oppdateres uansett.

        `avg_cost` på pitch-inventaret oppdateres som vektet gjennomsnitt
        der produsert bek teller som 0-kost.
        """
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
                # Vektet snitt: gammel snitt beholder sin vekt (old_qty),
                # produsert bek har kost 0. Avrundet til 2 desimaler for
                # UI-konsistens med buy()-resultater.
                new_avg = (old_qty * pitch.avg_cost) / new_qty
                pitch.avg_cost = round(new_avg, 2)
            pitch.quantity = new_qty

        state.total_produced += produced
        state.last_production_day = game_state.clock.day
        return produced
