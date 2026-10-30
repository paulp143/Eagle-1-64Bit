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


def test_debriefing_screen_hub_return_and_button_layout():
    """Verify hub return via hotkeys/clicks and ensure zero button layout overlaps."""
    from eagle1.ui.layout import validate_rects_no_overlap

    screen = DebriefingScreen(1280, 720)
    screen.set_results({"final_score": 5000})

    # Keyboard hotkey H
    ev_h = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_h)
    assert screen.handle_event(ev_h) == "super_destroyer"

    # Keyboard hotkey RETURN
    ev_ret = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN)
    assert screen.handle_event(ev_ret) == "super_destroyer"

    # Mouse click on Return to Hub button
    click_hub = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=screen.btn_hub_rect.center)
    assert screen.handle_event(click_hub, mouse_pos=screen.btn_hub_rect.center) == "super_destroyer"

    # Verify zero layout overlap across all 4 navigation buttons
    buttons = [
        screen.btn_replay_rect,
        screen.btn_hub_rect,
        screen.btn_select_rect,
        screen.btn_menu_rect,
    ]
    overlaps = validate_rects_no_overlap(buttons)
    assert overlaps == [], f"Detected button overlaps: {overlaps}"

    # Verify all buttons remain strictly inside panel_rect
    for btn in buttons:
        assert screen.panel_rect.contains(btn), f"Button {btn} falls outside panel {screen.panel_rect}"


def test_debriefing_screen_sanitization_and_nan_inf_handling():
    """Verify set_results defensively sanitizes None, NaN, Inf, and non-numeric fields."""
    screen = DebriefingScreen()

    # Scenario A: None payload
    screen.set_results(None)
    assert screen.is_active is True
    assert screen.results["final_score"] == 0
    assert screen.results["duration_seconds"] == 0.0

    # Scenario B: NaN / Inf / string values
    screen.set_results({
        "final_score": None,
        "highscore": "invalid",
        "duration_seconds": float("nan"),
        "waves_cleared": -5,
        "survivors_count": 99,
        "casualties_count": -3,
        "hull_ratio": float("inf"),
    })
    assert screen.results["final_score"] == 0
    assert screen.results["highscore"] == 0
    assert screen.results["duration_seconds"] == 0.0
    assert screen.results["waves_cleared"] == 1
    assert screen.results["survivors_count"] == 4
    assert screen.results["casualties_count"] == 0
    assert screen.results["hull_ratio"] == 0.0

    # Verify draw() does not crash with sanitized edge values
    surface = pygame.Surface((1280, 720))
    screen.draw(surface)

    # Verify close() deactivates screen
    screen.close()
    assert screen.is_active is False

