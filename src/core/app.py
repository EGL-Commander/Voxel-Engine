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
from rendering.crosshair import Crosshair
from world.chunk_manager import ChunkManager
from world.chunk import AIR, GRASS, DIRT, STONE, BLOCK_COLORS

# Hotbar: number key -> block type it places. Just 3 slots for now, matching
# the 3 block types that currently exist — extend this dict as new block
# types get added.
HOTBAR = {
    pygame.K_1: GRASS,
    pygame.K_2: DIRT,
    pygame.K_3: STONE,
}


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

        # No text/font rendering exists yet, so there's no on-screen hotbar
        # list — the crosshair's color doubles as the "selected block"
        # indicator until a real HUD exists.
        self.selected_block = STONE
        self.crosshair = Crosshair(self.ctx, self.program, BLOCK_COLORS[STONE])

        self.run()

    # -------------------------------------------------------------------------
    # Window calls these when it sees KEYDOWN/KEYUP/MOUSEBUTTONDOWN events
    # (see window.py)
    def on_keydown(self, key):
        if key in HOTBAR:
            self.selected_block = HOTBAR[key]
            self.crosshair.set_color(BLOCK_COLORS[self.selected_block])
        else:
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

        self.chunk_manager.set_block(*place_block, self.selected_block)

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

        # Crosshair is drawn directly in screen space, so it gets identity
        # matrices instead of the camera's (see Crosshair's docstring), and
        # depth testing is switched off so it always shows on top of the
        # world no matter what's directly in front of it.
        identity = glm.mat4()
        self.program['m_proj'].write(identity)
        self.program['m_view'].write(identity)
        self.program['m_model'].write(identity)

        self.ctx.disable(moderngl.DEPTH_TEST)
        self.crosshair.render()
        self.ctx.enable(moderngl.DEPTH_TEST)

    # -------------------------------------------------------------------------
    def quit(self):
        self.crosshair.destroy()
        self.chunk_manager.destroy()
        self.shader.destroy()
        super().quit()
