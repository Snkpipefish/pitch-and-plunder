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
from entities.commodity import InventoryItem, compute_trend
from systems import balance as _balance
from systems.economy import Market
from systems.save import GameState
from ui.toast import Toast, ToastQueue


# Panel-geometri (i intern 640x360-oppløsning)
PANEL_W = 480
PANEL_H = 240
PANEL_X = (constants.RENDER_WIDTH - PANEL_W) // 2   # 80
PANEL_Y = (constants.RENDER_HEIGHT - PANEL_H) // 2  # 60

# Kolonner (i render-koordinater)
NAME_X = PANEL_X + 24
PRICE_X = PANEL_X + 200
TREND_X = PANEL_X + 310
QTY_X = PANEL_X + 360

# Rader
HEADER_Y = PANEL_Y + 40
ROW_Y_START = PANEL_Y + 64
ROW_HEIGHT = 22

# Trend-indikator (Commit 5C, erstatter sparkline). Piler i fargekodet sett:
# stigende = kald blå, stabil = dempet grå, fallende = varm ember.
_TREND_COLORS = {
    "\u2191": constants.COLOR_STONE_LIT,
    "\u2192": constants.COLOR_FOG,
    "\u2193": constants.COLOR_EMBER,
}


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
        toasts: ToastQueue | None = None,
    ) -> None:
        self._font = font
        self._market = market
        self._state = state
        self._commodities = market.commodities
        self._n = len(self._commodities)
        self._selected = 0
        self._panel = _build_panel_surface()
        self._want_close = False
        # ToastQueue delt med VillageScene – brukes for feilhint
        # (gullmangel) ved mislykket kjøp. None = ingen toasts (testmodus).
        self._toasts = toasts

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
        # Gebyr-linje under gull-linjen. Re-rendres kun når gebyret endrer
        # seg (F5 hot-reload av balance.json) via _ensure_fee_surf().
        self._fee_value: int | None = None
        self._fee_surf: pygame.Surface | None = None

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

        # Trend-indikator pre-rendres for hver tick_id og vare. Cache-
        # nøkkel er (tick_id, commodity.id) slik at re-render kun skjer
        # ved daggry. Tom streng ("<3 dager") → lagres som None for å
        # markere "ikke noe blit".
        self._trend_tick_id: int = -1
        self._trend_surfs: dict[str, pygame.Surface | None] = {}

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
            # Reset dedup-flagget slik at samme feilmelding kan vises på nytt
            # hvis spilleren senere forsøker og feiler igjen.
            self._last_toast_text = None
            return
        # bought == 0: diagnoser hvorfor og gi feilhint via toast
        if self._toasts is None:
            return
        price = self._market.buy_price(cid)
        fee = _balance.get().economy.transaction_fee
        if self._state.gold < price + fee:
            # Gullet rekker ikke til én enhet + gebyr
            self._push_toast_once(
                f"For lite gull (trenger {price + fee} d.)",
                constants.COLOR_EMBER,
            )
        # Andre årsaker (cargo fullt) kommuniseres allerede via "Last: X/Y"-
        # indikatoren og dimmet seleksjonsramme – ingen toast nødvendig.

    def _sell(self, amount: int) -> None:
        cid = self._commodities[self._selected].id
        new_gold, new_inv, sold = self._market.sell(
            cid, amount, self._state.gold, self._state.inventory
        )
        if sold > 0:
            self._state.gold = new_gold
            self._state.inventory = new_inv

    def _push_toast_once(
        self,
        text: str,
        color: tuple[int, int, int],
    ) -> None:
        """Push feilhint-toast hvis ikke identisk toast allerede er i køen.

        Enkel dedup: hvis siste toast i køen har samme tekst og er fortsatt
        alive, skip. Unngår at gjentatte tastetrykk spammer skjermen med
        samme feilmelding.
        """
        assert self._toasts is not None
        # Enkel sjekk: hvis siste toast er aktiv og har samme tekst, skip.
        # Vi eier ikke privat tilstand til ToastQueue, så bruker count +
        # en flagg-attributt for sist-visede tekst.
        if getattr(self, "_last_toast_text", None) == text:
            return
        self._last_toast_text = text
        self._toasts.push(
            Toast(
                font=self._font,
                text=text,
                color=color,
                duration=2.0,
            )
        )

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

    def _ensure_trends(self) -> None:
        """Pre-render trend-pil per vare. Oppdateres én gang per daggry
        (når `market.tick_id` endrer seg). Varer med < 3 dager historikk
        får `None` (ingen blit).
        """
        tid = self._market.tick_id
        if self._trend_tick_id == tid:
            return
        self._trend_tick_id = tid
        for c in self._commodities:
            arrow = compute_trend(c.price_history)
            if not arrow:
                self._trend_surfs[c.id] = None
                continue
            color = _TREND_COLORS.get(arrow, constants.COLOR_FOG)
            self._trend_surfs[c.id] = self._font.render(
                arrow, False, color
            ).convert_alpha()

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
        self._ensure_trends()

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
            # Trend-pil: tegnes kun hvis vi har ≥3 dagers historikk
            trend_surf = self._trend_surfs.get(c.id)
            if trend_surf is not None:
                surface.blit(trend_surf, (TREND_X, y))
            surface.blit(self._qty_surfs[c.id], (QTY_X, y))

        assert self._gold_surf is not None
        # Gull-linje sammen med gebyr-info ved siden av (høyrekant av panel)
        surface.blit(self._gold_surf, (PANEL_X + 16, PANEL_Y + PANEL_H - 44))
        self._ensure_fee_surf()
        assert self._fee_surf is not None
        fee_x = PANEL_X + PANEL_W - self._fee_surf.get_width() - 16
        surface.blit(self._fee_surf, (fee_x, PANEL_Y + PANEL_H - 44))
        surface.blit(self._hint, (PANEL_X + 16, PANEL_Y + PANEL_H - 22))

    def _ensure_fee_surf(self) -> None:
        """Re-render gebyr-linja hvis transaction_fee har endret seg.

        Les fra balance.json; caches med fee-verdien som nøkkel. Hot-reload
        via F5 i dev-mode får teksten til å oppdatere seg neste frame.
        """
        fee = _balance.get().economy.transaction_fee
        if fee == self._fee_value and self._fee_surf is not None:
            return
        self._fee_value = fee
        self._fee_surf = self._font.render(
            f"Gebyr per handel: {fee} d.",
            False,
            constants.COLOR_FOG,
        ).convert_alpha()
