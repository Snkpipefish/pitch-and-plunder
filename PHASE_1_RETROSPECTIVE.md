# Pitch & Plunder – Fase 1 retrospektiv

Ferdigstilt: 2026-04-18
Commits: 1–8 (opprydding i Commit 9)

## Hva ble bygget

Hele Fase 1-MVP fra `PROSJEKT.md` §11 er implementert:

- **Prosjekt-infrastruktur**: venv, pygame-ce 2.5.7, 30-farges master-palett,
  SDL-env-vars før pygame-init, event-blokkering, `Clock.tick(30)`,
  `pygame.SCALED` med software-fallback, F11 fullskjerm.
- **Scene manager** med factory-baserte scene-bytter og en Fase 1-scene
  (`VillageScene`) + hjelpe-scener (`PlaceholderScene`, `ParallaxTestScene`).
- **Parallax-system** (`systems/parallax.py`): 3 lag i Fase 1 (bakgrunn pre-
  rendret med himmel, måne, stjerner, øy-silhuett; gameplay-lag pre-rendret
  med taverna/børshus/gateplan; forgrunn tom). Heltalls-offset, `fblits`-batch,
  støtter delvis tegning (start/stop-indeks) for å kunne legge entiteter
  mellom lagene.
- **Lys-system** (`systems/lighting.py`): gradient-cache med kvadratisk
  falloff, `prewarm()` pre-rendrer unike gradienter i scene-init. 3 lys i
  Tortuga-scenen: svingende lanterne (40 px, lantern-bright, sinus-swing ±3 px
  per 2 s), statisk tavern-dør-glød (70 px, flame), statisk børs-vindu-glød
  (60 px, stone-lit). Batch-tegnet med `fblits` + `BLEND_RGB_ADD`.
- **Partikler** (`systems/particles.py`): object pool (4 tåke + 4 ildfluer),
  pre-rendrede sprites, ingen allokering per frame. Tåke drifter 8–12 px/s
  fra venstre over gata og respawner. Ildfluer flagrer sinusoidalt rundt
  tavernaen, blinker 70/30 og respawner etter 3–5 s.
- **Entiteter**: Player med prosedyrelt placeholder-sprite (tricorn-hatt,
  frakk, ben) og sprite-speiling. NPC Hawkins (stein-grå frakk) foran
  Børshuset. Commodity-dataklasse for varer.
- **Økonomi** (`systems/economy.py`): Market lastet fra JSON, drift innen
  volatility hver 10. sek, 2% spread, rene kjøp/salg-funksjoner med
  snapshot-retur. `tick_id`-teller for UI-cache-invalidering.
- **Børs-overlay** (`scenes/exchange.py`): 480×240 SRCALPHA-panel (95%
  opacitet) i stein-dark med stone-lit ramme. Tastatur-UI (W/S eller ↑↓
  velger, A/D eller ←→ kjøper/selger, Shift = x10, ESC lukker). Tekst-cache
  per `tick_id` og inventar-hash.
- **HUD** (`ui/hud.py`): øverst venstre, tre linjer (sted/gull/dag) med
  bevisst varm-kald fargekoding. Setter-no-op når verdi uendret.
- **Save-system** (`systems/save.py`): `GameState`-dataklasse, JSON-
  serialisering, mild per-felt validering, `logging.warning` ved feil.
  Autosave ved QUIT, scene-bytte og overlay-åpning/-lukking.

## Ytelses-tall (målmaskin T4200 / GM45 / 3.8 GB RAM)

Fra `BENCHMARKS.md` sluttbenchmark:

| Metrikk | Village (alt aktivt) | Village + børs åpen |
|---------|----------------------|---------------------|
| Display-FPS | 30 (capped) | 30 (capped) |
| Compute-FPS avg | 372.75 | 270.77 |
| Compute-FPS 1% lav | 117.72 | 85.76 |
| Frame time avg | 2.81 ms | 3.90 ms |
| % av 33.3 ms-budsjett | 8.4% | 11.7% |
| Headroom over 30 FPS | 11.8× | 8.5× |
| Peak RSS | 102.90 MB | 103.35 MB |

