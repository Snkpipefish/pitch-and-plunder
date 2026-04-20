"""Tester for Fase 3 C3-6: bek-anlegg-gating + tavern-kjøp.

Tre tematiske grupper:

1. **PitchLake.on_new_day-gate**: purchased=False → ingen produksjon,
   ingen upkeep-trekk; purchased=True → eksisterende produksjon-adferd.
2. **TavernDayDialog-kjøp**: Tortuga før kjøp viser entry aktivt med
   pris; Enter = mutasjon; insufficient gold = ingen mutasjon +
   feilhint. Etter kjøp er entry skjult.
3. **v5→v6 migrering end-to-end** (presisering #3): Fresh v6 og legacy
   v5-migrert — eksplisitt bekreftet at produksjons-flyten er riktig i
   begge tilfeller.
"""

from __future__ import annotations

import json
from pathlib import Path

import pygame
import pytest

import constants
from state import GameState, PitchLakeState
from state.ship_state import ShipState
from systems import save as save_module
from systems.game_clock import GameClock
from systems.pitch_lake import PITCH_ID, PitchLake
from ui.tavern_dialog import (
    ACTION_BUY_ROOM,
    ACTION_PITCH_LAKE_PURCHASE,
    TavernDayDialog,
)
from ui.toast import ToastQueue


@pytest.fixture(scope="module", autouse=True)
def _pygame_setup():
    import os
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    pygame.display.init()
    pygame.font.init()
    pygame.display.set_mode((640, 360), pygame.HIDDEN)
    yield
    pygame.display.quit()
    pygame.font.quit()


@pytest.fixture
def font():
    return pygame.font.SysFont(None, 12)


@pytest.fixture
def toasts(font) -> ToastQueue:
    return ToastQueue(baseline_y=340, center_x=320)


def _state_with(gold: int = 1000, day: int = 1) -> GameState:
    """GameState med nok gull til kjøp + tilpasset dag."""
    s = save_module.new_game_state()
    s.player_state.gold = gold
    s.world_state.clock = GameClock(day=day, seconds_into_day=0.0)
    return s


def _keydown(key: int, mod: int = 0) -> pygame.event.Event:
    return pygame.event.Event(pygame.KEYDOWN, {"key": key, "mod": mod})


# -----------------------------------------------------------------------------
# 1. PitchLake.on_new_day-gate på purchased
# -----------------------------------------------------------------------------


class TestPurchasedGate:
    def test_not_purchased_returns_zero_tuple(self):
        state = GameState()
        state.player_state.gold = 100
        state.world_state.ship = ShipState(cargo_capacity=40)
        pl = PitchLakeState(
            production_per_day=2, upkeep_per_day=8, purchased=False
        )
        produced, paid = PitchLake.on_new_day(pl, state)
        assert produced == 0
        assert paid == 0

    def test_not_purchased_no_gold_mutation(self):
        state = GameState()
        state.player_state.gold = 100
        state.world_state.ship = ShipState(cargo_capacity=40)
        pl = PitchLakeState(
            production_per_day=2, upkeep_per_day=8, purchased=False
        )
        PitchLake.on_new_day(pl, state)
        assert state.player_state.gold == 100  # uendret

    def test_not_purchased_no_production(self):
        state = GameState()
        state.player_state.gold = 100
        state.world_state.ship = ShipState(cargo_capacity=40)
        pl = PitchLakeState(
            production_per_day=2, upkeep_per_day=8, purchased=False
        )
        PitchLake.on_new_day(pl, state)
        assert (
            state.player_state.inventory.get(PITCH_ID)
            and state.player_state.inventory[PITCH_ID].quantity == 0
        )

    def test_not_purchased_no_last_production_day_change(self):
        state = GameState()
        state.player_state.gold = 100
        state.world_state.ship = ShipState(cargo_capacity=40)
        state.world_state.clock = GameClock(day=5, seconds_into_day=0.0)
        pl = PitchLakeState(
            production_per_day=2, upkeep_per_day=8, purchased=False,
            last_production_day=3,
        )
        PitchLake.on_new_day(pl, state)
        assert pl.last_production_day == 3  # uendret

    def test_not_purchased_accepts_nonzero_production_defensively(self):
        """Selv om production_per_day=2 og upkeep_per_day=8 er satt,
        gaten har presedens og ingenting skjer."""
        state = GameState()
        state.player_state.gold = 500
        state.world_state.ship = ShipState(cargo_capacity=40)
        pl = PitchLakeState(
            production_per_day=2, upkeep_per_day=8, purchased=False,
        )
        PitchLake.on_new_day(pl, state)
        assert state.player_state.gold == 500  # upkeep ikke trukket


