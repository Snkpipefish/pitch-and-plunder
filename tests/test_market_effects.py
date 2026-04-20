"""Tester for systems.market_effects + tavern-handlere + rumor-integrasjon.

Fase 3 C3-10. Dekker:
- register_market_effect + sample_target pure-functions
- on_dawn: anvender effekter ved impact_day, fjerner dem
- Pris-mutasjon via direction + magnitude
- Integrasjon med tick_all_ports_dawn (etter regime-drift)
- Tavern-handler for sabotasje + falskt rykte
- Rumors spike-sampling inkluderer pending effects med forrang
"""

from __future__ import annotations

import json
import random
from pathlib import Path

import pygame
import pytest

import constants
from state.game_state import GameState
from state.market_effects import PendingMarketEffect
from state.market_state import CommodityMarket, MarketState
from state.rumor_state import ActiveRumor
from systems import balance as _balance
from systems import market_effects, rumors, save as save_module
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


def _keydown(key: int, mod: int = 0) -> pygame.event.Event:
    return pygame.event.Event(pygame.KEYDOWN, {"key": key, "mod": mod})


# -----------------------------------------------------------------------------
# sample_target
# -----------------------------------------------------------------------------


class TestSampleTarget:
    def test_returns_port_commodity_pair(self, state):
        target = market_effects.sample_target(
            state, exclude_port="tortuga", rng=random.Random(42),
        )
        assert target is not None
        port_id, commodity_id = target
        assert port_id != "tortuga"
        assert commodity_id in ("sugar", "rum", "tobacco", "pitch")

    def test_excludes_current_port(self, state):
        for _ in range(20):
            target = market_effects.sample_target(
                state, exclude_port="havana", rng=random.Random()
            )
            assert target[0] != "havana"

    def test_none_exclude_gives_any_port(self, state):
        target = market_effects.sample_target(state, exclude_port=None)
        # Ingen eksklusjon — hvilken som helst havn ok
        assert target is not None
        from config import port_config
        assert target[0] in port_config.get_all_port_ids()


# -----------------------------------------------------------------------------
# register_market_effect
# -----------------------------------------------------------------------------


class TestRegisterMarketEffect:
    def test_appends_effect_with_impact_day(self, state):
        state.world_state.clock.day = 10
        effect = market_effects.register_market_effect(
            state=state,
            port_id="havana",
            commodity_id="rum",
            direction="up",
            magnitude_pct=10.0,
            source_type="sabotage",
            impact_delay_days=2,
        )
        assert effect.impact_day == 12
        assert effect in state.economy_state.pending_market_effects

    def test_direction_up_preserved(self, state):
        effect = market_effects.register_market_effect(
            state, port_id="nassau", commodity_id="sugar",
            direction="up", magnitude_pct=10.0,
            source_type="sabotage", impact_delay_days=2,
        )
        assert effect.direction == "up"

    def test_direction_down_preserved(self, state):
        effect = market_effects.register_market_effect(
            state, port_id="port_royal", commodity_id="tobacco",
            direction="down", magnitude_pct=10.0,
            source_type="false_rumor", impact_delay_days=2,
        )
        assert effect.direction == "down"

    def test_multiple_effects_all_registered(self, state):
        market_effects.register_market_effect(
            state, port_id="havana", commodity_id="rum",
            direction="up", magnitude_pct=10.0,
            source_type="sabotage", impact_delay_days=2,
        )
        market_effects.register_market_effect(
            state, port_id="nassau", commodity_id="pitch",
            direction="down", magnitude_pct=10.0,
            source_type="false_rumor", impact_delay_days=3,
        )
        assert len(state.economy_state.pending_market_effects) == 2


# -----------------------------------------------------------------------------
# on_dawn
# -----------------------------------------------------------------------------


