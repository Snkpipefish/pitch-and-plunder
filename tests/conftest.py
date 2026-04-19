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
