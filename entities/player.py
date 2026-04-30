"""Spiller-entitet.

Fase 1: placeholder-sprite (tricorn-hatt + frakk) tegnet prosedyrelt med
master-paletten. Erstattes av et håndtegnet sprite (og walk-animasjon) i
en senere fase. Spillerens posisjon holdes som float internt; cast til int
skjer ved rendering.

Fase 2.6 sub-steg 5: sprite-bump 10×20 → 24×40 med utvidet pikselbudsjett
(200 → 960 piksler). Detalj-tillegg: tricorn-brem, hatt-bånd, ansikt med
øyne+nese+skjegg, frakk-flikk + knapper + belte, støvler. Fortsatt ren
master-palett.
"""

from __future__ import annotations

import pygame

import constants


#: Hvor høyt sprite-rektangelet er. Breidde beregnes fra innholdet.
PLAYER_SPRITE_HEIGHT = 40
PLAYER_SPRITE_WIDTH = 24


def _make_player_sprite(walk_frame: int = 0) -> pygame.Surface:
    """Tegn placeholder-sprite for spilleren (Fase 2.6 — 24×40).

    walk_frame:
      0 = stående (bena rett ned)
      1 = venstre fram (venstre ben litt frem, høyre litt tilbake)
      2 = høyre fram (motsatt)

    Pikselbudsjett 960. Master-palett.
    """
    w, h = PLAYER_SPRITE_WIDTH, PLAYER_SPRITE_HEIGHT
    surf = pygame.Surface((w, h)).convert()
    ck = (255, 0, 255)
    surf.fill(ck)

    # ---- Hatt ----
    pygame.draw.rect(surf, constants.COLOR_HAT, (0, 5, w, 3))
    pygame.draw.rect(surf, constants.COLOR_HAT, (5, 1, w - 10, 4))
    pygame.draw.rect(surf, constants.COLOR_SHIRT, (5, 4, w - 10, 1))
    pygame.draw.rect(surf, constants.COLOR_LANTERN, (8, 0, 1, 2))

    # ---- Ansikt ----
    pygame.draw.rect(surf, constants.COLOR_SKIN, (5, 8, w - 10, 8))
    pygame.draw.rect(surf, constants.COLOR_HAT, (5, 8, w - 10, 1))
    pygame.draw.rect(surf, constants.COLOR_HAT, (8, 11, 1, 1))
    pygame.draw.rect(surf, constants.COLOR_HAT, (15, 11, 1, 1))
    pygame.draw.rect(surf, constants.COLOR_WOOD_DARK, (11, 12, 2, 2))
    pygame.draw.rect(surf, constants.COLOR_HAT, (8, 14, 8, 2))

    # ---- Krage og skjorte ----
    pygame.draw.rect(surf, constants.COLOR_SHIRT, (4, 16, w - 8, 2))
    pygame.draw.rect(surf, constants.COLOR_SHIRT, (10, 18, 4, 1))

    # ---- Frakk ----
    pygame.draw.rect(surf, constants.COLOR_COAT, (3, 19, w - 6, 11))
    pygame.draw.rect(surf, (92, 78, 104), (3, 19, 1, 11))
    for ky in (21, 24, 27):
        pygame.draw.rect(surf, constants.COLOR_LANTERN, (11, ky, 2, 2))
    pygame.draw.rect(surf, constants.COLOR_WOOD_DARKEST, (3, 28, w - 6, 1))
    pygame.draw.rect(surf, constants.COLOR_LANTERN_BRIGHT, (11, 28, 2, 1))

    # ---- Bukser + støvler — varierer med walk-frame ----
    # Standard frame 0: bena ved siden av hverandre.
    # Frame 1: venstre ben fram (vises lengre ned, smalere), høyre tilbake (kortere).
    # Frame 2: omvendt.
    if walk_frame == 0:
        # Stående: bena symmetrisk
        pygame.draw.rect(surf, constants.COLOR_WOOD_DARK, (5, 30, 6, 5))
        pygame.draw.rect(surf, constants.COLOR_WOOD_DARK, (13, 30, 6, 5))
        pygame.draw.rect(surf, constants.COLOR_WOOD_DARKEST, (4, 35, 8, 5))
        pygame.draw.rect(surf, constants.COLOR_WOOD_DARKEST, (12, 35, 8, 5))
        pygame.draw.rect(surf, constants.COLOR_EMBER, (6, 36, 1, 1))
        pygame.draw.rect(surf, constants.COLOR_EMBER, (16, 36, 1, 1))
    elif walk_frame == 1:
        # Venstre ben fram (litt utover venstre + lavere), høyre tilbake (rett)
        pygame.draw.rect(surf, constants.COLOR_WOOD_DARK, (4, 30, 6, 6))   # venstre ben
        pygame.draw.rect(surf, constants.COLOR_WOOD_DARK, (14, 30, 6, 4))  # høyre ben (kortere = lengre tilbake)
        pygame.draw.rect(surf, constants.COLOR_WOOD_DARKEST, (3, 36, 8, 4))  # venstre støvel
        pygame.draw.rect(surf, constants.COLOR_WOOD_DARKEST, (13, 34, 8, 4))  # høyre støvel
        pygame.draw.rect(surf, constants.COLOR_EMBER, (5, 37, 1, 1))
        pygame.draw.rect(surf, constants.COLOR_EMBER, (17, 35, 1, 1))
    else:  # walk_frame == 2
        # Høyre ben fram, venstre tilbake (speilvendt 1)
        pygame.draw.rect(surf, constants.COLOR_WOOD_DARK, (4, 30, 6, 4))   # venstre ben (tilbake)
        pygame.draw.rect(surf, constants.COLOR_WOOD_DARK, (14, 30, 6, 6))  # høyre ben (fram)
        pygame.draw.rect(surf, constants.COLOR_WOOD_DARKEST, (3, 34, 8, 4))  # venstre støvel (bak)
        pygame.draw.rect(surf, constants.COLOR_WOOD_DARKEST, (13, 36, 8, 4))  # høyre støvel (fram)
        pygame.draw.rect(surf, constants.COLOR_EMBER, (5, 35, 1, 1))
        pygame.draw.rect(surf, constants.COLOR_EMBER, (17, 37, 1, 1))

    surf.set_colorkey(ck)
    return surf


