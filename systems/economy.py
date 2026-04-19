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
    """Katalog over varer + tick-logikk for ÉN havn (p.t. Tortuga).

    Mutasjonspunkter som endrer `self._commodities[cid].current_price`
    eller `price_history` (og dermed trenger sync til
    `state.economy_state.markets[port_id]` for at save skal bli konsistent):
    - `on_dawn(regimes)`: daglig prisdrift
    - `buy(...)`: ingen pris-endring, bare inventory/gold
    - `sell(...)`: ingen pris-endring, bare inventory/gold
    - `clamp_to_price_bounds(cid)`: kalles ved load, pris-rydding
    - direkte ekstern mutasjon via `market.get(cid).current_price = ...`
      (brukes av VillageScene.__init__ for å hydrere Market fra state)

    buy/sell trenger derfor IKKE sync av MarketState, men on_dawn OG
    ekstern mutasjon gjør det. Caller (VillageScene) må synkronisere
    eksplisitt — se `sync_market_to_state` nedenfor.

    Tech-debt: Full refactor til "Market-on-MarketState" (Market som
    stateless logikk-klasse som opererer på MarketState-parameter)
    tas i C4 når PortVillageScene-parameterisering uansett tvinger
    det frem. Frem til da: dobbelt-representasjon med eksplisitt sync.
    """

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

        Drift- og støy-prosent leses fra balance.regimes hver dagstikk.
        Formelen er `change_pct = uniform(drift_pct_<regime>) + uniform(±noise_pct)`;
        stable har [0.0, 0.0]-range i default, så ren støy der.
        """
        reg_balance = _balance.get().regimes
        drift_by_regime: dict[str, tuple[float, float]] = {
            "rising":  reg_balance.drift_pct_rising,
            "stable":  reg_balance.drift_pct_stable,
            "falling": reg_balance.drift_pct_falling,
        }
        noise_pct = reg_balance.noise_pct
        for cid, c in self._commodities.items():
            regime = regimes.get(cid) if regimes else None
            regime_name = regime.current if regime is not None else "stable"
            drift_range = drift_by_regime.get(regime_name, (0.0, 0.0))
            if drift_range[0] == drift_range[1]:
                drift_pct = drift_range[0]
            else:
                drift_pct = self._rng.uniform(*drift_range)
            noise = self._rng.uniform(-noise_pct, noise_pct)
            change = (drift_pct + noise) / 100.0
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
        fee = _balance.get().economy.transaction_fee
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
        fee = _balance.get().economy.transaction_fee
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


def apply_regime_drift_to_market_state(
    market_state: MarketState,
    regimes: "dict[str, RegimeState]",
    base_prices: dict[str, float],
    rng: random.Random,
) -> None:
    """Ren drift-funksjon for én havns MarketState uten Market-klasse.

    Muterer `market_state.commodities[cid]` in-place etter samme formel
    som `Market.on_dawn`: `change_pct = uniform(drift_pct_<regime>) +
    uniform(±noise_pct)`. Klampes mot `[base * PRICE_MIN_MULT,
    base * PRICE_MAX_MULT]`. `price_history` trunkeres til siste
    `PRICE_HISTORY_WINDOW` dager.

    Brukes for ikke-Tortuga-havner ved new_day i VillageScene (Tortuga
    bruker Market.on_dawn fordi Market holder dens aktive Commodity-
    katalog for rendering).
    """
    reg_balance = _balance.get().regimes
    drift_by_regime: dict[str, tuple[float, float]] = {
        "rising":  reg_balance.drift_pct_rising,
        "stable":  reg_balance.drift_pct_stable,
        "falling": reg_balance.drift_pct_falling,
    }
    noise_pct = reg_balance.noise_pct

    for cid, commodity in market_state.commodities.items():
        base_price = base_prices.get(cid)
        if base_price is None:
            continue
        regime = regimes.get(cid)
        regime_name = regime.current if regime is not None else "stable"
        drift_range = drift_by_regime.get(regime_name, (0.0, 0.0))
        if drift_range[0] == drift_range[1]:
            drift_pct = drift_range[0]
        else:
            drift_pct = rng.uniform(*drift_range)
        noise = rng.uniform(-noise_pct, noise_pct)
        change = (drift_pct + noise) / 100.0
        new_price = commodity.current_price * (1.0 + change)
        lo = base_price * PRICE_MIN_MULT
        hi = base_price * PRICE_MAX_MULT
        new_price = max(lo, min(hi, new_price))
        commodity.current_price = round(new_price, 2)
        commodity.price_history.append(commodity.current_price)
        if len(commodity.price_history) > PRICE_HISTORY_WINDOW:
            del commodity.price_history[
                : len(commodity.price_history) - PRICE_HISTORY_WINDOW
            ]


def sync_market_to_state(market: "Market", market_state: MarketState) -> None:
    """Kopier Market-klassens nåværende Commodity-tilstand til MarketState.

    Brukes av VillageScene etter hver Market-mutasjon (on_dawn, og etter
    VillageScene.__init__-hydration) for at `state.economy_state.markets
    ["tortuga"]` er autoritativt speil av Market-klassen. Autosave leser
    direkte fra state, ikke fra Market.
    """
    for c in market.commodities:
        market_state.commodities[c.id] = CommodityMarket(
            current_price=float(c.current_price),
            price_history=list(c.price_history),
        )
