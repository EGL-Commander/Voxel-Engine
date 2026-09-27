# =============================================================================
# RAYCASTER — Walks forward from the camera a small step at a time to find
# the first solid block in front of you. This is what lets you aim at a
# block to break it, or aim at its face to place a new one next to it.
#
# This is a simple "march forward and sample" raycast, not a proper voxel
# traversal algorithm (like Amanatides & Woo's DDA) — it's less efficient
# and can very rarely skip a corner at a bad angle, but it's a lot easier to
# follow, and at RAYCAST_STEP = 0.05 over a 6-block reach it's plenty
# accurate for gameplay. Worth revisiting only if aiming ever feels off.
# =============================================================================

import math
import glm
from core.settings import REACH_DISTANCE, RAYCAST_STEP
from world.chunk import AIR


def raycast(chunk_manager, origin, direction):
    """
    Returns (hit_block, place_block):
      hit_block   — (x, y, z) of the first solid block along the ray, the
                    one that left-click would break. None if nothing in reach.
      place_block — (x, y, z) of the empty space just before it — where a
                    new block would go if you right-clicked. None if hit_block
                    is None.
    """
    direction = glm.normalize(direction)
    previous_block = None

    distance = 0.0
    while distance <= REACH_DISTANCE:
        point = origin + direction * distance
        block_pos = (math.floor(point.x), math.floor(point.y), math.floor(point.z))

        if chunk_manager.get_block_world(*block_pos) != AIR:
            return block_pos, previous_block

        previous_block = block_pos
        distance += RAYCAST_STEP

    return None, None
