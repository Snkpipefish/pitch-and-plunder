"""CacheSubDialog — Fase 3 C3-5.

Per-havn gull-cache legg-inn/ta-ut. Åpnes fra HarbormasterDialog sin
"Åpne cache"-oppføring. Arver fra DialogOverlay.

UI-layout (FASE_3.md §1.12, presisering C3-5):
- Tittel: "{Port} Gullkiste" for Tortuga, "{Port} Cache" for andre havner.
  Eneste forskjell mellom havnene — all annen logikk/layout er identisk.
  Spilleren lærer score-mekanikken gjennom spill (ingen HUD-score) og
  score-overlay ved game-over (C3-12).
- To balanse-linjer: "På hånden: N d." og "I gullkiste/cache: N d."
- To modus-rader: "Legg inn" og "Ta ut". Up/Down toggler aktiv modus.
- Beløps-linje: "Beløp: N d." — A/D justerer ±1 (Shift=10), klampes
  per aktiv modus.
- Enter bekrefter, ESC avbryter (uten mutasjon).
- Hint: "A/D beløp  Shift×10  Enter bekreft  Esc lukk"

Aktiv modus-logikk:
- "Legg inn": max beløp = `player_state.gold` (kan ikke legge inn mer
  enn man har).
- "Ta ut": max beløp = `port_caches.get(port_id, 0)` (kan ikke ta ut
  mer enn cachen har).
- Ved modus-toggle: beløp nullstilles (unngår forvirring "hva
  representerer dette tallet nå?").

Commit-semantikk:
- Enter med beløp > 0:
  - Legg inn: trekker fra gold, legger til i port_caches[port_id].
  - Ta ut: trekker fra port_caches[port_id], legger til gold.
  - Dialog forblir åpen, beløp nullstilles, balanse-linjer oppdateres.
  - Toast-feedback med deponert/uttatt-mengde.
- Enter med beløp == 0: no-op (ingen feedback, ingen crash).
- ESC lukker uten ytterligere mutasjon.

Tortuga-spesialisering:
- Tortuga sitt port_caches["tortuga"]-tall ER spillets score
  (`GameState.get_score()`). Men dialog-UI viser det bare som
  "gullkiste"-balanse, ikke eksplisitt score-linje. Presisering #2:
  score forblir usynlig til C3-12. Redundans unngås ved at
  cache-balansen og score ER samme tall, ingen separat score-display.
"""

from __future__ import annotations

import pygame

import constants
from config import port_config
from state import GameState
from systems import balance as _balance
from systems import rest as _rest
from ui.dialog_overlay import DEFAULT_PANEL_H, DEFAULT_PANEL_W, DialogOverlay
from ui.toast import ToastQueue


#: Modus-konstanter
MODE_DEPOSIT = "deposit"
MODE_WITHDRAW = "withdraw"
_MODES = (MODE_DEPOSIT, MODE_WITHDRAW)

#: Layout-konstanter (matcher TavernDialog/HarbormasterDialog-mønster)
_TITLE_Y_OFFSET = 14
_ON_HAND_Y_OFFSET = 32
_CACHE_Y_OFFSET = 46
_MODES_START_Y_OFFSET = 72
_MODE_ROW_HEIGHT = 22
_AMOUNT_Y_OFFSET = 128
_LABEL_X_OFFSET = 24
_VALUE_X_FROM_RIGHT = 24
_HINT_Y_OFFSET_FROM_BOTTOM = 22

_TITLE_COLOR = constants.COLOR_MOON_CORE
_BALANCE_COLOR = constants.COLOR_MOON_CORE
_MODE_INACTIVE_COLOR = constants.COLOR_STONE_LIT
_MODE_ACTIVE_COLOR = constants.COLOR_SHIRT
_AMOUNT_COLOR = constants.COLOR_LANTERN_BRIGHT
_CURSOR_COLOR = constants.COLOR_LANTERN
_HINT_COLOR = constants.COLOR_STONE_LIT
_ERROR_COLOR = constants.COLOR_EMBER
_SUCCESS_COLOR = constants.COLOR_LANTERN_BRIGHT


