"""Tests for Task 3: BFM Fighter AI — Pursuit Geometry, Merge Breaks, and 1/2-Circle Tactics."""

import pytest

from eagle1.app.game import (
    CORNER_SPEED,
    PLAYER_MAX_SPEED,
    Light_Enemy,
    Player,
)


def test_head_on_merge_triggers_lateral_break():
    """Verify enemy approaching head-on within merge distance breaks laterally instead of ramming."""
    p = Player()
    # Player at (1000, 1200) flying NORTH (angle=0 -> forward vector (0, -1))
    p.pos_x = 1000.0
    p.pos_y = 1200.0
    p.x = 1000
    p.y = 1200
    p.angle = 0.0

    # Enemy 240px due NORTH at (1000, 960) flying SOUTH (angle=0 -> forward vector (0, +1))
    enemy = Light_Enemy(x=1000, y=960, squadron_id=0, orbit_direction=1)
    enemy.state = "AGRO"
    enemy.angle = 0.0

    enemy.update(target_player=p, enemies=[enemy])

    assert enemy.bfm_mode == "MERGE_BREAK"
    # Direct head-on angle from (1000, 960) to (1000, 1200) is 0.0 deg.
    # Enemy must steer significantly off-axis (> 40 deg) to avoid head-on suicide.
    direct_los_angle = 0.0
    diff_from_los = abs((enemy.target_heading - direct_los_angle + 180) % 360 - 180)
    assert diff_from_los >= 45.0


def test_one_circle_vs_two_circle_merge_speeds():
    """Verify even squadrons brake to Corner Speed (1-circle) while odd squadrons extend fast (2-circle)."""
    p = Player()
    p.pos_x = 1000.0
    p.pos_y = 1200.0
    p.angle = 0.0

    enemy_1circle = Light_Enemy(x=1000, y=960, squadron_id=0, orbit_direction=1)
    enemy_1circle.state = "AGRO"
    enemy_1circle.angle = 0.0
    enemy_1circle.update(target_player=p, enemies=[enemy_1circle])

    enemy_2circle = Light_Enemy(x=1000, y=960, squadron_id=1, orbit_direction=-1)
    enemy_2circle.state = "AGRO"
    enemy_2circle.angle = 0.0
    enemy_2circle.update(target_player=p, enemies=[enemy_2circle])

    assert enemy_1circle.speed == pytest.approx(CORNER_SPEED)
    assert enemy_2circle.speed > CORNER_SPEED


def test_tail_stalk_lag_pursuit_aims_behind_player():
    """Verify enemy at medium flank range uses lag pursuit aiming behind the player's tail."""
    p = Player()
    # Player at (1000, 1000) flying NORTH (angle=0 -> tail is SOUTH at (1000, 1160))
    p.pos_x = 1000.0
    p.pos_y = 1000.0
    p.angle = 0.0

    # Enemy 450px to the EAST at (1450, 1000), facing WEST (-90 deg)
    enemy = Light_Enemy(x=1450, y=1000, squadron_id=0, orbit_direction=1)
    enemy.state = "AGRO"
    enemy.angle = -90.0

    enemy.update(target_player=p, enemies=[enemy])

    assert enemy.bfm_mode == "TAIL_STALK"
    # Pure pursuit to (1000, 1000) from (1450, 1000) is -90.0 deg (due WEST).
    # Lag pursuit aims SOUTH-WEST toward player's tail (y > 1000), so dy > 0 -> angle between -90 and 0.
    assert -88.0 < enemy.target_heading < -10.0


