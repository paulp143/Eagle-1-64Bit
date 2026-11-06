"""Tests for the radar lock zones: CONE (long forward sector) and OMNI (short wide forward arc)."""

import math

from eagle1.app import game


def _player(mode):
    p = game.Player()
    p.pos_x, p.pos_y = 1000.0, 1000.0
    p.x, p.y = 1000, 1000
    p.angle = 0.0
    p.radar_mode = mode
    return p


def _enemy_at(player, distance, deviation_deg):
    """Light_Enemy whose center sits `distance` px from the player center, `deviation_deg` off the nose."""
    pcx = player.pos_x + game.PLAYER_WIDTH / 2
    pcy = player.pos_y + game.PLAYER_HEIGHT / 2
    rad = math.radians(deviation_deg)
    ecx = pcx - math.sin(rad) * distance
    ecy = pcy - math.cos(rad) * distance
    return game.Light_Enemy(x=ecx - game.LIGHT_ENEMY_WIDTH / 2, y=ecy - game.LIGHT_ENEMY_HEIGHT / 2)


def test_omni_locks_target_ahead():
    p = _player("OMNI")
    assert p.is_enemy_in_lock_zone(_enemy_at(p, 200, 0))


def test_omni_locks_target_at_60_degrees():
    p = _player("OMNI")
    assert p.is_enemy_in_lock_zone(_enemy_at(p, 200, 60))
    assert p.is_enemy_in_lock_zone(_enemy_at(p, 200, -60))


def test_omni_rejects_target_behind():
    p = _player("OMNI")
    assert not p.is_enemy_in_lock_zone(_enemy_at(p, 200, 180))


def test_omni_rejects_target_at_100_degrees():
    p = _player("OMNI")
    assert not p.is_enemy_in_lock_zone(_enemy_at(p, 200, 100))
    assert not p.is_enemy_in_lock_zone(_enemy_at(p, 200, -100))


def test_omni_rejects_target_beyond_range():
    p = _player("OMNI")
    assert not p.is_enemy_in_lock_zone(_enemy_at(p, 500, 0))


def test_cone_behavior_unchanged():
    p = _player("CONE")
    assert p.is_enemy_in_lock_zone(_enemy_at(p, 600, 0))
    assert not p.is_enemy_in_lock_zone(_enemy_at(p, 200, 0))
    assert not p.is_enemy_in_lock_zone(_enemy_at(p, 600, 40))
