"""Tester for Fase 2.5 C2.5-1 rekvisita-lag.

Dekker:
- Silhuett-fabrikker lager forventede sprite-dimensjoner
- Ground-texture-dispatch fungerer for gyldige/ugyldige navn
- Bake-funksjonene tegner innenfor target-surfacen uten å krasje
- PortConfig-parsing av props-felt (gyldig + ugyldige variasjoner)
"""

from __future__ import annotations

import os
from pathlib import Path

import pygame
import pytest

from config import port_config as pc


PROJECT_ROOT = Path(__file__).resolve().parent.parent
REAL_PORTS_PATH = PROJECT_ROOT / "data" / "ports.json"


@pytest.fixture(scope="module", autouse=True)
def _pygame_display():
    """Surface.convert() + draw krever et display."""
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    pygame.display.init()
    pygame.display.set_mode((640, 360))
    yield
    pygame.display.quit()


@pytest.fixture(autouse=True)
def _reset_port_config():
    pc._reset_for_tests()
    yield
    pc._reset_for_tests()


# --- Silhouette-fabrikker ---

class TestSilhouetteFactories:
    def test_standing_sprite_dimensions(self):
        from entities.npc_silhouette import build_silhouette

        sil = build_silhouette("standing", x=500, ground_top_y=340)
        assert sil.sprite.get_width() == 8
        assert sil.sprite.get_height() == 18
        # y skal plassere føttene på bakken
        assert sil.y == 340 - 18

    def test_sitting_sprite_is_shorter(self):
        from entities.npc_silhouette import build_silhouette

        standing = build_silhouette("standing", 0, 340)
        sitting = build_silhouette("sitting", 0, 340)
        assert sitting.sprite.get_height() < standing.sprite.get_height()

    def test_group_sprite_is_wider(self):
        from entities.npc_silhouette import build_silhouette

        standing = build_silhouette("standing", 0, 340)
        group = build_silhouette("group", 0, 340)
        assert group.sprite.get_width() > standing.sprite.get_width()

    def test_unknown_kind_raises(self):
        from entities.npc_silhouette import build_silhouette

        with pytest.raises(ValueError, match="Ukjent silhouette-kind"):
            build_silhouette("dancing", 0, 340)

    def test_valid_kinds_exported(self):
        from entities.npc_silhouette import VALID_KINDS

        # C2.5-1: 3 generiske; C2.5-2: 3 britiske; C2.5-3: 4 spanske;
        # C2.5-4: 2 pirat-typer.
        expected = {
            "standing", "sitting", "group",          # C2.5-1
            "officer", "merchant", "colonial_lady",  # C2.5-2
            "priest", "spanish_officer",             # C2.5-3
            "spanish_merchant", "mantilla_woman",    # C2.5-3
            "barefoot_sailor", "woman_with_child",   # C2.5-4
        }
        assert VALID_KINDS == frozenset(expected)

    def test_havana_specific_sprites_exist(self):
        """Prest, spansk offiser, handelsmann, kvinne med mantilla."""
        from entities.npc_silhouette import build_silhouette

        for kind in ("priest", "spanish_officer", "spanish_merchant",
                     "mantilla_woman"):
            sil = build_silhouette(kind, x=500, ground_top_y=340)
            assert sil.sprite.get_width() > 0
            assert sil.sprite.get_height() > 0

    def test_priest_is_tallest_havana_sprite(self):
        """Prest med hette skal rage høyere enn de andre Havana-typene."""
        from entities.npc_silhouette import build_silhouette

        priest = build_silhouette("priest", 0, 340)
        officer = build_silhouette("spanish_officer", 0, 340)
        merchant = build_silhouette("spanish_merchant", 0, 340)
        assert priest.sprite.get_height() >= officer.sprite.get_height()
        assert priest.sprite.get_height() >= merchant.sprite.get_height()

    def test_port_royal_specific_sprites_exist(self):
        """Offiser, handelsmann, kolonial dame må kunne bygges."""
        from entities.npc_silhouette import build_silhouette

        for kind in ("officer", "merchant", "colonial_lady"):
            sil = build_silhouette(kind, x=500, ground_top_y=340)
            assert sil.sprite.get_width() > 0
            assert sil.sprite.get_height() > 0

    def test_colonial_lady_is_tallest(self):
        """Parasoll-silhuett skal rage høyere enn andre figurer
        (ikonografisk signatur)."""
        from entities.npc_silhouette import build_silhouette

        lady = build_silhouette("colonial_lady", 0, 340)
        officer = build_silhouette("officer", 0, 340)
        assert lady.sprite.get_height() > officer.sprite.get_height()


