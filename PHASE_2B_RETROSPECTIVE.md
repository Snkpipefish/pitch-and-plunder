# Pitch & Plunder – Fase 2B retrospektiv

Ferdigstilt: 2026-04-19
Commits: C1a–C10 (16 hovedcommits + 2 patch-commits + dokumentasjons-
commits)

---

## Hva ble bygget

Fase 2B utvidet enkeltspill-økonomi-prototypen fra Fase 2A til et
multi-havn-system med verdenskart, aktiv seiling og observed-pris-
modell. Spillet har nå 4 havner (Tortuga + 3 stub-havner med
funksjonell børs), kart-scene med tooltip-rendering for sist sett
priser, og voyage-scene med akselerert klokke under reise. All
infrastruktur for stale-data-UI og dev-mode hot-reload er på plass.

### Commit-oversikt

- **Commit C1a (36ef2fe) – balance.json + F5 hot-reload.**
  Økonomiske konstanter flyttet fra `constants.py` til
  `data/balance.json`. `systems/balance.py` med singleton + reload().
  Dev-mode-deteksjon via `.devmode`-fil eller `PITCH_DEV=1` env-var.
  F5 i dev-mode hot-reloader balance med toast-bekreftelse. Tre
  hot-reload-kategorier (live / sesjon / nytt-spill) per spec §4.4.
- **Commit C1b (16dbd6d) – Nested GameState v5 + v4→v5-migrering.**
  GameState splittet til PlayerState / WorldState / EconomyState /
  PitchLakeState per spec §2.1. Voyage-state-felt klart for C7.
  Migreringskjede v1→v2→v3→v4→v5 med 7 spec-påkrevde tester for
  v4→v5 (Tortuga-bevaring, ikke-Tortuga-init, observed-snapshot,
  ship-defaults, v3-kjede, round-trip-på-disk).
- **Commit C2 (d6071b0) – PortConfig + ports.json + per-havn
  RegimeManager.** `data/ports.json` med 4 havner (Tortuga, Port
  Royal, Havana, Nassau) inkludert world_map_position, price_bias og
  regime_weights per spec §3.2. `config/port_config.py` singleton
  med `init()`/`get()`-API. RegimeManager utvidet fra
  `dict[cid, Regime]` til `dict[port_id, dict[cid, Regime]]`.
  16 regime-decisions per dawn (4 havner × 4 varer).
- **Commit C3a (7c1def5) – Celestial worldx per havn.** Sol/måne-
  posisjons-konstanter flyttet fra hardkodede `MOON_WORLD_X`/
  `SUN_WORLD_X_*` til `port_config[pid].celestial`. Forberedt for
  multi-havn-bytte. Colorkey-optimaliserings-delen forkastet etter
  mikrobenchmark — se 2A-retrospektiv addendum (a1d449b).
- **Commit C4 (613cf07) – PortVillageScene parameterisert + stateless
  Market.** `scenes/village.py` → `scenes/port_village.py` med
  `port_config`-parameter. Bygnings-plasseringer flyttet til
  `ports.json` `buildings`-felt. Market refaktorert til stateless
  katalog (én instans opererer på alle havners MarketState via
  parameter). Tortuga eneste spillbare i C4 — andre havner får
  layout i C6.
- **Commit C5 (3a16918) – WorldMapScene + havn-markører + round-
  trip.** Verdenskart-scene 640×360 med pre-rendret bakgrunn (4
  fase-varianter cachet ved init). 4 havn-markører via
  `entities/port_marker.py` (current/focused/other states). Skip-
  sprite via `entities/ship_icon.py` (rent top-down per VISUELL_
  REFERANSE §4, 2 unike pre-renderinger + 2 symmetri-flips). E på
  havn-kant-region åpner kart; E på current-port-markør går
  tilbake.
- **Commit C5.1 (6f65de4) – WorldMap visuelle lagrings-mekanismer.**
  Patch etter første C5-skjermbilde. Implementerte VISUELL_
  REFERANSE §8 fire lagringsmekanismer: kontur-belysning (Monkey
  Island), atmosfære-gradient ved horisontlinjen (Kingdom Two
  Crowns), havn-identifikasjon-labels (Pirates!), valgfri
  kyst-skygge (12 px coastal_radius landet på).
