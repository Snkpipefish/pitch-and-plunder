"""MarketState — per-havn snapshot av vare-priser.

Eksplisitt dataclass-hierarki (ikke dict[str, dict]) slik at typeannotasjoner
og JSON-parsing går via navngitte felter. Matcher mønsteret for de andre
state-objektene.

`current_price` og `price_history` er det som faktisk varierer per havn.
`base_price` er statisk fra `data/commodities.json` og lagres ikke — det
leses ved behov via Market.catalog[cid].base_price.

`tick_id` flyttet hit fra Market-klassen i Fase 2B C4 da Market ble
stateless. Brukes av UI-caching (exchange-overlay) for å invalidere
rendrede prisverdier ved hvert daggry.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class CommodityMarket:
    current_price: float
    price_history: list[float] = field(default_factory=list)


@dataclass
class MarketState:
    commodities: dict[str, CommodityMarket] = field(default_factory=dict)
    #: Monotont økende counter — inkrementeres av Market.on_dawn. UI
    #: invaliderer prisflater når denne endrer seg. Eksisterende v5-
    #: saves uten feltet får 0 ved parse (bak-kompatibel default).
    tick_id: int = 0
