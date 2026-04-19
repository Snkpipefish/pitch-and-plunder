"""Hint-tekst nederst på skjermen.

En `HintIndicator` holder flere pre-rendrede tekstsurfaces (ett per
navngitt tilstand) og viser den som passer til gjeldende spilletilstand.
Tekstene rendres kun én gang ved konstruksjon; `draw()` gjør en enkelt
blit uten allokering.

Trukket ut av `scenes/village.py` i Fase 2A / Commit 1. Utvidet i
Fase 2B C5 til å støtte flere interaksjons-tilstander (far, near-
exchange, near-dock) slik at port_village kan vise ulike hint avhengig
av hvor spilleren står.
"""

from __future__ import annotations

import pygame


#: Standard-tilstander. Scene kan legge til egne navn om nødvendig.
STATE_FAR = "far"
STATE_NEAR = "near"          # Legacy 2A-kompat: samme som near-exchange
STATE_NEAR_EXCHANGE = "near_exchange"
STATE_NEAR_DOCK = "near_dock"


class HintIndicator:
    """Multi-tilstand hint-tekst. Hver navngitt tilstand har sin egen
    pre-rendrede surface. `draw(surface, state)` velger riktig.

    Bak-kompatibel med 2A-signaturen (far_text + near_text). Nye
    tilstander legges via `add_state(name, text, color)`.
    """

    def __init__(
        self,
        font: pygame.font.Font,
        far_text: str,
        near_text: str,
        far_color: tuple[int, int, int],
        near_color: tuple[int, int, int],
        pos: tuple[int, int],
    ) -> None:
        self._font = font
        self._pos = pos
        self._surfaces: dict[str, pygame.Surface] = {
            STATE_FAR: font.render(
                far_text, False, far_color
            ).convert_alpha(),
            STATE_NEAR: font.render(
                near_text, False, near_color
            ).convert_alpha(),
        }
        # STATE_NEAR_EXCHANGE alias til STATE_NEAR for bak-kompat
        self._surfaces[STATE_NEAR_EXCHANGE] = self._surfaces[STATE_NEAR]

    def add_state(
        self,
        name: str,
        text: str,
        color: tuple[int, int, int],
    ) -> None:
        """Legg til ekstra tilstand (f.eks. near_dock for C5)."""
        self._surfaces[name] = self._font.render(
            text, False, color
        ).convert_alpha()

    def draw(
        self,
        surface: pygame.Surface,
        state_or_show_near: object = False,
    ) -> None:
        """Blit riktig hint-variant til `surface`.

        `state_or_show_near` tolerer to kall-konvensjoner:
        - Ny: streng-tilstandsnavn ("far", "near_exchange", "near_dock")
        - Gammel (2A): bool (True → "near", False → "far")
        """
        if isinstance(state_or_show_near, bool):
            key = STATE_NEAR if state_or_show_near else STATE_FAR
        else:
            key = str(state_or_show_near)
        sprite = self._surfaces.get(key, self._surfaces[STATE_FAR])
        surface.blit(sprite, self._pos)
