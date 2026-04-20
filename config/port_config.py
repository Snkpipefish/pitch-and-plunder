"""PortConfig — statisk havn-data fra `data/ports.json`.

Lastes eksplisitt via `init()` ved spill-oppstart (etter `balance.init()`).
Manglende eller ugyldig fil feiler oppstart med klar melding (ingen
papegøye-fortsettelse med tomme havner).

Singletonens livssyklus speiler `systems/balance.py`:
- `init(path)` kalles én gang i main.py, leser og validerer alle 4 havner
- `get(port_id)` returnerer PortConfig-objekt for gitt id
- `get_all_port_ids()` returnerer iterable over alle havn-id-er

Validering ved load:
- Alle 4 forventede havner til stede (`tortuga`, `port_royal`, `havana`,
  `nassau`)
- Alle 4 varer (`sugar`, `rum`, `tobacco`, `pitch`) har oppføring i
  `price_bias` og `regime_weights`
- `regime_weights[cid]` summerer til 1.0 (±0.01 toleranse)
"""

from __future__ import annotations

import json
import logging
import math
import os
from dataclasses import dataclass, field
from typing import Any


log = logging.getLogger(__name__)


#: Filplassering relativt til prosjekt-rota.
DEFAULT_PORTS_PATH = os.path.join("data", "ports.json")

#: Havn-id-er spillet krever. Må matche `tests/fixtures/save_v4.json`
#: og `state/economy_state.py`-forventningene (som leser via denne modulen).
REQUIRED_PORTS: frozenset[str] = frozenset({
    "tortuga", "port_royal", "havana", "nassau",
})

#: Vare-id-er som må finnes i price_bias og regime_weights per havn.
REQUIRED_COMMODITIES: frozenset[str] = frozenset({
    "sugar", "rum", "tobacco", "pitch",
})

#: Gyldige regime-navn (matcher systems.regime_manager.REGIMES).
VALID_REGIME_NAMES: frozenset[str] = frozenset({"rising", "stable", "falling"})

#: Toleranse for regime_weights-sum-validering.
REGIME_WEIGHT_SUM_TOLERANCE: float = 0.01


@dataclass(frozen=True)
class CelestialConfig:
    """Verdens-x-koordinater for himmel-objekter i en havns scene.

    `moon_worldx` er statisk over "institusjonelt anker" (Børshus i Tortuga).
    `sun_worldx_dawn` og `sun_worldx_dusk` definerer solens bane gjennom
    dagen. Brukes først i C3 når celestial flyttes ut av konstanter.
    """
    moon_worldx: int
    sun_worldx_dawn: int
    sun_worldx_dusk: int


@dataclass(frozen=True)
class BuildingPlacement:
    """Rektangulær bygningsplassering (verdens-koordinater)."""
    x: int
    y: int
    w: int
    h: int


@dataclass(frozen=True)
class LanternPost:
    """Lanterne-stolpe-plassering (verdens-x)."""
    x: int


@dataclass(frozen=True)
class MarketStall:
    """Markedsbod-plassering (verdens-x, bredde)."""
    x: int
    w: int


@dataclass(frozen=True)
class BarrelStack:
    """Stablede tønner (verdens-x, antall i første rad)."""
    x: int
    count: int


@dataclass(frozen=True)
class SilhouettePlacement:
    """NPC-silhuett-plassering.

    `kind` må være en gyldig silhuett-type per
    `entities.npc_silhouette.VALID_KINDS` ("standing", "sitting",
    "group", "officer", "merchant", "colonial_lady", ...).
    Validering skjer i `_parse_silhouette`.
    """
    kind: str
    x: int


@dataclass(frozen=True)
class IronFence:
    """Jerngjerde-seksjon (Port Royal). Start-x og lengde i piksler."""
    x: int
    length: int


@dataclass(frozen=True)
class Fountain:
    """Torgfontene-plassering (Havana). Statisk i C2.5-3; palette-
    cycling legges til i C2.5-6 animasjonspasset.
    """
    x: int


@dataclass(frozen=True)
class Planter:
    """Lav busk/plante-plassering (Havana — ved palasset)."""
    x: int


@dataclass(frozen=True)
class BambooLantern:
    """Improvisert lanterne på bambus/skipsmast-rest (Nassau).
    Forskjell fra LanternPost: skeiv, uten glød-halo, WOOD-familie
    i stedet for STONE.
    """
    x: int


@dataclass(frozen=True)
class Campfire:
    """Åpent bål på gaten (Nassau). Statisk i C2.5-4; palette-cycling
    på flammepiksler kommer i C2.5-6.
    """
    x: int


@dataclass(frozen=True)
class ChestStack:
    """Kaotisk stablede kister (Nassau — erstatter strukturerte tønner
    i pirat-markedsplassen).
    """
    x: int
    count: int


@dataclass(frozen=True)
class FillBuilding:
    """Fyll-bygning for bystruktur (Fase 2.5 C2.5-6a/6b).

    Utover signatur-bygningene skal hver havn ha 4-9 fyll-bygninger
    som gir scenen karakter av bebodd by. `kind` matcher mot bake-
    funksjoner i `entities/fill_buildings.py` via
    `VALID_FILL_BUILDING_KINDS`.

    `style_variant` bytter små visuelle detaljer (f.eks. speilvendt
    vindu/dør-plassering) slik at to cluster-bygninger av samme
    `kind` ikke er identiske.

    `h` må være ≤ `MAX_FILL_BUILDING_HEIGHT` (60 px) for å holde
    silhuett-hierarkiet per FASE_2_5.md §1.4.
    """
    kind: str
    x: int
    w: int
    h: int
    style_variant: int = 0


@dataclass(frozen=True)
class Alley:
    """Smug mellom bygninger (Fase 2.5 C2.5-6a/6b).

    Representerer en åpning der havet/skip bak er synlig gjennom.
    Alley er dokumentasjons-struktur: bake-pipelinen tegner ikke
    alleys eksplisitt — de oppstår naturlig som tomrom mellom
    fill_buildings og signatur-bygninger.

    Spec §1.4 krever bredde 20-40 px. Parser aksepterer 16-40 px
    (grense-fleksibilitet når havne-layout er trang, f.eks. Nassau
    hvor signatur-bygningene dominerer).

    `contents` (C2.5-7) legger valgfritt innhold i smuget — tønner,
    ugress, blomster, palme, sand-drift. Gyldige verdier validert
    mot `_VALID_ALLEY_CONTENTS`.
    """
    x: int
    w: int
    contents: str | None = None


