"""Integrasjonstester for VoyageScene + reise-dialog + ankomst-flyt
(Fase 2B C7c).

Dekker:
- VoyageScene init med aktiv voyage
- VoyageScene.update tikker dawn for alle 4 markeder per dag som passerer
- VoyageScene.update detekterer ankomst → next_scene = "port_village" og
  current_port = to_port via complete_voyage
- VoyageScene.draw kjører uten å kaste
- WorldMap E på annen havn → dialog åpen, ingen scene-bytte
- Dialog ESC → dialog lukket, ingen voyage
- Dialog E → voyage.start_voyage kalt, next_scene = "voyage"
- PortVillageScene.on_enter from_scene="voyage": observed populert,
  voyage cleared, clock til in_port, ankomst-toast pushet
- PortVillageScene.on_enter from_scene="voyage" + home_port match:
  pending realisert
"""

from __future__ import annotations

import os

import pygame
import pytest

from config import port_config
from state import GameState
from state.voyage_state import VoyageState
from systems import balance, save as save_module, voyage as voyage_module


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


def _state_with_voyage(
    from_port: str = "tortuga", to_port: str = "port_royal"
) -> GameState:
    """Bygg state med en aktiv voyage startet via voyage.start_voyage —
    sikrer at clock-tempo og observed-snapshot er korrekt initialisert.
    """
    state = save_module.new_game_state()
    voyage_module.start_voyage(state, balance.get(), from_port, to_port)
    return state


# -----------------------------------------------------------------------------
# VoyageScene
# -----------------------------------------------------------------------------


class TestVoyageSceneInit:
    def test_init_with_active_voyage_succeeds(self):
        from scenes.voyage import VoyageScene
        state = _state_with_voyage()
        scene = VoyageScene(_font(), state)
        assert scene is not None

    def test_init_without_voyage_raises(self):
        from scenes.voyage import VoyageScene
        state = save_module.new_game_state()
        # Ingen voyage satt — VoyageScene skal nekte å bygge
        with pytest.raises(ValueError, match="aktiv voyage"):
            VoyageScene(_font(), state)


class TestVoyageSceneUpdate:
    def test_update_ticks_dawn_for_all_ports_per_day_passed(self):
        """Når clock.day øker, skal tick_all_ports_dawn kalles én gang
        per dag som passerer — verifiserbart via tick_id-bumps på alle
        4 markeder.
        """
        from scenes.voyage import VoyageScene
        state = _state_with_voyage()
        scene = VoyageScene(_font(), state)

        before = {
            pid: ms.tick_id
            for pid, ms in state.economy_state.markets.items()
        }
        # Simuler at klokken har avansert 2 dager mens scenen var på
        state.world_state.clock.day += 2
        scene.update(0.0)

        for pid, ms in state.economy_state.markets.items():
            assert ms.tick_id == before[pid] + 2, (
                f"{pid}: forventet +2 dawn-tick, fikk {ms.tick_id - before[pid]}"
            )

    def test_arrival_triggers_scene_switch_and_complete_voyage(self):
        """Når clock.day >= voyage.arrival_day, skal:
        - voyage.complete_voyage kalles (current_port = to_port,
          voyage = None, clock-tempo til in_port)
        - next_scene = "port_village"
        """
        from scenes.voyage import VoyageScene
        state = _state_with_voyage(from_port="tortuga", to_port="havana")
        scene = VoyageScene(_font(), state)
        bal = balance.get()

        # Hopp til ankomst-dagen
        state.world_state.clock.day = state.world_state.voyage.arrival_day
        scene.update(0.0)

        assert scene.next_scene == "port_village"
        assert state.world_state.current_port == "havana"
        assert state.world_state.voyage is None
        assert state.world_state.clock.seconds_per_day == bal.time.seconds_per_day_in_port

    def test_no_arrival_before_arrival_day(self):
        from scenes.voyage import VoyageScene
        state = _state_with_voyage(from_port="tortuga", to_port="havana")
        scene = VoyageScene(_font(), state)
        # Halvveis: clock.day < arrival_day
        state.world_state.clock.day = state.world_state.voyage.arrival_day - 1
        scene.update(0.0)
        assert scene.next_scene is None
        assert state.world_state.voyage is not None


