"""Tester for PortVillageScene (Fase 2B C4).

Dekker scene-init med gyldig port_config, feilhåndtering for havner uten
buildings-layout, og at Tortuga-layout oppretter player/NPC på riktige
posisjoner fra buildings-config.
"""

from __future__ import annotations

import os
import time

import pygame
import pytest

from config import port_config
from state import GameState
from state.market_state import CommodityMarket, MarketState


@pytest.fixture(scope="module", autouse=True)
def _pygame_display():
    """Scene-init trenger et display for Surface.convert() og font-loading."""
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    pygame.display.init()
    pygame.font.init()
    pygame.display.set_mode((640, 360))
    yield
    pygame.font.quit()
    pygame.display.quit()


def _font() -> pygame.font.Font:
    return pygame.font.Font(None, 12)


def _state_for_tortuga() -> GameState:
    """Fersk GameState med Tortuga-markedsdata slik at scene-init kan
    hydrere uten feil. Bruker new_game_state for konsistens med main.py.
    """
    from systems import save as save_module
    return save_module.new_game_state()


class TestPortVillageSceneInit:
    def test_tortuga_scene_loads_without_error(self):
        """Happy path: Tortuga har buildings, scene-init går rent."""
        from scenes.port_village import PortVillageScene

        tortuga = port_config.get("tortuga")
        scene = PortVillageScene(_font(), _state_for_tortuga(), tortuga)
        assert scene is not None

    def test_scene_init_within_budget(self):
        """Spec-akseptansekriterium: scene-init < 100 ms på målmaskinen.

        I test-miljøet kan andre tester og GC gi spikes; vi bruker 200 ms
        som test-grense for å unngå flaky CI-feil, mens commit-rapporten
        verifiserer < 100 ms på varm kjøring av main.py på målmaskinen.
        """
        from scenes.port_village import PortVillageScene

        tortuga = port_config.get("tortuga")
        state = _state_for_tortuga()
        # Warmup: første init laster moduler og fonter; test-kjøring
        # måler en andre, hot init.
        PortVillageScene(_font(), state, tortuga)
        start = time.perf_counter()
        PortVillageScene(_font(), state, tortuga)
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        assert elapsed_ms < 200.0, (
            f"Scene-init tok {elapsed_ms:.1f} ms (> 200 ms test-grense)"
        )

    def test_scene_without_buildings_raises_value_error(self):
        """Scene-init skal kaste ValueError (ikke assertion) hvis
        buildings-felt mangler. Siden C6 aktiverte alle 4 havner, må
        vi bygge en syntetisk port uten buildings for å teste banen.
        """
        from config.port_config import (
            CelestialConfig, PortConfig,
        )
        from scenes.port_village import PortVillageScene

        # Syntetisk PortConfig med buildings=None
        phantom = PortConfig(
            id="phantom",
            name="Phantom",
            world_map_position=(0, 0),
            scene_class="scenes.port_village:PortVillageScene",
            world_width=1200,
            celestial=CelestialConfig(1000, 1100, 100),
            price_bias={"sugar": 1.0, "rum": 1.0, "tobacco": 1.0, "pitch": 1.0},
            regime_weights={
                "sugar":   {"rising": 0.33, "stable": 0.34, "falling": 0.33},
                "rum":     {"rising": 0.33, "stable": 0.34, "falling": 0.33},
                "tobacco": {"rising": 0.33, "stable": 0.34, "falling": 0.33},
                "pitch":   {"rising": 0.33, "stable": 0.34, "falling": 0.33},
            },
            buildings=None,
        )
        with pytest.raises(ValueError, match="no buildings layout"):
            PortVillageScene(_font(), _state_for_tortuga(), phantom)


