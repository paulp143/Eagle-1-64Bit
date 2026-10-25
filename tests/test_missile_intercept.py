"""Tests for Task 4: Missile Intercept Rework & Tactical Role Differentiation."""

import pytest

from eagle1.app.game import (
    BULLET_MAX_RANGE,
    BULLET_VELOCITY_Y,
    PLAYER_MAX_SPEED,
    PLAYER_ROCKET_RELOAD_TIME,
    ROCKET_MAX_RANGE,
    ROCKET_TURN_RATE,
    ROCKET_VELOCITY,
    Light_Enemy,
    Player,
    calculate_missile_intercept_point,
)


def test_missile_high_speed_and_maneuverability_constants():
    """Verify missiles travel significantly faster than aircraft and bullets with high-G turn rate."""
    assert ROCKET_VELOCITY >= 11.0
    assert ROCKET_VELOCITY > PLAYER_MAX_SPEED * 1.5
    assert ROCKET_VELOCITY > BULLET_VELOCITY_Y
    assert ROCKET_TURN_RATE >= 5.0
    assert PLAYER_ROCKET_RELOAD_TIME <= 15000


def test_cannon_bullet_finite_dogfight_range_vs_missile_bvr_range():
    """Verify quad-cannon bullets expire at close dogfight range while missiles reach BVR range."""
    assert 380.0 <= BULLET_MAX_RANGE <= 520.0
    assert ROCKET_MAX_RANGE >= BULLET_MAX_RANGE * 2.3

    bullet = Player.Bullet(1000, 1000, angle=0.0)
    assert bullet.used is False

    # Step bullet beyond BULLET_MAX_RANGE
    steps = int(BULLET_MAX_RANGE / bullet.speed) + 2
    for _ in range(steps):
        bullet.update_position()

    assert bullet.used is True


def test_calculate_missile_intercept_point_leads_moving_target():
    """Verify intercept point predicts ahead of a laterally moving fighter."""
    enemy = Light_Enemy(x=1000, y=700)
    # Enemy flying due EAST (angle=90 -> dx = +sin(90) = +1, dy = 0) at speed 4.5
    enemy.angle = 90.0
    enemy.speed = 4.5

    lead_x, lead_y = calculate_missile_intercept_point(1000.0, 1000.0, ROCKET_VELOCITY, enemy)
    enemy_cx = enemy.pos_x + enemy.width / 2.0

    # Lead X must be significantly east of current enemy center X
    assert lead_x > enemy_cx + 50.0
    assert lead_y == pytest.approx(enemy.pos_y + enemy.height / 2.0)


def test_rocket_intercepts_fleeing_or_crossing_enemy():
    """Simulate a rocket launched at a crossing Light_Enemy and verify hit within 45 frames."""
    enemy = Light_Enemy(x=1000, y=720)
    enemy.state = "PATROL"
    enemy.angle = 90.0
    enemy.speed = 4.0

    rocket = Player.Rocket(1000, 1000, angle=0.0, target=enemy)
    hit = False
    for _ in range(45):
        # Advance enemy along its heading
        enemy.pos_x += enemy.speed
        enemy.x = int(enemy.pos_x)

        rocket.update_position(targets=[enemy])
        if rocket.colliderect(enemy):
            hit = True
            break

    assert hit is True

