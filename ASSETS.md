# Pitch & Plunder – Asset-manifest

Dette dokumentet hører sammen med `PROSJEKT.md`. Målet er å vite nøyaktig hvilke eksterne assets vi trenger, når vi trenger dem, og hva vi må lage selv.

---

## 0. Realitetssjekk

`PROSJEKT.md` sier at Fase 1 bruker **placeholders (fargede rektangler)** for nesten alt. Vi trenger derfor veldig få eksterne assets for å komme i gang. Dette er bevisst – mekanikk først, grafikk etterpå. Å samle inn et stort asset-bibliotek nå er scope creep.

**Hva vi faktisk trenger før Commit 1-8:**
- 1 pixel font (OBLIGATORISK)
- 1 tegneverktøy installert/åpent (for å lage egne sprites når vi kommer dit)

**Hva som kan lastes ned senere (Fase 2+):**
- Karakter-sprites (etter Fase 1-benchmark viser at vi har ytelse til igjen)
- Skipssprites (Fase 2)
- Utvidede bakgrunnsreferanser

Resten er placeholders eller må tegnes selv for å matche master-paletten.

---

## 1. OBLIGATORISK – last ned før Fase 1 starter

### 1.1 Pixel font

**Public Pixel Font (CC0)**
- URL: https://ggbot.itch.io/public-pixel-font
- Lisens: CC0 (fri bruk, ingen kreditering nødvendig)
- Størrelser: 8, 16, 32, 64, 128 px
- Hvorfor denne: Ren sans-serif pixel font, leses godt på 640×360, passer både UI og dialog
- Plassering i prosjektet: `assets/fonts/public_pixel.ttf`

**Last ned denne først.** Uten pixel font ser HUD, børs-meny og priser ut som vanlig sans-serif (Arial-lignende) og bryter øyeblikkelig den visuelle stilen.

**Alternativ hvis du vil ha noe med mer middelalder-preg:**
- m5x7 eller monogram (CC0) – søk på itch.io. Litt smalere, bra for tette menyer.

### 1.2 Tegneverktøy (velg ett)

Vi kommer til å tegne mange egne sprites – master-paletten vår på 30 farger matcher ingen tredjepart. Velg ett av disse:

**Piskel** (anbefalt for enkelhet)
- URL: https://www.piskelapp.com/
- Kjører i nettleser, gratis, ingen installasjon
- Støtter palett-import, animasjon, lagreksport
- Perfekt for små sprites (16×16, 32×32)

**Aseprite** (hvis du vil gå dypere)
- URL: https://www.aseprite.org/
- Koster ~$20 eller kan kompileres gratis fra kildekode
- Industristandarden for profesjonell pixel art
- Bedre for animasjon og store illustrasjoner

For Fase 1 holder det med Piskel.

### 1.3 Master-palett som fil

Lag en `.gpl` (GIMP palette) eller `.hex` fil av våre 30 farger og importér den i tegneverktøyet. Dette er første oppgave i `assets/`-mappa.

Eksempel `.hex`-fil (lagre som `master_palette.hex` i `assets/`):
```
0a0e27
1a1f4d
2d3561
fff8e7
f5e6b3
ffd580
ffb347
ff8c42
d96c2e
e8c27a
0f1829
1e2a4a
2a3a5e
4a5a8a
1a1410
2a2018
3d3024
5c4a35
151a2a
1f2538
2d3548
3d4660
6b8bc7
8ba8d6
1a1620
3d3548
c49171
e8dcc4
3a3a4a
```

**Lospec palette editor** (nyttig verktøy): https://lospec.com/palette-list – kan konvertere palett til ulike formater inkludert `.gpl`, `.pal`, `.png`.

---

## 2. IKKE last ned (men andre anbefaler dem)

### Kenney Pirate Pack

- URL: https://kenney.nl/assets/pirate-pack
- **Grunn til å hoppe over:** Top-down perspektiv. Vårt spill er sideview. Passer ikke i det hele tatt.

### Kenney Tiny Town Pack

- Top-down. Samme problem.

### Tilfeldige "pirate asset pack" på itch.io

- De fleste er tegneserieaktige, feil palett, eller top-down platformer. Matching er vanskeligere enn å tegne selv med vår palett.

---

## 3. BOKMERK for Fase 2+ (ikke last ned nå)

### 3.1 Sideview-karakterreferanser

**Pirate Bomb av Pixel Frog**
- URL: https://pixelfrog-assets.itch.io/pirate-bomb
- Gratis, commercial use tillatt
- Sideview, animert pirat-hovedperson med gode walk-cycles
- Stil: Mer cartoony enn vår. Bruk som ANIMASJONSREFERANSE for egne sprites, ikke direkte.

**Ansimuz Legacy Collection**
- URL: https://ansimuz.itch.io/gothicvania-patreon-collection
- Gratis, CC0-lignende
- Masse sideview-miljøer og karakterer i 16-bit stil
- Bruk som referanse for parallax-komposisjon og lysføring

### 3.2 Bakgrunnsreferanser

