# Pitch & Plunder – Prosjektspesifikasjon (v2.7)

Et 2D pixel art pirat-spill satt til Karibien under pirattiden (sent 1600-tall / tidlig 1700-tall). Spillet er et **100-dagers pirat-liv med score** (Jones in the Fast Lane-inspirert life-sim) der spilleren veksler mellom respektabelt fasade-liv (handel på børsen, bek-produksjon) og skjult piratvirksomhet (sabotasje, falske rykter) i fire karibiske havner. Score = gull i Tortuga-kista ved dag 100, arrestasjon eller død. Ytterligere inspirasjon fra **Sid Meier's Pirates!** (PSP) for verden og havner, og et planlagt **bek-/tjære-utvinningsspill** (Fase 4, sideview med rør/pumper/vogner) inspirert av Pitch Lake på Trinidad. Visuell stil er en hybrid av Kingdom: Two Crowns (atmosfærisk parallax og volumetrisk lys) og Monkey Island (varm karibisk palett, lesbare karakterer).

---

## 0. Målmaskin og ytelsesbudsjett (KRITISK)

**Per v2.7 (2026-04-30):** Målmaskinen er oppgradert. Den gamle T4200/GM45-maskinen
(2008-laptop, OpenGL 2.1) er **ikke lenger støttet** — vi kjører ikke spillet
på den, og spec-en trenger ikke ta hensyn til den. Se "Historisk kontekst"
nederst i seksjonen for hvorfor flere optimaliseringer i §3.1 fortsatt
står — de er fortsatt god praksis, men ikke lenger kritiske.

**Ny målmaskin:**

- **CPU:** AMD A10-5757M APU, 4 kjerner / 4 tråder @ 2.5 GHz, AVX/FMA/SSE4.2/AES
- **RAM:** 7.2 GB total (~3.7 GB ledig), swap aktiv
- **GPU:** AMD Radeon HD 8650G (Richland), 512 MB VRAM
- **OpenGL:** 4.5 (Compatibility), GLSL 4.50, ARB_compute_shader + SSBO + framebuffer_object
- **OS:** Linux Mint 21.3, Mesa 23.2.1
- **Python:** 3.10.12

**Ytelsesbudsjett (IKKE overskrid uten godkjenning):**

| Ressurs | Mål | Hard grense |
|---------|-----|-------------|
| FPS | 60 | 50 minimum |
| Minne (heap) | 300 MB | 500 MB |
| Parallax-lag samtidig | 5 | 7 |
| Dynamiske lyskilder | 12 | 20 |
| Partikler synlige samtidig | 150 | 300 |
| Surfaces allokert i game loop | 0 | 0 |
| Scene-verden bredde | 2400 px | 3600 px |
| GLSL post-FX-passes | 3 (bloom + grading + CRT) | 5 |

**Hvis FPS faller under 50 i noen scene: STOPP og profiler før du legger til mer.**

Intern render-oppløsning forblir 640×360. Den nye maskinen tillater shaders
på sluttbildet, ikke høyere kildeoppløsning — pixel art-stilen er låst.

### 0.1 Grafikk-presets (high / low)

Spillet skal ha to grafikk-presets, valgbart ved oppstart eller via meny:

- **`high` (standard på ny målmaskin):** ModernGL post-FX-pipeline aktiv
  (bloom, varm/kald grading, valgfri CRT-scanlines), 5 parallax-lag,
  12 dynamiske lys, 150 partikler.
- **`low` (fallback):** Ren pygame-rendering uten GL-pipeline. 3 parallax-lag,
  4 dynamiske lys, 20 partikler. Brukes hvis ModernGL ikke initialiserer
  (manglende driver, fjernskjerm uten GL, etc.) eller hvis bruker velger det.

Spill-koden tegner alltid til samme 640×360 surface. `low` viser surfacen
direkte; `high` sender den gjennom et GL-post-FX-pass før den vises. Ingen
gameplay-logikk skiller på preset.

### 0.2 Historisk kontekst (T4200-arven)

Frem til v2.6 var målmaskinen en 2008-laptop. Mange optimaliseringer i §3.1
(`fblits`, `Clock.tick`, blokkerte events, heltallskoordinater, pre-rendrede
gradients, palette cycling) ble innført for å holde 30 FPS på den maskinen.
**De fleste er fortsatt god praksis** og blir værende — vi river dem ikke ut
bare fordi vi har mer å gå på. Men:

- `TARGET_FPS = 30` → **60** (nå standard).
- `MAX_DYNAMIC_LIGHTS = 4` → **12** (still cap; ikke fjern).
- `MAX_PARTICLES = 20` → **150**.
- numpy-forbudet i §3.3 punkt 7 er **opphevet**.
- Mixer-avslåing i §3.1 punkt F er ikke lenger kritisk; lyd kan tas inn
  når spec-fasen tilsier det.
- `tick_busy_loop` er fortsatt unødvendig på 4-kjerners maskin, men ikke
  katastrofal slik den var på T4200.
- Surface-allokering i game loop er **fortsatt forbudt** — det er en GC- og
  memory fragmentation-bekymring uavhengig av maskin.

---

## 1. Designpilarer

1. **100-dagers score-løp** – Spillet er et endelig pirat-liv på 100 dager med klar slutt-tilstand og score. Dette gir tempo, stakes og målbar progresjon — ikke et åpent life-sim. Score = gull i Tortuga-kista ved dag 100, arrestasjon eller død.
2. **Handlinger driver tid** – Jones in the Fast Lane-inspirert: hver handling koster timer, dagen blir natt når dag-budsjettet er brukt, neste dag når natt-budsjettet er brukt. Tid er diskret og dyrt, ikke en bakgrunnsstrøm.
3. **Dobbeltliv med mistanke** – Respektabel kjøpmann om dagen (handel, bek-produksjon), pirat om natten (sabotasje, falske rykter). Mistanke-meter sporer guvernørens bevissthet; arrest ved terskel.
4. **Markedsmanipulasjon som offensiv mekanikk** – Sabotasje hever priser i target-havn, falske rykter senker dem — begge med 2-dagers forsinkelse. Spilleren påvirker tilbud/etterspørsel via piratvirksomhet og profitterer på prisbevegelsene på den lokale børsen.
5. **Historisk forankret fantasi** – Ekte karibiske havner (Tortuga, Port Royal, Nassau, Havanna), ekte bek-utvinning, men frihet til pirat-eventyr.
6. **Atmosfærisk pixel art** – Ikke detalj-tett, men stemningstett. Lys, silhuetter og begrenset palett.
7. **Ytelse over effekter** – Spillet skal gå smidig på en 2009-maskin. Hvis noe er "kulest mulig" vs "smidig", velger vi smidig.

