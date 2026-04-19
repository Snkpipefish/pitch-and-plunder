# Pitch & Plunder – Fase 2B: Verdenskart, seiling, havner

Denne spesifikasjonen bygger på `PROSJEKT.md` (v2.3) og
`PHASE_2A_RETROSPECTIVE.md`. Les begge før du starter. Observasjonene 1–5 i
retrospektivet er ikke valgfri polish — de er blokkere for 2B og adresseres
i Commit 1a–3.

---

```
╔════════════════════════════════════════════════════════════════════╗
║                                                                    ║
║   ARBEIDSREGLER FOR FASE 2B — LES FØRST                            ║
║                                                                    ║
║   1. ALL KODE SKRIVES LOKALT i ~/prosjekter/pitch-and-plunder      ║
║      på main-branch. Ingen sandbox, ingen cloud-eksekusjon.        ║
║      Benchmark KJØRES på brukerens T4200-maskin, ikke estimeres.   ║
║                                                                    ║
║   2. STOPP ETTER HVER COMMIT og vent på grønt lys fra brukeren     ║
║      før neste commit starter. Rapporter:                          ║
║        - Hva ble gjort                                             ║
║        - Test-resultat (X/Y grønne)                                ║
║        - Benchmark-tall (begge scener)                             ║
║        - Eventuelle avvik fra plan                                 ║
║      Lærdom fra 2A: automatisk framgang gjennom flere commits      ║
║      tvang oss til å forkaste arbeid. Ikke gjør det.               ║
║                                                                    ║
║   3. ARBEID PÅ MAIN-BRANCH. Ingen git worktrees, ingen             ║
║      feature-branches. Lærdom fra 2A: worktrees skapte             ║
║      forvirring om hvor koden faktisk levde. Enkelhet vinner.      ║
║                                                                    ║
╚════════════════════════════════════════════════════════════════════╝
```

---

## 0. Kontekst og mål

### Hva Fase 2A leverte

Én havn (Tortuga) med daglig markedstakt, tre regimer per vare, dag-natt-
syklus i verdenskoordinater, bek-produksjon med vedlikeholdskostnad,
lasterom-begrensning, og transaksjonsgebyr. 18 commits, 187 tester,
frame time 4.61 ms lukket / 6.15 ms overlay. Brukertest konkluderte at
tempoet (180 sek/dag) og friksjonen (upkeep, gebyr, lasterom) får
spilleren til å ønske seg ut.

### Hva Fase 2B skal levere

**Kjerne:**

- Verdenskart-scene (top-down, 640×360, stilisert Karibia, ingen panning)
- Fire havner: Tortuga, Port Royal, Havana, Nassau
- Aktiv seiling med akselerert tid (75 sek/dag under seiling vs 180 i havn)
- Markedet i alle fire havner tikker parallelt under reise
- Per-havn prisbias + egne regimer per vare
- "Siste observert"-prissystem med stale-indikator for havner man ikke
  er i
- Flat avreise-kost per rute + upkeep/dager som passerer under reise

**Arkitektur (tech debt fra 2A-observasjoner):**

- `data/balance.json` for økonomiske konstanter, hot-reload i dev-mode
- Nested GameState (v5) med `player_state` / `world_state` / `economy_state`
- PortConfig som dataklasse, `data/ports.json` for havn-data
- RegimeManager port-dimensjonert
- Celestial-worldx flyttet fra hardkodet til per-havn config
- SRCALPHA fg-lag migrert til colorkey (~1.2 ms tilbake)

### Hva Fase 2B IKKE er

- Ingen skipskamp, kapring, eller fekting (Fase 3)
- Ingen rykte- eller mistanke-system (Fase 3/5)
- Ingen bek-utvinning-minispill (Fase 4)
- Ingen hendelser eller markedsmanipulasjon (Fase 5)
- Ingen fraksjons-politikk (Fase 3)
- Ingen flere skipsklasser — én "sloop" hele 2B
- Ingen mannskap, hull eller skipsstats utover cargo_capacity
- Ingen ekte sprites (fortsatt placeholders)
- Ingen lyd
- Ingen tilfeldige møter på sjøen (inaktiv reise i 2B; kommer i Fase 3)

---

## 1. Arbeidsregler (utvidet)

### 1.1 Lokal utvikling på main

Alle endringer skjer i `~/prosjekter/pitch-and-plunder` på main-branch.
Git-flow: `git add -p` for å velge, `git commit`, `git push` etter at
brukeren har bekreftet commit-resultat.

Hvis en commit viser seg mislykket etter rapport og brukeren ber om
revert: `git reset --hard HEAD~1` lokalt, og deretter ny
implementering. Ikke force-push før neste commit er klar.

### 1.2 Stopp-mellom-commits-protokoll

Etter hver commit, rapporter i dette formatet:

```
Commit Cx (hash): <kort tittel>

Hva ble gjort:
- <konkrete endringer>

Tester: X/Y grønne (Z nye i denne commit)

Benchmark (målmaskin):
- Port-scene lukket: X.XX ms
- Port-scene overlay: X.XX ms
- Verdenskart-scene: X.XX ms

Avvik fra plan: <hvis noen, ellers "ingen">

Klar for brukerverifisering.
```

Brukeren tester manuelt før grønt lys. Aldri start neste commit uten
eksplisitt "go".

### 1.3 Ingen worktrees

Bruk vanlig git på én branch. Hvis scenarioet virker å trenge worktrees
(parallelle eksperimenter, osv.): stopp og spør brukeren.

---

## 2. Arkitektur: Nested GameState (v5)

### 2.1 Strukturen

