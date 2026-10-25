"""Tests for EnlistmentScreen, username typing, contract scrolling, and oath signing."""

import os
from pathlib import Path
import tempfile
import pygame
import pytest

from eagle1.ui.enlistment_screen import EnlistmentScreen, CONTRACT_TEXT
from eagle1.data.player_profile import PlayerProfileManager


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


def test_contract_text_content():
    """Verify that the official Super Earth Contract of Employment clauses are present."""
    assert "CONTRACT OF EMPLOYMENT" in CONTRACT_TEXT
    assert "Helldivers Division of the Super Earth Armed Forces" in CONTRACT_TEXT
    assert "1 SERVICES" in CONTRACT_TEXT
    assert "Super Destroyer" in CONTRACT_TEXT
    assert "2 REMUNERATION" in CONTRACT_TEXT
    assert "4.5 citizenship points" in CONTRACT_TEXT
    assert "3 CONFIDENTIALITY" in CONTRACT_TEXT
    assert "Clause 3.2" in CONTRACT_TEXT
    assert "Clause 3.3" in CONTRACT_TEXT or "breach of Clause 3.2" in CONTRACT_TEXT
    assert "4 INDEMNIFICATION" in CONTRACT_TEXT
    assert "5 TERMINATION" in CONTRACT_TEXT
    assert "6 GENERAL PROVISIONS" in CONTRACT_TEXT
    assert "Clause 6.4" in CONTRACT_TEXT or "1 second within 15 meters" in CONTRACT_TEXT


def test_enlistment_screen_initial_state(temp_profile_env, dummy_surface):
    """Verify default initial state of EnlistmentScreen."""
    screen = EnlistmentScreen(1280, 720)
    assert screen.username == ""
    assert screen.error_message == ""
    assert screen.scroll_offset == 0

    # Headless draw check
    screen.draw(dummy_surface, mouse_pos=(640, 360))


def test_callsign_typing_and_backspace(temp_profile_env):
    """Verify typing characters and backspacing in the callsign input field."""
    screen = EnlistmentScreen(1280, 720)

    # Type "V", "I", "P", "E", "R"
    for char in "VIPER":
        event = pygame.event.Event(pygame.KEYDOWN, key=ord(char.lower()), unicode=char)
        screen.handle_event(event, (640, 360))

    assert screen.username == "VIPER"

    # Backspace once
    bs_event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_BACKSPACE, unicode="")
    screen.handle_event(bs_event, (640, 360))
    assert screen.username == "VIPE"

    # Backspace repeatedly
    for _ in range(10):
        screen.handle_event(bs_event, (640, 360))
    assert screen.username == ""


def test_callsign_max_length(temp_profile_env):
    """Verify that callsign typing enforces the maximum length limit."""
    screen = EnlistmentScreen(1280, 720)
    for char in "A" * 30:
        event = pygame.event.Event(pygame.KEYDOWN, key=ord("a"), unicode="A")
        screen.handle_event(event, (640, 360))

    assert len(screen.username) <= screen.MAX_USERNAME_LENGTH


def test_empty_callsign_rejected(temp_profile_env):
    """Attempting to sign with an empty callsign shows an error and returns None."""
    screen = EnlistmentScreen(1280, 720)
    enter_event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN, unicode="\r")
    action = screen.handle_event(enter_event, (640, 360))

    assert action is None
    assert "CALLSIGN" in screen.error_message.upper()


def test_contract_scrolling(temp_profile_env):
    """Verify mouse wheel and arrow keys scroll the contract container."""
    screen = EnlistmentScreen(1280, 720)
    assert screen.scroll_offset == 0

    # Mouse wheel down
    wheel_event = pygame.event.Event(pygame.MOUSEWHEEL, y=-3, x=0)
    screen.handle_event(wheel_event, (640, 360))
    assert screen.scroll_offset > 0

    # Mouse wheel up
    wheel_up = pygame.event.Event(pygame.MOUSEWHEEL, y=5, x=0)
    screen.handle_event(wheel_up, (640, 360))
    assert screen.scroll_offset == 0


def test_successful_signature_and_profile_creation(temp_profile_env):
    """Signing with valid username creates profile on disk and returns 'start_academy'."""
    manager = PlayerProfileManager()
    assert manager.has_active_profile() is False

    screen = EnlistmentScreen(1280, 720)
    for char in "SKULL-LEADER":
        event = pygame.event.Event(pygame.KEYDOWN, key=ord(char.lower()) if char.isalpha() else 0, unicode=char)
        screen.handle_event(event, (640, 360))

    enter_event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN, unicode="\r")
    action = screen.handle_event(enter_event, (640, 360))

    assert action == "start_academy"
    assert manager.has_active_profile() is True
    profile = manager.load_profile()
    assert profile.username == "SKULL-LEADER"
    assert profile.contract_signed is True
    assert profile.citizenship_grade == "E"
