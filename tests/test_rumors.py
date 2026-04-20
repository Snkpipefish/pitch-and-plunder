"""Tester for rykte-systemet — Fase 3 C3-9.

Dekker:
- systems.rumors pure-functions (sampling + TTL decay)
- Tavern-night rykte-kjøp (regime + spike, inkl. refund-flyt)
- Integrasjon med tick_all_ports_dawn (TTL akkumulerer over voyage)
- RumorsDialog layout og ESC-close
- HUD "Rykter: N"-linje
- R-tast i PortVillageScene
"""

from __future__ import annotations

import random

import pygame
import pytest

import constants
from state.game_state import GameState
from state.rumor_state import ActiveRumor
from systems import balance as _balance
from systems import rumors, save as save_module
from systems.economy import Market, tick_all_ports_dawn
from systems.regime_manager import RegimeManager, RegimeState


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
def state() -> GameState:
    return save_module.new_game_state()


@pytest.fixture
def rng() -> random.Random:
    return random.Random(42)  # seedet for deterministikk


def _keydown(key: int, mod: int = 0) -> pygame.event.Event:
    return pygame.event.Event(pygame.KEYDOWN, {"key": key, "mod": mod})


# -----------------------------------------------------------------------------
# systems.rumors: regime_preview sampling
# -----------------------------------------------------------------------------


class TestRegimePreview:
    def test_buy_adds_active_rumor(self, state, rng):
        initial = len(state.player_state.active_rumors)
        result = rumors.buy_regime_preview(state, rng)
        assert result is not None
        assert len(state.player_state.active_rumors) == initial + 1

    def test_rumor_type_is_regime_preview(self, state, rng):
        rumor = rumors.buy_regime_preview(state, rng)
        assert rumor.rumor_type == "regime_preview"

    def test_target_port_is_not_current(self, state, rng):
        """Presisering #1: sampler tilfeldig annen havn."""
        state.world_state.current_port = "tortuga"
        for _ in range(20):  # flere sampler for å sikre
            rumor = rumors.buy_regime_preview(state, rng)
            assert rumor.port_id != "tortuga"

    def test_ttl_set_from_balance(self, state, rng):
        bal = _balance.get()
        rumor = rumors.buy_regime_preview(state, rng)
        assert rumor.days_remaining == bal.rumors.ttl_days

    def test_payload_includes_regime_and_days(self, state, rng):
        rumor = rumors.buy_regime_preview(state, rng)
        assert "predicted_regime" in rumor.payload
        assert "days_until_tick" in rumor.payload
        assert rumor.payload["predicted_regime"] in ("rising", "stable", "falling")
        assert isinstance(rumor.payload["days_until_tick"], int)
        assert rumor.payload["days_until_tick"] >= 0

    def test_samples_from_all_three_other_ports_over_time(self, state):
        """20 seedede samples dekker minst 2-3 ulike andre havner.
        Bekrefter at sampling ikke fastlåses på én havn."""
        state.world_state.current_port = "tortuga"
        rng = random.Random(0)
        seen_ports = set()
        for _ in range(50):
            rumor = rumors.buy_regime_preview(state, rng)
            seen_ports.add(rumor.port_id)
        # Minst 2 andre havner sett (random.choice i 3-element-liste)
        assert len(seen_ports) >= 2
        assert "tortuga" not in seen_ports


# -----------------------------------------------------------------------------
# systems.rumors: price_spike_warning sampling
# -----------------------------------------------------------------------------


