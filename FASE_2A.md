# Fase 2A – Markedsdybde, teknisk opprydding, bek-produksjon

Denne filen er den autoritative spesifikasjonen for Fase 2A. Den bygger på `PROSJEKT.md` (fortsatt gyldig) og `PHASE_1_RETROSPECTIVE.md` (observasjoner som informerer valg her). Les begge de eksisterende filene først.

---

## 0. Kontekst og mål

### Hva er gjort

Fase 1 leverte spillbar landsby-scene med Tortuga havn om natten, dynamisk lyssystem, atmosfæriske partikler, og en fungerende børs-overlay med 4 varer som drifter priser tilfeldig. Spillet går på målmaskinen (Pentium T4200, GM45, Linux Mint 21.3) med 270-370 FPS compute-margin. Se `PHASE_1_RETROSPECTIVE.md` for detaljer.

### Hvorfor Fase 2A eksisterer

Fase 1-spilletesting avdekket at den nåværende børsen har et strukturelt gameplay-problem: arbitrasje er trivielt lønnsomt fordi priser drifter tilfeldig (volatility 15-25%) mens spread bare er 2%. Optimal strategi er "vent til prisen drifter ned, kjøp, vent til den drifter opp, selg, gjenta". Det er ingen risiko, ingen ferdighet.

Fase 2A løser dette før vi bygger flere havner i Fase 2B. Hvis markedsmodellen er feil, er det bedre å rette én implementasjon nå enn fire senere.

### Tre pilarer for Fase 2A

1. **Teknisk opprydding** – betale teknisk gjeld fra Fase 1 før vi bygger på
2. **Markedsdybde** – regimer, lagerbegrensning, transaksjonsgebyr
3. **Bek-produksjon** – passiv inntekt fra Pitch Lake, forankrer tema og skaper eksport-incentiv

### Hva Fase 2A IKKE er

- Ingen verdenskart (Fase 2B)
- Ingen seiling (Fase 2B)
- Ingen flere havner (Fase 2B)
- Ingen interaktiv bek-utvinning-minispill (Fase 4)
- Ingen piratvirksomhet (Fase 3)
- Ingen rykter, mistanke eller hendelser (Fase 5)
- Ingen lyd
- Ingen ekte pixel art-sprites (fortsatt placeholders)

---

## 1. Teknisk opprydding (MÅ komme først)

Disse er teknisk gjeld identifisert i `PHASE_1_RETROSPECTIVE.md`. De må løses som de første 3 commits i Fase 2A. Å bygge markedsdybde på skjør kode multipliserer problemene.

### 1.1 VillageScene-splitt

**Problem:** `scenes/village.py` er ~470 linjer. Den håndterer rendering, input, NPC-plassering, bygnings-bakning, kamera, hint-linje, og eksponerer et gnaggent interface mot ExchangeOverlay.

**Løsning:** Splitt i logiske moduler:

```
scenes/village.py                 # Orchestrering, BaseScene-arv, ~150 linjer max
scenes/village_renderer.py        # Pre-rendrede lag + draw-løkke
scenes/village_buildings.py       # Taverna, Børshus, parallax-lag (pre-rendering)
entities/hint_indicator.py        # Logikk for "E åpne børs"-hint
```

Ingen funksjonell endring – bare arkitektonisk opprydding. Ytelse skal være identisk (±50 μs).

### 1.2 GameClock-klasse

**Problem:** `day` i GameState har vært konstant 1 siden Fase 1. `Market.tick()` kjører hver 10. sekund men teller ikke dager. `PHASE_1_RETROSPECTIVE.md` identifiserte dette som kritisk for Fase 5, men det er nå kritisk for Fase 2A også – regime-skift og bek-produksjon trenger en ekte dag-teller.

**Løsning:** Ny klasse `systems/game_clock.py`:

