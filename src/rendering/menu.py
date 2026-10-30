# =============================================================================
# MAIN MENU — The title screen shown before the game world exists: New Game
# / Continue (only if a save is present) / Quit. Keyboard-only (Up/Down,
# Enter) since there's no mouse-to-screen hit-testing infrastructure built
# yet — reuses the exact same "render text with pygame, upload as a texture,
# draw on a full-screen quad" trick as HUD, just full-screen instead of a
# small corner panel, and redrawn only when the selection changes rather
# than every frame.
# =============================================================================

import moderngl
import numpy as np
import pygame
from core.settings import WINDOW_WIDTH, WINDOW_HEIGHT


class MainMenu:
    def __init__(self, ctx, shader_program, save_exists):
        self.ctx             = ctx
        self.shader_program  = shader_program

        self.options = ['New Game']
        if save_exists:
            self.options.append('Continue')
        self.options.append('Quit')
        # Default to Continue when there's a save to continue: with a single
        # save slot, starting a New Game means its first autosave overwrites
        # the old save, so one accidental Enter on launch shouldn't be able
        # to do that. (No save -> 'New Game' is the only real choice anyway.)
        self.selected = self.options.index('Continue') if save_exists else 0

        pygame.font.init()
        self.title_font  = pygame.font.Font(None, 72)
        self.option_font = pygame.font.Font(None, 42)

        # Full-screen quad, in NDC (-1..1 covers the whole window).
        quad = np.array([
            -1.0, -1.0,  0.0, 0.0,
             1.0, -1.0,  1.0, 0.0,
            -1.0,  1.0,  0.0, 1.0,
             1.0,  1.0,  1.0, 1.0,
        ], dtype = 'f4')
        self.vbo = ctx.buffer(quad)
        self.vao = ctx.vertex_array(
            shader_program, [(self.vbo, '2f 2f', 'in_position', 'in_uv')]
        )

        self.texture = ctx.texture((WINDOW_WIDTH, WINDOW_HEIGHT), 4)
        self.texture.filter = (ctx.NEAREST, ctx.NEAREST)
        self._redraw()

    # -------------------------------------------------------------------------
    def move_selection(self, delta):
        self.selected = (self.selected + delta) % len(self.options)
        self._redraw()

    # -------------------------------------------------------------------------
    def confirm(self):
        """Returns the chosen option's label ('New Game' / 'Continue' / 'Quit')."""
        return self.options[self.selected]

    # -------------------------------------------------------------------------
    def _redraw(self):
        surface = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        surface.fill((22, 26, 36, 255))   # opaque — this fully replaces the
                                            # world view, nothing renders behind it

        title = self.title_font.render("VOXEL ENGINE", True, (255, 255, 255))
        surface.blit(title, title.get_rect(center = (WINDOW_WIDTH // 2, WINDOW_HEIGHT // 3)))

        start_y = WINDOW_HEIGHT // 2
        for i, option in enumerate(self.options):
            is_selected = (i == self.selected)
            color  = (255, 215, 80) if is_selected else (200, 200, 200)
            prefix = "> " if is_selected else "  "
            text = self.option_font.render(prefix + option, True, color)
            surface.blit(text, text.get_rect(center = (WINDOW_WIDTH // 2, start_y + i * 54)))

        # flipped=True: pygame images start at the TOP row, OpenGL textures
        # start at the BOTTOM row.
        self.texture.write(pygame.image.tostring(surface, 'RGBA', True))

    # -------------------------------------------------------------------------
    def render(self):
        self.texture.use(location = 0)
        self.vao.render(mode = moderngl.TRIANGLE_STRIP)

    # -------------------------------------------------------------------------
    def destroy(self):
        self.vao.release()
        self.vbo.release()
        self.texture.release()