class TestPriceSpikeWarning:
    def test_returns_none_when_all_stable(self, state, rng):
        """Presisering #1: refund-sti når ingen spike-kandidater finnes."""
        # Sett alle regimer til stable
        for port_id, regime_dict in state.economy_state.regimes.items():
            for cid in regime_dict:
                regime_dict[cid] = RegimeState(current="stable", days_remaining=3)
        result = rumors.buy_price_spike_warning(state, rng)
        assert result is None
        assert len(state.player_state.active_rumors) == 0

    def test_samples_from_volatile_regimes(self, state, rng):
        """Hvis et regime er `rising`, skal spike-rykte peke på det."""
        # Tving alle regimer til stable, bortsett fra én rising
        for port_id, regime_dict in state.economy_state.regimes.items():
            for cid in regime_dict:
                regime_dict[cid] = RegimeState(current="stable", days_remaining=3)
        state.economy_state.regimes["havana"]["rum"] = RegimeState(
            current="rising", days_remaining=2
        )
        rumor = rumors.buy_price_spike_warning(state, rng)
        assert rumor is not None
        assert rumor.rumor_type == "price_spike_warning"
        assert rumor.port_id == "havana"
        assert rumor.commodity_id == "rum"
        assert rumor.payload["direction"] == "up"
        assert rumor.payload["days_until_tick"] == 2

    def test_falling_gives_down_direction(self, state, rng):
        for port_id, regime_dict in state.economy_state.regimes.items():
            for cid in regime_dict:
                regime_dict[cid] = RegimeState(current="stable", days_remaining=3)
        state.economy_state.regimes["nassau"]["pitch"] = RegimeState(
            current="falling", days_remaining=4
        )
        rumor = rumors.buy_price_spike_warning(state, rng)
        assert rumor is not None
        assert rumor.payload["direction"] == "down"

    def test_ttl_set_from_balance(self, state, rng):
        state.economy_state.regimes["tortuga"]["sugar"] = RegimeState(
            current="rising", days_remaining=2
        )
        bal = _balance.get()
        rumor = rumors.buy_price_spike_warning(state, rng)
        assert rumor.days_remaining == bal.rumors.ttl_days


# -----------------------------------------------------------------------------
# systems.rumors: TTL decay + on_dawn
# -----------------------------------------------------------------------------


class TestOnDawn:
    def test_decrements_days_remaining(self, state):
        state.player_state.active_rumors = [
            ActiveRumor(
                rumor_type="regime_preview", port_id="havana",
                commodity_id="rum", days_remaining=3, payload={},
            ),
        ]
        rumors.on_dawn(state)
        assert state.player_state.active_rumors[0].days_remaining == 2

    def test_removes_expired_rumors(self, state):
        state.player_state.active_rumors = [
            ActiveRumor(days_remaining=1),  # vil expire
            ActiveRumor(days_remaining=3),  # vil bli 2
        ]
        rumors.on_dawn(state)
        assert len(state.player_state.active_rumors) == 1
        assert state.player_state.active_rumors[0].days_remaining == 2

    def test_multi_day_decay_accumulates(self, state):
        state.player_state.active_rumors = [
            ActiveRumor(days_remaining=5),
        ]
        for _ in range(3):
            rumors.on_dawn(state)
        assert state.player_state.active_rumors[0].days_remaining == 2

    def test_all_expired_leaves_empty_list(self, state):
        state.player_state.active_rumors = [
            ActiveRumor(days_remaining=1),
            ActiveRumor(days_remaining=1),
        ]
        rumors.on_dawn(state)
        assert state.player_state.active_rumors == []

    def test_empty_list_is_safe_noop(self, state):
        assert state.player_state.active_rumors == []
        rumors.on_dawn(state)  # skal ikke crashe
        assert state.player_state.active_rumors == []


# -----------------------------------------------------------------------------
# Integrasjon: tick_all_ports_dawn kaller rumors.on_dawn
# -----------------------------------------------------------------------------


class TestDawnPipelineIntegration:
    def test_tick_all_ports_dawn_decrements_rumor_ttl(self, state):
        state.player_state.active_rumors = [
            ActiveRumor(days_remaining=3),
        ]
        market = Market.from_json("data/commodities.json")
        rm = RegimeManager()
        tick_all_ports_dawn(state, market, rm)
        assert state.player_state.active_rumors[0].days_remaining == 2

    def test_multi_day_voyage_expires_short_rumor(self, state):
        """Presisering #3: multi-day voyage kaller dawn N ganger, rykte
        med TTL=2 forsvinner etter 2+ dager reise."""
        state.player_state.active_rumors = [
            ActiveRumor(days_remaining=2),
        ]
        market = Market.from_json("data/commodities.json")
        rm = RegimeManager()
        for _ in range(3):  # 3 days
            tick_all_ports_dawn(state, market, rm)
        assert state.player_state.active_rumors == []


# -----------------------------------------------------------------------------
# Tavern-night rykte-kjøp
# -----------------------------------------------------------------------------