---

## 2. Visuell identitet (NORD-STJERNE)

### Signaturscene: Tortuga Havn om natten

All visuell beslutning måles mot denne scenen. Hvis et element ikke passer inn i komposisjonen, hører det ikke hjemme i spillet.

**Komposisjon (sideview):**
- Indigo nattehimmel med full måne, strødde stjerner
- Fjerne øy-silhuetter som smelter inn i horisonten
- Hav med måne-refleksjon som skimrer (palette cycling)
- 2-3 ankrede skip i mellomdistansen med bittesmå lanterne-prikker
- Silhuett av havne-bygninger bak
- GAMEPLAY-LAG: Tavernaen til venstre (varm oransje glød), Børshuset til høyre (kaldt blått lys), spiller på gaten mellom
- Forgrunn: palmeblad og tauverk, spilleren passerer bak

**Tematisk betydning:** Den varme tavernaen (fristelse, pirater) og det kalde Børshuset (respektabel kapital) er spillets kjernekonflikt i visuell form. Spilleren beveger seg mellom dem med varm rim-light på én side, kald på den andre.

### Master-palett (30 farger, låst)

Alle assets bruker kun disse fargene. Palett-disiplin er det som gir den samlede stemningen.

**Himmel & natt:**
`#0a0e27` `#1a1f4d` `#2d3561`

**Måne & varmt lys:**
`#fff8e7` `#f5e6b3` `#ffd580` `#ffb347` `#ff8c42` `#d96c2e` `#e8c27a`

**Sjø:**
`#0f1829` `#1e2a4a` `#2a3a5e` `#4a5a8a`

**Varmt tre:**
`#1a1410` `#2a2018` `#3d3024` `#5c4a35`

**Kald stein/marmor:**
`#151a2a` `#1f2538` `#2d3548` `#3d4660` `#6b8bc7` `#8ba8d6`

**Karakterer:**
`#1a1620` (hatt) `#3d3548` (frakk) `#c49171` (hud) `#e8dcc4` (krage)

**Tåke & atmosfære (lav alpha):**
`#3a3a4a`

### Parallax-system (justert for målmaskin)

Landsby- og havne-scener bruker maks 5 lag. For Fase 1: kun 3 lag.

**Fase 1 (3 lag):**
| Lag | Innhold | Hastighet |
|-----|---------|-----------|
| 1 | Himmel + måne + stjerner + hav + skip (alt bakt sammen) | 0.2 |
| 2 | Gameplay (bygninger, spiller, NPC, gateplan) | 1.0 |
| 3 | Forgrunn (palmer, tauverk) | 1.3 |

**Fase 2+ utvidelse (maks 5 lag):**
| Lag | Innhold | Hastighet |
|-----|---------|-----------|
| 1 | Himmel + måne + stjerner | 0.0 |
| 2 | Fjerne øyer + hav | 0.2 |
| 3 | Ankrede skip + havne-bakgrunn | 0.5 |
| 4 | Gameplay | 1.0 |
| 5 | Forgrunn | 1.3 |

Bakgrunnslag (1, 2, 3) bakes sammen ved scene-innlasting til én eller to pre-rendrede surfaces. Kun gameplay-lag tegnes dynamisk.

Implementasjonslogikk:
```python
# Ved scene-init: pre-render bakgrunnslag en gang
self.background_surface = self._render_background_layers_once()

# I draw(): blit ferdige surfaces med heltallskoordinater
screen.blit(self.background_surface, (int(-camera.x * 0.2), 0))
screen.blit(self.gameplay_surface, (int(-camera.x * 1.0), 0))
screen.blit(self.foreground_surface, (int(-camera.x * 1.3), 0))
```

### Lyssystem (justert for målmaskin)

**Nøkkelregel:** Lys-masker pre-renderes én gang per scene-innlasting og caches. ALDRI generer radial gradient i game loop.

**Strategi:**
1. Ved scene-init: kall `create_radial_gradient(radius, color)` for hver unike kombinasjon og lagre som cached Surface
2. Statiske lys (taverna-vinduer, måne, børshus) bakes inn i bakgrunnen ved scene-innlasting
3. Kun 2-4 dynamiske lys tegnes per frame
4. Ingen full-skjerm `BLEND_RGBA_MULT` hver frame – bruk forhåndsmikset mørke-lag bakt inn i bakgrunnen

**For Fase 1 – enklere tilnærming:**
- Tegn varme/kalde "glød-rektangler" rundt vinduer med `BLEND_ADD` (billigere enn radial)
- Én svingende lanterne med pre-rendret radial gradient
- Ingen full-skjerm mørke-overlay – scenen er allerede mørk via palettvalg

```python
class LightingSystem:
    def __init__(self):
        self.cached_gradients = {}  # (radius, color) -> Surface
    
    def get_gradient(self, radius: int, color: tuple) -> pygame.Surface:
        key = (radius, color)
        if key not in self.cached_gradients:
            self.cached_gradients[key] = self._create_radial(radius, color)
        return self.cached_gradients[key]
    
    def draw_dynamic_lights(self, surface, lights):
        # Bruk fblits for batch-blitting med samme blend-mode
        batch = [(self.get_gradient(l.radius, l.color), l.pos) for l in lights]
        surface.fblits(batch, special_flags=pygame.BLEND_RGB_ADD)
```

### Palette cycling (effektiv på gammel hardware)

Palette rotation på 8-bit surfaces er raskere enn pre-rendrede frames:
1. Last vann-sprite som 8-bit palettized surface
2. Hver 200ms: roter 4-6 palett-indekser til venstre
3. Kall `surface.set_palette_at(i, new_color)` – ingen pixel-manipulasjon, kun palett-lookup

Brukes på: måne-refleksjon, lanterne-flammer, fakler.

### Partikler (strengt budsjett)

Maks 20 synlige samtidig. Ingen per-pixel alpha – bruk enkle rektangler eller små pre-rendrede sprites. Bruk `fblits()` for å tegne alle partikler i én batch.

---

## 3. Teknisk stack