```python
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class GameState:
    version: int                   # 5
    player_state: "PlayerState"
    world_state: "WorldState"
    economy_state: "EconomyState"
    pitch_lake_state: "PitchLakeState"

@dataclass
class PlayerState:
    position_x: float              # innenfor nåværende scene
    gold: int
    inventory: dict[str, int]      # commodity_id -> units
    # NB: cargo_capacity er flyttet til ShipState

@dataclass
class WorldState:
    current_port: str              # "tortuga" | "port_royal" | "havana" | "nassau"
    clock: "GameClock"             # eksisterer fra 2A, uendret
    ship: "ShipState"
    voyage: Optional["VoyageState"] = None   # Non-None kun under seiling

@dataclass
class ShipState:
    class_id: str                  # "sloop" i 2B (eneste klasse)
    name: str                      # default "Sjarken", spiller kan navngi i Fase 3
    cargo_capacity: int            # fra ships.json via class_id, men overstyrbart

@dataclass
class VoyageState:
    from_port: str
    to_port: str
    depart_day: int                # hvilken spilldag avgangen skjedde
    arrival_day: int               # hvilken spilldag ankomsten forventes
    progress: float = 0.0          # 0.0 → 1.0, oppdateres per frame

@dataclass
class EconomyState:
    markets: dict[str, "MarketState"]                  # port_id -> marked
    regimes: dict[str, dict[str, "Regime"]]            # port_id -> commodity_id -> regime
    observed: dict[str, dict[str, "ObservedPrice"]]    # port_id -> commodity_id -> sist sett

@dataclass
class ObservedPrice:
    price: float                   # pris da spilleren sist så den
    day_seen: int                  # hvilken spilldag det var
    # Ingen regime-snapshot, ingen trend — bevisst.
    # Utdatert data skal ikke pretendere å si noe om retning.

@dataclass
class PitchLakeState:
    home_port: str                 # "tortuga" i 2B; struktur klar for Fase 4
    production_per_day: int
    upkeep_per_day: int
    pending_units: int = 0         # bufret produksjon ved full last eller fravær
```

### 2.2 Hvorfor denne oppdelingen

Hvert system eier ett felt:

- `PlayerState` endres av inventar-kjøp, bevegelse, gull-transaksjoner
- `WorldState` endres av scene-bytter, seiling, klokke
- `EconomyState` endres av RegimeManager, Market, observasjonslogikk
- `PitchLakeState` endres av PitchLake on_new_day

Lettere å resonnere om hvilke systemer som mutere hva. Og lettere å
skrive migrasjoner per underdomene i Fase 3+.

### 2.3 Viktige konsekvenser

**Cargo_capacity er skipets, ikke spillerens.** Når Fase 3 introduserer
større skip, endres kapasiteten automatisk ved `ship = new_ship`. Inventar
blir i PlayerState — det er "dine varer" — men grensen er skipets ror.

**PitchLake er port-tagget.** Produserer `on_new_day` uavhengig av hvor
spilleren er. Full-last-sjekk ser på Tortuga-havnens tilgjengelighet
(tenk: bekken lagres på kaia). Hvis `home_port != current_port`: produksjon
går til `pending_units`. Ved ankomst Tortuga: pending_units flyttes til
inventar (opp til ledig kapasitet).

**ObservedPrice har ingen regime- eller trend-felt.** Dette er
bevisst og er en del av designen. Utdatert data skal ikke lyve. UI
viser `?` for trend på stale data.

---

## 3. PortConfig og ports.json

### 3.1 Dataklasser

```python
@dataclass
class CelestialConfig:
    moon_worldx: int               # statisk, over "institusjonelt anker"
    sun_worldx_dawn: int
    sun_worldx_dusk: int

@dataclass
class PortConfig:
    id: str
    name: str
    world_map_position: tuple[int, int]    # (x, y) på 640×360 verdenskart
    scene_class: str                       # "scenes.port_village:PortVillageScene"
    world_width: int                       # scenens verdens-bredde
    celestial: CelestialConfig
    price_bias: dict[str, float]           # commodity_id -> multiplikator
    regime_weights: dict[str, dict[str, float]]  # cid -> {"rising": p, "stable": p, "falling": p}
```

### 3.2 Filformat: data/ports.json

```json
{
  "version": 1,
  "ports": {
    "tortuga": {
      "name": "Tortuga",
      "world_map_position": [410, 230],
      "scene_class": "scenes.port_village:PortVillageScene",
      "world_width": 1600,
      "celestial": {
        "moon_worldx": 1350,
        "sun_worldx_dawn": 1500,
        "sun_worldx_dusk": 100
      },
      "price_bias": {"sugar": 1.10, "rum": 1.10, "tobacco": 1.05, "pitch": 1.15},
      "regime_weights": {
        "sugar":   {"rising": 0.33, "stable": 0.34, "falling": 0.33},
        "rum":     {"rising": 0.33, "stable": 0.34, "falling": 0.33},
        "tobacco": {"rising": 0.33, "stable": 0.34, "falling": 0.33},
        "pitch":   {"rising": 0.40, "stable": 0.35, "falling": 0.25}
      }
    },
    "port_royal": {
      "name": "Port Royal",
      "world_map_position": [180, 260],
      "scene_class": "scenes.port_village:PortVillageScene",
      "world_width": 1200,
      "celestial": {
        "moon_worldx": 950,
        "sun_worldx_dawn": 1100,
        "sun_worldx_dusk": 100
      },
      "price_bias": {"sugar": 0.80, "rum": 0.85, "tobacco": 1.00, "pitch": 1.05},
      "regime_weights": {
        "sugar":   {"rising": 0.25, "stable": 0.40, "falling": 0.35},
        "rum":     {"rising": 0.30, "stable": 0.40, "falling": 0.30},
        "tobacco": {"rising": 0.33, "stable": 0.34, "falling": 0.33},
        "pitch":   {"rising": 0.35, "stable": 0.35, "falling": 0.30}
      }
    },
    "havana": {
      "name": "Havana",
      "world_map_position": [140, 140],
      "scene_class": "scenes.port_village:PortVillageScene",
      "world_width": 1400,
      "celestial": {
        "moon_worldx": 1100,
        "sun_worldx_dawn": 1300,
        "sun_worldx_dusk": 100
      },
      "price_bias": {"sugar": 1.05, "rum": 1.05, "tobacco": 0.75, "pitch": 1.10},
      "regime_weights": {
        "sugar":   {"rising": 0.35, "stable": 0.35, "falling": 0.30},
        "rum":     {"rising": 0.30, "stable": 0.40, "falling": 0.30},
        "tobacco": {"rising": 0.25, "stable": 0.40, "falling": 0.35},
        "pitch":   {"rising": 0.35, "stable": 0.40, "falling": 0.25}
      }
    },
    "nassau": {
      "name": "Nassau",
      "world_map_position": [420, 110],
      "scene_class": "scenes.port_village:PortVillageScene",
      "world_width": 1200,
      "celestial": {
        "moon_worldx": 950,
        "sun_worldx_dawn": 1100,
        "sun_worldx_dusk": 100
      },
      "price_bias": {"sugar": 1.00, "rum": 0.95, "tobacco": 1.05, "pitch": 0.90},
      "regime_weights": {
        "sugar":   {"rising": 0.33, "stable": 0.34, "falling": 0.33},
        "rum":     {"rising": 0.30, "stable": 0.40, "falling": 0.30},
        "tobacco": {"rising": 0.33, "stable": 0.34, "falling": 0.33},
        "pitch":   {"rising": 0.20, "stable": 0.40, "falling": 0.40}
      }
    }
  }
}
```

