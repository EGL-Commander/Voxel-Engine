# =============================================================================
# APP — The main application loop
# Controls the game loop : handle input → update → render → repeat
# =============================================================================


import pygame
import moderngl
from core.window import Window
from core.settings import *
from rendering.shader import ShaderProgram
from rendering.mesh_builder import TestTriangle


class App(Window):
    def __init__(self):
        super().__init__()

        # Load and compile the default shader program
        self.shader  = ShaderProgram(self.ctx)
        self.program = self.shader.load('default')

        # Build the test triangle using that shader
        self.triangle = TestTriangle(self.ctx, self.program)

        self.run()

    # -------------------------------------------------------------------------
    def run(self):
        while True:
            self.handle_events()
            self.render()
            pygame.display.flip()
            self.clock.tick(60)

    # -------------------------------------------------------------------------
    def render(self):
        self.ctx.clear(color = BG_COLOR)

        # Tell the triangle to draw itself
        self.triangle.render()

    # -------------------------------------------------------------------------
    def quit(self):
        self.triangle.destroy()
        self.shader.destroy()
        super().quit()