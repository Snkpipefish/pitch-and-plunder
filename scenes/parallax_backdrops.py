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


def _bake_stars(
    surf: pygame.Surface,
    horizon_y: int,
    seed: int = 42,
    intensity: float = 1.0,
) -> None:
    """Streng stjerner i øvre del av himmelen (deterministisk via seed).

    `intensity` er 0.0 (ingen stjerner tegnet) til 1.0 (full lysstyrke).
    Mellomverdier interpolerer hver stjerne-farge mot himmel-fargen på sin
    posisjon, slik at stjernene fader inn/ut glatt mot bakgrunnen.
    """
    if intensity <= 0.0:
        return
    rng = random.Random(seed)
    width = surf.get_width()
    star_color = constants.COLOR_MOON_CORE
    for _ in range(14):
        x = rng.randint(4, width - 5)
        y = rng.randint(4, horizon_y - 30)
        radius = rng.choice([1, 1, 1, 2])
        if intensity >= 1.0:
            color = star_color
        else:
            # Lerp himmel-pixel mot stjerne-farge ved intensity.
            sky_pixel = surf.get_at((x, y))
            color = (
                int(sky_pixel[0] * (1.0 - intensity) + star_color[0] * intensity),
                int(sky_pixel[1] * (1.0 - intensity) + star_color[1] * intensity),
                int(sky_pixel[2] * (1.0 - intensity) + star_color[2] * intensity),
            )
        pygame.draw.circle(surf, color, (x, y), radius)


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


# -----------------------------------------------------------------------------
# Fase 2A Commit 5B: 6 pre-rendrede bakgrunnsvarianter for dag-natt-syklus.
# Brukes av VillageRenderer via cross-fade mellom de to nærmeste anker-
# fraksjonene basert på DaySnapshot.day_fraction. Celestial (sol/måne)
# rendres som separat overlay og IKKE bakt inn i noen variant.
# -----------------------------------------------------------------------------

#: Linja mellom himmel og hav (i intern RENDER_HEIGHT-skala). Samme formel
#: som brukes av den originale build_background_layer() for konsistens.
_HORIZON_Y_RATIO = 0.58


def _lerp_rgb(
    a: tuple[int, int, int],
    b: tuple[int, int, int],
    t: float,
) -> tuple[int, int, int]:
    if t <= 0.0:
        return a
    if t >= 1.0:
        return b
    return (
        int(a[0] * (1.0 - t) + b[0] * t),
        int(a[1] * (1.0 - t) + b[1] * t),
        int(a[2] * (1.0 - t) + b[2] * t),
    )


def _build_parameterized_sky(
    width: int,
    height: int,
    horizon_y: int,
    top_color: tuple[int, int, int],
    horizon_color: tuple[int, int, int],
    sea_color: tuple[int, int, int],
) -> pygame.Surface:
    """Lineær himmelgradient fra topp-farge til horisont-farge, og sjø nedenfor.

    Enklere enn `_build_sky_gradient` (som har to-trinns interpolasjon med
    fast palett). Her gis alle farger eksplisitt slik at hver backdrop-
    variant kan bruke sin egen palett.
    """
    surf = pygame.Surface((width, height)).convert()
    for y in range(horizon_y):
        t = y / horizon_y
        r = int(top_color[0] * (1 - t) + horizon_color[0] * t)
        g = int(top_color[1] * (1 - t) + horizon_color[1] * t)
        bl = int(top_color[2] * (1 - t) + horizon_color[2] * t)
        pygame.draw.line(surf, (r, g, bl), (0, y), (width - 1, y))
    pygame.draw.rect(
        surf, sea_color, (0, horizon_y, width, height - horizon_y)
    )
    return surf


