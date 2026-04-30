"""Globale konstanter, palett og ytelsesgrenser for Pitch & Plunder.

Importér denne modulen FØRST i ethvert entry point. Den setter nødvendige
SDL/pygame env vars før pygame lastes, slik at skalering, støyfri oppstart
og sentrert vindu oppfører seg forutsigbart på målmaskinen (per v2.7:
AMD A10-5757M / Radeon HD 8650G / OpenGL 4.5).
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
TARGET_FPS = 60  # v2.7: heves fra 30 da T4200-støtte droppes.

# --- Grafikk-presets (v2.7) ---
# "high": ModernGL post-FX (bloom, color grading, valgfri CRT). Standard.
# "low":  Ren pygame-rendering. Fallback ved GL-init-feil eller bruker-valg.
GRAPHICS_PRESET_HIGH = "high"
GRAPHICS_PRESET_LOW = "low"
DEFAULT_GRAPHICS_PRESET = GRAPHICS_PRESET_HIGH

# --- Ytelsesgrenser (per v2.7-budsjett) ---
# Verdiene under er for "high"-preset. "low"-preset bruker de gamle T4200-tallene
# (4 lights, 20 particles, 3 parallax-lag) og leses fra _LOW_PRESET_BUDGETS.
MAX_DYNAMIC_LIGHTS = 12
MAX_PARTICLES = 150
MAX_PARALLAX_LAYERS_PHASE_1 = 5
# WORLD_WIDTH er fortsatt 1600 selv om v2.7-spec-cap er 2400. Eksisterende
# scener (Tortuga, Port Royal, Havana, Nassau) er bygget for 1600. Heves
# per scene når de ombygges, ikke globalt.
WORLD_WIDTH = 1600

_LOW_PRESET_BUDGETS = {
    "max_dynamic_lights": 4,
    "max_particles": 20,
    "max_parallax_layers": 3,
    "target_fps": 30,
}

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
# Økonomiske konstanter og SECONDS_PER_DAY er flyttet til data/balance.json
# i Fase 2B Commit C1a. Les via `systems.balance.get()`.
# MARKET_TICK_INTERVAL_SEC er dead fra Fase 2A Commit 5C; fjernet her.
PLAYER_WALK_SPEED = 80  # px/sek
INTERACTION_DISTANCE = 40

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
KEY_DEV_RELOAD = (pygame.K_F5,)  # Dev-mode: last balance.json på nytt (Fase 2B C1a)
KEY_RUMORS = (pygame.K_r,)  # Fase 3 C3-9: åpner RumorsDialog
