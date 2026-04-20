"""Tester for Fase 2.5 C2.5-9 animasjons-pass.

Dekker:
- compute_cycle_frame_index med kritiske input-verdier
- apply_palette_cycles gater korrekt basert på night_factor
- Permanent-kilder tegnes også ved dag
- Parser aksepterer gyldig animations-konfig, avviser ugyldige
- Per-havn: palette_cycles parses fra ports.json
"""

from __future__ import annotations

import json
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


# --- compute_cycle_frame_index ---

class TestComputeCycleFrameIndex:
    def test_at_zero_elapsed_returns_zero(self):
        from systems.animations import compute_cycle_frame_index
        assert compute_cycle_frame_index(0.0, fps=6, num_frames=3) == 0

    def test_advances_at_fps_rate(self):
        """Ved fps=6, etter 1 sek skal indeksen ha rotert 6 ganger."""
        from systems.animations import compute_cycle_frame_index
        # 1 sek × 6 fps = 6 ticks; mod 3 = 0
        assert compute_cycle_frame_index(1.0, fps=6, num_frames=3) == 0
        # 0.5 sek × 6 fps = 3 ticks; mod 3 = 0
        assert compute_cycle_frame_index(0.5, fps=6, num_frames=3) == 0
        # 0.17 sek × 6 fps = 1 tick; mod 3 = 1
        assert compute_cycle_frame_index(0.17, fps=6, num_frames=3) == 1

    def test_zero_fps_returns_zero(self):
        from systems.animations import compute_cycle_frame_index
        assert compute_cycle_frame_index(100.0, fps=0, num_frames=3) == 0

    def test_zero_num_frames_returns_zero(self):
        from systems.animations import compute_cycle_frame_index
        assert compute_cycle_frame_index(10.0, fps=6, num_frames=0) == 0

    def test_different_elapsed_gives_different_index(self):
        """To forskjellige tidspunkter innenfor samme palett-runde
        gir forskjellige indekser."""
        from systems.animations import compute_cycle_frame_index
        idx_0 = compute_cycle_frame_index(0.0, fps=6, num_frames=4)
        idx_1 = compute_cycle_frame_index(0.17, fps=6, num_frames=4)
        idx_2 = compute_cycle_frame_index(0.34, fps=6, num_frames=4)
        # 0.17 gir 1, 0.34 gir 2 — men kontekst-avhengig
        assert idx_0 != idx_1 or idx_1 != idx_2


# --- apply_palette_cycles ---

class TestApplyPaletteCycles:
    def test_permanent_source_draws_at_day(self):
        """Permanent=True skal tegne også ved night_factor=0 (dag)."""
        from systems.animations import apply_palette_cycles, PaletteCycleSource

        surf = pygame.Surface((100, 100)).convert()
        surf.fill((0, 0, 0))
        src = PaletteCycleSource(
            x=10, y=10, w=5, h=5,
            palette=("FLAME", "EMBER"),
            fps=6, permanent=True,
        )
        drawn = apply_palette_cycles(surf, [src], elapsed_seconds=0.0, night_factor=0.0)
        assert drawn == 1
        # Sjekk at piksler i (10, 10) ikke er svart
        p = surf.get_at((10, 10))
        assert p[:3] != (0, 0, 0)

    def test_gated_source_draws_at_night(self):
        from systems.animations import apply_palette_cycles, PaletteCycleSource

        surf = pygame.Surface((100, 100)).convert()
        surf.fill((0, 0, 0))
        src = PaletteCycleSource(
            x=20, y=20, w=5, h=5,
            palette=("LANTERN", "LANTERN_BRIGHT"),
            fps=6, permanent=False,
        )
        drawn = apply_palette_cycles(surf, [src], elapsed_seconds=0.0, night_factor=1.0)
        assert drawn == 1
        p = surf.get_at((20, 20))
        assert p[:3] != (0, 0, 0)

    def test_gated_source_off_at_day_uses_last_palette_color(self):
        """Ved dag skal gated-source bruke siste palett-farge
        (typisk mørkeste — "off-state"), fortsatt tegnes."""
        import constants
        from systems.animations import apply_palette_cycles, PaletteCycleSource

        surf = pygame.Surface((100, 100)).convert()
        surf.fill((0, 0, 0))
        src = PaletteCycleSource(
            x=30, y=30, w=5, h=5,
            palette=("LANTERN", "WOOD_DARK"),
            fps=6, permanent=False,
        )
        apply_palette_cycles(surf, [src], 0.0, night_factor=0.0)
        # Forventer siste palett-farge: WOOD_DARK
        p = surf.get_at((30, 30))[:3]
        assert p == constants.COLOR_WOOD_DARK

    def test_cycle_through_palette_over_time(self):
        """Over flere tidspunkter skal forskjellige palett-farger brukes."""
        from systems.animations import apply_palette_cycles, PaletteCycleSource

        src = PaletteCycleSource(
            x=40, y=40, w=3, h=3,
            palette=("FLAME", "EMBER", "LANTERN_BRIGHT"),
            fps=6, permanent=True,
        )
        colors_seen = set()
        for t_elapsed in (0.0, 0.17, 0.34):
            surf = pygame.Surface((100, 100)).convert()
            surf.fill((0, 0, 0))
            apply_palette_cycles(surf, [src], t_elapsed, night_factor=1.0)
            p = surf.get_at((40, 40))[:3]
            colors_seen.add(p)
        # Minst 2 forskjellige farger skal vises
        assert len(colors_seen) >= 2


