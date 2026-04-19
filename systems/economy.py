"""Markedsimulering: pris-drift og kjop/salg.

Model (Fase 2A Commit 5C):
- Priser er **statiske innen en dag** og endres kun ved daggry via
  `Market.on_dawn(regimes)`. Ingen per-tick-drift.
- Daglig endring = `regime_direction * magnitude + noise`, hvor
  magnitude ∈ [0.02, 0.04] (2–4%) og noise ∈ [-0.01, 0.01] (±1%).
- Pris klampes til `[base * 0.5, base * 2.0]` – strammere enn Fase 1
  (0.3–3.0) for at spread på 2% skal være meningsfullt friksjonsledd.
- `price_history` holdes til 14 dager (2 uker) per `PRICE_HISTORY_WINDOW`.
- Kjops-/salgspriser er `current_price ± spread` (default 2%).
"""

from __future__ import annotations

import json
import random
from typing import TYPE_CHECKING

import constants
from entities.commodity import PRICE_HISTORY_WINDOW, Commodity, InventoryItem

if TYPE_CHECKING:
    from systems.regime_manager import RegimeState


#: Kjop/salg-margin begge veier (0.02 = 2% spread per PROSJEKT.md §6).
DEFAULT_SPREAD = 0.02

#: Daglig endring fra regime-retning (±2–4% per dag).
DAILY_MAGNITUDE_MIN = 0.02
DAILY_MAGNITUDE_MAX = 0.04

#: Uavhengig markedsstøy per dag (±1% ≤ DAILY_MAGNITUDE_MIN slik at ren
#: støy ikke trigger trend-indikator-terskel på 3%).
DAILY_NOISE = 0.01

#: Klamp-grenser for current_price i forhold til base_price. Strammet
#: fra Fase 1 (0.3, 3.0) til Fase 2A (0.5, 2.0) slik at spread + gebyr
#: blir reell friksjon uansett hvor prisen står.
PRICE_MIN_MULT = 0.5
PRICE_MAX_MULT = 2.0

#: Regime-retning som multiplier på `magnitude`.
_REGIME_DIRECTION: dict[str, float] = {
    "rising": 1.0,
    "stable": 0.0,
    "falling": -1.0,
}


