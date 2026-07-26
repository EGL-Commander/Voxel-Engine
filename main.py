# =============================================================================
# MAIN — Entry point. This is the only file you ever run.
# =============================================================================

import sys
import os

# Make sure Python can find our src folder
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from core.app import App

if __name__ == '__main__':
    App()