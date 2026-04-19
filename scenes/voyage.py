"""VoyageScene — aktiv reise mellom to havner (Fase 2B C7c).

Top-down 640×360. Skip beveger seg lineært fra from_port til to_port
basert på `voyage.compute_progress(voyage, clock, balance)`. Posisjon
er ikke lagret som scene-state — beregnes per frame fra clock-state
slik at save/load-resume er deterministisk.

Per FASE_2B.md §7. Designvalg:

- Skip-posisjon og heading lever inline i scenen, ikke som Entity. Per
  C7-plan-godkjent inline-tilnærming. Heading beregnes én gang i
  __init__ via voyage.compute_heading; rotasjon underveis ville vært
  visuell støy gitt at skipet alltid følger en lineær bane.
- Bakgrunn = world_map_builder.build_world_map_background("noon").
  C10-polish kan legge til fase-cross-fade under reise.
- Dawn-tikk: VoyageScene kaller `economy.tick_all_ports_dawn` per dag
  som passerer (samme logikk som PortVillageScene), slik at markedet
  i alle 4 havner utvikler seg uavhengig av at spilleren er på sjøen.
- Ankomst-deteksjon: ved `clock.day >= voyage.arrival_day`, kall
  `voyage.complete_voyage(state, balance)` og sett
  `next_scene = "port_village"`. complete_voyage setter current_port
  til to_port slik at PortVillageScene-fabrikken konstruerer riktig
  havn ved scene-bytte. PortVillageScene.on_enter(from_scene="voyage")
  utfører ankomst-rituale (write_observed, realize_pending_units,
  toast).
- Ingen player-bevegelse, ingen interaktivitet (autopilot per spec
  §7.5). ESC og E er no-op i C7c — inventory-overlay deferert til C9.
"""

from __future__ import annotations

import logging
import os

import pygame

import constants
from config import port_config as _port_config
from entities.ship_icon import ShipIcon
from scenes.base_scene import BaseScene
from scenes.world_map_builder import build_world_map_background
from state import GameState
from systems import balance as _balance
from systems import voyage as _voyage
from systems.economy import Market, tick_all_ports_dawn
from systems.pitch_lake import PitchLake
from systems.regime_manager import RegimeManager


log = logging.getLogger(__name__)