Tematisk forankring: Port Royal er britisk Jamaica (sukker/rom-overflod,
lav pris, moderat "falling"-risiko). Havana er spansk Cuba (tobakk-
plantasjer, billig tobakk, regime-tilting mot stable/falling). Nassau
er pirat-republikk (plunder-forsyningskjede, billig bek, regime-tilting
mot falling). Tortuga er smugler-premium på alt og har optimistisk
regime-tilting på bek p.g.a. PitchLake.

### 3.3 Scene-gjenbruk

Én klasse `PortVillageScene` parameterisert med `port_config`. Tortugas
eksisterende bygnings-plasseringer (Taverna, Børshus, havn-kant)
flyttes til config-nivå. For de andre tre havnene i 2B: minimalt oppsett
(gateplan, Børshus, Taverna, havn-kant). Ingen unike bygninger eller
signatur-scener ennå — det kommer når havnene skal føles distinkte i
Fase 3+.

**Hvor er verdenskart-inngangen?** Legg til en "dokket skip"-sprite i
havn-kanten (venstre side av scenen i Tortuga; konfigurerbar per havn).
Spilleren går dit, trykker E → åpner verdenskart-scene.

---

## 4. balance.json

### 4.1 Skille: balance vs config

- `data/ports.json` definerer **hva en havn er** (geografi, karakter).
  Endres sjelden, strukturelle.
- `data/balance.json` inneholder **tall du vil iterere på**. Endres ofte
  under kalibrering.
- Regel: hvis endring av et tall endrer gameplay-følelse, er det balance.
  Hvis det endrer hva en havn er, er det config.

### 4.2 Filformat: data/balance.json

```json
{
  "version": 1,
  "economy": {
    "starting_gold": 300,
    "transaction_fee": 5,
    "ship_starting_cargo_capacity": 40
  },
  "time": {
    "seconds_per_day_in_port": 180.0,
    "seconds_per_day_at_sea": 75.0
  },
  "pitch_lake": {
    "production_per_day": 2,
    "upkeep_per_day": 8
  },
  "travel": {
    "routes": {
      "port_royal-tortuga": {"days": 2, "gold": 10},
      "havana-tortuga":     {"days": 3, "gold": 15},
      "nassau-tortuga":     {"days": 4, "gold": 20},
      "havana-port_royal":  {"days": 3, "gold": 15},
      "nassau-port_royal":  {"days": 4, "gold": 20},
      "havana-nassau":      {"days": 5, "gold": 25}
    }
  },
  "regimes": {
    "drift_pct_rising":  [2.0, 4.0],
    "drift_pct_stable":  [-1.0, 1.0],
    "drift_pct_falling": [-4.0, -2.0],
    "noise_pct": 1.0
  },
  "observed": {
    "stale_threshold_days": 5
  }
}
```

### 4.3 Rute-nøkkel-konvensjon

Alfabetisk sortert, bindestrek-separert: `"{a}-{b}"` der a < b
leksikografisk. Oppslag:

```python
def route_key(a: str, b: str) -> str:
    return "-".join(sorted([a, b]))

def get_route(balance: Balance, a: str, b: str) -> RouteInfo:
    return balance.travel.routes[route_key(a, b)]
```

Unngår duplikatoppføringer og glemte motveier.

### 4.4 Hot-reload-kategorier (F5 i dev-mode)

Tre kategorier:

**Live-applicable (gjelder umiddelbart):**

- `economy.transaction_fee`
- `pitch_lake.upkeep_per_day`
- `pitch_lake.production_per_day`
- `regimes.drift_pct_*`
- `regimes.noise_pct`
- `travel.routes.*`
- `observed.stale_threshold_days`

**Sesjons-applicable (gyldig fra neste dawn):**

- `time.seconds_per_day_in_port`
- `time.seconds_per_day_at_sea`

Logger advarsel. Klokken hopper ikke.

**Nytt-spill-only (krever ny save for å tre i kraft):**

- `economy.starting_gold`
- `economy.ship_starting_cargo_capacity`

Logger tydelig at verdien ikke endres i gjeldende sesjon.

**Implementasjon:** `systems/balance.py` eier singleton `Balance` med
`reload()`-metode. Systemer leser via `balance.economy.transaction_fee`
hver gang (ikke caches ved init). Hot-reload emitter en `ToastQueue`-
melding: "Balance lastet på nytt" eller "Balance: X endringer gjelder
fra neste dawn".

### 4.5 Dev-mode-deteksjon

To måter å aktivere dev-mode, i prioritert rekkefølge:

1. **Fil-flagg:** `.devmode` i prosjektrota — høyest prioritet
2. **Env-variabel:** `PITCH_DEV=1`

```python
# systems/dev_mode.py
def is_dev_mode() -> bool:
    if (PROJECT_ROOT / ".devmode").exists():
        return True
    return os.environ.get("PITCH_DEV") == "1"
```

Legg `.devmode` i `.gitignore`. Brukeren toggler med `touch .devmode`
og `rm .devmode`. F5-tasten registreres kun hvis `is_dev_mode()` er
True ved main.py-start.

