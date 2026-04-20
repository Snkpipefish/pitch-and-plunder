"""Pending markeds-effekter — Fase 3 C3-10.

Én felles dataclass `PendingMarketEffect` representerer både sabotasje
(direction="up") og falske rykter (direction="down"). Forskjellen er
i HVORDAN effekten ble initiert (source_type) og i retningen på
prisbevegelsen.

Erstatter C3-0-stubene `PendingSabotage` og `PendingRumorImpact` som
var duplisert infrastruktur. Save-migrering ikke nødvendig — stubene
var aldri populert i lagrede saves.

**Felt:**
- `port_id`, `commodity_id`: target-paret. Sampling-logikk bor i
  `systems/market_effects.register_market_effect` eller tavern-
  handlere.
- `direction`: `"up"` (sabotasje — knapphet hever pris) eller `"down"`
  (falsk rykte — frykt dumper pris).
- `magnitude_pct`: absolutt prosent-verdi. Tegn håndteres via
  `direction`-feltet.
- `impact_day`: absolutt GameClock.day-verdi når effekten skal
  anvendes. Systems-logikken i `market_effects.on_dawn` fjerner og
  anvender effekter med `impact_day <= clock.day`.
- `source_type`: `"sabotage"` eller `"false_rumor"`. Brukes av
  rumor-systemet for å gi spike-varsler om pending effekter
  (C3-10-presisering #2).
"""

from __future__ import annotations

from dataclasses import dataclass


#: Gyldige direction-verdier.
DIRECTIONS: frozenset[str] = frozenset({"up", "down"})

#: Gyldige source_type-verdier (utvides ev. i senere commits).
SOURCE_TYPES: frozenset[str] = frozenset({"sabotage", "false_rumor"})


@dataclass
class PendingMarketEffect:
    """Én forestående prisbevegelse på en vare i en havn.

    Opprettes av `systems.market_effects.register_market_effect` når
    spilleren bestiller sabotasje eller sprer falskt rykte. Anvendes
    og fjernes av `systems.market_effects.on_dawn` på impact_day.
    """

    port_id: str = "port_royal"
    commodity_id: str = "sugar"
    direction: str = "up"  # "up" | "down"
    magnitude_pct: float = 10.0
    impact_day: int = 0
    source_type: str = "sabotage"  # "sabotage" | "false_rumor"