class TestPurchasedTrueBehaviorUnchanged:
    """Confirm existing behavior med purchased=True fungerer uendret."""

    def test_normal_production_with_purchased(self):
        state = GameState()
        state.player_state.gold = 100
        state.world_state.ship = ShipState(cargo_capacity=40)
        pl = PitchLakeState(
            production_per_day=2, upkeep_per_day=8, purchased=True,
        )
        produced, paid = PitchLake.on_new_day(pl, state)
        assert produced == 2
        assert paid == 8
        assert state.player_state.gold == 92
        assert state.player_state.inventory[PITCH_ID].quantity == 2


# -----------------------------------------------------------------------------
# 2. TavernDayDialog bek-anlegg-kjøp
# -----------------------------------------------------------------------------


class TestBekAnleggEntryVisibility:
    def test_fresh_tortuga_has_bek_entry_active(self, font):
        state = _state_with()
        d = TavernDayDialog(font, state, port_id="tortuga")
        entries = d._build_entries()
        bek = next(
            (e for e in entries if e.action_id == ACTION_PITCH_LAKE_PURCHASE),
            None,
        )
        assert bek is not None
        assert bek.active is True

    def test_bek_entry_shows_price_and_hours(self, font):
        state = _state_with()
        d = TavernDayDialog(font, state, port_id="tortuga")
        entries = d._build_entries()
        bek = next(
            e for e in entries if e.action_id == ACTION_PITCH_LAKE_PURCHASE
        )
        # purchase_cost_gold = 500, cost_hours_per_action.pitch_lake_purchase = 1.0
        assert "500" in bek.cost_label
        assert "gull" in bek.cost_label
        assert "1.0" in bek.cost_label
        assert "h" in bek.cost_label
        # Ingen stub-tag
        assert "kommer" not in bek.cost_label

    def test_purchased_tortuga_hides_bek_entry(self, font):
        state = _state_with()
        state.pitch_lake_state.purchased = True
        d = TavernDayDialog(font, state, port_id="tortuga")
        entries = d._build_entries()
        action_ids = [e.action_id for e in entries]
        assert ACTION_PITCH_LAKE_PURCHASE not in action_ids

    def test_non_tortuga_never_shows_bek_entry(self, font):
        state = _state_with()
        for pid in ("port_royal", "havana", "nassau"):
            d = TavernDayDialog(font, state, port_id=pid)
            action_ids = [e.action_id for e in d._build_entries()]
            assert ACTION_PITCH_LAKE_PURCHASE not in action_ids


class TestBekAnleggPurchase:
    def test_enter_with_sufficient_gold_commits(self, font, toasts):
        state = _state_with(gold=1000)
        d = TavernDayDialog(font, state, port_id="tortuga", toasts=toasts)
        # Finn bek-entry-index
        entries = d._build_entries()
        bek_idx = next(
            i for i, e in enumerate(entries)
            if e.action_id == ACTION_PITCH_LAKE_PURCHASE
        )
        d._selected = bek_idx
        d.handle_event(_keydown(pygame.K_RETURN))
        # Mutations
        assert state.player_state.gold == 500  # 1000 - 500
        assert state.pitch_lake_state.purchased is True
        assert state.pitch_lake_state.production_per_day == 2
        assert state.pitch_lake_state.upkeep_per_day == 8

    def test_purchase_pushes_success_toast(self, font, toasts):
        state = _state_with(gold=1000)
        d = TavernDayDialog(font, state, port_id="tortuga", toasts=toasts)
        entries = d._build_entries()
        bek_idx = next(
            i for i, e in enumerate(entries)
            if e.action_id == ACTION_PITCH_LAKE_PURCHASE
        )
        d._selected = bek_idx
        assert toasts.count == 0
        d.handle_event(_keydown(pygame.K_RETURN))
        assert toasts.count == 1

    def test_purchase_invalidates_entry_cache_and_hides_entry(
        self, font, toasts
    ):
        state = _state_with(gold=1000)
        d = TavernDayDialog(font, state, port_id="tortuga", toasts=toasts)
        entries_before = d._entries()
        assert any(
            e.action_id == ACTION_PITCH_LAKE_PURCHASE for e in entries_before
        )
        bek_idx = next(
            i for i, e in enumerate(entries_before)
            if e.action_id == ACTION_PITCH_LAKE_PURCHASE
        )
        d._selected = bek_idx
        d.handle_event(_keydown(pygame.K_RETURN))
        # Neste draw skal rebuild entries uten bek-kjøp
        entries_after = d._entries()
        assert all(
            e.action_id != ACTION_PITCH_LAKE_PURCHASE for e in entries_after
        )

    def test_insufficient_gold_no_mutation(self, font, toasts):
        state = _state_with(gold=499)  # < 500
        d = TavernDayDialog(font, state, port_id="tortuga", toasts=toasts)
        entries = d._build_entries()
        bek_idx = next(
            i for i, e in enumerate(entries)
            if e.action_id == ACTION_PITCH_LAKE_PURCHASE
        )
        d._selected = bek_idx
        d.handle_event(_keydown(pygame.K_RETURN))
        # Ingen mutasjon
        assert state.player_state.gold == 499
        assert state.pitch_lake_state.purchased is False
        assert state.pitch_lake_state.production_per_day == 0
        assert state.pitch_lake_state.upkeep_per_day == 0

    def test_insufficient_gold_pushes_error_toast(self, font, toasts):
        state = _state_with(gold=400)
        d = TavernDayDialog(font, state, port_id="tortuga", toasts=toasts)
        entries = d._build_entries()
        bek_idx = next(
            i for i, e in enumerate(entries)
            if e.action_id == ACTION_PITCH_LAKE_PURCHASE
        )
        d._selected = bek_idx
        d.handle_event(_keydown(pygame.K_RETURN))
        assert toasts.count == 1

    def test_exact_gold_is_sufficient(self, font, toasts):
        state = _state_with(gold=500)
        d = TavernDayDialog(font, state, port_id="tortuga", toasts=toasts)
        entries = d._build_entries()
        bek_idx = next(
            i for i, e in enumerate(entries)
            if e.action_id == ACTION_PITCH_LAKE_PURCHASE
        )
        d._selected = bek_idx
        d.handle_event(_keydown(pygame.K_RETURN))
        assert state.player_state.gold == 0
        assert state.pitch_lake_state.purchased is True

    def test_dialog_stays_open_after_purchase(self, font, toasts):
        state = _state_with(gold=1000)
        d = TavernDayDialog(font, state, port_id="tortuga", toasts=toasts)
        entries = d._build_entries()
        bek_idx = next(
            i for i, e in enumerate(entries)
            if e.action_id == ACTION_PITCH_LAKE_PURCHASE
        )
        d._selected = bek_idx
        d.handle_event(_keydown(pygame.K_RETURN))
        assert d.want_close is False


