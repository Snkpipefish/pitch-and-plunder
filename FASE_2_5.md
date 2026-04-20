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

### 1.4 Bystruktur og silhuett-hierarki (fra v1.1)

Etter brukersamtale er fyll-bygninger og bystruktur lagt til scope.
Havnene skal leses som bebodde byer, ikke bare samlinger av
signatur-bygninger.

**Bygningsantall per havn:**

| Havn | Signatur | Fyll-bygninger | Smug | Totalt |
|------|----------|----------------|------|--------|
| Tortuga | 2 | 5-7 | 3 | 7-9 |
| Port Royal | 3 | 6-8 | 4 | 9-11 |
| Havana | 3 | 7-9 | 4-5 | 10-12 |
| Nassau | 3 | 4-6 | 3 | 7-9 |

**Silhuett-hierarki (4 nivåer):**

| Nivå | Høyde (px) | Hvem |
|------|-----------|------|
| Dominant | 96-108 | Taverna, katedral, Customs House-pediment |
| Signatur | 72-84 | Rum-magasin, palass, handelshus, Teach's hus |
| Fyll-høy | 48-60 | Borgerhus, offisersbolig, kloster-annex, boarding-hus |
| Fyll-lav | 32-44 | Fiskerhytter, pakkhus, lappverks-hytter, taverne-cluster |

Hierarkiet lar spilleren lese bygnings-viktighet ved first glance.
Fyll-bygninger må aldri overstige signatur-bygningenes høyde.

**Smug (åpninger mellom bygninger):**

- Bredde 20-40 px, nok til å leses som "åpning"
- Viser havet og ankrede skip gjennom
- Havn-spesifikk karakter:
  - Tortuga: uregelmessige, kan ha tønne eller tauverk i midten
  - Port Royal: ordnede, jevne avstander (britisk urbanisme)
  - Havana: brede arkade-lignende, noen med blomster-plantering
  - Nassau: uregelmessige med palmer eller sand-drift

**Havn-spesifikk stil per bygnings-type:**

Selv bygninger med samme funksjon skal se forskjellige ut per havn.
Tortuga tømmerpakkhus ≠ Port Royal sivilt pakkhus. En spiller skal
kunne se en bygning uten kontekst og vite hvilken havn den er fra.

### 1.5 Vann-refleksjoner (fra v1.2)

Vannet i havnene var per C2.5-6b tom plass. Refleksjoner av
lyskilder gir havnene atmosfærisk dybde og Kingdom Two Crowns-
kvalitet.

**Refleksjoner er egen teknikk**, ikke del av livfullhet eller
animasjon. Leveres i C2.5-8 mellom livfullhet (C2.5-7) og
animasjon (C2.5-9).

**Statisk base + animert bølge:**

C2.5-8 leverer statisk refleksjons-lag (bakes ved scene-init).
C2.5-9 animasjons-pass legger palette-cycling på deler av
refleksjons-striper for bølge-bevegelse.

**Per-havn karakter:**

- Tortuga: varme taverna-refleksjoner, dempet blå-tone
- Port Royal: kald månebane + institusjonelle lys, strekker seg
- Havana: rike lanterne-refleksjoner, katedral-glød på havet
- Nassau: bål-refleksjoner flimrende på sand-hav-kanten

**Teknisk:**

- Refleksjoner bakes som forskjøvet forvrengt palett-variant i
  vann-regionen
- Forvrengning: vertikal strekk, horisontal wobble (bølge-antydning)
- Moderat scope per havn: signatur-dør + alle vindus-lys + måne +
  ankrede skip-master (10-15 refleksjons-striper per havn)
- Ytelse: bakes én gang ved on_enter. Ingen per-frame-kost.

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

Fase 2.5 er 11 commits totalt. De første 7 er landet
(C2.5-1 til C2.5-6b).

### Landet (C2.5-1 til C2.5-6b)

- **C2.5-1** — Tortuga rekvisita-lag (21 nye tester)
- **C2.5-2** — Port Royal signatur-bygninger (18 nye tester)
- **C2.5-3** — Havana signatur-bygninger (11 nye tester)
- **C2.5-4** — Nassau markedsplass + Teach's hus + skipsverft
  (11 nye tester, lys-korrigering EMBER→LANTERN)
- **C2.5-5** — Ankrede skip-silhuetter per havn (17 nye tester)
- **C2.5-6a** — Tortuga + Nassau fyll-bygninger + smug
  (26 nye tester)
- **C2.5-6b** — Port Royal + Havana fyll-bygninger + smug
  (5 nye tester)

#### C2.5-7 — Livfullhet per havn (slitasje + natur + statisk lys)

Moderat omfang, per-havn rekkefølge i én commit.

