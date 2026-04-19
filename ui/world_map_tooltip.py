"""Tooltip for fokusert havn på verdenskartet (Fase 2B C8).

Viser observed-pris-data for havnen spilleren har piltast-fokus på.
Layout per FASE_2B.md §8.3 og VISUELL_REFERANSE §3.3:

```
Tortuga                                    ← MOON_CORE (havn-navn)
Du er her                                  ← FRESH (current port)
Sukker:  44 ↑                              ← FRESH + trend
Rom:     76 →
Tobakk:  91 ↓
Bek:     46 →
```

Eller for stale data:
```
Havana
sist besøkt Dag 2 (8 d. siden)             ← STALE_AGE (rød dagsteller)
Sukker:  42 ?                              ← STALE (grå)
...
```

Eller for aldri besøkt:
```
Nassau
aldri besøkt                               ← NEVER (mørk)
```

Designvalg:
- `build_tooltip_lines` er pure data — testbar uten pygame.
  `WorldMapTooltip.draw` tar list av TooltipLine og blits.
- Trend-pil for fersk data hentes fra `compute_trend` på den fokuserte
  havnens price_history (samme funksjon som exchange-overlay bruker).
  Stale data får alltid `?` per spec — utdatert observed skal ikke
  late som om den vet retningen markedet beveger seg i nå.
- Tooltip-plassering: under markøren, med klamping mot skjerm-kanter
  slik at innhold ikke blir kuttet hvis markøren er nær kant.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import pygame

import constants
from entities.commodity import compute_trend
from entities.port_marker import MARKER_SIZE
from state.observed_price import ObservedPrice
from ui import color_palette


log = logging.getLogger(__name__)


#: Padding fra markør-bunn til tooltip-topp (matcher §3.3-direktivet).
_TOOLTIP_PADDING_Y = 18  # under labelen som allerede er ~ringbunn+11

#: Tooltip-bakgrunn (mørk for kontrast mot kart) og ramme.
_TOOLTIP_BG = constants.COLOR_STONE_DARKEST
_TOOLTIP_BORDER = constants.COLOR_STONE_DARK

#: Padding mellom tooltip-kant og første tekst-linje.
_TEXT_PADDING_X = 4
_TEXT_PADDING_Y = 3
_LINE_SPACING = 2  # ekstra px mellom linjer

#: Stale-glyf erstatter trend-pil for stale data — utdatert observed
#: skal ikke late som om den vet markeds-retning.
_STALE_GLYPH = "?"
#: Fallback-glyf når compute_trend ikke har nok historikk (returnerer
#: tom streng). Bruker samme stable-glyf som compute_trend ville gitt
#: hvis historikken var stor nok.
_NEUTRAL_GLYPH = "\u2192"


@dataclass
class TooltipLine:
    """Én linje i tooltipen — tekst + farge. Caller blits via font."""
    text: str
    color: tuple[int, int, int]


def build_tooltip_lines(
    *,
    port_name: str,
    observed_for_port: dict[str, ObservedPrice] | None,
    market_state,  # MarketState; importert som type-hint hadde gitt sirkularitet
    catalog_order: list[str],  # commodity_id-rekkefølge (sukker, rum, tobakk, bek)
    catalog_names: dict[str, str],  # cid → display-navn
    current_day: int,
    stale_threshold: int,
    is_current_port: bool,
) -> list[TooltipLine]:
    """Bygg tooltip-linjer for én havn basert på observed-state.

    Returnerer ordnet liste — caller render i rekkefølge med
    samme y-spacing.

    Tilstands-logikk:
    - is_current_port=True: "Du er her" + ferske priser med trend
    - observed_for_port=None eller {}: "aldri besøkt", ingen pris-rader
    - observed med alle entries fersk: "sist besøkt Dag X (Y d. siden)"
      + priser med trend
    - observed med stale-status: "sist besøkt Dag X (Y d. siden)" i
      stale-farge + priser i stale-farge med "?" trend

    Per spec §8.3 er stale-grensen `current_day - day_seen > threshold`,
    og caller passer `stale_threshold` fra `balance.observed
    .stale_threshold_days` (default 5).
    """
    lines: list[TooltipLine] = [
        TooltipLine(text=port_name, color=constants.COLOR_MOON_CORE),
    ]

    if is_current_port:
        # Spilleren er her nå — ferske priser med trend fra
        # markedets price_history.
        lines.append(TooltipLine(
            text="Du er her", color=color_palette.DATA_FRESH,
        ))
        for cid in catalog_order:
            cm = market_state.commodities.get(cid)
            if cm is None:
                continue
            arrow = compute_trend(cm.price_history) or _NEUTRAL_GLYPH
            display_name = catalog_names.get(cid, cid)
            price = int(round(cm.current_price))
            lines.append(TooltipLine(
                text=f"{display_name}: {price} {arrow}",
                color=color_palette.DATA_FRESH,
            ))
        return lines

    # Annen havn — sjekk observed-status
    if not observed_for_port:
        # Aldri besøkt
        lines.append(TooltipLine(
            text="aldri besøkt", color=color_palette.DATA_NEVER,
        ))
        return lines

    # Bestem fersk vs stale basert på siste day_seen i denne havnen.
    # Alle commodities snapshotes samtidig (write_observed_for_port
    # itererer atomisk), så de har lik day_seen. Bruk en hvilken som
    # helst entry til age-beregning.
    sample_obs = next(iter(observed_for_port.values()))
    days_ago = sample_obs.days_since(current_day)
    is_stale = sample_obs.is_stale(current_day, stale_threshold)

    age_text = (
        f"sist besøkt Dag {sample_obs.day_seen} "
        f"({days_ago} d. siden)"
    )
    age_color = color_palette.DATA_STALE_AGE if is_stale else color_palette.DATA_FRESH
    lines.append(TooltipLine(text=age_text, color=age_color))

    # Per-commodity rader
    price_color = color_palette.DATA_STALE if is_stale else color_palette.DATA_FRESH
    for cid in catalog_order:
        obs = observed_for_port.get(cid)
        if obs is None:
            continue
        display_name = catalog_names.get(cid, cid)
        price = int(round(obs.price))
        if is_stale:
            arrow = _STALE_GLYPH
        else:
            cm = market_state.commodities.get(cid)
            if cm is not None:
                arrow = compute_trend(cm.price_history) or _NEUTRAL_GLYPH
            else:
                arrow = _STALE_GLYPH
        lines.append(TooltipLine(
            text=f"{display_name}: {price} {arrow}",
            color=price_color,
        ))

    return lines


class WorldMapTooltip:
    """Render-klasse for tooltip. Holder font og rendrer linjer per
    frame for fokusert havn.

    Caller bygger TooltipLine-listen via `build_tooltip_lines` og
    sender den til `draw` med ankur-posisjon (typisk markør-senter).
    """

    def __init__(self, font: pygame.font.Font) -> None:
        self._font = font

    def draw(
        self,
        surface: pygame.Surface,
        lines: list[TooltipLine],
        anchor_pos: tuple[int, int],
    ) -> None:
        """Tegn tooltip under markøren ved anchor_pos.

        Tooltip-boksen klampes mot skjerm-kanter slik at innhold ikke
        blir kuttet hvis markøren er nær kart-kant.
        """
        if not lines:
            return

        # Pre-render hver linje for å få bredder og høyder
        rendered = [
            (self._font.render(line.text, False, line.color).convert_alpha())
            for line in lines
        ]
        max_w = max(s.get_width() for s in rendered)
        line_h = rendered[0].get_height()
        total_h = (
            line_h * len(rendered)
            + _LINE_SPACING * max(0, len(rendered) - 1)
            + _TEXT_PADDING_Y * 2
        )
        total_w = max_w + _TEXT_PADDING_X * 2

        # Foreslått posisjon: rett under markøren (under labelen).
        # anchor_pos er markør-senter; tooltip-topp er under markør-
        # bunn med padding.
        x = anchor_pos[0] - total_w // 2
        y = anchor_pos[1] + MARKER_SIZE // 2 + _TOOLTIP_PADDING_Y

        # Klamp mot skjerm-kanter (640x360)
        if x < 2:
            x = 2
        if x + total_w > constants.RENDER_WIDTH - 2:
            x = constants.RENDER_WIDTH - 2 - total_w
        if y + total_h > constants.RENDER_HEIGHT - 2:
            # Tooltip ville gå utenfor bunnen — flytt OPP markøren
            # i stedet (legg den over markør-toppen).
            y = anchor_pos[1] - MARKER_SIZE // 2 - total_h - 2
        if y < 2:
            y = 2

        # Tegn bakgrunn + ramme
        pygame.draw.rect(surface, _TOOLTIP_BG, (x, y, total_w, total_h))
        pygame.draw.rect(surface, _TOOLTIP_BORDER, (x, y, total_w, total_h), 1)

        # Tegn linjene
        text_y = y + _TEXT_PADDING_Y
        for surf in rendered:
            surface.blit(surf, (x + _TEXT_PADDING_X, text_y))
            text_y += line_h + _LINE_SPACING