- **Språk:** Python 3.10+
- **Motor:** pygame-ce (Community Edition)
- **Avhengigheter:** `pygame-ce` (kjernen). Fra v2.7: `moderngl` + `numpy` for
  shader-pipelinen i `high`-preset (valgfri runtime, lazy-imported i
  `systems/post_fx.py` slik at `low`-preset fortsatt kan kjøre uten dem).
- **OS:** Linux (Mint 21.3 primært)
- **Intern render-oppløsning:** 640×360
- **Skalering:** `pygame.SCALED` med fallback til software nearest-neighcbor
- **Target FPS:** 60 (oppgradert fra 30 i v2.7)
- **Fullskjerm:** F11 toggler
- **Save-system:** Én JSON-fil (`saves/savegame.json`)

### 3.1 Pygame-optimaliseringer (anbefalt, ikke lenger kritiske)

Disse stammer fra v2.0–v2.6 da målmaskinen var T4200/GM45. På den nye
A10-/HD 8650G-maskinen er de **anbefalt god praksis**, ikke kritiske —
unntatt der det er eksplisitt markert.

**A. Bruk `Surface.fblits()` for batch-rendering (pygame-CE-spesifikt)**

`fblits` er målbart raskere enn `blits` på svak CPU fordi den hopper over per-element type-sjekk. Bruk for partikler, parallax-fliser, og gruppert sprite-tegning:

```python
# Ikke gjor dette i en lokke:
for particle in particles:
    surface.blit(particle.image, particle.pos)

# Gjor dette i stedet:
surface.fblits([(p.image, p.pos) for p in particles])

# Med blend flag:
surface.fblits(batch, special_flags=pygame.BLEND_RGB_ADD)
```

**B. `Clock.tick()` – IKKE `tick_busy_loop()`**

`tick_busy_loop` brenner 100% CPU på én kjerne for timing-presisjon. På en 2-kjerners CPU er dette katastrofalt.

```python
clock = pygame.time.Clock()
while running:
    dt = clock.tick(TARGET_FPS) / 1000.0  # Gir OS pustehull
```

**C. Blokker events du ikke bruker**

Event-køen kan fylles med musebevegelser og andre unødvendige events. Blokker dem én gang i `main.py`:

```python
pygame.event.set_blocked([
    pygame.MOUSEMOTION,
    pygame.ACTIVEEVENT,
    pygame.VIDEOEXPOSE,
    pygame.VIDEORESIZE,
    pygame.WINDOWEXPOSED,
    pygame.WINDOWHIDDEN,
    pygame.WINDOWFOCUSGAINED,
    pygame.WINDOWFOCUSLOST,
])
```

**D. `Surface.scroll()` for horisontal parallax**

Flytter pixel-data innenfor en surface uten full re-blit. Merkbart billigere på scrollende bakgrunner:

```python
# I stedet for a blit-e hele bakgrunnen pa nytt:
background.scroll(dx=-scroll_amount, dy=0)
# Fyll den nye kanten som ble avdekket
background.blit(new_column, (width - scroll_amount, 0))
```

**E. Heltallskoordinater ved rendering**

Float-koordinater tvinger pygame til sub-pixel-blending (dyrere). Bevar float internt for fysikk, cast til int ved blit:

```python
screen.blit(sprite, (int(self.x), int(self.y)))
```

**F. Skru av mixer i Fase 1**

Lyd er ikke i Fase 1. Per v2.7 ikke lenger kritisk for ressurs-bruk, men
fortsatt ren oppstart. Tas inn når lyd-fasen begynner.

```python
pygame.display.init()
pygame.font.init()
# IKKE pygame.init() som initialiserer alt
```

**G. ModernGL post-FX (v2.7+, kun `high`-preset)**

Når `high`-preset er aktivt, opprettes en GL-kontekst på toppen av
SDL-vinduet og 640×360-renderingen sendes som tekstur gjennom et 2-3
shader-passes:

1. **Bloom-pre-pass:** brightpass (luminans > terskel) + 5-tap blur. Forsterker
   måne-glød og lanterner uten å vaske ut paletten.
2. **Color grading:** varm/kald split etter spillets dobbeltliv-tema —
   varm-shift på taverna-side, kald-shift på børshus-side. Implementeres
   som LUT eller direkte fragment-uniform.
3. **CRT (valgfri):** subtile scanlines + barrel distortion. På/av i meny.

Pipeline må kunne skrus av runtime hvis init feiler — i praksis: prøv å lage
GL-kontekst, fang `moderngl.Error` / `pygame.error`, fall tilbake til ren
`pygame.display.flip()`. Spillet skal aldri krasje pga. GL-init.

### 3.2 Environment-variabler (settes før pygame.init)

I `main.py`, helt øverst før `import pygame`:

```python
import os
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"  # Stille oppstart
os.environ["SDL_HINT_RENDER_SCALE_QUALITY"] = "0"  # Nearest-neighbor, crisp pixel art
os.environ["SDL_VIDEO_CENTERED"] = "1"  # Sentrer vindu
import pygame
```

### 3.3 Generelle pygame-optimaliseringer (OBLIGATORISK)

1. **`.convert()` / `.convert_alpha()` på ALLE laste-operasjoner.** Uten dette bruker pygame 10x mer CPU per blit.
2. **Aldri opprett Surface-objekter i `update()` eller `draw()`.** All allokering skjer i `__init__()` eller scene-loading.
3. **Cache alle rendrede tekster.** `font.render()` er dyrt – kall én gang per unike streng, lagre som Surface. Re-render kun når teksten endres.
4. **Pre-render parallax-bakgrunn én gang ved scene-innlasting.**
5. **Unngå `pygame.Surface.fill()` med alpha** – fyll én gang ved init, ikke per frame.
6. **Bruk colorkey i stedet for per-pixel alpha** der mulig (sprites uten gjennomsiktighet-gradering).
7. ~~Ingen numpy i Fase 1-3.~~ **Opphevet i v2.7** — numpy er tillatt; brukes
   for å laste piksel-data inn i GL-teksturer i ModernGL-pipelinen.
8. **Bruk `pygame.transform.scale()`** (nearest-neighbor), aldri `smoothscale()` – smoothscale er 5-10x tregere og ødelegger pixel art uansett.

### 3.4 Ytelses-benchmark (obligatorisk Commit 2)

En `benchmark.py` skal finnes i roten og kjøre 10-sekunders test som viser:
- FPS gjennomsnitt / min / 1% lav
- Frame time (ms)
- Minnebruk (via `resource.getrusage()`)
- **cProfile topp-20 heteste funksjoner**