HUD i dev-mode: liten grå "DEV"-markør nede til høyre, slik at det er
visuelt tydelig at hot-reload er aktiv.

---

## 5. v4 → v5-migrering

### 5.1 Migreringsfunksjon

```python
def migrate_v4_to_v5(v4: dict, balance: Balance, ports: dict[str, PortConfig]) -> dict:
    day = v4.get("clock", {}).get("day", 1)
    
    # Tortuga-økonomien bevares nøyaktig — spillerens eneste marked i v4.
    tortuga_market = v4.get("commodities_state", {})
    tortuga_regimes = v4.get("regimes", {})
    
    # Andre havner initialiseres som "fersk new-game"
    other_markets = {
        pid: init_market_for_port(ports[pid]) 
        for pid in ["port_royal", "havana", "nassau"]
    }
    other_regimes = {
        pid: sample_regimes_from_weights(ports[pid])
        for pid in ["port_royal", "havana", "nassau"]
    }
    
    # Observed: kun Tortuga har data (spilleren er der)
    observed = {
        "tortuga": {
            cid: {"price": m["current_price"], "day_seen": day}
            for cid, m in tortuga_market.items()
        }
        # port_royal, havana, nassau: ingen oppføring = aldri observert
    }
    
    return {
        "version": 5,
        "player_state": {
            "position_x": v4.get("player_x", 320.0),
            "gold": v4.get("gold", 300),
            "inventory": v4.get("inventory_items", {}),
        },
        "world_state": {
            "current_port": "tortuga",
            "clock": v4.get("clock", {"day": 1, "seconds_into_day": 0.0}),
            "ship": {
                "class_id": "sloop",
                "name": "Sjarken",
                "cargo_capacity": v4.get(
                    "cargo_capacity", 
                    balance.economy.ship_starting_cargo_capacity
                ),
            },
            "voyage": None,
        },
        "economy_state": {
            "markets": {"tortuga": tortuga_market, **other_markets},
            "regimes": {"tortuga": tortuga_regimes, **other_regimes},
            "observed": observed,
        },
        "pitch_lake_state": {
            "home_port": "tortuga",
            "production_per_day": v4.get("pitch_lake", {}).get(
                "production_per_day", balance.pitch_lake.production_per_day
            ),
            "upkeep_per_day": v4.get("pitch_lake", {}).get(
                "upkeep_per_day", balance.pitch_lake.upkeep_per_day
            ),
            "pending_units": 0,
        },
    }
```

### 5.2 Tester (påkrevd før C1b lukkes — alle 7 må være grønne)

```
tests/test_save_v5_migration.py
```

1. **Load v4 save → v5 uten feil.** Tom stack trace på clean-path
   migrering.
2. **Tortuga-data bevares nøyaktig.** current_price, regime, inventar,
   gull verdi-for-verdi identiske.
3. **Andre havner får fersk marked + regimer fra config.** 
   Ikke-Tortuga-havner har `MarketState` med base-priser × price_bias, og
   regimer samplet fra port_config.regime_weights.
4. **Observed-dict har kun Tortuga-oppføring.** `"port_royal" not in
   observed`, `"havana" not in observed`, `"nassau" not in observed`.
5. **Skip default "Sjarken", cargo_capacity = v4-verdi.** Ikke 
   balance-default hvis v4 hadde eksplisitt cargo_capacity.
6. **v3 og eldre går via kjeden.** Test at v3 save lastes inn som v5
   gjennom v3→v4→v5-kjeden, ikke direkte.
7. **Round-trip: migrate → save til disk → load fra disk → sammenlign.**
   Verifiserer at alle nested dataclasses serialiseres og
   deserialiseres korrekt. Sammenlign dikt-for-dikt, ikke bare
   objekt-identitet.

Round-trip-testen fanger subtile serialiseringsfeil (tupler som blir
lister, enum-verdier som blir strenger) som ikke vises i minne-
basert migrerings-test.

---

## 6. Verdenskart-scene

### 6.1 Layout

- `WorldMapScene` i `scenes/world_map.py`
- 640×360 oppløsning, ingen panning, alt synlig samtidig
- Bakgrunn: stilisert Karibia med 4-5 øy-silhuetter
  - Havana i nordvest (øverst venstre) — Cuba
  - Nassau i nord (øverst høyre) — Bahamas
  - Tortuga nord Hispaniola (midten høyre-nede)
  - Port Royal i sørvest — Jamaica
- Bakgrunn pre-rendres én gang ved scene-init, holdes som Surface
- Hav-tekstur: enkel gradient + periodiske "bølge"-partikler
  (pre-rendret, animert via color cycling 200ms-takt hvis budsjett
  tillater)

### 6.2 Havn-markører

- Liten sprite (12×12 placeholder) på hver havn-posisjon fra ports.json
- Gjeldende havn: markert med varm ring (bruker COLOR_LANTERN-palett)
- Andre havner: kald ring (COLOR_STONE_LIT)
- Hover/fokus (pil-taster navigerer mellom havner): tooltip viser
  - Havn-navn
  - Distanse: "X dager reise"
  - Kost: "Y gull"
  - Hvis insufficient gold: "Trenger Y gull" (rødt)

### 6.3 Dag/natt på kartet

Himmel-gradient endres med `day_fraction` fra GameClock. Interpolasjon
mellom 4 tidspunkter: dawn (0.0) → noon (0.3) → dusk (0.7) → night
(1.0). Ingen sol/måne-sprites som vandrer — de "er" egentlig i havn-
verdenene, ikke over kartet.

Implementasjon: `sky_tint(day_fraction) -> (r, g, b)` returneres, og
bakgrunns-surfacen re-tint-es ved dag-overganger (ikke per frame).

### 6.4 Overgang kart ↔ havn

**Fra havn til kart:** spilleren går til havn-kant-sprite i
PortVillageScene, trykker E → 0.3s fade-ut → WorldMapScene laster →
fade-in. Spilleren ser kartet med nåværende havn markert.

**Fra kart til havn:** spilleren navigerer til en havn-markør med
piltaster, trykker E:

