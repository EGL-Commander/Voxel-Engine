#version 330 core

// 'out' means this is what we're outputting — the final pixel color
out vec4 fragColor;

void main() {
    // vec4 is RGBA — red, green, blue, alpha
    // all values between 0.0 and 1.0
    // this makes every pixel of our triangle white
    fragColor = vec4(1.0, 1.0, 1.0, 1.0);
}