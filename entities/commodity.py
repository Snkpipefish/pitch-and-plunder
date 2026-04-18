"""Vare (commodity) som handles paa borsen, samt spiller-inventar-post.

Fase 2A Commit 5C: priser endres nå KUN ved daggry via `Market.on_dawn()`.
Commodity-klassen er derfor en ren dataholder; tidligere `Commodity.tick()`
er fjernet fordi drift-logikken lever i Market nå (ett sted for hele
markedsmodellen).
"""

from __future__ import annotations

from dataclasses import dataclass, field


#: Hvor mange priser vi holder i historikken (Fase 2A Commit 5C: 14 dager
#: = 2 uker). Trend-indikatoren leser de siste 3; lenger historikk er
#: tilgjengelig for framtidige UI-utvidelser.
PRICE_HISTORY_WINDOW = 14


@dataclass
class Commodity:
    """En vare med grunnpris, volatility og løpende markedspris.

    `price_history` akkumulerer ved daggry via `Market.on_dawn()`. Den
    brukes av `compute_trend()` for enkel pil-indikator og for framtidig
    visning (f.eks. sparkline som toggle i polish-commit).
    """

    id: str
    name: str
    base_price: float
    current_price: float
    volatility: float
    description: str = ""
    price_history: list[float] = field(default_factory=list)

    @classmethod
    def from_data(cls, data: dict) -> "Commodity":
        base = float(data["base_price"])
        return cls(
            id=data["id"],
            name=data["name"],
            base_price=base,
            current_price=base,
            volatility=float(data["volatility"]),
            description=data.get("description", ""),
        )


@dataclass
class InventoryItem:
    """En post i spillerens inventar: mengde + vektet gjennomsnittlig innkjoepspris.

    `avg_cost` oppdateres ved kjoep som veid gjennomsnitt over alle kjoep:
    `new_avg = (old_qty * old_avg + bought * buy_price) / (old_qty + bought)`
    Ved salg beholdes `avg_cost` uendret (spilleren skal se hva hun *betalte*,
    ikke hva hun har igjen i gjennomsnitt etter delsalg).
    """

    quantity: int = 0
    avg_cost: float = 0.0


# -----------------------------------------------------------------------------
# Trend-indikator (Fase 2A Commit 5C)
# -----------------------------------------------------------------------------

#: Rising: siste pris > startpris × (1 + TREND_THRESHOLD).
#: Falling: siste pris < startpris × (1 - TREND_THRESHOLD).
#: 3% terskel unngår at ren markedsstøy (±1% per dag fra on_dawn-noise)
#: viser feilaktig retning – skal være klar trend før pilen viser opp/ned.
TREND_THRESHOLD = 0.03

#: Antall siste priser som inspiseres for trend-beregning.
TREND_WINDOW = 3


def compute_trend(price_history: list[float]) -> str:
    """Returner trend-pil ('↑', '→', '↓') basert på siste 3 priser.

    Returnerer tom streng hvis historikken er kortere enn 3 dager – da har
    vi ikke nok signal til å vise trend med mening.

    Resultatet er fargekodet i exchange UI:
    ↑ i COLOR_STONE_LIT (kald blå, institusjonelt signal),
    → i COLOR_FOG (nøytral dempet), ↓ i COLOR_EMBER (varm advarsel).
    """
    if len(price_history) < TREND_WINDOW:
        return ""
    recent = price_history[-TREND_WINDOW:]
    start, end = recent[0], recent[-1]
    if start <= 0.0:
        return "\u2192"
    if end > start * (1.0 + TREND_THRESHOLD):
        return "\u2191"
    if end < start * (1.0 - TREND_THRESHOLD):
        return "\u2193"
    return "\u2192"