@dataclass(frozen=True)
class PaletteCycle:
    """Palette-cycling-region (Fase 2.5 C2.5-9).

    Matcher `systems.animations.PaletteCycleSource`. Rektangel på
    gameplay-surface fylles syklisk med `palette`-fargene.

    `permanent=True` = kjører 24/7 (bål, smithy). `False` = gates
    av night_factor.
    """
    x: int
    y: int
    w: int
    h: int
    palette: tuple[str, ...]
    fps: float = 6.0
    permanent: bool = False


@dataclass(frozen=True)
class PortAnimations:
    """Per-havn animasjons-konfigurasjon (C2.5-9).

    Kun palette-cycling i C2.5-9. Alpha-pulsering flagg lagret men
    ikke implementert (utsatt til Fase 3).
    """
    palette_cycles: tuple[PaletteCycle, ...] = ()
    alpha_pulse_windows: bool = False


@dataclass(frozen=True)
class NatureElement:
    """Natur-element (palme, fugl, blomster, ugress, etc).

    Fase 2.5 C2.5-7 livfullhet. `kind` matcher
    `entities.nature.VALID_NATURE_KINDS`. `y` er kontekst-avhengig:
    for fugler plass på bygning; for vegetasjon/blomster y_top for
    hengestart; for palmer ignoreres y (ground_top_y brukes).
    """
    kind: str
    x: int
    y: int = 0


@dataclass(frozen=True)
class AnchoredShip:
    """Ankrede skip-silhuett i havnen (Fase 2.5 C2.5-5).

    Plasseres i forgrunns-lagets koordinatrom (speed 0.2). `x` og `y`
    er parallax-koordinater — `y` er vannlinjen (skroget tegnes opp fra
    dette nivået).

    `kind` må være i `entities.anchored_ship.VALID_SHIP_KINDS`:
    "smuggler", "frigate", "galleon", "small", "pirate".

    `flipped` speiler skipet horisontalt (bue mot venstre i stedet for
    høyre). `tilted` skråstiller pirat-skip subtilt — kun gyldig for
    "pirate".
    """
    x: int
    y: int
    kind: str
    flipped: bool = False
    tilted: bool = False


@dataclass(frozen=True)
class SignatureBuilding:
    """Havn-spesifikk signatur-bygning utover tavern + exchange.

    `kind` dispatcher til en bake-funksjon i `scenes/port_buildings.py`.
    Gyldige kinds valideres av `_parse_signature_building`.

    Per FASE_2_5.md §1.2: hver havn har 2-3 signatur-bygninger.
    Tavern og exchange er alltid på plass; ekstra signatur-bygninger
    listes her (klokketårn, rum-magasin, katedral, osv.).
    """
    kind: str
    placement: BuildingPlacement


@dataclass(frozen=True)
class PortProps:
    """Rekvisita-lag for en havn (Fase 2.5).

    `ground_texture` bestemmer hvilken bake-funksjon som brukes for
    gategulvet. Gyldige verdier validert via
    `entities.port_props.VALID_GROUND_TEXTURES`.

    Tuples (ikke lister) for immutabilitet.
    """
    ground_texture: str
    lanterns: tuple[LanternPost, ...] = ()
    market_stalls: tuple[MarketStall, ...] = ()
    barrel_stacks: tuple[BarrelStack, ...] = ()
    silhouettes: tuple[SilhouettePlacement, ...] = ()
    iron_fences: tuple[IronFence, ...] = ()
    fountains: tuple[Fountain, ...] = ()
    planters: tuple[Planter, ...] = ()
    bamboo_lanterns: tuple[BambooLantern, ...] = ()
    campfires: tuple[Campfire, ...] = ()
    chest_stacks: tuple[ChestStack, ...] = ()


@dataclass(frozen=True)
class PortBuildings:
    """Per-havn scene-layout: bakkehøyde, bygninger, spiller-start, NPC-er.

    Fase 2B C4: flyttet fra hardkodede konstanter i `scenes/village_buildings.py`.
    Fase 2B C6: Port Royal, Havana, Nassau får layout + stub-havner aktiveres.
    `dock_interaction_range` flyttet fra modul-konstanter i port_village.py
    til per-havn buildings per direktiv (obligatorisk felt).
    """
    #: Y-pixel der bakken starter (spiller-føttene hviler på denne).
    ground_top_y: int
    #: Verdens-x der spilleren spawn-es ved fersk start i havnen.
    player_start_x: int
    tavern: BuildingPlacement
    exchange: BuildingPlacement
    #: Verdens-x for hver NPC (id → x). Y utledes fra ground_top_y.
    npcs: dict[str, int]
    #: Venstre-kant dock-region [min_x, max_x] som trigger verdenskart-
    #: interaksjon når spilleren står i. Tortuga + stub-havnene bruker
    #: (8, 80) — dock-sprite flyttes til buildings i C7 sammen med
    #: voyage-arbeidet.
    dock_interaction_range: tuple[int, int]
    #: Havnekontor-bbox for fast-travel-dialog (Fase 3 C3-4). `None` =
    #: havn uten havnekontor-funksjon. Alle 4 havner i default-config har
    #: havnekontor; feltet er optional med default None for å støtte
    #: test-fixtures som konstruerer PortBuildings uten å fylle inn alle
    #: Fase 3-felt. Overlap med tavern/exchange valideres ved load i
    #: `_validate_harbormaster_placement`.
    harbormaster: BuildingPlacement | None = None
    #: Rekvisita-lag (gategulv-tekstur, lanterner, boder, tønner, NPC-
    #: silhuetter). `None` = ingen rekvisita ennå.
    #: Tortuga: C2.5-1. Port Royal: C2.5-2. Havana: C2.5-3. Nassau: C2.5-4.
    props: PortProps | None = None
    #: Havn-spesifikke signatur-bygninger utover tavern + exchange
    #: (klokketårn, rum-magasin, katedral, guvernørpalass, etc).
    #: Tom tuple = kun tavern + exchange (Tortuga i C2.5-1).
    signature_buildings: tuple[SignatureBuilding, ...] = ()
    #: Ankrede skip-silhuetter i havnen (Fase 2.5 C2.5-5).
    #: Bakes inn i foreground SRCALPHA-variantene ved scene-init.
    #: Tematisk variasjon: Tortuga 3 smugler, Port Royal 3 fregatt,
    #: Havana 2-3 imperiell, Nassau 4-5 kaotisk små.
    anchored_ships: tuple[AnchoredShip, ...] = ()
    #: Fyll-bygninger for bystruktur (Fase 2.5 C2.5-6a/6b).
    #: Bakes i gameplay-laget før signatur-bygninger. Tortuga og
    #: Nassau i 6a; Port Royal og Havana i 6b.
    fill_buildings: tuple[FillBuilding, ...] = ()
    #: Smug (åpninger) mellom bygninger. Dokumentasjons-felt;
    #: ikke brukt av bake-pipelinen direkte (smug er fravær av
    #: bygning). Brukes av tester for å verifisere at havet er
    #: synlig gjennom forventede smug-posisjoner.
    alleys: tuple[Alley, ...] = ()
    #: Natur-elementer (palmer, fugler, blomster, ugress).
    #: Fase 2.5 C2.5-7. Bakes i gameplay-laget etter bygninger
    #: slik at fugler på tak/mast og blomster på balkonger havner
    #: over bygnings-silhuettene.
    nature_elements: tuple[NatureElement, ...] = ()
    #: Palette-cycling-animasjoner (C2.5-9). Bål, smithy-esse,
    #: katedral-portal, markedsplass-LANTERN. Muterer gameplay-
    #: surface per frame; billig med <25 px per havn totalt.
    animations: PortAnimations = field(default_factory=PortAnimations)


