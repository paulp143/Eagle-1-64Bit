"""Tests for Story Mode Main Menu and TextBox enabled/disabled states."""

import os
from pathlib import Path
import tempfile
import pygame
import pytest

from eagle1.app.game import (
    TextBox,
    menu_new_game_box,
    menu_continue_box,
    main_menu,
    safe_font,
    profile_manager,
)


@pytest.fixture
def temp_profile_env():
    """Isolate player profile directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        old_env = os.environ.get("EAGLE1_USER_DATA_DIR")
        os.environ["EAGLE1_USER_DATA_DIR"] = tmpdir
        yield Path(tmpdir)
        if old_env is not None:
            os.environ["EAGLE1_USER_DATA_DIR"] = old_env
        else:
            os.environ.pop("EAGLE1_USER_DATA_DIR", None)


def test_textbox_enabled_disabled_behavior():
    """Verify TextBox disabled state rejects hover and click interactions."""
    font = safe_font("arial", 20)
    box = TextBox(
        "CONTINUE",
        font,
        enabled=False,
        centerx=640,
        centery=360,
    )

    hitbox = box.get_hitbox()
    click_pos = hitbox.center

    # Disabled box should not register hover or clicks
    assert box.is_hovered(click_pos) is False

    click_event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=click_pos)
    assert box.is_clicked(click_event, click_pos) is False

    # Enable box and verify click interaction resumes
    box.set_enabled(True)
    assert box.is_hovered(click_pos) is True
    assert box.is_clicked(click_event, click_pos) is True


def test_main_menu_first_time_state(temp_profile_env, dummy_surface):
    """On first launch with no profile, CONTINUE is disabled with notice."""
    profile_manager.clear_profile()
    assert profile_manager.has_active_profile() is False

    # Render main menu
    main_menu(mouse_pos=(640, 350))

    assert menu_continue_box.enabled is False
    assert "NO SERVICE RECORD" in menu_continue_box.text

    # Continue box should reject clicks when disabled
    click_event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(640, 350))
    assert menu_continue_box.is_clicked(click_event, (640, 350)) is False

    # New game button should remain enabled and clickable
    assert menu_new_game_box.enabled is True


def test_main_menu_active_profile_state(temp_profile_env, dummy_surface):
    """When an active profile exists, CONTINUE is enabled with pilot callsign."""
    profile_manager.create_profile("VIPER-LEAD", citizenship_grade="E")
    assert profile_manager.has_active_profile() is True

    # Render main menu
    main_menu(mouse_pos=(640, 350))

    assert menu_continue_box.enabled is True
    assert "VIPER-LEAD" in menu_continue_box.text

    hitbox = menu_continue_box.get_hitbox()
    click_event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=hitbox.center)
    assert menu_continue_box.is_clicked(click_event, hitbox.center) is True

