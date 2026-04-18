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
from entities.commodity import InventoryItem


log = logging.getLogger(__name__)

#: Naaverende save-format. Bump naar schema endres; load() migrerer fra
#: eldre versjoner hvis mulig, ellers returnerer None (kaller faller
#: tilbake til GameState()).
CURRENT_SAVE_VERSION = 2

#: Versjoner som load() aksepterer (med migrering for ikke-current).
ACCEPTED_VERSIONS = frozenset({1, 2})


def _default_inventory() -> dict[str, InventoryItem]:
    return {
        "sugar": InventoryItem(),
        "rum": InventoryItem(),
        "tobacco": InventoryItem(),
        "pitch": InventoryItem(),
    }


@dataclass
class GameState:
    """Hele spillets serialiserbare tilstand."""

    version: int = CURRENT_SAVE_VERSION
    gold: int = constants.STARTING_GOLD
    inventory: dict[str, InventoryItem] = field(default_factory=_default_inventory)
    current_scene: str = "village"
    player_position: tuple[float, float] = (320.0, 280.0)
    day: int = 1
    commodities_state: dict[str, dict] = field(default_factory=dict)


def save(state: GameState, path: str = constants.SAVE_PATH) -> bool:
    """Skriv hele `state` til `path`. Returner True ved suksess.

    Skriver alltid i naaverende format (CURRENT_SAVE_VERSION).
    """
    try:
        parent = os.path.dirname(path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        # Tvinger current version ved save uansett hva state.version er
        state.version = CURRENT_SAVE_VERSION
        # asdict() rekurserer gjennom InventoryItem slik at inventory blir
        # {"sugar": {"quantity": N, "avg_cost": P}, ...}
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


def _parse_inventory(raw: object) -> dict[str, InventoryItem]:
    """Tolke lagret inventar fra v1 (int) eller v2 (dict) format.

    Ukjente eller korrupte poster settes til InventoryItem() (tom).
    """
    result = _default_inventory()
    if not isinstance(raw, dict):
        return result
    for cid, val in raw.items():
        if isinstance(val, int):
            # v1: mengde som int, ingen pris tilgjengelig
            result[cid] = InventoryItem(quantity=val, avg_cost=0.0)
        elif isinstance(val, dict):
            # v2: {"quantity": N, "avg_cost": P}
            try:
                qty = int(val.get("quantity", 0))
            except (TypeError, ValueError):
                qty = 0
            try:
                avg = float(val.get("avg_cost", 0.0))
            except (TypeError, ValueError):
                avg = 0.0
            result[cid] = InventoryItem(quantity=qty, avg_cost=avg)
        else:
            # Ukjent form – hold default
            pass
    # Soerg for at alle kjente varer finnes (setter default for manglende)
    for known_id in _default_inventory():
        result.setdefault(known_id, InventoryItem())
    return result


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
    if version not in ACCEPTED_VERSIONS:
        log.warning(
            "Ukjent save-versjon %r (aksepterer %s) – startverdier brukes",
            version,
            sorted(ACCEPTED_VERSIONS),
        )
        return None
    if version != CURRENT_SAVE_VERSION:
        log.info(
            "Migrerer save fra v%d til v%d", version, CURRENT_SAVE_VERSION
        )

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

    # Inventar: tolk v1 (int) eller v2 (dict) form
    inventory = _parse_inventory(data.get("inventory"))

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

    # Oppgrader version-feltet i retur-objektet til naaverende; neste save
    # skriver i v2-format uansett.
    return GameState(
        version=CURRENT_SAVE_VERSION,
        gold=gold,
        inventory=inventory,
        current_scene=current_scene,
        player_position=player_position,
        day=day,
        commodities_state=commodities_state,
    )
