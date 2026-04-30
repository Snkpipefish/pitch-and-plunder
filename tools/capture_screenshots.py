"""Engangs-skript som genererer README-skjermbilder.

Bygger flere scener via samme fabrikk-mønster som benchmark.py og lagrer
hver scene som PNG i `docs/screenshots/`. Justerer `seconds_into_day` for
å fange ulike lysforhold (dag, kveld, natt).

Kjøres en gang for å regenerere screenshots:
    python tools/capture_screenshots.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import constants  # noqa: E402
import pygame  # noqa: E402

from config import port_config  # noqa: E402
from main import _load_font  # noqa: E402
from scenes.port_village import PortVillageScene  # noqa: E402
from scenes.voyage import VoyageScene  # noqa: E402
from scenes.world_map import WorldMapScene  # noqa: E402
from state import GameState  # noqa: E402
from systems import balance as balance_module  # noqa: E402
from systems import save as save_module  # noqa: E402
from systems import voyage as voyage_module  # noqa: E402

OUT_DIR = ROOT / "docs" / "screenshots"


def _settle(scene, state, frames: int = 60, dt: float = 1.0 / 60.0) -> None:
    """Tikk scenen i N frames slik at lighting/animasjoner konvergerer."""
    surface = pygame.Surface(
        (constants.RENDER_WIDTH, constants.RENDER_HEIGHT)
    ).convert()
    for _ in range(frames):
        scene.update(dt)
        scene.draw(surface)


def _shoot(scene, name: str, scale: int = 3) -> Path:
    """Render scenen til en PNG, oppskalert med nearest-neighbor."""
    surface = pygame.Surface(
        (constants.RENDER_WIDTH, constants.RENDER_HEIGHT)
    ).convert()
    scene.draw(surface)
    if scale != 1:
        scaled = pygame.transform.scale(
            surface,
            (constants.RENDER_WIDTH * scale, constants.RENDER_HEIGHT * scale),
        )
    else:
        scaled = surface
    path = OUT_DIR / f"{name}.png"
    pygame.image.save(scaled, str(path))
    print(f"  → {path.relative_to(ROOT)} ({scaled.get_width()}x{scaled.get_height()})")
    return path


def _new_state(seconds_into_day: float = 0.4 * 180.0) -> GameState:
    """Fersk GameState med litt gull og spesifisert tidspunkt på dagen."""
    state = GameState()
    state.player_state.gold = 500
    state.world_state.clock.seconds_into_day = seconds_into_day
    return state


def capture_village_day() -> None:
    print("village_day (Tortuga, midt på dagen)")
    state = _new_state(seconds_into_day=0.45 * 180.0)
    scene = PortVillageScene(
        _load_font(8), state, port_config.get(state.world_state.current_port)
    )
    scene.on_enter(state, from_scene=None)
    _settle(scene, state, frames=30)
    _shoot(scene, "village_day")


def capture_village_night() -> None:
    print("village_night (Tortuga, natt med lanterner)")
    state = _new_state(seconds_into_day=0.95 * 180.0)
    scene = PortVillageScene(
        _load_font(8), state, port_config.get(state.world_state.current_port)
    )
    scene.on_enter(state, from_scene=None)
    _settle(scene, state, frames=60)
    _shoot(scene, "village_night")


def capture_exchange() -> None:
    print("exchange (børs-overlay over Tortuga)")
    state = _new_state(seconds_into_day=0.5 * 180.0)
    scene = PortVillageScene(
        _load_font(8), state, port_config.get(state.world_state.current_port)
    )
    scene.on_enter(state, from_scene=None)
    scene._player.x = 1465.0
    scene._center_camera_on_player()
    scene._open_exchange()
    _settle(scene, state, frames=30)
    _shoot(scene, "exchange")


def capture_world_map() -> None:
    print("world_map (verdenskart)")
    state = _new_state()
    scene = WorldMapScene(_load_font(8), state)
    scene.on_enter(state, from_scene=None)
    _settle(scene, state, frames=30)
    _shoot(scene, "world_map")


def capture_voyage() -> None:
    print("voyage (skipet på reise)")
    state = _new_state()
    voyage_module.start_voyage(
        state, balance_module.get(), "tortuga", "port_royal"
    )
    scene = VoyageScene(_load_font(8), state)
    scene.on_enter(state, from_scene=None)
    state.world_state.clock.seconds_into_day = 0.5 * 75.0
    _settle(scene, state, frames=60)
    _shoot(scene, "voyage")


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    save_module.save = lambda *a, **kw: True

    if not os.environ.get("DISPLAY") and not os.environ.get("WAYLAND_DISPLAY"):
        os.environ["SDL_VIDEODRIVER"] = "dummy"

    pygame.display.init()
    pygame.font.init()
    pygame.event.set_blocked(constants.BLOCKED_EVENTS)
    pygame.display.set_mode(
        (constants.RENDER_WIDTH, constants.RENDER_HEIGHT), pygame.HIDDEN
    )

    capture_village_day()
    capture_village_night()
    capture_exchange()
    capture_world_map()
    capture_voyage()

    pygame.display.quit()
    pygame.font.quit()
    print(f"\nFerdig. {len(list(OUT_DIR.glob('*.png')))} bilder i {OUT_DIR.relative_to(ROOT)}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
