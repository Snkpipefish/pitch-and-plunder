"""Havn-markør for verdenskart-scenen (Fase 2B C5).

14×14 sprite med ring + sentrum-prikk. Tre tilstander i C5:

- `current`: havnen spilleren er i nå. Varm LANTERN-familie,
  statisk alpha 1.0.
- `focused`: havnen brukeren navigerer mot med piltaster. Varm ring,
  lys MOON_CORE-sentrum med sinus-pulsering alpha[0.7, 1.0] over 1 sek.
- `other`: andre kjente havner. Kald STONE_LIT-familie, statisk.

`never_visited`-tilstand kommer i C8 sammen med observed-pris-logikk.

Per FASE_2B_VISUELL_REFERANSE.md §3. Markøren rendrer seg selv i
`draw()`; caller passer posisjon og tilstand per frame.
"""

from __future__ import annotations

import logging
import math

import pygame

import constants


log = logging.getLogger(__name__)


#: Størrelse i pixels (kvadrat).
MARKER_SIZE = 14

#: Colorkey for transparente pixler i marker-sprites.
COLORKEY = (255, 0, 255)

#: Pulserings-periode i sekunder for fokusert markør.
PULSE_PERIOD = 1.0

#: Alpha-grenser for pulsering.
PULSE_ALPHA_MIN = 0.7
PULSE_ALPHA_MAX = 1.0


def _build_marker_surface(
    ring_color: tuple[int, int, int],
    center_color: tuple[int, int, int],
) -> pygame.Surface:
    """Bygg en 14×14 colorkey-transparent marker-sprite.

    Mønster (ring 2px tykk, sentrum 2×2):

        ....##....
        .###..###.
        .#......#.
        .#......#.
        ##..oo..##
        ##..oo..##
        .#......#.
        .#......#.
        .###..###.
        ....##....

    Colorkey = magenta (samme som andre transparent-surfaces i spillet).
    """
    surf = pygame.Surface((MARKER_SIZE, MARKER_SIZE))
    surf.fill(COLORKEY)

    cx, cy = MARKER_SIZE // 2, MARKER_SIZE // 2
    outer_r = 6
    inner_r = 4

    # Ring: tegn en sirkel fylt med ring_color, så fyll indre med colorkey
    # for å få 2px ring-tykkelse.
    pygame.draw.circle(surf, ring_color, (cx, cy), outer_r)
    pygame.draw.circle(surf, COLORKEY, (cx, cy), inner_r)

    # Sentrum-prikk (2×2)
    pygame.draw.rect(surf, center_color, (cx - 1, cy - 1, 2, 2))

    surf.set_colorkey(COLORKEY)
    return surf.convert()


class PortMarker:
    """Ett markør-sett med pre-rendrede sprites for 4 tilstander.

    Deling: én PortMarker-instans per WorldMapScene, ikke én per havn.
    Scene velger riktig sprite per havn per frame.

    States (per VISUELL_REFERANSE §3 marker-tabellen):
    - current: LANTERN_BRIGHT ring + LANTERN senter (varm hjem)
    - focused: LANTERN ring + MOON_CORE senter (varm + pulserende lys)
    - other: STONE_LIT ring + STONE_DARK senter (kald institusjonell)
    - never_visited: FOG ring + STONE_DARKEST senter (dempet ukjent — C8)
    """

    def __init__(self) -> None:
        # Current: LANTERN_BRIGHT ring, LANTERN senter
        self._surf_current = _build_marker_surface(
            constants.COLOR_LANTERN_BRIGHT, constants.COLOR_LANTERN,
        )
        # Focused: LANTERN ring, MOON_CORE senter (lys kjerne)
        self._surf_focused = _build_marker_surface(
            constants.COLOR_LANTERN, constants.COLOR_MOON_CORE,
        )
        # Other: STONE_LIT ring, STONE_DARK senter
        self._surf_other = _build_marker_surface(
            constants.COLOR_STONE_LIT, constants.COLOR_STONE_DARK,
        )
        # Never visited: FOG ring, STONE_DARKEST senter (C8). Lav
        # kontrast mot mørk hav-bakgrunn — spilleren må "lete" for å
        # se den, tematisk forsvarer at ukjente steder er usynligere.
        self._surf_never_visited = _build_marker_surface(
            constants.COLOR_FOG, constants.COLOR_STONE_DARKEST,
        )
        #: Logget én gang ved første fallback slik at dev-mode viser at
        #: pulsering er skrudd av. Ikke spammer logg.
        self._pulse_fallback_logged: bool = False
        #: True når pulsering er deaktivert (benchmark-regresjon). Scene
        #: kan sette dette via `disable_pulse()` hvis <5 ms-budsjett
        #: brytes etter aktivering.
        self._pulse_disabled: bool = False

    @staticmethod
    def center_offset() -> int:
        """Returner offset fra markør-topp-venstre til senter (6)."""
        return MARKER_SIZE // 2

    def disable_pulse(self) -> None:
        """Skru av pulsering og logg en gang i dev-mode.

        Kalles av scene hvis benchmark indikerer at pulsering bryter
        5 ms-budsjettet på world_map. Ikke-stille fallback per direktiv.
        """
        if self._pulse_disabled:
            return
        self._pulse_disabled = True
        from systems.dev_mode import is_dev_mode
        if is_dev_mode() and not self._pulse_fallback_logged:
            log.info(
                "PortMarker: pulsering deaktivert (benchmark-fallback) — "
                "focused-markør tegnes med statisk alpha 1.0"
            )
            self._pulse_fallback_logged = True

    def draw(
        self,
        surface: pygame.Surface,
        center_pos: tuple[int, int],
        state: str,
        elapsed: float = 0.0,
    ) -> None:
        """Tegn markør med senter ved `center_pos`.

        `state` er "current", "focused" eller "other".
        `elapsed` er totale sekunder scenen har kjørt — brukt til
        pulsering av fokusert markør.
        """
        if state == "current":
            sprite = self._surf_current
            sprite.set_alpha(255)
        elif state == "focused":
            sprite = self._surf_focused
            if self._pulse_disabled:
                sprite.set_alpha(255)
            else:
                # Sinus-modulert alpha [0.7, 1.0] over PULSE_PERIOD
                phase = (2.0 * math.pi * elapsed) / PULSE_PERIOD
                alpha_frac = (
                    (PULSE_ALPHA_MIN + PULSE_ALPHA_MAX) / 2.0
                    + ((PULSE_ALPHA_MAX - PULSE_ALPHA_MIN) / 2.0)
                    * math.sin(phase)
                )
                sprite.set_alpha(int(alpha_frac * 255))
        elif state == "other":
            sprite = self._surf_other
            sprite.set_alpha(255)
        elif state == "never_visited":
            sprite = self._surf_never_visited
            sprite.set_alpha(255)
        else:
            return

        cx, cy = center_pos
        surface.blit(sprite, (cx - MARKER_SIZE // 2, cy - MARKER_SIZE // 2))