```python
import cProfile
import pstats

def benchmark_scene(scene_class, duration_sec=10):
    profiler = cProfile.Profile()
    profiler.enable()
    # ... kjor scene ...
    profiler.disable()
    stats = pstats.Stats(profiler).sort_stats("cumulative")
    stats.print_stats(20)  # Topp 20 funksjoner
```

Scriptet kjøres etter hver fase og resultatet limes inn i `BENCHMARKS.md`.

---

## 4. Prosjektstruktur

```
pitch-and-plunder/
├── main.py                      # Entry point, scene manager
├── benchmark.py                 # Ytelsestest med cProfile
├── constants.py                 # Opplosning, farger, taster
├── requirements.txt
├── README.md
├── PROSJEKT.md                  # Denne filen
├── BENCHMARKS.md                # Ytelsesmalinger per fase
├── .gitignore
│
├── scenes/
│   ├── __init__.py
│   ├── base_scene.py
│   ├── village.py
│   ├── exchange.py
│   ├── world_map.py             # (fase 2)
│   ├── extraction.py            # (fase 4)
│   └── combat.py                # (fase 3)
│
├── systems/
│   ├── __init__.py
│   ├── economy.py
│   ├── save.py
│   ├── input.py
│   ├── lighting.py              # Med aggressiv caching
│   ├── parallax.py
│   └── particles.py             # Bruker fblits for batch
│
├── entities/
│   ├── __init__.py
│   ├── player.py
│   ├── npc.py
│   └── commodity.py
│
├── ui/
│   ├── __init__.py
│   ├── menu.py
│   └── hud.py
│
├── assets/
│   ├── sprites/
│   ├── parallax/
│   ├── lights/
│   └── fonts/
│
├── data/
│   ├── commodities.json
│   └── npcs.json
│
└── saves/
    └── .gitkeep
```

---

## 5. Utviklingsfaser (MVP-først)

Hver fase slutter med spillbart build + benchmark-måling.

### Fase 1 – Landsby (sideview) + børs
- 3 parallax-lag (bakgrunn pre-rendret, gameplay, forgrunn)
- Spiller vandrer med A/D
- Kamera følger, verden maks 1600 px bred
- Taverna til venstre (statisk, varmt lys bakt inn)
- Børshus til høyre, E åpner børs
- Børs-overlay: 4 varer, kjøp/selg
- Priser drifter hver 10. sekund
- HUD: gull, dag, scene
- 2-4 dynamiske lyskilder (én svingende lanterne, én glød fra døråpning)
- Tåke (3-4 partikler), ildfluer (3-5 partikler) – tegnes med `fblits`
- Save ved scene-bytte og avslutning
- F11 fullskjerm
- **Benchmark-mål: 30 FPS stabilt**

### Fase 2 – Verdenskart + seiling (KOMPLETT — Fase 2A + 2B)

**Fase 2A** (komplett v2.3): markedsdybde med daglig oppdatering og
regimer, dag-natt-syklus, bek-produksjon med upkeep, lagerbegrensning,
transaksjonsgebyr. Se `PHASE_2A_RETROSPECTIVE.md`.

**Fase 2B** (komplett v2.4): verdenskart-scene 640×360 med 4 havner
(Tortuga + Port Royal + Havana + Nassau), aktiv seiling med akselerert
klokke (75 sek/dag at sea vs 180 i havn), per-havn marked med
bias-priser og regimer som tikker parallelt under reise, ObservedPrice-
modell med stale-UI på kart-tooltip, reise-bekreftelse-dialog med
gull-trekk og blokkering, voyage-resume via save/load, dev-mode med
F5 hot-reload av balance.json og F1-F4 debug-teleport. Stub-havner
har funksjonell børs men deler Tortugas layout — distinkt karakter
kommer i Fase 3. Se `PHASE_2B_RETROSPECTIVE.md`.

### Fase 2.5 – Havn-atmosfære per havn (KOMPLETT — v2.5)

Se `PHASE_2_5_RETROSPECTIVE.md` og `FASE_2_5.md`. Ren visuell fase
som ga hver havn distinkt identitet, dag/natt-lys-gating via sprite-
varianter, og animerte bål/ild-kilder via palette-cycling.

### Fase 3 – 100-dagers pirat-liv med score (NESTE)

Pivot fra åpent life-sim til Jones in the Fast Lane-inspirert score-
løp. Handlinger driver tid (12 h dag-budsjett + 12 h natt-budsjett per
dag) — dag/natt-syklus går fra real-time til handlings-drevet.
Spiller kan sabotere (hever priser i target-havn, +10%, 2 dagers
delay) og spre falske rykter (senker priser i target, −10%, 2 dagers
delay) fra tavern-natt-meny; kjøpe rykter (`regime_preview`,
`price_spike_warning`); hvile i rom; gjemme gull i per-havn caches
(Tortuga-cachen teller i score, de andre beskytter kun mot arrest);
og investere i bek-anlegg (500 gull i tavern-dag-meny i Tortuga).
Mistanke-meter + arrestasjon, random events (voyage + port), tre
game-over-årsaker (dag 100, arrest, død). Score = gull i Tortuga-
cachen ved slutt. Se `FASE_3.md` for full spesifikasjon.

### Fase 2.6 – Visual remaster (NESTE etter Fase 3)

**Status:** Planlagt 2026-04-30 i v2.7. Sequencing: kan kjøres parallelt med
Fase 3 (mekanikk-arbeid berører ikke sprite-/oppløsning-laget) eller som
egen fokusert fase.

Pivot fra 640×360 + 16×16-sprites til **480×270 + 32×48 hovedsprite**
(vei B etter side-ved-side-sammenligning, se `tools/size_compare.py`).
Eksisterende moody Kingdom/Monkey Island-stemning og 30-farger-paletten er
**uendret** — kun pikselskala og sprite-detaljnivå endres.

**Begrunnelse:** Spilletest-tilbakemelding: "alt er litt smått og
upersonlig". 16×16 = 256 piksler å fordele over hatt+frakk+hud+skjorte —
for lite til ansiktsdetaljer. 32×48 = 1536 piksler (6× budsjett) gir plass
til ansikt med øyne+skjegg, klesfolder, hatt-silhuett, knapper, belte,
støvler. 480×270 × 4 = 1920×1080 (perfekt heltallsskala på FullHD).

**Omfang:**