- Hvis samme havn som `world_state.current_port`: lukker kartet, går
  tilbake til havn-scenen (spilleren posisjoneres ved havn-kanten)
- Hvis annen havn: åpner reise-bekreftelse-dialog

**Reise-bekreftelse:** enkelt dialog-overlay som viser:

```
Seile til Port Royal?
Tid: 2 dager
Kost: 10 gull
[E] Bekreft   [ESC] Avbryt
```

På bekreft: trekker gull, setter `world_state.voyage = VoyageState(...)`,
bytter til `VoyageScene`.

---

## 7. Seilings-mekanikk

### 7.1 VoyageState

Lever i `world_state.voyage`, non-None kun under aktiv reise. Oppdateres
hver frame med progress.

### 7.2 Akselerert tid

Under seiling: `GameClock.seconds_per_day = balance.time.seconds_per_day_at_sea`
(75.0 sek). Ved ankomst: tilbake til `seconds_per_day_in_port` (180.0).

Implementasjon: GameClock spør WorldState ved hver tick:

```python
def current_seconds_per_day(world: WorldState, balance: Balance) -> float:
    if world.voyage is not None:
        return balance.time.seconds_per_day_at_sea
    return balance.time.seconds_per_day_in_port
```

### 7.3 Markedet tikker parallelt

`on_new_day`-hendelsen kjøres som normalt. RegimeManager iterer over
**alle fire havner** og kjører regime-overgang per havn per vare. 4 × 4
= 16 regime-decisions per daggry. Billig operasjon; ingen FPS-impact.

Market.on_dawn kjøres også per havn: 4 markeder får ny pris basert på
`port_config.price_bias × base_price × regime_drift × noise`.

Dette betyr at hvis spilleren reiser 4 dager, passerer 4 daggry, 4 ×
16 = 64 regime-decisions, og prisene i alle fire havner har utviklet
seg. Dette gjør arbitrasje ikke-trivielt: prisen du forventer ved
ankomst er ikke den du så ved avreise.

### 7.4 Ankomst

Ved `clock.day >= voyage.arrival_day`:

- Fade-ut på VoyageScene
- `world_state.current_port = voyage.to_port`
- `world_state.voyage = None`
- PortVillageScene lastes med target port_config
- Spilleren plasseres ved havn-kanten
- Toast: "Ankommet {port_name}"
- Alle priser i den havnen registreres umiddelbart i `observed` (fresh
  data, day_seen = current_day)

### 7.5 VoyageScene

Minimal scene under reise: kan være en enklere variant av verdenskart
som viser skip-sprite som beveger seg langs en kurve mellom
from_port og to_port, med himmel-gradient som viser dag/natt-
progresjon. Spilleren kan åpne inventaret og se tall, men kan ikke
avbryte reisen eller endre retning.

**Ingen avbryte-mulighet.** Once committed, go.

---

## 8. Havn-markeder

### 8.1 Pris-bias (base-pris-multiplikator)

Anvendes før regime-drift:

```python
effective_base = commodity.base_price * port_config.price_bias[commodity_id]
current_price = apply_regime_drift(effective_base, regime, balance.regimes)
```

Dette gir strukturell karakter til hver havn (sukker er billig i Port
Royal, uansett regime) mens regimet gir daglig variasjon på toppen.

### 8.2 Regimer per havn

RegimeManager utvides fra `dict[str, Regime]` til
`dict[str, dict[str, Regime]]` (port_id -> commodity_id -> Regime).
Overgangs-logikken er den samme per (port, commodity) — bare gjentatt
over havner.

Regime-sampling ved new_game eller migrering:

```python
def sample_regimes_from_weights(port_config: PortConfig) -> dict[str, Regime]:
    result = {}
    for cid, weights in port_config.regime_weights.items():
        regime_name = random.choices(
            list(weights.keys()), 
            weights=list(weights.values())
        )[0]
        result[cid] = Regime(regime_name, days_remaining=random.randint(3, 5))
    return result
```

### 8.3 ObservedPrice og "siste sett"-UI

Når spilleren er i en havn: prisene vises med full detalj, inkludert
trend-pil basert på regime (status quo fra 2A). `observed[port_id][cid]`
oppdateres kontinuerlig (eller minst ved hver dawn) med `price=current`
og `day_seen=current_day`.

På verdenskartet: hover på en annen havn viser "siste observert":

```
Port Royal — sist besøkt Dag 12 (7 d. siden)
Sukker:  sist 22 gull  ?
Rom:     sist 41 gull  ?
Tobakk:  sist 88 gull  ?
Bek:     sist 37 gull  ?
```

Hvis `day_seen` aldri satt (aldri besøkt): "Port Royal — aldri besøkt"
uten prisfelt.

**Stale-indikator:** hvis `current_day - day_seen > balance.observed.stale_threshold_days`
(default 5), render priser i grå tone (`COLOR_FOG`) med rød dagsteller.
Trend-pil erstattes med `?` (ikke vis retning på data som er for gammel
til å stole på).

UI-palett-map for data-tilstander:

- Fersk data: COLOR_STONE_LIT (hvit-blå, tillit)
- Stale data: COLOR_FOG (grå, ikke stol på)
- Ingen data: COLOR_STONE_DARK (mørk, kontekstløs)

---

## 9. Ytelseskrav per commit

Hver commit skal benchmarke BÅDE port-scene (eksisterende) og verdenskart-
scene (ny etter C5). Mål:

| Scene | Mål | Hard grense |
|-------|-----|-------------|
| Port-scene lukket | 4.5–5 ms | 10 ms |
| Port-scene overlay | 6–7 ms | 10 ms |
| Verdenskart-scene | < 5 ms | 10 ms |
| VoyageScene | < 5 ms | 10 ms |

Hvis noen commit bringer en scene over 10 ms: **STOPP** og optimaliser
før neste commit. Ingen akkumulering av regresjoner.

Rapporter i commit-meldingen format (alle tre verdier, selv om en
scene ikke ble endret — vi vil se effekter på eksisterende scener også).

