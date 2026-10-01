"""Tests for power-up drops, pity system, drone companions, and abilities."""

from eagle1.systems.powerups import (
    PowerUpManager,
    PowerUpDrop,
    ABILITIES,
    POWERUP_DROP_BASE_CHANCE,
    POWERUP_PITY_INCREMENT,
    POWERUP_LIFETIME_SECONDS,
)


def test_powerup_abilities_table():
    """Verify all 8 power-up abilities are configured with duration and rarity."""
    assert len(ABILITIES) == 8
    for ability_id, config in ABILITIES.items():
        assert "name" in config
        assert "duration" in config
        assert config["duration"] > 0
        assert "rarity" in config
        assert config["rarity"] in ["Common", "Rare", "Epic", "Legendary"]


def test_powerup_manager_initial_state():
    """Verify clean initial state of the PowerUpManager."""
    mgr = PowerUpManager()
    assert len(mgr.drops) == 0
    assert len(mgr.active_buffs) == 0
    assert mgr.pity_counter == 0
    assert mgr.drone is None
    assert len(mgr.homing_missiles) == 0


def test_powerup_drop_initialization():
    """Verify a dropped power-up initializes with correct coordinates and duration."""
    drop = PowerUpDrop(500.0, 600.0, "rapid_fire")
    assert drop.x == 500.0
    assert drop.y == 600.0
    assert drop.ability_id == "rapid_fire"
    assert not drop.picked_up
    assert drop.lifetime == POWERUP_LIFETIME_SECONDS


def test_pity_system_constants():
    """Verify pity increment and base drop probability."""
    assert 0.0 < POWERUP_DROP_BASE_CHANCE < 1.0
    assert 0.0 < POWERUP_PITY_INCREMENT < 1.0
