# Pitch & Plunder – Ytelsesmålinger

Hver rad i tabellen er én måling tatt med `python benchmark.py --duration 10`.
FPS-tallene representerer hvor raskt scenen *kunne* ha kjørt (invers av ren
compute frame time), ikke display-raten som alltid er capped på
`TARGET_FPS=30` via `Clock.tick`.

Mål (fra `PROSJEKT.md` seksjon 0):

- FPS: ≥30 stabilt, ≥25 minimum
- Peak RSS (heap-indikasjon): mål 80 MB, hard grense 150 MB
- Frame-allokering av Surfaces: 0

> **Merk om målmaskin:** Målingene under er tatt på utviklingsmaskinen, ikke
> på Intel Pentium T4200 / GM45. De fungerer som en relativ referanse; når
> vi får tilgang til målmaskinen skal vi kjøre det samme benchmarket der og
> dokumentere det i egen kolonne.

---

## Commit 2 – Hovedløkke + placeholder-scene

Kjørt: 2026-04-18
Kommando: `python benchmark.py --scene placeholder --duration 10`
Miljø: dev-maskin, Linux, pygame-ce 2.5.7 (SDL 2.32.10), Python 3.10.12

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
  På målmaskinen (med mindre andre Python-libs og annen systemoverhead)
  kan dette være lavere.
- **Ingen flaskehalser** å adressere nå.

### Konklusjon

Grunnmuren er lett nok. Vi fortsetter til Commit 3 (parallax-system).

---

## Commit 3 – Parallax-system (3 lag) + kameratest

Kjørt: 2026-04-18
Kommando: `python benchmark.py --scene parallax_test --duration 10`
Miljø: dev-maskin, Linux, pygame-ce 2.5.7 (SDL 2.32.10), Python 3.10.12
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
   frame-budsjett brukt (6.8%)** – dvs. ~14× headroom over 30 FPS.

**Konklusjon:** `fblits` dominerer profilet fordi blit ER arbeidet i en
parallax-scene, men det er billig i absolutte tall. Vi beholder nåværende
implementasjon og går videre til Commit 4. Hvis målmaskinbenchmarking (når
vi får tilgang) viser <30 FPS, revurderer vi (f.eks. kan vi gå direkte til
`subsurface`-basert source-rect-blit, eller bakt-smalere bakgrunn).

**Andre observasjoner:**
- Peak RSS 102.75 MB (opp fra 96 MB i Commit 2). De tre lag-surfacesene
  tar til sammen ~4340×360×4 byte ≈ 6.1 MB. Økningen matcher.
- `Font.render` kalles 302 ganger (én gang per frame i testen) fordi
  kamera-int endrer seg nesten hvert frame med scroll-hastighet 80 px/s
  på 30 FPS ≈ 2.7 px/frame. Dette er lite cost i praksis (0.096 ms per
  frame). I produksjon kunne vi cache HUD-teksten per heltallsposisjon,
  men i et reelt spill viser ikke HUD kamera-x uansett.

