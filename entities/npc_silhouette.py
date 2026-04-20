"""NPC-silhuetter for rekvisita-laget (Fase 2.5).

Lette, ikke-interaktive statiske silhuetter som fyller gaten i havn-
scener. Blir blittet i samme fblits-batch som NPC-er og spiller, men
har ingen dialog, ingen state, ingen interaksjon.

Separat fra `entities/npc.py` fordi NPC er forberedt for Fase 3-dialog
og fraksjons-rykte; silhuetter har ingenting av dette og skal være
billige å lage og tegne.

Spec-referanse: `FASE_2_5.md §2.1 e` (Tortuga NPC-silhuetter).
"""

from __future__ import annotations

from dataclasses import dataclass

import pygame

import constants


#: Colorkey brukt av sprite-fabrikkene. Samme magenta som gameplay-laget.
_CK = (255, 0, 255)


@dataclass(frozen=True)
class NPCSilhouette:
    """Statisk silhuett med sprite og verdens-posisjon.

    `y` er top-left (samme konvensjon som NPC og Player). Kalkulert av
    `build_silhouette` fra `ground_top_y - sprite.get_height()` slik at
    føttene hviler på bakken.
    """
    kind: str
    x: float
    y: float
    sprite: pygame.Surface


def _make_standing_sprite() -> pygame.Surface:
    """Stående silhuett — 8×18. Dempet tri-corn, mørk frakk.

    Brukes for "enslige" silhuetter: én person ved en bod eller alene
    på gaten. Palett: HAT/SKIN/STONE_MID — litt kjøligere enn Hawkins
    (som har STONE_LIGHT-aksent) for å gi variasjon uten å introdusere
    nye farger.
    """
    w, h = 8, 18
    surf = pygame.Surface((w, h)).convert()
    surf.fill(_CK)
    # Hatt (tricorn-silhuett)
    pygame.draw.rect(surf, constants.COLOR_HAT, (0, 0, w, 2))
    pygame.draw.rect(surf, constants.COLOR_HAT, (2, 1, w - 4, 2))
    # Ansikt
    pygame.draw.rect(surf, constants.COLOR_SKIN, (2, 3, w - 4, 3))
    # Frakk — STONE_DARK (mørkere enn Hawkins' STONE_MID)
    pygame.draw.rect(surf, constants.COLOR_STONE_DARK, (1, 6, w - 2, 7))
    # Belte-aksent (WOOD_MID)
    pygame.draw.rect(surf, constants.COLOR_WOOD_MID, (1, 12, w - 2, 1))
    # Ben
    pygame.draw.rect(surf, constants.COLOR_HAT, (2, 13, 2, 5))
    pygame.draw.rect(surf, constants.COLOR_HAT, (4, 13, 2, 5))
    surf.set_colorkey(_CK)
    return surf


def _make_sitting_sprite() -> pygame.Surface:
    """Sittende silhuett — 10×13. Kompakt, bøyd over.

    Antyder "en som hviler" ved en bod eller tønne. Lavere profil enn
    stående.
    """
    w, h = 10, 13
    surf = pygame.Surface((w, h)).convert()
    surf.fill(_CK)
    # Hatt (liten, slapp — ikke tricorn)
    pygame.draw.rect(surf, constants.COLOR_HAT, (2, 0, 6, 2))
    # Ansikt — bøyd fremover
    pygame.draw.rect(surf, constants.COLOR_SKIN, (3, 2, 4, 2))
    # Kropp (bøyd) — bredere enn stående
    pygame.draw.rect(surf, constants.COLOR_STONE_DARK, (1, 4, w - 1, 5))
    # Armer som hviler på knær
    pygame.draw.rect(surf, constants.COLOR_STONE_DARKEST, (0, 6, 2, 3))
    pygame.draw.rect(surf, constants.COLOR_STONE_DARKEST, (w - 2, 6, 2, 3))
    # Ben (bøyd, sitter)
    pygame.draw.rect(surf, constants.COLOR_HAT, (2, 9, 3, 4))
    pygame.draw.rect(surf, constants.COLOR_HAT, (5, 9, 3, 4))
    surf.set_colorkey(_CK)
    return surf


