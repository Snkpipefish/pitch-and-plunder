"""Debug-teleport (F1–F4) — aktiv kun i dev-mode (Fase 2B C6).

F1 → tortuga, F2 → port_royal, F3 → havana, F4 → nassau.

Per FASE_2B.md §10 C6: "F1-F4 = teleport til port 1-4 for testing.
Inventar og gull bevares ved teleport."

Caller (main.py) er ansvarlig for å:
1. Sjekke dev_mode.is_dev_mode() før `handle_teleport_key` kalles.
2. Utføre scene-bytte til "port_village" hvis teleport returnerer en
   port-id. Bytte via SceneManager sikrer at kildescenen (f.eks.
   WorldMapScene) avsluttes ryddig og ikke lekker scene-state som
   pulsering-timer eller fokus-havn.

Teleport avbryter IKKE en aktiv voyage i C6 — voyage eksisterer ikke
ennå. C7+ må håndtere voyage-avbryt eller avvise teleport under seiling.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import pygame

from config import port_config

if TYPE_CHECKING:
    from state import GameState


log = logging.getLogger(__name__)


#: F-nøkkel → port_id mapping. Rekkefølgen matcher spec-direktivet.
_TELEPORT_KEYS: dict[int, str] = {
    pygame.K_F1: "tortuga",
    pygame.K_F2: "port_royal",
    pygame.K_F3: "havana",
    pygame.K_F4: "nassau",
}


def handle_teleport_key(key: int, state: "GameState") -> str | None:
    """Utfør teleport hvis `key` er en teleport-nøkkel.

    Returnerer port_id hvis teleport utført, None ellers. Caller må
    trigge scene-bytte ved ikke-None retur.

    Oppdaterer:
    - `state.world_state.current_port` til target-havn
    - `state.player_state.position_x` til target-havnens `buildings.player_start_x`
      slik at spilleren spawn-er foran børsen i ny havn (ikke ved
      venstre dock-kant eller på en klamp-grense)

    Returnerer None hvis:
    - `key` ikke er F1-F4
    - port_id ikke finnes i port_config (skal ikke skje i 2B; defensiv)
    - target-havnen mangler buildings (ikke-Tortuga før C6; defensiv)

    Gull, inventar, clock og økonomi-state forblir uendret.
    """
    target = _TELEPORT_KEYS.get(key)
    if target is None:
        return None

    try:
        target_port = port_config.get(target)
    except KeyError:
        log.warning("Debug teleport: ukjent port_id %r", target)
        return None

    if target_port.buildings is None:
        log.warning(
            "Debug teleport: port %r mangler buildings-layout — avbryter",
            target,
        )
        return None

    state.world_state.current_port = target
    state.player_state.position_x = float(
        target_port.buildings.player_start_x
    )
    log.info("Debug teleport → %s (dev-mode)", target)
    return target