Legg benchmark-resultat inn i `BENCHMARKS.md` per commit i tillegg til
rapportering til bruker.

---

## 10. Commit-plan

### C1a – balance.json-ekstraksjon + F5 hot-reload

**Hva:** flytt økonomiske konstanter fra `constants.py` til `data/balance.json`.
`systems/balance.py` med `Balance`-singleton og `reload()`. Dev-mode-
deteksjon. F5-tast registrert i main.py hvis `is_dev_mode()`. Toast-
varsel ved reload.

**Filer:**

- `data/balance.json` (ny)
- `systems/balance.py` (ny)
- `systems/dev_mode.py` (ny)
- `constants.py` (rydding — fjern flyttede konstanter, behold
  MARKET_TICK_INTERVAL_SEC-kommentar som historisk)
- `main.py` (F5-håndtering)
- `.gitignore` (legg til `.devmode`)
- `systems/economy.py`, `systems/pitch_lake.py` (les fra balance)

**Tester:**

- `test_balance.py`: load balance.json, reload med endret fil, 
  kategorisering av live/sesjon/nytt-spill verdier
- `test_dev_mode.py`: `.devmode`-fil og PITCH_DEV env prioritering

**Akseptansekriterier:**

- Spillet starter og oppfører seg identisk som 2A med default-verdier
- `touch .devmode && python main.py` aktiverer DEV-markør + F5
- Endre `transaction_fee` i balance.json → F5 → neste handel bruker
  ny verdi, toast vises

**Benchmark:** begge scener innenfor mål (kun port-scene eksisterer per C1a)

### C1b – Nested GameState + v4→v5-migrering

**Hva:** splitt GameState til nested dataclasses per seksjon 2.1.
Migreringsfunksjon. 7 tester.

**Filer:**

- `state/game_state.py` (nested strukturer)
- `state/player_state.py`
- `state/world_state.py`
- `state/economy_state.py`
- `state/pitch_lake_state.py`
- `state/ship_state.py`
- `systems/save.py` (v4→v5-migrering)
- Alle systemer som leste flat GameState: oppdater til nested (bør
  være mekanisk — field access, ikke logikk-endring)

**Tester:** 7 migrerings-tester per seksjon 5.2, pluss eksisterende
187 tester må fortsatt være grønne.

**Akseptansekriterier:**

- Eksisterende v4 save lastes og spillet kjører identisk
- Nytt spill starter med v5 direkte
- Round-trip-test grønn (disk-serialisering)

**Benchmark:** ingen regresjon — stille refactor, skal være ±0.1 ms

### C2 – PortConfig + ports.json + RegimeManager per havn

**Hva:** PortConfig-dataklasse, `data/ports.json` med alle 4 havner,
RegimeManager utvides til port-dimensjon. Per-havn marked initialiseres.
Tortuga fortsatt eneste spillbare havn (scene-bytte kommer i C5).

**Filer:**

- `data/ports.json` (ny)
- `config/port_config.py` (ny — PortConfig, load_ports)
- `systems/regime_manager.py` (utvid til per-port)
- `systems/economy.py` (markets per port)
- `state/economy_state.py` (dict[port_id, ...])

**Tester:**

- `test_port_config.py`: load ports.json, alle 4 havner parser, bias-
  sum-sanity, regime_weights summerer til ~1.0
- `test_regime_manager.py` (utvid): 16 regimer per dawn, per-port
  isolasjon

**Akseptansekriterier:**

- Tortuga spiller identisk, men under hood er det 4 markeder som tikker
- Save inkluderer alle 4 havners marked og regimer
- Regimer i ikke-Tortuga-havner kan observeres i en debug-logg ved
  dawn (kun i dev-mode)

**Benchmark:** port-scene uendret (±0.1 ms)

### C3 – Celestial per havn + colorkey fg-optimalisering

**Hva:** Celestial-worldx leses fra port_config i stedet for konstanter.
SRCALPHA fg-lag (fjell + hav) konverteres til colorkey-transparent
surface. Forventet ytelsesgevinst: ~1.2 ms tilbake på port-scene.

**Filer:**

- `entities/celestial.py` (les fra port_config via scene)
- `scenes/village_renderer.py` (colorkey fg-surface)
- `constants.py` (fjern MOON_WORLD_X, SUN_WORLD_X_DAWN, SUN_WORLD_X_DUSK)

**Tester:**

- `test_celestial.py` (utvid): celestial_x beregnes korrekt fra
  port_config, ikke fra konstanter

**Akseptansekriterier:**

- Tortuga-scene visuelt identisk
- Sol/måne beveger seg riktig
- Port-scene frame time redusert med 1.0–1.5 ms

**Benchmark:** port-scene 3.3–3.5 ms lukket forventet

> **Endring under implementering:** Opprinnelig spec delte C3 i
> to deler (celestial per havn + colorkey fg-optimalisering).
> Colorkey-delen ble forkastet — se 2A-retrospektiv addendum.
> C3 refererer derfor til kun celestial-refactor (commit 7c1def5).

### C4 – PortVillageScene (refactor Tortuga til parameterisert)

**Hva:** `scenes/village.py` flyttes/refaktoreres til
`scenes/port_village.py` som tar `port_config` som parameter.
Bygnings-plasseringer flyttes inline i `ports.json` (nytt felt
`buildings` per havn — færre filer enn separat port_layouts.json).
Tortuga fortsatt eneste spillbare — men nå gjennom parameterisert
scene-klasse.

**Filer:**

- `scenes/port_village.py` (ny; absorberer mye av village.py)
- `scenes/village_renderer.py` → `scenes/port_village_renderer.py`
- `data/ports.json` (utvid hver havn med `buildings`-felt)
- `config/port_config.py` (utvid PortConfig med buildings-liste)

**Tester:**

- `test_port_village_scene.py`: scene laster for Tortuga, alle bygninger
  på plass, havn-kant-interaksjon eksisterer

**Akseptansekriterier:**

- Tortuga ser identisk ut
- Scene-init tar <100 ms

**Benchmark:** port-scene uendret

### C5 – WorldMapScene + havn-markører + round-trip

