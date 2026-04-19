"""ObservedPrice — "siste sett"-pris i en havn spilleren ikke er i.

Per FASE_2B.md §2.3: ingen regime- eller trend-felt. Utdatert data skal
ikke lyve om retning. UI viser `?` for trend på stale data (stale-grense
i `balance.observed.stale_threshold_days`).

C8: helpers for days_since + is_stale brukes av tooltip-rendering på
verdenskartet og kan utvides senere til rykte-system (Fase 3) som vil
ha samme stale-semantikk for ulike data-typer.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ObservedPrice:
    price: float
    day_seen: int

    def days_since(self, current_day: int) -> int:
        """Antall dager siden prisen ble observert.

        Klampet til 0 hvis `day_seen` ligger i framtiden (urealistisk —
        skjer kun ved korrupt save eller tester med tilbakestilt klokke).
        """
        return max(0, current_day - self.day_seen)

    def is_stale(self, current_day: int, threshold_days: int) -> bool:
        """True hvis prisen er for gammel til å være pålitelig.

        Per spec §8.3: `days_since > threshold_days` regnes som stale.
        Default `threshold_days` leses av caller fra
        `balance.observed.stale_threshold_days` (5 i 2B-defaults).
        """
        return self.days_since(current_day) > threshold_days
