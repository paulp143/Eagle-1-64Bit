"""Tests for persisting the Settings menu's gameplay toggles."""

import json

import pygame

from eagle1.ui import gameplay_settings as gs
from eagle1.ui.settings_menu import SettingsMenu


def test_missing_file_returns_defaults(tmp_path):
    assert gs.load_gameplay_settings(tmp_path) == gs.DEFAULT_GAMEPLAY_SETTINGS


def test_malformed_or_partial_file_falls_back_per_key(tmp_path):
    (tmp_path / gs.SETTINGS_FILENAME).write_text("{not json", encoding="utf-8")
    assert gs.load_gameplay_settings(tmp_path) == gs.DEFAULT_GAMEPLAY_SETTINGS
    (tmp_path / gs.SETTINGS_FILENAME).write_text(
        json.dumps({"show_speedometer": False, "show_warnings": "no", "extra": 1}), encoding="utf-8"
    )
    loaded = gs.load_gameplay_settings(tmp_path)
    assert loaded == {"screen_shake": True, "show_speedometer": False, "show_warnings": True}


def test_save_roundtrip_is_atomic_and_leaves_no_temp_file(tmp_path):
    assert gs.save_gameplay_settings({"screen_shake": False, "show_speedometer": True, "show_warnings": False}, tmp_path)
    assert gs.load_gameplay_settings(tmp_path) == {"screen_shake": False, "show_speedometer": True, "show_warnings": False}
    assert [p.name for p in tmp_path.iterdir()] == [gs.SETTINGS_FILENAME]


def test_settings_menu_toggles_survive_restart(tmp_path, monkeypatch):
    monkeypatch.setenv("EAGLE1_USER_DATA_DIR", str(tmp_path))
    menu = SettingsMenu(1280, 720)
    assert menu.toggle_speedometer.state is True
    menu.toggle_speedometer.toggle()
    menu.toggle_warnings.toggle()

    restarted = SettingsMenu(1280, 720)
    assert restarted.toggle_speedometer.state is False
    assert restarted.toggle_warnings.state is False
    assert restarted.toggle_screen_shake.state is True
    pygame.event.clear()
