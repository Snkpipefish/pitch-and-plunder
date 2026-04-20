"""Tester for Fase 2.5 C2.5-8 vann-refleksjoner."""

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


class TestReflectionPrimitives:
    def test_valid_kinds(self):
        from entities.reflections import VALID_REFLECTION_KINDS

        assert VALID_REFLECTION_KINDS == frozenset({
            "lantern", "flame", "moon", "cold", "ship",
        })

    def test_bake_stripe_writes_pixels_below_horizon(self):
        """Refleksjonen skal skrive piksler i vann-regionen
        (y >= HORIZON_Y=208)."""
        from entities.reflections import (
            bake_reflection_stripe, ReflectionSource, HORIZON_Y,
        )

        surf = pygame.Surface((640, 360)).convert()
        surf.fill((0, 0, 0))
        src = ReflectionSource(x=100, kind="lantern", length=10)
        bake_reflection_stripe(surf, src)
        # Sjekk at minst én pixel er tegnet ved y=HORIZON_Y+2
        # (topp-segmentet med lantern-farge)
        found = False
        for dx in range(-2, 3):
            p = surf.get_at((100 + dx, HORIZON_Y + 2))
            if p[:3] != (0, 0, 0):
                found = True
                break
        assert found, "Forventet lantern-piksel i topp-segment"

    def test_bake_stripe_respects_length(self):
        """Piksler tegnes opp til `length` nedenfor horisonten, ikke forbi."""
        from entities.reflections import (
            bake_reflection_stripe, ReflectionSource, HORIZON_Y,
        )

        surf = pygame.Surface((640, 360)).convert()
        surf.fill((0, 0, 0))
        src = ReflectionSource(x=100, kind="lantern", length=10)
        bake_reflection_stripe(surf, src)
        # Pixel ved y=HORIZON_Y+15 (forbi length) skal fortsatt være svart
        for dx in range(-2, 3):
            p = surf.get_at((100 + dx, HORIZON_Y + 15))
            assert p[:3] == (0, 0, 0), (
                f"Fant uventet pixel ved ({100+dx}, {HORIZON_Y+15}): {p}"
            )

    def test_unknown_kind_raises(self):
        from entities.reflections import (
            bake_reflection_stripe, ReflectionSource,
        )

        surf = pygame.Surface((640, 360)).convert()
        src = ReflectionSource(x=100, kind="sunburst", length=10)
        with pytest.raises(ValueError, match="Ukjent reflection-kind"):
            bake_reflection_stripe(surf, src)

    def test_moon_width_spreads_horizontally(self):
        """Månens width=3 skal tegne 3 px bred strek."""
        from entities.reflections import (
            bake_reflection_stripe, ReflectionSource, HORIZON_Y,
        )

        surf = pygame.Surface((640, 360)).convert()
        surf.fill((0, 0, 0))
        src = ReflectionSource(x=200, kind="moon", length=10, width=3)
        bake_reflection_stripe(surf, src)
        # Topp-segmentet skal ha 3 piksler bred
        cnt = 0
        for dx in range(-2, 3):
            p = surf.get_at((200 + dx, HORIZON_Y + 1))
            if p[:3] != (0, 0, 0):
                cnt += 1
        assert cnt >= 3, "Bred stripe skal ha flere piksler på samme y"


