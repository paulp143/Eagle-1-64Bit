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


# ---------------------------------------------------------------------------
# Evasion roll (a well-timed break can make the rocket overshoot)
# ---------------------------------------------------------------------------

class _FixedRng:
    def __init__(self, values):
        self._values = list(values)

    def random(self):
        return self._values.pop(0)


class _EvadingEnemy(_StubEnemy):
    is_air_target = True

    def __init__(self, x, y, mode="MISSILE_DEFENSE"):
        super().__init__(x, y)
        self.bfm_mode = mode
        self.health = 20
        self.exploding = False


def _close_rocket(enemy):
    return _StubRocket(enemy.x + 19, enemy.y + 15 + 60, target=enemy)


def test_evasion_roll_success_breaks_lock():
    enemy = _EvadingEnemy(1000, 1000)
    rocket = _close_rocket(enemy)
    assert missile_defense.update_rocket_evasion(rocket, rng=_FixedRng([0.0])) is True
    assert rocket.decoyed is True
    assert rocket.target is None


def test_evasion_roll_failure_keeps_lock_and_rolls_once():
    enemy = _EvadingEnemy(1000, 1000)
    rocket = _close_rocket(enemy)
    assert missile_defense.update_rocket_evasion(rocket, rng=_FixedRng([0.99])) is False
    assert rocket.target is enemy
    assert rocket.evasion_rolled is True
    assert missile_defense.update_rocket_evasion(rocket, rng=_FixedRng([])) is False


def test_no_evasion_roll_when_not_breaking():
    enemy = _EvadingEnemy(1000, 1000, mode="TAIL_STALK")
    rocket = _close_rocket(enemy)
    assert missile_defense.update_rocket_evasion(rocket, rng=_FixedRng([0.0])) is False
    assert not getattr(rocket, "evasion_rolled", False)


def test_no_evasion_roll_outside_range():
    enemy = _EvadingEnemy(1000, 1000)
    rocket = _StubRocket(1000, 1000 + missile_defense.EVASION_ROLL_RANGE + 100, target=enemy)
    assert missile_defense.update_rocket_evasion(rocket, rng=_FixedRng([0.0])) is False


def test_stunned_enemy_cannot_evade():
    enemy = _EvadingEnemy(1000, 1000)
    enemy.stun_timer = 1.0
    rocket = _close_rocket(enemy)
    assert missile_defense.update_rocket_evasion(rocket, rng=_FixedRng([0.0])) is False


def test_decoyed_rocket_is_not_rolled_again():
    enemy = _EvadingEnemy(1000, 1000)
    rocket = _close_rocket(enemy)
    rocket.decoyed = True
    assert missile_defense.update_rocket_evasion(rocket, rng=_FixedRng([0.0])) is False


def test_smoke_blinded_enemy_cannot_evade_roll():
    enemy = _EvadingEnemy(1000, 1000)
    enemy.smoke_blinded = True
    assert missile_defense.update_rocket_evasion(_close_rocket(enemy), rng=_FixedRng([0.0])) is False


def test_frozen_enemy_cannot_evade_roll():
    enemy = _EvadingEnemy(1000, 1000)
    rocket = _close_rocket(enemy)
    assert missile_defense.update_rocket_evasion(rocket, rng=_FixedRng([0.0]), frozen=True) is False
    assert not getattr(rocket, "evasion_rolled", False)


def test_frozen_enemy_does_not_enter_missile_defense():
    p, enemy, rocket = _setup_enemy_and_rocket()
    for _ in range(missile_defense.MISSILE_REACTION_DELAY_FRAMES + 5):
        enemy.update(target_player=p, enemies=[enemy], speed_factor=0.0, incoming_rockets=[rocket])
    assert enemy.bfm_mode != "MISSILE_DEFENSE"
    assert enemy.missile_reaction_frames == 0


def test_smoke_blinded_enemy_does_not_notice_rocket():
    p, enemy, rocket = _setup_enemy_and_rocket(player_distance=1400.0)
    enemy.state = "PATROL"
    for _ in range(missile_defense.MISSILE_REACTION_DELAY_FRAMES + 5):
        enemy.smoke_blinded = True  # re-applied every frame by the smoke zone
        enemy.update(target_player=p, enemies=[enemy], incoming_rockets=[rocket])
    assert enemy.state == "PATROL"
    assert enemy.bfm_mode != "MISSILE_DEFENSE"
