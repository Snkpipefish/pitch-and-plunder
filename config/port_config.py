"""PortConfig — statisk havn-data fra `data/ports.json`.

Lastes eksplisitt via `init()` ved spill-oppstart (etter `balance.init()`).
Manglende eller ugyldig fil feiler oppstart med klar melding (ingen
papegøye-fortsettelse med tomme havner).

Singletonens livssyklus speiler `systems/balance.py`:
- `init(path)` kalles én gang i main.py, leser og validerer alle 4 havner
- `get(port_id)` returnerer PortConfig-objekt for gitt id
- `get_all_port_ids()` returnerer iterable over alle havn-id-er

Validering ved load:
- Alle 4 forventede havner til stede (`tortuga`, `port_royal`, `havana`,
  `nassau`)
- Alle 4 varer (`sugar`, `rum`, `tobacco`, `pitch`) har oppføring i
  `price_bias` og `regime_weights`
- `regime_weights[cid]` summerer til 1.0 (±0.01 toleranse)
"""

from __future__ import annotations

import json
import logging
import math
import os
from dataclasses import dataclass
from typing import Any


log = logging.getLogger(__name__)


#: Filplassering relativt til prosjekt-rota.
DEFAULT_PORTS_PATH = os.path.join("data", "ports.json")

#: Havn-id-er spillet krever. Må matche `tests/fixtures/save_v4.json`
#: og `state/economy_state.py`-forventningene (som leser via denne modulen).
REQUIRED_PORTS: frozenset[str] = frozenset({
    "tortuga", "port_royal", "havana", "nassau",
})

#: Vare-id-er som må finnes i price_bias og regime_weights per havn.
REQUIRED_COMMODITIES: frozenset[str] = frozenset({
    "sugar", "rum", "tobacco", "pitch",
})

#: Gyldige regime-navn (matcher systems.regime_manager.REGIMES).
VALID_REGIME_NAMES: frozenset[str] = frozenset({"rising", "stable", "falling"})

#: Toleranse for regime_weights-sum-validering.
REGIME_WEIGHT_SUM_TOLERANCE: float = 0.01


@dataclass(frozen=True)
class CelestialConfig:
    """Verdens-x-koordinater for himmel-objekter i en havns scene.

    `moon_worldx` er statisk over "institusjonelt anker" (Børshus i Tortuga).
    `sun_worldx_dawn` og `sun_worldx_dusk` definerer solens bane gjennom
    dagen. Brukes først i C3 når celestial flyttes ut av konstanter.
    """
    moon_worldx: int
    sun_worldx_dawn: int
    sun_worldx_dusk: int


@dataclass(frozen=True)
class BuildingPlacement:
    """Rektangulær bygningsplassering (verdens-koordinater)."""
    x: int
    y: int
    w: int
    h: int


@dataclass(frozen=True)
class PortBuildings:
    """Per-havn scene-layout: bakkehøyde, bygninger, spiller-start, NPC-er.

    Fase 2B C4: flyttet fra hardkodede konstanter i `scenes/village_buildings.py`.
    Fase 2B C6: Port Royal, Havana, Nassau får layout + stub-havner aktiveres.
    `dock_interaction_range` flyttet fra modul-konstanter i port_village.py
    til per-havn buildings per direktiv (obligatorisk felt).
    """
    #: Y-pixel der bakken starter (spiller-føttene hviler på denne).
    ground_top_y: int
    #: Verdens-x der spilleren spawn-es ved fersk start i havnen.
    player_start_x: int
    tavern: BuildingPlacement
    exchange: BuildingPlacement
    #: Verdens-x for hver NPC (id → x). Y utledes fra ground_top_y.
    npcs: dict[str, int]
    #: Venstre-kant dock-region [min_x, max_x] som trigger verdenskart-
    #: interaksjon når spilleren står i. Tortuga + stub-havnene bruker
    #: (8, 80) — dock-sprite flyttes til buildings i C7 sammen med
    #: voyage-arbeidet.
    dock_interaction_range: tuple[int, int]


@dataclass(frozen=True)
class PortConfig:
    """Immutabel struktur per havn lastet fra ports.json.

    Felter som ikke brukes ennå (scene_class, world_map_position osv.)
    parses likevel og lagres for commits som kommer (C3/C4/C5).

    `buildings` er None for havner uten layout ennå (C4: Port Royal,
    Havana, Nassau). C6 legger til deres buildings-felt.
    """
    id: str
    name: str
    world_map_position: tuple[int, int]
    scene_class: str
    world_width: int
    celestial: CelestialConfig
    price_bias: dict[str, float]
    regime_weights: dict[str, dict[str, float]]
    buildings: PortBuildings | None = None


# --- Parsing ---

