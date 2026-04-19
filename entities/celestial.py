"""Sol/måne-overlay for dag-natt-syklus.

Én sprite – en glatt hvit skive – re-tintes hver frame basert på
`DaySnapshot.celestial_color` via `pygame.BLEND_RGBA_MULT`. Rendring
skjer som overlay mellom bakgrunn og gameplay-lag.

Design-valg:
- **Pre-allokert base og tintet surface**. Ingen Surface-allokering per
  frame (jfr. PROSJEKT.md §14). Working-sprite re-fylles med base + tint.
- **Ingen halo** i Fase 2A (jfr. review-dokument). Enkel solid skive.
  Halo kan legges til som polish i senere commit.
- **Verdens-forankring 1:1** (Commit 7.2): celestial er tematisk
  forankret i verden. Månen står statisk over Børshuset (worldx=1350);
  solen beveger seg gjennom verden fra SUN_WORLD_X_DAWN til
  SUN_WORLD_X_DUSK gjennom dagen. `screen_x = int(worldx - cam_x)` —
  ekte 1:1 kamera-offset, ingen parallax-faktor. Det gir korrekt
  tematisk atferd: når spilleren går fra Børshuset til tavernaen om
  natten forsvinner månen ut til høyre (kan ikke "flyktes fra månen
  men kan gå ut av synsfeltet").
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pygame

import constants

if TYPE_CHECKING:
    from systems.day_cycle import DaySnapshot


#: Radius til sol/måne-skiven i piksler. Samme for begge fordi
#: differensieringen kommer via farge og kontekst (stjerner / ikke).
CELESTIAL_RADIUS = 14

#: Horisont-linje i skjerm-koordinater (matcher parallax-backdrops).
_HORIZON_Y = int(constants.RENDER_HEIGHT * 0.58)



class Celestial:
    """Overlay for sol eller måne."""

    def __init__(self) -> None:
        size = CELESTIAL_RADIUS * 2 + 2
        self._size = size
        # Base: hvit skive med per-pixel alpha. Brukt som mal for hver
        # re-tinting. Opprettes én gang.
        self._base = pygame.Surface((size, size), pygame.SRCALPHA).convert_alpha()
        pygame.draw.circle(
            self._base,
            (255, 255, 255, 255),
            (size // 2, size // 2),
            CELESTIAL_RADIUS,
        )
        # Arbeidssurfacen holder den tintete sprite-en. Også pre-allokert.
        self._tinted = self._base.copy()
        # Cache av siste tint-farge slik at vi hopper over re-tint når
        # fargen ikke har endret seg (f.eks. gjennom nattfase andre halvdel).
        self._last_color: tuple[int, int, int] | None = None

    def _tint(self, color: tuple[int, int, int]) -> None:
        """Re-tint arbeidssurfacen til `color` via BLEND_RGBA_MULT.

        Idempotent hvis `color` er uendret fra forrige kall.
        """
        if color == self._last_color:
            return
        self._last_color = color
        # Nullstill arbeidssurfacen (SRCALPHA-transparent)
        self._tinted.fill((0, 0, 0, 0))
        # Kopier base (hvit skive) inn
        self._tinted.blit(self._base, (0, 0))
        # Multipliser med ønsket farge. Transparente piksler forblir
        # transparente (0 * x = 0).
        self._tinted.fill(
            (*color, 255), special_flags=pygame.BLEND_RGBA_MULT
        )

    def draw(
        self,
        surface: pygame.Surface,
        snapshot: "DaySnapshot",
        cam_x: float,
    ) -> None:
        """Tegn sol/måne på `surface` basert på `snapshot` og kamera-posisjon.

        Hopper over blit hvis `snapshot.celestial_alpha <= 0.0` (gap-vinduer
        eller degenerert state). For partielle alpha-verdier anvendes
        per-surface alpha på sprite-en slik at den fader jevnt inn/ut
        gjennom moon/sun-transisjonene.

        Posisjon (Commit 7.2 — verdens-forankring):
        - x: `int(celestial_x - cam_x)` — celestial_x er verdens-x
          (0 til WORLD_WIDTH), subtraherer kamera 1:1. Ingen parallax-
          skalering: når spilleren står under himmellegemet, er det rett
          over ham; når han går bort, forsvinner det ut av synsfeltet.
        - y: `(1 - celestial_y) * HORIZON_Y` (celestial_y=0 ved horisont,
          celestial_y=1 ved topp av himmelen)
        """
        alpha = snapshot.celestial_alpha
        if alpha <= 0.0:
            return
        self._tint(snapshot.celestial_color)
        # Viktig: ALDRI bruk `set_alpha(None)` paa denne surfacen. pygame-ce
        # 2.5.7 disabler per-pixel alpha paa convert_alpha-surfaces naar
        # None settes, som gir sprite-korner tegnet som solid sort. Bruk
        # heller eksplisitt 255 for full opasitet (per-pixel alpha bevares).
        self._tinted.set_alpha(int(alpha * 255) if alpha < 1.0 else 255)
        center_x = int(snapshot.celestial_x - cam_x)
        center_y = int((1.0 - snapshot.celestial_y) * _HORIZON_Y)
        surface.blit(
            self._tinted,
            (center_x - self._size // 2, center_y - self._size // 2),
        )
