"""Tests for the redesigned main menu (keyboard navigation, cached profile state)."""

import os
import tempfile
from pathlib import Path

import pygame
import pytest

from eagle1.app import game
from eagle1.ui.layout import validate_rects_no_overlap


@pytest.fixture
def temp_profile_env():
    with tempfile.TemporaryDirectory() as tmpdir:
        old_env = os.environ.get("EAGLE1_USER_DATA_DIR")
        os.environ["EAGLE1_USER_DATA_DIR"] = tmpdir
        game._menu_profile_state["key"] = None
        yield Path(tmpdir)
        if old_env is not None:
            os.environ["EAGLE1_USER_DATA_DIR"] = old_env
        else:
            os.environ.pop("EAGLE1_USER_DATA_DIR", None)
        game._menu_profile_state["key"] = None


def _key(key):
    return pygame.event.Event(pygame.KEYDOWN, key=key)


def test_main_menu_does_not_parse_profile_every_frame(temp_profile_env, monkeypatch):
    game.profile_manager.clear_profile()
    game.main_menu()

    def _raise():
        raise AssertionError("profile parsed per frame")

    monkeypatch.setattr(game.profile_manager, "load_profile", _raise)
    for _ in range(5):
        game.main_menu()


def test_main_menu_refreshes_after_profile_created(temp_profile_env):
    game.profile_manager.clear_profile()
    game.main_menu()
    assert game.menu_continue_box.enabled is False
    game.profile_manager.create_profile("ACE", citizenship_grade="E")
    game.main_menu()
    assert game.menu_continue_box.enabled is True
    assert "ACE" in game.menu_continue_box.text


def test_main_menu_does_not_touch_the_file_system_per_frame(temp_profile_env, monkeypatch):
    """Once the profile state is known, menu frames neither stat nor parse the profile file."""
    game.profile_manager.create_profile("ACE", citizenship_grade="E")
    game.main_menu()

    def _raise(*args, **kwargs):
        raise AssertionError("profile file touched per frame")

    monkeypatch.setattr(game.profile_manager, "get_profile_path", _raise)
    monkeypatch.setattr(game.profile_manager, "has_active_profile", _raise)
    for _ in range(5):
        game.main_menu()
    assert "ACE" in game.menu_continue_box.text


def test_main_menu_nav_skips_disabled_continue(temp_profile_env):
    game.profile_manager.clear_profile()
    game.main_menu()
    game.main_menu_nav.focus(0)
    game.main_menu_nav.handle_event(_key(pygame.K_DOWN))
    assert game.main_menu_nav.focus_index == 2
    game.main_menu_nav.focus(0)


def test_activate_main_menu_action_quit_returns_true():
    assert game.activate_main_menu_action("quit") is True


def test_activate_main_menu_action_settings_sets_state():
    old_state, old_prev = game.game_state, game.previous_game_state
    try:
        assert game.activate_main_menu_action("settings") is False
        assert game.game_state == "settings_menu"
        assert game.previous_game_state == "main_menu"
    finally:
        game.game_state, game.previous_game_state = old_state, old_prev


def test_main_menu_buttons_do_not_overlap_and_fit_screen():
    rects = [b.rect for b in game.main_menu_nav.buttons]
    assert validate_rects_no_overlap(rects) == []
    screen = pygame.Rect(0, 0, game.GAME_WIDTH, game.GAME_HEIGHT)
    assert all(screen.contains(r) for r in rects)
