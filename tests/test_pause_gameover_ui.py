"""Tests for the redesigned pause menu and game-over screen."""

import inspect

import pygame

from eagle1.app import game
from eagle1.ui.layout import validate_rects_no_overlap


def test_pause_snapshot_reused_across_frames():
    game._pause_snapshot_valid = False
    game.canvas.fill((255, 0, 0))
    game.pause_menu()
    game.canvas.fill((0, 0, 255))
    game.pause_menu()
    assert tuple(game.pause_snapshot_surf.get_at((5, 5)))[:3] == (255, 0, 0)
    game._pause_snapshot_valid = False


def test_gameplay_draw_invalidates_pause_snapshot():
    game.respawn()
    game._pause_snapshot_valid = True
    game.draw((640, 360))
    assert game._pause_snapshot_valid is False


def test_pause_resume_action_sets_gameplay_state():
    old_state = game.game_state
    try:
        game.game_state = "pause_menu"
        game.activate_pause_action("resume")
        assert game.game_state == ""
        game.activate_pause_action("settings")
        assert game.game_state == "settings_menu"
        assert game.previous_game_state == "pause_menu"
    finally:
        game.game_state = old_state
        game.previous_game_state = "main_menu"


def _inside(panel, rects):
    return all(panel.contains(r) for r in rects) and validate_rects_no_overlap(rects) == []


def test_pause_buttons_inside_panel_no_overlap():
    assert _inside(game.pause_panel_rect, [b.rect for b in game.pause_nav.buttons])


def test_gameover_buttons_inside_panel_no_overlap():
    assert _inside(game.gameover_panel_rect, [b.rect for b in game.gameover_nav.buttons])


def test_no_per_frame_mute_polling():
    assert "keys[pygame.K_m]" not in inspect.getsource(game.run_game)


def test_pause_navigation_enter_returns_resume_index():
    game.pause_nav.focus(0)
    ev = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN)
    assert game.pause_nav.handle_event(ev) == 0
