# Pitch & Plunder – Fase 2.5 retrospektiv

Ferdigstilt: 2026-04-20
Commits: C2.5-1 til C2.5-10 (13 totalt, inkluderer 2 revert-commits)

---

## Hva ble bygget

Fase 2.5 løftet havnene fra "scene-plakater" til "bebodde byer". Der
Fase 2B leverte funksjonell multi-havn-økonomi med stub-havner
(Port Royal, Havana, Nassau som Tortuga-layout), ga Fase 2.5 hver
havn distinkt visuell identitet, bystruktur med fyll-bygninger og
smug, slitasje og natur, dag/natt-lys-gating, og animerte ild-kilder.

Havnene er nå lesbare som fire forskjellige steder med forskjellig
kultur og økonomi. Kingdom Two Crowns-nivået for nattscene-atmosfære
er i stor grad oppnådd, med unntak av vann-refleksjoner som ble
droppet etter to mislykkede implementasjons-forsøk.

---

## Commit-oversikt

### C2.5-1 (1fb72df) — Tortuga rekvisita-lag
Prototyp-commit. Rekvisita-mønster etablert for resten av fasen.
Tortuga fikk gategulv-tekstur (`cobblestone_wet`), 3 lanterne-
stolper, 3 markedsboder, 2 tønnestabler, 3 NPC-silhuetter. +21
tester (439 totalt). Frame-tid uendret.

Avvik: lanterne-glød statisk (ikke dynamisk), pga 4-lys-budsjett.

### C2.5-2 (8b35776) — Port Royal britisk kolonial
Første stub-havn fikk helt ny visuell identitet. Customs House
(erstatter børshus-sprite), klokketårn-kirke, rum-magasin. Tørr
brostein, jerngjerder, 3 britiske silhuetter (offiser, merchant,
colonial_lady). +18 tester (457 totalt).

### C2.5-3 (50f9523) — Havana spansk-barokk
Havana fikk katedral (to klokketårn, 30 px hver), guvernørpalass
med arkade, handelshus. Stone_slab-heller, fontene, 4 spanske
silhuetter (priest, spanish_officer, spanish_merchant,
mantilla_woman). +11 tester (468 totalt).

### C2.5-4 (c5725c3) — Nassau pirat-kaos
Mest radikal havn. Åpen markedsplass (INGEN børs-bygning),
Teach's hus med lappverks-arkitektur, skipsverft. Sand-gater,
bål, bambus-lanterner, 2 silhuetter (barefoot_sailor,
woman_with_child). Lys-korrigering: kaldt STONE_LIT → varm LANTERN
for markedsplass-glow. +11 tester (479 totalt).

### C2.5-5 (be391b1) — Ankrede skip-silhuetter
3 smugler-skuter (Tortuga), 3 fregatter (Port Royal), 2 galleoner
+ 1 small (Havana), 5 pirat-skip (Nassau). Bakt inn i foreground
SRCALPHA-variantene — 0 per-frame-regresjon. +17 tester (496
totalt).

### C2.5-6a (9f91f04) — Tortuga + Nassau fyll-bygninger + smug
v1.1-scope-utvidelse. Tortuga fikk 5 fyll-bygninger (fiskerhytte,
boarding-hus, tømmerpakkhus, felt-hospital, smithy), Nassau fikk
5 (inkl. taverne-cluster med `style_variant` for asymmetri).
Smug 3 per havn. +26 tester (522 totalt).

Nytt rammeverk: `entities/fill_buildings.py`, `FillBuilding`/`Alley`
dataclasses, `MAX_FILL_BUILDING_HEIGHT = 60` for silhuett-
hierarki-håndhevelse.

### C2.5-6b (f0be73a) — Port Royal + Havana fyll-bygninger
Større havner følger 6a-mønster. Port Royal fikk 6 institusjonelle
bygninger (officers_residence, east_india_company,
soldier_barracks, civil_warehouse, merchants_house, apothecary).
Havana fikk 7 spansk-barokke (borger_house, cloister_annex,
merchants_house_havana, artisans_workshop, guard_house,
tobacco_warehouse, chapel_small). +5 tester (527 totalt).

Havn-spesifikk stil validert: samme funksjon har distinkt utseende
per havn (Port Royal sivilt pakkhus ≠ Tortuga lumber_warehouse).

### C2.5-7 (df81134) — Livfullhet (slitasje + natur + statisk lys)
v1.2-scope-utvidelse. Største enkelt-commit. Natur-sprites (palmer,
fugler, bougainvillea, ugress, sand-drift), slitasje på eksisterende
bygninger (mose, flasseflekker), statisk lys-karakter (Tortuga-
vindus-silhuetter, Port Royal lone-guard-vindu, Havana glass-
mosaikk, Nassau 3 vinduer-fargede), smug-innhold. 12 nye nature-
kinds. +19 tester (546 totalt).

