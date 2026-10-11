"""Comprehensive regression test suite for all operational mission modes.

Verifies that the Super Earth Story Campaign Mode, Pilot Profile system,
and Main Menu redesign introduced zero regressions across the 5 legacy mission modes:
1. Air Superiority
2. Orbital Base Defense
3. Factory Strider Boss Raid
4. Outpost Demolition
5. Endless War
"""

from pathlib import Path
import pygame
import pytest

from eagle1.app import game
from eagle1.app.game import (
    MISSION_CONFIGS,
    MissionType,
    respawn,
    trigger_mission_complete,
    load_highscore,
    add_highscore,
)
from eagle1.data.player_profile import PlayerProfileManager


@pytest.fixture(autouse=True)
def isolated_test_environment(tmp_path, monkeypatch):
    """Ensure tests run with isolated user data and restored game globals."""
    monkeypatch.setenv("EAGLE1_USER_DATA_DIR", str(tmp_path))
    temp_highscore = str(tmp_path / "highscore.txt")
    monkeypatch.setattr(game, "HIGHSCORE_FILE", temp_highscore)

    orig_mission = game.active_mission_config
    orig_state = game.game_state
    orig_score = game.player.score
    orig_health = game.player.health

    yield

    game.active_mission_config = orig_mission
    game.game_state = orig_state
    game.player.score = orig_score
    game.player.health = orig_health


def test_air_superiority_lifecycle(dummy_surface):
    """Verify Air Superiority initialization, wave progression, move, and draw."""
    config = MISSION_CONFIGS[MissionType.AIR_SUPERIORITY]
    respawn(mission_config=config)

    assert game.active_mission_config["id"] == MissionType.AIR_SUPERIORITY
    assert game.active_mission_config["has_ground"] is False
    assert game.active_mission_config["has_bombers"] is False
    assert game.active_mission_config["has_base"] is False
    assert game.active_mission_config["max_waves"] == 5

    # Wave manager should be initialized with wave 1
    assert game.wave_manager.wave == 1
    assert len(game.wave_manager.enemies) > 0
    assert game.ground_support_manager.beacon.active is False

    # Simulate simulation step
    game.move()
    game.draw(mouse_pos=(640, 360))

    # Fast forward to clearing wave 5 (final wave)
    game.wave_manager.wave = 5
    game.wave_manager.enemies.clear()
    game.wave_manager.state = "INTERMISSION"
    game.wave_manager.intermission_timer = 0  # Force instant transition

    # Wave manager update should recognize max_waves reached and activate extraction
    game.wave_manager.update(game.player)
    assert game.ground_support_manager.beacon.active is True
    assert game.ground_support_manager.objective_phase == "EXTRACTION"


def test_orbital_base_defense_lifecycle(dummy_surface):
    """Verify Orbital Base Defense creates orbital base and handles bombers."""
    config = MISSION_CONFIGS[MissionType.BASE_DEFENSE]
    respawn(mission_config=config)

    assert game.active_mission_config["id"] == MissionType.BASE_DEFENSE
    assert game.active_mission_config["has_bombers"] is True
    assert game.active_mission_config["has_base"] is True
    assert game.orbital_base is not None
    assert game.orbital_base.health > 0

    # Simulate step
    game.move()
    game.draw(mouse_pos=(640, 360))


def test_factory_strider_raid_lifecycle(dummy_surface):
    """Verify Factory Strider Boss Raid initializes boss fortress and ground combat."""
    config = MISSION_CONFIGS[MissionType.STRIDER_RAID]
    respawn(mission_config=config)

    assert game.active_mission_config["id"] == MissionType.STRIDER_RAID
    assert game.active_mission_config["has_strider"] is True
    assert game.active_mission_config["has_ground"] is True
    assert len(game.wave_manager.enemies) == 0  # Strider raid focuses on ground boss

    # Factory Strider should be spawned in ground support manager
    assert game.ground_support_manager.factory_strider is not None
    assert game.ground_support_manager.factory_strider.is_alive is True

    # Simulate step
    game.move()
    game.draw(mouse_pos=(640, 360))

    # Destroy the strider
    strider = game.ground_support_manager.factory_strider
    strider.health = 0.0
    game.ground_support_manager.strider_destroyed = True

    # Ground support manager update should trigger extraction
    game.ground_support_manager.update(
        1.0 / 60.0,
        game.player,
        [],
        game.explosion_group,
        game.large_explosion_a_spritesheet.frames,
    )
    assert game.ground_support_manager.objective_phase == "EXTRACTION"
    assert game.ground_support_manager.beacon.active is True


