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
PLAYER_SPEED        = 0.005
MOUSE_SENSITIVITY   = 0.002
FOV                 = 50        # field of view in degrees
NEAR_PLANE          = 0.1       # closest distance camera renders
FAR_PLANE           = 2000.0    # furthest distance camera renders

# --- Background color (sky) ---
BG_COLOR            = (0.58, 0.83, 0.99)    # light blue RGB values 0.0 to 1.0