- **Commit C6 (94bd26d) – Stub-havner + debug-teleport.** Port
  Royal, Havana, Nassau fikk minimal layout (gjenbruker Tortuga-
  bygnings-design per VISUELL_REFERANSE §7). Funksjonell børs i
  alle 4. Ny `systems/debug_teleport.py`: F1-F4 i dev-mode
  teleporterer til havnene for testing. Inventar og gull bevares.
- **Commit C7a (ebc99fd) – Dawn-refactor + observed-helper.**
  Forberedende refactor for C7b/C7c. To fellesfunksjoner ekstrahert
  til `systems/economy.py`: `tick_all_ports_dawn` (flyttet fra
  PortVillageScene-metode) og `write_observed_for_port` (felles
  observed-snapshot). `save.new_game_state` og `save.load` bruker nå
  helperen for Tortuga-snapshot.
- **Commit C7b (f93da71) – Voyage-helpers + PitchLake pending +
  debug-teleport-rydding.** `systems/voyage.py` med pure helpers:
  `route_key`, `get_route`, `compute_heading`, `compute_progress`
  (deterministisk fra clock-state), `interpolate_position`,
  `start_voyage`, `complete_voyage`. PitchLake.on_new_day deler nå
  i hjemme/borte-grener — produksjon under reise går til
  `pending_units` (bekken lagres på kaia). `realize_pending_units`-
  helper for ankomst. Debug-teleport rydder voyage før teleport.
- **Commit C7c (6dba326) – VoyageScene + reise-dialog + ankomst-
  flyt.** Integrasjon-commit. `scenes/voyage.py` med skip som
  beveger seg langs interpolert bane. `_VoyageConfirmDialog` modal i
  WorldMapScene. PortVillageScene.on_enter med voyage-arrival-
  rituale (observed-snapshot, pending-realisering, toast). main.py
  initial-scene basert på voyage-state. benchmark.py voyage-
  bootstrap.
- **Commit C7c-patch (eb80ebd) – Labels på VoyageScene.** Brukertest
  avdekket at VoyageScene manglet havn-labels. Labels løste også
  perseptuell SEA_MID-dominans (semantisk forankring forhindrer
  geometrisk feillesing). `draw_port_markers_with_labels`-helper
  ekstrahert som felles funksjon for begge kart-scener.
- **Commit C7c-patch-2 (2fe93ab) – Benchmark autosave-safety.**
  Latent bug siden C5/C6: `python benchmark.py --open-exchange`
  trigget autosave med fersk GameState() (gold=0, tomme markeder)
  og overskrev brukerens save. Fix: `_disable_autosave_for_
  benchmark()` monkey-patcher `save_module.save` til no-op før
  scene-kall.
- **Commit C8 (c8d79b7) – ObservedPrice stale-UI + tooltip + UI-
  palett.** ObservedPrice-helpers `days_since` + `is_stale`. Ny
  `ui/color_palette.py` med data-state-mapping (FRESH/STALE/NEVER/
  STALE_AGE). Ny "never_visited"-state i PortMarker (FOG-ring).
  `tick_all_ports_dawn` skriver nå observed for current_port etter
  on_dawn (kun når voyage=None). PortVillageScene.on_enter skriver
  observed på alle scene-inngangs-stier. Ny `ui/world_map_tooltip.
  py` med `build_tooltip_lines` (pure data) + WorldMapTooltip.
  Tooltip 4 tilstander: current / fersk / stale / aldri besøkt.
  Trend-pil for fersk; `?` for stale per spec §2.3.
- **Commit C9 (299a563) – Reise-gull-kost + blokkering + polish.**
  `voyage.voyage_cost` pure helper. `start_voyage` trekker
  `route.gold` ved suksess (atomisk med voyage-state). Defensive
  guard returnerer None ved insufficient gold (ingen state-
  mutasjon). `_VoyageConfirmDialog` viser kost-linje i STONE_LIT.
  WorldMapScene + VoyageScene får ToastQueue. Pre-confirm-toast
  "Trenger {cost} gull" i EMBER ved insufficient. "Avreise mot X"-
  toast på fersk voyage (ikke ved save-resume).
