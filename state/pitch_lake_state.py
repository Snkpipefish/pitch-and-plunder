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

from systems import balance as _balance


def _default_production_per_day() -> int:
    return _balance.get().pitch_lake.production_per_day


def _default_upkeep_per_day() -> int:
    return _balance.get().pitch_lake.upkeep_per_day


@dataclass
class PitchLakeState:
    home_port: str = "tortuga"
    production_per_day: int = 0
    upkeep_per_day: int = 0
    pending_units: int = 0
    total_produced: int = 0
    last_production_day: int = 0

    @classmethod
    def new_default(cls) -> "PitchLakeState":
        """Bygger en PitchLakeState med defaults fra balance.

        Egen klassemetode i stedet for `field(default_factory=...)` fordi
        asdict/dict-unpacking skal gi forutsigbare verdier i load() —
        defaults brukes KUN ved ny save (ikke ved migrering), og da går
        det via denne funksjonen eksplisitt.
        """
        return cls(
            home_port="tortuga",
            production_per_day=_default_production_per_day(),
            upkeep_per_day=_default_upkeep_per_day(),
            pending_units=0,
            total_produced=0,
            last_production_day=0,
        )
