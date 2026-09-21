#version 330 core

// Per-vertex data coming in from the VBO (see mesh_builder.py)
in vec3 in_position;
in vec3 in_color;

// Passed on to the fragment shader — GPU interpolates this across each triangle
out vec3 v_color;

// Set from Python every frame (see App.update()) — these turn the cube's
// local coordinates into where it actually appears on screen.
uniform mat4 m_proj;    // camera lens: perspective/FOV
uniform mat4 m_view;    // camera position/rotation
uniform mat4 m_model;   // where this object sits in the world

void main() {
    v_color = in_color;

    // Order matters: model -> view -> projection
    gl_Position = m_proj * m_view * m_model * vec4(in_position, 1.0);
}