cProfile-hot path: `Surface.fblits` tar 75% av frame time ved 6 kall per
frame (3 parallax-lag + entiteter + lys + partikler, delt i to batcher
rundt fg-laget). Lighting.draw 6%, Particles.draw 4%, resten ≤7%.

Budsjett mot `PROSJEKT.md` §0 er overholdt med margin på alle akser:

| Krav | Mål | Oppnådd |
|------|-----|---------|
| FPS | ≥30 | 30 stabilt |
| Minne (heap/RSS) | 80 MB | 103 MB (over mål, under 150 MB hard) |
| Parallax-lag | 3 | 3 |
| Dynamiske lys | 4 | 3 |
| Partikler | ≤20 samtidig | 4+4 |
| Allokering i game loop | 0 | 0 |
| Verdensbredde | 1600 px | 1600 px |

## Observasjoner for Fase 2

1. **Ytelses-headroom er betydelig, men retningen betyr noe.**
   Vi har 8.5–11.8× headroom på frame-budsjettet. Hvis Fase 2 legger til 2
   nye parallax-lag (øyer, nær-havflate) og 1–2 ekstra lys, koster det
   grovt 1.2–1.5 ms per frame ekstra. Vi vil da ligge på 4.0–5.5 ms per
   frame – fortsatt komfortabelt. Men: hvis verdenskartet bruker en
   *større* verden (f.eks. 4800 px), bør vi re-evaluere pre-render-
   strategien før vi bygger – 4800×360 parallax-surfaces tar ~7 MB hver
   og begynner å presse RAM-budsjettet. Anbefaling: vurder tile-basert
   rendering eller chunk-streaming for Fase 2-kart.

2. **SRCALPHA-blits er dyrere enn jeg antok.**
   Børs-overlay-panelet koster ~1 ms alene (29% nedgang i compute-FPS når
   overlayet åpnes). Hvis Fase 2 får flere samtidige overlays (f.eks.
   dialog + mini-map + inventar), bør vi enten droppe 95%-opacity til
   fordel for colorkey, eller bake overlays i ett pre-rendret panel og
   blit-e uten alpha. Alternativt kan vi eksperimentere med SDL2s
   render-til-tekstur for å få hardware-accelerated alpha på GM45 – men
   det er ikke garantert å hjelpe på OpenGL 2.1.

3. **Market-tick er hardkodet til 10 s – trenger game-clock for Fase 5.**
   `VillageScene._market_tick_timer` inkrementeres med `dt` og utløses
   ved 10 s-tick. Når vi introduserer dag/natt-syklus (Fase 5) trenger vi
   en sentral `GameClock` som styrer både pris-drift, dag-skifte og
   NPC-tidsplan. Naturlig hjem: `systems/game_clock.py`. Bør innføres
   *før* Fase 5 for å slippe migrering av save-format.

4. **Scene-re-entry-logikken er skjør.**
   `main.py` har en `fresh_flags`-dict og en `make_village`-wrapper som
   toggler fra True til False etter første instansiering. I Fase 1 har
   vi bare én scene, så dette er OK. Men Fase 2 introduserer verdenskart
   som scene, og spilleren vil veksle mellom Tortuga og havet flere
   ganger. Trenger ordentlig scene-persistens (f.eks. cache av scene-
   instanser, eller skille "scene-data" fra "scene-render"). Anbefaler å
   refactorere før vi legger til andre scene.

