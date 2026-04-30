# Pitch & Plunder

Et 2D pixel art pirat-spill satt til Karibien på slutten av 1600-tallet.
Krysning mellom *Sid Meier's Pirates!* (PSP), et life-sim, og et skjult
økonomi-krigførings-spill der spilleren manipulerer en lokal børs gjennom
ulovlig piratvirksomhet.

Se `PROSJEKT.md` for full designspesifikasjon, `ASSETS.md` for assets, og
`BENCHMARKS.md` for ytelsesmålinger per fase.

**Status:** Fase 3 spillbar (dialoger, rykter, mistanke, sabotasje, tilfeldige hendelser, score-overlay). Se `FASE_3.md` for pågående arbeid og `PHASE_2B_RETROSPECTIVE.md` / `PHASE_2A_RETROSPECTIVE.md` / `PHASE_1_RETROSPECTIVE.md` for tidligere faser.

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
og måne pågår kontinuerlig (3 min reell tid per spilldag i havn,
1¼ min per dag på sjøen); priser oppdateres én gang per dag ved
daggry. Gå til venstre verdens-kant og trykk **E** for å åpne
verdenskartet og seile til Port Royal, Havana eller Nassau — hver
havn har egne priser og regimer som drifter parallelt under reise.

## Kontroller

| Tast | Havn | Verdenskart | Reise-dialog | VoyageScene | Børs-overlay |
|------|------|-------------|--------------|-------------|--------------|
| A / ← | Gå venstre | Naviger vest | – | – | Selg 1 (Shift: 10) |
| D / → | Gå høyre | Naviger øst | – | – | Kjøp 1 (Shift: 10) |
| W / ↑ | – | Naviger nord | – | – | Velg vare opp |
| S / ↓ | – | Naviger sør | – | – | Velg vare ned |
| E | Åpne børs / kart / dialog (taverna, havnekontor) | Bekreft fokus / åpne reise-dialog | Bekreft reise | – | – |
| R | Åpne ryktedialog | – | – | – | – |
| ESC | Pause-meny | Tilbake til havn | Avbryt | – | Lukk overlay |
| Enter | Bekreft | – | – | – | – |
| F11 | Veksle fullskjerm | Veksle fullskjerm | – | Veksle fullskjerm | Veksle fullskjerm |

**Dev-mode** (krever `.devmode`-fil i prosjektrota eller `PITCH_DEV=1`):
| F1 | Teleport til Tortuga |
| F2 | Teleport til Port Royal |
| F3 | Teleport til Havana |
| F4 | Teleport til Nassau |
| F5 | Hot-reload `data/balance.json` |

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

## Fase 2B – hva er lagt til

- **Verdenskart-scene** (640×360 top-down, ingen panning, alle 4 havner synlige)
  - 4 havn-markører: Tortuga (Hispaniola), Port Royal (Jamaica), Havana (Cuba), Nassau (Bahamas)
  - Markør-tilstander: current (varm LANTERN-ring), focused (pulserende), other (kald STONE_LIT), aldri besøkt (dempet FOG)
  - Skip-ikon ved current-port (rent top-down, 4 retninger via 2 unike pre-renderinger + 2 symmetri-flips)
  - Pre-rendrede øy-silhuetter med topp-kant-belysning og horisont-bånd per VISUELL_REFERANSE §8
  - Havn-labels (Public Pixel 8px) i COLOR_MOON_HALO under hver markør
- **Tooltip for fokusert havn** med 4 tilstander:
  - Current: "Du er her" + ferske priser med trend-pil (↑→↓)
  - Fersk observed (≤5 dager): "sist besøkt Dag X (Y d. siden)" + priser med trend
  - Stale observed (>5 dager): rød dagsteller + grå priser + "?" trend
  - Aldri besøkt: "aldri besøkt", ingen pris-rader
- **Fire havner** med funksjonell børs i alle:
  - Per-havn `price_bias` × `base_price` gir strukturell karakter (Port Royal sukker billig, Havana tobakk billig, Nassau bek billig, Tortuga premium på alt)
  - Per-havn `regime_weights` (Markov-overgang sampling) gir tematisk volatilitet
  - Markedet i alle 4 havner tikker parallelt — 16 regime-decisions per dawn uansett hvor spilleren er
- **Aktiv seiling** mellom havner
  - Reise-bekreftelse-dialog viser "Tid: N dager / Kost: X gull"
  - Insufficient gull blokkerer med toast "Trenger X gull"
  - Akselerert klokke under reise (75 sek/dag at sea vs 180 i havn)
  - Skip beveger seg langs lineær bane fra avreise-havn til ankomst
  - Save/load mid-voyage gjenoppretter posisjon deterministisk fra clock-state
  - Avreise-toast ved fersk start ("Avreise mot Port Royal"); ikke ved resume
  - Ankomst-toast og automatisk observed-snapshot ved ankomst
