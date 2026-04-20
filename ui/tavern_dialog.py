"""TavernDayDialog og TavernNightDialog — Fase 3 C3-3.

Arver fra DialogOverlay. Dag- og natt-meny per FASE_3.md §1.6:

**TavernDayDialog** (vises når night_factor < 0.5):
- Leie rom  —  AKTIV i C3-3
- Lytte på rykter (gratis-tier)  —  stubbed (C3-9)
- Invester i bek-anlegg (kun Tortuga, kun før kjøp)  —  stubbed (C3-6)

**TavernNightDialog** (vises når night_factor ≥ 0.5):
- Leie rom  —  AKTIV i C3-3
- Kjøpe rykter  —  stubbed (C3-9)
- Bestille sabotasje  —  stubbed (C3-10)
- Spre falskt rykte  —  stubbed (C3-10)
- Snakke med smugler  —  stubbed (senere fase)

Inaktive oppføringer tegnes med dempet farge og kan IKKE navigeres til
(up/down skipper dem). Enter aktiverer kun aktiv seleksjon.

Rom-kjøp (C3-3):
- Trekker `balance.rest.room_cost_gold` (default 10) fra gull.
- Setter `player_state.rest = 1.0`.
- INGEN handlings-tid-konsum — ActionBudget er ikke wiret til scene
  ennå (presisering C3-3 #2). Cost_hours i labelen er informativt.
- Toast ved suksess eller ved insufficient-gold (samme mønster som
  ExchangeOverlay-feilhint).

Dag-vs-natt-bytte (C3-3): drevet av `night_factor` i PortVillageScene.
Scene sjekker terskel 0.5 (samme som sprite-variant-snap) ved åpning
og instansierer TavernDayDialog eller TavernNightDialog. Dialog-
instansen byttes ikke under interaksjon — spilleren må lukke og åpne
på nytt for å få "oppdatert" meny hvis natt-/dag-overgang skjer
underveis.
"""

from __future__ import annotations

from dataclasses import dataclass

import pygame

import constants
from config import port_config
from state import GameState
from systems import balance as _balance
from systems import market_effects as _market_effects
from systems import rest as _rest
from systems import rumors as _rumors
from systems import suspicion as _suspicion
from ui.dialog_overlay import DEFAULT_PANEL_H, DEFAULT_PANEL_W, DialogOverlay
from ui.toast import Toast, ToastQueue


#: Norske vare-navn for toast-meldinger.
_COMMODITY_NORWEGIAN: dict[str, str] = {
    "sugar": "sukker",
    "rum": "rom",
    "tobacco": "tobakk",
    "pitch": "bek",
}


#: Action-ID-er brukt i entry-aktivering. Ikke-aktive entries har sin id
#: bare for debug-formål — de plukkes ikke opp av handle_event.
ACTION_BUY_ROOM = "buy_room"
ACTION_RUMOR_LISTEN_FREE = "rumor_listen_free"    # stubbed senere
ACTION_BUY_RUMOR_REGIME = "buy_rumor_regime"      # C3-9 (regime_preview)
ACTION_BUY_RUMOR_SPIKE = "buy_rumor_spike"        # C3-9 (price_spike_warning)
ACTION_PITCH_LAKE_PURCHASE = "pitch_lake_purchase"  # C3-6
ACTION_ORDER_SABOTAGE = "order_sabotage"          # C3-10
ACTION_SPREAD_FALSE_RUMOR = "spread_false_rumor"  # C3-10
ACTION_SMUGGLER_CONTACT = "smuggler_contact"      # senere fase

# Legacy-alias (C3-3 stub-navn). Brukes ikke lenger i kode, men imports
# fra test-filer eller ekstern kode skal ikke bryte.
ACTION_RUMOR_LISTEN_PAID = ACTION_BUY_RUMOR_REGIME


@dataclass
class TavernEntry:
    """Én meny-oppføring i tavern-dialog.

    `active` styrer om oppføringen kan velges med cursor og aktiveres
    med Enter. Inaktive oppføringer tegnes dempet og skipes av
    navigasjon. `cost_label` er informativ tekst ("10 gull, 1.0 h")
    som rendres ved siden av `label`.
    """

    action_id: str
    label: str
    cost_label: str
    active: bool


# --- Rendering-konstanter ---

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


