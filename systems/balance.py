"""Balansering fra `data/balance.json` — singleton med eksplisitt init.

Filosofi:
- `data/balance.json` inneholder alle tall man ønsker å iterere på under
  kalibrering (startgull, gebyr, upkeep, regime-drift, reise-kost,
  Fase 3 handlings-tid, mistanke, rom, rykter, sabotasje, events).
- Strukturelle valg (hva en havn er, geografi) ligger i `data/ports.json`.
- Balance lastes ÉN gang ved spill-oppstart via `init()`. Senere kaller
  `get()` og returnerer den samme instansen til hele prosessen.
- `reload()` leser filen på nytt og bytter ut singletonens felt in-place
  slik at alle eksisterende `get()`-referanser automatisk ser nye verdier.
- Ingen lazy-load: manglende eller ødelagt balance.json får spillet til
  å feile tydelig ved oppstart (i `init()`), ikke ved første handel.

Schema-versjoner:
- v1 (Fase 2B C1a): økonomi, tid, pitch_lake, travel, regimer, observed.
- v2 (Fase 3 C3-0): la til game, actions, suspicion, rest, rumors,
  sabotage, events. Utvidet pitch_lake med purchase_cost_gold.
  Fields som var i v1 er uendret.

Hot-reload-kategorier (spec §4.4):
- LIVE: gjelder umiddelbart (transaction_fee, upkeep_per_day, production_per_day,
  drift_pct_*, noise_pct, travel.routes.*, stale_threshold_days,
  actions.cost_hours_per_action.*, suspicion.daily_decay/rumor_increase/
  arrest_on_threshold, rest.decay_per_action/tired_penalty_multiplier/
  room_cost_*, rumors.*, sabotage.*, events.*)
- SESSION: gjelder fra neste dawn (seconds_per_day_in_port,
  seconds_per_day_at_sea, actions.day_budget_hours,
  actions.night_budget_hours, suspicion.threshold)
- NEWGAME: krever ny save (starting_gold, ship_starting_cargo_capacity,
  game.total_days, game.starting_port, pitch_lake.purchase_cost_gold,
  rest.default_start)
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field, fields
from typing import Any

log = logging.getLogger(__name__)


#: Filplassering relativt til prosjekt-rota. main.py CD-er til rota.
DEFAULT_BALANCE_PATH = os.path.join("data", "balance.json")


@dataclass
class EconomyBalance:
    starting_gold: int
    transaction_fee: int
    ship_starting_cargo_capacity: int


@dataclass
class TimeBalance:
    seconds_per_day_in_port: float
    seconds_per_day_at_sea: float


@dataclass
class PitchLakeBalance:
    production_per_day: int
    upkeep_per_day: int
    #: v2: engangskost for å låse opp bek-produksjon via tavern-dag-meny
    #: i Tortuga (Fase 3 C3-6). `purchased`-flagg bor i PitchLakeState.
    purchase_cost_gold: int


@dataclass
class RouteInfo:
    days: int
    gold: int


@dataclass
class TravelBalance:
    #: Rute-oppslag. Nøkkel = alfabetisk sortert "{a}-{b}", f.eks. "havana-nassau".
    routes: dict[str, RouteInfo] = field(default_factory=dict)


@dataclass
class RegimesBalance:
    #: Prosent-drift per dag per regime-type. (min, max) range.
    #: Stable er [0.0, 0.0] i default → ingen drift (spec Q1-avklaring).
    drift_pct_rising: tuple[float, float]
    drift_pct_stable: tuple[float, float]
    drift_pct_falling: tuple[float, float]
    #: Uavhengig markedsstøy per dag (±noise_pct%).
    noise_pct: float


@dataclass
class ObservedBalance:
    #: Antall dager før "siste observert"-pris regnes som utdatert.
    stale_threshold_days: int


# --- Fase 3 (v2-schema) balanse-seksjoner ---


@dataclass
class GameBalance:
    """Øvrig spill-skjelett: antall dager, start-havn."""
    total_days: int
    starting_port: str


@dataclass
class ActionsBalance:
    """Handlings-tid og per-handling-tid-kost (Fase 3 C3-1)."""
    day_budget_hours: float
    night_budget_hours: float
    #: Nøkkel = handlings-id (se FASE_3.md §1.3/§5), verdi = timer.
    #: Ukjente nøkler ignoreres; manglende nøkler faller tilbake til 0.0.
    cost_hours_per_action: dict[str, float] = field(default_factory=dict)


@dataclass
class SuspicionBalance:
    """Mistanke-meter (Fase 3 C3-7)."""
    threshold: float
    daily_decay: float
    #: `rumor_increase` er 0 i default (lytte-rykter gir ingen mistanke).
    #: Beholdes som felt for hot-reload-muligheter.
    rumor_increase: float
    arrest_on_threshold: bool


@dataclass
class RestBalance:
    """Rom-meter (Fase 3 C3-8)."""
    default_start: float
    decay_per_action: float
    tired_penalty_multiplier: float
    room_cost_gold: int
    room_cost_hours: float


@dataclass
class RumorsBalance:
    """Lytte-rykter (rumor_listen) — Fase 3 C3-9.

    Offensiv rumor_spread bor i SabotageBalance (felles infrastruktur
    med sabotasje).
    """
    cost_gold: int
    cost_hours: float
    ttl_days: int
    regime_preview_enabled: bool
    price_spike_warning_enabled: bool


@dataclass
class SabotageBalance:
    """Offensive markedseffekter (sabotasje + falskt rykte) — Fase 3 C3-10.

    Sabotasje hever target-pris; falskt rykte (rumor_spread) senker.
    Begge har samme infrastruktur og impact_delay; magnitude og
    gull-/mistanke-kost er separate.
    """
    base_cost_gold: int
    impact_delay_days: int
    magnitude_pct: float
    false_rumor_base_cost_gold: int
    false_rumor_magnitude_pct: float
    suspicion_increase_sabotage: float
    suspicion_increase_false_rumor: float


@dataclass
class EventsBalance:
    """Random events-rammeverk — Fase 3 C3-11."""
    voyage_frequency_per_day: float
    port_frequency_per_day_start: float
    positive_ratio: float


@dataclass
class Balance:
    """Top-level balance-struktur. Muteres in-place av `reload()`."""

    version: int
    economy: EconomyBalance
    time: TimeBalance
    pitch_lake: PitchLakeBalance
    travel: TravelBalance
    regimes: RegimesBalance
    observed: ObservedBalance
    # Fase 3 (v2) seksjoner:
    game: GameBalance
    actions: ActionsBalance
    suspicion: SuspicionBalance
    rest: RestBalance
    rumors: RumorsBalance
    sabotage: SabotageBalance
    events: EventsBalance


# --- Kategorier for hot-reload ---

#: Felt som trer i kraft umiddelbart ved hot-reload.
LIVE_FIELDS: frozenset[str] = frozenset({
    "economy.transaction_fee",
    "pitch_lake.upkeep_per_day",
    "pitch_lake.production_per_day",
    "regimes.drift_pct_rising",
    "regimes.drift_pct_stable",
    "regimes.drift_pct_falling",
    "regimes.noise_pct",
    "travel.routes",
    "observed.stale_threshold_days",
    # Fase 3 (v2) live-felt
    "actions.cost_hours_per_action",
    "suspicion.daily_decay",
    "suspicion.rumor_increase",
    "suspicion.arrest_on_threshold",
    "rest.decay_per_action",
    "rest.tired_penalty_multiplier",
    "rest.room_cost_gold",
    "rest.room_cost_hours",
    "rumors.cost_gold",
    "rumors.cost_hours",
    "rumors.ttl_days",
    "rumors.regime_preview_enabled",
    "rumors.price_spike_warning_enabled",
    "sabotage.base_cost_gold",
    "sabotage.impact_delay_days",
    "sabotage.magnitude_pct",
    "sabotage.false_rumor_base_cost_gold",
    "sabotage.false_rumor_magnitude_pct",
    "sabotage.suspicion_increase_sabotage",
    "sabotage.suspicion_increase_false_rumor",
    "events.voyage_frequency_per_day",
    "events.port_frequency_per_day_start",
    "events.positive_ratio",
})

#: Felt som trer i kraft fra neste dawn.
SESSION_FIELDS: frozenset[str] = frozenset({
    "time.seconds_per_day_in_port",
    "time.seconds_per_day_at_sea",
    # Fase 3 (v2) session-felt
    "actions.day_budget_hours",
    "actions.night_budget_hours",
    "suspicion.threshold",
})

#: Felt som kun gjelder for nye saves; ignoreres i nåværende sesjon.
NEWGAME_FIELDS: frozenset[str] = frozenset({
    "economy.starting_gold",
    "economy.ship_starting_cargo_capacity",
    # Fase 3 (v2) newgame-felt
    "game.total_days",
    "game.starting_port",
    "pitch_lake.purchase_cost_gold",
    "rest.default_start",
})


# --- Parsing ---

def _parse_routes(raw: Any) -> dict[str, RouteInfo]:
    result: dict[str, RouteInfo] = {}
    if not isinstance(raw, dict):
        return result
    for key, val in raw.items():
        if not isinstance(val, dict):
            continue
        try:
            result[key] = RouteInfo(
                days=int(val["days"]), gold=int(val["gold"])
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"travel.routes.{key}: {exc}") from exc
    return result


def _parse_pct_range(raw: Any, label: str) -> tuple[float, float]:
    if not isinstance(raw, (list, tuple)) or len(raw) != 2:
        raise ValueError(f"{label}: forventet [min, max]-liste, fikk {raw!r}")
    try:
        lo = float(raw[0])
        hi = float(raw[1])
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label}: {exc}") from exc
    return (lo, hi)


def _parse_cost_hours(raw: Any) -> dict[str, float]:
    """Parse actions.cost_hours_per_action som dict[str, float].

    Ikke-dict → tom dict (gir 0.0-default ved oppslag). Individuelle
    ikke-float-verdier hoppes over med ValueError.
    """
    if not isinstance(raw, dict):
        return {}
    result: dict[str, float] = {}
    for key, val in raw.items():
        if not isinstance(key, str):
            continue
        try:
            result[key] = float(val)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"actions.cost_hours_per_action.{key}: {exc}"
            ) from exc
    return result


def _parse_balance(raw: dict) -> Balance:
    """Bygg Balance fra rå JSON-dict. Kaster ValueError ved manglende felt."""
    try:
        version = int(raw["version"])
        eco_raw = raw["economy"]
        economy = EconomyBalance(
            starting_gold=int(eco_raw["starting_gold"]),
            transaction_fee=int(eco_raw["transaction_fee"]),
            ship_starting_cargo_capacity=int(eco_raw["ship_starting_cargo_capacity"]),
        )
        time_raw = raw["time"]
        time_b = TimeBalance(
            seconds_per_day_in_port=float(time_raw["seconds_per_day_in_port"]),
            seconds_per_day_at_sea=float(time_raw["seconds_per_day_at_sea"]),
        )
        pl_raw = raw["pitch_lake"]
        pitch_lake = PitchLakeBalance(
            production_per_day=int(pl_raw["production_per_day"]),
            upkeep_per_day=int(pl_raw["upkeep_per_day"]),
            purchase_cost_gold=int(pl_raw["purchase_cost_gold"]),
        )
        travel = TravelBalance(routes=_parse_routes(raw.get("travel", {}).get("routes", {})))
        reg_raw = raw["regimes"]
        regimes = RegimesBalance(
            drift_pct_rising=_parse_pct_range(
                reg_raw["drift_pct_rising"], "regimes.drift_pct_rising"
            ),
            drift_pct_stable=_parse_pct_range(
                reg_raw["drift_pct_stable"], "regimes.drift_pct_stable"
            ),
            drift_pct_falling=_parse_pct_range(
                reg_raw["drift_pct_falling"], "regimes.drift_pct_falling"
            ),
            noise_pct=float(reg_raw["noise_pct"]),
        )
        obs_raw = raw["observed"]
        observed = ObservedBalance(
            stale_threshold_days=int(obs_raw["stale_threshold_days"]),
        )
        # --- Fase 3 (v2) seksjoner ---
        game_raw = raw["game"]
        game = GameBalance(
            total_days=int(game_raw["total_days"]),
            starting_port=str(game_raw["starting_port"]),
        )
        act_raw = raw["actions"]
        actions = ActionsBalance(
            day_budget_hours=float(act_raw["day_budget_hours"]),
            night_budget_hours=float(act_raw["night_budget_hours"]),
            cost_hours_per_action=_parse_cost_hours(
                act_raw.get("cost_hours_per_action", {})
            ),
        )
        sus_raw = raw["suspicion"]
        suspicion = SuspicionBalance(
            threshold=float(sus_raw["threshold"]),
            daily_decay=float(sus_raw["daily_decay"]),
            rumor_increase=float(sus_raw["rumor_increase"]),
            arrest_on_threshold=bool(sus_raw["arrest_on_threshold"]),
        )
        rest_raw = raw["rest"]
        rest = RestBalance(
            default_start=float(rest_raw["default_start"]),
            decay_per_action=float(rest_raw["decay_per_action"]),
            tired_penalty_multiplier=float(rest_raw["tired_penalty_multiplier"]),
            room_cost_gold=int(rest_raw["room_cost_gold"]),
            room_cost_hours=float(rest_raw["room_cost_hours"]),
        )
        rum_raw = raw["rumors"]
        rumors = RumorsBalance(
            cost_gold=int(rum_raw["cost_gold"]),
            cost_hours=float(rum_raw["cost_hours"]),
            ttl_days=int(rum_raw["ttl_days"]),
            regime_preview_enabled=bool(rum_raw["regime_preview_enabled"]),
            price_spike_warning_enabled=bool(rum_raw["price_spike_warning_enabled"]),
        )
        sab_raw = raw["sabotage"]
        sabotage = SabotageBalance(
            base_cost_gold=int(sab_raw["base_cost_gold"]),
            impact_delay_days=int(sab_raw["impact_delay_days"]),
            magnitude_pct=float(sab_raw["magnitude_pct"]),
            false_rumor_base_cost_gold=int(sab_raw["false_rumor_base_cost_gold"]),
            false_rumor_magnitude_pct=float(sab_raw["false_rumor_magnitude_pct"]),
            suspicion_increase_sabotage=float(sab_raw["suspicion_increase_sabotage"]),
            suspicion_increase_false_rumor=float(sab_raw["suspicion_increase_false_rumor"]),
        )
        evt_raw = raw["events"]
        events = EventsBalance(
            voyage_frequency_per_day=float(evt_raw["voyage_frequency_per_day"]),
            port_frequency_per_day_start=float(evt_raw["port_frequency_per_day_start"]),
            positive_ratio=float(evt_raw["positive_ratio"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"balance.json: {exc}") from exc

    return Balance(
        version=version,
        economy=economy,
        time=time_b,
        pitch_lake=pitch_lake,
        travel=travel,
        regimes=regimes,
        observed=observed,
        game=game,
        actions=actions,
        suspicion=suspicion,
        rest=rest,
        rumors=rumors,
        sabotage=sabotage,
        events=events,
    )


def load_from_path(path: str) -> Balance:
    """Les og parse balance.json. Kaster FileNotFoundError eller ValueError."""
    with open(path, "r", encoding="utf-8") as fh:
        raw = json.load(fh)
    return _parse_balance(raw)


# --- Singleton ---

_instance: Balance | None = None
_path: str = DEFAULT_BALANCE_PATH


def init(path: str = DEFAULT_BALANCE_PATH) -> Balance:
    """Last balance.json eksplisitt ved oppstart. Kalles fra main.py før
    noen systemer som trenger balance importeres/lastes.

    Feiler høylydt (FileNotFoundError / ValueError) ved manglende eller
    ødelagt fil — vi vil oppdage dette nå, ikke ved første handel.
    """
    global _instance, _path
    _path = path
    _instance = load_from_path(path)
    log.info("Balance lastet fra %s (v%d)", path, _instance.version)
    return _instance


def get() -> Balance:
    """Returner gjeldende balance-instans. Krever at `init()` er kalt."""
    if _instance is None:
        raise RuntimeError(
            "Balance ikke initialisert. Kall systems.balance.init() først."
        )
    return _instance


def is_initialized() -> bool:
    return _instance is not None


@dataclass
class ReloadResult:
    """Resultat av hot-reload. Brukes av F5-handler for toast-tekst."""
    success: bool
    error: str | None = None
    live_changes: list[str] = field(default_factory=list)
    session_changes: list[str] = field(default_factory=list)
    newgame_changes: list[str] = field(default_factory=list)


def _diff_fields(old: Balance, new: Balance) -> dict[str, list[str]]:
    """Returner {live/session/newgame → liste av endrede dot-paths}."""
    changes = {"live": [], "session": [], "newgame": []}
    # Sammenlign felt-for-felt på dot-path-form
    paths_values = {
        # --- v1 (Fase 2B) felt ---
        "economy.starting_gold": (old.economy.starting_gold, new.economy.starting_gold),
        "economy.transaction_fee": (old.economy.transaction_fee, new.economy.transaction_fee),
        "economy.ship_starting_cargo_capacity": (
            old.economy.ship_starting_cargo_capacity,
            new.economy.ship_starting_cargo_capacity,
        ),
        "time.seconds_per_day_in_port": (
            old.time.seconds_per_day_in_port, new.time.seconds_per_day_in_port
        ),
        "time.seconds_per_day_at_sea": (
            old.time.seconds_per_day_at_sea, new.time.seconds_per_day_at_sea
        ),
        "pitch_lake.production_per_day": (
            old.pitch_lake.production_per_day, new.pitch_lake.production_per_day
        ),
        "pitch_lake.upkeep_per_day": (
            old.pitch_lake.upkeep_per_day, new.pitch_lake.upkeep_per_day
        ),
        "pitch_lake.purchase_cost_gold": (
            old.pitch_lake.purchase_cost_gold, new.pitch_lake.purchase_cost_gold
        ),
        "regimes.drift_pct_rising": (old.regimes.drift_pct_rising, new.regimes.drift_pct_rising),
        "regimes.drift_pct_stable": (old.regimes.drift_pct_stable, new.regimes.drift_pct_stable),
        "regimes.drift_pct_falling": (
            old.regimes.drift_pct_falling, new.regimes.drift_pct_falling
        ),
        "regimes.noise_pct": (old.regimes.noise_pct, new.regimes.noise_pct),
        "travel.routes": (old.travel.routes, new.travel.routes),
        "observed.stale_threshold_days": (
            old.observed.stale_threshold_days, new.observed.stale_threshold_days
        ),
        # --- v2 (Fase 3) felt ---
        "game.total_days": (old.game.total_days, new.game.total_days),
        "game.starting_port": (old.game.starting_port, new.game.starting_port),
        "actions.day_budget_hours": (
            old.actions.day_budget_hours, new.actions.day_budget_hours
        ),
        "actions.night_budget_hours": (
            old.actions.night_budget_hours, new.actions.night_budget_hours
        ),
        "actions.cost_hours_per_action": (
            old.actions.cost_hours_per_action, new.actions.cost_hours_per_action
        ),
        "suspicion.threshold": (old.suspicion.threshold, new.suspicion.threshold),
        "suspicion.daily_decay": (old.suspicion.daily_decay, new.suspicion.daily_decay),
        "suspicion.rumor_increase": (
            old.suspicion.rumor_increase, new.suspicion.rumor_increase
        ),
        "suspicion.arrest_on_threshold": (
            old.suspicion.arrest_on_threshold, new.suspicion.arrest_on_threshold
        ),
        "rest.default_start": (old.rest.default_start, new.rest.default_start),
        "rest.decay_per_action": (
            old.rest.decay_per_action, new.rest.decay_per_action
        ),
        "rest.tired_penalty_multiplier": (
            old.rest.tired_penalty_multiplier, new.rest.tired_penalty_multiplier
        ),
        "rest.room_cost_gold": (
            old.rest.room_cost_gold, new.rest.room_cost_gold
        ),
        "rest.room_cost_hours": (
            old.rest.room_cost_hours, new.rest.room_cost_hours
        ),
        "rumors.cost_gold": (old.rumors.cost_gold, new.rumors.cost_gold),
        "rumors.cost_hours": (old.rumors.cost_hours, new.rumors.cost_hours),
        "rumors.ttl_days": (old.rumors.ttl_days, new.rumors.ttl_days),
        "rumors.regime_preview_enabled": (
            old.rumors.regime_preview_enabled, new.rumors.regime_preview_enabled
        ),
        "rumors.price_spike_warning_enabled": (
            old.rumors.price_spike_warning_enabled,
            new.rumors.price_spike_warning_enabled,
        ),
        "sabotage.base_cost_gold": (
            old.sabotage.base_cost_gold, new.sabotage.base_cost_gold
        ),
        "sabotage.impact_delay_days": (
            old.sabotage.impact_delay_days, new.sabotage.impact_delay_days
        ),
        "sabotage.magnitude_pct": (
            old.sabotage.magnitude_pct, new.sabotage.magnitude_pct
        ),
        "sabotage.false_rumor_base_cost_gold": (
            old.sabotage.false_rumor_base_cost_gold,
            new.sabotage.false_rumor_base_cost_gold,
        ),
        "sabotage.false_rumor_magnitude_pct": (
            old.sabotage.false_rumor_magnitude_pct,
            new.sabotage.false_rumor_magnitude_pct,
        ),
        "sabotage.suspicion_increase_sabotage": (
            old.sabotage.suspicion_increase_sabotage,
            new.sabotage.suspicion_increase_sabotage,
        ),
        "sabotage.suspicion_increase_false_rumor": (
            old.sabotage.suspicion_increase_false_rumor,
            new.sabotage.suspicion_increase_false_rumor,
        ),
        "events.voyage_frequency_per_day": (
            old.events.voyage_frequency_per_day,
            new.events.voyage_frequency_per_day,
        ),
        "events.port_frequency_per_day_start": (
            old.events.port_frequency_per_day_start,
            new.events.port_frequency_per_day_start,
        ),
        "events.positive_ratio": (
            old.events.positive_ratio, new.events.positive_ratio
        ),
    }
    for path, (a, b) in paths_values.items():
        if a == b:
            continue
        if path in LIVE_FIELDS:
            changes["live"].append(path)
        elif path in SESSION_FIELDS:
            changes["session"].append(path)
        elif path in NEWGAME_FIELDS:
            changes["newgame"].append(path)
    return changes


def reload() -> ReloadResult:
    """Les balance.json på nytt og swap inn nye verdier in-place.

    In-place-mutasjon: alle eksisterende `get()`-referanser ser nye
    verdier uten å måtte re-lese singletonen.

    Ved feil (manglende eller ødelagt fil) beholder vi eksisterende
    instans uendret og returnerer `ReloadResult(success=False, error=...)`.
    """
    global _instance
    if _instance is None:
        return ReloadResult(success=False, error="Balance ikke initialisert")
    try:
        new = load_from_path(_path)
    except FileNotFoundError as exc:
        log.warning("Balance reload: fil mangler (%s)", exc)
        return ReloadResult(success=False, error=f"Fil mangler: {_path}")
    except (json.JSONDecodeError, ValueError) as exc:
        log.warning("Balance reload: ugyldig fil (%s)", exc)
        return ReloadResult(success=False, error=f"Ugyldig balance.json: {exc}")

    diff = _diff_fields(_instance, new)

    # In-place swap: kopier hvert top-level felt over. Beholder dermed
    # instans-identitet slik at referanser i konsumenter fortsatt peker
    # på singletonen.
    for f in fields(_instance):
        setattr(_instance, f.name, getattr(new, f.name))

    log.info(
        "Balance reloadet: %d live, %d session, %d newgame endringer",
        len(diff["live"]), len(diff["session"]), len(diff["newgame"]),
    )
    return ReloadResult(
        success=True,
        live_changes=diff["live"],
        session_changes=diff["session"],
        newgame_changes=diff["newgame"],
    )


def _reset_for_tests() -> None:
    """Tøm singleton. Kun for bruk i tester."""
    global _instance, _path
    _instance = None
    _path = DEFAULT_BALANCE_PATH