**Underwater Fantasy Pixel Art Environment (Ansimuz)**
- URL: https://ansimuz.itch.io/underwater-fantasy-pixel-art-environment
- 3-lags parallax, bra teknisk referanse selv om temaet er feil

**Ocean and Clouds Free Pixel Backgrounds**
- URL: https://free-game-assets.itch.io/ocean-and-clouds-free-pixel-art-backgrounds
- Gratis, kan gi inspirasjon til vår Tortuga-havn-komposisjon

### 3.3 Skipssprites (Fase 2 – verdenskart)

Når vi kommer dit, søk på itch.io etter "pirate ship pixel art sideview" – vi bestemmer spesifikt når Fase 1 er i mål, ikke nå.

---

## 4. Hva vi MÅ tegne selv (ingen tredjepart kan erstatte)

Disse er så spesifikke for vårt spill at de må tegnes med master-paletten:

### Fase 1
- **Spiller-karakter** (32×32, 2-4 walk-frames, med tricorn-hatt)
  - Bør matche Hawkins visuelt – begge er "respektable" skikkelser
- **NPC Hawkins** (32×32, 1-2 idle-frames, står foran Børshuset)
- **Tavernaen** (bygningsfasade, ca. 120×80 piksler, sideview)
  - Skilt, 2-3 vinduer, dør, skorstein
- **Børshuset** (bygningsfasade, ca. 160×90 piksler)
  - Klassisk fasade med søyler og trekantgavl, 3 vinduer, dør
- **Gateplan/brygge-tiles** (16×16 brosteinsfliser, 2-3 varianter)
- **Måne + stjerner** (kan tegnes programmatisk)
- **Hengende lanterne** (8×12 piksler, 2-frame flamme-animasjon)
- **4 vare-ikoner** (16×16 hver: sukker-sekk, rom-flaske, tobakk-blad, bek-tønne)

### Fase 1 polish (valgfritt)
- **Tønne** og **kasse** (16×16, atmosfære-props)
- **Palmeblad-silhuett** (til forgrunn-lag, ca. 80×120)
- **Tau** (til forgrunn, henger fra topp av skjerm)

**Estimat:** Alt over kan tegnes i Piskel på 2-4 timer for en person som kan grunnleggende pixel art. Hvis du ikke har erfaring, sett av et par kvelder – du lærer underveis.

**Alternativ hvis du ikke vil tegne:** La placeholdere stå i Fase 1, lever et fungerende spill først, og vurder å ansette en pixel artist på Fiverr/Reddit til $30-80 for Fase 1-sprites når du vet mekanikken holder.

---

## 5. Assets vi IKKE trenger i Fase 1

- Lyd (SFX, musikk) – legges til i Fase 2+
- Animasjoner utover walk-cycle – Fase 3+
- Værpartikkel-sprites – tegnes programmatisk (rektangler, sirkler)
- Himmel-texturer – tegnes programmatisk (gradient)
- Hav-bølger – palette cycling på 8-bit surface eller programmatisk
- Skip-sprites – Fase 2
- Bek-utvinning-props – Fase 4

---

## 6. Konkret handlingsliste

Gjør dette nå, i rekkefølge:

1. Gå til https://ggbot.itch.io/public-pixel-font og last ned (velg "No thanks, just take me to the downloads" hvis den ber om donasjon)
2. Pakk ut zip-filen, legg `.ttf`-fila i en trygg mappe du finner igjen (f.eks. `~/assets-library/public_pixel.ttf`)
3. Åpne https://www.piskelapp.com/ i nettleseren – du trenger ikke konto for å prøve det
4. Lag en ny sprite 32×32 og importér master-palett-fila (eller skriv inn hex-koder manuelt i fargepaletten)
5. Tegn en test-sprite av spilleren (tricorn-hatt + frakk) – ca. 10 minutter, setter deg inn i verktøyet

Når Claude Code kommer til commit 4 (Village-scene), kan du dra .ttf-fila inn i prosjektets `assets/fonts/`-mappe og dine sprites inn i `assets/sprites/`.

**Ikke last ned mer enn dette nå.** Resten vurderer vi når vi er der.

---

## 7. Lisens-oversikt

| Asset | Lisens | Kreditering? |
|-------|--------|--------------|
| Public Pixel Font | CC0 | Ikke nødvendig |
| Piskel (verktøy) | MIT/Apache | N/A |
| Ansimuz-ressurser | Custom permissive | Anbefalt, ikke påkrevd |
| Pirate Bomb | Custom permissive | Anbefalt, ikke påkrevd |
| Egne sprites | Ditt verk | N/A |

Lag en `CREDITS.md` i prosjektet når du legger til tredjepart-assets. Selv om kreditering ikke er påkrevd er det god skikk.

---

## CHANGELOG

- **v1.0** – Initial asset-manifest. Fokus på minimalt inngrep i Fase 1: kun pixel font og tegneverktøy er obligatorisk. Alt annet er bokmerker eller må tegnes selv for å matche master-paletten.