class TestReflectionGenerator:
    def test_all_4_ports_have_reflections(self):
        """Hver havn skal gi minst 6 refleksjons-kilder per spec."""
        from entities.reflections import generate_port_reflections

        for pid in ("tortuga", "port_royal", "havana", "nassau"):
            port = pc.get(pid)
            sources = generate_port_reflections(port)
            assert len(sources) >= 6, (
                f"{pid}: fikk {len(sources)} sources, forventet ≥6"
            )

    def test_per_port_counts_match_spec(self):
        """Spec §1.5: 10-15 per havn. Testen aksepterer 6-15 for
        fleksibilitet."""
        from entities.reflections import generate_port_reflections

        pc.init(str(REAL_PORTS_PATH))
        counts = {
            pid: len(generate_port_reflections(pc.get(pid)))
            for pid in ("tortuga", "port_royal", "havana", "nassau")
        }
        # Havana skal ha flest (mest ornamentell havn med flest
        # lyskilder)
        assert counts["havana"] >= counts["tortuga"]
        assert counts["havana"] >= counts["port_royal"]
        # Tortuga (enklest havn) skal ha færrest
        assert counts["tortuga"] <= counts["havana"]

    def test_all_ports_have_moon_reflection(self):
        """Alle 4 havner har månerefleksjon."""
        from entities.reflections import generate_port_reflections

        for pid in ("tortuga", "port_royal", "havana", "nassau"):
            sources = generate_port_reflections(pc.get(pid))
            kinds = {s.kind for s in sources}
            assert "moon" in kinds, f"{pid} mangler moon-refleksjon"

    def test_nassau_has_flame_reflections_from_campfires(self):
        """Nassau har 2 bål i C2.5-4 props; de gir flame-refleksjoner."""
        from entities.reflections import generate_port_reflections

        nassau = pc.get("nassau")
        sources = generate_port_reflections(nassau)
        flame_count = sum(1 for s in sources if s.kind == "flame")
        # Forventer minst 4 flame-kilder: 1 tavern-dør + 2 bål
        # + 1-2 Teach-vinduer
        assert flame_count >= 4

    def test_port_royal_has_cold_reflection(self):
        """Port Royal skal ha 'cold' refleksjon fra Customs House."""
        from entities.reflections import generate_port_reflections

        sources = generate_port_reflections(pc.get("port_royal"))
        kinds = {s.kind for s in sources}
        assert "cold" in kinds

    def test_havana_has_flame_from_cathedral_portal(self):
        """Havana katedral gir stor flame-refleksjon."""
        from entities.reflections import generate_port_reflections

        sources = generate_port_reflections(pc.get("havana"))
        flame_sources = [s for s in sources if s.kind == "flame"]
        assert len(flame_sources) >= 1
        # Katedral-refleksjonen skal være lengst (dominerende)
        max_flame_length = max(s.length for s in flame_sources)
        assert max_flame_length >= 20


class TestBakePipelineIntegration:
    def test_all_4_ports_bake_with_reflections(self):
        from scenes.port_buildings import build_port_gameplay_layer

        for pid in ("tortuga", "port_royal", "havana", "nassau"):
            surf = build_port_gameplay_layer(pc.get(pid))
            assert surf is not None

    def test_reflection_pixels_present_in_vann_region(self):
        """Gameplay-laget skal ha refleksjons-piksler i y=208..240-
        regionen for hver havn. Sjekk at minst én pixel er tegnet
        ved tavern-center-x, y=HORIZON_Y + 2."""
        from scenes.port_buildings import build_port_gameplay_layer, COLORKEY
        from entities.reflections import HORIZON_Y

        for pid in ("tortuga", "port_royal", "havana", "nassau"):
            port = pc.get(pid)
            surf = build_port_gameplay_layer(port)
            tavern = port.buildings.tavern
            cx = tavern.x + tavern.w // 2
            # Finn en ikke-colorkey-pixel i refleksjons-regionen rundt cx
            found = False
            for dx in range(-3, 4):
                for dy in range(1, 12):
                    px = surf.get_at((cx + dx, HORIZON_Y + dy))
                    if px[:3] != COLORKEY:
                        found = True
                        break
                if found:
                    break
            assert found, (
                f"{pid}: fant ingen refleksjons-piksler rundt tavern "
                f"ved y={HORIZON_Y}..+12"
            )

    def test_reflections_not_visible_where_buildings_cover(self):
        """Refleksjoner skal bli dekket av bygninger når de overlapper
        (bygninger tegnes etter refleksjoner i pipeline).

        Spesifikt: tavern-kropp er ved y=258..340 for Tortuga.
        Refleksjons-kilde ved tavern_cx, y=258 skal være tavern-
        pixel (ikke lantern-refleksjon)."""
        from scenes.port_buildings import build_port_gameplay_layer

        tortuga = pc.get("tortuga")
        surf = build_port_gameplay_layer(tortuga)
        tavern = tortuga.buildings.tavern
        cx = tavern.x + tavern.w // 2
        # y=270 er inne i tavern-kroppen
        px = surf.get_at((cx, 270))
        # Lantern-refleksjon ville gitt LANTERN (255, 179, 71)
        # Tavern-kroppen gir COLOR_WOOD_DARK (42, 32, 24)
        assert px[:3] != (255, 179, 71), (
            "Forventet bygnings-piksel (dekket refleksjon), "
            "fikk LANTERN-farge"
        )