class Market:
    """Katalog over varer + tick-logikk."""

    def __init__(
        self,
        commodities: list[Commodity],
        spread: float = DEFAULT_SPREAD,
        rng: random.Random | None = None,
    ) -> None:
        self._commodities: dict[str, Commodity] = {c.id: c for c in commodities}
        self._order: list[str] = [c.id for c in commodities]
        self._spread = spread
        self._rng = rng or random.Random()
        self._tick_id: int = 0

    @classmethod
    def from_json(cls, path: str) -> "Market":
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return cls([Commodity.from_data(entry) for entry in data["commodities"]])

    def clamp_to_price_bounds(self, commodity_id: str) -> None:
        """Klamp `current_price` og `price_history` for én vare mot gjeldende
        pris-grenser `[base * PRICE_MIN_MULT, base * PRICE_MAX_MULT]`.

        Brukes ved load av gamle saves der `base_price` er justert (f.eks.
        Fase 2A Commit 5D: bek 55 → 40). Uten clamp ville historiske priser
        utenfor nye grenser feilinformere trend-indikatoren; current_price
        ville først bli klampet ved neste `on_dawn`.
        """
        c = self._commodities[commodity_id]
        lo = c.base_price * PRICE_MIN_MULT
        hi = c.base_price * PRICE_MAX_MULT
        c.current_price = round(max(lo, min(hi, c.current_price)), 2)
        c.price_history = [
            round(max(lo, min(hi, p)), 2) for p in c.price_history
        ]

    # --- Daglig pris-drift (ved daggry) ---

    def on_dawn(
        self,
        regimes: "dict[str, RegimeState] | None" = None,
    ) -> None:
        """Kalles ved daggry (dag-skift). Oppdaterer alle priser én gang.

        Per vare:
          change = direction * magnitude + noise
          new_price = current_price * (1 + change)
          new_price = clamp(new_price, base*0.5, base*2.0)
          price_history.append(new_price)   # siste 14 dager beholdes
          tick_id += 1

        `regimes` er dict fra commodity.id → RegimeState. Mangler regime
        for en vare tolkes som "stable" (ingen retnings-bias).
        """
        for cid, c in self._commodities.items():
            regime = regimes.get(cid) if regimes else None
            direction = (
                _REGIME_DIRECTION.get(regime.current, 0.0)
                if regime is not None
                else 0.0
            )
            magnitude = self._rng.uniform(
                DAILY_MAGNITUDE_MIN, DAILY_MAGNITUDE_MAX
            )
            noise = self._rng.uniform(-DAILY_NOISE, DAILY_NOISE)
            change = direction * magnitude + noise
            new_price = c.current_price * (1.0 + change)
            lo = c.base_price * PRICE_MIN_MULT
            hi = c.base_price * PRICE_MAX_MULT
            new_price = max(lo, min(hi, new_price))
            c.current_price = round(new_price, 2)
            c.price_history.append(c.current_price)
            if len(c.price_history) > PRICE_HISTORY_WINDOW:
                del c.price_history[
                    : len(c.price_history) - PRICE_HISTORY_WINDOW
                ]
        self._tick_id += 1

    @property
    def tick_id(self) -> int:
        """Monotont tall – UI cacher tekst-surfaces per tick_id. Inkrementeres
        kun av `on_dawn()` fra og med Commit 5C (tidligere også per 10 s-tick)."""
        return self._tick_id

    # --- Oppslag ---

    @property
    def commodities(self) -> list[Commodity]:
        return [self._commodities[cid] for cid in self._order]

    def get(self, commodity_id: str) -> Commodity:
        return self._commodities[commodity_id]

    # --- Priser med spread ---

    def buy_price(self, commodity_id: str) -> int:
        """Pris for å kjøpe 1 enhet (avrundet til hel dubloon)."""
        return int(round(self._commodities[commodity_id].current_price * (1 + self._spread)))

    def sell_price(self, commodity_id: str) -> int:
        """Pris for å selge 1 enhet (avrundet til hel dubloon)."""
        return int(round(self._commodities[commodity_id].current_price * (1 - self._spread)))

    # --- Transaksjoner ---

    def buy(
        self,
        commodity_id: str,
        amount: int,
        gold: int,
        inventory: dict[str, InventoryItem],
        cargo_capacity: int | None = None,
    ) -> tuple[int, dict[str, InventoryItem], int]:
        """Forsøk å kjøpe `amount` av vare. Returner (nytt_gull, nytt_inventar, kjopt).

        Kjøper maks det gullet tillater gitt pris + `TRANSACTION_FEE`
        (flat gebyr per handel, ikke per enhet). Hvis `cargo_capacity`
        er satt, klampes også mot tilgjengelig lasterom.

        Transaksjon skjer kun hvis minst 1 enhet faktisk kan kjøpes;
        ingen gebyr trekkes hvis `bought == 0` (ingen handel).

        Modifiserer ikke input-argumentene (ren funksjon på immutable
        snapshot). Oppdaterer `avg_cost` som veid gjennomsnitt per kjøp –
        gebyret teller IKKE inn i avg_cost (det er en transaksjonskost,
        ikke en vare-kost).
        """
        if amount <= 0:
            return gold, inventory, 0
        price = self.buy_price(commodity_id)
        if price <= 0:
            return gold, inventory, 0
        fee = constants.TRANSACTION_FEE
        # Må kunne dekke minst 1 enhet + gebyr for å i det hele tatt handle.
        if gold < price + fee:
            return gold, inventory, 0
        max_affordable = (gold - fee) // price
        bought = min(amount, max_affordable)
        if cargo_capacity is not None:
            current_total = sum(
                item.quantity for item in inventory.values()
            )
            cargo_space = max(0, cargo_capacity - current_total)
            bought = min(bought, cargo_space)
        if bought <= 0:
            return gold, inventory, 0
        new_inventory = dict(inventory)
        old = new_inventory.get(commodity_id, InventoryItem())
        new_qty = old.quantity + bought
        # Veid gjennomsnitt: vekt gammel snitt med gammel mengde og ny pris
        # med kjøpt mengde. Gebyret teller ikke som en del av varekosten.
        if new_qty > 0:
            new_avg = (old.quantity * old.avg_cost + bought * price) / new_qty
        else:
            new_avg = 0.0
        new_inventory[commodity_id] = InventoryItem(
            quantity=new_qty, avg_cost=new_avg
        )
        new_gold = gold - bought * price - fee
        return new_gold, new_inventory, bought

    def sell(
        self,
        commodity_id: str,
        amount: int,
        gold: int,
        inventory: dict[str, InventoryItem],
    ) -> tuple[int, dict[str, InventoryItem], int]:
        """Forsøk å selge `amount` av vare. Returner (nytt_gull, nytt_inventar, solgt).

        Trekker `TRANSACTION_FEE` én gang fra inntekten. Hvis netto-
        inntekt (sold*sell_price - fee) er negativ blir handelen refusert
        (spilleren skal ikke tape penger på å selge); dette slår sjelden
        til i praksis siden sell_price >> fee for alle fire varer.

        Ved salg beholdes `avg_cost` uendret slik at spilleren fortsatt
        ser hva hun *betalte*. Når qty når 0 nullstilles avg_cost.
        """
        if amount <= 0:
            return gold, inventory, 0
        old = inventory.get(commodity_id, InventoryItem())
        have = old.quantity
        sold = min(amount, have)
        if sold <= 0:
            return gold, inventory, 0
        price = self.sell_price(commodity_id)
        fee = constants.TRANSACTION_FEE
        proceeds = sold * price - fee
        if proceeds < 0:
            # Edge case: selge gir netto tap. Refuser handelen.
            return gold, inventory, 0
        new_inventory = dict(inventory)
        new_qty = have - sold
        new_avg = old.avg_cost if new_qty > 0 else 0.0
        new_inventory[commodity_id] = InventoryItem(
            quantity=new_qty, avg_cost=new_avg
        )
        new_gold = gold + proceeds
        return new_gold, new_inventory, sold