class TestOnDawn:
    def _set_price(self, state, port_id, commodity_id, price):
        """Helper: sett current_price direkte."""
        state.economy_state.markets[port_id].commodities[commodity_id] = (
            CommodityMarket(current_price=price, price_history=[])
        )

    def test_effect_not_applied_before_impact_day(self, state):
        state.world_state.clock.day = 5
        self._set_price(state, "havana", "rum", 100.0)
        market_effects.register_market_effect(
            state, port_id="havana", commodity_id="rum",
            direction="up", magnitude_pct=10.0,
            source_type="sabotage", impact_delay_days=2,
        )
        # impact_day = 7, current day = 5
        market_effects.on_dawn(state)
        assert state.economy_state.markets["havana"].commodities["rum"].current_price == 100.0
        assert len(state.economy_state.pending_market_effects) == 1

    def test_up_effect_raises_price(self, state):
        state.world_state.clock.day = 5
        self._set_price(state, "havana", "rum", 100.0)
        # register med impact_delay=0 så det trigges umiddelbart
        market_effects.register_market_effect(
            state, port_id="havana", commodity_id="rum",
            direction="up", magnitude_pct=10.0,
            source_type="sabotage", impact_delay_days=0,
        )
        applied = market_effects.on_dawn(state)
        assert len(applied) == 1
        # 100 × 1.10 = 110
        assert state.economy_state.markets["havana"].commodities["rum"].current_price == pytest.approx(110.0)

    def test_down_effect_lowers_price(self, state):
        state.world_state.clock.day = 5
        self._set_price(state, "nassau", "sugar", 50.0)
        market_effects.register_market_effect(
            state, port_id="nassau", commodity_id="sugar",
            direction="down", magnitude_pct=10.0,
            source_type="false_rumor", impact_delay_days=0,
        )
        market_effects.on_dawn(state)
        # 50 × 0.90 = 45
        assert state.economy_state.markets["nassau"].commodities["sugar"].current_price == pytest.approx(45.0)

    def test_applied_effects_removed_from_pending(self, state):
        state.world_state.clock.day = 5
        self._set_price(state, "havana", "rum", 100.0)
        market_effects.register_market_effect(
            state, port_id="havana", commodity_id="rum",
            direction="up", magnitude_pct=10.0,
            source_type="sabotage", impact_delay_days=0,
        )
        market_effects.on_dawn(state)
        assert state.economy_state.pending_market_effects == []

    def test_only_due_effects_removed(self, state):
        """Effekt A har impact_day=5, B har impact_day=10.
        Ved dawn på dag 5 skal bare A anvendes."""
        state.world_state.clock.day = 5
        self._set_price(state, "havana", "rum", 100.0)
        self._set_price(state, "nassau", "pitch", 50.0)
        market_effects.register_market_effect(
            state, port_id="havana", commodity_id="rum",
            direction="up", magnitude_pct=10.0,
            source_type="sabotage", impact_delay_days=0,
        )
        market_effects.register_market_effect(
            state, port_id="nassau", commodity_id="pitch",
            direction="up", magnitude_pct=10.0,
            source_type="sabotage", impact_delay_days=5,
        )
        market_effects.on_dawn(state)
        # A anvendt, B igjen
        assert len(state.economy_state.pending_market_effects) == 1
        assert state.economy_state.pending_market_effects[0].port_id == "nassau"

    def test_bumps_tick_id(self, state):
        state.world_state.clock.day = 5
        self._set_price(state, "havana", "rum", 100.0)
        initial_tick = state.economy_state.markets["havana"].tick_id
        market_effects.register_market_effect(
            state, port_id="havana", commodity_id="rum",
            direction="up", magnitude_pct=10.0,
            source_type="sabotage", impact_delay_days=0,
        )
        market_effects.on_dawn(state)
        assert state.economy_state.markets["havana"].tick_id == initial_tick + 1

    def test_empty_pending_list_noop(self, state):
        """on_dawn med tom pending-liste crasher ikke."""
        state.world_state.clock.day = 5
        market_effects.on_dawn(state)
        assert state.economy_state.pending_market_effects == []

    def test_price_floor_prevents_zero_or_negative(self, state):
        """Stacking negative effekter skal ikke gi pris <= 0."""
        state.world_state.clock.day = 5
        self._set_price(state, "havana", "rum", 2.0)  # lav pris
        # Registrer mange "down" effekter for å prøve å drive til 0
        for _ in range(20):
            market_effects.register_market_effect(
                state, port_id="havana", commodity_id="rum",
                direction="down", magnitude_pct=50.0,
                source_type="false_rumor", impact_delay_days=0,
            )
        market_effects.on_dawn(state)
        price = state.economy_state.markets["havana"].commodities["rum"].current_price
        assert price >= 1.0  # floor = 1.0


