"""EconomyState — markeder, regimer og "siste sett"-priser per havn.

Endres av RegimeManager (regimer), Market (markets) og scene-inngang i en
havn (observed-oppdatering).

I C1b har kun Tortuga faktisk innhold; de tre andre havnene har tomme
`MarketState()` og `regimes={}` som placeholders til C2 fyller dem med
port-bias-initiert data fra PortConfig.

`observed` har kun nøkler for havner spilleren har besøkt. Ingen nøkkel
= "aldri besøkt" (UI viser "aldri besøkt" uten pris-felt). Stale-grense
i `balance.observed.stale_threshold_days`.

Fase 3 (v2-schema, C3-0 stubs):
- `pending_sabotages`: bestilte sabotasje-effekter som lander ved
  impact_day. C3-10 wiring.
- `pending_rumor_impacts`: falske rykter (rumor_spread) som senker
  target-pris ved impact_day. C3-10 wiring.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from state.market_effects import PendingRumorImpact, PendingSabotage
from state.market_state import MarketState
from state.observed_price import ObservedPrice
from systems.regime_manager import RegimeState


# Havn-id-er kommer fra `config.port_config.get_all_port_ids()`.
# KNOWN_PORTS-konstanten ble fjernet i C2 — ports.json er nå autoritativ,
# og manglende konfig skal stoppe spillet ved oppstart, ikke la det kjøre
# videre med implisitt hardkodet liste.


@dataclass
class EconomyState:
    markets: dict[str, MarketState] = field(default_factory=dict)
    regimes: dict[str, dict[str, RegimeState]] = field(default_factory=dict)
    observed: dict[str, dict[str, ObservedPrice]] = field(default_factory=dict)
    # Fase 3 (v2-schema, C3-0 stubs — ikke koblet enda)
    pending_sabotages: list[PendingSabotage] = field(default_factory=list)
    pending_rumor_impacts: list[PendingRumorImpact] = field(default_factory=list)
