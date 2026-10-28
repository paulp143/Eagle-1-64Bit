"""Tests for SuperDestroyerView core layout, viewport and Patriotism Index HUD (Issue #57)."""

import os
from unittest.mock import MagicMock, patch
import pygame
import pytest

from eagle1.story import (
    HUB_ZONES,
    PATRIOTISM_COLOR_DISSIDENT,
    PATRIOTISM_COLOR_NOMINAL,
    PATRIOTISM_COLOR_ZEALOT,
    PATRIOTISM_LABEL_DISSIDENT,
    PATRIOTISM_LABEL_NOMINAL,
    PATRIOTISM_LABEL_ZEALOT,
    ZONE_BRIDGE,
    ZONE_HANGAR,
    ZONE_METADATA,
    ZONE_READY_ROOM,
    CampaignSaveManager,
    StoryManager,
    SuperDestroyerView,
)


@pytest.fixture(autouse=True)
def headless_pygame():
    """Ensure headless pygame initialization for all tests."""
    old_video = os.environ.get("SDL_VIDEODRIVER")
    old_audio = os.environ.get("SDL_AUDIODRIVER")
    os.environ["SDL_VIDEODRIVER"] = "dummy"
    os.environ["SDL_AUDIODRIVER"] = "dummy"
    pygame.init()
    if not pygame.font.get_init():
        pygame.font.init()
    yield
    if old_video is not None:
        os.environ["SDL_VIDEODRIVER"] = old_video
    else:
        os.environ.pop("SDL_VIDEODRIVER", None)
    if old_audio is not None:
        os.environ["SDL_AUDIODRIVER"] = old_audio
    else:
        os.environ.pop("SDL_AUDIODRIVER", None)


@pytest.fixture
def story_mgr(tmp_path):
    """Provide a StoryManager instance isolated in tmp_path."""
    save_mgr = CampaignSaveManager(data_dir=tmp_path)
    return StoryManager(save_manager=save_mgr)


def test_super_destroyer_view_initializes_in_bridge_zone(story_mgr):
    """Verify SuperDestroyerView initializes in Bridge zone with cached surfaces."""
    view = SuperDestroyerView(story_manager=story_mgr)
    assert view.active_zone == ZONE_BRIDGE
    assert HUB_ZONES == (ZONE_BRIDGE, ZONE_READY_ROOM, ZONE_HANGAR)
    assert ZONE_BRIDGE in ZONE_METADATA
    assert ZONE_READY_ROOM in ZONE_METADATA
    assert ZONE_HANGAR in ZONE_METADATA

    # Verify cached surfaces are pre-allocated
    assert isinstance(view.orbital_bg_surface, pygame.Surface)
    assert view.orbital_bg_surface.get_size() == (1280, 720)
    assert isinstance(view.top_hud_bg_surface, pygame.Surface)
    assert isinstance(view.content_panel_bg_surface, pygame.Surface)
    assert isinstance(view.footer_bg_surface, pygame.Surface)


