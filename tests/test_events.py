"""Tester for systems.events — Fase 3 C3-11."""

from __future__ import annotations

import json
import random
from pathlib import Path

import pytest

from state.voyage_state import VoyageState
from systems import events as events_module
from systems import save as save_module


@pytest.fixture
def state():
    """Fersk GameState med events-katalog initialisert via conftest."""
    return save_module.new_game_state()


# -----------------------------------------------------------------------------
# Catalog load
# -----------------------------------------------------------------------------


def test_catalog_loads_all_twelve_events() -> None:
    """C3-13e: 8 voyage + 4 port = 12 totalt (C3-11 hadde 8 totalt)."""
    cat = events_module.get_all()
    assert len(cat) == 12
    # C3-11 første batch
    assert "shipwreck" in cat
    assert "pirates_raid" in cat
    assert "storm" in cat
    assert "lucky_find" in cat
    assert "sickness" in cat
    assert "suspicion_spike" in cat
    assert "lucky_acquaintance" in cat
    assert "drunken_brawl" in cat
    # C3-13e utvidelse
    assert "drivgods" in cat
    assert "vindstille" in cat
    assert "tunfisk_stim" in cat
    assert "kahyttfeber" in cat


def test_event_contexts_partitioned() -> None:
    """C3-13e: 8 voyage + 4 port."""
    cat = events_module.get_all()
    voyage = [e for e in cat.values() if e.context == "voyage"]
    port = [e for e in cat.values() if e.context == "port"]
    assert len(voyage) == 8
    assert len(port) == 4


def test_load_rejects_invalid_context(tmp_path: Path) -> None:
    bad = {
        "version": 1,
        "events": [{"id": "x", "context": "bogus", "weight": 1.0, "effects": []}],
    }
    p = tmp_path / "bad.json"
    p.write_text(json.dumps(bad), encoding="utf-8")
    with pytest.raises(ValueError, match="context"):
        events_module.load_from_path(str(p))


def test_load_rejects_invalid_effect_type(tmp_path: Path) -> None:
    bad = {
        "version": 1,
        "events": [
            {
                "id": "x", "context": "port", "weight": 1.0,
                "effects": [{"type": "does_not_exist", "value": 1.0}],
            }
        ],
    }
    p = tmp_path / "bad.json"
    p.write_text(json.dumps(bad), encoding="utf-8")
    with pytest.raises(ValueError, match="effect.type"):
        events_module.load_from_path(str(p))


# -----------------------------------------------------------------------------
# Sampling
# -----------------------------------------------------------------------------


def test_sample_voyage_event_deterministic_seed(state) -> None:
    rng = random.Random(42)
    result1 = events_module.sample_voyage_event(state, rng)
    rng = random.Random(42)
    result2 = events_module.sample_voyage_event(state, rng)
    assert result1 == result2


def test_sample_skips_when_arrested(state) -> None:
    state.arrested = True
    # 100 samples, alle skal returnere None
    for seed in range(100):
        assert events_module.sample_voyage_event(state, random.Random(seed)) is None
        assert events_module.sample_port_event(state, random.Random(seed)) is None


def test_sample_skips_when_dead(state) -> None:
    state.dead = True
    for seed in range(100):
        assert events_module.sample_voyage_event(state, random.Random(seed)) is None
        assert events_module.sample_port_event(state, random.Random(seed)) is None


def test_voyage_event_samples_voyage_context_only(state) -> None:
    """Over 200 sampel skal kun voyage-events komme ut."""
    voyage_ids = {
        eid for eid, ev in events_module.get_all().items() if ev.context == "voyage"
    }
    for seed in range(200):
        result = events_module.sample_voyage_event(state, random.Random(seed))
        if result is not None:
            assert result in voyage_ids


def test_port_event_samples_port_context_only(state) -> None:
    port_ids = {
        eid for eid, ev in events_module.get_all().items() if ev.context == "port"
    }
    for seed in range(200):
        result = events_module.sample_port_event(state, random.Random(seed))
        if result is not None:
            assert result in port_ids


# -----------------------------------------------------------------------------
# Resolver: data-drevne effekter
# -----------------------------------------------------------------------------


def test_resolve_gold_loss_pct(state) -> None:
    state.player_state.gold = 200
    # pirates_raid: 30% gold_loss_pct
    title, body, died = events_module.resolve(state, "pirates_raid")
    assert state.player_state.gold == 140  # 200 - 60
    assert not died
    assert title == "Ran"


def test_resolve_gold_gain_fixed(state) -> None:
    state.player_state.gold = 100
    title, body, died = events_module.resolve(state, "lucky_find")
    assert state.player_state.gold == 180  # 100 + 80
    assert not died


def test_resolve_suspicion_increase(state) -> None:
    state.player_state.suspicion = 0.0
    _title, _body, died = events_module.resolve(state, "suspicion_spike")
    assert state.player_state.suspicion == 20.0
    assert not died


def test_resolve_voyage_delay_extends_arrival(state) -> None:
    state.world_state.voyage = VoyageState(
        from_port="tortuga", to_port="port_royal",
        depart_day=1, arrival_day=3, progress=0.0,
    )
    _title, _body, died = events_module.resolve(state, "storm")
    assert state.world_state.voyage.arrival_day == 4
    assert not died


