# =============================================================================
# APP — The main application loop
# Controls the game loop : handle input → update → render → repeat
# =============================================================================

import pygame
import moderngl
from core.window import Window
from core.settings import *


class App(Window):
    def __init__(self):
        super().__init__()
        self.run()

    # -------------------------------------------------------------------------
    def run(self):
        while True:
            self.handle_events()
            self.render()
            pygame.display.flip()       # swap front and back buffer
            self.clock.tick(60)         # cap at 60 frames per second

    # -------------------------------------------------------------------------
    def render(self):
        # Clear the screen with our sky color before drawing anything
        self.ctx.clear(color = BG_COLOR)