# Pitch & Plunder

Et 2D pixel art pirat-spill satt til Karibien på slutten av 1600-tallet.
Krysning mellom *Sid Meier's Pirates!* (PSP), et life-sim, og et skjult
økonomi-krigførings-spill der spilleren manipulerer en lokal børs gjennom
ulovlig piratvirksomhet.

Se `PROSJEKT.md` for full designspesifikasjon, `ASSETS.md` for assets, og
`BENCHMARKS.md` for ytelsesmålinger per fase.

**Status:** Fase 2A ferdig. Se `PHASE_2A_RETROSPECTIVE.md` (og `PHASE_1_RETROSPECTIVE.md` for tidligere fase).

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

Spillet starter i Tortuga-landsbyen. Vandre mellom tavernaen (venstre)
og Børshuset (høyre). Nær Børshuset kan du trykke **E** for å åpne
børsen og handle sukker, rom, tobakk og bek. Dag-natt-syklus med sol
og måne pågår kontinuerlig (3 min reell tid per spilldag); priser
oppdateres én gang per dag ved daggry.

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

- **Landsby-scene** (Tortuga-gate, 1600 px bred verden)
  - 3-lags parallax (himmel + stjerner; gameplay med bygninger og gateplan; tom parallax-forgrunn)
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
- **Økonomi og børs** – 4 varer (sukker, rom, tobakk, bek) med kjøp/salg og 2% spread
- **HUD** øverst venstre: sted, gull (varm), dag (kald)
- **Save-system** med JSON-fil (`saves/savegame.json`), autosave ved QUIT, overlay-åpning/-lukking, scene-bytte

## Fase 2A – hva er lagt til

- **Dag-natt-syklus** (3 min reell tid per spilldag)
  - 6 pre-rendrede himmel-bakgrunner med cross-fade (midnatt, daggry starter, daggry fullført, midt på dag, solnedgang starter, solnedgang fullført)
  - Sol og måne som overlay i verdens-koordinater (1:1 kamera-offset)
    - Månen er statisk forankret over Børshuset (worldx 1350)
    - Solen beveger seg gjennom verden (worldx 1500 øst → 100 vest) med parabolsk y-bane som når horisonten ved sunrise og sunset
  - Fjell-silhuetter og hav okkluderer celestial ved horisont-passering
- **Markedsdybde**
  - Daglig prisoppdatering ved daggry (ikke kontinuerlig drift)
  - 3 regimer per vare (rising/stable/falling) med daglig rotasjons-sannsynlighet
  - Trend-pil i exchange (↑→↓) basert på siste 3 dager
  - Pris-historikk holder siste 14 dager
  - Pris clampet til [base×0.5, base×2.0]
- **Bek-produksjon via Pitch Lake**
  - Passiv 2 bek/dag ved daggry (avg_cost 0.00)
  - Daglig vedlikeholdskostnad 8 gull; stopper produksjon hvis gull < 8
  - HUD-linje viser "Bek: +2/dag (-8 d.)" eller "Bek: ingen drift"
- **Lagerbegrensning** – 40 enheter totalt i inventaret, kjøp blokkeres ved full last
- **Transaksjonsgebyr** – 5 gull flat per kjøp og salg
- **GameClock** – sentral dag-teller og sekunder-i-dag; `seconds_into_day` styrer alle dag-natt-rendringer og daglige events
- **Tester** – pytest-oppsett med 187 grønne tester (GameClock, DayCycle, Market, RegimeManager, PitchLake, save-migrering)
- **Toast-varsler** – generisk ui/toast.py-system (brukes for feilmeldinger ved utilstrekkelig gull)

Startgull: 300 (redusert fra 500 i Fase 1) for å matche den nye friksjonen.

## Benchmark

```bash
python benchmark.py                              # village-scene, 10 s
python benchmark.py --open-exchange              # village med børs åpen
python benchmark.py --scene parallax_test        # kun parallax + kamera
python benchmark.py --duration 30                # lengre måling
```

Resultater loggføres i `BENCHMARKS.md`. Målet er **≥30 FPS stabilt** på
Intel Pentium T4200 / GM45.

| Fase | Lukket | Overlay | % av 33.3 ms-budsjett |
|------|--------|---------|-----------------------|
| Fase 1-slutt | 2.81 ms | 3.90 ms | 8.4% / 11.7% |
| Fase 2A-slutt | 4.61 ms | 6.15 ms | 13.8% / 18.5% |

Regresjonen (+1.8 ms lukket, +2.25 ms overlay) stammer primært fra
SRCALPHA forgrunns-lag for celestial-okklusjon (Commit 7.2, +1.4 ms) og
cross-fade-rendering i dag-natt-syklus (+0.4 ms). Fortsatt ~7× headroom
over 30 FPS-målet. Se `PHASE_2A_RETROSPECTIVE.md` for detaljert
attribusjon og planlagte optimaliseringer.

## Prosjektstruktur

Se `PROSJEKT.md` seksjon 4. Kort fortalt:

- `main.py` – entry point, scene manager, save-loading
- `benchmark.py` – ytelsestest med cProfile
- `constants.py` – palett, taster, ytelseskonstanter, SDL env vars
- `scenes/` – scene-klasser (village, village_renderer, village_buildings, exchange-overlay, parallax_test, parallax_backdrops, base_scene)
- `systems/` – parallax, lighting, particles, economy, save, game_clock, day_cycle, pitch_lake, regime_manager
- `entities/` – player, npc, commodity, celestial
- `ui/` – hud, hint, toast
- `tests/` – pytest-tester (187 grønne per Fase 2A-slutt)
- `assets/fonts/` – Public Pixel (CC0)
- `data/` – JSON-data (commodities, npcs)
- `saves/` – spillerens lagring (i .gitignore)

## Lisens

Koden: eget prosjekt. Tredjepart-assets: se `CREDITS.md`.