@dataclass(frozen=True)
class PortConfig:
    """Immutabel struktur per havn lastet fra ports.json.

    Felter som ikke brukes ennå (scene_class, world_map_position osv.)
    parses likevel og lagres for commits som kommer (C3/C4/C5).

    `buildings` er None for havner uten layout ennå (C4: Port Royal,
    Havana, Nassau). C6 legger til deres buildings-felt.
    """
    id: str
    name: str
    world_map_position: tuple[int, int]
    scene_class: str
    world_width: int
    celestial: CelestialConfig
    price_bias: dict[str, float]
    regime_weights: dict[str, dict[str, float]]
    buildings: PortBuildings | None = None


# --- Parsing ---

def _parse_celestial(raw: Any, port_id: str) -> CelestialConfig:
    if not isinstance(raw, dict):
        raise ValueError(f"port '{port_id}': celestial må være et objekt")
    try:
        return CelestialConfig(
            moon_worldx=int(raw["moon_worldx"]),
            sun_worldx_dawn=int(raw["sun_worldx_dawn"]),
            sun_worldx_dusk=int(raw["sun_worldx_dusk"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"port '{port_id}': ugyldig celestial-blokk: {exc}") from exc


def _parse_world_map_position(raw: Any, port_id: str) -> tuple[int, int]:
    if not isinstance(raw, (list, tuple)) or len(raw) != 2:
        raise ValueError(
            f"port '{port_id}': world_map_position må være [x, y]-liste"
        )
    try:
        return (int(raw[0]), int(raw[1]))
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"port '{port_id}': ugyldig world_map_position: {exc}"
        ) from exc


def _parse_price_bias(raw: Any, port_id: str) -> dict[str, float]:
    if not isinstance(raw, dict):
        raise ValueError(f"port '{port_id}': price_bias må være et objekt")
    result: dict[str, float] = {}
    for cid, val in raw.items():
        try:
            result[cid] = float(val)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"port '{port_id}': price_bias[{cid!r}] ugyldig: {exc}"
            ) from exc
    missing = REQUIRED_COMMODITIES - set(result.keys())
    if missing:
        raise ValueError(
            f"port '{port_id}': price_bias mangler varer {sorted(missing)}"
        )
    return result


def _parse_regime_weights(
    raw: Any, port_id: str
) -> dict[str, dict[str, float]]:
    if not isinstance(raw, dict):
        raise ValueError(f"port '{port_id}': regime_weights må være et objekt")
    result: dict[str, dict[str, float]] = {}
    for cid, weights in raw.items():
        if not isinstance(weights, dict):
            raise ValueError(
                f"port '{port_id}': regime_weights[{cid!r}] må være et objekt"
            )
        parsed: dict[str, float] = {}
        for regime_name, weight in weights.items():
            if regime_name not in VALID_REGIME_NAMES:
                raise ValueError(
                    f"port '{port_id}': regime_weights[{cid!r}] ukjent "
                    f"regime-navn {regime_name!r}"
                )
            try:
                parsed[regime_name] = float(weight)
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    f"port '{port_id}': regime_weights[{cid!r}][{regime_name!r}] "
                    f"ugyldig: {exc}"
                ) from exc
        # Alle 3 regime-navn må være til stede slik at random.choices ikke
        # får implisitt vekt 0 på manglende.
        missing_regimes = VALID_REGIME_NAMES - set(parsed.keys())
        if missing_regimes:
            raise ValueError(
                f"port '{port_id}': regime_weights[{cid!r}] mangler regimer "
                f"{sorted(missing_regimes)}"
            )
        total = sum(parsed.values())
        if not math.isclose(total, 1.0, abs_tol=REGIME_WEIGHT_SUM_TOLERANCE):
            raise ValueError(
                f"port '{port_id}': regime_weights[{cid!r}] summerer til "
                f"{total:.4f}, ikke 1.0 (±{REGIME_WEIGHT_SUM_TOLERANCE})"
            )
        result[cid] = parsed
    missing_commodities = REQUIRED_COMMODITIES - set(result.keys())
    if missing_commodities:
        raise ValueError(
            f"port '{port_id}': regime_weights mangler varer "
            f"{sorted(missing_commodities)}"
        )
    return result


