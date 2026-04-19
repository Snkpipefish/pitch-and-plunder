# Pitch & Plunder – Fase 2.5: Havn-atmosfære og visuell fordypning

Denne spesifikasjonen bygger på `PROSJEKT.md` (v2.4),
`PHASE_2B_RETROSPECTIVE.md` og `FASE_2B_VISUELL_REFERANSE.md` (v1.2).
Les alle tre før du starter.

---

╔════════════════════════════════════════════════════════════════════╗
║                                                                    ║
║   ARBEIDSREGLER FOR FASE 2.5 — LES FØRST                           ║
║                                                                    ║
║   1. ALL KODE SKRIVES LOKALT i ~/prosjekter/pitch-and-plunder      ║
║      på main-branch. Ingen sandbox, ingen cloud-eksekusjon.        ║
║      Benchmark KJØRES på brukerens T4200-maskin, ikke estimeres.   ║
║                                                                    ║
║   2. STOPP ETTER HVER COMMIT og vent på grønt lys fra brukeren     ║
║      før neste commit starter. Visuelt arbeid krever skjermbilde-  ║
║      verifikasjon — du kan ikke selv se om noe ser riktig ut.      ║
║                                                                    ║
║   3. ARBEID PÅ MAIN-BRANCH. Ingen git worktrees, ingen             ║
║      feature-branches.                                             ║
║                                                                    ║
║   4. DETTE ER EN RENT VISUELL FASE. Ingen ny funksjonalitet.       ║
║      Ingen refactoring av systemer. Ingen endring av data-         ║
║      strukturer. Kun nye sprites, nye bakgrunner, nye rekvisita.   ║
║                                                                    ║
╚════════════════════════════════════════════════════════════════════╝

---

## 0. Kontekst og mål

### Hva Fase 2B leverte

Fire havner med funksjonell børs, verdenskart, aktiv seiling,
observed-pris-modell. Alle systemer fungerer, men stub-havnene
(Port Royal, Havana, Nassau) gjenbruker Tortugas bygnings-layout
uendret per `FASE_2B_VISUELL_REFERANSE.md §7`.

### Hva Fase 2.5 skal levere

Hver havn får unik visuell identitet gjennom signatur-bygninger,
rekvisita, ankrede skip og torg-aktivitet. Tortuga får rekvisita-
lag som løser det vedvarende "liten strek på gaten"-problemet.

**Kjerne:**

- Tortuga: rekvisita-lag mellom taverna og børs
- Port Royal: britisk kolonial, institusjonell kulde
- Havana: spansk kolonial, katolsk varm prakt
- Nassau: pirat-republikk, lovløs varm kaos (ingen børs-bygning,
  erstattes med åpen markedsplass)
- Ankrede skip-silhuetter per havn (tematisk variasjon i antall
  og stil)
- Subtil animasjon (palette-cycling, alpha-pulsering, pre-rendrede
  frame-lister)

### Hva Fase 2.5 IKKE er

- Ingen nye mekanikker
- Ingen NPC-interaksjon eller dialog (Fase 3)
- Ingen fraksjons-flagg (Fase 3 — havner er fortsatt nøytrale)
- Ingen guvernør-wappen, taverne-rykter (Fase 3)
- Ingen sprite-animasjon med object pools (Fase 3)
- Ingen endring av HUD-terminologi — "Nassau Børs — Dag 9" står
- Ingen endring av `ports.json`-logikk utover nye bygnings-felt
- Ingen endring av `scenes/port_village.py`-kode som refererer
  til "børs" eller "exchange"

---

## 1. Designfundament

### 1.1 Per-havn historisk forankring

Hver havn forankres i faktisk 1600-talls Karibien, ikke i fraksjons-
tilhørighet. Dette holder design stabilt uavhengig av Fase 3-valg.

