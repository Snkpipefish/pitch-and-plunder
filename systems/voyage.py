"""Voyage-helpers: rute-oppslag, progresjon, posisjon og start/komplett.

Pure (eller deterministisk muterende på state) — ingen scene-avhengighet.
Brukes av WorldMapScene (start_voyage ved bekreftet reise), VoyageScene
(progress + posisjon per frame), PortVillageScene.on_enter (complete_voyage
ved ankomst), og debug_teleport (complete_voyage ved teleport under reise).

Per FASE_2B.md §7. Designvalg:
- compute_progress er deterministisk fra clock-state, IKKE per-frame
  akkumulering. Voyage-resume etter save+load fungerer trivielt fordi
  clock-state alene rekonstruerer progresjonen.
- compute_heading klamper til nærmeste 4-retning; horisontal vinner ved
  diagonalt-likestilte vektorer (vilkårlig, men deterministisk).
- start_voyage trekker IKKE gull i C7. C9 eier gull-håndteringen
  (trekk + blokkering + toast). C7-dialog viser kun "Tid: N dager".
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from state.voyage_state import VoyageState
from systems.economy import write_observed_for_port

if TYPE_CHECKING:
    from state.game_state import GameState
    from systems.balance import Balance, RouteInfo
    from systems.game_clock import GameClock


log = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Rute-oppslag
# -----------------------------------------------------------------------------

def route_key(a: str, b: str) -> str:
    """Alfabetisk sortert "{a}-{b}"-nøkkel for travel.routes-oppslag.

    Per FASE_2B.md §4.3: rute-nøkler unngår duplikatoppføringer ved å
    standardisere på alfabetisk rekkefølge.
    """
    return "-".join(sorted([a, b]))


def get_route(balance: "Balance", a: str, b: str) -> "RouteInfo | None":
    """Hent rute-info mellom to havner, eller None hvis ruten ikke finnes."""
    return balance.travel.routes.get(route_key(a, b))


def voyage_cost(balance: "Balance", a: str, b: str) -> int | None:
    """Returner gull-kost for ruten, eller None hvis ruten ikke finnes.

    C9: pure helper for forhåndssjekk av affordability + dialog-
    rendering. Trekker IKKE gull selv — det gjør `start_voyage` etter
    å ha verifisert at spilleren har råd.
    """
    route = get_route(balance, a, b)
    if route is None:
        return None
    return route.gold


# -----------------------------------------------------------------------------
# Heading-beregning
# -----------------------------------------------------------------------------

def compute_heading(
    from_pos: tuple[int, int], to_pos: tuple[int, int]
) -> str:
    """Klamp fra→til-vektoren til nærmeste 4-retning ("N", "S", "E", "V").

    Pygame y-akse peker NEDOVER (positive y = sør). Konvensjon:
    - dy < 0 → N (nord)
    - dy > 0 → S (sør)
    - dx > 0 → E (øst)
    - dx < 0 → V (vest)

    Tie-breaking: hvis |dx| == |dy| (eksakt diagonal), velg horisontal —
    deterministisk valg, vilkårlig retning. Same-pos input (dx=dy=0) gir
    "N" (også deterministisk fallback).
    """
    dx = to_pos[0] - from_pos[0]
    dy = to_pos[1] - from_pos[1]
    if dx == 0 and dy == 0:
        return "N"
    if abs(dx) >= abs(dy):
        return "E" if dx > 0 else "V"
    return "S" if dy > 0 else "N"


# -----------------------------------------------------------------------------
# Progress + posisjon
# -----------------------------------------------------------------------------

def compute_progress(
    voyage: VoyageState, clock: "GameClock", balance: "Balance"
) -> float:
    """Returner progresjon 0.0–1.0 basert på klokken (deterministisk).

    elapsed_sec = (clock.day - depart_day) * spd_at_sea + clock.seconds_into_day
    total_sec   = (arrival_day - depart_day) * spd_at_sea
    progress    = clamp(elapsed_sec / total_sec, 0, 1)

    Ved same-day-rute (arrival_day == depart_day): returner 1.0 for å
    unngå division-by-zero. Min-rute er 2 dager i 2B, så dette er
    defensiv.
    """
    spd = balance.time.seconds_per_day_at_sea
    days_total = voyage.arrival_day - voyage.depart_day
    total_sec = days_total * spd
    if total_sec <= 0.0:
        return 1.0
    days_elapsed = clock.day - voyage.depart_day
    elapsed_sec = days_elapsed * spd + clock.seconds_into_day
    progress = elapsed_sec / total_sec
    if progress < 0.0:
        return 0.0
    if progress > 1.0:
        return 1.0
    return progress


def interpolate_position(
    from_pos: tuple[int, int],
    to_pos: tuple[int, int],
    progress: float,
) -> tuple[int, int]:
    """Lineær interpolasjon mellom from_pos og to_pos. Returnerer (int, int)
    klar for blit-koordinater.
    """
    x = round(from_pos[0] + (to_pos[0] - from_pos[0]) * progress)
    y = round(from_pos[1] + (to_pos[1] - from_pos[1]) * progress)
    return (x, y)


# -----------------------------------------------------------------------------
# Voyage-livssyklus
# -----------------------------------------------------------------------------

def start_voyage(
    state: "GameState",
    balance: "Balance",
    from_port: str,
    to_port: str,
) -> VoyageState | None:
    """Initier en aktiv reise fra `from_port` til `to_port`.

    Effekter ved suksess:
    - Snapshot av from_port observed (spilleren har akkurat vært i
      børsen, prisene er ferskt sett)
    - Trekk `route.gold` fra `state.player_state.gold` (C9: gull-
      håndtering er nå atomisk med voyage-state — enten begge
      lykkes eller ingen)
    - Ny VoyageState i `state.world_state.voyage` med depart_day fra
      klokken og arrival_day = depart_day + route.days
    - Klokkens `seconds_per_day` byttes til `at_sea`-tempo

    Returnerer VoyageState ved suksess, None hvis:
    - Ruten finnes ikke (ukjent (from, to)-par i balance.travel.routes)
    - En reise er allerede aktiv (defensive — caller burde ha sjekket)
    - Spilleren har ikke råd til ruten (gold < route.gold). C9:
      caller (WorldMapScene) skal ha pre-sjekket via `voyage_cost`
      og blokkert med toast før dialog åpnes — dette er en
      defensive guard for å holde state-mutasjonen atomisk.

    Ved None-retur: INGEN state-mutasjon (gull, voyage, clock,
    observed alle uendret).
    """
    if state.world_state.voyage is not None:
        log.warning(
            "start_voyage: voyage allerede aktiv (%s→%s) — ignorerer ny start",
            state.world_state.voyage.from_port,
            state.world_state.voyage.to_port,
        )
        return None
    route = get_route(balance, from_port, to_port)
    if route is None:
        log.warning(
            "start_voyage: ingen rute for %s→%s i balance.travel.routes",
            from_port, to_port,
        )
        return None
    if state.player_state.gold < route.gold:
        log.warning(
            "start_voyage: insufficient gold (%d < %d) for %s→%s",
            state.player_state.gold, route.gold, from_port, to_port,
        )
        return None

    # Snapshot from_port observed FØR mutasjon — defensivt mot at
    # write_observed-feil ikke skal etterlate halv-startet voyage.
    write_observed_for_port(state, from_port)

    # Atomisk: gull-trekk + voyage-state + clock-tempo. Etter denne
    # punktet er reisen committed.
    state.player_state.gold -= route.gold
    depart_day = state.world_state.clock.day
    voyage = VoyageState(
        from_port=from_port,
        to_port=to_port,
        depart_day=depart_day,
        arrival_day=depart_day + route.days,
        progress=0.0,
    )
    state.world_state.voyage = voyage
    state.world_state.clock.seconds_per_day = balance.time.seconds_per_day_at_sea
    # Fase 3 C3-12: løp-telling for score-overlay. Inkrementeres kun
    # ved suksessfull atomisk commit (etter gull-trekk + voyage-state).
    state.player_state.total_voyages += 1
    log.info(
        "Voyage startet: %s → %s, dag %d → %d (rute=%d dager, kost=%d gull)",
        from_port, to_port, depart_day, voyage.arrival_day,
        route.days, route.gold,
    )
    return voyage


def complete_voyage(state: "GameState", balance: "Balance") -> str:
    """Fullfør aktiv reise. Setter current_port=to_port, nuller voyage,
    justerer klokken tilbake til in_port-tempo.

    Returnerer den nye current_port-id-en.

    No-op hvis ingen voyage er aktiv — returnerer da gjeldende
    current_port. Defensiv mot dobbelt-kall (f.eks. ankomst + senere
    teleport-rydding).

    Skriver IKKE observed for to_port — det er ankomst-flytens ansvar
    (PortVillageScene.on_enter from_scene="voyage" i C7c) slik at
    debug_teleport-stien ikke blander seg inn i ankomst-semantikken.
    """
    voyage = state.world_state.voyage
    if voyage is None:
        return state.world_state.current_port
    to_port = voyage.to_port
    state.world_state.current_port = to_port
    state.world_state.voyage = None
    state.world_state.clock.seconds_per_day = balance.time.seconds_per_day_in_port
    log.info("Voyage fullført: ankomst %s (dag %d)", to_port, state.world_state.clock.day)
    return to_port
