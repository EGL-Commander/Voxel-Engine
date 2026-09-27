#version 330 core

in vec2 v_uv;
in float v_shade;

out vec4 fragColor;

uniform sampler2D u_texture;

void main() {
    vec4 tex_color = texture(u_texture, v_uv);
    // Multiply the actual texture color by the fake directional shade,
    // same trick as the old flat-color version — top faces stay bright,
    // sides and undersides get dimmer, so height changes still read
    // clearly even with real textures now doing most of the work.
    fragColor = vec4(tex_color.rgb * v_shade, tex_color.a);
}
