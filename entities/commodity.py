"""Vare (commodity) som handles paa borsen, samt spiller-inventar-post."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Commodity:
    """En vare med grunnpris, volatility og løpende markedspris."""

    id: str
    name: str
    base_price: float
    current_price: float
    volatility: float
    description: str = ""

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
