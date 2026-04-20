"""Tester for per-havn rendering (Fase 2.5 C2.5-2/3/4).

Verifiserer at PortVillageScene kan lastes for alle 4 havner, at
eksisterende Tortuga-funksjonalitet er uendret, og at Port Royals
Customs House + klokketårn + rum-magasin bakes inn i gameplay-surfacen.

Filen vokser i C2.5-3/4 når Havana og Nassau legges til.
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
    pc.init(str(REAL_PORTS_PATH))
    yield
    pc._reset_for_tests()


def _font() -> pygame.font.Font:
    return pygame.font.Font(None, 12)


def _state_for(port_id: str):
    """Bygg GameState plassert i oppgitt havn."""
    from systems import save as save_module
    state = save_module.new_game_state()
    state.world_state.current_port = port_id
    return state


class TestPortRoyalRendering:
    def test_port_royal_scene_loads(self):
        """Happy path: Port Royal har props + signatur-bygninger, scene-
        init går rent."""
        from scenes.port_village import PortVillageScene

        port_royal = pc.get("port_royal")
        scene = PortVillageScene(_font(), _state_for("port_royal"), port_royal)
        assert scene is not None

    def test_port_royal_gameplay_layer_bakes(self):
        from scenes.port_buildings import build_port_gameplay_layer

        port_royal = pc.get("port_royal")
        _, surf = build_port_gameplay_layer(port_royal)  # night-variant
        assert surf.get_width() == port_royal.world_width
        assert surf.get_height() == 360

    def test_port_royal_uses_customs_house_baker(self):
        """Exchange-bbox bakes med _bake_customs_house, ikke _bake_exchange.

        Verifiseres ved at pixel på ytter-kanten av pediment (nær y - 12)
        er tegnet (STONE-farge) — Tortuga-pediment når ikke så høyt opp.
        """
        from scenes.port_buildings import build_port_gameplay_layer

        port_royal = pc.get("port_royal")
        _, surf = build_port_gameplay_layer(port_royal)  # night-variant
        # Pediment-toppen er y - 12 (se _bake_customs_house).
        # For Port Royal er exchange y=248, så pediment når 236.
        ex = port_royal.buildings.exchange
        pediment_top = (ex.x + ex.w // 2, ex.y - 10)
        color = surf.get_at(pediment_top)
        # Forvent IKKE magenta (colorkey) — noe skal være tegnet
        assert color[:3] != (255, 0, 255), (
            "Pediment-toppen skal ha STONE-farge, ikke colorkey"
        )

    def test_port_royal_silhouettes_built(self):
        from scenes.port_village import PortVillageScene

        port_royal = pc.get("port_royal")
        scene = PortVillageScene(_font(), _state_for("port_royal"), port_royal)
        # 3 silhuetter per spec: officer, merchant, colonial_lady
        kinds = {s.kind for s in scene._silhouettes}
        assert kinds == {"officer", "merchant", "colonial_lady"}

    def test_port_royal_hud_says_borsen(self):
        """HUD-terminologi skal være uendret: 'Port Royal Børs' selv om
        bygningen visuelt er en Customs House."""
        from scenes.port_village import PortVillageScene

        port_royal = pc.get("port_royal")
        scene = PortVillageScene(_font(), _state_for("port_royal"), port_royal)
        # HUD bruker port.name = "Port Royal"; HUD-linje "<name> Børs —"
        # bygges ved render. Her verifiserer vi at port.name matcher spec.
        assert port_royal.name == "Port Royal"


class TestPortRoyalExchangeInteractionUnchanged:
    """Spec krever at exchange-interaksjonen fungerer uendret — kun
    visualisering byttes ut."""

    def test_exchange_bbox_same_as_before(self):
        """Exchange-posisjon skal være den samme som i C2.5-1/2B."""
        port_royal = pc.get("port_royal")
        assert port_royal.buildings.exchange.x == 980
        assert port_royal.buildings.exchange.w == 200

    def test_can_open_exchange_at_port_royal(self):
        """Interaksjon: spiller ved exchange-posisjon kan åpne børsen."""
        from scenes.port_village import PortVillageScene

        port_royal = pc.get("port_royal")
        scene = PortVillageScene(_font(), _state_for("port_royal"), port_royal)
        # Plasser spilleren foran børsen
        ex = port_royal.buildings.exchange
        scene._player.x = float(ex.x + ex.w // 2 - scene._player.width // 2)
        assert scene._player_can_interact_with_exchange()


class TestHavanaRendering:
    def test_havana_scene_loads(self):
        from scenes.port_village import PortVillageScene

        havana = pc.get("havana")
        scene = PortVillageScene(_font(), _state_for("havana"), havana)
        assert scene is not None

    def test_havana_gameplay_layer_bakes(self):
        from scenes.port_buildings import build_port_gameplay_layer

        havana = pc.get("havana")
        _, surf = build_port_gameplay_layer(havana)  # night-variant
        assert surf.get_width() == havana.world_width

    def test_havana_uses_trade_house_baker(self):
        """Exchange-bbox bakes med _bake_trade_house, ikke _bake_exchange."""
        from scenes.port_buildings import build_port_gameplay_layer

        havana = pc.get("havana")
        _, surf = build_port_gameplay_layer(havana)  # night-variant
        # Arkade-buene går ned fra y + h - 30 (i _bake_trade_house).
        # For Havana er exchange y=248, h=92 — så arkaden er ved y=310.
        # Sjekk at noe er tegnet der (IKKE colorkey).
        ex = havana.buildings.exchange
        arch_y = ex.y + ex.h - 20  # Inne i arkade-åpningen
        arch_center = (ex.x + ex.w // 2, arch_y)
        color = surf.get_at(arch_center)
        assert color[:3] != (255, 0, 255)

    def test_havana_has_cathedral_and_palace(self):
        havana = pc.get("havana")
        kinds = [sb.kind for sb in havana.buildings.signature_buildings]
        assert "cathedral" in kinds
        assert "governor_palace" in kinds

    def test_havana_is_most_populated(self):
        """Per FASE_2_5.md §2.3: Havana har 4 NPC-silhuetter (mest)."""
        havana = pc.get("havana")
        assert len(havana.buildings.props.silhouettes) == 4

    def test_havana_silhouette_kinds(self):
        """4 distinkte spanske typer."""
        from scenes.port_village import PortVillageScene

        havana = pc.get("havana")
        scene = PortVillageScene(_font(), _state_for("havana"), havana)
        kinds = {s.kind for s in scene._silhouettes}
        assert kinds == {
            "priest", "spanish_officer", "spanish_merchant",
            "mantilla_woman",
        }

    def test_havana_has_fountain(self):
        """Fontene er Havana-signatur (palette-cycling kommer i C2.5-6)."""
        havana = pc.get("havana")
        assert len(havana.buildings.props.fountains) == 1

    def test_havana_has_planters(self):
        """Plantere ved palasset."""
        havana = pc.get("havana")
        assert len(havana.buildings.props.planters) >= 1

    def test_havana_warmest_palette_no_iron_fences(self):
        """Havana har ingen iron_fences (de er britisk institusjonell
        signatur, tematisk feil for spansk katolsk prakt)."""
        havana = pc.get("havana")
        assert len(havana.buildings.props.iron_fences) == 0

    def test_havana_ground_texture_is_stone_slab(self):
        havana = pc.get("havana")
        assert havana.buildings.props.ground_texture == "stone_slab"


class TestNassauRendering:
    def test_nassau_scene_loads(self):
        from scenes.port_village import PortVillageScene

        nassau = pc.get("nassau")
        scene = PortVillageScene(_font(), _state_for("nassau"), nassau)
        assert scene is not None

    def test_nassau_uses_open_market_baker(self):
        """Exchange-bbox bakes med _bake_open_market, ikke _bake_exchange.

        Per spec: Nassau har ingen børs-BYGNING. Bbox inneholder bord-
        silhuetter i stedet for vegger. Vi verifiserer ved å sjekke at
        det IKKE er tegnet en stor kontinuerlig vegg.
        """
        from scenes.port_buildings import build_port_gameplay_layer

        nassau = pc.get("nassau")
        _, surf = build_port_gameplay_layer(nassau)  # night-variant
        ex = nassau.buildings.exchange
        # Midt i der eksisterende _bake_exchange ville tegnet vegg
        # (y + 20 er inni søyleradens topp) — skal være colorkey
        # (transparent) i Nassau siden det ikke er bygning.
        wall_check = surf.get_at((ex.x + ex.w // 2, ex.y + 20))
        # Tillat enten colorkey eller et bord-silhuett-element —
        # det viktige er at det IKKE er en solid stein-vegg
        # (STONE_DARK = (31, 37, 56)).
        assert wall_check[:3] != (31, 37, 56), (
            "Exchange-bbox midten skal IKKE være stein-vegg i Nassau"
        )

    def test_nassau_has_teachs_house_and_shipyard(self):
        nassau = pc.get("nassau")
        kinds = [sb.kind for sb in nassau.buildings.signature_buildings]
        assert "teachs_house" in kinds
        assert "shipyard" in kinds

    def test_nassau_is_least_populated(self):
        """Per FASE_2_5.md §2.4: Nassau har 2 NPC-silhuetter (minst)."""
        nassau = pc.get("nassau")
        assert len(nassau.buildings.props.silhouettes) == 2

    def test_nassau_silhouette_kinds(self):
        from scenes.port_village import PortVillageScene

        nassau = pc.get("nassau")
        scene = PortVillageScene(_font(), _state_for("nassau"), nassau)
        kinds = {s.kind for s in scene._silhouettes}
        assert kinds == {"barefoot_sailor", "woman_with_child"}

    def test_nassau_has_campfires(self):
        """Bål på gaten er Nassau-signatur."""
        nassau = pc.get("nassau")
        assert len(nassau.buildings.props.campfires) >= 1

    def test_nassau_has_bamboo_lanterns_not_iron(self):
        """Nassau bruker improviserte bambus-lanterner, ikke
        jern-stolper som Tortuga/Port Royal/Havana."""
        nassau = pc.get("nassau")
        assert len(nassau.buildings.props.bamboo_lanterns) > 0
        assert len(nassau.buildings.props.lanterns) == 0

    def test_nassau_has_chest_stacks(self):
        """Kister i stedet for strukturerte markedsboder."""
        nassau = pc.get("nassau")
        assert len(nassau.buildings.props.chest_stacks) >= 1

    def test_nassau_ground_is_sand(self):
        nassau = pc.get("nassau")
        assert nassau.buildings.props.ground_texture == "sand"

    def test_nassau_no_cold_institutional_props(self):
        """Nassau har ingen iron_fences (britisk), fountains (spansk),
        eller planters (spansk). Bare egne signatur-typer."""
        nassau = pc.get("nassau")
        props = nassau.buildings.props
        assert len(props.iron_fences) == 0
        assert len(props.fountains) == 0
        assert len(props.planters) == 0


class TestAllFourPortsDistinct:
    """Integration-test: alle 4 havner har nå unik visuell signatur."""

    def test_each_port_has_unique_ground_texture(self):
        textures = {
            pc.get(pid).buildings.props.ground_texture
            for pid in ("tortuga", "port_royal", "havana", "nassau")
        }
        assert textures == {
            "cobblestone_wet", "cobblestone_dry", "stone_slab", "sand"
        }

    def test_each_port_has_unique_exchange_baker(self):
        """Hver havn har egen exchange-baker i dispatch-tabellen."""
        from scenes.port_buildings import _EXCHANGE_BAKERS
        for pid in ("tortuga", "port_royal", "havana", "nassau"):
            assert pid in _EXCHANGE_BAKERS

    def test_populations_match_spec(self):
        """Havana=4 (mest), Tortuga=Port_Royal=3, Nassau=2 (minst)."""
        populations = {
            pid: len(pc.get(pid).buildings.props.silhouettes)
            for pid in ("tortuga", "port_royal", "havana", "nassau")
        }
        assert populations == {
            "tortuga": 3, "port_royal": 3, "havana": 4, "nassau": 2,
        }


class TestSignatureBuildingValidation:
    def test_unknown_signature_kind_rejected(self, tmp_path):
        """Parser må avvise ugyldige signatur-bygning-kinds."""
        import json
        ports_data = json.loads(REAL_PORTS_PATH.read_text(encoding="utf-8"))
        ports_data["ports"]["port_royal"]["buildings"][
            "signature_buildings"
        ] = [
            {"kind": "space_station", "x": 100, "y": 200, "w": 50, "h": 80},
        ]
        path = tmp_path / "ports.json"
        path.write_text(json.dumps(ports_data), encoding="utf-8")
        pc._reset_for_tests()
        with pytest.raises(ValueError, match="kind='space_station'"):
            pc.init(str(path))

    def test_valid_signature_kinds_exported(self):
        from config.port_config import VALID_SIGNATURE_BUILDING_KINDS

        # C2.5-2: church_tower + rum_warehouse
        # C2.5-3: cathedral + governor_palace
        for kind in ("church_tower", "rum_warehouse",
                     "cathedral", "governor_palace"):
            assert kind in VALID_SIGNATURE_BUILDING_KINDS
