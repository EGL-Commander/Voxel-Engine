#version 330 core

// Per-vertex data from the VBO (see chunk.py's build_mesh)
in vec3 in_position;
in vec2 in_uv;       // where in the texture atlas this vertex samples from
in float in_shade;   // fake directional lighting: top faces brighter, etc.

out vec2 v_uv;
out float v_shade;

uniform mat4 m_proj;
uniform mat4 m_view;
uniform mat4 m_model;

void main() {
    v_uv = in_uv;
    v_shade = in_shade;
    gl_Position = m_proj * m_view * m_model * vec4(in_position, 1.0);
}