```python
@dataclass
class GameClock:
    """Sentral tids-autoritet. Alt som skjer over tid spør denne."""
    day: int = 1
    seconds_into_day: float = 0.0
    SECONDS_PER_DAY: float = 60.0  # Fase 2A: 60 sek/dag
    
    def update(self, dt: float) -> list[str]:
        """
        Oppdaterer klokken. Returnerer liste av hendelses-strings som 
        skjedde denne oppdateringen (f.eks. ["new_day"]).
        """
        self.seconds_into_day += dt
        events = []
        while self.seconds_into_day >= self.SECONDS_PER_DAY:
            self.seconds_into_day -= self.SECONDS_PER_DAY
            self.day += 1
            events.append("new_day")
        return events
    
    def progress_fraction(self) -> float:
        """0.0 ved daggry, 1.0 ved midnatt. Til senere dag/natt-syklus."""
        return self.seconds_into_day / self.SECONDS_PER_DAY
```

`GameState` får et `clock: GameClock`-felt. `main.py` gjør én `clock.update(dt)` per frame. Alle systemer (Market, PitchLake, RegimeManager) abonnerer på `"new_day"`-hendelser ved å sjekke return-listen.

**Migrering:** GameState bumpes fra v2 til v3. v2→v3 legger til `clock: GameClock(day=old_day, seconds_into_day=0.0)`. Eksisterende saves leses fortsatt.

### 1.3 Scene re-entry-refactor

**Problem:** `fresh_flags` i VillageScene (nevnt som "skjørt" i retrospektivet). Scene re-entry skjer f.eks. når Player lukker ExchangeOverlay – scene må vite om den fortsetter eller initialiseres på nytt.

**Løsning:** Formell livssyklus-API i `BaseScene`:

```python
class BaseScene:
    def on_enter(self, game_state: GameState, from_scene: str | None = None) -> None:
        """Kalles når scene blir aktiv. `from_scene=None` ved første oppstart."""
        pass
    
    def on_exit(self, to_scene: str) -> None:
        """Kalles før scene deaktiveres."""
        pass
    
    def handle_events(self, events): ...
    def update(self, dt): ...
    def draw(self, surface): ...
```

Scene-manager håndterer livssyklus, scenene slipper å huske state selv.

**Viktig:** Dette er nødvendig før Fase 2B legger til WorldMap og PortScenes. Hvis vi utsetter blir det eksponentielt dyrere å fikse.

### 1.4 GameState eier alt

**Problem:** Per retrospektivet eier GameState ikke alle felter – Player.x/y og Market.day synkes ved save. Det er ugjennomsiktig magi.

**Løsning:** GameState holder sannheten. Scenes/systemer refererer til GameState-felter direkte:

```python
@dataclass
class GameState:
    version: int = 3
    gold: int = STARTING_GOLD
    inventory: dict[str, InventoryItem] = field(default_factory=...)
    player_position: tuple[float, float] = (320.0, 280.0)  # Player leser/skriver hit
    current_scene: str = "village"
    clock: GameClock = field(default_factory=GameClock)
    commodities_state: dict[str, CommodityState] = field(default_factory=dict)
    regimes: dict[str, RegimeState] = field(default_factory=dict)  # NY
    pitch_lake: PitchLakeState = field(default_factory=PitchLakeState)  # NY
    cargo_capacity: int = 40  # NY
```

Ingen `_sync_state()`-metode. Save skriver GameState direkte, load leser GameState direkte.

### Verifikasjon etter teknisk opprydding (Commit 1-3)

- `python main.py` starter identisk med Fase 1-sluttresultat
- Benchmark viser ingen regresjon (±100 μs per frame aksepteres)
- Save-fil fra Fase 1 (v2) lastes og migreres til v3 uten feil
- GameClock teller dager synlig i HUD: "Dag 1 → Dag 2 → ..." etter 60 sek

**Stopp etter Commit 3. Verifiser med bruker før gameplay-features.**

---

## 2. Markedsdybde

### 2.1 Regime-system

**Konsept:** Hver vare er i ett av tre regimer som styrer hvordan prisen drifter. Regimer bytter hver 3-5 dager (tilfeldig). Spilleren ser IKKE regimet direkte – de må lese markedet fra pris-historikk.

**Regimer:**

| Regime | Drift-bias | Volatilitet-multiplier |
|--------|-----------|------------------------|
| `rising` | +0.5% per tick | 1.0× |
| `stable` | 0% per tick | 0.7× |
| `falling` | -0.5% per tick | 1.0× |

**Implementasjon:** Ny klasse `systems/regime_manager.py`:

