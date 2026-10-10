"""Tests for macOS display scaling, letterboxing, mouse coordinate mapping, and system integration."""

from unittest.mock import patch
import pygame

from eagle1.app.game import get_display_scale_and_offset, get_canvas_mouse_pos, GAME_WIDTH, GAME_HEIGHT



def test_display_scale_and_offset_standard_16_9():
    """Verify standard 16:9 resolutions scale uniformly with zero offset."""
    with patch("eagle1.app.game.window") as mock_window:
        mock_window.get_size.return_value = (1280, 720)
        scale, offset_x, offset_y, scaled_w, scaled_h = get_display_scale_and_offset()
        assert scale == 1.0
        assert offset_x == 0
        assert offset_y == 0
        assert scaled_w == 1280
        assert scaled_h == 720


def test_display_scale_and_offset_macbook_16_10():
    """Verify 16:10 MacBook screens (e.g. 1440x900, 2560x1600) letterbox properly."""
    with patch("eagle1.app.game.window") as mock_window:
        mock_window.get_size.return_value = (1440, 900)
        scale, offset_x, offset_y, scaled_w, scaled_h = get_display_scale_and_offset()
        # 1440 / 1280 = 1.125; 900 / 720 = 1.25; scale should be min -> 1.125
        assert abs(scale - 1.125) < 1e-4
        assert scaled_w == 1440
        assert scaled_h == int(720 * 1.125)  # 810
        assert offset_x == 0
        assert offset_y == (900 - 810) // 2  # 45 px letterbox bar top & bottom


def test_canvas_mouse_pos_mapping():
    """Verify mouse coordinates map accurately from letterboxed window to canvas coordinates."""
    with patch("eagle1.app.game.window") as mock_window, \
         patch("pygame.mouse.get_pos") as mock_mouse:

        # Case 1: Standard 1280x720 window
        mock_window.get_size.return_value = (1280, 720)
        mock_mouse.return_value = (640, 360)
        cx, cy = get_canvas_mouse_pos()
        assert cx == 640.0
        assert cy == 360.0

        # Case 2: Letterboxed 1440x900 window
        # Center of canvas is at (640, 360) -> on 1440x900 window it is at (640 * 1.125, 360 * 1.125 + 45) = (720, 450)
        mock_window.get_size.return_value = (1440, 900)
        mock_mouse.return_value = (720, 450)
        cx, cy = get_canvas_mouse_pos()
        assert abs(cx - 640.0) < 1.0
        assert abs(cy - 360.0) < 1.0


def test_canvas_mouse_pos_clamping_in_letterbox_margin():
    """Verify mouse hovering in black letterbox borders is clamped to canvas boundaries."""
    with patch("eagle1.app.game.window") as mock_window, \
         patch("pygame.mouse.get_pos") as mock_mouse:

        # Mouse in top letterbox bar (y = 10, offset_y = 45)
        mock_window.get_size.return_value = (1440, 900)
        mock_mouse.return_value = (720, 10)
        cx, cy = get_canvas_mouse_pos()
        assert cx == 640.0
        assert cy == 0.0  # Clamped to top border
