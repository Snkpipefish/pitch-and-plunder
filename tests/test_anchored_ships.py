"""Tester for Fase 2.5 C2.5-5 ankrede skip-silhuetter."""

from __future__ import annotations

import os
import json
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


# --- Sprite-tegnefunksjoner ---

class TestShipDrawers:
    def test_valid_kinds_exported(self):
        from entities.anchored_ship import VALID_SHIP_KINDS
        assert VALID_SHIP_KINDS == frozenset({
            "smuggler", "frigate", "galleon", "small", "pirate",
        })

    def test_draw_anchored_ship_all_kinds(self):
        """Alle 5 skip-typer kan tegnes uten krasj."""
        from entities.anchored_ship import draw_anchored_ship, VALID_SHIP_KINDS

        surf = pygame.Surface((800, 360), pygame.SRCALPHA)
        for kind in VALID_SHIP_KINDS:
            draw_anchored_ship(surf, x=100, y=240, kind=kind)

    def test_unknown_kind_raises(self):
        from entities.anchored_ship import draw_anchored_ship

        surf = pygame.Surface((800, 360), pygame.SRCALPHA)
        with pytest.raises(ValueError, match="Ukjent anchored_ship.kind"):
            draw_anchored_ship(surf, 100, 240, "battleship")

    def test_pirate_supports_tilted(self):
        """Tilted er kun gyldig for pirate-kind."""
        from entities.anchored_ship import draw_anchored_ship

        surf = pygame.Surface((800, 360), pygame.SRCALPHA)
        # Skal ikke krasje
        draw_anchored_ship(surf, 100, 240, "pirate", tilted=True)
        draw_anchored_ship(surf, 100, 240, "pirate", tilted=False)

    def test_draw_marks_pixels_as_not_transparent(self):
        """Etter tegning skal noen piksler være ikke-transparente."""
        from entities.anchored_ship import draw_anchored_ship

        surf = pygame.Surface((800, 360), pygame.SRCALPHA)
        surf.fill((0, 0, 0, 0))
        draw_anchored_ship(surf, 100, 240, "frigate")
        # Sjekk noen piksler i skip-området (y ~230-240, x ~100-130)
        found_ship = False
        for dy in range(-15, 1):
            for dx in range(0, 30):
                px = surf.get_at((100 + dx, 240 + dy))
                if px[3] > 0:  # Alpha > 0 (ikke transparent)
                    found_ship = True
                    break
            if found_ship:
                break
        assert found_ship, "Skip-silhuett ble ikke tegnet på SRCALPHA-surface"


# --- Parser ---

