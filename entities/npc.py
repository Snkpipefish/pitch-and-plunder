"""NPC-entitet.

Fase 1: statiske NPC-er som Hawkins (Børsmester) med placeholder-sprite og
greet-dialog lastet fra JSON. Ingen patrulje, ingen AI.
"""

from __future__ import annotations

from dataclasses import dataclass

import pygame

import constants


def _make_hawkins_sprite() -> pygame.Surface:
    """Placeholder for Hawkins: tricorn + steingrå frakk (respektabel)."""
    w, h = 10, 20
    surf = pygame.Surface((w, h)).convert()
    ck = (255, 0, 255)
    surf.fill(ck)

    # Hatt
    pygame.draw.rect(surf, constants.COLOR_HAT, (0, 0, w, 3))
    pygame.draw.rect(surf, constants.COLOR_HAT, (2, 1, w - 4, 2))
    # Ansikt
    pygame.draw.rect(surf, constants.COLOR_SKIN, (3, 3, w - 6, 4))
    # Krage
    pygame.draw.rect(surf, constants.COLOR_SHIRT, (3, 7, w - 6, 1))
    # Frakk – steingrå i stedet for mørk fiolett
    pygame.draw.rect(surf, constants.COLOR_STONE_MID, (2, 8, w - 4, 7))
    pygame.draw.rect(surf, constants.COLOR_STONE_LIGHT, (2, 8, 1, 7))
    # Ben
    pygame.draw.rect(surf, constants.COLOR_HAT, (3, 15, 2, 5))
    pygame.draw.rect(surf, constants.COLOR_HAT, (5, 15, 2, 5))

    surf.set_colorkey(ck)
    return surf


_SPRITE_FACTORIES = {
    "hawkins": _make_hawkins_sprite,
}


@dataclass
class NPC:
    """Statisk NPC med fast verdensposisjon og en greet-linje."""

    id: str
    name: str
    x: float
    y: float
    dialog_greet: str
    sprite: pygame.Surface

    @classmethod
    def from_data(cls, data: dict, x: float, y: float) -> "NPC":
        """Bygg NPC fra JSON-record (felter som i data/npcs.json).

        `x`/`y` sendes som argumenter siden posisjonen i verdenen bestemmes
        av scenen, ikke dataene.
        """
        factory = _SPRITE_FACTORIES.get(
            data["id"], _SPRITE_FACTORIES["hawkins"]
        )
        return cls(
            id=data["id"],
            name=data["name"],
            x=float(x),
            y=float(y),
            dialog_greet=data.get("dialog_greet", ""),
            sprite=factory(),
        )