def _make_group_sprite() -> pygame.Surface:
    """To personer side ved side — 14×18. Pirater i samtale.

    Tematisk "gruppering" for smugler-havn — aldri én person alene når
    det er handel å gjøre.
    """
    w, h = 14, 18
    surf = pygame.Surface((w, h)).convert()
    surf.fill(_CK)
    # Venstre figur: lik stående, men forskjøvet
    pygame.draw.rect(surf, constants.COLOR_HAT, (0, 0, 7, 2))
    pygame.draw.rect(surf, constants.COLOR_HAT, (1, 1, 5, 2))
    pygame.draw.rect(surf, constants.COLOR_SKIN, (1, 3, 5, 3))
    pygame.draw.rect(surf, constants.COLOR_STONE_DARK, (0, 6, 7, 7))
    pygame.draw.rect(surf, constants.COLOR_HAT, (1, 13, 2, 5))
    pygame.draw.rect(surf, constants.COLOR_HAT, (3, 13, 2, 5))
    # Høyre figur: litt lavere hatt, LANTERN-aksent (varmere frakk)
    pygame.draw.rect(surf, constants.COLOR_HAT, (7, 1, 7, 2))
    pygame.draw.rect(surf, constants.COLOR_HAT, (8, 2, 5, 2))
    pygame.draw.rect(surf, constants.COLOR_SKIN, (8, 4, 5, 3))
    pygame.draw.rect(surf, constants.COLOR_WOOD_MID, (7, 7, 7, 6))
    pygame.draw.rect(surf, constants.COLOR_HAT, (8, 13, 2, 5))
    pygame.draw.rect(surf, constants.COLOR_HAT, (10, 13, 2, 5))
    surf.set_colorkey(_CK)
    return surf


def _make_officer_sprite() -> pygame.Surface:
    """Britisk offiser — 8×19. Tricorn, rød frakk (EMBER), hvit krage.

    Brukes i Port Royal. EMBER (#d96c2e) er master-palettens nærmeste
    røde tone og signaliserer britisk militær-uniform uten å introdusere
    ny farge. Aksent-valget bryter Port Royals "kun varme fra vindus-
    lys"-regel bevisst: historisk signal veier tyngre enn strenge
    tone-regler for et enkelt lite sprite.
    """
    w, h = 8, 19
    surf = pygame.Surface((w, h)).convert()
    surf.fill(_CK)
    # Tricorn-hatt
    pygame.draw.rect(surf, constants.COLOR_HAT, (0, 0, w, 2))
    pygame.draw.rect(surf, constants.COLOR_HAT, (1, 1, w - 2, 2))
    # Ansikt
    pygame.draw.rect(surf, constants.COLOR_SKIN, (2, 3, w - 4, 3))
    # Hvit krage (bredere signal enn Hawkins')
    pygame.draw.rect(surf, constants.COLOR_SHIRT, (1, 6, w - 2, 1))
    # Rød frakk (EMBER)
    pygame.draw.rect(surf, constants.COLOR_EMBER, (1, 7, w - 2, 6))
    # Belte — STONE_DARKEST
    pygame.draw.rect(surf, constants.COLOR_STONE_DARKEST, (1, 12, w - 2, 1))
    # Gylden knapp-strek ned forsiden
    pygame.draw.rect(surf, constants.COLOR_LANTERN_BRIGHT, (4, 8, 1, 4))
    # Hvite benklær (bryk) — STONE_LIGHT antyder hvit
    pygame.draw.rect(surf, constants.COLOR_STONE_LIGHT, (2, 13, 2, 3))
    pygame.draw.rect(surf, constants.COLOR_STONE_LIGHT, (4, 13, 2, 3))
    # Svarte støvler
    pygame.draw.rect(surf, constants.COLOR_HAT, (2, 16, 2, 3))
    pygame.draw.rect(surf, constants.COLOR_HAT, (4, 16, 2, 3))
    surf.set_colorkey(_CK)
    return surf


