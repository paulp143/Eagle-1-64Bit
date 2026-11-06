"""Regression tests: timed invincibility (e.g. after the orbital rearm cinematic) must expire."""

import pygame
import pytest

from eagle1.app import game
from eagle1.app.game import MISSION_CONFIGS, MissionType


@pytest.fixture(autouse=True)
def air_superiority(tmp_path, monkeypatch):
    """Fresh Air Superiority sortie with no enemies; restores shared game globals afterwards."""
    monkeypatch.setenv("EAGLE1_USER_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(game, "HIGHSCORE_FILE", str(tmp_path / "highscore.txt"))
    orig_mission = game.active_mission_config
    orig_state = game.game_state

    game.respawn(mission_config=MISSION_CONFIGS[MissionType.AIR_SUPERIORITY])
    game.game_state = ""
    game.wave_manager.enemies.clear()
    game.bomber_enemies.clear()
    p = game.player
    p.pos_x, p.pos_y = 1500.0, 1500.0
    p.x, p.y = 1500, 1500
    p.angle = 0.0

    yield

    game.wave_manager.enemies.clear()
    game.bomber_enemies.clear()
    game.player.invincible = False
    game.player.invincible_timer = 0
    game.active_mission_config = orig_mission
    game.game_state = orig_state


def test_player_starts_without_invincibility_timer():
    p = game.Player()
    assert p.invincible is False
    assert p.invincible_timer == 0


def test_update_invincibility_expires_timed_invincibility():
    p = game.Player()
    p.invincible = True
    p.invincible_timer = 5000
    p.update_invincibility(4999)
    assert p.invincible is True
    p.update_invincibility(5000)
    assert p.invincible is False
    assert p.invincible_timer == 0


def test_update_invincibility_leaves_hit_invincibility_to_its_event():
    """Post-hit i-frames (timer 0) are ended by the INVINCIBLE_END event, not by the timer check."""
    p = game.Player()
    p.invincible = True
    p.invincible_timer = 0
    p.update_invincibility(10_000_000)
    assert p.invincible is True


def test_rearm_invincibility_expires_in_move_and_ramming_damages_again():
    p = game.player
    # State the orbital rearm cinematic leaves behind, with its 1 s window already over.
    p.invincible = True
    p.invincible_timer = max(1, pygame.time.get_ticks() - 1)
    game.move()
    assert p.invincible is False

    shield_before = p.shield
    enemy = game.Light_Enemy(x=p.pos_x, y=p.pos_y - 10)
    enemy.state = "AGRO"
    game.wave_manager.enemies.append(enemy)
    game.move()
    assert p.shield < shield_before


def test_rearm_invincibility_still_active_inside_its_window():
    p = game.player
    p.invincible = True
    p.invincible_timer = pygame.time.get_ticks() + 60_000
    game.move()
    assert p.invincible is True


def test_respawn_clears_invincibility():
    p = game.player
    p.invincible = True
    p.invincible_timer = pygame.time.get_ticks() + 60_000
    game.respawn(mission_config=MISSION_CONFIGS[MissionType.AIR_SUPERIORITY])
    assert p.invincible is False
    assert p.invincible_timer == 0
