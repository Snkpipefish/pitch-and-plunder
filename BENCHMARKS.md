# Pitch & Plunder – Ytelsesmålinger

Hver rad i tabellen er én måling tatt med `python benchmark.py --duration 10`.
FPS-tallene representerer hvor raskt scenen *kunne* ha kjørt (invers av ren
compute frame time), ikke display-raten som alltid er capped på
`TARGET_FPS=30` via `Clock.tick`.

Mål (fra `PROSJEKT.md` seksjon 0):

- FPS: ≥30 stabilt, ≥25 minimum
- Peak RSS (heap-indikasjon): mål 80 MB, hard grense 150 MB
- Frame-allokering av Surfaces: 0

> **Målmaskin:** Målingene under er tatt direkte på målmaskinen (Pentium
> T4200 @ 2.00 GHz, 2 kjerner, GM45, 3.8 GB RAM, Linux Mint 21.3). Claude
> Code kjører i samme shell som benchmarken, så tallene er autentiske for
> den hardware vi designer mot.

---

## Commit 2 – Hovedløkke + placeholder-scene

Kjørt: 2026-04-18
Kommando: `python benchmark.py --scene placeholder --duration 10`
Miljø: målmaskin (Pentium T4200 / GM45 / 3.8GB RAM, Linux Mint 21.3, pygame-ce 2.5.7 / SDL 2.32.10 / Python 3.10.12)

| Metrikk | Verdi |
|---------|-------|
| Frames målt | 302 (capped 30 FPS × 10s ≈ 300) |
| FPS avg (compute) | 2370.98 |
| FPS min (compute) | 1197.57 |
| FPS 1% lav (compute) | 1208.85 |
| Frame time avg | 0.442 ms |
| Peak RSS | 96.0 MB |

### cProfile – topp hete funksjoner (cumulative)

```
ncalls  tottime  cumtime  funksjon
   302   9.861    9.861   Clock.tick (forventet – sover 33 ms)
   302   0.006    0.126   PlaceholderScene.draw
   302   0.106    0.106   Surface.fill
   604   0.014    0.014   Surface.blit
   302   0.012    0.012   pygame.event.get
```

### Vurdering

- **FPS:** Placeholder-scenen kan teoretisk kjøre ~2370 FPS. Vi har ca.
  2300× headroom over målet på 30 FPS. `Clock.tick` dominerer som ventet;
  det er sovingen som holder oss på 30 FPS.
- **Frame-allokering:** ingen per-frame Surface-allokeringer observert
  (`convert` kalles kun én gang ved scene-init).
- **Minnebruk:** 96 MB peak RSS er over 80 MB-målet, men under 150 MB hard
  grense. Dette er totalt prosess-RSS (Python + pygame + SDL + font) – når
  vi legger til parallax-surfaces i Commit 3 må vi holde øye med veksten.
- **Ingen flaskehalser** å adressere nå.

### Konklusjon

Grunnmuren er lett nok. Vi fortsetter til Commit 3 (parallax-system).

---

## Commit 3 – Parallax-system (3 lag) + kameratest

Kjørt: 2026-04-18
Kommando: `python benchmark.py --scene parallax_test --duration 10`
Miljø: målmaskin (Pentium T4200 / GM45 / 3.8GB RAM, Linux Mint 21.3, pygame-ce 2.5.7 / SDL 2.32.10 / Python 3.10.12)
Benchmark simulerer kamerabevegelse: holder "D" første halvdel, deretter "A"
for å dekke hele `[0, 960]`-intervallet.

| Metrikk | Verdi |
|---------|-------|
| Frames målt | 302 |
| FPS avg (compute) | 459.35 |
| FPS min (compute) | 179.66 |
| FPS 1% lav (compute) | 181.82 |
| Frame time avg | 2.260 ms |
| Peak RSS | 102.75 MB |

### cProfile – topp hete funksjoner (cumulative, ekskl. Clock.tick)

| tottime (s) | cumtime (s) | per frame (ms) | % av frame time | funksjon |
|-------------|-------------|----------------|-----------------|----------|
| 0.575 | 0.585 | 1.94 | **84%** | `Surface.fblits` (3 parallax-lag) |
| 0.029 | 0.029 | 0.096 | ~4% | `Font.render` (HUD, når kamera-int endrer) |
| 0.017 | 0.053 | 0.175 | ~8% | `ParallaxTestScene._ensure_hud` |
| 0.013 | 0.013 | 0.043 | ~2% | `Surface.blit` (HUD og hint) |
| 0.012 | 0.012 | 0.040 | ~2% | `pygame.event.get` |

