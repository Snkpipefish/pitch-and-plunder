"""Bors-overlay (Tortuga Exchange).

Dette er IKKE en full scene som bytter ut VillageScene, men et overlay
som rendres *oppa* landsbyen. Village fortsetter a oppdatere seg selv (maanen
beveger seg, lys svinger) mens spilleren er "inne" — det signaliserer
visuelt at du er i Borshuset, men fortsatt i verden.

Layout (480x240-panel, sentrert):
- Titel: "Tortuga Bors - Dag N"
- Kolonneheader: Vare | Pris | Antall
- 4 rader (valgt rad highlighted med COLOR_LANTERN)
- Bunn: "Gull: N d."
- Hint-linje: kontroller

Tastatur:
- Up/W   : flytt markør opp
- Down/S : flytt markør ned
- Right/D: kjøp 1 (Shift = 10)
- Left/A : selg 1 (Shift = 10)
- Esc    : lukk
"""

from __future__ import annotations

import pygame

import constants
from entities.commodity import InventoryItem
from systems.economy import Market
from systems.save import GameState


# Panel-geometri (i intern 640x360-oppløsning)
PANEL_W = 480
PANEL_H = 240
PANEL_X = (constants.RENDER_WIDTH - PANEL_W) // 2   # 80
PANEL_Y = (constants.RENDER_HEIGHT - PANEL_H) // 2  # 60

# Kolonner (i render-koordinater)
NAME_X = PANEL_X + 24
PRICE_X = PANEL_X + 200
SPARK_X = PANEL_X + 290
QTY_X = PANEL_X + 360

# Rader
HEADER_Y = PANEL_Y + 40
ROW_Y_START = PANEL_Y + 64
ROW_HEIGHT = 22

# Sparkline-geometri
SPARK_BARS = 10
SPARK_BAR_W = 3
SPARK_GAP = 1
SPARK_W = SPARK_BARS * (SPARK_BAR_W + SPARK_GAP)
SPARK_H = 10
SPARK_COLORKEY = (255, 0, 255)


def _build_panel_surface() -> pygame.Surface:
    """Semi-transparent stein-panel med ramme. Bygges én gang."""
    panel = pygame.Surface((PANEL_W, PANEL_H), pygame.SRCALPHA)
    # COLOR_STONE_DARK = (31, 37, 56), 95% opacity = 242/255
    panel.fill((*constants.COLOR_STONE_DARK, 242))
    pygame.draw.rect(
        panel, constants.COLOR_STONE_LIT, (0, 0, PANEL_W, PANEL_H), 2
    )
    # Subtil ny-ramme innenfor (gir ekstra "marmor"-preg)
    pygame.draw.rect(
        panel, constants.COLOR_STONE_MID, (4, 4, PANEL_W - 8, PANEL_H - 8), 1
    )
    return panel


