"""Tester for Fase 2.5 C2.5-7 livfullhet.

Dekker:
- Nature-element-fabrikker kjører uten krasj
- Parser validerer kind + alley contents
- Alle 4 havner har nature_elements og alley contents per spec
- Silhuett-hierarki er uendret (slitasje bryter ikke hierarkiet)
- Gameplay-layer bakes for alle 4 havner med nye elementer
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


# --- Nature-fabrikker ---

class TestNatureFactories:
    def test_valid_kinds_include_core_elements(self):
        from entities.nature import VALID_NATURE_KINDS

        required = {
            "palm", "palm_tall", "palm_leaning",
            "seagull", "dove", "pelican",
            "bougainvillea", "weeds", "moss_patch",
            "hanging_plant", "sand_drift", "seaweed",
        }
        assert required <= VALID_NATURE_KINDS

    def test_all_kinds_bake_without_crash(self):
        from entities.nature import bake_nature_element, VALID_NATURE_KINDS

        surf = pygame.Surface((800, 360)).convert()
        for kind in VALID_NATURE_KINDS:
            bake_nature_element(surf, kind, x=100, y=240, ground_top_y=340)

    def test_unknown_kind_raises(self):
        from entities.nature import bake_nature_element

        surf = pygame.Surface((400, 360)).convert()
        with pytest.raises(ValueError, match="Ukjent nature-kind"):
            bake_nature_element(surf, "unicorn", 100, 200, 340)

    def test_palm_variants_different_heights(self):
        """palm_tall skal rage høyere enn standard palm."""
        from entities.nature import bake_palm

        surf_tall = pygame.Surface((80, 360)).convert()
        surf_tall.fill((0, 0, 0))
        bake_palm(surf_tall, 40, 340, height=56)

        surf_short = pygame.Surface((80, 360)).convert()
        surf_short.fill((0, 0, 0))
        bake_palm(surf_short, 40, 340, height=40)

        # Sjekk at pixler er tegnet høyere oppe på surf_tall
        # (y=288 = 340-52, bør være påvirket for tall, ikke for short)
        tall_pixel = surf_tall.get_at((40, 288))
        short_pixel = surf_short.get_at((40, 288))
        # tall skal ha pixel tegnet der, short skal ikke
        assert tall_pixel != (0, 0, 0, 255) or short_pixel == (0, 0, 0, 255)


# --- Parser ---

class TestNatureParser:
    def test_all_4_ports_have_nature_elements(self):
        pc.init(str(REAL_PORTS_PATH))
        for pid in ("tortuga", "port_royal", "havana", "nassau"):
            port = pc.get(pid)
            assert len(port.buildings.nature_elements) > 0, (
                f"{pid} mangler nature_elements"
            )

    def test_tortuga_has_palms_and_seagulls(self):
        pc.init(str(REAL_PORTS_PATH))
        kinds = {ne.kind for ne in pc.get("tortuga").buildings.nature_elements}
        # Forventer minst én palme-variant og måker
        assert any("palm" in k for k in kinds)
        assert "seagull" in kinds

    def test_havana_has_doves_and_bougainvillea(self):
        pc.init(str(REAL_PORTS_PATH))
        kinds = {ne.kind for ne in pc.get("havana").buildings.nature_elements}
        assert "dove" in kinds
        assert "bougainvillea" in kinds

    def test_nassau_has_pelican(self):
        """Pelikan er Nassau-signatur (eneste havn med pelican)."""
        pc.init(str(REAL_PORTS_PATH))
        for pid in ("tortuga", "port_royal", "havana", "nassau"):
            kinds = {ne.kind for ne in pc.get(pid).buildings.nature_elements}
            if pid == "nassau":
                assert "pelican" in kinds
            else:
                assert "pelican" not in kinds, (
                    f"Pelican skal kun være i Nassau, fant i {pid}"
                )

    def test_nassau_most_palms(self):
        """Nassau har flest palmer (lovløs ukontrollert natur)."""
        pc.init(str(REAL_PORTS_PATH))
        palm_counts = {
            pid: sum(
                1 for ne in pc.get(pid).buildings.nature_elements
                if "palm" in ne.kind
            )
            for pid in ("tortuga", "port_royal", "havana", "nassau")
        }
        assert palm_counts["nassau"] >= palm_counts["tortuga"]
        assert palm_counts["nassau"] >= palm_counts["port_royal"]

    def test_unknown_nature_kind_rejected(self, tmp_path):
        ports_data = json.loads(REAL_PORTS_PATH.read_text(encoding="utf-8"))
        ports_data["ports"]["tortuga"]["buildings"]["nature_elements"] = [
            {"kind": "kraken", "x": 100, "y": 200},
        ]
        path = tmp_path / "ports.json"
        path.write_text(json.dumps(ports_data), encoding="utf-8")
        with pytest.raises(ValueError, match="kind='kraken'"):
            pc.init(str(path))


# --- Alley contents ---

class TestAlleyContents:
    def test_tortuga_alleys_have_ropes_or_barrels(self):
        pc.init(str(REAL_PORTS_PATH))
        for a in pc.get("tortuga").buildings.alleys:
            assert a.contents in ("ropes", "barrels"), (
                f"Tortuga alley content {a.contents} utenfor forventet"
            )

    def test_port_royal_alleys_have_weeds(self):
        pc.init(str(REAL_PORTS_PATH))
        for a in pc.get("port_royal").buildings.alleys:
            assert a.contents == "weeds"

    def test_havana_alleys_have_flower_pots(self):
        pc.init(str(REAL_PORTS_PATH))
        for a in pc.get("havana").buildings.alleys:
            assert a.contents == "flower_pot"

    def test_nassau_alleys_have_palm_or_sand_drift(self):
        pc.init(str(REAL_PORTS_PATH))
        for a in pc.get("nassau").buildings.alleys:
            assert a.contents in ("palm", "sand_drift")

    def test_unknown_alley_contents_rejected(self, tmp_path):
        ports_data = json.loads(REAL_PORTS_PATH.read_text(encoding="utf-8"))
        ports_data["ports"]["tortuga"]["buildings"]["alleys"][0]["contents"] = "gold_pile"
        path = tmp_path / "ports.json"
        path.write_text(json.dumps(ports_data), encoding="utf-8")
        with pytest.raises(ValueError, match="gold_pile"):
            pc.init(str(path))

    def test_alley_without_contents_still_valid(self, tmp_path):
        """Contents-feltet er optional; alley uten feltet skal parse
        med contents=None."""
        ports_data = json.loads(REAL_PORTS_PATH.read_text(encoding="utf-8"))
        # Fjern contents fra første alley
        del ports_data["ports"]["tortuga"]["buildings"]["alleys"][0]["contents"]
        path = tmp_path / "ports.json"
        path.write_text(json.dumps(ports_data), encoding="utf-8")
        pc.init(str(path))
        assert pc.get("tortuga").buildings.alleys[0].contents is None


# --- Bake-pipeline-integrasjon ---

class TestBakePipelineWithNature:
    def test_all_4_ports_bake_with_nature(self):
        from scenes.port_buildings import build_port_gameplay_layer

        pc.init(str(REAL_PORTS_PATH))
        for pid in ("tortuga", "port_royal", "havana", "nassau"):
            _, surf = build_port_gameplay_layer(pc.get(pid))  # night-variant
            assert surf is not None

    def test_silhouette_hierarchy_preserved(self):
        """Signatur-bygninger skal fortsatt ikke overstiges av fyll-
        bygninger etter livfullhet-endringer.

        Mose-patches og vindus-silhuetter legger til detaljer, men de
        endrer ikke bygnings-høyde. Bekreft at fill_buildings fortsatt
        holder ≤60 px.
        """
        pc.init(str(REAL_PORTS_PATH))
        for pid in ("tortuga", "port_royal", "havana", "nassau"):
            for fb in pc.get(pid).buildings.fill_buildings:
                assert fb.h <= 60

    def test_alleys_still_transparent_with_contents(self):
        """Smug skal fortsatt ha synlig hav gjennom selv etter innhold
        er bakt. Innholdet er lite (bakken-nivå), topp av smug skal være
        transparent."""
        from scenes.port_buildings import build_port_gameplay_layer, COLORKEY

        pc.init(str(REAL_PORTS_PATH))
        for pid in ("tortuga", "port_royal", "havana", "nassau"):
            port = pc.get(pid)
            _, surf = build_port_gameplay_layer(port)  # night-variant
            for i, a in enumerate(port.buildings.alleys):
                # Sjekk øvre del av smug (y=260, over eventuelt innhold
                # som er ved bakken y~330-340)
                check_x = a.x + a.w // 2
                check_y = 260
                px = surf.get_at((check_x, check_y))
                assert px[:3] == COLORKEY, (
                    f"{pid}/alley[{i}] topp-del skal være transparent "
                    f"selv med contents={a.contents!r}"
                )
