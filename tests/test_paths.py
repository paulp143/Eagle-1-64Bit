"""Tests for cross-platform path resolution and user data directories."""

from pathlib import Path
import sys
from eagle1.paths import (
    get_base_dir,
    get_user_data_dir,
    image_search_dirs,
    audio_search_dirs,
    IMAGES_DIR,
    AUDIO_DIR,
)


def test_get_base_dir_development():
    """Verify get_base_dir returns the project root during normal development execution."""
    base = get_base_dir()
    assert (base / "src" / "eagle1").is_dir()
    assert (base / "images").is_dir()


def test_get_base_dir_frozen_pyinstaller(monkeypatch, tmp_path):
    """Verify get_base_dir properly respects sys._MEIPASS when running in a PyInstaller bundle."""
    fake_meipass = tmp_path / "pyinstaller_bundle"
    fake_meipass.mkdir()

    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(fake_meipass), raising=False)

    base = get_base_dir()
    assert base == fake_meipass


def test_get_user_data_dir_development():
    """In development mode with existing data directory, get_user_data_dir returns local data directory."""
    user_data = get_user_data_dir()
    assert user_data.exists()
    assert user_data.name == "data"


def test_get_user_data_dir_frozen_linux(monkeypatch, tmp_path):
    """Simulate frozen application on Linux, asserting XDG standard directory is used."""
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "platform", "linux")
    fake_xdg = tmp_path / "xdg_share"
    monkeypatch.setenv("XDG_DATA_HOME", str(fake_xdg))

    user_data = get_user_data_dir()
    assert user_data == fake_xdg / "Eagle-1"
    assert user_data.is_dir()


def test_get_user_data_dir_frozen_macos(monkeypatch, tmp_path):
    """Simulate frozen application on macOS, asserting Library/Application Support is used."""
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "platform", "darwin")
    fake_home = tmp_path / "fake_mac_home"
    monkeypatch.setattr(Path, "home", lambda: fake_home)

    user_data = get_user_data_dir()
    expected = fake_home / "Library" / "Application Support" / "Eagle-1"
    assert user_data == expected
    assert user_data.is_dir()


def test_get_user_data_dir_frozen_windows(monkeypatch, tmp_path):
    """Simulate frozen application on Windows, asserting %APPDATA% directory is used."""
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "platform", "win32")
    fake_appdata = tmp_path / "fake_appdata"
    monkeypatch.setenv("APPDATA", str(fake_appdata))

    user_data = get_user_data_dir()
    assert user_data == fake_appdata / "Eagle-1"
    assert user_data.is_dir()


def test_search_dirs_include_primary():
    """Verify search dirs return expected base asset directories."""
    img_dirs = image_search_dirs()
    assert IMAGES_DIR in img_dirs

    snd_dirs = audio_search_dirs()
    assert AUDIO_DIR in snd_dirs


def test_get_user_data_dir_env_override(monkeypatch, tmp_path):
    """Verify EAGLE1_USER_DATA_DIR env variable overrides all defaults."""
    custom_dir = tmp_path / "custom_data_dir"
    monkeypatch.setenv("EAGLE1_USER_DATA_DIR", str(custom_dir))

    user_data = get_user_data_dir()
    assert user_data == custom_dir
    assert user_data.is_dir()