def test_resolve_voyage_delay_noop_without_voyage(state) -> None:
    state.world_state.voyage = None
    # Should not crash
    _title, _body, died = events_module.resolve(state, "storm")
    assert not died


def test_resolve_rest_restore(state) -> None:
    state.player_state.rest = 0.1
    _title, _body, died = events_module.resolve(state, "drunken_brawl")
    assert state.player_state.rest == 1.0
    assert not died


# -----------------------------------------------------------------------------
# Resolver: kode-drevne effekter (død)
# -----------------------------------------------------------------------------


def test_shipwreck_gold_always_zero(state) -> None:
    """Uansett død-roll: skipet forliser → gullet tapes."""
    state.player_state.gold = 500
    rng = random.Random(12345)
    _title, _body, _died = events_module.resolve(state, "shipwreck", rng)
    assert state.player_state.gold == 0


def test_shipwreck_deterministic_death_no_death(state) -> None:
    """Seed der uniform(0,100) >= 5 → survives."""
    # random.Random(0).uniform(0, 100) ≈ 84.4 — over 5% threshold
    rng = random.Random(0)
    _title, _body, died = events_module.resolve(state, "shipwreck", rng)
    assert died is False
    assert state.dead is False


def test_shipwreck_death_roll_hits(state) -> None:
    """RNG som returnerer 0.01 → 1.0 (under 5% threshold)."""
    class ForceDeathRng:
        def uniform(self, a: float, b: float) -> float:
            return a  # alltid minimum = 0
        def random(self) -> float:
            return 0.0
        def choice(self, seq):
            return seq[0]
    rng = ForceDeathRng()
    _title, _body, died = events_module.resolve(state, "shipwreck", rng)
    assert died is True
    assert state.dead is True
    assert state.death_cause == "shipwreck"


def test_sickness_death_when_rest_low(state) -> None:
    """rest_spike først (0.4), deretter sickness_death_check (0.2).
    Start rest = 0.3 → etter spike 0.0 → < 0.2 → død."""
    state.player_state.rest = 0.3
    state.player_state.gold = 100
    _title, _body, died = events_module.resolve(state, "sickness")
    assert died is True
    assert state.dead is True
    assert state.death_cause == "sickness"


def test_sickness_survives_when_rest_high(state) -> None:
    """Start rest = 1.0 → etter spike 0.6 → > 0.2 → overlever."""
    state.player_state.rest = 1.0
    state.player_state.gold = 100
    _title, _body, died = events_module.resolve(state, "sickness")
    assert died is False
    assert state.dead is False
    assert state.player_state.rest == pytest.approx(0.6)


def test_death_persists_in_save(state, tmp_path: Path) -> None:
    state.dead = True
    state.death_cause = "shipwreck"
    path = tmp_path / "dead.json"
    assert save_module.save(state, str(path)) is True
    loaded = save_module.load(str(path))
    assert loaded is not None
    assert loaded.dead is True
    assert loaded.death_cause == "shipwreck"


# -----------------------------------------------------------------------------
# Pending event ID flow
# -----------------------------------------------------------------------------


def test_tick_all_ports_dawn_may_set_pending_event(state) -> None:
    """Over mange iterasjoner med ulike seed skal pending_event_id bli
    satt minst én gang (frekvens 0.2 → ikke null).

    Denne testen verifiserer kun at kroken i economy.tick_all_ports_dawn
    er koblet inn; ingen garanti for eksakt seed.
    """
    from systems.economy import Market, tick_all_ports_dawn
    from systems.regime_manager import RegimeManager
    import os
    import constants

    market = Market.from_json(os.path.join(constants.DATA_DIR, "commodities.json"))
    rm = RegimeManager()

    got_event = False
    # Reset pending_event_id mellom runs — vi re-bruker samme state for
    # å akkumulere random chances
    for _ in range(200):
        state.world_state.pending_event_id = None
        tick_all_ports_dawn(state, market, rm)
        if state.world_state.pending_event_id is not None:
            got_event = True
            break
    assert got_event, "200 dawn-ticks ga ingen port-event — sampling-kroken er ikke koblet inn"


def test_voyage_context_skips_port_event_sampling(state) -> None:
    """Når state.world_state.voyage er satt, skal port-event-sampling
    i tick_all_ports_dawn IKKE trigge."""
    from systems.economy import Market, tick_all_ports_dawn
    from systems.regime_manager import RegimeManager
    import os
    import constants

    state.world_state.voyage = VoyageState(
        from_port="tortuga", to_port="port_royal",
        depart_day=1, arrival_day=3, progress=0.0,
    )
    market = Market.from_json(os.path.join(constants.DATA_DIR, "commodities.json"))
    rm = RegimeManager()
    for _ in range(50):
        state.world_state.pending_event_id = None
        tick_all_ports_dawn(state, market, rm)
        assert state.world_state.pending_event_id is None


# -----------------------------------------------------------------------------
# Rotasjons-mekanikk (C3-13e)
# -----------------------------------------------------------------------------