# -----------------------------------------------------------------------------
# Integrasjon med tick_all_ports_dawn
# -----------------------------------------------------------------------------


class TestDawnPipelineIntegration:
    def test_effects_applied_via_tick_all_ports_dawn(self, state):
        """Full dawn-pipeline kjører market_effects.on_dawn etter
        rumors og suspicion."""
        state.world_state.clock.day = 3
        state.economy_state.markets["havana"].commodities["rum"] = (
            CommodityMarket(current_price=100.0, price_history=[])
        )
        market_effects.register_market_effect(
            state, port_id="havana", commodity_id="rum",
            direction="up", magnitude_pct=10.0,
            source_type="sabotage", impact_delay_days=0,
        )
        m = Market.from_json("data/commodities.json")
        rm = RegimeManager()
        tick_all_ports_dawn(state, m, rm)
        # Effekten anvendt. current_price påvirkes først av regime-drift
        # (stable = 0) og så av market_effects (+10%). Kan være ±1% noise.
        new_price = state.economy_state.markets["havana"].commodities["rum"].current_price
        assert new_price >= 109.0  # ~110 minus liten noise
        assert state.economy_state.pending_market_effects == []

    def test_multi_day_voyage_effect_triggers_on_correct_day(self, state):
        """Sabotasje registrert på dag 1 med delay=2 → impact_day=3.
        Multi-day voyage kjører tick_all_ports_dawn flere ganger;
        effekten trigger kun på dag 3."""
        state.world_state.clock.day = 1
        state.economy_state.markets["nassau"].commodities["sugar"] = (
            CommodityMarket(current_price=40.0, price_history=[])
        )
        market_effects.register_market_effect(
            state, port_id="nassau", commodity_id="sugar",
            direction="up", magnitude_pct=10.0,
            source_type="sabotage", impact_delay_days=2,
        )
        m = Market.from_json("data/commodities.json")
        rm = RegimeManager()
        # Dag 1 → dag 2: ikke trigger
        state.world_state.clock.day = 2
        tick_all_ports_dawn(state, m, rm)
        assert len(state.economy_state.pending_market_effects) == 1
        # Dag 3: trigger
        state.world_state.clock.day = 3
        tick_all_ports_dawn(state, m, rm)
        assert len(state.economy_state.pending_market_effects) == 0


# -----------------------------------------------------------------------------
# Tavern-handlere: sabotasje og falskt rykte
# -----------------------------------------------------------------------------