Avvik: 6 slitasje-detaljer fra spec utelatt (rust-streker, salt-
ringer, grønnsky, solbrente striper, sot-sverting) — MVP-tilnærming
med ett slitasje-element + ett lys-element per havn.

### C2.5-8 (a0472cc) — Vann-refleksjoner [REVERT]
Første forsøk. Refleksjonene svevde mellom fjell-silhuett og
bygningstopper i stedet for i vannet. Ingen dag/natt-gating.
Fundamentale designfeil.

### C2.5-8a (09f7962) — Revert + diagnose
Revert av C2.5-8. Diagnose: bygnings-lys lyser 24/7 uten dag/natt-
gating. Dette måtte fikses først. Refleksjoner utsatt til C2.5-8c
bygget på 8b-infrastrukturen.

### C2.5-8b (9efba53) — Dag/natt-lys-gating
Kjerneinfrastruktur. `compute_night_factor` i `day_cycle.py`
(smoothstep-fade ved sunrise 0.08→0.17 og sunset 0.80→0.88).
`LightingSystem.draw(night_factor)` med threshold 0.5. Alle 9
signatur-bygnings-bakere + alle 22 fyll-bygnings-bakere fikk
`night_lights`-parameter. `build_port_gameplay_layer` returnerer nå
`(day, night)`-tuple. PortVillageScene bytter surface per frame.

Permanente lys (smithy-esse, campfires, metall-ornamenter)
kjører 24/7. Gated lys (vinduer, dør-glød, skilt) fades ved dag.

+14 tester (560 totalt).

Avvik: 18 av 22 fyll-bygnings-funksjoner fikk `night_lights`-param
men pixel-tegninger uendret (scope-kontroll). Threshold-snap i
stedet for smooth-fade (BLEND_RGB_ADD-begrensning).

### C2.5-8c (89a12c4) — Vann-refleksjoner andre forsøk [REVERT]
Nytt forsøk bygget på 8b. Refleksjoner bakt kun i night-variant,
før bygninger i bake-rekkefølgen. Alle tester grønne — men
brukerverifisering fant at refleksjonene fortsatt svevde over
bygningene, ikke i vannet. Samme bug på tross av spesifikke
tester som skulle fange det.

### C2.5-8d (118ca5b) — Revert av C2.5-8c
Andre revert. Beslutning: dropp vann-refleksjoner for Fase 2.5.
Grundig dokumentert som teknisk gjeld for Fase 3. C2.5-8b dag/natt-
infrastruktur bevart.

### C2.5-9 (736ea8f) — Animasjons-pass
Palette-cycling på bål, smithy-esse, katedral-portal, artisan-
verksted, Customs-vindu. 13/8/20/24 px cycling per havn (under 25
px-budsjett). Permanent vs gated-sondring (bål brenner 24/7,
vinduer slås av om dagen). +17 tester (577 totalt).

Avvik: alpha-pulsering på vinduer utsatt til Fase 3 (scope-
kontroll). Refleksjons-bølge-cycling fjernet siden refleksjoner
ble droppet.

### C2.5-10 (denne) — Retrospektiv og lukking
Brukertest + denne dokumentasjonen. Ingen kode-endringer.

---

## Fase 2.5 i tall

| Metrikk | Start (2B-slutt) | Slutt (2.5-slutt) | Delta |
|---------|-------------------|-------------------|-------|
| Tester | 418 | 577 | +159 |
| Bygnings-kinds | 2 (tavern + exchange) | 31 (2 + 6 signatur + 22 fyll + custom exchange-varianter) | +29 |
| Nature-kinds | 0 | 12 | +12 |
| Palett-farger i bruk | 30 (master) | 30 (uendret — palett-disiplin) | 0 |
| Animasjons-piksler | 0 | 65 (Tortuga 13 + Port Royal 8 + Havana 20 + Nassau 24) | +65 |
| Frame-tid lukket (median) | 4.87 ms | 4.0–4.5 ms | marginal |
| Frame-tid overlay (median) | 6.29 ms | 4.8–5.4 ms | marginal |
| Scene-init-tid | ~50 ms | 100–200 ms (to varianter) | ~2×, engangskost |

13 commits (11 fremdrift + 2 reverter).