1. `RENDER_WIDTH/HEIGHT` 640×360 → 480×270 i [constants.py](constants.py).
2. Re-tegne ALLE sprites med utvidet pikselbudsjett — ikke nearest-upskala.
   Bruk de ekstra pikslene til ekte detaljer.
3. Re-rendre ALLE pre-rendrede parallax-bakgrunner per havn på ny
   oppløsning. Tortuga først (signaturscene, stress-test), deretter Port
   Royal, Havana, Nassau på samme mal.
4. HUD-fonten Public Pixel 8 px → 10-12 px for lesbarhet.
5. ModernGL post-FX: render_size-parameter til `(480, 270)`. Bloom-radius
   tunes ned (chunkier piksler ⇒ mindre blur ellers blir bildet søkkvått).
6. Alle scene-tester må re-baseline-es for ny oppløsning.

**Eksplisitt utenfor scope:** Bytte til lyse/mettede farger (Seablip-stil)
ble vurdert og forkastet — brukeren vil beholde stemning. Master-paletten
er låst.

### Fase 4 – Bek-utvinning (sideview mini-game)
### Fase 5 – Dyp simulering + hendelser

(Detaljer senere – disse utformes når Fase 3 er stabil.)

---

## 6. Kjernemekanikker – detaljer

### Økonomi / børs
- Hver `Commodity`: `id`, `name`, `base_price`, `current_price`, `volatility`, `price_history`
- `Market.tick()`: `current_price = base_price * (1 + random drift innen volatility)`
- Kjøp/salg spread: 2% hver vei
- `inventory: dict[str, int]`

### Kontroller
| Tast | Handling |
|------|----------|
| A / Venstre | Gå venstre |
| D / Høyre | Gå høyre |
| E | Interagér |
| ESC | Meny / lukk overlay |
| Enter | Bekreft |
| F11 | Fullskjerm |

---

## 7. Data-filer

### `data/commodities.json`
```json
{
  "commodities": [
    {
      "id": "sugar",
      "name": "Sukker",
      "base_price": 40,
      "volatility": 0.15,
      "description": "Basisvare fra plantasjene."
    },
    {
      "id": "rum",
      "name": "Rom",
      "base_price": 75,
      "volatility": 0.20,
      "description": "Destillert fra sukker. Hoyt ettersport av marinen."
    },
    {
      "id": "tobacco",
      "name": "Tobakk",
      "base_price": 90,
      "volatility": 0.10,
      "description": "Stabil vare med god margin."
    },
    {
      "id": "pitch",
      "name": "Bek",
      "base_price": 55,
      "volatility": 0.25,
      "description": "Tettingsmiddel for skipsskrog."
    }
  ]
}
```

### `data/npcs.json`
```json
{
  "npcs": [
    {
      "id": "hawkins",
      "name": "Borsmester Hawkins",
      "location": "tortuga_exchange",
      "dialog_greet": "Velkommen til borsen."
    }
  ]
}
```

### `saves/savegame.json`
```json
{
  "version": 1,
  "player": {
    "gold": 500,
    "inventory": {"sugar": 0, "rum": 0, "tobacco": 0, "pitch": 0},
    "current_scene": "village",
    "position": [320, 280]
  },
  "market": {
    "day": 1,
    "commodities": {
      "sugar": {"current_price": 40.0},
      "rum": {"current_price": 75.0},
      "tobacco": {"current_price": 90.0},
      "pitch": {"current_price": 55.0}
    }
  }
}
```

---

## 8. Startverdier (Fase 1)

- Startgull: 500 dublooner
- Starttvarer: 0 av hver
- Startscene: `village`
- Startposisjon: midt på gaten foran Børshuset
- Dag: 1
- Pristick: hver 10. sekund

---

## 9. Kodekonvensjoner

- Type hints på alle funksjoner
- Docstrings på klasser
- Konstanter i `constants.py`
- Data-drevet design (JSON)
- Scene-klasser arver `BaseScene`
- Alt tegnes på 640×360 surface, så skaleres
- Engelske identifikatorer, norske brukertekster
- PEP 8, linjebredde 100
- Git commit per logisk enhet
- Heltallskoordinater ved alle blit-kall (`int(self.x)`)

---

## 10. `constants.py` – eksplisitt innhold

```python
import os

# Env vars MA settes for pygame.init
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
os.environ["SDL_HINT_RENDER_SCALE_QUALITY"] = "0"
os.environ["SDL_VIDEO_CENTERED"] = "1"

import pygame

# Opplosning og ytelse
RENDER_WIDTH = 640
RENDER_HEIGHT = 360
DEFAULT_SCALE = 2
DEFAULT_WINDOW_SIZE = (RENDER_WIDTH * DEFAULT_SCALE, RENDER_HEIGHT * DEFAULT_SCALE)
TARGET_FPS = 30  # OBS: 30, ikke 60 – malmaskin krever dette

# Ytelsesgrenser
MAX_DYNAMIC_LIGHTS = 4
MAX_PARTICLES = 20
MAX_PARALLAX_LAYERS_PHASE_1 = 3
WORLD_WIDTH = 1600

# Events som skal blokkeres (reduserer event-ko-trykk)
BLOCKED_EVENTS = [
    pygame.MOUSEMOTION,
    pygame.ACTIVEEVENT,
    pygame.VIDEOEXPOSE,
    pygame.VIDEORESIZE,
]

# Palett (hex som RGB-tupler)
COLOR_SKY_DEEP = (10, 14, 39)
COLOR_SKY_MID = (26, 31, 77)
COLOR_SKY_HORIZON = (45, 53, 97)

COLOR_MOON_CORE = (255, 248, 231)
COLOR_MOON_HALO = (245, 230, 179)
COLOR_LANTERN_BRIGHT = (255, 213, 128)
COLOR_LANTERN = (255, 179, 71)
COLOR_FLAME = (255, 140, 66)
COLOR_EMBER = (217, 108, 46)
COLOR_WATER_GLINT = (232, 194, 122)

COLOR_SEA_DEEP = (15, 24, 41)
COLOR_SEA_MID = (30, 42, 74)
COLOR_SEA_LIGHT = (42, 58, 94)
COLOR_SEA_HIGHLIGHT = (74, 90, 138)

COLOR_WOOD_DARKEST = (26, 20, 16)
COLOR_WOOD_DARK = (42, 32, 24)
COLOR_WOOD_MID = (61, 48, 36)
COLOR_WOOD_LIGHT = (92, 74, 53)

COLOR_STONE_DARKEST = (21, 26, 42)
COLOR_STONE_DARK = (31, 37, 56)
COLOR_STONE_MID = (45, 53, 72)
COLOR_STONE_LIGHT = (61, 70, 96)
COLOR_STONE_LIT = (107, 139, 199)
COLOR_STONE_BRIGHT = (139, 168, 214)

COLOR_HAT = (26, 22, 32)
COLOR_COAT = (61, 53, 72)
COLOR_SKIN = (196, 145, 113)
COLOR_SHIRT = (232, 220, 196)

COLOR_FOG = (58, 58, 74)

# Gameplay
STARTING_GOLD = 500
MARKET_TICK_INTERVAL_SEC = 10.0
PLAYER_WALK_SPEED = 80
INTERACTION_DISTANCE = 40

# Stier
SAVE_PATH = "saves/savegame.json"
DATA_DIR = "data"
ASSETS_DIR = "assets"

# Taster
KEY_LEFT = (pygame.K_a, pygame.K_LEFT)
KEY_RIGHT = (pygame.K_d, pygame.K_RIGHT)
KEY_UP = (pygame.K_w, pygame.K_UP)
KEY_DOWN = (pygame.K_s, pygame.K_DOWN)
KEY_INTERACT = (pygame.K_e,)
KEY_MENU = (pygame.K_ESCAPE,)
KEY_CONFIRM = (pygame.K_RETURN,)
KEY_FULLSCREEN = (pygame.K_F11,)
```

