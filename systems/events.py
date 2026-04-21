"""Random events — Fase 3 C3-11.

Data-drevet events-rammeverk med vekt-basert sampling. Events bor i
`data/events.json` og lastes via `init()` ved oppstart. Hvert event har:

- `id`: unik streng (f.eks. "shipwreck", "sickness")
- `context`: "voyage" eller "port"
- `weight`: vekt i sampling (kun blant events med samme (context, polarity))
- `positive`: bool — positivt event eller negativt
- `title` + `body`: tekst for EventDialog
- `effects`: liste av {type, value} — applyes av `resolve()`

**Effekt-typer (hybrid data + kode):**

Data-drevne (ren mutasjon på state):
- `gold_loss_pct`: trekk `value`% av spillerens gull (floor 0)
- `gold_gain_fixed`: legg til `value` gull
- `suspicion_increase`: kall `suspicion.increase(state, value)`
- `rest_spike`: trekk `value` fra rest (clamp 0..1). Negative verdier
  tillatt (liten boost).
- `rest_restore`: sett rest = `value` direkte (typisk 1.0 for full
  restore, klampet 0..1).
- `voyage_delay_days`: øk `voyage.arrival_day` med `value` (heltall).
  No-op hvis ingen aktiv voyage.

Kode-drevne (trenger egen logikk):
- `shipwreck_death_roll`: `value` er pct dødsrate. RNG-roll. Ved død:
  sett `state.dead=True`, `state.death_cause=event_id`. Uansett utfall:
  full gull-tap (spilleren mister alt gullet i skipet).
- `sickness_death_check`: `value` er rest-terskel. Hvis rest < value
  ETTER rest_spike + gull-tap, sett `state.dead=True`.

**Sampling:**

`sample_voyage_event(state, rng)` / `sample_port_event(state, rng)`:
1. Kast terning mot frekvens (`balance.events.voyage_frequency_per_day`
   eller `port_frequency_per_day_start`).
2. Hvis hit: bestem polarity via `positive_ratio`.
3. Vekt-basert sampling blant events med samme (context, polarity).
4. Returnér event-id eller None.

Arrested/dead spillere får ingen nye events (short-circuit i sampling).

**Resolver:**

`resolve(state, event_id, rng)` returnerer tuple (title, body,
death_triggered: bool). Muterer state i-stedet. Caller (VoyageScene /
PortVillageScene) konsumerer returverdien for å bygge EventDialog +
sjekke om game-over skal trigges.
"""

from __future__ import annotations

import json
import logging
import os
import random
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional

from systems import balance as _balance

if TYPE_CHECKING:
    from state.game_state import GameState


log = logging.getLogger(__name__)


DEFAULT_EVENTS_PATH = os.path.join("data", "events.json")

VALID_CONTEXTS: frozenset[str] = frozenset({"voyage", "port"})

#: Tillatte effekt-typer — valideres ved load() for å fange typos tidlig.
VALID_EFFECT_TYPES: frozenset[str] = frozenset({
    "gold_loss_pct",
    "gold_gain_fixed",
    "suspicion_increase",
    "rest_spike",
    "rest_restore",
    "voyage_delay_days",
    "shipwreck_death_roll",
    "sickness_death_check",
})


@dataclass(frozen=True)
class EventEffect:
    type: str
    value: float


@dataclass(frozen=True)
class Event:
    id: str
    context: str
    weight: float
    positive: bool
    title: str
    body: str
    effects: tuple[EventEffect, ...] = field(default_factory=tuple)


def _parse_event(raw: dict) -> Event:
    try:
        ev_id = str(raw["id"])
        context = str(raw["context"])
        if context not in VALID_CONTEXTS:
            raise ValueError(f"context={context!r} ikke i {VALID_CONTEXTS}")
        weight = float(raw.get("weight", 1.0))
        if weight <= 0:
            raise ValueError(f"weight må være > 0, fikk {weight}")
        positive = bool(raw.get("positive", False))
        title = str(raw.get("title", ev_id))
        body = str(raw.get("body", ""))
        raw_effects = raw.get("effects", [])
        if not isinstance(raw_effects, list):
            raise ValueError("effects må være liste")
        effects: list[EventEffect] = []
        for entry in raw_effects:
            if not isinstance(entry, dict):
                raise ValueError(f"effect-entry må være dict, fikk {entry!r}")
            et = str(entry.get("type", ""))
            if et not in VALID_EFFECT_TYPES:
                raise ValueError(f"effect.type={et!r} ikke i {VALID_EFFECT_TYPES}")
            ev = float(entry.get("value", 0.0))
            effects.append(EventEffect(type=et, value=ev))
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"event {raw!r}: {exc}") from exc
    return Event(
        id=ev_id, context=context, weight=weight, positive=positive,
        title=title, body=body, effects=tuple(effects),
    )


def load_from_path(path: str) -> dict[str, Event]:
    with open(path, "r", encoding="utf-8") as fh:
        raw = json.load(fh)
    events_raw = raw.get("events", [])
    if not isinstance(events_raw, list):
        raise ValueError("events.json: 'events' må være liste")
    result: dict[str, Event] = {}
    for entry in events_raw:
        ev = _parse_event(entry)
        if ev.id in result:
            raise ValueError(f"events.json: duplikat id {ev.id!r}")
        result[ev.id] = ev
    return result


# --- Singleton ---

_catalog: dict[str, Event] = {}
_path: str = DEFAULT_EVENTS_PATH