class TavernDialog(DialogOverlay):
    """Felles base for tavern dag- og natt-meny.

    Subklasser overstyrer `_TIME_LABEL` og `_build_entries`. Base
    håndterer navigasjon (som skipper inaktive oppføringer), rendering
    og rom-kjøp-aktivering (C3-3 sin eneste aktive handling).
    """

    _TIME_LABEL: str = "?"  # "dag" eller "natt"

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
        # Cache: fylles på første draw. Invalidation via
        # `_balance_changed()` (hot-reload av rest.room_cost_gold mm)
        # og via gold-value-endring.
        self._entries_cached: list[TavernEntry] | None = None
        self._label_surfs: list[pygame.Surface] = []
        self._cost_surfs: list[pygame.Surface] = []
        self._title_surf: pygame.Surface | None = None
        self._hint_surf: pygame.Surface | None = None
        self._gold_value: int | None = None
        self._gold_surf: pygame.Surface | None = None
        # Start-cursor på første aktive entry (kan være 0 hvis alle er aktive)
        self._selected = self._find_first_active()

    # --- Subklasse-hook ---

    def _build_entries(self) -> list[TavernEntry]:
        """Overstyres av TavernDayDialog / TavernNightDialog."""
        return []

    # --- Cache-hjelpere ---

    def _entries(self) -> list[TavernEntry]:
        """Returner cached entries, rebuild hvis balance har endret seg."""
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
            port_name = self._port_id.replace("_", " ").title()
            self._title_surf = self._font.render(
                f"{port_name} Tavern \u2014 {self._TIME_LABEL}",
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

    # --- Navigation: skip inaktive entries ---

    def _find_first_active(self) -> int:
        entries = self._build_entries()
        for i, e in enumerate(entries):
            if e.active:
                return i
        return 0  # ingen aktive — cursor kan stå på 0 (draw viser ingen cursor)

    def _find_next_active(self, start: int, direction: int) -> int:
        """Finn neste aktive-index fra `start` i `direction` (+1 / -1).

        Hvis ingen aktive finnes returneres `start` uendret. Wrap-around.
        """
        entries = self._entries()
        n = len(entries)
        if n == 0:
            return start
        idx = start
        for _ in range(n):
            idx = (idx + direction) % n
            if entries[idx].active:
                return idx
        return start  # ingen aktive

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
        if entry.action_id == ACTION_BUY_ROOM:
            self._do_buy_room()
        elif entry.action_id == ACTION_PITCH_LAKE_PURCHASE:
            self._do_purchase_pitch_lake()
        elif entry.action_id == ACTION_BUY_RUMOR_REGIME:
            self._do_buy_rumor_regime()
        elif entry.action_id == ACTION_BUY_RUMOR_SPIKE:
            self._do_buy_rumor_spike()
        elif entry.action_id == ACTION_ORDER_SABOTAGE:
            self._do_order_sabotage()
        elif entry.action_id == ACTION_SPREAD_FALSE_RUMOR:
            self._do_spread_false_rumor()

    # --- Aktive handlinger ---

    def _do_buy_room(self) -> None:
        """Rom-kjøp: trekk gull, gjenopprett rest til 1.0, toast-feedback.

        INGEN handlings-tid-konsum i C3-3 (presisering #2). Cost_hours
        i label er informativ tekst — ActionBudget-wiring venter.

        Rom-kjøp setter rest=1.0 direkte via `rest.restore()` (ikke
        decay-basert). Rommet gir full restitusjon uavhengig av pre-
        rest-nivå.
        """
        cost_gold = _balance.get().rest.room_cost_gold
        if self._state.player_state.gold < cost_gold:
            self._push_toast(
                f"For lite gull (trenger {cost_gold} d.)",
                constants.COLOR_EMBER,
            )
            return
        self._state.player_state.gold -= cost_gold
        _rest.restore(self._state)
        # Gold-surface er cachet per gold-value i _ensure_gold; vil re-
        # rendere neste draw automatisk.
        self._push_toast(
            "Rommet er leid (hvile: full)",
            constants.COLOR_LANTERN_BRIGHT,
        )

    def _do_purchase_pitch_lake(self) -> None:
        """Kjøp bek-anlegget (Fase 3 C3-6). Kun i Tortuga, kun før kjøp.

        Flyt:
        1. Sjekk at spilleren har råd (gold >= purchase_cost_gold).
           Insufficient → EMBER feilhint-toast, ingen mutasjon.
        2. Commit: trekk gull, sett `purchased=True`, sett
           `production_per_day` og `upkeep_per_day` fra balance.
        3. Invalidér entry-cache → oppføringen forsvinner fra neste
           draw (siden `_build_entries()` skjuler den når purchased).
        4. LANTERN_BRIGHT suksess-toast (samme som rom-kjøp).

        INGEN handlings-tid-konsum i C3-6 (samme som rom-kjøp) —
        ActionBudget-wiring venter.

        Produksjon starter FRA NESTE dawn-tick: `PitchLake.on_new_day`
        leser purchased-flagget og produksjons-verdier umiddelbart.
        """
        bal = _balance.get()
        cost_gold = bal.pitch_lake.purchase_cost_gold
        player = self._state.player_state
        if player.gold < cost_gold:
            self._push_toast(
                f"For lite gull (trenger {cost_gold} d.)",
                constants.COLOR_EMBER,
            )
            return
        # Commit kjøp
        player.gold -= cost_gold
        pls = self._state.pitch_lake_state
        pls.purchased = True
        pls.production_per_day = bal.pitch_lake.production_per_day
        pls.upkeep_per_day = bal.pitch_lake.upkeep_per_day
        # Fase 3 C3-8: rom-decay for tids-kostbar handling (1.0 h).
        # Direkte rest-endring, ikke via ActionBudget (som ikke er wiret).
        purchase_hours = bal.actions.cost_hours_per_action.get(
            "pitch_lake_purchase", 1.0
        )
        _rest.consume_for_action(self._state, purchase_hours)
        # Invalidér entry-cache slik at "Invester ..."-oppføringen
        # forsvinner fra menyen neste draw-kall (siden
        # `_build_entries()` skjuler den når purchased=True).
        self._entries_cached = None
        # Seleksjon kan nå peke på en entry som ikke lenger finnes.
        # Re-snap til første aktive.
        self._selected = 0
        self._push_toast(
            "Bek-anlegget er ditt!",
            constants.COLOR_LANTERN_BRIGHT,
        )

    def _do_buy_rumor_regime(self) -> None:
        """Kjøp regime_preview-rykte. Alltid suksess (C3-9 #1).

        Sampler tilfeldig annen havn + vare. Trekker gull, konsumerer
        rest, legger til rykte i active_rumors.
        """
        bal = _balance.get()
        cost_gold = bal.rumors.cost_gold
        player = self._state.player_state
        if player.gold < cost_gold:
            self._push_toast(
                f"For lite gull (trenger {cost_gold} d.)",
                constants.COLOR_EMBER,
            )
            return
        player.gold -= cost_gold
        _rumors.buy_regime_preview(self._state)
        _rest.consume_for_action(self._state, bal.rumors.cost_hours)
        self._push_toast(
            "Nytt rykte i lomma",
            constants.COLOR_LANTERN_BRIGHT,
        )

    def _do_buy_rumor_spike(self) -> None:
        """Kjøp price_spike_warning-rykte. Refund hvis ingen kandidater.

        C3-9 #1: hvis ingen spike-kandidater (alle regimer stabile),
        gis gull-refund og toast "Du hører ingen ferske rykter".
        `systems.rumors.buy_price_spike_warning` returnerer None ved
        dette tilfellet.
        """
        bal = _balance.get()
        cost_gold = bal.rumors.cost_gold
        player = self._state.player_state
        if player.gold < cost_gold:
            self._push_toast(
                f"For lite gull (trenger {cost_gold} d.)",
                constants.COLOR_EMBER,
            )
            return
        # Trekk først, refund hvis ingen kandidater
        player.gold -= cost_gold
        rumor = _rumors.buy_price_spike_warning(self._state)
        if rumor is None:
            # Refund — gi gullet tilbake, toast-feedback
            player.gold += cost_gold
            self._push_toast(
                "Du hører ingen ferske rykter",
                constants.COLOR_FOG,
            )
            # INGEN rest-decay heller — handlingen ble avvist
            return
        _rest.consume_for_action(self._state, bal.rumors.cost_hours)
        self._push_toast(
            "Nytt rykte i lomma",
            constants.COLOR_LANTERN_BRIGHT,
        )

    def _do_order_sabotage(self) -> None:
        """Bestill sabotasje mot tilfeldig (port, vare). Fase 3 C3-10.

        Random sampling av target (ikke current_port). Toast viser hva
        som ble satt i gang — presisering #3 krever at spilleren vet
        hva gullet ble brukt på siden det ikke er sub-dialog.

        Atomisk commit: gull + market-effect + mistanke + rest. Hvis
        target-sampling feiler (skjer ikke i prod — alltid 3 andre
        havner), ingen mutasjon.
        """
        bal = _balance.get()
        cost_gold = bal.sabotage.base_cost_gold
        player = self._state.player_state
        if player.gold < cost_gold:
            self._push_toast(
                f"For lite gull (trenger {cost_gold} d.)",
                constants.COLOR_EMBER,
            )
            return
        target = _market_effects.sample_target(
            self._state, exclude_port=self._port_id
        )
        if target is None:
            # Defensivt — aldri i prod, men beskytter mot edge-case
            self._push_toast(
                "Ingen kjøpmenn å sabotere",
                constants.COLOR_EMBER,
            )
            return
        port_id, commodity_id = target
        # Commit
        player.gold -= cost_gold
        _market_effects.register_market_effect(
            self._state,
            port_id=port_id,
            commodity_id=commodity_id,
            direction="up",
            magnitude_pct=bal.sabotage.magnitude_pct,
            source_type="sabotage",
            impact_delay_days=bal.sabotage.impact_delay_days,
        )
        _suspicion.increase(
            self._state, bal.sabotage.suspicion_increase_sabotage
        )
        _rest.consume_for_action(
            self._state,
            bal.actions.cost_hours_per_action.get("order_sabotage", 2.0),
        )
        port_name = port_config.get(port_id).name
        commodity_name = _COMMODITY_NORWEGIAN.get(commodity_id, commodity_id)
        self._push_toast(
            f"Sabotasje mot {port_name} {commodity_name} "
            f"\u2014 impact om {bal.sabotage.impact_delay_days}d",
            constants.COLOR_LANTERN_BRIGHT,
        )

    def _do_spread_false_rumor(self) -> None:
        """Spre falskt rykte mot tilfeldig (port, vare). Fase 3 C3-10.

        Samme infrastruktur som sabotasje men direction=down,
        magnitude_pct=false_rumor_magnitude_pct (10%), lavere
        mistanke-hit og lavere gull-kost. Source_type="false_rumor"
        for spike-varsel-integrasjon.
        """
        bal = _balance.get()
        cost_gold = bal.sabotage.false_rumor_base_cost_gold
        player = self._state.player_state
        if player.gold < cost_gold:
            self._push_toast(
                f"For lite gull (trenger {cost_gold} d.)",
                constants.COLOR_EMBER,
            )
            return
        target = _market_effects.sample_target(
            self._state, exclude_port=self._port_id
        )
        if target is None:
            self._push_toast(
                "Ingen kjøpmenn å lure",
                constants.COLOR_EMBER,
            )
            return
        port_id, commodity_id = target
        player.gold -= cost_gold
        _market_effects.register_market_effect(
            self._state,
            port_id=port_id,
            commodity_id=commodity_id,
            direction="down",
            magnitude_pct=bal.sabotage.false_rumor_magnitude_pct,
            source_type="false_rumor",
            impact_delay_days=bal.sabotage.impact_delay_days,
        )
        _suspicion.increase(
            self._state, bal.sabotage.suspicion_increase_false_rumor
        )
        _rest.consume_for_action(
            self._state,
            bal.actions.cost_hours_per_action.get("spread_false_rumor", 2.0),
        )
        port_name = port_config.get(port_id).name
        commodity_name = _COMMODITY_NORWEGIAN.get(commodity_id, commodity_id)
        self._push_toast(
            f"Falskt rykte om {port_name} {commodity_name} "
            f"\u2014 impact om {bal.sabotage.impact_delay_days}d",
            constants.COLOR_LANTERN_BRIGHT,
        )

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
        entries = self._entries()  # caches internt

        self._draw_panel(surface)
        px, py = self._panel_x, self._panel_y
        w, h = self._panel_w, self._panel_h

        assert self._title_surf is not None
        surface.blit(self._title_surf, (px + _LABEL_X_OFFSET, py + _TITLE_Y_OFFSET))
        assert self._gold_surf is not None
        surface.blit(self._gold_surf, (px + _LABEL_X_OFFSET, py + _GOLD_Y_OFFSET))

        # Seleksjonsramme kun over aktive oppføringer og kun hvis det
        # finnes minst én aktiv (ellers er cursor irrelevant).
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
            surface.blit(
                self._label_surfs[i], (px + _LABEL_X_OFFSET, row_y)
            )
            cost_surf = self._cost_surfs[i]
            cost_x = px + w - _COST_X_FROM_RIGHT - cost_surf.get_width()
            surface.blit(cost_surf, (cost_x, row_y))

        assert self._hint_surf is not None
        surface.blit(
            self._hint_surf,
            (px + _LABEL_X_OFFSET, py + h - _HINT_Y_OFFSET_FROM_BOTTOM),
        )


# -----------------------------------------------------------------------------
# Dag-meny
# -----------------------------------------------------------------------------


class TavernDayDialog(TavernDialog):
    """Tavern dag-meny. Rom-kjøp aktiv; rykter + bek-anlegg stubbed."""

    _TIME_LABEL = "dag"

    def _build_entries(self) -> list[TavernEntry]:
        bal = _balance.get()
        entries: list[TavernEntry] = [
            TavernEntry(
                action_id=ACTION_BUY_ROOM,
                label="Leie rom",
                cost_label=f"{bal.rest.room_cost_gold} gull, {bal.rest.room_cost_hours:.1f} h",
                active=True,
            ),
            TavernEntry(
                action_id=ACTION_RUMOR_LISTEN_FREE,
                label="Lytte på rykter (gratis)",
                cost_label="(kommer i C3-9)",
                active=False,
            ),
        ]
        # Bek-anlegg-kjøp (Fase 3 C3-6): kun i Tortuga, kun før kjøp.
        # Aktiv ved insufficient gold (guard ved aktivering, som rom-kjøp)
        # slik at spilleren ser prisen eksplisitt. Etter purchased=True
        # skjules oppføringen (ikke inaktiv, helt fjernet).
        if (
            self._port_id == "tortuga"
            and not self._state.pitch_lake_state.purchased
        ):
            purchase_hours = bal.actions.cost_hours_per_action.get(
                "pitch_lake_purchase", 0.0
            )
            entries.append(
                TavernEntry(
                    action_id=ACTION_PITCH_LAKE_PURCHASE,
                    label="Invester i bek-produksjon",
                    cost_label=(
                        f"{bal.pitch_lake.purchase_cost_gold} gull, "
                        f"{purchase_hours:.1f} h"
                    ),
                    active=True,
                )
            )
        return entries


# -----------------------------------------------------------------------------
# Natt-meny
# -----------------------------------------------------------------------------


class TavernNightDialog(TavernDialog):
    """Tavern natt-meny. Rom-kjøp aktiv; rykter/sabotasje/smugler stubbed."""

    _TIME_LABEL = "natt"

    def _build_entries(self) -> list[TavernEntry]:
        bal = _balance.get()
        rumor_cost_label = (
            f"{bal.rumors.cost_gold} gull, {bal.rumors.cost_hours:.1f} h"
        )
        return [
            TavernEntry(
                action_id=ACTION_BUY_ROOM,
                label="Leie rom",
                cost_label=f"{bal.rest.room_cost_gold} gull, {bal.rest.room_cost_hours:.1f} h",
                active=True,
            ),
            # C3-9: regime-rykte (alltid suksess, sampler annen havn)
            TavernEntry(
                action_id=ACTION_BUY_RUMOR_REGIME,
                label="Kjøpe regime-rykte",
                cost_label=rumor_cost_label,
                active=True,
            ),
            # C3-9: spike-rykte (kan gi refund hvis ingen kandidater)
            TavernEntry(
                action_id=ACTION_BUY_RUMOR_SPIKE,
                label="Kjøpe spike-rykte",
                cost_label=rumor_cost_label,
                active=True,
            ),
            # C3-10: sabotasje (pris-hever i target-havn)
            TavernEntry(
                action_id=ACTION_ORDER_SABOTAGE,
                label="Bestille sabotasje",
                cost_label=(
                    f"{bal.sabotage.base_cost_gold} gull, "
                    f"{bal.actions.cost_hours_per_action.get('order_sabotage', 2.0):.1f} h"
                ),
                active=True,
            ),
            # C3-10: falskt rykte (pris-senker i target-havn)
            TavernEntry(
                action_id=ACTION_SPREAD_FALSE_RUMOR,
                label="Spre falskt rykte",
                cost_label=(
                    f"{bal.sabotage.false_rumor_base_cost_gold} gull, "
                    f"{bal.actions.cost_hours_per_action.get('spread_false_rumor', 2.0):.1f} h"
                ),
                active=True,
            ),
            TavernEntry(
                action_id=ACTION_SMUGGLER_CONTACT,
                label="Snakke med smugler",
                cost_label="(senere fase)",
                active=False,
            ),
        ]
