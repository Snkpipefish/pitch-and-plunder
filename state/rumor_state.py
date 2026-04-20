"""ActiveRumor — lytte-rykter (rumor_listen) spilleren har kjøpt (Fase 3 C3-0 stub).

STUB i C3-0: dataklassen er definert, men ingen kjøp-logikk eksisterer.
C3-9 implementerer kjøp i tavern, TTL-utløp, og integrasjon med
ObservedPrice.

Navnekonvensjon (FASE_3.md §1.9):
- `rumor_listen` = lytte-rykter (denne filen, bor i PlayerState.active_rumors)
- `rumor_spread` = offensiv falsk-rykte-spredning (bor i
  EconomyState.pending_rumor_impacts, se state/market_effects.py)

Rykte-typer (`rumor_type`):
- `"regime_preview"` — avslører annen havns neste regime for en vare
- `"price_spike_warning"` — varsler kommende prisbevegelse (inkludert
  spiller-utløste sabotasje/falske-rykte-effekter)

`payload` er en fri dict-form for type-spesifikk data (C3-9 definerer
konkret skjema per type).
"""

from __future__ import annotations

from dataclasses import dataclass, field


#: Gyldige rumor_type-verdier. Validering i C3-9.
RUMOR_TYPES = frozenset({"regime_preview", "price_spike_warning"})


@dataclass
class ActiveRumor:
    """Ett aktivt lytte-rykte i spillerens besittelse.

    `expires_on_day` er absolutt GameClock.day-verdi — når
    `clock.day >= expires_on_day` utløper ryktet (fjernes fra listen).
    TTL-beregning ved kjøp: `clock.day + rumors.ttl_days` (default 3).

    `port_id` og `commodity_id` er target for info-en.
    """

    rumor_type: str = "regime_preview"
    port_id: str = "tortuga"
    commodity_id: str = "sugar"
    expires_on_day: int = 0
    payload: dict = field(default_factory=dict)
