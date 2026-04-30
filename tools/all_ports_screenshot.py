"""Render alle 4 havner med fokus på en kjent skorstein/bål-posisjon
slik at vi kan verifisere at røyken kommer fra rett sted.
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

from scenes.port_village import PortVillageScene  # noqa: E402
from systems import save  # noqa: E402

OUT_DIR = os.path.dirname(os.path.abspath(__file__))

# Camera-fokus per havn (skorstein/bål vi vil vise).
PORT_CAMERAS = {
    "tortuga": 50.0,        # taverna med skorstein
    "port_royal": 250.0,    # soldier_barracks (x=232+58/2 ≈ 261)
    "havana": 950.0,        # artisans_workshop (x=968)
    "nassau": 220.0,        # bål 1 (x=240)
}

font = pygame.font.SysFont(None, 12)

for port_id, cam_x in PORT_CAMERAS.items():
    state = save.new_game_state()
    state.world_state.current_port = port_id
    state.world_state.clock.day = 1
    state.world_state.clock.seconds_into_day = (
        state.world_state.clock.seconds_per_day * 0.40
    )
    scene = PortVillageScene(font, state, port_config.get(port_id))
    scene.on_enter(state, from_scene=None)
    surf = pygame.Surface((constants.RENDER_WIDTH, constants.RENDER_HEIGHT)).convert()
    for _ in range(180):
        scene.update(0.0166)
    scene._camera.set_x(cam_x)
    scene.draw(surf)
    big = pygame.transform.scale(surf, (surf.get_width() * 4, surf.get_height() * 4))
    out = os.path.join(OUT_DIR, f"all_ports_{port_id}.png")
    pygame.image.save(big, out)
    print(f"  -> {out}")

pygame.display.quit()
