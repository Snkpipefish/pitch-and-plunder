# Fase 2A – Revidering: dag-natt-syklus og daglig marked

Dette dokumentet **erstatter** Commit 5 i `FASE_2A.md` og legger til betydelig nytt scope. Årsaken er brukertest av Commit 5-implementasjonen: markedet var altfor volatilt, dag-skift var umerkelig, og markedsmanipulasjon ble meningsløs fordi prisene svingte trivielt mye på egen hånd.

## Designfilosofi-skifte

**Før (forkastet):**
- Priser drifter kontinuerlig hvert 10. sekund
- Regimer biaser drift-retning
- Dag-skift er en usynlig timer
- Markedsmanipulasjon er teoretisk mulig men unødvendig

**Nå:**
- Priser er **statiske innen en dag**, endres kun ved daggry
- Regimet bestemmer hvilken vei prisen beveger seg neste morgen
- Dag-skift er **visuell begivenhet** (himmelen endrer farge, sol/måne reposisjonerer)
- Markedsmanipulasjon blir meningsfylt fordi default-markedet er tregt og stabilt

**Historisk forankring:** Karibiske havner på 1600-1700-tallet hadde ikke kontinuerlige prisfluktuasjoner. Priser ble satt av hva som kom inn med skip, og det skjedde i dagssykluser – morgenens utlasting, ettermiddagens handel, nattens hvile. En pris-endring per dag er tematisk riktig.

---

## Ny systemarkitektur

### DayCycle-system (ny, Commit 5A)

Ny klasse `systems/day_cycle.py` med tre faser:

| Fase | Varighet | Himmel-farge | Sol/måne posisjon | Sol/måne farge |
|------|----------|--------------|-------------------|-----------------|
| Morgen (daggry) | 30 sek | #2d3561 → #6b8bc7 (glidende) | Stiger fra høyre horisont | #ffb347 (varm, lav) |
| Dag/kveld | 120 sek | #6b8bc7 midtvegs → #d96c2e mot slutt | Beveger seg over himmelen, synker mot venstre | #ffb347 → #ff8c42 → #d96c2e |
| Natt | 30 sek | #0a0e27 (mørk indigo, vår nåværende) | Måne oppe på høyre siden (nåværende posisjon) | #fff8e7 (kald hvit) |

**Totalt 180 sek per dag.**

**Overgang:** Palette-interpolering hver frame basert på `game_clock.progress_fraction()`. Interpolasjon bruker `_lerp_color` som allerede finnes i `parallax_backdrops.py`.

**Implementasjon:**

```python
@dataclass
class DaySnapshot:
    """Visuell state for nåværende tidspunkt i døgnet."""
    phase: str                      # "morning" | "day" | "night"
    sky_color_top: tuple[int,int,int]
    sky_color_horizon: tuple[int,int,int]
    celestial_x: float              # 0.0 = helt venstre, 1.0 = helt høyre (worldkoordinat)
    celestial_y: float              # 0.0 = horisont, 1.0 = topp av himmel
    celestial_color: tuple[int,int,int]
    celestial_radius: int           # Sol er litt større enn måne
    star_alpha: float               # 0.0 (dag) til 1.0 (natt)

class DayCycle:
    PHASES = [
        ("morning", 30.0),
        ("day", 120.0),
        ("night", 30.0),
    ]
    
    def compute_snapshot(self, clock: GameClock) -> DaySnapshot:
        """Returner visuell state basert på clock.seconds_into_day."""
        ...
```

### Revidert Parallax-rendering (Commit 5B)

Bakgrunnslaget kan ikke lenger pre-rendres statisk. Det må oppdateres når himmelfargen endres.

**To strategier:**

**Strategi A (anbefalt):** Pre-render 6 bakgrunnsvarianter (morgen-tidlig, morgen-sent, dag-tidlig, dag-midt, dag-sent, natt), interpoler IKKE himmelen piksel-for-piksel, men cross-fade mellom to nærmeste surfaces. Gir palett-bånd, men ser tematisk riktig ut og er billig.

**Strategi B:** Generer himmel-surface dynamisk hvert 2-3 sekund (pixelvis interpolasjon). Dyrere CPU, glattere overgang. Kan være for dyrt på T4200.

**Vi starter med Strategi A.** Hvis det ser stygt ut, bytter vi til B. Sol/måne tegnes som overlay på toppen (ikke bakt inn) – dens farge interpoleres glatt.

```
Render-pipeline per frame:
1. Snapshot = DayCycle.compute_snapshot(clock)
2. Finn to nærmeste pre-rendrede bakgrunner + interpoleringsfaktor
3. Blit bakgrunn-A med full alpha
4. Blit bakgrunn-B med alpha=faktor  
5. Tegn stjerner med alpha=snapshot.star_alpha
6. Tegn sol/måne-sprite med snapshot.celestial_color ved snapshot.celestial_x/y
7. Resten av scene (øyer, hav, bygninger, spiller) som før
```

