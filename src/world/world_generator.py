# =============================================================================
# WORLD GENERATOR — Decides the terrain height at every (x, z) column using
# Perlin noise. Chunks call get_height() to know how tall to build each
# column of blocks. This is the "procedural" in Procedural World Generation.
# =============================================================================

import random
from noise import pnoise2, pnoise3
from core.settings import *


class WorldGenerator:
    def __init__(self, seed = WORLD_SEED):
        self.seed = seed

        # The noise library's own `base` parameter wraps around at 256 (seed
        # 0 and seed 256 give the IDENTICAL world), so using it alone would
        # allow only 256 different worlds. Instead, each noise layer gets its
        # own random coordinate OFFSET derived from the seed — shifting where
        # you "look" in an effectively endless noise space gives a huge number
        # of distinct worlds, and keeps the layers independent of each other
        # (before, biomes/caves used seed+2/seed+1, needlessly tying them to
        # the hills' seed).
        rng = random.Random(seed)
        self.height_offset           = (rng.uniform(-500, 500), rng.uniform(-500, 500))
        self.continent_offset        = (rng.uniform(-500, 500), rng.uniform(-500, 500))
        self.mountain_region_offset  = (rng.uniform(-500, 500), rng.uniform(-500, 500))
        self.mountain_ridge_offset   = (rng.uniform(-500, 500), rng.uniform(-500, 500))
        self.cave_offset   = (rng.uniform(-500, 500), rng.uniform(-500, 500),
                               rng.uniform(-500, 500))
        self.biome_offset  = (rng.uniform(-500, 500), rng.uniform(-500, 500))
        self.base          = rng.randrange(256)   # also reshuffles the noise's
                                                   # internal gradient table

    # -------------------------------------------------------------------------
    def get_height(self, world_x, world_z):
        """
        Returns the ground height (in blocks) at a given WORLD (not local
        chunk) x/z coordinate. Same input always gives the same output —
        that's what makes the world persistent without storing every block.

        Built from 3 stacked layers (see settings.py for the full picture):
        continent (where the land sits overall), mountain (dramatic peaks
        in some regions only), and fine detail (the original hill bumpiness).
        """
        continent_noise = pnoise2(
            world_x * CONTINENT_SCALE + self.continent_offset[0],
            world_z * CONTINENT_SCALE + self.continent_offset[1],
            octaves = 2,
            base    = self.base,
        )
        base_elevation = SEA_LEVEL + continent_noise * CONTINENT_AMPLITUDE

        # Mountain REGION: only POSITIVE values become mountainous at all —
        # negative regions contribute nothing, staying as gentle continent
        # terrain. This is what keeps most of the world as rolling plains
        # with mountains concentrated in specific large ranges, rather than
        # jagged peaks scattered evenly everywhere.
        region_noise = pnoise2(
            world_x * MOUNTAIN_REGION_SCALE + self.mountain_region_offset[0],
            world_z * MOUNTAIN_REGION_SCALE + self.mountain_region_offset[1],
            octaves = 2,
            base    = self.base,
        )
        # region_noise rarely reaches past roughly +-0.5 in practice (2-octave
        # Perlin doesn't actually span the full -1..1 range), so without
        # amplifying it here, "mountain_region" would almost never get
        # anywhere close to 1 and mountains would stay nearly flat everywhere
        # — measured and caught exactly this before tuning the x3 below.
        # Ramps 0->1 as region_noise goes 0->0.33, then clamps at 1 — so
        # there's real full-strength mountain territory, not just a sliver
        # that only ever approaches full height at one single noise value.
        mountain_region = min(1.0, max(0.0, region_noise) * 3.0)

        # Mountain RIDGE shape: 1-abs(noise) turns ordinary smooth Perlin
        # noise into sharp ridgelines (values peak near 1 right where the
        # underlying noise crosses zero, instead of smooth round hilltops).
        ridge_noise = pnoise2(
            world_x * MOUNTAIN_RIDGE_SCALE + self.mountain_ridge_offset[0],
            world_z * MOUNTAIN_RIDGE_SCALE + self.mountain_ridge_offset[1],
            octaves = 4,
            base    = self.base,
        )
        ridged = (1.0 - abs(ridge_noise)) ** 2   # squared sharpens peaks further

        mountain_contribution = mountain_region * ridged * MOUNTAIN_HEIGHT

        detail_noise = pnoise2(
            world_x * NOISE_SCALE + self.height_offset[0],
            world_z * NOISE_SCALE + self.height_offset[1],
            octaves = NOISE_OCTAVES,
            base    = self.base,
        )

        height = int(base_elevation + detail_noise * TERRAIN_AMPLITUDE + mountain_contribution)

        # keep it inside the world's vertical bounds (0 to WORLD_HEIGHT - 1)
        return max(0, min(WORLD_HEIGHT - 1, height))

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
            world_x * CAVE_NOISE_SCALE + self.cave_offset[0],
            world_y * CAVE_NOISE_SCALE + self.cave_offset[1],
            world_z * CAVE_NOISE_SCALE + self.cave_offset[2],
            octaves = 3,
            base    = self.base,
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
            world_x * BIOME_SCALE + self.biome_offset[0],
            world_z * BIOME_SCALE + self.biome_offset[1],
            octaves = 2,
            base    = self.base,
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
        biome border or in a desert/snow patch — and, now that sea-level
        water exists, also above SEA_LEVEL everywhere in that margin, so
        you don't spawn standing in (or right at the edge of) a lake.
        Falls back to the start point if nothing is found (only possible
        in a freak seed).
        """
        def is_safe(x, z):
            return all(
                self.get_biome(x + dx, z + dz) == 'plains'
                and self.get_height(x + dx, z + dz) > SEA_LEVEL
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

