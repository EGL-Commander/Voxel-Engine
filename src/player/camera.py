# =============================================================================
# CAMERA — FPS-style camera. Owns the view matrix (where we're looking from)
# and the projection matrix (how 3D turns into what's on screen).
# =============================================================================

import glm
from core.settings import *


class Camera:
    def __init__(self, position = (0, 0, 3), yaw = -90, pitch = 0):
        self.position = glm.vec3(position)
        self.yaw      = yaw      # rotation around the Y axis (left/right look)
        self.pitch    = pitch    # rotation around the X axis (up/down look)

        # Direction vectors, recalculated every time yaw/pitch change
        self.forward  = glm.vec3(0, 0, -1)
        self.right    = glm.vec3(1, 0, 0)
        self.up       = glm.vec3(0, 1, 0)

        self.m_proj = self.get_projection_matrix()   # doesn't change at runtime
        self.update_vectors()
        self.m_view = self.get_view_matrix()

    # -------------------------------------------------------------------------
    def update_vectors(self):
        """
        Recompute forward/right/up from the current yaw and pitch.
        This is standard spherical-to-cartesian conversion.
        """
        yaw   = glm.radians(self.yaw)
        pitch = glm.radians(self.pitch)

        forward = glm.vec3()
        forward.x = glm.cos(yaw) * glm.cos(pitch)
        forward.y = glm.sin(pitch)
        forward.z = glm.sin(yaw) * glm.cos(pitch)

        self.forward = glm.normalize(forward)
        self.right   = glm.normalize(glm.cross(self.forward, glm.vec3(0, 1, 0)))
        self.up      = glm.normalize(glm.cross(self.right, self.forward))

    # -------------------------------------------------------------------------
    def rotate(self, dx, dy):
        """dx/dy are raw mouse pixel deltas for this frame."""
        self.yaw   += dx * MOUSE_SENSITIVITY
        self.pitch -= dy * MOUSE_SENSITIVITY   # inverted: mouse up = look up

        # stop the camera from flipping upside down
        self.pitch = max(-89.0, min(89.0, self.pitch))

        self.update_vectors()

    # -------------------------------------------------------------------------
    def move(self, keys, dt):
        velocity = PLAYER_SPEED * dt   # dt is milliseconds since last frame

        if keys['w']:     self.position += self.forward * velocity
        if keys['s']:     self.position -= self.forward * velocity
        if keys['a']:     self.position -= self.right   * velocity
        if keys['d']:     self.position += self.right   * velocity
        if keys['space']: self.position += glm.vec3(0, 1, 0) * velocity
        if keys['shift']: self.position -= glm.vec3(0, 1, 0) * velocity

    # -------------------------------------------------------------------------
    def update(self, keys, mouse_dx, mouse_dy, dt):
        """Called once per frame from App.update()."""
        self.rotate(mouse_dx, mouse_dy)
        self.move(keys, dt)
        self.m_view = self.get_view_matrix()

    # -------------------------------------------------------------------------
    def get_view_matrix(self):
        return glm.lookAt(self.position, self.position + self.forward, self.up)

    # -------------------------------------------------------------------------
    def get_projection_matrix(self):
        return glm.perspective(
            glm.radians(FOV), WINDOW_ASPECT_RATIO, NEAR_PLANE, FAR_PLANE
        )
