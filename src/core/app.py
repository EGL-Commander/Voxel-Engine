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
from world.world_generator import WorldGenerator
from world.chunk import AIR, GRASS, DIRT, STONE, SAND, SNOW, BLOCK_NAMES
from rendering.hud import HUD

# Hotbar: number key -> block type it places. Extend this dict (and
# HOTBAR_COLORS below) as new block types get added.
HOTBAR = {
    pygame.K_1: GRASS,
    pygame.K_2: DIRT,
    pygame.K_3: STONE,
    pygame.K_4: SAND,
    pygame.K_5: SNOW,
}

# The crosshair is a flat-color UI element (see ui.vert/ui.frag), so it needs
# its own plain RGB per block type — separate from the texture atlas, which
# is what the terrain itself actually samples from.
HOTBAR_COLORS = {
    GRASS: (0.40, 0.75, 0.30),
    DIRT:  (0.50, 0.36, 0.20),
    STONE: (0.55, 0.55, 0.58),
    SAND:  (0.86, 0.80, 0.59),
    SNOW:  (0.94, 0.96, 0.97),
}


class App(Window):
    def __init__(self):
        super().__init__()

        # Shown in the window title and printed, so a world you like (or a
        # bug you hit) can be reproduced: set WORLD_SEED in settings.py.
        pygame.display.set_caption(f"Voxel Engine — seed {WORLD_SEED}")
        print(f"World seed: {WORLD_SEED}")

        self.input = InputHandler()

        # Two separate shader programs: 'terrain' samples the texture atlas
        # with UV coords for the world, 'ui' is flat-color for screen-space
        # overlays like the crosshair — they need different vertex data, so
        # one shader trying to do both would need a bunch of unused inputs.
        self.shader          = ShaderProgram(self.ctx)
        self.terrain_program = self.shader.load('terrain')
        self.ui_program      = self.shader.load('ui')
        self.hud_program     = self.shader.load('hud')
        self.terrain_program['u_texture'] = 0   # texture unit 0, bound in render()
        self.hud_program['u_texture']     = 0

        self.texture_manager = TextureManager(self.ctx)

        # One shared generator for spawn search AND chunk generation — with
        # a random seed, two separately-created generators would each roll
        # their own seed and disagree on what the world even looks like.
        world_generator = WorldGenerator()
        spawn_x, spawn_z = world_generator.find_spawn_column()
        self.chunk_manager = ChunkManager(
            self.ctx, self.terrain_program, self.texture_manager,
            center_world_x = spawn_x, center_world_z = spawn_z,
            world_generator = world_generator
        )

        # Spawn a few blocks above the ground and let gravity drop the
        # player onto the terrain — a nice built-in proof that physics is
        # actually running, not just decorative code.
        ground_height = self.chunk_manager.world_generator.get_height(spawn_x, spawn_z)
        spawn = (spawn_x + 0.5, ground_height + 5, spawn_z + 0.5)
        self.player = Player(self.chunk_manager, spawn)

        # No text/font rendering exists yet, so there's no on-screen hotbar
        # list — the crosshair's color doubles as the "selected block"
        # indicator until a real HUD exists.
        self.selected_block = STONE
        self.crosshair = Crosshair(self.ctx, self.ui_program, HOTBAR_COLORS[STONE])

        # Debug HUD: position/biome/looking-at/fps, toggled with F3. F4 looks
        # for the nearest cave and shows how far away it is, since caves have
        # no other way to be found short of digging blind.
        self.hud         = HUD(self.ctx, self.hud_program)
        self.hud_visible = True
        self.cave_target = None

        self.run()

    # -------------------------------------------------------------------------
    # Window calls these when it sees KEYDOWN/KEYUP/MOUSEBUTTONDOWN events
    # (see window.py)
    def on_keydown(self, key):
        if key in HOTBAR:
            self.selected_block = HOTBAR[key]
            self.crosshair.set_color(HOTBAR_COLORS[self.selected_block])
        elif key == pygame.K_F3:
            self.hud_visible = not self.hud_visible
        elif key == pygame.K_F4:
            self.find_nearest_cave()
        else:
            self.input.handle_keydown(key)

    # -------------------------------------------------------------------------
    def find_nearest_cave(self):
        p = self.player.position
        self.cave_target = self.chunk_manager.world_generator.find_cave_spot(
            int(p.x), int(p.z)
        )

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
    def hud_lines(self):
        p      = self.player.position
        camera = self.player.camera
        biome  = self.chunk_manager.world_generator.get_biome(int(p.x), int(p.z))

        lines = [
            f"seed {WORLD_SEED}    fps {self.clock.get_fps():.0f}",
            f"pos {p.x:.1f}, {p.y:.1f}, {p.z:.1f}   biome {biome}",
            f"yaw {camera.yaw:.0f}  pitch {camera.pitch:.0f}   "
            f"chunks {len(self.chunk_manager.chunks)}",
        ]

        hit_block, _ = raycast(self.chunk_manager, camera.position, camera.forward)
        if hit_block is not None:
            block_id = self.chunk_manager.get_block_world(*hit_block)
            lines.append(f"looking at: {BLOCK_NAMES[block_id]} {hit_block}")
        else:
            lines.append("looking at: (nothing in reach)")

        lines.append(f"selected: {BLOCK_NAMES[self.selected_block]}  (keys 1-5)")

        if self.cave_target is not None:
            tx, ty, tz = self.cave_target
            lines.append(
                f"nearest cave: {tx - p.x:+.0f}, {ty - p.y:+.0f}, {tz - p.z:+.0f} "
                f"blocks away"
            )
        else:
            lines.append("F4: find nearest cave")

        lines.append("F3: toggle this display")
        return lines

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

        if self.hud_visible:
            self.hud.update(dt, self.hud_lines)

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
        if self.hud_visible:
            self.hud.render()
        self.ctx.enable(moderngl.DEPTH_TEST)

    # -------------------------------------------------------------------------
    def quit(self):
        self.hud.destroy()
        self.crosshair.destroy()
        self.texture_manager.destroy()
        self.chunk_manager.destroy()
        self.shader.destroy()
        super().quit()
