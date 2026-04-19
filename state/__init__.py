"""Nested GameState-pakke (Fase 2B Commit C1b).

Struktur per FASE_2B.md §2.1:

    GameState
    ├── version: int = 5
    ├── player_state: PlayerState
    │   ├── position_x: float
    │   ├── gold: int
    │   └── inventory: dict[str, InventoryItem]  (avg_cost bevart fra 2A)
    ├── world_state: WorldState
    │   ├── current_port: str
    │   ├── clock: GameClock
    │   ├── ship: ShipState
    │   └── voyage: VoyageState | None
    ├── economy_state: EconomyState
    │   ├── markets: dict[port_id, MarketState]
    │   ├── regimes: dict[port_id, dict[commodity_id, RegimeState]]
    │   └── observed: dict[port_id, dict[commodity_id, ObservedPrice]]
    └── pitch_lake_state: PitchLakeState

Re-eksport av de vanligste klassene for å slippe dype import-paths i
konsumenter.
"""

from state.game_state import GameState
from state.player_state import PlayerState
from state.world_state import WorldState
from state.ship_state import ShipState
from state.voyage_state import VoyageState
from state.economy_state import EconomyState
from state.market_state import CommodityMarket, MarketState
from state.observed_price import ObservedPrice
from state.pitch_lake_state import PitchLakeState

__all__ = [
    "GameState",
    "PlayerState",
    "WorldState",
    "ShipState",
    "VoyageState",
    "EconomyState",
    "MarketState",
    "CommodityMarket",
    "ObservedPrice",
    "PitchLakeState",
]