def test_patriotism_index_ratio_and_status_colors_across_thresholds(story_mgr):
    """Verify Patriotism Index ratio and status colors across defined thresholds."""
    view = SuperDestroyerView(story_manager=story_mgr)

    # Zealot state (>= 90.0)
    story_mgr.loyalty = 90.0
    assert view.get_patriotism_bar_ratio() == pytest.approx(0.9, rel=1e-4)
    label, color = view.get_patriotism_status_label_and_color()
    assert label == PATRIOTISM_LABEL_ZEALOT
    assert color == PATRIOTISM_COLOR_ZEALOT

    story_mgr.loyalty = 100.0
    assert view.get_patriotism_bar_ratio() == pytest.approx(1.0, rel=1e-4)
    label, color = view.get_patriotism_status_label_and_color()
    assert label == PATRIOTISM_LABEL_ZEALOT
    assert color == PATRIOTISM_COLOR_ZEALOT

    # Nominal state (15.0 < loyalty < 90.0)
    story_mgr.loyalty = 89.9
    assert view.get_patriotism_bar_ratio() == pytest.approx(0.899, rel=1e-4)
    label, color = view.get_patriotism_status_label_and_color()
    assert label == PATRIOTISM_LABEL_NOMINAL
    assert color == PATRIOTISM_COLOR_NOMINAL

    story_mgr.loyalty = 50.0
    assert view.get_patriotism_bar_ratio() == pytest.approx(0.5, rel=1e-4)
    label, color = view.get_patriotism_status_label_and_color()
    assert label == PATRIOTISM_LABEL_NOMINAL
    assert color == PATRIOTISM_COLOR_NOMINAL

    story_mgr.loyalty = 15.1
    assert view.get_patriotism_bar_ratio() == pytest.approx(0.151, rel=1e-4)
    label, color = view.get_patriotism_status_label_and_color()
    assert label == PATRIOTISM_LABEL_NOMINAL
    assert color == PATRIOTISM_COLOR_NOMINAL

    # Dissident state (<= 15.0)
    story_mgr.loyalty = 15.0
    assert view.get_patriotism_bar_ratio() == pytest.approx(0.15, rel=1e-4)
    label, color = view.get_patriotism_status_label_and_color()
    assert label == PATRIOTISM_LABEL_DISSIDENT
    assert color == PATRIOTISM_COLOR_DISSIDENT

    story_mgr.loyalty = 0.0
    assert view.get_patriotism_bar_ratio() == pytest.approx(0.0, rel=1e-4)
    label, color = view.get_patriotism_status_label_and_color()
    assert label == PATRIOTISM_LABEL_DISSIDENT
    assert color == PATRIOTISM_COLOR_DISSIDENT


def test_patriotism_index_clamps_out_of_range_and_nan_values(story_mgr):
    """Verify Patriotism Index clamps invalid or out-of-range loyalty cleanly."""
    view = SuperDestroyerView(story_manager=story_mgr)

    # Sub-zero
    story_mgr.loyalty = -25.0
    assert view.get_patriotism_bar_ratio() == 0.0

    # Over 100
    story_mgr.loyalty = 140.0
    assert view.get_patriotism_bar_ratio() == 1.0

    # NaN
    story_mgr.loyalty = float("nan")
    assert view.get_patriotism_bar_ratio() == 0.0

    # Inf
    story_mgr.loyalty = float("inf")
    assert view.get_patriotism_bar_ratio() == 1.0

    # -Inf
    story_mgr.loyalty = -float("inf")
    assert view.get_patriotism_bar_ratio() == 0.0


def test_zone_cycling_wraps_around_forward_and_backward(story_mgr):
    """Verify cycle_zone wraps around forward and backward across all 3 zones."""
    view = SuperDestroyerView(story_manager=story_mgr)
    assert view.active_zone == ZONE_BRIDGE

    # Forward cycling
    assert view.cycle_zone(1) == ZONE_READY_ROOM
    assert view.cycle_zone(1) == ZONE_HANGAR
    assert view.cycle_zone(1) == ZONE_BRIDGE

    # Backward cycling
    assert view.cycle_zone(-1) == ZONE_HANGAR
    assert view.cycle_zone(-1) == ZONE_READY_ROOM
    assert view.cycle_zone(-1) == ZONE_BRIDGE

    # Zero or invalid direction returns current active zone without change
    assert view.cycle_zone(0) == ZONE_BRIDGE
    assert view.cycle_zone(True) == ZONE_BRIDGE  # type: ignore


def test_select_zone_by_id_and_index_and_reject_invalid(story_mgr):
    """Verify select_zone handles strings, ints, whitespace and rejects invalid inputs."""
    view = SuperDestroyerView(story_manager=story_mgr)

    # Valid string identifiers
    assert view.select_zone("ready_room") is True
    assert view.active_zone == ZONE_READY_ROOM

    assert view.select_zone("  HANGAR  ") is True
    assert view.active_zone == ZONE_HANGAR

    # Valid integer index
    assert view.select_zone(0) is True
    assert view.active_zone == ZONE_BRIDGE

    # Invalid string identifier
    assert view.select_zone("engine_room") is False
    assert view.active_zone == ZONE_BRIDGE

    # Invalid integer indices
    assert view.select_zone(-1) is False
    assert view.select_zone(99) is False
    assert view.active_zone == ZONE_BRIDGE

    # Boolean input guard
    assert view.select_zone(True) is False
    assert view.select_zone(False) is False
    assert view.active_zone == ZONE_BRIDGE