- **Commit C10 (denne) – Endelig benchmark + dokumentasjons-closure.**
  Brukertest-protokollen droppet — provisoriske tall kan ikke
  meningsfullt balanseres før Fase 3-mekanikker gir kontekst.

## Ytelses-tall (målmaskin T4200 / GM45 / 3.8 GB RAM)

Sammenlignet med Fase 2A-sluttbenchmark:

| Metrikk | Fase 2A-slutt | Fase 2B-slutt | Delta |
|---------|---------------|---------------|-------|
| Frame time lukket (median) | 4.61 ms | 4.87 ms | +0.26 ms |
| Frame time overlay (median) | 6.15 ms | 6.29 ms | +0.14 ms |
| Frame time verdenskart-scene | n/a | 1.21 ms | ny baseline |
| Frame time VoyageScene | n/a | 1.25 ms | ny baseline |
| % av 33.3 ms-budsjett (lukket) | 13.8% | 14.6% | +0.8 pp |
| % av 33.3 ms-budsjett (overlay) | 18.5% | 18.9% | +0.4 pp |
| Headroom over 30 FPS (lukket) | 7.2× | 6.8× | — |
| Tester | 187 grønne | 418 grønne | +231 |

Akkumulert regresjon over 18+ commits er moderat (<1 ms på begge
modi). Voyage og verdenskart leverer 4× headroom mot hard grense
(10 ms). Detaljert per-commit-historikk i `BENCHMARKS.md`.

Tester: `pytest` viser 418 grønne tester, 8.46 s totalt. Distribusjon:

| Modul | Antall | Tilkomst |
|-------|--------|----------|
| `test_voyage.py` | 30 | C7b |
| `test_world_map.py` | 35 | C5 + C7c-patch + C8 |
| `test_voyage_scene.py` | 23 | C7c + C9 |
| `test_world_map_tooltip.py` | 11 | C8 |
| `test_voyage_cost.py` | 8 | C9 |
| `test_observed_price.py` | 8 | C8 |
| `test_economy_helpers.py` | 9 | C7a |
| `test_save_v5_migration.py` | 12 | C1b + C2 |
| `test_balance.py` | 11 | C1a |
| `test_dev_mode.py` | 8 | C1a |
| Annet (Fase 2A-arv + utvidelser) | ~263 | — |

## Brukertest-observasjoner

Spec §10-C10 sin formelle brukertest-protokoll (20+ min sammenhengende,
balansering-iterasjoner) ble droppet av samme grunn som 2A-retrospektivet
flagger: ekte balansering krever Fase 3-mekanikker (piratinntekter,
møter, rykter) for å kontekstualisere reise-friksjonen. Observasjoner
samlet under utvikling beholdes.

### SEA_MID-dominans (perseptuell, C7-test)

Bakgrunnens SEA_MID-stripe (108 px lys-blå mellom horisont y=36 og
SEA_DEEP-overgang y=144) oppleves som en sekundær "horisont" ved
første møte med VoyageScene. Øy-silhuetter plassert i denne sonen
(Nassau y=110, Havana y=140) leses som "flytende i en mellom-sone"
i stedet for å være tydelig forankret i hav.

**Status:** Løst i stor grad av havn-labels (C7c-patch). Når labels
identifiserer hver silhuett som et navn-festet sted, slutter spilleren
å lese plasseringen som geometrisk feil. Visuelt symptom forsvinner
med semantisk forankring. C10 polish-vurdering: smalere SEA_MID-stripe,
mørkere SEA_MID-farge, eller større himmel-region — lav prioritet.

### 75 sek/dag seiling-tempo (C7-test)

Brukertest opplevde tempoet som kjedelig — VoyageScene har ingen
interaktivitet (autopilot per spec §7.5), og uten innhold underveis
føles 75 sek/dag (≈ 150 sek for en 2-dagers reise) som dødtid.

**Vurderinger for senere:**
- Kortere tempo (50 eller 40 sek/dag) — enkleste fix
- Ambient-toasts under reise (vær-observasjoner, dagsteller-varsel)
- Dagsteller i HUD som tikker synlig

