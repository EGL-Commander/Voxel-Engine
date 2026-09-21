# =============================================================================
# MESH BUILDER — TestTriangle confirmed the pipeline works. Cube is the next
# step: real 3D geometry, drawn with an index buffer instead of raw triangles.
# This file will later be replaced by chunk-based voxel meshing.
# =============================================================================

import numpy as np


class TestTriangle:
    def __init__(self, ctx, shader_program):
        self.ctx            = ctx
        self.shader_program = shader_program
        self.vao            = self.build()

    # -------------------------------------------------------------------------
    def build(self):
        """
        Defines 3 vertices in 3D space forming a triangle.
        Coordinates go from -1.0 to 1.0 on each axis in OpenGL's space.
        (0, 0, 0) is the center of the screen.
        """
        vertices = np.array([
            # x      y      z
             0.0,   0.5,   0.0,    # top center
            -0.5,  -0.5,   0.0,    # bottom left
             0.5,  -0.5,   0.0,    # bottom right
        ], dtype = 'f4')           # f4 means 32-bit float, what OpenGL expects

        # VBO — Vertex Buffer Object
        # This sends the vertex data from CPU memory to GPU memory
        vbo = self.ctx.buffer(vertices)

        # VAO — Vertex Array Object
        # This tells the GPU how to read the VBO data
        # '3f' means each vertex is 3 floats (x, y, z)
        # 'in_position' must exactly match the variable name in default.vert
        vao = self.ctx.vertex_array(
            self.shader_program,
            [(vbo, '3f', 'in_position')]
        )

        return vao

    # -------------------------------------------------------------------------
    def render(self):
        self.vao.render()

    # -------------------------------------------------------------------------
    def destroy(self):
        self.vao.release()


class Cube:
    """
    A single unit cube centered on the origin, from -0.5 to 0.5 on each axis.
    Each of the 6 faces gets its own 4 vertices (so it can have its own flat
    color/normal) instead of sharing corners — 24 vertices total, drawn with
    an index buffer (EBO) so we don't repeat vertex data for the 12 triangles.
    """

    def __init__(self, ctx, shader_program):
        self.ctx            = ctx
        self.shader_program = shader_program
        self.vao            = self.build()

    # -------------------------------------------------------------------------
    def build(self):
        # One flat color per face — makes it easy to see the cube rotate
        # correctly once the camera is moving.
        RED     = (1.0, 0.2, 0.2)
        GREEN   = (0.2, 1.0, 0.2)
        BLUE    = (0.2, 0.4, 1.0)
        YELLOW  = (1.0, 1.0, 0.2)
        CYAN    = (0.2, 1.0, 1.0)
        MAGENTA = (1.0, 0.2, 1.0)

        # Each tuple is (x, y, z, r, g, b) — position interleaved with color
        raw = [
            # Front face  (z = +0.5)
            (-0.5, -0.5,  0.5, *RED), ( 0.5, -0.5,  0.5, *RED),
            ( 0.5,  0.5,  0.5, *RED), (-0.5,  0.5,  0.5, *RED),
            # Back face   (z = -0.5)
            ( 0.5, -0.5, -0.5, *GREEN), (-0.5, -0.5, -0.5, *GREEN),
            (-0.5,  0.5, -0.5, *GREEN), ( 0.5,  0.5, -0.5, *GREEN),
            # Left face   (x = -0.5)
            (-0.5, -0.5, -0.5, *BLUE), (-0.5, -0.5,  0.5, *BLUE),
            (-0.5,  0.5,  0.5, *BLUE), (-0.5,  0.5, -0.5, *BLUE),
            # Right face  (x = +0.5)
            ( 0.5, -0.5,  0.5, *YELLOW), ( 0.5, -0.5, -0.5, *YELLOW),
            ( 0.5,  0.5, -0.5, *YELLOW), ( 0.5,  0.5,  0.5, *YELLOW),
            # Top face    (y = +0.5)
            (-0.5,  0.5,  0.5, *CYAN), ( 0.5,  0.5,  0.5, *CYAN),
            ( 0.5,  0.5, -0.5, *CYAN), (-0.5,  0.5, -0.5, *CYAN),
            # Bottom face (y = -0.5)
            (-0.5, -0.5, -0.5, *MAGENTA), ( 0.5, -0.5, -0.5, *MAGENTA),
            ( 0.5, -0.5,  0.5, *MAGENTA), (-0.5, -0.5,  0.5, *MAGENTA),
        ]
        vertices = np.array(raw, dtype = 'f4').flatten()

        # Two triangles per face, each face's 4 verts start at index i*4
        indices = []
        for face in range(6):
            base = face * 4
            indices += [base, base + 1, base + 2, base, base + 2, base + 3]
        indices = np.array(indices, dtype = 'i4')

        vbo = self.ctx.buffer(vertices)
        ebo = self.ctx.buffer(indices)

        # '3f 3f' = 3 floats for position, then 3 floats for color, per vertex
        vao = self.ctx.vertex_array(
            self.shader_program,
            [(vbo, '3f 3f', 'in_position', 'in_color')],
            ebo
        )

        return vao

    # -------------------------------------------------------------------------
    def render(self):
        self.vao.render()

    # -------------------------------------------------------------------------
    def destroy(self):
        self.vao.release()