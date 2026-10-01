"""Pytest fixtures and headless environment configuration for Eagle-1 tests."""

import os
import sys
from pathlib import Path
import pytest

# Ensure headless drivers before any pygame import occurs
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

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


@pytest.fixture
def dummy_surface():
    """Provide a standard 1280x720 surface for testing render methods."""
    return pygame.Surface((1280, 720))