# -----------------------------------------------------------------------------
# 3. v5→v6 migrering end-to-end (presisering #3)
# -----------------------------------------------------------------------------


class TestFreshV6Flow:
    """Ny v6-save: ingen bek-produksjon før kjøp. Etter kjøp starter
    produksjon fra neste dawn-tick."""

    def test_fresh_v6_no_production_on_first_dawn(self):
        state = save_module.new_game_state()
        assert state.version == 6
        assert state.pitch_lake_state.purchased is False

        # Kjør dawn-tick
        initial_gold = state.player_state.gold
        produced, paid = PitchLake.on_new_day(
            state.pitch_lake_state, state
        )
        assert produced == 0
        assert paid == 0
        assert state.player_state.gold == initial_gold  # ingen upkeep

    def test_fresh_v6_no_hud_halt_flag_signalling(self):
        """halted-deteksjon i port_village_scene bruker
        `last_production_day < clock.day - 1`. For fresh v6 er begge 0,
        så halted=False (ikke "driften står" feilhint)."""
        state = save_module.new_game_state()
        # Manuelt kjør samme check som scene
        halted = (
            state.pitch_lake_state.last_production_day
            < state.world_state.clock.day - 1
        )
        # Dag 1, last_production_day=0 → 0 < 0 = False
        assert halted is False

    def test_purchase_activates_production_from_next_dawn(
        self, font, toasts
    ):
        """Presisering #3 (første punkt): etter kjøp starter produksjon
        fra neste dawn-tick."""
        state = save_module.new_game_state()
        state.player_state.gold = 1000  # overrider fra balance
        # Kjøp via dialog
        d = TavernDayDialog(font, state, port_id="tortuga", toasts=toasts)
        entries = d._build_entries()
        bek_idx = next(
            i for i, e in enumerate(entries)
            if e.action_id == ACTION_PITCH_LAKE_PURCHASE
        )
        d._selected = bek_idx
        d.handle_event(_keydown(pygame.K_RETURN))
        # Umiddelbart etter kjøp: purchased=True, production/upkeep satt
        assert state.pitch_lake_state.purchased is True
        assert state.pitch_lake_state.production_per_day == 2
        assert state.pitch_lake_state.upkeep_per_day == 8

        # Neste dawn-tick produserer normalt
        state.world_state.clock.day = 2
        gold_before = state.player_state.gold
        produced, paid = PitchLake.on_new_day(
            state.pitch_lake_state, state
        )
        assert produced == 2
        assert paid == 8
        assert state.player_state.gold == gold_before - 8
        assert state.player_state.inventory[PITCH_ID].quantity == 2


