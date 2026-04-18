"""Dag-natt-syklus.

Ren beregning: gitt en `GameClock`, returner en `DaySnapshot` som beskriver
visuell state (himmelfarge, sol/måne-posisjon og -farge, stjerne-alpha).
Renderen tar snapshotten og tegner scenen deretter.

Designvalg:
- **Stateless**. `DayCycle.compute_snapshot()` er en ren funksjon av klokken.
  Scene/renderer sporer selv om fasen har skiftet (f.eks. via forrige snapshot
  eller via clock-events). Holder systemet testbart uten fixtures.
- **Proporsjoner, ikke absolutte sekunder**. Fase-lengder er brøker av
  `clock.seconds_per_day` slik at endring av dag-lengde (f.eks. Commit 8
  polish eller tester med akselerert tid) automatisk skalerer fasene.
- **Paletten er låst** til farger i `constants.py` (30-paletten i PROSJEKT.md).
  Interpolering skjer kun mellom disse ankerfargene, ikke mot vilkårlige RGB.

Fase-oppdeling (brøker av én dag):

    0.0    ... 1/6    morning  — himmel lysner, sol stiger fra høyre
    1/6    ... 5/6    day      — sol beveger seg over himmelen mot venstre
    5/6    ... 1.0    night    — mørk indigo, måne på venstre side,
                                 stjerner synlige

Spec-verdier (ved seconds_per_day = 180): morning 30 s, day 120 s, night 30 s.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import constants

if TYPE_CHECKING:
    from systems.game_clock import GameClock


#: Proporsjonell fase-oppdeling. Summerer til 1.0.
MORNING_FRAC = 1.0 / 6.0
DAY_FRAC = 4.0 / 6.0
NIGHT_FRAC = 1.0 / 6.0

#: Kumulative fase-grenser (dag-brøk).
MORNING_END = MORNING_FRAC                       # 0.1667
DAY_END = MORNING_FRAC + DAY_FRAC                # 0.8333
# NIGHT_END = 1.0 (implisitt)

#: Sol-bane (x,y-fraksjoner av skjerm-bredde/høyde-område). Sol står opp i
#: høyre kant av skjermen, buer til venstre over hele dagen, går ned til
#: venstre ved kveld. Y er målt fra horisont-toppen: 1.0 = høyt på himmelen,
#: 0.1 = like over horisonten.
SUN_X_DAWN = 0.9
SUN_X_NOON = 0.5
SUN_X_DUSK = 0.1
SUN_Y_DAWN = 0.15
SUN_Y_NOON = 0.85
SUN_Y_DUSK = 0.15

#: Måne-plassering (konstant). Tematisk hører månen til Børshuset; posisjonen
#: matcher nåværende statiske måne (over børshuset på skjermen).
MOON_X = 0.75
MOON_Y = 0.25


@dataclass(frozen=True)
class DaySnapshot:
    """Visuell state for ett tidspunkt i døgnet.

    `celestial_x` og `celestial_y` er skjerm-relative fraksjoner (0.0–1.0).
    Renderen skalerer mot faktisk skjerm-geometri.
    `star_alpha` er 0.0 (ingen stjerner synlig) til 1.0 (full natt).
    """

    phase: str  # "morning" | "day" | "night"
    sky_top_color: tuple[int, int, int]
    sky_horizon_color: tuple[int, int, int]
    celestial_x: float
    celestial_y: float
    celestial_color: tuple[int, int, int]
    celestial_is_sun: bool
    star_alpha: float


def _lerp_color(
    a: tuple[int, int, int],
    b: tuple[int, int, int],
    t: float,
) -> tuple[int, int, int]:
    """Lineær interpolering mellom to RGB-tripler. t klampes til [0, 1]."""
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


class DayCycle:
    """Stateless beregner av visuell state fra klokke-posisjon."""

    # Fase-grenser eksponert som klasse-konstanter slik at tester kan lese
    # dem uten å duplikere magic numbers.
    MORNING_END_FRAC: float = MORNING_END
    DAY_END_FRAC: float = DAY_END

    @staticmethod
    def compute_snapshot(clock: "GameClock") -> DaySnapshot:
        """Returner DaySnapshot for klokkens nåværende posisjon.

        Bruker `clock.progress_fraction()` som input; tåler alle gyldige
        klokke-tilstander (inkl. degenerated seconds_per_day=0 fra clock-
        default-factory).
        """
        t = clock.progress_fraction()

        if t < MORNING_END:
            return _morning_snapshot(t / MORNING_FRAC)
        if t < DAY_END:
            return _day_snapshot((t - MORNING_END) / DAY_FRAC)
        return _night_snapshot((t - DAY_END) / NIGHT_FRAC)


def _morning_snapshot(f: float) -> DaySnapshot:
    """Morgenfase. `f` er 0.0 (daggry start) til 1.0 (morgen slutter).

    Himmelen glir fra natt-palett til dag-palett. Solen står opp fra høyre,
    stjernene fader ut.
    """
    sky_top = _lerp_color(
        constants.COLOR_SKY_DEEP, constants.COLOR_SKY_DAY_TOP, f
    )
    sky_horizon = _lerp_color(
        constants.COLOR_SKY_HORIZON, constants.COLOR_SKY_DAY_HORIZON, f
    )
    # Sol-farge: varm daggry → mot hvit middag
    celestial_color = _lerp_color(
        constants.COLOR_SUN_DAWN, constants.COLOR_SUN_DAY, f
    )
    celestial_x = _lerp(SUN_X_DAWN, SUN_X_DAWN - 0.1, f)  # 0.9 → 0.8
    celestial_y = _lerp(SUN_Y_DAWN, SUN_Y_DAWN + 0.25, f)  # 0.15 → 0.4
    return DaySnapshot(
        phase="morning",
        sky_top_color=sky_top,
        sky_horizon_color=sky_horizon,
        celestial_x=celestial_x,
        celestial_y=celestial_y,
        celestial_color=celestial_color,
        celestial_is_sun=True,
        star_alpha=1.0 - f,
    )


def _day_snapshot(f: float) -> DaySnapshot:
    """Dagfase. `f` er 0.0 (morgen slutt) til 1.0 (kveld starter).

    Himmelen går fra dag-palett mot skumring. Solen buer over himmelen
    fra 0.8 → 0.5 → 0.2 i x, med parabolsk y (høyest ved f=0.5).
    """
    # Himmel: dag-palett i første halvdel, glir mot skumring i andre halvdel
    if f < 0.5:
        # Ingen merkbar endring innen første halvdel; holder dag-palett
        sky_top = constants.COLOR_SKY_DAY_TOP
        sky_horizon = constants.COLOR_SKY_DAY_HORIZON
    else:
        # Andre halvdel: glir fra dag mot skumring
        k = (f - 0.5) / 0.5
        sky_top = _lerp_color(
            constants.COLOR_SKY_DAY_TOP, constants.COLOR_SKY_DUSK_TOP, k
        )
        sky_horizon = _lerp_color(
            constants.COLOR_SKY_DAY_HORIZON, constants.COLOR_SKY_DUSK_HORIZON, k
        )

    # Sol-farge: hvit middag → brennende kveld (lineært gjennom dagen)
    celestial_color = _lerp_color(
        constants.COLOR_SUN_DAY, constants.COLOR_SUN_DUSK, f
    )

    # Sol-x: lineært fra 0.8 til 0.2 over hele dagfasen
    celestial_x = _lerp(SUN_X_NOON + 0.3, SUN_X_NOON - 0.3, f)

    # Sol-y: parabel med topp ved f=0.5. y = y_low + (y_high - y_low) * 4f(1-f)
    parabola = 4.0 * f * (1.0 - f)
    celestial_y = SUN_Y_DAWN + (SUN_Y_NOON - SUN_Y_DAWN) * parabola

    return DaySnapshot(
        phase="day",
        sky_top_color=sky_top,
        sky_horizon_color=sky_horizon,
        celestial_x=celestial_x,
        celestial_y=celestial_y,
        celestial_color=celestial_color,
        celestial_is_sun=True,
        star_alpha=0.0,
    )


def _night_snapshot(f: float) -> DaySnapshot:
    """Nattfase. `f` er 0.0 (kveld starter) til 1.0 (natt slutter).

    Himmelen glir fra skumring til full natt i første halvdel, holdes i
    natt-palett resten av nattfasen. Månen er på plass over Børshuset.
    Stjernene fader inn i første halvdel.
    """
    # Første halvdel av natten: skumring → full natt. Andre halvdel: holdes.
    if f < 0.5:
        k = f / 0.5
        sky_top = _lerp_color(
            constants.COLOR_SKY_DUSK_TOP, constants.COLOR_SKY_DEEP, k
        )
        sky_horizon = _lerp_color(
            constants.COLOR_SKY_DUSK_HORIZON, constants.COLOR_SKY_HORIZON, k
        )
        star_alpha = k
    else:
        sky_top = constants.COLOR_SKY_DEEP
        sky_horizon = constants.COLOR_SKY_HORIZON
        star_alpha = 1.0

    return DaySnapshot(
        phase="night",
        sky_top_color=sky_top,
        sky_horizon_color=sky_horizon,
        celestial_x=MOON_X,
        celestial_y=MOON_Y,
        celestial_color=constants.COLOR_MOON_CORE,
        celestial_is_sun=False,
        star_alpha=star_alpha,
    )