class VoyageScene(BaseScene):
    """Reise-scene. Krever at `state.world_state.voyage` er non-None
    ved instansiering — fabrikker (main.py og benchmark.py) må sørge
    for at voyage er satt før scenen bygges.
    """

    def __init__(
        self,
        font: pygame.font.Font,
        state: GameState,
    ) -> None:
        super().__init__()
        if state.world_state.voyage is None:
            raise ValueError(
                "VoyageScene krever aktiv voyage i state.world_state.voyage"
            )
        self._font = font
        self._state = state
        voyage = state.world_state.voyage

        # Endepunkter og heading — beregnes én gang per scene-init.
        ports = _port_config.get_all()
        self._from_pos: tuple[int, int] = tuple(
            ports[voyage.from_port].world_map_position
        )
        self._to_pos: tuple[int, int] = tuple(
            ports[voyage.to_port].world_map_position
        )
        self._heading: str = _voyage.compute_heading(
            self._from_pos, self._to_pos
        )
        self._to_port_name: str = ports[voyage.to_port].name
        self._from_port_name: str = ports[voyage.from_port].name

        # Kart-bakgrunn (C7c bruker noon; C10 kan utvide til cross-fade).
        self._background = build_world_map_background(
            ports, phase="noon",
        )

        # Skip-sprite (gjenbrukt fra C5).
        self._ship = ShipIcon()

        # Dawn-tikk-infrastruktur — samme mønster som PortVillageScene.
        # Market er stateless katalog; samme instans opererer på alle
        # havners MarketState via parameter.
        self._market = Market.from_json(
            os.path.join(constants.DATA_DIR, "commodities.json")
        )
        self._regime_manager = RegimeManager()
        self._last_seen_day = state.world_state.clock.day

        # HUD-tekst (statisk for hele reisen — destinasjons-info)
        self._title_surf = font.render(
            f"Reise: {self._from_port_name} \u2192 {self._to_port_name}",
            False, constants.COLOR_MOON_CORE,
        ).convert_alpha()
        self._hint_surf = font.render(
            "Reisen kan ikke avbrytes",
            False, constants.COLOR_FOG,
        ).convert_alpha()

    # --- Input ---

    def handle_event(self, event: pygame.event.Event) -> None:
        # Per spec §7.5: "Once committed, go." Ingen avbryt, ingen
        # styring. ESC og E er no-op i C7c. C9 vurderer inventory-
        # overlay med E.
        return

    # --- Update ---

    def update(self, dt: float) -> None:
        # Klokken oppdateres av main.run() (felles for alle scener);
        # VoyageScene må kun reagere på dag-skift og ankomst.
        clock = self._state.world_state.clock
        curr_day = clock.day

        # Dawn-tikk for hver dag som har passert siden forrige update.
        # Samme algoritme som PortVillageScene; sikrer at markedet i
        # alle 4 havner utvikler seg uavhengig av at spilleren er på
        # sjøen (per spec §7.3).
        if curr_day != self._last_seen_day:
            days_passed = max(0, curr_day - self._last_seen_day)
            for _ in range(days_passed):
                tick_all_ports_dawn(
                    self._state, self._market, self._regime_manager,
                )
                PitchLake.on_new_day(
                    self._state.pitch_lake_state, self._state,
                )
            self._last_seen_day = curr_day

        # Ankomst-deteksjon. complete_voyage setter current_port til
        # to_port og clock-tempo tilbake til in_port; PortVillageScene-
        # fabrikken (main.py) leser current_port og konstruerer riktig
        # havn-scene.
        voyage = self._state.world_state.voyage
        if voyage is not None and curr_day >= voyage.arrival_day:
            _voyage.complete_voyage(self._state, _balance.get())
            self.next_scene = "port_village"

    # --- Rendering ---

    def draw(self, surface: pygame.Surface) -> None:
        # Bakgrunn (pre-rendret én gang)
        surface.blit(self._background, (0, 0))

        # Endepunkter — diskret markering. Ingen markør-pulsering eller
        # focus-state; reisen handler om bevegelse, ikke valg.
        # Tegn små prikker på from_pos og to_pos slik at spilleren ser
        # hva de reiser FRA og TIL.
        pygame.draw.circle(
            surface, constants.COLOR_LANTERN, self._to_pos, 3,
        )
        pygame.draw.circle(
            surface, constants.COLOR_FOG, self._from_pos, 2,
        )

        # Skip-posisjon — beregnes deterministisk fra clock-state per
        # frame. Save/load-resume fungerer trivielt fordi posisjon
        # rekonstrueres uten scene-state.
        voyage = self._state.world_state.voyage
        if voyage is not None:
            bal = _balance.get()
            progress = _voyage.compute_progress(
                voyage, self._state.world_state.clock, bal,
            )
            ship_pos = _voyage.interpolate_position(
                self._from_pos, self._to_pos, progress,
            )
            self._ship.draw(surface, ship_pos, heading=self._heading)

        # HUD-tekst (statisk per scene-init)
        surface.blit(self._title_surf, (8, 4))
        surface.blit(
            self._hint_surf,
            (8, constants.RENDER_HEIGHT - self._hint_surf.get_height() - 4),
        )

    # --- Lifecycle ---

    def on_enter(
        self,
        game_state: GameState,
        from_scene: str | None = None,
    ) -> None:
        """Ingen state-mutasjon — voyage er allerede satt opp av
        `voyage.start_voyage` i WorldMapScene-dialogen, eller av
        save-load (resume). VoyageScene leser kun.
        """
        return

    def on_exit(self, to_scene: str | None = None) -> None:
        """Ingen autosave her — clock + voyage + economy persistere
        konsistent via state-mutasjoner i update(). PortVillageScene
        (target-scenen) tar autosave i sin egen on_enter via ankomst-
        flyten."""
        return
