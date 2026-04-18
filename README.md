# Pitch & Plunder

Et 2D pixel art pirat-spill satt til Karibien på slutten av 1600-tallet.
Se `PROSJEKT.md` for full designspesifikasjon og `ASSETS.md` for assets.

## Krav

- Python 3.10+
- Linux (primærmål: Mint 21.3), kan også kjøre på andre OS pygame-ce støtter
- pygame-ce 2.5+ (IKKE vanlig `pygame` – Community Edition har API-er vi bruker, bl.a. `Surface.fblits()`)

## Oppsett

```bash
# Klone / gå inn i prosjektmappen
cd pitch-and-plunder

# Lag virtuelt miljø
python3 -m venv venv
source venv/bin/activate         # Linux/macOS
# eller: venv\Scripts\activate   # Windows

# Installer avhengigheter
pip install -r requirements.txt

# Verifiser at pygame-CE er korrekt installert
python -c "import pygame; print('CE:', hasattr(pygame, 'IS_CE'), pygame.version.ver)"
# Forventet output: CE: True 2.5.x
```

Hvis pygame-importen krasjer med SIGILL eller lignende på gammel maskinvare,
prøv:

```bash
pip install --upgrade --force-reinstall pygame-ce
```

## Kjøring

```bash
source venv/bin/activate
python main.py
```

(`main.py` kommer i Commit 2.)

## Kontroller

| Tast | Handling |
|------|----------|
| A / ← | Gå venstre |
| D / → | Gå høyre |
| E | Interagér |
| ESC | Meny / lukk overlay |
| Enter | Bekreft |
| F11 | Fullskjerm |

## Benchmark

```bash
python benchmark.py
```

Kjører en 10-sekunders ytelsestest og skriver resultatet til `BENCHMARKS.md`.
Målet er **≥30 FPS stabilt** på Intel Pentium T4200 / GM45. Se `PROSJEKT.md`
seksjon 0 for ytelsesbudsjett.

## Prosjektstruktur

Se `PROSJEKT.md` seksjon 4. Kort fortalt:

- `main.py` – entry point
- `constants.py` – palett, taster, ytelseskonstanter
- `scenes/` – scene-klasser (village, exchange, …)
- `systems/` – parallax, lys, partikler, økonomi, save
- `entities/` – spiller, NPC, varer
- `ui/` – HUD, menyer
- `assets/` – sprites, fonter, parallax-lag
- `data/` – JSON-data (varer, NPC-er)
- `saves/` – spillerens lagring (ignoreres av git)

## Lisens

Koden: eget prosjekt. Tredjepart-assets: se `CREDITS.md`.
