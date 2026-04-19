# Pitch & Plunder – Fase 2A retrospektiv

Ferdigstilt: 2026-04-19
Commits: 1–7.2 (18 commits inkludert underversjoner)

## Hva ble bygget

Fase 2A adresserte designmanglene fra Fase 1-retrospektivets gameplay-
observasjon ("markedet er trivielt å utnytte"). Fasen landet én havn med
markedsdybde, dag-natt-syklus, bek-produksjon, lagerbegrensning, og
transaksjonsgebyr — infrastruktur som Fase 2B bygger videre på med
verdenskart og flere havner.

### Commit-oversikt

- **Commit 1 (b02f874) – VillageScene-splitt.** `scenes/village.py` 524 →
  315 linjer. `VillageRenderer` (93 linjer), `village_buildings.py` (222),
  `parallax_backdrops.py` (188, delt med `parallax_test`), `ui/hint.py`
  (36). Ryddet skjev import-avhengighet der produksjons-scenen hentet
  fra test-scenen.
- **Commit 2 (5c7538c) – BaseScene livssyklus-API.** `on_enter(state,
  from_scene)` / `on_exit()` / `on_pause()` / `on_resume()` erstatter
  `fresh_flags`-dict og `make_village`-wrapper i `main.py`. SceneManager
  håndterer scene-bytte uten tilstandsforvirring.
- **Commit 3 (893fe03) – GameClock + v3-migrering.** `systems/game_clock.py`
  med dag-teller og `seconds_into_day`, `progress_fraction()`, tick-basert
  oppdatering. GameState bumpet til v3 med graceful v2-migrering.
- **Commit 3.5 (d7e155d) – pytest-oppsett.** Minimalt test-stillas med
  `conftest.py`, tester for GameClock (9 tester) og save-migrering (4).
  Ikke UI/rendering. Totalt 13 tester grønne.
- **Commit 4 (9fe8c8e) – Lagerbegrensning.** `CARGO_CAPACITY_DEFAULT = 40`
  enheter totalt i inventaret. Kjøp blokkeres ved full last med toast-hint.
- **Commit 5 (14969c2) – Regimer + startgull 300 + sparkline.** Første
  markedsmodell-iterasjon: 3 regimer per vare (rising/stable/falling) med
  random.choice-overgang per dag, sparkline-widget i exchange-overlay.
- **Commit 5.6 (e42598a) – Revidering etter brukertest.** Dokumentasjon av
  refaktoreringsplan. Bruker konstaterte at kontinuerlig drift gjorde
  markedsmanipulasjon meningsløs; sparkline var ikke intuitiv. Kuren: dag-
  natt-syklus + daglig markedstakt + trend-piler.
- **Commit 5A (1780564) – DayCycle-system (infrastruktur).** `systems/day_cycle.py`
  med `DaySnapshot`-dataklasse og stateless `compute_snapshot(clock)`.
  37 nye tester, ingen visuell integrasjon ennå.
- **Commit 5B (59ac24c) – Dag-natt-syklus visuell integrasjon.** 6 pre-
  rendrede bakgrunner (stjerner bakt inn med fraksjons-spesifikk styrke),
  `entities/celestial.py` som overlay (sol/måne-skive med BLEND_RGBA_MULT-
  tinting), cross-fade mellom nærmeste to bakgrunner basert på
  day_fraction. 7-vindus celestial-logikk (moon-fade, gap, sun-fade).
  3-stegs sol-fargekurve. COLOR_SKY_DAY_TOP endret til STONE_LIT for
  monoton daggry-lysning.
- **Commit 5C (cac64f6) – Daglig marked + trend-indikator.**
  `Market.tick()` fjernet. Erstattet med `Market.on_dawn(regimes)` som
  kjøres én gang per dag ved daggry-fase-overgang. Direction (regime) ×
  magnitude (2-4%) + støy (±1%). Price history holder 14 dager. Trend-pil
  (↑→↓) basert på siste 3 dager, erstatter sparkline. SECONDS_PER_DAY bumpet
  fra 60 til 180 (3 min reell tid per spilldag).
- **Commit 5D (ebd5cd3) – Bek base_price 55 → 40.** Prisjustering slik at
  bek blir billigere å kjøpe; passer bedre til senere PitchLake-produksjon
  (2/dag). Clamp ved load-tid for saves utenfor nye grenser.
- **Commit 5E (94d17a1) – Daggry-toast via ui/toast.py.** Generisk
  `Toast`/`ToastQueue` med tidsbasert fade-ut. "Daggry — Dag N"-varsel
  ved dag-skift. *Senere fjernet i 6.1 som redundant; toast-systemet
  beholdt for fremtidige varsler.*