```python
@dataclass
class RegimeState:
    current: str  # "rising" | "stable" | "falling"
    days_remaining: int  # 3-5, tilfeldig ved skift
    history: list[str] = field(default_factory=list)  # siste 10 regimer

class RegimeManager:
    def on_new_day(self, commodities: dict[str, Commodity], 
                   regimes: dict[str, RegimeState]) -> list[str]:
        """Returnerer liste av commodity-id der regime skiftet."""
        changed = []
        for cid, regime in regimes.items():
            regime.days_remaining -= 1
            if regime.days_remaining <= 0:
                old = regime.current
                regime.current = self._pick_next_regime(regime.history)
                regime.days_remaining = random.randint(3, 5)
                regime.history.append(old)
                regime.history = regime.history[-10:]
                changed.append(cid)
        return changed
    
    def _pick_next_regime(self, history: list[str]) -> str:
        """
        Markov-lignende overgang. Stable er mer sannsynlig etter volatilitet.
        Unngå å skifte til samme regime tre ganger på rad.
        """
        ...
```

**Drift-logikk i `Commodity.tick()`:**

```python
def tick(self, regime: RegimeState) -> None:
    bias = {"rising": 0.005, "stable": 0.0, "falling": -0.005}[regime.current]
    vol_mult = {"rising": 1.0, "stable": 0.7, "falling": 1.0}[regime.current]
    
    drift = random.uniform(-self.volatility, self.volatility) * vol_mult
    self.current_price *= (1 + bias + drift)
    self.current_price = max(self.base_price * 0.3, 
                             min(self.base_price * 3.0, self.current_price))
    self.price_history.append(self.current_price)
    self.price_history = self.price_history[-20:]  # Hold siste 20
```

**Price-history i børs-UI:** Nedenfor kjøp/salg-raden viser 10 siste priser som små rektangler – en sparkline-visualisering. Lar spilleren visuelt lese trend uten å vite regime eksplisitt.

### 2.2 Lagerbegrensning

**Konsept:** Lasterommet holder maks 40 enheter totalt. Én enhet = én stykk av hvilken som helst vare. Kjøp som overstiger kapasitet blokkeres.

**Implementasjon:** I `Market.buy()`:

```python
def buy(self, commodity_id: str, quantity: int, game_state: GameState) -> BuyResult:
    current_total = sum(item.quantity for item in game_state.inventory.values())
    if current_total + quantity > game_state.cargo_capacity:
        return BuyResult.failed("cargo_full", 
                                f"Lasterom: {current_total}/{game_state.cargo_capacity}")
    ...
```

**UI i børs-overlayet:**
- Øverste høyre hjørne: "Last: 25/40" i COLOR_STONE_LIT
- Varer som ikke får plass: raden dimmes, prisen vises men kjøp-pil gir feil-hint

### 2.3 Transaksjonsgebyr

**Konsept:** Hver handel koster 5 dublooner fast. Thematisk "bestikkelse til havnemesteren". Gjør smålige handler ulønnsomme.

**Implementasjon:** I `Market.buy()` og `Market.sell()`:

```python
TRANSACTION_FEE = 5  # Dublooner per handel (kjøp eller salg)

def buy(self, commodity_id: str, quantity: int, ...) -> BuyResult:
    total_cost = buy_price * quantity + TRANSACTION_FEE
    if game_state.gold < total_cost:
        return BuyResult.failed("insufficient_gold", ...)
    ...
```

**UI:** Under gull-linjen i børs-overlayet, liten tekst: "Gebyr per handel: 5 d." i dempet farge.

### 2.4 Balansering

**Startgull:** Redusert fra 500 til 300. Tvinger bek-salg eller smart handel.

**Bek base_price:** Redusert fra 55 til 40 (fordi spilleren har konstant tilgang via produksjon, prisen skal være lav).

**Andre base_prices:** Uendret – Sukker 40, Rom 75, Tobakk 90.

---

## 3. Bek-produksjon (passiv)

### 3.1 Konsept

Spilleren "arver" Pitch Lake på Trinidad fra spillstart. Produksjonen genererer 2 bek per dag automatisk, som legges til inventar. Gir motivasjon til å reise/selge aktivt for å unngå full last.

