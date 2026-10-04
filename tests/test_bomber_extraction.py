"""Tests verifying that bomber waves must be fully repelled before extraction is possible."""

from eagle1.app.game import (
    MISSION_CONFIGS,
    MissionType,
    BomberEnemy,
    SCORE_EXTRACTION_BONUS,
    respawn,
)
import eagle1.app.game as game


def test_bomber_waves_do_not_activate_beacon_early():
    """Verify that clearing wave 3 in a bomber mission does NOT prematurely activate the extraction beacon."""
    config = MISSION_CONFIGS[MissionType.BASE_DEFENSE]
    respawn(config)

    assert game.active_mission_config["has_bombers"] is True
    assert game.ground_support_manager.beacon.active is False

    # Simulate clearing wave 1, 2, 3
    for w in range(1, 4):
        game.wave_manager.wave = w
        game.ground_support_manager.on_wave_cleared(w, game.player)
        # Extraction beacon must remain FALSE while bomber waves remain
        assert game.ground_support_manager.beacon.active is False
        assert game.ground_support_manager.objective_phase != "EXTRACTION"


def test_bombers_still_spawning_blocks_extraction():
    """Verify that even if a beacon were somehow active, extraction is blocked while bombers are spawning."""
    config = MISSION_CONFIGS[MissionType.BASE_DEFENSE]
    respawn(config)

    # Force beacon active early at wave 2
    game.wave_manager.wave = 2
    game.wave_manager.state = "ACTIVE"
    game.ground_support_manager.beacon.active = True
    game.ground_support_manager.beacon.pelican_departed = False

    # Spawn an active bomber
    bomber = BomberEnemy(1500, 1500)
    game.bomber_enemies.append(bomber)

    # Position player directly inside the extraction beacon
    bx = game.ground_support_manager.beacon.x
    by = game.ground_support_manager.beacon.y
    game.player.pos_x = bx - game.PLAYER_WIDTH / 2
    game.player.pos_y = by - game.PLAYER_HEIGHT / 2

    # Run move()
    game.move()

    # Extraction MUST be blocked because bombers are still active/spawning
    assert game.ground_support_manager.beacon.pelican_departed is False
    assert game.ground_support_manager.objective_phase != "COMPLETE"
    assert game.game_state != "mission_debriefing"


def test_extraction_activates_and_succeeds_when_bombers_no_longer_spawning():
    """Verify that after all 5 bomber waves are repelled, the extraction beacon activates and Eagle-1 can extract."""
    config = MISSION_CONFIGS[MissionType.BASE_DEFENSE]
    respawn(config)

    # Fast forward to final wave (Wave 5)
    game.wave_manager.wave = 5
    game.wave_manager.state = "INTERMISSION"
    game.wave_manager.intermission_timer = 0  # Force timer expired
    game.bomber_enemies.clear()

    score_before = game.player.score

    # Update wave manager: next_wave will be 6 > max_waves (5)
    game.wave_manager.update(game.player)

    # Bombers are no longer spawning!
    assert game.wave_manager.state == "COMPLETE"
    assert game.ground_support_manager.beacon.active is True
    assert game.ground_support_manager.objective_phase == "EXTRACTION"
    assert game.player.score >= score_before + 1500

    # Player flies to extraction beacon
    bx = game.ground_support_manager.beacon.x
    by = game.ground_support_manager.beacon.y
    game.player.pos_x = bx - game.PLAYER_WIDTH / 2
    game.player.pos_y = by - game.PLAYER_HEIGHT / 2

    score_pre_extract = game.player.score
    game.move()

    # Extraction must succeed now that bombers are no longer spawning
    assert game.ground_support_manager.beacon.pelican_departed is True
    assert game.ground_support_manager.objective_phase == "COMPLETE"
    assert game.player.score == score_pre_extract + SCORE_EXTRACTION_BONUS
    assert game.game_state == "mission_debriefing"
    assert game.debriefing_screen.is_active is True

    # Clean up game state
    game.game_state = "main_menu"
    game.debriefing_screen.is_active = False


def test_endless_war_allows_wave_3_extraction():
    """Verify that Endless War (no bombers) still activates extraction beacon at wave 3 as an optional extraction."""
    config = MISSION_CONFIGS[MissionType.ENDLESS_WAR]
    respawn(config)

    assert game.active_mission_config["has_bombers"] is False
    assert game.ground_support_manager.beacon.active is False

    # Waves 1 and 2: no beacon
    game.ground_support_manager.on_wave_cleared(1, game.player)
    assert game.ground_support_manager.beacon.active is False
    game.ground_support_manager.on_wave_cleared(2, game.player)
    assert game.ground_support_manager.beacon.active is False

    # Wave 3: beacon activates
    game.ground_support_manager.on_wave_cleared(3, game.player)
    assert game.ground_support_manager.beacon.active is True
    assert game.ground_support_manager.objective_phase == "EXTRACTION"