class TestTavernBuyRumor:
    def _buy(self, font, state, action_id, toasts=None):
        from ui.tavern_dialog import TavernNightDialog
        from ui.toast import ToastQueue
        if toasts is None:
            toasts = ToastQueue(baseline_y=340, center_x=320)
        d = TavernNightDialog(font, state, port_id="tortuga", toasts=toasts)
        entries = d._build_entries()
        idx = next(i for i, e in enumerate(entries) if e.action_id == action_id)
        d._selected = idx
        d.handle_event(_keydown(pygame.K_RETURN))
        return d, toasts

    def test_regime_rumor_purchase_deducts_gold(self, font, state):
        from ui.tavern_dialog import ACTION_BUY_RUMOR_REGIME
        state.player_state.gold = 100
        self._buy(font, state, ACTION_BUY_RUMOR_REGIME)
        # rumors.cost_gold = 20
        assert state.player_state.gold == 80

    def test_regime_rumor_adds_to_active_rumors(self, font, state):
        from ui.tavern_dialog import ACTION_BUY_RUMOR_REGIME
        state.player_state.gold = 100
        initial = len(state.player_state.active_rumors)
        self._buy(font, state, ACTION_BUY_RUMOR_REGIME)
        assert len(state.player_state.active_rumors) == initial + 1

    def test_regime_rumor_consumes_rest(self, font, state):
        from ui.tavern_dialog import ACTION_BUY_RUMOR_REGIME
        state.player_state.gold = 100
        state.player_state.rest = 1.0
        self._buy(font, state, ACTION_BUY_RUMOR_REGIME)
        # 1.0 h × 0.05 decay = 0.05
        assert state.player_state.rest == pytest.approx(0.95)

    def test_regime_rumor_insufficient_gold_no_mutation(self, font, state):
        from ui.tavern_dialog import ACTION_BUY_RUMOR_REGIME
        state.player_state.gold = 10  # < 20
        state.player_state.rest = 1.0
        initial_rumors = len(state.player_state.active_rumors)
        self._buy(font, state, ACTION_BUY_RUMOR_REGIME)
        assert state.player_state.gold == 10
        assert state.player_state.rest == 1.0
        assert len(state.player_state.active_rumors) == initial_rumors

    def test_spike_rumor_refund_when_no_candidates(self, font, state):
        """Presisering #1: alle regimer stabile → refund + toast, ingen
        rest-decay."""
        from ui.tavern_dialog import ACTION_BUY_RUMOR_SPIKE
        # Tving alle regimer til stable
        for port_id, regime_dict in state.economy_state.regimes.items():
            for cid in regime_dict:
                regime_dict[cid] = RegimeState(current="stable", days_remaining=3)
        state.player_state.gold = 100
        state.player_state.rest = 1.0
        initial_rumors = len(state.player_state.active_rumors)
        _, toasts = self._buy(font, state, ACTION_BUY_RUMOR_SPIKE)
        # Gull refundert, rest uendret, ingen rykte lagt til, toast pushet
        assert state.player_state.gold == 100
        assert state.player_state.rest == 1.0
        assert len(state.player_state.active_rumors) == initial_rumors
        assert toasts.count == 1

    def test_spike_rumor_success_adds_rumor(self, font, state):
        from ui.tavern_dialog import ACTION_BUY_RUMOR_SPIKE
        # Sikre minst én volatilt regime
        state.economy_state.regimes["havana"]["rum"] = RegimeState(
            current="rising", days_remaining=2
        )
        state.player_state.gold = 100
        self._buy(font, state, ACTION_BUY_RUMOR_SPIKE)
        assert state.player_state.gold == 80
        # Finn nyeste spike-rykte
        spike_rumors = [
            r for r in state.player_state.active_rumors
            if r.rumor_type == "price_spike_warning"
        ]
        assert len(spike_rumors) >= 1


# -----------------------------------------------------------------------------
# RumorsDialog
# -----------------------------------------------------------------------------


