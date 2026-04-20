"""Rom-meter-system — Fase 3 C3-8.

Spillerens hvile-tilstand `rest ∈ [0.0, 1.0]` bor i
`PlayerState.rest` (innført som stub i C3-0). Reduseres via eksplisitt
`consume_for_action(state, hours)`-kall fra hver tids-kostbar handler —
IKKE automatisk fra ActionBudget (som ikke er wiret til scene ennå).
Restaureres til 1.0 ved rom-kjøp i tavern (C3-3).

**Decay-formel** (presisering C3-8 #1):

    rest -= hours * decay_per_action / 1.0

Tolkning: `balance.rest.decay_per_action = 0.05` er decay for en
"standard handling" på 1.0 h. Kortere handlinger gir proporsjonalt
mindre decay:

- 0.25 h cache deposit: 0.25 × 0.05 = 0.0125
- 1.0 h bek-kjøp: 1.0 × 0.05 = 0.05
- 2.0 h sabotasje (C3-10): 2.0 × 0.05 = 0.10

Formelt: decay-rate per time = `decay_per_action / 1h` (0.05/h ved
default). Etter 20 "standard" 1-h-handlinger er rest=0 (20 × 0.05 = 1.0).

**Reise-decay** (`consume_for_voyage`): flerdagers-reise ville vært
uforholdsmessig drenerende med `days × 24 h` × 0.05/h = days × 1.2
rest-units (full drain etter 1 dag). Design-valg: reise-decay modell-
erer at sleep-at-sea-erfaring gir NOEN hvile, så bare 2 effektive
handle-timer per dag forbrukes. 2-dagers reise = 0.20 decay, 5-dagers
= 0.50 decay. Spilleren bør normalt kjøpe rom etter lengre reiser,
men overlever enkle ruter uten tvungen tavern-stopp.

**Tired-penalty** (`effective_cost`, presisering C3-8 #2): Pure
function. Returnerer `base_hours × tired_penalty_multiplier` (default
2.0) hvis `rest < EXHAUSTED_THRESHOLD`, ellers `base_hours`. Kalles
IKKE fra C3-8 (ActionBudget ikke wiret) — klar for senere cutover.

**Terskel for utmattelse**: `rest < 0.01` (`EXHAUSTED_THRESHOLD`).
Matcher HUD FLAME-bånd slik at "Rom: 0%"-display og penalty-aktivering
er konsistente. Player's `rest` klampes til 0.0 ved consume, så i
praksis triggeres penalty når rest er eksakt 0.0 etter flere handlinger.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from systems import balance as _balance

if TYPE_CHECKING:
    from state.game_state import GameState


#: Terskel for "utslitt"-tilstand. Aktiverer penalty i effective_cost()
#: og trigger FLAME-farge i HUD. Verdier ≤ 0.01 vises som "Rom: 0%"
#: (int-rundet) — holder UX konsistent med penalty-semantikken.
EXHAUSTED_THRESHOLD = 0.01

#: Effektive handle-timer per dag under reise. Reflekterer at sleep-at-
#: sea gir noen hvile, men ikke full restitusjon som et rom. Hardkodet
#: i C3-8; kan flyttes til balance.rest.voyage_hours_per_day ved
#: fremtidig tuning.
VOYAGE_EFFECTIVE_HOURS_PER_DAY = 2.0

#: Referanse-handlings-lengde for decay-formelen. `decay_per_action` i
#: balance er decay PER 1.0 h handling — kortere/lengre handlinger
#: skaleres proporsjonalt.
_STANDARD_ACTION_HOURS = 1.0


def consume_for_action(state: "GameState", hours: float) -> None:
    """Reduser spillerens rest basert på timer forbrukt av handlingen.

    Kalles fra dialog-handlere som utfører tids-kostbare handlinger
    (bek-kjøp, sabotasje, cache-commit, osv.). Klampes til 0.0 — kan
    ikke gå negativt.

    `hours <= 0` er no-op (defensivt — callere trenger ikke filtrere
    "gratis" handlinger som enter_building).
    """
    if hours <= 0:
        return
    decay_per_hour = _balance.get().rest.decay_per_action / _STANDARD_ACTION_HOURS
    state.player_state.rest = max(
        0.0, state.player_state.rest - hours * decay_per_hour
    )


def consume_for_voyage(state: "GameState", days: int) -> None:
    """Reise-spesifikk decay — flerdagers-reise med sleep-at-sea-rabatt.

    Tolker `days` × `VOYAGE_EFFECTIVE_HOURS_PER_DAY` (default 2.0) som
    effektive handle-timer, så konsument-formelen stemmer med
    consume_for_action.

    `days <= 0` er no-op (defensivt — caller trenger ikke filtrere).
    """
    if days <= 0:
        return
    consume_for_action(state, days * VOYAGE_EFFECTIVE_HOURS_PER_DAY)


def restore(state: "GameState") -> None:
    """Gjenopprett rest til 1.0 (full hvile). Kalt fra rom-kjøp.

    Er ikke avhengig av balance — rom-kjøp gir ALLTID full restitusjon
    uavhengig av pre-rest-nivå (kan ikke "overskudd-hvile" ≥ 1.0).
    """
    state.player_state.rest = 1.0


def effective_cost(state: "GameState", base_hours: float) -> float:
    """Pure function: returnér faktisk tids-kost for en handling.

    Hvis spilleren er utslitt (`rest < EXHAUSTED_THRESHOLD`), multipliseres
    `base_hours` med `balance.rest.tired_penalty_multiplier` (default 2.0).
    Ellers returneres `base_hours` uendret.

    INGEN state-mutasjon. Pure for C3-8 (presisering #2) — klar for
    ActionBudget-cutover i senere commit. Beskriver hva ActionBudget
    SKAL forbruke; ikke hva som forbrukes fra `rest` selv (det er
    `consume_for_action` sin rolle, drevet av base_hours).
    """
    if is_exhausted(state):
        return base_hours * _balance.get().rest.tired_penalty_multiplier
    return base_hours


def is_exhausted(state: "GameState") -> bool:
    """True hvis `rest < EXHAUSTED_THRESHOLD`.

    Matcher HUD FLAME-bånd-grense slik at penalty-aktivering og "Rom:
    0%"-display skjer samtidig.
    """
    return state.player_state.rest < EXHAUSTED_THRESHOLD