| Havn | Historisk profil | Tone |
|------|------------------|------|
| Tortuga | Smugler-havn nord Hispaniola | Smugler-varm + kald børs (indre kontrast) |
| Port Royal | Britisk Jamaica (1655-1692) | Institusjonell kulde |
| Havana | Spansk Cuba, sølv-flåte-hovedstad | Katolsk varm prakt |
| Nassau | Pirat-republikk, New Providence | Lovløs varm kaos |

### 1.2 Signatur-bygninger per havn (moderat omfang, 2-3 per havn)

Børs-bygningen per havn har ulik arkitektonisk signatur. HUD-teksten
forblir "X Børs — Dag N" (generisk spill-term), men det spilleren
ser varierer.

| Havn | Børs-struktur | Arkitektonisk signatur |
|------|---------------|------------------------|
| Tortuga | Smugler-børshus | Eksisterende (behold), kaldt blått lys |
| Port Royal | Customs House | Kolonnet portal, kolonial orden, hvitkalket |
| Havana | Handelshus | Arkade-fasade, åpen side mot havnen, barokk |
| Nassau | INGEN bygning | Åpen markedsplass (teltduker, vekter, kister) |

### 1.3 Nassaus radikale valg — bevisst fravær

Nassau har *ingen* børs-bygning. Det er ingen dominant bygning i
det hele tatt. Dette er designet, ikke en forkortet leveranse.

Begrunnelse: pirat-republikker hadde ikke institusjonell handel.
Varer ble byttet på stranden eller direkte fra skip til kjøper.
Å gi Nassau en børs-bygning ville være historisk feil og tonalt feil.

Risikoen er at spillere leser Nassau som "halvferdig, mindre designet
enn de andre". Vi holder linjen: fraværet ER signalet. Når spillere
reiser mellom Port Royal (kolonial orden) og Nassau (lovløs kaos),
skal forskjellen være umiddelbar.

---

## 2. Detaljspesifikasjon per havn

### 2.1 Tortuga — rekvisita-lag

**Scope:** ingen nye bygninger. Fyll det tomme rommet mellom taverna
og børshus.

**Elementer:**

a) **Gategulv med tekstur**
   - Erstatt flat gulv-linje med brosteins-mønster
   - Enkelte våte flekker (smugler-havnen regner ofte)
   - Subtilt — bakken dominerer ikke, men er ikke én farge

b) **Lanterne-stolper (2-3 stk)**
   - Plassert langs gaten mellom taverna og børs
   - Hver har svingende glow (bruk eksisterende lanterne-system)
   - Fikser gammelt problem: gaten var mørk mellom de to lyskildene

c) **Markedsboder (2-3 stk)**
   - Silhuetter av presenninger og reisverk
   - Lukket for natten (det er tross alt natt-scene)
   - Antyder dagens aktivitet, ikke interaktive

d) **Stablede varer**
   - Tønner, kurver, tauer nær bodene
   - Pirat-havn-rekvisita

e) **NPC-silhuetter (3 stk, per tema-drevet tetthet)**
   - Én ved en bod
   - Én som står med en annen (gruppering)
   - Én sittende
   - Ingen animasjon, ingen dialog
   - Placeholder-sprites i samme palett som spiller og Hawkins

**Begrensninger:**

- Signatur-bygningene (taverna, børs) forblir visuelle hovedanker.
  Rekvisita skal komplettere, ikke konkurrere.
- Varm/kald-kontrasten skal forsterkes: boder nærmere taverna kan
  ha varmere toner, rekvisita nærmere børs kjøligere.
- Alt pre-rendret, ingen animasjon utenom lanterner og eventuell
  røyk (palette-cycling).

**Rendering-lag (fra bakerst til forrest):**

1. Gategulv (erstatter/utvider eksisterende bakke-lag)
2. Rekvisita-lag (boder, stablede varer) — bak NPC-er
3. NPC-silhuetter — bak lanterne-stolper
4. Lanterne-stolper (stolper under spiller-Z, glow over)

### 2.2 Port Royal — britisk kolonial