# --- Ground-texture-dispatch ---

class TestGroundTextureDispatch:
    def test_wood_dark_bakes_without_error(self):
        from entities.port_props import bake_ground

        surf = pygame.Surface((1600, 360)).convert()
        bake_ground(surf, ground_top_y=340, texture="wood_dark")

    def test_cobblestone_wet_bakes_without_error(self):
        from entities.port_props import bake_ground

        surf = pygame.Surface((1600, 360)).convert()
        bake_ground(surf, ground_top_y=340, texture="cobblestone_wet")

    def test_unknown_texture_raises(self):
        from entities.port_props import bake_ground

        surf = pygame.Surface((1600, 360)).convert()
        with pytest.raises(ValueError, match="Ukjent ground_texture"):
            bake_ground(surf, ground_top_y=340, texture="lava")

    def test_valid_ground_textures_exported(self):
        from entities.port_props import VALID_GROUND_TEXTURES

        # C2.5-1 leverer 2 teksturer. Senere commits utvider dette.
        assert "wood_dark" in VALID_GROUND_TEXTURES
        assert "cobblestone_wet" in VALID_GROUND_TEXTURES


# --- Bake-funksjoner renderer uten krasj ---

class TestPropBaking:
    def test_lantern_post_bakes_within_surface(self):
        from entities.port_props import bake_lantern_post

        surf = pygame.Surface((1600, 360)).convert()
        bake_lantern_post(surf, x=700, ground_top_y=340)
        # Stolpen skal plassere noe ikke-svart (ikke default-fyll) rundt (700, 340)
        # — enkel sanity: toppen av lanternen ved y=300 bør ha lysere pixel
        top_color = surf.get_at((700, 305))
        # LANTERN_BRIGHT er (255, 213, 128); vi sjekker bare at noe ble tegnet
        assert top_color != (0, 0, 0, 255)

    def test_market_stall_bakes_within_surface(self):
        from entities.port_props import bake_market_stall

        surf = pygame.Surface((1600, 360)).convert()
        bake_market_stall(surf, x=500, ground_top_y=340, w=80)

    def test_barrel_stack_bakes_within_surface(self):
        from entities.port_props import bake_barrel_stack

        surf = pygame.Surface((1600, 360)).convert()
        bake_barrel_stack(surf, x=300, ground_top_y=340, count=3)

    def test_barrel_count_clamped_to_4(self):
        """bake_barrel_stack klamper count til max 4 for å unngå
        off-surface-rendering ved uforsiktig data."""
        from entities.port_props import bake_barrel_stack

        surf = pygame.Surface((1600, 360)).convert()
        # count=10 skal ikke krasje; klampet internt
        bake_barrel_stack(surf, x=300, ground_top_y=340, count=10)


# --- PortConfig-parsing av props-felt ---

