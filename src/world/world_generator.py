# =============================================================================
# WORLD GENERATOR — Decides the terrain height at every (x, z) column using
# Perlin noise. Chunks call get_height() to know how tall to build each
# column of blocks. This is the "procedural" in Procedural World Generation.
# =============================================================================

from noise import pnoise2
from core.settings import *


class WorldGenerator:
    def __init__(self, seed = WORLD_SEED):
        self.seed = seed

    # -------------------------------------------------------------------------
    def get_height(self, world_x, world_z):
        """
        Returns the ground height (in blocks) at a given WORLD (not local
        chunk) x/z coordinate. Same input always gives the same output —
        that's what makes the world persistent without storing every block.
        """
        noise_value = pnoise2(
            world_x * NOISE_SCALE,
            world_z * NOISE_SCALE,
            octaves = NOISE_OCTAVES,
            base    = self.seed,
        )
        # pnoise2 returns roughly -1.0 to 1.0 — scale that into a block height
        height = int(TERRAIN_BASE_HEIGHT + noise_value * TERRAIN_AMPLITUDE)

        # keep it inside the chunk's vertical bounds (0 to CHUNK_SIZE - 1)
        return max(0, min(CHUNK_SIZE - 1, height))
