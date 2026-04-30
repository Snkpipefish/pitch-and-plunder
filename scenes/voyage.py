"""VoyageScene — aktiv reise mellom to havner (Fase 2B C7c + Fase 3 C3-9.5).

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
- Ingen player-bevegelse utover skip-ikon, ingen aktiv styring.

**Fase 3 C3-9.5 — Tempo-akselerasjon (KUN wall-clock)**:

Scene-init setter `clock.seconds_per_day` til
`balance.time.voyage_animation_seconds / days_remaining`. Total wall-
clock-varighet er ~5 sek uansett rute-lengde. In-game-varighet
(arrival_day, antall dawn-ticks, rest-decay-basert-på-days) påvirkes
IKKE — KUN animasjons-tempo komprimeres.

Enter/Space/ESC hopper over resterende animasjon ved å sette
`clock.day = voyage.arrival_day` direkte. update() kjører dawn-tick-
loopen for gjenværende dager og trigger complete_voyage normalt.
Events og state-mutasjoner respekteres (C3-11 events vil interrupe
som vanlig siden de lever inne i dawn-tick-pipelinen).

Save/load under reise fungerer uendret: clock-state rekonstruerer
skip-posisjon, og scene-init recomputer tempo basert på nytt
days_remaining ved load — ~5 sek resterende animasjon uansett når
spilleren gjenopptar.
"""

from __future__ import annotations

import logging
import os

import pygame