class TestLegacyV5Migration:
    """Legacy v5-save migrert til v6: purchased=True, bek-produksjon
    fortsetter uendret uten endring av kjøp-entry-synlighet."""

    def _make_v5_payload(
        self, production_per_day: int = 2, upkeep_per_day: int = 8,
        gold: int = 250, total_produced: int = 24, last_production_day: int = 11,
    ) -> dict:
        return {
            "version": 5,
            "player_state": {
                "position_x": 320.0,
                "gold": gold,
                "inventory": {
                    "sugar": {"quantity": 0, "avg_cost": 0.0},
                    "rum": {"quantity": 0, "avg_cost": 0.0},
                    "tobacco": {"quantity": 0, "avg_cost": 0.0},
                    "pitch": {"quantity": 0, "avg_cost": 0.0},
                },
            },
            "world_state": {
                "current_port": "tortuga",
                "clock": {
                    "day": 12, "seconds_into_day": 0.0, "seconds_per_day": 180.0,
                },
                "ship": {
                    "class_id": "sloop", "name": "Sjarken", "cargo_capacity": 40,
                },
                "voyage": None,
            },
            "economy_state": {
                "markets": {"tortuga": {"commodities": {}, "tick_id": 0}},
                "regimes": {},
                "observed": {},
            },
            "pitch_lake_state": {
                "home_port": "tortuga",
                "production_per_day": production_per_day,
                "upkeep_per_day": upkeep_per_day,
                "pending_units": 0,
                "total_produced": total_produced,
                "last_production_day": last_production_day,
            },
        }

    def test_legacy_v5_migrated_has_purchased_true(self, tmp_path):
        path = tmp_path / "v5.json"
        path.write_text(json.dumps(self._make_v5_payload()), encoding="utf-8")
        loaded = save_module.load(str(path))
        assert loaded is not None
        assert loaded.version == 6
        assert loaded.pitch_lake_state.purchased is True

    def test_legacy_v5_preserves_production_values(self, tmp_path):
        """v5-save hadde production=2, upkeep=8 → v6 bevarer disse
        (ikke nullet som for fresh v6)."""
        path = tmp_path / "v5.json"
        path.write_text(json.dumps(self._make_v5_payload()), encoding="utf-8")
        loaded = save_module.load(str(path))
        assert loaded.pitch_lake_state.production_per_day == 2
        assert loaded.pitch_lake_state.upkeep_per_day == 8
        assert loaded.pitch_lake_state.total_produced == 24  # historikk bevart
        assert loaded.pitch_lake_state.last_production_day == 11

    def test_legacy_v5_produces_on_next_dawn_unchanged(self, tmp_path):
        """Presisering #3 (andre punkt): migrert v5-save fortsetter å
        produsere uendret ved neste dawn-tick."""
        path = tmp_path / "v5.json"
        path.write_text(json.dumps(self._make_v5_payload(gold=100)), encoding="utf-8")
        loaded = save_module.load(str(path))
        assert loaded.pitch_lake_state.purchased is True

        # Simulér dawn-tick på dag 13 (clock fortsetter fra 12)
        loaded.world_state.clock.day = 13
        produced, paid = PitchLake.on_new_day(
            loaded.pitch_lake_state, loaded
        )
        assert produced == 2
        assert paid == 8
        assert loaded.player_state.gold == 100 - 8
        # total_produced oppdatert fra 24 → 26
        assert loaded.pitch_lake_state.total_produced == 26

    def test_legacy_v5_bek_entry_hidden_in_tavern(self, tmp_path, font):
        """Presisering #3 (andre punkt): etter migrering er kjøp-entry
        skjult (purchased=True)."""
        path = tmp_path / "v5.json"
        path.write_text(json.dumps(self._make_v5_payload()), encoding="utf-8")
        loaded = save_module.load(str(path))

        d = TavernDayDialog(font, loaded, port_id="tortuga")
        entries = d._build_entries()
        action_ids = [e.action_id for e in entries]
        assert ACTION_PITCH_LAKE_PURCHASE not in action_ids

    def test_legacy_v5_custom_production_preserved(self, tmp_path):
        """Edge: v5-save med ikke-standard production/upkeep (f.eks.
        spiller som tunet balance.json) bevarer disse verdiene."""
        path = tmp_path / "v5.json"
        path.write_text(
            json.dumps(self._make_v5_payload(
                production_per_day=5, upkeep_per_day=15
            )),
            encoding="utf-8",
        )
        loaded = save_module.load(str(path))
        assert loaded.pitch_lake_state.purchased is True
        assert loaded.pitch_lake_state.production_per_day == 5
        assert loaded.pitch_lake_state.upkeep_per_day == 15
