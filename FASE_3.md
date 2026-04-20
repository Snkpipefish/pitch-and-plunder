# Pitch & Plunder – Fase 3: Pirat-liv, rykte og 100-dagers løp

Denne spesifikasjonen bygger på `PROSJEKT.md` (v2.5 → v2.6),
`PHASE_2B_RETROSPECTIVE.md` og `PHASE_2_5_RETROSPECTIVE.md`.
Les disse tre før du starter.

---

╔════════════════════════════════════════════════════════════════════╗
║                                                                    ║
║   ARBEIDSREGLER FOR FASE 3 — LES FØRST                             ║
║                                                                    ║
║   1. ALL KODE SKRIVES LOKALT i ~/prosjekter/pitch-and-plunder      ║
║      på main-branch. Ingen sandbox, ingen cloud-eksekusjon.        ║
║      Benchmark KJØRES på brukerens T4200-maskin, ikke estimeres.   ║
║                                                                    ║
║   2. STOPP ETTER HVER COMMIT og vent på grønt lys fra brukeren     ║
║      før neste commit starter. Fase 3 endrer tid, save-format og   ║
║      input-flyt — regresjonspotensialet er stort.                  ║
║                                                                    ║
║   3. ARBEID PÅ MAIN-BRANCH. Ingen git worktrees, ingen             ║
║      feature-branches.                                             ║
║                                                                    ║
║   4. DETTE ER EN MEKANIKK-FASE. Ingen nye scener (unntak:          ║
║      score-overlay i C3-12 er overlay, ikke scene). Ingen ny       ║
║      visuell identitet. Fase 2.5s palett- og silhuett-disiplin     ║
║      holdes uendret. Nye vinduer er dialog-overlay oppå            ║
║      PortVillageScene, mønster tatt fra ExchangeOverlay.           ║
║                                                                    ║
║   5. SAVE-VERSION bumpes KUN i C3-1 (handlings-tid → v6). Alle     ║
║      andre commits må bevare save-kompatibilitet med forrige       ║
║      versjon i fasen. C3-0 er skjelett uten version-bump.          ║
║                                                                    ║
╚════════════════════════════════════════════════════════════════════╝

---

## 0. Kontekst og mål

### Hva Fase 2B+2.5 leverte

Funksjonell multi-havn-økonomi med fire distinkte havner (Tortuga
smugler / Port Royal britisk kolonial / Havana spansk barokk / Nassau
pirat-kaos). Verdenskart, seiling med observed-pris-modell, per-havn
regimer og dawn-drevet marked. 577/577 tester grønne. Alle 4 havner
under 10 ms per frame på T4200.

Det spillet leverte var "en marked-simulator med atmosfære". Det var
ikke et spill med mål, tempo eller narrativ innsats — arbitrasjen
kunne kjøres i det uendelige uten konsekvens.

### Hva Fase 3 skal levere

Et **100-dagers pirat-liv** med klare stakes: spilleren starter i
Tortuga og skal samle mest mulig gull i Tortuga-kista på 100 dager.
Spillet kan slutte tidlig ved arrestasjon (mistanke når terskel) eller
død (random event). Score beregnes ved slutt.

Spillet skal være spillbart fra start til slutt, men ikke balansert —
det er et skjelett som senere faser iterererer på. Narrative innslag
(sabotasje, falske rykter, events) gir variasjon; mistanke- og rom-
systemene gir rytme.

Kjerneomlegningen er at **handlinger driver tid**, ikke omvendt. Dag/
natt-syklusen er ikke lenger real-time: spilleren bruker timer ved å
handle, dagen blir natt når dag-budsjettet er brukt, og neste dag
starter når natt-budsjettet er brukt. Dette gir tid diskret
betydning — hver handling koster noe.

### Hva Fase 3 IKKE er

- Ingen eget skip eller sabotasje-mekanikk på skip
- Ingen mannskaps-rekruttering
- Ingen 70-års liv, livsfaser, aldring, ekteskap, arv
- Ingen bek-utvinnings-scene (Fase 4)
- Ingen skipskamp-scene
- Ingen multiple scoring-dimensjoner (rykte, makt, rikdom — kun gull i Tortuga-kista teller)
- Ingen hvile-meter utover enkel rom-decay
- Ingen lyd (nedarvet fra tidligere faser)
- Ingen nye havner
- Ingen ny visuell identitet (palett- og silhuett-disiplin uendret)
- Ingen smooth dag/natt-fade (Fase 2.5-gjeld, ikke adressert)
- Ingen bakgrunnslag-fyll-bygninger (Fase 2.5-gjeld)

---

## 1. Design-fundament

### 1.1 Kjerne-loop

