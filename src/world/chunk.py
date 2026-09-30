# =============================================================================
# CHUNK — A 16x16x16 grid of blocks. Builds its own mesh, but only from the
# faces that are actually visible (a face touching another solid block is
# skipped entirely) — including faces that touch a NEIGHBORING chunk, which
# is why chunk generation now happens in two passes (see ChunkManager).
# =============================================================================

import numpy as np
from core.settings import *

# --- Block IDs --------------------------------------------------------------
AIR   = 0
GRASS = 1
DIRT  = 2
STONE = 3
SAND  = 4
SNOW  = 5

# Human-readable names, for the debug HUD and anywhere else text is shown.
BLOCK_NAMES = {
    AIR: 'air', GRASS: 'grass', DIRT: 'dirt', STONE: 'stone',
    SAND: 'sand', SNOW: 'snow',
}

# Per biome: (surface block, filler block used for the 2 layers under it).
# The generator only reports a biome NAME — mapping that to actual block IDs
# lives here, since this file owns the block IDs.
BIOME_BLOCKS = {
    'plains': (GRASS, DIRT),
    'desert': (SAND,  SAND),
    'snow':   (SNOW,  DIRT),
}

# Which texture atlas tile each block uses, per face group. 'sides' covers
# front/back/left/right — only grass currently needs different textures per
# face (green top, dirt-with-overhang sides, plain dirt underneath); dirt
# and stone just use the same tile everywhere.
BLOCK_FACE_TEXTURES = {
    GRASS: {'top': 'grass_top', 'bottom': 'dirt',  'sides': 'grass_side'},
    DIRT:  {'top': 'dirt',      'bottom': 'dirt',  'sides': 'dirt'},
    STONE: {'top': 'stone',     'bottom': 'stone', 'sides': 'stone'},
    SAND:  {'top': 'sand',      'bottom': 'sand',  'sides': 'sand'},
    SNOW:  {'top': 'snow_top',  'bottom': 'dirt',  'sides': 'snow_side'},
}

# UV coordinates for each face's 4 corners, in the SAME order as that face's
# position corners above — (0,0) bottom-left, (1,0) bottom-right, (1,1)
# top-right, (0,1) top-left. This alignment matters: get it wrong and a
# directional texture (like grass_side's overhang) would render sideways or
# upside down on some faces even though a plain noisy texture would still
# look fine by coincidence.
FACE_UV = [(0, 0), (1, 0), (1, 1), (0, 1)]

# For each of the 6 directions a face can point: (offset to the neighbor
# block, and the 4 corner points of that face in counter-clockwise order as
# seen from outside the cube — required for backface culling to work).
# Corner offsets are relative to the block's own (0,0,0) corner, going 0-1.
FACES = {
    'right':  ((1, 0, 0),  [(1, 0, 1), (1, 0, 0), (1, 1, 0), (1, 1, 1)]),
    'left':   ((-1, 0, 0), [(0, 0, 0), (0, 0, 1), (0, 1, 1), (0, 1, 0)]),
    'top':    ((0, 1, 0),  [(0, 1, 1), (1, 1, 1), (1, 1, 0), (0, 1, 0)]),
    'bottom': ((0, -1, 0), [(0, 0, 0), (1, 0, 0), (1, 0, 1), (0, 0, 1)]),
    'front':  ((0, 0, 1),  [(0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1)]),
    'back':   ((0, 0, -1), [(1, 0, 0), (0, 0, 0), (0, 1, 0), (1, 1, 0)]),
}

# Which face group ('top' / 'bottom' / 'sides') each named face belongs to.
FACE_GROUP = {
    'top': 'top', 'bottom': 'bottom',
    'front': 'sides', 'back': 'sides', 'left': 'sides', 'right': 'sides',
}

# Fake directional lighting: real textures now do most of the work
# distinguishing blocks, but height changes (a step up or down between two
# same-type blocks) can still disappear without SOME per-face brightness
# difference, since a flat top-down light gives every top face identical
# lighting regardless of height. Multiplying each face by a fixed brightness
# per direction (top brightest, sides dimmer, bottom darkest) is the classic
# cheap trick voxel engines use for this without an actual lighting engine.
FACE_SHADE = {
    'top':    1.00,
    'front':  0.85,
    'right':  0.80,
    'left':   0.75,
    'back':   0.70,
    'bottom': 0.55,
}


