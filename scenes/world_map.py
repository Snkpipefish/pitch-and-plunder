"""WorldMapScene — verdenskart med 4 havn-markører (Fase 2B C5).

Top-down 640×360. Ingen panning — alt synlig samtidig.

I C5 MVP:
- Statisk pre-rendret bakgrunn (noon-fase; C10 legger til 4-faset cross-
  fade per FASE_2B_VISUELL_REFERANSE.md §6)
- 4 havn-markører: 1 current + 3 other, med en focused-markør som
  følger piltast-fokus
- Stasjonær skip-sprite ved current_port (heading "N" som nøytral
  placeholder; reell retning kommer i C7 med voyage)
- E på focused current-port → tilbake til PortVillageScene
- E på focused annen-port → ingen handling i C5 (reise kommer i C7)
- ESC → tilbake til PortVillageScene

Overgang inn/ut av scenen: instant cut i C5. Fade-infrastruktur landes
i C7 sammen med VoyageScene og brukes tilbake til alle scene-bytter.
"""

from __future__ import annotations

import logging

import pygame

import constants
from config import port_config as _port_config
from entities.port_marker import MARKER_SIZE, PortMarker
from entities.ship_icon import ShipIcon
from scenes.base_scene import BaseScene
from scenes.world_map_builder import build_all_phase_variants
from state import GameState


#: §8.3 — padding mellom markør-ring-bunn og label-topp.
_LABEL_PADDING = 3


log = logging.getLogger(__name__)