**Forkastet:** "Skippe"-knapp som lar spilleren hoppe til ankomst.
Bryter spec §7.5 "once committed, go"-prinsippet.

**Fase 3-territorium:** musikk, tilfeldige møter på sjøen, aktiv
seiling-mekanikk.

### Benchmark autosave-regresjon (C7c-patch-2)

Latent bug siden C5/C6: `python benchmark.py --open-exchange` brukte
fersk `GameState()` og trigget autosave via
`PortVillageScene._open_exchange`. Den tomme staten ble skrevet til
prod-save og overskrev brukerens spilltest-progresjon.

**Fix:** `benchmark._disable_autosave_for_benchmark()` monkey-patcher
`save_module.save` til no-op. Universell beskyttelse.

**Lærdom:** dev-verktøy trenger samme test-disiplin som spill-koden.
Benchmark-prosessen er ikke en passiv observatør; den kan trigge
side-effekter som påvirker bruker-data.

### HUD-tekst overlapper med himmel-gradient (C8-test)

HUD-tekst oppe til venstre (sted/gull/dag/bek-status) blander seg
perseptuelt med himmel-bakgrunnen i lyse dag-faser. Tekst kan se
"doblet" ut der den krysser farge-overganger i bakgrunnen.

**Status:** ikke funksjonelt problem, leselig. C10/Fase 3-polish.

**Vurderinger:**
- Subtil tekst-bakgrunn (semi-transparent STONE_DARKEST-rektangel)
  — minst invasiv
- Tekst-outline (1 px mørk kant) — kan se klumpete på 8 px Public
  Pixel
- Tekst-skygge (1 px offset) — mellomtilnærming

Anbefaling: semi-transparent bakgrunns-rektangel med
COLOR_STONE_DARKEST og alpha ~120-140.

### Toast-fragmentering (C9-implementasjons-notat)

Tre scener eier nå hver sin ToastQueue-instans: PortVillageScene
(fra Fase 2A), WorldMapScene (C9 — for blokk-meldinger), VoyageScene
(C9 — for avreise-varsel). Ingen kommunikasjon mellom dem.

**Konsekvenser:**
- Avreise-toast vises på VoyageScene (ikke WorldMapScene som ble
  forlatt) — riktig visningssted, men krevde ekstra ToastQueue-
  instans.
- F5-balance-reload-toast vises kun på scenen som var aktiv ved
  reload; ingen historikk.

**Vurderinger for Fase 3:**
- Singleton-toast-system med global ToastQueue.
- Toast-overlevelse via SceneManager-injection.
- Status quo: per-scene-toasts er enkelt og fungerer; ulempen er
  kun ved sjeldne overgangs-meldinger.

Anbefaling: vurder konsolidering i Fase 3 hvis flere meldings-typer
(vær, regimes, hendelser) kommer til.

## Teknisk gjeld for Fase 3

Samlet fra retrospektiv-observasjoner og spec §12.

### Visuell polish (lav prioritet)

- **SEA_MID-stripe-justering** på verdenskart: smalere stripe, mørkere
  farge, eller større himmel-region. Mindre akutt etter labels.
- **HUD-bakgrunn** for tekst-leselighet over lyse dag-faser. Anbefalt
  semi-transparent STONE_DARKEST-rektangel.
- **Fade-transisjoner** mellom scener (havn ↔ kart ↔ voyage). Spec
  §6.4 nevner 0.3s fade; deferert i C7.

### Arkitektur-polish (vurder-når-relevant)

- **Toast-konsolidering**: 3 ToastQueue-instanser uten kommunikasjon.
  Vurder singleton eller SceneManager-injection når flere meldings-
  typer kommer.
- **Inventory-overlay i VoyageScene**: spec §7.5 antyder at spilleren
  kan se inventar under reise. Deferert i C7c.

### Innhold-mangler (Fase 3-territorium)

- **Stub-havner er tematisk tomme.** Port Royal, Havana, Nassau har
  funksjonell børs men ingen unik atmosfære, signatur-bygninger, eller
  NPC-er. Behandles i Fase 3 når havner får fraksjoner, guvernører og
  taverne-rykter.
