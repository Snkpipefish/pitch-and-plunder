"""DialogOverlay — base class for Fase 3 tekst-vindu-dialoger (C3-2).

Ekstrahert fra `ExchangeOverlay`-mønsteret (Fase 1) for gjenbruk i
Fase 3-dialogene TavernDayDialog, TavernNightDialog, HarbormasterDialog,
CacheSubDialog og ScoreOverlay. C3-3+ fyller inn faktiske oppføringer
per dialog; C3-2 etablerer bare felles mønsterbase.

Hva generaliseres her:
- SRCALPHA-panel-bygging (stein-dark fyll, stone-lit 2 px ramme,
  stone-mid 1 px indre ramme) — identisk med Exchange-panel
- `_want_close`-flagg, satt via ESC-tasten
- Seleksjons-cursor (up/w eller down/s) med wrap-around basert på
  `_build_entries()`-returverdi
- Balance hot-reload-cache-invalidation via `balance.tick_id()` (pull-
  ved-draw — subklasser kaller `_balance_changed()` i sine
  `_ensure_*`-helpere, konsistent med MarketState.tick_id-mønsteret i
  ExchangeOverlay)

Hva er IKKE generalisert (subklasse-spesifikt):
- Entry-rendering og layout (Exchange er kolonner; Tavern-menyer er
  lister; ScoreOverlay er statisk panel uten seleksjon)
- Activation-keys (Exchange: A/D/Left/Right for kjøp/salg; menyer:
  Enter for select)
- `draw`-signatur (Exchange tar `market_state`; andre tar kun
  `surface` eller (`surface`, `game_state`))
- Data-avhengigheter (Exchange leser fra Market + MarketState; Tavern
  leser fra GameState + balance; HarbormasterDialog leser port_config)

Brukes slik av subklasser:

    class MyDialog(DialogOverlay):
        def __init__(self, font, game_state):
            super().__init__(font)
            self._state = game_state

        def _build_entries(self):
            return ["Alternativ 1", "Alternativ 2"]

        def handle_event(self, event):
            entries = self._build_entries()
            if self._handle_navigation(event, len(entries)):
                return
            # Egen activation-key-håndtering her
            if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
                self._activate(entries[self._selected])

        def draw(self, surface):
            self._draw_panel(surface)
            # Egen rendering av entries + tittel her

Hot-reload-cache-invalidation:

    def _ensure_fee_surf(self):
        if self._balance_changed() or self._fee_surf is None:
            self._fee_surf = self._font.render(
                f"Gebyr: {_balance.get().economy.transaction_fee}",
                False, constants.COLOR_FOG,
            ).convert_alpha()

Se `ExchangeOverlay` (scenes/exchange.py) for referanse-implementasjon
med kolonne-layout og A/D-kjøp/salg-logikk.
"""

from __future__ import annotations

import pygame

import constants
from systems import balance as _balance


#: Standard panel-dimensjoner fra Exchange (Fase 1). Subklasser kan
#: overstyre via panel_w/panel_h i __init__.
DEFAULT_PANEL_W = 480
DEFAULT_PANEL_H = 240


