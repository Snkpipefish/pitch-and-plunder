"""Tester for verdenskart-tooltip (Fase 2B C8).

Dekker:
- build_tooltip_lines: 4 tilstander (current / fersk / stale / aldri besøkt)
- Linje-count og farge-mapping per tilstand
- Trend-pil for fersk data, "?" for stale data
- WorldMapTooltip.draw kjører uten å kaste på alle tilstander
- Pixel-sampling: tooltip-tekst (MOON_CORE) finnes ved anchor
"""

from __future__ import annotations

import os

import pygame
import pytest

import constants
from state.market_state import CommodityMarket, MarketState
from state.observed_price import ObservedPrice
from ui import color_palette
from ui.world_map_tooltip import (
    TooltipLine,
    WorldMapTooltip,
    build_tooltip_lines,
)


@pytest.fixture(scope="module", autouse=True)
def _pygame_display():
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    pygame.display.init()
    pygame.font.init()
    pygame.display.set_mode((640, 360))
    yield
    pygame.font.quit()
    pygame.display.quit()


def _font() -> pygame.font.Font:
    return pygame.font.Font(None, 12)


# Standard test-katalog: alle 4 commodities i fast rekkefølge.
_CATALOG_ORDER = ["sugar", "rum", "tobacco", "pitch"]
_CATALOG_NAMES = {
    "sugar": "Sukker",
    "rum": "Rom",
    "tobacco": "Tobakk",
    "pitch": "Bek",
}


def _market_with_history() -> MarketState:
    """Bygg en MarketState med pris-historikk lang nok til å gi en
    deterministisk trend (rising)."""
    commodities = {
        "sugar":   CommodityMarket(current_price=44.0, price_history=[40.0, 42.0, 44.0]),
        "rum":     CommodityMarket(current_price=80.0, price_history=[75.0, 78.0, 80.0]),
        "tobacco": CommodityMarket(current_price=90.0, price_history=[88.0, 89.0, 90.0]),
        "pitch":   CommodityMarket(current_price=42.0, price_history=[40.0, 41.0, 42.0]),
    }
    return MarketState(commodities=commodities)


# -----------------------------------------------------------------------------
# build_tooltip_lines — current port
# -----------------------------------------------------------------------------


class TestBuildTooltipCurrentPort:
    def test_current_port_shows_du_er_her_with_fresh_prices(self):
        market_state = _market_with_history()
        lines = build_tooltip_lines(
            port_name="Tortuga",
            observed_for_port=None,  # ignored when is_current_port
            market_state=market_state,
            catalog_order=_CATALOG_ORDER,
            catalog_names=_CATALOG_NAMES,
            current_day=5,
            stale_threshold=5,
            is_current_port=True,
        )
        # 1 navn + 1 status + 4 commodity-rader = 6 linjer
        assert len(lines) == 6
        assert lines[0].text == "Tortuga"
        assert lines[0].color == constants.COLOR_MOON_CORE
        assert lines[1].text == "Du er her"
        assert lines[1].color == color_palette.DATA_FRESH

    def test_current_port_includes_trend_arrow(self):
        market_state = _market_with_history()
        lines = build_tooltip_lines(
            port_name="Tortuga",
            observed_for_port=None,
            market_state=market_state,
            catalog_order=_CATALOG_ORDER,
            catalog_names=_CATALOG_NAMES,
            current_day=5,
            stale_threshold=5,
            is_current_port=True,
        )
        # Sukker: 44 ↑ (rising trend)
        sugar_line = lines[2]
        assert "Sukker" in sugar_line.text
        assert "44" in sugar_line.text
        assert "\u2191" in sugar_line.text  # rising arrow
        assert sugar_line.color == color_palette.DATA_FRESH


# -----------------------------------------------------------------------------
# build_tooltip_lines — never visited
# -----------------------------------------------------------------------------