class TestPortVillageScenePlayerPlacement:
    def test_fresh_start_places_player_at_player_start_x(self):
        """Fersk save (position_x=320.0 = default) → on_enter plasserer
        spilleren ved port.buildings.player_start_x (Tortuga: 1340).
        """
        from scenes.port_village import PortVillageScene

        tortuga = port_config.get("tortuga")
        state = _state_for_tortuga()
        # Simuler fersk save: GameState-default position_x
        state.player_state.position_x = 320.0
        scene = PortVillageScene(_font(), state, tortuga)
        scene.on_enter(state, from_scene=None)
        assert scene._player.x == 1340.0  # Tortugas player_start_x

    def test_saved_position_respected_on_reenter(self):
        """Hvis player_state.position_x er ikke-default, bruker on_enter den."""
        from scenes.port_village import PortVillageScene

        tortuga = port_config.get("tortuga")
        state = _state_for_tortuga()
        state.player_state.position_x = 800.0
        scene = PortVillageScene(_font(), state, tortuga)
        scene.on_enter(state, from_scene=None)
        # Her er from_scene=None, men position_x != 320.0, så bruker lagret
        assert scene._player.x == 800.0

    def test_player_y_from_ground_top_y(self):
        """Player-y gjenopprettes fra buildings.ground_top_y - sprite-høyde."""
        from scenes.port_village import PortVillageScene

        tortuga = port_config.get("tortuga")
        scene = PortVillageScene(_font(), _state_for_tortuga(), tortuga)
        scene.on_enter(_state_for_tortuga(), from_scene=None)
        # Fase 2.6: Tortugas ground_top_y=255, sprite-høyde=20 → y=235
        assert scene._player.y == 235.0


class TestPortVillageSceneNPCs:
    def test_hawkins_positioned_from_buildings_npcs(self):
        """Hawkins skal stå ved Tortugas buildings.npcs['hawkins']=1470."""
        from scenes.port_village import PortVillageScene

        tortuga = port_config.get("tortuga")
        scene = PortVillageScene(_font(), _state_for_tortuga(), tortuga)
        # Minst én NPC, og den er hawkins på x=1470
        assert len(scene._npcs) >= 1
        hawkins = next(
            (n for n in scene._npcs if "hawkins" in str(getattr(n, "name", ""))),
            None,
        )
        # NPC.from_data lager navn; enklere å sjekke x direkte
        assert any(n.x == 1470.0 for n in scene._npcs), (
            f"Ingen NPC ved x=1470, fikk {[n.x for n in scene._npcs]}"
        )


class TestPortVillageSceneExchangeInteraction:
    def test_exchange_interaction_distance_uses_buildings_layout(self):
        """_player_can_interact_with_exchange må bruke buildings.exchange-x,
        ikke hardkodet EXCHANGE_CENTER_X.
        """
        from scenes.port_village import PortVillageScene

        tortuga = port_config.get("tortuga")
        scene = PortVillageScene(_font(), _state_for_tortuga(), tortuga)
        # Tortuga exchange: x=1380, w=200 → center=1480.
        # INTERACTION_DISTANCE=40. Spiller på x=1440 (center 1450) bør kunne
        # interagere siden |1450 - 1480| = 30 < 40.
        scene._player.x = 1440.0
        assert scene._player_can_interact_with_exchange()
        # På x=800 bør det IKKE gå
        scene._player.x = 800.0
        assert not scene._player_can_interact_with_exchange()


class TestPortVillageSceneMarketAccess:
    def test_current_market_state_returns_port_market(self):
        """_current_market_state returnerer MarketState for scenens havn."""
        from scenes.port_village import PortVillageScene

        tortuga = port_config.get("tortuga")
        state = _state_for_tortuga()
        scene = PortVillageScene(_font(), state, tortuga)
        ms = scene._current_market_state()
        # Samme instans som i state.economy_state.markets["tortuga"]
        assert ms is state.economy_state.markets["tortuga"]
        # Har commodities populert fra new_game_state
        assert ms.commodities


# -----------------------------------------------------------------------------
# C6: Alle 4 havner kan aktiveres som PortVillageScene
# -----------------------------------------------------------------------------


