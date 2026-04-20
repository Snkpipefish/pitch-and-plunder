"""RumorsDialog — Fase 3 C3-9.

Viser liste over aktive rykter fra `PlayerState.active_rumors`.
Åpnes med R-tast i PortVillageScene. Kun les-visning — ingen kjøp
(det skjer i tavern-natt-meny) og ingen aktivering.

Layout:
- Tittel: "Aktive rykter"
- Liste over rykter med:
  - Type-ikon/label (Regime: / Spike:)
  - Target (port + vare)
  - Payload-sammendrag (predicted regime / direction)
  - Dager igjen
- Hvis ingen: "Ingen aktive rykter"
- Hint: "Esc lukk" (ingen navigasjon, ingen aktivering)

Samme DialogOverlay-mønster som resten. Ingen R-tast-mening internt —
kun ESC lukker.
"""

from __future__ import annotations

import pygame

import constants
from state import GameState
from state.rumor_state import ActiveRumor
from ui.dialog_overlay import DEFAULT_PANEL_H, DEFAULT_PANEL_W, DialogOverlay


_TITLE_Y_OFFSET = 14
_LIST_START_Y_OFFSET = 40
_LIST_ROW_HEIGHT = 18
_LABEL_X_OFFSET = 24
_VALUE_X_FROM_RIGHT = 24
_HINT_Y_OFFSET_FROM_BOTTOM = 22

_TITLE_COLOR = constants.COLOR_MOON_CORE
_TYPE_COLOR = constants.COLOR_SHIRT
_TARGET_COLOR = constants.COLOR_STONE_LIT
_DAYS_COLOR = constants.COLOR_LANTERN
_EMPTY_COLOR = constants.COLOR_FOG
_HINT_COLOR = constants.COLOR_STONE_LIT

#: Maks rykter som vises i listen (ytterligere skroller ikke i C3-9 —
#: TTL-decay og øvre grense i balance bør holde listen håndterlig).
_MAX_VISIBLE_ROWS = 10


def _port_display_name(port_id: str) -> str:
    """Bruker-vennlig havn-navn. Faller tilbake til port_id hvis ukjent."""
    try:
        from config import port_config
        return port_config.get(port_id).name
    except (KeyError, RuntimeError):
        return port_id.replace("_", " ").title()


def _commodity_display_name(commodity_id: str) -> str:
    """Norsk vare-navn."""
    names = {
        "sugar": "sukker",
        "rum": "rom",
        "tobacco": "tobakk",
        "pitch": "bek",
    }
    return names.get(commodity_id, commodity_id)


def _regime_display(regime: str) -> str:
    """Norsk regime-navn."""
    names = {
        "rising": "stigende",
        "stable": "stabilt",
        "falling": "fallende",
    }
    return names.get(regime, regime)


def format_rumor_line(rumor: ActiveRumor) -> tuple[str, str]:
    """Returnér (label_text, right_text) for én rykte-rad.

    label: "Regime: {port} / {vare} → {regime}"
    right: "{days_remaining}d"

    Spike:
    label: "Spike: {port} / {vare} ({direction})"
    right: "{days_remaining}d"

    Hjelpefunksjon — også brukbar fra HUD eller tester.
    """
    port = _port_display_name(rumor.port_id)
    commodity = _commodity_display_name(rumor.commodity_id)
    days = f"{rumor.days_remaining}d"
    if rumor.rumor_type == "regime_preview":
        regime = _regime_display(rumor.payload.get("predicted_regime", "?"))
        label = f"Regime: {port} / {commodity} \u2192 {regime}"
    elif rumor.rumor_type == "price_spike_warning":
        direction = rumor.payload.get("direction", "?")
        arrow = "\u2191" if direction == "up" else "\u2193"
        label = f"Spike: {port} / {commodity} {arrow}"
    else:
        label = f"{rumor.rumor_type}: {port} / {commodity}"
    return label, days


