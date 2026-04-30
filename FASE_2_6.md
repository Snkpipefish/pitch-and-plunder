# Fase 2.6 — Visual remaster (480×270 + 32×48 sprites)

**Status:** Planlagt 2026-04-30. Kan kjøres parallelt med Fase 3 (mekanikk-
arbeid berører ikke sprite-/oppløsning-laget) eller som egen fokusert fase.

**Mål:** Pivot fra 640×360 + 16×16 sprites til **480×270 + 32×48 hovedsprite**
(Vei B etter side-ved-side-sammenligning i `tools/size_compare.py`).

**Bevart:** Moody Kingdom/Monkey Island-stemning, 30-farger master-palett,
Tortuga-natt-signaturscene, dobbeltliv-tema, dag/natt-syklus, alle
gameplay-mekanikker.

**Endret:** Pikselskala (det blir 1.78× større piksler på skjerm) +
sprite-detaljnivå (6× pikselbudsjett per karakter).

---

## 0. Scope-oversikt

Migrasjons-scope kartlagt 2026-04-30:

- **47 referanser** til `constants.RENDER_WIDTH/HEIGHT` i scenes/, systems/,
  ui/, entities/. Auto-oppdaterer ved konstant-flipp.
- **13 hardkodede 640/360-referanser** spredt i kommentarer og `port_buildings.py`,
  `exchange.py`, `parallax.py`. Krever manuell sweep.
- **4 `world_map_position`-koordinater** i `data/ports.json` plassert for
  640×360 kart-layout. Må re-balanseres for 480×270.
- **Alle pre-rendrede parallax-bakgrunner** i 4 havner (`port_buildings.py`,
  `parallax_backdrops.py`, `world_map_builder.py`) — bygd for 640×360, må
  regenereres på 480×270.
- **Sprite-størrelser** for player (16×16), NPC, props, signature buildings
  — må re-tegnes med utvidet pikselbudsjett.
- **HUD-fonten Public Pixel 8 px** — vurder 10-12 px for lesbarhet på den
  nye, mer komprimerte skjermflaten.

**Total ~5500 linjer scene-kode** å auditere; mest **logikk** holder seg
intakt, det er **rendering-veggene** som må regenereres.

---

## 1. Strategi: bottom-up rebuild på feature-branch

Migrasjonen utføres på en feature-branch (`v2.7-fase-2.6`) slik at `main`
beholder en spillbar bygging gjennom hele arbeidet. Sub-steg merges
tilbake samlet når hele opp­løsnings-/sprite-suite kompilerer rent.

**Hvorfor ikke per-scene migrasjon med legacy-flag?** For mye scaffolding-
gjeld for kortvarig nytte. Vi planlegger uansett å re-tegne ALT — å bygge
en parallell render-sti for å støtte halv-migrert tilstand er bortkastet
arbeid.

---

## 2. Sub-steg-rekkefølge

Hvert sub-steg er én commit. Test-pakken må være grønn før neste steg
starter.

### Sub-steg 1 (TRIVIELL) — Flip konstantene + assess [LANDET 2026-04-30]

- `RENDER_WIDTH` 640 → **480**, `RENDER_HEIGHT` 360 → **270** i `constants.py`
- `DEFAULT_SCALE` 2 → **3** (3 × 480 = 1440 vindus-bredde, behagelig størrelse)
- `WORLD_WIDTH` 1600 (uendret — havne-verden-bredde er world-coordinate, ikke skjerm)
- `post_fx` `render_size` default → `(480, 270)`

**Dokumentert visuelt brudd** (se `tools/fase_2_6_*.png`):

1. **Tortuga: bygninger usynlige** — `ground_top_y` ligger på ~280-300 i
   eksisterende layout, som er under den nye 270 px-grensen. Bygningsraden
   forsvinner under skjermen. Smoke-kilder spawner i havet (y=222 var
   nær roof-line, nå er det rett over horizonten).
2. **Tortuga: hav-andelen er for stor** — fjell-silhuetter ligger fortsatt
   ved riktig parallax-offset, men siden gameplay-laget er borte ser hele
   bunnhalvdelen ut som åpent hav.
3. **World map: klipping på høyre + bunn** — bakgrunnen er pre-rendret
   640×360, blit på 480×270 viser kun øvre venstre kvadrant. ~25 % av kart-
   innholdet er utenfor skjermen. Port Royal-markøren er borte, Tortuga
   sitter i hjørnet, øvrige labels er kuttet eller kollapser med tooltip.
4. **Voyage: skip + havne-markører delvis synlige** — samme grunn (640-bg
   blit på 480-skjerm). Skip-trail og fugler tegnes på riktig sted i scene-
   koordinater, men deres referansepunkt er på 640-kart, ikke 480.

**Test-pakke etter flipp:** 10 tester feiler (1047 grønne):

- `test_dialog_overlay`: Panel-sentrering forutsetter 640-bredde
- `test_night_factor`: Tavern-vindu-gating-tester forutsetter Y-koordinater
  fra 360-tall layout
- `test_per_port_rendering`: Port Royal og Havana-bake-tester forutsetter
  full-bredde sprites
- `test_port_props`: Tortuga-gameplay-bake forutsetter ground_top_y i 360
- `test_world_map[_tooltip]`: Markør-posisjon-assertions

Disse fikses i sub-steg 2-9 etter hvert som tilhørende rendering-vegger
regenereres. **IKKE fix-forsøk i sub-steg 1.**

**Verktøy:** `tools/fase_2_6_assess.py` — renderer alle scener på ny
oppløsning og lagrer 4× upskala-PNG for visuell sammenligning.

### Sub-steg 2 — World map background

