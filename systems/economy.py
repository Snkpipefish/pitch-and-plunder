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

from entities.commodity import PRICE_HISTORY_WINDOW, Commodity, InventoryItem
from state.market_state import CommodityMarket, MarketState
from systems import balance as _balance

if TYPE_CHECKING:
    from config.port_config import PortConfig
    from systems.regime_manager import RegimeState


#: Kjop/salg-margin begge veier (0.02 = 2% spread per PROSJEKT.md §6).
DEFAULT_SPREAD = 0.02

#: Klamp-grenser for current_price i forhold til base_price. Strammet
#: fra Fase 1 (0.3, 3.0) til Fase 2A (0.5, 2.0) slik at spread + gebyr
#: blir reell friksjon uansett hvor prisen står.
PRICE_MIN_MULT = 0.5
PRICE_MAX_MULT = 2.0


class Market:
    """Stateless markedsfunksjoner over vare-katalog.

    Refactored i Fase 2B C4: Market holder ikke lenger egen
    Commodity-katalog med mutable pris-state. Pris-state lever kun i
    `MarketState.commodities[cid]` (per havn). Market er kun katalog
    (base_prices + navn + rekkefølge) + logikk (drift-formel, kjøp/salg-
    kalkyle).

    Én Market-instans brukes for ALLE havner. `on_dawn/buy/sell/...`
    tar `state: MarketState` som parameter — samme Market kan operere
    på Tortugas, Port Royals, Havanas, Nassaus markeder vekselvis.

    Catalog inneholder:
    - `base_price` — brukt til pris-klamp og catalog-iterasjon
    - `name`, `id` — vare-metadata
    - `volatility` — ubrukt i C4 (legacy-felt), beholdes for evt. fremtid

    UI-caching: `MarketState.tick_id` inkrementeres av `on_dawn`.
    Eksterne cachere (exchange-overlay) invaliderer rendrede priser når
    tick_id endrer seg.
    """

    def __init__(
        self,
        commodities: list[Commodity],
        spread: float = DEFAULT_SPREAD,
        rng: random.Random | None = None,
    ) -> None:
        # Katalog er immutable: vi bruker Commodity kun for base_price+navn,
        # IKKE som aktiv pris-container. `current_price`/`price_history`-
        # feltene på Commodity er ignorert her — state fra MarketState
        # er autoritativt.
        self._catalog: dict[str, Commodity] = {c.id: c for c in commodities}
        self._order: list[str] = [c.id for c in commodities]
        self._spread = spread
        self._rng = rng or random.Random()

    @classmethod
    def from_json(cls, path: str) -> "Market":
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return cls([Commodity.from_data(entry) for entry in data["commodities"]])

    # --- Katalog-oppslag (immutable) ---

    @property
    def commodities(self) -> list[Commodity]:
        """Katalog-iterasjon (base_price + navn). Priser lever ikke her."""
        return [self._catalog[cid] for cid in self._order]

    def get(self, commodity_id: str) -> Commodity:
        """Hent Commodity fra katalog (base_price + navn)."""
        return self._catalog[commodity_id]

    def base_price(self, commodity_id: str) -> float:
        return self._catalog[commodity_id].base_price

    # --- Pris-klamp ---

    def clamp_to_price_bounds(
        self, state: MarketState, commodity_id: str
    ) -> None:
        """Klamp `current_price` og `price_history` i `state` mot
        `[base * PRICE_MIN_MULT, base * PRICE_MAX_MULT]`.

        Brukes ved load av gamle saves der `base_price` er justert (f.eks.
        Fase 2A Commit 5D: bek 55 → 40). Uten clamp ville historiske priser
        utenfor nye grenser feilinformere trend-indikatoren.
        """
        if commodity_id not in state.commodities:
            return
        cm = state.commodities[commodity_id]
        base = self._catalog[commodity_id].base_price
        lo = base * PRICE_MIN_MULT
        hi = base * PRICE_MAX_MULT
        cm.current_price = round(max(lo, min(hi, cm.current_price)), 2)
        cm.price_history = [
            round(max(lo, min(hi, p)), 2) for p in cm.price_history
        ]

    # --- Daglig pris-drift (ved daggry) ---

    def on_dawn(
        self,
        state: MarketState,
        regimes: "dict[str, RegimeState] | None" = None,
    ) -> None:
        """Oppdater alle priser i `state` én gang (kall ved daggry).

        Per vare:
          change = uniform(drift_pct_<regime>) + uniform(±noise_pct)
          new_price = current_price * (1 + change/100)
          clamp mot [base*PRICE_MIN_MULT, base*PRICE_MAX_MULT]
          price_history.append(new_price)   # siste 14 dager beholdes

        `regimes` mapper commodity_id → RegimeState. Manglende regime
        tolkes som "stable" (ren støy-drift).

        Drift- og støy-prosent leses fra balance.regimes. stable har
        [0.0, 0.0]-range i default, så ren støy der.

        Inkrementerer `state.tick_id` ved slutten slik at UI-cachere
        invaliderer rendrede priser. Erstatter `apply_regime_drift_to_market_state`
        som fantes i C2 (samme funksjon, nå fusjonert inn i Market).
        """
        reg_balance = _balance.get().regimes
        drift_by_regime: dict[str, tuple[float, float]] = {
            "rising":  reg_balance.drift_pct_rising,
            "stable":  reg_balance.drift_pct_stable,
            "falling": reg_balance.drift_pct_falling,
        }
        noise_pct = reg_balance.noise_pct
        for cid, cm in state.commodities.items():
            if cid not in self._catalog:
                continue
            base = self._catalog[cid].base_price
            regime = regimes.get(cid) if regimes else None
            regime_name = regime.current if regime is not None else "stable"
            drift_range = drift_by_regime.get(regime_name, (0.0, 0.0))
            if drift_range[0] == drift_range[1]:
                drift_pct = drift_range[0]
            else:
                drift_pct = self._rng.uniform(*drift_range)
            noise = self._rng.uniform(-noise_pct, noise_pct)
            change = (drift_pct + noise) / 100.0
            new_price = cm.current_price * (1.0 + change)
            lo = base * PRICE_MIN_MULT
            hi = base * PRICE_MAX_MULT
            new_price = max(lo, min(hi, new_price))
            cm.current_price = round(new_price, 2)
            cm.price_history.append(cm.current_price)
            if len(cm.price_history) > PRICE_HISTORY_WINDOW:
                del cm.price_history[
                    : len(cm.price_history) - PRICE_HISTORY_WINDOW
                ]
        state.tick_id += 1

    # --- Priser med spread ---

    def buy_price(self, state: MarketState, commodity_id: str) -> int:
        """Pris for å kjøpe 1 enhet (avrundet til hel dubloon)."""
        cm = state.commodities.get(commodity_id)
        if cm is None:
            return 0
        return int(round(cm.current_price * (1 + self._spread)))

    def sell_price(self, state: MarketState, commodity_id: str) -> int:
        """Pris for å selge 1 enhet (avrundet til hel dubloon)."""
        cm = state.commodities.get(commodity_id)
        if cm is None:
            return 0
        return int(round(cm.current_price * (1 - self._spread)))

    # --- Transaksjoner ---

    def buy(
        self,
        state: MarketState,
        commodity_id: str,
        amount: int,
        gold: int,
        inventory: dict[str, InventoryItem],
        cargo_capacity: int | None = None,
    ) -> tuple[int, dict[str, InventoryItem], int]:
        """Forsøk å kjøpe `amount` av vare. Returner (nytt_gull, nytt_inventar, kjopt).

        Kjøper maks det gullet tillater gitt pris + `transaction_fee`
        (flat gebyr per handel). Hvis `cargo_capacity` er satt, klampes
        også mot tilgjengelig lasterom.

        Transaksjon skjer kun hvis minst 1 enhet faktisk kan kjøpes;
        ingen gebyr trekkes hvis `bought == 0`. Inventar kopieres (ren
        funksjon), `state` ikke mutert av buy.
        """
        if amount <= 0:
            return gold, inventory, 0
        price = self.buy_price(state, commodity_id)
        if price <= 0:
            return gold, inventory, 0
        fee = _balance.get().economy.transaction_fee
        if gold < price + fee:
            return gold, inventory, 0
        max_affordable = (gold - fee) // price
        bought = min(amount, max_affordable)
        if cargo_capacity is not None:
            current_total = sum(item.quantity for item in inventory.values())
            cargo_space = max(0, cargo_capacity - current_total)
            bought = min(bought, cargo_space)
        if bought <= 0:
            return gold, inventory, 0
        new_inventory = dict(inventory)
        old = new_inventory.get(commodity_id, InventoryItem())
        new_qty = old.quantity + bought
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
        state: MarketState,
        commodity_id: str,
        amount: int,
        gold: int,
        inventory: dict[str, InventoryItem],
    ) -> tuple[int, dict[str, InventoryItem], int]:
        """Forsøk å selge `amount` av vare. Returner (nytt_gull, nytt_inventar, solgt).

        Trekker `transaction_fee` én gang fra inntekten. Handelen
        refuseres hvis netto-inntekt (sold*sell_price - fee) er negativ.
        Ved salg beholdes `avg_cost` uendret; nullstilles når qty når 0.
        """
        if amount <= 0:
            return gold, inventory, 0
        old = inventory.get(commodity_id, InventoryItem())
        have = old.quantity
        sold = min(amount, have)
        if sold <= 0:
            return gold, inventory, 0
        price = self.sell_price(state, commodity_id)
        fee = _balance.get().economy.transaction_fee
        proceeds = sold * price - fee
        if proceeds < 0:
            return gold, inventory, 0
        new_inventory = dict(inventory)
        new_qty = have - sold
        new_avg = old.avg_cost if new_qty > 0 else 0.0
        new_inventory[commodity_id] = InventoryItem(
            quantity=new_qty, avg_cost=new_avg
        )
        new_gold = gold + proceeds
        return new_gold, new_inventory, sold