def _make_merchant_sprite() -> pygame.Surface:
    """Handelsmann — 8×19. Høy sylinderhatt, WOOD-frakk.

    Britisk kolonial kjøpmann: mer formell enn Tortugas pirater.
    Sylinderhatt signaliserer klasse; WOOD_LIGHT-frakk gir varmere
    undertone enn STONE-familien uten å være uniform-rød.
    """
    w, h = 8, 19
    surf = pygame.Surface((w, h)).convert()
    surf.fill(_CK)
    # Sylinderhatt (høyere enn tricorn — 3 px høy topp)
    pygame.draw.rect(surf, constants.COLOR_HAT, (2, 0, 4, 3))
    # Hatt-bredde (brem)
    pygame.draw.rect(surf, constants.COLOR_HAT, (1, 3, w - 2, 1))
    # Ansikt
    pygame.draw.rect(surf, constants.COLOR_SKIN, (2, 4, w - 4, 3))
    # Krage
    pygame.draw.rect(surf, constants.COLOR_SHIRT, (2, 7, w - 4, 1))
    # WOOD_LIGHT-frakk (kjøpmann-brun)
    pygame.draw.rect(surf, constants.COLOR_WOOD_LIGHT, (1, 8, w - 2, 6))
    # Skygge-aksent på høyre side
    pygame.draw.rect(surf, constants.COLOR_WOOD_MID, (w - 2, 8, 1, 6))
    # Ben
    pygame.draw.rect(surf, constants.COLOR_HAT, (2, 14, 2, 5))
    pygame.draw.rect(surf, constants.COLOR_HAT, (4, 14, 2, 5))
    surf.set_colorkey(_CK)
    return surf


def _make_colonial_lady_sprite() -> pygame.Surface:
    """Kolonial dame med parasoll — 10×22. Parasoll stikker opp over
    hodet.

    Parasollen er silhuett-signatur: ingen annen figur i spillet har
    en rund form over seg. Dette gjør kolonial-dame-typen umiddelbart
    gjenkjennelig på avstand.
    """
    w, h = 10, 22
    surf = pygame.Surface((w, h)).convert()
    surf.fill(_CK)
    # Parasoll-topp (rund, STONE_LIGHT for lys-hvit)
    pygame.draw.rect(surf, constants.COLOR_STONE_LIGHT, (2, 0, 6, 1))
    pygame.draw.rect(surf, constants.COLOR_STONE_LIGHT, (1, 1, 8, 2))
    pygame.draw.rect(surf, constants.COLOR_STONE_MID, (1, 3, 8, 1))  # Kant
    # Parasoll-skaft ned til hånd
    pygame.draw.rect(surf, constants.COLOR_HAT, (4, 4, 1, 5))
    # Hodet (under parasollen)
    pygame.draw.rect(surf, constants.COLOR_SKIN, (3, 7, 4, 3))
    # Hår (håret stikker litt ut) — HAT
    pygame.draw.rect(surf, constants.COLOR_HAT, (3, 7, 1, 3))
    pygame.draw.rect(surf, constants.COLOR_HAT, (6, 7, 1, 3))
    # Kjole (lang, bred i bunnen) — STONE_MID hvitkalket-blek
    pygame.draw.rect(surf, constants.COLOR_STONE_MID, (2, 10, w - 4, 4))
    pygame.draw.rect(surf, constants.COLOR_STONE_MID, (1, 14, w - 2, 7))
    # Skygge-aksent
    pygame.draw.rect(surf, constants.COLOR_STONE_DARK, (1, 14, 1, 7))
    # Sko kikker ut under
    pygame.draw.rect(surf, constants.COLOR_HAT, (3, 21, 2, 1))
    pygame.draw.rect(surf, constants.COLOR_HAT, (5, 21, 2, 1))
    surf.set_colorkey(_CK)
    return surf


def _make_priest_sprite() -> pygame.Surface:
    """Katolsk prest — 8×20. Lang mørk kappe med hette.

    Brukes i Havana. Silhuetten er bevisst uten ansiktsdetaljer
    (hetten skygger for øynene) — antyder "religiøs autoritet" via
    den enkle omrisset. Palett: STONE_DARK-kappe med STONE_DARKEST-
    skygger. Ingen varme farger for å unngå konkurranse med
    Havanas LANTERN-baserte varme palett — presten er et stille
    mørk-element.
    """
    w, h = 8, 20
    surf = pygame.Surface((w, h)).convert()
    surf.fill(_CK)
    # Hette (topp rund, spisser seg)
    pygame.draw.rect(surf, constants.COLOR_STONE_DARKEST, (2, 0, 4, 1))
    pygame.draw.rect(surf, constants.COLOR_STONE_DARKEST, (1, 1, 6, 3))
    # Ansikt (små glimt av hud under hetten)
    pygame.draw.rect(surf, constants.COLOR_SKIN, (3, 4, 2, 2))
    # Lang kappe — bred på skuldrene, litt inn på livet, så bred ned
    pygame.draw.rect(surf, constants.COLOR_STONE_DARK, (0, 6, w, 2))
    pygame.draw.rect(surf, constants.COLOR_STONE_DARK, (1, 8, w - 2, 8))
    pygame.draw.rect(surf, constants.COLOR_STONE_DARK, (0, 16, w, 4))
    # Kappens skygge (vertikal linje på høyre side)
    pygame.draw.rect(surf, constants.COLOR_STONE_DARKEST, (w - 1, 6, 1, 14))
    # Kors på brystet — LANTERN for gylden metallglimt
    pygame.draw.rect(surf, constants.COLOR_LANTERN, (3, 10, 2, 1))
    pygame.draw.rect(surf, constants.COLOR_LANTERN, (4, 9, 1, 3))
    surf.set_colorkey(_CK)
    return surf


