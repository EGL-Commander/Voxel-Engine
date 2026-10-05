# =============================================================================
# SETTINGS — Global configuration for the entire engine
# Every module imports from here. Change values here, they change everywhere.
# =============================================================================

# --- Window ---
WINDOW_TITLE        = 'Voxel Engine'
WINDOW_WIDTH        = 1280
WINDOW_HEIGHT       = 720
WINDOW_ASPECT_RATIO = WINDOW_WIDTH / WINDOW_HEIGHT

# --- OpenGL ---
OPENGL_MAJOR_VERSION = 3
OPENGL_MINOR_VERSION = 3

# --- World / Chunks ---
CHUNK_SIZE          = 16        # each chunk is 16 x 16 x 16 blocks
RENDER_DISTANCE     = 4         # how many chunks to load around the player
CHUNKS_PER_FRAME    = 2         # how many chunk loads/remeshes to process per
                                 # frame after the initial load — spreads a
                                 # chunk-boundary crossing's work (previously
                                 # all done in one frame, ~100-200ms stutter)
                                 # across several frames instead

# --- Player / Camera ---
PLAYER_SPEED        = 0.004     # was 0.003 — bumped ~30%, applies to WASD + space/shift
SPRINT_MULTIPLIER   = 1.6       # holding shift while moving multiplies speed by this
FLY_SPEED           = 0.008     # horizontal AND vertical speed while flying
                                 # (creative mode) — faster than normal walking
                                 # speed since flying is meant for covering
                                 # ground quickly to explore/showcase the world
MOUSE_SENSITIVITY   = 0.12      # was 0.002 — way too low, ~60x more here
FOV                 = 50        # field of view in degrees
NEAR_PLANE          = 0.1       # closest distance camera renders
FAR_PLANE           = 2000.0    # furthest distance camera renders

# --- HUD ---
CROSSHAIR_SIZE      = 0.02      # half-length of each crosshair line, in NDC units
HUD_FONT_SIZE       = 22        # debug text size, in pixels
HUD_UPDATE_MS       = 100       # how often the debug text is re-rendered

# --- Saving ---
AUTOSAVE_INTERVAL_MS = 30000     # how often the game autosaves while running,
                                  # on top of always saving on quit and F5

# --- Physics ---
# All in blocks per millisecond (or per ms^2 for gravity) since dt comes from
# pygame's clock in milliseconds. Space is now a jump instead of fly-up;
# gravity + collision replace the old free-flying camera movement.
GRAVITY             = 0.00004   # downward acceleration
JUMP_SPEED          = 0.01      # upward velocity applied the instant you jump
JUMP_COOLDOWN_MS    = 600       # was 300 — still felt instant/rapid, doubled
EYE_HEIGHT          = 1.6       # camera sits this many blocks above your feet
PLAYER_HEIGHT       = 1.8       # total collision box height, in blocks
PLAYER_HALF_WIDTH   = 0.3       # half the collision box's width/depth, in blocks
MAX_DT_MS           = 50        # cap one frame's dt (e.g. after the slow first
                                 # frame spent building chunks) so physics never
                                 # takes one giant catch-up step and falls through
                                 # the floor — always simulate in small steps

# --- Block Interaction ---
REACH_DISTANCE      = 4.5       # was 6.0 — verified the raycast itself is
                                 # direction-consistent (tested: a target at
                                 # the same Euclidean distance in 4 different
                                 # directions hits exactly right every time),
                                 # so the "reach feels inconsistent" was really
                                 # just "reach is long enough that small
                                 # differences become noticeable" — shortening
                                 # it to Minecraft's own default reach fixes both
                                 # complaints (too far AND feels inconsistent)
                                 # at once
RAYCAST_STEP        = 0.05      # smaller = more precise aim, more checks per click

# --- World Generation ---
# Leave this as None for a brand-new random world every launch (that's the
# default). Set it to a number (e.g. 42) instead to always regenerate that
# exact same world — handy for reproducing a bug or showing someone the
# same terrain twice.
WORLD_SEED = None

# Resolved here, once, when settings is first imported, so every part of the
# game (spawn search, chunk generation, ...) agrees on the same seed this
# run. The try/except is a safety net: if the WORLD_SEED line above ever
# gets deleted or commented out, this falls back to random instead of
# crashing the whole game with a NameError.
import random as _random
try:
    _seed_setting = WORLD_SEED
except NameError:
    _seed_setting = None
WORLD_SEED = _seed_setting if _seed_setting is not None else _random.randrange(1_000_000)
NOISE_SCALE          = 0.08     # smaller = smoother, larger = spikier terrain
NOISE_OCTAVES        = 3        # layers of detail in the noise
TERRAIN_BASE_HEIGHT  = 6        # average ground height (in blocks, 0-15)
TERRAIN_AMPLITUDE    = 4        # how far hills rise/fall from the base height

# --- Biomes ---
BIOME_SCALE          = 0.012    # much smaller than NOISE_SCALE = big regions
BIOME_DESERT_MAX     = -0.12    # biome noise below this -> desert
BIOME_SNOW_MIN       = 0.12     # biome noise above this -> snow (between = plains)

# --- Caves ---
CAVE_NOISE_SCALE     = 0.08     # smaller = larger, smoother caverns
CAVE_THRESHOLD       = 0.35     # was 0.3 — tested (flood-fill analysis): 0.3
                                 # produced caverns over 400 voxels large in
                                 # places (looked like vast open rooms, and
                                 # large enough in one case to see clear
                                 # through gaps to the unrendered void below
                                 # the world). 0.35 keeps density reasonable
                                 # (~1.8% of stone) while keeping the largest
                                 # connected caverns closer to 20-30 voxels —
                                 # modest pockets/tunnels instead of rooms
CAVE_MIN_Y           = 2        # never carve below this height — guarantees a
                                 # solid floor at the world's bottom, so a cave
                                 # can never open straight through into the
                                 # unrendered void below y=0 (that gap has no
                                 # actual mesh, just an implicit "solid" for
                                 # collision, so without this buffer you could
                                 # see clean through to background sky)

# --- Background color (sky) ---
BG_COLOR            = (0.58, 0.83, 0.99)    # light blue RGB values 0.0 to 1.0