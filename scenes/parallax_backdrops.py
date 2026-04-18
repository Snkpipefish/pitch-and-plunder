"""Pre-render-hjelpere for parallax-bakgrunn og tomme lag.

Trekket ut av `scenes/parallax_test.py` i Fase 2A / Commit 1 for å bryte den
skjeve import-relasjonen der produksjons-scenen `VillageScene` hentet bygge-
funksjoner fra en test-scene. Begge scener importerer nå fra denne modulen.

Alle funksjoner her er rene bake-hjelpere som kalles én gang ved scene-
innlasting. Ingen state, ingen per-frame-arbeid.
"""

from __future__ import annotations

import random

import pygame

import constants
from systems.parallax import required_layer_width


#: Transparent colorkey-farge brukt for tomme parallax-lag.
_COLORKEY_MAGENTA = (255, 0, 255)


def _build_sky_gradient(width: int, height: int, horizon_y: int) -> pygame.Surface:
    """Vertikal gradient fra himmel-dyp topp til horisont, sjø-dyp nedenfor."""
    surf = pygame.Surface((width, height)).convert()
    # Himmel: interpoler i to trinn for en mykere overgang
    for y in range(horizon_y):
        t = y / horizon_y
        if t < 0.6:
            k = t / 0.6
            a, b = constants.COLOR_SKY_DEEP, constants.COLOR_SKY_MID
        else:
            k = (t - 0.6) / 0.4
            a, b = constants.COLOR_SKY_MID, constants.COLOR_SKY_HORIZON
        r = int(a[0] * (1 - k) + b[0] * k)
        g = int(a[1] * (1 - k) + b[1] * k)
        bl = int(a[2] * (1 - k) + b[2] * k)
        pygame.draw.line(surf, (r, g, bl), (0, y), (width - 1, y))
    # Sjø-bånd under horisonten – mørk indigo
    pygame.draw.rect(
        surf,
        constants.COLOR_SEA_DEEP,
        (0, horizon_y, width, height - horizon_y),
    )
    return surf


def _bake_stars(surf: pygame.Surface, horizon_y: int, seed: int = 42) -> None:
    """Streng stjerner i øvre del av himmelen (deterministisk via seed)."""
    rng = random.Random(seed)
    width = surf.get_width()
    for _ in range(14):
        x = rng.randint(4, width - 5)
        y = rng.randint(4, horizon_y - 30)
        radius = rng.choice([1, 1, 1, 2])
        pygame.draw.circle(surf, constants.COLOR_MOON_CORE, (x, y), radius)


def _bake_distant_islands(surf: pygame.Surface, horizon_y: int) -> None:
    """Bølget silhuett som antyder fjerne øyer rett over horisontlinjen."""
    width = surf.get_width()
    # Lag en bølget polygon i mørk stein-tone
    points = [(0, horizon_y)]
    x = 0
    rng = random.Random(7)
    while x <= width:
        x += rng.randint(40, 90)
        dip = rng.randint(-14, -4)  # opp over horisonten
        points.append((min(x, width), horizon_y + dip))
    points.append((width, horizon_y))
    points.append((width, horizon_y + 6))
    points.append((0, horizon_y + 6))
    pygame.draw.polygon(surf, constants.COLOR_STONE_DARKEST, points)


def _sky_color_at(y: int, height: int) -> tuple[int, int, int]:
    """Returner bakgrunns-himmelfargen ved en gitt y i samme gradient som
    `_build_sky_gradient` lager (himmel-over-horisont)."""
    horizon_y = int(height * 0.58)
    if y >= horizon_y:
        return constants.COLOR_SEA_DEEP
    t = y / horizon_y
    if t < 0.6:
        k = t / 0.6
        a, b = constants.COLOR_SKY_DEEP, constants.COLOR_SKY_MID
    else:
        k = (t - 0.6) / 0.4
        a, b = constants.COLOR_SKY_MID, constants.COLOR_SKY_HORIZON
    return (
        int(a[0] * (1 - k) + b[0] * k),
        int(a[1] * (1 - k) + b[1] * k),
        int(a[2] * (1 - k) + b[2] * k),
    )


def _smoothstep(t: float) -> float:
    """3*t^2 - 2*t^3 — myk S-kurve uten knekk i endepunkter."""
    if t <= 0.0:
        return 0.0
    if t >= 1.0:
        return 1.0
    return t * t * (3.0 - 2.0 * t)