class ExchangeOverlay:
    """UI-overlay for kjop/salg."""

    def __init__(
        self,
        font: pygame.font.Font,
        market: Market,
        state: GameState,
    ) -> None:
        self._font = font
        self._market = market
        self._state = state
        self._commodities = market.commodities
        self._n = len(self._commodities)
        self._selected = 0
        self._panel = _build_panel_surface()
        self._want_close = False

        # Statisk pre-rendret
        self._name_surfs = {
            c.id: font.render(
                c.name, False, constants.COLOR_STONE_BRIGHT
            ).convert_alpha()
            for c in self._commodities
        }
        self._header_name = font.render(
            "Vare", False, constants.COLOR_STONE_LIT
        ).convert_alpha()
        self._header_price = font.render(
            "Kjøp / Salg", False, constants.COLOR_STONE_LIT
        ).convert_alpha()
        self._header_qty = font.render(
            "Antall", False, constants.COLOR_STONE_LIT
        ).convert_alpha()
        # Pixelfont stoetter norsk tegn og piler – bruker dem for kompakt hint
        self._hint = font.render(
            "\u2191\u2193 velg   \u2192 kj\u00f8p   \u2190 selg   "
            "Shift\u00d710   Esc lukk",
            False,
            constants.COLOR_STONE_LIT,
        ).convert_alpha()

        # Dynamisk (cached)
        self._title_day: int | None = None
        self._title_surf: pygame.Surface | None = None

        self._price_tick_id: int = -1
        self._price_surfs: dict[str, pygame.Surface] = {}

        self._qty_key: tuple[int, ...] | None = None
        self._qty_surfs: dict[str, pygame.Surface] = {}

        self._gold_value: int | None = None
        self._gold_surf: pygame.Surface | None = None

        # Cargo-indikator ("Last: X/40") i topp-hoyre. Re-rendres bare naar
        # totalen endres.
        self._cargo_total: int | None = None
        self._cargo_cap: int | None = None
        self._cargo_surf: pygame.Surface | None = None

        # Sparkline-surfaces pre-allokerte per vare. Re-bakes naar
        # market.tick_id endrer seg (hver 10. sek).
        self._spark_tick_id: int = -1
        self._spark_surfs: dict[str, pygame.Surface] = {
            c.id: pygame.Surface((SPARK_W, SPARK_H)).convert()
            for c in self._commodities
        }
        for surf in self._spark_surfs.values():
            surf.set_colorkey(SPARK_COLORKEY)

    # --- Lifecycle ---

    @property
    def want_close(self) -> bool:
        return self._want_close

    # --- Input ---

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type != pygame.KEYDOWN:
            return
        key = event.key
        shift_held = bool(event.mod & pygame.KMOD_SHIFT)
        amount = 10 if shift_held else 1

        if key == pygame.K_ESCAPE:
            self._want_close = True
        elif key in (pygame.K_UP, pygame.K_w):
            self._selected = (self._selected - 1) % self._n
        elif key in (pygame.K_DOWN, pygame.K_s):
            self._selected = (self._selected + 1) % self._n
        elif key in (pygame.K_RIGHT, pygame.K_d):
            self._buy(amount)
        elif key in (pygame.K_LEFT, pygame.K_a):
            self._sell(amount)

    def _buy(self, amount: int) -> None:
        cid = self._commodities[self._selected].id
        new_gold, new_inv, bought = self._market.buy(
            cid,
            amount,
            self._state.gold,
            self._state.inventory,
            cargo_capacity=self._state.cargo_capacity,
        )
        if bought > 0:
            self._state.gold = new_gold
            self._state.inventory = new_inv

    def _sell(self, amount: int) -> None:
        cid = self._commodities[self._selected].id
        new_gold, new_inv, sold = self._market.sell(
            cid, amount, self._state.gold, self._state.inventory
        )
        if sold > 0:
            self._state.gold = new_gold
            self._state.inventory = new_inv

    # --- Update ---

    def update(self, dt: float) -> None:
        """Ingen tidsdrevet logikk i overlayet selv. Markedet ticker i village."""

    # --- Cache-invalidering ---

    def _ensure_title(self) -> None:
        day = self._state.clock.day
        if self._title_day != day:
            self._title_day = day
            self._title_surf = self._font.render(
                f"Tortuga Børs \u2014 Dag {day}",
                False,
                constants.COLOR_MOON_CORE,
            ).convert_alpha()

    def _ensure_prices(self) -> None:
        tid = self._market.tick_id
        if self._price_tick_id == tid:
            return
        self._price_tick_id = tid
        for c in self._commodities:
            buy_p = self._market.buy_price(c.id)
            sell_p = self._market.sell_price(c.id)
            self._price_surfs[c.id] = self._font.render(
                f"{buy_p:>3d} / {sell_p:>3d}",
                False,
                constants.COLOR_SHIRT,
            ).convert_alpha()

    def _ensure_qty(self) -> None:
        inv = self._state.inventory
        # Cache-noekkel: (quantity, rounded avg_cost) per vare
        key = tuple(
            (
                inv.get(c.id, InventoryItem()).quantity,
                round(inv.get(c.id, InventoryItem()).avg_cost, 2),
            )
            for c in self._commodities
        )
        if self._qty_key == key:
            return
        self._qty_key = key
        for c in self._commodities:
            item = inv.get(c.id, InventoryItem())
            if item.quantity == 0:
                text = "0"
            else:
                text = f"{item.quantity} @ {item.avg_cost:.2f}"
            self._qty_surfs[c.id] = self._font.render(
                text, False, constants.COLOR_SHIRT
            ).convert_alpha()

    def _ensure_gold(self) -> None:
        g = self._state.gold
        if self._gold_value == g:
            return
        self._gold_value = g
        self._gold_surf = self._font.render(
            f"Gull: {g} d.", False, constants.COLOR_MOON_CORE
        ).convert_alpha()

    def _ensure_sparklines(self) -> None:
        tid = self._market.tick_id
        if self._spark_tick_id == tid:
            return
        self._spark_tick_id = tid
        for c in self._commodities:
            surf = self._spark_surfs[c.id]
            surf.fill(SPARK_COLORKEY)
            history = c.price_history[-SPARK_BARS:]
            if not history:
                continue
            # Auto-skaler til min/max i vinduet — viser trend, ikke
            # absolutt nivaa. Hvis hi == lo (alle like) → midtstilte barer.
            lo = min(history)
            hi = max(history)
            span = hi - lo if hi > lo else 1.0
            max_bar_h = SPARK_H - 1
            step = SPARK_BAR_W + SPARK_GAP
            for i, p in enumerate(history):
                ratio = (p - lo) / span
                ratio = max(0.0, min(1.0, ratio))
                h = max(1, int(ratio * max_bar_h))
                x = i * step
                y = SPARK_H - h
                pygame.draw.rect(
                    surf,
                    constants.COLOR_STONE_LIT,
                    (x, y, SPARK_BAR_W, h),
                )

    def _ensure_cargo(self) -> None:
        total = sum(item.quantity for item in self._state.inventory.values())
        cap = self._state.cargo_capacity
        if self._cargo_total == total and self._cargo_cap == cap:
            return
        self._cargo_total = total
        self._cargo_cap = cap
        # Dempet farge hvis lasten er full (stoene varselsignal uten roedt)
        color = (
            constants.COLOR_LANTERN if total >= cap else constants.COLOR_STONE_LIT
        )
        self._cargo_surf = self._font.render(
            f"Last: {total}/{cap}", False, color
        ).convert_alpha()

    # --- Rendering ---

    def draw(self, surface: pygame.Surface) -> None:
        self._ensure_title()
        self._ensure_prices()
        self._ensure_qty()
        self._ensure_gold()
        self._ensure_cargo()
        self._ensure_sparklines()

        surface.blit(self._panel, (PANEL_X, PANEL_Y))
        assert self._title_surf is not None
        surface.blit(self._title_surf, (PANEL_X + 16, PANEL_Y + 14))

        # Cargo-indikator, topp-hoyre (samme baseline som tittelen)
        assert self._cargo_surf is not None
        cargo_x = PANEL_X + PANEL_W - self._cargo_surf.get_width() - 16
        surface.blit(self._cargo_surf, (cargo_x, PANEL_Y + 14))

        surface.blit(self._header_name, (NAME_X, HEADER_Y))
        surface.blit(self._header_price, (PRICE_X, HEADER_Y))
        surface.blit(self._header_qty, (QTY_X, HEADER_Y))

        # Rader: dimmet hvis lasten er full (kan ikke kjoepe mer av noen vare)
        cargo_full = (self._cargo_total or 0) >= (self._cargo_cap or 0)
        for i, c in enumerate(self._commodities):
            y = ROW_Y_START + i * ROW_HEIGHT
            if i == self._selected:
                # Highlight-ramme i COLOR_LANTERN (1 px). Dempet naar
                # lasten er full slik at markoeren ikke lyver om at
                # radene er aktive.
                frame_color = (
                    constants.COLOR_STONE_MID
                    if cargo_full
                    else constants.COLOR_LANTERN
                )
                pygame.draw.rect(
                    surface,
                    frame_color,
                    (PANEL_X + 12, y - 3, PANEL_W - 24, ROW_HEIGHT - 2),
                    1,
                )
            surface.blit(self._name_surfs[c.id], (NAME_X, y))
            surface.blit(self._price_surfs[c.id], (PRICE_X, y))
            # Sparkline: vertikalt sentrert mot row-baseline (font ~8 px)
            surface.blit(
                self._spark_surfs[c.id],
                (SPARK_X, y + 2),
            )
            surface.blit(self._qty_surfs[c.id], (QTY_X, y))

        assert self._gold_surf is not None
        surface.blit(self._gold_surf, (PANEL_X + 16, PANEL_Y + PANEL_H - 44))
        surface.blit(self._hint, (PANEL_X + 16, PANEL_Y + PANEL_H - 22))