def _make_spanish_officer_sprite() -> pygame.Surface:
    """Spansk offiser med morion-hjelm — 9×19.

    Morionen er distinkt sprite-signatur: buet topp med fremoverkant
    (andre hjelmformer er sjeldne i spillet). LANTERN-aksent på
    hjelm-kanten antyder metall-refleksjon fra festlys.
    """
    w, h = 9, 19
    surf = pygame.Surface((w, h)).convert()
    surf.fill(_CK)
    # Morion-hjelm: buet topp (3 rader) + fremoverkant
    pygame.draw.rect(surf, constants.COLOR_STONE_DARKEST, (3, 0, 3, 1))
    pygame.draw.rect(surf, constants.COLOR_STONE_DARKEST, (2, 1, 5, 1))
    pygame.draw.rect(surf, constants.COLOR_STONE_DARKEST, (1, 2, 7, 2))
    # Kam-detalj på toppen (høy rygg)
    pygame.draw.rect(surf, constants.COLOR_STONE_DARKEST, (4, 0, 1, 3))
    # Metallrefleksjon-høylys
    pygame.draw.rect(surf, constants.COLOR_LANTERN, (2, 2, 1, 1))
    # Ansikt
    pygame.draw.rect(surf, constants.COLOR_SKIN, (3, 4, w - 6, 3))
    # Krage
    pygame.draw.rect(surf, constants.COLOR_SHIRT, (2, 7, w - 4, 1))
    # Drakt — oker/LANTERN (spansk rik varm)
    pygame.draw.rect(surf, constants.COLOR_LANTERN, (1, 8, w - 2, 6))
    # Rustnings-skyggelinje
    pygame.draw.rect(surf, constants.COLOR_EMBER, (1, 9, w - 2, 1))
    pygame.draw.rect(surf, constants.COLOR_EMBER, (1, 12, w - 2, 1))
    # Belte
    pygame.draw.rect(surf, constants.COLOR_STONE_DARKEST, (1, 13, w - 2, 1))
    # Ben
    pygame.draw.rect(surf, constants.COLOR_WOOD_DARK, (3, 14, 2, 5))
    pygame.draw.rect(surf, constants.COLOR_WOOD_DARK, (5, 14, 2, 5))
    surf.set_colorkey(_CK)
    return surf


def _make_spanish_merchant_sprite() -> pygame.Surface:
    """Spansk handelsmann — 9×19. Bred-bremshatt + rik WOOD-drakt.

    Bred hatt skiller seg fra britiske handelsmannens sylinderhatt.
    Rik WOOD_MID-drakt med EMBER-skjerf-aksent signaliserer
    "velhavende spansk handelsmann" uten å konkurrere med prestens
    mørke autoritet eller offiserens metall.
    """
    w, h = 9, 19
    surf = pygame.Surface((w, h)).convert()
    surf.fill(_CK)
    # Bred hatt (7 px — bredere enn ansiktet)
    pygame.draw.rect(surf, constants.COLOR_HAT, (1, 2, w - 2, 1))
    # Hatt-krone
    pygame.draw.rect(surf, constants.COLOR_HAT, (2, 0, 5, 2))
    # Hatt-bånd (EMBER-aksent)
    pygame.draw.rect(surf, constants.COLOR_EMBER, (2, 1, 5, 1))
    # Ansikt
    pygame.draw.rect(surf, constants.COLOR_SKIN, (3, 3, w - 6, 3))
    # Skjerf (EMBER — rødt over krage)
    pygame.draw.rect(surf, constants.COLOR_EMBER, (2, 6, w - 4, 1))
    # Drakt (WOOD_MID — rik brun)
    pygame.draw.rect(surf, constants.COLOR_WOOD_MID, (1, 7, w - 2, 7))
    # Frakk-kant
    pygame.draw.rect(surf, constants.COLOR_WOOD_LIGHT, (1, 7, 1, 7))
    # Knappe-rekke (LANTERN_BRIGHT)
    pygame.draw.rect(surf, constants.COLOR_LANTERN_BRIGHT, (4, 9, 1, 1))
    pygame.draw.rect(surf, constants.COLOR_LANTERN_BRIGHT, (4, 11, 1, 1))
    # Ben
    pygame.draw.rect(surf, constants.COLOR_WOOD_DARK, (3, 14, 2, 5))
    pygame.draw.rect(surf, constants.COLOR_WOOD_DARK, (5, 14, 2, 5))
    surf.set_colorkey(_CK)
    return surf


