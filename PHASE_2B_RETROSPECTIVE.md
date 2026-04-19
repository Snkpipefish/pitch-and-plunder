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

## Brukertest-observasjoner C8

Notert ved formell lukking av C8 (ObservedPrice stale-UI + tooltip +
UI-palett). Alle fire tooltip-tilstander visuelt verifisert
(current/aldri-besøkt/fersk/stale), markør-differensiering leses
umiddelbart, tooltip-tone er Sid Meier-saklig.

### HUD-tekst overlapper med himmel-gradient

Ikke-blokker, observert som perseptuelt artefakt: HUD-tekst oppe til
venstre (sted/gull/dag/bek-status) blander seg perseptuelt med
himmel-bakgrunnen i lyse dag-faser. Tekst kan se "doblet" ut der
den krysser farge-overganger i bakgrunnen.

**Status:** ikke funksjonelt problem, leselig. Noter for C10-polish.

**C10-vurderinger:**
- Subtil tekst-bakgrunn (semi-transparent STONE_DARKEST-rektangel
  bak HUD-teksten) — minst invasive løsning
- Tekst-outline (1 px mørk kant) — endrer font-rendering, kan se
  klumpete på 8 px Public Pixel
- Tekst-skygge (1 px offset i mørk farge) — mellomtilnærming

Anbefaling foreløpig: semi-transparent bakgrunns-rektangel med
COLOR_STONE_DARKEST og alpha ~120-140. Tester på alle 6 himmel-
varianter før låsing av valg.

---

## Brukertest-observasjoner C9 (under utvikling)

### Toast-fragmentering (notert under C9-implementasjon)

Tre scener eier nå hver sin ToastQueue-instans: PortVillageScene
(fra Fase 2A), WorldMapScene (C9 — for blokk-meldinger), VoyageScene
(C9 — for avreise-varsel). Ingen kommunikasjon mellom dem.

**Konsekvenser av fragmenteringen:**
- Avreise-toast vises på VoyageScene som umiddelbart laster etter
  start_voyage, ikke på WorldMapScene som ble forlatt — riktig
  visningssted, men krevde ekstra ToastQueue-instans.
- Hvis vi ville ha "Avreise mot X" som siste melding på kartet før
  scene-bytte, ville det krevd toast-overlevelse mellom scener.
- F5-balance-reload-toast vises kun på scenen som var aktiv ved
  reload; ingen historikk.

**Ikke C9-fix:** scope-creep. Notert for vurdering i C10 eller Fase 3:

- **Singleton-toast-system** i `ui/toast.py` med global ToastQueue.
  Scener pusher til den globale; main.py rendrer den uavhengig av
  scene. Krever at scene-bytte ikke clearer toaster automatisk.
- **Toast-overlevelse via SceneManager**: pass toast-queue inn ved
  scene-konstruksjon i factory. Mindre invasivt enn singleton.
- **Status quo**: per-scene-toasts er enkelt og fungerer. Ulempen
  er kun ved sjeldne overgangs-meldinger.

Anbefaling for C10/Fase 3: vurder singleton hvis flere meldings-
typer (vær-varsel, regimes, hendelser) kommer til. Hvis bare
voyage-relaterte meldinger forblir, behold per-scene.

---

## Status

- C1a–C8: lukket og verifisert
- C9: Reise-gull-kost + blokkering + polish — under utvikling
- C10: Balansering + retrospektiv

Endelig retrospektiv ved C10-lukking vil utvide denne fila med:
hva ble bygget per commit, ytelses-tall før/etter, brukertest-
observasjoner med sitater, teknisk gjeld for Fase 3, rebalansering-
notat med alle endrede tall.