- **Commit 6 (e1af0a2) – Bek-produksjon via PitchLake.** `systems/pitch_lake.py`
  med `PitchLakeState` og `on_new_day`. Passiv produksjon: 2 bek/dag med
  avg_cost 0.00. Full last blokkerer produksjon uten varsling. GameState
  bumpet til v4.
- **Commit 6.1 (8e06f45) – Daglig vedlikeholdskostnad.** "Gratis bek"
  undergravde tension — ingen kostnad = ingen valg. La til
  `PITCH_LAKE_DEFAULT_UPKEEP = 8` gull/dag. Hvis gull < 8 stopper produksjon
  (men upkeep trekkes til gold=0). HUD viser "Bek: +2/dag (-8 d.)" eller
  "Bek: ingen drift" (når produksjonen stopper). Toast fjernet fra daggry.
- **Commit 6.2 (0f04bd6) – Økonomi-konstanter samlet.** Ny seksjon
  "Økonomiske konstanter (under balansering)" i `constants.py` med
  STARTING_GOLD, CARGO_CAPACITY_DEFAULT, TRANSACTION_FEE,
  PITCH_LAKE_DEFAULT_PRODUCTION, PITCH_LAKE_DEFAULT_UPKEEP. Kjent issues-
  seksjon i FASE_2A.md dokumenterer at ekte balansering venter på Fase 2B
  (seilingskostnader, arbitrasje) og Fase 3 (piratinntekter).
- **Commit 7 (da295cb) – Transaksjonsgebyr.** 5 gull flat per kjøp og
  salg, trekkes før varekost/inntekt. Feil-varsel via ToastQueue hvis
  gull ikke dekker gebyr + vare.
- **Commit 7.1 (8ea2710) – Celestial kamera-offset og glatt solnedgang.**
  `Celestial.draw` tar cam_x. Parallax 0.2× (matcher bakgrunn).
  SUN_FADE_OUT_START 0.83 → 0.80 (14 s fade). Sol-y-bane: parabel
  4f(1-f) × SUN_Y_NOON som treffer horisont ved både f=0 og f=1.
- **Commit 7.2 (67e7421) – Celestial verdens-forankring.** `celestial_x`
  representerer nå verdens-x (0 til WORLD_WIDTH). MOON_WORLD_X = 1350
  (statisk over Børshuset), SUN_WORLD_X_DAWN = 1500 (øst),
  SUN_WORLD_X_DUSK = 100 (vest). Ekte 1:1 kamera-offset. Fg-lag (fjell +
  hav) skilt ut fra himmel-backdrop til 6 SRCALPHA-varianter; tegnet
  ETTER celestial slik at sol/måne okkluderes ved horisont-passering.

## Ytelses-tall (målmaskin T4200 / GM45 / 3.8 GB RAM)

Sammenlignet med Fase 1-sluttbenchmark:

| Metrikk | Fase 1-slutt | Fase 2A-slutt | Delta |
|---------|---------------|----------------|-------|
| Frame time lukket (avg) | 2.81 ms | 4.61 ms | +1.80 ms |
| Frame time overlay (avg) | 3.90 ms | 6.15 ms | +2.25 ms |
| % av 33.3 ms-budsjett (lukket) | 8.4% | 13.8% | +5.4 pp |
| % av 33.3 ms-budsjett (overlay) | 11.7% | 18.5% | +6.8 pp |
| Headroom over 30 FPS (lukket) | 11.8× | 7.2× | — |
| Tester | 0 | 187 grønne | — |

Regresjon-attribusjon:

| Kilde | Kostnad | Commit |
|-------|---------|--------|
| SRCALPHA fg-lag (fjell + hav, cross-fade to blits) | +1.4 ms | 7.2 |
| Celestial overlay (BLEND_MULT-tinting per frame) | +0.15 ms | 5B |
| Himmel cross-fade (andre blit med set_alpha) | +0.2 ms | 5B |
| Toast-rendering (font.render ved push) | <0.05 ms | 5E |
| Trend-pil-rendering i overlay | +0.1 ms | 5C |
| Sum rapportert | ~+1.9 ms | — |

Hovedkostnaden er forgrunns-laget for celestial-okklusjon (Commit 7.2).
Alternativ: bake fjell-silhuett som colorkey-transparent surface i stedet
for SRCALPHA (se "Observasjoner for Fase 2B"). Fortsatt godt innenfor
60 FPS-budsjett; 30 FPS-målet er nådd med 7× headroom.

Tester: `pytest` viser 187 grønne tester, 1.40 s totalt. Fordeling:

| Modul | Antall |
|-------|--------|
| `test_day_cycle.py` | 43 |
| `test_market.py` | 28 |
| `test_game_clock.py` | 16 |
| `test_pitch_lake.py` | 12 |
| `test_regime_manager.py` | 11 |
| `test_save.py` | 14 |
| Annet (scene, toast, ui) | 63 |