def _make_mantilla_woman_sprite() -> pygame.Surface:
    """Kvinne med mantilla — 8×20. Sjal over hodet som henger ned
    over skuldrene.

    Mantilla-silhuetten er distinkt fra kolonial-damens parasoll
    (som er rund over hodet). Mantillaen er bred på skuldrene og
    smaler inn mot midjen. Palett: LANTERN-toner (varm kvinnelig
    figur — kontrast mot prestens mørke).
    """
    w, h = 8, 20
    surf = pygame.Surface((w, h)).convert()
    surf.fill(_CK)
    # Mantilla-topp (ovalt over hodet) — EMBER (rik rød-oker)
    pygame.draw.rect(surf, constants.COLOR_EMBER, (2, 0, 4, 1))
    pygame.draw.rect(surf, constants.COLOR_EMBER, (1, 1, 6, 2))
    # Ansikt
    pygame.draw.rect(surf, constants.COLOR_SKIN, (2, 3, 4, 3))
    # Mantilla faller ned over skuldrene (bred)
    pygame.draw.rect(surf, constants.COLOR_EMBER, (0, 6, w, 3))
    pygame.draw.rect(surf, constants.COLOR_EMBER, (1, 9, w - 2, 2))
    # Kjole (LANTERN — varm oker)
    pygame.draw.rect(surf, constants.COLOR_LANTERN, (1, 11, w - 2, 4))
    pygame.draw.rect(surf, constants.COLOR_LANTERN, (0, 15, w, 5))
    # Kjole-skygge
    pygame.draw.rect(surf, constants.COLOR_EMBER, (0, 15, 1, 5))
    # Sko kikker ut
    pygame.draw.rect(surf, constants.COLOR_HAT, (2, 19, 2, 1))
    pygame.draw.rect(surf, constants.COLOR_HAT, (4, 19, 2, 1))
    surf.set_colorkey(_CK)
    return surf


_SPRITE_FACTORIES = {
    "standing": _make_standing_sprite,
    "sitting": _make_sitting_sprite,
    "group": _make_group_sprite,
    "officer": _make_officer_sprite,
    "merchant": _make_merchant_sprite,
    "colonial_lady": _make_colonial_lady_sprite,
    "priest": _make_priest_sprite,
    "spanish_officer": _make_spanish_officer_sprite,
    "spanish_merchant": _make_spanish_merchant_sprite,
    "mantilla_woman": _make_mantilla_woman_sprite,
}

#: Gyldige silhuett-typer. Brukes av port_config.py for validering.
VALID_KINDS: frozenset[str] = frozenset(_SPRITE_FACTORIES.keys())


def build_silhouette(kind: str, x: int, ground_top_y: int) -> NPCSilhouette:
    """Bygg silhuett med sprite festet til ground_top_y.

    Kaster `ValueError` hvis `kind` ikke er en gyldig type. Sprite-
    høyden avgjør y-koordinaten (føttene hviler på bakken).
    """
    factory = _SPRITE_FACTORIES.get(kind)
    if factory is None:
        raise ValueError(
            f"Ukjent silhouette-kind: {kind!r} (gyldige: {sorted(VALID_KINDS)})"
        )
    sprite = factory()
    y = ground_top_y - sprite.get_height()
    return NPCSilhouette(kind=kind, x=float(x), y=float(y), sprite=sprite)