1. Spiller starter i Tortuga, dag 1, med startgull og tom Tortuga-kiste.
2. Hver dag har et handlings-budsjett i timer: 12 h dag + 12 h natt.
3. Handlinger (kjøp, seile, snakke med NPC, bestille sabotasje, spre
   falske rykter, kjøpe rykter, hvile) koster timer og ev. gull, kan
   øke mistanke eller utløse hendelser.
4. Når dag-timer er brukt → natt begynner automatisk. Når natt-timer
   er brukt → neste dag starter automatisk (dawn-tick: marked, regime,
   bek-produksjon).
5. Spiller kan gjemme gull i hver havns cache (beskytter mot
   arrestasjon, teller IKKE i score, unntatt Tortuga — se §1.9).
6. Spill slutter ved:
   - (a) dag 101 begynner (natt av dag 100 ferdig),
   - (b) mistanke ≥ terskel (arrest), eller
   - (c) død (random event).
   Score = gull i Tortuga-cachen ved slutt.

### 1.2 Score-modell

Kun én dimensjon teller: **gull i Tortuga-cachen** ved slutt-tidspunkt.

- Gull på hånden teller ikke i score (kan tas ved arrest eller tap).
- Gull i andre havners caches teller ikke (logisk: spilleren er ikke
  i havnen, kan ikke bringe det tilbake).
- Tortuga-cachen fungerer dobbelt: beskytter mot arrestasjon OG er
  score-telleren. Samme entitet, ikke to separate objekter.

Score-skjermen (overlay, ikke scene) vises ved game-over med:
- Score (gull i Tortuga-cache)
- Dager overlevd
- Årsak (dag 100 / arrest / død-<type>)
- Slutt-mistanke
- Antall sabotasjer/falske rykter/reiser som info-linjer

### 1.3 Tids-modell (handlings-drevet)

Real-time klokke-drift slås av for dag-progresjon i havn. Refactor
landes i C3-1:

- `GameClock.seconds_into_day` erstattes konseptuelt av
  `ActionBudget.hours_used_today` og `hours_used_tonight`, med fase-
  flagg `phase ∈ {"day", "night"}`.
- `ActionBudget.consume(hours)` returnerer liste av hendelser
  (`["phase_changed"]`, `["new_day"]`, kombinasjoner hvis én handling
  spenner over fase- eller dag-grense).
- Dag→natt-overgang er **automatisk** når dag-budsjett er brukt. Ingen
  manuell "vent til kveld"-handling.
- Dawn-tick (Market.on_dawn, RegimeManager, PitchLake.on_new_day)
  kalles på `"new_day"`-hendelse — altså når natt-budsjett er ferdig.
- `GameClock.day`-felt bevares (dag-teller).

### 1.4 Flerdagers reise — kalendertid

Reise mellom havner er **én handling** som forbruker N dager i én
operasjon. Men dawn-tick kalles N ganger sekvensielt (ikke batchet
ved ankomst):

- Dag i+1, i+2, ..., i+N, med full Market.on_dawn / regime-tick per
  dag.
- Random events kan avbryte mellom dagene (modal dialog under reise).
- Sabotasje-effekter og rykte-impact lander ved riktig kalenderdag.
- Hvis hendelse endrer reisetid (storm = +1 dag), skyves ankomst
  tilsvarende.

VoyageScene beholdes som visualisering, men akselerert til ~2 sek
wall-clock uansett reise-lengde. Skippbar med tastetrykk.

Celestial-visning (sol/måne) utledes fra `hours_used_today / day_budget`
i havn; under reise settes en fiksert progress-fraction for visuelt
skip-i-åpent-hav.

### 1.5 Mistanke-system

Én skalar `suspicion ∈ [0.0, threshold]` i PlayerState.

- Pirat-handlinger øker mistanke (sabotasje +15, falskt rykte +8, visse
  events variabelt).
- Passiv daglig decay reduserer mistanke (default -2/dag).
- Ingen aktiv reduksjon via børshandel eller bek-salg — kun passiv decay.
- Ved `suspicion ≥ threshold` utløses arrestasjon umiddelbart.
- HUD viser mistanke-nivå (ny linje under eksisterende stakk).

### 1.6 Rom-meter

`rest ∈ [0.0, 1.0]` i PlayerState. Default 1.0 ved ny spiller.

- Hver handling reduserer rest med 0.05 (default) → 20 handlinger til
  sliten.
- Ved `rest == 0.0`: neste handlings tids-kost multipliseres med
  `tired_penalty_multiplier` (default 2.0). Hver påfølgende handling
  koster også dobbelt til spilleren kjøper rom.
- Kjøpe rom i tavern (dag- eller natt-meny): setter `rest = 1.0` mot
  gull (10) + tid (1.0 h).

Rom-pres gir rytme: spilleren MÅ til tavern regelmessig, og tavern er
samme scene som eksponerer sabotasje, rykte-kjøp, smugler-kontakter.

### 1.7 Handlinger og dialog-vinduer

