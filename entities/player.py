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


def _make_player_sprite() -> pygame.Surface:
    """Tegn placeholder-sprite for spilleren (Fase 2.6 — 24×40).

    Pikselbudsjett 960. Komposisjon (fra topp, alt i master-paletten):
    - Tricorn-hatt med bred brem, krone, mørkt bånd
    - Ansikt med øyne, nese-skygge, skjegg
    - Krage og skjorte-V
    - Frakk med knapperekke, belte, frakk-fald
    - Bukser + støvler med varm kontrast
    """
    w, h = PLAYER_SPRITE_WIDTH, PLAYER_SPRITE_HEIGHT
    surf = pygame.Surface((w, h)).convert()
    ck = (255, 0, 255)
    surf.fill(ck)

    # ---- Hatt (y=0..7) ----
    # Tricorn-brem, bred silhuett
    pygame.draw.rect(surf, constants.COLOR_HAT, (0, 5, w, 3))
    # Krone — smal pyramide
    pygame.draw.rect(surf, constants.COLOR_HAT, (5, 1, w - 10, 4))
    # Hatt-bånd (lysere shirt-tone for kontrast)
    pygame.draw.rect(surf, constants.COLOR_SHIRT, (5, 4, w - 10, 1))
    # Plumet (lysere på toppen)
    pygame.draw.rect(surf, constants.COLOR_LANTERN, (8, 0, 1, 2))

    # ---- Ansikt (y=8..15) ----
    pygame.draw.rect(surf, constants.COLOR_SKIN, (5, 8, w - 10, 8))
    # Skygge under hatt
    pygame.draw.rect(surf, constants.COLOR_HAT, (5, 8, w - 10, 1))
    # Øyne
    pygame.draw.rect(surf, constants.COLOR_HAT, (8, 11, 1, 1))
    pygame.draw.rect(surf, constants.COLOR_HAT, (15, 11, 1, 1))
    # Nese
    pygame.draw.rect(surf, constants.COLOR_WOOD_DARK, (11, 12, 2, 2))
    # Skjegg (under munn)
    pygame.draw.rect(surf, constants.COLOR_HAT, (8, 14, 8, 2))

    # ---- Krage og skjorte (y=16..18) ----
    pygame.draw.rect(surf, constants.COLOR_SHIRT, (4, 16, w - 8, 2))
    pygame.draw.rect(surf, constants.COLOR_SHIRT, (10, 18, 4, 1))  # V-snitt

    # ---- Frakk (y=18..30) ----
    pygame.draw.rect(surf, constants.COLOR_COAT, (3, 19, w - 6, 11))
    # Lysere venstre side (lys fra venstre — kommer fra måne i Tortuga)
    pygame.draw.rect(surf, (92, 78, 104), (3, 19, 1, 11))
    # Knapperekke (lanterne-gull mot mørk frakk)
    for ky in (21, 24, 27):
        pygame.draw.rect(surf, constants.COLOR_LANTERN, (11, ky, 2, 2))
    # Belte — mørk stripe
    pygame.draw.rect(surf, constants.COLOR_WOOD_DARKEST, (3, 28, w - 6, 1))
    # Belte-spenne (varm gull-aksent)
    pygame.draw.rect(surf, constants.COLOR_LANTERN_BRIGHT, (11, 28, 2, 1))

    # ---- Bukser (y=30..35) ----
    pygame.draw.rect(surf, constants.COLOR_WOOD_DARK, (5, 30, 6, 5))
    pygame.draw.rect(surf, constants.COLOR_WOOD_DARK, (13, 30, 6, 5))

    # ---- Støvler (y=35..40) ----
    pygame.draw.rect(surf, constants.COLOR_WOOD_DARKEST, (4, 35, 8, 5))
    pygame.draw.rect(surf, constants.COLOR_WOOD_DARKEST, (12, 35, 8, 5))
    # Varme støvel-detaljer (snørrebånd / brunlig sølje)
    pygame.draw.rect(surf, constants.COLOR_EMBER, (6, 36, 1, 1))
    pygame.draw.rect(surf, constants.COLOR_EMBER, (16, 36, 1, 1))

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