**Hva:** WorldMapScene implementeres. Havn-kant-sprite i Tortuga
åpner kartet. Kartet viser alle 4 havner (Tortuga markert), lar
spilleren navigere med piltaster mellom markører, og E fra Tortuga-
markør går tilbake til Tortuga. Ingen faktisk reise ennå.

**Filer:**

- `scenes/world_map.py` (ny)
- `scenes/port_village.py` (havn-kant-interaksjon)
- `entities/ship_icon.py` (skip-sprite på kartet, plassert ved
  current_port)

**Tester:**

- `test_world_map.py`: scene laster, alle 4 markører på plass, navigasjon
  fungerer, E på current_port returnerer til PortVillageScene

**Akseptansekriterier:**

- Spilleren kan gå til havn-kant, trykke E, se kartet, navigere til
  Tortuga-markør, trykke E, tilbake i Tortuga
- Verdenskart-scenen benchmarker <5 ms

**Benchmark:** verdenskart-scene etableres som baseline (<5 ms); port-
scene uendret

### C6 – Tre stub-havner (Port Royal, Havana, Nassau) + scene-bytte

**Hva:** Minimale scener for de tre andre havnene. Hver har:
gateplan, Børshus med funksjonell børs, Taverna (lukket/placeholder),
havn-kant. Ingen unike bygninger eller signatur-atmosfære — det
utvikles når havnene skal føles distinkte i Fase 3+.

`port_layouts.json` eller inline-config får plassering for alle 4
havner.

Kart-klikk på annen havn går ennå ikke dit — det kommer med voyage i
C7. Men hvis spilleren kommer til en havn (eksempel: via debug-teleport
i dev-mode), skal scenen lastes og fungere.

**Filer:**

- `data/port_layouts.json` eller utvidelse av ports.json
- `scenes/port_village.py` (bruk layout-data)
- `systems/debug_teleport.py` (dev-mode only; F1-F4 = teleport til
  port 1-4 for testing)

**Tester:**

- `test_port_village_scene.py` (utvid): load av alle 4 havner, børs
  funksjonell i alle, havn-kant-sprite på plass i alle

**Akseptansekriterier:**

- Dev-mode: F1-F4 teleporterer til havnene. Hver har fungerende børs
  med havn-spesifikke priser (bias anvendt). Inventar og gull
  bevares ved teleport.

**Benchmark:** port-scene for hver havn <5 ms (stub-scener er mindre,
bør være raskere enn Tortuga)

### C7 – VoyageState + akselerert tid + ankomst

**Hva:** Reise-bekreftelse-dialog på kartet, VoyageState, VoyageScene,
akselerert klokke, ankomst-logikk. Debug-teleport kan fjernes eller
flyttes til en ren shortcut (F-taster i dev-mode fortsatt aktive for
regression-testing).

**Filer:**

- `state/voyage_state.py` (hvis ikke allerede i C1b)
- `scenes/voyage.py` (ny — skip som beveger seg mellom havner)
- `scenes/world_map.py` (reise-bekreftelse-dialog, kall til voyage)
- `systems/game_clock.py` (per-scene seconds_per_day)
- `systems/save.py` (håndter pågående voyage i save — spilleren kan
  lagre under reise)

**Tester:**

- `test_voyage.py`: voyage-state initialiseres, progress oppdateres,
  ankomst-trigger kjører riktig
- `test_game_clock.py` (utvid): akselerert tid under voyage, retur til
  port-tempo ved ankomst
- `test_save.py` (utvid): save og load under aktiv voyage

**Akseptansekriterier:**

- Velg Port Royal på kartet, bekreft reise, se VoyageScene i 2 dager
  (~150 sek), ankom Port Royal, se børsen med havn-spesifikke priser
- Markedet i alle 4 havner har utviklet seg under reisen (verifiserbart
  via observed-data)
- **Voyage resume:** save mid-voyage på dag 3 av 4, avslutt spillet,
  start på nytt og load. Spillet gjenoppretter `voyage.progress`,
  `voyage.depart_day` og `voyage.arrival_day` nøyaktig. Reisen fortsetter
  fra samme punkt — ikke hopp til ankomst, ikke nullstilt tidtaker, ikke
  re-trukket gull. GameClock fortsetter med seconds_per_day_at_sea frem
  til ankomst-dagen nås.

**Benchmark:** VoyageScene <5 ms; port-scene uendret; verdenskart uendret

### C8 – ObservedPrice + stale UI + trend "?" på gammel data

**Hva:** ObservedPrice registreres ved inngang i hver havn. Stale-logikk
og UI-variant på verdenskartet for å vise siste observerte priser per
havn.

**Filer:**

- `state/observed_price.py`
- `systems/economy.py` (oppdater observed ved scene-inngang og ved
  børs-åpning i gjeldende havn)
- `ui/world_map_tooltip.py` (ny — tooltip for havn på kartet)
- `ui/color_palette.py` (ny — UI-signal-palett: fersk/stale/ingen data)

**Tester:**

- `test_observed_price.py`: fersk/stale-klassifisering ved ulike
  day_seen-verdier
- `test_world_map_tooltip.py`: riktig info og formatering per tilstand

**Akseptansekriterier:**

- Aldri-besøkt havn viser "aldri besøkt"
- Nylig besøkt (<5 dager) viser fersk data med trend-pil
- Stale (>5 dager) viser grå tall + "?" for trend + rød dagsteller
- Ved retur til en havn: prisene oppdateres til ferske umiddelbart

**Benchmark:** ingen regresjon

### C9 – Reise-gull-kost + blokkering + polish

**Hva:** Gull trekkes ved avreise-bekreftelse. Blokkering hvis
insufficient gold. Polish på reise-flyten: toast ved avreise, toast ved
ankomst, UI-polish på reise-dialog.

**Filer:**

- `scenes/world_map.py` (gull-trekking + blokkering)
- `ui/voyage_confirm_dialog.py` (ny eller del av world_map.py)

**Tester:**

- `test_voyage_cost.py`: gull-trekking, blokkering, toast-varsling

**Akseptansekriterier:**

