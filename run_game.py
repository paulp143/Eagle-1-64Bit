"""Repository-root launcher for Eagle-1."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
SRC_DIR = ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from eagle1.app.game import run_game


if __name__ == "__main__":
    run_game()