Kommentar: Frame-tid gikk marginalt ned til tross for mye nytt
innhold. Scene-init gikk opp pga bake to gameplay-surface-varianter
— akseptabelt siden det bare skjer ved scene-entry.

---

## Commit-ytelse-sammendrag (lukket/overlay per havn, dev-maskin)

| Commit | Tortuga | Port Royal | Havana | Nassau |
|--------|---------|------------|--------|--------|
| C2.5-1 | 4.54/6.07 | — | — | — |
| C2.5-5 | 3.84/4.77 | 4.37/4.82 | 3.91/5.12 | 3.82/5.26 |
| C2.5-6b | 4.00/4.79 | 3.92/4.98 | 4.00/5.14 | 3.97/4.91 |
| C2.5-7 | 3.78/4.79 | 3.78/5.35 | 3.93/4.90 | 3.75/4.31 |
| C2.5-8b | 3.79/4.70 | 3.90/4.30 | 3.97/4.46 | 4.33/4.59 |
| C2.5-9 | 4.03/4.82 | 4.38/5.35 | 3.95/4.93 | 4.46/5.23 |

Alle havner alltid under 10 ms hard grense. Headroom 2.5× mot
grense ved endpoints.

---

## Designbeslutninger

### Per-havn historisk forankring (ikke faction-based)

Havnene er forankret i 1600-talls Karibien-historie
(Tortuga=smugler, Port Royal=britisk, Havana=spansk, Nassau=
pirat-republikk) snarere enn spill-fraksjon. Dette lot design
låses stabilt før Fase 3-fraksjons-valg er tatt. Konsekvens:
Fase 3 kan legge flagg/wappen på eksisterende bygninger uten
å omgjøre visuell identitet.

### Nassau uten børs-bygning

Radikalt valg fra spec §1.3: Nassau har *ingen* dominant bygning.
Markedsplass med teltduker og vekt-stokk erstatter børshus. HUD
sier fortsatt "Nassau Børs — Dag N" (generisk spill-term) selv om
det spilleren ser er uten bygning.

Brukerverifisering bekreftet at dette leses som "designet kaos",
ikke "halvferdig". Fraværet er signalet.

### 4-nivå silhuett-hierarki (§1.4)

Dominant (96–108) > Signatur (72–84) > Fyll-høy (48–60) > Fyll-lav
(32–44). Håndhevet i parser (`MAX_FILL_BUILDING_HEIGHT = 60`) og
ved bake-tid. Brukerverifisering bekreftet at signatur-bygningene
dominerer naturlig — spilleren ser katedralen først, så palasset,
så andre bygninger.

### Havn-spesifikk stil per bygning-type

Samme funksjon har distinkt utseende per havn:
- Pakkhus: Tortuga tømmerstokker ≠ Port Royal sivilt murstein ≠
  Havana tobakksballer ≠ Nassau improvisert lappverk
- Merchants_house: Port Royal streng pilaster-portal ≠ Havana
  balkong-med-blomster + FLAME-dør

Brukeren kunne identifisere havner på enkelte fyll-bygninger
alene i brukertest.

### Alternativ 1 (sprite-varianter) for dag/natt-gating

Bygninger bakes i to varianter (`day_surface`, `night_surface`).
Scene bytter mellom dem per frame basert på `night_factor ≥ 0.5`.
Per-frame-kost uendret (samme én blit). Scene-init ~2× (to bakes).

Alternativ 2 (runtime halo-overlay) og 3 (dim-overlay) avvist
pga per-frame-kost og palett-disiplin-problemer.

### To refleksjons-forsøk mislykkes → droppet for Fase 3

Begge forsøk (C2.5-8, C2.5-8c) feilet på samme måte: piksler
utenfor vann-regionen, på tross av eksplisitte tester. Revert-
mønsteret fungerte — vi unngikk å fastlåse dårlig design. Noteres
som arkitektur-utfordring for Fase 3, dokumentert i C2.5-8d-
commit.

---

## Tekniske lærdommer

### Stillbilder kan lure om parallax-oppførsel

C2.5-5 ankrede-skip-commit så riktig ut i stillbilder, men
brukerverifisering ved kamera-bevegelse ville avslørt
parallax-drift hvis jeg hadde lagt refleksjoner i foreground-laget
tidligere. Ett argument for å plassere refleksjoner i gameplay-
laget (speed 1.0) som lyskildene.

### Revert + diagnose-sub-commit-mønsteret

C2.5-8a var ikke bare en revert — det var også en diagnose-
sub-commit som kartla eksisterende lys-infrastruktur før det neste
forsøket. Dette avdekket at dag/natt-gating var et dypere
arkitektur-problem som måtte løses FØR refleksjoner.