---

## 11. Konkret oppgaveliste for Fase 1

**Når du leser denne filen, start slik:**

1. **Vis meg planen din** for Fase 1 før du skriver kode. List filer, rekkefølge, flaskehalser.
2. Vent på bekreftelse før du starter.

Deretter, én commit per logisk enhet:

### Commit 1 – Prosjekt-oppsett
- Opprett venv (`python3 -m venv venv`), aktiver, installer pygame-ce
- Skriv `requirements.txt` (`pygame-ce>=2.5.0`)
- `.gitignore`: `venv/`, `__pycache__/`, `saves/savegame.json`, `.vscode/`, `.idea/`, `*.pyc`
- Opprett mappestruktur med tomme `__init__.py`
- Implementer `constants.py` fra seksjon 10 (med env vars øverst)
- README med kjøringsinstruksjoner

**Bekreft at `python -c "import pygame; pygame.init(); print('OK')"` virker uten SIGILL eller crash.** Hvis det krasjer, prøv `pip install --upgrade --force-reinstall pygame-ce` eller rapporter feilen til brukeren.

### Commit 2 – Hovedløkke, scene manager, benchmark
- `main.py`: 
  - Importer `constants` først (setter env vars)
  - `pygame.display.init()` + `pygame.font.init()` (IKKE pygame.init() – unngår mixer)
  - `pygame.event.set_blocked(BLOCKED_EVENTS)`
  - pygame.SCALED-vindu med fallback
  - 640×360 intern surface
  - `clock.tick(TARGET_FPS)` (IKKE tick_busy_loop)
  - F11 toggle
- `scenes/base_scene.py`: abstrakt klasse
- Scene manager med `change_scene(name)`
- Placeholder-scene som viser `COLOR_SKY_DEEP`
- `benchmark.py`: kjører en scene 10 sekunder, rapporterer FPS min/avg/1%-lav, frame time, minne, **cProfile topp-20 funksjoner**
- Kjør benchmark og dokumenter i `BENCHMARKS.md`
- **Hvis FPS < 50 på tom scene: noe er feil, stopp og undersøk**

### Commit 3 – Parallax-system
- `systems/parallax.py`: `ParallaxLayer` (holder pre-rendret Surface), `ParallaxRenderer`
- Tre lag: bakgrunn (fargegradient + måne + stjerner bakt inn), gameplay (tom for nå), forgrunn (tom)
- Bruk heltallskoordinater ved blitting (`int(-camera.x * layer.speed)`)
- Vurder `Surface.scroll()` hvis kontinuerlig scrolling viser seg tregt
- Test med piltaster for å flytte kamera manuelt
- Benchmark igjen – skal fortsatt være 30 FPS stabil

### Commit 4 – Village-scene
- `scenes/village.py`: Tortuga-gate
- Pre-render hele bakgrunnslag ved init
- Pre-render gameplay-lag med bygninger
- Spiller-sprite med hatt-silhuett beveger seg med A/D
- Float-posisjon internt, `int()` ved blit
- Kamera følger, clampet til [0, WORLD_WIDTH - RENDER_WIDTH]
- NPC "Hawkins" foran Børshuset (statisk)
- Benchmark: ≥30 FPS

### Commit 5 – Lyssystem
- `systems/lighting.py`: `LightingSystem` med gradient-cache
- `Light`-dataklasse: pos, radius, color, flicker
- Pre-rendrede radial gradients (kun 3-4 unike kombinasjoner)
- Statiske lys bakes inn i gameplay-laget ved scene-init
- **Bruk `fblits()` for batch-blitting av dynamiske lys med `BLEND_RGB_ADD`**
- 2-3 dynamiske lys: svingende lanterne, taverna-døråpning, børshus-vinduer
- Benchmark: ≥30 FPS med lys aktivt

### Commit 6 – Økonomi og børs
- `entities/commodity.py`: `Commodity`-dataklasse
- `systems/economy.py`: `Market`, laster JSON, `tick()`, `buy()`, `sell()`
- `data/commodities.json` fra seksjon 7
- `scenes/exchange.py`: tastatur-navigert meny med pre-rendrede tekst-surfaces
- Cache rendrede priser – re-render kun når `tick()` kjører
- E åpner, ESC lukker

### Commit 7 – HUD og save
- `ui/hud.py`: gull, dag, scene-navn. Cache rendrede tekster, re-render kun ved endring
- `systems/save.py`: JSON serialisering av GameState
- Autosave ved scene-bytte og `pygame.QUIT`
- Fallback til startverdier hvis save mangler

### Commit 8 – Partikler (minimal)
- `systems/particles.py`: 
  - Maks 20 aktive, object pool (forhåndsallokert liste)
  - **Tegnes med `surface.fblits()` i én batch per frame**
  - Ingen nye Surface-allokeringer per frame
- 3-4 tåke-ellipser drifter over gateplan
- 3-5 ildfluer nær taverna
- **Endelig benchmark: ≥30 FPS med alt aktivt**

