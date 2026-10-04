"""Tests for DebriefingScreen, combat rank calculation, and mission completion flow."""

import pygame
from eagle1.ui.debriefing_screen import DebriefingScreen


def test_debriefing_screen_ranks():
    """Verify rank evaluation across different score and survival conditions."""
    screen = DebriefingScreen(1280, 720)

    # Rank S: high score or flawless squad with >= 6000
    screen.set_results({"final_score": 11000, "flawless_squad": False, "survivors_count": 2})
    assert screen.rank_letter == "S"
    assert screen.rank_title == "HERO OF SUPER EARTH"

    screen.set_results({"final_score": 6200, "flawless_squad": True, "survivors_count": 4})
    assert screen.rank_letter == "S"

    # Rank A: score >= 6500 or 3+ survivors with >= 4500
    screen.set_results({"final_score": 7000, "flawless_squad": False, "survivors_count": 1})
    assert screen.rank_letter == "A"
    assert screen.rank_title == "CHIEF MARSHAL"

    screen.set_results({"final_score": 4800, "flawless_squad": False, "survivors_count": 3})
    assert screen.rank_letter == "A"

    # Rank B: score >= 3500
    screen.set_results({"final_score": 3800, "flawless_squad": False, "survivors_count": 1})
    assert screen.rank_letter == "B"
    assert screen.rank_title == "PATRIOT VANGUARD"

    # Rank C: low score
    screen.set_results({"final_score": 1200, "flawless_squad": False, "survivors_count": 0})
    assert screen.rank_letter == "C"
    assert screen.rank_title == "COMBAT SURVIVOR"


def test_debriefing_screen_keyboard_events():
    """Verify keyboard shortcuts for replay, mission select, and main menu."""
    screen = DebriefingScreen(1280, 720)
    screen.set_results({"final_score": 5000})

    ev_r = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_r)
    assert screen.handle_event(ev_r) == "replay"

    ev_space = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE)
    assert screen.handle_event(ev_space) == "mission_select"

    ev_esc = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE)
    assert screen.handle_event(ev_esc) == "main_menu"

    ev_other = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_x)
    assert screen.handle_event(ev_other) is None


def test_debriefing_screen_mouse_events():
    """Verify mouse clicks on replay, mission select, and menu buttons."""
    screen = DebriefingScreen(1280, 720)
    screen.set_results({"final_score": 5000})

    # Click Replay button
    click_r = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=screen.btn_replay_rect.center)
    assert screen.handle_event(click_r, mouse_pos=screen.btn_replay_rect.center) == "replay"

    # Click Select button
    click_s = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=screen.btn_select_rect.center)
    assert screen.handle_event(click_s, mouse_pos=screen.btn_select_rect.center) == "mission_select"

    # Click Menu button
    click_m = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=screen.btn_menu_rect.center)
    assert screen.handle_event(click_m, mouse_pos=screen.btn_menu_rect.center) == "main_menu"

    # Click outside buttons
    click_out = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(10, 10))
    assert screen.handle_event(click_out, mouse_pos=(10, 10)) is None


def test_debriefing_screen_draw(dummy_surface):
    """Verify headless rendering of DebriefingScreen without exceptions."""
    screen = DebriefingScreen(1280, 720)
    results = {
        "mission_name": "OUTPOST DEMOLITION",
        "final_score": 8500,
        "highscore": 8500,
        "is_new_highscore": True,
        "duration_seconds": 185.0,
        "waves_cleared": 4,
        "aerial_kills": 24,
        "bomber_kills": 3,
        "fabricators_destroyed": 4,
        "strider_destroyed": True,
        "cas_kills": 12,
        "survivors_count": 4,
        "flawless_squad": True,
        "hero_score": 350,
    }
    screen.set_results(results)
    assert screen.is_active is True
    screen.draw(dummy_surface, mouse_pos=(640, 360))


def test_mission_complete_blocks_simulation():
    """Verify that entering mission debriefing immediately halts move() simulation."""
    import eagle1.app.game as game

    # Save original game state
    orig_state = game.game_state
    orig_pos_x = game.player.pos_x
    orig_health = game.player.health

    try:
        # Trigger mission complete
        game.trigger_mission_complete()
        assert game.game_state == "mission_debriefing"
        assert game.debriefing_screen.is_active is True

        # Call move() - should return immediately without altering player position or taking damage
        game.player.pos_x = 9999.0  # Out of boundary: would normally trigger boundary damage
        game.move()
        assert game.player.health == orig_health
    finally:
        # Restore state
        game.game_state = orig_state
        game.player.pos_x = orig_pos_x
        game.debriefing_screen.is_active = False
