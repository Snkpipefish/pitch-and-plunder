"""Balansering fra `data/balance.json` — singleton med eksplisitt init.

Filosofi:
- `data/balance.json` inneholder alle tall man ønsker å iterere på under
  kalibrering (startgull, gebyr, upkeep, regime-drift, reise-kost).
- Strukturelle valg (hva en havn er, geografi) ligger i `data/ports.json`.
- Balance lastes ÉN gang ved spill-oppstart via `init()`. Senere kaller
  `get()` og returnerer den samme instansen til hele prosessen.
- `reload()` leser filen på nytt og bytter ut singletonens felt in-place
  slik at alle eksisterende `get()`-referanser automatisk ser nye verdier.
- Ingen lazy-load: manglende eller ødelagt balance.json får spillet til
  å feile tydelig ved oppstart (i `init()`), ikke ved første handel.

Hot-reload-kategorier (spec §4.4):
- LIVE: gjelder umiddelbart (transaction_fee, upkeep_per_day, production_per_day,
  drift_pct_*, noise_pct, travel.routes.*, stale_threshold_days)
- SESSION: gjelder fra neste dawn (seconds_per_day_in_port, seconds_per_day_at_sea)
- NEWGAME: krever ny save (starting_gold, ship_starting_cargo_capacity)
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
})

#: Felt som trer i kraft fra neste dawn.
SESSION_FIELDS: frozenset[str] = frozenset({
    "time.seconds_per_day_in_port",
    "time.seconds_per_day_at_sea",
})

#: Felt som kun gjelder for nye saves; ignoreres i nåværende sesjon.
NEWGAME_FIELDS: frozenset[str] = frozenset({
    "economy.starting_gold",
    "economy.ship_starting_cargo_capacity",
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