Alle vinduer er dialog-overlays oppå PortVillageScene. Ingen nye
scener. Alle arver fra `ui/dialog_overlay.py::DialogOverlay`.

| Bygning | Dag-meny | Natt-meny |
|---------|----------|-----------|
| Tavern | Rom-kjøp, `rumor_listen` (gratis-tier: rykte fra miljøet), bek-anlegg-kjøp (KUN i Tortuga, kun før kjøp) | Rom-kjøp, `rumor_listen` (betalt, bedre info), sabotasje-bestilling, `rumor_spread` (falsk rykte), smugler-kontakter (stub) |
| Børs (Exchange) | Kjøp/salg — hver transaksjon 0.5 h | Kjøp/salg — hver transaksjon 0.5 h (åpent også om natten) |
| Havnekontor | Fast-travel + cache-oppføring (per havn) | Fast-travel + cache-oppføring |
| Verdenskart-snarvei | Behold eksisterende keybind + `Vis kart`-oppføring i havnekontor-dialog | — |

### 1.8 Sabotasje og falsk rykte — to offensive mekanikker

Begge landes i C3-10 (felles infrastruktur):

**Sabotasje (`order_sabotage`)** — tavern natt-meny
- Fysisk forstyrrelse av forsyning. Pris stiger i target-havn.
- Kost: gull 50 + 2.0 h + mistanke +15.
- Retning: **alltid opp** i target (knapphet → høyere pris).
- Impact: forsinket 2 dager, magnitude +10% av base_price.
- Mål: (target_port, commodity_id) par — spilleren velger.
- Mekanisme: `EconomyState.pending_sabotages: list[PendingSabotage]`,
  konsumeres i `Market.on_dawn` på impact_day.

**Falskt rykte (`spread_false_rumor`)** — tavern natt-meny
- Betalt informasjons-manipulasjon. Kjøpmenn blir redde, dumper priser.
- Kost: gull 40 + 2.0 h + mistanke +8.
- Retning: **alltid ned** i target.
- Impact: forsinket 2 dager, magnitude −10% av base_price.
- Mekanisme: parallell til sabotasje. `EconomyState.pending_rumor_impacts:
  list[PendingRumorImpact]`.

Spillerens bruk: sabotasje for prisspike (kjøp billig → saboter →
selg dyrt); falsk rykte for prisdykk (vent → kjøp billig → selg
senere når markedet er nominelt). To komplementære strategier.

### 1.9 Rykte-system (to typer *lytte*-rykter)

Separate fra offensiv `rumor_spread` (sabotasje-parallell).

- **`rumor_listen` (regime_preview)**: avslør annen havns neste regime.
  Gratis-tier i dag-tavern (tilfeldig havn/vare). Kjøpt i natt-tavern
  (spilleren velger havn og vare).
- **`rumor_listen` (price_spike_warning)**: varsler om kommende
  prisbevegelse på spesifikk vare inkludert spiller-utløste
  sabotasje/falske-rykte-effekter. Kun kjøpt (natt-tavern).
- Aktive rykter bor i `PlayerState.active_rumors: list[ActiveRumor]`.
- TTL: 3 dager (default) eller til info blir foreldet (regimet har
  allerede tiktet).
- Presentasjon: UI-panel i tavern-dialog eller HUD-sub-linje
  (avklares i C3-9).

Navngiving i kode (unngå "rykte" tvetydighet):
- `rumor_listen` = lytte, kjøp av info (PlayerState.active_rumors)
- `rumor_spread` = spre falsk, offensiv (pending_rumor_impacts)
- `regime_preview`, `price_spike_warning` = undertyper av rumor_listen

### 1.10 Random events

Data-drevet via `data/events.json` med vekt-basert sampling.

**Kontekster:**
- Voyage-events: trigges under reise-dager (frekvens 0.5/dag).
- Port-events: trigges ved dag-overgang i havn (frekvens 0.2/dag).

**Første batch (8 events, detaljerte tall i C3-11):**
- **Voyage:** forlis (gull-tap, 5% dødssjanse), ran (gull-tap), storm
  (forsinkelse +1 dag), heldige funn (gull-gevinst)
- **Port:** sykdom (rom-spike + gull-tap, død-sjekk hvis rom < 0.2),
  mistanke-spike (guvernør får nyss), heldig bekjentskap (gratis
  rumor_listen), drankebrøl (rom-reset til 1.0 uten kost)

**Ratio positiv/negativ:** 30/70 (mest gjett spilleren må håndtere).

### 1.11 Bek-anlegg-gating

`PitchLakeState.purchased: bool = False`. Før kjøp: ingen produksjon,
ingen upkeep (tidlig-return i `PitchLake.on_new_day`).

