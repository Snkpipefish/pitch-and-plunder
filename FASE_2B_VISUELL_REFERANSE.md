# Fase 2B — Visuell referanse for verdenskart og havn-assets

Sidefil til `FASE_2B.md`. Dokumenterer visuelle valg som binder
verdenskart-scenen (C5) og havn-markørene til master-paletten fra
`PROSJEKT.md §2` og den etablerte Tortuga-signaturen fra 2A.

Hensikt: sikre at når WorldMapScene og havn-assets bygges i C5+, er
palett-valg og inspirasjons-vekting eksplisitte slik at vi ikke
drifter bort fra den visuelle identiteten spillet har etablert i Fase 1
og 2A.

---

## 1. Verdenskart-estetikk — palett-forankring

Top-down-perspektivet endrer hvordan master-paletten brukes sammenlignet
med sideview-scenene. I Tortuga-havn-scenen er himmelen ~2/3 av
bildet og havet en smal stripe; på verdenskartet er det omvendt.

**Palett-vekting på kartet:**

- **Hav (dominerer ~70% av flatet):** `COLOR_SEA_DEEP` (`#0f1829`) som
  hovedtone, `COLOR_SEA_MID` (`#1e2a4a`) for varige bølgemønstre, og
  `COLOR_SEA_LIGHT` (`#2a3a5e`) som fremhevet "sjøgress"- eller
  strøm-indikasjon. `COLOR_SEA_HIGHLIGHT` (`#4a5a8a`) reserveres for
  sol-refleksjoner — bare synlige om dagen, forsvinner om natten.
- **Øy-silhuetter:** `COLOR_STONE_DARKEST` (`#151a2a`) som hovedtone.
  Tematisk valg: silhuettene skal føles som "skygge på hav", ikke som
  distinkte landmasser. Ingen indre detalj-tekstur. Kanter blir derfor
  tydelige mot SEA_DEEP (kontrast 3.5:1 mot bakgrunn).
- **Himmel (topp 10–15% av skjermen):** gradient fra
  `COLOR_SKY_HORIZON` (`#2d3561`) ned mot SEA_DEEP. Topp av skjermen
  bruker `COLOR_SKY_MID` for kveld/natt-faser. Dag-fasen løfter topp
  til `COLOR_SKY_DAY_HORIZON` (`#8ba8d6`).
- **UI-lag (havnemarkører, skip, tooltip):** varme farger fra
  LANTERN-familien dominerer — disse må "lyse opp" mot den kalde
  havbakgrunnen.

**Regel:** ingen farger utenfor master-paletten. Ingen gråtoner via
fargemiks. Hvis en farge ikke finnes i palett-listen, eksisterer den
ikke.

---

## 2. Inspirasjonskilder — eksplisitt vekting

Spec-referanser fra `PROSJEKT.md §15`: Kingdom: Two Crowns, Sid Meier's
Pirates! PSP (2005), Monkey Island VGA, Mark Ferraris color cycling.
For verdenskart-scenen prioriteres de to første.

### Kingdom: Two Crowns — sterk påvirkning

Brukes for **øy-silhuett-estetikk**:

- Flate mørke former, **ingen indre detalj-tekstur**. Øyene defineres
  kun av konturen.
- Silhuetter står fram via ren kontrast mot bakgrunnen, ikke via
  rendering-triks.
- Horisonten er ofte varmt tinted mens forgrunn/midgrunn forblir
  kjølig — gir atmosfærisk dybde uten parallax.

For verdenskart: øyene tegnes som enkle polygon-fylt i STONE_DARKEST,
**uten** skrågrense-kanter, tekstur eller høyde-indikasjon. De er
"hvor land er", ikke hva de er.

### Sid Meier's Pirates! (PSP 2005) — moderat påvirkning

Brukes for **top-down-ikonografi**:

- Skip-sprite: gjenkjennelig profil fra fugleperspektiv (mast sentrert,
  skrog som smal ellipse, to seil til hver side).
- Havnemarkør-design: sirkulær symbol, varm for aktiv havn, dempet for
  andre. Pirates! bruker forskjellige flagg-farger for fraksjoner —
  **dette forkastes** i 2B (vi har ikke fraksjoner før Fase 3).