def init(path: str = DEFAULT_EVENTS_PATH) -> dict[str, Event]:
    """Last events.json eksplisitt ved oppstart. Feiler høylydt ved
    manglende eller ødelagt fil — samme filosofi som balance.init().
    """
    global _catalog, _path
    _path = path
    _catalog = load_from_path(path)
    log.info("Events lastet fra %s (%d events)", path, len(_catalog))
    return _catalog


def get_all() -> dict[str, Event]:
    return dict(_catalog)


def get(event_id: str) -> Event:
    return _catalog[event_id]


def is_initialized() -> bool:
    return bool(_catalog)


def _reset_for_tests() -> None:
    global _catalog, _path
    _catalog = {}
    _path = DEFAULT_EVENTS_PATH


# --- Sampling ---


def _pick_weighted(
    candidates: list[Event], rng: random.Random
) -> Optional[Event]:
    if not candidates:
        return None
    total = sum(e.weight for e in candidates)
    if total <= 0:
        return None
    r = rng.uniform(0.0, total)
    cum = 0.0
    for ev in candidates:
        cum += ev.weight
        if r <= cum:
            return ev
    return candidates[-1]


def _sample_event(
    state: "GameState",
    context: str,
    frequency: float,
    rng: random.Random,
) -> Optional[Event]:
    """Felles sampling-logikk for voyage- og port-events.

    Short-circuit ved arrested/dead — døde/arresterte får ingen nye
    events.
    """
    if state.arrested or state.dead:
        return None
    if frequency <= 0.0:
        return None
    if rng.random() >= frequency:
        return None
    positive_ratio = _balance.get().events.positive_ratio
    want_positive = rng.random() < positive_ratio
    candidates = [
        ev for ev in _catalog.values()
        if ev.context == context and ev.positive == want_positive
    ]
    if not candidates:
        # Degenerert: ingen events med ønsket polarity — prøv motsatt.
        candidates = [
            ev for ev in _catalog.values() if ev.context == context
        ]
    return _pick_weighted(candidates, rng)


def sample_voyage_event(
    state: "GameState", rng: Optional[random.Random] = None,
) -> Optional[str]:
    """Sample et voyage-event for denne dawn-tikken. Returnerer event-id
    eller None."""
    rng = rng or random.Random()
    freq = _balance.get().events.voyage_frequency_per_day
    ev = _sample_event(state, "voyage", freq, rng)
    return ev.id if ev is not None else None


def sample_port_event(
    state: "GameState", rng: Optional[random.Random] = None,
) -> Optional[str]:
    """Sample et port-event for denne dawn-tikken. Returnerer event-id
    eller None."""
    rng = rng or random.Random()
    freq = _balance.get().events.port_frequency_per_day_start
    ev = _sample_event(state, "port", freq, rng)
    return ev.id if ev is not None else None


# --- Resolver ---


def _apply_gold_loss_pct(state: "GameState", pct: float) -> None:
    if pct <= 0:
        return
    loss = int(state.player_state.gold * pct / 100.0)
    state.player_state.gold = max(0, state.player_state.gold - loss)


def _apply_gold_gain(state: "GameState", amount: float) -> None:
    if amount <= 0:
        return
    state.player_state.gold += int(amount)


def _apply_rest_spike(state: "GameState", amount: float) -> None:
    new_rest = state.player_state.rest - amount
    state.player_state.rest = max(0.0, min(1.0, new_rest))


def _apply_rest_restore(state: "GameState", value: float) -> None:
    state.player_state.rest = max(0.0, min(1.0, value))


def _apply_voyage_delay(state: "GameState", days: float) -> None:
    voyage = state.world_state.voyage
    if voyage is None:
        return
    voyage.arrival_day += int(days)


def resolve(
    state: "GameState",
    event_id: str,
    rng: Optional[random.Random] = None,
) -> tuple[str, str, bool]:
    """Applyer effekter for `event_id`. Returnerer (title, body, died).

    `died` er True hvis event-effekten trigget dødelig utfall
    (shipwreck_death_roll hit, eller sickness_death_check rest < value).
    I begge tilfeller er `state.dead` og `state.death_cause` allerede
    satt — caller trenger kun å signalere game-over.

    Applyer effekter i rekkefølgen de står i events.json. Rekkefølgen
    betyr noe for sickness: `rest_spike` kjører før `sickness_death_check`
    slik at dødssjekk leser oppdatert rest-verdi.
    """
    rng = rng or random.Random()
    from systems import suspicion as _suspicion

    ev = _catalog.get(event_id)
    if ev is None:
        log.warning("resolve: ukjent event_id=%r", event_id)
        return ("Ukjent hendelse", "", False)

    died = False
    for effect in ev.effects:
        et = effect.type
        val = effect.value
        if et == "gold_loss_pct":
            _apply_gold_loss_pct(state, val)
        elif et == "gold_gain_fixed":
            _apply_gold_gain(state, val)
        elif et == "suspicion_increase":
            _suspicion.increase(state, val)
        elif et == "rest_spike":
            _apply_rest_spike(state, val)
        elif et == "rest_restore":
            _apply_rest_restore(state, val)
        elif et == "voyage_delay_days":
            _apply_voyage_delay(state, val)
        elif et == "shipwreck_death_roll":
            # Full gull-tap uansett utfall (skipet forliste).
            state.player_state.gold = 0
            roll = rng.uniform(0.0, 100.0)
            if roll < val:
                state.dead = True
                state.death_cause = event_id
                died = True
        elif et == "sickness_death_check":
            if state.player_state.rest < val:
                state.dead = True
                state.death_cause = event_id
                died = True
    return (ev.title, ev.body, died)
