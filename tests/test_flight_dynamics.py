"""Tests for Corner Speed flight dynamics and speed-dependent turn rate curves."""

import math
import pytest

from eagle1.app.game import (
    CORNER_SPEED,
    LIGHT_ENEMY_TURN_RATE,
    PLAYER_MAX_SPEED,
    PLAYER_MIN_SPEED,
    PLAYER_TURN_RATE,
    Light_Enemy,
    Player,
    calculate_turn_rate,
)


def test_corner_speed_constant():
    """Verify optimal corner speed sits in the mid-band between min and max speed."""
    assert PLAYER_MIN_SPEED < CORNER_SPEED < PLAYER_MAX_SPEED
    assert CORNER_SPEED == pytest.approx(4.5)


def test_calculate_turn_rate_peaks_at_corner_speed():
    """Verify turn rate achieves maximum angular velocity at CORNER_SPEED."""
    base = 3.0
    rate_stall = calculate_turn_rate(PLAYER_MIN_SPEED, base)
    rate_corner = calculate_turn_rate(CORNER_SPEED, base)
    rate_max = calculate_turn_rate(PLAYER_MAX_SPEED, base)

    # Corner speed yields highest instantaneous turn rate (1.35x base)
    assert rate_corner == pytest.approx(base * 1.35)
    assert rate_stall == pytest.approx(base * 0.80)
    assert rate_max == pytest.approx(base * 0.75)

    assert rate_corner > rate_stall
    assert rate_corner > rate_max


def test_calculate_turn_rate_monotonic_slopes():
    """Verify smooth progression from stall -> corner -> max speed."""
    base = 3.0
    # Increasing from stall (2.0) to corner (4.5)
    r_20 = calculate_turn_rate(2.0, base)
    r_32 = calculate_turn_rate(3.2, base)
    r_45 = calculate_turn_rate(4.5, base)
    assert r_20 < r_32 < r_45

    # Decreasing from corner (4.5) to max speed (7.0)
    r_58 = calculate_turn_rate(5.8, base)
    r_70 = calculate_turn_rate(7.0, base)
    assert r_45 > r_58 > r_70


def test_turn_radius_widens_at_high_speed():
    """Verify turn radius R = v / omega_rad is significantly tighter at corner speed than max speed."""
    rate_corner_rad = math.radians(calculate_turn_rate(CORNER_SPEED, PLAYER_TURN_RATE))
    rate_max_rad = math.radians(calculate_turn_rate(PLAYER_MAX_SPEED, PLAYER_TURN_RATE))

    radius_corner = CORNER_SPEED / rate_corner_rad
    radius_max = PLAYER_MAX_SPEED / rate_max_rad

    # High-speed dash produces > 2.5x wider turn circle than corner speed cut
    assert radius_max > radius_corner * 2.5


def test_player_get_effective_turn_rate():
    """Verify Player.get_effective_turn_rate dynamically scales with current forward speed."""
    p = Player()

    p.velocity_x = CORNER_SPEED
    p.velocity_y = CORNER_SPEED
    assert p.get_effective_turn_rate() == pytest.approx(PLAYER_TURN_RATE * 1.35)

    p.velocity_x = PLAYER_MAX_SPEED
    p.velocity_y = PLAYER_MAX_SPEED
    assert p.get_effective_turn_rate() == pytest.approx(PLAYER_TURN_RATE * 0.75)


def test_light_enemy_uses_dynamic_turn_rate():
    """Verify Light_Enemy turning speed scales with its current flight velocity."""
    enemy = Light_Enemy(x=1000, y=1000)
    assert hasattr(enemy, "get_effective_turn_rate")

    enemy.speed = CORNER_SPEED
    assert enemy.get_effective_turn_rate() == pytest.approx(LIGHT_ENEMY_TURN_RATE * 1.35)

    enemy.speed = PLAYER_MAX_SPEED
    assert enemy.get_effective_turn_rate() == pytest.approx(LIGHT_ENEMY_TURN_RATE * 0.75)

