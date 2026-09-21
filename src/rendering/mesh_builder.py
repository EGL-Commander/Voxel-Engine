# =============================================================================
# MESH BUILDER — For now, builds a test triangle to confirm the pipeline works
# This file will later handle voxel chunk geometry
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