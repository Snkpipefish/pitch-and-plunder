"""Offensiv markeds-manipulasjon: pending sabotasje + falske rykter (Fase 3 C3-0 stub).

STUB i C3-0: dataklassene er definert, men ingen purchase-logikk eller
impact-evaluering er koblet til. C3-10 implementerer begge felles.

Modell (FASE_3.md §1.8):
- `PendingSabotage`: spilleren har bestilt fysisk sabotasje mot en vare
  i en target-havn. Prisen HEVES ved impact_day (knapphet).
- `PendingRumorImpact`: spilleren har betalt for å spre falsk rykte.
  Prisen FALLER ved impact_day (kjøpmenn dumpet frykt-salg).

Begge konsumeres av `Market.on_dawn(day)` når `day == impact_day`.
`EconomyState.pending_sabotages` og `EconomyState.pending_rumor_impacts`
er to parallelle lister — samme lifecycle, forskjellig retning på
magnitude.

Placeholder-navn for Fase 3-referanse:
- `rumor_spread` = offensiv falsk-rykte-spredning (denne filen)
- `rumor_listen` = spillerens lytte-rykter (bor i state/rumor_state.py)
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PendingSabotage:
    """Bestilt sabotasje mot en vare i en target-havn.

    Magnitude er uttrykt som positiv prosent av base_price. Retning er
    alltid OPP (knapphet hever pris). C3-10 kaller
    `Market.on_dawn(day)` som konsumerer effekter med
    `impact_day == day`.

    `ordered_on_day` er bokføring for testing/UI ("bestilt dag N").
    `target_port` + `commodity_id` identifiserer hvor effekten lander.
    """

    target_port: str = "port_royal"
    commodity_id: str = "sugar"
    magnitude_pct: float = 10.0
    ordered_on_day: int = 0
    impact_day: int = 0


@dataclass
class PendingRumorImpact:
    """Falskt rykte (rumor_spread) — motparten til PendingSabotage.

    Magnitude er uttrykt som positiv prosent av base_price, men retning
    er alltid NED (falske rykter får kjøpmenn til å dumpe priser).
    C3-10 evaluerer tilsvarende som sabotasje men med motsatt fortegn.
    """

    target_port: str = "port_royal"
    commodity_id: str = "sugar"
    magnitude_pct: float = 10.0
    ordered_on_day: int = 0
    impact_day: int = 0