Kjøp-handling: "Invester i bek-produksjon (500 gull)" i **tavern dag-
meny i Tortuga**. Oppføring kun synlig før anlegget er kjøpt. Ingen ny
bygning, ingen ny bbox — pirat-narrativet (uformelle investeringer i
tavernen) passer tematisk.

Kjøp: gull 500 + N timer (avklares — sannsynligvis 1.0 h). Etter kjøp:
eksisterende 2/dag-produksjon og 8/dag upkeep aktiveres.

### 1.12 Cache per havn

`PlayerState.port_caches: dict[port_id, int]`. Kapasitet ubegrenset.
Oppføring i havnekontor-dialog: "Cache (N gull)" med legg-inn/ta-ut-
underdialog.

- Cache er låst til havnen — kan ikke overføres.
- `port_caches["tortuga"]` er SCORE-telleren. `get_score()` returnerer
  denne verdien.
- Legg-inn/ta-ut koster 0.25 h (default).

---

## 2. Gjenbruk av eksisterende mekanismer

Fase 3 bygges på Fase 1/2A/2B/2.5-infrastruktur. Eksplisitt liste:

### 2.1 Fra Fase 1

| Mekanisme | Fil | Bruk i Fase 3 |
|-----------|-----|---------------|
| Scene-manager + BaseScene livssyklus | `main.py` / `scenes/base_scene.py` | Uendret. Ingen nye scener. Score-skjerm er overlay. |
| Exchange-overlay-mønster | `scenes/exchange.py` | Refaktoreres i C3-2 til å arve fra DialogOverlay. Mønster: SRCALPHA-panel, pre-rendret tekst-cache, tick_id-invalidering, tastatur-navigasjon, `_want_close`-flag. |
| ToastQueue | `ui/toast.py` | Gjenbrukes for event-notifikasjon, mistanke-advarsel, sabotasje-bekreftelse, arrest-varsel. |
| LightingSystem + gated lys | `systems/lighting.py` + `scenes/port_buildings.py` | Uendret. `night_factor` fortsatt input — bare kilden endres (fra clock til ActionBudget). |
| HUD | `ui/hud.py` | Utvides med mistanke- og rom-linjer i C3-7/C3-8. Samme cache-pattern. |
| Save (JSON, migrering) | `systems/save.py` | Utvides med v5→v6-migrering i C3-1. Mønster etablert over 5 migreringer. |

### 2.2 Fra Fase 2A

| Mekanisme | Fil | Bruk i Fase 3 |
|-----------|-----|---------------|
| GameClock.day | `systems/game_clock.py` | Uendret. `seconds_into_day` deprekeres fra handlings-tid-perspektiv; feltet kan beholdes for save-kompatibilitet. |
| DayCycle snapshot | `systems/day_cycle.py` | `compute_night_factor` blir funksjon av `hours_used / day_budget`. Visuell stack uendret. |
| Market.on_dawn + RegimeManager | `systems/economy.py` / `systems/regime_manager.py` | Uendret logikk. Kalles nå på handlings-drevet dag-skift. `Market.on_dawn` utvides med sabotasje/falskt-rykte-impact-evaluering (C3-10). |
| PitchLake.on_new_day | `systems/pitch_lake.py` | Gates på ny `state.purchased`-flagg i C3-6. Ellers uendret. |
| Toast | `ui/toast.py` | Uendret. |
| Commodity + InventoryItem | `entities/commodity.py` | Uendret. |
| balance.json hot-reload + kategorier | `systems/balance.py` | Utvides med nye felt (se §5). Samme LIVE/SESSION/NEWGAME-skjema. |

### 2.3 Fra Fase 2B

| Mekanisme | Fil | Bruk i Fase 3 |
|-----------|-----|---------------|
| Nested GameState | `state/game_state.py` | Utvides med nye felt under PlayerState, EconomyState, PitchLakeState, WorldState. Bumpes til v6 i C3-1. |
| PortConfig + ports.json | `config/port_config.py` + `data/ports.json` | Uendret struktur. Ev. nye dialog-bygnings-bbox-er (havnekontor) avklares i C3-4. |
| Voyage-helpers | `systems/voyage.py` | Direkte gjenbruk. `start_voyage`/`voyage_cost` kalles fra havnekontor-dialog i C3-4. |
| Verdenskart-scene | `scenes/world_map.py` | Beholdes. Havnekontor-dialog er primær inngang; verdenskart er alternativ (behold keybind + `Vis kart`-oppføring). |
| VoyageScene | `scenes/voyage.py` | Beholdes, men akselerert til ~2 sek wall-clock uansett reise-lengde. Skippbar. |
| Observed prices | `state/observed_price.py` | Uendret. `rumor_listen` kan skrive preview-data. |
| ToastQueue per scene | (3 instanser i dag) | Vurder konsolidering i C3-2 sammen med DialogOverlay-base. Ikke obligatorisk. |
| Dev-mode + F5 hot-reload | `systems/dev_mode.py` + `systems/balance.py` | Utvides med nye balance-felt. F5-handler uendret. |
| F1–F4 debug-teleport | `systems/debug_teleport.py` | Uendret. Ignorer handlings-tid ved teleport (dev-verktøy). |

