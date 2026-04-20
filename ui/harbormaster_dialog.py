"""HarbormasterDialog — Fase 3 C3-4.

Havnekontor-dialog: fast-travel + cache-subdialog (stubbed C3-5) +
"Vis kart"-snarvei. Åpnes ved E på harbormaster-bbox (ports.json).

Meny-innhold per FASE_3.md §1.6:

- **Fast-travel**: én oppføring per annen havn (ikke current_port).
  Cost-label viser `{route.days}d, {route.gold} gull` fra
  `balance.travel.routes`. Aktiv uansett affordability — insufficient
  gold fanges av `voyage.start_voyage` og vises som toast-feilhint.
- **Cache** (stubbed C3-5): "Åpne cache" i grått med "(kommer i C3-5)".
  C3-5 wirer inn CacheSubDialog for deposit/withdraw.
- **Vis kart**: launch WorldMapScene (eksisterende 2B-mekanisme som
  alternativ visualisering).

Aktivering:
- `travel_<dest_id>`: kaller `voyage.start_voyage`. Ved suksess:
  `_want_close=True`, `requested_next_scene="voyage"`. Ved None (ruten
  finnes ikke eller insufficient gold): toast-feilhint, dialog forblir
  åpen.
- `show_map`: `_want_close=True`, `requested_next_scene="world_map"`.
- `cache`: stubbet, inaktiv, Enter blokkeres.

Scene-transisjon:
Dialog muterer bare `GameState` via `start_voyage` + setter
`_requested_next_scene`. PortVillageScene.update poller dette når
dialogen lukkes og setter `self.next_scene`. Ingen direkte scene-
manipulasjon fra dialogen.

Flerdagers-reise dawn-tick-loop (presisering C3-4 #1):
Allerede implementert i `VoyageScene.update` via eksisterende
`economy.tick_all_ports_dawn` + `PitchLake.on_new_day` per dag som
passerer. C3-4 gjør ingen endring her — events (C3-11) og market-
effects (C3-10) utvides i respektive senere commits, IKKE som
placeholder-stubs her nå.
"""

from __future__ import annotations

from dataclasses import dataclass

import pygame

import constants
from config import port_config
from state import GameState
from systems import balance as _balance
from systems import voyage as _voyage
from ui.dialog_overlay import DEFAULT_PANEL_H, DEFAULT_PANEL_W, DialogOverlay
from ui.toast import Toast, ToastQueue


#: Action-id-prefiks for reise-oppføringer (destinasjons-id appenderes).
ACTION_TRAVEL_PREFIX = "travel_"
ACTION_CACHE = "cache"  # C3-5 wiring
ACTION_SHOW_MAP = "show_map"


@dataclass
class HarbormasterEntry:
    """Én meny-oppføring i HarbormasterDialog.

    `dest_port_id` er kun satt for reise-oppføringer (trengs av
    `start_voyage`-kallet). `None` for cache/show_map.
    """

    action_id: str
    label: str
    cost_label: str
    active: bool
    dest_port_id: str | None = None


# --- Rendering-konstanter (matcher TavernDialog-mønster) ---

_TITLE_Y_OFFSET = 14
_GOLD_Y_OFFSET = 28
_ENTRIES_START_Y_OFFSET = 56
_ENTRY_ROW_HEIGHT = 22
_LABEL_X_OFFSET = 24
_COST_X_FROM_RIGHT = 24
_HINT_Y_OFFSET_FROM_BOTTOM = 22

_ACTIVE_COLOR = constants.COLOR_SHIRT
_ACTIVE_COST_COLOR = constants.COLOR_STONE_LIT
_INACTIVE_COLOR = constants.COLOR_FOG
_TITLE_COLOR = constants.COLOR_MOON_CORE
_GOLD_COLOR = constants.COLOR_MOON_CORE
_CURSOR_COLOR = constants.COLOR_LANTERN
_HINT_COLOR = constants.COLOR_STONE_LIT