class TestPortPropsParser:
    def test_real_tortuga_has_props(self):
        pc.init(str(REAL_PORTS_PATH))
        tortuga = pc.get("tortuga")
        assert tortuga.buildings is not None
        assert tortuga.buildings.props is not None
        props = tortuga.buildings.props
        assert props.ground_texture == "cobblestone_wet"
        assert len(props.lanterns) == 3
        assert len(props.market_stalls) == 3
        assert len(props.barrel_stacks) == 2
        assert len(props.silhouettes) == 3

    def test_real_port_royal_has_props(self):
        """C2.5-2 leverer Port Royal-props: cobblestone_dry + britiske
        signatur-bygninger + institusjonelle rekvisita."""
        pc.init(str(REAL_PORTS_PATH))
        port_royal = pc.get("port_royal")
        assert port_royal.buildings is not None
        assert port_royal.buildings.props is not None
        props = port_royal.buildings.props
        assert props.ground_texture == "cobblestone_dry"
        # Færre lanterner enn Tortuga (ordnet, ikke kaotisk)
        assert len(props.lanterns) == 2
        # Ingen markedsboder (Tortugas smugler-signatur, ikke Port Royal)
        assert len(props.market_stalls) == 0
        # Jerngjerder er Port Royal-signatur
        assert len(props.iron_fences) > 0

    def test_real_havana_has_props(self):
        """C2.5-3: Havana har stone_slab + katedral + fontene + 4 silhuetter."""
        pc.init(str(REAL_PORTS_PATH))
        havana = pc.get("havana")
        assert havana.buildings is not None
        assert havana.buildings.props is not None
        props = havana.buildings.props
        assert props.ground_texture == "stone_slab"
        assert len(props.silhouettes) == 4  # Mest befolket
        assert len(props.fountains) == 1

    def test_real_nassau_has_props(self):
        """C2.5-4: Nassau har sand + bål + bambus-lanterner."""
        pc.init(str(REAL_PORTS_PATH))
        nassau = pc.get("nassau")
        assert nassau.buildings is not None
        assert nassau.buildings.props is not None
        props = nassau.buildings.props
        assert props.ground_texture == "sand"
        assert len(props.silhouettes) == 2  # Minst befolket
        assert len(props.campfires) >= 1
        assert len(props.bamboo_lanterns) >= 1
        assert len(props.chest_stacks) >= 1

    def test_real_port_royal_has_signature_buildings(self):
        """Port Royal har klokketårn + rum-magasin som signatur-bygninger."""
        pc.init(str(REAL_PORTS_PATH))
        port_royal = pc.get("port_royal")
        kinds = [sb.kind for sb in port_royal.buildings.signature_buildings]
        assert "church_tower" in kinds
        assert "rum_warehouse" in kinds

    def test_real_tortuga_no_signature_buildings(self):
        """Tortuga beholder klassisk tavern+børs uten ekstra bygninger."""
        pc.init(str(REAL_PORTS_PATH))
        tortuga = pc.get("tortuga")
        assert tortuga.buildings.signature_buildings == ()

    def test_silhouette_kinds_validated(self, tmp_path):
        """Ugyldig kind skal gi ValueError ved load."""
        ports_data = _load_real_ports()
        ports_data["ports"]["tortuga"]["buildings"]["props"]["silhouettes"] = [
            {"kind": "dancing", "x": 500},
        ]
        path = tmp_path / "ports.json"
        import json
        path.write_text(json.dumps(ports_data), encoding="utf-8")
        with pytest.raises(ValueError, match="kind='dancing'"):
            pc.init(str(path))

    def test_ground_texture_validated(self, tmp_path):
        """Ugyldig ground_texture skal gi ValueError ved load."""
        ports_data = _load_real_ports()
        ports_data["ports"]["tortuga"]["buildings"]["props"][
            "ground_texture"
        ] = "lava"
        path = tmp_path / "ports.json"
        import json
        path.write_text(json.dumps(ports_data), encoding="utf-8")
        with pytest.raises(ValueError, match="ground_texture='lava'"):
            pc.init(str(path))

    def test_barrel_count_bounds_validated(self, tmp_path):
        """count utenfor [1, 4] skal gi ValueError ved load."""
        ports_data = _load_real_ports()
        ports_data["ports"]["tortuga"]["buildings"]["props"]["barrel_stacks"] = [
            {"x": 300, "count": 10},
        ]
        path = tmp_path / "ports.json"
        import json
        path.write_text(json.dumps(ports_data), encoding="utf-8")
        with pytest.raises(ValueError, match="count må være 1-4"):
            pc.init(str(path))

    def test_missing_props_is_allowed(self, tmp_path):
        """Havn uten props-felt skal fortsatt laste (backward compat)."""
        ports_data = _load_real_ports()
        del ports_data["ports"]["tortuga"]["buildings"]["props"]
        path = tmp_path / "ports.json"
        import json
        path.write_text(json.dumps(ports_data), encoding="utf-8")
        # Skal ikke kaste
        pc.init(str(path))
        assert pc.get("tortuga").buildings.props is None


# --- Gameplay-layer-integrasjon ---

class TestGameplayLayerWithProps:
    def test_tortuga_gameplay_layer_bakes_with_props(self):
        from scenes.port_buildings import build_port_gameplay_layer

        pc.init(str(REAL_PORTS_PATH))
        tortuga = pc.get("tortuga")
        surf = build_port_gameplay_layer(tortuga)
        assert surf.get_width() == tortuga.world_width
        assert surf.get_height() == 360

    def test_stub_ports_still_bake_without_props(self):
        """C2.5-1 må ikke knekke ikke-Tortuga-havner som mangler props."""
        from scenes.port_buildings import build_port_gameplay_layer

        pc.init(str(REAL_PORTS_PATH))
        for pid in ("port_royal", "havana", "nassau"):
            port = pc.get(pid)
            surf = build_port_gameplay_layer(port)
            assert surf is not None


# --- Helpers ---

def _load_real_ports() -> dict:
    import json
    return json.loads(REAL_PORTS_PATH.read_text(encoding="utf-8"))