class TestAnchoredShipParser:
    def test_real_ports_have_anchored_ships(self):
        """Alle 4 havner har anchored_ships i ports.json (C2.5-5)."""
        pc.init(str(REAL_PORTS_PATH))
        for pid in ("tortuga", "port_royal", "havana", "nassau"):
            port = pc.get(pid)
            assert len(port.buildings.anchored_ships) > 0, (
                f"{pid} mangler anchored_ships"
            )

    def test_counts_match_spec(self):
        """Per FASE_2_5.md: Tortuga 3, Port Royal 3, Havana 3, Nassau 5.
        Spec sier Havana har 1-2 galleoner + 1 mindre = 2-3 totalt;
        Nassau 4-5 kaotisk.
        """
        pc.init(str(REAL_PORTS_PATH))
        counts = {
            pid: len(pc.get(pid).buildings.anchored_ships)
            for pid in ("tortuga", "port_royal", "havana", "nassau")
        }
        assert counts["tortuga"] == 3
        assert counts["port_royal"] == 3
        assert 2 <= counts["havana"] <= 3
        assert 4 <= counts["nassau"] <= 5

    def test_tortuga_uses_smugglers(self):
        pc.init(str(REAL_PORTS_PATH))
        kinds = {s.kind for s in pc.get("tortuga").buildings.anchored_ships}
        assert kinds == {"smuggler"}

    def test_port_royal_uses_frigates(self):
        pc.init(str(REAL_PORTS_PATH))
        kinds = {s.kind for s in pc.get("port_royal").buildings.anchored_ships}
        assert kinds == {"frigate"}

    def test_havana_uses_galleons_plus_small(self):
        pc.init(str(REAL_PORTS_PATH))
        kinds = {s.kind for s in pc.get("havana").buildings.anchored_ships}
        # Enten {galleon, small} eller kun {galleon} er gyldig per spec
        assert "galleon" in kinds

    def test_nassau_uses_pirates(self):
        pc.init(str(REAL_PORTS_PATH))
        kinds = {s.kind for s in pc.get("nassau").buildings.anchored_ships}
        assert kinds == {"pirate"}

    def test_nassau_has_tilted_ships(self):
        """Per spec: Nassau har 'noen skråstilte' skip."""
        pc.init(str(REAL_PORTS_PATH))
        ships = pc.get("nassau").buildings.anchored_ships
        tilted_count = sum(1 for s in ships if s.tilted)
        assert tilted_count >= 1

    def test_tilted_only_valid_for_pirate(self, tmp_path):
        """Parser må avvise tilted for ikke-pirat-skip."""
        ports_data = json.loads(REAL_PORTS_PATH.read_text(encoding="utf-8"))
        ports_data["ports"]["tortuga"]["buildings"]["anchored_ships"] = [
            {"kind": "smuggler", "x": 100, "y": 240, "tilted": True},
        ]
        path = tmp_path / "ports.json"
        path.write_text(json.dumps(ports_data), encoding="utf-8")
        with pytest.raises(ValueError, match="tilted"):
            pc.init(str(path))

    def test_unknown_kind_rejected(self, tmp_path):
        ports_data = json.loads(REAL_PORTS_PATH.read_text(encoding="utf-8"))
        ports_data["ports"]["tortuga"]["buildings"]["anchored_ships"] = [
            {"kind": "submarine", "x": 100, "y": 240},
        ]
        path = tmp_path / "ports.json"
        path.write_text(json.dumps(ports_data), encoding="utf-8")
        with pytest.raises(ValueError, match="kind='submarine'"):
            pc.init(str(path))


# --- Foreground-integration ---

class TestForegroundIntegration:
    def test_foreground_variants_bake_with_ships(self):
        """Forgrunns-variantene skal inneholde skip-piksler for havner
        som har anchored_ships."""
        from scenes.parallax_backdrops import build_foreground_variants

        pc.init(str(REAL_PORTS_PATH))
        tortuga = pc.get("tortuga")
        variants = build_foreground_variants(tortuga)
        assert len(variants) == 6  # Samme antall som før — 6 dag-faser

        # Finn skip-piksel (WOOD_DARK skrog ved x=110, y=232-228)
        _frac, surf = variants[0]  # First variant
        # Sjekk en pixel i første smuggler-skip
        ships = tortuga.buildings.anchored_ships
        first = ships[0]
        # Mast-pikselet burde være i ~(first.x + 10, first.y - 8..0)
        found = False
        for dy in range(-10, 0):
            p = surf.get_at((first.x + 10, first.y + dy))
            if p[3] > 0 and p[:3] != (21, 26, 42):  # Ikke STONE_DARKEST (fjell)
                found = True
                break
        assert found, "Fant ikke skip-piksler i første foreground-variant"

    def test_foreground_variants_without_port_still_works(self):
        """Backward-compat: build_foreground_variants() uten port skal
        fortsatt fungere (brukes av eventuelle legacy-kall)."""
        from scenes.parallax_backdrops import build_foreground_variants

        variants = build_foreground_variants()  # Ingen port
        assert len(variants) == 6

    def test_port_village_scene_loads_all_ports_with_ships(self):
        """Alle 4 havner skal laste uten feil når skip er med."""
        from scenes.port_village import PortVillageScene
        from systems import save as save_module

        pc.init(str(REAL_PORTS_PATH))
        font = pygame.font.Font(None, 12)
        for pid in ("tortuga", "port_royal", "havana", "nassau"):
            state = save_module.new_game_state()
            state.world_state.current_port = pid
            scene = PortVillageScene(font, state, pc.get(pid))
            assert scene is not None