### Vurdering – `fblits` tar 84% av frame time

Regelen fra `PROSJEKT.md` sier "hvis blit dominerer > 20%, stopp og vurder
`Surface.scroll()`". Vi har observert 84% dominans, så vi stopper og evaluerer
eksplisitt:

**Hvorfor fblits dominerer:** I en software-rasterisert parallax med 3 lag
ER lag-blittene hovedarbeidet i scenen – det er omtrent bare det scenen gjør.
Per frame blittes:
- Bakgrunn: 833×360 surface (clip til 640×360 synlig ≈ 230k px)
- Gameplay: 1601×360 surface (clip til 640×360 ≈ 230k px)
- Forgrunn: 1889×360 surface (clip til 640×360 ≈ 230k px)

Totalt ~691k pixels rastrert per frame. pygame blit-clipper til synlig
destinasjon, så ikke-synlige piksler koster lite.

**Hvorfor `Surface.scroll()` IKKE anbefales her:**
1. `Surface.scroll()` flytter piksler innad i én surface og krever at man
   fyller den avdekkede kanten etter hver scroll. Det hjelper når man vil
   unngå å tegne på nytt en hel surface; men vi tegner ikke bakgrunnen på
   nytt – vi blitter den som pre-rendret og lar SDL clip-e.
2. De tre lagene har forskjellige bredder OG forskjellige hastigheter.
   `scroll()` per lag ville kreve at vi vedlikeholder en forskjøvet
   «nå-tilstand» per lag og håndterer retningsskifter, noe som
   kompliserer koden betydelig.
3. Vi har svært mye headroom i absolutt målestokk: **2.26 ms av 33.33 ms
   frame-budsjett brukt (6.8%)** – dvs. ~14× headroom over 30 FPS. Dette
   er på målmaskinen (T4200/GM45), ikke på en raskere utviklings-CPU.

**Konklusjon:** `fblits` dominerer profilet fordi blit ER arbeidet i en
parallax-scene, men det er billig i absolutte tall på målmaskinen. Vi
beholder nåværende implementasjon og går videre til Commit 4.

**Andre observasjoner:**
- Peak RSS 102.75 MB (opp fra 96 MB i Commit 2). De tre lag-surfacesene
  tar til sammen ~4340×360×4 byte ≈ 6.1 MB. Økningen matcher.
- `Font.render` kalles 302 ganger (én gang per frame i testen) fordi
  kamera-int endrer seg nesten hvert frame med scroll-hastighet 80 px/s
  på 30 FPS ≈ 2.7 px/frame. Dette er lite cost i praksis (0.096 ms per
  frame). I produksjon kunne vi cache HUD-teksten per heltallsposisjon,
  men i et reelt spill viser ikke HUD kamera-x uansett.

---

## Commit 4 – Village-scene med bygninger, spiller og Hawkins

Kjørt: 2026-04-18
Kommando: `python benchmark.py --scene village --duration 10`
Miljø: målmaskin (T4200 / GM45 / Linux Mint 21.3), pygame-ce 2.5.7
Kamerabevegelse simulert som i Commit 3 (syntetiske keydown/-up for D og A).

| Metrikk | Verdi | Endring fra Commit 3 |
|---------|-------|----------------------|
| Frames målt | 302 | – |
| FPS avg (compute) | 435.30 | −24 |
| FPS min (compute) | 125.05 | −55 |
| FPS 1% lav (compute) | 128.67 | −53 |
| Frame time avg | 2.432 ms | +0.17 ms |
| Peak RSS | 103.37 MB | +0.6 MB |

### cProfile – topp hete funksjoner (ekskl. Clock.tick)

| per frame (ms) | % av frame time | funksjon |
|----------------|-----------------|----------|
| 2.12 | 87% | `Surface.fblits` (906 kall → 3 per frame: lag 0-1, entiteter, lag 2) |
| 0.040 | 2% | `Surface.blit` (bare hint-teksten) |
| 0.043 | 2% | `pygame.event.get` |
| 0.017 | 1% | `Player.update` + `Camera.set_x` |
| 0.023 | 1% | `ParallaxTestScene._build_*`-hjelpere kalt kun én gang (overhead fra init, ikke per frame) |

Alle øvrige oppføringer er <1%.

### Vurdering

- **Frame time økte fra 2.26 → 2.43 ms (+7%)**. Forventet fra ekstra fblits-
  kall (2 → 3 per frame) og en mer kompleks gameplay-surface.
