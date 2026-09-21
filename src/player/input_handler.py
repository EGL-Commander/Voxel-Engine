# =============================================================================
# INPUT HANDLER — Tracks which movement keys are currently held down and the
# mouse's movement this frame. The Camera reads this to know how to move/look.
# =============================================================================

import pygame


class InputHandler:
    # Maps pygame key constants to the simple names Camera.move() checks
    KEY_MAP = {
        pygame.K_w:      'w',
        pygame.K_a:      'a',
        pygame.K_s:      's',
        pygame.K_d:      'd',
        pygame.K_SPACE:  'space',
        pygame.K_LSHIFT: 'shift',
    }

    def __init__(self):
        self.keys = {name: False for name in self.KEY_MAP.values()}
        self.mouse_dx = 0
        self.mouse_dy = 0

    # -------------------------------------------------------------------------
    def handle_keydown(self, key):
        if key in self.KEY_MAP:
            self.keys[self.KEY_MAP[key]] = True

    # -------------------------------------------------------------------------
    def handle_keyup(self, key):
        if key in self.KEY_MAP:
            self.keys[self.KEY_MAP[key]] = False

    # -------------------------------------------------------------------------
    def update_mouse(self):
        """
        pygame.mouse.get_rel() returns how far the mouse moved since the last
        call, then resets to (0, 0). Call this exactly once per frame.
        """
        self.mouse_dx, self.mouse_dy = pygame.mouse.get_rel()