class CacheSubDialog(DialogOverlay):
    """Gull-cache deposit/withdraw-dialog. Fase 3 C3-5.

    Identisk for alle 4 havner; Tortuga skiller seg kun på tittel-
    ("Gullkiste" vs "Cache"). `port_caches[port_id]` muteres direkte —
    cache er lagret i PlayerState.
    """

    def __init__(
        self,
        font: pygame.font.Font,
        game_state: GameState,
        port_id: str,
        toasts: ToastQueue | None = None,
    ) -> None:
        # C3-10.5: toasts via base — felles _push_toast.
        super().__init__(
            font, panel_w=DEFAULT_PANEL_W, panel_h=DEFAULT_PANEL_H,
            toasts=toasts,
        )
        self._state = game_state
        self._port_id = port_id
        # Modus-state: "deposit" (legg inn) eller "withdraw" (ta ut).
        self._mode: str = MODE_DEPOSIT
        # Gjeldende beløp som ventes på commit. 0 = no-op ved Enter.
        self._amount: int = 0
        # Sørg for at port_caches-entry eksisterer for denne havnen
        # (default 0). Gjør mutasjons-logikken enklere nedenfor.
        self._state.player_state.port_caches.setdefault(self._port_id, 0)
        # Caches for pre-rendrede tekst-surfaces
        self._title_surf: pygame.Surface | None = None
        self._hint_surf: pygame.Surface | None = None
        self._mode_label_surfs: dict[str, pygame.Surface] = {}
        self._balance_cached_key: tuple[int, int] | None = None
        self._on_hand_surf: pygame.Surface | None = None
        self._cache_surf: pygame.Surface | None = None
        self._amount_cached: int | None = None
        self._amount_surf: pygame.Surface | None = None

    # --- Cache-helpers ---

    def _ensure_title(self) -> None:
        if self._title_surf is None:
            port_name = port_config.get(self._port_id).name
            # Tortuga-spesialisering: "Gullkiste". Alle andre: "Cache".
            box_label = "Gullkiste" if self._port_id == "tortuga" else "Cache"
            self._title_surf = self._font.render(
                f"{port_name} {box_label}",
                False, _TITLE_COLOR,
            ).convert_alpha()

    def _ensure_hint(self) -> None:
        if self._hint_surf is None:
            self._hint_surf = self._font.render(
                "A/D bel\u00f8p   Shift\u00d710   Enter bekreft   Esc lukk",
                False, _HINT_COLOR,
            ).convert_alpha()

    def _ensure_mode_labels(self) -> None:
        """Pre-render "Legg inn" og "Ta ut"-labels i begge farger."""
        if self._mode_label_surfs:
            return
        for mode, text in (
            (MODE_DEPOSIT, "Legg inn"),
            (MODE_WITHDRAW, "Ta ut"),
        ):
            # Lagre begge farger for enkel veksling ved cursor-endring
            self._mode_label_surfs[f"{mode}_active"] = self._font.render(
                text, False, _MODE_ACTIVE_COLOR,
            ).convert_alpha()
            self._mode_label_surfs[f"{mode}_inactive"] = self._font.render(
                text, False, _MODE_INACTIVE_COLOR,
            ).convert_alpha()

    def _ensure_balance_surfs(self) -> None:
        """Re-render balanse-linjer når gold eller cache-balance endrer seg."""
        gold = self._state.player_state.gold
        cache_balance = self._state.player_state.port_caches.get(
            self._port_id, 0
        )
        key = (gold, cache_balance)
        if key == self._balance_cached_key:
            return
        self._balance_cached_key = key
        self._on_hand_surf = self._font.render(
            f"P\u00e5 h\u00e5nden: {gold} d.", False, _BALANCE_COLOR,
        ).convert_alpha()
        box_label = "Gullkiste" if self._port_id == "tortuga" else "Cache"
        self._cache_surf = self._font.render(
            f"I {box_label.lower()}: {cache_balance} d.",
            False, _BALANCE_COLOR,
        ).convert_alpha()

    def _ensure_amount_surf(self) -> None:
        if self._amount == self._amount_cached and self._amount_surf is not None:
            return
        self._amount_cached = self._amount
        self._amount_surf = self._font.render(
            f"Bel\u00f8p: {self._amount} d.", False, _AMOUNT_COLOR,
        ).convert_alpha()

    # --- Limit-logikk ---

    def _current_max(self) -> int:
        """Maks beløp for aktiv modus."""
        if self._mode == MODE_DEPOSIT:
            return max(0, self._state.player_state.gold)
        # withdraw
        return max(0, self._state.player_state.port_caches.get(self._port_id, 0))

    def _clamp_amount(self) -> None:
        """Klamp _amount til [0, _current_max()]."""
        self._amount = max(0, min(self._amount, self._current_max()))

    # --- Event handling ---

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type != pygame.KEYDOWN:
            return
        if event.key == pygame.K_ESCAPE:
            self._want_close = True
            return
        if event.key in (pygame.K_UP, pygame.K_w):
            self._set_mode(MODE_DEPOSIT)
            return
        if event.key in (pygame.K_DOWN, pygame.K_s):
            self._set_mode(MODE_WITHDRAW)
            return
        shift_held = bool(event.mod & pygame.KMOD_SHIFT)
        step = 10 if shift_held else 1
        if event.key in (pygame.K_LEFT, pygame.K_a):
            self._amount = max(0, self._amount - step)
            return
        if event.key in (pygame.K_RIGHT, pygame.K_d):
            self._amount = min(self._current_max(), self._amount + step)
            return
        if event.key == pygame.K_RETURN:
            self._commit()

    def _set_mode(self, mode: str) -> None:
        """Bytt modus. Nullstill beløp for å unngå forvirring."""
        if mode not in _MODES:
            return
        if mode == self._mode:
            return
        self._mode = mode
        self._amount = 0

    def _commit(self) -> None:
        """Utfør deposit eller withdraw på aktiv modus + beløp.

        No-op hvis beløp = 0. Defensiv re-klamp før mutasjon slik at
        en stale amount-verdi (etter at balance-endringer gjør beløpet
        for stort) ikke overtrekker.
        """
        if self._amount <= 0:
            return
        self._clamp_amount()
        if self._amount <= 0:
            return
        port_caches = self._state.player_state.port_caches
        if self._mode == MODE_DEPOSIT:
            # Legg inn: trekk fra gold, legg til i cache
            self._state.player_state.gold -= self._amount
            port_caches[self._port_id] = (
                port_caches.get(self._port_id, 0) + self._amount
            )
            self._push_toast(
                f"Deponert {self._amount} d.",
                _SUCCESS_COLOR,
            )
        else:
            # Ta ut: trekk fra cache, legg til gold
            port_caches[self._port_id] = (
                port_caches.get(self._port_id, 0) - self._amount
            )
            self._state.player_state.gold += self._amount
            self._push_toast(
                f"Tatt ut {self._amount} d.",
                _SUCCESS_COLOR,
            )
        # Fase 3 C3-8: rom-decay per cache-commit. Kost leses fra balance
        # slik at deposit og withdraw bruker samme cost_hours-nøkkel.
        cost_hours = _balance.get().actions.cost_hours_per_action.get(
            "cache_deposit", 0.25
        )
        _rest.consume_for_action(self._state, cost_hours)
        # Nullstill beløp etter commit
        self._amount = 0

    # _push_toast arves fra DialogOverlay (C3-10.5)

    # --- Rendering ---

    def draw(self, surface: pygame.Surface) -> None:
        self._ensure_title()
        self._ensure_hint()
        self._ensure_mode_labels()
        self._ensure_balance_surfs()
        self._ensure_amount_surf()
        # Re-klamp beløp defensivt ved hver draw — dekker tilfeller der
        # hot-reload eller ekstern mutasjon har krympet maks.
        if self._amount > self._current_max():
            self._amount = self._current_max()
            self._amount_cached = None  # tving re-render
            self._ensure_amount_surf()

        self._draw_panel(surface)
        px, py = self._panel_x, self._panel_y
        w, h = self._panel_w, self._panel_h

        assert self._title_surf is not None
        surface.blit(self._title_surf, (px + _LABEL_X_OFFSET, py + _TITLE_Y_OFFSET))
        assert self._on_hand_surf is not None
        assert self._cache_surf is not None
        surface.blit(self._on_hand_surf, (px + _LABEL_X_OFFSET, py + _ON_HAND_Y_OFFSET))
        surface.blit(self._cache_surf, (px + _LABEL_X_OFFSET, py + _CACHE_Y_OFFSET))

        # Modus-rader: "Legg inn" (index 0) og "Ta ut" (index 1)
        for i, mode in enumerate(_MODES):
            row_y = py + _MODES_START_Y_OFFSET + i * _MODE_ROW_HEIGHT
            is_active = (mode == self._mode)
            if is_active:
                pygame.draw.rect(
                    surface,
                    _CURSOR_COLOR,
                    (px + 12, row_y - 3, w - 24, _MODE_ROW_HEIGHT - 2),
                    1,
                )
            key = f"{mode}_active" if is_active else f"{mode}_inactive"
            surface.blit(
                self._mode_label_surfs[key], (px + _LABEL_X_OFFSET, row_y)
            )

        # Beløp-linje
        assert self._amount_surf is not None
        surface.blit(
            self._amount_surf, (px + _LABEL_X_OFFSET, py + _AMOUNT_Y_OFFSET)
        )

        # Hint
        assert self._hint_surf is not None
        surface.blit(
            self._hint_surf,
            (px + _LABEL_X_OFFSET, py + h - _HINT_Y_OFFSET_FROM_BOTTOM),
        )
