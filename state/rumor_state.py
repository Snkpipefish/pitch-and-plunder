"""ActiveRumor — lytte-rykter (rumor_listen) spilleren har kjøpt.

Fase 3 C3-9 aktiverer dette: kjøp i tavern-natt-meny, RumorsDialog via
R-tast i PortVillageScene, TTL-decay via dawn-pipelinen.

Navnekonvensjon (FASE_3.md §1.9):
- `rumor_listen` = lytte-rykter (denne filen, bor i PlayerState.active_rumors)
- `rumor_spread` = offensiv falsk-rykte-spredning (bor i
  EconomyState.pending_rumor_impacts, se state/market_effects.py — C3-10)

Rykte-typer (`rumor_type`):
- `"regime_preview"` — avslører annen havns regime for en vare.
  Payload: `{"predicted_regime": "rising|stable|falling",
             "days_until_tick": int}`
- `"price_spike_warning"` — varsler forventet prisbevegelse.
  Payload: `{"direction": "up|down", "days_until_tick": int}`

**TTL-mekanikk** (Fase 3 C3-9, presisering #3):
`days_remaining` er en teller som dekrementeres én gang per dag via
`systems.rumors.on_dawn()` (kalt fra `economy.tick_all_ports_dawn`).
Rykter med `days_remaining <= 0` fjernes. Multi-day reise kaller
dawn N ganger, så TTL akkumuleres korrekt.

"Foreldet info"-utløp (regime har tiktet, spike har landet) er IKKE
implementert i C3-9 — kun TTL-basert utløp. Markerings-sjekk kobles
inn i C3-10 når market-effects eksisterer.
"""

from __future__ import annotations

from dataclasses import dataclass, field


#: Gyldige rumor_type-verdier. Validering i systems.rumors.
RUMOR_TYPES = frozenset({"regime_preview", "price_spike_warning"})


@dataclass
class ActiveRumor:
    """Ett aktivt lytte-rykte i spillerens besittelse.

    `days_remaining` er antall dager til ryktet utløper. Settes til
    `balance.rumors.ttl_days` ved kjøp og dekrementeres i dawn-pipeline.

    `port_id` og `commodity_id` er target for info-en.

    `payload` er type-spesifikk data:
    - regime_preview: `{"predicted_regime": str, "days_until_tick": int}`
    - price_spike_warning: `{"direction": str, "days_until_tick": int}`
    """

    rumor_type: str = "regime_preview"
    port_id: str = "tortuga"
    commodity_id: str = "sugar"
    days_remaining: int = 0
    payload: dict = field(default_factory=dict)
