"""Vare (commodity) som handles paa borsen, samt spiller-inventar-post."""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from systems.regime_manager import RegimeState


#: Hvor mange priser vi holder i historikken (for sparkline-visning).
PRICE_HISTORY_WINDOW = 20

#: Klamp-grenser for current_price i forhold til base_price.
#: Hindrer at random walk drifter til meningsløse ytterpunkter.
PRICE_MIN_MULT = 0.3
PRICE_MAX_MULT = 3.0


@dataclass
class Commodity:
    """En vare med grunnpris, volatility og løpende markedspris."""

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

    def tick(
        self,
        regime: "RegimeState | None" = None,
        rng: random.Random | None = None,
    ) -> None:
        """Oppdater current_price med random drift + eventuell regime-bias.

        - Regime-bias (ubetydelig per enkelt-tick, men akkumulerer over dager).
        - Vol-multiplier fra regimet (stable-regime demper amplituden).
        - Klamping mot [base*0.3, base*3.0] hindrer runaway.
        - price_history holder de siste PRICE_HISTORY_WINDOW prisene (for
          sparkline-visning og trend-lesning).
        """
        # Sen import for å unngå sirkulær avhengighet (regime_manager
        # refererer ikke Commodity, men vi holder type-hint bak TYPE_CHECKING).
        from systems.regime_manager import REGIME_BIAS, REGIME_VOL_MULT

        rng = rng or random.Random()
        if regime is None:
            bias = 0.0
            vol_mult = 1.0
        else:
            bias = REGIME_BIAS.get(regime.current, 0.0)
            vol_mult = REGIME_VOL_MULT.get(regime.current, 1.0)

        drift = rng.uniform(-self.volatility, self.volatility) * vol_mult
        new_price = self.current_price * (1.0 + bias + drift)
        # Klamp
        lo = self.base_price * PRICE_MIN_MULT
        hi = self.base_price * PRICE_MAX_MULT
        new_price = max(lo, min(hi, new_price))
        self.current_price = round(new_price, 2)

        self.price_history.append(self.current_price)
        if len(self.price_history) > PRICE_HISTORY_WINDOW:
            del self.price_history[: len(self.price_history) - PRICE_HISTORY_WINDOW]


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