Ingen interaktiv mekanikk i Fase 2A. Bare passiv drift. Interaktiv utvinning med rør/pumper kommer i Fase 4.

### 3.2 Implementasjon

Ny klasse `systems/pitch_lake.py`:

```python
@dataclass
class PitchLakeState:
    production_per_day: int = 2
    total_produced: int = 0  # Livstids-teller for stats/oppnåelser senere
    last_production_day: int = 0

class PitchLake:
    @staticmethod
    def on_new_day(state: PitchLakeState, game_state: GameState) -> int:
        """
        Produserer bek ved dag-skift. Returnerer antall bek produsert 
        (0 hvis lasterom er fullt).
        """
        current_total = sum(item.quantity for item in game_state.inventory.values())
        available_space = game_state.cargo_capacity - current_total
        produced = min(state.production_per_day, available_space)
        
        if produced > 0:
            pitch_item = game_state.inventory["pitch"]
            # Produksjon teller som "fri vare" - avg_cost blir vektet med 0
            old_qty = pitch_item.quantity
            new_qty = old_qty + produced
            pitch_item.avg_cost = (pitch_item.avg_cost * old_qty) / new_qty if new_qty > 0 else 0
            pitch_item.quantity = new_qty
        
        state.total_produced += produced
        state.last_production_day = game_state.clock.day
        return produced
```

### 3.3 UI-integrasjon

**HUD (øverst venstre, ny linje):**
```
Tortuga           (gul – MOON_HALO)
300 d.            (varm gull – LANTERN)
Dag 1             (kald blå – STONE_LIT)
Bek: +2/dag       (bek-oransje – EMBER)
```

**Dag-skift-feedback:** Når en ny dag starter, vis kort toast nederst på skjerm: "Pitch Lake: +2 bek" (5 sek, fader ut). Hvis lasterom var fullt: "Pitch Lake: lageret fullt, produksjon tapt" (samme toast-system, rødlig tone).

---

## 4. Ytelsesbudsjett (uendret fra Fase 1)

| Ressurs | Mål | Hard grense |
|---------|-----|-------------|
| FPS | 30 | 25 minimum |
| Minne (heap) | 100 MB | 150 MB |
| Frame time | < 10 ms | 33 ms |

Fase 2A skal ikke pushe disse grensene. Nye systemer (RegimeManager, GameClock, PitchLake) kjører bare ved "new_day"-hendelser = hvert 60. sek. Per-frame-kost er tilnærmet null.

---

## 5. Prosjektstruktur-tillegg

```
pitch-and-plunder/
├── ...  (eksisterende)
├── FASE_2A.md                   # Denne filen
├── systems/
│   ├── game_clock.py            # NY - Commit 2
│   ├── regime_manager.py        # NY - Commit 5
│   ├── pitch_lake.py            # NY - Commit 6
│   └── ...
├── scenes/
│   ├── village.py               # REFACTOR - Commit 1
│   ├── village_renderer.py      # NY - Commit 1
│   ├── village_buildings.py     # NY - Commit 1
│   └── ...
└── entities/
    ├── hint_indicator.py        # NY - Commit 1
    └── ...
```

---

## 6. Utviklingsrekkefølge (8 commits)

> **Revidert 2026-04-19** (etter brukertest av Commit 5): Commits 5 og framover er
> erstattet av en ny plan. Se `FASE_2A_REVIEW.md` for Commits 5.6, 5A–5E samt ny
> Commit 6 og Commit 7. Commits 1–4 og original Commit 5 beholdes i git-historikken
> som dokumentasjon av læringsløypen; refactoringen gjøres inkrementelt på plass
> (ikke git revert) slik at historikken forteller hva som faktisk skjedde.
>
> Sammendrag av endring: kontinuerlig markedsdrift per 10 sek forkastes til fordel
> for daglig oppdatering ved daggry, med full dag-natt-syklus som visuell
> feedback. Se `FASE_2A_REVIEW.md` for detaljer og begrunnelse.