# --- Parser ---

class TestAnimationsParser:
    def test_all_4_ports_have_animations(self):
        """Alle 4 havner får animations-felt (kan være tom tuple)."""
        for pid in ("tortuga", "port_royal", "havana", "nassau"):
            port = pc.get(pid)
            # PortAnimations default er tom
            assert port.buildings.animations is not None

    def test_tortuga_has_permanent_smithy_cycles(self):
        """Tortuga har smithy-esse cycling (permanent)."""
        tortuga = pc.get("tortuga")
        cycles = tortuga.buildings.animations.palette_cycles
        assert len(cycles) >= 1
        # Minst én permanent
        permanent_count = sum(1 for c in cycles if c.permanent)
        assert permanent_count >= 1

    def test_nassau_has_multiple_campfire_cycles(self):
        """Nassau har 2 bål med cycling (permanent)."""
        nassau = pc.get("nassau")
        cycles = nassau.buildings.animations.palette_cycles
        # 4 cycling-regioner (2 bål × 2 regioner hver — kjerne + topp)
        assert len(cycles) >= 2
        # Alle permanent
        assert all(c.permanent for c in cycles)

    def test_port_royal_has_gated_customs_cycle(self):
        """Port Royal Customs-cycling er gated (off om dagen)."""
        port_royal = pc.get("port_royal")
        cycles = port_royal.buildings.animations.palette_cycles
        gated = [c for c in cycles if not c.permanent]
        assert len(gated) >= 1

    def test_havana_has_cathedral_and_artisan_cycles(self):
        """Havana har katedral-portal (gated) + artisan-esse (permanent)."""
        havana = pc.get("havana")
        cycles = havana.buildings.animations.palette_cycles
        has_gated = any(not c.permanent for c in cycles)
        has_permanent = any(c.permanent for c in cycles)
        assert has_gated and has_permanent

    def test_invalid_palette_name_rejected(self, tmp_path):
        ports_data = json.loads(REAL_PORTS_PATH.read_text(encoding="utf-8"))
        ports_data["ports"]["tortuga"]["buildings"]["animations"] = {
            "palette_cycles": [
                {"x": 100, "y": 100, "w": 5, "h": 5,
                 "palette": ["NEON_PINK", "FLAME"],
                 "fps": 6, "permanent": True}
            ]
        }
        path = tmp_path / "ports.json"
        path.write_text(json.dumps(ports_data), encoding="utf-8")
        with pytest.raises(ValueError, match="ukjent.*palett"):
            pc.init(str(path))

    def test_palette_too_short_rejected(self, tmp_path):
        """Palett med kun 1 farge er ugyldig — må være ≥2."""
        ports_data = json.loads(REAL_PORTS_PATH.read_text(encoding="utf-8"))
        ports_data["ports"]["tortuga"]["buildings"]["animations"] = {
            "palette_cycles": [
                {"x": 100, "y": 100, "w": 5, "h": 5,
                 "palette": ["FLAME"],
                 "fps": 6, "permanent": True}
            ]
        }
        path = tmp_path / "ports.json"
        path.write_text(json.dumps(ports_data), encoding="utf-8")
        with pytest.raises(ValueError, match="minst 2 farger"):
            pc.init(str(path))


class TestPixelBudget:
    """Maks 25 px cycling per havn per spec §C2.5-9."""

    def test_each_port_under_25_pixel_budget(self):
        for pid in ("tortuga", "port_royal", "havana", "nassau"):
            cycles = pc.get(pid).buildings.animations.palette_cycles
            total_pixels = sum(c.w * c.h for c in cycles)
            assert total_pixels <= 25, (
                f"{pid}: {total_pixels} px cycling (over 25 budget)"
            )
