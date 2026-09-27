#version 330 core

in vec3 in_position;
in vec3 in_color;

out vec3 v_color;

void main() {
    v_color = in_color;
    gl_Position = vec4(in_position, 1.0);
}
