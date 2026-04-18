"""pytest-konfigurasjon.

Legger prosjekt-roten på sys.path slik at tester kan importere moduler
(constants, systems, scenes, etc.) uten å installere prosjektet som pakke.
Dette speiler måten `main.py` og `benchmark.py` kjører på.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