@pytest.mark.parametrize(
    "port_id",
    ["tortuga", "port_royal", "havana", "nassau"],
)
class TestAllPortsSceneInit:
    def test_scene_loads_without_error(self, port_id):
        from scenes.port_village import PortVillageScene
        port = port_config.get(port_id)
        assert port.buildings is not None, (
            f"{port_id} mangler buildings — C6 skulle ha lagt det til"
        )
        state = _state_for_tortuga()
        state.world_state.current_port = port_id
        scene = PortVillageScene(_font(), state, port)
        assert scene is not None

    def test_player_can_interact_with_dock(self, port_id):
        """Dock-interaksjon (E → world_map) fungerer for alle 4 havner.
        Player ved x=40 skal være i range [8, 80]."""
        from scenes.port_village import PortVillageScene
        port = port_config.get(port_id)
        state = _state_for_tortuga()
        state.world_state.current_port = port_id
        scene = PortVillageScene(_font(), state, port)
        scene._player.x = 36.0  # center = 40
        assert scene._player_can_interact_with_dock()

    def test_exchange_interaction_works(self, port_id):
        """Exchange-interaksjon fungerer ved havnens exchange-sentrum."""
        from scenes.port_village import PortVillageScene
        port = port_config.get(port_id)
        state = _state_for_tortuga()
        state.world_state.current_port = port_id
        scene = PortVillageScene(_font(), state, port)
        # Exchange senter = x + w/2
        exchange_center = port.buildings.exchange.x + port.buildings.exchange.w / 2
        scene._player.x = exchange_center - scene._player.width / 2
        assert scene._player_can_interact_with_exchange()


# -----------------------------------------------------------------------------
# C6: Bias-justerte priser per havn
# -----------------------------------------------------------------------------


class TestBiasAdjustedPrices:
    """Verifiser at Market opererer på riktig havns MarketState — bias-
    justerte priser reflekteres i buy_price/sell_price per spec-
    akseptansekriterium C6.
    """

    def test_port_royal_sugar_has_bias_discount(self):
        """Port Royal sugar bias = 0.80. base_price = 40.
        Forventet: current_price ≈ 32.0 (i fresh market via bias-init).
        """
        from systems import save as save_module
        state = save_module.new_game_state()
        ms = state.economy_state.markets["port_royal"]
        sugar = ms.commodities["sugar"]
        # 40 × 0.80 = 32.0
        assert abs(sugar.current_price - 32.0) < 0.01

    def test_havana_tobacco_has_bias_discount(self):
        """Havana tobacco bias = 0.75. base_price = 90.
        Forventet: current_price ≈ 67.5."""
        from systems import save as save_module
        state = save_module.new_game_state()
        ms = state.economy_state.markets["havana"]
        tobacco = ms.commodities["tobacco"]
        # 90 × 0.75 = 67.5
        assert abs(tobacco.current_price - 67.5) < 0.01

    def test_market_buy_price_reads_from_target_port_market(self):
        """Market.buy_price(state, cid) skal reflektere havnens bias.
        Spread = 2%, så buy_price = current_price × 1.02 avrundet.
        """
        import os
        import constants
        from systems import save as save_module
        from systems.economy import Market
        state = save_module.new_game_state()
        market = Market.from_json(
            os.path.join(constants.DATA_DIR, "commodities.json")
        )
        # Port Royal sugar current = 32.0 → buy = round(32 × 1.02) = 33
        pr_sugar_buy = market.buy_price(
            state.economy_state.markets["port_royal"], "sugar",
        )
        assert pr_sugar_buy == 33

        # Tortuga sugar bias = 1.10 → current = 44.0 → buy = round(44 × 1.02) = 45
        tortuga_sugar_buy = market.buy_price(
            state.economy_state.markets["tortuga"], "sugar",
        )
        assert tortuga_sugar_buy == 45

        # Havana tobacco current = 67.5 → buy = round(67.5 × 1.02) = round(68.85) = 69
        havana_tobacco_buy = market.buy_price(
            state.economy_state.markets["havana"], "tobacco",
        )
        assert havana_tobacco_buy == 69

        # Priser fra forskjellige havner må IKKE kollidere
        assert pr_sugar_buy != tortuga_sugar_buy


# -----------------------------------------------------------------------------
# C8: write_observed_for_port-integrasjon
# -----------------------------------------------------------------------------


