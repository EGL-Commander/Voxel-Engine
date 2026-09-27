# =============================================================================
# CHUNK MANAGER — Owns every chunk currently loaded, builds them all up front
# from the world generator, and draws each one at its correct world position.
# =============================================================================

import glm
from core.settings import *
from world.chunk import Chunk, AIR, STONE, CHUNK_SIZE
from world.world_generator import WorldGenerator


class ChunkManager:
    def __init__(self, ctx, shader_program):
        self.ctx             = ctx
        self.shader_program  = shader_program
        self.world_generator = WorldGenerator()

        self.chunks = {}   # (chunk_x, chunk_z) -> Chunk
        self.build_chunks()

    # -------------------------------------------------------------------------
    def build_chunks(self):
        """
        Builds a square grid of chunks, RENDER_DISTANCE chunks out from the
        origin in every direction. Static for now — this will later rebuild
        around the player as they move instead of generating everything once.
        """
        r = RENDER_DISTANCE

        # Pass 1: every chunk's VOXEL DATA, with no mesh yet. Meshing needs
        # to check neighboring chunks' blocks (to know whether a face at the
        # chunk's edge is actually hidden), so all of that data has to exist
        # before any chunk is allowed to start building its mesh.
        for cx in range(-r, r + 1):
            for cz in range(-r, r + 1):
                self.chunks[(cx, cz)] = Chunk(cx, cz, self.world_generator)

        # Pass 2: now build every chunk's mesh, with the full picture available.
        for chunk in self.chunks.values():
            chunk.build_mesh(self.ctx, self.shader_program, self)

    # -------------------------------------------------------------------------
    def get_block_world(self, world_x, world_y, world_z):
        """
        Block ID at WORLD coordinates (not local to any one chunk) — used by
        player physics for collision checks. Floor-divides down to which
        chunk owns that position, same vertical rules as Chunk.get_block:
        solid below the world, open air above it.
        """
        if world_y < 0:
            return STONE
        if world_y >= CHUNK_SIZE:
            return AIR

        chunk_x, local_x = divmod(world_x, CHUNK_SIZE)
        chunk_z, local_z = divmod(world_z, CHUNK_SIZE)

        chunk = self.chunks.get((chunk_x, chunk_z))
        if chunk is None:
            return AIR   # outside the currently loaded world

        return chunk.voxels[local_x, world_y, local_z]

    # -------------------------------------------------------------------------
    def set_block(self, world_x, world_y, world_z, block_id):
        """
        Changes one block at WORLD coordinates (breaking = AIR, placing =
        whatever block type) and rebuilds every mesh that could have been
        affected. That's not just this chunk — if the edited block sits right
        on a chunk's edge, the NEIGHBORING chunk's mesh was culling a face
        against it too, so that neighbor needs to be re-meshed as well or
        you'd see a hole (or a hidden extra face) appear at the seam.
        Returns True if the edit happened, False if it was out of bounds.
        """
        if world_y < 0 or world_y >= CHUNK_SIZE:
            return False   # can't edit the "floor" or above the build limit

        chunk_x, local_x = divmod(world_x, CHUNK_SIZE)
        chunk_z, local_z = divmod(world_z, CHUNK_SIZE)

        chunk = self.chunks.get((chunk_x, chunk_z))
        if chunk is None:
            return False   # outside the currently loaded world

        chunk.voxels[local_x, world_y, local_z] = block_id
        self._remesh_around(chunk_x, chunk_z)
        return True

    # -------------------------------------------------------------------------
    def _remesh_around(self, chunk_x, chunk_z):
        for dx, dz in [(0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)]:
            chunk = self.chunks.get((chunk_x + dx, chunk_z + dz))
            if chunk is not None:
                chunk.destroy()   # release the old VAO/VBO before rebuilding
                chunk.build_mesh(self.ctx, self.shader_program, self)

    # -------------------------------------------------------------------------
    def render(self, m_model_uniform):
        """
        Each chunk's mesh is built in LOCAL coordinates (0-16), so we position
        it in the world by writing a fresh translation into m_model right
        before drawing it.
        """
        for (chunk_x, chunk_z), chunk in self.chunks.items():
            world_offset = glm.vec3(chunk_x * CHUNK_SIZE, 0, chunk_z * CHUNK_SIZE)
            m_model_uniform.write(glm.translate(glm.mat4(), world_offset))
            chunk.render()

    # -------------------------------------------------------------------------
    def destroy(self):
        for chunk in self.chunks.values():
            chunk.destroy()
