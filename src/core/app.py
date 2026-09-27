# =============================================================================
# APP — The main application loop
# Controls the game loop : handle input → update → render → repeat
# =============================================================================


import pygame
import moderngl
import glm
from core.window import Window
from core.settings import *
from player.player import Player
from player.input_handler import InputHandler
from player.raycaster import raycast
from player.physics import block_intersects_box
from rendering.shader import ShaderProgram
from world.chunk_manager import ChunkManager
from world.chunk import AIR, STONE


class App(Window):
    def __init__(self):
        super().__init__()

        self.input = InputHandler()

        # Load and compile the default shader program
        self.shader  = ShaderProgram(self.ctx)
        self.program = self.shader.load('default')

        # Build every chunk in the render-distance grid, each with its own
        # voxel data (from WorldGenerator) and its own face-culled mesh.
        self.chunk_manager = ChunkManager(self.ctx, self.program)

        # Spawn a few blocks above the ground at (8, 8) and let gravity drop
        # the player onto the terrain — a nice built-in proof that physics
        # is actually running, not just decorative code.
        ground_height = self.chunk_manager.world_generator.get_height(8, 8)
        spawn = (8, ground_height + 5, 8)
        self.player = Player(self.chunk_manager, spawn)

        self.run()

    # -------------------------------------------------------------------------
    # Window calls these when it sees KEYDOWN/KEYUP/MOUSEBUTTONDOWN events
    # (see window.py)
    def on_keydown(self, key):
        self.input.handle_keydown(key)

    def on_keyup(self, key):
        self.input.handle_keyup(key)

    def on_mousedown(self, button):
        if button == 1:      # left click — break the block you're looking at
            self.break_block()
        elif button == 3:    # right click — place one against its face
            self.place_block()

    # -------------------------------------------------------------------------
    def break_block(self):
        hit_block, _ = raycast(
            self.chunk_manager, self.player.camera.position, self.player.camera.forward
        )
        if hit_block is not None:
            self.chunk_manager.set_block(*hit_block, AIR)

    # -------------------------------------------------------------------------
    def place_block(self):
        _, place_block = raycast(
            self.chunk_manager, self.player.camera.position, self.player.camera.forward
        )
        if place_block is None:
            return

        # Don't let the player wedge a block into their own body — that
        # would trap them inside solid geometry with no way to move out.
        if block_intersects_box(
            self.player.position, PLAYER_HALF_WIDTH, PLAYER_HEIGHT, place_block
        ):
            return

        self.chunk_manager.set_block(*place_block, STONE)

    # -------------------------------------------------------------------------
    def run(self):
        while True:
            dt = self.clock.tick(60)   # milliseconds since the last frame
            dt = min(dt, MAX_DT_MS)    # never let one slow frame (e.g. the
                                        # first frame, spent building chunks)
                                        # cause an oversized physics step
            self.handle_events()
            self.update(dt)
            self.render()
            pygame.display.flip()

    # -------------------------------------------------------------------------
    def update(self, dt):
        self.input.update_mouse()
        self.player.update(
            self.input.keys, self.input.mouse_dx, self.input.mouse_dy, dt
        )

        camera = self.player.camera
        self.program['m_proj'].write(camera.m_proj)
        self.program['m_view'].write(camera.m_view)

    # -------------------------------------------------------------------------
    def render(self):
        self.ctx.clear(color = BG_COLOR)
        self.chunk_manager.render(self.program['m_model'])

    # -------------------------------------------------------------------------
    def quit(self):
        self.chunk_manager.destroy()
        self.shader.destroy()
        super().quit()
