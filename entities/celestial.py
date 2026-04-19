"""Sol/måne-overlay for dag-natt-syklus.

Én sprite – en glatt hvit skive – re-tintes hver frame basert på
`DaySnapshot.celestial_color` via `pygame.BLEND_RGBA_MULT`. Rendring
skjer som overlay mellom bakgrunn og gameplay-lag.

Design-valg:
- **Pre-allokert base og tintet surface**. Ingen Surface-allokering per
  frame (jfr. PROSJEKT.md §14). Working-sprite re-fylles med base + tint.
- **Ingen halo** i Fase 2A (jfr. review-dokument). Enkel solid skive.
  Halo kan legges til som polish i senere commit.
- **Parallax på 0.2×** (Commit 7.1): celestial er "i verden", ikke fast
  på skjermen. Matcher bakgrunnslagets parallax slik at sol/måne føles
  tilhørende samme avstand som distant horisont og øyer — og gir
  visuell følelse av at himmellegemene forblir ankret mens spilleren
  går. Matcher også Fase 1 der månen var bakt inn i bg_layer-surfaces
  med speed 0.2.
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

#: Parallax-hastighet for celestial (sol/måne). 0.2 matcher bakgrunnslaget
#: slik at himmellegemene føles som del av samme distante sky-scene som
#: horisont og distant-øyer. Større verdi = celestial drifter raskere
#: (= føles nærmere); mindre = føles fjernere.
CELESTIAL_PARALLAX_SPEED = 0.2


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

        Posisjon:
        - basis-x = `celestial_x * RENDER_WIDTH`
        - parallax-offset = `cam_x * CELESTIAL_PARALLAX_SPEED` (trukket fra)
        - y = `(1 - celestial_y) * HORIZON_Y` (celestial_y=0 ved horisont,
          celestial_y=1 ved topp av himmelen)

        Parallax gjør at celestial drifter i motsatt retning av spillerens
        bevegelse — naturlig avstandsillusjon. Når spilleren går fra
        tavernaen til Børshuset (cam_x: 0 → 960) rykker celestial ca. 192
        px til venstre på skjermen.
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
        base_x = int(snapshot.celestial_x * constants.RENDER_WIDTH)
        parallax_offset = int(cam_x * CELESTIAL_PARALLAX_SPEED)
        center_x = base_x - parallax_offset
        center_y = int((1.0 - snapshot.celestial_y) * _HORIZON_Y)
        surface.blit(
            self._tinted,
            (center_x - self._size // 2, center_y - self._size // 2),
        )
