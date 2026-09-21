#version 330 core

// 'in' means this data comes IN from the vertex buffer we send from Python
// location = 0 means this is attribute slot 0
in vec3 in_position;

void main() {
    // gl_Position is a built-in variable — this is what the GPU uses
    // to know where on screen this vertex lands
    // vec4 means 4 values : x, y, z, w
    // w = 1.0 always for a regular 3D point
    gl_Position = vec4(in_position, 1.0);
}