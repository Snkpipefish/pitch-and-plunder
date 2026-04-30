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

### Sub-steg 1 (TRIVIELL) — Flip konstantene + assess

- `RENDER_WIDTH` 640 → **480**, `RENDER_HEIGHT` 360 → **270** i `constants.py`
- `WORLD_WIDTH` 1600 (uendret — havne-verden-bredde er world-coordinate, ikke skjerm)
- `post_fx` `render_size` default → `(480, 270)`
- Kjør test-pakken og ta screenshots av alle scener for å dokumentere
  det visuelle bruddet (forventet: bakgrunner er 640 wide, klipper på
  høyre kant; world_map blit gir avkutting; Tortuga bygnings-layout går
  utenfor skjermen).
- IKKE forsøk å fikse bruddet i denne committen — bare dokumentér.

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

### Sub-steg 5 — Player- og NPC-sprite-bump

- `entities/player.py`: 16×16 → 32×48 med ny detalj (ansikt, øyne, skjegg,
  klesfolder, knapper, belte, støvler — bruk pikselbudsjettet).
- `entities/npc.py`: tilsvarende bump for alle NPC-er.
- Player-collision-bbox oppdateres til ny sprite-størrelse.
- Camera-følge-logikken er allerede generisk.

### Sub-steg 6 — Bygning-sprite-detaljbump (Tortuga)

- Re-tegn taverna, børshus, signature buildings, fyll-bygninger med utvidet
  detalj. ~50 % av piksel-arbeidet i fasen.

### Sub-steg 7 — Port Royal remaster

- Backdrop, foreground, gameplay-layer, signature buildings, props på 480×270.

### Sub-steg 8 — Havana remaster

- Som steg 7.

### Sub-steg 9 — Nassau remaster

- Som steg 7.

### Sub-steg 10 — Polish + ModernGL re-tuning

- HUD-font 8 → 10 eller 12 px.
- Bloom_radius i post_fx tunes for chunkier piksler (typisk 1.5 nedover —
  ellers blir bildet søkkvått).
- Verifiser test-pakke + alle scene-screenshots + `--preset=high` boot.

### Sub-steg 11 — Merge til main

- Squash-merge eller fast-forward avhengig av commit-hygiene.

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
