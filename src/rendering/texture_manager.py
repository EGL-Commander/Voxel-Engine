# =============================================================================
# TEXTURE MANAGER — Loads the block texture atlas (src/assets/textures/
# atlas.png) onto the GPU and hands out the UV rectangle for each named tile,
# so chunk.py can look up "grass_top" or "stone" without knowing the atlas's
# actual pixel layout.
# =============================================================================

import os
from PIL import Image

# Must match the left-to-right layout of atlas.png (a horizontal strip of
# 16x16 tiles). If atlas.png is ever replaced with a bigger/different sheet,
# this list is the only place that needs to change — the count follows it.
TILE_NAMES = [
    'grass_top', 'grass_side', 'dirt', 'stone',
    'sand', 'snow_top', 'snow_side', 'water',
]
TILE_COUNT = len(TILE_NAMES)


class TextureManager:
    def __init__(self, ctx):
        self.ctx = ctx

        atlas_path = os.path.join(
            os.path.dirname(__file__), '..', 'assets', 'textures', 'atlas.png'
        )
        image = Image.open(atlas_path).convert('RGB')

        self.texture = ctx.texture(image.size, 3, image.tobytes())
        # NEAREST (not the default smoothing) keeps every texture crisp and
        # blocky up close, matching the voxel look, instead of going blurry.
        self.texture.filter = (self.ctx.NEAREST, self.ctx.NEAREST)

        # Precompute each tile's UV rectangle as (u_min, u_max) — v spans the
        # full 0-1 height since the atlas is only one row tall.
        self.uv_rects = {}
        for i, name in enumerate(TILE_NAMES):
            u_min = i / TILE_COUNT
            u_max = (i + 1) / TILE_COUNT
            self.uv_rects[name] = (u_min, u_max)

    # -------------------------------------------------------------------------
    def get_uv_rect(self, tile_name):
        return self.uv_rects[tile_name]

    # -------------------------------------------------------------------------
    def use(self, location = 0):
        self.texture.use(location = location)

    # -------------------------------------------------------------------------
    def destroy(self):
        self.texture.release()
