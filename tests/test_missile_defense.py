"""Tests for eagle1.systems.missile_defense: air-target tagging, heading math and flares."""

import pytest

from eagle1.systems import missile_defense
from eagle1.systems.missile_defense import (
    FLARE_LIFETIME_FRAMES,
    Flare,
    filter_air_targets,
    heading_deviation_deg,
    is_air_target,
)


class _Tagged:
    def __init__(self, air=True, health=10, exploding=False):
        if air is not None:
            self.is_air_target = air
        self.health = health
        self.exploding = exploding


def test_is_air_target_reads_class_flag():
    assert is_air_target(_Tagged(air=True)) is True
    assert is_air_target(_Tagged(air=False)) is False
    assert is_air_target(_Tagged(air=None)) is False
    assert is_air_target(None) is False


def test_filter_air_targets_drops_dead_exploding_and_ground():
    alive = _Tagged()
    dead = _Tagged(health=0)
    exploding = _Tagged(exploding=True)
    ground = _Tagged(air=False)
    assert filter_air_targets([alive, dead, exploding, ground, None]) == [alive]
    assert filter_air_targets(None) == []
    assert filter_air_targets([]) == []


def test_heading_deviation_ahead_is_zero():
    assert heading_deviation_deg(0.0, 0.0, 0.0, 0.0, -100.0) == pytest.approx(0.0, abs=1e-6)


def test_heading_deviation_behind_is_180():
    assert heading_deviation_deg(0.0, 0.0, 0.0, 0.0, 100.0) == pytest.approx(180.0, abs=1e-6)


def test_heading_deviation_side_is_90():
    assert heading_deviation_deg(0.0, 0.0, 0.0, 100.0, 0.0) == pytest.approx(90.0, abs=1e-6)
    assert heading_deviation_deg(0.0, 0.0, 0.0, -100.0, 0.0) == pytest.approx(90.0, abs=1e-6)


def test_flare_drifts_decelerates_and_expires():
    flare = Flare(100.0, 100.0, 3.0, 0.0)
    assert flare.is_alive
    start_x, _ = flare.center()
    flare.update()
    moved_x, _ = flare.center()
    assert moved_x > start_x
    assert abs(flare.velocity[0]) < 3.0
    for _ in range(FLARE_LIFETIME_FRAMES):
        flare.update()
    assert flare.is_alive is False


def test_flare_is_not_lockable():
    assert is_air_target(Flare(0.0, 0.0, 0.0, 0.0)) is False


def test_flare_frozen_still_expires():
    flare = Flare(50.0, 50.0, 1.0, 1.0)
    for _ in range(FLARE_LIFETIME_FRAMES):
        flare.update(speed_factor=0.0)
    assert flare.center() == pytest.approx((50.0, 50.0))
    assert flare.is_alive is False


def test_omni_half_angle_is_forward_only():
    assert 0.0 < missile_defense.RADAR_OMNI_HALF_ANGLE < 90.0