def test_keyboard_navigation_ad_arrows_direct_keys_and_escape(story_mgr):
    """Verify handle_event supports A/D, arrows, direct numbers and ESC."""
    view = SuperDestroyerView(story_manager=story_mgr)
    assert view.active_zone == ZONE_BRIDGE

    # 'D' cycles forward
    event_d = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_d)
    res = view.handle_event(event_d)
    assert res == {"action": "select_zone", "zone": ZONE_READY_ROOM}
    assert view.active_zone == ZONE_READY_ROOM

    # Right arrow cycles forward
    event_right = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RIGHT)
    res = view.handle_event(event_right)
    assert res == {"action": "select_zone", "zone": ZONE_HANGAR}
    assert view.active_zone == ZONE_HANGAR

    # 'A' cycles backward
    event_a = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_a)
    res = view.handle_event(event_a)
    assert res == {"action": "select_zone", "zone": ZONE_READY_ROOM}
    assert view.active_zone == ZONE_READY_ROOM

    # Left arrow cycles backward
    event_left = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_LEFT)
    res = view.handle_event(event_left)
    assert res == {"action": "select_zone", "zone": ZONE_BRIDGE}
    assert view.active_zone == ZONE_BRIDGE

    # Direct number 3 selects HANGAR
    event_3 = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_3)
    res = view.handle_event(event_3)
    assert res == {"action": "select_zone", "zone": ZONE_HANGAR}
    assert view.active_zone == ZONE_HANGAR

    # Direct number 1 selects BRIDGE
    event_1 = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_1)
    res = view.handle_event(event_1)
    assert res == {"action": "select_zone", "zone": ZONE_BRIDGE}
    assert view.active_zone == ZONE_BRIDGE

    # ESC returns main_menu action
    event_esc = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE)
    res = view.handle_event(event_esc)
    assert res == {"action": "main_menu"}


def test_mouse_click_and_hover_on_zone_tabs(story_mgr):
    """Verify mouse motion sets hovered_zone and click selects zone tab."""
    audio_mock = MagicMock()
    view = SuperDestroyerView(story_manager=story_mgr, audio_manager=audio_mock)

    ready_tab_rect = view.zone_tab_rects[ZONE_READY_ROOM]
    hover_pos = (ready_tab_rect.centerx, ready_tab_rect.centery)

    # Mouse motion hover
    motion_event = pygame.event.Event(pygame.MOUSEMOTION, pos=hover_pos)
    view.handle_event(motion_event)
    assert view.hovered_zone == ZONE_READY_ROOM
    audio_mock.play_sfx.assert_called_with("ui_hover")

    # Mouse click selection
    audio_mock.reset_mock()
    click_event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=hover_pos)
    res = view.handle_event(click_event)
    assert res == {"action": "select_zone", "zone": ZONE_READY_ROOM}
    assert view.active_zone == ZONE_READY_ROOM
    audio_mock.play_sfx.assert_called_with("ui_click")

    # Click on Hangar tab
    hangar_tab_rect = view.zone_tab_rects[ZONE_HANGAR]
    click_hangar = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=hangar_tab_rect.center)
    res = view.handle_event(click_hangar)
    assert res == {"action": "select_zone", "zone": ZONE_HANGAR}
    assert view.active_zone == ZONE_HANGAR


def test_draw_executes_without_per_frame_surface_allocations(story_mgr):
    """Verify draw() runs cleanly and does not allocate pygame.Surface in per-frame render loop."""
    view = SuperDestroyerView(story_manager=story_mgr)
    target_surface = pygame.Surface((1280, 720))

    # Warmup frame to establish initial caches
    view.update(1.0 / 60.0)
    view.draw(target_surface, mouse_pos=(200, 100))

    # Monitor Surface creation during subsequent frames
    allocated_surfaces = []
    real_surface_cls = pygame.Surface

    def tracking_surface(*args, **kwargs):
        allocated_surfaces.append(args)
        return real_surface_cls(*args, **kwargs)

    with patch("eagle1.story.super_destroyer_view.pygame.Surface", side_effect=tracking_surface):
        for _ in range(60):
            view.update(1.0 / 60.0)
            view.draw(target_surface, mouse_pos=(200, 100))

    # Assert no dynamic surfaces allocated during steady-state rendering
    assert len(allocated_surfaces) == 0, f"Detected unexpected surface allocations: {allocated_surfaces}"
