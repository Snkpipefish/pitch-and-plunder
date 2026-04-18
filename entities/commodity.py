"""Vare (commodity) som handles paa borsen."""

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
