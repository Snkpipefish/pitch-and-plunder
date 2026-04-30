"""Generer en side-ved-side-sammenligning av oppløsnings/sprite-veiene.

Lager en PNG som viser samme mock-Tortuga-scene rendret i:
  - Nåværende:  640×360 intern, 16×16 hovedsprite
  - Vei B:      480×270 intern, 32×48 hovedsprite
  - Vei C:      320×180 intern, 32×48 hovedsprite

Alle skaleres til samme display-størrelse (960×540) med nearest-neighbor
slik at de visuelle pikselstørrelse blir direkte sammenlignbar.

Output: tools/size_compare.png
"""

from __future__ import annotations

import os
import sys

# Sett env-vars FØR pygame importeres.
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
os.environ.setdefault("SDL_HINT_RENDER_SCALE_QUALITY", "0")
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import constants  # noqa: E402


def draw_scene(surface: pygame.Surface, sprite_w: int, sprite_h: int) -> None:
    """Tegn en mock-Tortuga-natt-scene.

    Komposisjon: indigo himmel, måne, tavernasilhuett til venstre med
    varmt vindu, børshus til høyre med kaldt vindu, hovedperson på gaten.
    Sprite-størrelsen styrer detaljnivået.
    """
    w, h = surface.get_size()

    # Himmel (gradient via to fargebånd)
    surface.fill(constants.COLOR_SKY_DEEP)
    pygame.draw.rect(surface, constants.COLOR_SKY_MID, (0, h // 3, w, h // 3))
    pygame.draw.rect(surface, constants.COLOR_SKY_HORIZON, (0, 2 * h // 3, w, h // 3))

    # Måne
    moon_r = max(4, h // 24)
    moon_x = int(w * 0.78)
    moon_y = int(h * 0.18)
    pygame.draw.circle(surface, constants.COLOR_MOON_HALO, (moon_x, moon_y), moon_r + 1)
    pygame.draw.circle(surface, constants.COLOR_MOON_CORE, (moon_x, moon_y), moon_r)

    # Stjerner
    for sx, sy in [(0.10, 0.12), (0.22, 0.20), (0.40, 0.08),
                   (0.55, 0.15), (0.92, 0.25), (0.65, 0.06)]:
        surface.set_at((int(sx * w), int(sy * h)), constants.COLOR_MOON_CORE)

    # Hav (nederste fjerdedel)
    sea_top = int(h * 0.72)
    pygame.draw.rect(surface, constants.COLOR_SEA_DEEP, (0, sea_top, w, h - sea_top))
    pygame.draw.rect(
        surface, constants.COLOR_SEA_MID,
        (0, sea_top, w, max(2, h // 32)),
    )

    # Bakke
    ground_top = int(h * 0.78)
    pygame.draw.rect(surface, constants.COLOR_WOOD_DARK, (0, ground_top, w, h - ground_top))

    # Taverna (venstre, varmt vindu)
    tav_w = int(w * 0.22)
    tav_h = int(h * 0.40)
    tav_x = int(w * 0.08)
    tav_y = ground_top - tav_h
    pygame.draw.rect(surface, constants.COLOR_WOOD_DARKEST, (tav_x, tav_y, tav_w, tav_h))
    pygame.draw.rect(surface, constants.COLOR_WOOD_MID, (tav_x, tav_y, tav_w, max(2, h // 60)))
    # Vindu (varmt)
    win_w = max(3, tav_w // 5)
    win_h = max(3, tav_h // 4)
    win_x = tav_x + tav_w // 3
    win_y = tav_y + tav_h // 2
    pygame.draw.rect(surface, constants.COLOR_LANTERN_BRIGHT, (win_x, win_y, win_w, win_h))
    # Varm glød (additiv)
    glow = pygame.Surface((win_w * 3, win_h * 3), pygame.SRCALPHA)
    pygame.draw.circle(
        glow, (*constants.COLOR_LANTERN, 80),
        (win_w * 3 // 2, win_h * 3 // 2), max(2, win_w),
    )
    surface.blit(
        glow, (win_x - win_w, win_y - win_h),
        special_flags=pygame.BLEND_RGB_ADD,
    )

    # Børshus (høyre, kaldt vindu)
    bor_w = int(w * 0.20)
    bor_h = int(h * 0.45)
    bor_x = int(w * 0.70)
    bor_y = ground_top - bor_h
    pygame.draw.rect(surface, constants.COLOR_STONE_DARK, (bor_x, bor_y, bor_w, bor_h))
    pygame.draw.rect(surface, constants.COLOR_STONE_MID, (bor_x, bor_y, bor_w, max(2, h // 60)))
    # Vindu (kaldt)
    bwin_w = max(3, bor_w // 5)
    bwin_h = max(3, bor_h // 4)
    bwin_x = bor_x + bor_w // 2 - bwin_w // 2
    bwin_y = bor_y + bor_h // 3
    pygame.draw.rect(surface, constants.COLOR_STONE_BRIGHT, (bwin_x, bwin_y, bwin_w, bwin_h))

    # Hovedsprite (player) — sentrert på gaten foran
    player_x = w // 2 - sprite_w // 2
    player_y = ground_top - sprite_h
    _draw_player(surface, player_x, player_y, sprite_w, sprite_h)

    # Skala-indikator (sprite-pikselstørrelse i hjørnet)
    label_color = constants.COLOR_MOON_CORE
    pygame.draw.rect(surface, (0, 0, 0), (2, 2, max(40, sprite_w + 4), 8))
    # 1-piksel-rektangel som viser sprite-størrelse-eksempel
    pygame.draw.rect(surface, label_color, (3, 3, sprite_w, 6), 1)


def _draw_player(
    surface: pygame.Surface, x: int, y: int, w: int, h: int,
) -> None:
    """Tegn en hovedperson med detaljnivå proporsjonalt med sprite-størrelsen.

    16×16: grov silhuett (hatt, frakk, ben).
    32×48: ansikt, krage, frakkfolder, støvler.
    32×64: enda mer detalj.
    """
    # Grov anatomi: hatt 25 %, ansikt 15 %, krage 8 %, frakk 40 %, ben 12 %
    hat_h = max(2, int(h * 0.20))
    face_h = max(2, int(h * 0.16))
    collar_h = max(1, int(h * 0.06))
    coat_h = max(2, int(h * 0.40))
    legs_h = max(2, h - hat_h - face_h - collar_h - coat_h)

    # Hatt
    hat_brim_h = max(1, hat_h // 3)
    pygame.draw.rect(surface, constants.COLOR_HAT,
                     (x, y + hat_h - hat_brim_h, w, hat_brim_h))
    pygame.draw.rect(surface, constants.COLOR_HAT,
                     (x + w // 4, y, w // 2, hat_h - hat_brim_h))

    # Ansikt
    face_y = y + hat_h
    pygame.draw.rect(surface, constants.COLOR_SKIN,
                     (x + w // 4, face_y, w // 2, face_h))
    if w >= 24:
        # Øyne (kun synlig på ≥24 px bredde)
        eye_y = face_y + face_h // 3
        pygame.draw.rect(surface, constants.COLOR_HAT,
                         (x + w // 4 + max(1, w // 12), eye_y,
                          max(1, w // 16), max(1, h // 48)))
        pygame.draw.rect(surface, constants.COLOR_HAT,
                         (x + w - w // 4 - max(2, w // 12), eye_y,
                          max(1, w // 16), max(1, h // 48)))
    if w >= 32 and h >= 48:
        # Skjegg (kun ≥32×48)
        beard_y = face_y + face_h * 2 // 3
        pygame.draw.rect(surface, constants.COLOR_HAT,
                         (x + w // 4, beard_y, w // 2, max(1, face_h // 4)))

    # Krage
    collar_y = face_y + face_h
    pygame.draw.rect(surface, constants.COLOR_SHIRT,
                     (x + w // 5, collar_y, w * 3 // 5, collar_h))

    # Frakk
    coat_y = collar_y + collar_h
    pygame.draw.rect(surface, constants.COLOR_COAT,
                     (x, coat_y, w, coat_h))
    if w >= 24:
        # Knapper / knappestripe
        button_x = x + w // 2
        for i in range(3):
            by = coat_y + (coat_h // 4) * (i + 1) - 1
            pygame.draw.rect(surface, constants.COLOR_LANTERN,
                             (button_x - max(1, w // 32), by,
                              max(1, w // 16), max(1, w // 16)))
    if w >= 32:
        # Belte-detalj
        belt_y = coat_y + coat_h * 2 // 3
        pygame.draw.rect(surface, constants.COLOR_WOOD_DARKEST,
                         (x, belt_y, w, max(1, h // 48)))

    # Ben / støvler
    legs_y = coat_y + coat_h
    leg_w = max(1, w // 3)
    pygame.draw.rect(surface, constants.COLOR_WOOD_DARKEST,
                     (x + w // 6, legs_y, leg_w, legs_h))
    pygame.draw.rect(surface, constants.COLOR_WOOD_DARKEST,
                     (x + w - w // 6 - leg_w, legs_y, leg_w, legs_h))


def render_panel(label: str, internal: tuple, sprite: tuple,
                 panel_size: tuple, font: pygame.font.Font) -> pygame.Surface:
    """Render én panel: scene + label-bånd."""
    iw, ih = internal
    sw, sh = sprite
    pw, ph = panel_size

    scene = pygame.Surface(internal).convert()
    draw_scene(scene, sw, sh)

    # Skaler scenen til panel_w × (proportional høyde) med nearest-neighbor
    scaled_h = pw * ih // iw
    scaled = pygame.transform.scale(scene, (pw, scaled_h))

    panel = pygame.Surface(panel_size).convert()
    panel.fill((20, 20, 24))
    panel.blit(scaled, (0, 0))

    # Label-bånd nederst
    band_y = scaled_h
    band_h = ph - scaled_h
    pygame.draw.rect(panel, (10, 10, 14), (0, band_y, pw, band_h))
    text1 = font.render(label, True, constants.COLOR_MOON_CORE)
    text2_str = (f"intern {iw}×{ih}   sprite {sw}×{sh}px   "
                 f"({sw*sh} pikselbudsjett)")
    text2 = font.render(text2_str, True, constants.COLOR_STONE_LIT)
    panel.blit(text1, (8, band_y + 4))
    panel.blit(text2, (8, band_y + 4 + text1.get_height() + 2))
    return panel


def main() -> int:
    pygame.display.init()
    pygame.font.init()
    pygame.display.set_mode((1, 1))  # dummy

    try:
        font = pygame.font.Font("assets/fonts/PublicPixel.ttf", 10)
    except (pygame.error, FileNotFoundError):
        font = pygame.font.SysFont(None, 14)

    # Display-størrelse per panel (ingen integer-skala — den varierer per
    # vei. Det vi vil sammenligne er hvordan sprites SER UT på samme skjerm-
    # størrelse, ikke heltallsskalaer.)
    panel_w = 960
    panel_h = panel_w * 9 // 16 + 30  # 16:9 + label-bånd

    panels = [
        render_panel(
            "NÅVÆRENDE  – 16×16 sprite på 640×360",
            (640, 360), (16, 16), (panel_w, panel_h), font,
        ),
        render_panel(
            "VEI B  – 32×48 sprite på 480×270   (anbefalt)",
            (480, 270), (32, 48), (panel_w, panel_h), font,
        ),
        render_panel(
            "VEI C  – 32×48 sprite på 320×180",
            (320, 180), (32, 48), (panel_w, panel_h), font,
        ),
    ]

    out_w = panel_w
    out_h = panel_h * len(panels) + 8 * (len(panels) - 1)
    out = pygame.Surface((out_w, out_h)).convert()
    out.fill((0, 0, 0))
    y = 0
    for p in panels:
        out.blit(p, (0, y))
        y += panel_h + 8

    target = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "size_compare.png",
    )
    pygame.image.save(out, target)
    print(f"Skrevet: {target}  ({out_w}×{out_h})")

    pygame.display.quit()
    return 0


if __name__ == "__main__":
    sys.exit(main())