**Signatur-bygninger (3 stk):**

1. **Customs House** — erstatter generisk børshus-sprite
   - Kolonnet portal
   - Hvitkalket kolonial-orden
   - Kjølig palett (STONE-familien)

2. **Klokketårn-kirke**
   - Liten men høy, klokke synlig
   - Sender orden-signal (kontrast til Tortugas kaos)

3. **Rum-magasin**
   - Lang, lav bygning
   - Fat synlige i åpne porter
   - Tematisk knytting til rum-bias (0.85)
   - Eneste varme element i ellers kjølig havn

**Rekvisita-lag:**

- Brosteinsgater (tørre og ordnede, ikke våte som Tortuga)
- Jerngjerde-seksjoner
- Kolonial-lamper på jern-stolper (færre enn Tortuga, mer ordnet)
- Stablede fat med britiske merkinger

**NPC-silhuetter (3 stk):**

- Offiser i uniform-form
- Handelsmann med hatt
- Kolonial dame med parasoll

**Ankrede skip:** 3 britiske fregatter, ordnet i formasjon, seilene
pent rullet.

**Tone-palett:** STONE-familien dominerer. Varme kun fra vindus-lys,
ikke fra gate-nivå.

### 2.3 Havana — spansk kolonial, katolsk prakt

**Signatur-bygninger (3 stk):**

1. **Katedralen**
   - To klokketårn (dominerende silhuett)
   - Barokk fasade antydet ved kurvede taklinjer
   - Mest imponerende bygning av alle 4 havner

2. **Guvernørpalass**
   - Bredt med arkade (buegang) langs fronten
   - Spansk kolonial-arkitektur

3. **Handelshus** — erstatter generisk børshus
   - Arkade-fasade (gjenspeiler palasset)
   - Åpen side mot havnen (hvor handel faktisk skjer)
   - Tunge vekter synlige
   - Tematisk knytting til tobakk-bias (0.75)

**Rekvisita-lag:**

- Steinheller (lyse, varme — antyder at solen har scort dem)
- Kirkeportal-detaljer
- Fontene på torget (palette-cycling på vannoverflate — Monkey
  Island-teknikk)
- Hengeplanter eller lave trær ved palasset

**NPC-silhuetter (4 stk, mest befolket):**

- Prest (kappe-silhuett)
- Spansk offiser (morion-hjelm-silhuett)
- Handelsmann i spansk drakt
- Kvinne med mantilla

**Ankrede skip:** 1-2 store spanske galleoner + 1 mindre skip.
Store silhuetter forteller om imperiell rikdom.

**Tone-palett:** Varmest av de fire havnene. LANTERN-familien og
WOOD-familien aktive. Oker og rødt. Ingen kald institusjonell farge.

### 2.4 Nassau — pirat-republikk, lovløs kaos

**Signatur-strukturer (3 stk, én er "ikke-bygning"):**

1. **Åpen markedsplass** — erstatter børs-bygning
   - Teltduker (presenninger på reisverk)
   - Vekter på bord
   - Kister og bytte-stabler
   - E-interaksjon går her, ikke til en bygning

2. **Teach's hus** (eller lignende pirat-leder-residens)
   - Romslig trehus, litt større enn nabobygninger
   - IKKE monumentalt — pirat-demokrati, ikke konge
   - Lappverk-arkitektur: rest-tre fra skipsvrak

3. **Skipsverft i det fri**
   - Halvferdige skipsskrog på stranden
   - Stablede skipsplanker, rep-ruller
   - Dette er Nassaus produksjons-lokalitet

**Rekvisita-lag:**

- Sand-gater (ikke stein)
- Improviserte lanterne-stenger (bambus, skipsmast-rester)
- Bål på gaten (flimrende palette-cycling)
- Stablede tønner og kister med kaotisk ordning — ikke pent
  arrangert
- Tauerier og presenninger i forgrunn

**NPC-silhuetter (2 stk, minst befolket):**