- **Ingen skipsvariasjon.** Én sloop-klasse. Fase 3 introduserer
  kapring, brigg, galleoner.
- **Ingen aktiv reise-mekanikk.** VoyageScene er visuell, ikke
  interaktiv. Fase 3 legger til tilfeldige møter på sjøen, "kjedelig
  tempo"-observasjonen får sin reelle løsning her.
- **Ingen regime-synlighet utenom trend-pil** (fra 2A). Ryktesystemet
  i Fase 3 bør gi indirekte regime-avsløringer.

### Nedarvede flagg fra Fase 2A

- **Sol-stutter under bevegelse** (sub-pixel celestial-rendering).
  Ikke adressert i 2B.
- **Exchange overlay fortsatt SRCALPHA.** ~1 ms ved åpent overlay.
  Lav prioritet.
- **Trend-pil-farger** delvis flyttet til `ui/color_palette.py` i C8,
  men exchange-overlay rendrer fortsatt direkte. Konsolider ved
  neste UI-rydding.
- **Ingen lyd.** Fortsatt ikke initialisert.

## Rebalanseringsnotat

**Alle økonomiske tall i Fase 2B er provisoriske.** Brukertest-
protokollen ble droppet av samme grunn som 2A-retrospektivet flagger:
ekte balansering kan ikke gjøres før Fase 3-mekanikker gir kontekst:

- Piratinntekter (alternativ inntektsstrøm til arbitrasje)
- Tilfeldige møter på sjøen (ekte reise-friksjon utover gull/tid)
- Skipsvedlikehold (kontinuerlig kost-press)
- Rykte-system (informasjons-asymmetri som kan kalibrere stale-
  threshold)
- Hendelser og markedsmanipulasjon (volatilitets-kontekst)

**Balansering utsatt til Fase 3 eller senere.** Endringer kan gjøres
ad-hoc via `data/balance.json` og `data/ports.json` + F5 hot-reload
når behov dukker opp under videre utvikling. Ingen formell iterasjon
nå.

Provisoriske tall som forventes justert:

| Konstant | Sted | Verdi | Forventet endring i Fase 3+ |
|----------|------|-------|------------------------------|
| `seconds_per_day_at_sea` | balance.json | 75.0 | sannsynlig 50 eller 40 |
| `seconds_per_day_in_port` | balance.json | 180.0 | uendret hvis tempo-bytte |
| `travel.routes.*.gold` | balance.json | 10-25 | kalibreres mot piratinntekt |
| `travel.routes.*.days` | balance.json | 2-5 | kalibreres mot møte-tetthet |
| `pitch_lake.upkeep_per_day` | balance.json | 8 | mot vedlikeholdskost |
| `regimes.drift_pct_*` | balance.json | ±2-4% | kalibreres mot manipulasjon |
| `observed.stale_threshold_days` | balance.json | 5 | mot rykte-friskhet |
| `price_bias` per havn | ports.json | 0.75-1.15 | mot fraksjons-effekter |
| `regime_weights` per havn | ports.json | varierer | mot guvernør-politikk |

Kjørbare hot-reload-iterasjoner: alle `balance.json`-felt i live-
kategori (transaction_fee, upkeep_per_day, production_per_day, drift_
pct_*, noise_pct, travel.routes.*, stale_threshold_days) gjelder
umiddelbart ved F5. `seconds_per_day_*` gjelder fra neste dawn.
Newgame-only-felt (starting_gold, ship_starting_cargo_capacity)
krever ny save.

Forvent minst tre større rebalanseringer:
- Underveis i Fase 3: når piratvirksomhet gir alternativ inntekt
- Etter Fase 3: full re-pass på arbitrasje vs piratinntekt
- Etter Fase 5: når hendelser og markedsmanipulasjon lander

Det er bevisst at C10 ikke prøver å låse tall som ikke kan valideres
mot manglende mekanikker — å iterere på reise-kost uten piratinntekt
ville gi feil signal til design.

---

Fase 2B er formelt lukket. Fase 3-planlegging skjer gjennom samtale
med bruker; ingen kode før den diskusjonen.
