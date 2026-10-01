"""Tests for data persistence: high score reading/writing and audio settings fallback."""

import json
from eagle1.app.game import load_highscore, add_highscore
from eagle1.systems.audio_manager import AudioManager, DEFAULT_SETTINGS


def test_highscore_io_with_temp_file(tmp_path):
    """Verify high score saves and loads correctly without touching real data."""
    test_file = tmp_path / "test_highscore.txt"

    # Non-existent file returns 0
    assert load_highscore(filepath=str(test_file)) == 0

    # Save and reload
    add_highscore(4250, filepath=str(test_file))
    assert load_highscore(filepath=str(test_file)) == 4250

    # Corrupted content falls back to 0
    test_file.write_text("corrupted_score_text")
    assert load_highscore(filepath=str(test_file)) == 0


def test_audio_settings_fallback_on_missing_file(tmp_path):
    """Verify audio settings gracefully fall back to defaults when file is missing."""
    am = AudioManager()
    am.settings_file = str(tmp_path / "non_existent_settings.json")
    settings = am._load_settings()

    assert settings["master_volume"] == DEFAULT_SETTINGS["master_volume"]
    assert settings["sfx_volume"] == DEFAULT_SETTINGS["sfx_volume"]
    assert settings["music_volume"] == DEFAULT_SETTINGS["music_volume"]
    assert settings["is_muted"] == DEFAULT_SETTINGS["is_muted"]


def test_audio_settings_partial_keys(tmp_path):
    """Verify audio settings handle missing keys gracefully by merging with defaults."""
    settings_file = tmp_path / "partial_settings.json"
    settings_file.write_text(json.dumps({"master_volume": 0.35}))

    am = AudioManager()
    am.settings_file = str(settings_file)
    settings = am._load_settings()

    assert settings["master_volume"] == 0.35
    assert settings["music_volume"] == DEFAULT_SETTINGS["music_volume"]