- Barfot sjømann
- Kvinne med barn (antydning til at dette faktisk er bebodd,
  ikke bare ransom-base)

**Ankrede skip:** 4-5 små skip, kaotisk plassert, noen skråstilte
som om de ble forlatt hastig. Mange små forteller om pirat-kaos.

**Tone-palett:** Varm men ustrukturert. LANTERN-familien, men i
kaos. Ingen kald institusjonell farge. Sand i WOOD_LIGHT, bål i
LANTERN_BRIGHT.

---

## 3. Animasjonsteknikker (B2-nivå)

Tre teknikker, alle billige, ingen sprite-animasjons-infrastruktur:

### 3.1 Palette-cycling

Flagg, røyk, bål, vann-overflater. Monkey Island-teknikk
(`surface.set_palette_at(i, new_color)`). Praktisk talt gratis på
små regioner.

Bruk på:
- Tortuga: røyk fra taverna-skorstein
- Havana: vann i fontene, røyk fra katedralens røkelser (valgfritt)
- Nassau: bål-flammer på gaten

Budsjett: maks 20 piksler per havn med palette-cycling.

### 3.2 Alpha-pulsering på lys-kilder

Vindus-lys pulserer mellom 0.85-1.0 alpha over 2-3 sekunder,
asynkront per vindu. Simulerer stearinlys.

Implementering: én ekstra `set_alpha` + blit per vindu per frame.
Forventet kost <0.05 ms per scene.

Bruk på:
- Tortuga: eksisterende taverna-vinduer (allerede implementert i
  Fase 1, verifiser at det fortsatt virker)
- Port Royal: garnisonsvinduer i Customs House
- Havana: katedralvinduer, palass-vinduer
- Nassau: kun taverne-vinduer i Teach's hus (få lyskilder er
  tematisk — lovløs by har ikke mye lys)

### 3.3 Pre-rendrede frame-lister

For elementer som ikke passer palette-cycling eller alpha-pulsering,
men trenger synlig bevegelse: pre-render 3 frames, modulo-teller for
å velge riktig frame.

Bruk på (valgfritt, prioriter ikke over grunnleggende atmosfære):
- Port Royal: klokketårn-skygge (3 vinkler over minutt-sykluser)
- Havana: prest-figurens hender (hvis hendene er spesifikke og
  ikke i skygge)

**Ikke bruk for:**
- NPC-bevegelse — alle NPC-er er STATISKE i Fase 2.5. Sprite-
  animasjon er Fase 3-arbeid.
- Skip-bevegelse — ankrede skip er statiske.

---

## 4. Palett-disiplin

Master-paletten (30 farger, per `PROSJEKT.md §2`) er låst. Ingen
farger utenfor paletten. Ingen nye hex-koder.

Per-havn-vekting av master-paletten:

| Havn | Dominerende familie | Sekundær | Aksent |
|------|---------------------|----------|--------|
| Tortuga | WOOD (mørkt tre) | LANTERN (varme) | STONE (kald børs) |
| Port Royal | STONE (kald stein) | LANTERN (sparsomt) | WOOD (rum-magasin) |
| Havana | LANTERN (varme) | WOOD (moderat) | STONE (minimal) |
| Nassau | WOOD_LIGHT (sand) | LANTERN (varme) | — (ingen kald) |

Tortuga som referansepunkt beholder sin eksisterende balanse.

---

## 5. Tekniske krav

### 5.1 Pre-render ved scene-init

Alle signatur-bygninger, rekvisita-lag og NPC-silhuetter skal
pre-rendres ved scene-init og blittes flatt per frame. Ingen
runtime-generering.

Strategi per port_village-scene:
1. `_bake_background_layers()` ved `on_enter`
2. Bakgrunn + gameplay-lag som pre-rendrede surfaces
3. Per-frame: `fblits` av pre-rendrede surfaces med kamera-offset

### 5.2 Data-struktur-endringer (minimale)