## Gameplay-observasjoner fra brukertesten

### Commit 5 – Regime-driftet marked (første iterasjon)

Bruker spilletestet 18 minutter og rapporterte:
> "Markedet er for volatilt til at manipulasjon er nødvendig. Jeg tjener
> penger trivielt ved å bare vente – sparkline-indikatoren er tilstrekkelig
> til å se når det er tid for kjøp og salg."

Det kontinuerlige pris-driften (hvert 10. sek) underminerte hele
designpremisset om at markedsmanipulasjon skulle være kjernemekanikken.
Sparkline-widget'en var heller ikke intuitiv.

### Commit 5.6–5E – Ny markedsmodell (daglig takt)

Løsning: pris-endringer én gang per dag ved daggry. Dagen får visuell
syklus (sol/måne, skiftende himmelfarger). Dette gir:
- Tematisk forankring (pirattiden hadde ikke kontinuerlig drift)
- Visuell feedback på tidspassering
- Rom der markedsmanipulasjon blir meningsfylt (prisene oppdateres
  sjelden nok til at en handling kan bevisst påvirke neste daggry)

Brukertest etter Commit 5C:
> "Tempoet føles bra så man vil ut å plante bek eller reise til andre
> havner eller bestikke noen i stedet for å bare sitte på børsen.
> Måtte tenke litt og vente på bra piler. Trend-piler er klare."

Markedsmodellen er nå et meningsfylt fundament for Fase 2B-mekanikker.

### Commit 6 – Bek-produksjon uten kostnad

Første bek-produksjonsiterasjon hadde ingen kostnad: 2 bek/dag, gratis,
uten konsekvens. Bruker påpekte at dette manglet gameplay-tension.

### Commit 6.1 – Daglig vedlikeholdskostnad

Løsning: 8 gull/dag upkeep. Gjør bek-produksjon til et valg (hvis gull
er lavt, kan spilleren miste den tematisk ved å sulte arbeiderne).
Brukeren validerte dette som "riktig friksjon". *Merknad: spesifikke
tall er provisoriske — se Rebalanseringsnotat.*

### Commit 7.2 – Visuell tematisk forankring

Brukertest av 7.1 avdekket at celestial var forankret midt på skjermen:
> "Jeg ønsket å gå til tavern og ikke se månen selv om det er natt."

Dette reflekterte Fase 1-designet der månen var bakt inn i bakgrunnslaget
over Børshuset som institusjonell vokter, mens tavernaen var den varme
fluktmuligheten. Løsningen: celestial_x representerer nå verdens-x, ikke
skjermfraksjon. Månen er statisk over Børshuset (worldx=1350); solen
reiser gjennom verden fra 1500 (øst) til 100 (vest) gjennom dagen.

Brukertest etter 7.2:
> "Månen er forankret over Børshuset, solen beveger seg gjennom verden,
> render-rekkefølgen er korrekt."

## Observasjoner for Fase 2B

1. **SRCALPHA-fg-lag kan optimaliseres til colorkey.**
   Commit 7.2s +1.4 ms regresjon kommer fra per-pixel alpha-blanding
   av et 833×360 SRCALPHA-surface. Fjell-silhuetten og havet er alle
   opake – det er BARE regionen utenfor silhuetten som trenger
   transparens. Løsning: bruk colorkey-transparent surface i stedet.
   Bør gi ~1.2 ms tilbake. Spares til Fase 2B når vi uansett utvider
   fg-systemet med parallax-havn-detaljer.

2. **GameState har mange felter nå – vurder gruppering før Fase 2B.**
   `GameState` er v4 med felter `commodities_state`, `player_x`,
   `inventory_items`, `cargo_capacity`, `regimes`, `clock`, `pitch_lake`.
   Fase 2B legger til havn-liste, skip-tilstand, mannskap. Det kan bli
   15+ felter på ett nivå. Vurder nested-struct `economy_state`,
   `world_state`, `player_state` før migreringen til v5. Ryddigere save-
   fil og lettere å migrere per underdomene.

3. **Constants.py har nå balansering-seksjon – vurder data/balance.json.**
   Seksjonen "Økonomiske konstanter (under balansering)" gjør det klart at
   tallene skal endres. Å flytte dem til `data/balance.json` ville la oss
   iterere uten å restarte spillet (hot-reload ved dev-tast) og gjøre
   A/B-balansering enklere. Spares til vi har flere havner og verdiene
   kan være havn-spesifikke.

4. **Celestial-worldx er hardkodet til Tortugas verden.**
   MOON_WORLD_X = 1350, SUN_WORLD_X_DAWN = 1500, SUN_WORLD_X_DUSK = 100
   er alle spesifikke for Tortuga-verdenens bredde (1600). Når Fase 2B
   legger til flere havner med ulik bredde, må disse bli havn-spesifikke
   eller uttrykkes som fraksjoner av havnens verdens-bredde. Anbefaling:
   flytt til havn-config når havn-systemet designes.