def _parse_building_placement(
    raw: Any, port_id: str, building_name: str
) -> BuildingPlacement:
    if not isinstance(raw, dict):
        raise ValueError(
            f"port '{port_id}': buildings.{building_name} må være et objekt"
        )
    try:
        return BuildingPlacement(
            x=int(raw["x"]), y=int(raw["y"]),
            w=int(raw["w"]), h=int(raw["h"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(
            f"port '{port_id}': buildings.{building_name} ugyldig: {exc}"
        ) from exc


def _bboxes_overlap(a: BuildingPlacement, b: BuildingPlacement) -> bool:
    """Returnér True hvis to rektangulære bbox-er overlapper (axis-aligned).

    Brukes til å verifisere at havnekontor-bbox ikke krasjer med tavern
    eller exchange (FASE_3.md C3-4 presisering #3).
    """
    return (
        a.x < b.x + b.w
        and a.x + a.w > b.x
        and a.y < b.y + b.h
        and a.y + a.h > b.y
    )


def _validate_harbormaster_placement(
    hm: BuildingPlacement,
    tavern: BuildingPlacement,
    exchange: BuildingPlacement,
    port_id: str,
) -> None:
    """Kast ValueError hvis havnekontor overlapper tavern eller exchange.

    Fase 3 C3-4 presisering: bbox-overlapp skal eksplisitt sjekkes,
    ikke antas at plassering er disjunkt. `fill_buildings` og
    `signature_buildings` sjekkes IKKE her — havnekontor kan overlappe
    eksisterende bygnings-silhuetter visuelt (bbox-en er logisk for
    interaksjon, ikke rendering).
    """
    if _bboxes_overlap(hm, tavern):
        raise ValueError(
            f"port '{port_id}': harbormaster-bbox overlapper tavern-bbox"
        )
    if _bboxes_overlap(hm, exchange):
        raise ValueError(
            f"port '{port_id}': harbormaster-bbox overlapper exchange-bbox"
        )


def _parse_lantern_posts(
    raw: Any, port_id: str,
) -> tuple[LanternPost, ...]:
    if raw is None:
        return ()
    if not isinstance(raw, list):
        raise ValueError(
            f"port '{port_id}': props.lanterns må være en liste"
        )
    result: list[LanternPost] = []
    for i, entry in enumerate(raw):
        if not isinstance(entry, dict):
            raise ValueError(
                f"port '{port_id}': props.lanterns[{i}] må være et objekt"
            )
        try:
            result.append(LanternPost(x=int(entry["x"])))
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(
                f"port '{port_id}': props.lanterns[{i}] ugyldig: {exc}"
            ) from exc
    return tuple(result)


def _parse_market_stalls(
    raw: Any, port_id: str,
) -> tuple[MarketStall, ...]:
    if raw is None:
        return ()
    if not isinstance(raw, list):
        raise ValueError(
            f"port '{port_id}': props.market_stalls må være en liste"
        )
    result: list[MarketStall] = []
    for i, entry in enumerate(raw):
        if not isinstance(entry, dict):
            raise ValueError(
                f"port '{port_id}': props.market_stalls[{i}] må være et objekt"
            )
        try:
            result.append(
                MarketStall(x=int(entry["x"]), w=int(entry["w"]))
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(
                f"port '{port_id}': props.market_stalls[{i}] ugyldig: {exc}"
            ) from exc
    return tuple(result)


def _parse_barrel_stacks(
    raw: Any, port_id: str,
) -> tuple[BarrelStack, ...]:
    if raw is None:
        return ()
    if not isinstance(raw, list):
        raise ValueError(
            f"port '{port_id}': props.barrel_stacks må være en liste"
        )
    result: list[BarrelStack] = []
    for i, entry in enumerate(raw):
        if not isinstance(entry, dict):
            raise ValueError(
                f"port '{port_id}': props.barrel_stacks[{i}] må være et objekt"
            )
        try:
            count = int(entry["count"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(
                f"port '{port_id}': props.barrel_stacks[{i}] ugyldig: {exc}"
            ) from exc
        if count < 1 or count > 4:
            raise ValueError(
                f"port '{port_id}': props.barrel_stacks[{i}].count må være 1-4, "
                f"fikk {count}"
            )
        try:
            result.append(BarrelStack(x=int(entry["x"]), count=count))
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(
                f"port '{port_id}': props.barrel_stacks[{i}] ugyldig: {exc}"
            ) from exc
    return tuple(result)


def _parse_silhouettes(
    raw: Any, port_id: str,
) -> tuple[SilhouettePlacement, ...]:
    # Valider kind mot entities.npc_silhouette.VALID_KINDS. Importer lazy
    # for å unngå top-level-avhengighet fra config/ til entities/.
    from entities.npc_silhouette import VALID_KINDS as _VALID_SILHOUETTE_KINDS

    if raw is None:
        return ()
    if not isinstance(raw, list):
        raise ValueError(
            f"port '{port_id}': props.silhouettes må være en liste"
        )
    result: list[SilhouettePlacement] = []
    for i, entry in enumerate(raw):
        if not isinstance(entry, dict):
            raise ValueError(
                f"port '{port_id}': props.silhouettes[{i}] må være et objekt"
            )
        try:
            kind = str(entry["kind"])
            x = int(entry["x"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(
                f"port '{port_id}': props.silhouettes[{i}] ugyldig: {exc}"
            ) from exc
        if kind not in _VALID_SILHOUETTE_KINDS:
            raise ValueError(
                f"port '{port_id}': props.silhouettes[{i}].kind={kind!r} "
                f"ikke gyldig (må være en av {sorted(_VALID_SILHOUETTE_KINDS)})"
            )
        result.append(SilhouettePlacement(kind=kind, x=x))
    return tuple(result)


def _parse_iron_fences(
    raw: Any, port_id: str,
) -> tuple[IronFence, ...]:
    if raw is None:
        return ()
    if not isinstance(raw, list):
        raise ValueError(
            f"port '{port_id}': props.iron_fences må være en liste"
        )
    result: list[IronFence] = []
    for i, entry in enumerate(raw):
        if not isinstance(entry, dict):
            raise ValueError(
                f"port '{port_id}': props.iron_fences[{i}] må være et objekt"
            )
        try:
            length = int(entry["length"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(
                f"port '{port_id}': props.iron_fences[{i}] ugyldig: {exc}"
            ) from exc
        if length <= 0:
            raise ValueError(
                f"port '{port_id}': props.iron_fences[{i}].length må være "
                f"positiv, fikk {length}"
            )
        try:
            result.append(IronFence(x=int(entry["x"]), length=length))
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(
                f"port '{port_id}': props.iron_fences[{i}] ugyldig: {exc}"
            ) from exc
    return tuple(result)


def _parse_fountains(raw: Any, port_id: str) -> tuple[Fountain, ...]:
    if raw is None:
        return ()
    if not isinstance(raw, list):
        raise ValueError(
            f"port '{port_id}': props.fountains må være en liste"
        )
    result: list[Fountain] = []
    for i, entry in enumerate(raw):
        if not isinstance(entry, dict):
            raise ValueError(
                f"port '{port_id}': props.fountains[{i}] må være et objekt"
            )
        try:
            result.append(Fountain(x=int(entry["x"])))
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(
                f"port '{port_id}': props.fountains[{i}] ugyldig: {exc}"
            ) from exc
    return tuple(result)


def _parse_planters(raw: Any, port_id: str) -> tuple[Planter, ...]:
    if raw is None:
        return ()
    if not isinstance(raw, list):
        raise ValueError(
            f"port '{port_id}': props.planters må være en liste"
        )
    result: list[Planter] = []
    for i, entry in enumerate(raw):
        if not isinstance(entry, dict):
            raise ValueError(
                f"port '{port_id}': props.planters[{i}] må være et objekt"
            )
        try:
            result.append(Planter(x=int(entry["x"])))
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(
                f"port '{port_id}': props.planters[{i}] ugyldig: {exc}"
            ) from exc
    return tuple(result)


def _parse_bamboo_lanterns(
    raw: Any, port_id: str,
) -> tuple[BambooLantern, ...]:
    if raw is None:
        return ()
    if not isinstance(raw, list):
        raise ValueError(
            f"port '{port_id}': props.bamboo_lanterns må være en liste"
        )
    result: list[BambooLantern] = []
    for i, entry in enumerate(raw):
        if not isinstance(entry, dict):
            raise ValueError(
                f"port '{port_id}': props.bamboo_lanterns[{i}] må være et objekt"
            )
        try:
            result.append(BambooLantern(x=int(entry["x"])))
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(
                f"port '{port_id}': props.bamboo_lanterns[{i}] ugyldig: {exc}"
            ) from exc
    return tuple(result)


def _parse_campfires(raw: Any, port_id: str) -> tuple[Campfire, ...]:
    if raw is None:
        return ()
    if not isinstance(raw, list):
        raise ValueError(
            f"port '{port_id}': props.campfires må være en liste"
        )
    result: list[Campfire] = []
    for i, entry in enumerate(raw):
        if not isinstance(entry, dict):
            raise ValueError(
                f"port '{port_id}': props.campfires[{i}] må være et objekt"
            )
        try:
            result.append(Campfire(x=int(entry["x"])))
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(
                f"port '{port_id}': props.campfires[{i}] ugyldig: {exc}"
            ) from exc
    return tuple(result)


def _parse_chest_stacks(raw: Any, port_id: str) -> tuple[ChestStack, ...]:
    if raw is None:
        return ()
    if not isinstance(raw, list):
        raise ValueError(
            f"port '{port_id}': props.chest_stacks må være en liste"
        )
    result: list[ChestStack] = []
    for i, entry in enumerate(raw):
        if not isinstance(entry, dict):
            raise ValueError(
                f"port '{port_id}': props.chest_stacks[{i}] må være et objekt"
            )
        try:
            count = int(entry["count"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(
                f"port '{port_id}': props.chest_stacks[{i}] ugyldig: {exc}"
            ) from exc
        if count < 1 or count > 3:
            raise ValueError(
                f"port '{port_id}': props.chest_stacks[{i}].count må være 1-3, "
                f"fikk {count}"
            )
        try:
            result.append(ChestStack(x=int(entry["x"]), count=count))
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(
                f"port '{port_id}': props.chest_stacks[{i}] ugyldig: {exc}"
            ) from exc
    return tuple(result)


def _parse_props(raw: Any, port_id: str) -> PortProps | None:
    """Parse props-blokken. None hvis feltet mangler eller er null."""
    # Lazy import for å unngå top-level-avhengighet fra config/ til
    # entities/. VALID_GROUND_TEXTURES er en frozenset av strenger.
    from entities.port_props import VALID_GROUND_TEXTURES

    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise ValueError(
            f"port '{port_id}': props må være et objekt eller null"
        )
    try:
        ground_texture = str(raw["ground_texture"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(
            f"port '{port_id}': props.ground_texture mangler: {exc}"
        ) from exc
    if ground_texture not in VALID_GROUND_TEXTURES:
        raise ValueError(
            f"port '{port_id}': props.ground_texture={ground_texture!r} "
            f"ikke gyldig (må være en av {sorted(VALID_GROUND_TEXTURES)})"
        )
    return PortProps(
        ground_texture=ground_texture,
        lanterns=_parse_lantern_posts(raw.get("lanterns"), port_id),
        market_stalls=_parse_market_stalls(raw.get("market_stalls"), port_id),
        barrel_stacks=_parse_barrel_stacks(raw.get("barrel_stacks"), port_id),
        silhouettes=_parse_silhouettes(raw.get("silhouettes"), port_id),
        iron_fences=_parse_iron_fences(raw.get("iron_fences"), port_id),
        fountains=_parse_fountains(raw.get("fountains"), port_id),
        planters=_parse_planters(raw.get("planters"), port_id),
        bamboo_lanterns=_parse_bamboo_lanterns(
            raw.get("bamboo_lanterns"), port_id,
        ),
        campfires=_parse_campfires(raw.get("campfires"), port_id),
        chest_stacks=_parse_chest_stacks(raw.get("chest_stacks"), port_id),
    )


#: Gyldige signatur-bygning-kinds. Matches mot bake-funksjoner i
#: `scenes/port_buildings.py`. Utvides per commit:
#: - C2.5-2: church_tower, rum_warehouse (Port Royal)
#: - C2.5-3: cathedral, governor_palace (Havana)
#: - C2.5-4: teachs_house, shipyard (Nassau)
VALID_SIGNATURE_BUILDING_KINDS: frozenset[str] = frozenset({
    "church_tower", "rum_warehouse",
    "cathedral", "governor_palace",
    "teachs_house", "shipyard",
})


def _parse_signature_buildings(
    raw: Any, port_id: str,
) -> tuple[SignatureBuilding, ...]:
    if raw is None:
        return ()
    if not isinstance(raw, list):
        raise ValueError(
            f"port '{port_id}': buildings.signature_buildings må være en liste"
        )
    result: list[SignatureBuilding] = []
    for i, entry in enumerate(raw):
        if not isinstance(entry, dict):
            raise ValueError(
                f"port '{port_id}': signature_buildings[{i}] må være et objekt"
            )
        try:
            kind = str(entry["kind"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(
                f"port '{port_id}': signature_buildings[{i}] ugyldig: {exc}"
            ) from exc
        if kind not in VALID_SIGNATURE_BUILDING_KINDS:
            raise ValueError(
                f"port '{port_id}': signature_buildings[{i}].kind={kind!r} "
                f"ikke gyldig (må være en av "
                f"{sorted(VALID_SIGNATURE_BUILDING_KINDS)})"
            )
        try:
            placement = BuildingPlacement(
                x=int(entry["x"]), y=int(entry["y"]),
                w=int(entry["w"]), h=int(entry["h"]),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(
                f"port '{port_id}': signature_buildings[{i}] ugyldig "
                f"placement: {exc}"
            ) from exc
        result.append(SignatureBuilding(kind=kind, placement=placement))
    return tuple(result)


def _parse_fill_buildings(
    raw: Any, port_id: str,
) -> tuple[FillBuilding, ...]:
    # Lazy import for å unngå top-level-avhengighet fra config/ til entities/
    from entities.fill_buildings import (
        VALID_FILL_BUILDING_KINDS,
        MAX_FILL_BUILDING_HEIGHT,
    )

    if raw is None:
        return ()
    if not isinstance(raw, list):
        raise ValueError(
            f"port '{port_id}': fill_buildings må være en liste"
        )
    result: list[FillBuilding] = []
    for i, entry in enumerate(raw):
        if not isinstance(entry, dict):
            raise ValueError(
                f"port '{port_id}': fill_buildings[{i}] må være et objekt"
            )
        try:
            kind = str(entry["kind"])
            x = int(entry["x"])
            w = int(entry["w"])
            h = int(entry["h"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(
                f"port '{port_id}': fill_buildings[{i}] ugyldig: {exc}"
            ) from exc
        style_variant = int(entry.get("style_variant", 0))
        if kind not in VALID_FILL_BUILDING_KINDS:
            raise ValueError(
                f"port '{port_id}': fill_buildings[{i}].kind={kind!r} "
                f"ikke gyldig (må være en av "
                f"{sorted(VALID_FILL_BUILDING_KINDS)})"
            )
        if h > MAX_FILL_BUILDING_HEIGHT:
            raise ValueError(
                f"port '{port_id}': fill_buildings[{i}] h={h} > maks "
                f"{MAX_FILL_BUILDING_HEIGHT} (silhuett-hierarki-brudd)"
            )
        if h < 16:
            raise ValueError(
                f"port '{port_id}': fill_buildings[{i}] h={h} < 16 "
                f"(for lav for bygning)"
            )
        result.append(FillBuilding(
            kind=kind, x=x, w=w, h=h, style_variant=style_variant,
        ))
    return tuple(result)


#: Gyldige alley-contents-verdier (C2.5-7 smug-innhold).
_VALID_ALLEY_CONTENTS: frozenset[str] = frozenset({
    "ropes",          # Tortuga
    "barrels",        # Tortuga
    "weeds",          # Port Royal
    "flower_pot",     # Havana
    "palm",           # Nassau
    "sand_drift",     # Nassau
})


def _parse_alleys(
    raw: Any, port_id: str,
) -> tuple[Alley, ...]:
    if raw is None:
        return ()
    if not isinstance(raw, list):
        raise ValueError(
            f"port '{port_id}': alleys må være en liste"
        )
    result: list[Alley] = []
    for i, entry in enumerate(raw):
        if not isinstance(entry, dict):
            raise ValueError(
                f"port '{port_id}': alleys[{i}] må være et objekt"
            )
        try:
            x = int(entry["x"])
            w = int(entry["w"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(
                f"port '{port_id}': alleys[{i}] ugyldig: {exc}"
            ) from exc
        # Spec §1.4 krever 20-40 px; vi aksepterer 16-40 for grense-
        # fleksibilitet i trange havner (Nassau).
        if not (16 <= w <= 40):
            raise ValueError(
                f"port '{port_id}': alleys[{i}].w={w} utenfor [16, 40]"
            )
        contents = entry.get("contents")
        if contents is not None:
            contents = str(contents)
            if contents not in _VALID_ALLEY_CONTENTS:
                raise ValueError(
                    f"port '{port_id}': alleys[{i}].contents={contents!r} "
                    f"ikke gyldig (må være en av "
                    f"{sorted(_VALID_ALLEY_CONTENTS)})"
                )
        result.append(Alley(x=x, w=w, contents=contents))
    return tuple(result)


def _parse_palette_cycles(
    raw: Any, port_id: str,
) -> tuple[PaletteCycle, ...]:
    # Lazy import for å unngå top-level-avhengighet
    from systems.animations import PALETTE_NAMES

    if raw is None:
        return ()
    if not isinstance(raw, list):
        raise ValueError(
            f"port '{port_id}': animations.palette_cycles må være en liste"
        )
    result: list[PaletteCycle] = []
    for i, entry in enumerate(raw):
        if not isinstance(entry, dict):
            raise ValueError(
                f"port '{port_id}': palette_cycles[{i}] må være et objekt"
            )
        try:
            x = int(entry["x"])
            y = int(entry["y"])
            w = int(entry["w"])
            h = int(entry["h"])
            palette_list = entry["palette"]
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(
                f"port '{port_id}': palette_cycles[{i}] ugyldig: {exc}"
            ) from exc
        if not isinstance(palette_list, list) or len(palette_list) < 2:
            raise ValueError(
                f"port '{port_id}': palette_cycles[{i}].palette må være "
                f"liste med minst 2 farger"
            )
        palette_tuple: tuple[str, ...] = tuple(str(c) for c in palette_list)
        for color_name in palette_tuple:
            if color_name not in PALETTE_NAMES:
                raise ValueError(
                    f"port '{port_id}': palette_cycles[{i}] har ukjent "
                    f"palett-navn {color_name!r} (gyldige: "
                    f"{sorted(PALETTE_NAMES.keys())})"
                )
        fps = float(entry.get("fps", 6.0))
        permanent = bool(entry.get("permanent", False))
        result.append(PaletteCycle(
            x=x, y=y, w=w, h=h, palette=palette_tuple,
            fps=fps, permanent=permanent,
        ))
    return tuple(result)


def _parse_animations(
    raw: Any, port_id: str,
) -> PortAnimations:
    if raw is None:
        return PortAnimations()
    if not isinstance(raw, dict):
        raise ValueError(
            f"port '{port_id}': animations må være et objekt"
        )
    palette_cycles = _parse_palette_cycles(
        raw.get("palette_cycles"), port_id,
    )
    alpha_pulse = bool(raw.get("alpha_pulse_windows", False))
    return PortAnimations(
        palette_cycles=palette_cycles,
        alpha_pulse_windows=alpha_pulse,
    )


def _parse_nature_elements(
    raw: Any, port_id: str,
) -> tuple[NatureElement, ...]:
    # Lazy import for å unngå top-level-avhengighet fra config/ til entities/
    from entities.nature import VALID_NATURE_KINDS

    if raw is None:
        return ()
    if not isinstance(raw, list):
        raise ValueError(
            f"port '{port_id}': nature_elements må være en liste"
        )
    result: list[NatureElement] = []
    for i, entry in enumerate(raw):
        if not isinstance(entry, dict):
            raise ValueError(
                f"port '{port_id}': nature_elements[{i}] må være et objekt"
            )
        try:
            kind = str(entry["kind"])
            x = int(entry["x"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(
                f"port '{port_id}': nature_elements[{i}] ugyldig: {exc}"
            ) from exc
        if kind not in VALID_NATURE_KINDS:
            raise ValueError(
                f"port '{port_id}': nature_elements[{i}].kind={kind!r} "
                f"ikke gyldig (må være en av {sorted(VALID_NATURE_KINDS)})"
            )
        y = int(entry.get("y", 0))
        result.append(NatureElement(kind=kind, x=x, y=y))
    return tuple(result)


def _parse_anchored_ships(
    raw: Any, port_id: str,
) -> tuple[AnchoredShip, ...]:
    # Lazy import for å unngå top-level-avhengighet fra config/ til entities/
    from entities.anchored_ship import VALID_SHIP_KINDS

    if raw is None:
        return ()
    if not isinstance(raw, list):
        raise ValueError(
            f"port '{port_id}': anchored_ships må være en liste"
        )
    result: list[AnchoredShip] = []
    for i, entry in enumerate(raw):
        if not isinstance(entry, dict):
            raise ValueError(
                f"port '{port_id}': anchored_ships[{i}] må være et objekt"
            )
        try:
            kind = str(entry["kind"])
            x = int(entry["x"])
            y = int(entry["y"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(
                f"port '{port_id}': anchored_ships[{i}] ugyldig: {exc}"
            ) from exc
        if kind not in VALID_SHIP_KINDS:
            raise ValueError(
                f"port '{port_id}': anchored_ships[{i}].kind={kind!r} "
                f"ikke gyldig (må være en av {sorted(VALID_SHIP_KINDS)})"
            )
        flipped = bool(entry.get("flipped", False))
        tilted = bool(entry.get("tilted", False))
        if tilted and kind != "pirate":
            raise ValueError(
                f"port '{port_id}': anchored_ships[{i}]: 'tilted' er kun "
                f"gyldig for kind='pirate', fikk kind={kind!r}"
            )
        result.append(AnchoredShip(
            x=x, y=y, kind=kind, flipped=flipped, tilted=tilted,
        ))
    return tuple(result)


def _parse_buildings(raw: Any, port_id: str) -> PortBuildings | None:
    """Parse buildings-blokken. None hvis feltet mangler eller er null
    (havn uten layout ennå).
    """
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise ValueError(
            f"port '{port_id}': buildings må være et objekt eller null"
        )
    try:
        ground_top_y = int(raw["ground_top_y"])
        player_start_x = int(raw["player_start_x"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(
            f"port '{port_id}': buildings mangler/ugyldig felt: {exc}"
        ) from exc
    tavern = _parse_building_placement(raw.get("tavern"), port_id, "tavern")
    exchange = _parse_building_placement(
        raw.get("exchange"), port_id, "exchange"
    )
    # Fase 3 C3-4: havnekontor er optional i skjemaet (for testfiksturer),
    # men i default-config skal alle 4 havner ha det. Valider overlap mot
    # tavern/exchange — presisering C3-4 #3.
    harbormaster_raw = raw.get("harbormaster")
    if harbormaster_raw is None:
        harbormaster: BuildingPlacement | None = None
    else:
        harbormaster = _parse_building_placement(
            harbormaster_raw, port_id, "harbormaster"
        )
        _validate_harbormaster_placement(harbormaster, tavern, exchange, port_id)
    npcs_raw = raw.get("npcs", {})
    if not isinstance(npcs_raw, dict):
        raise ValueError(
            f"port '{port_id}': buildings.npcs må være et objekt"
        )
    npcs: dict[str, int] = {}
    for npc_id, x_raw in npcs_raw.items():
        try:
            npcs[str(npc_id)] = int(x_raw)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"port '{port_id}': buildings.npcs[{npc_id!r}] ugyldig: {exc}"
            ) from exc
    # dock_interaction_range er obligatorisk (fail-fast) — introdusert
    # i C6, ikke valgfritt med fallback.
    dock_raw = raw.get("dock_interaction_range")
    if not isinstance(dock_raw, (list, tuple)) or len(dock_raw) != 2:
        raise ValueError(
            f"port '{port_id}': buildings.dock_interaction_range må være "
            f"[min_x, max_x]-liste"
        )
    try:
        dock_range = (int(dock_raw[0]), int(dock_raw[1]))
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"port '{port_id}': buildings.dock_interaction_range ugyldig: "
            f"{exc}"
        ) from exc
    if dock_range[0] >= dock_range[1]:
        raise ValueError(
            f"port '{port_id}': buildings.dock_interaction_range "
            f"min_x ({dock_range[0]}) må være mindre enn max_x "
            f"({dock_range[1]})"
        )
    props = _parse_props(raw.get("props"), port_id)
    signature_buildings = _parse_signature_buildings(
        raw.get("signature_buildings"), port_id,
    )
    anchored_ships = _parse_anchored_ships(
        raw.get("anchored_ships"), port_id,
    )
    fill_buildings = _parse_fill_buildings(
        raw.get("fill_buildings"), port_id,
    )
    alleys = _parse_alleys(raw.get("alleys"), port_id)
    nature_elements = _parse_nature_elements(
        raw.get("nature_elements"), port_id,
    )
    animations = _parse_animations(raw.get("animations"), port_id)
    return PortBuildings(
        ground_top_y=ground_top_y,
        player_start_x=player_start_x,
        tavern=tavern,
        exchange=exchange,
        npcs=npcs,
        dock_interaction_range=dock_range,
        harbormaster=harbormaster,
        props=props,
        signature_buildings=signature_buildings,
        anchored_ships=anchored_ships,
        fill_buildings=fill_buildings,
        alleys=alleys,
        nature_elements=nature_elements,
        animations=animations,
    )


def _parse_port(port_id: str, raw: Any) -> PortConfig:
    if not isinstance(raw, dict):
        raise ValueError(f"port '{port_id}': må være et objekt")
    try:
        name = str(raw["name"])
        scene_class = str(raw["scene_class"])
        world_width = int(raw["world_width"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"port '{port_id}': ugyldig toppnivå-felt: {exc}") from exc
    return PortConfig(
        id=port_id,
        name=name,
        world_map_position=_parse_world_map_position(
            raw.get("world_map_position"), port_id
        ),
        scene_class=scene_class,
        world_width=world_width,
        celestial=_parse_celestial(raw.get("celestial"), port_id),
        price_bias=_parse_price_bias(raw.get("price_bias"), port_id),
        regime_weights=_parse_regime_weights(raw.get("regime_weights"), port_id),
        buildings=_parse_buildings(raw.get("buildings"), port_id),
    )


def load_ports(path: str) -> dict[str, PortConfig]:
    """Les ports.json fra disk og bygg dict[port_id, PortConfig].

    Feil:
    - `FileNotFoundError` med klar melding hvis filen mangler
    - `ValueError` hvis JSON er ugyldig, havner mangler, eller vekter ikke
      summerer til 1.0
    """
    try:
        with open(path, "r", encoding="utf-8") as fh:
            raw = json.load(fh)
    except FileNotFoundError as exc:
        raise FileNotFoundError(
            f"ports-config mangler: {path} — "
            "data/ports.json er påkrevd for spill-oppstart"
        ) from exc
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"ports-config {path} inneholder ugyldig JSON: {exc}"
        ) from exc

    if not isinstance(raw, dict):
        raise ValueError(f"ports-config {path}: rot-objektet må være en dict")

    ports_raw = raw.get("ports")
    if not isinstance(ports_raw, dict):
        raise ValueError(
            f"ports-config {path}: 'ports'-feltet må være et objekt"
        )

    missing = REQUIRED_PORTS - set(ports_raw.keys())
    if missing:
        raise ValueError(
            f"ports-config {path}: mangler påkrevde havner {sorted(missing)}"
        )

    result: dict[str, PortConfig] = {}
    for port_id, port_raw in ports_raw.items():
        result[port_id] = _parse_port(port_id, port_raw)
    return result


# --- Singleton ---

_ports: dict[str, PortConfig] | None = None
_path: str = DEFAULT_PORTS_PATH


def init(path: str = DEFAULT_PORTS_PATH) -> dict[str, PortConfig]:
    """Last ports.json eksplisitt ved oppstart.

    Feiler høylydt ved manglende eller ødelagt fil — dette er en konfig-
    feil som skal stoppe spillet, ikke la det kjøre videre med tomme
    havner.
    """
    global _ports, _path
    _path = path
    _ports = load_ports(path)
    log.info("PortConfig lastet fra %s (%d havner)", path, len(_ports))
    return _ports


def get(port_id: str) -> PortConfig:
    """Returner PortConfig for gitt havn-id. Krever at `init()` er kalt."""
    if _ports is None:
        raise RuntimeError(
            "PortConfig ikke initialisert. Kall config.port_config.init() først."
        )
    if port_id not in _ports:
        raise KeyError(f"Ukjent port_id: {port_id!r}")
    return _ports[port_id]


def get_all() -> dict[str, PortConfig]:
    """Returner hele dict[port_id, PortConfig]. Krever init()."""
    if _ports is None:
        raise RuntimeError(
            "PortConfig ikke initialisert. Kall config.port_config.init() først."
        )
    return _ports


def get_all_port_ids() -> list[str]:
    """Returner sortert liste av havn-id-er. Tortuga først (home_port)."""
    if _ports is None:
        raise RuntimeError(
            "PortConfig ikke initialisert. Kall config.port_config.init() først."
        )
    # Stabil rekkefølge: tortuga først, resten i alfabetisk orden
    others = sorted(pid for pid in _ports if pid != "tortuga")
    return ["tortuga"] + others


def is_initialized() -> bool:
    return _ports is not None


def _reset_for_tests() -> None:
    """Tøm singleton. Kun for bruk i tester."""
    global _ports, _path
    _ports = None
    _path = DEFAULT_PORTS_PATH