class TestVoyageSceneRendering:
    def test_draw_does_not_crash(self):
        from scenes.voyage import VoyageScene
        state = _state_with_voyage()
        scene = VoyageScene(_font(), state)
        surf = pygame.Surface((640, 360))
        scene.draw(surf)

    def test_draw_after_arrival_does_not_crash(self):
        """Etter ankomst er voyage None — draw skal håndtere det
        defensivt (ingen ship-rendering)."""
        from scenes.voyage import VoyageScene
        state = _state_with_voyage(from_port="tortuga", to_port="havana")
        scene = VoyageScene(_font(), state)
        state.world_state.clock.day = state.world_state.voyage.arrival_day
        scene.update(0.0)  # trigger arrival
        assert state.world_state.voyage is None
        surf = pygame.Surface((640, 360))
        scene.draw(surf)  # skal ikke krasje


# -----------------------------------------------------------------------------
# WorldMapScene-dialog
# -----------------------------------------------------------------------------


class TestWorldMapDialog:
    def _scene_with_focus(self, focused: str = "havana"):
        from scenes.world_map import WorldMapScene
        state = save_module.new_game_state()
        state.world_state.current_port = "tortuga"
        scene = WorldMapScene(_font(), state)
        scene._focused_port_id = focused
        return scene, state

    def _key(self, k: int) -> pygame.event.Event:
        return pygame.event.Event(pygame.KEYDOWN, {"key": k, "mod": 0})

    def test_e_on_other_port_opens_dialog(self):
        scene, _ = self._scene_with_focus("havana")
        assert scene._dialog is None
        scene.handle_event(self._key(pygame.K_e))
        # Dialog åpen, ingen scene-bytte
        assert scene._dialog is not None
        assert scene.next_scene is None

    def test_dialog_esc_cancels_without_voyage(self):
        scene, state = self._scene_with_focus("havana")
        scene.handle_event(self._key(pygame.K_e))  # åpne dialog
        assert scene._dialog is not None
        scene.handle_event(self._key(pygame.K_ESCAPE))  # avbryt
        assert scene._dialog is None
        assert scene.next_scene is None
        assert state.world_state.voyage is None

    def test_dialog_e_starts_voyage_and_switches_scene(self):
        scene, state = self._scene_with_focus("port_royal")
        scene.handle_event(self._key(pygame.K_e))  # åpne dialog
        scene.handle_event(self._key(pygame.K_e))  # bekreft
        assert scene._dialog is None
        assert scene.next_scene == "voyage"
        assert state.world_state.voyage is not None
        assert state.world_state.voyage.from_port == "tortuga"
        assert state.world_state.voyage.to_port == "port_royal"
        # Clock-tempo byttet til at_sea
        bal = balance.get()
        assert state.world_state.clock.seconds_per_day == bal.time.seconds_per_day_at_sea

    def test_dialog_e_does_not_mutate_gold(self):
        """C7c-konvensjon: gull-trekking eies av C9. Bekreftelse av
        reise rører ikke gull."""
        scene, state = self._scene_with_focus("nassau")
        state.player_state.gold = 200
        scene.handle_event(self._key(pygame.K_e))  # åpne dialog
        scene.handle_event(self._key(pygame.K_e))  # bekreft
        assert state.player_state.gold == 200

    def test_navigation_blocked_while_dialog_open(self):
        """Dialog konsumerer all input — piltaster skal ikke flytte
        fokus mens dialogen er åpen."""
        scene, _ = self._scene_with_focus("havana")
        scene.handle_event(self._key(pygame.K_e))  # åpne dialog
        focus_before = scene._focused_port_id
        scene.handle_event(self._key(pygame.K_LEFT))  # skal ignoreres
        assert scene._focused_port_id == focus_before


# -----------------------------------------------------------------------------
# PortVillageScene ankomst-flyt
# -----------------------------------------------------------------------------


