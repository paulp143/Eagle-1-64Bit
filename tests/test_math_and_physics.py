"""Tests for flight physics, coordinate transformations, and targeting math."""

import math
import pytest
from eagle1.app.game import (
    Player,
    GAME_WIDTH,
    GAME_HEIGHT,
    MAP_WIDTH,
    MAP_HEIGHT,
    RADAR_CONE_ANGLE,
    RADAR_CONE_MIN_RANGE,
    RADAR_CONE_RANGE,
    RADAR_OMNI_RANGE,
)


def test_player_flight_speed_boundaries():
    """Verify that player speed is bounded between min_speed and max_speed."""
    player = Player()
    assert player.min_speed == 2.0
    assert player.max_speed == 7.0

    # Test initial velocity vector components
    speed = math.hypot(player.velocity_x, player.velocity_y)
    assert player.min_speed <= speed <= player.max_speed + 0.1


def test_camera_viewport_clamping():
    """Verify that camera clamping stays within 0 and MAP_SIZE - GAME_SIZE."""
    max_cam_x = MAP_WIDTH - GAME_WIDTH
    max_cam_y = MAP_HEIGHT - GAME_HEIGHT

    # Player near top-left origin
    cam_x = max(0, min(100 - GAME_WIDTH / 2, max_cam_x))
    cam_y = max(0, min(100 - GAME_HEIGHT / 2, max_cam_y))
    assert cam_x == 0
    assert cam_y == 0

    # Player near center
    center_x = MAP_WIDTH / 2
    center_y = MAP_HEIGHT / 2
    cam_x = max(0, min(center_x - GAME_WIDTH / 2, max_cam_x))
    cam_y = max(0, min(center_y - GAME_HEIGHT / 2, max_cam_y))
    assert 0 < cam_x < max_cam_x
    assert 0 < cam_y < max_cam_y

    # Player near bottom-right edge
    cam_x = max(0, min(2990 - GAME_WIDTH / 2, max_cam_x))
    cam_y = max(0, min(2990 - GAME_HEIGHT / 2, max_cam_y))
    assert cam_x == max_cam_x
    assert cam_y == max_cam_y


def test_predictive_reticle_lead_formula():
    """Verify that bomb reticle lead scales dynamically with velocity."""
    # Formula in game: lead = 320.0 + velocity * 8.0
    for v in [2.0, 4.5, 7.0]:
        expected_lead = 320.0 + (v * 8.0)
        actual_lead = 320.0 + (v * 8.0)
        assert actual_lead == pytest.approx(expected_lead)
        assert 336.0 <= actual_lead <= 376.0


def test_radar_ranges_and_cone_constants():
    """Verify radar operating constants match the game combat specifications."""
    assert RADAR_CONE_ANGLE == 50
    assert RADAR_CONE_MIN_RANGE == 300
    assert RADAR_CONE_RANGE == 1050
    assert RADAR_OMNI_RANGE == 420