### Celestial-klasse (erstatter dagens måne)

Ny sprite som rendrer sol/måne. Samme sprite, forskjellig farge:

```python
class Celestial:
    def __init__(self):
        # Pre-render smooth disc (som dagens måne, uten halo for nå - kan legges til senere)
        self._base_sprite = self._render_disc(radius=14)
        self._halo_sprite = self._render_halo(radius=30)
    
    def draw(self, surface, snapshot: DaySnapshot, cam_x: float):
        # Tinting: ta base-sprite og modulér med celestial_color
        tinted = self._tint(self._base_sprite, snapshot.celestial_color)
        x = int(snapshot.celestial_x * WORLD_WIDTH - cam_x)
        y = int(snapshot.celestial_y * HORIZON_Y_RANGE)
        surface.blit(tinted, (x, y))
```

### Daglig marked (Commit 5C)

**Ny regel:** `Market.tick()` fjernes som periodisk operasjon. Ingen prisendringer innen en dag.

**Ny metode `Market.on_dawn()`:** Kalles når `DayCycle` registrerer fase-overgang `night → morning`. Genererer nye priser for dagen basert på regime.

```python
def on_dawn(self, regimes: dict[str, RegimeState]):
    for cid, commodity in self.commodities.items():
        regime = regimes[cid]
        # Regimet bestemmer retning av daglig endring
        direction = {"rising": 1.0, "stable": 0.0, "falling": -1.0}[regime.current]
        # Endring er liten per dag (2-4%), akkumulerer over regime-varigheten
        magnitude = random.uniform(0.02, 0.04)
        change = direction * magnitude
        # Liten støy uavhengig av regime (market-bevegelse)
        noise = random.uniform(-0.01, 0.01)
        commodity.current_price *= (1 + change + noise)
        # Clamp mot base_price
        commodity.current_price = max(commodity.base_price * 0.5,
                                      min(commodity.base_price * 2.0,
                                          commodity.current_price))
        commodity.price_history.append(commodity.current_price)
        commodity.price_history = commodity.price_history[-14:]  # Hold 14 dager = 2 uker
```

**Effekt:**
- En stigende vare over 5 dager blir ca. +12% til +20% totalt (ikke 60% som nå)
- En stabil vare svinger ±5% totalt
- Spread på 2% er nå betydelig relativ til daglig endring
- Transaksjonsgebyr på 5 dublooner gjør smålige handler meningsløse

### Trend-indikator (erstatter sparkline)

Sparkline fjernes. Erstattes med enkel pil per vare:

- **↑** (grønn): Har steget flere dager på rad (sjekk siste 3 priser)
- **→** (grå): Relativt stabil
- **↓** (rød): Har falt flere dager på rad

Vises kun hvis `len(price_history) >= 3`. Ellers ingen indikator.

```python
def compute_trend_indicator(price_history: list[float]) -> str:
    if len(price_history) < 3:
        return ""
    recent = price_history[-3:]
    if recent[-1] > recent[0] * 1.03:
        return "↑"
    elif recent[-1] < recent[0] * 0.97:
        return "↓"
    return "→"
```

### Dag-skift i UI

Når DayCycle registrerer `night → morning`:
1. Emit event `"new_day"` (som nå)
2. `Market.on_dawn()` kalles
3. `PitchLake.on_new_day()` kalles
4. Toast vises: "Daggry — Dag N" (3 sek fadeout)

Brukeren får visuell feedback gjennom *både* himmelen som endrer seg OG toast. Men det er himmelens farge som er primær indikator, toast er bekreftende.

---

## Commit-plan (revidert)

Commits 1-4 fra opprinnelig FASE_2A er uendret og committet. Commit 5 ble committet men erstattes med under. Ny plan fra nå:

### Commit 5.6 – Revert og restrukturering (DENNE COMMIT)
- Revert Commit 5 (`git revert 14969c2` eller tilsvarende)
- Eventuelt: revert Commit 5.5 hvis du committet den (du stoppet før 5.5)
- Dokumenter beslutning i FASE_2A_REVIEW.md (denne filen)
- Sikre at commits 1-4 fortsatt er stabile

### Commit 5A – DayCycle-system
- Ny klasse `systems/day_cycle.py` med DaySnapshot og DayCycle
- Enhetstester (pytest) for snapshot-beregning på forskjellige clock-tider
- Ingen visuell integrasjon ennå – kun systemet

### Commit 5B – Himmel-interpolasjon og Celestial
- Pre-render 6 bakgrunnsvarianter i `parallax_backdrops.py`
- Oppdater `VillageRenderer` til å blende to nærmeste bakgrunner
- Ny klasse `entities/celestial.py` (erstatter statisk måne i bakgrunnslaget)
- Stjerne-alpha moduleres av snapshot
- Verifiser visuelt: kjør spillet 3+ minutter, se overgangene