class TestVoyageArrivalFlow:
    def _arrived_state(
        self,
        to_port: str = "port_royal",
        from_port: str = "tortuga",
    ) -> GameState:
        """Simuler full voyage-syklus opp til ankomst, men før on_enter
        på port_village. State er i "akkurat ankommet"-stand:
        voyage er cleared, current_port = to_port, clock = in_port-tempo.

        from_port må være forskjellig fra to_port (ingen self-rute i
        balance.json). Default Tortuga-utgangspunkt; for ankomst til
        Tortuga selv må caller passere annen from_port.
        """
        state = save_module.new_game_state()
        # Sett current_port til from_port før start_voyage (default
        # new_game er alltid Tortuga)
        state.world_state.current_port = from_port
        bal = balance.get()
        v = voyage_module.start_voyage(state, bal, from_port, to_port)
        assert v is not None, f"Ugyldig rute {from_port}→{to_port}"
        # Hopp til ankomst og kall complete_voyage som VoyageScene ville
        state.world_state.clock.day = state.world_state.voyage.arrival_day
        voyage_module.complete_voyage(state, bal)
        return state

    def test_on_enter_writes_observed_for_arrival_port(self):
        from scenes.port_village import PortVillageScene
        state = self._arrived_state(to_port="port_royal")
        # Slett observed for port_royal (skulle uansett ikke finnes
        # på fersk new_game-state, men vær eksplisitt)
        state.economy_state.observed.pop("port_royal", None)

        port = port_config.get("port_royal")
        scene = PortVillageScene(_font(), state, port)
        scene.on_enter(state, from_scene="voyage")

        observed = state.economy_state.observed.get("port_royal")
        assert observed is not None
        assert set(observed.keys()) == {"sugar", "rum", "tobacco", "pitch"}
        # day_seen = ankomst-dagen
        for cid, obs in observed.items():
            assert obs.day_seen == state.world_state.clock.day

    def test_on_enter_pushes_arrival_toast(self):
        """Verifiser at ankomst-toast pushes (én toast, fra 0 til 1).
        Toast-API-et eksponerer ikke text-feltet utad, så vi sjekker
        teller-deltaet — implementasjonen i _handle_voyage_arrival
        pusher én Toast med 'Ankommet X'.
        """
        from scenes.port_village import PortVillageScene
        state = self._arrived_state(to_port="havana")
        port = port_config.get("havana")
        scene = PortVillageScene(_font(), state, port)
        # Ingen toasts før on_enter
        assert len(scene._toasts._toasts) == 0
        scene.on_enter(state, from_scene="voyage")
        # Minst én toast — "Ankommet Havana"
        assert len(scene._toasts._toasts) >= 1

    def test_on_enter_realizes_pending_when_arriving_at_home_port(self):
        """Tortuga er home_port. Hvis pending_units > 0 og spilleren
        ankommer Tortuga, skal pending realiseres til inventar.

        Bruker Nassau→Tortuga som rute (ingen self-rute i balance.json).
        """
        from entities.commodity import InventoryItem
        from scenes.port_village import PortVillageScene
        state = self._arrived_state(to_port="tortuga", from_port="nassau")
        # Sett pending som om vi har akkumulert under reise
        state.pitch_lake_state.pending_units = 5
        # Tom inventar for klar verifisering
        state.player_state.inventory["pitch"] = InventoryItem()

        port = port_config.get("tortuga")
        scene = PortVillageScene(_font(), state, port)
        scene.on_enter(state, from_scene="voyage")

        assert state.player_state.inventory["pitch"].quantity == 5
        assert state.pitch_lake_state.pending_units == 0
        # Hjemmeankomst med pending → 2 toasts (hentet bek + Ankommet)
        assert len(scene._toasts._toasts) >= 2

    def test_on_enter_no_pending_realization_at_non_home_port(self):
        """Ankomst i Port Royal med pending bek skal IKKE realisere
        pending — bekken venter til retur til Tortuga."""
        from entities.commodity import InventoryItem
        from scenes.port_village import PortVillageScene
        state = self._arrived_state(to_port="port_royal")
        state.pitch_lake_state.pending_units = 3
        state.player_state.inventory["pitch"] = InventoryItem()

        port = port_config.get("port_royal")
        scene = PortVillageScene(_font(), state, port)
        scene.on_enter(state, from_scene="voyage")

        assert state.player_state.inventory["pitch"].quantity == 0
        assert state.pitch_lake_state.pending_units == 3

    def test_on_enter_places_player_at_dock(self):
        """Etter voyage-ankomst skal spilleren stå ved dock-region
        (samme som from_scene='world_map')."""
        from scenes.port_village import PortVillageScene
        state = self._arrived_state(to_port="havana")
        port = port_config.get("havana")
        scene = PortVillageScene(_font(), state, port)
        scene.on_enter(state, from_scene="voyage")
        # Dock-retur-x = 60.0; klampet inn i lovlig intervall
        assert 8.0 <= scene._player.x <= 80.0
