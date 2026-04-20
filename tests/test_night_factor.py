"""Tester for Fase 2.5 C2.5-8b dag/natt-lys-gating.

Dekker:
- `compute_night_factor` returnerer riktige verdier ved kritiske
  day_fraction-punkter
- LightingSystem.draw respekterer night_factor-threshold
- Bygnings-bake-funksjoner produserer forskjellige piksel-mønstre
  ved night_lights=True vs False
- build_port_gameplay_layer returnerer (day, night) tuple
"""

from __future__ import annotations

import os
from pathlib import Path

import pygame
import pytest

from config import port_config as pc


PROJECT_ROOT = Path(__file__).resolve().parent.parent
REAL_PORTS_PATH = PROJECT_ROOT / "data" / "ports.json"


@pytest.fixture(scope="module", autouse=True)
def _pygame_display():
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    pygame.display.init()
    pygame.font.init()
    pygame.display.set_mode((640, 360))
    yield
    pygame.font.quit()
    pygame.display.quit()


@pytest.fixture(autouse=True)
def _reset_port_config():
    pc._reset_for_tests()
    pc.init(str(REAL_PORTS_PATH))
    yield
    pc._reset_for_tests()


# --- compute_night_factor ---

class TestComputeNightFactor:
    def test_midnight_is_full_night(self):
        from systems.day_cycle import compute_night_factor
        assert compute_night_factor(0.0) == 1.0
        assert compute_night_factor(0.05) == 1.0

    def test_before_sunrise_fade_is_full_night(self):
        from systems.day_cycle import compute_night_factor
        assert compute_night_factor(0.07) == 1.0

    def test_sunrise_transition(self):
        """[0.08, 0.17]: fra 1.0 mot 0.0."""
        from systems.day_cycle import compute_night_factor
        # Start av fade
        assert compute_night_factor(0.08) == 1.0
        # Midt i — ca 0.5
        mid = compute_night_factor(0.125)
        assert 0.3 < mid < 0.7
        # Slutt av fade
        assert compute_night_factor(0.17) == 0.0

    def test_daytime_is_zero(self):
        """[0.17, 0.80]: full dag."""
        from systems.day_cycle import compute_night_factor
        assert compute_night_factor(0.20) == 0.0
        assert compute_night_factor(0.50) == 0.0
        assert compute_night_factor(0.79) == 0.0

    def test_sunset_transition(self):
        """[0.80, 0.88]: fra 0.0 mot 1.0."""
        from systems.day_cycle import compute_night_factor
        assert compute_night_factor(0.80) == 0.0
        # Midt i
        mid = compute_night_factor(0.84)
        assert 0.3 < mid < 0.7
        # Slutt av fade
        assert compute_night_factor(0.88) == 1.0

    def test_after_sunset_is_full_night(self):
        from systems.day_cycle import compute_night_factor
        assert compute_night_factor(0.90) == 1.0
        assert compute_night_factor(0.95) == 1.0
        assert compute_night_factor(0.99) == 1.0

    def test_smoothstep_monotonic(self):
        """Sunset/sunrise skal være monotone (ikke bølgete)."""
        from systems.day_cycle import compute_night_factor
        # Sunrise: skal monotont synke
        prev = compute_night_factor(0.08)
        for i in range(9, 18):
            f = i / 100
            curr = compute_night_factor(f)
            assert curr <= prev + 0.01, f"Ikke-monoton ved f={f}"
            prev = curr


# --- LightingSystem gating ---

