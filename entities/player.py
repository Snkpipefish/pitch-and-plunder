"""Spiller-entitet.

Fase 1: placeholder-sprite (tricorn-hatt + frakk) tegnet prosedyrelt med
master-paletten. Erstattes av et håndtegnet sprite (og walk-animasjon) i
en senere fase. Spillerens posisjon holdes som float internt; cast til int
skjer ved rendering.
"""

from __future__ import annotations

import pygame

import constants


#: Hvor høyt sprite-rektangelet er. Breidde beregnes fra innholdet.
PLAYER_SPRITE_HEIGHT = 20
PLAYER_SPRITE_WIDTH = 10


def _make_player_sprite() -> pygame.Surface:
    """Tegn placeholder-sprite for spilleren.

    Komposisjon (fra topp):
    - Tricorn-hatt (mørkeste farge, bred silhuett)
    - Ansikt (hud)
    - Krage (cream)
    - Frakk (koldfiolett)
    - Ben (samme som hatt for silhuett-effekt)
    """
    w, h = PLAYER_SPRITE_WIDTH, PLAYER_SPRITE_HEIGHT
    surf = pygame.Surface((w, h)).convert()
    # Colorkey = magenta (en farge som IKKE finnes i paletten)
    ck = (255, 0, 255)
    surf.fill(ck)

    # Hatt: bred tricorn-silhuett øverst
    pygame.draw.rect(surf, constants.COLOR_HAT, (0, 0, w, 3))           # brem
    pygame.draw.rect(surf, constants.COLOR_HAT, (2, 1, w - 4, 2))       # krone
    # Ansikt
    pygame.draw.rect(surf, constants.COLOR_SKIN, (3, 3, w - 6, 4))
    # Krage (lyst)
    pygame.draw.rect(surf, constants.COLOR_SHIRT, (3, 7, w - 6, 1))
    # Frakk
    pygame.draw.rect(surf, constants.COLOR_COAT, (2, 8, w - 4, 7))
    # Anstrøk lysere frakk-side (venstre) for dimensjon
    pygame.draw.rect(surf, (92, 78, 104), (2, 8, 1, 7))
    # Ben
    pygame.draw.rect(surf, constants.COLOR_HAT, (3, 15, 2, 5))
    pygame.draw.rect(surf, constants.COLOR_HAT, (5, 15, 2, 5))

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
        self._sprite = _make_player_sprite()
        self._facing_left = False
        self._sprite_flipped = pygame.transform.flip(self._sprite, True, False)
        self._left_pressed = False
        self._right_pressed = False

    @property
    def sprite(self) -> pygame.Surface:
        return self._sprite_flipped if self._facing_left else self._sprite

    @property
    def width(self) -> int:
        return self._sprite.get_width()

    @property
    def height(self) -> int:
        return self._sprite.get_height()

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