### Verifikasjon før Fase 1 er godkjent
- `python main.py` starter uten feil
- F11 veksler fullskjerm, skalering ser riktig ut (crisp pixel art, ingen blur)
- Spiller går jevnt, kamera følger
- Taverna har varm glød, børshus kald
- Tåke drifter, ildfluer flagrer
- E nær børshus åpner børs
- Priser endres synlig hvert ~10 sekund
- Kjøp/salg oppdaterer gull og inventar
- ESC lukker børs
- Lukker og gjenstarter spillet: tilstand bevart
- **Benchmark viser ≥30 FPS i village-scenen**
- **cProfile rapport vises i BENCHMARKS.md – ingen enkelt-funksjon dominerer over 20% av frame time**

**Stopp og vent på tilbakemelding før Fase 2.**

---

## 12. Art-strategi

- Placeholders først (fargede rektangler med små detaljer som hatt-silhuett)
- Gradvis erstatning med 16×16 eller 32×32 sprites (kun master-palett)
- Ressursene holdes i minne som `.convert()`-ede surfaces
- Gratis asset packs: Kenney.nl, itch.io – men verifiser at antall farger ikke sprenger paletten

---

## 13. Arbeidsflyt

- Kjør spillet etter hver endring
- Hvis noe ser feil ut visuelt: brukeren sender screenshot – du kan lese bilder
- Kjør benchmark etter hver fase, dokumenter i BENCHMARKS.md
- Hvis FPS < 25: STOPP og profiler, ikke legg til mer
- Foreslå forbedringer men ikke utvid scope uten godkjenning
- Git commit per logisk enhet
- Bruk `logging`-modulen, ikke `print()`

---

## 14. Feilmoduser å unngå

- **Surface-allokering i game loop** – dreper FPS umiddelbart på T4200
- **Ikke-konverterte surfaces** – 10x tregere enn konverterte
- **Radial gradient per frame** – pre-render og cache
- **Full-skjerm alpha-blit hver frame** – bakes inn i bakgrunn der mulig
- **Font.render() hver frame** – cache rendrede tekster
- **For mange lys** – maks 4 dynamiske
- **`tick_busy_loop()` i stedet for `tick()`** – brenner 100% CPU
- **`smoothscale()`** – bruk `scale()` for nearest-neighbor
- **Float-koordinater ved blit** – cast til int
- **Individuelle blit-kall i løkker** – bruk `fblits()` for batch
- **pygame.init() når du bare trenger display+font** – init mixer unødvendig
- **Scope creep** – Fase 1 skal være MVP, ikke alt
- **Hardkoding** – JSON for alt data
- **For mange farger** – master-palett er låst
- ~~**numpy i Fase 1-3** – unødvendig avhengighet~~ — opphevet i v2.7
- **Tapt save ved krasj** – autosave ved QUIT

---

## 15. Inspirasjon

- **Sid Meier's Pirates! (PSP, 2005)** – havner, fekting, dansescene, fraksjonsrykte
- **Kingdom: Two Crowns** – parallax, volumetrisk lys, silhuett
- **The Secret of Monkey Island (VGA)** – karibisk varme, lesbare karakterer, tablå-komposisjon
- **Pitch Lake, Trinidad** – historisk bek-sjø brukt av Walter Raleigh i 1595
- **Mark Ferraris color cycling** – palett-rotasjon for animert vann og flammer

---

## CHANGELOG

- **v2.7** (2026-04-30) – Målmaskin oppgradert: AMD A10-5757M / Radeon HD 8650G
  / OpenGL 4.5 erstatter T4200 / GM45 / OpenGL 2.1. T4200-støtte droppet
  (brukeren kjører ikke lenger på 2008-laptopen). Nytt budsjett: 60 FPS,
  300 MB heap, 5 parallax-lag, 12 dynamiske lys, 150 partikler, 3 GLSL
  post-FX-passes. To grafikk-presets innført (`high` med ModernGL post-FX,
  `low` som ren pygame-fallback). numpy-forbudet opphevet. ModernGL-pipeline
  spesifisert i §3.1.G: bloom + color grading + valgfri CRT. Pipeline init
  må alltid kunne fall tilbake til ren pygame ved GL-feil. **Fase 2.6
  Visual remaster planlagt:** 480×270 intern + 32×48 hovedsprites, paletten
  uendret (vei B etter side-ved-side-sammenligning av tre alternativer).
  **FlyingBirds-system landet** i `systems/flying_birds.py` — adresserer
  "fugler frosset i lufta" ved å legge til animerte flokker som flyr over
  himmelen (per-havn-konfig: måker på Tortuga, pelikaner på Nassau, duer på
  Havana, måker på Port Royal). Sove om natten via night_factor-gating.
  Render BAK gameplay-laget slik at bygnings-silhuetter okkluderer fugler
  ved tårn-passering. Frame-time-impact: ~0 (innenfor måle-støy).
  **ChimneySmoke-system landet** i `systems/chimney_smoke.py` — drivende røyk
  fra warm/cool-kilder per havn (Tortuga: smie + tavern-pipe; Port Royal:
  customs + exchange-pipe; Havana: bakeri + katedral; Nassau: bål + shack-
  pipe). Pool av 5 partikler per kilde, additiv blending, sprite-størrelse
  vokser med alder. Tegnes ETTER bygninger men FØR dynamiske lys slik at
  varme lyskilder farger røyken naturlig. Frame-time: 3.25 ms (vs 3.27 ms
  baseline) — innenfor støy. **ModernGL post-FX verifisert end-to-end** mot
  ekte Tortuga-render; parametre tunet (bloom_threshold 0.45, radius 2.5,
  strength 1.10, warm_cool 0.55) for synlig glød rundt lanterner og varm/
  kald split mellom taverna-side og børshus-side. `present()` har nå `flip`-
  flag for å støtte offscreen-readback i tester.
  **VoyageScene fikk også fugler** — 4 stk drifter sakte over havet med
  bredt høyde-bånd (18-300) og uten night-gating (`sleep_threshold=2.0`)
  siden voyage-scenen er kart-form, ikke sideview-natt. Frame-time 0.75 ms
  (vs 0.69 baseline). **Test-pakken (1121 tester) grønn etter passet.**
  **`python main.py --preset=low` boot+exit verifisert** under headless
  dummy-driver — autosave ved QUIT fungerer.
  **`python main.py --preset=high` boot+exit verifisert** under x11 —
  ModernGL-kontekst opprettes, pipeline kompilerer, full hovedløkke kjører
  med shader-rendering aktiv, autosave ved QUIT fungerer.
  **WorldMapScene fikk fugler** (4 stk, sakte drift) og **VoyageScene fikk
  skip-røyk-trail** (én dynamisk røyk-kilde som flyttes til skipets
  posisjon hvert frame, 12-partikkel pool, cool-tonet, kort lifetime).
  ChimneySmoke har nå `set_source_position()` for dynamiske kilder.
  Test-pakken (1057 tester) grønn etter hele v2.7-passet.