def build_backdrop_variants() -> list[tuple[float, pygame.Surface]]:
    """Bygg 6 pre-rendrede bakgrunner for dag-natt-syklus.

    Returnerer en liste med `(day_fraction, surface)`-tupler sortert
    stigende på fraksjon. Anker-fraksjonene er valgt slik at hvert av
    de tre DayCycle-fasene (morgen, dag, natt) får tilstrekkelig
    sampling for cross-fade.

    Sol/måne er IKKE bakt inn i noen variant – rendring av himmellegeme
    gjøres av `entities.celestial.Celestial` som overlay.

    Anker-fraksjoner (samme navn som i spec):
    - 0.00 bg_000: midnatt, full stjerner
    - 0.08 bg_008: morgengry starter, full stjerner, antydning av varme
    - 0.17 bg_017: daggry fullført, stjerner halvveis ute
    - 0.50 bg_050: midt på dagen, ingen stjerner
    - 0.83 bg_083: solnedgang begynner, brennende horisont
    - 0.92 bg_092: solnedgang fullført, stjerner halvveis inn
    """
    speed = 0.2
    width = required_layer_width(
        constants.WORLD_WIDTH, constants.RENDER_WIDTH, speed
    )
    height = constants.RENDER_HEIGHT
    horizon_y = int(height * _HORIZON_Y_RATIO)

    # (fraction, top_color, horizon_color, sea_color, star_intensity, seed)
    # Seed holdes konstant på 42 slik at stjerne-posisjoner er identiske
    # på tvers av varianter – ellers ville cross-fade "flimre" stjernene.
    anchors: list[
        tuple[
            float,
            tuple[int, int, int],
            tuple[int, int, int],
            tuple[int, int, int],
            float,
        ]
    ] = [
        # 0.00 midnatt: natt-palett, full stjerner
        (
            0.00,
            constants.COLOR_SKY_DEEP,
            constants.COLOR_SKY_HORIZON,
            constants.COLOR_SEA_DEEP,
            1.0,
        ),
        # 0.08 morgengry starter: fortsatt mørkt men med varm antydning på
        # horisonten. Topp er lik mid-himmel, horisont er blanding av
        # natt-horisont og dag-horisont (20% mot dag).
        (
            0.08,
            constants.COLOR_SKY_MID,
            _lerp_rgb(
                constants.COLOR_SKY_HORIZON,
                constants.COLOR_SKY_DAY_HORIZON,
                0.2,
            ),
            constants.COLOR_SEA_DEEP,
            1.0,
        ),
        # 0.17 daggry fullført: klarblå dag-topp med varm peach-horisont.
        # Topp MÅ være klart lysere enn bg_008 for å unngå at morgen-
        # progresjonen ser ut som en "dip" (numerisk monoton, men
        # perseptuelt dunkel hvis STONE_LIGHT brukes). Kraftigere warm
        # tint på horisont (30% mot SUN_DAWN) gir tydelig daggry-feel.
        (
            0.17,
            constants.COLOR_SKY_DAY_TOP,
            _lerp_rgb(
                constants.COLOR_SKY_DAY_HORIZON,
                constants.COLOR_SUN_DAWN,
                0.3,
            ),
            constants.COLOR_SEA_MID,
            0.5,
        ),
        # 0.50 midt på dagen: full dag-palett, sjø lysere
        (
            0.50,
            constants.COLOR_SKY_DAY_TOP,
            constants.COLOR_SKY_DAY_HORIZON,
            constants.COLOR_SEA_LIGHT,
            0.0,
        ),
        # 0.83 solnedgang begynner: skumring, brennende horisont
        (
            0.83,
            constants.COLOR_SKY_DUSK_TOP,
            constants.COLOR_SKY_DUSK_HORIZON,
            constants.COLOR_SEA_MID,
            0.0,
        ),
        # 0.92 solnedgang fullført: mørkt med antydning av rødt i horisont
        (
            0.92,
            constants.COLOR_SKY_MID,
            _lerp_rgb(
                constants.COLOR_SKY_HORIZON,
                constants.COLOR_SKY_DUSK_HORIZON,
                0.3,
            ),
            constants.COLOR_SEA_DEEP,
            0.5,
        ),
    ]

    variants: list[tuple[float, pygame.Surface]] = []
    for frac, top_c, horizon_c, sea_c, star_intensity in anchors:
        surf = _build_parameterized_sky(
            width, height, horizon_y, top_c, horizon_c, sea_c
        )
        _bake_stars(surf, horizon_y, intensity=star_intensity)
        _bake_distant_islands(surf, horizon_y)
        variants.append((frac, surf))
    return variants