`ports.json` kan utvides med per-havn `buildings`-felt som lister
signatur-bygninger og deres plasseringer. Scene-loading leser
dette ved init.

Ingen endring av:
- `PortConfig`-dataklassen utover nye felt
- `systems/economy.py`
- `state/*.py`
- Save-format (v5 fortsatt)

### 5.3 Ytelse-budsjett

Uendret fra 2B:

| Scene | Mål | Hard grense |
|-------|-----|-------------|
| Port-scene lukket | 4.5-5 ms | 10 ms |
| Port-scene overlay | 6-7 ms | 10 ms |
| Verdenskart-scene | <5 ms | 10 ms |
| VoyageScene | <5 ms | 10 ms |

Hver havn har samme budsjett som Tortuga. Flere rekvisita-elementer
betyr flere blits — pre-render alt sammen til én gameplay-surface
for å holde blit-antall konstant.

### 5.4 Palette-cycling-budsjett

Maks 20 piksler per havn får palette-cycling. Større regioner
(hele hav-tekstur) er forbudt — skaper full-frame re-render som
er for dyrt på GM45.

---

## 6. Commit-plan

### C2.5-1 — Tortuga rekvisita-lag

**Hva:** gategulv, lanterne-stolper, markedsboder, stablede varer,
3 NPC-silhuetter mellom taverna og børs. Røyk fra taverna-skorstein
(palette-cycling).

**Filer:**

- `entities/port_props.py` (ny — rekvisita-sprites)
- `scenes/port_village_renderer.py` (utvid bake-funksjoner)
- `data/ports.json` (Tortuga buildings-felt utvides med props-liste)

**Tester:**

- `test_port_props.py`: props lastes, pre-rendres korrekt,
  plasseringer matcher config
- `test_port_village_scene.py` (utvid): Tortuga-scene inkluderer
  nye elementer, benchmark uendret

**Akseptansekriterier:**

- Tortuga føles befolket, ikke lenger "liten strek på gaten"
- Taverna og børs forblir visuelle hovedanker
- Frame time uendret

### C2.5-2 — Port Royal signatur-bygninger + rekvisita

**Hva:** Customs House (erstatter børshus-sprite), klokketårn-kirke,
rum-magasin. Brosteinsgater, jerngjerder, kolonial-lamper. 3 NPC-
silhuetter.

**Filer:**

- `entities/port_buildings.py` (ny eller utvid eksisterende —
  bygnings-sprites per havn)
- `data/ports.json` (Port Royal buildings-felt)
- `scenes/port_village_renderer.py` (port-spesifikk routing basert
  på `port_config.id`)

**Tester:**

- `test_port_royal_rendering.py` (ny): scene laster med PR-
  spesifikke bygninger, pre-render-surfaces korrekte

**Akseptansekriterier:**

- Port Royal ser institusjonell-kald og britisk ut
- Tydelig distinkt fra Tortuga ved første øyekast
- Customs House erstatter generisk børshus-sprite (HUD sier fortsatt
  "Port Royal Børs")

### C2.5-3 — Havana signatur-bygninger + rekvisita

**Hva:** Katedral, guvernørpalass, handelshus. Steinheller, fontene
(palette-cycling), 4 NPC-silhuetter.

**Filer:** som C2.5-2 men for Havana.

**Akseptansekriterier:**

- Havana ser spansk-barokk ut
- Mest befolket og visuelt rikest
- Varmeste palett av de fire

### C2.5-4 — Nassau markedsplass + rekvisita

**Hva:** Åpen markedsplass (erstatter børs-bygning), Teach's hus,
skipsverft. Sand-gater, improviserte lanterner, bål (palette-cycling),
2 NPC-silhuetter.

**Filer:** som C2.5-2 men for Nassau.

**Akseptansekriterier:**

- Nassau ser lovløs og kaotisk ut
- INGEN dominant bygning (designet)
- Tydelig kontrast mot Port Royals orden

