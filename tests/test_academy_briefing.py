"""Tests for AcademyTutorialManager, waypoint gates, drill progression, and Commander Vance comms."""

import os
from pathlib import Path
import tempfile
import pygame
import pytest

from eagle1.systems.academy_briefing import (
    AcademyTutorialManager,
    AcademyWaypointGate,
    AcademyTargetDrone,
    AcademyTargetBunker,
    CommsHUDBox,
    DRILL_BRIEFING,
    DRILL_STEERING,
    DRILL_THROTTLE,
    DRILL_BORDER_SAFETY,
    DRILL_CANNONS,
    DRILL_RADAR_ROCKETS,
    DRILL_STRATAGEM,
    DRILL_GRADUATION,
    DRILL_COMPLETE,
)


class MockPlayer:
    """Mock Player object for headless academy testing."""
    def __init__(self, x=1500.0, y=1500.0):
        self.pos_x = float(x)
        self.pos_y = float(y)
        self.x = int(x)
        self.y = int(y)
        self.angle = 0.0
        self.velocity_x = 0.0
        self.velocity_y = 4.0
        self.speed = 4.0
        self.score = 0
        self.health = 5.0
        self.max_health = 5.0
        self.shield = 20.0
        self.used_bullets = 0
        self.max_bullets = 200
        self.bullets = []
        self.rockets = []
        self.radar_mode = "CONE"

    def get_forward_speed(self):
        import math
        return math.hypot(self.velocity_x, self.velocity_y)


def test_academy_manager_initial_state():
    """Verify default initial state of AcademyTutorialManager."""
    manager = AcademyTutorialManager()
    assert manager.state == DRILL_BRIEFING
    assert manager.is_completed is False
    assert manager.graduated is False
    assert "BRIEFING" in manager.get_active_drill_title().upper()
    assert "VANCE" in manager.comms_box.speaker_title.upper()


def test_waypoint_gate_collision():
    """Verify AcademyWaypointGate detection and radius checks."""
    gate = AcademyWaypointGate(x=1500.0, y=1500.0, radius=80.0, label="ALPHA")
    assert gate.cleared is False

    # Miss: too far
    assert gate.check_collision(1200.0, 1200.0) is False
    assert gate.cleared is False

    # Hit: inside gate radius
    assert gate.check_collision(1520.0, 1510.0) is True
    assert gate.cleared is True


def test_target_drone_damage_and_destruction():
    """Verify target drone takes damage and is destroyed."""
    drone = AcademyTargetDrone(x=1000.0, y=1000.0, max_health=50.0, label="DRONE-1")
    assert drone.is_alive is True

    drone.take_damage(20.0)
    assert drone.health == 30.0
    assert drone.is_alive is True

    drone.take_damage(35.0)
    assert drone.health <= 0.0
    assert drone.is_alive is False


def test_target_bunker_damage_and_destruction():
    """Verify target bunker takes air strike damage."""
    bunker = AcademyTargetBunker(x=1200.0, y=1200.0, max_health=100.0, label="TARGET FOUNDRY")
    assert bunker.is_alive is True

    bunker.take_damage(120.0)
    assert bunker.health <= 0.0
    assert bunker.is_alive is False


def test_drill_state_advancement_sequence():
    """Verify sequential advancement through all academy drills."""
    manager = AcademyTutorialManager()
    player = MockPlayer()

    assert manager.state == DRILL_BRIEFING
    manager.advance_drill(player)
    assert manager.state == DRILL_STEERING
    manager.advance_drill(player)
    assert manager.state == DRILL_THROTTLE
    manager.advance_drill(player)
    assert manager.state == DRILL_BORDER_SAFETY
    manager.advance_drill(player)
    assert manager.state == DRILL_CANNONS
    manager.advance_drill(player)
    assert manager.state == DRILL_RADAR_ROCKETS
    manager.advance_drill(player)
    assert manager.state == DRILL_STRATAGEM
    manager.advance_drill(player)
    assert manager.state == DRILL_GRADUATION
    manager.advance_drill(player)
    assert manager.state == DRILL_COMPLETE
    assert manager.is_completed is True


def test_throttle_drill_evaluation():
    """Verify throttle accumulator advances when high and low speed thresholds are maintained."""
    manager = AcademyTutorialManager()
    player = MockPlayer()
    manager.state = DRILL_THROTTLE

    # Simulate fast throttle (v = 7.0)
    player.velocity_y = 7.0
    keys = {pygame.K_w: True, pygame.K_s: False}

    # Step for 2.1 seconds at 60 FPS
    for _ in range(130):
        manager.update_throttle_drill(dt=1.0 / 60.0, player=player)

    assert manager.throttle_high_completed is True

    # Simulate air brakes / slow throttle (v = 2.0)
    player.velocity_y = 2.0
    for _ in range(130):
        manager.update_throttle_drill(dt=1.0 / 60.0, player=player)

    assert manager.throttle_low_completed is True


def test_headless_world_and_hud_draw(dummy_surface):
    """Verify draw_world and draw_hud execute cleanly in headless environment."""
    manager = AcademyTutorialManager()
    player = MockPlayer()
    manager.reset(player)

    manager.draw_world(dummy_surface, camera_x=0, camera_y=0)
    manager.draw_hud(dummy_surface, player=player)
