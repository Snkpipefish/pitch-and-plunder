"""Quick screenshot of Tortuga med flygende fugler — visuell verifikasjon.

Kjør: python tools/birds_screenshot.py
Output: tools/birds_screenshot.png
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
from state import GameState  # noqa: E402

state = GameState()
# Tving dag-tid via clock-manipulering — vi vil se fuglene flyr.
state.world_state.clock.day = 1
# Tving seconds_into_day så day_fraction ~ 0.40 (formiddag).
state.world_state.clock.seconds_into_day = (
    state.world_state.clock.seconds_per_day * 0.40
)
font = pygame.font.SysFont(None, 12)
scene = PortVillageScene(font, state, port_config.get(state.world_state.current_port))
scene.on_enter(state, from_scene=None)

# Kjør noen frames slik at fuglene har beveget seg fra spawn-pos.
surf = pygame.Surface((640, 360)).convert()
for _ in range(180):  # ~3 sek på 60 fps
    scene.update(0.0166)

# Plasser kameraet midt i Tortuga slik at vi ser bygninger + fugler.
scene._camera.set_x(120.0)  # peker mot Tortuga-essen for å se røyk

from systems.day_cycle import DayCycle, compute_night_factor  # noqa: E402
celestial_cfg = port_config.get(state.world_state.current_port).celestial
snap = DayCycle.compute_snapshot(state.world_state.clock, celestial_cfg)
nf = compute_night_factor(snap.day_fraction)
print(f"day_fraction={snap.day_fraction:.3f}  night_factor={nf:.3f}  "
      f"sleep_thr={scene._flying_birds.config.sleep_threshold}")
scene.draw(surf)

# 4× upskala for synlighet
big = pygame.transform.scale(surf, (640 * 3, 360 * 3))
target = os.path.join(os.path.dirname(os.path.abspath(__file__)), "birds_screenshot.png")
pygame.image.save(big, target)
print(f"Skrevet: {target} ({big.get_width()}×{big.get_height()})")
print(f"Fugler i flokk: {len(scene._flying_birds._birds)}")
print(f"Night factor: {scene._flying_birds.config.sleep_threshold}")

pygame.display.quit()
