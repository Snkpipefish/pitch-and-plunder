"""Mistanke-system — Fase 3 C3-7.

Guvernør-mistanke på spilleren. Øker ved pirat-handlinger (sabotasje
C3-10, falske rykter C3-10), reduseres passivt med daily decay via
dawn-pipelinen. Ved `suspicion >= threshold` settes
`game_state.arrested = True` — flagget konsumeres av C3-12 score-
overlay for "arrestert"-game-over.

Alle funksjoner er pure over GameState. Ingen state lever i modulen.
Balance-verdier (threshold, daily_decay) leses live fra
`systems.balance` — hot-reload slår inn neste kall.

Kontrakt:

- `increase(state, amount)` øker suspicion, klampes IKKE (kan gå over
  threshold slik at check_threshold kan fange nøyaktig crossover).
- `decrease(state, amount)` reduserer suspicion, klampes til 0.
- `check_threshold(state)` setter `state.arrested=True` hvis
  suspicion >= threshold OG `arrest_on_threshold=True` i balance.
  Idempotent: kalles trygt flere ganger.
- `on_dawn(state)` utfører daglig decay. Kalt fra
  `economy.tick_all_ports_dawn` — kalles én gang per kalenderdag,
  uavhengig av om spilleren er i havn eller under reise (presisering
  C3-7 #1).
- `is_arrested(state)` leser `game_state.arrested`-flagget. C3-12
  poller dette.

Fase 3 C3-10 (sabotasje) og potensielt C3-11 (random events) kaller
`increase()` ved pirat-handlinger. Denne modulen har ingen kunnskap
om disse — kun basis-mekanikken.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from systems import balance as _balance

if TYPE_CHECKING:
    from state.game_state import GameState


def increase(state: "GameState", amount: float) -> None:
    """Øk suspicion med `amount`. Sjekker terskel etter økningen.

    `amount <= 0` er no-op (defensiv — callere trenger ikke filtrere).
    Suspicion klampes IKKE oppover — det er tillatt å gå over threshold
    slik at check_threshold detekterer crossover presist og markerer
    arrest. Etter arrest er verdien ikke lenger relevant.
    """
    if amount <= 0:
        return
    state.player_state.suspicion += amount
    check_threshold(state)


def decrease(state: "GameState", amount: float) -> None:
    """Reduser suspicion med `amount`. Klampes til 0.

    `amount <= 0` er no-op. Setter IKKE arrested=False hvis spilleren
    allerede er arrestert — en gang arrestert, alltid arrestert (frem
    til game-over).
    """
    if amount <= 0:
        return
    state.player_state.suspicion = max(
        0.0, state.player_state.suspicion - amount
    )


def check_threshold(state: "GameState") -> None:
    """Sett `arrested=True` hvis suspicion har nådd terskel.

    Respekterer `balance.suspicion.arrest_on_threshold`-flagget slik
    at testere kan deaktivere arrest-trigger ved balance-tuning.
    Idempotent — trygg å kalle flere ganger.
    """
    bal = _balance.get().suspicion
    if not bal.arrest_on_threshold:
        return
    if state.player_state.suspicion >= bal.threshold:
        state.arrested = True


def on_dawn(state: "GameState") -> None:
    """Daglig decay av suspicion. Kalt fra dawn-pipelinen (C3-7).

    Leser `balance.suspicion.daily_decay` live — hot-reload av balance
    slår inn neste dawn. Klampes til 0 via `decrease`.

    Flerdagers-reise: kalles N ganger fra `economy.tick_all_ports_dawn`
    (en gang per passert dag). Decay akkumuleres korrekt.
    """
    decay = _balance.get().suspicion.daily_decay
    decrease(state, decay)


def is_arrested(state: "GameState") -> bool:
    """Returnér True hvis spilleren er arrestert (game-over-hook).

    Konsumeres av C3-12 score-overlay. Ren read — ingen mutasjon.
    """
    return state.arrested
