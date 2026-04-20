"""HUD for village-scenen: Tortuga / gull / dag / bek-drift / mistanke /
rom, øverst venstre.

Fargekoding er bevisst:
- Sted         (moon-halo ) : "dette er et sted"
- Gull         (lantern   ) : varmt, tied til rikdom og tavernaens verden
- Dag          (stone-lit ) : kaldt, tied til institusjonell tid / Børshuset
- Bek (drift)  (ember     ) : varm-rød, tied til Pitch Lake og råvare-strøm
- Bek (stopp)  (fog       ) : nøytral dempet, signaliserer manglende drift
- Mistanke     (bånd-farge) : STONE_BRIGHT<30, LANTERN<70, EMBER<90, FLAME≥90
- Rom          (bånd-farge) : STONE_BRIGHT≥50%, LANTERN≥20%, EMBER≥1%, FLAME<1%

Tekst-surfaces caches og re-rendres bare når verdien endrer seg – settere
er no-ops hvis input er likt forrige verdi.
"""

from __future__ import annotations

import pygame

import constants


PADDING = 4
LINE_HEIGHT = 10  # 8 px glyff + 2 px linjeavstand


class Hud:
    """HUD-widget: sted, gull, dag, og bek-produksjonsstatus."""

    def __init__(
        self,
        font: pygame.font.Font,
        place: str,
        gold: int,
        day: int,
        pitch_per_day: int = 0,
        pitch_upkeep: int = 0,
        pitch_halted: bool = False,
        dev_mode: bool = False,
    ) -> None:
        self._font = font
        self._place: str | None = None
        self._gold: int | None = None
        self._day: int | None = None
        self._pitch_key: tuple[int, int, bool] | None = None
        self._suspicion_value: int | None = None
        self._rest_pct: int | None = None
        self._place_surf: pygame.Surface | None = None
        self._gold_surf: pygame.Surface | None = None
        self._day_surf: pygame.Surface | None = None
        # pitch_surf er None når produksjon er 0 OG ikke halted (skjuler linja).
        self._pitch_surf: pygame.Surface | None = None
        # Mistanke-linje (Fase 3 C3-7) — alltid synlig. Farge varierer
        # per bånd (STONE_BRIGHT<30, LANTERN<70, EMBER<90, FLAME≥90).
        self._suspicion_surf: pygame.Surface | None = None
        # Rom-linje (Fase 3 C3-8) — alltid synlig. Farge varierer per bånd
        # (STONE_BRIGHT≥50%, LANTERN≥20%, EMBER≥1%, FLAME<1% = utslitt).
        self._rest_surf: pygame.Surface | None = None
        # DEV-markør nederst til høyre. Rendres ÉN gang i __init__ og
        # caches som attributt — font.render per frame er dyrt på T4200
        # (PROSJEKT.md §14 feilmodus).
        self._dev_surf: pygame.Surface | None = None
        if dev_mode:
            self._dev_surf = font.render(
                "DEV", False, constants.COLOR_FOG
            ).convert_alpha()
        self.set_place(place)
        self.set_gold(gold)
        self.set_day(day)
        self.set_pitch_status(pitch_per_day, pitch_upkeep, pitch_halted)
        self.set_suspicion(0.0)
        self.set_rest(1.0)

    def set_place(self, place: str) -> None:
        if place == self._place:
            return
        self._place = place
        self._place_surf = self._font.render(
            place, False, constants.COLOR_MOON_HALO
        ).convert_alpha()

    def set_gold(self, gold: int) -> None:
        if gold == self._gold:
            return
        self._gold = gold
        self._gold_surf = self._font.render(
            f"{gold} d.", False, constants.COLOR_LANTERN
        ).convert_alpha()

    def set_day(self, day: int) -> None:
        if day == self._day:
            return
        self._day = day
        self._day_surf = self._font.render(
            f"Dag {day}", False, constants.COLOR_STONE_LIT
        ).convert_alpha()

    def set_pitch_status(
        self,
        pitch_per_day: int,
        upkeep: int,
        halted: bool,
    ) -> None:
        """Oppdater bek-linja basert på produksjons-status.

        - halted=True → "Bek: ingen drift" i dempet COLOR_FOG.
        - ellers pitch_per_day>0 → "Bek: +X/dag (-Y d.)" i COLOR_EMBER.
        - ellers (per_day=0, ikke halted) → ingen linje (skjult).
        """
        key = (pitch_per_day, upkeep, halted)
        if key == self._pitch_key:
            return
        self._pitch_key = key
        if halted:
            self._pitch_surf = self._font.render(
                "Bek: ingen drift", False, constants.COLOR_FOG
            ).convert_alpha()
        elif pitch_per_day > 0:
            self._pitch_surf = self._font.render(
                f"Bek: +{pitch_per_day}/dag (-{upkeep} d.)",
                False,
                constants.COLOR_EMBER,
            ).convert_alpha()
        else:
            self._pitch_surf = None

    @staticmethod
    def _suspicion_color(value: int) -> tuple[int, int, int]:
        """Farge-bånd per presisering C3-7 #3.

        Absolutte terskel-verdier (ikke prosent av max), slik at tuning
        av balance.suspicion.threshold ikke endrer fargeoverganger:

        - < 30:  STONE_BRIGHT — rolig
        - 30-69: LANTERN       — merkbar
        - 70-89: EMBER         — høy
        - ≥ 90:  FLAME         — kritisk (nærmer seg arrest ved default
                                  threshold=100)
        """
        if value < 30:
            return constants.COLOR_STONE_BRIGHT
        if value < 70:
            return constants.COLOR_LANTERN
        if value < 90:
            return constants.COLOR_EMBER
        return constants.COLOR_FLAME

    def set_suspicion(self, suspicion: float) -> None:
        """Oppdater mistanke-linja. Farge per bånd. Fase 3 C3-7.

        Verdi avrundes til int for visning (kontinuerlig decay gir
        desimal-verdier). Cache-nøkkel er også int, slik at minor
        flytpunkt-støy ikke trigger re-render.
        """
        value = int(suspicion)
        if value == self._suspicion_value:
            return
        self._suspicion_value = value
        color = self._suspicion_color(value)
        self._suspicion_surf = self._font.render(
            f"Mistanke: {value}", False, color,
        ).convert_alpha()

    @staticmethod
    def _rest_color(pct: int) -> tuple[int, int, int]:
        """Farge-bånd per presisering C3-8 #3.

        Prosent-verdier (int): ≥50 rolig, ≥20 merkbart sliten, ≥1 sliten,
        <1 utslitt (penalty aktiv i rest.effective_cost). FLAME-båndet
        (<1%) matcher `rest.is_exhausted` sin 0.01-terskel — konsistent
        UX mellom display og penalty-semantikk.
        """
        if pct >= 50:
            return constants.COLOR_STONE_BRIGHT
        if pct >= 20:
            return constants.COLOR_LANTERN
        if pct >= 1:
            return constants.COLOR_EMBER
        return constants.COLOR_FLAME  # utslitt, penalty aktiv

    def set_rest(self, rest: float) -> None:
        """Oppdater rom-linja. Farge per bånd. Fase 3 C3-8.

        Verdien vises som prosent (int). Cache-nøkkel er prosent-int,
        så minor flytpunkt-støy ikke trigger re-render.
        """
        pct = int(rest * 100)
        # Klamp defensivt til [0, 100] for visning.
        pct = max(0, min(100, pct))
        if pct == self._rest_pct:
            return
        self._rest_pct = pct
        color = self._rest_color(pct)
        self._rest_surf = self._font.render(
            f"Rom: {pct}%", False, color,
        ).convert_alpha()

    def draw(self, surface: pygame.Surface) -> None:
        """Tegn HUD-linjene. Dynamisk y-beregning slik at mistanke-linja
        posisjoneres riktig selv når bek-linja er skjult."""
        assert self._place_surf is not None
        assert self._gold_surf is not None
        assert self._day_surf is not None
        y = PADDING
        surface.blit(self._place_surf, (PADDING, y))
        y += LINE_HEIGHT
        surface.blit(self._gold_surf, (PADDING, y))
        y += LINE_HEIGHT
        surface.blit(self._day_surf, (PADDING, y))
        y += LINE_HEIGHT
        if self._pitch_surf is not None:
            surface.blit(self._pitch_surf, (PADDING, y))
            y += LINE_HEIGHT
        if self._suspicion_surf is not None:
            surface.blit(self._suspicion_surf, (PADDING, y))
            y += LINE_HEIGHT
        if self._rest_surf is not None:
            surface.blit(self._rest_surf, (PADDING, y))
            y += LINE_HEIGHT
        if self._dev_surf is not None:
            dev_x = constants.RENDER_WIDTH - self._dev_surf.get_width() - PADDING
            dev_y = constants.RENDER_HEIGHT - self._dev_surf.get_height() - PADDING
            surface.blit(self._dev_surf, (dev_x, dev_y))