class TestTavernSabotageHandler:
    def _buy(self, font, state, action_id):
        from ui.tavern_dialog import TavernNightDialog
        from ui.toast import ToastQueue
        toasts = ToastQueue(baseline_y=340, center_x=320)
        d = TavernNightDialog(font, state, port_id="tortuga", toasts=toasts)
        entries = d._build_entries()
        idx = next(i for i, e in enumerate(entries) if e.action_id == action_id)
        d._selected = idx
        d.handle_event(_keydown(pygame.K_RETURN))
        return d, toasts

    def test_sabotage_deducts_50_gold(self, font, state):
        from ui.tavern_dialog import ACTION_ORDER_SABOTAGE
        state.player_state.gold = 100
        self._buy(font, state, ACTION_ORDER_SABOTAGE)
        assert state.player_state.gold == 50

    def test_sabotage_increases_suspicion(self, font, state):
        from ui.tavern_dialog import ACTION_ORDER_SABOTAGE
        state.player_state.gold = 100
        initial_sus = state.player_state.suspicion
        self._buy(font, state, ACTION_ORDER_SABOTAGE)
        # sabotage.suspicion_increase_sabotage = 15
        assert state.player_state.suspicion == initial_sus + 15.0

    def test_sabotage_consumes_rest(self, font, state):
        from ui.tavern_dialog import ACTION_ORDER_SABOTAGE
        state.player_state.gold = 100
        state.player_state.rest = 1.0
        self._buy(font, state, ACTION_ORDER_SABOTAGE)
        # 2.0 h × 0.05 decay = 0.10
        assert state.player_state.rest == pytest.approx(0.90)

    def test_sabotage_registers_pending_effect_up(self, font, state):
        from ui.tavern_dialog import ACTION_ORDER_SABOTAGE
        state.player_state.gold = 100
        initial_count = len(state.economy_state.pending_market_effects)
        self._buy(font, state, ACTION_ORDER_SABOTAGE)
        assert len(state.economy_state.pending_market_effects) == initial_count + 1
        new_effect = state.economy_state.pending_market_effects[-1]
        assert new_effect.direction == "up"
        assert new_effect.source_type == "sabotage"
        assert new_effect.magnitude_pct == 10.0

    def test_sabotage_target_not_current_port(self, font, state):
        """Sampling ekskluderer current_port (tortuga her)."""
        from ui.tavern_dialog import ACTION_ORDER_SABOTAGE
        state.player_state.gold = 10000
        for _ in range(10):
            d, _ = self._buy(font, state, ACTION_ORDER_SABOTAGE)
        targets = {
            e.port_id for e in state.economy_state.pending_market_effects
        }
        assert "tortuga" not in targets

    def test_sabotage_insufficient_gold_no_mutation(self, font, state):
        from ui.tavern_dialog import ACTION_ORDER_SABOTAGE
        state.player_state.gold = 10  # < 50
        initial_sus = state.player_state.suspicion
        initial_count = len(state.economy_state.pending_market_effects)
        self._buy(font, state, ACTION_ORDER_SABOTAGE)
        assert state.player_state.gold == 10
        assert state.player_state.suspicion == initial_sus
        assert len(state.economy_state.pending_market_effects) == initial_count

    def test_sabotage_pushes_toast(self, font, state):
        from ui.tavern_dialog import ACTION_ORDER_SABOTAGE
        state.player_state.gold = 100
        _, toasts = self._buy(font, state, ACTION_ORDER_SABOTAGE)
        assert toasts.count == 1


class TestTavernFalseRumorHandler:
    def _buy(self, font, state, action_id):
        from ui.tavern_dialog import TavernNightDialog
        from ui.toast import ToastQueue
        toasts = ToastQueue(baseline_y=340, center_x=320)
        d = TavernNightDialog(font, state, port_id="tortuga", toasts=toasts)
        entries = d._build_entries()
        idx = next(i for i, e in enumerate(entries) if e.action_id == action_id)
        d._selected = idx
        d.handle_event(_keydown(pygame.K_RETURN))
        return d, toasts

    def test_false_rumor_deducts_40_gold(self, font, state):
        from ui.tavern_dialog import ACTION_SPREAD_FALSE_RUMOR
        state.player_state.gold = 100
        self._buy(font, state, ACTION_SPREAD_FALSE_RUMOR)
        # sabotage.false_rumor_base_cost_gold = 40
        assert state.player_state.gold == 60

    def test_false_rumor_increases_suspicion_less(self, font, state):
        from ui.tavern_dialog import ACTION_SPREAD_FALSE_RUMOR
        state.player_state.gold = 100
        initial_sus = state.player_state.suspicion
        self._buy(font, state, ACTION_SPREAD_FALSE_RUMOR)
        # sabotage.suspicion_increase_false_rumor = 8
        assert state.player_state.suspicion == initial_sus + 8.0

    def test_false_rumor_registers_pending_effect_down(self, font, state):
        from ui.tavern_dialog import ACTION_SPREAD_FALSE_RUMOR
        state.player_state.gold = 100
        self._buy(font, state, ACTION_SPREAD_FALSE_RUMOR)
        effect = state.economy_state.pending_market_effects[-1]
        assert effect.direction == "down"
        assert effect.source_type == "false_rumor"

    def test_false_rumor_insufficient_gold_no_mutation(self, font, state):
        from ui.tavern_dialog import ACTION_SPREAD_FALSE_RUMOR
        state.player_state.gold = 30  # < 40
        initial_sus = state.player_state.suspicion
        initial_count = len(state.economy_state.pending_market_effects)
        self._buy(font, state, ACTION_SPREAD_FALSE_RUMOR)
        assert state.player_state.gold == 30
        assert state.player_state.suspicion == initial_sus
        assert len(state.economy_state.pending_market_effects) == initial_count