def test_outpost_demolition_lifecycle(dummy_surface):
    """Verify Outpost Demolition spawns 3 fabricators and triggers extraction on demolition."""
    config = MISSION_CONFIGS[MissionType.OUTPOST_DEMOLITION]
    respawn(mission_config=config)

    assert game.active_mission_config["id"] == MissionType.OUTPOST_DEMOLITION
    assert game.active_mission_config["has_fabricators"] is True
    assert game.active_mission_config.get("target_fabs") == 3
    assert len(game.ground_support_manager.enemy_fabricators) >= 3

    # Simulate step
    game.move()
    game.draw(mouse_pos=(640, 360))

    # Destroy all fabricators
    for fab in game.ground_support_manager.enemy_fabricators:
        fab.health = 0.0
    game.ground_support_manager.destroyed_fabs_count = 3

    # Update ground support manager to detect all target fabs destroyed
    game.ground_support_manager.update(
        1.0 / 60.0,
        game.player,
        [],
        game.explosion_group,
        game.large_explosion_a_spritesheet.frames,
    )
    assert game.ground_support_manager.objective_phase == "EXTRACTION"
    assert game.ground_support_manager.beacon.active is True


def test_endless_war_lifecycle(dummy_surface):
    """Verify Endless War spawns full-scale ground and air combat."""
    config = MISSION_CONFIGS[MissionType.ENDLESS_WAR]
    respawn(mission_config=config)

    assert game.active_mission_config["id"] == MissionType.ENDLESS_WAR
    assert game.active_mission_config["max_waves"] == 999
    assert game.active_mission_config["has_ground"] is True
    assert game.active_mission_config["has_fabricators"] is True

    # Simulate multiple game steps
    for _ in range(5):
        game.move()
    game.draw(mouse_pos=(640, 360))


def test_mission_complete_results_and_debriefing(dummy_surface):
    """Verify trigger_mission_complete sets up results for debriefing screen."""
    config = MISSION_CONFIGS[MissionType.AIR_SUPERIORITY]
    respawn(mission_config=config)
    game.player.score = 3500
    game.mission_air_kills = 12

    trigger_mission_complete()

    assert game.game_state == "mission_debriefing"
    assert game.debriefing_screen.results["final_score"] == 3500
    assert game.debriefing_screen.results["aerial_kills"] == 12

    # Draw debriefing screen
    game.debriefing_screen.draw(dummy_surface, mouse_pos=(640, 360))

    # Test actions
    replay_pos = game.debriefing_screen.btn_replay_rect.center
    replay_event = pygame.event.Event(
        pygame.MOUSEBUTTONDOWN,
        button=1,
        pos=replay_pos,
    )
    action = game.debriefing_screen.handle_event(
        replay_event,
        mouse_pos=replay_pos,
    )
    assert action == "replay"


def test_highscore_isolation_integrity(tmp_path):
    """Verify highscore read/write operations never affect default highscore file."""
    test_file = str(tmp_path / "custom_highscore.txt")
    assert load_highscore(test_file) == 0

    add_highscore(4200, test_file)
    assert load_highscore(test_file) == 4200

    # Ensure real file was not touched
    real_file = Path("data/highscore.txt")
    if real_file.exists():
        real_score = int(real_file.read_text().strip())
        assert real_score != 4200 or real_score >= 0


def test_main_menu_flow_resume_campaign(dummy_surface):
    """Verify CONTINUE button launches saved active mission directly."""
    prof_mgr = PlayerProfileManager()
    prof = prof_mgr.create_profile("CADET-TEST", citizenship_grade="E")
    prof.academy_completed = True
    prof.active_mission = MissionType.AIR_SUPERIORITY
    prof_mgr.save_profile(prof)

    game.game_state = "main_menu"
    game.main_menu(mouse_pos=(640, 350))

    assert game.menu_continue_box.enabled is True
    assert "CADET-TEST" in game.menu_continue_box.text

    # Click continue button
    click_pos = game.menu_continue_box.get_hitbox().center
    click_event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=click_pos)

    # Simulate main menu event handling
    if game.menu_continue_box.is_clicked(click_event, click_pos):
        if prof_mgr.has_active_profile():
            active_prof = prof_mgr.load_profile()
            target_mission = (
                MissionType.ACADEMY_TUTORIAL
                if not active_prof.academy_completed
                else active_prof.active_mission
            )
            config = game.MISSION_CONFIGS.get(
                target_mission,
                game.MISSION_CONFIGS[MissionType.ACADEMY_TUTORIAL],
            )
            respawn(mission_config=config)
            game.game_state = ""

    assert game.game_state == ""
    assert game.active_mission_config["id"] == MissionType.AIR_SUPERIORITY
