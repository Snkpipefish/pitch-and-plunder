"""Migrer Y-koordinater i data/ports.json fra 360-høyde til 270-høyde.

Fase 2.6 sub-steg 3-4: skalerer alle vertikale verdier med 270/360 = 0.75.

Felter som migreres (rekursiv traversering):
- "y", "y_top", "y2", "_y" — rene Y-koordinater
- "ground_top_y" — bakke-linje
- Hopper over "h" / "w" / "x" — bredde og X-koordinater er uendret.

NB: dette er en éngangsmigrering. Etter Fase 2.6 lever data/ports.json i
480×270-koordinatrom; eldre ports.json-versjoner kan ikke konsumeres uten
re-migrering.
"""
from __future__ import annotations

import json
import sys

SCALE = 270.0 / 360.0  # 0.75

# Felter med Y-verdi som skal skaleres.
Y_FIELDS = {"y", "y_top", "y2", "ground_top_y"}


def migrate(node):
    if isinstance(node, dict):
        for k, v in list(node.items()):
            if k in Y_FIELDS and isinstance(v, (int, float)):
                node[k] = round(v * SCALE)
            elif k.endswith("_y") and isinstance(v, (int, float)):
                node[k] = round(v * SCALE)
            elif k == "world_map_position":
                # Allerede migrert i sub-steg 2.
                pass
            elif k == "celestial":
                # Verdens-koordinater for sol/måne — ikke Y-relaterte
                # her, men sjekk evt. y-felt under.
                migrate(v)
            else:
                migrate(v)
    elif isinstance(node, list):
        for item in node:
            migrate(item)


def main() -> int:
    path = "data/ports.json"
    with open(path, "r") as f:
        data = json.load(f)

    # Lag en pretty diff-friendly migrert versjon
    migrate(data)

    with open(path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"Skalert Y-koordinater i {path} med faktor {SCALE} (360 -> 270).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
