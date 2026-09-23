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
from world.chunk_manager import ChunkManager


class App(Window):
    def __init__(self):
        super().__init__()

        # Input + camera. Positioned up and back from the world's origin so
        # you spawn looking down at the generated terrain instead of inside it.
        self.input  = InputHandler()
        self.camera = Camera(position = (8, 35, 130), yaw = -90, pitch = -20)

        # Load and compile the default shader program
        self.shader  = ShaderProgram(self.ctx)
        self.program = self.shader.load('default')

        # Build every chunk in the render-distance grid, each with its own
        # voxel data (from WorldGenerator) and its own face-culled mesh.
        self.chunk_manager = ChunkManager(self.ctx, self.program)

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

        # Camera matrices only need to be sent once per frame here.
        # m_model is written per-chunk inside ChunkManager.render() instead,
        # since every chunk sits at a different world position.
        self.program['m_proj'].write(self.camera.m_proj)
        self.program['m_view'].write(self.camera.m_view)

    # -------------------------------------------------------------------------
    def render(self):
        self.ctx.clear(color = BG_COLOR)
        self.chunk_manager.render(self.program['m_model'])

    # -------------------------------------------------------------------------
    def quit(self):
        self.chunk_manager.destroy()
        self.shader.destroy()
        super().quit()