- **7.3% av 33.3 ms frame-budsjett brukt, ~14× headroom over 30 FPS.**
- **Peak RSS: +0.6 MB**. Gameplay-surfaken er 1600×360×4 = ~2.3 MB, men
  den erstatter den gamle tomme 1600-surface-en fra parallax_test, så
  netto endring er liten.
- **Ingen nye flaskehalser.** Fblits fortsatt dominerende (87% av frame
  time), men total kost er lav.

### Visuell kontroll

Lagret screenshots (ikke commit-et) viser:
- Tavernaen med 2 varme vinduer, skilt, varm åpen dør og bakt gulv-glød
- Børshuset med trekantgavl, 4 søyler, 3 kalde vinduer, steinfasade
- Månen forblir i synsfeltet gjennom hele kameraets panorering
- Distante øyer og stjerner følger bakgrunnslagets drift
- Spiller og Hawkins står på gateplanet, player-sprite vender begge veier

### Konklusjon

Village-scenen ligger godt innenfor ytelsesbudsjett. Klar for Commit 5
(dynamisk lys).

---

## Commit 5 – Dynamisk lyssystem (3 lys med BLEND_RGB_ADD)

Kjørt: 2026-04-18
Kommando: `python benchmark.py --scene village --duration 10`
Miljø: målmaskin (T4200 / GM45 / Linux Mint 21.3), pygame-ce 2.5.7

3 lys aktive per frame:
1. Tavernaens svingende lanterne (radius 40, `COLOR_LANTERN_BRIGHT`, sinus ±3 px, periode 2 s)
2. Tavernaens dør-glød (radius 70, `COLOR_FLAME`, statisk)
3. Børshusets midtvindu (radius 60, `COLOR_STONE_LIT`, statisk)

Alle 3 gradienter pre-rendres i `LightingSystem.prewarm()` ved scene-init.
Tegnes per frame med `fblits(..., BLEND_RGB_ADD)`.

| Metrikk | Verdi | Endring fra Commit 4 |
|---------|-------|----------------------|
| Frames målt | 302 | – |
| FPS avg (compute) | 420.68 | −15 |
| FPS min (compute) | 118.72 | −6 |
| FPS 1% lav (compute) | 136.95 | +8 |
| Frame time avg | 2.495 ms | +0.06 ms (+3%) |
| Peak RSS | 103.70 MB | +0.33 MB |
| Gradient-cache-størrelse | 3 | – |

### cProfile – topp hete funksjoner (ekskl. Clock.tick)

| per frame (ms) | % av frame time | funksjon |
|----------------|-----------------|----------|
| 2.05 | 82% | `Surface.fblits` (4 kall per frame: lag 0-1, entiteter, lys, lag 2) |
| 0.15 | 6% | `LightingSystem.draw` inkl. batch-bygging (ekskl. fblits) |
| 0.023 | 1% | `math.sin` + `horizontal_offset` (lanterne-swing) |
| 0.040 | 2% | `pygame.event.get` |
| 0.030 | 1% | `Surface.blit` (HUD hint) |

### Vurdering

- **Kostnaden av å legge til 3 lys: 63 μs per frame.** Grensen i
  brukerspesifikasjonen var «revurder gradient-størrelser hvis frame time
  > 15 ms». Vi er på 2.50 ms – 6× under den grensen.
- **Gradient-prewarm** skjer én gang i scene-init; ingen gradient-
  generering per frame.
- **FPS 1% lav gikk opp** (128 → 137) tross ekstra arbeid – sannsynligvis
  støy i målingen; frame-tiden er så kort at små variasjoner i OS-
  scheduling slår gjennom.
- **RSS-endring marginal** (3 gradient-surfaces: ~81×81 + 141×141 +
  121×121 × 4 byte = ~130 KB).

### Visuell kontroll

Screenshots lagret (ikke commit-et):
- `village_lit_tavern.png`: tavernaen med varm glød fra vinduene,
  gullfarget glow fra lanterne-området over skiltet, sterk varm glød
  fra den åpne døren. Spilleren står i døråpningen og får varm rim-
  light.
- `village_lit_exchange.png`: børshuset med tydelig kald blå glød fra
  midtvinduet, søylene får subtil blå belysning. Kald autoritær ro i
  kontrast til tavernaen.
- Månen forblir dominerende i bakgrunnen.

Den tematiske varm/kald-kontrasten fra SVG-referansen er nå synlig.

### Konklusjon

Ytelse- og minnebudsjettet holder lett. Klar for Commit 6 (økonomi og
børs-overlay).