- **v2.6** (2026-04-20) – Fase 3-planlegging komplett, C3-0 landet.
  Designpilarer omformet: "Dobbeltliv + markedsmanipulasjon" blir
  "100-dagers score-løp + handlings-drevet tid + offensiv
  markedsmanipulasjon". Jones in the Fast Lane-inspirert pivot fra
  åpent life-sim til endelig spill med score. Nye mekanikker i
  Fase 3: handlings-tid (12+12 h per dag), sabotasje (+10% target
  pris, 2 dagers delay, mistanke +15), falske rykter (−10% target
  pris, 2 dagers delay, mistanke +8), rykte-kjøp
  (`regime_preview` + `price_spike_warning`), rom-meter med decay,
  mistanke-meter med arrestasjon ved terskel, per-havn gull-caches
  (Tortuga-cachen = score), bek-anlegg-kjøp gate, random events
  (voyage + port), score-overlay ved dag 100 / arrest / død.
  balance.json v1 → v2 med nye seksjoner (game, actions, suspicion,
  rest, rumors, sabotage, events) og utvidede pitch_lake-felt. Save
  v5 → v6 bumpes i C3-1. Se `FASE_3.md`.
- **v2.5** (2026-04-20) – Fase 2.5 komplett. Alle 4 havner har distinkt visuell identitet (Tortuga råhet, Port Royal autoritet, Havana grandiositet, Nassau lovløshet), bystruktur med fyll-bygninger og smug, slitasje/natur/statisk-lys-karakter, dag/natt-lys-gating via sprite-variant-snap (night_factor ≥ 0.5) og animerte bål/ild-kilder med palett-cycling (≤25 px budsjett per havn). 13 commits (C2.5-1 til C2.5-10 inkl. 2 vann-refleksjons-reverter som ble Fase 3-teknisk gjeld). Tester 577/577 (+159 fra v2.4). Ingen mekaniske endringer — ren visuell fase; 2B-balanse-parametere urørt. Se `PHASE_2_5_RETROSPECTIVE.md` for commit-historikk, designbeslutninger, brukertest-observasjoner og Fase 3-gjeld (bakgrunn-bygningslag HØY prioritet, Tortuga-tavern-silhuett-redesign, flere NPC-er, glatt dag/natt-fade).
- **v2.4** – Fase 2B komplett. Verdenskart-scene (640×360 top-down med 4 havn-markører + tooltip for sist sett priser), aktiv seiling mellom 4 havner (Tortuga, Port Royal, Havana, Nassau) med akselerert klokke (75 sek/dag at sea vs 180 i havn), per-havn marked med bias-priser og regimer som tikker parallelt for alle havner under reise, ObservedPrice-modell med fersk/stale/aldri-besøkt-tilstander, reise-bekreftelse-dialog med gull-trekk + blokkering ved insufficient gold, voyage-resume via save/load (deterministisk progress fra clock-state), dev-mode med F5 hot-reload av balance.json og F1-F4 debug-teleport. Stub-havner deler Tortugas layout — distinkt karakter kommer i Fase 3. Nested GameState v5 med per-domene-felter (PlayerState/WorldState/EconomyState/PitchLakeState). PortConfig + ports.json. balance.json med live/sesjon/nytt-spill hot-reload-kategorier. 16 hovedcommits (C1a–C10) + 2 patch-commits, 418 tester grønne (+231 gjennom 2B), 4.87/6.29 ms frame time (+0.26/+0.14 ms over 2A), 1.21 ms verdenskart, 1.25 ms voyage-scene. Se `PHASE_2B_RETROSPECTIVE.md`. Brukertest-protokollen ble droppet — provisoriske tall kan ikke meningsfullt balanseres før Fase 3-mekanikker (piratinntekter, møter, rykter) gir kontekst.
- **v2.3** – Fase 2A komplett. Markedsdybde (daglig oppdatering, regimer, trend-piler), dag-natt-syklus (6 pre-rendrede bakgrunner, sol/måne i verdenskoordinater med 1:1 kamera-offset og render-rekkefølge som gir fjell-okklusjon), bek-produksjon med daglig vedlikeholdskostnad, lagerbegrensning, transaksjonsgebyr. 18 commits (inkl. underversjoner), 187 tester grønne, 4.61-6.15 ms frame time. Se `PHASE_2A_RETROSPECTIVE.md`.
- **v2.2** – Fase 2 reformulert fra "verdenskart + seiling" til "markedsdybde + verdenskart + seiling" basert på Fase 1-spilletesting. Spilleren observerte at den mekaniske børsen er triviell å utnytte uten friksjon (tilbud/etterspørsel, transport-risiko, guvernør-mistanke, informasjons-kost). Disse komponentene adresseres i Fase 2 parallelt med kartscenen.
- **Fase 1 komplett.** Se Commit 9 for oppsummering og Fase 2 ikke påbegynt.
- **v2.1** – Lagt til seksjon 3.1 "Maskin-spesifikke optimaliseringer" med fblits(), Clock.tick() vs tick_busy_loop(), event.set_blocked(), Surface.scroll(), heltallskoordinater og mixer-avslåing. Ny seksjon 3.2 om environment-variabler (SDL_HINT_RENDER_SCALE_QUALITY, PYGAME_HIDE_SUPPORT_PROMPT). Utvidet benchmark til å inkludere cProfile topp-20. Oppdatert constants.py til å sette env vars før pygame-import og inkludere BLOCKED_EVENTS-liste. Commit 2 presiserer `pygame.display.init()` + `pygame.font.init()` i stedet for `pygame.init()`. Lagt til flere feilmoduser.
- **v2.0** – Justert for målmaskin (Pentium T4200, GM45, 3.8GB RAM). Target FPS 30. Parallax-lag redusert til 3 i Fase 1. Lys pre-rendres og caches strengt. Maks 4 dynamiske lys, 20 partikler. Python 3.10+.
- **v1.0** – Initial spesifikasjon. Sideview, hybrid Kingdom + Monkey Island-stil, 30-farge master-palett.
