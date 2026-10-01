"""Compatibility wrapper for moved module."""

from pathlib import Path
import sys

SRC_DIR = Path(__file__).resolve().parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from tools.generate_audio_assets import *  # noqa: F401,F403
from tools.generate_audio_assets import generate_all


if __name__ == "__main__":
    generate_all()