class WorldMapScene(BaseScene):
    """Kart-scene. Spilleren navigerer mellom havner med piltaster og
    bekrefter valg med E.

    Referanse-rekkefølge for iterasjon over havner: tatt fra
    `port_config.get_all_port_ids()` (tortuga først, deretter alfabetisk).
    Bruk eksplisitt sortering hvis rekkefølgen påvirker spillbarhet —
    dict-orden kan endre seg ved konfig-endringer.
    """

    def __init__(
        self,
        font: pygame.font.Font,
        state: GameState,
    ) -> None:
        super().__init__()
        self._font = font
        self._state = state

        ports = _port_config.get_all()
        # Rekkefølge fra get_all_port_ids(); bruk eksplisitt sortering
        # hvis rekkefølgen påvirker spillbarhet.
        self._port_ids = _port_config.get_all_port_ids()
        self._port_positions: dict[str, tuple[int, int]] = {
            pid: tuple(ports[pid].world_map_position)
            for pid in self._port_ids
        }

        # Bakgrunn: pre-render ALLE 4 fase-varianter ved scene-init
        # (§8-patch). C5.1 bruker "noon" ved runtime; C10 aktiverer
        # cross-fade uten å måtte rive opp scene-init.
        self._phase_variants = build_all_phase_variants(ports, rng_seed=0xC5C5)
        self._active_phase = "noon"
        self._background = self._phase_variants[self._active_phase]

        # §8.3 — pre-render havn-labels. Tekst er statisk per havn i
        # C5.1; C8 introduserer "never_visited"-fargeskifte. Én surface
        # per havn, cachet på samme måte som HUD-tekster.
        self._port_labels: dict[str, pygame.Surface] = {
            pid: font.render(
                ports[pid].name, False, constants.COLOR_MOON_HALO,
            ).convert_alpha()
            for pid in self._port_ids
        }

        # Markør- og skip-sprites (pre-rendret inne i egne klasser)
        self._marker = PortMarker()
        self._ship = ShipIcon()
        # Verifiser at flip-sprites er korrekte. Logging hvis ikke — men
        # kaster ikke: fall-back ville være å pre-rendre 4 separate
        # sprites, men dette bygges kun hvis verifisering feiler.
        ok, report = self._ship.verify_flip_symmetry()
        if not ok:
            log.warning("ShipIcon flip-symmetri-sjekk FEILET: %s", report)
        else:
            log.debug("ShipIcon flip-symmetri OK: %s", report)

        # Fokus starter på current port. Focus-state er scene-lokal;
        # forsvinner ved scene-bytte.
        self._current_port_id = state.world_state.current_port
        self._focused_port_id = self._current_port_id

        # Tid siden scene-åpning, brukt til markør-pulsering.
        self._elapsed: float = 0.0

        # HUD-tekst: kartets overskrift (statisk)
        self._title_surf = font.render(
            "Karibia", False, constants.COLOR_MOON_CORE,
        ).convert_alpha()
        self._hint_surf = font.render(
            "\u2190\u2191\u2192\u2193 velg havn   E bekreft   Esc tilbake",
            False, constants.COLOR_STONE_LIT,
        ).convert_alpha()

    # --- Input ---

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type != pygame.KEYDOWN:
            return
        key = event.key
        if key in constants.KEY_MENU:
            # ESC → tilbake til nåværende havn
            self.next_scene = "port_village"
            return
        if key in constants.KEY_INTERACT:
            self._confirm_focused()
            return
        if key in constants.KEY_LEFT:
            self._navigate((-1, 0))
        elif key in constants.KEY_RIGHT:
            self._navigate((1, 0))
        elif key in constants.KEY_UP:
            self._navigate((0, -1))
        elif key in constants.KEY_DOWN:
            self._navigate((0, 1))

    def _confirm_focused(self) -> None:
        """E bekrefter valg. I C5: kun current-port er gyldig mål.
        Andre havner reserveres til C7-voyage; ingen handling nå.
        """
        if self._focused_port_id == self._current_port_id:
            self.next_scene = "port_village"
        else:
            # C5 no-op. Dev-mode logger stille for sporbarhet under
            # testing.
            from systems.dev_mode import is_dev_mode
            if is_dev_mode():
                log.info(
                    "E på annen havn '%s' — reise kommer i C7 (no-op i C5)",
                    self._focused_port_id,
                )

    def _navigate(self, direction: tuple[int, int]) -> None:
        """Flytt fokus til nærmeste havn i gitt retning.

        Bruker 2D-nærmeste-nabo i halvplan: kandidat må ha ikke-null
        komponent i retningen (dot product > 0), velg minst euklidisk
        avstand. Hvis ingen kandidat finnes, behold gjeldende fokus.
        """
        fx, fy = self._port_positions[self._focused_port_id]
        dx, dy = direction
        best_pid: str | None = None
        best_dist_sq = float("inf")
        for pid, (px, py) in self._port_positions.items():
            if pid == self._focused_port_id:
                continue
            vx = px - fx
            vy = py - fy
            # Dot product i retningen
            dot = vx * dx + vy * dy
            if dot <= 0:
                continue
            dist_sq = vx * vx + vy * vy
            if dist_sq < best_dist_sq:
                best_dist_sq = dist_sq
                best_pid = pid
        if best_pid is not None:
            self._focused_port_id = best_pid

    # --- Update ---

    def update(self, dt: float) -> None:
        self._elapsed += dt

    # --- Rendering ---

    def draw(self, surface: pygame.Surface) -> None:
        surface.blit(self._background, (0, 0))

        # Tittel topp-venstre
        surface.blit(self._title_surf, (8, 4))

        # Havn-markører. Rekkefølge fra _port_ids (Tortuga først); fokus-
        # markøren tegnes SIST slik at pulserende alpha legges oppå de
        # andre hvis overlap skulle oppstå.
        for pid in self._port_ids:
            pos = self._port_positions[pid]
            if pid == self._focused_port_id:
                continue  # tegnes til slutt
            state = "current" if pid == self._current_port_id else "other"
            self._marker.draw(surface, pos, state, self._elapsed)
        # Fokus sist. Hvis focused == current, tegn som "current" først
        # OG "focused" oppå (gir stable varm ring + pulserende kjerne).
        focus_pos = self._port_positions[self._focused_port_id]
        if self._focused_port_id == self._current_port_id:
            self._marker.draw(surface, focus_pos, "current", self._elapsed)
        self._marker.draw(surface, focus_pos, "focused", self._elapsed)

        # §8.3 — Havn-labels: sentrert under hver markør-ring
        for pid in self._port_ids:
            pos = self._port_positions[pid]
            label = self._port_labels[pid]
            # Sentrum av markør er pos; ring-bunn = pos.y + MARKER_SIZE/2.
            # Label-topp = ring-bunn + padding.
            label_x = pos[0] - label.get_width() // 2
            label_y = pos[1] + MARKER_SIZE // 2 + _LABEL_PADDING
            surface.blit(label, (label_x, label_y))

        # Skip-sprite ved current_port. Offset 8 px nord-ost for å unngå
        # overlapp med marker-senter. Heading "N" som nøytral C5-placeholder.
        current_pos = self._port_positions[self._current_port_id]
        ship_pos = (current_pos[0] + 10, current_pos[1] - 8)
        self._ship.draw(surface, ship_pos, heading="N")

        # Hint-linje nederst
        surface.blit(
            self._hint_surf,
            (8, constants.RENDER_HEIGHT - self._hint_surf.get_height() - 4),
        )

    def on_exit(self, to_scene: str | None = None) -> None:
        """Ingen save her — WorldMapScene har ingen mutabel state som
        ikke allerede lever i GameState.
        """
        pass
