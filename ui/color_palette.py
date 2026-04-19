"""UI-signal-palett for data-tilstander (Fase 2B C8).

Sentralisert mapping fra "tillit til data" → palett-farge. Brukes av
verdenskart-tooltip for ObservedPrice-tilstander, og kan utvides til
andre UI-elementer i senere faser:

- Fase 3 rykter: samme stale-semantikk når NPC-rykter mister relevans
- Fase 5 hendelser: ferskhet på markeds-varsler
- Fase 5 markedsmanipulasjon: synlighet av spillerens egen påvirkning

Per spec FASE_2B.md §8.3 og PHASE_2A_RETROSPECTIVE.md observasjon
om at trend-pil-farger var hardkodet i exchange-overlay (teknisk
gjeld). Denne modulen er stedet de eventuelt skal samles.

Designprinsipp: én bærer per signal. Disse fargene signaliserer KUN
"hvor mye stoler vi på denne dataen", ikke geografisk tilhørighet
eller emosjonell tone.
"""

from __future__ import annotations

import constants


#: Fersk data — spilleren har sett dette nylig. Hvit-blå tone
#: signaliserer tillit (samme palett som "current"-markør sin omkrets).
DATA_FRESH: tuple[int, int, int] = constants.COLOR_STONE_LIT

#: Stale data — observert en gang, for gammelt til å stole på. Grå
#: tone signaliserer "er informasjon, men kan være feil nå".
DATA_STALE: tuple[int, int, int] = constants.COLOR_FOG

#: Ingen data — havnen er aldri besøkt. Mørk tone signaliserer
#: "ukjent territorium" uten å være alarmerende rødt.
DATA_NEVER: tuple[int, int, int] = constants.COLOR_STONE_DARK

#: Stale-dagsteller — antall dager siden observasjon, rendret i varm
#: tone (EMBER) for å trekke øyet til stale-status før spilleren
#: handler på dataen. Per spec §8.3: "rød dagsteller".
DATA_STALE_AGE: tuple[int, int, int] = constants.COLOR_EMBER
