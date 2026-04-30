"""NPC-entitet.

Fase 1: statiske NPC-er som Hawkins (Børsmester) med placeholder-sprite og
greet-dialog lastet fra JSON. Ingen patrulje, ingen AI.
"""

from __future__ import annotations

from dataclasses import dataclass

import pygame

import constants


def _make_hawkins_sprite() -> pygame.Surface:
    """Hawkins (Børsmester): tricorn + stein-grå frakk (respektabel autoritet).

    Fase 2.6 sub-steg 5: 24×40 med utvidet pikselbudsjett. Hawkins skiller
    seg fra spilleren via stein-paletten (kald, autoritær) i stedet for
    den varme COAT-fiolette frakken — visuell match til Børshusets kalde
    blå-grå tematikk.
    """
    w, h = 24, 40
    surf = pygame.Surface((w, h)).convert()
    ck = (255, 0, 255)
    surf.fill(ck)

    # ---- Hatt ----
    pygame.draw.rect(surf, constants.COLOR_HAT, (0, 5, w, 3))
    pygame.draw.rect(surf, constants.COLOR_HAT, (5, 1, w - 10, 4))
    # Hatt-bånd (lysere stone for kontrast — matcher frakken)
    pygame.draw.rect(surf, constants.COLOR_STONE_LIT, (5, 4, w - 10, 1))

    # ---- Ansikt ----
    pygame.draw.rect(surf, constants.COLOR_SKIN, (5, 8, w - 10, 8))
    pygame.draw.rect(surf, constants.COLOR_HAT, (5, 8, w - 10, 1))
    # Øyne
    pygame.draw.rect(surf, constants.COLOR_HAT, (8, 11, 1, 1))
    pygame.draw.rect(surf, constants.COLOR_HAT, (15, 11, 1, 1))
    # Snurrebart (Hawkins-signatur)
    pygame.draw.rect(surf, constants.COLOR_WOOD_DARK, (8, 14, 8, 1))

    # ---- Krage og skjorte (hvit krage er børsmester-uniform) ----
    pygame.draw.rect(surf, constants.COLOR_SHIRT, (3, 16, w - 6, 2))
    pygame.draw.rect(surf, constants.COLOR_SHIRT, (10, 18, 4, 1))

    # ---- Frakk (stein-grå — kald respektabel) ----
    pygame.draw.rect(surf, constants.COLOR_STONE_MID, (3, 19, w - 6, 11))
    pygame.draw.rect(surf, constants.COLOR_STONE_LIGHT, (3, 19, 1, 11))
    # Sølv-knapper (lys stone i stedet for varm gull)
    for ky in (21, 24, 27):
        pygame.draw.rect(surf, constants.COLOR_STONE_BRIGHT, (11, ky, 2, 2))
    # Belte
    pygame.draw.rect(surf, constants.COLOR_STONE_DARKEST, (3, 28, w - 6, 1))

    # ---- Bukser (sorte bukser, autoritær) ----
    pygame.draw.rect(surf, constants.COLOR_STONE_DARK, (5, 30, 6, 5))
    pygame.draw.rect(surf, constants.COLOR_STONE_DARK, (13, 30, 6, 5))

    # ---- Sko (svarte, blanke — sølv-spenne) ----
    pygame.draw.rect(surf, constants.COLOR_HAT, (4, 35, 8, 5))
    pygame.draw.rect(surf, constants.COLOR_HAT, (12, 35, 8, 5))
    pygame.draw.rect(surf, constants.COLOR_STONE_BRIGHT, (6, 36, 1, 1))
    pygame.draw.rect(surf, constants.COLOR_STONE_BRIGHT, (16, 36, 1, 1))

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
