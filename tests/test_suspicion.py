"""Tester for systems.suspicion + GameState.arrested + HUD-integrasjon.

Fase 3 C3-7. Pure-function-tester på state-mutasjon, samt integrasjon
med `economy.tick_all_ports_dawn` (daglig decay) og HUD-farge-bånd.
"""

from __future__ import annotations

from unittest.mock import patch

import pygame
import pytest

import constants
from state.game_state import GameState
from state.market_state import MarketState
from systems import balance as _balance
from systems import suspicion
from systems.economy import Market, tick_all_ports_dawn
from systems.regime_manager import RegimeManager


def _state_with_suspicion(value: float = 0.0, arrested: bool = False) -> GameState:
    s = GameState()
    s.player_state.suspicion = value
    s.arrested = arrested
    return s


# -----------------------------------------------------------------------------
# increase
# -----------------------------------------------------------------------------


class TestIncrease:
    def test_positive_amount_adds(self):
        state = _state_with_suspicion(0.0)
        suspicion.increase(state, 15.0)
        assert state.player_state.suspicion == 15.0

    def test_accumulates_over_multiple_calls(self):
        state = _state_with_suspicion(0.0)
        suspicion.increase(state, 15.0)
        suspicion.increase(state, 8.0)
        suspicion.increase(state, 3.5)
        assert state.player_state.suspicion == 26.5

    def test_zero_is_noop(self):
        state = _state_with_suspicion(10.0)
        suspicion.increase(state, 0.0)
        assert state.player_state.suspicion == 10.0

    def test_negative_amount_is_noop(self):
        """Negative verdier skal ikke redusere via increase — bruk
        decrease for det."""
        state = _state_with_suspicion(10.0)
        suspicion.increase(state, -5.0)
        assert state.player_state.suspicion == 10.0

    def test_can_exceed_threshold(self):
        """Ingen klamp oppover — suspicion kan gå over threshold slik
        at check_threshold detekterer arrest nøyaktig."""
        state = _state_with_suspicion(95.0)
        suspicion.increase(state, 50.0)
        # Ingen klamp — 145.0
        assert state.player_state.suspicion == 145.0


# -----------------------------------------------------------------------------
# decrease
# -----------------------------------------------------------------------------


class TestDecrease:
    def test_positive_amount_subtracts(self):
        state = _state_with_suspicion(50.0)
        suspicion.decrease(state, 10.0)
        assert state.player_state.suspicion == 40.0

    def test_clamps_to_zero(self):
        state = _state_with_suspicion(3.0)
        suspicion.decrease(state, 10.0)
        assert state.player_state.suspicion == 0.0

    def test_zero_floor_does_not_go_negative(self):
        state = _state_with_suspicion(0.0)
        suspicion.decrease(state, 5.0)
        assert state.player_state.suspicion == 0.0

    def test_zero_amount_is_noop(self):
        state = _state_with_suspicion(10.0)
        suspicion.decrease(state, 0.0)
        assert state.player_state.suspicion == 10.0

    def test_negative_amount_is_noop(self):
        state = _state_with_suspicion(10.0)
        suspicion.decrease(state, -5.0)
        assert state.player_state.suspicion == 10.0


# -----------------------------------------------------------------------------
# check_threshold + arrested-flagg
# -----------------------------------------------------------------------------


class TestCheckThreshold:
    def test_below_threshold_no_arrest(self):
        state = _state_with_suspicion(99.0)
        suspicion.check_threshold(state)
        assert state.arrested is False

    def test_exact_threshold_triggers_arrest(self):
        """suspicion == threshold (default 100) → arrested=True."""
        state = _state_with_suspicion(100.0)
        suspicion.check_threshold(state)
        assert state.arrested is True

    def test_above_threshold_triggers_arrest(self):
        state = _state_with_suspicion(150.0)
        suspicion.check_threshold(state)
        assert state.arrested is True

    def test_idempotent(self):
        """Gjentatte kall endrer ikke arrested fra True til False."""
        state = _state_with_suspicion(110.0)
        suspicion.check_threshold(state)
        assert state.arrested is True
        suspicion.decrease(state, 200.0)  # forced drop under threshold
        assert state.player_state.suspicion == 0.0
        suspicion.check_threshold(state)
        # Arrested forblir True — idempotent bare kan "låse opp" True
        assert state.arrested is True

    def test_increase_to_threshold_auto_calls_check(self):
        """increase() bør kalle check_threshold etter økning."""
        state = _state_with_suspicion(85.0)
        suspicion.increase(state, 20.0)  # 85 + 20 = 105 ≥ 100
        assert state.arrested is True


