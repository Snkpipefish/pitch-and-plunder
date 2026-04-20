"""Tester for `_validate_harbormaster_placement` — Fase 3 C3-4.

Direkte-tester av overlap-deteksjon i port_config. Kan konstruere
syntetiske bbox-er for å verifisere at parser kaster ValueError ved
kollisjon med tavern eller exchange.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from config import port_config


@pytest.fixture
def _reset_ports():
    port_config._reset_for_tests()
    yield
    # Gjeninnsett default-konfig for resten av test-kjøringen
    port_config._reset_for_tests()
    root = Path(__file__).resolve().parent.parent
    port_config.init(str(root / "data" / "ports.json"))


def _minimal_port(name: str, harbormaster: dict | None = None) -> dict:
    """Bygg minimal port-config-dict for test."""
    port = {
        "name": name.title(),
        "world_map_position": [100, 100],
        "scene_class": "scenes.port_village:PortVillageScene",
        "world_width": 1200,
        "celestial": {
            "moon_worldx": 900,
            "sun_worldx_dawn": 1100,
            "sun_worldx_dusk": 100,
        },
        "price_bias": {
            "sugar": 1.0, "rum": 1.0, "tobacco": 1.0, "pitch": 1.0,
        },
        "regime_weights": {
            c: {"rising": 0.33, "stable": 0.34, "falling": 0.33}
            for c in ("sugar", "rum", "tobacco", "pitch")
        },
        "buildings": {
            "ground_top_y": 340,
            "player_start_x": 600,
            "tavern":   {"x": 20,  "y": 258, "w": 200, "h": 82},
            "exchange": {"x": 980, "y": 248, "w": 200, "h": 92},
            "npcs": {},
            "dock_interaction_range": [8, 80],
        }
    }
    if harbormaster is not None:
        port["buildings"]["harbormaster"] = harbormaster
    return port


def _write_ports_file(path: Path, harbormaster: dict | None) -> None:
    payload = {
        "version": 1,
        "ports": {
            "tortuga": _minimal_port("tortuga", harbormaster),
            "port_royal": _minimal_port("port_royal"),
            "havana": _minimal_port("havana"),
            "nassau": _minimal_port("nassau"),
        }
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


class TestHarbormasterOverlapValidation:
    def test_harbormaster_none_is_accepted(
        self, _reset_ports, tmp_path: Path
    ):
        """Harbormaster-felt kan mangle (None) uten feil."""
        path = tmp_path / "ports.json"
        _write_ports_file(path, harbormaster=None)
        port_config.init(str(path))  # skal ikke kaste
        p = port_config.get("tortuga")
        assert p.buildings.harbormaster is None

    def test_harbormaster_disjoint_is_accepted(
        self, _reset_ports, tmp_path: Path
    ):
        """Bbox disjunkt fra tavern/exchange → OK."""
        path = tmp_path / "ports.json"
        # tavern [20,220], exchange [980,1180], harbormaster [500,580]
        _write_ports_file(
            path,
            harbormaster={"x": 500, "y": 268, "w": 80, "h": 72},
        )
        port_config.init(str(path))
        p = port_config.get("tortuga")
        assert p.buildings.harbormaster is not None
        assert p.buildings.harbormaster.x == 500

    def test_harbormaster_overlapping_tavern_raises(
        self, _reset_ports, tmp_path: Path
    ):
        """Harbormaster krasjer med tavern [20,220] → ValueError."""
        path = tmp_path / "ports.json"
        _write_ports_file(
            path,
            # x=100 starter inne i tavern-bbox
            harbormaster={"x": 100, "y": 268, "w": 80, "h": 72},
        )
        with pytest.raises(ValueError, match="harbormaster-bbox overlapper tavern-bbox"):
            port_config.init(str(path))

    def test_harbormaster_overlapping_exchange_raises(
        self, _reset_ports, tmp_path: Path
    ):
        """Harbormaster krasjer med exchange [980,1180] → ValueError."""
        path = tmp_path / "ports.json"
        _write_ports_file(
            path,
            # x=1000 starter inne i exchange-bbox
            harbormaster={"x": 1000, "y": 268, "w": 80, "h": 72},
        )
        with pytest.raises(ValueError, match="harbormaster-bbox overlapper exchange-bbox"):
            port_config.init(str(path))

    def test_harbormaster_touching_edge_not_overlapping(
        self, _reset_ports, tmp_path: Path
    ):
        """Bbox som berører tavern-kant (x=220) er IKKE overlapp
        (axis-aligned strict-less-than test)."""
        path = tmp_path / "ports.json"
        # tavern slutter ved x=220; harbormaster starter ved x=220
        _write_ports_file(
            path,
            harbormaster={"x": 220, "y": 268, "w": 80, "h": 72},
        )
        port_config.init(str(path))  # skal ikke kaste
        p = port_config.get("tortuga")
        assert p.buildings.harbormaster is not None

    def test_harbormaster_y_disjoint_not_overlapping(
        self, _reset_ports, tmp_path: Path
    ):
        """Selv om x-range overlapper, så er y-disjunkt OK."""
        path = tmp_path / "ports.json"
        # Tavern y=[258, 340]. Harbormaster y=[100, 172] — y-disjunkt.
        # x overlapper ([100, 180] vs tavern [20, 220]) — men y-disjunkt
        # regnes som non-overlap per axis-aligned-test.
        _write_ports_file(
            path,
            harbormaster={"x": 100, "y": 100, "w": 80, "h": 72},
        )
        port_config.init(str(path))  # skal ikke kaste