### 2.4 Fra Fase 2.5

| Mekanisme | Fil | Bruk i Fase 3 |
|-----------|-----|---------------|
| Palett + silhuett-hierarki | Hele codebase | Uendret. Nye dialog-vinduer bruker STONE-palett og Exchange-overlay-proporsjoner. |
| Dag/natt-sprite-varianter | `scenes/port_buildings.py` | Uendret. `night_factor` er nå handlings-drevet men representasjonen er lik. |
| Palette-cycling | `systems/animations.py` | Uendret. |
| NPC-silhuetter | `entities/npc_silhouette.py` | Uendret visuelt. Interaktivitet utenfor scope. |

---

## 3. Ny infrastruktur

### 3.1 Handlings-tid (C3-1)

`state/action_budget.py`:
- `ActionBudget` dataclass: `day_budget_hours`, `night_budget_hours`,
  `hours_used_today`, `hours_used_tonight`, `phase: "day" | "night"`.
- `consume(hours: float) -> list[str]` returnerer hendelses-strings.
- `progress_fraction() -> float` for DayCycle-input.
- Bor i `WorldState.action_budget: ActionBudget`.

### 3.2 Dialog-rammeverk (C3-2)

`ui/dialog_overlay.py`:
- `DialogOverlay` base class ekstraherer mønster fra `ExchangeOverlay`.
- Konkrete dialoger arver og implementerer `_build_entries()`,
  `_render_row(i)`, `_handle_select(i)`.
- `ExchangeOverlay` refaktoreres til å arve; eksisterende cache-
  pattern bevart.
- Adresserer balance-hot-reload-kobling: subscribe-mekanisme eller
  pull-ved-draw (velges under review).

### 3.3 Mistanke-system (C3-7)

`systems/suspicion.py`:
- Pure functions: `increase(state, amount)`, `decrease(state, amount)`,
  `is_arrested(state) -> bool`, `on_new_day(state)` for daily decay.
- State: `PlayerState.suspicion: float`.
- Arrest utløser score-overlay med årsak "arrestert" (overlay landes
  i C3-12; C3-7 stubber trigger-pathen).

### 3.4 Rom-meter (C3-8)

`systems/rest.py`:
- Pure functions: `consume_for_action(state, base_hours)`,
  `restore(state)`, `effective_cost(state, base_hours) -> float`.
- State: `PlayerState.rest: float`.

### 3.5 Rykte-system — rumor_listen (C3-9)

`systems/rumors.py`:
- `RumorType`-enum: `"regime_preview"`, `"price_spike_warning"`.
- `ActiveRumor` dataclass (bor i `state/rumor_state.py`): type,
  target (port_id, commodity_id), payload, expires_on_day.
- `PlayerState.active_rumors: list[ActiveRumor]`.
- Gratis-tier i dag-tavern + betalt-tier i natt-tavern.
- Render: tavern-dialog-panel og/eller HUD-sub-linje (avklares).

### 3.6 Sabotasje + falskt rykte — pending market effects (C3-10)

`systems/market_effects.py` (ny fil):
- `PendingSabotage` og `PendingRumorImpact` dataclasses (bor i
  `state/market_effects.py`).
- `apply_pending_effects(market, effects, day)`: konsumerer effekter
  som har `impact_day == day`.
- `EconomyState.pending_sabotages`, `EconomyState.pending_rumor_impacts`.
- Kalles fra `Market.on_dawn` før regime-drift.
- Purchase-handlinger i TavernNightDialog lager nye effekt-objekter.

### 3.7 Random events (C3-11)

`systems/events.py` + `data/events.json`:
- `Event` dataclass: id, kontekst, vekt, effekt-funksjon-id, payload.
- `EventSampler` vekt-basert tilfeldig trekning.
- `EventResolver` applyer effekt (ta gull, forsinke reise, sette rom,
  øke mistanke, død-sjekk).
- Voyage-krok: kalles i per-dag-loop under reise (C3-4 sin dawn-tick-
  loop — se commit-rekkefølge-note).
- Havn-krok: kalles ved `"new_day"`-hendelse fra ActionBudget.

### 3.8 Score-overlay + game-over-flyt (C3-12)

`ui/score_overlay.py`:
- Triggeres fra 3 kilder: dag 101 starter, suspicion ≥ threshold,
  random event med death-flagg.
- Input: Enter/Esc for å avslutte prosessen.
- Ingen restart-flyt i Fase 3.

### 3.9 Cache-handling (C3-5)

