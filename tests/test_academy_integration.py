"""Integration tests for Academy Tutorial Mission loop in game.py."""

import os
from pathlib import Path
import tempfile
import pygame
import pytest

from eagle1.app import game
from eagle1.systems.academy_briefing import (
    AcademyTutorialManager,
    DRILL_BRIEFING,
    DRILL_STEERING,
    DRILL_THROTTLE,
    DRILL_CANNONS,
    DRILL_RADAR_ROCKETS,
    DRILL_STRATAGEM,
    DRILL_GRADUATION,
    DRILL_COMPLETE,
)
from eagle1.data.player_profile import PlayerProfileManager, PlayerProfile


@pytest.fixture(autouse=True)
def clean_game_state(monkeypatch, tmp_path):
    """Isolate user profile and restore game states."""
    old_env = os.environ.get("EAGLE1_USER_DATA_DIR")
    os.environ["EAGLE1_USER_DATA_DIR"] = str(tmp_path)
    
    # Save active state
    orig_mission = game.active_mission_config
    orig_state = game.game_state
    
    yield
    
    game.active_mission_config = orig_mission
    game.game_state = orig_state
    if old_env is not None:
        os.environ["EAGLE1_USER_DATA_DIR"] = old_env
    else:
        os.environ.pop("EAGLE1_USER_DATA_DIR", None)


def test_academy_respawn_initialization():
    """Verify respawn() cleanly prepares Academy tutorial state."""
    config = game.MISSION_CONFIGS[game.MissionType.ACADEMY_TUTORIAL]
    game.respawn(mission_config=config)

    assert game.active_mission_config["id"] == game.MissionType.ACADEMY_TUTORIAL
    assert len(game.wave_manager.enemies) == 0
    assert game.academy_manager.state == DRILL_BRIEFING
    assert game.academy_manager.is_completed is False
    assert len(game.academy_manager.waypoint_gates) == 3


def test_bullet_damage_to_academy_drones():
    """Verify player bullets collide with and damage training drones."""
    config = game.MISSION_CONFIGS[game.MissionType.ACADEMY_TUTORIAL]
    game.respawn(mission_config=config)
    
    # Force advance to cannons drill
    game.academy_manager.state = DRILL_CANNONS
    game.academy_manager.advance_drill(game.player)
    # Re-set to CANNONS with fresh drones
    game.academy_manager.state = DRILL_CANNONS
    drone = game.academy_manager.target_drones[0]
    initial_health = drone.health

    # Spawn a bullet right over the drone
    bullet = game.Player.Bullet(drone.x + 10, drone.y + 10, 0.0)
    game.player.bullets.append(bullet)

    # Run move()
    game.move()

    assert bullet.used is True
    assert drone.health < initial_health


def test_rocket_damage_to_academy_drones():
    """Verify player rockets collide with and damage training drones."""
    config = game.MISSION_CONFIGS[game.MissionType.ACADEMY_TUTORIAL]
    game.respawn(mission_config=config)
    
    # Setup radar rockets drill
    game.academy_manager.state = DRILL_RADAR_ROCKETS
    drone = game.academy_manager.target_drones[0] if game.academy_manager.target_drones else None
    if not drone:
        from eagle1.systems.academy_briefing import AcademyTargetDrone
        drone = AcademyTargetDrone(game.player.pos_x, game.player.pos_y - 200.0, max_health=50.0)
        game.academy_manager.target_drones = [drone]

    initial_health = drone.health

    # Spawn a rocket directly at drone
    rocket = game.Player.Rocket(drone.x + 5, drone.y + 5, 0.0, target=drone)
    game.player.rockets.append(rocket)

    # Run move()
    game.move()

    assert rocket.used is True
    assert drone.health < initial_health


def test_stratagem_air_strike_destroys_academy_bunker():
    """Verify active stratagem air strikes damage the training foundry bunker."""
    config = game.MISSION_CONFIGS[game.MissionType.ACADEMY_TUTORIAL]
    game.respawn(mission_config=config)
    
    game.academy_manager.state = DRILL_STRATAGEM
    from eagle1.systems.academy_briefing import AcademyTargetBunker
    game.academy_manager.target_bunker = AcademyTargetBunker(1500.0, 1000.0, max_health=100.0)

    # Deploy stratagem near bunker
    hit = game.academy_manager.on_stratagem_deployed(1500.0, 1000.0, radius=300.0, damage=200.0)
    assert hit is True
    assert game.academy_manager.target_bunker.is_alive is False


def test_academy_completion_triggers_debriefing():
    """Verify that when academy is completed, trigger_mission_complete is fired."""
    config = game.MISSION_CONFIGS[game.MissionType.ACADEMY_TUTORIAL]
    game.respawn(mission_config=config)
    game.game_state = ""

    # Set academy to completion
    game.academy_manager.state = DRILL_GRADUATION
    game.academy_manager.advance_drill(game.player)
    assert game.academy_manager.is_completed is True

    # Run move()
    game.move()

    assert game.game_state == "mission_debriefing"


def test_academy_draw_world_and_hud(dummy_surface):
    """Verify headless drawing of Academy world and HUD overlay."""
    config = game.MISSION_CONFIGS[game.MissionType.ACADEMY_TUTORIAL]
    game.respawn(mission_config=config)

    # Run draw without exception
    game.draw(mouse_pos=(640, 360))
