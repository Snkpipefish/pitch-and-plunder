"""PitchLakeState — Pitch Lake-produksjon, bufret for fravær.

Spec §2.1 lister `home_port`, `production_per_day`, `upkeep_per_day`,
`pending_units`. `total_produced` og `last_production_day` er preservert
fra Fase 2A — HUD bruker `last_production_day < clock.day - 1` for
"halted"-deteksjon (Commit 6.1). Disse fases trolig ut når interaktiv
bek-utvinning (Fase 4) erstatter passiv produksjon.

Rename fra 2A: `daily_upkeep_cost` → `upkeep_per_day` (matcher
`data/balance.json`-feltnavn).

`pending_units`: når spilleren er vekk fra Tortuga (home_port != current_port)
akkumuleres produksjonen her. Ved retur flyttes enheter opp til ledig
cargo-kapasitet (C7).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PitchLakeState:
    home_port: str = "tortuga"
    production_per_day: int = 0
    upkeep_per_day: int = 0
    pending_units: int = 0
    total_produced: int = 0
    last_production_day: int = 0
    #: Fase 3 (v2-schema) C3-0 stub. Gates bek-produksjon: False → ingen
    #: produksjon eller upkeep. True → aktiv. C3-6 wirer dette inn i
    #: PitchLake.on_new_day som tidlig-return. v5→v6-migrering (C3-1)
    #: setter True for eksisterende dev-saves; ny save starter False.
    purchased: bool = False

    @classmethod
    def new_default(cls) -> "PitchLakeState":
        """Bygger en PitchLakeState for fresh save (Fase 3 C3-6).

        Fresh v6-save: `purchased=False` og `production_per_day=0`/
        `upkeep_per_day=0`. Spillet kjører uten bek-produksjon før
        spilleren kjøper anlegget via tavern-dag-meny i Tortuga, som
        setter `purchased=True` og fyller produksjons-verdier fra
        `balance.pitch_lake`.

        Migrerte v5-saves går IKKE gjennom denne funksjonen — de
        beholder sine v5-produksjons-verdier (typisk 2/8) og får
        `purchased=True` satt av migrate_v5_to_v6. Dette sikrer at
        eksisterende dev-saves fortsetter å produsere uavbrutt.

        Egen klassemetode i stedet for `field(default_factory=...)`
        fordi asdict/dict-unpacking skal gi forutsigbare verdier i
        load() — defaults brukes KUN ved ny save (ikke ved migrering),
        og da går det via denne funksjonen eksplisitt.
        """
        return cls(
            home_port="tortuga",
            production_per_day=0,
            upkeep_per_day=0,
            pending_units=0,
            total_produced=0,
            last_production_day=0,
            purchased=False,
        )
