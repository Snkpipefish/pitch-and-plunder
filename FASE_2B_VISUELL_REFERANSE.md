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

**Alias-kommentar:** noen "tematiske" konstanter er aliaser introdusert
i Fase 2A Commit 5B for dag-natt-syklus:

| Tematisk alias | Peker på | Hex |
|----------------|----------|-----|
| `COLOR_SKY_DAY_HORIZON` | `COLOR_STONE_BRIGHT` | `#8ba8d6` |
| `COLOR_SKY_DUSK_HORIZON` | `COLOR_EMBER` | `#d96c2e` |
| `COLOR_SKY_DAY_TOP` | `COLOR_STONE_LIT` | `#6b8bc7` |
| `COLOR_SKY_DUSK_TOP` | `COLOR_COAT` | `#3d3548` |
| `COLOR_SUN_DAWN` | `COLOR_LANTERN` | `#ffb347` |
| `COLOR_SUN_DAY` | `COLOR_MOON_CORE` | `#fff8e7` |
| `COLOR_SUN_DUSK` | `COLOR_EMBER` | `#d96c2e` |

Bruk den tematiske aliasen der intent er himmel/sol-tilknyttet; bruk
grunnkonstanten der intent er generell (stein/ember). Begge lever som
eksisterende referanser i `constants.py`.

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
| Fokusert (piltast-valg) | `COLOR_LANTERN` (`#ffb347`) | `COLOR_MOON_CORE` (`#fff8e7`), pulserende alpha | Varm ring + lys kjerne signaliserer "under vurdering". Pulsering leverer bevegelse uten å bryte stillhetstemaet. |
| Andre havner | `COLOR_STONE_LIT` (`#6b8bc7`) | `COLOR_STONE_DARK` (`#1f2538`) | Kald familie = institusjonelt kjent men ikke aktivt. |
| Aldri besøkt | `COLOR_FOG` (`#3a3a4a`) | `COLOR_STONE_DARKEST` (`#151a2a`) | Dempet grå, lav kontrast mot hav — må "lete" for å se den. Forsvarer tematisk at ukjente steder er usynligere. |

**Fokusert-tilstand: pulserende sentrum-prikk**

Sentrum-prikken på fokusert markør moduleres med sinus-kurve mellom
alpha 0.7 og 1.0 over 1 sekund (2π rad / 1 s = 2π rad/s vinkelhastighet).
Ring-fargen er statisk; kun sentrum-prikken pulserer — det gir bevegelse
uten å overgå current-port-markørens stabile glød.

Formel:
```python
t = scene_elapsed_seconds
alpha = 0.7 + 0.15 * (1.0 + math.sin(2 * math.pi * t))
# Sinus-rekkevidde [-1, 1] → shift+scale gir [0.7, 1.0]
```

**Implementasjon:** pre-render sentrum-prikken i COLOR_MOON_CORE én gang
(som del av `PortMarker`-init), bruk `set_alpha(int(alpha * 255))` per
frame. `set_alpha` på colorkey-surfaces er billig (målt ~0.01 ms per
sprite på målmaskinen i 2A-perioden).

**Ytelseskrav:** pulsasjon må ikke regressere world_map-scenen under
5 ms-målet. Én ekstra `set_alpha` + én ekstra `blit` per frame for
fokus-markøren — forventet kost <0.1 ms. Hvis benchmark viser ellers,
flagg og fall tilbake til ikke-pulserende (statisk alpha 1.0).

**Tooltip-integrasjon (spec §6.2):** tooltip flyttes inn under markøren
(høyrehav-side) med 2 px padding. Fersk-data i `COLOR_STONE_LIT`, stale
i `COLOR_FOG`, aldri-besøkt-tekst i `COLOR_STONE_DARKEST` (knapt synlig
— bevisst).

---

## 4. Skip-sprite

**Dimensjon:** 12×12 placeholder. Skipet er et punkt på kartet, ikke
en detaljert modell — mindre plass hindrer overdetaljering.

**Perspektiv: RENT TOP-DOWN (fugleperspektiv).** Ikke Pirates!-stilens
semi-top-down hybrid der skroget ligger isometrisk. Her ser man skipet
rett ovenfra — som om man er i utkiksposten. Mast sentrert,
skrog/seil symmetriske om baug-akkse.

Rasjonal: 12×12 er for liten skala til å bære stilisert perspektiv-
hybrid uten å bli visuelt støy. Rent top-down gir klarest leselighet.