class TestLightingGating:
    def test_draw_skips_at_full_day(self):
        """night_factor=0 skal ikke tegne noe."""
        from systems.lighting import LightingSystem, Light
        import constants

        ls = LightingSystem()
        light = Light(x=100, y=100, radius=20, color=constants.COLOR_LANTERN)
        surf = pygame.Surface((200, 200)).convert()
        surf.fill((0, 0, 0))
        # Tegne med night_factor=0 (dag)
        ls.draw(surf, [light], camera_x=0, elapsed=0.0, night_factor=0.0)
        # Sjekk at ingen pixler er endret
        p = surf.get_at((100, 100))
        assert p[:3] == (0, 0, 0), "Lys burde ikke være tegnet ved dag"

    def test_draw_renders_at_full_night(self):
        """night_factor=1 skal tegne lys normalt."""
        from systems.lighting import LightingSystem, Light
        import constants

        ls = LightingSystem()
        light = Light(x=100, y=100, radius=20, color=constants.COLOR_LANTERN)
        surf = pygame.Surface((200, 200)).convert()
        surf.fill((0, 0, 0))
        ls.draw(surf, [light], camera_x=0, elapsed=0.0, night_factor=1.0)
        p = surf.get_at((100, 100))
        assert p[:3] != (0, 0, 0), "Lys burde være tegnet ved natt"

    def test_threshold_snap_at_0_5(self):
        """Threshold: ≥0.5 = tegne, <0.5 = hoppe over."""
        from systems.lighting import LightingSystem, Light
        import constants

        ls = LightingSystem()
        light = Light(x=100, y=100, radius=20, color=constants.COLOR_LANTERN)
        # Above threshold — tegnes
        surf1 = pygame.Surface((200, 200)).convert()
        surf1.fill((0, 0, 0))
        ls.draw(surf1, [light], 0, 0.0, night_factor=0.5)
        p1 = surf1.get_at((100, 100))
        assert p1[:3] != (0, 0, 0)
        # Below threshold — hoppet over
        surf2 = pygame.Surface((200, 200)).convert()
        surf2.fill((0, 0, 0))
        ls.draw(surf2, [light], 0, 0.0, night_factor=0.49)
        p2 = surf2.get_at((100, 100))
        assert p2[:3] == (0, 0, 0)


# --- Gameplay-layer (day, night) tuple ---

class TestGameplayDayNightTuple:
    def test_returns_tuple_of_two_surfaces(self):
        from scenes.port_buildings import build_port_gameplay_layer

        tortuga = pc.get("tortuga")
        result = build_port_gameplay_layer(tortuga)
        assert isinstance(result, tuple)
        assert len(result) == 2
        day, night = result
        assert day.get_size() == night.get_size()

    def test_day_and_night_differ_at_tavern_window(self):
        """Tavern-vindus-regionen skal være annerledes ved natt vs dag.

        Tavern-vinduer: LANTERN-fyll ved natt, WOOD_DARKEST ved dag.
        """
        from scenes.port_buildings import build_port_gameplay_layer

        tortuga = pc.get("tortuga")
        day, night = build_port_gameplay_layer(tortuga)
        tavern = tortuga.buildings.tavern
        # Tavern-venstrevindu — LANTERN_BRIGHT-fyll innerst
        # tavern.x=20, vindu starter x=60, width 24.
        # LANTERN_BRIGHT-rekten er (62, 274, 20, 24). Sjekk offset
        # fra krysset: pixel (66, 276) er på LANTERN_BRIGHT i night,
        # WOOD_DARK i day.
        win_x = tavern.x + 40 + 6  # 66
        win_y = tavern.y + 14 + 4  # 276
        day_pixel = day.get_at((win_x, win_y))
        night_pixel = night.get_at((win_x, win_y))
        assert day_pixel[:3] != night_pixel[:3], (
            f"Tavern-vindu skal se annerledes ut: day={day_pixel[:3]}, "
            f"night={night_pixel[:3]}"
        )

    def test_all_4_ports_bake_both_variants(self):
        from scenes.port_buildings import build_port_gameplay_layer

        for pid in ("tortuga", "port_royal", "havana", "nassau"):
            day, night = build_port_gameplay_layer(pc.get(pid))
            assert day is not None
            assert night is not None

    def test_day_variant_lacks_tavern_door_glow(self):
        """Tavern-dør har FLAME-glød ved natt; ved dag er døren bare
        WOOD_DARKEST-åpning."""
        from scenes.port_buildings import build_port_gameplay_layer
        import constants

        tortuga = pc.get("tortuga")
        day, night = build_port_gameplay_layer(tortuga)
        tavern = tortuga.buildings.tavern
        # Tavern-dør sentralt: tavern.x + tavern.w/2
        door_cx = tavern.x + tavern.w // 2
        door_check_y = 340 - 18  # inne i dør-gløden
        day_pixel = day.get_at((door_cx, door_check_y))
        night_pixel = night.get_at((door_cx, door_check_y))
        # Night skal ha FLAME eller LANTERN_BRIGHT (varm farge)
        # Day skal være mørk (WOOD_DARKEST eller lignende)
        assert day_pixel[:3] != night_pixel[:3]
