"""VoyageState — aktiv reise mellom to havner.

`None` når spilleren er i en havn. Non-None kun under seiling. Oppdateres
hver frame med `progress` 0.0 → 1.0 under VoyageScene (lander i C7).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class VoyageState:
    from_port: str
    to_port: str
    depart_day: int
    arrival_day: int
    progress: float = 0.0
