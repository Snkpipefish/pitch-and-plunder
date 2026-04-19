"""Globale konstanter, palett og ytelsesgrenser for Pitch & Plunder.

Importér denne modulen FØRST i ethvert entry point. Den setter nødvendige
SDL/pygame env vars før pygame lastes, slik at skalering, støyfri oppstart
og sentrert vindu oppfører seg forutsigbart på målmaskinen (GM45 / T4200).
"""

import os

# Env vars MÅ settes før pygame importeres for å ha effekt.
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
os.environ["SDL_HINT_RENDER_SCALE_QUALITY"] = "0"  # Nearest-neighbor
os.environ["SDL_VIDEO_CENTERED"] = "1"

import pygame  # noqa: E402  (må komme etter env-vars)

# --- Oppløsning og ytelse ---
RENDER_WIDTH = 640
RENDER_HEIGHT = 360
DEFAULT_SCALE = 2
DEFAULT_WINDOW_SIZE = (RENDER_WIDTH * DEFAULT_SCALE, RENDER_HEIGHT * DEFAULT_SCALE)
TARGET_FPS = 30  # 30, ikke 60 – målmaskin krever dette.

# --- Ytelsesgrenser ---
MAX_DYNAMIC_LIGHTS = 4
MAX_PARTICLES = 20
MAX_PARALLAX_LAYERS_PHASE_1 = 3
WORLD_WIDTH = 1600

# --- Events som skal blokkeres (reduserer event-kø-trykk) ---
BLOCKED_EVENTS = [
    pygame.MOUSEMOTION,
    pygame.ACTIVEEVENT,
    pygame.VIDEOEXPOSE,
    pygame.VIDEORESIZE,
]

# --- Palett (hex → RGB) ---
# Himmel & natt
COLOR_SKY_DEEP = (10, 14, 39)
COLOR_SKY_MID = (26, 31, 77)
COLOR_SKY_HORIZON = (45, 53, 97)

# Måne & varmt lys
COLOR_MOON_CORE = (255, 248, 231)
COLOR_MOON_HALO = (245, 230, 179)
COLOR_LANTERN_BRIGHT = (255, 213, 128)
COLOR_LANTERN = (255, 179, 71)
COLOR_FLAME = (255, 140, 66)
COLOR_EMBER = (217, 108, 46)
COLOR_WATER_GLINT = (232, 194, 122)

# Sjø
COLOR_SEA_DEEP = (15, 24, 41)
COLOR_SEA_MID = (30, 42, 74)
COLOR_SEA_LIGHT = (42, 58, 94)
COLOR_SEA_HIGHLIGHT = (74, 90, 138)

# Varmt tre
COLOR_WOOD_DARKEST = (26, 20, 16)
COLOR_WOOD_DARK = (42, 32, 24)
COLOR_WOOD_MID = (61, 48, 36)
COLOR_WOOD_LIGHT = (92, 74, 53)

# Kald stein / marmor
COLOR_STONE_DARKEST = (21, 26, 42)
COLOR_STONE_DARK = (31, 37, 56)
COLOR_STONE_MID = (45, 53, 72)
COLOR_STONE_LIGHT = (61, 70, 96)
COLOR_STONE_LIT = (107, 139, 199)
COLOR_STONE_BRIGHT = (139, 168, 214)

# Karakterer
COLOR_HAT = (26, 22, 32)
COLOR_COAT = (61, 53, 72)
COLOR_SKIN = (196, 145, 113)
COLOR_SHIRT = (232, 220, 196)

# Tåke & atmosfære (bruk med lav alpha)
COLOR_FOG = (58, 58, 74)

# Dag-natt-syklus (Fase 2A Commit 5A). Alle fra eksisterende 30-palett.
# Sol-farger gjennom dagen: varm daggry → hvit middag → brennende kveld.
COLOR_SUN_DAWN = COLOR_LANTERN           # (255, 179, 71)  varm lav sol
COLOR_SUN_DAY = COLOR_MOON_CORE          # (255, 248, 231) hvit middag
COLOR_SUN_DUSK = COLOR_EMBER             # (217, 108, 46)  kveld
# Himmelfarger gjennom dagen (topp og horisont). Matcher review-spec
# (#6b8bc7 = STONE_LIT som dag-topp); nødvendig for monoton lysning
# gjennom morgen-fasen. Tidligere (STONE_LIGHT) ga dagen et dunet
# overcast-preg i stedet for klarblå himmel.
COLOR_SKY_DAY_TOP = COLOR_STONE_LIT          # (107, 139, 199) klarblå
COLOR_SKY_DAY_HORIZON = COLOR_STONE_BRIGHT   # (139, 168, 214) lys blå horisont
COLOR_SKY_DUSK_TOP = COLOR_COAT              # (61, 53, 72)    dempet lilla
COLOR_SKY_DUSK_HORIZON = COLOR_EMBER         # (217, 108, 46)  brennende horisont
# Natthimmel og måne finnes allerede via COLOR_SKY_DEEP/MID/HORIZON + COLOR_MOON_CORE

# --- Gameplay (tid og bevegelse) ---
MARKET_TICK_INTERVAL_SEC = 10.0
SECONDS_PER_DAY = 180.0  # Fase 2A Commit 5C: 180 s/dag (30 morgen + 120 dag + 30 natt).
# MARKET_TICK_INTERVAL_SEC er ikke lenger i bruk: priser endres kun ved daggry.
# Konstanten beholdes for at save-migreringstester og historiske kjøringer skal
# kunne referere den; kan fjernes i Commit 8-polish hvis ingen bruker den da.
PLAYER_WALK_SPEED = 80  # px/sek
INTERACTION_DISTANCE = 40

# --- Økonomiske konstanter (under balansering) ---
#
# Alle tall i denne seksjonen er provisoriske. Ekte balansering kan ikke
# gjøres før Fase 2B (seiling + flere havner), Fase 3 (piratinntekter),
# og Fase 5 (hendelser og markedsmanipulasjon). Se FASE_2A.md
# §"Kjente issues" → "Økonomisk balansering er midlertidig" for full
# begrunnelse.
#
# Endring av et av disse tallene skal ikke kreve endringer andre steder
# i kodebasen – alt økonomi-relatert leser fra `constants`.

STARTING_GOLD = 300                        # Dubloner ved fersk spillstart
CARGO_CAPACITY_DEFAULT = 40                # Totalt antall enheter i lasterom
TRANSACTION_FEE = 5                        # Dubloner per kjøp/salg (Commit 7)
PITCH_LAKE_DEFAULT_PRODUCTION = 2          # Bek per dag ved daggry
PITCH_LAKE_DEFAULT_UPKEEP = 8              # Dubloner per dag (arbeidere, leie, transport)

# --- Stier ---
SAVE_PATH = "saves/savegame.json"
DATA_DIR = "data"
ASSETS_DIR = "assets"

# --- Taster ---
KEY_LEFT = (pygame.K_a, pygame.K_LEFT)
KEY_RIGHT = (pygame.K_d, pygame.K_RIGHT)
KEY_UP = (pygame.K_w, pygame.K_UP)
KEY_DOWN = (pygame.K_s, pygame.K_DOWN)
KEY_INTERACT = (pygame.K_e,)
KEY_MENU = (pygame.K_ESCAPE,)
KEY_CONFIRM = (pygame.K_RETURN,)
KEY_FULLSCREEN = (pygame.K_F11,)
