"""Render-komposisjon for Tortuga-landsbyen.

`VillageRenderer` eier bakgrunns-varianter (6 pre-rendrede for dag-natt-
syklus), parallax-laget (gameplay + forgrunn), Celestial-overlay, og
hint-indikatoren. Utfører tegnings-sekvensen for verdens-laget (alt
unntatt HUD og børs-overlay).

Trukket ut av `scenes/village.py` i Fase 2A / Commit 1. Utvidet i
Commit 5B til å kobles mot `DaySnapshot` for dag-natt-rendering:
cross-fade mellom to nærmeste backdrop-varianter + Celestial-sprite som
overlay.

Sekvens (per frame):
    1. Backdrop cross-fade (2 blits, parallax speed 0.2)
    2. Celestial (sol/måne) som overlay
    3. Gameplay-lag (parallax speed 1.0)
    4. Entiteter (spiller + NPC-er) i én fblits-batch
    5. Dynamiske lys (BLEND_RGB_ADD)
    6. Partikler (tåke + ildfluer)
    7. Hint-linje
    8. Parallax forgrunn (speed 1.3)

Scene-eier tegner HUD og overlay etter at `draw()` returnerer.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Sequence

import pygame

from systems.parallax import ParallaxRenderer

if TYPE_CHECKING:
    from entities.celestial import Celestial
    from entities.npc import NPC
    from entities.player import Player
    from systems.day_cycle import DaySnapshot
    from systems.lighting import Light, LightingSystem
    from systems.particles import ParticleSystem
    from ui.hint import HintIndicator


#: Parallax-hastighet for bakgrunnslaget (samme som tidligere statisk bg).
_BACKDROP_PARALLAX_SPEED = 0.2


class VillageRenderer:
    """Komposisjon av backdrop, celestial, parallax-lag, entiteter, lys,
    partikler og hint.

    Renderen har ingen intern mutable state utenom referanser til pre-
    konstruerte render-komponenter. All per-frame-input kommer inn som
    argumenter til `draw()`.
    """

    def __init__(
        self,
        backdrops: Sequence[tuple[float, pygame.Surface]],
        parallax_renderer: ParallaxRenderer,
        celestial: "Celestial",
        hint: "HintIndicator",
    ) -> None:
        # Backdrops sorteres stigende på fraksjon (forutsetter at input
        # allerede er sortert; assert beskytter mot feil i byggeren).
        self._backdrops: list[tuple[float, pygame.Surface]] = list(backdrops)
        assert self._backdrops, "VillageRenderer trenger minst én backdrop"
        assert all(
            self._backdrops[i][0] <= self._backdrops[i + 1][0]
            for i in range(len(self._backdrops) - 1)
        ), "Backdrop-fraksjoner må være sortert stigende"
        self._parallax = parallax_renderer
        self._celestial = celestial
        self._hint = hint

    def _find_backdrop_pair(
        self, fraction: float
    ) -> tuple[pygame.Surface, pygame.Surface, float]:
        """Returner (backdrop_A, backdrop_B, blend_t) for gitt fraksjon.

        `blend_t=0` → bare A er synlig; `blend_t=1` → bare B. For
        `fraction` mellom to anker-fraksjoner, blend_t er lineært
        interpolert. Wrap-around fra siste anker (f.eks. 0.92) til første
        (0.00) håndteres ved å behandle 0.00 som også 1.00.
        """
        backdrops = self._backdrops
        n = len(backdrops)
        # Klamp fraksjon til [0, 1) for å håndtere floating-point overshoot
        f = fraction % 1.0
        for i in range(n):
            next_i = (i + 1) % n
            frac_a = backdrops[i][0]
            # Wrap-around: siste ankers "slutt" er 1.0, ikke første ankers 0.0
            frac_b = backdrops[next_i][0] if next_i != 0 else 1.0
            if frac_a <= f < frac_b:
                span = frac_b - frac_a
                if span <= 0.0:
                    return backdrops[i][1], backdrops[next_i][1], 0.0
                t = (f - frac_a) / span
                return backdrops[i][1], backdrops[next_i][1], t
        # Fallback (numerisk kantsituasjon): bruk første anker fullt ut
        return backdrops[0][1], backdrops[0][1], 0.0

    def _draw_backdrop(
        self,
        surface: pygame.Surface,
        cam_x: float,
        snapshot: "DaySnapshot",
    ) -> None:
        """Blit to backdrops med cross-fade basert på snapshot-fraksjon.

        Begge backdrops flyttes med parallax-speed 0.2. Første backdrop
        tegnes som opaque (raskt), andre med per-surface alpha for
        cross-fade. `set_alpha(None)` på første er viktig – uten det vil
        pygame utføre full per-pixel alpha-blending selv ved alpha=255,
        noe som gir en 5–10 ms/frame regresjon på svak CPU.
        """
        bg_a, bg_b, t = self._find_backdrop_pair(snapshot.day_fraction)
        offset_x = int(-cam_x * _BACKDROP_PARALLAX_SPEED)
        # Første backdrop: fullt opaque, alpha disabled → memcpy-fast blit
        bg_a.set_alpha(None)
        surface.blit(bg_a, (offset_x, 0))
        # Andre backdrop: alpha = t*255 for cross-fade. Hopp over hvis
        # fraksjon er nøyaktig på anker (t=0) eller bg_a og bg_b er samme.
        if t > 0.0 and bg_a is not bg_b:
            bg_b.set_alpha(int(t * 255))
            surface.blit(bg_b, (offset_x, 0))

    def draw(
        self,
        surface: pygame.Surface,
        cam_x: float,
        snapshot: "DaySnapshot",
        player: "Player",
        npcs: Sequence["NPC"],
        lighting: "LightingSystem",
        lights: Sequence["Light"],
        elapsed: float,
        particles: "ParticleSystem",
        show_near_hint: bool,
    ) -> None:
        # 1) Backdrop (cross-fade mellom to nærmeste varianter)
        self._draw_backdrop(surface, cam_x, snapshot)

        # 2) Celestial (sol eller måne) som overlay, ikke del av parallax
        self._celestial.draw(surface, snapshot)

        # 3) Gameplay-lag (index 0 i denne parallax-renderen)
        self._parallax.draw(surface, cam_x, start=0, stop=1)

        # 4) Entiteter (spiller og NPC-er) i verdens-koordinater.
        # Bruk fblits for én batch; ingen overlap-sortering er nødvendig
        # i Fase 1 siden alle står på samme gatenivå.
        cx = int(cam_x)
        batch: list[tuple[pygame.Surface, tuple[int, int]]] = []
        for npc in npcs:
            batch.append((npc.sprite, (int(npc.x) - cx, int(npc.y))))
        batch.append(
            (player.sprite, (int(player.x) - cx, int(player.y)))
        )
        surface.fblits(batch)

        # 5) Dynamiske lys (BLEND_RGB_ADD) – legger seg over bygninger og
        # entiteter slik at lyset "faller på" spilleren.
        lighting.draw(surface, lights, cam_x, elapsed)

        # 6) Partikler: taake (normal blit) + ildfluer (BLEND_RGB_ADD).
        particles.draw(surface, cam_x)

        # 7) Hint-linje
        self._hint.draw(surface, show_near_hint)

        # 8) Forgrunnslag (index 1 i parallax-renderen)
        self._parallax.draw(surface, cam_x, start=1, stop=2)
