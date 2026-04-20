"""Tester for Fase 2.5 C2.5-6a fyll-bygninger + smug.

Dekker:
- Alle 9 bake-funksjoner kjører uten krasj
- Silhuett-hierarki: alle fyll-bygninger ≤ 60 px
- Smug (alleys) er faktisk tomme (colorkey synlig)
- Parser validerer kind, høyde-grense, alley-bredde
- Havn-spesifikk stil: Tortuga kinds er bare for Tortuga, Nassau
  kinds bare for Nassau (6b vil utvide med port_royal_/havana_)
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pygame
import pytest

from config import port_config as pc


PROJECT_ROOT = Path(__file__).resolve().parent.parent
REAL_PORTS_PATH = PROJECT_ROOT / "data" / "ports.json"


@pytest.fixture(scope="module", autouse=True)
def _pygame_display():
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    pygame.display.init()
    pygame.font.init()
    pygame.display.set_mode((640, 360))
    yield
    pygame.font.quit()
    pygame.display.quit()


@pytest.fixture(autouse=True)
def _reset_port_config():
    pc._reset_for_tests()
    yield
    pc._reset_for_tests()


# --- Sprite-fabrikker ---

class TestFillBuildingBakers:
    def test_valid_kinds_include_all_tortuga_and_nassau(self):
        from entities.fill_buildings import VALID_FILL_BUILDING_KINDS

        expected_tortuga = {
            "tortuga_fishers_hut",
            "tortuga_boarding_house",
            "tortuga_lumber_warehouse",
            "tortuga_field_hospital",
            "tortuga_smithy",
        }
        expected_nassau = {
            "nassau_tavern_small",
            "nassau_improvised_warehouse",
            "nassau_patchwork_hut",
            "nassau_rope_workshop",
        }
        assert expected_tortuga <= VALID_FILL_BUILDING_KINDS
        assert expected_nassau <= VALID_FILL_BUILDING_KINDS

    def test_all_9_kinds_bake_without_crash(self):
        """Alle 9 fyll-bygninger (5 Tortuga + 4 Nassau) skal tegnes
        uten krasj."""
        from entities.fill_buildings import (
            bake_fill_building, VALID_FILL_BUILDING_KINDS,
        )

        surf = pygame.Surface((1600, 360)).convert()
        # Bruk moderate dimensjoner (innenfor hierarki-grensen)
        for kind in VALID_FILL_BUILDING_KINDS:
            bake_fill_building(
                surf, kind, x=100, w=60, h=40, ground_top_y=340,
            )

    def test_nassau_tavern_small_supports_style_variants(self):
        """Cluster-bygningen må støtte style_variant 0 og 1."""
        from entities.fill_buildings import bake_fill_building

        surf = pygame.Surface((400, 360)).convert()
        bake_fill_building(
            surf, "nassau_tavern_small", x=50, w=30, h=30,
            ground_top_y=340, style_variant=0,
        )
        bake_fill_building(
            surf, "nassau_tavern_small", x=100, w=30, h=30,
            ground_top_y=340, style_variant=1,
        )

    def test_unknown_kind_raises(self):
        from entities.fill_buildings import bake_fill_building

        surf = pygame.Surface((400, 360)).convert()
        with pytest.raises(ValueError, match="Ukjent fill_building.kind"):
            bake_fill_building(surf, "port_royal_mansion", 100, 60, 40, 340)

    def test_height_over_60_rejected_at_bake_time(self):
        """Silhuett-hierarki-regelen håndheves i bake-funksjonen også."""
        from entities.fill_buildings import bake_fill_building

        surf = pygame.Surface((400, 360)).convert()
        with pytest.raises(ValueError, match="silhuett-hierarki"):
            bake_fill_building(
                surf, "tortuga_fishers_hut", 100, 60, 80, 340,
            )

    def test_max_fill_building_height_constant(self):
        """Maks-høyde-konstanten er 60 (fyll-høy-tier-topp)."""
        from entities.fill_buildings import MAX_FILL_BUILDING_HEIGHT

        assert MAX_FILL_BUILDING_HEIGHT == 60


# --- Parser ---

class TestFillBuildingParser:
    def test_tortuga_has_5_fill_buildings(self):
        pc.init(str(REAL_PORTS_PATH))
        tortuga = pc.get("tortuga")
        assert len(tortuga.buildings.fill_buildings) == 5

    def test_nassau_has_5_fill_buildings_including_cluster(self):
        """Nassau: 2 tavern_small (cluster) + 3 andre = 5 totalt."""
        pc.init(str(REAL_PORTS_PATH))
        nassau = pc.get("nassau")
        assert len(nassau.buildings.fill_buildings) == 5

    def test_port_royal_havana_still_empty_fill_buildings(self):
        """C2.5-6b kommer; disse havnene skal ha tom fill_buildings."""
        pc.init(str(REAL_PORTS_PATH))
        for pid in ("port_royal", "havana"):
            port = pc.get(pid)
            assert len(port.buildings.fill_buildings) == 0

    def test_tortuga_fill_building_kinds_all_tortuga(self):
        """Havn-spesifikk stil: Tortuga bruker bare tortuga_-kinds."""
        pc.init(str(REAL_PORTS_PATH))
        tortuga = pc.get("tortuga")
        for fb in tortuga.buildings.fill_buildings:
            assert fb.kind.startswith("tortuga_"), (
                f"Tortuga har ikke-tortuga fill_building: {fb.kind}"
            )

    def test_nassau_fill_building_kinds_all_nassau(self):
        pc.init(str(REAL_PORTS_PATH))
        nassau = pc.get("nassau")
        for fb in nassau.buildings.fill_buildings:
            assert fb.kind.startswith("nassau_"), (
                f"Nassau har ikke-nassau fill_building: {fb.kind}"
            )

    def test_silhouette_hierarchy_enforced_in_real_data(self):
        """Alle fyll-bygninger i ports.json skal være ≤ 60 px."""
        pc.init(str(REAL_PORTS_PATH))
        for pid in ("tortuga", "nassau"):
            port = pc.get(pid)
            for fb in port.buildings.fill_buildings:
                assert fb.h <= 60, (
                    f"{pid}/{fb.kind}: h={fb.h} > 60 (silhuett-brudd)"
                )

    def test_fill_building_height_over_60_rejected(self, tmp_path):
        """Parser må avvise fill_building med h > 60."""
        ports_data = json.loads(REAL_PORTS_PATH.read_text(encoding="utf-8"))
        ports_data["ports"]["tortuga"]["buildings"]["fill_buildings"] = [
            {"kind": "tortuga_fishers_hut", "x": 240, "w": 60, "h": 80},
        ]
        path = tmp_path / "ports.json"
        path.write_text(json.dumps(ports_data), encoding="utf-8")
        with pytest.raises(ValueError, match="silhuett-hierarki"):
            pc.init(str(path))

    def test_unknown_fill_kind_rejected(self, tmp_path):
        ports_data = json.loads(REAL_PORTS_PATH.read_text(encoding="utf-8"))
        ports_data["ports"]["tortuga"]["buildings"]["fill_buildings"] = [
            {"kind": "space_station", "x": 100, "w": 60, "h": 40},
        ]
        path = tmp_path / "ports.json"
        path.write_text(json.dumps(ports_data), encoding="utf-8")
        with pytest.raises(ValueError, match="kind='space_station'"):
            pc.init(str(path))

    def test_style_variant_defaults_to_0(self, tmp_path):
        """Parser skal default style_variant til 0 hvis ikke angitt."""
        ports_data = json.loads(REAL_PORTS_PATH.read_text(encoding="utf-8"))
        ports_data["ports"]["tortuga"]["buildings"]["fill_buildings"] = [
            {"kind": "tortuga_fishers_hut", "x": 240, "w": 60, "h": 40},
        ]
        path = tmp_path / "ports.json"
        path.write_text(json.dumps(ports_data), encoding="utf-8")
        pc.init(str(path))
        fb = pc.get("tortuga").buildings.fill_buildings[0]
        assert fb.style_variant == 0


# --- Alleys ---

class TestAlleyParser:
    def test_tortuga_has_3_alleys(self):
        pc.init(str(REAL_PORTS_PATH))
        assert len(pc.get("tortuga").buildings.alleys) == 3

    def test_nassau_has_3_alleys(self):
        pc.init(str(REAL_PORTS_PATH))
        assert len(pc.get("nassau").buildings.alleys) == 3

    def test_all_alleys_have_valid_width(self):
        """Per spec §1.4: smug 20-40 px; parser tillater 16-40 for
        trange havner."""
        pc.init(str(REAL_PORTS_PATH))
        for pid in ("tortuga", "nassau"):
            for a in pc.get(pid).buildings.alleys:
                assert 16 <= a.w <= 40, (
                    f"{pid}: alley w={a.w} utenfor [16, 40]"
                )

    def test_alley_width_below_16_rejected(self, tmp_path):
        ports_data = json.loads(REAL_PORTS_PATH.read_text(encoding="utf-8"))
        ports_data["ports"]["tortuga"]["buildings"]["alleys"] = [
            {"x": 100, "w": 10},
        ]
        path = tmp_path / "ports.json"
        path.write_text(json.dumps(ports_data), encoding="utf-8")
        with pytest.raises(ValueError, match=r"alleys\[0\].w=10"):
            pc.init(str(path))

    def test_alley_width_above_40_rejected(self, tmp_path):
        ports_data = json.loads(REAL_PORTS_PATH.read_text(encoding="utf-8"))
        ports_data["ports"]["tortuga"]["buildings"]["alleys"] = [
            {"x": 100, "w": 50},
        ]
        path = tmp_path / "ports.json"
        path.write_text(json.dumps(ports_data), encoding="utf-8")
        with pytest.raises(ValueError, match=r"alleys\[0\].w=50"):
            pc.init(str(path))


# --- Bake-pipeline-integrasjon ---

class TestGameplayLayerWithFillBuildings:
    def test_tortuga_gameplay_bakes_with_fill_buildings(self):
        from scenes.port_buildings import build_port_gameplay_layer

        pc.init(str(REAL_PORTS_PATH))
        surf = build_port_gameplay_layer(pc.get("tortuga"))
        assert surf is not None

    def test_nassau_gameplay_bakes_with_fill_buildings(self):
        from scenes.port_buildings import build_port_gameplay_layer

        pc.init(str(REAL_PORTS_PATH))
        surf = build_port_gameplay_layer(pc.get("nassau"))
        assert surf is not None

    def test_alleys_remain_transparent_in_gameplay_layer(self):
        """Kritisk: hav/skip må være synlig gjennom smug. Verifiser
        at alley-posisjoner har colorkey-piksel (transparent) i
        gameplay-laget.

        Colorkey er (255, 0, 255) magenta per port_buildings.COLORKEY.
        """
        from scenes.port_buildings import build_port_gameplay_layer, COLORKEY

        pc.init(str(REAL_PORTS_PATH))
        for pid in ("tortuga", "nassau"):
            port = pc.get(pid)
            surf = build_port_gameplay_layer(port)
            for i, a in enumerate(port.buildings.alleys):
                # Sjekk midten av alley, på bygnings-høyde (y=260 —
                # over ground_top_y=340 så det er i bygnings-sonen,
                # ikke i gate-linjen hvor props og gategulv tegnes).
                check_x = a.x + a.w // 2
                check_y = 260
                px = surf.get_at((check_x, check_y))
                assert px[:3] == COLORKEY, (
                    f"{pid}/alley[{i}] at ({check_x}, {check_y}) "
                    f"forventet colorkey {COLORKEY}, fant {px[:3]}"
                )

    def test_port_royal_havana_still_bake_without_fill_buildings(self):
        """Backward-compat: havner uten fill_buildings skal fortsatt
        bake uten feil (C2.5-6b er ikke landet)."""
        from scenes.port_buildings import build_port_gameplay_layer

        pc.init(str(REAL_PORTS_PATH))
        for pid in ("port_royal", "havana"):
            surf = build_port_gameplay_layer(pc.get(pid))
            assert surf is not None


class TestScenesLoadWithFillBuildings:
    def test_tortuga_scene_loads(self):
        from scenes.port_village import PortVillageScene
        from systems import save as save_module

        pc.init(str(REAL_PORTS_PATH))
        font = pygame.font.Font(None, 12)
        state = save_module.new_game_state()
        state.world_state.current_port = "tortuga"
        scene = PortVillageScene(font, state, pc.get("tortuga"))
        assert scene is not None

    def test_nassau_scene_loads(self):
        from scenes.port_village import PortVillageScene
        from systems import save as save_module

        pc.init(str(REAL_PORTS_PATH))
        font = pygame.font.Font(None, 12)
        state = save_module.new_game_state()
        state.world_state.current_port = "nassau"
        scene = PortVillageScene(font, state, pc.get("nassau"))
        assert scene is not None
