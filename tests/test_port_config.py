"""Tester for config/port_config.py."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from config import port_config as pc


PROJECT_ROOT = Path(__file__).resolve().parent.parent
REAL_PORTS_PATH = PROJECT_ROOT / "data" / "ports.json"


@pytest.fixture(autouse=True)
def _reset_port_config():
    pc._reset_for_tests()
    yield
    pc._reset_for_tests()


def _write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data), encoding="utf-8")


def _valid_port_payload(**overrides) -> dict:
    payload = {
        "name": "Tortuga",
        "world_map_position": [410, 230],
        "scene_class": "scenes.port_village:PortVillageScene",
        "world_width": 1600,
        "celestial": {
            "moon_worldx": 1350,
            "sun_worldx_dawn": 1500,
            "sun_worldx_dusk": 100,
        },
        "price_bias": {
            "sugar": 1.10, "rum": 1.10, "tobacco": 1.05, "pitch": 1.15,
        },
        "regime_weights": {
            "sugar":   {"rising": 0.33, "stable": 0.34, "falling": 0.33},
            "rum":     {"rising": 0.33, "stable": 0.34, "falling": 0.33},
            "tobacco": {"rising": 0.33, "stable": 0.34, "falling": 0.33},
            "pitch":   {"rising": 0.40, "stable": 0.35, "falling": 0.25},
        },
    }
    payload.update(overrides)
    return payload


def _valid_full_payload() -> dict:
    """Minimal gyldig ports.json med alle 4 påkrevde havner."""
    tortuga = _valid_port_payload()
    port_royal = _valid_port_payload(
        name="Port Royal", world_map_position=[180, 260],
    )
    havana = _valid_port_payload(name="Havana", world_map_position=[140, 140])
    nassau = _valid_port_payload(name="Nassau", world_map_position=[420, 110])
    return {
        "version": 1,
        "ports": {
            "tortuga": tortuga,
            "port_royal": port_royal,
            "havana": havana,
            "nassau": nassau,
        },
    }


# -----------------------------------------------------------------------------
# Load og parse
# -----------------------------------------------------------------------------

class TestLoad:
    def test_real_ports_json_loads_all_4(self) -> None:
        """Prosjektets faktiske data/ports.json laster alle 4 havner."""
        ports = pc.load_ports(str(REAL_PORTS_PATH))
        assert set(ports.keys()) == {"tortuga", "port_royal", "havana", "nassau"}
        for port in ports.values():
            assert isinstance(port, pc.PortConfig)

    def test_port_fields_parsed_correctly(self, tmp_path: Path) -> None:
        path = tmp_path / "ports.json"
        _write_json(path, _valid_full_payload())
        ports = pc.load_ports(str(path))

        tortuga = ports["tortuga"]
        assert tortuga.id == "tortuga"
        assert tortuga.name == "Tortuga"
        assert tortuga.world_map_position == (410, 230)
        assert tortuga.scene_class == "scenes.port_village:PortVillageScene"
        assert tortuga.world_width == 1600
        assert tortuga.celestial.moon_worldx == 1350
        assert tortuga.celestial.sun_worldx_dawn == 1500
        assert tortuga.celestial.sun_worldx_dusk == 100
        assert tortuga.price_bias["sugar"] == 1.10
        assert tortuga.regime_weights["pitch"]["rising"] == 0.40

    def test_world_map_position_is_tuple(self, tmp_path: Path) -> None:
        """JSON-liste skal parses til tuple (typestrikthet)."""
        path = tmp_path / "ports.json"
        _write_json(path, _valid_full_payload())
        ports = pc.load_ports(str(path))
        assert isinstance(ports["tortuga"].world_map_position, tuple)

    def test_price_bias_sanity_all_ports_have_all_commodities(self) -> None:
        """Sanity: hver havn har bias for alle 4 varer."""
        ports = pc.load_ports(str(REAL_PORTS_PATH))
        for port in ports.values():
            assert set(port.price_bias.keys()) == {
                "sugar", "rum", "tobacco", "pitch"
            }

    def test_regime_weights_sum_to_one(self) -> None:
        """Hver (port, commodity)-kombinasjon skal ha weights som summerer
        til 1.0 (±0.01)."""
        ports = pc.load_ports(str(REAL_PORTS_PATH))
        for port in ports.values():
            for cid, weights in port.regime_weights.items():
                total = sum(weights.values())
                assert abs(total - 1.0) < 0.01, (
                    f"{port.id}.{cid} summerer til {total}"
                )


# -----------------------------------------------------------------------------
# Fail-fast ved ugyldig konfig
# -----------------------------------------------------------------------------

class TestLoadFailures:
    def test_missing_file_raises_with_context(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError, match="ports-config mangler"):
            pc.load_ports(str(tmp_path / "does_not_exist.json"))

    def test_invalid_json_raises(self, tmp_path: Path) -> None:
        path = tmp_path / "bad.json"
        path.write_text("{not valid json", encoding="utf-8")
        with pytest.raises(ValueError, match="ugyldig JSON"):
            pc.load_ports(str(path))

    def test_missing_required_port_raises(self, tmp_path: Path) -> None:
        payload = _valid_full_payload()
        del payload["ports"]["havana"]
        path = tmp_path / "ports.json"
        _write_json(path, payload)
        with pytest.raises(ValueError, match="mangler påkrevde havner"):
            pc.load_ports(str(path))

    def test_weights_not_summing_raises(self, tmp_path: Path) -> None:
        payload = _valid_full_payload()
        # Bryt sugar-weights for tortuga: 0.5 + 0.5 + 0.5 = 1.5
        payload["ports"]["tortuga"]["regime_weights"]["sugar"] = {
            "rising": 0.5, "stable": 0.5, "falling": 0.5,
        }
        path = tmp_path / "ports.json"
        _write_json(path, payload)
        with pytest.raises(ValueError, match="summerer til"):
            pc.load_ports(str(path))

    def test_missing_commodity_in_price_bias_raises(self, tmp_path: Path) -> None:
        payload = _valid_full_payload()
        del payload["ports"]["tortuga"]["price_bias"]["pitch"]
        path = tmp_path / "ports.json"
        _write_json(path, payload)
        with pytest.raises(ValueError, match="price_bias mangler varer"):
            pc.load_ports(str(path))

    def test_missing_regime_name_raises(self, tmp_path: Path) -> None:
        payload = _valid_full_payload()
        # Tortuga sugar mangler "falling"
        payload["ports"]["tortuga"]["regime_weights"]["sugar"] = {
            "rising": 0.5, "stable": 0.5,
        }
        path = tmp_path / "ports.json"
        _write_json(path, payload)
        with pytest.raises(ValueError, match="mangler regimer"):
            pc.load_ports(str(path))

    def test_unknown_regime_name_raises(self, tmp_path: Path) -> None:
        payload = _valid_full_payload()
        payload["ports"]["tortuga"]["regime_weights"]["sugar"]["falling"] = None
        # Erstatt valid key med ugyldig navn
        payload["ports"]["tortuga"]["regime_weights"]["sugar"] = {
            "rising": 0.3, "stable": 0.4, "falling": 0.2, "crashing": 0.1,
        }
        path = tmp_path / "ports.json"
        _write_json(path, payload)
        with pytest.raises(ValueError, match="ukjent regime-navn"):
            pc.load_ports(str(path))


# -----------------------------------------------------------------------------
# Singleton
# -----------------------------------------------------------------------------

class TestSingleton:
    def test_init_and_get(self, tmp_path: Path) -> None:
        path = tmp_path / "ports.json"
        _write_json(path, _valid_full_payload())
        assert not pc.is_initialized()
        pc.init(str(path))
        assert pc.is_initialized()
        assert pc.get("tortuga").name == "Tortuga"
        assert pc.get("havana").name == "Havana"

    def test_get_without_init_raises(self) -> None:
        with pytest.raises(RuntimeError):
            pc.get("tortuga")

    def test_get_unknown_port_id_raises(self, tmp_path: Path) -> None:
        path = tmp_path / "ports.json"
        _write_json(path, _valid_full_payload())
        pc.init(str(path))
        with pytest.raises(KeyError):
            pc.get("atlantis")

    def test_get_all_port_ids_tortuga_first(self, tmp_path: Path) -> None:
        path = tmp_path / "ports.json"
        _write_json(path, _valid_full_payload())
        pc.init(str(path))
        ids = pc.get_all_port_ids()
        assert ids[0] == "tortuga"
        assert set(ids) == {"tortuga", "port_royal", "havana", "nassau"}

    def test_init_missing_file_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            pc.init(str(tmp_path / "nope.json"))


# -----------------------------------------------------------------------------
# Buildings (Fase 2B C4) — parser, validering, None for havner uten layout
# -----------------------------------------------------------------------------

def _valid_buildings_payload() -> dict:
    return {
        "ground_top_y": 340,
        "player_start_x": 1340,
        "tavern":   {"x": 20,   "y": 258, "w": 200, "h": 82},
        "exchange": {"x": 1380, "y": 248, "w": 200, "h": 92},
        "npcs": {"hawkins": 1470},
        "dock_interaction_range": [8, 80],
    }


class TestBuildingsParsing:
    def test_real_tortuga_has_buildings(self) -> None:
        """Faktisk data/ports.json har buildings for Tortuga."""
        ports = pc.load_ports(str(REAL_PORTS_PATH))
        tortuga = ports["tortuga"]
        assert tortuga.buildings is not None
        # Fase 2.6: ground_top_y skalert fra 340 til 255 (×270/360).
        assert tortuga.buildings.ground_top_y == 255
        assert tortuga.buildings.player_start_x == 1340
        assert tortuga.buildings.tavern.x == 20
        assert tortuga.buildings.exchange.x == 1380
        assert tortuga.buildings.npcs["hawkins"] == 1470

    def test_real_non_tortuga_ports_have_buildings_after_c6(self) -> None:
        """C6 aktiverte stub-havnene: Port Royal/Havana/Nassau har nå
        buildings-felt i ports.json (kopi av Tortugas layout klampet til
        respektiv world_width).
        """
        ports = pc.load_ports(str(REAL_PORTS_PATH))
        for pid in ("port_royal", "havana", "nassau"):
            assert ports[pid].buildings is not None, (
                f"{pid} skal ha buildings fra C6"
            )
            # Alle stub-havner bruker samme dock-range som Tortuga
            assert ports[pid].buildings.dock_interaction_range == (8, 80)
            # Player start er innenfor verdenes bredde
            assert 0 < ports[pid].buildings.player_start_x < ports[pid].world_width

    def test_buildings_parsed_from_synthetic_payload(self, tmp_path: Path) -> None:
        payload = _valid_full_payload()
        payload["ports"]["tortuga"]["buildings"] = _valid_buildings_payload()
        path = tmp_path / "ports.json"
        _write_json(path, payload)
        ports = pc.load_ports(str(path))
        tortuga = ports["tortuga"]
        assert tortuga.buildings is not None
        assert tortuga.buildings.tavern.w == 200
        assert tortuga.buildings.tavern.h == 82
        assert tortuga.buildings.exchange.w == 200

    def test_buildings_absent_gives_none(self, tmp_path: Path) -> None:
        payload = _valid_full_payload()
        # Tortuga uten buildings-felt
        assert "buildings" not in payload["ports"]["tortuga"]
        path = tmp_path / "ports.json"
        _write_json(path, payload)
        ports = pc.load_ports(str(path))
        assert ports["tortuga"].buildings is None

    def test_buildings_explicit_null_gives_none(self, tmp_path: Path) -> None:
        payload = _valid_full_payload()
        payload["ports"]["tortuga"]["buildings"] = None
        path = tmp_path / "ports.json"
        _write_json(path, payload)
        ports = pc.load_ports(str(path))
        assert ports["tortuga"].buildings is None


class TestBuildingsValidation:
    def test_missing_ground_top_y_raises(self, tmp_path: Path) -> None:
        payload = _valid_full_payload()
        buildings = _valid_buildings_payload()
        del buildings["ground_top_y"]
        payload["ports"]["tortuga"]["buildings"] = buildings
        path = tmp_path / "ports.json"
        _write_json(path, payload)
        with pytest.raises(ValueError, match="buildings mangler/ugyldig"):
            pc.load_ports(str(path))

    def test_missing_tavern_raises(self, tmp_path: Path) -> None:
        payload = _valid_full_payload()
        buildings = _valid_buildings_payload()
        del buildings["tavern"]
        payload["ports"]["tortuga"]["buildings"] = buildings
        path = tmp_path / "ports.json"
        _write_json(path, payload)
        with pytest.raises(ValueError, match="buildings.tavern"):
            pc.load_ports(str(path))

    def test_invalid_tavern_placement_raises(self, tmp_path: Path) -> None:
        payload = _valid_full_payload()
        buildings = _valid_buildings_payload()
        buildings["tavern"] = {"x": "not-a-number", "y": 258, "w": 200, "h": 82}
        payload["ports"]["tortuga"]["buildings"] = buildings
        path = tmp_path / "ports.json"
        _write_json(path, payload)
        with pytest.raises(ValueError, match="buildings.tavern"):
            pc.load_ports(str(path))

    def test_npcs_not_dict_raises(self, tmp_path: Path) -> None:
        payload = _valid_full_payload()
        buildings = _valid_buildings_payload()
        buildings["npcs"] = ["hawkins"]  # feil struktur (liste)
        payload["ports"]["tortuga"]["buildings"] = buildings
        path = tmp_path / "ports.json"
        _write_json(path, payload)
        with pytest.raises(ValueError, match="buildings.npcs"):
            pc.load_ports(str(path))

    def test_empty_npcs_ok(self, tmp_path: Path) -> None:
        """Havner uten NPC-er (hypotetisk) parser fortsatt med tomt dict."""
        payload = _valid_full_payload()
        buildings = _valid_buildings_payload()
        buildings["npcs"] = {}
        payload["ports"]["tortuga"]["buildings"] = buildings
        path = tmp_path / "ports.json"
        _write_json(path, payload)
        ports = pc.load_ports(str(path))
        assert ports["tortuga"].buildings.npcs == {}