# -----------------------------------------------------------------------------
# Rumors spike-sampling utvidelse
# -----------------------------------------------------------------------------


class TestRumorSpikeSamplingIncludesEffects:
    def test_pending_effect_shows_up_as_candidate(self, state):
        """Alle regimer stable → C3-9 returnerte None. C3-10 skal
        fortsatt returnere None uten pending effects, men med en
        pending effect skal kandidat-listen ikke være tom."""
        # Tving alle regimer stable
        for port_id, regime_dict in state.economy_state.regimes.items():
            for cid in regime_dict:
                regime_dict[cid] = RegimeState(current="stable", days_remaining=3)
        # Ingen effekter → None
        assert rumors.buy_price_spike_warning(state, random.Random(0)) is None
        # Legg til pending effect
        state.world_state.clock.day = 5
        market_effects.register_market_effect(
            state, port_id="havana", commodity_id="rum",
            direction="up", magnitude_pct=10.0,
            source_type="sabotage", impact_delay_days=2,
        )
        # Nå skal det finnes en kandidat
        rumor = rumors.buy_price_spike_warning(state, random.Random(0))
        assert rumor is not None
        assert rumor.port_id == "havana"
        assert rumor.commodity_id == "rum"
        assert rumor.payload["direction"] == "up"

    def test_effect_takes_precedence_over_regime(self, state):
        """Hvis samme (port, commodity) har både volatilt regime OG
        pending effect, skal effect ha forrang."""
        # Tving alle regimer stable for å isolere
        for port_id, regime_dict in state.economy_state.regimes.items():
            for cid in regime_dict:
                regime_dict[cid] = RegimeState(current="stable", days_remaining=3)
        # Regime = rising (3 dager igjen)
        state.economy_state.regimes["havana"]["rum"] = RegimeState(
            current="rising", days_remaining=3
        )
        # Effekt = down (1 dag til)
        state.world_state.clock.day = 5
        market_effects.register_market_effect(
            state, port_id="havana", commodity_id="rum",
            direction="down", magnitude_pct=10.0,
            source_type="false_rumor", impact_delay_days=1,
        )
        # Sampel skal prefere effekten
        rumor = rumors.buy_price_spike_warning(state, random.Random(0))
        assert rumor is not None
        assert rumor.port_id == "havana"
        assert rumor.commodity_id == "rum"
        # Direction fra effekten, ikke regimet
        assert rumor.payload["direction"] == "down"
        assert rumor.payload["days_until_tick"] == 1

    def test_both_regime_and_effect_give_multiple_candidates(self, state):
        """Regime på (A, sukker) + effect på (B, rom) = 2 kandidater.
        Sampling-fordeling er random."""
        # Tving alt stable
        for port_id, regime_dict in state.economy_state.regimes.items():
            for cid in regime_dict:
                regime_dict[cid] = RegimeState(current="stable", days_remaining=3)
        state.economy_state.regimes["havana"]["sugar"] = RegimeState(
            current="rising", days_remaining=2
        )
        state.world_state.clock.day = 5
        market_effects.register_market_effect(
            state, port_id="nassau", commodity_id="rum",
            direction="down", magnitude_pct=10.0,
            source_type="false_rumor", impact_delay_days=3,
        )
        # Sampel N ganger, forvent begge som mulige
        seen_targets = set()
        for _ in range(30):
            state.player_state.active_rumors = []  # reset
            rumor = rumors.buy_price_spike_warning(state, random.Random())
            seen_targets.add((rumor.port_id, rumor.commodity_id))
        assert ("havana", "sugar") in seen_targets
        assert ("nassau", "rum") in seen_targets
