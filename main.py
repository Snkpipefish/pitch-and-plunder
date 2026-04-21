"""Entry point for Pitch & Plunder.

Ansvar:
- Sette SDL env vars (via import av constants) FØR pygame initialiseres
- Opprette vindu med pygame.SCALED og 640x360 intern render-surface
- Blokkere unødvendige events
- Kjøre hovedløkke med Clock.tick(TARGET_FPS) (IKKE tick_busy_loop)
- Holde styr på scene-bytter
- F11 toggler fullskjerm
"""

from __future__ import annotations

import logging
import sys
from typing import Callable

import constants  # Setter env vars som MÅ være satt før pygame importeres
import pygame

from config import port_config as port_config_module
from systems import balance as balance_module  # Må init-es før andre systemer
from systems import debug_teleport
from systems import dev_mode
from systems import events as events_module


# Eksplisitt init ved oppstart — feiler høylydt hvis balance.json eller
# ports.json mangler eller er ødelagt. Må skje FØR moduler som leser
# balance/ports (economy, save, pitch_lake, game_clock, exchange, village)
# importeres via scenes/systems-under.
balance_module.init()
port_config_module.init()
# Fase 3 C3-11: events.json må være lastet før økonomi-pipeline kaller
# sample_port_event / sample_voyage_event. Samme filosofi som balance —
# feil høylydt ved oppstart, ikke midt i handel.
events_module.init()


from scenes.base_scene import BaseScene  # noqa: E402
from scenes.parallax_test import ParallaxTestScene  # noqa: E402
from scenes.port_village import PortVillageScene  # noqa: E402
from scenes.voyage import VoyageScene  # noqa: E402
from scenes.world_map import WorldMapScene  # noqa: E402
from state import GameState  # noqa: E402
from systems import save as save_module  # noqa: E402
from ui.toast import Toast  # noqa: E402


log = logging.getLogger("pitch_and_plunder")


class PlaceholderScene(BaseScene):
    """Midlertidig scene som kun fyller skjermen med himmelfargen.

    Erstattes av village-scenen i Commit 4. Finnes for å gi oss en kjørbar
    hovedløkke og noe å benchmarke mot.
    """

    def __init__(self, font: pygame.font.Font) -> None:
        super().__init__()
        self._bg_color = constants.COLOR_SKY_DEEP
        # Pre-rendrede tekst-surfaces (cache: aldri re-render per frame)
        self._title = font.render(
            "Pitch & Plunder", False, constants.COLOR_MOON_CORE
        ).convert_alpha()
        self._hint = font.render(
            "F11 fullskjerm  ESC avslutt", False, constants.COLOR_STONE_LIT
        ).convert_alpha()
        self._title_pos = (
            (constants.RENDER_WIDTH - self._title.get_width()) // 2,
            constants.RENDER_HEIGHT // 2 - 20,
        )
        self._hint_pos = (
            (constants.RENDER_WIDTH - self._hint.get_width()) // 2,
            constants.RENDER_HEIGHT // 2 + 10,
        )

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN and event.key in constants.KEY_MENU:
            self.want_quit = True

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill(self._bg_color)
        surface.blit(self._title, self._title_pos)
        surface.blit(self._hint, self._hint_pos)


SceneFactory = Callable[[], BaseScene]


class SceneManager:
    """Holder aktiv scene og utfører bytter mellom dem.

    Eier `GameState`-referansen og sender den med inn i scenenes
    `on_enter`/`on_exit`-kall slik at scener ikke trenger å hente state
    selv. `from_scene=None` ved første oppstart; ellers navnet på
    forrige scene.
    """

    def __init__(
        self,
        factories: dict[str, SceneFactory],
        initial: str,
        game_state: GameState,
    ) -> None:
        self._factories = factories
        self._game_state = game_state
        self._current_name = initial
        self._current: BaseScene = factories[initial]()
        self._current.on_enter(game_state, from_scene=None)

    @property
    def current(self) -> BaseScene:
        return self._current

    @property
    def current_name(self) -> str:
        return self._current_name

    def maybe_switch(self) -> None:
        """Utfør scene-bytte hvis aktiv scene har bedt om det."""
        target = self._current.next_scene
        if target is None:
            return
        if target not in self._factories:
            log.warning("Ukjent scene: %s", target)
            self._current.next_scene = None
            return
        self._current.on_exit(to_scene=target)
        prev_name = self._current_name
        self._current = self._factories[target]()
        self._current_name = target
        self._current.on_enter(self._game_state, from_scene=prev_name)


