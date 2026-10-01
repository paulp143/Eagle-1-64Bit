"""Repository-relative paths for Eagle-1 assets and data."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
IMAGES_DIR = PROJECT_ROOT / "images"
ASSET_IMAGES_DIR = PROJECT_ROOT / "assets" / "images"
AUDIO_DIR = PROJECT_ROOT / "audio"
ASSET_AUDIO_DIR = PROJECT_ROOT / "assets" / "audio"
DATA_DIR = PROJECT_ROOT / "data"


def image_search_dirs():
    return [IMAGES_DIR, ASSET_IMAGES_DIR]


def audio_search_dirs():
    return [AUDIO_DIR, ASSET_AUDIO_DIR]
