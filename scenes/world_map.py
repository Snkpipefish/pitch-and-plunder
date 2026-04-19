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
from systems import balance as _balance
from systems import voyage as _voyage


#: §8.3 — padding mellom markør-ring-bunn og label-topp.
_LABEL_PADDING = 3

#: Reise-dialog modal-boks dimensjoner (sentrert på skjermen).
_DIALOG_WIDTH = 220
_DIALOG_HEIGHT = 80


log = logging.getLogger(__name__)


class _VoyageConfirmDialog:
    """Modal reise-bekreftelse-dialog (Fase 2B C7c).

    Per FASE_2B.md §6.4 viser kort rute-info og venter på bekreft/avbryt.
    Viser KUN "Tid: N dager" — ingen kost-linje (gull-håndtering eies
    av C9 per godkjent C7-justering).
    """

    def __init__(
        self,
        font: pygame.font.Font,
        target_port_name: str,
        days: int,
    ) -> None:
        self._title_surf = font.render(
            f"Seile til {target_port_name}?",
            False, constants.COLOR_MOON_CORE,
        ).convert_alpha()
        self._info_surf = font.render(
            f"Tid: {days} dager",
            False, constants.COLOR_STONE_LIT,
        ).convert_alpha()
        self._hint_surf = font.render(
            "[E] Bekreft   [Esc] Avbryt",
            False, constants.COLOR_LANTERN_BRIGHT,
        ).convert_alpha()
        # Resultat — settes av handle_event, leses av WorldMapScene
        self.confirmed: bool = False
        self.cancelled: bool = False

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type != pygame.KEYDOWN:
            return
        if event.key in constants.KEY_INTERACT:
            self.confirmed = True
        elif event.key in constants.KEY_MENU:
            self.cancelled = True

    def draw(self, surface: pygame.Surface) -> None:
        # Sentrert modal-boks
        x = (constants.RENDER_WIDTH - _DIALOG_WIDTH) // 2
        y = (constants.RENDER_HEIGHT - _DIALOG_HEIGHT) // 2
        # Bakgrunn (mørk) + ramme (lys)
        pygame.draw.rect(
            surface, constants.COLOR_STONE_DARKEST,
            (x, y, _DIALOG_WIDTH, _DIALOG_HEIGHT),
        )
        pygame.draw.rect(
            surface, constants.COLOR_STONE_LIT,
            (x, y, _DIALOG_WIDTH, _DIALOG_HEIGHT), 1,
        )
        # Tekst-stable
        title_x = x + (_DIALOG_WIDTH - self._title_surf.get_width()) // 2
        info_x = x + (_DIALOG_WIDTH - self._info_surf.get_width()) // 2
        hint_x = x + (_DIALOG_WIDTH - self._hint_surf.get_width()) // 2
        surface.blit(self._title_surf, (title_x, y + 12))
        surface.blit(self._info_surf, (info_x, y + 32))
        surface.blit(self._hint_surf, (hint_x, y + 56))


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

        # Reise-dialog (None når ikke aktiv). C7c-modal som blokkerer
        # all kart-input til den lukkes via E (bekreft) eller Esc (avbryt).
        self._dialog: _VoyageConfirmDialog | None = None

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
        # Når dialog er åpen konsumerer den all input, og vi reagerer
        # på resultatet etter delegasjon.
        if self._dialog is not None:
            self._dialog.handle_event(event)
            self._process_dialog_result()
            return

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

    def _process_dialog_result(self) -> None:
        """Håndter dialog-resultat etter at den har konsumert en event.

        Ved bekreft: kall voyage.start_voyage og bytt scene. Ved avbryt:
        bare lukk dialogen.
        """
        if self._dialog is None:
            return
        if self._dialog.cancelled:
            self._dialog = None
            return
        if self._dialog.confirmed:
            target = self._focused_port_id
            bal = _balance.get()
            voyage = _voyage.start_voyage(
                self._state, bal, self._current_port_id, target,
            )
            self._dialog = None
            if voyage is None:
                # start_voyage feilet (ukjent rute eller voyage allerede
                # aktiv) — log og bli stående på kartet
                log.warning(
                    "start_voyage returnerte None for %s→%s",
                    self._current_port_id, target,
                )
                return
            self.next_scene = "voyage"

    def _confirm_focused(self) -> None:
        """E bekrefter valg.

        - Hvis fokusert havn er current_port: lukk kartet, tilbake til
          PortVillageScene (samme som ESC).
        - Hvis fokusert havn er en annen havn: åpne reise-dialog. Gull-
          blokkering ligger i C9; C7c lar dialog åpnes uavhengig av
          gull-balanse.
        """
        if self._focused_port_id == self._current_port_id:
            self.next_scene = "port_village"
            return
        bal = _balance.get()
        route = _voyage.get_route(
            bal, self._current_port_id, self._focused_port_id,
        )
        if route is None:
            log.warning(
                "Ingen rute fra %s til %s — ingen dialog",
                self._current_port_id, self._focused_port_id,
            )
            return
        target_name = _port_config.get(self._focused_port_id).name
        self._dialog = _VoyageConfirmDialog(
            self._font, target_name, route.days,
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

        # Reise-dialog (modal) tegnes sist, over alt annet
        if self._dialog is not None:
            self._dialog.draw(surface)

    def on_exit(self, to_scene: str | None = None) -> None:
        """Ingen save her — WorldMapScene har ingen mutabel state som
        ikke allerede lever i GameState.
        """
        pass