**Farge:** `COLOR_WOOD_LIGHT` (`#5c4a35`) for skrog, `COLOR_SHIRT`
(`#e8dcc4`) for seil. **Ikke LANTERN** — varm oransje-tone ville
trekke oppmerksomhet vekk fra havn-markøren som skal eie den rollen.
Skip er "verktøy for navigasjon", havn er "destinasjon"; visuell
hierarki speiler dette.

**Orientering: 4 SEPARATE pre-rendrede sprites (N, S, Ø, V).**

**Ikke sprite-flip.** Fire ekte sprites fordi top-down skip ser
markant forskjellig ut i N/S kontra Ø/V — baugen peker ut av
sprite-aksen i begge tilfeller, men retningen skroget går bred-inn-til-
skjermen endrer seg. Speiling via `pygame.transform.flip` gir feil
visuelt resultat for top-down siden en østvendt sprite er en 90°
rotert versjon av nordvendt, ikke speilbilde.

- **N** (nord): baug peker opp, bred side horisontal. Se skisse nedenfor.
- **S** (sør): baug peker ned. Kan genereres via vertikal flip av
  N-spriten siden skrog-formen er symmetrisk om x-aksen for top-down
  — akseptabelt her *fordi* sørvendt skip ER speiling av nordvendt
  når vi ser rett ned.
- **Ø** (øst): baug peker høyre, bred side vertikal. **Ny rendering**,
  ikke 90° rotasjon av N (asymmetri i seilføring ville gi feil).
- **V** (vest): baug peker venstre. Horisontal flip av Ø-sprite OK av
  samme symmetri-argument som S-N.

Netto: **2 unike pre-renderinger** (N og Ø), 2 flips (S og V) — men
dette er implementasjonsdetalj. Konseptuelt tenker vi fire distinkte
sprites.

Skipet peker mot destinasjon under voyage; stasjonær ved havn,
orientert bort fra havn-markøren mot åpent hav (C5 default "N").

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

**Bølge-indikatorer (statisk, per fase):**

- Sparse 1-px prikker spredt ut i øvre halvdel av hav-regionen.
  Sjekkerbrett-lignende fordeling (ikke regulær) — gir teksturfølelse
  uten å lese som raster.
- Tetthet: ~50 prikker spredt over 640×360-halvdel.
- Pre-rendret inn i bakgrunns-variantene per dag-fase.
- **Ingen animasjon i 2B.**

**Fargevalg per fase — varm glimt ved dawn/dusk:**

Havet må signalere solens posisjon subtilt. Ved skumring/daggry fanger
ekte hav opp varme fra horisonten og refleksjoner fra himmelen. På
kartet gjenskaper vi dette ved å bytte en andel prikker fra
`COLOR_STONE_BRIGHT` til `COLOR_EMBER`:

| Fase | Prikke-fordeling | Effekt |
|------|------------------|--------|
| Dawn (0.17) | ~80% `COLOR_STONE_BRIGHT`, **~20% `COLOR_EMBER`** | Spredt varm glimt mot horisont-retningen — holder scenen levende |
| Noon (0.50) | 100% `COLOR_STONE_BRIGHT` | Rent kjølig glitter; ingen varm forstyrrelse midt på dagen |
| Dusk (0.80) | ~80% `COLOR_STONE_BRIGHT`, **~20% `COLOR_EMBER`** | Speiler dawn; siste varme refleksjoner før natt |
| Night (0.92+) | 100% `COLOR_STONE_BRIGHT` (eller reduser tetthet til 60%) | Månelys-glitter; EMBER borte uten sol |

**Implementasjon:** bakefunksjonen `build_world_map_background` tar en
`phase: str`-parameter og velger prikke-palett deretter. Alle 4 faser
pre-rendres ved scene-init; cross-fade mellom dem skjer som på havn-
scenen (set_alpha på påfølgende bakgrunn ved fase-skifte).

Antall prikker skal være **samme** på tvers av faser (deterministisk
sjekkerbrett) — kun fargen på ~20% av dem endres. Dette gjør cross-fade
visuelt rolig: prikkene "blinker ikke bort og tilbake", de endrer bare
temperatur.

**Seed-kontroll:** bakefunksjonen tar `rng: random.Random | None = None`-
parameter. Produksjon bruker default (ikke-deterministisk spredning per
kjøring), tester bruker seedet rng for reproduserbare fordelinger.
Plasseringen forblir konstant gjennom fasene innenfor én scene-session.

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