class TestBuildTooltipNeverVisited:
    def test_no_observed_shows_aldri_besokt(self):
        market_state = _market_with_history()
        lines = build_tooltip_lines(
            port_name="Nassau",
            observed_for_port=None,
            market_state=market_state,
            catalog_order=_CATALOG_ORDER,
            catalog_names=_CATALOG_NAMES,
            current_day=10,
            stale_threshold=5,
            is_current_port=False,
        )
        # 1 navn + 1 "aldri besøkt" = 2 linjer, ingen pris-rader
        assert len(lines) == 2
        assert lines[0].text == "Nassau"
        assert lines[1].text == "aldri besøkt"
        assert lines[1].color == color_palette.DATA_NEVER

    def test_empty_observed_dict_treated_as_never_visited(self):
        """observed_for_port = {} skal tolkes likt som None."""
        market_state = _market_with_history()
        lines = build_tooltip_lines(
            port_name="Havana",
            observed_for_port={},
            market_state=market_state,
            catalog_order=_CATALOG_ORDER,
            catalog_names=_CATALOG_NAMES,
            current_day=10,
            stale_threshold=5,
            is_current_port=False,
        )
        assert len(lines) == 2
        assert lines[1].text == "aldri besøkt"


# -----------------------------------------------------------------------------
# build_tooltip_lines — fresh observed
# -----------------------------------------------------------------------------


class TestBuildTooltipFreshObserved:
    def test_fresh_observed_shows_age_in_fresh_color(self):
        market_state = _market_with_history()
        observed = {
            cid: ObservedPrice(price=42.0, day_seen=3)
            for cid in _CATALOG_ORDER
        }
        lines = build_tooltip_lines(
            port_name="Port Royal",
            observed_for_port=observed,
            market_state=market_state,
            catalog_order=_CATALOG_ORDER,
            catalog_names=_CATALOG_NAMES,
            current_day=5,  # 2 dager siden, threshold=5 → fersk
            stale_threshold=5,
            is_current_port=False,
        )
        # 1 navn + 1 alder + 4 commodity-rader = 6 linjer
        assert len(lines) == 6
        assert lines[0].text == "Port Royal"
        assert "Dag 3" in lines[1].text
        assert "2 d. siden" in lines[1].text
        assert lines[1].color == color_palette.DATA_FRESH

    def test_fresh_observed_uses_trend_arrow_not_question(self):
        market_state = _market_with_history()  # rising-trend
        observed = {
            cid: ObservedPrice(price=42.0, day_seen=3)
            for cid in _CATALOG_ORDER
        }
        lines = build_tooltip_lines(
            port_name="Port Royal",
            observed_for_port=observed,
            market_state=market_state,
            catalog_order=_CATALOG_ORDER,
            catalog_names=_CATALOG_NAMES,
            current_day=5,
            stale_threshold=5,
            is_current_port=False,
        )
        sugar_line = lines[2]
        assert "\u2191" in sugar_line.text  # rising arrow, ikke "?"
        assert "?" not in sugar_line.text
        assert sugar_line.color == color_palette.DATA_FRESH


# -----------------------------------------------------------------------------
# build_tooltip_lines — stale observed
# -----------------------------------------------------------------------------


class TestBuildTooltipStaleObserved:
    def test_stale_observed_shows_age_in_stale_color(self):
        market_state = _market_with_history()
        observed = {
            cid: ObservedPrice(price=42.0, day_seen=2)
            for cid in _CATALOG_ORDER
        }
        lines = build_tooltip_lines(
            port_name="Havana",
            observed_for_port=observed,
            market_state=market_state,
            catalog_order=_CATALOG_ORDER,
            catalog_names=_CATALOG_NAMES,
            current_day=10,  # 8 dager siden, threshold=5 → stale
            stale_threshold=5,
            is_current_port=False,
        )
        # 1 navn + 1 alder + 4 commodity-rader = 6 linjer
        assert len(lines) == 6
        assert "Dag 2" in lines[1].text
        assert "8 d. siden" in lines[1].text
        assert lines[1].color == color_palette.DATA_STALE_AGE

    def test_stale_observed_uses_question_mark_not_trend(self):
        """Per spec §2.3: 'Utdatert data skal ikke lyve om retning.'
        Stale observed får ALLTID '?', uavhengig av price_history-
        trend i markedet nå."""
        market_state = _market_with_history()  # rising trend i markedet
        observed = {
            cid: ObservedPrice(price=42.0, day_seen=2)
            for cid in _CATALOG_ORDER
        }
        lines = build_tooltip_lines(
            port_name="Havana",
            observed_for_port=observed,
            market_state=market_state,
            catalog_order=_CATALOG_ORDER,
            catalog_names=_CATALOG_NAMES,
            current_day=10,
            stale_threshold=5,
            is_current_port=False,
        )
        sugar_line = lines[2]
        assert "?" in sugar_line.text
        assert "\u2191" not in sugar_line.text
        assert sugar_line.color == color_palette.DATA_STALE


# -----------------------------------------------------------------------------
# WorldMapTooltip.draw — render-tester
# -----------------------------------------------------------------------------


