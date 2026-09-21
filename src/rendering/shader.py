# =============================================================================
# SHADER — Reads GLSL files from disk and compiles them into a GPU program
# =============================================================================

import os


class ShaderProgram:
    def __init__(self, ctx):
        self.ctx      = ctx
        self.programs = {}      # dictionary to store all compiled shader programs

    # -------------------------------------------------------------------------
    def load(self, shader_name):
        """
        Reads the .vert and .frag files for a given shader name,
        compiles them, and stores the result.

        shader_name : string matching the filename without extension
                      e.g. 'default' loads default.vert and default.frag
        """
        shader_dir  = os.path.join(os.path.dirname(__file__), '..', 'shaders')
        vert_path   = os.path.join(shader_dir, f'{shader_name}.vert')
        frag_path   = os.path.join(shader_dir, f'{shader_name}.frag')

        with open(vert_path) as f:
            vert_src = f.read()

        with open(frag_path) as f:
            frag_src = f.read()

        # moderngl compiles both shaders and links them into one program
        self.programs[shader_name] = self.ctx.program(
            vertex_shader   = vert_src,
            fragment_shader = frag_src
        )

        return self.programs[shader_name]

    # -------------------------------------------------------------------------
    def __getitem__(self, name):
        # allows you to access programs like: shader['default']
        return self.programs[name]

    # -------------------------------------------------------------------------
    def destroy(self):
        # clean up GPU memory when we're done
        for program in self.programs.values():
            program.release()