"""Tests for health, shield absorption priority, and invincibility mechanics."""

from eagle1.app.game import (
    Player,
    PLAYER_MAX_HEALTH,
    PLAYER_MAX_SHIELD,
    PLAYER_INVINCIBLE_TIME,
)


def test_player_initial_health_and_shield():
    """Verify player starts with max health and max shield."""
    player = Player()
    assert player.health == PLAYER_MAX_HEALTH
    assert player.shield == PLAYER_MAX_SHIELD
    assert player.invincible is False
    assert player.invincible_time == PLAYER_INVINCIBLE_TIME


def test_shield_absorbs_damage_first():
    """Verify incoming damage depletes shield before health."""
    player = Player()
    initial_health = player.health
    initial_shield = player.shield

    damage = 5
    player.take_damage(damage)

    assert player.shield == initial_shield - damage
    assert player.health == initial_health
    assert player.invincible is True


def test_damage_spillover_into_health():
    """Verify that damage exceeding shield spills into health."""
    player = Player()
    initial_health = player.health
    player.shield = 4

    damage = 6  # 4 absorbed by shield, 2 to health
    player.take_damage(damage)

    assert player.shield == 0
    assert player.health == initial_health - 2
    assert player.invincible is True


def test_invulnerability_prevents_damage():
    """Verify that player takes no damage while in invincible state."""
    player = Player()
    player.invincible = True
    initial_shield = player.shield
    initial_health = player.health

    player.take_damage(10)

    assert player.shield == initial_shield
    assert player.health == initial_health