class HarbormasterDialog(DialogOverlay):
    """Havnekontor-dialog. Åpnes av PortVillageScene ved E på bbox.

    Scene-owner leser `requested_next_scene` etter lukking for å
    utføre transisjon (voyage eller world_map).
    """

    def __init__(
        self,
        font: pygame.font.Font,
        game_state: GameState,
        port_id: str,
        toasts: ToastQueue | None = None,
    ) -> None:
        super().__init__(font, panel_w=DEFAULT_PANEL_W, panel_h=DEFAULT_PANEL_H)
        self._state = game_state
        self._port_id = port_id
        self._toasts = toasts
        #: Scene-owner leser denne når `want_close` settes. None = lukk
        #: uten transisjon (ESC).
        self.requested_next_scene: str | None = None
        #: C3-5: Signaler at scene-owner skal åpne CacheSubDialog etter
        #: at denne dialogen lukker. Scene-owner leser sammen med
        #: `want_close` og instansierer CacheSubDialog i stedet for å
        #: gå tilbake til havn-input.
        self.open_cache: bool = False
        # Caches
        self._entries_cached: list[HarbormasterEntry] | None = None
        self._label_surfs: list[pygame.Surface] = []
        self._cost_surfs: list[pygame.Surface] = []
        self._title_surf: pygame.Surface | None = None
        self._hint_surf: pygame.Surface | None = None
        self._gold_value: int | None = None
        self._gold_surf: pygame.Surface | None = None
        # Start-cursor på første aktive entry
        self._selected = self._find_first_active()

    # --- Entry-bygging ---

    def _build_entries(self) -> list[HarbormasterEntry]:
        bal = _balance.get()
        entries: list[HarbormasterEntry] = []
        # Fast-travel per annen havn. Rekkefølge fra port_config-ordningen
        # (tortuga først, rest alfabetisk), skip current_port.
        for dest_id in port_config.get_all_port_ids():
            if dest_id == self._port_id:
                continue
            route = _voyage.get_route(bal, self._port_id, dest_id)
            if route is None:
                # Ingen rute definert for dette paret — skip defensivt.
                continue
            dest = port_config.get(dest_id)
            entries.append(HarbormasterEntry(
                action_id=f"{ACTION_TRAVEL_PREFIX}{dest_id}",
                label=f"Seil til {dest.name}",
                cost_label=f"{route.days}d, {route.gold} gull",
                active=True,
                dest_port_id=dest_id,
            ))
        # C3-5: Cache-oppføring aktivert. Tortuga viser "Gullkiste",
        # andre havner viser "Cache" — samme UI mekanisk, kun tittel
        # skiller seg. Aktivering åpner CacheSubDialog via scene-owner.
        cache_label = (
            "\u00c5pne gullkiste"
            if self._port_id == "tortuga"
            else "\u00c5pne cache"
        )
        entries.append(HarbormasterEntry(
            action_id=ACTION_CACHE,
            label=cache_label,
            cost_label="\u2014",
            active=True,
        ))
        # Vis kart (aktiv, eksisterende WorldMapScene)
        entries.append(HarbormasterEntry(
            action_id=ACTION_SHOW_MAP,
            label="Vis kart",
            cost_label="—",
            active=True,
        ))
        return entries

    # --- Cache-hjelpere (samme mønster som TavernDialog) ---

    def _entries(self) -> list[HarbormasterEntry]:
        # Cache invalideres ved balance-reload (rute-kost kan endres) OG
        # ved gold-change fordi noe cost_label-rendering kan avhenge av
        # spiller-state. Vi re-bygger konservativt ved hver _balance_changed.
        if self._entries_cached is None or self._balance_changed():
            self._entries_cached = self._build_entries()
            self._label_surfs = []
            self._cost_surfs = []
            for e in self._entries_cached:
                color = _ACTIVE_COLOR if e.active else _INACTIVE_COLOR
                cost_color = _ACTIVE_COST_COLOR if e.active else _INACTIVE_COLOR
                self._label_surfs.append(
                    self._font.render(e.label, False, color).convert_alpha()
                )
                self._cost_surfs.append(
                    self._font.render(
                        e.cost_label, False, cost_color
                    ).convert_alpha()
                )
        return self._entries_cached

    def _ensure_title(self) -> None:
        if self._title_surf is None:
            port_name = port_config.get(self._port_id).name
            self._title_surf = self._font.render(
                f"{port_name} Havnekontor",
                False, _TITLE_COLOR,
            ).convert_alpha()

    def _ensure_hint(self) -> None:
        if self._hint_surf is None:
            self._hint_surf = self._font.render(
                "\u2191\u2193 velg   Enter velg   Esc lukk",
                False, _HINT_COLOR,
            ).convert_alpha()

    def _ensure_gold(self) -> None:
        g = self._state.player_state.gold
        if g == self._gold_value and self._gold_surf is not None:
            return
        self._gold_value = g
        self._gold_surf = self._font.render(
            f"Gull: {g} d.", False, _GOLD_COLOR
        ).convert_alpha()

    # --- Navigasjon (skip inaktive — samme mønster som TavernDialog) ---

    def _find_first_active(self) -> int:
        entries = self._build_entries()
        for i, e in enumerate(entries):
            if e.active:
                return i
        return 0

    def _find_next_active(self, start: int, direction: int) -> int:
        entries = self._entries()
        n = len(entries)
        if n == 0:
            return start
        idx = start
        for _ in range(n):
            idx = (idx + direction) % n
            if entries[idx].active:
                return idx
        return start

    def _has_any_active(self) -> bool:
        return any(e.active for e in self._entries())

    # --- Event handling ---

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type != pygame.KEYDOWN:
            return
        if event.key == pygame.K_ESCAPE:
            self._want_close = True
            return
        if event.key in (pygame.K_UP, pygame.K_w):
            if self._has_any_active():
                self._selected = self._find_next_active(
                    self._selected, direction=-1
                )
            return
        if event.key in (pygame.K_DOWN, pygame.K_s):
            if self._has_any_active():
                self._selected = self._find_next_active(
                    self._selected, direction=+1
                )
            return
        if event.key == pygame.K_RETURN:
            self._activate_selected()

    def _activate_selected(self) -> None:
        entries = self._entries()
        if not (0 <= self._selected < len(entries)):
            return
        entry = entries[self._selected]
        if not entry.active:
            return
        if entry.action_id.startswith(ACTION_TRAVEL_PREFIX):
            self._do_travel(entry)
        elif entry.action_id == ACTION_SHOW_MAP:
            self._do_show_map()
        elif entry.action_id == ACTION_CACHE:
            self._do_open_cache()

    # --- Aktive handlinger ---

    def _do_travel(self, entry: HarbormasterEntry) -> None:
        """Start reise via `voyage.start_voyage`.

        Suksess → `_want_close=True`, `requested_next_scene="voyage"`.
        Scene-owner (PortVillageScene) transisjonerer til VoyageScene.

        start_voyage returnerer None ved:
        - Ruten finnes ikke (skulle ikke skje — entries filtreres)
        - Voyage allerede aktiv (defensivt — E blokkerer scene-owner
          fra å åpne dialog mens voyage er aktiv)
        - Insufficient gold → toast-feilhint, dialog forblir åpen
        """
        if entry.dest_port_id is None:
            return
        bal = _balance.get()
        voyage = _voyage.start_voyage(
            self._state, bal,
            from_port=self._port_id,
            to_port=entry.dest_port_id,
        )
        if voyage is None:
            # Diagnoser årsaken — mest sannsynlig insufficient gold.
            cost = _voyage.voyage_cost(bal, self._port_id, entry.dest_port_id)
            if cost is not None and self._state.player_state.gold < cost:
                self._push_toast(
                    f"For lite gull (trenger {cost} d.)",
                    constants.COLOR_EMBER,
                )
            return
        # Voyage startet. Signalér scene-transisjon.
        self._want_close = True
        self.requested_next_scene = "voyage"

    def _do_show_map(self) -> None:
        """Be scene om å bytte til WorldMapScene."""
        self._want_close = True
        self.requested_next_scene = "world_map"

    def _do_open_cache(self) -> None:
        """Signaliser scene-owner om å åpne CacheSubDialog (C3-5).

        Ingen direkte scene-transisjon — CacheSubDialog er peer-dialog
        i samme scene. Scene-owner lukker HarbormasterDialog og åpner
        CacheSubDialog etter autosave.
        """
        self._want_close = True
        self.open_cache = True

    def _push_toast(self, text: str, color) -> None:
        if self._toasts is None:
            return
        self._toasts.push(
            Toast(font=self._font, text=text, color=color, duration=2.0)
        )

    # --- Rendering ---

    def draw(self, surface: pygame.Surface) -> None:
        self._ensure_title()
        self._ensure_hint()
        self._ensure_gold()
        entries = self._entries()

        self._draw_panel(surface)
        px, py = self._panel_x, self._panel_y
        w, h = self._panel_w, self._panel_h

        assert self._title_surf is not None
        surface.blit(self._title_surf, (px + _LABEL_X_OFFSET, py + _TITLE_Y_OFFSET))
        assert self._gold_surf is not None
        surface.blit(self._gold_surf, (px + _LABEL_X_OFFSET, py + _GOLD_Y_OFFSET))

        draw_cursor = self._has_any_active() and (
            0 <= self._selected < len(entries)
            and entries[self._selected].active
        )

        for i, entry in enumerate(entries):
            row_y = py + _ENTRIES_START_Y_OFFSET + i * _ENTRY_ROW_HEIGHT
            if draw_cursor and i == self._selected:
                pygame.draw.rect(
                    surface,
                    _CURSOR_COLOR,
                    (px + 12, row_y - 3, w - 24, _ENTRY_ROW_HEIGHT - 2),
                    1,
                )
            surface.blit(self._label_surfs[i], (px + _LABEL_X_OFFSET, row_y))
            cost_surf = self._cost_surfs[i]
            cost_x = px + w - _COST_X_FROM_RIGHT - cost_surf.get_width()
            surface.blit(cost_surf, (cost_x, row_y))

        assert self._hint_surf is not None
        surface.blit(
            self._hint_surf,
            (px + _LABEL_X_OFFSET, py + h - _HINT_Y_OFFSET_FROM_BOTTOM),
        )