class DialogOverlay:
    """Base class for tekst-vindu-dialoger over PortVillageScene.

    Ikke strengt abstrakt — kan instansieres direkte (f.eks. tests),
    men typisk ubrukelig uten en konkret `draw()`-override.
    """

    def __init__(
        self,
        font: pygame.font.Font,
        panel_w: int = DEFAULT_PANEL_W,
        panel_h: int = DEFAULT_PANEL_H,
    ) -> None:
        self._font = font
        self._panel_w = panel_w
        self._panel_h = panel_h
        self._panel_x = (constants.RENDER_WIDTH - panel_w) // 2
        self._panel_y = (constants.RENDER_HEIGHT - panel_h) // 2
        self._panel_surface = self.build_panel_surface(panel_w, panel_h)
        self._want_close = False
        self._selected = 0
        self._balance_tick_id_seen = _balance.tick_id()

    # --- Lifecycle ---

    @property
    def want_close(self) -> bool:
        """Sett til True av ESC-tasten. Scene-eieren poller denne og
        lukker dialogen når True."""
        return self._want_close

    @property
    def selected(self) -> int:
        """Gjeldende cursor-posisjon (indeks i _build_entries()-listen)."""
        return self._selected

    # --- Panel ---

    @staticmethod
    def build_panel_surface(w: int, h: int) -> pygame.Surface:
        """Bygg SRCALPHA-panel med stein-dark fyll og stone-lit/mid-rammer.

        Statisk og gjenbrukbar: subklasser kan bruke direkte hvis de
        vil ha egen panel-instans med avvikende størrelse. Standard
        bruk går via __init__ → self._panel_surface.
        """
        panel = pygame.Surface((w, h), pygame.SRCALPHA)
        # COLOR_STONE_DARK = (31, 37, 56) med 95 % opacity = 242/255
        panel.fill((*constants.COLOR_STONE_DARK, 242))
        pygame.draw.rect(
            panel, constants.COLOR_STONE_LIT, (0, 0, w, h), 2
        )
        pygame.draw.rect(
            panel, constants.COLOR_STONE_MID, (4, 4, w - 8, h - 8), 1
        )
        return panel

    def _draw_panel(self, surface: pygame.Surface) -> None:
        """Blit ferdig panel ved base-plassering. Subklasser med egen
        geometri kan kalle `build_panel_surface` direkte i stedet."""
        surface.blit(self._panel_surface, (self._panel_x, self._panel_y))

    # --- Navigation ---

    def _handle_navigation(
        self, event: pygame.event.Event, n_entries: int
    ) -> bool:
        """Håndter ESC (sett want_close) og up/w/down/s (flytt selected).

        Returnér True hvis event ble konsumert. Subklasser kaller denne
        først i sin `handle_event`, og sjekker return-verdien før egen
        activation-key-håndtering (Enter, A/D, etc.).

        Wrap-around: `_selected` holder seg i [0, n_entries) når
        n_entries > 0. Hvis n_entries ≤ 0 blir navigerings-keys no-op
        (men ESC konsumeres fortsatt).
        """
        if event.type != pygame.KEYDOWN:
            return False
        if event.key == pygame.K_ESCAPE:
            self._want_close = True
            return True
        if n_entries <= 0:
            return False
        if event.key in (pygame.K_UP, pygame.K_w):
            self._selected = (self._selected - 1) % n_entries
            return True
        if event.key in (pygame.K_DOWN, pygame.K_s):
            self._selected = (self._selected + 1) % n_entries
            return True
        return False

    # --- Balance hot-reload cache-invalidation ---

    def _balance_changed(self) -> bool:
        """Returnér True hvis balance har blitt hot-reloadet siden sist
        kall, ELLERS False.

        Konsumer-mønster (i `_ensure_*`-helpere):

            def _ensure_fee_surf(self):
                if self._balance_changed() or self._fee_surf is None:
                    self._fee_surf = self._font.render(...)

        Pull-ved-draw-design: dialoger leser balance-verdier ved render
        og invaliderer cached tekst-surfaces KUN når tick_id har endret
        seg. Ingen subscribe-infrastruktur. Konsistent med
        MarketState.tick_id-mønsteret.
        """
        current = _balance.tick_id()
        if current != self._balance_tick_id_seen:
            self._balance_tick_id_seen = current
            return True
        return False

    # --- Subklasse-hook ---

    def _build_entries(self) -> list:
        """Subklasser overstyrer: returnér liste av navigerbare oppføringer.

        Tom liste betyr ingen seleksjon tilgjengelig (relevant for
        stubs og for ScoreOverlay som ikke har seleksjon).
        """
        return []

    # Subklasser implementerer egne `draw(surface, ...)` og typisk egen
    # `handle_event(event, ...)`. Base tilbyr ingen default-draw for å
    # unngå at subklasser får delvis-rendret skjerm ved glemt override.