class TestArrestOnThresholdFlag:
    def test_arrest_on_threshold_false_disables_arrest(
        self, tmp_path, monkeypatch
    ):
        """Hvis balance.suspicion.arrest_on_threshold=False skal arrest
        ikke trigges. Viktig for balanse-eksperiment uten game-over."""
        import json
        _balance._reset_for_tests()
        try:
            from pathlib import Path as _P
            root = _P(__file__).resolve().parent.parent
            content = json.loads(
                (root / "data" / "balance.json").read_text(encoding="utf-8")
            )
            content["suspicion"]["arrest_on_threshold"] = False
            path = tmp_path / "balance.json"
            path.write_text(json.dumps(content), encoding="utf-8")
            _balance.init(str(path))
            state = _state_with_suspicion(200.0)
            suspicion.check_threshold(state)
            assert state.arrested is False
        finally:
            _balance._reset_for_tests()
            from pathlib import Path as _P
            root = _P(__file__).resolve().parent.parent
            _balance.init(str(root / "data" / "balance.json"))


# -----------------------------------------------------------------------------
# is_arrested
# -----------------------------------------------------------------------------


class TestIsArrested:
    def test_default_false(self):
        state = GameState()
        assert suspicion.is_arrested(state) is False

    def test_true_when_flagged(self):
        state = _state_with_suspicion(0.0, arrested=True)
        assert suspicion.is_arrested(state) is True


# -----------------------------------------------------------------------------
# on_dawn — daglig decay
# -----------------------------------------------------------------------------


class TestOnDawn:
    def test_decreases_by_daily_decay(self):
        """balance.suspicion.daily_decay = 2.0 (default)."""
        state = _state_with_suspicion(50.0)
        suspicion.on_dawn(state)
        assert state.player_state.suspicion == 48.0

    def test_clamps_to_zero(self):
        state = _state_with_suspicion(1.0)
        suspicion.on_dawn(state)
        assert state.player_state.suspicion == 0.0

    def test_accumulates_over_multiple_days(self):
        """Presisering #1: decay akkumuleres korrekt over flere dager —
        relevant for flerdagers-reise der dawn-tikkes N ganger."""
        state = _state_with_suspicion(100.0)
        for _ in range(10):
            suspicion.on_dawn(state)
        # 100 - 10×2 = 80
        assert state.player_state.suspicion == 80.0

    def test_no_arrest_from_decay(self):
        """Decay reduserer — skal ikke kunne trigge arrest."""
        state = _state_with_suspicion(50.0, arrested=False)
        suspicion.on_dawn(state)
        assert state.arrested is False


# -----------------------------------------------------------------------------
# Integrasjon med tick_all_ports_dawn
# -----------------------------------------------------------------------------


class TestDawnPipelineIntegration:
    """Verifiserer at suspicion.on_dawn kalles som del av
    economy.tick_all_ports_dawn-pipelinen (presisering #1)."""

    def _fresh_state_with_market(self) -> GameState:
        from systems.save import new_game_state
        return new_game_state()

    def test_tick_all_ports_dawn_reduces_suspicion(self):
        state = self._fresh_state_with_market()
        state.player_state.suspicion = 50.0
        market = Market.from_json("data/commodities.json")
        rm = RegimeManager()
        tick_all_ports_dawn(state, market, rm)
        # 50 - 2 = 48 (balance daily_decay=2)
        assert state.player_state.suspicion == 48.0

    def test_multi_day_voyage_accumulates_decay(self):
        """Simuler N-dagers reise: tick_all_ports_dawn kalles N ganger."""
        state = self._fresh_state_with_market()
        state.player_state.suspicion = 100.0
        market = Market.from_json("data/commodities.json")
        rm = RegimeManager()
        # 5 dager reise → 5 × decay = 10
        for _ in range(5):
            tick_all_ports_dawn(state, market, rm)
        assert state.player_state.suspicion == 90.0

    def test_tick_dawn_preserves_arrested_flag(self):
        """Spilleren er allerede arrestert — dawn-tick skal ikke
        "av-arresting" selv om decay senker suspicion under threshold."""
        state = self._fresh_state_with_market()
        state.player_state.suspicion = 100.0
        state.arrested = True
        market = Market.from_json("data/commodities.json")
        rm = RegimeManager()
        for _ in range(10):
            tick_all_ports_dawn(state, market, rm)
        # Suspicion klampet til 0 eller lav verdi, men arrested forblir True
        assert state.arrested is True


# -----------------------------------------------------------------------------
# HUD-fargebånd
# -----------------------------------------------------------------------------


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


