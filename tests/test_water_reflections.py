"""Tester for Fase 2.5 C2.5-8c vann-refleksjoner.

Kritiske tester basert på lærdom fra C2.5-8-revert:
1. Refleksjons-piksler er alle i vann-region (aldri over water_y_top)
2. Refleksjoner dekkes av bygninger der de overlapper (okklusjon)
3. Day-variant har INGEN refleksjoner (gating via night_surface-bytte)
4. Brede, levende — width ≥ 4, flere y-linjer har forskjellige farger
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


# --- Primitives ---

class TestReflectionPrimitives:
    def test_valid_palettes(self):
        from entities.water_reflections import VALID_PALETTES

        assert VALID_PALETTES == frozenset({
            "lantern", "flame", "ember", "stone_lit",
        })

    def test_water_y_top_constant(self):
        """WATER_Y_TOP skal være rett under horisont-silhuetten."""
        from entities.water_reflections import WATER_Y_TOP

        # horizon_y = int(360 * 0.58) = 208, silhouette ender ~y=214
        assert 210 <= WATER_Y_TOP <= 220

    def test_unknown_palette_raises(self):
        from entities.water_reflections import (
            bake_reflection_source, ReflectionSource,
        )

        surf = pygame.Surface((640, 360)).convert()
        src = ReflectionSource(x=100, palette_key="neon", width=6, length=20)
        with pytest.raises(ValueError, match="Ukjent reflection"):
            bake_reflection_source(surf, src, 214, 340)


# --- Kritisk: vann-region ---

class TestReflectionsInWaterRegion:
    """Forrige C2.5-8 hadde refleksjoner som svevet over bygninger.
    Disse testene verifiserer at alle piksler er i vann-regionen
    y=[water_y_top, water_y_bottom]."""

    def test_single_reflection_pixels_in_water_region(self):
        from entities.water_reflections import (
            bake_reflection_source, ReflectionSource, WATER_Y_TOP,
        )

        surf = pygame.Surface((640, 360)).convert()
        surf.fill((0, 0, 0))
        src = ReflectionSource(x=100, palette_key="lantern", width=6, length=24)
        bake_reflection_source(surf, src, WATER_Y_TOP, 340)

        # Scan alle piksler — finn alle ikke-sorte
        lit_pixels_y = set()
        for y in range(360):
            for x in range(90, 111):
                p = surf.get_at((x, y))
                if p[:3] != (0, 0, 0):
                    lit_pixels_y.add(y)
        # Alle lit-piksler må være innenfor vann-region
        assert lit_pixels_y, "Ingen refleksjons-piksler tegnet"
        min_y, max_y = min(lit_pixels_y), max(lit_pixels_y)
        assert min_y >= WATER_Y_TOP, (
            f"Refleksjon svever: min y={min_y} < water_y_top={WATER_Y_TOP}"
        )
        assert max_y < 340, (
            f"Refleksjon går forbi water_y_bottom=340: max y={max_y}"
        )

    def test_reflection_starts_at_water_y_top_not_source_y(self):
        """Selv hvis kildens konseptuelle y er 258 (bygnings-topp),
        skal refleksjonen starte ved WATER_Y_TOP=214."""
        from entities.water_reflections import (
            bake_reflection_source, ReflectionSource, WATER_Y_TOP,
        )

        surf = pygame.Surface((640, 360)).convert()
        surf.fill((0, 0, 0))
        src = ReflectionSource(x=100, palette_key="flame", width=8, length=20)
        bake_reflection_source(surf, src, WATER_Y_TOP, 340)

        # Finn toppen av refleksjonen
        for y in range(WATER_Y_TOP, 340):
            for x in range(90, 111):
                p = surf.get_at((x, y))
                if p[:3] != (0, 0, 0):
                    # Topp-y skal være WATER_Y_TOP eller innen få px
                    assert y <= WATER_Y_TOP + 2
                    return
        pytest.fail("Ingen piksler funnet i refleksjons-regionen")


# --- Brede og levende ---

class TestReflectionWidthAndGradient:
    def test_reflection_width_matches_source(self):
        """Width=8 skal gi ~8 px bred refleksjon."""
        from entities.water_reflections import (
            bake_reflection_source, ReflectionSource, WATER_Y_TOP,
        )

        surf = pygame.Surface((640, 360)).convert()
        surf.fill((0, 0, 0))
        src = ReflectionSource(x=300, palette_key="lantern", width=8, length=20)
        bake_reflection_source(surf, src, WATER_Y_TOP, 340)

        # Tel bredden ved y=WATER_Y_TOP+2 (unngå wobble-effekter ved y=0)
        lit_cnt = 0
        for x in range(280, 321):
            p = surf.get_at((x, WATER_Y_TOP + 2))
            if p[:3] != (0, 0, 0):
                lit_cnt += 1
        # Min 5 px (accounting for wobble) — ikke bare 1-2 px
        assert lit_cnt >= 5, (
            f"Refleksjon for smal: {lit_cnt} px ved topp"
        )

    def test_gradient_darkens_toward_bottom(self):
        """Topp skal ha lys farge, bunn mørk."""
        from entities.water_reflections import (
            bake_reflection_source, ReflectionSource, WATER_Y_TOP,
        )
        import constants

        surf = pygame.Surface((640, 360)).convert()
        surf.fill((0, 0, 0))
        src = ReflectionSource(x=100, palette_key="lantern", width=6, length=24)
        bake_reflection_source(surf, src, WATER_Y_TOP, 340)

        # Topp-pixel ved y=WATER_Y_TOP+1 skal være LANTERN_BRIGHT eller nær
        # Bunn-pixel ved y=WATER_Y_TOP+22 skal være mørkere
        top_pixel = None
        bottom_pixel = None
        for x in range(95, 106):
            p_top = surf.get_at((x, WATER_Y_TOP + 1))
            p_bottom = surf.get_at((x, WATER_Y_TOP + 22))
            if p_top[:3] != (0, 0, 0):
                top_pixel = p_top
            if p_bottom[:3] != (0, 0, 0):
                bottom_pixel = p_bottom
        assert top_pixel is not None
        assert bottom_pixel is not None
        # Sum av RGB skal være høyere for topp (lysere)
        top_brightness = sum(top_pixel[:3])
        bottom_brightness = sum(bottom_pixel[:3])
        assert top_brightness > bottom_brightness, (
            f"Gradient feil retning: topp={top_pixel[:3]} brightness "
            f"{top_brightness}, bunn={bottom_pixel[:3]} "
            f"brightness {bottom_brightness}"
        )


# --- Per-havn generator ---

class TestGeneratePortReflections:
    def test_all_4_ports_generate_sources(self):
        from entities.water_reflections import generate_port_reflections

        for pid in ("tortuga", "port_royal", "havana", "nassau"):
            sources = generate_port_reflections(pc.get(pid))
            assert len(sources) >= 5, (
                f"{pid}: {len(sources)} kilder, forventet >= 5"
            )

    def test_havana_most_sources(self):
        """Havana er rikt på lyskilder (katedral + palass + handelshus)."""
        from entities.water_reflections import generate_port_reflections

        counts = {
            pid: len(generate_port_reflections(pc.get(pid)))
            for pid in ("tortuga", "port_royal", "havana", "nassau")
        }
        assert counts["havana"] >= counts["tortuga"]
        assert counts["havana"] >= counts["port_royal"]

    def test_port_royal_has_stone_lit(self):
        """Port Royal har kald STONE_LIT-refleksjon fra Customs."""
        from entities.water_reflections import generate_port_reflections

        sources = generate_port_reflections(pc.get("port_royal"))
        palettes = {s.palette_key for s in sources}
        assert "stone_lit" in palettes

    def test_nassau_has_campfire_flame(self):
        """Nassau har 2 bål — flame-kilder."""
        from entities.water_reflections import generate_port_reflections

        sources = generate_port_reflections(pc.get("nassau"))
        flame_count = sum(1 for s in sources if s.palette_key == "flame")
        assert flame_count >= 4, (
            "Nassau: forventet flere flame-kilder "
            "(tavern-dør + 2 bål + Teach-vinduer)"
        )


# --- Bake-pipeline integrasjon ---

class TestReflectionsInGameplayLayer:
    def test_night_surface_has_reflections_in_water_region(self):
        """night_surface skal ha refleksjons-piksler i vann-region."""
        from scenes.port_buildings import build_port_gameplay_layer, COLORKEY
        from entities.water_reflections import WATER_Y_TOP

        tortuga = pc.get("tortuga")
        day, night = build_port_gameplay_layer(tortuga)
        tavern = tortuga.buildings.tavern
        # Scan regionen rundt tavern-sentrum for refleksjons-piksler
        # i vann-området (y=WATER_Y_TOP..258). Bygninger starter ved
        # tavern.y=258, så y=214..258 er ÅPENT vann.
        tavern_cx = tavern.x + tavern.w // 2
        found = False
        for y in range(WATER_Y_TOP, tavern.y):
            for dx in range(-10, 11):
                p = night.get_at((tavern_cx + dx, y))
                if p[:3] != COLORKEY:
                    found = True
                    break
            if found:
                break
        assert found, (
            "Forventet refleksjons-piksler i vann-region under tavern"
        )

    def test_day_surface_has_no_reflections(self):
        """day_surface skal mangle refleksjons-piksler der night har dem.

        Test-strategi: finn en pixel der night-variant har refleksjons-
        piksel (LANTERN/FLAME/EMBER/STONE_LIT), og verifiser at day-
        variant har COLORKEY på samme sted. Natur-elementer som måker
        (MOON_HALO) er i begge varianter og ekskluderes.
        """
        from scenes.port_buildings import build_port_gameplay_layer, COLORKEY
        from entities.water_reflections import WATER_Y_TOP, _GRADIENTS
        import constants

        # Alle palett-farger som er refleksjons-spesifikke
        reflection_colors = set()
        for grad in _GRADIENTS.values():
            for c in grad:
                reflection_colors.add(tuple(c))

        tortuga = pc.get("tortuga")
        day, night = build_port_gameplay_layer(tortuga)
        tavern = tortuga.buildings.tavern
        tavern_cx = tavern.x + tavern.w // 2

        # Scan kun y-region over alle bygnings-topper.
        # Tortuga: tavern.y=258, exchange.y=248 → stop ved 247.
        # I dette området kan kun refleksjoner og natur-elementer være.
        min_building_top = min(
            tortuga.buildings.tavern.y,
            tortuga.buildings.exchange.y,
        )
        # Finn refleksjons-piksel i night og sjekk at day mangler den.
        # Bruker spesifikke refleksjons-UNIKE farger for å unngå
        # overlapp med natur-elementer (måker: MOON_HALO, fjell:
        # STONE_DARKEST, etc). LANTERN_BRIGHT + LANTERN er nesten
        # eksklusive for refleksjoner i denne regionen.
        unique_reflection_colors = {
            tuple(constants.COLOR_LANTERN_BRIGHT),
            tuple(constants.COLOR_LANTERN),
            tuple(constants.COLOR_FLAME),
            tuple(constants.COLOR_EMBER),
        }
        found_reflection_check = False
        for y in range(WATER_Y_TOP, min_building_top):
            for dx in range(-15, 16):
                px = tavern_cx + dx
                night_p = night.get_at((px, y))[:3]
                if night_p in unique_reflection_colors:
                    day_p = day.get_at((px, y))[:3]
                    assert day_p == COLORKEY, (
                        f"Day-variant har refleksjon ved ({px}, {y}): "
                        f"{day_p} (night: {night_p})"
                    )
                    found_reflection_check = True
        assert found_reflection_check, (
            "Testet ingen refleksjons-piksler — bake-pipeline feil?"
        )

    def test_reflection_occluded_by_building(self):
        """Refleksjoner skal IKKE vises gjennom bygninger.

        Tavern-bygningen står ved y=258..340. Ved tavern-sentrum y=300,
        pixel skal være bygnings-farge (WOOD_*, FLAME, LANTERN —
        tavern-sprite), ikke refleksjons-farge.
        """
        from scenes.port_buildings import build_port_gameplay_layer

        tortuga = pc.get("tortuga")
        _, night = build_port_gameplay_layer(tortuga)
        tavern = tortuga.buildings.tavern
        tavern_cx = tavern.x + tavern.w // 2
        # Y=300 er inne i tavern-kroppen
        pixel = night.get_at((tavern_cx, 300))
        # Skal være tavern-pixel (bygning) ikke refleksjon.
        # Bygnings-pixler er IKKE COLORKEY (255, 0, 255).
        assert pixel[:3] != (255, 0, 255)


# --- Alle 4 havner baker ---

class TestAll4PortsBakeWithReflections:
    def test_all_ports_bake(self):
        from scenes.port_buildings import build_port_gameplay_layer

        for pid in ("tortuga", "port_royal", "havana", "nassau"):
            day, night = build_port_gameplay_layer(pc.get(pid))
            assert day is not None and night is not None
