"""Dev-mode-deteksjon (spec §4.5).

To måter å aktivere dev-mode, i prioritert rekkefølge:
1. Fil-flagg `.devmode` i prosjektrota (høyest prioritet)
2. Env-variabel `PITCH_DEV=1`

Brukeren toggler med `touch .devmode` / `rm .devmode`. `.devmode` er i
.gitignore. Dev-mode slår på F5 hot-reload og en grå "DEV"-markør i
HUD-en nederst til høyre.
"""

from __future__ import annotations

import os
from pathlib import Path


#: Prosjekt-rota = forelder til denne filens systems/-mappe.
PROJECT_ROOT = Path(__file__).resolve().parent.parent

DEVMODE_FLAG_NAME = ".devmode"


def is_dev_mode() -> bool:
    """True hvis dev-mode er aktivert via fil-flagg eller env-var."""
    if (PROJECT_ROOT / DEVMODE_FLAG_NAME).exists():
        return True
    return os.environ.get("PITCH_DEV") == "1"
