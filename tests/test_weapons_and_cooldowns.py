"""Tests for weapons, ammunition limits, reload timers, and stratagems."""

from eagle1.app.game import (
    Player,
    PLAYER_MAX_BULLETS,
    PLAYER_RELOAD_TIME,
    PLAYER_MAX_ROCKETS,
    PLAYER_ROCKET_RELOAD_TIME,
)
from eagle1.systems.ground_support import AirStrikeType


def test_player_cannon_initial_state():
    """Verify player begins with full cannon ammunition."""
    player = Player()
    assert player.max_bullets == PLAYER_MAX_BULLETS
    assert player.used_bullets == 0
    assert not player.reloading
    assert player.reloading_time == PLAYER_RELOAD_TIME


def test_player_rocket_initial_state():
    """Verify player begins with full rocket payload and correct cooldown."""
    player = Player()
    assert player.max_rockets == PLAYER_MAX_ROCKETS
    assert player.used_rockets == 0
    assert not player.rocket_reloading
    assert player.rocket_reloading_time == PLAYER_ROCKET_RELOAD_TIME


def test_stratagems_definitions():
    """Verify all 8 stratagems are defined with name, cooldown, and description."""
    expected_keys = [
        "strafe",
        "bomb_500kg",
        "cluster",
        "napalm",
        "gas",
        "rockets",
        "ems",
        "smoke",
    ]
    assert set(AirStrikeType.DATA.keys()) == set(expected_keys)

    for key, data in AirStrikeType.DATA.items():
        assert "name" in data
        assert "cooldown" in data
        assert data["cooldown"] > 0
        assert "desc" in data
        assert len(data["desc"]) > 0
