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

    Re-design 2026-05-01: tonet ned alle gul-/oransje-aksenter etter
    "ser ut som klovn"-tilbakemelding. Beholder kun mørk pirat-tone
    inspirert av Sid Meier's Pirates! / Monkey Island sin Guybrush —
    silhuett-fokus, ikke fargekontrast-fokus.

    walk_frame:
      0 = stående
      1 = venstre fram
      2 = høyre fram
    """
    w, h = PLAYER_SPRITE_WIDTH, PLAYER_SPRITE_HEIGHT
    surf = pygame.Surface((w, h)).convert()
    ck = (255, 0, 255)
    surf.fill(ck)

    # ---- Hatt: solid tricorn, ingen gul plumet eller lyse bånd ----
    # Brem (bred, definerer silhuetten)
    pygame.draw.rect(surf, constants.COLOR_HAT, (0, 5, w, 3))
    # Krone (smalere pyramide) — rakere enn før, færre hatt-bånd-distraksjoner
    pygame.draw.rect(surf, constants.COLOR_HAT, (6, 0, w - 12, 5))
    # Subtil mørk skygge i krone (gir dybde uten å innføre ny farge)
    pygame.draw.rect(surf, constants.COLOR_WOOD_DARKEST, (6, 0, w - 12, 1))
    # Brem-skygge under (gir rim av lys)
    pygame.draw.rect(surf, constants.COLOR_WOOD_DARKEST, (0, 7, w, 1))

    # ---- Ansikt ----
    # Hud
    pygame.draw.rect(surf, constants.COLOR_SKIN, (6, 8, w - 12, 7))
    # Skygge under hattebrem
    pygame.draw.rect(surf, constants.COLOR_WOOD_DARK, (6, 8, w - 12, 1))
    # Øyne (2x1, mer definert enn 1px-prikker)
    pygame.draw.rect(surf, constants.COLOR_HAT, (8, 11, 2, 1))
    pygame.draw.rect(surf, constants.COLOR_HAT, (14, 11, 2, 1))
    # Subtil nese-skygge (smalere enn før, mindre dramatisk)
    pygame.draw.rect(surf, constants.COLOR_WOOD_DARK, (11, 13, 2, 1))
    # Skjegg (mørk under-ansikt, fyller bunnen av ansiktet)
    pygame.draw.rect(surf, constants.COLOR_HAT, (7, 14, w - 14, 2))

    # ---- Krage (kun smal V-form, ikke full hvit krage) ----
    # Mørk frakk-skulder først (uten lys-bånd)
    pygame.draw.rect(surf, constants.COLOR_COAT, (3, 16, w - 6, 2))
    # Liten skjorte-V (kun 4 px bred, mindre påfallende)
    pygame.draw.rect(surf, constants.COLOR_SHIRT, (10, 16, 4, 2))
    pygame.draw.rect(surf, constants.COLOR_SHIRT, (11, 18, 2, 1))

    # ---- Frakk ----
    pygame.draw.rect(surf, constants.COLOR_COAT, (3, 18, w - 6, 12))
    # Lysere venstre side (rim-light fra månen) — beholder, gir 3D-form
    pygame.draw.rect(surf, (92, 78, 104), (3, 18, 1, 12))
    # Frakk-knapper: 2 stk, små stein-grå (sølv) i stedet for 3 store gull.
    # Mindre påfallende, tematisk match til pirat-grovhet
    pygame.draw.rect(surf, constants.COLOR_STONE_LIGHT, (12, 22, 1, 1))
    pygame.draw.rect(surf, constants.COLOR_STONE_LIGHT, (12, 26, 1, 1))
    # Belte — mørk stripe (ingen gull-spenne lenger)
    pygame.draw.rect(surf, constants.COLOR_WOOD_DARKEST, (3, 28, w - 6, 1))
    # Belte-detail: liten mørk stein-spenne i stedet for varm gull
    pygame.draw.rect(surf, constants.COLOR_STONE_DARK, (11, 28, 2, 1))

    # ---- Bukser + støvler — alle varianter mørke, ingen orange aksenter ----
    if walk_frame == 0:
        # Stående: bena symmetrisk
        pygame.draw.rect(surf, constants.COLOR_WOOD_DARK, (5, 30, 6, 5))
        pygame.draw.rect(surf, constants.COLOR_WOOD_DARK, (13, 30, 6, 5))
        # Støvler — kun mørk, ingen EMBER-aksent
        pygame.draw.rect(surf, constants.COLOR_HAT, (4, 35, 8, 5))
        pygame.draw.rect(surf, constants.COLOR_HAT, (12, 35, 8, 5))
    elif walk_frame == 1:
        pygame.draw.rect(surf, constants.COLOR_WOOD_DARK, (4, 30, 6, 6))
        pygame.draw.rect(surf, constants.COLOR_WOOD_DARK, (14, 30, 6, 4))
        pygame.draw.rect(surf, constants.COLOR_HAT, (3, 36, 8, 4))
        pygame.draw.rect(surf, constants.COLOR_HAT, (13, 34, 8, 4))
    else:  # walk_frame == 2
        pygame.draw.rect(surf, constants.COLOR_WOOD_DARK, (4, 30, 6, 4))
        pygame.draw.rect(surf, constants.COLOR_WOOD_DARK, (14, 30, 6, 6))
        pygame.draw.rect(surf, constants.COLOR_HAT, (3, 34, 8, 4))
        pygame.draw.rect(surf, constants.COLOR_HAT, (13, 36, 8, 4))

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
