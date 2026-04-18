"""Abstrakt grunnklasse for scener.

En scene er én logisk skjerm/tilstand (landsby, børs, verdenskart, ...).
Scene manager i `main.py` kaller `handle_event`, `update`, og `draw` hver
frame. Scener kan be om scene-bytte ved å sette `self.next_scene` til et
strengt scene-navn; `None` betyr "bli her".
"""

from __future__ import annotations

import pygame


class BaseScene:
    """Felles interface for alle scener.

    Subklasser overstyrer `handle_event`, `update`, `draw`. Allokering av
    Surfaces skal skje i `__init__` eller `on_enter`, aldri i `update`/`draw`.
    """

    #: Navnet scene manager skal bytte til. None = ingen bytte.
    next_scene: str | None
    #: Satt til True når spillet skal avsluttes.
    want_quit: bool

    def __init__(self) -> None:
        self.next_scene = None
        self.want_quit = False

    def on_enter(self) -> None:
        """Kalles når scene manager aktiverer denne scenen."""

    def on_exit(self) -> None:
        """Kalles rett før scene manager bytter bort fra denne scenen."""

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
