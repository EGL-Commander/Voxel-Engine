# =============================================================================
# CHUNK MANAGER — Owns every chunk currently loaded, builds them all up front
# from the world generator, and draws each one at its correct world position.
# =============================================================================

import math
import glm
from core.settings import *
from world.chunk import Chunk, AIR, STONE, CHUNK_SIZE
from world.world_generator import WorldGenerator


class ChunkManager:
    def __init__(self, ctx, shader_program, texture_manager, center_world_x = 0, center_world_z = 0,
                 world_generator = None):
        self.ctx             = ctx
        self.shader_program  = shader_program
        self.texture_manager = texture_manager
        # Accept a shared WorldGenerator if given (so spawn search and chunk
        # generation agree on the same seed), otherwise make our own — this
        # matters once the seed is random: two separately-created generators
        # would each roll their OWN random seed and disagree with each other.
        self.world_generator = world_generator or WorldGenerator()

        self.chunks = {}   # (chunk_x, chunk_z) -> Chunk

        center = (
            math.floor(center_world_x / CHUNK_SIZE),
            math.floor(center_world_z / CHUNK_SIZE),
        )
        self.build_chunks(center)
        self.loaded_center = center   # avoids redundant work if update() is
                                       # called before the player has actually
                                       # crossed into a new chunk

    # -------------------------------------------------------------------------
    def build_chunks(self, center):
        """
        Builds a square grid of chunks, RENDER_DISTANCE chunks out from
        `center` in every direction. Used both for the very first load and,
        by update(), every time that grid needs to shift.
        """
        center_x, center_z = center
        r = RENDER_DISTANCE

        # Pass 1: every chunk's VOXEL DATA, with no mesh yet. Meshing needs
        # to check neighboring chunks' blocks (to know whether a face at the
        # chunk's edge is actually hidden), so all of that data has to exist
        # before any chunk is allowed to start building its mesh.
        for cx in range(center_x - r, center_x + r + 1):
            for cz in range(center_z - r, center_z + r + 1):
                self.chunks[(cx, cz)] = Chunk(cx, cz, self.world_generator)

        # Pass 2: now build every chunk's mesh, with the full picture available.
        for chunk in self.chunks.values():
            chunk.build_mesh(self.ctx, self.shader_program, self, self.texture_manager)

    # -------------------------------------------------------------------------
    def update(self, player_world_x, player_world_z):
        """
        Called once per frame. Cheap when the player hasn't left their
        current chunk (a couple of divisions and a tuple comparison) — the
        actual load/unload work only runs the moment they cross a chunk
        boundary, keeping the world centered on wherever they are instead of
        the fixed grid we started with.
        """
        center = (
            math.floor(player_world_x / CHUNK_SIZE),
            math.floor(player_world_z / CHUNK_SIZE),
        )
        if center == self.loaded_center:
            return
        self.loaded_center = center

        center_x, center_z = center
        r = RENDER_DISTANCE
        desired = {
            (cx, cz)
            for cx in range(center_x - r, center_x + r + 1)
            for cz in range(center_z - r, center_z + r + 1)
        }
        current = set(self.chunks.keys())

        # Unload anything now outside the render-distance square.
        for coord in current - desired:
            self.chunks.pop(coord).destroy()

        # Pass 1: voxel data for every newly-needed chunk.
        new_chunks = {}
        for coord in desired - current:
            chunk = Chunk(coord[0], coord[1], self.world_generator)
            self.chunks[coord] = chunk
            new_chunks[coord] = chunk

        # Pass 2: mesh the new chunks now that all their neighbors' voxel
        # data exists (some of those neighbors are pre-existing chunks we
        # kept, some are other chunks from this same batch).
        for chunk in new_chunks.values():
            chunk.build_mesh(self.ctx, self.shader_program, self, self.texture_manager)

        # A chunk we KEPT that happens to border a newly-loaded chunk was
        # previously culling its edge faces against "nothing" (treated as
        # air, same as the world's old fixed boundary) — now that a real
        # neighbor exists there, it needs to be re-meshed too, or you'd see
        # its old boundary wall still rendered as a solid face sitting in
        # what should now be open passage into the new chunk.
        to_remesh = set()
        for (cx, cz) in new_chunks:
            for dx, dz in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
                neighbor = (cx + dx, cz + dz)
                if neighbor in self.chunks and neighbor not in new_chunks:
                    to_remesh.add(neighbor)

        for coord in to_remesh:
            chunk = self.chunks[coord]
            chunk.destroy()
            chunk.build_mesh(self.ctx, self.shader_program, self, self.texture_manager)

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
                chunk.build_mesh(self.ctx, self.shader_program, self, self.texture_manager)

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
