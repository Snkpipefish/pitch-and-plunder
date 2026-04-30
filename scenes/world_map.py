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

import os

import constants
from config import port_config as _port_config
from entities.port_marker import MARKER_SIZE, PortMarker
from entities.ship_icon import ShipIcon
from scenes.base_scene import BaseScene
from scenes.world_map_builder import build_all_phase_variants
from state import GameState
from systems import balance as _balance
from systems import voyage as _voyage
from systems.economy import Market
from ui.toast import Toast, ToastQueue
from ui.world_map_tooltip import WorldMapTooltip, build_tooltip_lines


#: §8.3 — padding mellom markør-ring-bunn og label-topp.
_LABEL_PADDING = 3

#: Reise-dialog modal-boks dimensjoner (sentrert på skjermen).
#: Høyde økt fra 80 til 96 i C9 for å gi plass til kost-linjen.
_DIALOG_WIDTH = 220
_DIALOG_HEIGHT = 96


log = logging.getLogger(__name__)


def draw_port_markers_with_labels(
    surface: pygame.Surface,
    port_ids: list[str],
    port_positions: dict[str, tuple[int, int]],
    port_labels: dict[str, pygame.Surface],
    marker: PortMarker,
    current_port_id: str,
    elapsed: float,
    skip_port_id: str | None = None,
    visited_port_ids: set[str] | None = None,
) -> None:
    """Tegn havn-markører + labels for verdenskart-relaterte scener.

    Brukt av WorldMapScene (med skip_port_id=focused, scenen tegner
    fokus-markøren separat etterpå med pulserende sentrum) og
    VoyageScene (uten skip — alle 4 markører tegnes her, ship-sprite
    tegnes etterpå på toppen av call-site).

    Markør-state per havn (prioritert i denne rekkefølgen):
    - `current_port_id`: "current" (varm LANTERN-ring)
    - ikke i `visited_port_ids` (når satt): "never_visited" (FOG-ring)
    - andre: "other" (kald STONE_LIT-ring)

    `visited_port_ids=None` (default for backward-kompatibilitet) gir
    samme oppførsel som C7 — alle non-current = "other". Når satt
    (typisk `set(state.economy_state.observed.keys())`), markeres
    ports IKKE i settet med "never_visited"-tilstand. Per spec §8.3:
    aldri-besøkte havner har ingen observed-oppføring og skal være
    visuelt dempet på kartet.

    Labels tegnes for ALLE port_ids uavhengig av skip_port_id —
    fokus-markøren beholder labelen sin selv om markør-tegningen
    deferes til caller. Per VISUELL_REFERANSE §8.3 er labels alltid
    synlige slik at spilleren kan navne-orientere seg.
    """
    for pid in port_ids:
        if pid == skip_port_id:
            continue
        pos = port_positions[pid]
        if pid == current_port_id:
            state = "current"
        elif visited_port_ids is not None and pid not in visited_port_ids:
            state = "never_visited"
        else:
            state = "other"
        marker.draw(surface, pos, state, elapsed)

    for pid in port_ids:
        pos = port_positions[pid]
        label = port_labels[pid]
        label_x = pos[0] - label.get_width() // 2
        label_y = pos[1] + MARKER_SIZE // 2 + _LABEL_PADDING
        surface.blit(label, (label_x, label_y))