### Commit 5C – Daglig marked + trend-indikator
- `Market.on_dawn()` erstatter `Market.tick()`
- Fjern 10-sek market-tick-timer fra VillageScene
- RegimeManager endres: regime varer fortsatt 3-5 dager, påvirker retning
- Sparkline fjernes fra exchange overlay
- Trend-indikator (↑→↓) legges til
- Enhetstester for on_dawn, trend-indikator

### Commit 5D – Startgull 300, bek base_price 40
- Reduksjon i `constants.py` og `commodities.json`
- Sikre at eksisterende save fra v4 fortsatt loader (eller bump til v5 og migrer)

### Commit 5E – Daggry-toast
- Implementer `ui/toast.py` (generisk, brukes senere for bek og feil)
- DayCycle emitter new_day-event, scene viser toast
- Visuell test: én dag gjennom hele syklusen med observerbar daggry-toast

**Verifikasjon etter Commit 5E:**
- Spill 3 hele dager (9 minutter)
- Himmelens farge endrer seg merkbart
- Priser endres én gang per dag
- Trend-indikator viser riktig retning etter 3+ dager samme regime
- Dagene føles forskjellige, ikke bare en abstrakt teller
- Stopp og brukertest før Commit 6

### Commit 6 – Bek-produksjon (uendret fra original plan)
- Som spesifisert i FASE_2A.md, men nå naturlig integrert i ny daggry-event
- Toast: "Daggry — Dag N — Pitch Lake: +2 bek"

### Commit 7 – Transaksjonsgebyr (uendret)

### Commit 8 – Polish, balansering, retrospektiv (uendret)

---

## Åpne spørsmål til implementasjon

1. **Sol-størrelse vs måne-størrelse:** Solen kan være litt større og mer intens enn månen. Sol-radius 18 px (vs måne 14 px)? Eller samme størrelse?
   - **Anbefaling:** Samme størrelse for enkelhet. Forskjell er i farge og omgivelser (ingen stjerner om dag).

2. **Solens posisjon over Tortuga:** Sol står opp i øst, går ned i vest. I vår verden (1600 px bred) hvor plasserer vi øst vs vest?
   - **Anbefaling:** Sol står opp på høyre side (x=0.9 av world) tidlig om morgenen, vandrer til venstre, går ned på venstre side (x=0.1) på kvelden. Måne er omvendt – står opp på venstre om kvelden, vandrer til høyre over natten. Gir tematisk kontinuitet mellom dagene.

3. **Skulle vi beholde stjernene om dagen men usynlige?** 
   - **Anbefaling:** Ja. Samme sprite, bare alpha=0 om dag, alpha=1 om natt. Billig.

4. **Varmt ettermiddagslys på bygninger:** Kingdom har gyllent lys på bygninger ved solnedgang. Skal vi gjøre det?
   - **Anbefaling:** Ikke i Fase 2A. Det er visuell polish som krever å re-bake bygningsfasader. Spar til en senere polish-commit.

5. **Skal børsen holdes åpen om natten?**
   - **Anbefaling:** Ja i Fase 2A, men logg at det er en potensiell mekanikk senere ("nattmarked med fargete varer"). Ikke bygg nå.

---

## Migrering fra eksisterende state

Commit 5 er allerede committet (hash `14969c2`). Hva gjør vi?

**Alternativ A: git revert**
- `git revert 14969c2`
- Starter frisk fra Commit 4
- Mister regime-koden som er skrevet (regime-konseptet overlever, bare implementasjonen endres)

**Alternativ B: Rebuild på plass**
- Behold Commit 5 i historikken
- Skriv om Market, RegimeManager, Commodity i nye commits
- Historikken blir rotete men kronologisk riktig

**Anbefaling: Alternativ B.** Git-historikk skal vise hva som faktisk skjedde. Vi lærte noe av Commit 5, det er verdt å beholde. Commit 5.6 dokumenterer beslutningen og starter restruktureringen.

---

## Ytelsesbudsjett

Dag-natt-syklus legger til:
- 2 blits per frame for himmel-cross-fade (billig, pre-rendret surface)
- 1 sprite-draw for sol/måne (billig)
- Alpha-modulering av stjerner (pre-rendret, bare alpha-set)
- Én on_dawn-operasjon hver 180. sek (praktisk talt gratis)

Forventet påvirkning: +100-200 μs per frame. Fortsatt godt innenfor budsjett (~3 ms lukket, 4 ms overlay).

---

## CHANGELOG

- **v1.0** – Initial revidering basert på brukertest av Commit 5. Flytter markedsmodell fra kontinuerlig drift til daglig oppdatering ved daggry. Introduserer dag-natt-syklus som både visuell feedback og tematisk forankring. Sparkline erstattes med enkel trend-pil. Regime-system beholdes men forenkles.
