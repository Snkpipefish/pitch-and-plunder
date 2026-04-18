"""Partikkel-system: kald taake og varme ildfluer.

Object pool med forhaandsallokert liste paa 8 partikler totalt (4 taake +
4 ildfluer). Inaktive partikler tegnes ikke og oppdateres ikke (ingen
`active`-flag i praksis her, men taake-partiklene recycles alltid saa de
er alltid aktive; ildfluene despawner og respawner etter livsloeps-timer).

Ingen allokering per frame. Alle sprites pre-rendres ved init. Tegning
skjer i to fblits-batcher per frame: én for taake (normal blit) og én
for ildfluer (BLEND_RGB_ADD).

Rendering-rekkefolge (besluttet av scenen):
- Lys paa bygninger tegnes FOR taake-laget saa taaka forblir kald.
- Ildfluer tegnes ETTER taake-laget og med additive blending fordi de er
  naermere kameraet og skal lyse gjennom atmosfaeren.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass

import pygame

import constants


# Approksimert "30% taake over sjoe-moerk bakgrunn".
# 0.3 * COLOR_FOG (58,58,74) + 0.7 * COLOR_SEA_DEEP (15,24,41) ≈ (28,34,51).
# Vi loefter den litt for at taaka skal vaere lesbar: (45, 45, 58).
_FOG_MIXED = (45, 45, 58)

# Firefly-farge: full-intensitet gir additiv blast. Vi demper litt.
_FIREFLY_COLOR = (200, 170, 96)

# Magenta colorkey – en farge som ikke finnes i masterpaletten.
_CK = (255, 0, 255)


def _build_fog_sprites() -> list[pygame.Surface]:
    """Tre ellipsestoerrelser som recycles blant taake-partiklene."""
    sizes = [(24, 12), (32, 16), (40, 20)]
    sprites: list[pygame.Surface] = []
    for w, h in sizes:
        surf = pygame.Surface((w, h)).convert()
        surf.fill(_CK)
        pygame.draw.ellipse(surf, _FOG_MIXED, (0, 0, w, h))
        surf.set_colorkey(_CK)
        sprites.append(surf)
    return sprites


def _build_firefly_sprite() -> pygame.Surface:
    """2x2 px varm prikk, egnet for BLEND_RGB_ADD (ingen colorkey noedvendig)."""
    surf = pygame.Surface((2, 2)).convert()
    surf.fill(_FIREFLY_COLOR)
    return surf


@dataclass
class Particle:
    """Felles partikkelrecord. Ikke alle felt gjelder begge typer."""

    kind: str = ""          # "fog" eller "firefly"
    x: float = 0.0
    y: float = 0.0
    vx: float = 0.0
    vy: float = 0.0
    life: float = 0.0       # sekunder gjenstaende (firefly)

    # Taake-spesifikt
    sprite: pygame.Surface | None = None

    # Firefly-spesifikt
    base_x: float = 0.0
    base_y: float = 0.0
    amplitude: float = 0.0
    freq_x: float = 1.0
    freq_y: float = 1.0
    phase_x: float = 0.0
    phase_y: float = 0.0
    blink_phase: float = 0.0
    blink_period: float = 1.0


class ParticleSystem:
    """Holder partikkel-poolen og render-logikken."""

    def __init__(
        self,
        tavern_center: tuple[float, float],
        world_width: int,
        seed: int = 7,
    ) -> None:
        self._rng = random.Random(seed)
        self._fog_sprites = _build_fog_sprites()
        self._firefly_sprite = _build_firefly_sprite()
        self._tavern_cx, self._tavern_cy = tavern_center
        self._world_width = world_width
        self._elapsed: float = 0.0

        # Forhaandsallokert pool
        self._particles: list[Particle] = []
        for _ in range(4):
            p = Particle(kind="fog")
            self._init_fog(p, spread=True)
            self._particles.append(p)
        for _ in range(4):
            p = Particle(kind="firefly")
            self._init_firefly(p)
            self._particles.append(p)

        # Pre-allokerte batcher (recyclable) for draw() – bare referanser
        # oppdateres per frame.
        self._fog_batch: list[tuple[pygame.Surface, tuple[int, int]]] = []
        self._firefly_batch: list[tuple[pygame.Surface, tuple[int, int]]] = []

    # --- Initialisering / respawn ---

    def _init_fog(self, p: Particle, spread: bool = False) -> None:
        """Sett partikkel til fersk taake.

        `spread=True`: spre over hele verden ved init slik at taaken ikke
        "stroemmer inn" paa start. Ellers: spawn rett utenfor venstre kant.
        """
        if spread:
            p.x = self._rng.uniform(0.0, float(self._world_width))
        else:
            p.x = -40.0
        p.y = self._rng.uniform(325.0, 345.0)
        p.vx = self._rng.uniform(8.0, 12.0)
        p.vy = 0.0
        p.sprite = self._rng.choice(self._fog_sprites)

    def _init_firefly(self, p: Particle) -> None:
        """Sett partikkel til fersk ildflue rundt tavernaens midt."""
        angle = self._rng.uniform(0.0, 2.0 * math.pi)
        radius = self._rng.uniform(10.0, 60.0)
        p.base_x = self._tavern_cx + math.cos(angle) * radius
        # Halve radius i y-retning for mer elliptisk spredning (holder seg
        # naerere tavernaens vinduer/doer enn rett opp i himmelen).
        p.base_y = self._tavern_cy + math.sin(angle) * radius * 0.5
        p.amplitude = self._rng.uniform(3.0, 5.0)
        p.freq_x = self._rng.uniform(0.7, 1.3)
        p.freq_y = self._rng.uniform(0.5, 1.0)
        p.phase_x = self._rng.uniform(0.0, 2.0 * math.pi)
        p.phase_y = self._rng.uniform(0.0, 2.0 * math.pi)
        p.blink_phase = self._rng.uniform(0.0, 1.0)
        p.blink_period = self._rng.uniform(0.8, 1.2)
        p.life = self._rng.uniform(3.0, 5.0)
        # Initier posisjonen slik at den ikke blinker til base-punktet paa
        # frame 0.
        p.x = p.base_x
        p.y = p.base_y

    # --- Update ---

    def update(self, dt: float) -> None:
        self._elapsed += dt
        for p in self._particles:
            if p.kind == "fog":
                p.x += p.vx * dt
                if p.x > self._world_width + 40.0:
                    self._init_fog(p, spread=False)
            else:  # firefly
                p.life -= dt
                if p.life <= 0.0:
                    self._init_firefly(p)
                    continue
                t = self._elapsed
                p.x = p.base_x + p.amplitude * math.sin(
                    2.0 * math.pi * p.freq_x * t + p.phase_x
                )
                p.y = p.base_y + p.amplitude * math.sin(
                    2.0 * math.pi * p.freq_y * t + p.phase_y
                )

    # --- Rendering ---

    def draw(self, target: pygame.Surface, camera_x: float) -> None:
        """Tegn begge batcher. Kalleren bestemmer rekkefoelgen rundt dette.

        Taake tegnes foerst (alminnelig blit, colorkey). Ildfluer tegnes
        deretter med BLEND_RGB_ADD saa de stikker gjennom taaken.
        """
        cx = int(camera_x)
        fog_batch = self._fog_batch
        firefly_batch = self._firefly_batch
        fog_batch.clear()
        firefly_batch.clear()

        for p in self._particles:
            if p.kind == "fog":
                sprite = p.sprite
                if sprite is None:
                    continue
                fog_batch.append((sprite, (int(p.x) - cx, int(p.y))))
            else:
                # Blinkelogikk: synlig i 70% av syklusen, av i 30%
                phase = (self._elapsed / p.blink_period + p.blink_phase) % 1.0
                if phase > 0.7:
                    continue
                firefly_batch.append(
                    (self._firefly_sprite, (int(p.x) - cx, int(p.y)))
                )

        if fog_batch:
            target.fblits(fog_batch)
        if firefly_batch:
            target.fblits(firefly_batch, pygame.BLEND_RGB_ADD)