class TestTooltipDraw:
    def test_draw_does_not_crash_for_all_states(self):
        market_state = _market_with_history()
        tooltip = WorldMapTooltip(_font())
        surf = pygame.Surface((640, 360))

        # Current
        lines = build_tooltip_lines(
            port_name="Tortuga",
            observed_for_port=None,
            market_state=market_state,
            catalog_order=_CATALOG_ORDER,
            catalog_names=_CATALOG_NAMES,
            current_day=5, stale_threshold=5, is_current_port=True,
        )
        tooltip.draw(surf, lines, anchor_pos=(320, 180))

        # Fresh observed
        observed_fresh = {
            cid: ObservedPrice(price=42.0, day_seen=3)
            for cid in _CATALOG_ORDER
        }
        lines = build_tooltip_lines(
            port_name="Port Royal",
            observed_for_port=observed_fresh,
            market_state=market_state,
            catalog_order=_CATALOG_ORDER,
            catalog_names=_CATALOG_NAMES,
            current_day=5, stale_threshold=5, is_current_port=False,
        )
        tooltip.draw(surf, lines, anchor_pos=(180, 260))

        # Stale observed
        observed_stale = {
            cid: ObservedPrice(price=42.0, day_seen=2)
            for cid in _CATALOG_ORDER
        }
        lines = build_tooltip_lines(
            port_name="Havana",
            observed_for_port=observed_stale,
            market_state=market_state,
            catalog_order=_CATALOG_ORDER,
            catalog_names=_CATALOG_NAMES,
            current_day=10, stale_threshold=5, is_current_port=False,
        )
        tooltip.draw(surf, lines, anchor_pos=(140, 140))

        # Never visited
        lines = build_tooltip_lines(
            port_name="Nassau",
            observed_for_port=None,
            market_state=market_state,
            catalog_order=_CATALOG_ORDER,
            catalog_names=_CATALOG_NAMES,
            current_day=10, stale_threshold=5, is_current_port=False,
        )
        tooltip.draw(surf, lines, anchor_pos=(420, 110))

    def test_draw_writes_port_name_pixels_in_moon_core_color(self):
        """Sample COLOR_MOON_CORE-piksler i tooltip-region — havn-navn
        rendret med den fargen er en pålitelig signatur."""
        market_state = _market_with_history()
        tooltip = WorldMapTooltip(_font())
        # Bruk samme oppløsning som spillet for at clamp-logikken skal
        # plassere tooltipen i samme region testen scanner i (Fase 2.6).
        surf = pygame.Surface((constants.RENDER_WIDTH, constants.RENDER_HEIGHT))

        lines = build_tooltip_lines(
            port_name="Tortuga",
            observed_for_port=None,
            market_state=market_state,
            catalog_order=_CATALOG_ORDER,
            catalog_names=_CATALOG_NAMES,
            current_day=5, stale_threshold=5, is_current_port=True,
        )
        # Anker midt på skjermen så tooltip ikke trenger flip-clamp.
        anchor = (constants.RENDER_WIDTH // 2, constants.RENDER_HEIGHT // 3)
        tooltip.draw(surf, lines, anchor)

        # Tooltip ligger normalt under anchor, men kan flippe over ved
        # bunn-clamp. Skann ±100 px vertikalt for COLOR_MOON_CORE.
        target = constants.COLOR_MOON_CORE
        found = False
        h_max = constants.RENDER_HEIGHT
        w_max = constants.RENDER_WIDTH
        for y in range(max(0, anchor[1] - 100), min(h_max, anchor[1] + 100)):
            for x in range(max(0, anchor[0] - 80), min(w_max, anchor[0] + 80)):
                pix = surf.get_at((x, y))
                if (pix[0], pix[1], pix[2]) == target:
                    found = True
                    break
            if found:
                break
        assert found, "Tooltip-tekst (COLOR_MOON_CORE) ikke funnet"

    def test_empty_lines_does_not_crash(self):
        tooltip = WorldMapTooltip(_font())
        surf = pygame.Surface((640, 360))
        tooltip.draw(surf, [], anchor_pos=(100, 100))


# -----------------------------------------------------------------------------
# TooltipLine dataclass
# -----------------------------------------------------------------------------


def test_tooltip_line_has_text_and_color():
    line = TooltipLine(text="hello", color=(255, 0, 0))
    assert line.text == "hello"
    assert line.color == (255, 0, 0)
