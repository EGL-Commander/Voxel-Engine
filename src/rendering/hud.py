# =============================================================================
# HUD — A block of debug text in the top-left corner (position, biome, what
# you're looking at, FPS...). OpenGL has no text drawing of its own, so the
# trick is: render the text into a small image with pygame's font module, upload
# that image as a texture, and draw it on a screen-space quad. The image is
# only re-rendered a few times a second (not every frame), since re-rendering
# and re-uploading text 60 times a second would be wasted work for numbers a
# human can't read that fast anyway.
# =============================================================================

import moderngl
import numpy as np
import pygame
from core.settings import WINDOW_WIDTH, WINDOW_HEIGHT, HUD_FONT_SIZE, HUD_UPDATE_MS

PADDING   = 8     # pixels between the panel edge and the text
MARGIN    = 10    # pixels between the panel and the window edge
MAX_LINES = 11    # the panel is a fixed size, so it needs a line cap


class HUD:
    def __init__(self, ctx, shader_program):
        self.ctx            = ctx
        self.shader_program = shader_program

        pygame.font.init()
        # Font(None, size) is pygame's built-in default font — no font file
        # needs to ship with the project.
        self.font = pygame.font.Font(None, HUD_FONT_SIZE)

        line_height = self.font.get_linesize()
        self.width  = 380
        self.height = MAX_LINES * line_height + 2 * PADDING

        self.texture = ctx.texture((self.width, self.height), 4)
        self.texture.filter = (ctx.NEAREST, ctx.NEAREST)   # 1 texel = 1 pixel, keep it crisp

        # The quad, in NDC (-1..1). Sized so the texture maps 1:1 onto screen
        # pixels regardless of window size (2 NDC units span the full window).
        w = 2 * self.width  / WINDOW_WIDTH
        h = 2 * self.height / WINDOW_HEIGHT
        left = -1 + 2 * MARGIN / WINDOW_WIDTH
        top  =  1 - 2 * MARGIN / WINDOW_HEIGHT
        #        x            y          u    v
        quad = np.array([
            left,     top - h,   0.0, 0.0,    # bottom-left
            left + w, top - h,   1.0, 0.0,    # bottom-right
            left,     top,       0.0, 1.0,    # top-left
            left + w, top,       1.0, 1.0,    # top-right
        ], dtype = 'f4')
        self.vbo = ctx.buffer(quad)
        self.vao = ctx.vertex_array(
            shader_program, [(self.vbo, '2f 2f', 'in_position', 'in_uv')]
        )

        self.timer = HUD_UPDATE_MS   # start "due", so the first frame draws text

    # -------------------------------------------------------------------------
    def update(self, dt, get_lines):
        """
        Called every frame. `get_lines` is a function returning the list of
        strings to show — passed as a function (not a list) so the work of
        building the text, which can include a raycast, only happens on the
        frames when we actually re-render, not all 60 of them each second.
        """
        self.timer += dt
        if self.timer < HUD_UPDATE_MS:
            return
        self.timer = 0
        self._redraw(get_lines())

    # -------------------------------------------------------------------------
    def _redraw(self, lines):
        surface = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        surface.fill((0, 0, 0, 150))    # translucent dark panel so text stays readable

        y = PADDING
        for line in lines[:MAX_LINES]:
            text = self.font.render(line, True, (255, 255, 255))
            surface.blit(text, (PADDING, y))
            y += self.font.get_linesize()

        # flipped=True: pygame images start at the TOP row but OpenGL
        # textures start at the BOTTOM row, so the rows must be reversed.
        self.texture.write(pygame.image.tostring(surface, 'RGBA', True))

    # -------------------------------------------------------------------------
    def render(self):
        self.texture.use(location = 0)
        self.ctx.enable(moderngl.BLEND)   # default blend = source alpha over what's underneath
        self.vao.render(mode = moderngl.TRIANGLE_STRIP)
        self.ctx.disable(moderngl.BLEND)

    # -------------------------------------------------------------------------
    def destroy(self):
        self.vao.release()
        self.vbo.release()
        self.texture.release()
