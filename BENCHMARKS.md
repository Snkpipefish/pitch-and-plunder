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
