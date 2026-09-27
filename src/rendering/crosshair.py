# =============================================================================
# CROSSHAIR — A small '+' fixed at the center of the screen, drawn in NDC
# (screen) space rather than world space. Its color matches whichever block
# type is currently selected for placing, as a lightweight substitute for a
# proper hotbar UI (no text/font rendering exists yet).
# =============================================================================

import moderngl
import numpy as np
from core.settings import CROSSHAIR_SIZE, WINDOW_ASPECT_RATIO


class Crosshair:
    def __init__(self, ctx, shader_program, color):
        self.ctx             = ctx
        self.shader_program  = shader_program
        self.vbo             = None
        self.vao             = self.build(color)

    # -------------------------------------------------------------------------
    def _vertices(self, color):
        # A vertical line drawn with the same NDC half-length as a horizontal
        # one would look visually STRETCHED, since NDC's -1..1 range maps to
        # a wider span in pixels horizontally than vertically on a widescreen
        # window. Scaling the vertical half-length by the aspect ratio keeps
        # the '+' visually even.
        half_x = CROSSHAIR_SIZE
        half_y = CROSSHAIR_SIZE * WINDOW_ASPECT_RATIO

        return np.array([
            -half_x, 0.0,    0.0, *color,
             half_x, 0.0,    0.0, *color,
             0.0,   -half_y, 0.0, *color,
             0.0,    half_y, 0.0, *color,
        ], dtype = 'f4')

    # -------------------------------------------------------------------------
    def build(self, color):
        self.vbo = self.ctx.buffer(self._vertices(color))
        return self.ctx.vertex_array(
            self.shader_program, [(self.vbo, '3f 3f', 'in_position', 'in_color')]
        )

    # -------------------------------------------------------------------------
    def set_color(self, color):
        """Called when the hotbar selection changes — rewrites the 4 tiny
        vertices in place rather than rebuilding the buffer from scratch."""
        self.vbo.write(self._vertices(color))

    # -------------------------------------------------------------------------
    def render(self):
        self.vao.render(mode = moderngl.LINES)

    # -------------------------------------------------------------------------
    def destroy(self):
        self.vao.release()
