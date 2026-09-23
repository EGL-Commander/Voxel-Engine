# =============================================================================
# CHUNK — A 16x16x16 grid of blocks. Builds its own mesh, but only from the
# faces that are actually visible (a face touching another solid block is
# skipped entirely). This one change is what makes rendering a whole world
# of cubes possible — without it we'd be drawing millions of hidden faces.
# =============================================================================

import numpy as np
from core.settings import *

# --- Block IDs --------------------------------------------------------------
AIR   = 0
GRASS = 1
DIRT  = 2
STONE = 3

# Flat color per block type. Good enough until texture_manager.py is wired up.
BLOCK_COLORS = {
    GRASS: (0.40, 0.75, 0.30),
    DIRT:  (0.50, 0.36, 0.20),
    STONE: (0.55, 0.55, 0.58),
}

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

# Fake directional lighting: with no texture atlas yet, every top face of
# every grass block is the exact same flat green, so two grass blocks that
# happen to be at the same height are visually indistinguishable from one
# another — there's nothing to tell you where one cube ends and the next
# begins. Multiplying each face by a fixed brightness per direction (top
# brightest, like sunlight from directly above, sides dimmer, bottom
# darkest) is the classic cheap trick voxel engines use to make individual
# blocks and height changes readable without any lighting engine at all.
FACE_SHADE = {
    'top':    1.00,
    'front':  0.85,
    'right':  0.80,
    'left':   0.75,
    'back':   0.70,
    'bottom': 0.55,
}


class Chunk:
    def __init__(self, ctx, shader_program, chunk_x, chunk_z, world_generator):
        self.ctx             = ctx
        self.shader_program  = shader_program
        self.chunk_x         = chunk_x     # chunk grid coordinates, NOT world coords
        self.chunk_z         = chunk_z

        self.voxels = self.generate_voxels(world_generator)
        self.vao    = self.build_mesh()

    # -------------------------------------------------------------------------
    def generate_voxels(self, world_generator):
        """
        Fills a CHUNK_SIZE^3 array with block IDs based on the world
        generator's height for each (x, z) column: grass on top, a few
        layers of dirt, stone for everything below that, air above ground.
        """
        voxels = np.zeros((CHUNK_SIZE, CHUNK_SIZE, CHUNK_SIZE), dtype = np.uint8)

        for lx in range(CHUNK_SIZE):
            for lz in range(CHUNK_SIZE):
                # local chunk coords -> world coords, so terrain lines up
                # seamlessly between neighboring chunks
                world_x = self.chunk_x * CHUNK_SIZE + lx
                world_z = self.chunk_z * CHUNK_SIZE + lz
                height  = world_generator.get_height(world_x, world_z)

                for ly in range(CHUNK_SIZE):
                    if ly > height:
                        voxels[lx, ly, lz] = AIR
                    elif ly == height:
                        voxels[lx, ly, lz] = GRASS
                    elif ly >= height - 2:
                        voxels[lx, ly, lz] = DIRT
                    else:
                        voxels[lx, ly, lz] = STONE

        return voxels

    # -------------------------------------------------------------------------
    def is_solid(self, lx, ly, lz):
        """
        True if the given LOCAL position holds a non-air block.
        Anything outside this chunk's own bounds is treated as air for now —
        meaning faces right at a chunk's edge get drawn even when the
        neighboring chunk is solid there. Wastes a few triangles at chunk
        borders but keeps this milestone simple; fixable later by looking
        up the neighboring chunk instead of assuming air.
        """
        if 0 <= lx < CHUNK_SIZE and 0 <= ly < CHUNK_SIZE and 0 <= lz < CHUNK_SIZE:
            return self.voxels[lx, ly, lz] != AIR
        return False

    # -------------------------------------------------------------------------
    def build_mesh(self):
        vertices = []
        indices  = []
        next_index = 0

        for lx in range(CHUNK_SIZE):
            for ly in range(CHUNK_SIZE):
                for lz in range(CHUNK_SIZE):
                    block = self.voxels[lx, ly, lz]
                    if block == AIR:
                        continue

                    base_color = BLOCK_COLORS[block]

                    # A tiny alternating tint per block column (like a
                    # checkerboard) — on top of the directional shading
                    # below, this is what makes a flat field of same-height,
                    # same-type blocks still read as individual cubes instead
                    # of one solid painted surface.
                    world_x = self.chunk_x * CHUNK_SIZE + lx
                    world_z = self.chunk_z * CHUNK_SIZE + lz
                    tint = 1.06 if (world_x + world_z) % 2 == 0 else 0.94

                    for face_name, (offset, corners) in FACES.items():
                        nx, ny, nz = lx + offset[0], ly + offset[1], lz + offset[2]
                        if self.is_solid(nx, ny, nz):
                            continue   # hidden face — a neighbor block covers it

                        shade = FACE_SHADE[face_name] * tint
                        color = tuple(min(1.0, c * shade) for c in base_color)

                        for cx, cy, cz in corners:
                            vertices.extend([lx + cx, ly + cy, lz + cz, *color])

                        # two triangles per face, using this face's 4 verts
                        indices.extend([
                            next_index,     next_index + 1, next_index + 2,
                            next_index,     next_index + 2, next_index + 3,
                        ])
                        next_index += 4

        if not vertices:
            return None   # an all-air chunk has nothing to draw

        vertices = np.array(vertices, dtype = 'f4')
        indices  = np.array(indices,  dtype = 'i4')

        vbo = self.ctx.buffer(vertices)
        ebo = self.ctx.buffer(indices)

        return self.ctx.vertex_array(
            self.shader_program,
            [(vbo, '3f 3f', 'in_position', 'in_color')],
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
