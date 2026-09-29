"""Compatibility wrapper for moved module."""

from pathlib import Path
import sys

SRC_DIR = Path(__file__).resolve().parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from eagle1.ui.settings_menu import *  # noqa: F401,F403
