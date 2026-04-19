"""Tester for gull-håndtering i voyage-systemet (Fase 2B C9).

Dekker:
- voyage.voyage_cost-helper (oppslag + None for ukjent rute)
- start_voyage trekker route.gold ved suksess
- start_voyage returnerer None hvis insufficient gull (ingen mutasjon)
- Eksakt-affordable (gold == cost) lykkes og ender på 0
- Insufficient guard etterlater all state uendret (defensivt mot
  halv-mutering)
"""

from __future__ import annotations

from systems import balance, save as save_module, voyage as voyage_module


# -----------------------------------------------------------------------------
# voyage_cost
# -----------------------------------------------------------------------------


class TestVoyageCost:
    def test_returns_correct_gold_for_known_routes(self):
        bal = balance.get()
        # Per data/balance.json
        assert voyage_module.voyage_cost(bal, "tortuga", "port_royal") == 10
        assert voyage_module.voyage_cost(bal, "tortuga", "havana") == 15
        assert voyage_module.voyage_cost(bal, "havana", "nassau") == 25

    def test_alphabetical_invariant(self):
        bal = balance.get()
        assert (voyage_module.voyage_cost(bal, "tortuga", "havana")
                == voyage_module.voyage_cost(bal, "havana", "tortuga"))

    def test_returns_none_for_unknown_route(self):
        bal = balance.get()
        assert voyage_module.voyage_cost(bal, "atlantis", "tortuga") is None
        assert voyage_module.voyage_cost(bal, "tortuga", "tortuga") is None


# -----------------------------------------------------------------------------
# start_voyage gull-trekking
# -----------------------------------------------------------------------------


class TestStartVoyageGoldDeduction:
    def test_deducts_route_gold_on_success(self):
        state = save_module.new_game_state()
        state.player_state.gold = 100
        bal = balance.get()
        v = voyage_module.start_voyage(state, bal, "tortuga", "port_royal")
        assert v is not None
        # Tortuga→Port Royal koster 10 gull
        assert state.player_state.gold == 90

    def test_returns_none_when_insufficient_gold(self):
        state = save_module.new_game_state()
        state.player_state.gold = 5  # under 10-kost
        bal = balance.get()
        v = voyage_module.start_voyage(state, bal, "tortuga", "port_royal")
        assert v is None
        # INGEN state-mutasjon — alle felter uendret
        assert state.player_state.gold == 5
        assert state.world_state.voyage is None
        assert state.world_state.clock.seconds_per_day == bal.time.seconds_per_day_in_port

    def test_exact_affordable_succeeds_and_ends_at_zero(self):
        state = save_module.new_game_state()
        state.player_state.gold = 10  # nøyaktig kost
        bal = balance.get()
        v = voyage_module.start_voyage(state, bal, "tortuga", "port_royal")
        assert v is not None
        assert state.player_state.gold == 0  # blakk men avgang lykkes

    def test_insufficient_gold_does_not_write_observed(self):
        """Defensivt: hele start_voyage skal være atomisk. Ved
        affordability-feil skal heller ikke from_port observed bli
        snapshotet (selv om det er idempotent og ufarlig — vi vil
        teste at retur-stien er ren).
        """
        state = save_module.new_game_state()
        # Tøm Tortuga-observed for å detektere endringer
        state.economy_state.observed.pop("tortuga", None)
        state.player_state.gold = 0
        bal = balance.get()
        v = voyage_module.start_voyage(state, bal, "tortuga", "havana")
        assert v is None
        assert "tortuga" not in state.economy_state.observed

    def test_unknown_route_does_not_deduct_gold(self):
        state = save_module.new_game_state()
        state.player_state.gold = 1000
        bal = balance.get()
        v = voyage_module.start_voyage(state, bal, "atlantis", "tortuga")
        assert v is None
        assert state.player_state.gold == 1000