Resultat: C2.5-8b ble mer verdifull commit enn refleksjoner
noen gang kom til å være (gating gjelder hele scenen, ikke bare
havet).

### "Tester grønne" betyr ikke "fungerer"

C2.5-8c hadde 15 spesifikke tester som skulle fange "svever
utenfor vann-region", inkludert pixel-scan-tester. Alle tester
passerte. Brukerverifisering avdekket at refleksjonene fortsatt
svevde.

Problemet var at testene scannet rundt tavern-center-x, mens
refleksjonene ble generert rundt andre x-koordinater (signatur-
bygninger, exchange) som ikke ble testet. Fullstendig pixel-dekning
er vanskelig uten at teststrategien selv er feil.

Lærdom: visuell brukerverifisering er irreduceable for visuelle
features. Tester kan validere invarianter (piksler i y-region) men
ikke oppfattet-kvalitet.

### Arkitektonisk hull oppdaget sent

Dag/natt-gating var ikke i den opprinnelige Fase 2.5-spec. Det
ble avslørt ved at refleksjoner skulle implementeres — vi oppdaget
at bygnings-lys lyste 24/7, som var dyperere problem enn bare å
legge til refleksjoner.

Å stoppe og fikse gating først (C2.5-8b) ga høyere verdi enn
refleksjonene selv. Ikke alle "spec-features" er like viktige
som "infrastruktur som spec'en forutsatte men ikke eksplisitt
krevde".

### Palett-disiplinen i 30 farger uten grønn

Master-paletten har ingen grønn. For mose, løv, ugress måtte vi
velge nærmeste alternativer:
- STONE_LIT (salt-grønn mot stein)
- WOOD_MID (våt-grønn mot tre)
- WOOD_DARKEST (mørk løv-silhuett)

Brukerverifisering fant at disse leses som "plante-aktig mot
natthimmel". Begrensningen ble kreativ løsning snarere enn
blokker.

---

## Observasjoner fra brukertest (2026-04-20)

### Styrker

- Alle 4 havner leses som sin tiltenkte identitet (smugler/
  kolonial/barokk/pirat-kaos). Spørsmål 1–4 alle JA.
- Dag/natt-oppførsel fungerer. Havnene ser "døde" ut om dagen
  (tavern signatur-bygg spesielt) og levende om natten.
- Nassau-bål asynkrone (6 vs 5 fps) er tydelig merkbart og gir
  "ikke-synkron flimring".
- Smithy-esse leses som levende arbeidslys.
- Natur-elementer (palmer, fugler, blomster) er synlige uten
  å være dominerende.
- Havana-silhuett er IKKE flat — variasjon mellom katedral,
  palass, handelshus holder skulderlinjen levende.
- Nassau-høyre-seksjonen er IKKE for stille — C2.5-6a-
  observasjonen løste seg naturlig med fyll-bygninger.

### Svakheter

- **Dag/natt-overgang slås av brått** (threshold-snap). Akseptert
  av bruker som OK, men noteres for senere smooth-fade.
- **Tortuga-taverna-silhuetter (hatt, spillekort) leses som
  "bordlampe-silhuett"**. Design-treff ikke. Trenger re-design for
  å lese som "folk innenfor" i stedet for møbler.
- **Havnene føles "nesten" bebodd** — bruker peker på manglende
  bakgrunnslag med bygninger bak eksisterende bygninger.
  Illusjonen av at byen strekker seg innover mangler.
- **Lite NPC-er** per havn — ikke akutt, men noteres.
- **Bål-flimring leses som "litt futuristisk"** — akseptert og
  beholdt, men notert.

### Overraskelser

- **Noen fugler er statisk i luften** — ikke visuelt problem
  for brukeren, beholdes.
- **Bakgrunnslag-observasjonen var ny**. Det kom som forslag
  fra brukertesten, ikke fra spec. Signifikant Fase 3-input.

---

## Teknisk gjeld for Fase 3

### Visuell polish (prioritert av brukerverifisering)

1. **Bakgrunnslag med fyller-bygninger bak eksisterende**
   (HØY prioritet per brukertest). Illusjon av større by.
   Teknisk: kunne være nytt lag med speed 0.5-0.7, plassert
   mellom nåværende foreground (0.2) og gameplay (1.0). Silhuett-
   lag med små mørke bygnings-former.

2. **Re-design Tortuga-taverna-vindus-silhuetter**. Nåværende
   "hatt"-silhuett og "spillekort"-silhuett leses som bordlampe.
   Trenger tydeligere menneskelige former (skulder-linje,
   gruppe-silhuett) eller bevegelse (alpha-pulsering bak).