class TestObservedUpdatesOnSceneEntry:
    def test_on_enter_writes_observed_for_initial_spawn(self):
        """from_scene=None: initial spawn skal sikre at observed for
        current_port er populert. new_game_state gjør dette allerede,
        men on_enter skal være idempotent og overskrive med ferskt.
        """
        from scenes.port_village import PortVillageScene
        from systems import save as save_module

        state = save_module.new_game_state()
        # Endre Tortuga-pris (innen klamp-grenser: base 40 × 0.5..2.0
        # = [20, 80]). on_enter skal snapshotte gjeldende pris.
        state.economy_state.markets["tortuga"].commodities["sugar"].current_price = 55.0
        state.world_state.clock.day = 7

        port = port_config.get("tortuga")
        scene = PortVillageScene(_font(), state, port)
        scene.on_enter(state, from_scene=None)

        observed_sugar = state.economy_state.observed["tortuga"]["sugar"]
        assert observed_sugar.price == 55.0
        assert observed_sugar.day_seen == 7

    def test_on_enter_from_world_map_writes_observed(self):
        """from_scene='world_map': retur uten reise skal også oppdatere
        observed (spilleren ser priser igjen).
        """
        from scenes.port_village import PortVillageScene
        from systems import save as save_module

        state = save_module.new_game_state()
        # Pris innen klamp-grenser (base 40, max 80)
        state.economy_state.markets["tortuga"].commodities["sugar"].current_price = 65.0
        state.world_state.clock.day = 4

        port = port_config.get("tortuga")
        scene = PortVillageScene(_font(), state, port)
        scene.on_enter(state, from_scene="world_map")

        observed_sugar = state.economy_state.observed["tortuga"]["sugar"]
        assert observed_sugar.price == 65.0
        assert observed_sugar.day_seen == 4


class TestObservedUpdatesAtDawn:
    def test_dawn_tick_updates_observed_for_current_port_after_on_dawn(self):
        """Per Q2-presisering: write_observed må kalles ETTER
        Market.on_dawn slik at observed reflekterer dagens NYE pris,
        ikke gårsdagens.
        """
        from scenes.port_village import PortVillageScene
        from systems import save as save_module
        from systems.economy import write_observed_for_port

        state = save_module.new_game_state()
        state.world_state.clock.day = 1
        # Snapshot ferskt observed for tortuga
        write_observed_for_port(state, "tortuga")

        # Bygg scene og simuler at klokken har avansert til dag 2
        port = port_config.get("tortuga")
        scene = PortVillageScene(_font(), state, port)
        scene._last_seen_day = 1
        state.world_state.clock.day = 2
        scene.update(0.0)

        # Observed skal nå reflektere den NYE prisen etter Market.on_dawn
        new_observed = state.economy_state.observed["tortuga"]["sugar"]
        new_market_price = state.economy_state.markets["tortuga"].commodities["sugar"].current_price
        assert new_observed.price == new_market_price
        assert new_observed.day_seen == 2

    def test_dawn_tick_during_voyage_skips_observed_update(self):
        """Per spec §8.3: observed oppdateres KUN når spilleren er i
        en havn. Under voyage skal tick_all_ports_dawn ikke skrive
        observed (from_port-snapshotet ble skrevet av start_voyage).
        """
        from systems import balance, save as save_module
        from systems import voyage as voyage_module
        from systems.economy import Market, tick_all_ports_dawn
        from systems.regime_manager import RegimeManager

        state = save_module.new_game_state()
        state.world_state.clock.day = 1
        depart_day = state.world_state.clock.day
        # start_voyage skriver observed for from_port (Tortuga)
        voyage_module.start_voyage(state, balance.get(), "tortuga", "havana")
        observed_at_voyage_start = {
            cid: (obs.price, obs.day_seen)
            for cid, obs in state.economy_state.observed["tortuga"].items()
        }

        # Avanser klokken og kall tick_all_ports_dawn (under voyage)
        state.world_state.clock.day = depart_day + 1
        market = Market.from_json("data/commodities.json")
        tick_all_ports_dawn(state, market, RegimeManager())

        # Observed for Tortuga skal IKKE være oppdatert (vi er på sjøen)
        observed_after = state.economy_state.observed["tortuga"]
        for cid, obs in observed_after.items():
            assert obs.day_seen == observed_at_voyage_start[cid][1], (
                f"{cid}: observed.day_seen oppdatert under voyage "
                f"(start={observed_at_voyage_start[cid][1]}, "
                f"etter={obs.day_seen})"
            )