### C2.5-5 — Ankrede skip-silhuetter per havn

**Hva:** skip-silhuetter i havnen for alle 4 havner. Tematisk
variasjon i antall og stil:

- Tortuga: utvid til 3 smugler-skuter
- Port Royal: 3 britiske fregatter, ordnet
- Havana: 1-2 galleoner + 1 mindre, imperiell
- Nassau: 4-5 små, kaotisk

**Filer:**

- `entities/anchored_ship.py` (ny — silhuett-sprites)
- `data/ports.json` (ship-felt per havn: antall, stil, plasseringer)
- `scenes/port_village_renderer.py` (inkluder i bake)

### C2.5-6 — Animasjons-pass

**Hva:** alpha-pulsering på vinduer i alle havner, palette-cycling
på eventuelle flagg, bål for Nassau, røyk for havner som har det.

**Filer:**

- `systems/palette_cycling.py` (ny eller utvid eksisterende lanterne-
  system)
- `scenes/port_village.py` (per-frame cycling-oppdatering)

**Akseptansekriterier:**

- Subtil bevegelse i alle havner
- Frame time uendret
- Ingen distraksjon fra gameplay (effektene er støttende, ikke
  fremtredende)

### C2.5-7 — Brukertest + retrospektiv

**Brukertest-protokoll:**

- Besøk alle 4 havner via debug-teleport (F1-F4)
- Minst 2 minutter i hver (se på detaljer, la palette-cycling
  kjøre)
- Subjektive vurderinger:
  1. Føles hver havn unik ved første øyekast?
  2. Klarer du å identifisere hvilken havn du er i uten å lese
     HUD-teksten?
  3. Er NPC-tettheten tematisk riktig (Havana travel, Nassau glissent)?
  4. Fungerer Nassaus fravær av børs-bygning, eller leses det
     som "ufullstendig"?
  5. Er animasjons-elementene subtile nok, eller distraherer de?

**Retrospektiv:** `PHASE_2_5_RETROSPECTIVE.md` med per-commit-oversikt,
brukertest-observasjoner, teknisk gjeld for Fase 3, oppdatering av
`PROSJEKT.md` CHANGELOG til v2.5.

---

## 7. Verifikasjonsliste for Fase 2.5-avslutning

- `python main.py` starter og kjører stabilt
- Alle 4 havner har unik visuell identitet
- Debug-teleport (F1-F4) besøker alle 4 havner med distinkt uttrykk
- HUD-terminologi uendret ("X Børs — Dag N" overalt)
- Benchmark på målmaskin:
  - Port-scene lukket per havn: <5 ms
  - Port-scene overlay per havn: <7 ms
  - Verdenskart og voyage: uendret
- Alle Fase 2B-tester fortsatt grønne (418+)
- Nye tester for bygnings-rendering per havn
- `PHASE_2_5_RETROSPECTIVE.md` skrevet
- Brukertest-protokoll gjennomført

---

## 8. Teknisk gjeld som videreføres til Fase 3

Forventet gjeld ved 2.5-slutt:

- **NPC-er fortsatt statiske silhuetter.** Fase 3 legger til
  interaktivitet (dialog, fraksjons-rykte).
- **Ingen fraksjons-flagg.** Bygninger er nøytrale designmessig.
  Fase 3 legger til flagg på eksisterende bygninger.
- **Ingen guvernør-wappen, taverne-navn, NPC-navn.** Fase 3-arbeid.
- **Animasjons-systemet er begrenset** til palette-cycling og alpha-
  pulsering. Sprite-animasjon med object pools kommer i Fase 3.
- **HUD-leselighet over lyse dag-faser** (arvet fra 2B C8-observasjon).
  Vurder i Fase 3 eller senere polish-runde.

---

## CHANGELOG

- **v1.0** – Initial Fase 2.5-spesifikasjon (Fase 2.5-planlegging
  gjennom samtale med bruker).