import constants
from config import port_config as _port_config
from entities.port_marker import PortMarker
from entities.ship_icon import ShipIcon
from scenes.base_scene import BaseScene
from scenes.world_map import draw_port_markers_with_labels
from scenes.world_map_builder import build_world_map_background
from state import GameState
from systems import balance as _balance
from systems import events as _events
from systems import voyage as _voyage
from systems.economy import Market, tick_all_ports_dawn
from systems.pitch_lake import PitchLake
from systems.regime_manager import RegimeManager
from ui.event_dialog import EventDialog
from ui.toast import Toast, ToastQueue


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

        # Havn-markører + labels — samme rendering som WorldMapScene
        # via felles helper. C7c-patch: labels mangler ledet til
        # navigasjons-forvirring; spilleren trenger navne-orientering
        # under reise selv om scenen er passiv.
        self._port_ids = _port_config.get_all_port_ids()
        self._port_positions: dict[str, tuple[int, int]] = {
            pid: tuple(ports[pid].world_map_position)
            for pid in self._port_ids
        }
        self._port_labels: dict[str, pygame.Surface] = {
            pid: font.render(
                ports[pid].name, False, constants.COLOR_MOON_HALO,
            ).convert_alpha()
            for pid in self._port_ids
        }
        self._marker = PortMarker()

        # Skip-sprite (gjenbrukt fra C5).
        self._ship = ShipIcon()

        # Skip-røyk-trail (v2.7 livfullhet-pass): én dynamisk røyk-kilde
        # som flyttes til skipets posisjon hvert frame. Liten cool-tonet
        # røykfane med kort lifetime — gir skipet et levende trail uten
        # å distrahere fra det fjerne kart-perspektivet.
        from systems import chimney_smoke as _chimney_smoke  # lazy
        self._ship_smoke = _chimney_smoke.ChimneySmoke(
            sources=[_chimney_smoke.SmokeSource(
                x=0.0, y=0.0, kind="cool",
                period=0.18, pool_size=12,
                drift_x=0.0, rise_speed=8.0,
            )],
            seed=27,
        )

        # Flygende fugler over havet (v2.7 livfullhet-pass på voyage-scenen).
        # Topp-down 640x360 — fuglene drifter langsomt over hele kart-bredden.
        # Brukes uten night-gating (havet er alltid synlig i kart-form,
        # også om natten — havne-fasene endres ikke i C7c).
        from systems import flying_birds as _flying_birds  # lazy
        self._flying_birds = _flying_birds.FlyingBirds(
            world_width=constants.RENDER_WIDTH,
            config=_flying_birds.FlyingBirdsConfig(
                count=4,
                color=constants.COLOR_MOON_HALO,
                altitude_min=18,
                altitude_max=300,
                speed_min=18.0,
                speed_max=30.0,
                sin_amp_min=0.5,
                sin_amp_max=2.0,
                flock_burst_count=2,
                flock_burst_min_sec=20.0,
                flock_burst_max_sec=40.0,
                sleep_threshold=2.0,  # 2.0 = aldri sove (havet er vannskill)
            ),
        )

        # Dawn-tikk-infrastruktur — samme mønster som PortVillageScene.
        # Market er stateless katalog; samme instans opererer på alle
        # havners MarketState via parameter.
        self._market = Market.from_json(
            os.path.join(constants.DATA_DIR, "commodities.json")
        )
        self._regime_manager = RegimeManager()
        self._last_seen_day = state.world_state.clock.day

        # Fase 3 C3-9.5: akselerert wall-clock-tempo. Komprimerer hele
        # reise-animasjonen til `voyage_animation_seconds` total, uansett
        # rute-lengde. Dawn-tick-loopen i update() kjøres fortsatt N
        # ganger for gjenstående dager — kun tidsskalaen endres.
        #
        # days_remaining = voyage.arrival_day - current day. Ved fresh
        # voyage er det = route.days. Ved resume etter save/load kan
        # det være mindre; animasjonen bruker da ~voyage_animation_seconds
        # for resten av reisen.
        #
        # Nullstill seconds_into_day: hadde spilleren lagret midt-i-dag
        # med at_sea-tempo (75 s/dag, f.eks. 30 s inn), ville
        # ny (mye mindre) seconds_per_day tolke det som mange fulle
        # dager. Vi ofrer sub-day-presisjon ved resume for å holde
        # animasjons-semantikken ren.
        bal = _balance.get()
        days_remaining = voyage.arrival_day - state.world_state.clock.day
        if days_remaining > 0:
            state.world_state.clock.seconds_per_day = (
                bal.time.voyage_animation_seconds / days_remaining
            )
            state.world_state.clock.seconds_into_day = 0.0

        # HUD-tekst (statisk for hele reisen — destinasjons-info)
        self._title_surf = font.render(
            f"Reise: {self._from_port_name} \u2192 {self._to_port_name}",
            False, constants.COLOR_MOON_CORE,
        ).convert_alpha()
        # Fase 3 C3-9.5: skip-hint. Reisen kan ikke AVBRYTES (dawn-ticks
        # landes fortsatt); bare animasjonen hoppes over.
        self._hint_surf = font.render(
            "Enter/Space/Esc hopper til ankomst",
            False, constants.COLOR_FOG,
        ).convert_alpha()

        # C9: toast-kø for avreise-varsel ("Avreise mot Port Royal").
        # Eksisterer kun for fersk voyage, ikke ved resume — sporing
        # via clock.day == voyage.depart_day-sjekk i on_enter.
        self._toasts = ToastQueue(
            baseline_y=constants.RENDER_HEIGHT - 18,
            center_x=constants.RENDER_WIDTH // 2,
        )

        # Fase 3 C3-11: event-dialog. None naar ingen pending event.
        # Animasjonen pauses mens dialogen er åpen — oppnås ved at
        # update() returnerer tidlig før clock.update kjører (main.py
        # oppdaterer clock uansett, så vi må eksplisitt holde
        # seconds_into_day konstant). Praktisk: dialogen konsumerer
        # alle input-events og vi lar update() returnere tidlig for
        # å unngå nye dawn-ticks/arrival-deteksjon. Main.py sin
        # clock.update kjører fortsatt, men skip_to_arrival-logikken
        # og arrival-sjekk blokkeres. For en 5-sek-animasjon er dette
        # akseptabelt — dialogen tar typisk over hele oppmerksomheten.
        self._event_dialog: EventDialog | None = None
        self._pending_death_after_dialog = False

    @property
    def toasts(self) -> ToastQueue:
        """Eksponer toast-køen for eksterne systemer."""
        return self._toasts

    # --- Input ---

    def handle_event(self, event: pygame.event.Event) -> None:
        # Fase 3 C3-11: event-dialog konsumerer all input når åpen.
        if self._event_dialog is not None:
            self._event_dialog.handle_event(event)
            return
        # Fase 3 C3-9.5: Enter/Space/ESC hopper over resterende
        # animasjon ved å sette clock.day = arrival_day direkte. Neste
        # update() ser days_passed = gjenværende dager, kjører dawn-
        # tick-loopen som normalt (inkludert evt. events, sabotasje-
        # impact osv.) og trigger deretter complete_voyage. Ingen
        # spill-logikk hoppes over — kun wall-clock-animasjonen.
        #
        # Presisering C3-9.5 #2: "Once committed, go" fra spec §7.5
        # bevares — reisen AVBRYTES ikke (ingen retur til from_port),
        # bare visningen komprimeres til én frame.
        if event.type != pygame.KEYDOWN:
            return
        if event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_ESCAPE):
            self._skip_to_arrival()

    def _skip_to_arrival(self) -> None:
        """Hopp direkte til arrival-dagen. update() håndterer dawn-ticks
        + complete_voyage på neste frame."""
        voyage = self._state.world_state.voyage
        if voyage is None:
            return
        clock = self._state.world_state.clock
        if clock.day >= voyage.arrival_day:
            # Allerede ved eller forbi arrival — neste update() vil
            # trigge complete_voyage uansett. Ingen endring nødvendig.
            return
        clock.day = voyage.arrival_day
        clock.seconds_into_day = 0.0

    # --- Update ---

    def update(self, dt: float) -> None:
        # Fase 3 C3-11: event-dialog pauser videre logikk — ingen dawn-
        # ticks, ingen arrival-deteksjon mens spilleren leser eventet.
        # Main.py oppdaterer clock uansett, så vi må fryse seconds_into_day
        # for å forhindre at animasjonen skrider frem.
        if self._event_dialog is not None:
            self._toasts.update(dt)
            # Frys seconds_into_day for å pause animasjon visuelt.
            # Day er allerede bumped av main.py før event-sample; vi
            # lar bare seconds_into_day stå stille.
            self._state.world_state.clock.seconds_into_day = 0.0
            if self._event_dialog.want_close:
                self._event_dialog = None
                if self._pending_death_after_dialog:
                    self._pending_death_after_dialog = False
                    # Gå til port_village slik at C3-12 score-overlay
                    # kan trigges. C3-12 vil lese state.dead ved scene-
                    # entry. Foreløpig (før C3-12 lander): PortVillageScene
                    # fortsetter som normalt — score-overlay kommer senere.
                    self.next_scene = "port_village"
            return

        # Klokken oppdateres av main.run() (felles for alle scener);
        # VoyageScene må kun reagere på dag-skift og ankomst.
        self._toasts.update(dt)
        self._flying_birds.update(dt, night_factor=0.0)
        # Oppdater skip-røyk-kilden til skipets aktuelle posisjon før
        # smoke.update så nye partikler spawner ved riktig sted.
        voyage_active = self._state.world_state.voyage
        if voyage_active is not None:
            bal2 = _balance.get()
            progress2 = _voyage.compute_progress(
                voyage_active, self._state.world_state.clock, bal2,
            )
            sx, sy = _voyage.interpolate_position(
                self._from_pos, self._to_pos, progress2,
            )
            # Skip-skorstein litt over senter av skip-icon (3 px over).
            self._ship_smoke.set_source_position(0, sx, sy - 3)
        self._ship_smoke.update(dt, night_factor=0.0)
        clock = self._state.world_state.clock
        curr_day = clock.day

        # Dawn-tikk for hver dag som har passert siden forrige update.
        # Samme algoritme som PortVillageScene; sikrer at markedet i
        # alle 4 havner utvikler seg uavhengig av at spilleren er på
        # sjøen (per spec §7.3).
        #
        # Fase 3 C3-13b.1: `_last_seen_day` oppdateres basert på FAKTISK
        # prosesserte dawn-ticks, ikke clock.day ved exit. Hvis et
        # voyage-event bryter loopen tidlig, skal resterende dawn-
        # ticks prosesseres ved neste update etter dialog-close —
        # ingen dager kan tapes.
        if curr_day != self._last_seen_day:
            days_passed = max(0, curr_day - self._last_seen_day)
            processed = 0
            for _ in range(days_passed):
                tick_all_ports_dawn(
                    self._state, self._market, self._regime_manager,
                )
                PitchLake.on_new_day(
                    self._state.pitch_lake_state, self._state,
                )
                processed += 1
                # Fase 3 C3-11: voyage-event-sampling per passert dag.
                # Kjøres ETTER tick_all_ports_dawn (samme dawn-pipeline-
                # prinsipp som rumors/market_effects). Hvis en event
                # samples, resolve umiddelbart og pause animasjonen via
                # event-dialog. Break ut av for-loopen — resterende
                # dager prosesseres ved neste update etter dialog-close.
                if self._maybe_trigger_voyage_event():
                    break
            # Bruk faktisk prosesserte dager for å spore progresjon;
            # hvis vi brøt tidlig er _last_seen_day < curr_day, slik
            # at neste update finner `curr_day != _last_seen_day` og
            # prosesserer de gjenværende.
            self._last_seen_day += processed

        # Ankomst-deteksjon. complete_voyage setter current_port til
        # to_port og clock-tempo tilbake til in_port; PortVillageScene-
        # fabrikken (main.py) leser current_port og konstruerer riktig
        # havn-scene.
        #
        # Fase 3 C3-13b: vent på at event-dialogen er lukket før
        # scene-switch. Uten denne guarden rakk ikke dialogen å rendre
        # hvis et voyage-event ble samplet på siste dag av reisen —
        # complete_voyage triggeret scene-switch i samme update() som
        # åpnet dialogen. Neste update() etter close vil fortsatt se
        # curr_day >= arrival_day og trigger ankomsten normalt.
        if self._event_dialog is not None:
            return
        voyage = self._state.world_state.voyage
        if voyage is not None and curr_day >= voyage.arrival_day:
            _voyage.complete_voyage(self._state, _balance.get())
            self.next_scene = "port_village"

    def _maybe_trigger_voyage_event(self) -> bool:
        """Sample og eventuelt trigger voyage-event for denne dawn.
        Returnerer True hvis event ble triggered (event-dialog åpnet)."""
        if not _events.is_initialized():
            return False
        if self._state.arrested or self._state.dead:
            return False
        ev_id = _events.sample_voyage_event(self._state)
        if ev_id is None:
            return False
        title, body, died = _events.resolve(self._state, ev_id)
        self._event_dialog = EventDialog(
            font=self._font, title=title, body=body,
        )
        self._pending_death_after_dialog = died
        return True

    # --- Rendering ---

    def draw(self, surface: pygame.Surface) -> None:
        # Bakgrunn (pre-rendret én gang)
        surface.blit(self._background, (0, 0))

        # Havn-markører + labels via felles helper (C7c-patch).
        # from_port får "current"-state (varm ring) — spilleren er
        # konseptuelt fortsatt knyttet til avreise-havnen til ankomst
        # er fullført. Andre havner (inkludert to_port) får "other"-
        # state (kald ring); destinasjonen signaliseres tydelig nok via
        # skip-sprite som beveger seg mot den. Pulserende fokus-state
        # bruker vi ikke — reisen er passiv, ingen navigasjons-valg.
        voyage = self._state.world_state.voyage
        current_port_id = (
            voyage.from_port if voyage is not None
            else self._state.world_state.current_port
        )
        # C8: visited_port_ids fra observed — dempet markør for
        # havner spilleren aldri har besøkt.
        visited = set(self._state.economy_state.observed.keys())
        draw_port_markers_with_labels(
            surface=surface,
            port_ids=self._port_ids,
            port_positions=self._port_positions,
            port_labels=self._port_labels,
            marker=self._marker,
            current_port_id=current_port_id,
            elapsed=0.0,  # ingen pulsering i VoyageScene
            visited_port_ids=visited,
        )

        # Skip-posisjon — beregnes deterministisk fra clock-state per
        # frame. Save/load-resume fungerer trivielt fordi posisjon
        # rekonstrueres uten scene-state. Tegnes SIST slik at skipet
        # legger seg over markørene når det krysser dem.
        if voyage is not None:
            bal = _balance.get()
            progress = _voyage.compute_progress(
                voyage, self._state.world_state.clock, bal,
            )
            ship_pos = _voyage.interpolate_position(
                self._from_pos, self._to_pos, progress,
            )
            self._ship.draw(surface, ship_pos, heading=self._heading)

        # Skip-røyk-trail tegnes ETTER skipet (over master/seil) slik at
        # røyken stiger naturlig fra skorsteinen og ikke skjules av icon-
        # silhuetten.
        self._ship_smoke.draw(surface, camera_x=0.0)

        # Flygende fugler over havet — tegnes etter røyk og skip slik at
        # nærliggende silhuetter overlapper skipets master.
        self._flying_birds.draw(surface, camera_x=0.0, night_factor=0.0)

        # HUD-tekst (statisk per scene-init)
        surface.blit(self._title_surf, (8, 4))
        surface.blit(
            self._hint_surf,
            (8, constants.RENDER_HEIGHT - self._hint_surf.get_height() - 4),
        )

        # Toasts (avreise-varsel ved fersk voyage)
        self._toasts.draw(surface)

        # Fase 3 C3-11: event-dialog på topp (modal).
        if self._event_dialog is not None:
            self._event_dialog.draw(surface)

    # --- Lifecycle ---

    def on_enter(
        self,
        game_state: GameState,
        from_scene: str | None = None,
    ) -> None:
        """Ingen state-mutasjon — voyage er allerede satt opp av
        `voyage.start_voyage` i WorldMapScene-dialogen, eller av
        save-load (resume).

        C9: ved FERSK voyage (clock.day == voyage.depart_day) push
        avreise-toast. Ved RESUME (clock.day > depart_day) hopper vi
        over toasten — spilleren restartet midt-i-reise og trenger
        ikke en "Avreise"-melding for noe som allerede skjedde.
        """
        voyage = game_state.world_state.voyage
        if voyage is None:
            return
        if game_state.world_state.clock.day == voyage.depart_day:
            self._toasts.push(Toast(
                font=self._font,
                text=f"Avreise mot {self._to_port_name}",
                color=constants.COLOR_MOON_CORE,
            ))

    def on_exit(self, to_scene: str | None = None) -> None:
        """Ingen autosave her — clock + voyage + economy persistere
        konsistent via state-mutasjoner i update(). PortVillageScene
        (target-scenen) tar autosave i sin egen on_enter via ankomst-
        flyten."""
        return