def _lerp_color(
    a: tuple[int, int, int], b: tuple[int, int, int], t: float
) -> tuple[int, int, int]:
    return (
        int(a[0] * (1.0 - t) + b[0] * t),
        int(a[1] * (1.0 - t) + b[1] * t),
        int(a[2] * (1.0 - t) + b[2] * t),
    )


def _bake_moon(
    surf: pygame.Surface, cx: int, cy: int, bg_height: int
) -> None:
    """Bak mane som en skarp skive med subtil halo.

    Kjerne: solid COLOR_MOON_CORE diameter ~28 px (radius 14). Ingen intern
    gradient – den skal fremstaa som en klar avgrenset skive, slik en
    mane paa nattehimmel gjoer.

    Halo: subtil antydning rundt kjernen, ikke en dominerende gloed. Fra
    kjernekanten (r=14) ut til r=30 interpoleres himmel-fargen mot
    COLOR_MOON_HALO med topp-blanding paa 40% ved kjernekanten og 0% ved
    r=30. Bruker smoothstep for myk avfasing uten synlige ringer.

    Referanse: `references/tortuga_signature_scene.svg` — skarp kjerne,
    diskret halo.
    """
    sky_bg = _sky_color_at(cy, bg_height)
    halo_color = constants.COLOR_MOON_HALO
    core_color = constants.COLOR_MOON_CORE

    core_r = 14       # Diameter 28 px
    halo_max_r = 30   # Halo strekker seg kun ca. 16 px utenfor kjernen
    max_halo_blend = 0.40  # Sterkeste halo-innblanding = 40% av halo_color

    # Halo: fra halo_max_r (0% innblanding) til core_r (40% innblanding).
    # Ved halo_max_r settes fargen til sky_bg (usynlig mot himmelen), saa
    # det er ingen skarp ytterring.
    for r in range(halo_max_r, core_r, -1):
        t = (halo_max_r - r) / (halo_max_r - core_r)
        t = _smoothstep(t) * max_halo_blend
        pygame.draw.circle(
            surf, _lerp_color(sky_bg, halo_color, t), (cx, cy), r
        )

    # Kjerne: solid MOON_CORE, ingen gradient. Skarp kant mot halo.
    pygame.draw.circle(surf, core_color, (cx, cy), core_r)

    # Et par diskrete krater-prikker i halo-fargen (maa ikke overvelde kjernen)
    pygame.draw.circle(surf, halo_color, (cx + 3, cy - 3), 1)
    pygame.draw.circle(surf, halo_color, (cx - 3, cy + 2), 1)


def build_background_layer() -> pygame.Surface:
    """Pre-render hele bakgrunnslaget (sky + måne + stjerner + øyer)."""
    speed = 0.2
    width = required_layer_width(constants.WORLD_WIDTH, constants.RENDER_WIDTH, speed)
    height = constants.RENDER_HEIGHT
    horizon_y = int(height * 0.58)  # ≈ 209 (matcher SVG-referansens horisont)

    surf = _build_sky_gradient(width, height, horizon_y)
    _bake_stars(surf, horizon_y, seed=42)
    _bake_distant_islands(surf, horizon_y)
    # Maanen plasseres paa bakgrunnslaget slik at den "hoerer til" Boershuset:
    # ved camera_x=0 (tavernaen) er maanen off-screen hoeyre; ved camera_x=960
    # (Boershuset) havner den rett over Boershuset paa skjermen. Se utregning
    # i kommentar under. Konkret: bg-layer-x=720 gir screen_x=720 ved cam=0
    # (off-screen), 624 ved cam=480 (ved hoeyrekanten), 528 ved cam=960 (rett
    # over Boershuset som okkuperer screen 420..620).
    moon_cx = 720
    moon_cy = 72
    _bake_moon(surf, moon_cx, moon_cy, height)
    return surf


def build_empty_layer(speed: float) -> pygame.Surface:
    """Tom, transparent surface på riktig bredde for lagets parallax-speed."""
    width = required_layer_width(constants.WORLD_WIDTH, constants.RENDER_WIDTH, speed)
    surf = pygame.Surface((width, constants.RENDER_HEIGHT)).convert()
    surf.fill(_COLORKEY_MAGENTA)
    surf.set_colorkey(_COLORKEY_MAGENTA)
    return surf