def _create_display(fullscreen: bool) -> pygame.Surface:
    """Opprett pygame display.

    Vi bruker `pygame.SCALED` slik at vi kan tegne direkte i logisk 640x360-
    oppløsning, og lar SDL skalere opp til ønsket vindusstørrelse med
    nearest-neighbor. Hvis SCALED ikke er tilgjengelig (f.eks. gamle SDL-
    byggd eller rare driver-kombinasjoner), fallbacker vi til et større
    software-vindu og skalerer manuelt.

    Returnerer surface som scenen skal tegne på (alltid 640x360).
    """
    flags = pygame.SCALED
    if fullscreen:
        flags |= pygame.FULLSCREEN
    try:
        window = pygame.display.set_mode(
            (constants.RENDER_WIDTH, constants.RENDER_HEIGHT), flags
        )
        log.info("Display: pygame.SCALED %dx%d fullscreen=%s",
                 constants.RENDER_WIDTH, constants.RENDER_HEIGHT, fullscreen)
        return window
    except pygame.error as exc:
        log.warning("SCALED feilet (%s) – bruker software fallback", exc)
        flags = pygame.FULLSCREEN if fullscreen else 0
        pygame.display.set_mode(constants.DEFAULT_WINDOW_SIZE, flags)
        # Returner en intern render-surface; main-løkken skalerer manuelt
        return pygame.Surface(
            (constants.RENDER_WIDTH, constants.RENDER_HEIGHT)
        ).convert()


def _load_font(size: int) -> pygame.font.Font:
    """Last Public Pixel-fonten. Fallback til SysFont hvis den mangler."""
    path = "assets/fonts/PublicPixel.ttf"
    try:
        font = pygame.font.Font(path, size)
        log.info("Lastet pixel font: %s (size=%d)", path, size)
        return font
    except (pygame.error, FileNotFoundError) as exc:
        log.warning("Kunne ikke laste %s (%s) – bruker SysFont", path, exc)
        return pygame.font.SysFont(None, size)


def _handle_balance_reload(
    game_state: "GameState",
    manager: "SceneManager",
    pending_session_sync: bool,
    font: pygame.font.Font,
) -> bool:
    """Kalles ved F5 i dev-mode. Returnerer ny pending_session_sync-verdi.

    - Leser balance.json på nytt via balance_module.reload().
    - Live-applicable endringer synkes umiddelbart til `game_state` felt
      som carry-over verdier (pitch_lake upkeep/production).
    - Session-applicable endringer (time.seconds_per_day_*) utsettes til
      neste new_day-event — signalisert via retur-True.
    - Newgame-only endringer ignoreres; logges via toast.
    - Feil: toast med feilmelding, ingen state-endring.
    """
    result = balance_module.reload()
    toasts = manager.current.toasts
    if not result.success:
        log.warning("Balance reload feilet: %s", result.error)
        if toasts is not None:
            toasts.push(Toast(
                font=font,
                text=f"Balance: {result.error}",
                color=constants.COLOR_EMBER,
            ))
        return pending_session_sync

    # Live-sync: pitch_lake-felt (upkeep og production er live per spec §4.4).
    new_bal = balance_module.get()
    if "pitch_lake.upkeep_per_day" in result.live_changes:
        game_state.pitch_lake_state.upkeep_per_day = new_bal.pitch_lake.upkeep_per_day
    if "pitch_lake.production_per_day" in result.live_changes:
        game_state.pitch_lake_state.production_per_day = new_bal.pitch_lake.production_per_day

    # Session-sync: hvis time-endringer, marker pending. Klokken selv
    # oppdateres ved neste new_day-event (se hovedløkka).
    if result.session_changes:
        pending_session_sync = True

    # Toast
    if toasts is not None:
        total = (
            len(result.live_changes)
            + len(result.session_changes)
            + len(result.newgame_changes)
        )
        if total == 0:
            msg = "Balance lastet på nytt (ingen endringer)"
        elif result.session_changes and not result.live_changes:
            msg = "Balance: tid/dag endres fra neste dawn"
        elif result.newgame_changes and not result.live_changes and not result.session_changes:
            msg = "Balance: krever nytt spill"
        else:
            bits = []
            if result.live_changes:
                bits.append(f"{len(result.live_changes)} live")
            if result.session_changes:
                bits.append(f"{len(result.session_changes)} dawn")
            if result.newgame_changes:
                bits.append(f"{len(result.newgame_changes)} nytt spill")
            msg = "Balance: " + " + ".join(bits)
        toasts.push(Toast(font=font, text=msg, color=constants.COLOR_STONE_LIT))
    log.info(
        "Balance reload: %d live, %d session, %d newgame",
        len(result.live_changes),
        len(result.session_changes),
        len(result.newgame_changes),
    )
    return pending_session_sync


