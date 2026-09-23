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

# --- Player / Camera ---
PLAYER_SPEED        = 0.004     # was 0.003 — bumped ~30%, applies to WASD + space/shift
MOUSE_SENSITIVITY   = 0.12      # was 0.002 — way too low, ~60x more here
FOV                 = 50        # field of view in degrees
NEAR_PLANE          = 0.1       # closest distance camera renders
FAR_PLANE           = 2000.0    # furthest distance camera renders

# --- World Generation ---
WORLD_SEED           = 42       # change this to get a different-looking world
NOISE_SCALE          = 0.08     # smaller = smoother, larger = spikier terrain
NOISE_OCTAVES        = 3        # layers of detail in the noise
TERRAIN_BASE_HEIGHT  = 6        # average ground height (in blocks, 0-15)
TERRAIN_AMPLITUDE    = 4        # how far hills rise/fall from the base height

# --- Background color (sky) ---
BG_COLOR            = (0.58, 0.83, 0.99)    # light blue RGB values 0.0 to 1.0