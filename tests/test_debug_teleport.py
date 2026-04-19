"""Tester for systems/debug_teleport (Fase 2B C6).

Verifiserer F1-F4 → port-mapping, dev-mode-vakting (håndteres i
main.py; teleport-funksjonen selv er ikke-dev-mode-bevisst), at
teleport oppdaterer state korrekt, og at ukjente keys er no-op.
"""

from __future__ import annotations

import logging

import pygame
import pytest

from config import port_config
from state import GameState
from systems import debug_teleport


def _state() -> GameState:
    from systems import save as save_module
    return save_module.new_game_state()


class TestTeleportKeyMapping:
    def test_f1_goes_to_tortuga(self):
        state = _state()
        result = debug_teleport.handle_teleport_key(pygame.K_F1, state)
        assert result == "tortuga"
        assert state.world_state.current_port == "tortuga"

    def test_f2_goes_to_port_royal(self):
        state = _state()
        result = debug_teleport.handle_teleport_key(pygame.K_F2, state)
        assert result == "port_royal"
        assert state.world_state.current_port == "port_royal"

    def test_f3_goes_to_havana(self):
        state = _state()
        result = debug_teleport.handle_teleport_key(pygame.K_F3, state)
        assert result == "havana"
        assert state.world_state.current_port == "havana"

    def test_f4_goes_to_nassau(self):
        state = _state()
        result = debug_teleport.handle_teleport_key(pygame.K_F4, state)
        assert result == "nassau"
        assert state.world_state.current_port == "nassau"


class TestTeleportSpawnPosition:
    def test_teleport_sets_position_x_from_buildings(self):
        """Teleport setter position_x fra target-havnens player_start_x
        slik at spilleren spawn-er foran børsen i ny havn.
        """
        state = _state()
        # Før teleport: position fra fresh new_game = 320.0
        assert state.player_state.position_x == 320.0

        debug_teleport.handle_teleport_key(pygame.K_F2, state)
        # Port Royal's player_start_x er 940 per data/ports.json
        expected = port_config.get("port_royal").buildings.player_start_x
        assert state.player_state.position_x == float(expected)
        assert state.player_state.position_x == 940.0

    def test_teleport_to_tortuga_sets_position_to_tortuga_start(self):
        state = _state()
        # Plasser spiller et vilkårlig annet sted først
        state.player_state.position_x = 800.0
        debug_teleport.handle_teleport_key(pygame.K_F1, state)
        # Tortugas player_start_x er 1340
        assert state.player_state.position_x == 1340.0

    def test_teleport_preserves_gold_inventory_clock(self):
        """Teleport skal IKKE røre gull, inventar eller klokke (spec §10 C6:
        'Inventar og gull bevares ved teleport')."""
        from entities.commodity import InventoryItem
        state = _state()
        state.player_state.gold = 777
        state.player_state.inventory["sugar"] = InventoryItem(quantity=5, avg_cost=42.0)
        state.world_state.clock.day = 10
        state.world_state.clock.seconds_into_day = 47.5

        debug_teleport.handle_teleport_key(pygame.K_F3, state)

        assert state.player_state.gold == 777
        assert state.player_state.inventory["sugar"].quantity == 5
        assert state.player_state.inventory["sugar"].avg_cost == 42.0
        assert state.world_state.clock.day == 10
        assert state.world_state.clock.seconds_into_day == 47.5


class TestTeleportUnknownKeys:
    def test_unknown_key_returns_none_and_does_not_change_state(self):
        state = _state()
        original_port = state.world_state.current_port
        original_x = state.player_state.position_x

        result = debug_teleport.handle_teleport_key(pygame.K_SPACE, state)

        assert result is None
        assert state.world_state.current_port == original_port
        assert state.player_state.position_x == original_x

    def test_f5_is_not_teleport(self):
        """F5 tilhører balance-reload i dev-mode; skal ikke trigge teleport."""
        state = _state()
        result = debug_teleport.handle_teleport_key(pygame.K_F5, state)
        assert result is None


class TestTeleportLogging:
    def test_teleport_logs_info_line(self, caplog):
        state = _state()
        with caplog.at_level(logging.INFO, logger="systems.debug_teleport"):
            debug_teleport.handle_teleport_key(pygame.K_F2, state)
        teleport_records = [
            r for r in caplog.records
            if "teleport" in r.getMessage().lower()
        ]
        assert len(teleport_records) == 1, (
            f"Forventet én teleport-logg, fikk {len(teleport_records)}"
        )
        assert "port_royal" in teleport_records[0].getMessage()


