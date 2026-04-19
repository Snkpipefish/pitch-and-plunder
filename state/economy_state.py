"""EconomyState — markeder, regimer og "siste sett"-priser per havn.

Endres av RegimeManager (regimer), Market (markets) og scene-inngang i en
havn (observed-oppdatering).

I C1b har kun Tortuga faktisk innhold; de tre andre havnene har tomme
`MarketState()` og `regimes={}` som placeholders til C2 fyller dem med
port-bias-initiert data fra PortConfig.

`observed` har kun nøkler for havner spilleren har besøkt. Ingen nøkkel
= "aldri besøkt" (UI viser "aldri besøkt" uten pris-felt). Stale-grense
i `balance.observed.stale_threshold_days`.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from state.market_state import MarketState
from state.observed_price import ObservedPrice
from systems.regime_manager import RegimeState


#: Port-id for alle 4 havner. Tortuga først siden den er home_port og
#: den eneste spillbare i C1b. Port Royal, Havana, Nassau aktiveres i C6.
KNOWN_PORTS: tuple[str, ...] = ("tortuga", "port_royal", "havana", "nassau")


@dataclass
class EconomyState:
    markets: dict[str, MarketState] = field(default_factory=dict)
    regimes: dict[str, dict[str, RegimeState]] = field(default_factory=dict)
    observed: dict[str, dict[str, ObservedPrice]] = field(default_factory=dict)
