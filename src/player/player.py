# =============================================================================
# PLAYER — Wraps a Camera with actual physics: gravity, jumping, and
# collision against the voxel world. Before this, the "camera" WAS the
# player and could fly through solid ground; now the player has real feet.
# =============================================================================

import glm
from core.settings import *
from player.camera import Camera
from player.physics import move_and_collide


class Player:
    def __init__(self, chunk_manager, spawn_position):
        self.chunk_manager = chunk_manager

        # position is the player's FEET, at world coordinates. The camera
        # (the eyes) always sits EYE_HEIGHT above this.
        self.position   = glm.vec3(spawn_position)
        self.velocity_y = 0.0
        self.on_ground  = False

        # Starts "ready" (>= cooldown) so the very first jump isn't delayed.
        self.time_since_jump = JUMP_COOLDOWN_MS

        # Set by App when creative mode is toggled. While flying, gravity is
        # off and space/shift move straight up/down instead of jump/sprint —
        # everything else (horizontal movement, collision) stays the same.
        self.flying = False

        self.camera = Camera(position = self._eye_position(), yaw = -90, pitch = -10)

    # -------------------------------------------------------------------------
    def _eye_position(self):
        return glm.vec3(self.position.x, self.position.y + EYE_HEIGHT, self.position.z)

    # -------------------------------------------------------------------------
    def update(self, keys, mouse_dx, mouse_dy, dt):
        self.camera.rotate(mouse_dx, mouse_dy)

        # Horizontal movement uses the camera's forward/right FLATTENED onto
        # the ground plane — otherwise looking up at the sky while holding W
        # would make you fly upward, which isn't how walking works.
        forward = glm.vec3(self.camera.forward.x, 0, self.camera.forward.z)
        right   = glm.vec3(self.camera.right.x,   0, self.camera.right.z)
        if glm.length(forward) > 0: forward = glm.normalize(forward)
        if glm.length(right)   > 0: right   = glm.normalize(right)

        speed = FLY_SPEED * dt if self.flying else PLAYER_SPEED * dt
        if keys['shift'] and not self.flying:
            speed *= SPRINT_MULTIPLIER   # while flying, shift means "descend" instead

        move = glm.vec3(0)
        if keys['w']: move += forward
        if keys['s']: move -= forward
        if keys['a']: move -= right
        if keys['d']: move += right
        if glm.length(move) > 0:
            move = glm.normalize(move) * speed

        if self.flying:
            # No gravity, no jump cooldown — space/shift move straight up
            # and down at the same speed as horizontal flight.
            self.velocity_y = 0.0
            vertical = (1 if keys['space'] else 0) - (1 if keys['shift'] else 0)
            move.y = vertical * speed
        else:
            # Gravity always pulls down; jumping only works while on the
            # ground AND the cooldown has elapsed — without the cooldown,
            # on_ground flips back to True a frame or two after leaving the
            # ground (while you're still holding space), so it'd refire
            # instantly instead of feeling like one real jump.
            self.velocity_y -= GRAVITY * dt
            self.time_since_jump += dt
            if keys['space'] and self.on_ground and self.time_since_jump >= JUMP_COOLDOWN_MS:
                self.velocity_y = JUMP_SPEED
                self.time_since_jump = 0
            move.y = self.velocity_y * dt

        self.on_ground = move_and_collide(
            self.chunk_manager, self.position, move, PLAYER_HALF_WIDTH, PLAYER_HEIGHT
        )
        if self.on_ground:
            self.velocity_y = 0.0

        # Sync the camera to the new feet position and refresh its view matrix.
        self.camera.position = self._eye_position()
        self.camera.m_view   = self.camera.get_view_matrix()
