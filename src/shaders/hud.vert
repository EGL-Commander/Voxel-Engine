#version 330 core

// A flat 2D quad drawn directly in screen space (NDC), textured with the
// pre-rendered text image — see rendering/hud.py.
in vec2 in_position;
in vec2 in_uv;

out vec2 v_uv;

void main() {
    v_uv = in_uv;
    gl_Position = vec4(in_position, 0.0, 1.0);
}
