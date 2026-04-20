"""Markeds-effekt-system — Fase 3 C3-10.

Felles infrastruktur for sabotasje (`direction="up"`) og falske rykter
(`direction="down"`). Begge mekanismer delegeres via samme registrering
(`register_market_effect`) og anvendelse (`on_dawn`).

**Lifecycle:**

1. Spilleren bestiller handling i tavern-natt-meny:
   - `order_sabotage`: gull 50, mistanke +15, magnitude +10%
   - `spread_false_rumor`: gull 40, mistanke +8, magnitude −10%
2. Tavern-handler kaller `register_market_effect(...)` med korrekt
   direction + source_type. Impact_day = clock.day + balance.sabotage.
   impact_delay_days (default 2).
3. Effekten lagres i `EconomyState.pending_market_effects`.
4. Ved hver `tick_all_ports_dawn` kalles `market_effects.on_dawn(state,
   market)` etter rumors.on_dawn. Effekter hvis `impact_day <= clock.day`
   anvendes via `_apply_effect` og fjernes fra listen.
5. Anvendelse: multipliserer `CommodityMarket.current_price` med
   `(1 + magnitude_pct/100)` for "up" eller `(1 - magnitude_pct/100)`
   for "down". Floor på 1.0 for å unngå degenererte priser. Bumper
   `MarketState.tick_id` slik at exchange-UI caches invalideres.
6. Ingen klamping mot base × 0.5/2.0 her — Market.on_dawn klamper
   uansett ved neste dawn. Pending effects kan midlertidig pushe
   priser utenfor normal range; neste drift klamper tilbake.

**Integrasjon med rumor-system** (C3-10-presisering #2):
`systems.rumors._find_spike_candidates` inkluderer nå pending market-
effects i tillegg til volatile regimer. Pending effects har forrang
ved samme (port, commodity) — "nyere info" om prisen.

**Target-sampling** (`sample_target`):
Sampler tilfeldig (port, commodity) blant ikke-current-havner × 4
commodities. Brukes av tavern-handlere for å velge target uten egen
sub-dialog (C3-10-presisering #3). Kan replaces med interaktivt
valg i senere commit hvis brukertest viser behov.
"""

from __future__ import annotations

import random
from typing import TYPE_CHECKING, Optional

from config import port_config
from state.market_effects import PendingMarketEffect

if TYPE_CHECKING:
    from state.game_state import GameState
    from systems.economy import Market


#: Commodities som kan være target. Matcher
#: `config.port_config.REQUIRED_COMMODITIES`.
_COMMODITIES: tuple[str, ...] = ("sugar", "rum", "tobacco", "pitch")

#: Absolutt minimum current_price — defensivt mot stacking-negative-
#: effekter som ville gi <=0 pris. Market.on_dawn klamper til base×0.5
#: uansett ved neste dawn.
_MIN_PRICE_FLOOR = 1.0


def sample_target(
    state: "GameState",
    exclude_port: Optional[str] = None,
    rng: Optional[random.Random] = None,
) -> Optional[tuple[str, str]]:
    """Sample tilfeldig (port, commodity) fra andre havner enn `exclude_port`.

    Brukes av sabotasje- og falsk-rykte-handlerne. Returnerer None
    (degenerert — kun én havn finnes, eller alle ble ekskludert).
    """
    rng = rng or random.Random()
    other_ports = [
        p for p in port_config.get_all_port_ids() if p != exclude_port
    ]
    if not other_ports:
        return None
    return (rng.choice(other_ports), rng.choice(_COMMODITIES))


def register_market_effect(
    state: "GameState",
    port_id: str,
    commodity_id: str,
    direction: str,
    magnitude_pct: float,
    source_type: str,
    impact_delay_days: int,
) -> PendingMarketEffect:
    """Registrer en ny pending effekt. Returnerer det nye objektet.

    `impact_day = clock.day + impact_delay_days`. Caller er ansvarlig
    for gull-trekk, suspicion-increase, rest-decay — denne funksjonen
    gjør KUN registrering.
    """
    clock_day = state.world_state.clock.day
    effect = PendingMarketEffect(
        port_id=port_id,
        commodity_id=commodity_id,
        direction=direction,
        magnitude_pct=magnitude_pct,
        impact_day=clock_day + impact_delay_days,
        source_type=source_type,
    )
    state.economy_state.pending_market_effects.append(effect)
    return effect


def _apply_effect(state: "GameState", effect: PendingMarketEffect) -> None:
    """Muterer CommodityMarket.current_price basert på direction +
    magnitude_pct. Bumper tick_id for cache-invalidering."""
    market_state = state.economy_state.markets.get(effect.port_id)
    if market_state is None:
        return
    cm = market_state.commodities.get(effect.commodity_id)
    if cm is None:
        return
    delta_pct = effect.magnitude_pct
    if effect.direction == "down":
        delta_pct = -delta_pct
    new_price = cm.current_price * (1.0 + delta_pct / 100.0)
    cm.current_price = max(_MIN_PRICE_FLOOR, new_price)
    # Bump tick_id så exchange-overlay cache invalideres.
    market_state.tick_id += 1


def on_dawn(state: "GameState") -> list[PendingMarketEffect]:
    """Anvend alle pending effekter med `impact_day <= clock.day`.

    Returnerer listen av anvendte effekter (for ev. toast-varsling
    eller testing). Muterer state: markeds-priser + fjerner anvendte
    effekter fra pending-listen.

    Kalles fra `economy.tick_all_ports_dawn` etter suspicion og rumors
    on_dawn. Rekkefølge-avhengighet: market.on_dawn (regime-drift)
    kjører FØR denne funksjonen i samme dawn-pipeline, så pending
    effekter kommer på TOPP av dagens drift-baserte pris.

    Multi-day voyage: tick_all_ports_dawn kalles N ganger, denne
    funksjonen evaluerer `impact_day <= clock.day` per dawn. Så en
    effekt registrert med impact_delay=2 på dag 1 vil få impact_day=3;
    i en 5-dags reise som starter på dag 2 vil effekten anvendes på
    3. dawn-tick (når clock.day har blitt 3).
    """
    clock_day = state.world_state.clock.day
    effects = state.economy_state.pending_market_effects
    to_apply: list[PendingMarketEffect] = []
    remaining: list[PendingMarketEffect] = []
    for e in effects:
        if e.impact_day <= clock_day:
            to_apply.append(e)
        else:
            remaining.append(e)
    state.economy_state.pending_market_effects = remaining
    for effect in to_apply:
        _apply_effect(state, effect)
    return to_apply
