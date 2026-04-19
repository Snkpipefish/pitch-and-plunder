"""Skip-sprite for verdenskart-scenen (Fase 2B C5).

12×12 rent top-down (fugleperspektiv) per
FASE_2B_VISUELL_REFERANSE.md §4. Fire orienteringer (N, S, Ø, V).

Implementasjon: 2 unike pre-renderinger (N og Ø) + 2 symmetri-flips
(S fra N via vertical flip, V fra Ø via horizontal flip). Denne
reduksjonen er mulig fordi ship-formen har bilateral symmetri om
lengde-aksen — mast sentrert, seil symmetriske.

Hvis visuell verifisering viser at flip-produkter ikke ser riktige
ut (asymmetri i seil, mast ikke sentrert), rull tilbake til 4 separate
pre-renderinger. `verify_flip_symmetry()` gir automatisert sjekk.
"""

from __future__ import annotations

import pygame

import constants


#: Sprite-størrelse (kvadrat).
SHIP_SIZE = 12

#: Colorkey for transparens.
COLORKEY = (255, 0, 255)


# -----------------------------------------------------------------------------
# Pre-render-mønstre (compact string-form for lesbarhet)
# -----------------------------------------------------------------------------
#   .  = transparent (colorkey)
#   H  = skrog (COLOR_WOOD_LIGHT)
#   S  = seil (COLOR_SHIRT)
#
# N-orientering: baug topp, seil horisontalt utvidet fra mast-linje,
# skrog smalner mot prow. 12×12.

_NORTH_PATTERN = [
    ".....HH.....",  # mast-topp (baug)
    ".....HH.....",
    "....SSSS....",  # seil start
    "...SHHHHS...",
    "..SHHHHHHS..",
    "..SHHHHHHS..",  # vidden av seil
    "...SHHHHS...",
    "....SSSS....",  # seil slutt
    ".....HH.....",  # skrog smalnet
    ".....HH.....",
    ".....HH.....",
    ".....HH.....",  # akter
]

# Ø-orientering: baug høyre. Hull er horisontalt, seil vertikalt
# utvidet (90° rotert konseptuelt, men dokumentet eksplisitt forbyr
# sprite-rotate for alle retninger — vi pre-renderer denne som unik
# variant).
#
# Bilateral symmetri om horizontal-aksen: topp-halv speiler bunn-halv.

_EAST_PATTERN = [
    "............",
    ".....S......",
    "....SS......",
    "...SSSS.....",
    "..SSHHHHHH..",  # seil topp, skrog midt
    ".HHHHHHHHHH.",  # akter til venstre, baug til høyre
    ".HHHHHHHHHH.",
    "..SSHHHHHH..",  # seil bunn
    "...SSSS.....",
    "....SS......",
    ".....S......",
    "............",
]


def _render_pattern(pattern: list[str]) -> pygame.Surface:
    """Render en pattern-streng til en colorkey-surface."""
    assert len(pattern) == SHIP_SIZE, f"Pattern må være {SHIP_SIZE} rader"
    assert all(len(row) == SHIP_SIZE for row in pattern), (
        f"Hver rad må være {SHIP_SIZE} kolonner"
    )
    surf = pygame.Surface((SHIP_SIZE, SHIP_SIZE))
    surf.fill(COLORKEY)
    for y, row in enumerate(pattern):
        for x, ch in enumerate(row):
            if ch == "H":
                surf.set_at((x, y), constants.COLOR_WOOD_LIGHT)
            elif ch == "S":
                surf.set_at((x, y), constants.COLOR_SHIRT)
            # "." forblir colorkey
    surf.set_colorkey(COLORKEY)
    return surf.convert()


class ShipIcon:
    """Pre-rendrede skip-sprites for 4 kart-retninger.

    Én ShipIcon-instans per scene. `draw()` velger sprite per heading.
    """

    def __init__(self) -> None:
        # Unike renderinger
        self._north = _render_pattern(_NORTH_PATTERN)
        self._east = _render_pattern(_EAST_PATTERN)
        # Symmetri-flips
        self._south = pygame.transform.flip(self._north, False, True)
        self._west = pygame.transform.flip(self._east, True, False)

        self._sprites: dict[str, pygame.Surface] = {
            "N": self._north,
            "S": self._south,
            "E": self._east,
            "W": self._west,
        }

    def draw(
        self,
        surface: pygame.Surface,
        center_pos: tuple[int, int],
        heading: str = "N",
    ) -> None:
        """Tegn skipet med senter ved `center_pos` og gitt retning.

        `heading` er "N", "S", "E" eller "W". Ukjent heading faller
        tilbake til "N".
        """
        sprite = self._sprites.get(heading, self._north)
        cx, cy = center_pos
        surface.blit(sprite, (cx - SHIP_SIZE // 2, cy - SHIP_SIZE // 2))

    def verify_flip_symmetry(self) -> tuple[bool, str]:
        """Sanity-sjekk at flip-produkter er visuelt korrekte.

        Returnerer (ok, rapport). Brukes av scene-init eller test til å
        avgjøre om 2+2-flip-tilnærmingen leverer.

        Sjekker:
        1. S-sprite er vertikal flip av N-sprite (pixel-sammenligning).
        2. V-sprite er horisontal flip av Ø-sprite.
        3. N-sprite har mast/baug i topp (COLOR_WOOD_LIGHT eller
           COLOR_SHIRT i øvre halvdel sentrum-kolonnen), aksjonsmønster
           som antyder skip.
        4. S-sprite har mast/baug i bunn (sentrum-kolonnen, nedre halvdel).
        """
        # Sjekk 3: N-sprite sentrum-kolonne øvre halvdel har data
        cx = SHIP_SIZE // 2
        n_has_top = any(
            self._north.get_at((cx, y))[:3] != COLORKEY
            for y in range(0, SHIP_SIZE // 2)
        )
        if not n_has_top:
            return False, "N-sprite mangler innhold i topp-halvdel"

        # Sjekk 4: S-sprite sentrum-kolonne nedre halvdel har data
        s_has_bottom = any(
            self._south.get_at((cx, y))[:3] != COLORKEY
            for y in range(SHIP_SIZE // 2, SHIP_SIZE)
        )
        if not s_has_bottom:
            return False, "S-sprite mangler innhold i bunn-halvdel etter flip"

        # Sjekk 1: S er eksakt vertikal flip av N
        for y in range(SHIP_SIZE):
            for x in range(SHIP_SIZE):
                n_pix = self._north.get_at((x, y))
                s_pix = self._south.get_at((x, SHIP_SIZE - 1 - y))
                if (n_pix[0], n_pix[1], n_pix[2]) != (s_pix[0], s_pix[1], s_pix[2]):
                    return False, (
                        f"S-sprite avviker fra vertical-flip(N) ved ({x},{y})"
                    )

        # Sjekk 2: V er eksakt horisontal flip av Ø
        for y in range(SHIP_SIZE):
            for x in range(SHIP_SIZE):
                e_pix = self._east.get_at((x, y))
                w_pix = self._west.get_at((SHIP_SIZE - 1 - x, y))
                if (e_pix[0], e_pix[1], e_pix[2]) != (w_pix[0], w_pix[1], w_pix[2]):
                    return False, (
                        f"V-sprite avviker fra horizontal-flip(Ø) ved ({x},{y})"
                    )

        return True, "2+2-flip OK"