### Commit 1 – VillageScene-splitt
- Opprett `scenes/village_renderer.py`, `scenes/village_buildings.py`, `entities/hint_indicator.py`
- Flytt logikk fra `scenes/village.py` til riktig modul
- `scenes/village.py` blir tynn orchestrerer (< 150 linjer)
- Ingen funksjonell endring – spillet skal oppføre seg identisk
- Benchmark: ingen regresjon (< 100 μs per frame)

### Commit 2 – GameClock og scene-livssyklus
- Opprett `systems/game_clock.py`
- Refactor `scenes/base_scene.py` med `on_enter`/`on_exit`
- Oppdater scene-manager til å kalle livssyklus-metoder
- Fjern `fresh_flags`-hack
- GameState bumpet til v3 med v2→v3 migrering
- HUD viser dag som teller faktisk oppover
- Test: start spill, vent 60 sek, bekreft "Dag 2"

### Commit 3 – GameState-refaktor
- GameState eier `player_position`, `clock`, og alle nye felt
- Fjern `_sync_state()`-metoden fra VillageScene
- Scene/systemer skriver direkte til GameState
- Save/load skjer uten mellomlag
- Test: stilleskjerm-save mid-tick, last, posisjon og tid bevart

**STOPP etter Commit 3. Brukeren tester før vi går videre.**

### Commit 4 – Lagerbegrensning
- `GameState.cargo_capacity: int = 40`
- `Market.buy()` validerer mot total kapasitet
- Børs-UI viser "Last: X/40" øverst høyre i overlayet
- Fulle rader dimmes
- Balansering: startgull redusert til 300

### Commit 5 – Regimer
- Opprett `systems/regime_manager.py` med Markov-lignende overgang
- Initialiser regime per vare ved første spillstart ("stable", 3-5 dager)
- `Market.tick()` tar regime-parameter fra GameState
- Sparkline-visning i børs-UI (10 siste priser som små rektangler)
- Regime-skift ved dag-slutt (abonnerer på `"new_day"`-hendelse)
- Test: spill 10 minutter, bekreft at priser viser tydelige trend-perioder

### Commit 6 – Bek-produksjon
- Opprett `systems/pitch_lake.py`
- Abonnerer på `"new_day"`, produserer 2 bek per dag
- HUD-linje "Bek: +2/dag"
- Toast-system for produksjons-feedback (ny `ui/toast.py`)
- Full-last-håndtering med rødlig toast
- Test: la 3 dager gå, bekreft 6 bek i inventar, selg noen, fortsett

### Commit 7 – Transaksjonsgebyr
- Konstant `TRANSACTION_FEE = 5` i `constants.py`
- `Market.buy()` og `Market.sell()` trekker gebyr
- Børs-UI viser "Gebyr per handel: 5 d." under gull-linjen
- Feil-hint hvis gull ikke dekker gebyr + vare

### Commit 8 – Polish + retrospektiv
- Juster sparkline-visualisering basert på brukertest
- Balanser regime-overgangs-sannsynligheter basert på 20 min spilletest
- Oppdater `PROSJEKT.md` CHANGELOG med v2.3
- Skriv `PHASE_2A_RETROSPECTIVE.md` med:
  - Hva ble bygget per commit
  - Benchmark-tall før/etter
  - Gameplay-observasjoner fra bruker
  - Teknisk gjeld identifisert for Fase 2B
- Endelig benchmark

---

## 7. Verifikasjonsliste for Fase 2A-avslutning

- `python main.py` starter og kjører stabilt
- Benchmark viser ≥30 FPS på målmaskin
- Dag-telleren inkrementeres hvert 60. sek
- Markedet viser tydelige regimer når du spiller 10+ minutter (stigende/fallende perioder, ikke bare støy)
- Lasterom fylles, meldingen "X/40" oppdateres korrekt
- Transaksjonsgebyr trekkes ved hver handel
- Bek akkumuleres passivt (2 per dag)
- Toast varsler ved dag-skift og full-last
- Sparkline viser siste 10 priser per vare i børs-UI
- Save-fil fra Fase 1 (v2) migreres til v3 uten feil
- Ingen scene re-entry-bugs (åpne og lukk børs 10 ganger fortløpende uten krasj)

---

## 8. Etter Fase 2A

