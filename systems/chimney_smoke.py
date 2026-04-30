"""Drivende røyk fra Tortuga-essen, skorsteiner, bål osv.

Adresserer "mer liv i havnene" (v2.7): hver havn har 1-3 statiske røyk-
kilder som kontinuerlig sender opp røyksøyler. Røyken drifter oppover med
liten sideveis-wind og fader ut over levetiden.

Designvalg:

- **Object pool.** Hver kilde har et fast pool på 5 partikler; ingen alloc
  i `update`/`draw`. Total budsjett: 4 havner × 3 kilder × 5 partikler = 60
  worst-case (innenfor 150-partikkel-budsjettet i v2.7).
- **Pre-rendrede sprites.** 3 størrelser (4×3, 6×4, 8×5) som veksler med
  alder slik at røyken vokser etter hvert som den stiger.
- **Additiv blending.** Som tåke-systemet — gir naturlig stabling der
  røyk-strømmer møtes og en varm tone der røyk passerer foran lyskilder.
- **Lys-gating valgfritt.** Bål (Nassau-type) brenner 24/7. Skorsteiner
  (vanntank, tavern) kan røyke bare om kvelden hvis ønsket; for enkelhet
  i v2.7 røyker alle 24/7 med litt redusert intensitet om natten.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass

import pygame

import constants


_CK = (255, 0, 255)


def _build_smoke_sprites() -> list[pygame.Surface]:
    """Tre vekselvise størrelser: ung (smal) → moden (stor og diffus).

    Hver sprite er på svart bakgrunn med fyll i en dempet kald-grå
    additivt-bidrag — gir en "avkjølt røyk"-tone som passer paletten.
    """
    sizes = [(4, 3), (6, 4), (8, 5)]
    additive = (28, 28, 36)  # liten kald-grå additiv
    sprites: list[pygame.Surface] = []
    for w, h in sizes:
        s = pygame.Surface((w, h)).convert()
        s.fill((0, 0, 0))
        # Sentral klump
        pygame.draw.ellipse(s, additive, (0, 0, w, h))
        sprites.append(s)
    return sprites


def _build_warm_smoke_sprites() -> list[pygame.Surface]:
    """Variant for varm røyk (bål, smie). Legger til en nedre varm aksent."""
    sizes = [(4, 3), (6, 4), (8, 5)]
    cold = (24, 24, 32)
    warm = (38, 22, 14)  # subtil varm rødbrun additiv
    sprites: list[pygame.Surface] = []
    for w, h in sizes:
        s = pygame.Surface((w, h)).convert()
        s.fill((0, 0, 0))
        pygame.draw.ellipse(s, cold, (0, 0, w, h))
        # Nedre varm halv-ellipse antyder brennende kilde rett under
        pygame.draw.ellipse(s, warm, (1, max(0, h - 2), w - 2, 2))
        sprites.append(s)
    return sprites


@dataclass
class SmokeSource:
    """En statisk røyk-kilde i verden-koordinater.

    `kind`: "warm" (bål, smie) eller "cool" (skorstein, lommer).
    `period`: sekunder mellom partikkel-spawns. Lavere = tettere røyk.
    """
    x: float
    y: float
    kind: str = "cool"
    period: float = 0.45
    pool_size: int = 5
    drift_x: float = 4.0      # px/sek sideveis (positiv = mot høyre)
    rise_speed: float = 14.0  # px/sek opp


@dataclass
class _SmokeParticle:
    x: float = 0.0
    y: float = 0.0
    vy: float = 0.0
    vx: float = 0.0
    age: float = 0.0
    lifetime: float = 0.0    # 0 = inaktiv
    size_idx: int = 0
    source_idx: int = 0


def _make_default_sources_for_port(port_id: str) -> list[SmokeSource]:
    """Per-havn røyk-kilder. Posisjoner basert på pre-eksisterende layouts.

    Disse er bevisst kalibrert etter typiske havne-coordinater:
    - Tortuga: smie/esse rundt x=300, tavern-pipe rundt x=220
    - Port Royal: customs-skorstein rundt x=550
    - Havana: bakeri/tavernpipe rundt x=400, katedral-røkelse rundt x=900
    - Nassau: bål rundt x=650 (varm)
    """
    # Fase 2.6: posisjoner re-kalibrert mot faktiske bygnings-koordinater
    # i data/ports.json (etter Y-skalering 360→270). Hver kilde plasseres
    # ved chimney/skorstein-toppen til den respektive bygningen.
    if port_id == "tortuga":
        # Tavern: x=20, w=200 (chimney på høyre side). y_top=194 etter
        # migrering; røyk-kilde rett over taket.
        # Smithy: x=890, w=70, h=42 (esse i midten). y_top=ground-h=255-42=213.
        return [
            SmokeSource(x=920, y=210, kind="warm", period=0.32,
                        drift_x=4.0, rise_speed=18.0),  # smie-esse
            SmokeSource(x=185, y=190, kind="cool", period=0.55,
                        drift_x=3.0, rise_speed=14.0),  # tavern-pipe
        ]
    if port_id == "port_royal":
        return [
            SmokeSource(x=420, y=150, kind="cool", period=0.50,
                        drift_x=2.5, rise_speed=15.0),  # customs
            SmokeSource(x=620, y=160, kind="cool", period=0.65,
                        drift_x=2.0, rise_speed=13.0),  # exchange-pipe
        ]
    if port_id == "havana":
        return [
            SmokeSource(x=300, y=160, kind="warm", period=0.45,
                        drift_x=3.0, rise_speed=15.0),  # bakeri
            SmokeSource(x=680, y=145, kind="cool", period=0.80,
                        drift_x=1.5, rise_speed=10.0),  # katedral-røkelse
        ]
    if port_id == "nassau":
        return [
            SmokeSource(x=490, y=185, kind="warm", period=0.30,
                        drift_x=5.0, rise_speed=20.0),  # bål
            SmokeSource(x=240, y=170, kind="cool", period=0.55,
                        drift_x=3.5, rise_speed=14.0),  # shack-pipe
        ]
    return []


class ChimneySmoke:
    """Manager for alle røyk-kilder i en havn.

    Hver kilde eier en pool. Update advarer alder/posisjon, recycler
    døde partikler, og spawner nye etter `period`. Draw bygger to fblits-
    batcher (warm + cool) per frame.
    """

    def __init__(self, sources: list[SmokeSource], seed: int = 13) -> None:
        self._sources = sources
        self._cool_sprites = _build_smoke_sprites()
        self._warm_sprites = _build_warm_smoke_sprites()
        self._rng = random.Random(seed)
        # Pool — flat array; (source_idx, i) bestemmer plassering.
        self._particles: list[_SmokeParticle] = []
        self._spawn_timers: list[float] = []
        for i, src in enumerate(sources):
            self._spawn_timers.append(self._rng.uniform(0, src.period))
            for _ in range(src.pool_size):
                p = _SmokeParticle(source_idx=i)
                self._particles.append(p)
        # Recyclables
        self._cool_batch: list[tuple[pygame.Surface, tuple[int, int]]] = []
        self._warm_batch: list[tuple[pygame.Surface, tuple[int, int]]] = []

    def set_source_position(self, idx: int, x: float, y: float) -> None:
        """Flytt en eksisterende kilde — for skip-trail og andre dynamiske
        kilder. Påvirker kun spawn-pos for NYE partikler; eksisterende
        partikler blir der de er og driver ut etter sin lifetime."""
        if 0 <= idx < len(self._sources):
            src = self._sources[idx]
            src.x = float(x)
            src.y = float(y)

    def _spawn_particle(self, src_idx: int) -> None:
        """Aktiver en ledig partikkel for kilden."""
        for p in self._particles:
            if p.source_idx == src_idx and p.lifetime <= 0.0:
                src = self._sources[src_idx]
                # Litt jitter i spawn-pos så røyken ikke kommer fra én piksel
                p.x = src.x + self._rng.uniform(-1.5, 1.5)
                p.y = src.y
                p.vy = -src.rise_speed * self._rng.uniform(0.85, 1.15)
                p.vx = src.drift_x * self._rng.uniform(-0.6, 1.4)
                p.age = 0.0
                p.lifetime = self._rng.uniform(2.4, 3.5)
                p.size_idx = 0
                return

    def update(self, dt: float, night_factor: float = 0.0) -> None:
        """Oppdater alle partikler. `night_factor` reduserer spawn-rate
        litt om natten, men røyken slutter aldri (varme kilder brenner alltid)."""
        spawn_mult = 1.0 - 0.2 * night_factor  # 1.0 dag, 0.8 natt
        for i, src in enumerate(self._sources):
            self._spawn_timers[i] -= dt * spawn_mult
            if self._spawn_timers[i] <= 0.0:
                self._spawn_timers[i] = src.period
                self._spawn_particle(i)

        for p in self._particles:
            if p.lifetime <= 0.0:
                continue
            p.age += dt
            if p.age >= p.lifetime:
                p.lifetime = 0.0
                continue
            p.x += p.vx * dt
            p.y += p.vy * dt
            # Aksellerer oppstigning litt over tid (røyk blir lettere)
            p.vy *= 1.0 + 0.2 * dt
            p.vx *= 1.0 - 0.5 * dt   # demp sideveis-drift
            # Veks i størrelse-indeks med alder (0 → 1 → 2)
            t = p.age / max(1e-3, p.lifetime)
            if t < 0.33:
                p.size_idx = 0
            elif t < 0.66:
                p.size_idx = 1
            else:
                p.size_idx = 2

    def draw(self, surface: pygame.Surface, camera_x: float) -> None:
        cx = int(camera_x)
        cool = self._cool_batch
        warm = self._warm_batch
        cool.clear()
        warm.clear()
        screen_w = surface.get_width()
        for p in self._particles:
            if p.lifetime <= 0.0:
                continue
            sx = int(p.x) - cx
            sy = int(p.y)
            if sx < -16 or sx > screen_w + 16:
                continue
            src = self._sources[p.source_idx]
            sprites = self._warm_sprites if src.kind == "warm" else self._cool_sprites
            # Eldre partikler tegnes svakere ved å hoppe over noen frames
            # basert på age_t (poor man's alpha-fade for additive surfaces).
            t = p.age / max(1e-3, p.lifetime)
            if t > 0.85 and (p.age * 12.0) % 2.0 < 1.0:
                continue
            sprite = sprites[min(p.size_idx, len(sprites) - 1)]
            if src.kind == "warm":
                warm.append((sprite, (sx, sy)))
            else:
                cool.append((sprite, (sx, sy)))
        if cool:
            surface.fblits(cool, pygame.BLEND_RGB_ADD)
        if warm:
            surface.fblits(warm, pygame.BLEND_RGB_ADD)


def make_default_for_port(port_id: str) -> ChimneySmoke:
    return ChimneySmoke(_make_default_sources_for_port(port_id))
