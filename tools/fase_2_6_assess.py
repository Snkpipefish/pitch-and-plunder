"""Sub-steg 1 visuell assessment.

Renderer alle scener på den nye 480×270-oppløsningen og dokumenterer det
visuelle bruddet. Output:
  tools/fase_2_6_village_day.png
  tools/fase_2_6_village_night.png
  tools/fase_2_6_world_map.png
  tools/fase_2_6_voyage.png
"""
from __future__ import annotations

import os
import sys

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
os.environ.setdefault("SDL_HINT_RENDER_SCALE_QUALITY", "0")
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import constants  # noqa: E402

pygame.display.init()
pygame.font.init()
pygame.display.set_mode((1, 1))

from systems import balance  # noqa: E402
balance.init()
from config import port_config  # noqa: E402
port_config.init()

OUT_DIR = os.path.dirname(os.path.abspath(__file__))


def save_at(surf, name):
    out = os.path.join(OUT_DIR, f"fase_2_6_{name}.png")
    big = pygame.transform.scale(surf, (surf.get_width() * 4, surf.get_height() * 4))
    pygame.image.save(big, out)
    print(f"  -> {out}")


def render_village(force_day: bool):
    from scenes.port_village import PortVillageScene
    from state import GameState
    state = GameState()
    state.world_state.clock.day = 1
    if force_day:
        state.world_state.clock.seconds_into_day = (
            state.world_state.clock.seconds_per_day * 0.40
        )
    font = pygame.font.SysFont(None, 12)
    scene = PortVillageScene(font, state, port_config.get(state.world_state.current_port))
    scene.on_enter(state, from_scene=None)
    surf = pygame.Surface((constants.RENDER_WIDTH, constants.RENDER_HEIGHT)).convert()
    for _ in range(120):
        scene.update(0.0166)
    # Sentrer over taverna for å se hengende skilt + skorsteinsrøyk.
    scene._camera.set_x(0.0)
    try:
        scene.draw(surf)
    except Exception as exc:
        print(f"  KRASJ ved village.draw: {exc}")
        return None
    return surf


def render_world_map():
    from scenes.world_map import WorldMapScene
    from state import GameState
    state = GameState()
    font = pygame.font.SysFont(None, 12)
    scene = WorldMapScene(font, state)
    scene.on_enter(state, from_scene=None)
    surf = pygame.Surface((constants.RENDER_WIDTH, constants.RENDER_HEIGHT)).convert()
    try:
        scene.draw(surf)
    except Exception as exc:
        print(f"  KRASJ ved world_map.draw: {exc}")
        return None
    return surf


def render_voyage():
    from scenes.voyage import VoyageScene
    from state import GameState
    from systems import voyage as voyage_module
    state = GameState()
    state.player_state.gold = 100
    voyage_module.start_voyage(
        state, balance.get(), "tortuga", "port_royal",
    )
    font = pygame.font.SysFont(None, 12)
    scene = VoyageScene(font, state)
    scene.on_enter(state, from_scene=None)
    surf = pygame.Surface((constants.RENDER_WIDTH, constants.RENDER_HEIGHT)).convert()
    for _ in range(60):
        scene.update(0.0166)
    try:
        scene.draw(surf)
    except Exception as exc:
        print(f"  KRASJ ved voyage.draw: {exc}")
        return None
    return surf


print(f"RENDER_WIDTH={constants.RENDER_WIDTH}  RENDER_HEIGHT={constants.RENDER_HEIGHT}")

print("village (dag)...")
v_day = render_village(True)
if v_day is not None:
    save_at(v_day, "village_day")

print("village (natt)...")
v_night = render_village(False)
if v_night is not None:
    save_at(v_night, "village_night")

print("world_map...")
wm = render_world_map()
if wm is not None:
    save_at(wm, "world_map")

print("voyage...")
vo = render_voyage()
if vo is not None:
    save_at(vo, "voyage")

pygame.display.quit()