- **Pitch Lake pending-units**
  - Når spilleren er borte fra Tortuga (under reise eller i annen havn): produksjon akkumuleres i `pending_units` (bekken lagres på kaia)
  - Ved ankomst Tortuga: `realize_pending_units` flytter pending → inventar opp til ledig kapasitet ("Hentet N bek fra kaia"-toast)
  - Upkeep trekkes uansett hvor spilleren er
- **Nested GameState v5**: PlayerState / WorldState / EconomyState / PitchLakeState. Migreringskjede fra v1-v4.
- **`data/balance.json` + `data/ports.json`**: alle økonomi-tall og havn-konfig flyttet ut av kode. Hot-reload via F5 i dev-mode.
- **Dev-mode**: `.devmode`-fil eller `PITCH_DEV=1` env-var aktiverer F1-F4 debug-teleport + F5 balance-reload + DEV-markør i HUD.
- **Tester**: 418 grønne (+231 gjennom 2B). Voyage-helpers, save-migrering, marker-states, tooltip-rendering, dialog-flow, gull-trekking — alt dekket.

## Benchmark

```bash
python benchmark.py                              # village-scene, 10 s
python benchmark.py --open-exchange              # village med børs åpen
python benchmark.py --scene world_map            # verdenskart-scene
python benchmark.py --scene voyage               # voyage-scene (auto-bootstrap reise)
python benchmark.py --scene parallax_test        # kun parallax + kamera
python benchmark.py --duration 30                # lengre måling
```

Resultater loggføres i `BENCHMARKS.md`. Målet er **≥30 FPS stabilt** på
Intel Pentium T4200 / GM45.

Benchmark-prosessen monkey-patcher `save_module.save` til no-op før
scene-init, slik at `--open-exchange` (som ellers ville trigget
autosave) ikke kan overskrive `saves/savegame.json` med fersk
GameState()-default. Lagt til etter en C7c-patch-2-bug.

| Fase | Lukket | Overlay | Verdenskart | Voyage |
|------|--------|---------|-------------|--------|
| Fase 1-slutt | 2.81 ms | 3.90 ms | – | – |
| Fase 2A-slutt | 4.61 ms | 6.15 ms | – | – |
| Fase 2B-slutt | 4.87 ms | 6.29 ms | 1.21 ms | 1.25 ms |

Akkumulert 2B-regresjon (+0.26 ms lukket, +0.14 ms overlay) er
moderat. Verdenskart og voyage leverer 4× headroom mot hard grense
(10 ms). Se `PHASE_2B_RETROSPECTIVE.md` for per-commit-historikk.

## Prosjektstruktur

Se `PROSJEKT.md` seksjon 4. Kort fortalt:

- `main.py` – entry point, scene manager, save-loading, dev-mode F5/F1-F4
- `benchmark.py` – ytelsestest med cProfile, autosave-disabled for safety
- `constants.py` – palett, taster, ytelseskonstanter, SDL env vars
- `config/` – `port_config.py` (PortConfig dataclass + ports.json-loader)
- `scenes/` – `port_village`, `port_village_renderer`, `port_buildings`, `exchange`, `world_map`, `world_map_builder`, `voyage`, `parallax_backdrops`, `parallax_test`, `base_scene`
- `systems/` – `balance`, `dev_mode`, `economy`, `save`, `game_clock`, `day_cycle`, `pitch_lake`, `regime_manager`, `voyage`, `parallax`, `lighting`, `particles`, `debug_teleport`
- `state/` – `game_state` (v5 nested), `player_state`, `world_state`, `economy_state`, `pitch_lake_state`, `ship_state`, `voyage_state`, `market_state`, `observed_price`
- `entities/` – `player`, `npc`, `commodity`, `celestial`, `port_marker`, `ship_icon`
- `ui/` – `hud`, `hint`, `toast`, `color_palette`, `world_map_tooltip`
- `tests/` – pytest-tester (418 grønne per Fase 2B-slutt)
- `assets/fonts/` – Public Pixel (CC0)
- `data/` – JSON-data (`commodities.json`, `npcs.json`, `balance.json`, `ports.json`)
- `saves/` – spillerens lagring (i .gitignore)

## Lisens

Koden: eget prosjekt. Tredjepart-assets: se `CREDITS.md`.