- `world_map_builder.py`: regenerer kart-bakgrunn for 480×270.
- `data/ports.json`: re-skalér `world_map_position` (typisk × 0.75) eller
  re-balanser manuelt for å fortsatt få god spredning.
- Verifiser: world_map-scenen viser alle 4 havner uten klipping; voyage-
  scenen viser skip-trail på riktig sted.

### Sub-steg 3 — Tortuga backdrop + foreground

- `parallax_backdrops.py`: regenerer 6 dag-fase-varianter på 480×270.
- `parallax_backdrops.py`: regenerer foreground (fjell + hav) på 480×270.
- Cross-fade-logikken er uendret (er allerede generisk på surface-størrelse).

### Sub-steg 4 — Tortuga gameplay layer

- `port_buildings.py`: regenerer Tortuga gameplay-surface for ny oppløsning.
  Verden-bredde holdes 1600; det er bare Y-aksen som komprimeres til 270.
  Bygnings-ground_top_y må flyttes (typisk fra ~300 til ~225).
- Re-balansér bygningenes layout siden vi har 25 % mindre vertikal plass.
- NB: dette er **strukturelt** arbeid; sprites for bygninger trenger ikke
  re-tegnes ennå (de blir bare proporsjonalt mindre i scene-rommet).

### Sub-steg 5 — Player- og NPC-sprite-bump [LANDET 2026-04-30]

- `entities/player.py`: 10×20 → **24×40** (planen sa 32×48; redusert til
  24×40 for å holde proporsjonene mer i tråd med Kingdom-stil-referansen).
  Ny detalj: tricorn med plumet, hatt-bånd, ansikt med øyne+nese+skjegg,
  krage med V-snitt, frakk med 3 knapper, belte med spenne, bukser,
  støvler med varm aksent. 4.8× pikselbudsjett (200 → 960).
- `entities/npc.py`: Hawkins tilsvarende bumpet til 24×40 men med stein-
  paletten (kald, autoritær børsmester) — distinkt fra spillerens varm
  pirat-tone. Sølv-knapper, hvit krage, snurrebart.
- NPCSilhouette (background-props) holdt på gammel detaljnivå —
  protagonist-vs-bakgrunn-kontrast er ønsket.
- Player-collision-bbox følger sprite-bredde via `Player.width`-property.
- Camera-følge-logikken er allerede generisk på sprite-bredde.

### Sub-steg 6 — Bygning-sprite-detaljbump (Tortuga) [UTSATT]

- Re-tegn taverna, børshus, signature buildings, fyll-bygninger med utvidet
  detalj. ~50 % av piksel-arbeidet i fasen.
- **Status:** UTSATT til incremental work post-merge. Sub-steg 1-5+10 har
  brakt foundation-en på plass; per-bygning-polish kan landes som separate
  små commits på main uten å holde merge-en tilbake.

### Sub-steg 7 — Port Royal remaster

- Backdrop, foreground, gameplay-layer, signature buildings, props på 480×270.

### Sub-steg 8 — Havana remaster

- Som steg 7.

### Sub-steg 9 — Nassau remaster

- Som steg 7.

### Sub-steg 10 — Polish + ModernGL re-tuning [LANDET 2026-04-30]

- HUD-font 8 → 10 eller 12 px. **UTSATT** — fonten er fortsatt 8 px, og
  fungerer akseptabelt på 480×270 (vurderes mens vi spiller med ny
  oppløsning og bygger erfaring).
- ModernGL-tuning: bloom_radius 2.5 → 1.8, threshold 0.45 → 0.50, strength
  1.10 → 0.85 i `systems/post_fx.py`. Chunkier piksler trenger mindre blur
  ellers blir bildet søkkvått.
- Test-pakken (1057) verifisert grønn etter hver sub-steg.
- `tools/fase_2_6_*.png` viser alle 4 scener på ny oppløsning.
- `tools/postfx_high.png` viser shader-pipelinen med ny tuning på Tortuga.

### Sub-steg 11 — Merge til main

- Foundation (sub-steg 1-5+10) merger til main 2026-05-01.
- Per-bygning-detalj-polish (sub-steg 6-9) blir incremental work direkte
  på main siden den ikke er foundational.
- Bruk fast-forward merge — commits er hver for seg meningsfulle og
  begrunnelser er rene. Ingen squash.

---

## 3. Risikoer

- **Sprite-arbeid undervurderes.** Hvert havne-remaster er flere timer
  pikselarbeid. Realistisk tidsforbruk: 1-2 dager per havn for å holde
  kvalitetsnivået.
- **`world_map_position`-rebalanse kan kreve manuell justering** — å bare
  multiplisere med 0.75 gir kanskje for tette markører.
- **Test-pakke-baseline har ingen visuell oppfatning.** Tests kan være
  grønne mens scener ser ødelagte ut. Vi må manuelt screenshot-verifisere
  hvert steg.
- **HUD-overlapp.** Med 25 % mindre høyde kan HUD-toppen og dialog-bokser
  overlappe — krever layout-tweaks.

---

## 4. Akseptansekriterier

Fasen er ferdig når:

1. `python main.py --preset=low` viser alle 4 havner + voyage + world_map
   uten visuelle artefakter.
2. `python main.py --preset=high` viser samme med shader-pipelinen
   tunet for ny piksel-skala.
3. Hovedperson-spriten har synlig ansikt med øyne+skjegg, klesfolder,
   knapper. Sammenlignbar detalj med inspirasjons-Vei B i `tools/size_compare.png`.
4. Test-pakken (1057+) grønn.
5. `python benchmark.py` viser ≥60 FPS på alle scener (tilsvarer ≤16.7 ms
   frame time).
6. `BENCHMARKS.md` og `PROSJEKT.md` CHANGELOG oppdatert til v2.8.
