"""ShipState — skipets klasse, navn og kapasitet.

I Fase 2B er `class_id` alltid "sloop" og `name` default "Sjarken".
Fase 3 åpner for flere skipsklasser via kapring.

`cargo_capacity` flyttet hit fra flat GameState per spec §2.3:
"cargo_capacity er skipets, ikke spillerens".
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ShipState:
    class_id: str = "sloop"
    name: str = "Sjarken"
    cargo_capacity: int = 40