Ingen ny fil — cache er felt på PlayerState og dialog-oppføring i
havnekontor:
- `PlayerState.port_caches: dict[port_id, int]` (default `{}`).
- `CacheSubDialog` i havnekontor: deposit/withdraw gull mot timer-
  kost.
- `GameState.get_score() -> int` returnerer
  `player_state.port_caches.get("tortuga", 0)`.

### 3.10 Bek-anlegg-kjøp (C3-6)

Ingen ny fil — `PitchLakeState.purchased: bool` + ny oppføring i
TavernDayDialog (kun synlig i Tortuga, kun før kjøp):
- "Invester i bek-produksjon (500 gull)"
- Kjøp: `state.purchased = True`, trekk gull + timer.
- `PitchLake.on_new_day` tidlig-return hvis `not purchased`.

---

## 4. Commit-plan (14 commits)

Hver commit følger 2B-størrelse. Etter hver: stopp, brukerverifisering,
benchmark hvis relevant, dokumentasjon.

### Foundation

- **C3-0 — FASE_3.md + balance.json utvidelse + state-stubs.**
  Skeleton-commit. FASE_3.md, PROSJEKT.md v2.6, balance.json v2 med
  nye felt, stub-felt i state uten kobling. Ingen gameplay-endring.
  0 nye tester utover balance-skjema-validering og stub-round-trip.

- **C3-1 — Handlings-tid-refactor.** ActionBudget-dataklasse,
  consume/phase_changed/new_day-events. Save v5→v6-migrering (setter
  `purchased=True` for eksisterende saves, default ActionBudget-
  verdier fra balance). Unit tester for consume-semantikk. Mid-fase-
  build trenger ikke være spillbar — tester må være grønne. NOP-
  default action-kostnad 0 for eksisterende bevegelse.

- **C3-2 — DialogOverlay-generalisering.** Base class ekstrahert fra
  ExchangeOverlay. Ekisterende exchange refaktoreres til å arve.
  Adresser balance-hot-reload-kobling. Ingen ny UX. Stub-filer for
  TavernDayDialog, TavernNightDialog, CacheSubDialog,
  HarbormasterDialog, ScoreOverlay — tomme klasse-skjeletter.

### Dialog-vinduer

- **C3-3 — Tavern-dialog (dag + natt-meny).** TavernDayDialog og
  TavernNightDialog. Dag: rom-kjøp + stubbed rumor_listen-free +
  stubbed bek-anlegg-kjøp (kun i Tortuga). Natt: rom-kjøp + stubbed
  rumor_listen-paid + stubbed sabotage/spread_false_rumor/smuggler-
  oppføringer. Rom-kjøp FUNGERER (forbruker gull + timer, setter rest).
  Tavern-bbox i ports.json brukes for interact-logic.

- **C3-4 — Havnekontor-dialog (fast-travel + cache).** Nytt dialog-
  vindu som kaller `voyage.start_voyage` og eksponerer cache-
  subdialog. Havnekontor-bbox i ports.json per havn (legges til som
  del av commit).
  **Commit-rekkefølge-note:** Siden dawn-tick-loop under reise er
  avhengig av C3-10 (sabotasje impacts) og C3-11 (events), bygges
  C3-4 med stubbed dawn-tick-loop (kun Market.on_dawn + regime-tick,
  ingen events, ingen sabotasje-impact). Full integrasjon i C3-10/C3-11.
  Alternativt: re-sekvenser C3-10/C3-11 før C3-4 hvis regresjon-
  risiko er lavere — velges under implementasjon.

- **C3-5 — Cache + Tortuga-score-computation.** Per-havn cache-
  dialog fullt funksjonell. Gull-legg-inn/ta-ut-mekanikk.
  `game_state.get_score()` eksponert.

- **C3-6 — Bek-anlegg-gating.** `PitchLake.on_new_day` gater på
  `purchased`. Kjøp-handling i TavernDayDialog (kun Tortuga, kun før
  kjøp). Kjøpspris (500) fra balance.

### Game-systems

- **C3-7 — Mistanke-system.** `systems/suspicion.py`. HUD-linje.
  Increase/decrease-funksjoner. Arrest-flyt stub (score-overlay
  utvides i C3-12). Test for daily decay og trigger-logikk.

- **C3-8 — Rom-meter-system.** `systems/rest.py`. Decay per handling.
  Dobbel-tid-effekt ved rest=0. HUD-linje. Rom-kjøp i tavern kobles
  fullt til.

- **C3-9 — Rykte-system (rumor_listen).** Kjøp i tavern. ActiveRumor-
  struktur + TTL-logikk. Regime_preview + price_spike_warning-typer.
  Rykte-panel (HUD-sub eller eget panel). Tester for TTL-utløp.

- **C3-10 — Sabotasje + falskt rykte (rumor_spread).** Felles
  infrastruktur: `systems/market_effects.py`,
  `state/market_effects.py`. Bestill i tavern-natt. Impact anvendes
  i Market.on_dawn. Mistanke-trigger per handling. Tester for
  impact-forsinkelse, rute-mål-validering, to samtidige effekter.