class RumorsDialog(DialogOverlay):
    """Rykte-liste-dialog. Kun les-visning. Fase 3 C3-9."""

    def __init__(
        self,
        font: pygame.font.Font,
        game_state: GameState,
    ) -> None:
        super().__init__(font, panel_w=DEFAULT_PANEL_W, panel_h=DEFAULT_PANEL_H)
        self._state = game_state
        # Caches — invalideres via rumor-liste-endring (komplett liste-
        # equality-sjekk i _ensure_rows). Tekst-rendering er billig nok
        # til at dette er pragmatisk uten å introdusere tick_id.
        self._rows_snapshot: tuple[tuple[str, str, int], ...] | None = None
        self._label_surfs: list[pygame.Surface] = []
        self._value_surfs: list[pygame.Surface] = []
        self._title_surf: pygame.Surface | None = None
        self._hint_surf: pygame.Surface | None = None
        self._empty_surf: pygame.Surface | None = None

    def _ensure_title(self) -> None:
        if self._title_surf is None:
            self._title_surf = self._font.render(
                "Aktive rykter",
                False, _TITLE_COLOR,
            ).convert_alpha()

    def _ensure_hint(self) -> None:
        if self._hint_surf is None:
            self._hint_surf = self._font.render(
                "Esc lukk",
                False, _HINT_COLOR,
            ).convert_alpha()

    def _ensure_empty(self) -> None:
        if self._empty_surf is None:
            self._empty_surf = self._font.render(
                "Ingen aktive rykter",
                False, _EMPTY_COLOR,
            ).convert_alpha()

    def _rumor_snapshot(self) -> tuple[tuple[str, str, int], ...]:
        """Immutable-tuple representasjon av aktive rykter for cache-
        sammenligning. Inkluderer (rumor_type, port+commodity, days)."""
        return tuple(
            (r.rumor_type, f"{r.port_id}/{r.commodity_id}", r.days_remaining)
            for r in self._state.player_state.active_rumors
        )

    def _ensure_rows(self) -> None:
        """Re-render rad-surfaces hvis rykte-listen har endret seg."""
        snapshot = self._rumor_snapshot()
        if snapshot == self._rows_snapshot:
            return
        self._rows_snapshot = snapshot
        self._label_surfs = []
        self._value_surfs = []
        for r in self._state.player_state.active_rumors[:_MAX_VISIBLE_ROWS]:
            label, value = format_rumor_line(r)
            self._label_surfs.append(
                self._font.render(label, False, _TYPE_COLOR).convert_alpha()
            )
            self._value_surfs.append(
                self._font.render(value, False, _DAYS_COLOR).convert_alpha()
            )

    def handle_event(self, event: pygame.event.Event) -> None:
        """Kun ESC lukker. Ingen navigasjon, ingen aktivering."""
        if event.type != pygame.KEYDOWN:
            return
        if event.key == pygame.K_ESCAPE:
            self._want_close = True

    def draw(self, surface: pygame.Surface) -> None:
        self._ensure_title()
        self._ensure_hint()
        self._ensure_rows()

        self._draw_panel(surface)
        px, py = self._panel_x, self._panel_y
        w, h = self._panel_w, self._panel_h

        assert self._title_surf is not None
        surface.blit(self._title_surf, (px + _LABEL_X_OFFSET, py + _TITLE_Y_OFFSET))

        rumors = self._state.player_state.active_rumors
        if not rumors:
            self._ensure_empty()
            assert self._empty_surf is not None
            surface.blit(
                self._empty_surf,
                (px + _LABEL_X_OFFSET, py + _LIST_START_Y_OFFSET),
            )
        else:
            for i, (label_surf, value_surf) in enumerate(
                zip(self._label_surfs, self._value_surfs)
            ):
                row_y = py + _LIST_START_Y_OFFSET + i * _LIST_ROW_HEIGHT
                surface.blit(label_surf, (px + _LABEL_X_OFFSET, row_y))
                value_x = px + w - _VALUE_X_FROM_RIGHT - value_surf.get_width()
                surface.blit(value_surf, (value_x, row_y))

        assert self._hint_surf is not None
        surface.blit(
            self._hint_surf,
            (px + _LABEL_X_OFFSET, py + h - _HINT_Y_OFFSET_FROM_BOTTOM),
        )