class TestRumorsDialog:
    def test_empty_state_shows_message(self, font, state):
        from ui.rumors_dialog import RumorsDialog
        assert state.player_state.active_rumors == []
        d = RumorsDialog(font, state)
        surf = pygame.Surface((640, 360))
        d.draw(surf)  # skal ikke crashe

    def test_renders_with_multiple_rumors(self, font, state):
        from ui.rumors_dialog import RumorsDialog
        state.player_state.active_rumors = [
            ActiveRumor(
                rumor_type="regime_preview", port_id="havana",
                commodity_id="rum", days_remaining=3,
                payload={"predicted_regime": "rising", "days_until_tick": 2},
            ),
            ActiveRumor(
                rumor_type="price_spike_warning", port_id="nassau",
                commodity_id="pitch", days_remaining=2,
                payload={"direction": "down", "days_until_tick": 1},
            ),
        ]
        d = RumorsDialog(font, state)
        surf = pygame.Surface((640, 360))
        d.draw(surf)

    def test_esc_sets_want_close(self, font, state):
        from ui.rumors_dialog import RumorsDialog
        d = RumorsDialog(font, state)
        d.handle_event(_keydown(pygame.K_ESCAPE))
        assert d.want_close is True

    def test_no_activation_on_enter(self, font, state):
        from ui.rumors_dialog import RumorsDialog
        d = RumorsDialog(font, state)
        d.handle_event(_keydown(pygame.K_RETURN))
        # Enter gjør ingenting — ikke lukker, ikke muterer
        assert d.want_close is False

    def test_format_rumor_line_regime_preview(self):
        from ui.rumors_dialog import format_rumor_line
        rumor = ActiveRumor(
            rumor_type="regime_preview", port_id="havana",
            commodity_id="rum", days_remaining=3,
            payload={"predicted_regime": "rising", "days_until_tick": 2},
        )
        label, days = format_rumor_line(rumor)
        assert "Regime" in label
        assert "Havana" in label
        assert "rom" in label  # norsk vare-navn
        assert "stigende" in label
        assert days == "3d"

    def test_format_rumor_line_spike(self):
        from ui.rumors_dialog import format_rumor_line
        rumor = ActiveRumor(
            rumor_type="price_spike_warning", port_id="port_royal",
            commodity_id="sugar", days_remaining=2,
            payload={"direction": "up", "days_until_tick": 1},
        )
        label, days = format_rumor_line(rumor)
        assert "Spike" in label
        assert "Port Royal" in label
        assert "sukker" in label
        assert days == "2d"


# -----------------------------------------------------------------------------
# HUD Rykter-linje
# -----------------------------------------------------------------------------


class TestHudRumorLine:
    def _hud(self, font):
        from ui.hud import Hud
        return Hud(font, "Tortuga", 100, 1)

    def test_initial_count_is_zero(self, font):
        hud = self._hud(font)
        assert hud._rumor_count == 0
        assert hud._rumor_surf is None  # skjult ved 0

    def test_zero_count_hides_line(self, font):
        hud = self._hud(font)
        hud.set_rumor_count(3)
        hud.set_rumor_count(0)
        assert hud._rumor_surf is None

    def test_positive_count_shows_line(self, font):
        hud = self._hud(font)
        hud.set_rumor_count(3)
        assert hud._rumor_surf is not None

    def test_noop_same_count(self, font):
        hud = self._hud(font)
        hud.set_rumor_count(2)
        surf_before = hud._rumor_surf
        hud.set_rumor_count(2)
        assert hud._rumor_surf is surf_before

    def test_draw_with_rumor_line(self, font):
        hud = self._hud(font)
        hud.set_rumor_count(5)
        surf = pygame.Surface((640, 360))
        hud.draw(surf)  # skal ikke crashe


# -----------------------------------------------------------------------------
# R-tast + PortVillageScene
# -----------------------------------------------------------------------------


class TestRKeyOpensRumorsDialog:
    def _scene(self, font):
        from config import port_config
        from scenes.port_village import PortVillageScene
        state = save_module.new_game_state()
        port = port_config.get("tortuga")
        scene = PortVillageScene(font, state, port)
        scene.on_enter(state, from_scene=None)
        return scene

    def test_r_key_opens_rumors_dialog(self, font):
        scene = self._scene(font)
        assert scene._rumors_dialog is None
        scene.handle_event(_keydown(pygame.K_r))
        assert scene._rumors_dialog is not None

    def test_r_key_blocked_when_other_dialog_open(self, font):
        """Når en annen dialog er åpen, skal R-tast ikke åpne rumors-
        dialogen (event konsumeres av den aktive dialogen)."""
        scene = self._scene(font)
        scene._open_tavern()
        assert scene._tavern_dialog is not None
        scene.handle_event(_keydown(pygame.K_r))
        assert scene._rumors_dialog is None

    def test_esc_closes_rumors_dialog(self, font):
        scene = self._scene(font)
        scene.handle_event(_keydown(pygame.K_r))
        assert scene._rumors_dialog is not None
        scene.handle_event(_keydown(pygame.K_ESCAPE))
        scene.update(0.016)
        assert scene._rumors_dialog is None
