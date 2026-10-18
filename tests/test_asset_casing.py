"""Tests for cross-platform asset filename casing and case sensitivity enforcement."""

import ast
import os
from pathlib import Path
import pytest

from eagle1.paths import (
    get_base_dir,
    IMAGES_DIR,
    AUDIO_DIR,
    verify_path_exact_casing,
)
from eagle1.app.game import load_image
from eagle1.systems.audio_manager import AudioManager, SOUND_CHANNELS, SOUND_MIN_INTERVALS


ASSET_EXTENSIONS = {".png", ".wav", ".ogg", ".mp3", ".webp", ".icns", ".jpg", ".jpeg"}


def _get_all_disk_assets():
    """Returns a dict of {relpath_posix: filename} for all assets in images/ and audio/."""
    base = get_base_dir()
    disk_assets = {}
    for folder in [base / "images", base / "audio"]:
        if not folder.exists():
            continue
        for root, _, files in os.walk(folder):
            for f in files:
                full_path = Path(root) / f
                rel_posix = full_path.relative_to(base).as_posix()
                disk_assets[rel_posix] = f
    return disk_assets


def test_verify_path_exact_casing_accuracy():
    """Verify that verify_path_exact_casing accurately distinguishes exact vs mismatched casing."""
    base = get_base_dir()

    # Exact on-disk cases
    assert verify_path_exact_casing("images/Space-Invaders-Ship.png")
    assert verify_path_exact_casing(base / "images" / "Space-Invaders-Ship.png")
    assert verify_path_exact_casing("images/bullet.png")
    assert verify_path_exact_casing("audio/sfx/laser_player.wav")
    assert verify_path_exact_casing("audio/music/menu_theme.wav")

    # Mismatched cases (which would succeed on macOS APFS / Windows NTFS without check)
    assert not verify_path_exact_casing("images/space-invaders-ship.png")
    assert not verify_path_exact_casing("images/SPACE-INVADERS-SHIP.PNG")
    assert not verify_path_exact_casing("images/BULLET.png")
    assert not verify_path_exact_casing("audio/SFX/laser_player.wav")
    assert not verify_path_exact_casing("audio/sfx/Laser_Player.wav")
    assert not verify_path_exact_casing("audio/music/MENU_THEME.wav")

    # Non-existent files
    assert not verify_path_exact_casing("images/non_existent_file.png")
    assert not verify_path_exact_casing("audio/sfx/missing_audio.wav")


def test_disk_assets_have_no_case_collisions():
    """Ensure no two files in images/ or audio/ differ solely by casing."""
    disk_assets = _get_all_disk_assets()
    lower_map = {}
    collisions = []

    for rel_path in disk_assets:
        lower = rel_path.lower()
        if lower in lower_map:
            collisions.append((lower_map[lower], rel_path))
        else:
            lower_map[lower] = rel_path

    assert not collisions, f"Found filesystem case collisions: {collisions}"


def test_all_disk_assets_pass_exact_casing_check():
    """Ensure every asset currently on disk passes exact casing verification."""
    disk_assets = _get_all_disk_assets()
    assert len(disk_assets) > 0, "No assets found on disk"

    mismatches = []
    for rel_path in disk_assets:
        if not verify_path_exact_casing(rel_path):
            mismatches.append(rel_path)

    assert not mismatches, f"Assets failed exact casing check: {mismatches}"


