"""Render-komposisjon for Tortuga-landsbyen.

`VillageRenderer` eier parallax-laget og hint-indikatoren, og utfører
tegnings-sekvensen for verdens-laget (alt unntatt HUD og børs-overlay).
Trukket ut av `scenes/village.py` i Fase 2A / Commit 1 for å separere
rendering fra scene-orchestrering.

Sekvens (per frame):
    1. Parallax bakgrunn + gameplay-lag
    2. Entiteter (spiller + NPC-er) i én fblits-batch
    3. Dynamiske lys (BLEND_RGB_ADD)
    4. Partikler (tåke + ildfluer)
    5. Hint-linje
    6. Parallax forgrunn

Scene-eier tegner HUD og overlay etter at `draw()` returnerer.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Sequence

import pygame

from systems.parallax import ParallaxRenderer

if TYPE_CHECKING:
    from entities.npc import NPC
    from entities.player import Player
    from systems.lighting import Light, LightingSystem
    from systems.particles import ParticleSystem
    from ui.hint import HintIndicator


class VillageRenderer:
    """Komposisjon av parallax-lag, entiteter, lys, partikler og hint.

    Renderen har ingen intern mutable state – den holder kun referanser
    til pre-konstruerte render-komponenter. All per-frame-input kommer
    inn som argumenter til `draw()`.
    """

    def __init__(
        self,
        parallax_renderer: ParallaxRenderer,
        hint: "HintIndicator",
    ) -> None:
        self._parallax = parallax_renderer
        self._hint = hint

    def draw(
        self,
        surface: pygame.Surface,
        cam_x: float,
        player: "Player",
        npcs: Sequence["NPC"],
        lighting: "LightingSystem",
        lights: Sequence["Light"],
        elapsed: float,
        particles: "ParticleSystem",
        show_near_hint: bool,
    ) -> None:
        # 1) Bakgrunn + gameplay-lag (de første 2 parallax-lagene)
        self._parallax.draw(surface, cam_x, start=0, stop=2)

        # 2) Entiteter (spiller og NPC-er) i verdens-koordinater.
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

        # 3) Dynamiske lys (BLEND_RGB_ADD) – legger seg over bygninger og
        # entiteter slik at lyset "faller på" spilleren.
        lighting.draw(surface, lights, cam_x, elapsed)

        # 4) Partikler: taake (normal blit) + ildfluer (BLEND_RGB_ADD).
        # Taake tegnes ETTER lysene slik at tavernaens varme gloed ikke
        # vasker taaken oransje – taaken forblir kald og atmosfaerisk.
        # Ildfluene tegnes til slutt i systemet siden de er "naerere" og
        # skal stikke gjennom taaken.
        particles.draw(surface, cam_x)

        # 5) Hint-linje
        self._hint.draw(surface, show_near_hint)

        # 6) Forgrunnslag (siste parallax-lag)
        self._parallax.draw(surface, cam_x, start=2, stop=3)