def run() -> int:
    """Start hovedløkken. Returnerer exit-kode."""
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )

    # IKKE pygame.init() – vi unngår mixer-subsystemet i Fase 1.
    pygame.display.init()
    pygame.font.init()
    pygame.event.set_blocked(constants.BLOCKED_EVENTS)
    pygame.display.set_caption("Pitch & Plunder")

    fullscreen = False
    render_surface = _create_display(fullscreen)
    # Når SCALED fungerer er render_surface == window, og pygame håndterer
    # skaleringen. I software-fallback er render_surface en separat surface
    # og vi må blit-e + skalere manuelt til display-vinduet.
    window = pygame.display.get_surface()
    needs_manual_scale = render_surface is not window

    font_small = _load_font(8)

    # Last spilltilstand fra disk, eller fall tilbake til startverdier.
    # PortVillageScene avgjør selv i on_enter om den skal bruke saved posisjon
    # eller scene-spesifikk startposisjon, basert paa from_scene-argumentet
    # og innholdet i game_state.
    loaded = save_module.load()
    game_state = loaded if loaded is not None else save_module.new_game_state()

    # Initial-scene-valg: hvis save inneholder en aktiv voyage, resume
    # midt i reise via VoyageScene. Ellers start i havn.
    initial_scene = (
        "voyage"
        if game_state.world_state.voyage is not None
        else "port_village"
    )
    if initial_scene == "voyage":
        log.info(
            "Voyage-resume: %s → %s (dag %d → %d)",
            game_state.world_state.voyage.from_port,
            game_state.world_state.voyage.to_port,
            game_state.world_state.voyage.depart_day,
            game_state.world_state.voyage.arrival_day,
        )

    manager = SceneManager(
        factories={
            "placeholder": lambda: PlaceholderScene(font_small),
            "parallax_test": lambda: ParallaxTestScene(font_small),
            "port_village": lambda: PortVillageScene(
                font_small,
                game_state,
                port_config_module.get(game_state.world_state.current_port),
            ),
            "world_map": lambda: WorldMapScene(font_small, game_state),
            "voyage": lambda: VoyageScene(font_small, game_state),
        },
        initial=initial_scene,
        game_state=game_state,
    )

    # Dev-mode (F5 hot-reload av balance.json) detekteres ved oppstart.
    # Endring krever restart.
    dev_active = dev_mode.is_dev_mode()
    if dev_active:
        log.info("Dev-mode aktiv: F5 re-laster data/balance.json")

    # Pending-flagg for "session-applicable"-endringer (spec §4.4):
    # seconds_per_day_in_port kan endres via hot-reload, men klokken skal
    # ikke hoppe midt i en dag. Vi synker ved neste new_day-event.
    pending_session_sync = False

    clock = pygame.time.Clock()
    running = True
    while running:
        dt = clock.tick(constants.TARGET_FPS) / 1000.0

        # Sentral spill-klokke – inkrementerer dag hvert seconds_per_day.
        # Ved new_day-event: hvis hot-reload har endret time.*-felt, synker
        # vi clock.seconds_per_day fra balance her (session-applicable).
        events = game_state.world_state.clock.update(dt)
        if pending_session_sync and "new_day" in events:
            new_spd = balance_module.get().time.seconds_per_day_in_port
            game_state.world_state.clock.seconds_per_day = new_spd
            pending_session_sync = False
            log.info("Clock seconds_per_day synket til %.1f", new_spd)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                break
            if event.type == pygame.KEYDOWN and event.key in constants.KEY_FULLSCREEN:
                fullscreen = not fullscreen
                render_surface = _create_display(fullscreen)
                window = pygame.display.get_surface()
                needs_manual_scale = render_surface is not window
                continue
            if (
                dev_active
                and event.type == pygame.KEYDOWN
                and event.key in constants.KEY_DEV_RELOAD
            ):
                pending_session_sync = _handle_balance_reload(
                    game_state, manager, pending_session_sync, font_small
                )
                continue
            # Debug-teleport F1-F4 i dev-mode (per spec §10 C6). Fanges
            # før scenens handle_event slik at det fungerer uansett
            # hvilken scene spilleren er i (port_village eller world_map).
            if (
                dev_active
                and event.type == pygame.KEYDOWN
            ):
                teleport_target = debug_teleport.handle_teleport_key(
                    event.key, game_state,
                )
                if teleport_target is not None:
                    # Scene-bytte til port_village (samme scene-id uansett
                    # target-havn; PortVillageScene-factoryen leser
                    # current_port ved instansiering). Gjør eksplisitt
                    # scene-bytte framfor å la current scene fortsette —
                    # ellers lekker scene-state (pulsering-timer, fokus)
                    # fra world_map hvis teleport skjer derfra.
                    manager.current.next_scene = "port_village"
                    continue
            manager.current.handle_event(event)

        if manager.current.want_quit:
            running = False
            break

        manager.current.update(dt)
        manager.current.draw(render_surface)

        if needs_manual_scale:
            pygame.transform.scale(render_surface, window.get_size(), window)
        pygame.display.flip()

        manager.maybe_switch()

    # Autosave paa QUIT: lar scenen sync-e sin tilstand inn i GameState
    # og skrive til disk. BaseScene.autosave() er no-op i default-klassen,
    # saa ukjente scener faller gjennom trygt.
    try:
        manager.current.autosave()
    except Exception:  # Logg og fortsett avslutning uansett
        log.exception("Autosave paa QUIT feilet")

    pygame.display.quit()
    pygame.font.quit()
    return 0


if __name__ == "__main__":
    sys.exit(run())