def _parse_celestial(raw: Any, port_id: str) -> CelestialConfig:
    if not isinstance(raw, dict):
        raise ValueError(f"port '{port_id}': celestial må være et objekt")
    try:
        return CelestialConfig(
            moon_worldx=int(raw["moon_worldx"]),
            sun_worldx_dawn=int(raw["sun_worldx_dawn"]),
            sun_worldx_dusk=int(raw["sun_worldx_dusk"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"port '{port_id}': ugyldig celestial-blokk: {exc}") from exc


def _parse_world_map_position(raw: Any, port_id: str) -> tuple[int, int]:
    if not isinstance(raw, (list, tuple)) or len(raw) != 2:
        raise ValueError(
            f"port '{port_id}': world_map_position må være [x, y]-liste"
        )
    try:
        return (int(raw[0]), int(raw[1]))
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"port '{port_id}': ugyldig world_map_position: {exc}"
        ) from exc


def _parse_price_bias(raw: Any, port_id: str) -> dict[str, float]:
    if not isinstance(raw, dict):
        raise ValueError(f"port '{port_id}': price_bias må være et objekt")
    result: dict[str, float] = {}
    for cid, val in raw.items():
        try:
            result[cid] = float(val)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"port '{port_id}': price_bias[{cid!r}] ugyldig: {exc}"
            ) from exc
    missing = REQUIRED_COMMODITIES - set(result.keys())
    if missing:
        raise ValueError(
            f"port '{port_id}': price_bias mangler varer {sorted(missing)}"
        )
    return result


def _parse_regime_weights(
    raw: Any, port_id: str
) -> dict[str, dict[str, float]]:
    if not isinstance(raw, dict):
        raise ValueError(f"port '{port_id}': regime_weights må være et objekt")
    result: dict[str, dict[str, float]] = {}
    for cid, weights in raw.items():
        if not isinstance(weights, dict):
            raise ValueError(
                f"port '{port_id}': regime_weights[{cid!r}] må være et objekt"
            )
        parsed: dict[str, float] = {}
        for regime_name, weight in weights.items():
            if regime_name not in VALID_REGIME_NAMES:
                raise ValueError(
                    f"port '{port_id}': regime_weights[{cid!r}] ukjent "
                    f"regime-navn {regime_name!r}"
                )
            try:
                parsed[regime_name] = float(weight)
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    f"port '{port_id}': regime_weights[{cid!r}][{regime_name!r}] "
                    f"ugyldig: {exc}"
                ) from exc
        # Alle 3 regime-navn må være til stede slik at random.choices ikke
        # får implisitt vekt 0 på manglende.
        missing_regimes = VALID_REGIME_NAMES - set(parsed.keys())
        if missing_regimes:
            raise ValueError(
                f"port '{port_id}': regime_weights[{cid!r}] mangler regimer "
                f"{sorted(missing_regimes)}"
            )
        total = sum(parsed.values())
        if not math.isclose(total, 1.0, abs_tol=REGIME_WEIGHT_SUM_TOLERANCE):
            raise ValueError(
                f"port '{port_id}': regime_weights[{cid!r}] summerer til "
                f"{total:.4f}, ikke 1.0 (±{REGIME_WEIGHT_SUM_TOLERANCE})"
            )
        result[cid] = parsed
    missing_commodities = REQUIRED_COMMODITIES - set(result.keys())
    if missing_commodities:
        raise ValueError(
            f"port '{port_id}': regime_weights mangler varer "
            f"{sorted(missing_commodities)}"
        )
    return result


