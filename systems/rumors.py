"""Rykte-system (rumor_listen) — Fase 3 C3-9.

Pure functions over GameState for å kjøpe og administrere aktive
lytte-rykter (`PlayerState.active_rumors`). To rumor-typer:

- **regime_preview**: Sampler tilfeldig annen havn (ikke current_port)
  + vare. Avslører gjeldende regime for den (port, commodity)-paret —
  tolkes som "hva du vil forvente ved neste dawn" (regimet kan tikke
  mellom nå og da; `days_until_tick`-payload forteller når). Alltid
  suksess — refund-sti ikke aktivert.

- **price_spike_warning**: Sampler blant (port, commodity)-par med
  aktivt volatilt regime (`rising` eller `falling`). Hvis ingen slike
  kandidater finnes → None-return (caller gir refund + toast).

Begge koster `balance.rumors.cost_gold` og `balance.rumors.cost_hours`.
TTL ved kjøp = `balance.rumors.ttl_days`.

**TTL-decay** (`on_dawn`): dekrementerer `days_remaining` for alle
aktive rykter. Fjerner rykter med `days_remaining <= 0`. Kalles fra
`economy.tick_all_ports_dawn` — én gang per dag-skift, inkludert
multi-day-reiser (dawn-tikkes N ganger).

**C3-10-kobling** (presisering #1): price_spike_warning-samplingen
utvides senere til å inkludere pending sabotage/false_rumor-effekter
fra `EconomyState.pending_*`. C3-9 dekker kun regime-drevne spikes.
"Foreldet info"-sjekk (ryktet peker på tikket-regime eller landet
spike) legges også til i C3-10. C3-9 har KUN TTL-basert utløp.
"""

from __future__ import annotations

import random
from typing import TYPE_CHECKING, Optional

from config import port_config
from state.rumor_state import ActiveRumor
from systems import balance as _balance

if TYPE_CHECKING:
    from state.game_state import GameState


#: Commodity-id-er (samme som REQUIRED_COMMODITIES i port_config).
_COMMODITIES: tuple[str, ...] = ("sugar", "rum", "tobacco", "pitch")

#: Regimer som kvalifiserer som "spike-kandidat" (volatile).
_VOLATILE_REGIMES: frozenset[str] = frozenset({"rising", "falling"})


def _sample_regime_preview_target(
    state: "GameState", rng: Optional[random.Random] = None
) -> tuple[str, str]:
    """Sample (port_id, commodity_id) der port != current_port.

    Tilfeldig blant de tre andre havnene × 4 varer = 12 kombinasjoner.
    Usikkerheten er del av mekanikken (presisering C3-9 #1): spilleren
    velger ikke havn.
    """
    rng = rng or random.Random()
    current = state.world_state.current_port
    other_ports = [
        p for p in port_config.get_all_port_ids() if p != current
    ]
    port = rng.choice(other_ports)
    commodity = rng.choice(_COMMODITIES)
    return port, commodity


def _find_spike_candidates(state: "GameState") -> list[tuple[str, str]]:
    """Returnér alle (port, commodity)-par med volatilt regime.

    Volatilt = `rising` eller `falling` (`_VOLATILE_REGIMES`). Stabile
    regimer filtreres bort — ingen spike å varsle om.

    Inkluderer current_port-kandidater også — presisering sier IKKE at
    price_spike_warning skal ekskludere current-havn. Spilleren kan
    uansett bruke varselet for timing-beslutninger (hvis de ikke har
    sett børsen nylig).
    """
    candidates: list[tuple[str, str]] = []
    for port_id, regimes in state.economy_state.regimes.items():
        for cid, regime_state in regimes.items():
            if regime_state.current in _VOLATILE_REGIMES:
                candidates.append((port_id, cid))
    return candidates


def buy_regime_preview(
    state: "GameState", rng: Optional[random.Random] = None
) -> Optional[ActiveRumor]:
    """Kjøp regime_preview-rykte. Sampler + legger til i active_rumors.

    Returnerer den nye ActiveRumor ved suksess. Trekker IKKE gull —
    det er caller (tavern-dialog) sin rolle.

    Alltid suksess — presisering #1 spesifiserer at regime-rykter
    sampler blant andre havner uten refund-path. Hvis det eneste
    andre port-sett er tomt (ikke reelt — 3 andre havner finnes
    alltid), sampler _sample_regime_preview_target likevel.
    """
    port_id, commodity_id = _sample_regime_preview_target(state, rng)
    regime_state = state.economy_state.regimes.get(port_id, {}).get(commodity_id)
    if regime_state is None:
        # Defensivt: ingen regime-state for target (skjer ikke i prod,
        # men kan skje i syntetiske tester med tom economy_state)
        predicted_regime = "stable"
        days_until_tick = 0
    else:
        predicted_regime = regime_state.current
        days_until_tick = max(0, regime_state.days_remaining)
    bal = _balance.get()
    rumor = ActiveRumor(
        rumor_type="regime_preview",
        port_id=port_id,
        commodity_id=commodity_id,
        days_remaining=bal.rumors.ttl_days,
        payload={
            "predicted_regime": predicted_regime,
            "days_until_tick": days_until_tick,
        },
    )
    state.player_state.active_rumors.append(rumor)
    return rumor


def buy_price_spike_warning(
    state: "GameState", rng: Optional[random.Random] = None
) -> Optional[ActiveRumor]:
    """Kjøp price_spike_warning-rykte. Returnerer None hvis ingen
    spike-kandidater finnes (caller skal da gi gull-refund + toast).

    Sampler blant aktive volatile regimer. C3-10 utvider kandidat-
    listen med pending sabotage/false_rumor-effekter — ikke forberedt
    nå.
    """
    rng = rng or random.Random()
    candidates = _find_spike_candidates(state)
    if not candidates:
        return None
    port_id, commodity_id = rng.choice(candidates)
    regime_state = state.economy_state.regimes[port_id][commodity_id]
    direction = "up" if regime_state.current == "rising" else "down"
    days_until_tick = max(0, regime_state.days_remaining)
    bal = _balance.get()
    rumor = ActiveRumor(
        rumor_type="price_spike_warning",
        port_id=port_id,
        commodity_id=commodity_id,
        days_remaining=bal.rumors.ttl_days,
        payload={
            "direction": direction,
            "days_until_tick": days_until_tick,
        },
    )
    state.player_state.active_rumors.append(rumor)
    return rumor


def on_dawn(state: "GameState") -> None:
    """TTL-decay: dekrementer `days_remaining` for alle aktive rykter.

    Fjerner rykter med `days_remaining <= 0` etter dekrementering.
    Kalles fra `economy.tick_all_ports_dawn` én gang per dag-skift.
    Multi-day reise: kalles N ganger, TTL akkumuleres korrekt.

    Ingen "foreldet info"-sjekk i C3-9 — KUN TTL. C3-10 kobler inn
    regime-tick- og spike-landing-deteksjon.
    """
    rumors = state.player_state.active_rumors
    # Dekrement først, så filter
    for r in rumors:
        r.days_remaining -= 1
    state.player_state.active_rumors = [
        r for r in rumors if r.days_remaining > 0
    ]