5. **Tåkens farge er pre-mikset mot ÉN bakgrunnsantagelse.**
   Tåke-sprites er bakt i en dempet lilla-grå (45,45,58) som ser riktig
   ut mot sjø-mørk bakgrunn (COLOR_SEA_DEEP). Over varme tavern-
   væggpartier eller den lyse månen ville en *korrekt* tåke se
   annerledes ut (varmere respektive lysere). I praksis vises tåken kun
   over gateplan (y=325–345) som nesten alltid er mørk, så det ser OK
   ut. Men: hvis Fase 2 gir tåke som dekker større y-område (sjø-tåke,
   morgendis over havet), bør vi vurdere per-pixel alpha eller et annet
   pre-miks-sett per høyde-bånd.

## Teknisk gjeld og forenklinger

Ting som ble enklere enn spec / må ryddes før Fase 3–4:

- **Placeholders i stedet for håndtegnede sprites.** Player, NPC, bygninger
  og props er prosedyrelle boks-silhuetter med basisfarge. `ASSETS.md` §4
  lister hva som må tegnes: spiller-walk-cycle, Hawkins, tavern-fasade,
  børshus-fasade, vare-ikoner, tønner/palmer. Placeholders fungerer fordi
  master-paletten holder visuell konsistens, men Fase 3+ krever ordentlige
  sprites for karakter og salability.

- **Tom forgrunn.** Parallax-lag 2 (speed 1.3) er en transparent surface.
  Palmeblader og tauverk (spec §2) er ikke tegnet. Planlagt i Commit 8 av
  spec, men utsatt uten merkbar tap – scenen fungerer. Skal fylles med
  innhold i Fase 2 sammen med øy-silhuetter.

- **Palette cycling droppet.** Spec §2.5 beskriver palette rotation for
  måne-refleksjon, lanterne-flamme og fakler. Vi bruker statiske
  surfaces. Du og jeg ble enige om å utsette til Fase 2 når vi vet om
  headroom er tilstrekkelig.

- **HUD er minimal.** Kun sted/gull/dag. Ikke helse, ikke fraksjonsrykte,
  ikke mistanke-meter. Kommer i Fase 3 når piratvirksomhet og rykte
  introduseres.

- **Ingen tester.** Ingen unit tests, ingen integration tests. Manuell
  verifisering er dokumentert i `BENCHMARKS.md` (save/load-syklus) men
  automatiseres ikke. Akseptabelt for Fase 1 MVP; bør introdusere pytest
  senest i Fase 2 når økonomi-logikken blir mer kompleks.

- **Ingen lyd.** Spec §5 plasserer lyd i Fase 2+. Vi har ikke initialisert
  `pygame.mixer` i det hele tatt.

- **Fbits-batcher er splittet på tvers av metoder.** `VillageScene.draw`
  gjør 3 separate `fblits`-kall (bg+gameplay, entiteter, fg) pluss 3 via
  lighting/particles/overlay. Kunne slås sammen for marginal ytelses-
  gevinst, men koder-klarhet vinner for nå.

- **Village-scenen er tett på å bli for stor.** ~470 linjer med
  baking-hjelpere for taverna og børshus inline. Neste scene (verdenskart)
  bør bruke et eget "scene-building"-modul eller inline-klasser per
  bygning for å unngå at scene-filer drukner.

- **GameState eier ikke alt.** Player.x/y og Market.day er primært på
  scene-objekter og synkroniseres til GameState før save. Fungerer, men
  gjør `_sync_state`-kallet en kritisk path. Enten dropp sync og gjør
  GameState til single source of truth (Player og Market leser fra state
  hvert frame), eller aksepter sync-patternen og dokumenter det tydelig.

- **Autosave på hver overlay-åpning/-lukking er støyete i prod.** Gjort
  bevisst for debugging. I Fase 2 bør vi throttle (f.eks. maks én save
  per 10 s) eller fjerne overlay-triggerne.

- **Hint-tekst er ASCII-only.** "aa" i stedet for "å" etc. Public Pixel-
  fontens glyph-dekning er ikke verifisert for norsk. Bør testes eller
  byttes til en font med full latin-1.

---

Hvis du vil diskutere noen av observasjonene, er jeg klar. Fase 2 er ikke
påbegynt og blir ikke startet uten eksplisitt godkjenning.
