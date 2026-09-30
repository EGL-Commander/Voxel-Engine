#version 330 core

in vec2 v_uv;
out vec4 fragColor;

uniform sampler2D u_texture;

void main() {
    // Keep the texture's alpha (not forced to 1.0) so the panel is
    // semi-transparent and the text edges are anti-aliased over the world.
    fragColor = texture(u_texture, v_uv);
}