3. **Flere NPC-er**. Ikke blokker, men nåværende 2–4 per havn
   er lite for "bebodd".

### Tekniske infrastruktur-mangler

4. **Vann-refleksjoner**. Droppet i Fase 2.5 etter to forsøk.
   Arkitektur-utfordring: foreground-lag speed 0.2 vs gameplay-
   lag speed 1.0 mismatch. Måne-refleksjon kan isoleres som
   egen commit siden månen er verdens-forankret x.

5. **Smooth dag/natt-fade** i stedet for threshold-snap.
   BLEND_RGB_ADD-begrensning — krever intermediate surface +
   alpha-blend. Bruker aksepterte snap, så ikke akutt.

6. **Alpha-pulsering på vinduer**. Planlagt for C2.5-9 men
   utsatt. Halo-surface-blits over gameplay med asynkron alpha.

### Scope-mangler fra spec

7. **18 fyll-bygninger har night_lights-parameter men ikke
   pixel-endringer**. Konkret: Havana merchants_house og Nassau
   improvised_warehouse kan fortsatt vise vindus-lys om dagen.

8. **6 slitasje-detaljer utelatt fra C2.5-7**: rust-streker
   under Tortuga-børshus, bøyde takkanter på fiskerhytte/
   boarding-hus, salt-ringer rundt offisersbolig, grønnsky på
   palass, solbrente striper på stone_slab, sot-sverting over
   Nassau-bål.

9. **Statiske fugler i luften** — noen måker er tegnet som om
   de flyr, men er statiske. Bruker aksepterer.

### Animasjons-utvidelser

10. **Nassau bål-cycling "litt futuristisk"**. Palett-rotasjon
    kan ha for høy FPS eller for spredte farger. Finpusse fps
    eller palett-sekvens.

11. **Ambient effekter** ikke implementert: røyk fra taverna-
    skorstein, fontene-vann-cycling i Havana, vind-effekter på
    seilduk-tak.

---

## Rebalanseringsnotat

Fase 2.5 er **visuell fase** — ingen mekaniske tall endret.
Fase 2B-rebalanseringsnotatet gjelder fortsatt: alle
økonomiske tall er provisoriske inntil Fase 3-mekanikker
(piratinntekter, møter, rykter) gir kontekst for balansering.

F5 hot-reload av `balance.json` fungerer fortsatt. F1–F4 debug-
teleport til alle 4 havner fungerer.

---

## Versjonene som førte til 2.5

FASE_2_5.md gjennomgikk tre versjoner i løpet av fasen:
- **v1.0**: Initial spec (7 commits, C2.5-1 til C2.5-7)
- **v1.1**: Etter C2.5-6a. Utvidet scope med fyll-bygninger,
  bystruktur, silhuett-hierarki. 10 commits.
- **v1.2**: Etter C2.5-7. Lagt til vann-refleksjoner som egen
  commit (C2.5-8). 11 commits.

Faktisk resultat: 13 commits pga revert-sub-commits for de to
mislykkede refleksjons-forsøkene. Ingen planlagt C2.5-8 ble
faktisk landet — vi har isteden C2.5-8a/b/c/d hvor kun 8b
overlevde.

---

## Fase 3-kobling

Fase 2.5 er ren visuell — ingen mekanikker endret. Fase 3 har
friksjon mot Fase 2.5 på flere punkter:

1. **Fraksjons-flagg** kan legges på eksisterende bygninger
   uten refaktorering. Bygnings-bbox-er er tilgjengelig i
   port_config.
2. **NPC-interaksjon**: silhuettene i C2.5-1/2/3/4/7 er
   non-interactive. Fase 3 kan bytte dem med `NPC`-klasse-
   instanser (dialog, rykte-tilbakemelding) uten scene-
   refactor.
3. **Guvernør-wappen** på Havana-palass eller Port Royal-
   Customs House kan legges til i bake-funksjoner som
   optional parameter.
4. **Taverne-rykter**: tavern-dør leder i dag til child scene
   i Fase 3-plan. Bygnings-bbox i `port_config.buildings.tavern`
   er klar for interaksjon.

Fase 2.5-disiplin om palett + silhuett-hierarki + havn-
spesifikk stil skal bevares i Fase 3. Vi introduserer ikke
nye farger, og ny dynamikk (NPC-bevegelse) må respektere
eksisterende silhuett-hierarki.

---

Fase 2.5 er formelt lukket. Fase 3-planlegging skjer gjennom
samtale med bruker; ingen kode før den diskusjonen.
