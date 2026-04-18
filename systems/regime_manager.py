"""Markedsregimer per vare.

En vare er til enhver tid i ett av tre regimer: `rising` (svak positiv
drift-bias), `stable` (ingen bias, lav volatilitet), eller `falling` (svak
negativ drift-bias). Regimer varer 3–5 dager og byttes ved dag-skift via
en Markov-lignende overgang. Spilleren ser IKKE regimet direkte – det må
leses fra pris-historikken (sparkline i børs-UI).

Regime-tabell (per spec §2.1):

    Regime    | Bias per tick | Volatilitet-multiplier
    ----------|---------------|------------------------
    rising    | +0.5 %        | 1.0×
    stable    |  0 %          | 0.7×
    falling   | -0.5 %        | 1.0×

Markov-overgang:
- Etter et volatilt regime (rising/falling) er `stable` dobbelt så
  sannsynlig som et nytt volatilt regime. Dette gir naturlige
  avkjølingsperioder.
- Samme regime to ganger på rad blokkerer det regimet fra å velges for
  tredje gang – unngår monotone trender.
- Ingen andre prioriteringer; ellers likt fordelt blant mulige regimer.

Historien bevares som liste av de siste 10 regimene (rullerende vindu).
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field


#: Gyldige regime-strenger. Bruker tuple (immutable) for å tydeliggjøre
#: at dette er et fast sett; ikke en konfig.
REGIMES: tuple[str, ...] = ("rising", "stable", "falling")

#: Drift-bias per tick (multiplier på current_price i tillegg til random drift).
REGIME_BIAS: dict[str, float] = {
    "rising": 0.005,
    "stable": 0.0,
    "falling": -0.005,
}

#: Multiplier på random-drift-amplituden per regime.
REGIME_VOL_MULT: dict[str, float] = {
    "rising": 1.0,
    "stable": 0.7,
    "falling": 1.0,
}

#: Min/maks dager et nytt regime varer før det kan byttes.
MIN_REGIME_DAYS = 3
MAX_REGIME_DAYS = 5

#: Hvor mange tidligere regimer som holdes i history (rullerende).
HISTORY_WINDOW = 10


@dataclass
class RegimeState:
    """Regime-tilstand for én vare."""

    current: str = "stable"
    days_remaining: int = 0
    history: list[str] = field(default_factory=list)


class RegimeManager:
    """Håndterer regime-overganger ved dag-skift.

    Holder ingen state selv (utenom RNG); all state ligger i
    `RegimeState`-instansene i GameState. Det gjør det enkelt å
    teste: konstruer en Manager med seedet RNG og evaluer logikken
    deterministisk.
    """

    def __init__(self, rng: random.Random | None = None) -> None:
        self._rng = rng or random.Random()

    # --- Initialisering (first boot) ---

    def initialize_regimes(
        self, commodity_ids: list[str]
    ) -> dict[str, RegimeState]:
        """Bygg en ny regime-samling for alle oppgitte varer.

        Alle starter i `stable` med 3–5 dager igjen (tilfeldig), og tom
        historikk. Kalles ved første spillstart eller når en lagret state
        mangler regimer for en kjent vare.
        """
        return {
            cid: RegimeState(
                current="stable",
                days_remaining=self._rng.randint(
                    MIN_REGIME_DAYS, MAX_REGIME_DAYS
                ),
                history=[],
            )
            for cid in commodity_ids
        }

    # --- Dag-skift ---

    def on_new_day(
        self, regimes: dict[str, RegimeState]
    ) -> list[str]:
        """Tikk alle regime-klokker med én dag.

        Returnerer liste av vare-ider der regimet skiftet denne dagen.
        Muterer `regimes`-dict'en direkte.
        """
        changed: list[str] = []
        for cid, regime in regimes.items():
            regime.days_remaining -= 1
            if regime.days_remaining <= 0:
                old = regime.current
                regime.current = self._pick_next_regime(regime.history)
                regime.days_remaining = self._rng.randint(
                    MIN_REGIME_DAYS, MAX_REGIME_DAYS
                )
                # Legg til forrige regime sist i historien
                regime.history.append(old)
                if len(regime.history) > HISTORY_WINDOW:
                    del regime.history[: len(regime.history) - HISTORY_WINDOW]
                changed.append(cid)
        return changed

    def _pick_next_regime(self, history: list[str]) -> str:
        """Velg neste regime med vektet Markov-overgang.

        Vektregler:
        - `stable` får 2× vekt hvis siste regime var `rising` eller
          `falling` (avkjøling etter volatilitet).
        - Et regime som har gått to ganger på rad blokkeres (vekt 0)
          slik at vi unngår tre-på-rad.
        - Alle andre vekter starter på 1.0.
        """
        weights: dict[str, float] = {r: 1.0 for r in REGIMES}

        if history and history[-1] in ("rising", "falling"):
            weights["stable"] = 2.0

        if len(history) >= 2 and history[-1] == history[-2]:
            blocked = history[-1]
            weights[blocked] = 0.0

        total = sum(weights.values())
        if total <= 0.0:
            # Pathologisk case (alle blokkert) – fall tilbake til stable
            return "stable"
        roll = self._rng.uniform(0.0, total)
        cum = 0.0
        for regime in REGIMES:
            cum += weights[regime]
            if roll <= cum:
                return regime
        return "stable"  # numerisk fallback
