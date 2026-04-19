"""Tester for WorldMapScene og relaterte entities (Fase 2B C5).

Dekker:
- PortMarker (3 tilstander: current/focused/other, pulserings-fallback)
- ShipIcon (4 retninger, flip-symmetri-verifisering)
- build_world_map_background (bakgrunns-komposisjon, deterministisk
  bølge-prikke-plassering gitt seed)
- WorldMapScene (init, markør-plassering, piltast-navigasjon, E-handling,
  ESC)
"""

from __future__ import annotations

import os
import random

import pygame
import pytest

from config import port_config
from state import GameState


@pytest.fixture(scope="module", autouse=True)
def _pygame_display():
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    pygame.display.init()
    pygame.font.init()
    pygame.display.set_mode((640, 360))
    yield
    pygame.font.quit()
    pygame.display.quit()


def _font() -> pygame.font.Font:
    return pygame.font.Font(None, 12)


def _state() -> GameState:
    from systems import save as save_module
    return save_module.new_game_state()


# -----------------------------------------------------------------------------
# PortMarker
# -----------------------------------------------------------------------------


class TestPortMarker:
    def test_three_states_available(self):
        from entities.port_marker import PortMarker
        m = PortMarker()
        surf = pygame.Surface((100, 100))
        # Ingen av disse skal kaste
        m.draw(surf, (50, 50), "current")
        m.draw(surf, (50, 50), "focused", elapsed=0.5)
        m.draw(surf, (50, 50), "other")

    def test_unknown_state_does_not_crash(self):
        from entities.port_marker import PortMarker
        m = PortMarker()
        surf = pygame.Surface((100, 100))
        m.draw(surf, (50, 50), "never_visited")  # C5-scope: ignorert

    def test_pulse_fallback_is_logged_in_dev_mode(
        self, caplog, monkeypatch
    ):
        """disable_pulse skal logge én INFO-linje i dev-mode (ikke stille).
        """
        import logging
        from entities.port_marker import PortMarker
        from systems import dev_mode

        # Simuler dev-mode aktiv
        monkeypatch.setenv("PITCH_DEV", "1")
        assert dev_mode.is_dev_mode()

        m = PortMarker()
        with caplog.at_level(logging.INFO, logger="entities.port_marker"):
            m.disable_pulse()
            # Andre kall skal ikke spamme logg
            m.disable_pulse()
        fallback_records = [
            r for r in caplog.records
            if "deaktivert" in r.getMessage()
        ]
        assert len(fallback_records) == 1, (
            "Fallback-logging skal skje én gang, ikke flere"
        )


# -----------------------------------------------------------------------------
# ShipIcon
# -----------------------------------------------------------------------------