- **Mini-kart-følelsen**: stilisert, ikke geografisk korrekt. Karibien
  er representert, ikke kartlagt.

**Ikke-brukt fra Pirates!:** animerte bølger langs skip-sporet,
kursindikator-linje, sanntids-skyggestrek. For 2B holder vi det
statisk og rent.

### Monkey Island VGA — bakgrunnspåvirkning

Kun referanse for **varm/kjølig-kontrast** på dag/natt-faser — ikke
kopiert direkte. Fargevalg i LANTERN- og STONE-familiene er allerede
destillert fra denne kilden i master-paletten.

---

## 3. Havnemarkør-design

**Dimensjon:** 14×14 placeholder.

**Rasjonal for 14 over 12:** 12×12 er på grensen til å føles som en
pixel-klump på 640×360 skjerm; 14×14 gir én pixel mer ring-tykkelse
som gjør sirkelen lesbar uten å bli "chunky". Se spec §6.2 som
antyder 12×12 — jeg anbefaler 14×14 med dokumentert rasjonale.

**Form:** sirkulær ring (2px tykk) med solid fyllt sentrum-prikk
(2×2 px). Ikke havn-ikon i sentrum — detaljer under 8×8 blir
uleselig på denne skjermen.

```
  ....##....      legende:   . = transparent
  .###..###.                  # = ring-farge
  .#......#.                  o = senter-farge
  .#......#.
  ##..oo..##
  ##..oo..##
  .#......#.
  .#......#.
  .###..###.
  ....##....
```

**Farger per tilstand:**

| Tilstand | Ring | Senter | Rasjonale |
|----------|------|--------|-----------|
| Current port (hvor spiller er) | `COLOR_LANTERN_BRIGHT` (`#ffd580`) | `COLOR_LANTERN` (`#ffb347`) | Varm familie = spillerens "hjem" i øyeblikket. Bright i ytterkant gir strålingseffekt mot kjølig hav. |
| Fokusert/hover (piltast-valg) | `COLOR_LANTERN` (`#ffb347`) | `COLOR_EMBER` (`#d96c2e`) | Dempet varm — signaliserer "under vurdering, ikke aktiv". |
| Andre havner | `COLOR_STONE_LIT` (`#6b8bc7`) | `COLOR_STONE_DARK` (`#1f2538`) | Kald familie = institusjonelt kjent men ikke aktivt. |
| Aldri besøkt | `COLOR_FOG` (`#3a3a4a`) | `COLOR_STONE_DARKEST` (`#151a2a`) | Dempet grå, lav kontrast mot hav — må "lete" for å se den. Forsvarer tematisk at ukjente steder er usynligere. |

**Tooltip-integrasjon (spec §6.2):** tooltip flyttes inn under markøren
(høyrehav-side) med 2 px padding. Fersk-data i `COLOR_STONE_LIT`, stale
i `COLOR_FOG`, aldri-besøkt-tekst i `COLOR_STONE_DARKEST` (knapt synlig
— bevisst).

---

## 4. Skip-sprite

**Dimensjon:** 12×12 placeholder. Skipet er et punkt på kartet, ikke
en detaljert modell — mindre plass hindrer overdetaljering.

**Farge:** `COLOR_WOOD_LIGHT` (`#5c4a35`) for skrog, `COLOR_SHIRT`
(`#e8dcc4`) for seil. **Ikke LANTERN** — varm oransje-tone ville
trekke oppmerksomhet vekk fra havn-markøren som skal eie den rollen.
Skip er "verktøy for navigasjon", havn er "destinasjon"; visuell
hierarki speiler dette.

**Orientering:** 4 retninger i 2B (N, S, Ø, V). Skipet peker mot
destinasjon under voyage; stasjonær ved havn (orientert mot åpent hav,
ikke mot havn-markøren). 4 varianter pre-rendres ved scene-init.

**Tilstand:**

- **Ved havn (no voyage):** 12×12-sprite tegnes med 2 px offset fra
  current-port-markøren (mot åpent hav). Orientering: havn-avhengig,
  kan leses fra port_config eller hardkodes i C5-fase.