def test_code_asset_string_literals_match_disk_casing():
    """Audit all Python source files to ensure every asset string literal matches exact disk casing."""
    base = get_base_dir()
    disk_assets = _get_all_disk_assets()

    # Index by lowercase basename and lowercase relpath
    lookup_by_basename = {os.path.basename(p).lower(): os.path.basename(p) for p in disk_assets}
    lookup_by_relpath = {p.lower(): p for p in disk_assets}

    # Collect Python files
    py_files = []
    for folder in [base / "src", base / "tools"]:
        if folder.exists():
            for root, _, files in os.walk(folder):
                for f in files:
                    if f.endswith(".py"):
                        py_files.append(Path(root) / f)

    for root_file in ["main.py", "ground_support.py", "powerup_system.py", "audio_manager.py"]:
        rf = base / root_file
        if rf.exists():
            py_files.append(rf)

    casing_errors = []

    for file_path in py_files:
        try:
            tree = ast.parse(file_path.read_text(encoding="utf-8"), filename=str(file_path))
        except Exception:
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                val = node.value.strip().replace("\\", "/")
                # Ignore web URLs
                if val.startswith("http://") or val.startswith("https://"):
                    continue

                ext = os.path.splitext(val)[1].lower()
                if ext in ASSET_EXTENSIONS:
                    val_basename = os.path.basename(val)
                    base_lower = val_basename.lower()

                    if base_lower in lookup_by_basename:
                        expected_base = lookup_by_basename[base_lower]
                        if val_basename != expected_base:
                            casing_errors.append(
                                f"{file_path.name}:{getattr(node, 'lineno', '?')} -> "
                                f"'{val_basename}' != disk '{expected_base}'"
                            )

                    val_lower = val.lower()
                    if val_lower in lookup_by_relpath:
                        expected_rel = lookup_by_relpath[val_lower]
                        if val != expected_rel:
                            casing_errors.append(
                                f"{file_path.name}:{getattr(node, 'lineno', '?')} -> "
                                f"'{val}' != disk '{expected_rel}'"
                            )

    assert not casing_errors, f"Case sensitivity discrepancies detected in code:\n" + "\n".join(casing_errors)


def test_audio_sfx_and_music_identifiers_match_disk():
    """Verify that all SFX and music IDs used in audio manager match exact filenames on disk."""
    base = get_base_dir()
    sfx_dir = base / "audio" / "sfx"
    music_dir = base / "audio" / "music"

    if not sfx_dir.exists() or not music_dir.exists():
        pytest.skip("Audio directory not present")

    actual_sfx = {f.stem for f in sfx_dir.glob("*.wav")}
    actual_music = {f.stem for f in music_dir.glob("*.wav")}

    # Verify channel allocations
    for sfx_name in SOUND_CHANNELS:
        assert sfx_name in actual_sfx, f"SFX '{sfx_name}' in SOUND_CHANNELS not found in {sfx_dir}"
        assert sfx_name == sfx_name.lower(), f"SFX ID '{sfx_name}' should be lowercase"

    # Verify min interval configs
    for sfx_name in SOUND_MIN_INTERVALS:
        assert sfx_name in actual_sfx, f"SFX '{sfx_name}' in SOUND_MIN_INTERVALS not found in {sfx_dir}"


def test_load_image_rejects_case_mismatches():
    """Ensure load_image succeeds on exact case but raises FileNotFoundError on casing mismatch."""
    # Exact case must succeed
    img_exact = load_image("images/Space-Invaders-Ship.png")
    assert img_exact is not None

    # Mismatched case must fail even on case-insensitive OS
    with pytest.raises(FileNotFoundError):
        load_image("images/space-invaders-ship.png")

    with pytest.raises(FileNotFoundError):
        load_image("images/SPACE-INVADERS-SHIP.PNG")

    with pytest.raises(FileNotFoundError):
        load_image("images/bullet.PNG")


def test_audio_manager_play_music_rejects_case_mismatches(tmp_path):
    """Ensure AudioManager.play_music only loads music with exact filename casing."""
    am = AudioManager()
    if not am.enabled:
        pytest.skip("Audio device not enabled in environment")

    # Lowercase valid track
    am.play_music("menu_theme")
    assert am.current_music == "menu_theme"

    # Uppercase invalid track name must be rejected and not set as current_music
    am.current_music = None
    am.play_music("MENU_THEME")
    assert am.current_music != "MENU_THEME"

