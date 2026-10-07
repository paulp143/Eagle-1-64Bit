"""Repository-relative and platform-aware paths for Eagle-1 assets and user data."""

import os
from pathlib import Path
import sys


def get_base_dir() -> Path:
    """Return the base directory for bundled assets.

    In a PyInstaller frozen application, assets are unpacked into sys._MEIPASS.
    In development / source mode, assets reside at the project root.
    """
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    # src/eagle1/paths.py -> parents[2] is project root
    return Path(__file__).resolve().parents[2]


PROJECT_ROOT = get_base_dir()
IMAGES_DIR = PROJECT_ROOT / "images"
ASSET_IMAGES_DIR = PROJECT_ROOT / "assets" / "images"
AUDIO_DIR = PROJECT_ROOT / "audio"
ASSET_AUDIO_DIR = PROJECT_ROOT / "assets" / "audio"
DATA_DIR = PROJECT_ROOT / "data"


def get_user_data_dir() -> Path:
    """Return the writable user data directory following platform standards.

    - Linux / BSD: $XDG_DATA_HOME/Eagle-1 or ~/.local/share/Eagle-1
    - macOS: ~/Library/Application Support/Eagle-1
    - Windows: %APPDATA%/Eagle-1 or fallback to data/ directory

    In development / source runs, if the local 'data/' directory exists and is writable,
    it is preferred to keep development workflows self-contained.
    """
    # Explicit override (useful for tests and headless automation)
    env_override = os.environ.get("EAGLE1_USER_DATA_DIR")
    if env_override:
        p = Path(env_override)
        p.mkdir(parents=True, exist_ok=True)
        return p

    # If running from source (not frozen) and local data dir exists, keep using local data dir
    if not getattr(sys, "frozen", False):
        local_data = Path(__file__).resolve().parents[2] / "data"
        if local_data.exists():
            return local_data

    # Frozen or installed mode: use OS standard app data directories
    if sys.platform.startswith("win"):
        appdata = os.environ.get("APPDATA")
        base = Path(appdata) if appdata else Path.home() / "AppData" / "Roaming"
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        # Linux and other UNIX systems (XDG Base Directory Specification)
        xdg_data = os.environ.get("XDG_DATA_HOME")
        base = Path(xdg_data) if xdg_data else Path.home() / ".local" / "share"

    user_dir = base / "Eagle-1"
    try:
        user_dir.mkdir(parents=True, exist_ok=True)
    except Exception:
        # Fallback to local data dir if standard directory is inaccessible
        return DATA_DIR
    return user_dir


def image_search_dirs():
    return [IMAGES_DIR, ASSET_IMAGES_DIR]


def audio_search_dirs():
    return [AUDIO_DIR, ASSET_AUDIO_DIR]
