# =============================================================================
# APP — The main application loop
# Controls the game loop : handle input → update → render → repeat
# =============================================================================


import pygame
import moderngl
import glm
from core.window import Window
from core.settings import *
from player.camera import Camera
from player.input_handler import InputHandler
from rendering.shader import ShaderProgram
from rendering.mesh_builder import Cube


class App(Window):
    def __init__(self):
        super().__init__()

        # Input + camera
        self.input  = InputHandler()
        self.camera = Camera(position = (0, 0, 3))

        # Load and compile the default shader program
        self.shader  = ShaderProgram(self.ctx)
        self.program = self.shader.load('default')

        # Build the cube using that shader
        self.cube = Cube(self.ctx, self.program)

        # Where the cube sits in the world — identity = centered at origin,
        # no rotation, no scale. This will matter once we have many objects.
        self.m_model = glm.mat4()

        self.run()

    # -------------------------------------------------------------------------
    # Window calls these when it sees KEYDOWN/KEYUP events (see window.py)
    def on_keydown(self, key):
        self.input.handle_keydown(key)

    def on_keyup(self, key):
        self.input.handle_keyup(key)

    # -------------------------------------------------------------------------
    def run(self):
        while True:
            dt = self.clock.tick(60)   # milliseconds since the last frame
            self.handle_events()
            self.update(dt)
            self.render()
            pygame.display.flip()

    # -------------------------------------------------------------------------
    def update(self, dt):
        self.input.update_mouse()
        self.camera.update(
            self.input.keys, self.input.mouse_dx, self.input.mouse_dy, dt
        )

        # Push the latest matrices to the GPU. moderngl accepts glm matrices
        # directly — they support the buffer protocol .write() needs.
        self.program['m_proj'].write(self.camera.m_proj)
        self.program['m_view'].write(self.camera.m_view)
        self.program['m_model'].write(self.m_model)

    # -------------------------------------------------------------------------
    def render(self):
        self.ctx.clear(color = BG_COLOR)
        self.cube.render()

    # -------------------------------------------------------------------------
    def quit(self):
        self.cube.destroy()
        self.shader.destroy()
        super().quit()