5. **RegimeManager er fortsatt Tortuga-spesifikk.**
   Regimer per vare uten havn-dimensjon. For Fase 2B der flere havner har
   sine egne økonomiske karakterer (sukker-plantasjer gir lav pris i
   Port Royal, høy i Havana), må RegimeManager ha en havn-parameter og
   `GameState.regimes` bli en `dict[port_id, dict[commodity_id, regime]]`.
   Naturlig arkitekturstreff med observasjon 2 (state-gruppering).

## Teknisk gjeld

Kjente mangler og forenklinger ved Fase 2A-avslutning:

- **Sol-stutter under bevegelse.** Brukertest av Commit 5C rapporterte
  "solen hakker bittelitt – hvis det går an å gjøre bevegelsene litt
  smoothere." Årsak sannsynligvis: `celestial_x` oppdateres diskret per
  frame med liten endring (mindre enn 1 px per frame ved sen dag); heltalls-
  konvertering i `int(worldx - cam_x)` rundér stutter. Flagget i
  FASE_2A.md kjent issues; ikke fikset. Løsning kan være sub-pixel-
  rendering av celestial eller forhåndsberegnet bane.
- **MARKET_TICK_INTERVAL_SEC er dead constant.** `Market.tick()` ble
  fjernet i Commit 5C til fordel for `on_dawn()`. Konstanten brukes ikke
  lenger, men ble beholdt i `constants.py` for å dokumentere den gamle
  modellen. Bør fjernes når vi er trygge på at daglig marked er endelig.
- **Exchange overlay-panelet er fortsatt SRCALPHA.** Koster ~1 ms ved
  åpent overlay. Flagget i Fase 1-retrospektivet; ikke adressert. Lav
  prioritet siden overlay bare er synlig når spilleren handler aktivt.
- **Ingen save-migreringssti fra v4 til v5.** Hvis Fase 2B bumper
  save-versjon (sannsynlig med havn-system og skip), må migrerings-koden
  i `systems/save.py` utvides. Nåværende migrering dekker v1→v2→v3→v4,
  mønsteret er klart; implementasjonen bør være triviell.
- **Trend-pil-farger er hardkodet i exchange-overlay.** COLOR_STONE_LIT
  (↑), COLOR_FOG (→), COLOR_EMBER (↓) refereres direkte i tegn-koden.
  Bør flyttes til en egen palett-map for UI-signaler når samme farge-
  logikk brukes flere steder (rykter i Fase 3, hendelser i Fase 5).
- **PitchLakeState.daily_upkeep_cost er ikke havn-spesifikk.** Når Fase 4
  åpner en egen Pitch Lake-scene der spilleren manuelt henter bek fra
  vogner, blir daglig upkeep + passiv produksjon en underlig dobling.
  Planlagt omdesign i Fase 4 (se FASE_2A.md "Fremtidige utvidelser").
- **Ingen regime-synlighet for spiller.** RegimeManager påvirker daglig
  prisutvikling, men spilleren ser ikke regimet eksplisitt. Trend-pilen
  er en avledning; spilleren må utlede regimet fra prisbevegelser over
  tid. Det er bevisst obfuskasjon, men kan være for obskurt – vurder å
  introdusere rykter i Fase 3 som avslører regime-informasjon.
- **Ingen lyd.** Fortsatt ikke initialisert (nedarvet fra Fase 1).

## Rebalanseringsnotat

**Alle økonomiske konstanter i Fase 2A er provisoriske.** Ekte
balansering kan ikke gjøres før:

- Fase 2B introduserer seilingskostnader og flere havner (arbitrasje)
- Fase 3 introduserer piratinntekter og skipsvedlikehold
- Fase 5 introduserer hendelser og markedsmanipulasjon

Forvent minst to større rebalanseringer:
- Etter Fase 2B: når arbitrasje mellom havner er spillbart
- Etter Fase 3: når piratvirksomhet gir alternativ inntekt

Økonomi-relaterte konstanter samlet i `constants.py` under seksjonen
"Økonomiske konstanter (under balansering)":

- `STARTING_GOLD = 300`
- `CARGO_CAPACITY_DEFAULT = 40`
- `TRANSACTION_FEE = 5`
- `PITCH_LAKE_DEFAULT_PRODUCTION = 2`
- `PITCH_LAKE_DEFAULT_UPKEEP = 8`
- `SECONDS_PER_DAY = 180.0`

Commodity base-priser ligger fortsatt i `data/commodities.json` (sukker
40, rom 75, tobakk 90, bek 40).

---

Fase 2A er formelt lukket. Fase 2B-planlegging skjer eksplisitt gjennom
samtale med bruker; ingen kode før den diskusjonen.
