"""Animerte fugler som flyr over havne-himmelen.

Adresserer "fugler som er frosset i lufta": de baked-in fugle-silhuettene i
gameplay-laget er statiske (silhuetter på master/tak). Dette systemet legger
til *flygende* fugler som driver horisontalt over himmelen med vinge-flapp
og subtil vertikal sinus-bevegelse — visuell liv uten å forstyrre den
baked-in atmosfæren.

Designprinsipper:

- **Per-havn-konfig.** Antall, høyde-bånd, og art (måke/pelikan) varieres
  per havn slik at Tortuga får måker, Nassau pelikaner, Havana duer osv.
- **World-koordinater.** Fugler beveger seg i verden-koordinater, ikke
  skjerm-koordinater. Camera-offset håndteres ved tegning.
- **Lat oppdatering.** Vinge-toggle hvert 0.35 sek, ingen tunge per-frame
  beregninger. Fblits for batch-blitting.
- **Lys-gating.** Synlige hovedsakelig om dagen og kvelden. Om natten er
  fuglene sovende — vi tegner dem ikke (bevarer den moody natt-stemningen).
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

import pygame

import constants


# To-frame vinge-positur for en distansert silhuett. Hver "frame" er en
# liten 5x3-Surface med colorkey for transparens. Vi cacher dem globalt
# slik at alle scener deler samme to surfaces.
_FRAME_CACHE: dict[tuple, tuple[pygame.Surface, pygame.Surface]] = {}
_COLORKEY = (255, 0, 255)


def _build_frames(color: tuple) -> tuple[pygame.Surface, pygame.Surface]:
    """Lag (vinger_opp, vinger_ned)-silhuetter i oppgitt farge."""
    cached = _FRAME_CACHE.get(color)
    if cached is not None:
        return cached

    # Vinger opp: V-form ovenfra (klassisk "fugl i det fjerne"-ikon)
    up = pygame.Surface((5, 3)).convert()
    up.set_colorkey(_COLORKEY)
    up.fill(_COLORKEY)
    up.set_at((0, 1), color)
    up.set_at((1, 0), color)
    up.set_at((2, 1), color)
    up.set_at((3, 0), color)
    up.set_at((4, 1), color)

    # Vinger ned: M-form (motsatt fase)
    down = pygame.Surface((5, 3)).convert()
    down.set_colorkey(_COLORKEY)
    down.fill(_COLORKEY)
    down.set_at((0, 0), color)
    down.set_at((1, 1), color)
    down.set_at((2, 0), color)
    down.set_at((3, 1), color)
    down.set_at((4, 0), color)

    _FRAME_CACHE[color] = (up, down)
    return up, down


@dataclass
class FlyingBird:
    """Enkelt-fugl med world-pos, hastighet, og fase-offset for vinge-takt."""
    x: float
    y: float
    vx: float            # px/sek; positiv = flyr høyre
    base_y: float        # midten av sinus-bølgen
    sin_amp: float       # vertikal amplitude i px
    sin_freq: float      # rad/sek
    phase: float         # rad-offset i sinus-syklus
    flap_offset: float   # 0..1; offset i flapp-takt slik at flokken ikke synker
    color: tuple = constants.COLOR_HAT


@dataclass
class FlyingBirdsConfig:
    """Per-havn-konfig for fugle-systemet."""
    count: int = 4                    # antall fugler i flokken
    speed_min: float = 22.0           # px/sek
    speed_max: float = 38.0
    altitude_min: int = 30            # y_min (toppen av sky-bånd)
    altitude_max: int = 110           # y_max (bunnen — under måne, over horisont)
    sin_amp_min: float = 1.0
    sin_amp_max: float = 4.0
    color: tuple = constants.COLOR_HAT
    # Når night_factor >= dette tallet, slutter vi å tegne fugler.
    # 0.5 = sove fra ~kveld til ~daggry; 1.0 = aldri sove.
    sleep_threshold: float = 0.55
    # Ekstra fugler som spawner i flokk-bursts (sjeldent — gir liv-pulser).
    flock_burst_min_sec: float = 18.0
    flock_burst_max_sec: float = 35.0
    flock_burst_count: int = 3


class FlyingBirds:
    """Manager for fugle-flokken. Eier en pool og oppdaterer/tegner dem.

    Bruks:
        birds = FlyingBirds(world_width=1600, config=FlyingBirdsConfig())
        # i scene.update(dt):
        birds.update(dt, night_factor)
        # i scene.draw():
        birds.draw(surface, camera_x)
    """

    def __init__(self, world_width: int, config: FlyingBirdsConfig | None = None) -> None:
        self.world_width = world_width
        self.config = config or FlyingBirdsConfig()
        self._birds: list[FlyingBird] = []
        self._flap_timer: float = 0.0
        self._flap_state: int = 0  # 0 = wings up, 1 = wings down
        self._flock_burst_timer: float = self._roll_burst_interval()
        self._rng = random.Random(0xB1D5)
        self._spawn_initial_flock()

    def _roll_burst_interval(self) -> float:
        return random.uniform(
            self.config.flock_burst_min_sec, self.config.flock_burst_max_sec,
        )

    def _spawn_initial_flock(self) -> None:
        """Forhåndsfyll med fugler spredt over hele verden-bredden, slik at
        spilleren ser dem umiddelbart — ikke en tom himmel som først blir
        befolket etter første reise gjennom verden."""
        for _ in range(self.config.count):
            self._birds.append(self._spawn_at_random_x())

    def _spawn_at_random_x(self) -> FlyingBird:
        c = self.config
        x = self._rng.uniform(0, self.world_width)
        return self._make_bird(x, prefer_direction=None)

    def _spawn_off_left_or_right(self) -> FlyingBird:
        """Spawn utenfor verden-kant slik at fuglen flyr inn på skjermen."""
        c = self.config
        if self._rng.random() < 0.5:
            x = -8.0
            return self._make_bird(x, prefer_direction=+1)
        else:
            x = float(self.world_width + 8)
            return self._make_bird(x, prefer_direction=-1)

    def _make_bird(self, x: float, prefer_direction: int | None) -> FlyingBird:
        c = self.config
        speed = self._rng.uniform(c.speed_min, c.speed_max)
        if prefer_direction is None:
            vx = speed * (1.0 if self._rng.random() < 0.5 else -1.0)
        else:
            vx = speed * prefer_direction
        base_y = float(self._rng.randint(c.altitude_min, c.altitude_max))
        sin_amp = self._rng.uniform(c.sin_amp_min, c.sin_amp_max)
        sin_freq = self._rng.uniform(0.6, 1.4)
        phase = self._rng.uniform(0, math.tau)
        flap_offset = self._rng.uniform(0, 1.0)
        return FlyingBird(
            x=x, y=base_y, vx=vx, base_y=base_y,
            sin_amp=sin_amp, sin_freq=sin_freq, phase=phase,
            flap_offset=flap_offset, color=c.color,
        )

    def update(self, dt: float, night_factor: float = 0.0) -> None:
        """Avansér fugle-flokken. `night_factor` >= sleep_threshold → no-op
        (fuglene sover om natten — pure no-op, vi rører ikke pos)."""
        if night_factor >= self.config.sleep_threshold:
            return

        self._flap_timer += dt
        if self._flap_timer >= 0.35:
            self._flap_timer = 0.0
            self._flap_state ^= 1

        # Flokk-bursts: av og til slipper vi inn ekstra fugler i kort flokk.
        self._flock_burst_timer -= dt
        if self._flock_burst_timer <= 0.0:
            self._flock_burst_timer = self._roll_burst_interval()
            for _ in range(self.config.flock_burst_count):
                self._birds.append(self._spawn_off_left_or_right())

        # Bevegelse og resirkulering
        new_list: list[FlyingBird] = []
        for b in self._birds:
            b.x += b.vx * dt
            # Vertikal sinus rundt base_y
            b.y = b.base_y + math.sin(self._flap_timer * b.sin_freq + b.phase) * b.sin_amp
            # Holde bare fugler innenfor en margin rundt verden — slipp dem
            # ut av sirkulasjon når de flyr godt utenfor for å unngå
            # uendelig vekst etter mange flokk-bursts.
            margin = 32
            if -margin <= b.x <= self.world_width + margin:
                new_list.append(b)
        self._birds = new_list

        # Hold minimum config.count i live — etterfyll fra kanten.
        while len(self._birds) < self.config.count:
            self._birds.append(self._spawn_off_left_or_right())

    def draw(
        self, surface: pygame.Surface, camera_x: float, night_factor: float = 0.0,
    ) -> None:
        if night_factor >= self.config.sleep_threshold:
            return
        if not self._birds:
            return
        frame_up, frame_down = _build_frames(self.config.color)
        frame = frame_up if self._flap_state == 0 else frame_down
        # Bygg batch i ett pass; filtrér ut fugler utenfor synsfelt.
        screen_w = surface.get_width()
        batch = []
        for b in self._birds:
            sx = int(b.x - camera_x)
            sy = int(b.y)
            if -8 <= sx <= screen_w + 8:
                # Velg per-fugl frame ut fra flap_offset slik at flokken ikke
                # synker (flapp-fase ulik per fugl).
                use_alt = (self._flap_state ^ (1 if b.flap_offset > 0.5 else 0)) != 0
                f = frame_down if use_alt else frame_up
                batch.append((f, (sx, sy)))
        if batch:
            surface.fblits(batch)


def make_default_config_for_port(port_id: str) -> FlyingBirdsConfig:
    """Per-havn-konfig som matcher havnens karakter.

    - Tortuga: måker, mange, lavt — havne-mas og rå atmosfære
    - Port Royal: måker, færre, høyere — autoritet, ren himmel
    - Havana: duer, varierende — mer urban, jevn aktivitet
    - Nassau: pelikaner, færre men store — lovløs, latskap
    """
    if port_id == "tortuga":
        return FlyingBirdsConfig(
            count=9, color=constants.COLOR_MOON_HALO,
            altitude_min=30, altitude_max=130,
            speed_min=24.0, speed_max=44.0,
            flock_burst_count=5,
            flock_burst_min_sec=12.0, flock_burst_max_sec=22.0,
        )
    if port_id == "port_royal":
        return FlyingBirdsConfig(
            count=6, color=constants.COLOR_MOON_HALO,
            altitude_min=25, altitude_max=95,
            speed_min=28.0, speed_max=42.0,
            flock_burst_count=3,
            flock_burst_min_sec=14.0, flock_burst_max_sec=24.0,
        )
    if port_id == "havana":
        return FlyingBirdsConfig(
            count=7, color=constants.COLOR_STONE_LIT,
            altitude_min=30, altitude_max=115,
            speed_min=20.0, speed_max=36.0,
            flock_burst_count=4,
            flock_burst_min_sec=12.0, flock_burst_max_sec=20.0,
        )
    if port_id == "nassau":
        return FlyingBirdsConfig(
            count=6, color=constants.COLOR_WOOD_LIGHT,
            altitude_min=45, altitude_max=135,
            speed_min=18.0, speed_max=32.0,
            flock_burst_count=3,
            flock_burst_min_sec=14.0, flock_burst_max_sec=26.0,
        )
    # Fallback
    return FlyingBirdsConfig()
