"""Dag-natt-syklus.

Ren beregning: gitt en `GameClock`, returner en `DaySnapshot` som beskriver
visuell state (himmelfarge, sol/måne-posisjon og -farge, stjerne-alpha,
celestial-alpha for fading).

Designvalg:
- **Stateless**. `DayCycle.compute_snapshot()` er en ren funksjon av klokken.
- **Himmel-fase** (morning/day/night) er proporsjoner av dagen. Fase bruker
  `MORNING_FRAC` = 1/6 og `NIGHT_FRAC` = 1/6 av `seconds_per_day`.
- **Celestial-vinduer** er uavhengige av fase-grensene:
    - Moon window:  [0.00, 0.12) + [0.88, 1.00)   (wrapping over midnatt)
    - Sun window:   [0.17, 0.88)   (inkl. fade-out fra 0.80)
    - Gap window:   [0.12, 0.17)   (ingen celestial — tom himmel før daggry)
  Sun-fade fra 0.80 til 0.88 er samtidig med at moon-fade-in starter ved
  0.88 — solen når horisonten akkurat når månen begynner å stige.
- **Sol-farge 3-stegs**:
    - [0.17, 0.25): SUN_DAWN → SUN_DAY (varm innledning)
    - [0.25, 0.65): SUN_DAY (hvit midt på dagen, konstant)
    - [0.65, 0.88): SUN_DAY → SUN_DUSK (orange mot kvelden, over hele
      restperioden inkludert fade-out)
- **Sol-bane**: x linært 0.9 → 0.1, y parabolsk med y=0 ved både sunrise
  og sunset (f=0 og f=1), peak SUN_Y_NOON ved midt. Spannet er hele sol-
  vinduet [0.17, 0.88]; y når horisonten akkurat når alpha=0.
- **Moon fade**: måne fader ut [0.08, 0.12) og fader inn [0.88, 0.92).

Fase-oppdeling (for himmelfarge):

    0.0   ... 1/6    morning  — himmel lysner, stjerner fader ut
    1/6   ... 5/6    day      — dag-palett, glir mot skumring i andre halvdel
    5/6   ... 1.0    night    — skumring → natt i første halvdel, holdes resten
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import constants

if TYPE_CHECKING:
    from config.port_config import CelestialConfig
    from systems.game_clock import GameClock


#: Proporsjonell fase-oppdeling for himmelfarge.
MORNING_FRAC = 1.0 / 6.0
DAY_FRAC = 4.0 / 6.0
NIGHT_FRAC = 1.0 / 6.0
MORNING_END = MORNING_FRAC
DAY_END = MORNING_FRAC + DAY_FRAC

# --- Celestial-vinduer (review-spec) ---
#: Måne synlig på full styrke til og med denne fraksjonen (før morgen-fade).
MOON_FADE_OUT_START = 0.08
#: Måne ute av syne (alpha=0) fra og med denne fraksjonen.
MOON_FADE_OUT_END = 0.12
#: Sol begynner å være synlig (full alpha) fra og med denne fraksjonen.
SUN_VISIBLE_START = 0.17
#: Sol starter fade-out (alpha 1.0 → 0.0) fra og med denne fraksjonen.
#: Utvidet i Commit 7.1 fra 0.83 → 0.80 for glatt solnedgang (14 s i
#: stedet for 9 s på 180 s/dag).
SUN_FADE_OUT_START = 0.80
#: Sol fullt ute av syne (alpha=0) fra og med denne fraksjonen. Sol-
#: bevegelsen fortsetter helt til denne fraksjonen slik at solen når
#: horisonten (celestial_y=0) samtidig som alpha blir 0.
SUN_FADE_OUT_END = 0.88
#: Måne fader inn fra denne fraksjonen.
MOON_FADE_IN_START = 0.88
#: Måne på full styrke fra og med denne fraksjonen.
MOON_FADE_IN_END = 0.92

# --- Sol-farge-grenser (3-stegs) ---
SUN_COLOR_WARM_END = 0.25     # Slutt på varm innledning
SUN_COLOR_DUSK_START = 0.65   # Start på orange-glidning mot dusk

# --- Celestial y-fraksjoner (felles for alle havner) ---
#: Y-koordinater er universelle på tvers av havner — solens bue-topp og
#: månens høyde over horisonten er felles visuell språk. Kun x-
#: koordinater er per-havn og lever i `config.port_config.CelestialConfig`
#: (Fase 2B C3).
SUN_Y_NOON = 0.85  # Nær topp av himmelen (parabel-topp; endene er 0)
#: MOON_Y=0.65 gir screen_y ≈ 72, matcher originalen fra Fase 1.
MOON_Y = 0.65


@dataclass(frozen=True)
class DaySnapshot:
    """Visuell state for ett tidspunkt i døgnet.

    `celestial_x` er en verdens-koordinat (0.0–WORLD_WIDTH) slik at
    himmellegemene er forankret i scenen: månen står fast over Børshuset,
    solen reiser gjennom verden. `celestial_y` er en fraksjon (0.0 ved
    horisont, 1.0 ved topp av himmelen). Renderen beregner skjerm-x
    som `int(celestial_x - cam_x)`.
    `celestial_alpha` er 0.0 (sprite ikke synlig) til 1.0 (full styrke);
    brukt for fade inn/ut ved celestial-vindu-grensene.
    `star_alpha` er 0.0 (ingen stjerner) til 1.0 (full natt).
    `day_fraction` matcher `clock.progress_fraction()` (renderen bruker det
    til å velge backdrop-varianter for cross-fade).
    """

    phase: str  # "morning" | "day" | "night"
    sky_top_color: tuple[int, int, int]
    sky_horizon_color: tuple[int, int, int]
    celestial_x: float
    celestial_y: float
    celestial_color: tuple[int, int, int]
    celestial_is_sun: bool
    celestial_alpha: float
    star_alpha: float
    day_fraction: float


def _lerp_color(
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


def _lerp(a: float, b: float, t: float) -> float:
    if t <= 0.0:
        return a
    if t >= 1.0:
        return b
    return a * (1.0 - t) + b * t


# -----------------------------------------------------------------------------
# Himmel-farge (avhenger av fase)
# -----------------------------------------------------------------------------

def _morning_sky(
    f: float,
) -> tuple[tuple[int, int, int], tuple[int, int, int], float]:
    """Morgen-fase sky. `f` er 0.0 (start) til 1.0 (slutt).

    Sky interpolerer monotont fra natt-palett mot dag-palett.
    Stjerner fader ut lineært.
    """
    sky_top = _lerp_color(
        constants.COLOR_SKY_DEEP, constants.COLOR_SKY_DAY_TOP, f
    )
    sky_horizon = _lerp_color(
        constants.COLOR_SKY_HORIZON, constants.COLOR_SKY_DAY_HORIZON, f
    )
    return sky_top, sky_horizon, 1.0 - f


def _day_sky(
    f: float,
) -> tuple[tuple[int, int, int], tuple[int, int, int], float]:
    """Dag-fase sky. `f` er 0.0 (morgen slutt) til 1.0 (kveld starter).

    Første halvdel: ren dag-palett. Andre halvdel: glir mot skumring.
    Ingen stjerner.
    """
    if f < 0.5:
        return (
            constants.COLOR_SKY_DAY_TOP,
            constants.COLOR_SKY_DAY_HORIZON,
            0.0,
        )
    k = (f - 0.5) / 0.5
    sky_top = _lerp_color(
        constants.COLOR_SKY_DAY_TOP, constants.COLOR_SKY_DUSK_TOP, k
    )
    sky_horizon = _lerp_color(
        constants.COLOR_SKY_DAY_HORIZON, constants.COLOR_SKY_DUSK_HORIZON, k
    )
    return sky_top, sky_horizon, 0.0


def _night_sky(
    f: float,
) -> tuple[tuple[int, int, int], tuple[int, int, int], float]:
    """Natt-fase sky. `f` er 0.0 (kveld starter) til 1.0 (natt slutter).

    Første halvdel: skumring → natt (stjerner fader inn). Andre halvdel:
    fullt natt-palett.
    """
    if f < 0.5:
        k = f / 0.5
        sky_top = _lerp_color(
            constants.COLOR_SKY_DUSK_TOP, constants.COLOR_SKY_DEEP, k
        )
        sky_horizon = _lerp_color(
            constants.COLOR_SKY_DUSK_HORIZON, constants.COLOR_SKY_HORIZON, k
        )
        return sky_top, sky_horizon, k
    return (
        constants.COLOR_SKY_DEEP,
        constants.COLOR_SKY_HORIZON,
        1.0,
    )


# -----------------------------------------------------------------------------
# Celestial (uavhengig av fase — basert på global day_fraction)
# -----------------------------------------------------------------------------

def _celestial_for_fraction(
    t: float,
    celestial_config: "CelestialConfig",
) -> tuple[bool, float, float, tuple[int, int, int], float]:
    """Returner (is_sun, x, y, color, alpha) for global day_fraction t.

    `celestial_config` gir per-havn verdens-x for måne og sol (Fase 2B C3).

    Celestial-vinduer (review-spec):
    - [0.00, 0.08):         måne, full styrke
    - [0.08, 0.12):         måne, fading ut (1.0 → 0.0)
    - [0.12, 0.17):         ingen celestial (alpha=0)
    - [0.17, 0.83):         sol (farge og posisjon per _sun_state)
    - [0.83, 0.88):         ingen celestial (alpha=0)
    - [0.88, 0.92):         måne, fading inn (0.0 → 1.0)
    - [0.92, 1.00):         måne, full styrke
    """
    moon_x = float(celestial_config.moon_worldx)
    # Måne-vinduer først (wrap-around over midnatt)
    if t < MOON_FADE_OUT_START:
        # Full måne, første del av natten-etter-midnatt
        return False, moon_x, MOON_Y, constants.COLOR_MOON_CORE, 1.0

    if t < MOON_FADE_OUT_END:
        # Måne fader ut
        k = (t - MOON_FADE_OUT_START) / (
            MOON_FADE_OUT_END - MOON_FADE_OUT_START
        )
        return False, moon_x, MOON_Y, constants.COLOR_MOON_CORE, 1.0 - k

    if t < SUN_VISIBLE_START:
        # Gap mellom måne-set og sol-opp (ingen celestial synlig)
        return False, moon_x, MOON_Y, constants.COLOR_MOON_CORE, 0.0

    if t < SUN_FADE_OUT_START:
        # Sol synlig, full alpha
        is_sun, x, y, color = _sun_state(t, celestial_config)
        return is_sun, x, y, color, 1.0

    if t < SUN_FADE_OUT_END:
        # Sol synlig men fader ut. Posisjonen fortsetter å bevege seg
        # gjennom _sun_state slik at solen når horisonten (celestial_y=0)
        # samtidig som alpha blir 0 ved SUN_FADE_OUT_END. Visuelt: solen
        # setter seg gradvis i stedet for å "henge fast midt i lufta".
        k = (t - SUN_FADE_OUT_START) / (
            SUN_FADE_OUT_END - SUN_FADE_OUT_START
        )
        is_sun, x, y, color = _sun_state(t, celestial_config)
        return is_sun, x, y, color, 1.0 - k

    if t < MOON_FADE_IN_START:
        # Numerisk nesten-umulig (SUN_FADE_OUT_END == MOON_FADE_IN_START),
        # men defensivt: ingen celestial i denne micro-greinen.
        return False, moon_x, MOON_Y, constants.COLOR_MOON_CORE, 0.0

    if t < MOON_FADE_IN_END:
        # Måne fader inn
        k = (t - MOON_FADE_IN_START) / (
            MOON_FADE_IN_END - MOON_FADE_IN_START
        )
        return False, moon_x, MOON_Y, constants.COLOR_MOON_CORE, k

    # t in [MOON_FADE_IN_END, 1.0)
    return False, moon_x, MOON_Y, constants.COLOR_MOON_CORE, 1.0


def _sun_state(
    t: float,
    celestial_config: "CelestialConfig",
) -> tuple[bool, float, float, tuple[int, int, int]]:
    """Sol-posisjon og farge innenfor [SUN_VISIBLE_START, SUN_FADE_OUT_END).

    - Lineær x-bane i verdens-koordinater fra `celestial_config.sun_worldx_dawn`
      → `celestial_config.sun_worldx_dusk` over hele sol-vinduet (Commit 7.2;
      per-havn konfig fra C3).
    - Parabolsk y-bane: y = 4f(1-f) * SUN_Y_NOON. y=0 ved f=0 og f=1
      (sunrise og sunset rører horisonten), peak SUN_Y_NOON ved f=0.5.
    - 3-stegs farge (spenner hele sol-vinduet [0.17, 0.88]):
        [0.17, 0.25):            SUN_DAWN → SUN_DAY (varm innledning)
        [0.25, 0.65):            SUN_DAY (hvit midt på dagen, konstant)
        [0.65, SUN_FADE_OUT_END): SUN_DAY → SUN_DUSK (orange mot kvelden)
    """
    # Lineær sol-x fra per-havn dawn → dusk over hele sol-vinduet
    span = SUN_FADE_OUT_END - SUN_VISIBLE_START
    f = (t - SUN_VISIBLE_START) / span  # 0 at sunrise, 1 at sunset
    f = max(0.0, min(1.0, f))  # defensivt klamp
    x = _lerp(
        float(celestial_config.sun_worldx_dawn),
        float(celestial_config.sun_worldx_dusk),
        f,
    )
    # Parabolsk y: 4f(1-f) har topp 1.0 ved f=0.5, og 0.0 ved f=0 og f=1.
    # Solen rører altså horisonten både ved sunrise og sunset.
    parabola = 4.0 * f * (1.0 - f)
    y = SUN_Y_NOON * parabola

    # 3-stegs farge
    if t < SUN_COLOR_WARM_END:
        k = (t - SUN_VISIBLE_START) / (SUN_COLOR_WARM_END - SUN_VISIBLE_START)
        color = _lerp_color(
            constants.COLOR_SUN_DAWN, constants.COLOR_SUN_DAY, k
        )
    elif t < SUN_COLOR_DUSK_START:
        color = constants.COLOR_SUN_DAY
    else:
        # Dusk-interpolering spenner helt til SUN_FADE_OUT_END slik at
        # farge og alpha begge når SUN_DUSK / 0.0 samtidig.
        k = (t - SUN_COLOR_DUSK_START) / (
            SUN_FADE_OUT_END - SUN_COLOR_DUSK_START
        )
        k = min(1.0, k)
        color = _lerp_color(
            constants.COLOR_SUN_DAY, constants.COLOR_SUN_DUSK, k
        )

    return True, x, y, color


# -----------------------------------------------------------------------------
# Public API
# -----------------------------------------------------------------------------

class DayCycle:
    """Stateless beregner av visuell state fra klokke-posisjon."""

    MORNING_END_FRAC: float = MORNING_END
    DAY_END_FRAC: float = DAY_END

    @staticmethod
    def compute_snapshot(
        clock: "GameClock",
        celestial_config: "CelestialConfig",
    ) -> DaySnapshot:
        """Returner DaySnapshot for klokkens nåværende posisjon.

        `celestial_config` gir per-havn verdens-x for måne og sol (C3). Caller
        passer `port_config.get(current_port).celestial`.
        """
        t = clock.progress_fraction()

        # Himmel-farge (fase-basert)
        if t < MORNING_END:
            sky_top, sky_horizon, star_alpha = _morning_sky(t / MORNING_FRAC)
            phase = "morning"
        elif t < DAY_END:
            sky_top, sky_horizon, star_alpha = _day_sky(
                (t - MORNING_END) / DAY_FRAC
            )
            phase = "day"
        else:
            sky_top, sky_horizon, star_alpha = _night_sky(
                (t - DAY_END) / NIGHT_FRAC
            )
            phase = "night"

        # Celestial (global-fraksjon-basert, uavhengig av fase)
        (
            is_sun,
            cel_x,
            cel_y,
            cel_color,
            cel_alpha,
        ) = _celestial_for_fraction(t, celestial_config)

        return DaySnapshot(
            phase=phase,
            sky_top_color=sky_top,
            sky_horizon_color=sky_horizon,
            celestial_x=cel_x,
            celestial_y=cel_y,
            celestial_color=cel_color,
            celestial_is_sun=is_sun,
            celestial_alpha=cel_alpha,
            star_alpha=star_alpha,
            day_fraction=t,
        )