class TestTeleportSceneSwitch:
    """Per brukerens presisering: teleport fra world_map skal utføre
    ordinært scene-bytte, ikke bare sette current_port og la world_map
    fortsette underliggende. Dette for å unngå lekkasje av
    scene-lokal tilstand (pulsering-timer, fokus-havn).
    """

    def test_teleport_from_world_map_triggers_scene_switch(self):
        """Etter teleport fra WorldMapScene skal SceneManager bytte
        til PortVillageScene. Vi simulerer main.py-loopen direkte:
        1. handle_teleport_key returnerer target-port
        2. main.py setter manager.current.next_scene = 'port_village'
        3. manager.maybe_switch() bytter scenen

        Resultat: manager.current er PortVillageScene, ikke WorldMapScene.
        """
        import os
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

        pygame.display.init()
        pygame.font.init()
        pygame.display.set_mode((640, 360))
        try:
            from main import SceneManager
            from scenes.port_village import PortVillageScene
            from scenes.world_map import WorldMapScene

            font = pygame.font.Font(None, 12)
            state = _state()
            state.world_state.current_port = "tortuga"

            manager = SceneManager(
                factories={
                    "world_map": lambda: WorldMapScene(font, state),
                    "port_village": lambda: PortVillageScene(
                        font, state,
                        port_config.get(state.world_state.current_port),
                    ),
                },
                initial="world_map",
                game_state=state,
            )
            assert isinstance(manager.current, WorldMapScene)

            # Simuler F2-teleport fra main.py: teleport + next_scene
            target = debug_teleport.handle_teleport_key(pygame.K_F2, state)
            assert target == "port_royal"
            manager.current.next_scene = "port_village"
            manager.maybe_switch()

            assert isinstance(manager.current, PortVillageScene), (
                "Etter teleport fra world_map skal scene være PortVillage"
            )
            # Ny PortVillageScene-instans har Port Royal-port — ikke
            # lekket fra forrige scene
            assert manager.current._port.id == "port_royal"
        finally:
            pygame.font.quit()
            pygame.display.quit()


class TestTeleportToPortWithoutBuildings:
    """Defensiv test: hvis en port mangler buildings (kan ikke skje i
    2B etter C6, men banen finnes), skal teleport avbryte pent.
    """

    def test_teleport_to_phantom_port_returns_none(self, monkeypatch):
        """Monkey-patch port_config.get til å returnere en port uten
        buildings — simulerer fremtidig havn lagt til uten layout.
        """
        from config.port_config import (
            CelestialConfig, PortConfig,
        )

        # Opprett state FØR monkeypatch slik at new_game_state() får
        # bygge normale havner. Deretter patcher vi for teleport-kallet.
        state = _state()
        original_port = state.world_state.current_port

        phantom = PortConfig(
            id="phantom",
            name="Phantom",
            world_map_position=(0, 0),
            scene_class="scenes.port_village:PortVillageScene",
            world_width=1200,
            celestial=CelestialConfig(1000, 1100, 100),
            price_bias={"sugar": 1.0, "rum": 1.0, "tobacco": 1.0, "pitch": 1.0},
            regime_weights={
                "sugar":   {"rising": 0.33, "stable": 0.34, "falling": 0.33},
                "rum":     {"rising": 0.33, "stable": 0.34, "falling": 0.33},
                "tobacco": {"rising": 0.33, "stable": 0.34, "falling": 0.33},
                "pitch":   {"rising": 0.33, "stable": 0.34, "falling": 0.33},
            },
            buildings=None,
        )
        # Patch: F1 returnerer nå phantom-porten
        monkeypatch.setitem(
            debug_teleport._TELEPORT_KEYS,
            pygame.K_F1,
            "phantom",
        )

        def fake_get(pid):
            if pid == "phantom":
                return phantom
            raise KeyError(pid)

        monkeypatch.setattr(port_config, "get", fake_get)

        result = debug_teleport.handle_teleport_key(pygame.K_F1, state)
        assert result is None
        assert state.world_state.current_port == original_port
