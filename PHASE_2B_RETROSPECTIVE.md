# Pitch & Plunder – Fase 2B retrospektiv (under utarbeidelse)

Skrives løpende per-commit som notat-base for endelig retrospektiv ved
C10-lukking. Detaljerte commit-rapporter ligger i `BENCHMARKS.md`.

---

## Brukertest-observasjoner C7

Notert ved formell lukking av C7 (commits C7a/C7b/C7c + C7c-patch +
C7c-patch-2).

### SEA_MID-dominans (perseptuell)

Bakgrunnens SEA_MID-stripe (108 px lys-blå mellom horisont y=36 og
SEA_DEEP-overgang y=144) oppleves som en sekundær "horisont" ved
første møte med VoyageScene. Øy-silhuetter plassert i denne sonen
(Nassau y=110, Havana y=140) leses som "flytende i en mellom-sone"
i stedet for å være tydelig forankret i hav.

**Status:** Løst i stor grad av havn-labels (C7c-patch). Når labels
identifiserer hver silhuett som et navn-festet sted, slutter
spilleren å lese plasseringen som geometrisk feil. Visuelt
symptom forsvinner med semantisk forankring.

**C10 polish-vurdering:** smalere SEA_MID-stripe, mørkere SEA_MID-
farge nærmere SEA_DEEP, eller større himmel-region (15-20% i stedet
for 10%). Lav prioritet siden labels løste hovedsymptomet.

### 75 sek/dag seiling-tempo

Brukertest opplevde tempoet som kjedelig — VoyageScene har ingen
interaktivitet (autopilot per spec §7.5), og uten innhold underveis
føles 75 sek/dag (≈ 150 sek for en 2-dagers reise) som dødtid.

**C10-vurderinger:**
- Kortere tempo (50 eller 40 sek/dag) — enkleste fix
- Ambient-toasts under reise (vær-observasjoner, dagsteller-varsel)
- Dagsteller i HUD som tikker synlig

**Forkastet:** "Skippe"-knapp som lar spilleren hoppe til ankomst.
Bryter spec §7.5 "once committed, go"-prinsippet og undergraver
friksjons-elementet reiser skal levere.

**Fase 3-territorium:** musikk, tilfeldige møter på sjøen, aktiv
seiling-mekanikk. Disse er per Chat 1-føring eksplisitt utenfor 2B-
scope.

### Benchmark autosave-regresjon (C7c-patch-2)

Latent bug siden C5/C6: `python benchmark.py --open-exchange` brukte
fersk `GameState()` (gold=0, tomme markeder, pitch_lake 0/0) og
trigget autosave via `PortVillageScene._open_exchange`. Den tomme
staten ble skrevet til prod-save og overskrev brukerens spilltest-
progresjon.

Manifesterte seg ikke før jeg traff samme test-vindu med en aktiv
save under C7c-patch-benchmarken.

**Fix:** `benchmark._disable_autosave_for_benchmark()` monkey-patcher
`save_module.save` til no-op før noen scene-kall. Universell
beskyttelse — dekker alle nåværende OG fremtidige autosave-stier.

**Lærdom:** dev-verktøy trenger samme test-disiplin som spill-koden.
Benchmark-prosessen er ikke en passiv observatør; den kan trigge
side-effekter som påvirker bruker-data. Bør sjekkes som en del av
verktøy-design, ikke etter at en bruker har mistet data.

---

## Status

- C1a–C7c-patch-2: lukket og verifisert
- C8: ObservedPrice stale-UI + tooltip + UI-palett — neste
- C9: Reise-gull-kost + blokkering + polish
- C10: Balansering + retrospektiv

Endelig retrospektiv ved C10-lukking vil utvide denne fila med:
hva ble bygget per commit, ytelses-tall før/etter, brukertest-
observasjoner med sitater, teknisk gjeld for Fase 3, rebalansering-
notat med alle endrede tall.
