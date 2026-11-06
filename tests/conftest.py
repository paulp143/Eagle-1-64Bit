"""Pytest fixtures and headless environment configuration for Eagle-1 tests."""

import os
import shutil
import sys
import tempfile
from pathlib import Path
import pytest

# Ensure headless drivers before any pygame import occurs
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

# Redirect all user data (profile, campaign save, audio settings, highscores) to a throwaway
# directory before any game module is imported, so no test can ever touch the real data/ files.
# Tests that need their own isolated directory still override EAGLE1_USER_DATA_DIR via monkeypatch.
_TEST_USER_DATA_DIR = tempfile.mkdtemp(prefix="eagle1-test-data-")
os.environ["EAGLE1_USER_DATA_DIR"] = _TEST_USER_DATA_DIR
os.environ.pop("EAGLE1_DATA_DIR", None)

# Ensure src/ is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pygame


@pytest.fixture(scope="session", autouse=True)
def pygame_session():
    """Initialize pygame once in headless mode for the entire test session."""
    pygame.init()
    if not pygame.font.get_init():
        pygame.font.init()
    # Create a dummy screen surface for rendering tests
    screen = pygame.display.set_mode((1280, 720))
    yield screen
    pygame.quit()
    shutil.rmtree(_TEST_USER_DATA_DIR, ignore_errors=True)


@pytest.fixture
def dummy_surface():
    """Provide a standard 1280x720 surface for testing render methods."""
    return pygame.Surface((1280, 720))