def _parse_building_placement(
    raw: Any, port_id: str, building_name: str
) -> BuildingPlacement:
    if not isinstance(raw, dict):
        raise ValueError(
            f"port '{port_id}': buildings.{building_name} må være et objekt"
        )
    try:
        return BuildingPlacement(
            x=int(raw["x"]), y=int(raw["y"]),
            w=int(raw["w"]), h=int(raw["h"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(
            f"port '{port_id}': buildings.{building_name} ugyldig: {exc}"
        ) from exc


def _parse_buildings(raw: Any, port_id: str) -> PortBuildings | None:
    """Parse buildings-blokken. None hvis feltet mangler eller er null
    (havn uten layout ennå).
    """
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise ValueError(
            f"port '{port_id}': buildings må være et objekt eller null"
        )
    try:
        ground_top_y = int(raw["ground_top_y"])
        player_start_x = int(raw["player_start_x"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(
            f"port '{port_id}': buildings mangler/ugyldig felt: {exc}"
        ) from exc
    tavern = _parse_building_placement(raw.get("tavern"), port_id, "tavern")
    exchange = _parse_building_placement(
        raw.get("exchange"), port_id, "exchange"
    )
    npcs_raw = raw.get("npcs", {})
    if not isinstance(npcs_raw, dict):
        raise ValueError(
            f"port '{port_id}': buildings.npcs må være et objekt"
        )
    npcs: dict[str, int] = {}
    for npc_id, x_raw in npcs_raw.items():
        try:
            npcs[str(npc_id)] = int(x_raw)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"port '{port_id}': buildings.npcs[{npc_id!r}] ugyldig: {exc}"
            ) from exc
    # dock_interaction_range er obligatorisk (fail-fast) — introdusert
    # i C6, ikke valgfritt med fallback.
    dock_raw = raw.get("dock_interaction_range")
    if not isinstance(dock_raw, (list, tuple)) or len(dock_raw) != 2:
        raise ValueError(
            f"port '{port_id}': buildings.dock_interaction_range må være "
            f"[min_x, max_x]-liste"
        )
    try:
        dock_range = (int(dock_raw[0]), int(dock_raw[1]))
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"port '{port_id}': buildings.dock_interaction_range ugyldig: "
            f"{exc}"
        ) from exc
    if dock_range[0] >= dock_range[1]:
        raise ValueError(
            f"port '{port_id}': buildings.dock_interaction_range "
            f"min_x ({dock_range[0]}) må være mindre enn max_x "
            f"({dock_range[1]})"
        )
    return PortBuildings(
        ground_top_y=ground_top_y,
        player_start_x=player_start_x,
        tavern=tavern,
        exchange=exchange,
        npcs=npcs,
        dock_interaction_range=dock_range,
    )


def _parse_port(port_id: str, raw: Any) -> PortConfig:
    if not isinstance(raw, dict):
        raise ValueError(f"port '{port_id}': må være et objekt")
    try:
        name = str(raw["name"])
        scene_class = str(raw["scene_class"])
        world_width = int(raw["world_width"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"port '{port_id}': ugyldig toppnivå-felt: {exc}") from exc
    return PortConfig(
        id=port_id,
        name=name,
        world_map_position=_parse_world_map_position(
            raw.get("world_map_position"), port_id
        ),
        scene_class=scene_class,
        world_width=world_width,
        celestial=_parse_celestial(raw.get("celestial"), port_id),
        price_bias=_parse_price_bias(raw.get("price_bias"), port_id),
        regime_weights=_parse_regime_weights(raw.get("regime_weights"), port_id),
        buildings=_parse_buildings(raw.get("buildings"), port_id),
    )


def load_ports(path: str) -> dict[str, PortConfig]:
    """Les ports.json fra disk og bygg dict[port_id, PortConfig].

    Feil:
    - `FileNotFoundError` med klar melding hvis filen mangler
    - `ValueError` hvis JSON er ugyldig, havner mangler, eller vekter ikke
      summerer til 1.0
    """
    try:
        with open(path, "r", encoding="utf-8") as fh:
            raw = json.load(fh)
    except FileNotFoundError as exc:
        raise FileNotFoundError(
            f"ports-config mangler: {path} — "
            "data/ports.json er påkrevd for spill-oppstart"
        ) from exc
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"ports-config {path} inneholder ugyldig JSON: {exc}"
        ) from exc

    if not isinstance(raw, dict):
        raise ValueError(f"ports-config {path}: rot-objektet må være en dict")

    ports_raw = raw.get("ports")
    if not isinstance(ports_raw, dict):
        raise ValueError(
            f"ports-config {path}: 'ports'-feltet må være et objekt"
        )

    missing = REQUIRED_PORTS - set(ports_raw.keys())
    if missing:
        raise ValueError(
            f"ports-config {path}: mangler påkrevde havner {sorted(missing)}"
        )

    result: dict[str, PortConfig] = {}
    for port_id, port_raw in ports_raw.items():
        result[port_id] = _parse_port(port_id, port_raw)
    return result


# --- Singleton ---

_ports: dict[str, PortConfig] | None = None
_path: str = DEFAULT_PORTS_PATH


def init(path: str = DEFAULT_PORTS_PATH) -> dict[str, PortConfig]:
    """Last ports.json eksplisitt ved oppstart.

    Feiler høylydt ved manglende eller ødelagt fil — dette er en konfig-
    feil som skal stoppe spillet, ikke la det kjøre videre med tomme
    havner.
    """
    global _ports, _path
    _path = path
    _ports = load_ports(path)
    log.info("PortConfig lastet fra %s (%d havner)", path, len(_ports))
    return _ports


def get(port_id: str) -> PortConfig:
    """Returner PortConfig for gitt havn-id. Krever at `init()` er kalt."""
    if _ports is None:
        raise RuntimeError(
            "PortConfig ikke initialisert. Kall config.port_config.init() først."
        )
    if port_id not in _ports:
        raise KeyError(f"Ukjent port_id: {port_id!r}")
    return _ports[port_id]


def get_all() -> dict[str, PortConfig]:
    """Returner hele dict[port_id, PortConfig]. Krever init()."""
    if _ports is None:
        raise RuntimeError(
            "PortConfig ikke initialisert. Kall config.port_config.init() først."
        )
    return _ports


def get_all_port_ids() -> list[str]:
    """Returner sortert liste av havn-id-er. Tortuga først (home_port)."""
    if _ports is None:
        raise RuntimeError(
            "PortConfig ikke initialisert. Kall config.port_config.init() først."
        )
    # Stabil rekkefølge: tortuga først, resten i alfabetisk orden
    others = sorted(pid for pid in _ports if pid != "tortuga")
    return ["tortuga"] + others


def is_initialized() -> bool:
    return _ports is not None


def _reset_for_tests() -> None:
    """Tøm singleton. Kun for bruk i tester."""
    global _ports, _path
    _ports = None
    _path = DEFAULT_PORTS_PATH
