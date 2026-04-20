"""Lagring og lasting av spilltilstand (v6-formatet — Fase 3 Commit C3-1).

Struktur er nested (se `state/game_state.py`). Eldre saves migreres
via chained `migrate_vN_to_vN+1`-funksjoner som transformerer rå dicts
sekvensielt frem til nåværende versjon, før én parse-funksjon bygger
GameState-treet.

Autosave-triggere (kalles fra VillageScene / main):
- `pygame.QUIT`
- Scene-bytte (infrastruktur for Fase 2+)
- Åpning og lukking av børs-overlay

Versjonering: `version: int`. Ukjent versjon → returner `None` slik at
kaller faller tilbake til en fersk `GameState()`.

Migreringskjede:
- v1 → v2: legg til `seconds_into_day`-felt i klokke (erstattet av v3-
  clock-dict; v1 har ingen clock-struktur)
- v2 → v3: pakke inn `day` i `clock`-dict
- v3 → v4: legg til `cargo_capacity`, `regimes`, `pitch_lake` defaults
- v4 → v5: nest felter under player_state / world_state / economy_state /
  pitch_lake_state; initialiser Tortuga-markedet fra v4 commodities_state,
  fyll de tre andre havnene med tomme MarketState; bygg observed kun for
  Tortuga
- v5 → v6 (Fase 3 C3-1): legg til Fase 3-stub-felt som ble innført i
  C3-0 uten versjon-bump. Eksisterende dev-saves får
  `pitch_lake_state.purchased=True` (bakoverkompatibilitet — beholder
  aktiv bek-produksjon). `world_state.action_budget` settes fra balance-
  defaults. player/economy-stubs initialiseres til tomme/null-verdier.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict
from typing import Any

import random
from dataclasses import asdict as _asdict

import constants
from config import port_config as _port_config
from entities.commodity import InventoryItem
from state.action_budget import ActionBudget
from state.economy_state import EconomyState
from state.game_state import CURRENT_SAVE_VERSION, GameState
from state.market_effects import PendingRumorImpact, PendingSabotage
from state.market_state import CommodityMarket, MarketState
from state.observed_price import ObservedPrice
from state.pitch_lake_state import PitchLakeState
from state.player_state import PlayerState
from state.rumor_state import ActiveRumor
from state.ship_state import ShipState
from state.voyage_state import VoyageState
from state.world_state import WorldState
from systems import balance as _balance
from systems.economy import (  # noqa: F401
    init_market_for_port,
    load_base_prices,
    write_observed_for_port,
)
from systems.game_clock import GameClock
from systems.regime_manager import (
    REGIMES,
    RegimeState,
    sample_regimes_from_weights,
)


log = logging.getLogger(__name__)


#: Versjoner som load() aksepterer (med migrering for ikke-current).
ACCEPTED_VERSIONS = frozenset({1, 2, 3, 4, 5, 6})


def _default_inventory_dict() -> dict[str, dict]:
    """Inventar som dict-form (serialiserbar) for bruk i migreringsfunksjoner."""
    return {
        "sugar":   {"quantity": 0, "avg_cost": 0.0},
        "rum":     {"quantity": 0, "avg_cost": 0.0},
        "tobacco": {"quantity": 0, "avg_cost": 0.0},
        "pitch":   {"quantity": 0, "avg_cost": 0.0},
    }


# -----------------------------------------------------------------------------
# Chained migreringsfunksjoner: rå dict → rå dict, én versjons-bump per kall
# -----------------------------------------------------------------------------


def migrate_v1_to_v2(d: dict) -> dict:
    """v1 hadde inventar som dict[str, int] og `day` som top-level int.

    v2 innførte `inventory: dict[str, InventoryItem{quantity, avg_cost}]`.
    Klokke-strukturen kom først i v3.
    """
    log.info("Migrating save v%d → v%d", 1, 2)
    out = dict(d)
    raw_inv = out.get("inventory", {})
    new_inv: dict[str, dict] = _default_inventory_dict()
    if isinstance(raw_inv, dict):
        for cid, val in raw_inv.items():
            if isinstance(val, int):
                new_inv[cid] = {"quantity": val, "avg_cost": 0.0}
            elif isinstance(val, dict):
                new_inv[cid] = {
                    "quantity": int(val.get("quantity", 0)),
                    "avg_cost": float(val.get("avg_cost", 0.0)),
                }
    out["inventory"] = new_inv
    out["version"] = 2
    return out


def migrate_v2_to_v3(d: dict) -> dict:
    """v3 innførte `clock: {day, seconds_into_day, seconds_per_day}` som
    nested dict; tidligere saves hadde `day` som top-level int.
    """
    log.info("Migrating save v%d → v%d", 2, 3)
    out = dict(d)
    if "clock" not in out or not isinstance(out.get("clock"), dict):
        day = int(out.get("day", 1))
        seconds_per_day = _balance.get().time.seconds_per_day_in_port
        out["clock"] = {
            "day": day,
            "seconds_into_day": 0.0,
            "seconds_per_day": seconds_per_day,
        }
    out.pop("day", None)  # top-level day er nå representert i clock-dict
    out["version"] = 3
    return out


def migrate_v3_to_v4(d: dict) -> dict:
    """v4 la til `cargo_capacity`, `regimes`, `pitch_lake` (Fase 2A).

    Mangler disse settes til defaults fra balance + tom regimes.
    """
    log.info("Migrating save v%d → v%d", 3, 4)
    out = dict(d)
    bal = _balance.get()
    out.setdefault("cargo_capacity", bal.economy.ship_starting_cargo_capacity)
    out.setdefault("regimes", {})
    out.setdefault("pitch_lake", {
        "production_per_day": bal.pitch_lake.production_per_day,
        "daily_upkeep_cost": bal.pitch_lake.upkeep_per_day,
        "total_produced": 0,
        "last_production_day": 0,
    })
    out["version"] = 4
    return out


def migrate_v4_to_v5(d: dict) -> dict:
    """v5 nester GameState: player_state / world_state / economy_state /
    pitch_lake_state. Flater felter inn i nested dicts.

    Tortuga-markedet bevares NØYAKTIG fra v4 (spiller er alltid i Tortuga
    i v4). De andre tre havnene initialiseres som tomme MarketState-dicts
    og tomme regime-dicts; C2 fyller dem med port-bias-initiert data når
    PortConfig lander. `observed` settes til `{}` her — load() fyller
    Tortuga-snapshot post-parse via `write_observed_for_port` når
    original_version < 5 (C7a-refactor).

    `current_scene` i v4 droppes — scene-manager bestemmer startscene
    fra world_state.voyage (Some → VoyageScene) eller
    world_state.current_port (ellers PortVillageScene).
    """
    log.info("Migrating save v%d → v%d", 4, 5)
    bal = _balance.get()
    clock_raw = d.get("clock", {})

    # --- player_state ---
    raw_pos = d.get("player_position", [320.0, 0.0])
    if isinstance(raw_pos, (list, tuple)) and len(raw_pos) >= 1:
        try:
            position_x = float(raw_pos[0])
        except (TypeError, ValueError):
            position_x = 320.0
    else:
        position_x = 320.0

    player_state = {
        "position_x": position_x,
        "gold": int(d.get("gold", bal.economy.starting_gold)),
        "inventory": d.get("inventory", _default_inventory_dict()),
    }

    # --- world_state ---
    world_state = {
        "current_port": "tortuga",
        "clock": clock_raw if isinstance(clock_raw, dict) else {
            "day": 1, "seconds_into_day": 0.0,
            "seconds_per_day": bal.time.seconds_per_day_in_port,
        },
        "ship": {
            "class_id": "sloop",
            "name": "Sjarken",
            "cargo_capacity": int(
                d.get("cargo_capacity", bal.economy.ship_starting_cargo_capacity)
            ),
        },
        "voyage": None,
    }

    # --- economy_state ---
    tortuga_commodities = d.get("commodities_state", {})
    if not isinstance(tortuga_commodities, dict):
        tortuga_commodities = {}

    # Laster port-config og base-priser for bias-initialisering av ikke-
    # Tortuga-havner. Port-config må være `init()`-ed i main.py før
    # load() kalles — ellers kaster get_all_port_ids() RuntimeError.
    all_port_ids = _port_config.get_all_port_ids()
    base_prices = load_base_prices(
        os.path.join(constants.DATA_DIR, "commodities.json")
    )
    rng = random.Random()

    # markets[port_id]: Tortuga beholder v4-data; ikke-Tortuga får
    # base_price × price_bias for hver vare (tom price_history).
    markets: dict[str, dict] = {
        "tortuga": {"commodities": tortuga_commodities}
    }
    for pid in all_port_ids:
        if pid == "tortuga":
            continue
        pcfg = _port_config.get(pid)
        ms = init_market_for_port(pcfg, base_prices)
        markets[pid] = _asdict(ms)

    # regimes[port_id]: Tortuga beholder v4-regimer; ikke-Tortuga
    # samples fra regime_weights.
    tortuga_regimes = d.get("regimes", {})
    if not isinstance(tortuga_regimes, dict):
        tortuga_regimes = {}
    regimes: dict[str, dict] = {"tortuga": tortuga_regimes}
    for pid in all_port_ids:
        if pid == "tortuga":
            continue
        pcfg = _port_config.get(pid)
        sampled = sample_regimes_from_weights(pcfg, rng=rng)
        regimes[pid] = {cid: _asdict(r) for cid, r in sampled.items()}

    # observed[port_id][cid] = {price, day_seen}. Tortuga-snapshot
    # bygges via write_observed_for_port post-parse i load() (C7a-refactor).
    economy_state = {
        "markets": markets,
        "regimes": regimes,
        "observed": {},
    }

    # --- pitch_lake_state ---
    pl_raw = d.get("pitch_lake", {})
    if not isinstance(pl_raw, dict):
        pl_raw = {}
    pitch_lake_state = {
        "home_port": "tortuga",
        "production_per_day": int(pl_raw.get(
            "production_per_day", bal.pitch_lake.production_per_day
        )),
        # v4-felt het `daily_upkeep_cost`; v5 renamer til `upkeep_per_day`.
        "upkeep_per_day": int(pl_raw.get(
            "daily_upkeep_cost", bal.pitch_lake.upkeep_per_day
        )),
        "pending_units": 0,
        "total_produced": int(pl_raw.get("total_produced", 0)),
        "last_production_day": int(pl_raw.get("last_production_day", 0)),
    }

    return {
        "version": 5,
        "player_state": player_state,
        "world_state": world_state,
        "economy_state": economy_state,
        "pitch_lake_state": pitch_lake_state,
    }


def migrate_v5_to_v6(d: dict) -> dict:
    """v6 (Fase 3 C3-1) formaliserer Fase 3-stub-feltene fra C3-0.

    Fase 3-stubs ble innført i C3-0 uten versjons-bump; v5 → v6 markerer
    offisielt at disse nå er en del av skjemaet. Migreringen skiller
    mellom "eksisterende v5-save" og "ny v6-save" ved å gi eksisterende
    dev-saves `pitch_lake_state.purchased=True` (bevarer aktiv bek-
    produksjon) mens fresh saves starter `purchased=False` (spilleren
    må kjøpe anlegget i tavern-dag-meny i Tortuga — C3-6 gate-logikk).

    Alle andre Fase 3-stub-felt får nøytrale init-verdier:
    - `player_state.suspicion = 0.0`
    - `player_state.rest = balance.rest.default_start`
    - `player_state.port_caches = {}`
    - `player_state.active_rumors = []`
    - `world_state.action_budget = {balance.actions-defaults, day-phase}`
    - `economy_state.pending_sabotages = []`
    - `economy_state.pending_rumor_impacts = []`

    Bruker `setdefault` for felt som kanskje allerede er skrevet av
    C3-0-save som ble lagret før versjons-bumpen. Det eneste feltet som
    aktivt OVERSKRIVES er `pitch_lake_state.purchased` (migreringens
    hovedformål).
    """
    log.info("Migrating save v%d → v%d", 5, 6)
    out = dict(d)
    bal = _balance.get()

    # player_state stubs — setdefault slik at C3-0-era saves med eksplisitte
    # verdier bevares
    ps = out.get("player_state")
    if not isinstance(ps, dict):
        ps = {}
    ps.setdefault("suspicion", 0.0)
    ps.setdefault("rest", bal.rest.default_start)
    ps.setdefault("port_caches", {})
    ps.setdefault("active_rumors", [])
    out["player_state"] = ps

    # world_state.action_budget — initialiseres fra balance-defaults
    ws = out.get("world_state")
    if not isinstance(ws, dict):
        ws = {}
    ws.setdefault("action_budget", {
        "day_budget_hours": bal.actions.day_budget_hours,
        "night_budget_hours": bal.actions.night_budget_hours,
        "hours_used_today": 0.0,
        "hours_used_tonight": 0.0,
        "phase": "day",
    })
    out["world_state"] = ws

    # economy_state stubs
    es = out.get("economy_state")
    if not isinstance(es, dict):
        es = {}
    es.setdefault("pending_sabotages", [])
    es.setdefault("pending_rumor_impacts", [])
    out["economy_state"] = es

    # pitch_lake_state.purchased — ALLTID True for v5→v6-migrering
    # (bakoverkompatibilitet for eksisterende dev-saves som hadde aktiv
    # produksjon). Ikke setdefault — vi vil overskrive en ev. False-
    # verdi som kan ha blitt lagret av en C3-0-era save-write.
    pls = out.get("pitch_lake_state")
    if not isinstance(pls, dict):
        pls = {}
    pls["purchased"] = True
    out["pitch_lake_state"] = pls

    out["version"] = 6
    return out


#: Migreringskjede — indeks = fra-versjon.
_MIGRATIONS: dict[int, Any] = {
    1: migrate_v1_to_v2,
    2: migrate_v2_to_v3,
    3: migrate_v3_to_v4,
    4: migrate_v4_to_v5,
    5: migrate_v5_to_v6,
}


def migrate_to_latest(d: dict) -> dict:
    """Kjør alle nødvendige migreringer til dict er på v5-format.

    Kaster ValueError hvis versjon er ukjent eller over CURRENT_SAVE_VERSION.
    """
    version = int(d.get("version", 1))
    if version > CURRENT_SAVE_VERSION:
        raise ValueError(
            f"Save-versjon {version} er nyere enn støttet "
            f"(current={CURRENT_SAVE_VERSION})"
        )
    while version < CURRENT_SAVE_VERSION:
        if version not in _MIGRATIONS:
            raise ValueError(f"Ingen migrering for versjon {version}")
        d = _MIGRATIONS[version](d)
        version = int(d.get("version", version + 1))
    return d


# -----------------------------------------------------------------------------
# Parsing: rå v5-dict → GameState-tre
# -----------------------------------------------------------------------------


def _parse_inventory(raw: Any) -> dict[str, InventoryItem]:
    result: dict[str, InventoryItem] = {
        "sugar": InventoryItem(),
        "rum": InventoryItem(),
        "tobacco": InventoryItem(),
        "pitch": InventoryItem(),
    }
    if not isinstance(raw, dict):
        return result
    for cid, val in raw.items():
        if not isinstance(val, dict):
            continue
        try:
            qty = int(val.get("quantity", 0))
        except (TypeError, ValueError):
            qty = 0
        try:
            avg = float(val.get("avg_cost", 0.0))
        except (TypeError, ValueError):
            avg = 0.0
        result[cid] = InventoryItem(quantity=qty, avg_cost=avg)
    for known_id in ("sugar", "rum", "tobacco", "pitch"):
        result.setdefault(known_id, InventoryItem())
    return result


def _parse_regimes(raw: Any) -> dict[str, RegimeState]:
    result: dict[str, RegimeState] = {}
    if not isinstance(raw, dict):
        return result
    for cid, val in raw.items():
        if not isinstance(val, dict):
            continue
        current = val.get("current", "stable")
        if current not in REGIMES:
            current = "stable"
        try:
            days_remaining = int(val.get("days_remaining", 0))
        except (TypeError, ValueError):
            days_remaining = 0
        raw_history = val.get("history", [])
        if isinstance(raw_history, list):
            history = [h for h in raw_history if isinstance(h, str) and h in REGIMES]
        else:
            history = []
        result[cid] = RegimeState(
            current=current,
            days_remaining=days_remaining,
            history=history,
        )
    return result


def _parse_clock(raw: Any) -> GameClock:
    bal = _balance.get()
    if not isinstance(raw, dict):
        return GameClock()
    try:
        day = int(raw.get("day", 1))
    except (TypeError, ValueError):
        day = 1
    try:
        seconds_into_day = float(raw.get("seconds_into_day", 0.0))
    except (TypeError, ValueError):
        seconds_into_day = 0.0
    try:
        seconds_per_day = float(
            raw.get("seconds_per_day", bal.time.seconds_per_day_in_port)
        )
    except (TypeError, ValueError):
        seconds_per_day = bal.time.seconds_per_day_in_port
    return GameClock(
        day=day, seconds_into_day=seconds_into_day, seconds_per_day=seconds_per_day
    )


def _parse_commodity_market(raw: Any) -> CommodityMarket:
    if not isinstance(raw, dict):
        return CommodityMarket(current_price=0.0)
    try:
        current_price = float(raw.get("current_price", 0.0))
    except (TypeError, ValueError):
        current_price = 0.0
    raw_hist = raw.get("price_history", [])
    if isinstance(raw_hist, list):
        try:
            history = [float(p) for p in raw_hist]
        except (TypeError, ValueError):
            history = []
    else:
        history = []
    return CommodityMarket(current_price=current_price, price_history=history)


def _parse_market_state(raw: Any) -> MarketState:
    if not isinstance(raw, dict):
        return MarketState()
    raw_commodities = raw.get("commodities", {})
    if not isinstance(raw_commodities, dict):
        return MarketState()
    commodities = {
        cid: _parse_commodity_market(cdata)
        for cid, cdata in raw_commodities.items()
    }
    try:
        tick_id = int(raw.get("tick_id", 0))
    except (TypeError, ValueError):
        tick_id = 0
    return MarketState(commodities=commodities, tick_id=tick_id)


def _parse_observed(raw: Any) -> dict[str, dict[str, ObservedPrice]]:
    result: dict[str, dict[str, ObservedPrice]] = {}
    if not isinstance(raw, dict):
        return result
    for port_id, port_dict in raw.items():
        if not isinstance(port_dict, dict):
            continue
        entry: dict[str, ObservedPrice] = {}
        for cid, val in port_dict.items():
            if not isinstance(val, dict):
                continue
            try:
                price = float(val.get("price", 0.0))
                day_seen = int(val.get("day_seen", 0))
            except (TypeError, ValueError):
                continue
            entry[cid] = ObservedPrice(price=price, day_seen=day_seen)
        result[port_id] = entry
    return result


def _parse_ship(raw: Any) -> ShipState:
    bal = _balance.get()
    if not isinstance(raw, dict):
        return ShipState(
            cargo_capacity=bal.economy.ship_starting_cargo_capacity
        )
    try:
        cargo_capacity = int(
            raw.get("cargo_capacity", bal.economy.ship_starting_cargo_capacity)
        )
    except (TypeError, ValueError):
        cargo_capacity = bal.economy.ship_starting_cargo_capacity
    class_id = raw.get("class_id", "sloop") or "sloop"
    name = raw.get("name", "Sjarken") or "Sjarken"
    return ShipState(class_id=str(class_id), name=str(name), cargo_capacity=cargo_capacity)


def _parse_voyage(raw: Any) -> VoyageState | None:
    if raw is None or not isinstance(raw, dict):
        return None
    try:
        return VoyageState(
            from_port=str(raw["from_port"]),
            to_port=str(raw["to_port"]),
            depart_day=int(raw["depart_day"]),
            arrival_day=int(raw["arrival_day"]),
            progress=float(raw.get("progress", 0.0)),
        )
    except (KeyError, TypeError, ValueError):
        return None


def _parse_active_rumors(raw: Any) -> list[ActiveRumor]:
    """Fase 3 (v2) stub-parse. Ukjente/manglende nøkler → tom liste."""
    if not isinstance(raw, list):
        return []
    result: list[ActiveRumor] = []
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        try:
            result.append(
                ActiveRumor(
                    rumor_type=str(entry.get("rumor_type", "regime_preview")),
                    port_id=str(entry.get("port_id", "tortuga")),
                    commodity_id=str(entry.get("commodity_id", "sugar")),
                    expires_on_day=int(entry.get("expires_on_day", 0)),
                    payload=(
                        entry["payload"]
                        if isinstance(entry.get("payload"), dict)
                        else {}
                    ),
                )
            )
        except (TypeError, ValueError):
            continue
    return result


def _parse_port_caches(raw: Any) -> dict[str, int]:
    """Fase 3 (v2) stub-parse. Ikke-dict → tom."""
    if not isinstance(raw, dict):
        return {}
    result: dict[str, int] = {}
    for port_id, val in raw.items():
        if not isinstance(port_id, str):
            continue
        try:
            result[port_id] = int(val)
        except (TypeError, ValueError):
            continue
    return result


def _parse_player_state(raw: Any) -> PlayerState:
    bal = _balance.get()
    if not isinstance(raw, dict):
        return PlayerState(
            gold=bal.economy.starting_gold,
            rest=bal.rest.default_start,
        )
    try:
        position_x = float(raw.get("position_x", 320.0))
    except (TypeError, ValueError):
        position_x = 320.0
    try:
        gold = int(raw.get("gold", bal.economy.starting_gold))
    except (TypeError, ValueError):
        gold = bal.economy.starting_gold
    inventory = _parse_inventory(raw.get("inventory"))
    # Fase 3 (v2) stub-felt — defaults ved mangel (v5-saves uten feltet)
    try:
        suspicion = float(raw.get("suspicion", 0.0))
    except (TypeError, ValueError):
        suspicion = 0.0
    try:
        rest = float(raw.get("rest", bal.rest.default_start))
    except (TypeError, ValueError):
        rest = bal.rest.default_start
    port_caches = _parse_port_caches(raw.get("port_caches"))
    active_rumors = _parse_active_rumors(raw.get("active_rumors"))
    return PlayerState(
        position_x=position_x,
        gold=gold,
        inventory=inventory,
        suspicion=suspicion,
        rest=rest,
        port_caches=port_caches,
        active_rumors=active_rumors,
    )


def _parse_action_budget(raw: Any) -> ActionBudget:
    """Fase 3 (v2) stub-parse. Mangler/invalid → new_default fra balance."""
    if not isinstance(raw, dict):
        return ActionBudget.new_default()
    bal = _balance.get()
    try:
        day_budget = float(raw.get(
            "day_budget_hours", bal.actions.day_budget_hours
        ))
    except (TypeError, ValueError):
        day_budget = bal.actions.day_budget_hours
    try:
        night_budget = float(raw.get(
            "night_budget_hours", bal.actions.night_budget_hours
        ))
    except (TypeError, ValueError):
        night_budget = bal.actions.night_budget_hours
    try:
        hours_used_today = float(raw.get("hours_used_today", 0.0))
    except (TypeError, ValueError):
        hours_used_today = 0.0
    try:
        hours_used_tonight = float(raw.get("hours_used_tonight", 0.0))
    except (TypeError, ValueError):
        hours_used_tonight = 0.0
    phase = raw.get("phase", "day")
    if phase not in ("day", "night"):
        phase = "day"
    return ActionBudget(
        day_budget_hours=day_budget,
        night_budget_hours=night_budget,
        hours_used_today=hours_used_today,
        hours_used_tonight=hours_used_tonight,
        phase=phase,
    )


def _parse_world_state(raw: Any) -> WorldState:
    if not isinstance(raw, dict):
        return WorldState(action_budget=ActionBudget.new_default())
    current_port = raw.get("current_port", "tortuga")
    if not isinstance(current_port, str):
        current_port = "tortuga"
    clock = _parse_clock(raw.get("clock"))
    ship = _parse_ship(raw.get("ship"))
    voyage = _parse_voyage(raw.get("voyage"))
    # Fase 3 (v2) stub: action_budget feltet. v5-saves uten feltet får
    # default fra balance via _parse_action_budget.
    action_budget = _parse_action_budget(raw.get("action_budget"))
    return WorldState(
        current_port=current_port,
        clock=clock,
        ship=ship,
        voyage=voyage,
        action_budget=action_budget,
    )


def _parse_pending_sabotage(raw: Any) -> PendingSabotage | None:
    if not isinstance(raw, dict):
        return None
    try:
        return PendingSabotage(
            target_port=str(raw.get("target_port", "port_royal")),
            commodity_id=str(raw.get("commodity_id", "sugar")),
            magnitude_pct=float(raw.get("magnitude_pct", 10.0)),
            ordered_on_day=int(raw.get("ordered_on_day", 0)),
            impact_day=int(raw.get("impact_day", 0)),
        )
    except (TypeError, ValueError):
        return None


def _parse_pending_rumor_impact(raw: Any) -> PendingRumorImpact | None:
    if not isinstance(raw, dict):
        return None
    try:
        return PendingRumorImpact(
            target_port=str(raw.get("target_port", "port_royal")),
            commodity_id=str(raw.get("commodity_id", "sugar")),
            magnitude_pct=float(raw.get("magnitude_pct", 10.0)),
            ordered_on_day=int(raw.get("ordered_on_day", 0)),
            impact_day=int(raw.get("impact_day", 0)),
        )
    except (TypeError, ValueError):
        return None


def _parse_economy_state(raw: Any) -> EconomyState:
    if not isinstance(raw, dict):
        return EconomyState()
    raw_markets = raw.get("markets", {})
    markets: dict[str, MarketState] = {}
    if isinstance(raw_markets, dict):
        for pid, mdata in raw_markets.items():
            markets[pid] = _parse_market_state(mdata)
    raw_regimes = raw.get("regimes", {})
    regimes: dict[str, dict[str, RegimeState]] = {}
    if isinstance(raw_regimes, dict):
        for pid, rdata in raw_regimes.items():
            regimes[pid] = _parse_regimes(rdata)
    observed = _parse_observed(raw.get("observed", {}))
    # Fase 3 (v2) stub-felt — tom liste ved mangel
    pending_sabotages: list[PendingSabotage] = []
    raw_ps = raw.get("pending_sabotages", [])
    if isinstance(raw_ps, list):
        for entry in raw_ps:
            parsed = _parse_pending_sabotage(entry)
            if parsed is not None:
                pending_sabotages.append(parsed)
    pending_rumor_impacts: list[PendingRumorImpact] = []
    raw_pri = raw.get("pending_rumor_impacts", [])
    if isinstance(raw_pri, list):
        for entry in raw_pri:
            parsed = _parse_pending_rumor_impact(entry)
            if parsed is not None:
                pending_rumor_impacts.append(parsed)
    return EconomyState(
        markets=markets,
        regimes=regimes,
        observed=observed,
        pending_sabotages=pending_sabotages,
        pending_rumor_impacts=pending_rumor_impacts,
    )


def _parse_pitch_lake_state(raw: Any) -> PitchLakeState:
    bal = _balance.get()
    if not isinstance(raw, dict):
        return PitchLakeState.new_default()
    try:
        production_per_day = int(
            raw.get("production_per_day", bal.pitch_lake.production_per_day)
        )
    except (TypeError, ValueError):
        production_per_day = bal.pitch_lake.production_per_day
    try:
        upkeep_per_day = int(
            raw.get("upkeep_per_day", bal.pitch_lake.upkeep_per_day)
        )
    except (TypeError, ValueError):
        upkeep_per_day = bal.pitch_lake.upkeep_per_day
    try:
        pending_units = int(raw.get("pending_units", 0))
    except (TypeError, ValueError):
        pending_units = 0
    try:
        total_produced = int(raw.get("total_produced", 0))
    except (TypeError, ValueError):
        total_produced = 0
    try:
        last_production_day = int(raw.get("last_production_day", 0))
    except (TypeError, ValueError):
        last_production_day = 0
    home_port = raw.get("home_port", "tortuga")
    if not isinstance(home_port, str):
        home_port = "tortuga"
    # Fase 3 (v2) stub-felt. Default False ved mangel (v5-saves uten
    # feltet). v5→v6-migreringen i C3-1 vil sette True for eksisterende
    # dev-saves — foreløpig er stubben ikke koblet til gate-logikk, så
    # default har ingen effekt på gameplay.
    purchased = bool(raw.get("purchased", False))
    return PitchLakeState(
        home_port=home_port,
        production_per_day=production_per_day,
        upkeep_per_day=upkeep_per_day,
        pending_units=pending_units,
        total_produced=total_produced,
        last_production_day=last_production_day,
        purchased=purchased,
    )


def parse_v5(d: dict) -> GameState:
    """Parse en rå v5-dict til GameState-treet."""
    return GameState(
        version=CURRENT_SAVE_VERSION,
        player_state=_parse_player_state(d.get("player_state")),
        world_state=_parse_world_state(d.get("world_state")),
        economy_state=_parse_economy_state(d.get("economy_state")),
        pitch_lake_state=_parse_pitch_lake_state(d.get("pitch_lake_state")),
    )


def new_game_state() -> GameState:
    """Opprett en fersk v5 GameState med defaults fra balance og bias-
    initialiserte markeder + samplet regimer for alle 4 havner.

    Brukes av main.py når ingen save eksisterer.
    """
    bal = _balance.get()
    player = PlayerState(
        position_x=320.0,
        gold=bal.economy.starting_gold,
        inventory={
            "sugar": InventoryItem(),
            "rum": InventoryItem(),
            "tobacco": InventoryItem(),
            "pitch": InventoryItem(),
        },
        # Fase 3 (v2) C3-0 stubs: default-verdier fra balance. Ingen
        # wiring ennå.
        suspicion=0.0,
        rest=bal.rest.default_start,
        port_caches={},
        active_rumors=[],
    )
    world = WorldState(
        current_port="tortuga",
        clock=GameClock(),
        ship=ShipState(
            class_id="sloop", name="Sjarken",
            cargo_capacity=bal.economy.ship_starting_cargo_capacity,
        ),
        voyage=None,
        # Fase 3 (v2) C3-0 stub: ActionBudget med balance-forankrede
        # verdier. Koblingen til game loop kommer i C3-1.
        action_budget=ActionBudget.new_default(),
    )
    base_prices = load_base_prices(
        os.path.join(constants.DATA_DIR, "commodities.json")
    )
    rng = random.Random()
    markets: dict[str, MarketState] = {}
    regimes: dict[str, dict[str, RegimeState]] = {}
    for port_id in _port_config.get_all_port_ids():
        pcfg = _port_config.get(port_id)
        markets[port_id] = init_market_for_port(pcfg, base_prices)
        regimes[port_id] = sample_regimes_from_weights(pcfg, rng=rng)
    economy = EconomyState(markets=markets, regimes=regimes, observed={})
    pitch_lake = PitchLakeState.new_default()
    state = GameState(
        player_state=player,
        world_state=world,
        economy_state=economy,
        pitch_lake_state=pitch_lake,
    )
    # Tortuga-snapshot ved spillstart: spilleren spawn-er i Tortuga, så
    # prisene der er observerte med en gang.
    write_observed_for_port(state, "tortuga")
    return state


# -----------------------------------------------------------------------------
# Silent rescue: v5-save fra C1b hadde tomme ikke-Tortuga-markeder.
# C2 fyller dem via init_market_for_port + sample_regimes ved load, uten
# versjons-bump (skjemaet er uendret, bare defaults populated).
# -----------------------------------------------------------------------------

def _rescue_empty_nontortuga_ports(state: GameState) -> None:
    """Detekter tomme ikke-Tortuga-markeder/regimer og initialiser dem
    med bias + regime-sampling. Muterer state in-place.

    Kriterier for "tom" som utløser rescue:
    - markets[pid].commodities er {} OG regimes[pid] er {}
    Begge må være tomme — delvis utfylt antas å være meningsbærende
    brukerdata som ikke skal overstyres.

    Logger én INFO-linje per havn som ble rescued.
    """
    try:
        port_ids = _port_config.get_all_port_ids()
    except RuntimeError:
        return  # port_config ikke initialisert (kun tester som ikke trenger rescue)

    base_prices = load_base_prices(
        os.path.join(constants.DATA_DIR, "commodities.json")
    )
    rng = random.Random()
    markets = state.economy_state.markets
    regimes = state.economy_state.regimes

    for pid in port_ids:
        if pid == "tortuga":
            continue
        market = markets.get(pid)
        regime_dict = regimes.get(pid, {})
        market_empty = market is None or not market.commodities
        regimes_empty = not regime_dict
        if market_empty and regimes_empty:
            pcfg = _port_config.get(pid)
            markets[pid] = init_market_for_port(pcfg, base_prices)
            regimes[pid] = sample_regimes_from_weights(pcfg, rng=rng)
            log.info(
                "Initializing port %s markets with bias (was empty)", pid
            )


# -----------------------------------------------------------------------------
# Disk I/O
# -----------------------------------------------------------------------------


def save(state: GameState, path: str = constants.SAVE_PATH) -> bool:
    """Skriv hele `state` til `path`. Returner True ved suksess.

    Skriver alltid i nåværende format (CURRENT_SAVE_VERSION).
    asdict() rekurserer gjennom hele nested-treet til primitive typer.
    """
    try:
        parent = os.path.dirname(path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        state.version = CURRENT_SAVE_VERSION
        data = asdict(state)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, ensure_ascii=False)
        log.info(
            "Lagret save til %s (gull=%d, dag=%d)",
            path, state.player_state.gold, state.world_state.clock.day,
        )
        return True
    except OSError as exc:
        log.warning("Klarte ikke lagre save til %s: %s", path, exc)
        return False


def load(path: str = constants.SAVE_PATH) -> GameState | None:
    """Les save fra `path`. `None` ved manglende eller ugyldig innhold.

    Startscene utledes av caller (main.py):
    - Hvis `world_state.voyage is not None` → VoyageScene (lander i C7)
    - Ellers → PortVillageScene(world_state.current_port)
    """
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except FileNotFoundError:
        log.info("Ingen save paa %s – startverdier brukes", path)
        return None
    except (OSError, json.JSONDecodeError) as exc:
        log.warning(
            "Kunne ikke lese save %s: %s – startverdier brukes", path, exc
        )
        return None

    version = data.get("version")
    if version not in ACCEPTED_VERSIONS:
        log.warning(
            "Ukjent save-versjon %r (aksepterer %s) – startverdier brukes",
            version, sorted(ACCEPTED_VERSIONS),
        )
        return None
    if version != CURRENT_SAVE_VERSION:
        log.info("Migrerer save fra v%d til v%d", version, CURRENT_SAVE_VERSION)

    try:
        v5_data = migrate_to_latest(data)
    except ValueError as exc:
        log.warning("Migrering feilet: %s – startverdier brukes", exc)
        return None

    state = parse_v5(v5_data)
    # Silent rescue: v5-saves fra C1b har tomme ikke-Tortuga-markeder.
    # Fyll dem fra port_config uten versjons-bump.
    _rescue_empty_nontortuga_ports(state)
    # v4-og-eldre saves: spilleren var alltid i Tortuga (eneste havn),
    # så prisene der er det vi vil registrere som observerte. C7a-refactor
    # erstatter inline observed-bygging i migrate_v4_to_v5.
    if version < CURRENT_SAVE_VERSION:
        write_observed_for_port(state, "tortuga")
    return state
