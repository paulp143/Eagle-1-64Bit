"""Tests for Light_Enemy missile evasion (MISSILE_DEFENSE beam break)."""

import math

import pytest

from eagle1.app import game
from eagle1.systems import missile_defense
from eagle1.systems.missile_defense import compute_beam_heading, find_incoming_rocket


class _StubRocket:
    def __init__(self, x, y, target=None, used=False, decoyed=False):
        self.x = x
        self.y = y
        self.width = 12
        self.height = 16
        self.target = target
        self.used = used
        self.decoyed = decoyed


class _StubEnemy:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.width = 50
        self.height = 46


def _angle_diff(a, b):
    return abs((a - b + 180) % 360 - 180)


def test_find_incoming_rocket_ignores_other_targets_and_decoyed():
    enemy = _StubEnemy(1000, 1000)
    other = _StubEnemy(2000, 2000)
    rockets = [
        _StubRocket(1000, 1100, target=other),
        _StubRocket(1000, 1100, target=enemy, decoyed=True),
        _StubRocket(1000, 1100, target=enemy, used=True),
    ]
    assert find_incoming_rocket(enemy, rockets) is None
    homing = _StubRocket(1000, 1200, target=enemy)
    closer = _StubRocket(1000, 1100, target=enemy)
    assert find_incoming_rocket(enemy, rockets + [homing, closer]) is closer


def test_find_incoming_rocket_respects_warning_range():
    enemy = _StubEnemy(1000, 1000)
    far = _StubRocket(1000, 1000 + missile_defense.MISSILE_WARNING_RANGE + 100, target=enemy)
    assert find_incoming_rocket(enemy, [far]) is None
    assert find_incoming_rocket(enemy, None) is None
    assert find_incoming_rocket(enemy, []) is None


def test_compute_beam_heading_is_perpendicular():
    # Rocket due +y of the enemy: LOS heading (enemy convention) = 0°
    heading = compute_beam_heading(0.0, 0.0, 10.0, 0.0, 100.0)
    assert _angle_diff(heading, 0.0) == pytest.approx(90.0, abs=0.01)
    assert -180.0 <= heading < 180.0


def test_compute_beam_heading_picks_smaller_turn():
    assert compute_beam_heading(0.0, 0.0, 80.0, 0.0, 100.0) == pytest.approx(90.0, abs=0.01)
    assert compute_beam_heading(0.0, 0.0, -80.0, 0.0, 100.0) == pytest.approx(-90.0, abs=0.01)


def _setup_enemy_and_rocket(rocket_distance=300.0, player_distance=900.0):
    p = game.Player()
    p.pos_x, p.pos_y = 1000.0, 1000.0 + player_distance
    p.x, p.y = int(p.pos_x), int(p.pos_y)
    p.angle = 0.0
    enemy = game.Light_Enemy(x=1000, y=1000)
    enemy.state = "AGRO"
    enemy.angle = 180.0
    rocket = game.Player.Rocket(1000 + 19, 1000 + 15 + rocket_distance, 0.0, target=enemy)
    return p, enemy, rocket


def test_enemy_reacts_only_after_reaction_delay():
    p, enemy, rocket = _setup_enemy_and_rocket()
    for _ in range(missile_defense.MISSILE_REACTION_DELAY_FRAMES):
        enemy.update(target_player=p, enemies=[enemy], incoming_rockets=[rocket])
    assert enemy.bfm_mode != "MISSILE_DEFENSE"
    for _ in range(2):
        enemy.update(target_player=p, enemies=[enemy], incoming_rockets=[rocket])
    assert enemy.bfm_mode == "MISSILE_DEFENSE"
    assert enemy.speed == game.CORNER_SPEED


def test_no_rockets_keeps_existing_behavior():
    p, enemy, _ = _setup_enemy_and_rocket()
    for _ in range(20):
        enemy.update(target_player=p, enemies=[enemy])
    assert enemy.bfm_mode != "MISSILE_DEFENSE"
    assert enemy.missile_reaction_frames == 0


def test_anti_ramming_break_has_priority_over_missile_defense():
    p, enemy, rocket = _setup_enemy_and_rocket(player_distance=150.0)
    enemy.angle = 0.0  # nose toward the player (enemy convention, +y)
    enemy.missile_reaction_frames = missile_defense.MISSILE_REACTION_DELAY_FRAMES + 5
    enemy.update(target_player=p, enemies=[enemy], incoming_rockets=[rocket])
    assert enemy.bfm_mode == "MERGE_BREAK"


def test_patrol_enemy_goes_agro_on_missile_threat():
    p, enemy, rocket = _setup_enemy_and_rocket(player_distance=1400.0)
    enemy.state = "PATROL"
    for _ in range(missile_defense.MISSILE_REACTION_DELAY_FRAMES + 1):
        enemy.update(target_player=p, enemies=[enemy], incoming_rockets=[rocket])
    assert enemy.state == "AGRO"


def test_beam_turn_increases_angle_off_rocket_los():
    p, enemy, rocket = _setup_enemy_and_rocket()
    for _ in range(missile_defense.MISSILE_REACTION_DELAY_FRAMES + 15):
        enemy.update(target_player=p, enemies=[enemy], incoming_rockets=[rocket])
    ecx, ecy = missile_defense.entity_center(enemy)
    rcx, rcy = missile_defense.entity_center(rocket)
    los_to_rocket = math.degrees(math.atan2(rcx - ecx, rcy - ecy))
    # Started flying straight away from the rocket (180° off LOS); beaming rotates toward 90° off LOS.
    assert _angle_diff(enemy.angle, los_to_rocket) < 170.0
