"""pytest-konfigurasjon.

Legger prosjekt-roten på sys.path slik at tester kan importere moduler
(constants, systems, scenes, etc.) uten å installere prosjektet som pakke.
Dette speiler måten `main.py` og `benchmark.py` kjører på.

Fra Fase 2B Commit C1a: sørger også for at `systems.balance` er
initialisert for enhver test som leser balance.json. Tester som tester
balance-modulen selv overstyrer med sin egen _reset_for_tests-fixture.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture(autouse=True)
def _ensure_balance_initialized():
    """Initialiser balance-singleton fra prosjektets data/balance.json hvis
    ikke allerede satt. Kjører før hver test (function scope) slik at
    test_balance.py's egen reset-fixture kan tilbakestille singletonen
    mellom tester der.
    """
    from systems import balance

    if not balance.is_initialized():
        balance.init(str(ROOT / "data" / "balance.json"))
    yield


@pytest.fixture(autouse=True)
def _ensure_port_config_initialized():
    """Initialiser port_config-singleton fra prosjektets data/ports.json
    hvis ikke allerede satt. test_port_config.py overstyrer med egen
    reset-fixture for sine isolasjonstester.
    """
    from config import port_config

    if not port_config.is_initialized():
        port_config.init(str(ROOT / "data" / "ports.json"))
    yield


@pytest.fixture(autouse=True)
def _ensure_events_initialized():
    """Fase 3 C3-11: initialiser events-katalogen fra data/events.json
    hvis ikke allerede satt. test_events.py overstyrer med egen reset-
    fixture for isolasjonstester.
    """
    from systems import events

    if not events.is_initialized():
        events.init(str(ROOT / "data" / "events.json"))
    yield


@pytest.fixture(autouse=True)
def _block_default_save_path(monkeypatch, tmp_path):
    """Hindre at tester skriver til prod-save (`saves/savegame.json`).

    Samme klasse bug som C7c-patch-2 fikset for benchmark.py: scene-
    tester som trigger autosave (eks. PortVillageScene._open_world_map
    via E i dock-region) ville ellers overskrive brukerens save under
    pytest-kjøring.

    Wrap `save_module.save` slik at default-path (eller eksplisitt
    prod-path) redirigeres til en tmp_path-fil per test. Tester som
    eksplisitt passer en annen path (f.eks. tmp_path/roundtrip.json
    i test_save_v5_migration) er upåvirket.

    Default-arg-evaluering på save(state, path=constants.SAVE_PATH)
    binder path til prod-stringen ved funksjons-def-tid, så et naivt
    monkeypatch.setattr på constants.SAVE_PATH virker ikke.
    Wrapper-tilnærmingen sjekker path både for None og lik prod-path.
    """
    import constants
    from systems import save as save_module

    prod_path = constants.SAVE_PATH
    test_path = str(tmp_path / "test_savegame.json")
    original_save = save_module.save

    def save_wrapper(state, path=None):
        if path is None or path == prod_path:
            path = test_path
        return original_save(state, path)

    monkeypatch.setattr(save_module, "save", save_wrapper)
    yield
