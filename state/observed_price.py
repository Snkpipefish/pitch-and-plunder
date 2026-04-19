"""ObservedPrice — "siste sett"-pris i en havn spilleren ikke er i.

Per FASE_2B.md §2.3: ingen regime- eller trend-felt. Utdatert data skal
ikke lyve om retning. UI viser `?` for trend på stale data (stale-grense
i `balance.observed.stale_threshold_days`).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ObservedPrice:
    price: float
    day_seen: int