# -----------------------------------------------------------------------------
# Per-havn initialisering og drift (Fase 2B C2)
# -----------------------------------------------------------------------------

def load_base_prices(path: str) -> dict[str, float]:
    """Les base_price per vare fra `data/commodities.json`.

    Returnerer dict[commodity_id, base_price]. Brukes av save.py
    (migrering og new_game) og VillageScene (per-havn drift for ikke-
    Tortuga).
    """
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    return {
        entry["id"]: float(entry["base_price"])
        for entry in data["commodities"]
    }


def init_market_for_port(
    port_config: "PortConfig",
    base_prices: dict[str, float],
) -> MarketState:
    """Bygg en fersk `MarketState` for en havn basert på port-bias.

    For hver vare: `current_price = base_price * price_bias[cid]`,
    `price_history` tom. Brukes ved new_game og ved v4→v5-migrering
    for ikke-Tortuga-havner (Tortuga bevarer v4-data).
    """
    commodities: dict[str, CommodityMarket] = {}
    for cid, base_price in base_prices.items():
        bias = port_config.price_bias.get(cid, 1.0)
        commodities[cid] = CommodityMarket(
            current_price=round(base_price * bias, 2),
            price_history=[],
        )
    return MarketState(commodities=commodities)


# `apply_regime_drift_to_market_state` er fusjonert inn i `Market.on_dawn`
# i Fase 2B C4. Én Market-instans kan nå operere på alle havners
# MarketState — ingen behov for en separat pure-funksjon.
#
# `sync_market_to_state` slettet i C4: Market er stateless, så ingen
# dobbelt-representasjon å synkronisere. State.markets[port_id] er
# eneste sannhet.
