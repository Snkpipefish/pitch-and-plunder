"""End-to-end-test av ModernGL post-FX-pipelinen mot ekte Tortuga.

Renderer Tortuga til 640x360 surface, sender den gjennom shader-pipelinen,
og leser tilbake fra default framebuffer. Sammenligner mot ren pygame-
output. Output:
  tools/postfx_baseline.png  — ren pygame, ingen shader
  tools/postfx_high.png      — pygame → ModernGL post-FX
"""
from __future__ import annotations

import os
import sys

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
os.environ.setdefault("SDL_HINT_RENDER_SCALE_QUALITY", "0")
os.environ.setdefault("SDL_VIDEODRIVER", "x11")

import pygame  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import constants  # noqa: E402

pygame.display.init()
pygame.font.init()

from systems import balance  # noqa: E402
balance.init()
from config import port_config  # noqa: E402
port_config.init()


def render_scene(force_day: bool = True) -> pygame.Surface:
    """Bygg én Tortuga-frame som 640x360 surface."""
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
    for _ in range(180):
        scene.update(0.0166)
    scene._camera.set_x(120.0)
    scene.draw(surf)
    return surf


# ---- Pass 1: ren pygame baseline ----
pygame.display.set_mode((1, 1))
baseline = render_scene(force_day=True)
big_baseline = pygame.transform.scale(baseline, (1920, 1080))
out1 = os.path.join(os.path.dirname(os.path.abspath(__file__)), "postfx_baseline.png")
pygame.image.save(big_baseline, out1)
print(f"Skrevet baseline: {out1}")
pygame.display.quit()

# ---- Pass 2: ModernGL high-preset ----
pygame.display.init()
window = pygame.display.set_mode((1280, 720), pygame.OPENGL | pygame.DOUBLEBUF)
from systems import post_fx  # noqa: E402
pipeline = post_fx.PostFXPipeline.try_create(window_size=(1280, 720))
if pipeline is None:
    print("PostFX init feilet — kan ikke generere high-preset-bilde")
    sys.exit(1)

# Re-bygge scenen i denne nye GL-konteksten (pygame.font.SysFont krever
# fresh font-init etter set_mode-bytte)
pygame.font.init()
shaded = render_scene(force_day=True)
pipeline.present(shaded, flip=False)  # ikke flip — vi vil lese fra back buffer
# Les tilbake default framebuffer (1280x720) FØR flip
import moderngl  # noqa: E402
ctx = pipeline.ctx
data = ctx.screen.read(viewport=(0, 0, 1280, 720), components=3)
# moderngl gir bytes i bottom-up rekkefølge (OpenGL-konvensjon)
# pygame trenger top-down, så vi flipper
import numpy as np  # noqa: E402
arr = np.frombuffer(data, dtype=np.uint8).reshape(720, 1280, 3)
arr = np.flipud(arr).copy()
out_surface = pygame.image.frombuffer(arr.tobytes(), (1280, 720), "RGB")
out2 = os.path.join(os.path.dirname(os.path.abspath(__file__)), "postfx_high.png")
pygame.image.save(out_surface, out2)
print(f"Skrevet high-preset: {out2}")

pipeline.release()
pygame.display.quit()
