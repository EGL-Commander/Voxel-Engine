# =============================================================================
# CHUNK MANAGER — Owns every chunk currently loaded, builds them all up front
# from the world generator, and draws each one at its correct world position.
# =============================================================================

import math
from collections import deque
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

        self.chunks = {}   # (chunk_x, chunk_z) -> Chunk, only EVER holds fully
                            # loaded chunks (voxels generated + mesh built)

        # Work queue for spreading chunk loading across frames (see update()).
        # Each entry is ((chunk_x, chunk_z), job) with job 'load' or 'remesh'.
        # The two sets mirror what's currently queued, purely so we can check
        # "is this coord already queued?" in O(1) instead of scanning the
        # deque — entries are left in the deque when they become stale (e.g.
        # the player wandered back away before a load even ran) and are just
        # skipped cheaply when their turn comes up, rather than being
        # actively removed from the middle of the queue.
        self.queue         = deque()
        self.queued_loads  = set()
        self.queued_remesh = set()

        center = (
            math.floor(center_world_x / CHUNK_SIZE),
            math.floor(center_world_z / CHUNK_SIZE),
        )
        self.loaded_center = center
        self._queue_region(center)

        # The very FIRST load is the one case where spreading the work out
        # would be worse, not better — the game would open on a mostly empty
        # void that slowly fills in, instead of the existing one-time
        # loading pause. So only crossings AFTER startup get spread across
        # frames; this first batch is drained synchronously right here.
        while self.queue:
            self._process_one()

    # -------------------------------------------------------------------------
    def _queue_region(self, center):
        """
        Unloads anything now outside RENDER_DISTANCE of `center` (immediate —
        releasing GPU buffers is cheap, there's no need to spread that out),
        and queues everything newly needed for loading (NOT processed here —
        see update()).
        """
        center_x, center_z = center
        r = RENDER_DISTANCE
        desired = {
            (cx, cz)
            for cx in range(center_x - r, center_x + r + 1)
            for cz in range(center_z - r, center_z + r + 1)
        }
        current = set(self.chunks.keys())

        for coord in current - desired:
            self.chunks.pop(coord).destroy()

        for coord in desired - current:
            if coord not in self.queued_loads:
                self.queue.append((coord, 'load'))
                self.queued_loads.add(coord)

    # -------------------------------------------------------------------------
    def _process_one(self):
        """Does ONE unit of queued work — either loading one new chunk or
        re-meshing one existing one. See update() for how many of these run
        per frame."""
        coord, job = self.queue.popleft()

        if job == 'load':
            self.queued_loads.discard(coord)
            if coord in self.chunks:
                return   # shouldn't normally happen, but cheap to guard

            cx, cz = coord
            center_x, center_z = self.loaded_center
            r = RENDER_DISTANCE
            if not (center_x - r <= cx <= center_x + r and
                    center_z - r <= cz <= center_z + r):
                return   # the player moved away before this one's turn came up

            chunk = Chunk(cx, cz, self.world_generator)
            self.chunks[coord] = chunk
            chunk.build_mesh(self.ctx, self.shader_program, self, self.texture_manager)

            # A chunk we already had that borders this new one was previously
            # culling its edge faces against "nothing" (treated as air, same
            # as the world's old fixed boundary) — it needs to be re-meshed
            # too now, or you'd see its old boundary wall still rendered as a
            # solid face sitting in what should now be open passage.
            for dx, dz in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
                neighbor = (cx + dx, cz + dz)
                if (neighbor in self.chunks and neighbor != coord
                        and neighbor not in self.queued_remesh):
                    self.queue.append((neighbor, 'remesh'))
                    self.queued_remesh.add(neighbor)

        elif job == 'remesh':
            self.queued_remesh.discard(coord)
            chunk = self.chunks.get(coord)
            if chunk is not None:   # might have been unloaded since queuing
                chunk.destroy()
                chunk.build_mesh(self.ctx, self.shader_program, self, self.texture_manager)

    # -------------------------------------------------------------------------
    def update(self, player_world_x, player_world_z):
        """
        Called once per frame. Cheap when the player hasn't left their
        current chunk (a couple of divisions and a tuple comparison) and
        there's nothing left in the work queue — the world re-centers the
        moment they cross a chunk boundary, but the actual loading/meshing
        work for that crossing is spread across several frames afterward
        (CHUNKS_PER_FRAME per frame) instead of all landing in one frame as
        a single stutter.
        """
        center = (
            math.floor(player_world_x / CHUNK_SIZE),
            math.floor(player_world_z / CHUNK_SIZE),
        )
        if center != self.loaded_center:
            self.loaded_center = center
            self._queue_region(center)

        for _ in range(CHUNKS_PER_FRAME):
            if not self.queue:
                break
            self._process_one()

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
        you'd see a hole (or a hidden extra face) appear at the seam. This
        stays synchronous (not queued) — editing one block only ever touches
        up to 5 chunks, which is cheap enough to just do immediately so the
        change is visible the instant you click.
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