class Player:
    """Spiller med horisontal bevegelse.

    `x`, `y` er i verdens-koordinater. `y` er topp-venstre av sprite,
    ikke føtter. Klamping mot verdensgrensene håndteres av scenen.
    """

    def __init__(self, x: float, y: float) -> None:
        self.x: float = float(x)
        self.y: float = float(y)
        # 3-frame walk-cycle (0=stå, 1=venstre fram, 2=høyre fram).
        # Pre-rendret + venstre-vendt variant for hver = 6 surfaces totalt.
        self._frames_right = [_make_player_sprite(i) for i in range(3)]
        self._frames_left = [
            pygame.transform.flip(s, True, False) for s in self._frames_right
        ]
        self._facing_left = False
        self._left_pressed = False
        self._right_pressed = False
        # Walk-cycle-tilstand: timer går opp ved bevegelse, frame-index
        # alternerer 1↔2 når timer > step_period. Når spilleren stopper,
        # snap-er vi tilbake til frame 0 (stå).
        self._walk_timer: float = 0.0
        self._walk_step_period: float = 0.18  # sek per fot-skift
        self._walk_frame: int = 0  # aktiv frame-index

    @property
    def sprite(self) -> pygame.Surface:
        frames = self._frames_left if self._facing_left else self._frames_right
        return frames[self._walk_frame]

    @property
    def width(self) -> int:
        return self._frames_right[0].get_width()

    @property
    def height(self) -> int:
        return self._frames_right[0].get_height()

    def press(self, direction: int) -> None:
        """direction: -1 = venstre, +1 = høyre, 0 = slipp begge."""
        if direction < 0:
            self._left_pressed = True
        elif direction > 0:
            self._right_pressed = True
        else:
            self._left_pressed = self._right_pressed = False

    def release(self, direction: int) -> None:
        if direction < 0:
            self._left_pressed = False
        elif direction > 0:
            self._right_pressed = False

    def update(self, dt: float, min_x: float, max_x: float) -> None:
        dx = (1 if self._right_pressed else 0) - (1 if self._left_pressed else 0)
        if dx != 0:
            self._facing_left = dx < 0
            self.x += dx * constants.PLAYER_WALK_SPEED * dt
            if self.x < min_x:
                self.x = min_x
            elif self.x > max_x:
                self.x = max_x
            # Avanser walk-cycle: alternér mellom frame 1 og 2.
            self._walk_timer += dt
            if self._walk_timer >= self._walk_step_period:
                self._walk_timer = 0.0
                # 1↔2; hvis vi sto stille (frame 0), start på 1.
                self._walk_frame = 2 if self._walk_frame == 1 else 1
        else:
            # Snap tilbake til stående positur og nullstill timer.
            self._walk_frame = 0
            self._walk_timer = 0.0
