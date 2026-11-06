"""gameplay_settings.py - Persistence for the Settings menu's gameplay toggles.

Stores screen shake, speedometer and low hull/shield warning visibility in
``gameplay_settings.json`` inside the user data directory. Missing or malformed
files fall back to defaults; writes are atomic (temp file + ``os.replace``).
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Dict, Optional

from eagle1.paths import get_user_data_dir

logger = logging.getLogger(__name__)

SETTINGS_FILENAME = "gameplay_settings.json"
DEFAULT_GAMEPLAY_SETTINGS: Dict[str, bool] = {
    "screen_shake": True,
    "show_speedometer": True,
    "show_warnings": True,
}


def _settings_path(data_dir: Optional[Path] = None) -> Path:
    return Path(data_dir if data_dir is not None else get_user_data_dir()) / SETTINGS_FILENAME


def load_gameplay_settings(data_dir: Optional[Path] = None) -> Dict[str, bool]:
    """Return the persisted toggles merged over the defaults (unknown keys and non-bools are ignored)."""
    settings = dict(DEFAULT_GAMEPLAY_SETTINGS)
    path = _settings_path(data_dir)
    try:
        with open(path, "r", encoding="utf-8") as handle:
            loaded = json.load(handle)
    except FileNotFoundError:
        return settings
    except (OSError, ValueError) as exc:
        logger.warning("Could not read %s (%s); using default gameplay settings", path.name, exc)
        return settings
    if isinstance(loaded, dict):
        for key in DEFAULT_GAMEPLAY_SETTINGS:
            if isinstance(loaded.get(key), bool):
                settings[key] = loaded[key]
    return settings


def save_gameplay_settings(settings: Dict[str, bool], data_dir: Optional[Path] = None) -> bool:
    """Atomically write the known toggles; returns False (and logs) when the file cannot be written."""
    path = _settings_path(data_dir)
    payload = {key: bool(settings.get(key, default)) for key, default in DEFAULT_GAMEPLAY_SETTINGS.items()}
    tmp_path = path.with_suffix(".json.tmp")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(tmp_path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=4)
        os.replace(tmp_path, path)
    except OSError as exc:
        logger.warning("Could not save %s: %s", path.name, exc)
        return False
    return True