### Content

- **C3-11 — Random events-rammeverk + innhold.** `data/events.json`
  med 8-event-batch. EventSampler + EventResolver. Integrasjon i
  VoyageScene-flyt (voyage-events) og dawn-tick (port-events).
  Tester for sampling-determinisme og effekt-isolasjon.

- **C3-12 — Score-overlay + tre game-over-årsaker.** Dag 101 +
  arrest + random-death. Score-beregning. Info-linjer (dager,
  årsak, slutt-mistanke, sabotasje-teller, reise-teller).
  Input: Enter/Esc for å lukke spillet.

### Closing

- **C3-13 — Brukertest + retrospektiv.** Full gjennomspilling 1–2
  100-dagers løp. Observer spillbarhet. Skriv
  `PHASE_3_RETROSPECTIVE.md`, oppdater PROSJEKT.md CHANGELOG til
  v2.6 endelig. Ingen kode-endringer utover triviell bug-fiks.

---

## 5. Balanse-parametere (`data/balance.json`)

Alle verdier er **provisoriske**. Schema bumpes til `version: 2` i C3-0.

```json
{
  "version": 2,
  "game": {
    "total_days": 100,
    "starting_port": "tortuga"
  },
  "economy": {
    "starting_gold": 300,
    "transaction_fee": 5,
    "ship_starting_cargo_capacity": 40
  },
  "time": {
    "seconds_per_day_in_port": 180.0,
    "seconds_per_day_at_sea": 75.0
  },
  "actions": {
    "day_budget_hours": 12.0,
    "night_budget_hours": 12.0,
    "cost_hours_per_action": {
      "walk_across_port": 0.25,
      "enter_building": 0.0,
      "exchange_trade": 0.5,
      "buy_room": 1.0,
      "buy_rumor": 1.0,
      "order_sabotage": 2.0,
      "spread_false_rumor": 2.0,
      "cache_deposit": 0.25,
      "cache_withdraw": 0.25,
      "pitch_lake_purchase": 1.0
    }
  },
  "suspicion": {
    "threshold": 100.0,
    "daily_decay": 2.0,
    "rumor_increase": 0.0,
    "arrest_on_threshold": true
  },
  "rest": {
    "default_start": 1.0,
    "decay_per_action": 0.05,
    "tired_penalty_multiplier": 2.0,
    "room_cost_gold": 10,
    "room_cost_hours": 1.0
  },
  "rumors": {
    "cost_gold": 20,
    "cost_hours": 1.0,
    "ttl_days": 3,
    "regime_preview_enabled": true,
    "price_spike_warning_enabled": true
  },
  "sabotage": {
    "base_cost_gold": 50,
    "impact_delay_days": 2,
    "magnitude_pct": 10.0,
    "false_rumor_base_cost_gold": 40,
    "false_rumor_magnitude_pct": 10.0,
    "suspicion_increase_sabotage": 15.0,
    "suspicion_increase_false_rumor": 8.0
  },
  "events": {
    "voyage_frequency_per_day": 0.5,
    "port_frequency_per_day_start": 0.2,
    "positive_ratio": 0.3
  },
  "pitch_lake": {
    "production_per_day": 2,
    "upkeep_per_day": 8,
    "purchase_cost_gold": 500
  },
  "travel": { "...": "uendret fra v1" },
  "regimes": { "...": "uendret fra v1" },
  "observed": { "...": "uendret fra v1" }
}
```

### Hot-reload-kategorier

**LIVE** (tre i kraft umiddelbart):
- `economy.transaction_fee`
- `pitch_lake.upkeep_per_day`, `pitch_lake.production_per_day`
- `regimes.*`, `travel.routes.*`, `observed.stale_threshold_days`
- `actions.cost_hours_per_action.*`
- `suspicion.daily_decay`, `suspicion.rumor_increase`,
  `suspicion.arrest_on_threshold`
- `rest.decay_per_action`, `rest.tired_penalty_multiplier`,
  `rest.room_cost_gold`, `rest.room_cost_hours`
- `rumors.*`, `sabotage.*`, `events.*`

**SESSION** (neste dawn):
- `time.seconds_per_day_in_port`, `time.seconds_per_day_at_sea`
- `actions.day_budget_hours`, `actions.night_budget_hours`
- `suspicion.threshold`

**NEWGAME** (krever ny save):
- `economy.starting_gold`, `economy.ship_starting_cargo_capacity`
- `game.total_days`, `game.starting_port`
- `pitch_lake.purchase_cost_gold`
- `rest.default_start`

---

## 6. Tekniske krav

### 6.1 Ingen nye scener
Alle Fase 3-vinduer er dialog-overlays oppå PortVillageScene. Score
vises som overlay (ikke scene).