- **Under voyage:** sprite interpoleres langs lineær bane fra
  from_port til to_port basert på `voyage.progress`. Heading beregnes
  fra vektoren mellom havnene (klampet til nærmeste 4-retnings). Ingen
  rotasjon, bare valg mellom 4 pre-renderte sprites.
- **Ankomst:** sprite "lander" på destinasjonens havn-markør uten
  ekstra animasjon. Voyage-ankomst-toast signaliserer hendelsen.

**Pre-render skisse (N-orientering):**

```
  .....##.....       legende:   . = transparent
  .....##.....                   # = skrog (WOOD_LIGHT)
  ....####....                   o = seil (SHIRT)
  ...#oooo#...
  ..#oooooo#..
  ..#oooooo#..
  ...#oooo#...
  ....####....
  .....##.....
  .....##.....
  .....##.....
  .....##.....
```

Seilene utgjør en enkel triangel/rektangulær form — leselig som
"skip" uten å kreve sprite-arbeid.

---

## 5. Hav-tekstur

**Tilnærming:** pre-rendret gradient + statiske bølge-indikatorer.

**Gradient-konstruksjon:**

- Topp av hav-regionen (rett under himmel-band): `COLOR_SEA_MID`
  (`#1e2a4a`) — litt mindre mørk, antyder reflektert skumrings-lys.
- Midten av hav-regionen: `COLOR_SEA_DEEP` (`#0f1829`).
- Bunn: `COLOR_SEA_DEEP` (samme farge) — vi går ikke enda mørkere
  fordi paletten stopper der.

Gradient implementeres som 3–5 horisontale striper, ikke kontinuerlig
interpolasjon (vi vil unngå farger utenfor palett).

**Bølge-indikatorer (statisk):**

- Sparse 1-px hvite prikker spredt ut i øvre halvdel av hav-regionen,
  tegnet i `COLOR_STONE_BRIGHT` (`#8ba8d6`) eller
  `COLOR_SEA_HIGHLIGHT` (`#4a5a8a`). Sjekkerbrett-lignende fordeling
  (ikke regulær) — gir teksturfølelse uten å lese som raster.
- Tetthet: ~50 prikker spredt over 640×360-halvdel. Pre-rendret i bake-
  funksjonen.
- **Ingen animasjon i 2B.**

**Anbefaling om palette cycling:** forkast for 2B.

Rasjonal: Tortuga-signatur-scenens måne-refleksjon er palette-cycled,
men den er ett begrenset område på 8–12 pixler. På verdenskartet ville
palette cycling over hele hav-regionen enten kreve:
(a) en dedikert palettized surface for havet, noe som bryter med
`.convert()`-raster vi bruker ellers;
(b) render-lag-tricks som introduserer kompleksitet.

Budsjettering til Fase 3 eller senere når vi ser hva kart-dynamikken
faktisk trenger. **Statisk hav holder** for 2B-MVPen.

---

## 6. Dag/natt på kartet

Spec §6.3 definerer mekanikken: interpolasjon mellom 4 tidspunkter
(dawn, noon, dusk, night). Visuelt betyr det re-tintet bakgrunn ved
dag-faseskifter (ikke per frame).

**Faseskifte-palett:**

| Fase | sky_top | sea_top | sea_deep | Notat |
|------|---------|---------|----------|-------|
| Dawn (0.17) | `COLOR_SKY_DUSK_HORIZON` (`#d96c2e`) | `COLOR_SEA_LIGHT` | `COLOR_SEA_MID` | Varm horisont, hav lysnet |
| Noon (0.50) | `COLOR_SKY_DAY_HORIZON` (`#8ba8d6`) | `COLOR_SEA_HIGHLIGHT` | `COLOR_SEA_LIGHT` | Lyseste state; sol-refleksjoner i hav |
| Dusk (0.80) | `COLOR_SKY_DUSK_HORIZON` (`#d96c2e`) | `COLOR_SEA_MID` | `COLOR_SEA_DEEP` | Symmetrisk med dawn; litt dypere hav |
| Night (0.92+) | `COLOR_SKY_MID` (`#1a1f4d`) | `COLOR_SEA_DEEP` | `COLOR_SEA_DEEP` | Full natt; hav kollapser til én tone |

