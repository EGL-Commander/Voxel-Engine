# =============================================================================
# PHYSICS — Simple axis-aligned collision between the player's bounding box
# and the voxel world. Not a full physics engine: just enough to walk on
# terrain, fall under gravity, and jump without clipping through blocks.
# =============================================================================

import math
from world.chunk import AIR


def _block_at(chunk_manager, x, y, z):
    """World-space (x, y, z) -> the block ID occupying that point."""
    return chunk_manager.get_block_world(
        math.floor(x), math.floor(y), math.floor(z)
    )


def _box_collides(chunk_manager, position, half_width, height):
    """
    True if the player's box — centered on (x, z), feet at position.y, top at
    position.y + height — overlaps any solid block. We only need to test the
    8 corners of the box: since blocks are axis-aligned unit cubes, if none
    of the box's corners are inside a solid block, nothing else is either.
    """
    for x in (position.x - half_width, position.x + half_width):
        for z in (position.z - half_width, position.z + half_width):
            for y in (position.y + 0.01, position.y + height - 0.01):
                if _block_at(chunk_manager, x, y, z) != AIR:
                    return True
    return False


def move_and_collide(chunk_manager, position, delta, half_width, height):
    """
    Moves `position` (the player's FEET, mutated in place) by `delta`, one
    axis at a time, cancelling whichever axes would land inside a solid
    block. Resolving X, Z, and Y separately (instead of all at once) is what
    lets you slide along a wall instead of just stopping dead when you walk
    into it at an angle.

    Returns True if the player is resting on solid ground (i.e. downward
    movement this frame was blocked) — used to decide whether a jump is
    allowed and whether gravity should keep accumulating.
    """
    position.x += delta.x
    if _box_collides(chunk_manager, position, half_width, height):
        position.x -= delta.x

    position.z += delta.z
    if _box_collides(chunk_manager, position, half_width, height):
        position.z -= delta.z

    on_ground = False
    position.y += delta.y
    if _box_collides(chunk_manager, position, half_width, height):
        # Just reverting to the pre-move position isn't good enough here:
        # at high fall speed a single frame's drop can be much bigger than
        # this collision check's precision, so "undo the move" would leave
        # you hovering visibly above the ground and then creeping down a
        # tiny bit more each frame until it finally settles. Instead, snap
        # straight to resting exactly on the surface (or exactly under a
        # ceiling, if we were moving up) so landing is a single clean stop.
        if delta.y < 0:
            position.y = math.floor(position.y) + 1.0
            on_ground = True
        else:
            position.y = math.floor(position.y + height) - height

    return on_ground
