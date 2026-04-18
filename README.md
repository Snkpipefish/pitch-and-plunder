# Pitch & Plunder

Et 2D pixel art pirat-spill satt til Karibien på slutten av 1600-tallet.
Krysning mellom *Sid Meier's Pirates!* (PSP), et life-sim, og et skjult
økonomi-krigførings-spill der spilleren manipulerer en lokal børs gjennom
ulovlig piratvirksomhet.

Se `PROSJEKT.md` for full designspesifikasjon, `ASSETS.md` for assets, og
`BENCHMARKS.md` for ytelsesmålinger per fase.

**Status:** Fase 1 ferdig. Se `PHASE_1_RETROSPECTIVE.md`.

## Krav

- Python 3.10+
- Linux (primærmål: Mint 21.3), kan også kjøre på andre OS pygame-ce støtter
- pygame-ce 2.5+ (IKKE vanlig `pygame` – Community Edition har API-er vi bruker, bl.a. `Surface.fblits()`)

## Oppsett

```bash
cd pitch-and-plunder

python3 -m venv venv
source venv/bin/activate         # Linux/macOS
# eller: venv\Scripts\activate   # Windows

pip install -r requirements.txt

# Verifiser at pygame-CE er korrekt installert
python -c "import pygame; print('CE:', hasattr(pygame, 'IS_CE'), pygame.version.ver)"
# Forventet: CE: True 2.5.x
```

Hvis pygame-importen krasjer med SIGILL eller lignende på gammel maskinvare:

```bash
pip install --upgrade --force-reinstall pygame-ce
```

## Kjøring

```bash
source venv/bin/activate
python main.py
```

Spillet starter i Tortuga-landsbyen om natten. Vandre mellom tavernaen
(venstre) og Børshuset (høyre). Nær Børshuset kan du trykke **E** for å
åpne børsen og handle sukker, rom, tobakk og bek.

## Kontroller

| Tast | Village-scenen | Børs-overlay |
|------|----------------|--------------|
| A / ← | Gå venstre | Selg 1 (Shift: 10) |
| D / → | Gå høyre | Kjøp 1 (Shift: 10) |
| W / ↑ | – | Velg vare opp |
| S / ↓ | – | Velg vare ned |
| E | Åpne børs (nær Børshuset) | – |
| ESC | Avslutt spillet | Lukk overlay |
| Enter | Bekreft | – |
| F11 | Veksle fullskjerm | Veksle fullskjerm |

Musen brukes ikke.

## Fase 1 – hva er inkludert

- **Landsby-scene** (Tortuga-gate om natten, 1600 px bred verden)
  - 3-lags parallax (bakgrunn pre-rendret med himmel, måne, stjerner, øy-silhuetter, sjø; gameplay med bygninger og gateplan; tom forgrunn for Fase 2+)
  - Spiller-karakter med hatt-silhuett som vandrer med A/D
  - NPC Hawkins (statisk) foran Børshuset
  - Tavernaen til venstre (varmt lys bakt inn, 2 vinduer, skilt, åpen dør)
  - Børshuset til høyre (4 søyler, trekantgavl, 3 kalde vinduer)
- **Dynamisk lys** – 3 pre-rendrede radiale gradienter:
  - Svingende lanterne over tavernaens skilt
  - Varm døråpnings-glød ved tavernaen
  - Kald stødig glød fra Børshusets midtvindu
- **Tåke og ildfluer** – 4 + 4 partikler i object pool:
  - Tåke drifter over gata (kald, 30% metning)
  - Ildfluer klynger rundt tavernaen (additive, blinker)
- **Økonomi og børs** – 4 varer som drifter hver 10. sekund:
  - Sukker (base 40, volatility 15%)
  - Rom (base 75, volatility 20%)
  - Tobakk (base 90, volatility 10%)
  - Bek (base 55, volatility 25%)
  - Kjøp/salg-spread 2% hver vei
- **HUD** øverst venstre: sted, gull (varm), dag (kald)
- **Save-system** med JSON-fil (`saves/savegame.json`), autosave ved QUIT, overlay-åpning/-lukking, scene-bytte

## Benchmark

```bash
python benchmark.py                              # village-scene, 10 s
python benchmark.py --open-exchange              # village med børs åpen
python benchmark.py --scene parallax_test        # kun parallax + kamera
python benchmark.py --duration 30                # lengre måling
```

Resultater loggføres i `BENCHMARKS.md`. Målet er **≥30 FPS stabilt** på
Intel Pentium T4200 / GM45. Ved sluttmåling for Fase 1 ligger vi på
~370 FPS compute / 2.8 ms frame time lukket og ~270 FPS / 3.9 ms med
børs-overlay åpent – 8–12× headroom over 30 FPS-målet.

## Prosjektstruktur

Se `PROSJEKT.md` seksjon 4. Kort fortalt:

- `main.py` – entry point, scene manager, save-loading
- `benchmark.py` – ytelsestest med cProfile
- `constants.py` – palett, taster, ytelseskonstanter, SDL env vars
- `scenes/` – scene-klasser (village, exchange-overlay, parallax_test, base_scene)
- `systems/` – parallax, lighting, particles, economy, save
- `entities/` – player, npc, commodity
- `ui/` – hud
- `assets/fonts/` – Public Pixel (CC0)
- `data/` – JSON-data (commodities, npcs)
- `saves/` – spillerens lagring (i .gitignore)

## Lisens

Koden: eget prosjekt. Tredjepart-assets: se `CREDITS.md`.
