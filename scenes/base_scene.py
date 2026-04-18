"""Abstrakt grunnklasse for scener.

En scene er én logisk skjerm/tilstand (landsby, børs, verdenskart, ...).
Scene manager i `main.py` kaller `handle_event`, `update`, og `draw` hver
frame, og `on_enter`/`on_exit` ved scene-bytte.

Livssyklus-API:
- `on_enter(game_state, from_scene)` kalles rett etter at scenen er opprettet
  og igjen hver gang den blir aktiv etter scene-bytte. `from_scene=None`
  betyr "første gang denne scenen aktiveres i økten" (typisk ved oppstart).
- `on_exit(to_scene)` kalles rett før en annen scene blir aktiv, slik at
  scenen kan synke state og autosave. `to_scene=None` betyr at applikasjonen
  avsluttes (QUIT); scener som trenger save-on-QUIT kan bruke `autosave()`
  direkte i stedet.

Scener kan be om scene-bytte ved å sette `self.next_scene` til et
strengt scene-navn; `None` betyr "bli her".
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pygame

if TYPE_CHECKING:
    from systems.save import GameState


class BaseScene:
    """Felles interface for alle scener.

    Subklasser overstyrer `handle_event`, `update`, `draw`, og eventuelt
    `on_enter`/`on_exit` for å reagere på aktivering/deaktivering.
    Allokering av Surfaces skal skje i `__init__` eller `on_enter`, aldri
    i `update`/`draw`.
    """

    #: Navnet scene manager skal bytte til. None = ingen bytte.
    next_scene: str | None
    #: Satt til True når spillet skal avsluttes.
    want_quit: bool

    def __init__(self) -> None:
        self.next_scene = None
        self.want_quit = False

    def on_enter(
        self,
        game_state: "GameState",
        from_scene: str | None = None,
    ) -> None:
        """Kalles når scene manager aktiverer denne scenen.

        `from_scene=None` betyr at dette er første gang scenen aktiveres i
        økten (typisk oppstart). Ellers er det navnet på scenen vi kommer
        fra, slik at scenen kan avgjøre om den skal gjenopprette lagret
        posisjon eller bruke en scene-spesifikk startposisjon.
        """

    def on_exit(self, to_scene: str | None = None) -> None:
        """Kalles rett før scene manager bytter bort fra denne scenen.

        `to_scene` er navnet på scenen vi bytter til, eller `None` ved
        applikasjons-avslutning (QUIT-path går direkte til `autosave()`).
        """

    def handle_event(self, event: pygame.event.Event) -> None:
        """Behandle én pygame-event."""

    def update(self, dt: float) -> None:
        """Oppdater tilstand. `dt` er sekunder siden forrige frame."""

    def draw(self, surface: pygame.Surface) -> None:
        """Tegn scenen til intern render-surface (640x360)."""

    def autosave(self) -> None:
        """Lagre gjeldende tilstand hvis scenen eier slik. Default: no-op.

        Kalles fra main ved pygame.QUIT og fra scene manager ved bytte.
        Scener som holder GameState-referanse overskriver dette.
        """