class TestHudSuspicionColorBands:
    def test_zero_stone_bright(self, font):
        from ui.hud import Hud
        assert Hud._suspicion_color(0) == constants.COLOR_STONE_BRIGHT

    def test_below_30_stone_bright(self, font):
        from ui.hud import Hud
        assert Hud._suspicion_color(29) == constants.COLOR_STONE_BRIGHT

    def test_exactly_30_lantern(self, font):
        from ui.hud import Hud
        assert Hud._suspicion_color(30) == constants.COLOR_LANTERN

    def test_below_70_lantern(self, font):
        from ui.hud import Hud
        assert Hud._suspicion_color(69) == constants.COLOR_LANTERN

    def test_exactly_70_ember(self, font):
        from ui.hud import Hud
        assert Hud._suspicion_color(70) == constants.COLOR_EMBER

    def test_below_90_ember(self, font):
        from ui.hud import Hud
        assert Hud._suspicion_color(89) == constants.COLOR_EMBER

    def test_exactly_90_flame(self, font):
        from ui.hud import Hud
        assert Hud._suspicion_color(90) == constants.COLOR_FLAME

    def test_above_90_flame(self, font):
        from ui.hud import Hud
        assert Hud._suspicion_color(150) == constants.COLOR_FLAME


class TestHudSuspicionCache:
    """Set-metoden skal være no-op når int-verdien er uendret."""

    def _hud(self, font):
        from ui.hud import Hud
        return Hud(font, "Tortuga", 100, 1)

    def test_initial_value_is_zero(self, font):
        hud = self._hud(font)
        assert hud._suspicion_value == 0
        assert hud._suspicion_surf is not None

    def test_setter_no_op_for_same_int(self, font):
        hud = self._hud(font)
        hud.set_suspicion(5.0)
        surf_before = hud._suspicion_surf
        hud.set_suspicion(5.4)  # samme int → no-op
        assert hud._suspicion_surf is surf_before

    def test_setter_triggers_rebuild_on_int_change(self, font):
        hud = self._hud(font)
        hud.set_suspicion(5.0)
        surf_before = hud._suspicion_surf
        hud.set_suspicion(6.0)
        assert hud._suspicion_surf is not surf_before

    def test_setter_updates_value_across_bands(self, font):
        hud = self._hud(font)
        hud.set_suspicion(10.0)
        assert hud._suspicion_value == 10
        hud.set_suspicion(75.0)
        assert hud._suspicion_value == 75


class TestHudDrawDynamicLayout:
    """Draw skal plassere mistanke-linja under siste synlige linje,
    uavhengig av om bek-linja er skjult."""

    def test_draw_no_crash_with_pitch_hidden(self, font):
        from ui.hud import Hud
        hud = Hud(
            font, "Tortuga", 100, 1,
            pitch_per_day=0, pitch_upkeep=0, pitch_halted=False,
        )
        surf = pygame.Surface((640, 360))
        hud.draw(surf)

    def test_draw_no_crash_with_pitch_visible(self, font):
        from ui.hud import Hud
        hud = Hud(
            font, "Tortuga", 100, 1,
            pitch_per_day=2, pitch_upkeep=8, pitch_halted=False,
        )
        surf = pygame.Surface((640, 360))
        hud.draw(surf)

    def test_draw_no_crash_critical_suspicion(self, font):
        from ui.hud import Hud
        hud = Hud(font, "Tortuga", 100, 1)
        hud.set_suspicion(95.0)
        surf = pygame.Surface((640, 360))
        hud.draw(surf)


# -----------------------------------------------------------------------------
# Save/load bevarer arrested-flagg
# -----------------------------------------------------------------------------


class TestSaveLoadArrested:
    def test_arrested_roundtrip(self, tmp_path):
        from systems import save as save_module
        state = save_module.new_game_state()
        state.arrested = True
        state.player_state.suspicion = 120.0
        path = tmp_path / "arrested.json"
        save_module.save(state, str(path))
        loaded = save_module.load(str(path))
        assert loaded is not None
        assert loaded.arrested is True
        assert loaded.player_state.suspicion == 120.0

    def test_legacy_v5_load_defaults_arrested_false(self, tmp_path):
        """Legacy v5-save mangler `arrested` → default False ved load."""
        import json
        minimal_v5 = {
            "version": 5,
            "player_state": {
                "position_x": 320.0, "gold": 100, "inventory": {},
            },
            "world_state": {
                "current_port": "tortuga",
                "clock": {"day": 1, "seconds_into_day": 0.0, "seconds_per_day": 180.0},
                "ship": {"class_id": "sloop", "name": "Sjarken", "cargo_capacity": 40},
                "voyage": None,
            },
            "economy_state": {
                "markets": {"tortuga": {"commodities": {}, "tick_id": 0}},
                "regimes": {},
                "observed": {},
            },
            "pitch_lake_state": {
                "home_port": "tortuga",
                "production_per_day": 2, "upkeep_per_day": 8,
                "pending_units": 0, "total_produced": 0,
                "last_production_day": 0,
            },
        }
        path = tmp_path / "legacy.json"
        path.write_text(json.dumps(minimal_v5), encoding="utf-8")
        from systems import save as save_module
        loaded = save_module.load(str(path))
        assert loaded is not None
        assert loaded.arrested is False