Interpolering skjer lineært mellom 4 pre-renderte bakgrunner (samme
mønster som parallax-backdrops i Tortuga-scenen). Cross-fade via
`set_alpha` på påfølgende bakgrunn.

**Leselighet-krav for øy-silhuetter:**

Øyene er tegnet i `COLOR_STONE_DARKEST` (`#151a2a`). Kontrast-sjekk
mot bakgrunn i hver fase:

| Fase | Hav bak øy | Kontrast-ratio | Status |
|------|-----------|----------------|--------|
| Dawn | SEA_MID (`#1e2a4a`) | 1.6:1 | Grenseland — OK fordi horisont gir ekstra varm kant |
| Noon | SEA_LIGHT (`#2a3a5e`) | 2.2:1 | OK |
| Dusk | SEA_DEEP (`#0f1829`) | 1.3:1 | **KRITISK** — silhuetter smelter delvis inn |
| Night | SEA_DEEP (`#0f1829`) | 1.3:1 | **KRITISK** |

**Løsning:** om natten og dusk, tegn en 1-px ytre "skimmer-linje" i
`COLOR_STONE_DARK` (`#1f2538`) som subtil silhuett-forsterker. Gir
1.8:1-kontrast mot SEA_DEEP — nok til at øyene fortsatt er leselige
selv om de er mørkere enn dagfasen. Skimmer-linjen pre-rendres som
del av natt-bakgrunns-varianten, ikke dynamisk.

**Ikke-løsning:** ikke gjør øy-fargene lysere om natten. Det ville
bryte tematikken (verden blir mørkere om natten, ikke invertert).

---

## 7. Stub-havnene i C6 — eksplisitt direktiv

Per brukerens heads-up fra C1a-oppstart og gjentatt her:

**Stub-havnene (Port Royal, Havana, Nassau) i C6 skal bruke Tortugas
bygnings-layout uendret og samme assets.** Ingen unike bygninger,
ingen fargevariasjon, ingen signatur-atmosfære.

**Konkret i C6-implementasjon:**

- `data/ports.json` sitt `buildings`-felt for Port Royal / Havana /
  Nassau kopierer Tortugas `ground_top_y`, `player_start_x`, `tavern`
  og `exchange`-plasseringer eksakt.
- `player_start_x` kan eventuelt variere per havn hvis world_width
  skiller seg (Port Royal 1200 vs Tortuga 1600), men konseptuelt er
  layout samme.
- Hawkins flyttes ikke som NPC til andre havner — hver havn trenger
  enten sin egen børsmester-id i `npcs.json`, eller vi aksepterer at
  samme "hawkins" står i alle havner som placeholder til Fase 3.
  **Anbefaling**: samme hawkins-placeholder; distinkte NPC-er er et
  Fase 3-anliggende når havnene får sine egne fraksjoner.
- Ingen endring i bake-funksjoner (`_bake_tavern`, `_bake_exchange`)
  — samme sprite tegnes for alle havner.

**Hvorfor dette er bevisst:**

Distinkt havn-karakter trenger ikke bare forskjellige sprites. Det
trenger distinkte NPC-er, historier, fraksjoner, rykter. Å gi stub-
havnene halvveis visuell differensiering (forskjellige taverna-farger
eller bygnings-plasseringer) i 2B ville:

1. Lage arbeid som må omgjøres i Fase 3 når havnene skal få skikkelig
   identitet.
2. Skape en falsk forventning hos spilleren om at havnene er
   forskjellige når mekanikken bak ikke er det.

**Fase 3-plan** (dokumenteres her for sporbarhet, ikke implementert):

- Per-havn NPC-sett (`data/npcs.json` utvides med `location`-felt).
- Fraksjonsmarkering på bygninger (flaggfarge, guvernør-wappen).
- Signaturlyd eller musikk per havn — men dette er først aktuelt når
  audio-systemet lander.

Inntil da: Port Royal, Havana og Nassau SER ut som Tortuga. Det er
riktig valg.

---

## CHANGELOG

- **v1.0 (2026-04-19)** — Initial versjon etter Commit C4-lukking,
  før C5-planlegging. Kodifiserer palett-vekting, inspirasjons-
  balansering, og stub-havn-direktivet slik at C5-C6-implementering
  har eksplisitt referanse å måles mot.