def test_defensive_evasive_jink_when_player_on_six():
    """Verify enemy breaks hard at Corner Speed when player is directly on its tail aiming at it."""
    p = Player()
    # Player at (1000, 1250) flying NORTH (angle=0 -> aiming straight NORTH at enemy)
    p.pos_x = 1000.0
    p.pos_y = 1250.0
    p.angle = 0.0

    # Enemy 250px ahead at (1000, 1000) also flying NORTH (angle=180 -> forward vector (0, -1))
    enemy = Light_Enemy(x=1000, y=1000, squadron_id=0, orbit_direction=1)
    enemy.state = "AGRO"
    enemy.angle = 180.0

    enemy.update(target_player=p, enemies=[enemy])

    assert enemy.bfm_mode == "EVASIVE_JINK"
    assert enemy.speed == pytest.approx(CORNER_SPEED)
    # Enemy was flying 180 deg (straight away). Break turn must pull hard off 180 deg.
    diff_from_straight = abs((enemy.target_heading - 180.0 + 180) % 360 - 180)
    assert diff_from_straight >= 60.0


def test_player_outturns_enemy_across_combat_speeds():
    """Verify the player has superior turn authority over Light_Enemy across normal and corner speeds,
    so the enemy cannot endlessly out-turn the player."""
    p = Player()
    enemy = Light_Enemy(x=1000, y=1000)

    # Enemy at optimal corner speed
    enemy.speed = CORNER_SPEED
    enemy_corner_turn = enemy.get_effective_turn_rate()

    # Player at max speed (7.0) and corner speed (4.5) both out-turn the enemy
    p.velocity_x = PLAYER_MAX_SPEED
    p.velocity_y = PLAYER_MAX_SPEED
    player_max_spd_turn = p.get_effective_turn_rate()

    p.velocity_x = CORNER_SPEED
    p.velocity_y = CORNER_SPEED
    player_corner_turn = p.get_effective_turn_rate()

    assert player_max_spd_turn > enemy_corner_turn
    assert player_corner_turn > player_max_spd_turn


def test_player_wins_sustained_turning_circle_and_gets_guns_on():
    """Prove-It Reproduction: In a sustained close-in turning fight (120 frames),
    a turning player must out-rate the enemy and bring the enemy into the player's
    forward firing arc (< 25 deg), rather than being endlessly out-turned or orbited."""
    import math

    p = Player()
    p.pos_x = 1500.0
    p.pos_y = 1500.0
    p.angle = 0.0
    # Even if player is flying fast (6.0) or at corner speed (4.5), turning hard left:
    p.velocity_x = 5.5
    p.velocity_y = 5.5

    # Enemy starts 180px abeam/ahead at (1650, 1400) in AGRO
    enemy = Light_Enemy(x=1650, y=1400, squadron_id=0, orbit_direction=1)
    enemy.state = "AGRO"
    enemy.angle = 0.0

    got_guns_on_frames = 0
    for _ in range(150):
        # Player turns toward the enemy
        cx = enemy.pos_x + 17.5
        cy = enemy.pos_y + 16.0
        pcx = p.pos_x + 24.0
        pcy = p.pos_y + 30.5
        dx = cx - pcx
        dy = cy - pcy
        desired_player_angle = math.degrees(math.atan2(-dx, -dy)) % 360
        p_diff = (desired_player_angle - p.angle + 180) % 360 - 180
        p_turn = p.get_effective_turn_rate()
        if abs(p_diff) <= p_turn:
            p.angle = desired_player_angle
        elif p_diff > 0:
            p.angle += p_turn
        else:
            p.angle -= p_turn
        p.angle %= 360

        rad = math.radians(p.angle)
        p.pos_x += -math.sin(rad) * p.velocity_x
        p.pos_y += -math.cos(rad) * p.velocity_y
        p.x = int(p.pos_x)
        p.y = int(p.pos_y)

        enemy.update(target_player=p, enemies=[enemy])

        # Check if enemy is now in player's forward firing solution (< 22 deg off nose, dist < 440)
        dist = math.hypot(cx - pcx, cy - pcy)
        aim_error = abs((desired_player_angle - p.angle + 180) % 360 - 180)
        if aim_error <= 22.0 and dist <= 440.0:
            got_guns_on_frames += 1

    # Player must reliably achieve sustained guns-on time (at least 25 frames out of 150)
    assert got_guns_on_frames >= 25

