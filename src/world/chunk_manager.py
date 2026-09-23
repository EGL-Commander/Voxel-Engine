# =============================================================================
# CHUNK MANAGER — Owns every chunk currently loaded, builds them all up front
# from the world generator, and draws each one at its correct world position.
# =============================================================================

import glm
from core.settings import *
from world.chunk import Chunk
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
        for cx in range(-r, r + 1):
            for cz in range(-r, r + 1):
                self.chunks[(cx, cz)] = Chunk(
                    self.ctx, self.shader_program, cx, cz, self.world_generator
                )

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
