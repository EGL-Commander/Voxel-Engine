# =============================================================================
# WORLD GENERATOR — Decides the terrain height at every (x, z) column using
# Perlin noise. Chunks call get_height() to know how tall to build each
# column of blocks. This is the "procedural" in Procedural World Generation.
# =============================================================================

from noise import pnoise2, pnoise3
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

    # -------------------------------------------------------------------------
    def is_cave(self, world_x, world_y, world_z):
        """
        True if this position should be hollowed out into a cave. 3D noise
        (unlike get_height's 2D noise) gives a value for every point in
        space, not just per-column — sampling it at a block's exact (x,y,z)
        and carving out anywhere it crosses a threshold is what produces
        actual 3D cavities instead of just a height per column. Perlin
        noise is spatially smooth (nearby points give similar values), so
        thresholding it naturally forms connected blobby caverns rather
        than scattered single-block holes.
        """
        noise_value = pnoise3(
            world_x * CAVE_NOISE_SCALE,
            world_y * CAVE_NOISE_SCALE,
            world_z * CAVE_NOISE_SCALE,
            octaves = 3,
            base    = self.seed + 1,   # offset from the height noise's seed
                                        # so caves aren't correlated with hills
        )
        return noise_value > CAVE_THRESHOLD

    # -------------------------------------------------------------------------
    def get_biome(self, world_x, world_z):
        """
        Returns 'plains', 'desert' or 'snow' for this column. Uses 2D noise at
        a much LOWER frequency than the terrain hills (BIOME_SCALE is small),
        so the value changes slowly and biomes come out as big contiguous
        regions rather than a per-block scatter. The noise is thresholded at
        two cutoffs: low values are desert, high values are snow, and the
        middle band (the widest) is plains — which also means plains always
        sit between the other two, so you never hit a hard desert-to-snow edge.
        """
        value = pnoise2(
            world_x * BIOME_SCALE,
            world_z * BIOME_SCALE,
            octaves = 2,
            base    = self.seed + 2,   # own offset, independent of hills/caves
        )
        if value < BIOME_DESERT_MAX:
            return 'desert'
        if value > BIOME_SNOW_MIN:
            return 'snow'
        return 'plains'

    # -------------------------------------------------------------------------
    def find_spawn_column(self, start_x = 8, start_z = 8, margin = 8, max_radius = 400):
        """
        Searches outward (in growing square rings) from a starting point for
        a column that is plains AND has plains on all sides out to `margin`
        blocks, so you spawn on grass with room to walk instead of on a
        biome border or in a desert/snow patch. Falls back to the start
        point if nothing is found (only possible in a freak seed).
        """
        def is_safe(x, z):
            return all(
                self.get_biome(x + dx, z + dz) == 'plains'
                for dx in (-margin, 0, margin)
                for dz in (-margin, 0, margin)
            )

        for radius in range(0, max_radius, 2):
            for dx in range(-radius, radius + 1, 2):
                for dz in range(-radius, radius + 1, 2):
                    if max(abs(dx), abs(dz)) != radius:
                        continue   # only the ring's outline, inner area already checked
                    if is_safe(start_x + dx, start_z + dz):
                        return start_x + dx, start_z + dz
        return start_x, start_z

    # -------------------------------------------------------------------------
    def find_cave_spot(self, start_x, start_z, max_radius = 250):
        """
        Finds the nearest place you could STAND inside a natural cave: two
        stacked air cells (room for the 1.8-block-tall player) sitting on
        solid ground. Searches in growing square rings around (start_x,
        start_z), so the first hit is (approximately) the closest one.
        Returns the (x, y, z) of the lower air cell, or None if nothing is
        found within max_radius.

        This mirrors exactly how Chunk.generate_voxels carves caves — stone
        region only (y from CAVE_MIN_Y up to height-3, since the top three
        layers are surface + filler), so what this reports is what really
        exists once the chunk is generated. It's a debug/exploration helper
        (F4 in-game), which is why it can afford to scan in plain Python.
        """
        for radius in range(0, max_radius, 2):
            for dx in range(-radius, radius + 1, 2):
                for dz in range(-radius, radius + 1, 2):
                    if max(abs(dx), abs(dz)) != radius:
                        continue   # ring outline only; inner area already done
                    x, z = start_x + dx, start_z + dz
                    top = self.get_height(x, z) - 3    # highest carvable y
                    for y in range(CAVE_MIN_Y, top):   # y+1 must stay <= top
                        if not (self.is_cave(x, y, z) and self.is_cave(x, y + 1, z)):
                            continue
                        floor_is_solid = (y - 1 < CAVE_MIN_Y) or not self.is_cave(x, y - 1, z)
                        if floor_is_solid:
                            return x, y, z
        return None