**Slitasje per havn:**
- Tortuga: forfall i funksjon — mose, rust på jern, slitasje
- Port Royal: pompøs nedslitthet — flassende hvitkalk, salt-ringer
- Havana: rik pato — værtmerkede farger, grønnskyggestreif
- Nassau: organisk villskap — tre som vokser mellom planker

**Natur-elementer:**
- Palmer (1-2 Tortuga / 1-2 Port Royal utkant / 2-3 Havana
  plantet / 3-4 Nassau ukontrollerte)
- Bougainvillea og hengeplanter (Havana-signatur)
- Mose/lav (Port Royal salt-grønn, Tortuga våt-grønn)
- Fugler: måker på master, duer på katedraltårn, pelikan ved
  Nassau-kai
- Ugress mellom brosteiner (Port Royal), mellom sand (Nassau)

**Statisk lys-karakter per havn (bakt inn, ikke dynamisk):**
- Tortuga: klaustrofobisk varme — antydning av silhuetter i vinduer
- Port Royal: kald overvåking — ordnet lys-plassering, kaldt hvitt
  institusjonelt, ett lone-guard varmt vindu
- Havana: katolsk varme — glass-mosaikk-antydning i katedralvinduer,
  lanterne-mønster projisert på palassbakke
- Nassau: flimrende kaos — ulike vindus-farger (gul/rød) i Teach's
  hus, kaotisk belysning

**Smug-innhold (utsatt fra C2.5-6a/6b):**
Natur-innhold i smugene hører hjemme i denne commiten:
- Tortuga: tønner eller tauverk i midten av smug
- Port Royal: ugress langs smug-kanter
- Havana: blomster-plantering i brede arkade-smug
- Nassau: palmer eller sand-drift i midten

#### C2.5-8 — Vann-refleksjoner

Egen teknikk per §1.5. Statisk base, bakes ved scene-init.

**Per havn:**

- Tortuga: taverna-dør + 4 vindus-lys + måne + 3 smugler-skip-master
- Port Royal: Customs House kaldt dør-lys + klokketårn-vindu +
  rum-magasin porter + måne + 3 fregatt-master
- Havana: katedral-dør + palass-balkong lys + arkade-lys +
  fontene-reflekt + måne + 3 galleon-master
- Nassau: Teach's hus vinduer + markedsplass LANTERN + 2 bål +
  måne + 5 pirat-skip-master

**Teknisk:**

- Bakes i foreground-lag under horisontlinjen
- Forskjøvet palett (mørkere versjoner av kilde-lysets farge)
- Vertikal strekk 2-3x kilde-høyde
- Horisontal wobble: enkel sinuskurve-forskyvning per y-linje
- Måne-bane: ett vertikal lys-bånd midt i vannet, bredere enn
  vindus-refleksjoner

**Akseptansekriterier:**

- Alle 4 havner har distinkt refleksjons-karakter
- Refleksjoner forvrenger, ikke speiler perfekt
- Ytelse: bakes ved on_enter, ingen per-frame-kost
- Palett-disiplin: kun master-palett-farger

#### C2.5-9 — Animasjons-pass

Som tidligere planlagt, utvidet med refleksjons-bølger:

- Palette-cycling på bål (Nassau), røyk (Tortuga/Havana), fontene
  (Havana)
- Alpha-pulsering på vinduer alle havner, asynkron 0.85-1.0 over
  2-3 sek
- **Nytt:** palette-cycling på deler av refleksjons-striper for
  bølge-bevegelse (2-3 piksel vertikal forskyvning sykliskt)
- Data-drevet via ports.json `animations`-felt

Maks 25 px palette-cycling per havn (utvidet fra 20 for å
inkludere refleksjons-bølger).

#### C2.5-10 — Brukertest + retrospektiv

Utvidet brukertest med eksplisitt spørsmål om vann-refleksjonene
gir havnene den atmosfæriske dybden som var tiltenkt.

PHASE_2_5_RETROSPECTIVE.md med per-commit-oversikt, brukertest-
observasjoner, teknisk gjeld for Fase 3, oppdatering av
PROSJEKT.md CHANGELOG til v2.5.

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

- **v1.2** (2026-04-20) – Lagt til vann-refleksjoner som egen
  commit (C2.5-8). Ny §1.5, oppdatert §6 commit-plan.
  Fase 2.5 er nå 11 commits totalt. Animasjons-passet utvidet
  med refleksjons-bølge-cycling.
- **v1.1** (2026-04-20) – Utvidet scope etter brukersamtale:
  fyll-bygninger per havn, bystruktur med smug, silhuett-hierarki
  (§1.4), 4 nye commits.
- **v1.0** – Initial Fase 2.5-spesifikasjon.
