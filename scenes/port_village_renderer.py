"""Render-komposisjon for havn-scener.

`PortVillageRenderer` eier to sett backdrop-varianter (himmel og fjell/hav),
parallax-laget (gameplay + parallax-forgrunn), Celestial-overlay, og
hint-indikatoren. Utfører tegnings-sekvensen for verdens-laget (alt
unntatt HUD og børs-overlay).

Trukket ut av `scenes/village.py` i Fase 2A / Commit 1 som VillageRenderer.
Utvidet i Commit 5B (dag-natt-rendering med cross-fade + Celestial-overlay)
og Commit 7.2 (split av backdrop i himmel-lag og fjell/hav-lag for å få
riktig render-rekkefølge rundt celestial). Omdøpt til PortVillageRenderer
i Fase 2B C4 samtidig med at scenen ble parameterisert over PortConfig.

Sekvens (per frame):
    1. Himmel-lag cross-fade (opakt; gradient + stjerner)
    2. Celestial (sol/måne) som overlay — verdens-forankret, 1:1 cam
    3. Forgrunns-lag cross-fade (SRCALPHA; fjell + opakt hav) — okkluderer
       celestial som måtte nærme seg eller ha sunket under horisonten
    4. Gameplay-lag (parallax speed 1.0)
    5. Entiteter (spiller + NPC-er) i én fblits-batch
    6. Dynamiske lys (BLEND_RGB_ADD)
    7. Partikler (tåke + ildfluer)
    8. Hint-linje
    9. Parallax forgrunn (speed 1.3)

Scene-eier tegner HUD og overlay etter at `draw()` returnerer.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Sequence

import pygame

from systems.parallax import ParallaxRenderer

if TYPE_CHECKING:
    from entities.celestial import Celestial
    from entities.npc import NPC
    from entities.npc_silhouette import NPCSilhouette
    from entities.player import Player
    from systems.day_cycle import DaySnapshot
    from systems.lighting import Light, LightingSystem
    from systems.particles import ParticleSystem
    from ui.hint import HintIndicator


#: Parallax-hastighet for bakgrunnslaget (samme som tidligere statisk bg).
_BACKDROP_PARALLAX_SPEED = 0.2


class PortVillageRenderer:
    """Komposisjon av backdrop, celestial, parallax-lag, entiteter, lys,
    partikler og hint.

    Renderen har ingen intern mutable state utenom referanser til pre-
    konstruerte render-komponenter. All per-frame-input kommer inn som
    argumenter til `draw()`.
    """

    def __init__(
        self,
        backdrops: Sequence[tuple[float, pygame.Surface]],
        foregrounds: Sequence[tuple[float, pygame.Surface]],
        parallax_renderer: ParallaxRenderer,
        celestial: "Celestial",
        hint: "HintIndicator",
    ) -> None:
        # Backdrops og foregrounds sorteres stigende på fraksjon
        # (forutsetter at input allerede er sortert; assert beskytter mot
        # feil i byggeren).
        self._backdrops: list[tuple[float, pygame.Surface]] = list(backdrops)
        self._foregrounds: list[tuple[float, pygame.Surface]] = list(
            foregrounds
        )
        assert self._backdrops, "PortVillageRenderer trenger minst én backdrop"
        assert self._foregrounds, (
            "PortVillageRenderer trenger minst ett foreground-lag"
        )
        assert len(self._backdrops) == len(self._foregrounds), (
            "Backdrops og foregrounds må ha samme antall varianter"
        )
        assert all(
            self._backdrops[i][0] <= self._backdrops[i + 1][0]
            for i in range(len(self._backdrops) - 1)
        ), "Backdrop-fraksjoner må være sortert stigende"
        self._parallax = parallax_renderer
        self._celestial = celestial
        self._hint = hint

    @staticmethod
    def _find_variant_pair(
        variants: list[tuple[float, pygame.Surface]],
        fraction: float,
    ) -> tuple[pygame.Surface, pygame.Surface, float]:
        """Returner (A, B, blend_t) for en gitt fraksjon fra et sortert
        variant-sett. Wrap-around fra siste (f.eks. 0.92) til første (0.00)
        håndteres ved å behandle 0.00 som også 1.00.
        """
        n = len(variants)
        # Klamp fraksjon til [0, 1) for å håndtere floating-point overshoot
        f = fraction % 1.0
        for i in range(n):
            next_i = (i + 1) % n
            frac_a = variants[i][0]
            # Wrap-around: siste ankers "slutt" er 1.0, ikke første ankers 0.0
            frac_b = variants[next_i][0] if next_i != 0 else 1.0
            if frac_a <= f < frac_b:
                span = frac_b - frac_a
                if span <= 0.0:
                    return variants[i][1], variants[next_i][1], 0.0
                t = (f - frac_a) / span
                return variants[i][1], variants[next_i][1], t
        # Fallback (numerisk kantsituasjon): bruk første anker fullt ut
        return variants[0][1], variants[0][1], 0.0

    def _draw_backdrop(
        self,
        surface: pygame.Surface,
        cam_x: float,
        snapshot: "DaySnapshot",
    ) -> None:
        """Blit to himmel-varianter med cross-fade.

        Begge flyttes med parallax-speed 0.2. Første tegnes opaque
        (raskt), andre med per-surface alpha for cross-fade.
        `set_alpha(None)` på første er viktig – uten det vil pygame
        utføre full per-pixel alpha-blending selv ved alpha=255, som gir
        5–10 ms/frame regresjon på svak CPU.
        """
        bg_a, bg_b, t = self._find_variant_pair(
            self._backdrops, snapshot.day_fraction
        )
        offset_x = int(-cam_x * _BACKDROP_PARALLAX_SPEED)
        # Første himmel: fullt opaque, alpha disabled → memcpy-fast blit
        bg_a.set_alpha(None)
        surface.blit(bg_a, (offset_x, 0))
        if t > 0.0 and bg_a is not bg_b:
            bg_b.set_alpha(int(t * 255))
            surface.blit(bg_b, (offset_x, 0))

    def _draw_foreground_backdrop(
        self,
        surface: pygame.Surface,
        cam_x: float,
        snapshot: "DaySnapshot",
    ) -> None:
        """Blit to forgrunns-varianter (fjell + hav) med cross-fade.

        SRCALPHA-surfaces: første blits med sin egen per-pixel alpha,
        andre med set_alpha for cross-fade. Forgrunnen kalles EFTER
        celestial slik at fjellsilhuetter og hav kan okkludere solen og
        månen når de nærmer seg eller har sunket under horisonten.
        """
        fg_a, fg_b, t = self._find_variant_pair(
            self._foregrounds, snapshot.day_fraction
        )
        offset_x = int(-cam_x * _BACKDROP_PARALLAX_SPEED)
        # For SRCALPHA-surface er alpha=255 default når set_alpha ikke
        # settes; vi setter eksplisitt 255 for konsistens.
        fg_a.set_alpha(255)
        surface.blit(fg_a, (offset_x, 0))
        if t > 0.0 and fg_a is not fg_b:
            fg_b.set_alpha(int(t * 255))
            surface.blit(fg_b, (offset_x, 0))

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
        hint_state: "bool | str" = False,
        silhouettes: Sequence["NPCSilhouette"] = (),
        night_factor: float = 1.0,
    ) -> None:
        # 1) Himmel-lag (cross-fade mellom to nærmeste varianter)
        self._draw_backdrop(surface, cam_x, snapshot)

        # 2) Celestial (sol eller måne) som overlay. Verdens-forankret
        # (Commit 7.2): screen_x = worldx - cam_x. Månen står over
        # Børshuset; solen beveger seg gjennom verden fra øst til vest.
        self._celestial.draw(surface, snapshot, cam_x)

        # 3) Forgrunns-lag (fjell + opakt hav). Tegnes ETTER celestial
        # (Commit 7.2) slik at fjell-silhuetter og hav okkluderer solen
        # og månen ved horisont-passering.
        self._draw_foreground_backdrop(surface, cam_x, snapshot)

        # 4) Gameplay-lag (index 0 i denne parallax-renderen)
        self._parallax.draw(surface, cam_x, start=0, stop=1)

        # 5) Entiteter (spiller, NPC-er, rekvisita-silhuetter) i verdens-
        # koordinater. Bruk fblits for én batch.
        # Render-rekkefølge (fra bakerst til forrest):
        #   - Silhuetter (FASE_2_5 §2.1: "bak lanterne-stolper, men
        #     lanterne-stolper er bakt inn i gameplay-laget så silhuetter
        #     tegnes over dem — tematisk OK på natt-scener hvor
        #     lanterne-stolpene er tynne silhuetter uten å konkurrere")
        #   - NPC-er (Hawkins osv)
        #   - Spiller (forrest)
        cx = int(cam_x)
        batch: list[tuple[pygame.Surface, tuple[int, int]]] = []
        for sil in silhouettes:
            batch.append((sil.sprite, (int(sil.x) - cx, int(sil.y))))
        for npc in npcs:
            batch.append((npc.sprite, (int(npc.x) - cx, int(npc.y))))
        batch.append(
            (player.sprite, (int(player.x) - cx, int(player.y)))
        )
        surface.fblits(batch)

        # 6) Dynamiske lys (BLEND_RGB_ADD) – legger seg over bygninger og
        # entiteter slik at lyset "faller på" spilleren.
        lighting.draw(surface, lights, cam_x, elapsed, night_factor=night_factor)

        # 7) Partikler: taake (normal blit) + ildfluer (BLEND_RGB_ADD).
        particles.draw(surface, cam_x)

        # 8) Hint-linje — tar bool (2A-kompat) eller str (C5: "far",
        # "near"/"near_exchange", "near_dock")
        self._hint.draw(surface, hint_state)

        # 9) Parallax forgrunn (index 1 i parallax-renderen, speed 1.3)
        self._parallax.draw(surface, cam_x, start=1, stop=2)
