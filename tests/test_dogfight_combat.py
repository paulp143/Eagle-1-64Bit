"""Tests for Task 2: Health, TTK, Directional Armor, and Kamikaze Collision Physics."""

import math
import pytest

from eagle1.app.game import (
    LIGHT_ENEMY_HEALTH,
    Light_Enemy,
    Player,
    calculate_directional_gun_damage,
    calculate_turn_rate,
    resolve_aerial_collision,
)


def test_light_enemy_increased_health_ttk():
    """Verify Light_Enemy health is 20 so it survives multiple cannon bursts."""
    assert LIGHT_ENEMY_HEALTH == 20
    enemy = Light_Enemy(x=1000, y=1000)
    assert enemy.health == 20


def test_directional_armor_head_on_vs_tail_chase():
    """Verify frontal shots deflect (50% dmg) while rear-engine shots deal full/critical dmg."""
    base_dmg = 1.0
    # Enemy flying straight SOUTH (angle=0 -> forward vector is (sin(0), cos(0)) = (0, 1))
    enemy_angle = 0.0

    # 1. Rear-aspect shot (Player behind enemy, shooting SOUTH: dx=0, dy=+8)
    rear_dmg = calculate_directional_gun_damage(base_dmg, 0.0, 8.0, enemy_angle)
    assert rear_dmg >= base_dmg * 1.0

    # 2. Frontal head-on shot (Player in front of enemy, shooting NORTH: dx=0, dy=-8)
    front_dmg = calculate_directional_gun_damage(base_dmg, 0.0, -8.0, enemy_angle)
    assert front_dmg == pytest.approx(base_dmg * 0.5)

    # 3. Side 90-degree beam shot (shooting EAST: dx=+8, dy=0)
    side_dmg = calculate_directional_gun_damage(base_dmg, 8.0, 0.0, enemy_angle)
    assert front_dmg < side_dmg < rear_dmg


def test_aerial_collision_one_hit_kills_enemy_and_separates():
    """Verify mid-air collision one-hit destroys Light_Enemy, bounces craft apart, and returns True."""
    p = Player()
    p.pos_x = 1000.0
    p.pos_y = 1000.0
    p.x = 1000
    p.y = 1000
    p.velocity_x = 6.5
    p.velocity_y = 6.5

    enemy = Light_Enemy(x=1005, y=1005)

    hit = resolve_aerial_collision(p, enemy, current_time_ms=1000)

    # Collision returns True to trigger screen shake and hit sparks
    assert hit is True

    # Enemy is destroyed in one hit (health <= 0)
    assert enemy.health <= 0

    # Aircraft are physically pushed apart to prevent multi-frame overlap grinding
    dist_after = math.hypot(p.pos_x - enemy.pos_x, p.pos_y - enemy.pos_y)
    assert dist_after >= 40.0

    # Player loses speed on impact
    assert p.velocity_x < 6.5


def test_aerial_collision_cooldown_prevents_invincibility_grinding():
    """Verify repeated collision checks within cooldown window do not deal additional damage."""
    p = Player()
    p.pos_x = 1000.0
    p.pos_y = 1000.0
    enemy = Light_Enemy(x=1000, y=1000)

    hit1 = resolve_aerial_collision(p, enemy, current_time_ms=1000)
    assert hit1 is True
    hp_after_first = enemy.health

    # Immediate second call within 500ms cooldown should return False and not deal additional damage
    hit2 = resolve_aerial_collision(p, enemy, current_time_ms=1100)
    assert hit2 is False
    assert enemy.health == hp_after_first


def test_calculate_turn_rate_stall_corner_overspeed_curve():
    """Verify aerodynamic curve multipliers at stall, corner peak, max speed, and overspeed."""
    base_rate = 2.0
    # 1. Stall speed (<= 2.0)
    assert calculate_turn_rate(1.5, base_rate) == pytest.approx(base_rate * 0.80)
    assert calculate_turn_rate(2.0, base_rate) == pytest.approx(base_rate * 0.80)

    # 2. Corner speed peak (4.5)
    assert calculate_turn_rate(4.5, base_rate) == pytest.approx(base_rate * 1.35)

    # 3. Max speed (7.0)
    assert calculate_turn_rate(7.0, base_rate) == pytest.approx(base_rate * 0.75)

    # 4. Overspeed (> 7.0)
    assert calculate_turn_rate(10.0, base_rate) == pytest.approx(base_rate * (0.75 - 0.10))


def test_resolve_aerial_collision_exact_coincident_centers():
    """Verify coincident center positions (dist < 0.001) fallback to heading normal without error."""
    p = Player()
    p.pos_x = 1000.0
    p.pos_y = 1000.0
    p.angle = 90.0

    # Align enemy center exactly with player center
    # p_cx = 1000 + 48/2 = 1024; p_cy = 1000 + 61/2 = 1030.5
    # e_x = 1024 - 50/2 = 999; e_y = 1030.5 - 46/2 = 1007.5
    enemy = Light_Enemy(x=999, y=1007.5)

    hit = resolve_aerial_collision(p, enemy, current_time_ms=1000)
    assert hit is True
    # Craft should be pushed apart cleanly
    sep = math.hypot(p.pos_x - enemy.pos_x, p.pos_y - enemy.pos_y)
    assert sep >= 40.0


def test_directional_gun_damage_zero_velocity_bullet():
    """Verify zero-velocity bullet does not raise ZeroDivisionError and returns base damage."""
    dmg = calculate_directional_gun_damage(base_damage=5.0, bullet_dx=0.0, bullet_dy=0.0, enemy_angle=45.0)
    assert dmg == 5.0

