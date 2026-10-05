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
from core.save_manager import SaveManager

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

# A new game starts having collected nothing — you have to mine blocks
# before you can place them. Used as a base so a save from an older version
# (missing a block type that's been added since) still ends up with every
# key present, instead of a KeyError the first time that block is selected.
DEFAULT_INVENTORY = {GRASS: 0, DIRT: 0, STONE: 0, SAND: 0, SNOW: 0}


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
        self.hud_program     = self.shader.load('hud')
        self.terrain_program['u_texture'] = 0   # texture unit 0, bound in render()
        self.hud_program['u_texture']     = 0

        self.texture_manager = TextureManager(self.ctx)

        # Load a save if one exists — everything about how the world starts
        # (seed, spawn point, look direction, inventory, every block edit)
        # branches on whether we're resuming a game or starting fresh.
        save = SaveManager.load()

        if save is not None:
            self.world_seed  = save['seed']
            world_generator  = WorldGenerator(seed = self.world_seed)
            spawn_x, spawn_y, spawn_z = save['player_x'], save['player_y'], save['player_z']
            spawn_yaw, spawn_pitch   = save['yaw'], save['pitch']
            self.selected_block = save['selected_block']
            self.inventory       = {**DEFAULT_INVENTORY, **save['inventory']}
            edits                 = save['edits']
            print(f"Loaded save (seed {self.world_seed})")
        else:
            self.world_seed = WORLD_SEED
            world_generator = WorldGenerator()
            spawn_x, spawn_z = world_generator.find_spawn_column()
            # Spawn a few blocks above the ground and let gravity drop the
            # player onto the terrain — a nice built-in proof that physics
            # is actually running, not just decorative code.
            ground_height = world_generator.get_height(spawn_x, spawn_z)
            # +0.5 centers the player on the block instead of its corner —
            # save files don't need this since they store an exact position
            # that was already centered when it was originally spawned.
            spawn_x, spawn_z = spawn_x + 0.5, spawn_z + 0.5
            spawn_y = ground_height + 5
            spawn_yaw, spawn_pitch = -90, -10   # Player's own defaults
            self.selected_block = STONE
            self.inventory       = dict(DEFAULT_INVENTORY)
            edits                 = {}

        # Window title always reflects the seed ACTUALLY in use — which, with
        # a loaded save, is that save's seed, not whatever settings.py says.
        pygame.display.set_caption(f"Voxel Engine — seed {self.world_seed}")
        print(f"World seed: {self.world_seed}")

        # One shared generator for spawn search AND chunk generation — with
        # a random seed, two separately-created generators would each roll
        # their own seed and disagree on what the world even looks like.
        self.chunk_manager = ChunkManager(
            self.ctx, self.terrain_program, self.texture_manager,
            center_world_x = spawn_x, center_world_z = spawn_z,
            world_generator = world_generator, edits = edits
        )

        self.player = Player(self.chunk_manager, (spawn_x, spawn_y, spawn_z))
        # Player's own constructor always starts facing its own default
        # direction — restore the saved look direction on top of that.
        self.player.camera.yaw   = spawn_yaw
        self.player.camera.pitch = spawn_pitch
        self.player.camera.update_vectors()
        self.player.camera.m_view = self.player.camera.get_view_matrix()

        self.crosshair = Crosshair(self.ctx, self.ui_program, HOTBAR_COLORS[self.selected_block])
        self.autosave_timer = 0

        # Creative mode is a SESSION toggle, not something saved — it always
        # starts off, even when resuming a save. Flying and infinite
        # placement are bundled into one toggle (same as Minecraft's own
        # creative mode) since that's the simpler, more familiar mental
        # model than two separate keys.
        self.creative_mode = False

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
        elif key == pygame.K_F5:
            self.save_game()
        elif key == pygame.K_c:
            self.toggle_creative()
        else:
            self.input.handle_keydown(key)

    # -------------------------------------------------------------------------
    def toggle_creative(self):
        self.creative_mode  = not self.creative_mode
        self.player.flying  = self.creative_mode
        self.player.velocity_y = 0   # don't carry fall speed into/out of flight

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
        if hit_block is None:
            return

        broken_type = self.chunk_manager.get_block_world(*hit_block)
        placed = self.chunk_manager.set_block(*hit_block, AIR)
        # In creative mode, breaking doesn't add to your SURVIVAL inventory
        # (same as Minecraft creative) — it just removes the block. Keeps
        # creative-mode experimentation from polluting the real inventory
        # you'll have when you switch back.
        if placed and not self.creative_mode:
            self.inventory[broken_type] = self.inventory.get(broken_type, 0) + 1

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

        # Creative mode places freely, ignoring (and not touching) the
        # survival inventory count entirely.
        if not self.creative_mode and self.inventory.get(self.selected_block, 0) <= 0:
            return   # nothing left of this block type to place

        if self.chunk_manager.set_block(*place_block, self.selected_block):
            if not self.creative_mode:
                self.inventory[self.selected_block] -= 1

    # -------------------------------------------------------------------------
    def save_game(self):
        SaveManager.save(
            seed             = self.world_seed,
            player_position  = self.player.position,
            yaw              = self.player.camera.yaw,
            pitch            = self.player.camera.pitch,
            selected_block   = self.selected_block,
            inventory        = self.inventory,
            edits            = self.chunk_manager.edits,
        )

    # -------------------------------------------------------------------------
    def hud_lines(self):
        p      = self.player.position
        camera = self.player.camera
        biome  = self.chunk_manager.world_generator.get_biome(int(p.x), int(p.z))

        lines = [
            f"seed {self.world_seed}    fps {self.clock.get_fps():.0f}",
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

        selected_count = self.inventory.get(self.selected_block, 0)
        lines.append(
            f"selected: {BLOCK_NAMES[self.selected_block]} x{selected_count}  (keys 1-5)"
        )
        lines.append("inv: " + "  ".join(
            f"{BLOCK_NAMES[b]} {self.inventory.get(b, 0)}"
            for b in (GRASS, DIRT, STONE, SAND, SNOW)
        ))

        if self.cave_target is not None:
            tx, ty, tz = self.cave_target
            lines.append(
                f"nearest cave: {tx - p.x:+.0f}, {ty - p.y:+.0f}, {tz - p.z:+.0f} "
                f"blocks away"
            )
        else:
            lines.append("F4: find nearest cave")

        mode = "CREATIVE" if self.creative_mode else "SURVIVAL"
        lines.append(f"mode: {mode}  (C to toggle)")
        lines.append("F3: toggle display   F5: save")
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

        self.autosave_timer += dt
        if self.autosave_timer >= AUTOSAVE_INTERVAL_MS:
            self.autosave_timer = 0
            self.save_game()

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
        self.save_game()
        self.hud.destroy()
        self.crosshair.destroy()
        self.texture_manager.destroy()
        self.chunk_manager.destroy()
        self.shader.destroy()
        super().quit()