### 6.2 Ingen allokering i game loop
Alle dialog-overlays pre-rendrer tekst-surfaces ved åpning og cacher
per verdi-endring. Mønster 1:1 fra ExchangeOverlay.

### 6.3 Ytelse-budsjett

Uendret fra 2B/2.5. Hver havn + åpent dialog-overlay ≤ 10 ms per
frame på T4200. Dialog-overlay-kostnad ≤ 1 ms (tilsvarende Exchange).

| Scene | Mål | Hard grense |
|-------|-----|-------------|
| Port-scene lukket | 4.5–5 ms | 10 ms |
| Port-scene + dialog åpen | 6–7 ms | 10 ms |
| Verdenskart | <5 ms | 10 ms |
| VoyageScene | <5 ms | 10 ms |
| Port-scene + score-overlay | 6–7 ms | 10 ms |

### 6.4 Save v5→v6-migrering (C3-1)

Nye felt:
- `PlayerState.suspicion: float = 0.0`
- `PlayerState.rest: float = 1.0`
- `PlayerState.port_caches: dict[str, int]` (default `{}`)
- `PlayerState.active_rumors: list[ActiveRumor]` (default `[]`)
- `EconomyState.pending_sabotages: list[PendingSabotage]` (default `[]`)
- `EconomyState.pending_rumor_impacts: list[PendingRumorImpact]` (default `[]`)
- `PitchLakeState.purchased: bool` (v5→v6-migrering: `True` for
  eksisterende dev-saves, `False` for nye saves)
- `WorldState.action_budget: ActionBudget` (default fra balance)

Mønster fra v1→v5 gjentatt.

### 6.5 Test-strategi

- Minst 30 nye tester fordelt på: action_budget (5), dialog_overlay
  (3), suspicion (4), rest (3), rumors (4), market_effects (5),
  events (4), score_overlay (2), v5→v6-migrering (3).
- Eksisterende 577+ tester holdes grønne gjennom hele fasen.

### 6.6 Palett-disiplin

Nye dialog-overlays bruker kun master-palett-farger. Ingen nye farge-
koder.

---

## 7. Verifikasjonsliste for Fase 3-avslutning

- `python main.py` starter, spillet spillbart fra dag 1 til dag 101.
- Alle 3 game-over-årsaker (dag 100, arrest, død) trigger score-overlay
  med riktig årsak og korrekt score.
- Debug-teleport (F1–F4) fungerer uendret; action-tid respekteres ikke
  ved teleport.
- Bek-anlegg-kjøp: før kjøp ingen produksjon/upkeep; etter kjøp
  produksjon resumeres som før. Eksisterende v5-saves beholder
  produksjon via v5→v6-migrering.
- Mistanke, rom, rykter (lytte), sabotasje, falskt rykte, cache,
  Tortuga-score alle funksjonelle fra tavern/havnekontor-dialog.
- Sabotasje hever pris i target; falskt rykte senker pris i target;
  begge med 2-dagers forsinkelse.
- Benchmark på målmaskin, alle 4 havner + dialog åpen: <10 ms.
- Tester: 577 + ca. 30 nye, alle grønne.
- `PHASE_3_RETROSPECTIVE.md` skrevet, PROSJEKT.md oppdatert til v2.6.
- Bruker har gjennomspilt minst ett 100-dagers løp og bekreftet at
  spillet "føles som et spill" — ikke nødvendigvis balansert, men
  spillbart med meningsfulle valg.

---

## 8. Hva som er utenfor scope (notert for senere faser)

- Eget skip-vedlikehold og skip-oppgradering
- Sabotasje-meny på eget skip (f.eks. senke konkurrenters last)
- Mannskaps-rekruttering, mannskaps-moral
- 70-års liv, livsfaser, ektefelle, barn, arv
- Bek-utvinnings-mini-game (sideview rør/pumper) — Fase 4
- Skipskamp
- Multiple scoring-dimensjoner (rykte, status, makt, områdekontroll)
- Hvile-meter utover enkel rom-decay
- Lyd
- Smooth dag/natt-fade (arvet gjeld fra Fase 2.5)
- Bakgrunnslag med fyll-bygninger (arvet gjeld fra Fase 2.5)
- Tortuga-tavern-silhuett-redesign (arvet gjeld fra Fase 2.5)
- Vann-refleksjoner (arvet gjeld fra Fase 2.5)
- Toast-konsolidering (arvet gjeld fra Fase 2B) — kan landes som
  sub-commit i C3-2 hvis lav risiko
- Restart-flyt etter game-over

---

## CHANGELOG

- **v1.0** (2026-04-20) — Initial Fase 3-spesifikasjon. Godkjent
  etter design-runde med 33 spørsmål besvart og 6 design-presiseringer
  integrert. C3-0 starter skjelett-oppsett.