Når verifikasjonsliste er OK og retrospektiv er skrevet, stopper vi. Brukeren skal spille spillet i minst 15-20 minutter og rapportere observasjoner før Fase 2B planlegges.

Nøkkelspørsmål som skal besvares ved Fase 2A-retrospektiv:
1. Føles regimene som meningsfulle trender, eller fortsatt som tilfeldig støy?
2. Er 40-enhets lasterom riktig størrelse?
3. Er 5-dublooner gebyr riktig mengde friksjon?
4. Skaper 2 bek/dag nok press til aktiv handel?
5. Tom-sider i UI som må fylles?

---

## CHANGELOG

- **v1.0** – Initial Fase 2A-spesifikasjon. Teknisk opprydding (VillageScene-splitt, GameClock, livssyklus, GameState-eierskap) + markedsdybde (regimer, last, gebyr) + bek-produksjon (passiv).

---

## Addendum – justeringer etter Commit 1-planlegging (2026-04-18)

Etter diskusjon med bruker før Commit 1 er følgende justert fra §6:

- **Commit 1** inkluderer flytting av `_build_background_layer` / `_build_empty_layer` (og deres hjelpere) fra `scenes/parallax_test.py` til ny `scenes/parallax_backdrops.py`. Begge scener importerer derfra.
- **HintIndicator** legges i `ui/hint.py`, ikke `entities/hint_indicator.py` (den har ingen verdens-posisjon eller sprite-logikk).
- **Commit 2** = kun livssyklus-API (`on_enter`/`on_exit`) + fjerning av `fresh_flags`. **Commit 3** = kun GameClock + GameState v3-migrering. Splittet fra sammenslått Commit 2 for mindre, mer håndterbare commits.
- **Commit 3.5** (nytt): pytest-oppsett + enhetstester for `GameClock`, `RegimeManager` (når den finnes), `PitchLake`, og save-migrering v2→v3. Ingen UI/rendering-tester.
- **Commit 4** beholder 500 dubloon startgull. Reduksjon til 300 flyttes til **Commit 5** (slik at friksjon fra regimer og startgull-kutt kommer samtidig).
- **Player-posisjonseierskap (§1.4):** Player beholder intern `x`/`y` som arbeidsdata. `to_state(game_state)` og `from_state(game_state)` kalles eksplisitt ved save/load og scene-skift. Ingen per-frame-lesing fra GameState. Unngår skjult container-avhengighet.
- **SECONDS_PER_DAY** legges som justerbar konstant i `constants.py` (default 60.0). Eksperimenteres med i Commit 8-polish.
- **Market-tick vs GameClock:** forblir uavhengige. Market-tick hvert 10. sek. RegimeManager abonnerer på `"new_day"`-hendelser.
- **ui/toast.py** (Commit 6): bygges generisk for gjenbruk i Fase 3 (pris-varsler) og Fase 5 (mistanke-varsler).

---

## Kjente issues (noteres for Commit 8-polish)

- **Sol-bevegelse hakker litt** (observert i Commit 5C brukertest 2026-04-19).
  Solens `celestial_x` oppdateres lineært fra DayCycle per frame, og sprite-
  posisjonen konverteres til int ved blit. Resultat: sprite hopper 1 px per
  N frames i stedet for å flyte jevnt. Mulige medvirkende årsaker: (1) int-
  casting uten sub-pixel-rendering, (2) cross-fade mellom backdrop-varianter
  med per-surface alpha kan gi varierende rendering-tid → dt-hikst. Fikses
  i Commit 8-polish (dedikert undersøkelse og mål).

---

## Fremtidige utvidelser (utover Fase 2A-scope)

- **Pitch Lake visuell utvinning (Fase 4)**: Brukeren ønsker at bek-
  produksjonen blir visuelt observerbar og interaktiv. Konseptskisse:
  separat Pitch Lake-scene (nåbar via Fase 2B-seiling) med sideview av
  svart beksjø, arbeidere som graver, vogner som spilleren kan interagere
  med ("E hent bek" ved vogn). Erstatter passiv daglig produksjon med
  aktiv henting. Den daglige upkeep-kostnaden forblir som abstraksjon av
  driftsutgifter mellom besøk. Notert etter Commit 6.1-brukertest
  (2026-04-19).