**Løsning (oppdatert i v1.2):** §6's skimmer-linje er **erstattet** av
§8.1 topp-kant-belysning som lagringsmekanisme for silhuett-leselighet.
Samme implementasjons-mønster (pre-rendret per bakgrunns-variant), men
kanten er nå kun på silhuettens topp (ikke rundt hele), og fargen
varierer per fase per §8.5.

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

## 8. Addendum — lagringsmekanismer for visuell lesbarhet (C5.1)

Første C5-skjermbilde avdekket at dokumentets §1–§6 leverer på palett-
disiplin, men mangler de **visuelle lagringsmekanismene** som gjør at
spilleren faktisk skiller forgrunn fra bakgrunn, himmel fra hav, og
funksjonelle elementer fra dekor. Uten disse mekanismene kollapser
kartet til flate tonede områder uten dybde.

Denne seksjonen er **bindende for C5.1-patch** og overordnet §1–§6 der
de kolliderer. Senere polish i C10 bygger på dette grunnlaget.

### 8.1 Monkey Island — kontur-belysning på silhuetter

**Referanse:** Monkey Island EGA/VGA (1990, LucasArts) etablerte at
øy-silhuetter ikke er flate svarte klumper — de har **lysere kant på
silhuettens topp** ("edges and detail picked out in blue to denote
starlight"). Dette gir tydelig kontur mot natt-himmel selv når både
silhuett og bakgrunn er i mørke toner.

**Implementering på verdenskartet:**

- Hver øy-silhuett tegnes først i `COLOR_STONE_DARKEST` som hovedform.
- Deretter tegnes en **1-px lysere kant kun på topp-siden** av
  silhuetten, i `COLOR_STONE_DARK` (`#1f2538`) som "stjernelys" eller i
  `COLOR_MOON_HALO` (`#f5e6b3`) for faser der månen er synlig.
- Kanten er IKKE rundt hele silhuetten — kun toppen (der lyset treffer).
  Sider og bunn forblir i hovedfargen.
- Kant-fargens valg avhenger av dag-fase (se §8.5).

**Implementasjons-note:** kantene pre-rendres som del av bakgrunns-
varianten per fase, ikke dynamisk. Kantene er deterministiske — samme
silhuett-form gir samme kant hver gang.

### 8.2 Kingdom Two Crowns — atmosfære-gradient ved horisontlinjen

**Referanse:** Kingdom Two Crowns' sidescrolling-scener har konsistent
**varm horisont mot kjølig forgrunn/bakgrunn**, uansett tid på døgnet.
Selv i nattscener har horisonten en subtil varm understrek (disappearing
sun/approaching dawn) som gir atmosfærisk dybde. Det er ikke et
kontinuerlig vertikalt fargeskift — det er en tydelig horisontal
"belt-zone" der himmel møter jord/hav.

**Implementering på verdenskartet:**

- I den horisontale overgangen mellom himmel-region og hav-region,
  introduser et **horisont-bånd på 4 pixler høyde** (startverdi —
  kan justeres opp til 6 hvis 4 viser seg for subtilt, men ikke
  høyere; 8+ gir konstant skumring og underminerer Kingdom-
  effekten som fungerer fordi den er subtil).
- Glatt interpolering mellom hav-farge og himmel-farge via
  alpha-blend, ikke hard gradient. Ingen dithering nødvendig hvis
  glatt alpha fungerer.
- Tre tilnærminger, én per fase-gruppe:
  - **Dawn/dusk:** horisont-bånd med varmetilting i `COLOR_EMBER`
    (`#d96c2e`) eller tematisk alias `COLOR_SUN_DAWN`
    (`COLOR_LANTERN` = `#ffb347`). Direkte lagringsmekanisme for
    varm/kjølig-kontrasten spec'en antydet.
  - **Noon:** horisont-bånd i `COLOR_STONE_BRIGHT` (`#8ba8d6`) som
    fremhever horisont-linjen uten fargedramatikk. Lagringsmekanismen
    er kontrast i luminans, ikke hue.
  - **Night:** horisont-bånd i `COLOR_MOON_HALO` (`#f5e6b3`) — subtil
    måne-refleksjon langs horisonten. Lav intensitet (alpha-blending
    til 30–40%).
- Båndet er **ikke** et jevnt horisontalt stripe; det er 4 px høyt
  med alpha-gradient fra 100% ved horisont-linjen til 0% ved øvre/nedre
  ende. Gir "glød"-effekt uten hard kant.

**Kalibreringsnotat:** lettere å øke høyden til 6 senere enn å redusere
hvis 8+ viser seg feil. Start konservativt.

**Implementasjons-note:** alpha-gradient innenfor pre-rendret
bakgrunns-variant gir ingen ekstra runtime-kostnad. Gradient lages én
gang per fase-variant ved scene-init.

### 8.3 Havn-identifikasjon — tekstlabel under hver markør

**Referanse:** Sid Meier's Pirates! (alle versjoner) har alltid hatt
synlige havn-navn på kartet. Anonyme markører fungerer kun når
spilleren har ekstern kontekst (tutorial, minimap-legend). 2B har ingen
av delene.

**Implementering:**

- Under hver havn-markør tegnes et tekstlabel med havnens navn fra
  `port_config.name` (`"Tortuga"`, `"Port Royal"`, `"Havana"`,
  `"Nassau"`).
- Font: Public Pixel 8px (konsistent med HUD).
- Sentrert under markøren, 2–3 px padding mellom ring-bunn og label-topp.
- Label-bakgrunn: ingen (tekst rendret direkte på havgradient).

**Farger per tilstand:**

| Tilstand | Label-farge | Rasjonal |
|----------|------------|----------|
| Current port | `COLOR_MOON_HALO` (`#f5e6b3`) | Dempet gul, nøytral — signaliserer "merket sted uten politisk tilhørighet". Ring-fargen (varm LANTERN) bærer "her vs der"-signalet, ikke label. |
| Fokusert | `COLOR_MOON_HALO` (`#f5e6b3`) | Samme som current — fokus-differensiering skjer via ring-pulsering + lys sentrum-prikk. Label forblir uendret for å unngå visuell støy på allerede tett element. |
| Andre havner | `COLOR_MOON_HALO` (`#f5e6b3`) | Samme som current. Forskjell mellom "current/fokusert/andre" leses kun fra ring-farge/pulsering. |
| Aldri besøkt (C8+) | `COLOR_FOG` (`#3a3a4a`) | Dempet, konsistent med "kart-hull"-estetikken fra §3. Eneste unntak fra ensfarget regel. |

**Designprinsipp:** én bærer per signal. Ring bærer "her vs der" og
"fokusert vs ikke-fokusert". Label bærer kun identifikasjon.
Differensiert label-farge i tillegg til ring-tilstand ville gi redundant
signal og visuell støy på et 14-px element.

**Fase 3-plan (ikke implementert):** label-farge kan senere reflektere
fraksjons-tilhørighet (rød=engelsk, gul=spansk, blå=fransk, grå=pirat).
I 2B er alle havner nøytrale MOON_HALO.

### 8.4 Skyggedybde på hav — valgfri fjerde lagringsmekanisme

**Prinsipp:** ekte hav er **lysere nær kyster** (grunt vann reflekterer
mer) og **mørkere i åpent hav** (dyp vann absorberer lys). Kart-
representasjon kan speile dette uten å bryte palett-disiplinen.

**Implementering:**

- I en radius rundt hver øy-silhuett, bytt hav-farge fra
  `COLOR_SEA_DEEP` til `COLOR_SEA_MID` (`#1e2a4a`) — ett hakk lysere.
- **Test-rekkefølge for radius (bindende):**
  1. Prøv 12 px først (midt i intervallet).
  2. Hvis øyer overlapper visuelt: ned til 10, deretter 8.
  3. Hvis selv 8 px skaper overlapp: drop effekten helt.
     Bedre ingen effekt enn uklar hav-rendering.
  4. Hvis 12 px ser tynn ut og ingen overlapp: opp til 16 px.
- **Maksimal søkesone: 8–16 px.** Ikke eksperimenter utenfor.
- Overgangen mellom kyst-sone og åpent hav: 1 stegs hard overgang (ikke
  gradient) for å holde pixel-estetikken ren.

**Implementasjons-krav (bindende):**

1. **Pre-render ved scene-init, ikke per frame.** Én bakt surface for
   havet, ikke dynamisk shading. Radial mask per silhuett bakes inn i
   bakgrunns-varianten.
2. **Fallback ved overlapp:** drop skyggedybde helt hvis 8 px radius
   skaper visuelt overlapp mellom kyst-soner fra nærliggende øyer.
   Dokumenter valget i commit-melding.

**Rapportering:** oppgi hvilken radius-verdi som ble landet på, og
eventuelt screenshot som støtter valget.

**Valgfri i C5.1:** dette kan implementeres hvis det passer inn i
samme patch-runde, men er ikke blokkerende. Hvis det utsettes til C10,
dokumenter det i C5.1-commit-melding.

**Rasjonal for "valgfri":** de tre første lagringsmekanismene (8.1,
8.2, 8.3) løser lesbarhets-kritiske problemer. 8.4 er estetisk
forsterking.

### 8.5 Fase-spesifikk kontur-farge — sammenheng med §6

§6's kontrast-kritiske faser (dusk/night der øyer kan smelte inn) løses
elegant av §8.1-kant-belysningen. Skimmer-linjen som §6 opprinnelig
foreslo er nå **erstattet av den eksplisitte topp-kant-belysningen** i
§8.1. Resultat:

- **Noon:** topp-kant i `COLOR_STONE_DARK` (`#1f2538`) — subtilt men synlig.
- **Dawn:** topp-kant i `COLOR_STONE_DARK` (`#1f2538`) — dag-tone,
  silhuetter er allerede rimelig leselige mot SEA_MID-bakgrunn.
- **Dusk:** topp-kant i `COLOR_MOON_HALO` (`#f5e6b3`) — varm aksent
  matcher horisont-båndet, leverer silhuett-leselighet mot SEA_DEEP.
- **Night:** topp-kant i `COLOR_MOON_HALO` (`#f5e6b3`) — varm/kjølig-
  kontrast mot SEA_DEEP gir maksimal silhuett-kontur.

§6-tabellens løsnings-linje ("tegn en 1-px ytre skimmer-linje") er
oppdatert til: "topp-kant per §8.1 erstatter skimmer-linjen; samme
implementasjons-mønster (pre-rendret per bakgrunns-variant)".

---

## CHANGELOG

- **v1.2 (2026-04-19)** — Addendum (§8) etter C5-skjermbilde-review:
  fire lagringsmekanismer (kontur-belysning per Monkey Island,
  atmosfære-gradient per Kingdom Two Crowns, havn-identifikasjon per
  Pirates!, valgfri skyggedybde på hav). Bindende for C5.1-patch.
  §6 skimmer-linje-løsning erstattet av §8.1 topp-kant-belysning.

  Brukerens kalibrering:
  - §8.2 horisont-bånd: 4 px startverdi (ikke 8–12). Maks 6 px hvis 4
    viser seg for subtilt. 8+ forkastet som konstant skumring.
  - §8.3 label-farge: MOON_HALO for alle tilstander (inkludert
    fokusert). Ring bærer "her vs der" og fokus-signal alene.
  - §8.4 kyst-sone-radius: 8–16 px søkesone. Start på 12 px, test-
    rekkefølge dokumentert. Fallback = drop effekten hvis 8 px gir
    overlapp.

- **v1.1 (2026-04-19)** — Presiseringer fra brukeren før C5-start:
  (1) §1 alias-tabell legger til dokumentasjon av tematiske
  himmel/sol-aliaser for grunnkonstanter (COLOR_SKY_DAY_HORIZON →
  COLOR_STONE_BRIGHT osv.); (2) §3 markør-spec oppdatert med pulserende
  sentrum-prikk på fokus-tilstand (COLOR_MOON_CORE, sinus-alpha 0.7–1.0
  over 1 sek); (3) §4 skip-sprite-perspektivet eksplisitt definert som
  rent top-down (ikke Pirates!-hybrid), med fire separate pre-rendrede
  sprites — 2 unike renderinger (N, Ø) + 2 symmetri-flips (S fra N,
  V fra Ø); (4) §5 hav-tekstur utvidet med varm-glimt-fase per tid på
  døgnet (20% EMBER-prikker ved dawn/dusk, 100% STONE_BRIGHT ved
  noon/night). Ingen semantiske endringer i §2/§6/§7.

- **v1.0 (2026-04-19)** — Initial versjon etter Commit C4-lukking,
  før C5-planlegging. Kodifiserer palett-vekting, inspirasjons-
  balansering, og stub-havn-direktivet slik at C5-C6-implementering
  har eksplisitt referanse å måles mot.
