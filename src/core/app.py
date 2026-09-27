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
from rendering.texture_manager import TextureManager
from rendering.crosshair import Crosshair
from world.chunk_manager import ChunkManager
from world.chunk import AIR, GRASS, DIRT, STONE

# Hotbar: number key -> block type it places. Just 3 slots for now, matching
# the 3 block types that currently exist — extend this dict as new block
# types get added.
HOTBAR = {
    pygame.K_1: GRASS,
    pygame.K_2: DIRT,
    pygame.K_3: STONE,
}

# The crosshair is a flat-color UI element (see ui.vert/ui.frag), so it needs
# its own plain RGB per block type — separate from the texture atlas, which
# is what the terrain itself actually samples from.
HOTBAR_COLORS = {
    GRASS: (0.40, 0.75, 0.30),
    DIRT:  (0.50, 0.36, 0.20),
    STONE: (0.55, 0.55, 0.58),
}


class App(Window):
    def __init__(self):
        super().__init__()

        self.input = InputHandler()

        # Two separate shader programs: 'terrain' samples the texture atlas
        # with UV coords for the world, 'ui' is flat-color for screen-space
        # overlays like the crosshair — they need different vertex data, so
        # one shader trying to do both would need a bunch of unused inputs.
        self.shader          = ShaderProgram(self.ctx)
        self.terrain_program = self.shader.load('terrain')
        self.ui_program      = self.shader.load('ui')
        self.terrain_program['u_texture'] = 0   # texture unit 0, bound in render()

        self.texture_manager = TextureManager(self.ctx)

        # Build the initial chunk grid centered on world origin (where the
        # player spawns) — update() will re-center this around the player
        # as they move, instead of this staying a fixed diorama forever.
        self.chunk_manager = ChunkManager(
            self.ctx, self.terrain_program, self.texture_manager,
            center_world_x = 8, center_world_z = 8
        )

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
        self.crosshair = Crosshair(self.ctx, self.ui_program, HOTBAR_COLORS[STONE])

        self.run()

    # -------------------------------------------------------------------------
    # Window calls these when it sees KEYDOWN/KEYUP/MOUSEBUTTONDOWN events
    # (see window.py)
    def on_keydown(self, key):
        if key in HOTBAR:
            self.selected_block = HOTBAR[key]
            self.crosshair.set_color(HOTBAR_COLORS[self.selected_block])
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
        self.chunk_manager.update(self.player.position.x, self.player.position.z)

        camera = self.player.camera
        self.terrain_program['m_proj'].write(camera.m_proj)
        self.terrain_program['m_view'].write(camera.m_view)

    # -------------------------------------------------------------------------
    def render(self):
        self.ctx.clear(color = BG_COLOR)

        self.texture_manager.use(location = 0)
        self.chunk_manager.render(self.terrain_program['m_model'])

        # Crosshair uses its own shader with no matrices at all (always
        # drawn directly in NDC space — see ui.vert), so there's nothing to
        # set here beyond turning depth testing off so it's always on top.
        self.ctx.disable(moderngl.DEPTH_TEST)
        self.crosshair.render()
        self.ctx.enable(moderngl.DEPTH_TEST)

    # -------------------------------------------------------------------------
    def quit(self):
        self.crosshair.destroy()
        self.texture_manager.destroy()
        self.chunk_manager.destroy()
        self.shader.destroy()
        super().quit()