class _VoyageConfirmDialog:
    """Modal reise-bekreftelse-dialog (Fase 2B C7c, utvidet C9).

    Per FASE_2B.md §6.4 viser rute-info og venter på bekreft/avbryt.
    C9 utvidet med kost-linje. Spilleren har allerede passert
    affordability-sjekken (WorldMapScene blokkerer dialog-åpning ved
    insufficient gull) — kost-linjen vises som faktum, ikke advarsel.

    Tone: alle tre informasjons-linjer i STONE_LIT for ro. LANTERN_BRIGHT
    er reservert for muligheter/belønninger (current-port-markør, "du
    er her") — kost er konstant og fortjener ikke varm emfase.
    """

    def __init__(
        self,
        font: pygame.font.Font,
        target_port_name: str,
        days: int,
        gold: int,
    ) -> None:
        self._title_surf = font.render(
            f"Seile til {target_port_name}?",
            False, constants.COLOR_MOON_CORE,
        ).convert_alpha()
        self._time_surf = font.render(
            f"Tid: {days} dager",
            False, constants.COLOR_STONE_LIT,
        ).convert_alpha()
        self._cost_surf = font.render(
            f"Kost: {gold} gull",
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
        # Tekst-stable: tittel / tid / kost / hint
        title_x = x + (_DIALOG_WIDTH - self._title_surf.get_width()) // 2
        time_x = x + (_DIALOG_WIDTH - self._time_surf.get_width()) // 2
        cost_x = x + (_DIALOG_WIDTH - self._cost_surf.get_width()) // 2
        hint_x = x + (_DIALOG_WIDTH - self._hint_surf.get_width()) // 2
        surface.blit(self._title_surf, (title_x, y + 12))
        surface.blit(self._time_surf, (time_x, y + 32))
        surface.blit(self._cost_surf, (cost_x, y + 48))
        surface.blit(self._hint_surf, (hint_x, y + 72))


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

        # Flygende fugler over kartet (v2.7 livfullhet-pass) — sakte drift,
        # samme stil som voyage-scenen siden begge er top-down kart-form.
        from systems import flying_birds as _flying_birds  # lazy
        self._flying_birds = _flying_birds.FlyingBirds(
            world_width=constants.RENDER_WIDTH,
            config=_flying_birds.FlyingBirdsConfig(
                count=4,
                color=constants.COLOR_MOON_HALO,
                altitude_min=20,
                altitude_max=300,
                speed_min=14.0,
                speed_max=24.0,
                sin_amp_min=0.5,
                sin_amp_max=1.5,
                flock_burst_count=2,
                flock_burst_min_sec=25.0,
                flock_burst_max_sec=45.0,
                sleep_threshold=2.0,
            ),
        )
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

        # C8: tooltip for fokusert havn. Market-katalog brukes til
        # display-navn og price_history-trend-beregning.
        self._market = Market.from_json(
            os.path.join(constants.DATA_DIR, "commodities.json")
        )
        self._catalog_order: list[str] = [
            c.id for c in self._market.commodities
        ]
        self._catalog_names: dict[str, str] = {
            c.id: c.name for c in self._market.commodities
        }
        self._tooltip = WorldMapTooltip(font)

        # C9: toast-kø for blokk-meldinger ("Trenger X gull") og
        # avreise-varsler. Baseline like over hint-linja.
        self._toasts = ToastQueue(
            baseline_y=constants.RENDER_HEIGHT - 18,
            center_x=constants.RENDER_WIDTH // 2,
        )

        # HUD-tekst: kartets overskrift (statisk)
        self._title_surf = font.render(
            "Karibia", False, constants.COLOR_MOON_CORE,
        ).convert_alpha()
        self._hint_surf = font.render(
            "\u2190\u2191\u2192\u2193 velg havn   E bekreft   Esc tilbake",
            False, constants.COLOR_STONE_LIT,
        ).convert_alpha()

    @property
    def toasts(self) -> ToastQueue:
        """Eksponer toast-køen for eksterne systemer (F5 hot-reload-
        handler i main.py).
        """
        return self._toasts

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
                # start_voyage feilet — defensivt fallback. WorldMap har
                # pre-sjekket affordability, så dette skal ikke skje
                # i normalflyten. Log og bli stående på kartet.
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
        - Hvis fokusert havn er en annen havn: pre-sjekk gull-
          affordability via voyage.voyage_cost. Hvis insufficient → push
          "Trenger X gull"-toast og IKKE åpne dialog (per spec C9 og
          tone-direktivet om at kost ikke trenger å skrike fra dialog).
          Hvis sufficient → åpne reise-dialog som viser kost-linjen
          som faktum.
        """
        if self._focused_port_id == self._current_port_id:
            self.next_scene = "port_village"
            return
        bal = _balance.get()
        cost = _voyage.voyage_cost(
            bal, self._current_port_id, self._focused_port_id,
        )
        if cost is None:
            log.warning(
                "Ingen rute fra %s til %s — ingen dialog",
                self._current_port_id, self._focused_port_id,
            )
            return
        if self._state.player_state.gold < cost:
            self._toasts.push(Toast(
                font=self._font,
                text=f"Trenger {cost} gull",
                color=constants.COLOR_EMBER,
            ))
            return
        # Affordability OK — åpne dialog med kost-linje
        route = _voyage.get_route(
            bal, self._current_port_id, self._focused_port_id,
        )
        target_name = _port_config.get(self._focused_port_id).name
        self._dialog = _VoyageConfirmDialog(
            self._font, target_name, route.days, route.gold,
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
        self._toasts.update(dt)
        self._flying_birds.update(dt, night_factor=0.0)

    # --- Rendering ---

    def draw(self, surface: pygame.Surface) -> None:
        surface.blit(self._background, (0, 0))

        # Tittel topp-venstre
        surface.blit(self._title_surf, (8, 4))

        # C8: visited_port_ids = havner med observed-oppføringer.
        # Ports IKKE i settet får "never_visited"-markør (FOG-ring).
        visited = set(self._state.economy_state.observed.keys())

        # Havn-markører + labels via felles helper. Vi skipper fokus-
        # markøren her og tegner den separat sist slik at pulserende
        # alpha legges oppå hvis overlap skulle oppstå. Labels tegnes
        # for ALLE havner i helperen (også fokus-havnen).
        draw_port_markers_with_labels(
            surface=surface,
            port_ids=self._port_ids,
            port_positions=self._port_positions,
            port_labels=self._port_labels,
            marker=self._marker,
            current_port_id=self._current_port_id,
            elapsed=self._elapsed,
            skip_port_id=self._focused_port_id,
            visited_port_ids=visited,
        )
        # Fokus sist. Hvis focused == current, tegn som "current" først
        # OG "focused" oppå (gir stable varm ring + pulserende kjerne).
        focus_pos = self._port_positions[self._focused_port_id]
        if self._focused_port_id == self._current_port_id:
            self._marker.draw(surface, focus_pos, "current", self._elapsed)
        self._marker.draw(surface, focus_pos, "focused", self._elapsed)

        # C8: tooltip for fokusert havn (alltid synlig på fokus per Q4).
        # Skip når dialog er åpen — modal har all skjerm-fokus.
        if self._dialog is None:
            self._draw_focus_tooltip(surface)

        # Skip-sprite ved current_port. Offset 8 px nord-ost for å unngå
        # overlapp med marker-senter. Heading "N" som nøytral C5-placeholder.
        current_pos = self._port_positions[self._current_port_id]
        ship_pos = (current_pos[0] + 10, current_pos[1] - 8)
        self._ship.draw(surface, ship_pos, heading="N")

        # Flygende fugler — over markører og skip men under tooltip og
        # hint-linjen (de er rene UI-elementer som skal være øverst).
        self._flying_birds.draw(surface, camera_x=0.0, night_factor=0.0)

        # Hint-linje nederst
        surface.blit(
            self._hint_surf,
            (8, constants.RENDER_HEIGHT - self._hint_surf.get_height() - 4),
        )

        # Toasts (under hint-linje, over kart-bakgrunn)
        self._toasts.draw(surface)

        # Reise-dialog (modal) tegnes sist, over alt annet
        if self._dialog is not None:
            self._dialog.draw(surface)

    def _draw_focus_tooltip(self, surface: pygame.Surface) -> None:
        """C8: tegn tooltip for fokusert havn med observed-data.

        Tooltip-innhold: havn-navn + ferskhet-status + per-vare priser
        med trend (eller "?" for stale, ingen rader for aldri besøkt).
        """
        focused_pid = self._focused_port_id
        port_cfg = _port_config.get(focused_pid)
        bal = _balance.get()
        clock = self._state.world_state.clock
        observed_for_port = self._state.economy_state.observed.get(focused_pid)
        market_state = self._state.economy_state.markets.get(focused_pid)
        if market_state is None:
            return  # defensive — burde alltid eksistere
        is_current = focused_pid == self._current_port_id
        lines = build_tooltip_lines(
            port_name=port_cfg.name,
            observed_for_port=observed_for_port,
            market_state=market_state,
            catalog_order=self._catalog_order,
            catalog_names=self._catalog_names,
            current_day=clock.day,
            stale_threshold=bal.observed.stale_threshold_days,
            is_current_port=is_current,
        )
        anchor = self._port_positions[focused_pid]
        self._tooltip.draw(surface, lines, anchor)

    def on_exit(self, to_scene: str | None = None) -> None:
        """Ingen save her — WorldMapScene har ingen mutabel state som
        ikke allerede lever i GameState.
        """
        pass