class TestRotationMechanic:
    def test_last_event_id_default_empty(self, state) -> None:
        """Fersk state har tom last_event_id."""
        assert state.world_state.last_event_id == ""

    def test_sample_sets_last_event_id(self, state) -> None:
        """Ved suksessfull sampling oppdateres last_event_id."""
        # Bruk seed som treffer en event (freq=0.2 i default balance)
        # Prøv mange seeds til en treffer.
        for seed in range(200):
            rng = random.Random(seed)
            result = events_module.sample_voyage_event(state, rng)
            if result is not None:
                assert state.world_state.last_event_id == result
                return
        pytest.fail("Ingen voyage-event samplet over 200 seeds")

    def test_filter_excludes_last_event_id(self, state) -> None:
        """Med last_event_id satt skal den IDen aldri returneres
        (så lenge det finnes andre kandidater).

        Merk: sample_voyage_event muterer last_event_id ved suksess,
        så vi reset-er før hvert kall for å holde rotasjonen konstant
        mot "storm" i denne testen.
        """
        results = []
        for seed in range(500):
            state.world_state.last_event_id = "storm"  # reset før hver sample
            rng = random.Random(seed)
            r = events_module.sample_voyage_event(state, rng)
            if r is not None:
                results.append(r)
        assert len(results) > 0, "Forventet noen samples med freq=0.2"
        assert "storm" not in results, (
            f"last_event_id=storm skulle ha blitt filtrert. Fikk {set(results)}"
        )

    def test_fallback_allows_repeat_when_only_candidate(
        self, state, monkeypatch,
    ):
        """Hvis filtrering tømmer kandidat-listen, fallback tillater
        gjentak i stedet for None-retur."""
        # Force kun ett voyage-event i katalogen via patch
        import systems.events as ev_mod
        original_catalog = dict(ev_mod._catalog)
        monkeypatch.setattr(
            ev_mod, "_catalog", {
                "solo": ev_mod.Event(
                    id="solo", context="voyage", weight=1.0,
                    positive=True, title="T", body="B", effects=(),
                ),
            },
        )
        state.world_state.last_event_id = "solo"  # eneste tilgjengelig
        # Kraftig trigger-sannsynlighet: mange seeds bør gi minst én
        # returnerer "solo" tross rotasjon (fallback).
        returned_solo = False
        for seed in range(200):
            rng = random.Random(seed)
            r = events_module.sample_voyage_event(state, rng)
            if r == "solo":
                returned_solo = True
                break
        assert returned_solo, "Fallback skulle tillate gjentak som siste utvei"

    def test_port_and_voyage_share_last_event_id(self, state) -> None:
        """Rotasjonen bruker felles last_event_id — port-event-
        sampling respekterer forbudet satt av tidligere voyage- eller
        port-event. Reset før hvert kall for å holde rotasjonen
        konstant i denne testen."""
        results = []
        for seed in range(500):
            state.world_state.last_event_id = "suspicion_spike"
            rng = random.Random(seed)
            r = events_module.sample_port_event(state, rng)
            if r is not None:
                results.append(r)
        assert "suspicion_spike" not in results, (
            f"port-event-sampling respekterer ikke last_event_id: {set(results)}"
        )

    def test_last_event_id_persists_via_save_load(
        self, state, tmp_path
    ):
        """Save/load bevarer last_event_id."""
        from pathlib import Path
        state.world_state.last_event_id = "drivgods"
        path = tmp_path / "save.json"
        assert save_module.save(state, str(path)) is True
        loaded = save_module.load(str(path))
        assert loaded is not None
        assert loaded.world_state.last_event_id == "drivgods"

    def test_load_legacy_save_defaults_empty(self, tmp_path):
        """Legacy save uten last_event_id-felt defaulter til ""."""
        from pathlib import Path
        minimal = {
            "version": 6,
            "player_state": {
                "position_x": 320.0, "gold": 300,
                "inventory": {
                    "sugar": {"quantity": 0, "avg_cost": 0.0},
                    "rum": {"quantity": 0, "avg_cost": 0.0},
                    "tobacco": {"quantity": 0, "avg_cost": 0.0},
                    "pitch": {"quantity": 0, "avg_cost": 0.0},
                },
            },
            "world_state": {
                "current_port": "tortuga",
                "clock": {"day": 1, "seconds_into_day": 0.0, "seconds_per_day": 180.0},
                "ship": {"class_id": "sloop", "name": "Sjarken", "cargo_capacity": 40},
                "voyage": None,
                # MANGLER: last_event_id
            },
            "economy_state": {"markets": {}, "regimes": {}, "observed": {}},
            "pitch_lake_state": {
                "home_port": "tortuga", "production_per_day": 2,
                "upkeep_per_day": 8, "pending_units": 0,
                "total_produced": 0, "last_production_day": 0,
                "purchased": True,
            },
        }
        path = tmp_path / "legacy.json"
        path.write_text(json.dumps(minimal), encoding="utf-8")
        loaded = save_module.load(str(path))
        assert loaded is not None
        assert loaded.world_state.last_event_id == ""