class Chunk:
    def __init__(self, chunk_x, chunk_z, world_generator):
        self.chunk_x = chunk_x     # chunk grid coordinates, NOT world coords
        self.chunk_z = chunk_z

        self.voxels = self.generate_voxels(world_generator)

        # Mesh isn't built yet — see build_mesh(). Meshing needs to look at
        # neighboring chunks' voxel data, so every chunk's voxels must exist
        # first (that's why ChunkManager builds ALL chunks' voxels, THEN
        # calls build_mesh() on each one, instead of doing both in one pass).
        self.ctx            = None
        self.shader_program = None
        self.vao             = None

    # -------------------------------------------------------------------------
    def generate_voxels(self, world_generator):
        """
        Fills a CHUNK_SIZE^3 array with block IDs based on the world
        generator's height for each (x, z) column: the biome's surface block
        on top (grass / sand / snow), 2 filler layers under it, stone for
        everything below that, air above ground.
        """
        voxels = np.zeros((CHUNK_SIZE, CHUNK_SIZE, CHUNK_SIZE), dtype = np.uint8)

        for lx in range(CHUNK_SIZE):
            for lz in range(CHUNK_SIZE):
                # local chunk coords -> world coords, so terrain lines up
                # seamlessly between neighboring chunks
                world_x = self.chunk_x * CHUNK_SIZE + lx
                world_z = self.chunk_z * CHUNK_SIZE + lz
                height  = world_generator.get_height(world_x, world_z)
                surface_block, filler_block = BIOME_BLOCKS[
                    world_generator.get_biome(world_x, world_z)
                ]

                for ly in range(CHUNK_SIZE):
                    if ly > height:
                        voxels[lx, ly, lz] = AIR
                    elif ly == height:
                        voxels[lx, ly, lz] = surface_block
                    elif ly >= height - 2:
                        voxels[lx, ly, lz] = filler_block
                    elif ly >= CAVE_MIN_Y and world_generator.is_cave(world_x, ly, world_z):
                        # Only stone gets hollowed out — never the surface
                        # and filler layers — so the walkable ground and
                        # spawn point are never at risk of caving in under
                        # the player; caves stay strictly an underground
                        # feature you have to dig down or find an exposed
                        # cliff face to discover.
                        voxels[lx, ly, lz] = AIR
                    else:
                        voxels[lx, ly, lz] = STONE

        return voxels

    # -------------------------------------------------------------------------
    @staticmethod
    def _wrap(chunk_coord, local_coord):
        """
        A local coordinate that steps outside 0..CHUNK_SIZE-1 has crossed
        into a neighboring chunk. Returns (that neighbor's chunk coord, the
        equivalent local coord inside IT). Only ever off by one in either
        direction, since callers only step ±1 block at a time.
        """
        if local_coord < 0:
            return chunk_coord - 1, local_coord + CHUNK_SIZE
        if local_coord >= CHUNK_SIZE:
            return chunk_coord + 1, local_coord - CHUNK_SIZE
        return chunk_coord, local_coord

    # -------------------------------------------------------------------------
    def get_block(self, lx, ly, lz, chunk_manager):
        """
        Block ID at a LOCAL position, reaching into a neighboring chunk when
        that position falls outside this chunk's own 0..15 bounds.
        """
        # Vertical bounds aren't chunk-to-chunk — there's only one chunk of
        # height right now. Treat "below the world" as solid stone (so we
        # never bother drawing the floor's underside) and "above the world"
        # as open air (so the top of the tallest hill is never sealed shut).
        if ly < 0:
            return STONE
        if ly >= CHUNK_SIZE:
            return AIR

        if 0 <= lx < CHUNK_SIZE and 0 <= lz < CHUNK_SIZE:
            return self.voxels[lx, ly, lz]

        neighbor_cx, nlx = self._wrap(self.chunk_x, lx)
        neighbor_cz, nlz = self._wrap(self.chunk_z, lz)
        neighbor = chunk_manager.chunks.get((neighbor_cx, neighbor_cz))

        if neighbor is None:
            return AIR   # past the edge of the currently loaded world

        return neighbor.voxels[nlx, ly, nlz]

    # -------------------------------------------------------------------------
    def is_solid(self, lx, ly, lz, chunk_manager):
        return self.get_block(lx, ly, lz, chunk_manager) != AIR

    # -------------------------------------------------------------------------
    def build_mesh(self, ctx, shader_program, chunk_manager, texture_manager):
        self.ctx            = ctx
        self.shader_program = shader_program

        vertices = []
        indices  = []
        next_index = 0

        for lx in range(CHUNK_SIZE):
            for ly in range(CHUNK_SIZE):
                for lz in range(CHUNK_SIZE):
                    block = self.voxels[lx, ly, lz]
                    if block == AIR:
                        continue

                    face_textures = BLOCK_FACE_TEXTURES[block]

                    for face_name, (offset, corners) in FACES.items():
                        nx, ny, nz = lx + offset[0], ly + offset[1], lz + offset[2]
                        if self.is_solid(nx, ny, nz, chunk_manager):
                            continue   # hidden face — a neighbor block covers it

                        tile_name    = face_textures[FACE_GROUP[face_name]]
                        u_min, u_max = texture_manager.get_uv_rect(tile_name)
                        shade        = FACE_SHADE[face_name]

                        for (cx, cy, cz), (u, v) in zip(corners, FACE_UV):
                            # u is 0..1 within just this ONE tile — remap it
                            # into that tile's slice of the shared atlas.
                            atlas_u = u_min + u * (u_max - u_min)
                            vertices.extend([
                                lx + cx, ly + cy, lz + cz, atlas_u, v, shade
                            ])

                        # two triangles per face, using this face's 4 verts
                        indices.extend([
                            next_index,     next_index + 1, next_index + 2,
                            next_index,     next_index + 2, next_index + 3,
                        ])
                        next_index += 4

        if not vertices:
            return   # an all-air chunk has nothing to draw — self.vao stays None

        vertices = np.array(vertices, dtype = 'f4')
        indices  = np.array(indices,  dtype = 'i4')

        vbo = self.ctx.buffer(vertices)
        ebo = self.ctx.buffer(indices)

        self.vao = self.ctx.vertex_array(
            self.shader_program,
            [(vbo, '3f 2f 1f', 'in_position', 'in_uv', 'in_shade')],
            ebo
        )

    # -------------------------------------------------------------------------
    def render(self):
        if self.vao is not None:
            self.vao.render()

    # -------------------------------------------------------------------------
    def destroy(self):
        if self.vao is not None:
            self.vao.release()
