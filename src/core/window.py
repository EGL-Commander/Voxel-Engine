# =============================================================================
# WINDOW — Creates the display window and OpenGL context
# This is the first thing that runs visually. If this works, our pipeline works.
# =============================================================================

import pygame
import moderngl
import sys
from core.settings import *


class Window:
    def __init__(self):
        self.init_pygame()
        self.ctx  = self.init_opengl()
        self.clock = pygame.time.Clock()

    # -------------------------------------------------------------------------
    def init_pygame(self):
        pygame.init()

        # Tell pygame we want an OpenGL-compatible window
        pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MAJOR_VERSION, OPENGL_MAJOR_VERSION)
        pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MINOR_VERSION, OPENGL_MINOR_VERSION)
        pygame.display.gl_set_attribute(pygame.GL_CONTEXT_PROFILE_MASK,
                                         pygame.GL_CONTEXT_PROFILE_CORE)

        pygame.display.set_mode(
            (WINDOW_WIDTH, WINDOW_HEIGHT),
            flags = pygame.OPENGL | pygame.DOUBLEBUF
        )
        pygame.display.set_caption(WINDOW_TITLE)

        # Lock the mouse cursor to the center of the window (FPS style)
        pygame.event.set_grab(True)
        pygame.mouse.set_visible(False)

        # get_rel() reports movement SINCE THE LAST CALL — the very first
        # reading can be a big leftover jump from before the window had
        # focus, so we throw one reading away here to start clean.
        pygame.mouse.get_rel()

    # -------------------------------------------------------------------------
    def init_opengl(self):
        ctx = moderngl.create_context()

        # Enable depth testing — closer objects block farther ones
        ctx.enable(moderngl.DEPTH_TEST)

        # Enable face culling — don't render faces pointing away from camera
        ctx.enable(moderngl.CULL_FACE)

        return ctx

    # -------------------------------------------------------------------------
    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.quit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.quit()
                else:
                    self.on_keydown(event.key)
            elif event.type == pygame.KEYUP:
                self.on_keyup(event.key)

    # -------------------------------------------------------------------------
    # Hooks for subclasses (App) that care about individual key presses.
    # Window itself doesn't need them — left as no-ops here.
    def on_keydown(self, key):
        pass

    def on_keyup(self, key):
        pass

    # -------------------------------------------------------------------------
    def quit(self):
        pygame.quit()
        sys.exit()