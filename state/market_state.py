"""MarketState — per-havn snapshot av vare-priser.

Eksplisitt dataclass-hierarki (ikke dict[str, dict]) slik at typeannotasjoner
og JSON-parsing går via navngitte felter. Matcher mønsteret for de andre
state-objektene.

`current_price` og `price_history` er det som faktisk varierer per havn.
`base_price` er statisk fra `data/commodities.json` og lagres ikke — det
leses ved behov via Market.get(cid).base_price.
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
