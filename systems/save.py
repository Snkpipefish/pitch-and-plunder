"""Lagring og lasting av spilltilstand.

Designet enkelt: én JSON-fil per savegame. `save()` skriver hele `GameState`
til disk. `load()` leser og validerer mildt per felt; ved manglende fil
eller korrupt innhold returneres `None` slik at kaller kan falle tilbake
til `GameState()` (defaults).

Autosave-triggere (kalles fra VillageScene / main):
- `pygame.QUIT`
- Scene-bytte (infrastruktur for Fase 2+)
- Aapning og lukking av bors-overlay

Versjonering: `version: int`. Ukjent versjon -> tilbakefall til startverdier.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict, dataclass, field

import constants


log = logging.getLogger(__name__)

CURRENT_SAVE_VERSION = 1


@dataclass
class GameState:
    """Hele spillets serialiserbare tilstand."""

    version: int = CURRENT_SAVE_VERSION
    gold: int = constants.STARTING_GOLD
    inventory: dict[str, int] = field(
        default_factory=lambda: {"sugar": 0, "rum": 0, "tobacco": 0, "pitch": 0}
    )
    current_scene: str = "village"
    player_position: tuple[float, float] = (320.0, 280.0)
    day: int = 1
    commodities_state: dict[str, dict] = field(default_factory=dict)


def save(state: GameState, path: str = constants.SAVE_PATH) -> bool:
    """Skriv hele `state` til `path`. Returner True ved suksess."""
    try:
        parent = os.path.dirname(path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        data = asdict(state)
        # Tuple til list for JSON-vennlighet
        data["player_position"] = [
            float(state.player_position[0]),
            float(state.player_position[1]),
        ]
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, ensure_ascii=False)
        log.info("Lagret save til %s (gull=%d, dag=%d)", path, state.gold, state.day)
        return True
    except OSError as exc:
        log.warning("Klarte ikke lagre save til %s: %s", path, exc)
        return False


def load(path: str = constants.SAVE_PATH) -> GameState | None:
    """Les save fra `path`. None ved manglende eller ugyldig innhold."""
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except FileNotFoundError:
        log.info("Ingen save paa %s – startverdier brukes", path)
        return None
    except (OSError, json.JSONDecodeError) as exc:
        log.warning(
            "Kunne ikke lese save %s: %s – startverdier brukes", path, exc
        )
        return None

    version = data.get("version")
    if version != CURRENT_SAVE_VERSION:
        log.warning(
            "Ukjent save-versjon %r (forventet %d) – startverdier brukes",
            version,
            CURRENT_SAVE_VERSION,
        )
        return None

    defaults = GameState()

    # Player-posisjon: tuple av 2 floats
    raw_pos = data.get("player_position", list(defaults.player_position))
    if isinstance(raw_pos, (list, tuple)) and len(raw_pos) == 2:
        try:
            player_position = (float(raw_pos[0]), float(raw_pos[1]))
        except (TypeError, ValueError):
            player_position = defaults.player_position
    else:
        player_position = defaults.player_position

    inventory = data.get("inventory")
    if not isinstance(inventory, dict):
        inventory = dict(defaults.inventory)
    # Sørg for at alle kjente varer er til stede
    for cid, zero in defaults.inventory.items():
        inventory.setdefault(cid, zero)

    commodities_state = data.get("commodities_state", {})
    if not isinstance(commodities_state, dict):
        commodities_state = {}

    try:
        gold = int(data.get("gold", defaults.gold))
    except (TypeError, ValueError):
        gold = defaults.gold
    try:
        day = int(data.get("day", defaults.day))
    except (TypeError, ValueError):
        day = defaults.day

    current_scene = data.get("current_scene", defaults.current_scene)
    if not isinstance(current_scene, str):
        current_scene = defaults.current_scene

    return GameState(
        version=version,
        gold=gold,
        inventory=inventory,
        current_scene=current_scene,
        player_position=player_position,
        day=day,
        commodities_state=commodities_state,
    )