- Forsøk på reise med for lite gull blokkeres, toast viser "Trenger X
  gull"
- Gull trekkes ved bekreft-knapp, ikke ved ankomst
- Toast "Avreise mot {port_name}" ved start, "Ankommet {port_name}" ved
  ankomst

**Benchmark:** ingen regresjon

### C10 – Balansering + retrospektiv + final benchmark

**Hva:** Brukeren spiller 30+ minutter og gir balansering-feedback.
Iterer på travel_costs, price_bias, regime_weights i balance.json /
ports.json via hot-reload. Skriv `PHASE_2B_RETROSPECTIVE.md` i samme
format som 2A. Oppdater `PROSJEKT.md` CHANGELOG med v2.4 og oppdater
seksjon 5 (utviklingsfaser) til å reflektere at Fase 2 er komplett.

**Filer:**

- `PHASE_2B_RETROSPECTIVE.md` (ny)
- `PROSJEKT.md` (CHANGELOG + seksjon 5)
- `README.md` (oppdater feature-liste og kontroller)
- `BENCHMARKS.md` (endelig 2B-oppføring)
- `data/balance.json` og `data/ports.json` (etter kalibrering)

**Brukertest-protokoll (obligatorisk før retrospektiv skrives):**

- Minimum 20 minutters sammenhengende spilling
- Minimum 5 komplette reiser gjennomført, minst én A→B→A-syklus (retur
  til avreisehavn)
- Gull-progresjon: fra 300 startgull til minst 500 gull gjennom arbitrasje
  alene (ingen debug-tilskudd)
- Brukeren rapporterer subjektivt på disse punktene:
  - Føles reise-friksjonen (gull + dager) riktig kalibrert, eller for hard/for myk?
  - Er arbitrasje engasjerende beslutnings-arbeid, eller grind?
  - Er stale-UI på verdenskartet forståelig ved første møte?
  - Føles de fire havnene tematisk forskjellige fra hverandre over tid?
  - Er 75 sek/dag seiling-tempo riktig — for tregt, for raskt, eller bra?
- Hot-reload-iterasjon: juster `balance.json` og/eller `ports.json`
  basert på feedback i minst 2 runder før retrospektivet ferdigstilles.
  Dokumenter hver iterasjon i `PHASE_2B_RETROSPECTIVE.md` under
  "Balansering under C10".

**Akseptansekriterier:**

- Brukertest-protokoll over er fullført og dokumentert
- Retrospektivet dekker: hva ble bygget per commit, benchmark før/etter,
  brukertest-observasjoner (sitater), teknisk gjeld identifisert for
  Fase 3, rebalanseringsnotat med alle endrede tall
- Endelig benchmark dokumentert på målmaskin i `BENCHMARKS.md`

**Benchmark:** endelig måling på alle scener. Skal fortsatt være
under 10 ms hard grense, helst <7 ms for alle.

---

## 11. Verifikasjonsliste for Fase 2B-avslutning

- `python main.py` starter og kjører stabilt
- Alle 4 havner har fungerende børs med havn-spesifikke priser
- Verdenskart viser alle 4 havner, navigasjon fungerer
- Reise fra Tortuga til annen havn kjører gjennom VoyageScene, ankomst
  fungerer, prisene i målet er reflektert i børsen
- Markedet i alle 4 havner utvikler seg under reise (verifiserbart: reis
  4 dager, returner til Tortuga, sjekk at sukker-prisen har endret seg)
- Stale-data på verdenskart fungerer: havn man ikke har besøkt på 5+
  dager viser grå tall og "?" for trend
- Havn aldri besøkt viser "aldri besøkt", ingen prisfelt
- Reise-gull-kost trekkes ved avreise, blokkering ved utilstrekkelig
  gull
- Upkeep for PitchLake trekkes under reise (pending_units akkumuleres,
  realiseres ved retur til Tortuga)
- Save/load fungerer midt i en reise og gjenopptar voyage ved load
- Dev-mode aktiveres via `.devmode` eller `PITCH_DEV=1`, F5 hot-reloader
  balance.json, toast bekrefter
- Benchmark på målmaskin:
  - Port-scene lukket: ~4.6–4.7 ms (baseline opprettholdt; colorkey-
    optimalisering forkastet, se 2A-retrospektiv addendum)
  - Port-scene overlay: ~6 ms
  - Verdenskart-scene: <5 ms
  - VoyageScene: <5 ms
- Alle tester grønne (minimum ~220 totalt: 187 eksisterende + 30–40 nye).
  Vi skriver tester for enheter der kjøretest ikke fanger regresjon godt
  — ikke formelle tester for ting kjøretest dekker bedre.
- Ingen v4→v5-save-feil for eksisterende brukertest-saves
- Round-trip save-test grønn
- 30+ minutter brukertest utført uten krasj

---

## 12. Teknisk gjeld å ta inn i Fase 3 eller senere

Forventet teknisk gjeld ved 2B-slutt:

- **Stub-havner er tematisk tomme.** Port Royal, Havana, Nassau har
  fungerende børs men ingen unik atmosfære, signatur-bygninger, eller
  NPC-er. Behandles i Fase 3 når havner får fraksjoner, guvernører og
  taverne-rykter.
- **Ingen skipsvariasjon.** Én sloop-klasse. Fase 3 introduserer
  kapring, brigg, galleoner.
- **Ingen aktiv reise-mekanikk.** VoyageScene er visuell, ikke
  interaktiv. Fase 3 legger til tilfeldige møter på sjøen.
- **Sol-stutter under bevegelse** (nedarvet fra 2A, ikke adressert i 2B).
  Sub-pixel celestial-rendering utsatt.
- **Ingen regime-synlighet utenom trend-pil.** Vurdert i 2A; fortsatt
  obskurt. Ryktesystemet i Fase 3 bør gi indirekte regime-avsløringer.
- **Exchange overlay fortsatt SRCALPHA.** ~1 ms på åpen overlay.
  Lav prioritet.
- **Ingen lyd** (fortsatt).

---

## CHANGELOG

- **v1.0** – Initial Fase 2B-spesifikasjon.

