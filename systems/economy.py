"""Markedsimulering: pris-drift og kjop/salg.

Model (Fase 1, enkel):
- Hver `tick()` trekker en ny current_price per vare som
  `base_price * (1 + uniform(-volatility, volatility))`.
- Kjops- og salgspriser er current_price +/- `spread` (default 2%).
- Salg krever at inventaret har minst ønsket mengde; kjøp krever at
  gullet rekker.

Markedet eier tilstand for priser og for dag/tick-teller. Spillerens
gull og inventar ligger på et eget objekt (GameState i Commit 7); for
nå holdes de på VillageScene og refereres av ExchangeOverlay.
"""

from __future__ import annotations

import json
import random

from entities.commodity import Commodity, InventoryItem


#: Kjop/salg-margin begge veier (0.02 = 2% spread per PROSJEKT.md §6).
DEFAULT_SPREAD = 0.02


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

    # --- Tick / pris-drift ---

    def tick(self) -> None:
        """Trekk nye priser for alle varer. Inkrementer tick_id."""
        for c in self._commodities.values():
            factor = 1.0 + self._rng.uniform(-c.volatility, c.volatility)
            c.current_price = round(c.base_price * factor, 2)
        self._tick_id += 1

    @property
    def tick_id(self) -> int:
        """Monotont tall – UI kan cache tekst-surfaces per tick_id."""
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
    ) -> tuple[int, dict[str, InventoryItem], int]:
        """Forsøk å kjøpe `amount` av vare. Returner (nytt_gull, nytt_inventar, kjopt).

        Kjøper maks det gullet tillater hvis `amount` er mer enn mulig; returner
        `kjopt == 0` hvis ingenting kunne kjøpes. Modifiserer ikke input-argumentene
        (ren funksjon på immutable snapshot).

        Oppdaterer `avg_cost` som veid gjennomsnitt over alle kjoep.
        """
        if amount <= 0:
            return gold, inventory, 0
        price = self.buy_price(commodity_id)
        if price <= 0:
            return gold, inventory, 0
        max_affordable = gold // price
        bought = min(amount, max_affordable)
        if bought <= 0:
            return gold, inventory, 0
        new_inventory = dict(inventory)
        old = new_inventory.get(commodity_id, InventoryItem())
        new_qty = old.quantity + bought
        # Veid gjennomsnitt: vekt gammel snitt med gammel mengde og ny pris
        # med kjoept mengde.
        if new_qty > 0:
            new_avg = (old.quantity * old.avg_cost + bought * price) / new_qty
        else:
            new_avg = 0.0
        new_inventory[commodity_id] = InventoryItem(
            quantity=new_qty, avg_cost=new_avg
        )
        new_gold = gold - bought * price
        return new_gold, new_inventory, bought

    def sell(
        self,
        commodity_id: str,
        amount: int,
        gold: int,
        inventory: dict[str, InventoryItem],
    ) -> tuple[int, dict[str, InventoryItem], int]:
        """Forsøk å selge `amount` av vare. Returner (nytt_gull, nytt_inventar, solgt).

        Ved salg beholdes `avg_cost` uendret slik at spilleren fortsatt ser
        hva hun *betalte*. Naar qty naar 0 nullstilles avg_cost.
        """
        if amount <= 0:
            return gold, inventory, 0
        old = inventory.get(commodity_id, InventoryItem())
        have = old.quantity
        sold = min(amount, have)
        if sold <= 0:
            return gold, inventory, 0
        price = self.sell_price(commodity_id)
        new_inventory = dict(inventory)
        new_qty = have - sold
        new_avg = old.avg_cost if new_qty > 0 else 0.0
        new_inventory[commodity_id] = InventoryItem(
            quantity=new_qty, avg_cost=new_avg
        )
        new_gold = gold + sold * price
        return new_gold, new_inventory, sold
