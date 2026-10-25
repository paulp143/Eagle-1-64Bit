"""Tests for Task 2: Health, TTK, Directional Armor, and Anti-Kamikaze Collision Physics."""

import math
import pytest

from eagle1.app.game import (
    LIGHT_ENEMY_HEALTH,
    Light_Enemy,
    Player,
    calculate_directional_gun_damage,
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


def test_aerial_collision_does_not_instakill_and_separates():
    """Verify mid-air collision bounces craft apart and does not insta-kill Light_Enemy."""
    p = Player()
    p.pos_x = 1000.0
    p.pos_y = 1000.0
    p.x = 1000
    p.y = 1000
    p.velocity_x = 6.5
    p.velocity_y = 6.5

    enemy = Light_Enemy(x=1005, y=1005)
    initial_enemy_hp = enemy.health

    resolve_aerial_collision(p, enemy, current_time_ms=1000)

    # Enemy survives collision with majority of health intact
    assert enemy.health > 0
    assert enemy.health >= initial_enemy_hp - 8

    # Aircraft are physically pushed apart to prevent multi-frame overlap grinding
    dist_after = math.hypot(p.pos_x - enemy.pos_x, p.pos_y - enemy.pos_y)
    assert dist_after >= 40.0

    # Player loses speed on impact
    assert p.velocity_x < 6.5


def test_aerial_collision_cooldown_prevents_invincibility_grinding():
    """Verify repeated collision checks within cooldown window do not drain enemy HP."""
    p = Player()
    p.pos_x = 1000.0
    p.pos_y = 1000.0
    enemy = Light_Enemy(x=1000, y=1000)

    resolve_aerial_collision(p, enemy, current_time_ms=1000)
    hp_after_first = enemy.health

    # Immediate second call within 500ms cooldown should not deal additional damage
    resolve_aerial_collision(p, enemy, current_time_ms=1100)
    assert enemy.health == hp_after_first