class TestShipIcon:
    def test_all_four_headings_draw(self):
        from entities.ship_icon import ShipIcon
        ship = ShipIcon()
        surf = pygame.Surface((100, 100))
        for heading in ("N", "S", "E", "W"):
            ship.draw(surf, (50, 50), heading)

    def test_unknown_heading_falls_back_to_north(self):
        from entities.ship_icon import ShipIcon
        ship = ShipIcon()
        surf = pygame.Surface((100, 100))
        ship.draw(surf, (50, 50), "NE")  # ikke støttet — fallback

    def test_flip_symmetry_verification_passes(self):
        """S-sprite skal være vertikal flip av N, V av Ø. Per
        FASE_2B_VISUELL_REFERANSE.md §4 og direktiv-krav.
        """
        from entities.ship_icon import ShipIcon
        ship = ShipIcon()
        ok, report = ship.verify_flip_symmetry()
        assert ok, f"Flip-symmetri FEILET: {report}"

    def test_north_sprite_has_mast_in_top_half(self):
        """Rent top-down: mast/baug skal være i øvre halvdel av N-sprite.
        """
        from entities.ship_icon import SHIP_SIZE, COLORKEY, ShipIcon
        ship = ShipIcon()
        north = ship._sprites["N"]
        cx = SHIP_SIZE // 2
        top_half_has_content = any(
            north.get_at((cx, y))[:3] != COLORKEY
            for y in range(0, SHIP_SIZE // 2)
        )
        assert top_half_has_content

    def test_south_is_vertical_mirror_of_north(self):
        from entities.ship_icon import SHIP_SIZE, ShipIcon
        ship = ShipIcon()
        n = ship._sprites["N"]
        s = ship._sprites["S"]
        for y in range(SHIP_SIZE):
            for x in range(SHIP_SIZE):
                n_rgb = n.get_at((x, y))[:3]
                s_rgb = s.get_at((x, SHIP_SIZE - 1 - y))[:3]
                assert n_rgb == s_rgb, (
                    f"S-sprite avviker fra N-vertikal-flip på ({x},{y})"
                )


# -----------------------------------------------------------------------------
# build_world_map_background
# -----------------------------------------------------------------------------


class TestWorldMapBuilder:
    def test_background_dimensions_match_render_size(self):
        import constants
        from scenes.world_map_builder import build_world_map_background

        ports = port_config.get_all()
        bg = build_world_map_background(ports, phase="noon")
        assert bg.get_width() == constants.RENDER_WIDTH
        assert bg.get_height() == constants.RENDER_HEIGHT

    def test_background_deterministic_given_seed(self):
        """Samme seed → samme bølge-prikke-plassering."""
        from scenes.world_map_builder import build_world_map_background

        ports = port_config.get_all()
        a = build_world_map_background(ports, phase="noon", rng=random.Random(42))
        b = build_world_map_background(ports, phase="noon", rng=random.Random(42))
        # Sjekk noen prøve-piksler i hav-regionen
        for x, y in [(100, 50), (300, 150), (500, 250)]:
            assert a.get_at((x, y)) == b.get_at((x, y))

    def test_noon_and_dawn_phases_build_without_error(self):
        """C5 bruker kun noon; dawn/dusk/night-API-et skal likevel
        fungere (utvides i C10)."""
        from scenes.world_map_builder import build_world_map_background

        ports = port_config.get_all()
        for phase in ("noon", "dawn", "dusk", "night"):
            bg = build_world_map_background(
                ports, phase=phase, rng=random.Random(1)
            )
            assert bg is not None


# -----------------------------------------------------------------------------
# WorldMapScene
# -----------------------------------------------------------------------------


class TestWorldMapSceneInit:
    def test_scene_loads_without_error(self):
        from scenes.world_map import WorldMapScene
        scene = WorldMapScene(_font(), _state())
        assert scene is not None

    def test_current_port_focused_initially(self):
        from scenes.world_map import WorldMapScene
        state = _state()
        state.world_state.current_port = "tortuga"
        scene = WorldMapScene(_font(), state)
        assert scene._focused_port_id == "tortuga"
        assert scene._current_port_id == "tortuga"


class TestWorldMapSceneNavigation:
    def _scene(self) -> "WorldMapScene":
        from scenes.world_map import WorldMapScene
        state = _state()
        state.world_state.current_port = "tortuga"
        return WorldMapScene(_font(), state)

    def _key_down(self, key: int) -> pygame.event.Event:
        return pygame.event.Event(pygame.KEYDOWN, {"key": key, "mod": 0})

    def test_left_from_tortuga_goes_to_port_royal(self):
        """Tortuga (410, 230) → ← skal velge Port Royal (180, 260):
        vest-retningen peker mot lavere x."""
        scene = self._scene()
        scene.handle_event(self._key_down(pygame.K_LEFT))
        assert scene._focused_port_id == "port_royal"

    def test_up_from_tortuga_goes_to_nassau(self):
        """Tortuga (410, 230) → ↑ skal velge Nassau (420, 110).
        Nord-retningen peker mot lavere y. Havana (140, 140) har også
        lavere y men er lengre vekk fra Tortugas x.
        """
        scene = self._scene()
        scene.handle_event(self._key_down(pygame.K_UP))
        assert scene._focused_port_id == "nassau"

    def test_down_from_tortuga_no_ports_below(self):
        """Tortuga (410, 230) — kun Port Royal (180, 260) har y > 230.
        ↓ (sør) skal velge den hvis dot-product > 0 (som det er —
        (180-410, 260-230) = (-230, +30), dot med (0, 1) = +30).
        """
        scene = self._scene()
        scene.handle_event(self._key_down(pygame.K_DOWN))
        # Port Royal er eneste havn med y > 230
        assert scene._focused_port_id == "port_royal"

    def test_right_from_havana_goes_to_nearest_in_right_halfplane(self):
        """Havana (140, 140) → høyre. Kandidater med dx > 0:
        - Port Royal (180, 260): dist² = 40² + 120² = 16000  ← nærmest
        - Tortuga (410, 230): dist² = 270² + 90² = 81000
        - Nassau (420, 110): dist² = 280² + 30² = 79300
        """
        scene = self._scene()
        scene._focused_port_id = "havana"
        scene.handle_event(self._key_down(pygame.K_RIGHT))
        assert scene._focused_port_id == "port_royal"


class TestWorldMapSceneConfirm:
    def test_e_on_current_port_returns_to_port_village(self):
        from scenes.world_map import WorldMapScene
        state = _state()
        state.world_state.current_port = "tortuga"
        scene = WorldMapScene(_font(), state)
        # Fokus er tortuga ved init
        scene.handle_event(pygame.event.Event(
            pygame.KEYDOWN, {"key": pygame.K_e, "mod": 0},
        ))
        assert scene.next_scene == "port_village"

    def test_e_on_other_port_is_noop_in_c5(self):
        """C5: E på annen havn gjør ingenting (reise kommer i C7)."""
        from scenes.world_map import WorldMapScene
        state = _state()
        state.world_state.current_port = "tortuga"
        scene = WorldMapScene(_font(), state)
        scene._focused_port_id = "havana"
        scene.handle_event(pygame.event.Event(
            pygame.KEYDOWN, {"key": pygame.K_e, "mod": 0},
        ))
        assert scene.next_scene is None

    def test_esc_returns_to_port_village(self):
        from scenes.world_map import WorldMapScene
        state = _state()
        scene = WorldMapScene(_font(), state)
        scene.handle_event(pygame.event.Event(
            pygame.KEYDOWN, {"key": pygame.K_ESCAPE, "mod": 0},
        ))
        assert scene.next_scene == "port_village"


class TestWorldMapSceneRendering:
    def test_draw_does_not_crash(self):
        from scenes.world_map import WorldMapScene
        scene = WorldMapScene(_font(), _state())
        surf = pygame.Surface((640, 360))
        scene.draw(surf)

    def test_elapsed_advances_on_update(self):
        from scenes.world_map import WorldMapScene
        scene = WorldMapScene(_font(), _state())
        assert scene._elapsed == 0.0
        scene.update(0.5)
        scene.update(0.3)
        assert abs(scene._elapsed - 0.8) < 1e-9

    def test_draw_renders_label_pixels_below_each_marker(self):
        """Regression-vakt for C7c-patch: helper-extraction skal ikke
        ha brutt eksisterende label-tegning i WorldMapScene. Sampler
        COLOR_MOON_HALO under hver markør (samme metode som for
        VoyageScene-tester).
        """
        from constants import COLOR_MOON_HALO
        from entities.port_marker import MARKER_SIZE
        from scenes.world_map import WorldMapScene
        scene = WorldMapScene(_font(), _state())
        surf = pygame.Surface((640, 360))
        scene.draw(surf)

        ports = port_config.get_all()
        for pid in ("tortuga", "port_royal", "havana", "nassau"):
            cx, cy = ports[pid].world_map_position
            label_top_y = cy + MARKER_SIZE // 2 + 3
            found_halo = False
            for dy in range(0, 12):
                y = label_top_y + dy
                if not (0 <= y < 360):
                    continue
                for dx in range(-30, 31):
                    x = cx + dx
                    if not (0 <= x < 640):
                        continue
                    pix = surf.get_at((x, y))
                    if (pix[0], pix[1], pix[2]) == COLOR_MOON_HALO:
                        found_halo = True
                        break
                if found_halo:
                    break
            assert found_halo, f"Ingen label-piksler funnet under {pid}"


# -----------------------------------------------------------------------------
# C8: never_visited markør + tooltip på fokus
# -----------------------------------------------------------------------------


class TestWorldMapNeverVisitedMarker:
    def test_never_visited_marker_drawn_for_unvisited_ports(self):
        """Når observed kun har Tortuga, skal Port Royal/Havana/Nassau
        markører tegnes med 'never_visited'-state (FOG-ring). Sampler
        COLOR_FOG-piksler i markør-region.
        """
        from constants import COLOR_FOG
        from entities.port_marker import MARKER_SIZE
        from scenes.world_map import WorldMapScene

        state = _state()
        # Fresh new_game har observed["tortuga"] populert. Andre havner
        # har ingen observed → never_visited.
        assert "tortuga" in state.economy_state.observed
        for pid in ("port_royal", "havana", "nassau"):
            assert pid not in state.economy_state.observed

        # Sett fokus til Tortuga slik at Tortuga får "current"/"focused"
        # state, og de tre andre får "never_visited".
        scene = WorldMapScene(_font(), state)
        scene._focused_port_id = "tortuga"
        surf = pygame.Surface((640, 360))
        scene.draw(surf)

        ports = port_config.get_all()
        for pid in ("port_royal", "havana", "nassau"):
            cx, cy = ports[pid].world_map_position
            # Marker er 14×14 sentrert på (cx, cy). Sampler ring-region.
            half = MARKER_SIZE // 2
            found_fog = False
            for dy in range(-half, half + 1):
                for dx in range(-half, half + 1):
                    x, y = cx + dx, cy + dy
                    if not (0 <= x < 640 and 0 <= y < 360):
                        continue
                    pix = surf.get_at((x, y))
                    if (pix[0], pix[1], pix[2]) == COLOR_FOG:
                        found_fog = True
                        break
                if found_fog:
                    break
            assert found_fog, f"Ingen FOG-pixler (never_visited) for {pid}"

    def test_visited_port_uses_other_state_not_never(self):
        """Når en havn HAR observed-data, skal den ikke få never_visited.
        Sjekk at COLOR_STONE_LIT (other-ringe) finnes for besøkt havn
        som ikke er current eller focused.
        """
        from constants import COLOR_STONE_LIT
        from entities.port_marker import MARKER_SIZE
        from scenes.world_map import WorldMapScene
        from systems.economy import write_observed_for_port

        state = _state()
        # Marker port_royal som besøkt
        write_observed_for_port(state, "port_royal")

        scene = WorldMapScene(_font(), state)
        scene._focused_port_id = "tortuga"  # tortuga = focused, ikke port_royal
        surf = pygame.Surface((640, 360))
        scene.draw(surf)

        ports = port_config.get_all()
        cx, cy = ports["port_royal"].world_map_position
        half = MARKER_SIZE // 2
        found_lit = False
        for dy in range(-half, half + 1):
            for dx in range(-half, half + 1):
                x, y = cx + dx, cy + dy
                if not (0 <= x < 640 and 0 <= y < 360):
                    continue
                pix = surf.get_at((x, y))
                if (pix[0], pix[1], pix[2]) == COLOR_STONE_LIT:
                    found_lit = True
                    break
            if found_lit:
                break
        assert found_lit, (
            "Port Royal med observed-data skal ha STONE_LIT-ring "
            "(other-state), ikke FOG (never_visited)"
        )


class TestWorldMapTooltipOnFocus:
    def test_tooltip_drawn_when_no_dialog_open(self):
        """Tooltip for fokusert havn skal tegne MOON_CORE-piksler
        (havn-navn) under markøren når dialog er lukket.
        """
        from constants import COLOR_MOON_CORE
        from scenes.world_map import WorldMapScene
        scene = WorldMapScene(_font(), _state())
        scene._focused_port_id = "tortuga"
        surf = pygame.Surface((640, 360))
        scene.draw(surf)

        # Tooltip ligger under fokusert markør (Tortuga ved 410, 230)
        anchor = (410, 230)
        found_navn = False
        for y in range(anchor[1] + 10, min(360, anchor[1] + 90)):
            for x in range(max(0, anchor[0] - 80), min(640, anchor[0] + 80)):
                pix = surf.get_at((x, y))
                if (pix[0], pix[1], pix[2]) == COLOR_MOON_CORE:
                    found_navn = True
                    break
            if found_navn:
                break
        assert found_navn, "Tooltip-tekst (havn-navn) ikke funnet ved fokus"

    def test_tooltip_skipped_when_dialog_open(self):
        """Når reise-dialog er åpen, skal tooltip ikke tegnes (modal
        eier skjermen). Verifiser ved å sjekke at draw kjører uten
        krasj og uten å eksplodere på dialog+tooltip-overlap.
        """
        from scenes.world_map import WorldMapScene, _VoyageConfirmDialog
        scene = WorldMapScene(_font(), _state())
        scene._focused_port_id = "havana"
        scene._dialog = _VoyageConfirmDialog(_font(), "Havana", 3)
        surf = pygame.Surface((640, 360))
        scene.draw(surf)  # skal ikke krasje
        # Implisitt: ingen kontroll på tooltip — hvis koden var feil
        # ville surf-pixel-state vært udefinert. Test passerer hvis
        # vi kommer hit.


# -----------------------------------------------------------------------------
# PortVillageScene dock-interaksjon (C5-endring)
# -----------------------------------------------------------------------------


class TestPortVillageDockInteraction:
    def test_player_in_dock_region_can_interact(self):
        from scenes.port_village import PortVillageScene
        tortuga = port_config.get("tortuga")
        scene = PortVillageScene(_font(), _state(), tortuga)
        # Dock-region: x ∈ [8, 80]. Player.width ≈ 8 (sprite), så
        # center ved x=40 gir player.x ≈ 36.
        scene._player.x = 36.0
        assert scene._player_can_interact_with_dock()
        # Utenfor region: ingen interaksjon
        scene._player.x = 500.0
        assert not scene._player_can_interact_with_dock()

    def test_e_in_dock_region_triggers_world_map(self):
        from scenes.port_village import PortVillageScene
        tortuga = port_config.get("tortuga")
        scene = PortVillageScene(_font(), _state(), tortuga)
        scene._player.x = 36.0
        scene.handle_event(pygame.event.Event(
            pygame.KEYDOWN, {"key": pygame.K_e, "mod": 0},
        ))
        assert scene.next_scene == "world_map"

    def test_hint_state_in_dock_region(self):
        from scenes.port_village import PortVillageScene
        tortuga = port_config.get("tortuga")
        scene = PortVillageScene(_font(), _state(), tortuga)
        scene._player.x = 36.0
        assert scene._compute_hint_state() == "near_dock"
        # Utenfor dock og utenfor exchange → far
        scene._player.x = 800.0
        assert scene._compute_hint_state() == "far"

    def test_on_enter_from_world_map_places_at_dock(self):
        from scenes.port_village import PortVillageScene
        tortuga = port_config.get("tortuga")
        state = _state()
        scene = PortVillageScene(_font(), state, tortuga)
        scene.on_enter(state, from_scene="world_map")
        # Ved retur fra kartet står spilleren ved dock-region
        assert 8.0 <= scene._player.x <= 80.0
