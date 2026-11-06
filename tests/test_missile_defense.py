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


# ---------------------------------------------------------------------------
# Flare countermeasures
# ---------------------------------------------------------------------------

class _StubRocket:
    def __init__(self, x, y, target=None):
        self.x = x
        self.y = y
        self.width = 12
        self.height = 16
        self.used = False
        self.target = target


class _StubEnemy:
    is_air_target = True

    def __init__(self, x, y, flares=1, chance=1.0):
        self.x = x
        self.y = y
        self.width = 50
        self.height = 46
        self.health = 20
        self.exploding = False
        self.flares_remaining = flares
        self.flare_deploy_chance = chance


class _FixedRng:
    """Returns a scripted sequence of random() values."""

    def __init__(self, values):
        self._values = list(values)

    def random(self):
        return self._values.pop(0)


def test_no_flares_outside_trigger_range():
    enemy = _StubEnemy(1000, 1000)
    rocket = _StubRocket(1000, 1000 + missile_defense.FLARE_TRIGGER_RANGE + 100, target=enemy)
    assert missile_defense.update_rocket_countermeasures(rocket, rng=_FixedRng([0.0, 0.0])) == []
    assert enemy.flares_remaining == 1
    assert not getattr(rocket, "countermeasure_rolled", False)


def test_flare_roll_happens_once_per_rocket():
    enemy = _StubEnemy(1000, 1000, chance=0.0)
    rocket = _StubRocket(1000, 1100, target=enemy)
    assert missile_defense.update_rocket_countermeasures(rocket, rng=_FixedRng([0.5])) == []
    assert rocket.countermeasure_rolled is True
    # A second call must not consume another roll (empty rng would raise IndexError).
    assert missile_defense.update_rocket_countermeasures(rocket, rng=_FixedRng([])) == []
    assert enemy.flares_remaining == 1


def test_deploy_and_decoy_retargets_rocket():
    enemy = _StubEnemy(1000, 1000)
    rocket = _StubRocket(1000, 1100, target=enemy)
    flares = missile_defense.update_rocket_countermeasures(rocket, rng=_FixedRng([0.0, 0.0]))
    assert len(flares) == missile_defense.FLARES_PER_SALVO
    assert rocket.decoyed is True
    assert isinstance(rocket.target, Flare)
    assert enemy.flares_remaining == 0


def test_deploy_without_decoy_keeps_target():
    enemy = _StubEnemy(1000, 1000)
    rocket = _StubRocket(1000, 1100, target=enemy)
    flares = missile_defense.update_rocket_countermeasures(rocket, rng=_FixedRng([0.0, 0.99]))
    assert len(flares) == missile_defense.FLARES_PER_SALVO
    assert not getattr(rocket, "decoyed", False)
    assert rocket.target is enemy


def test_stunned_target_cannot_flare():
    enemy = _StubEnemy(1000, 1000)
    enemy.stun_timer = 1.0
    rocket = _StubRocket(1000, 1100, target=enemy)
    assert missile_defense.update_rocket_countermeasures(rocket, rng=_FixedRng([0.0, 0.0])) == []
    assert enemy.flares_remaining == 1


def test_target_without_flares_cannot_flare():
    enemy = _StubEnemy(1000, 1000, flares=0)
    rocket = _StubRocket(1000, 1100, target=enemy)
    assert missile_defense.update_rocket_countermeasures(rocket, rng=_FixedRng([0.0, 0.0])) == []


def test_spawn_flare_salvo_centers_on_entity():
    enemy = _StubEnemy(1000, 1000)
    flares = missile_defense.spawn_flare_salvo(enemy)
    assert len(flares) == missile_defense.FLARES_PER_SALVO
    for flare in flares:
        assert flare.center() == pytest.approx((1025.0, 1023.0))


def test_check_flare_detonation_consumes_rocket_and_flare():
    flare = Flare(1006.0, 1008.0, 0.0, 0.0)
    rocket = _StubRocket(1000, 1000, target=flare)
    rocket.decoyed = True
    assert missile_defense.check_flare_detonation(rocket) is True
    assert rocket.used is True
    assert flare.is_alive is False


def test_check_flare_detonation_ignores_distant_flare():
    flare = Flare(1300.0, 1300.0, 0.0, 0.0)
    rocket = _StubRocket(1000, 1000, target=flare)
    rocket.decoyed = True
    assert missile_defense.check_flare_detonation(rocket) is False
    assert rocket.used is False


def test_draw_flares_paints_alive_flares_only():
    import pygame

    surface = pygame.Surface((100, 100))
    surface.fill((0, 0, 0))
    alive = Flare(30.0, 30.0, 0.0, 0.0)
    dead = Flare(70.0, 70.0, 0.0, 0.0)
    dead.health = 0.0
    missile_defense.draw_flares(surface, [alive, dead], 0.0, 0.0)
    assert tuple(surface.get_at((30, 30)))[:3] == missile_defense.FLARE_CORE_COLOR
    assert tuple(surface.get_at((70, 70)))[:3] == (0, 0, 0)


def test_decoyed_rocket_does_not_reacquire():
    from eagle1.app import game

    enemy = game.Light_Enemy(x=980, y=700)
    flare = Flare(1000.0, 900.0, 0.0, 0.0)
    flare.health = 0.0
    rocket = game.Player.Rocket(1000, 1000, 0.0, target=flare)
    rocket.decoyed = True
    rocket.update_position([enemy])
    assert rocket.target is flare


def test_respawn_clears_active_flares():
    from eagle1.app import game

    game.active_flares.append(Flare(100.0, 100.0, 0.0, 0.0))
    game.respawn()
    assert game.active_flares == []


# ---------------------------------------------------------------------------
# Disabled defenses (EMS stun, smoke, freeze) and the shared rocket step
# ---------------------------------------------------------------------------

def test_smoke_blinded_target_cannot_flare():
    enemy = _StubEnemy(1000, 1000)
    enemy.smoke_blinded = True
    rocket = _StubRocket(1000, 1100, target=enemy)
    assert missile_defense.update_rocket_countermeasures(rocket, rng=_FixedRng([0.0, 0.0])) == []
    assert enemy.flares_remaining == 1


def test_frozen_target_cannot_flare():
    enemy = _StubEnemy(1000, 1000)
    rocket = _StubRocket(1000, 1100, target=enemy)
    assert missile_defense.update_rocket_countermeasures(rocket, rng=_FixedRng([0.0, 0.0]), frozen=True) == []
    assert enemy.flares_remaining == 1
    assert not getattr(rocket, "countermeasure_rolled", False)


class _SteppableRocket(_StubRocket):
    """Stub rocket with a no-op guidance step, enough for step_rocket()."""

    def update_position(self, targets=None, player=None):
        self.updated_with = targets


def test_step_rocket_reports_decoy_popup_above_target():
    enemy = _StubEnemy(1000, 1000)
    rocket = _SteppableRocket(1000, 1100, target=enemy)
    step = missile_defense.step_rocket(rocket, [enemy], rng=_FixedRng([0.0, 0.0]))
    assert len(step.flares) == missile_defense.FLARES_PER_SALVO
    assert step.popup == "MISSILE DECOYED"
    assert step.popup_pos == pytest.approx((1025.0, 1023.0 - 30))
    assert rocket.updated_with == [enemy]


def test_step_rocket_reports_flares_without_decoy():
    enemy = _StubEnemy(1000, 1000)
    rocket = _SteppableRocket(1000, 1100, target=enemy)
    step = missile_defense.step_rocket(rocket, [enemy], rng=_FixedRng([0.0, 0.99]))
    assert step.popup == "FLARES"


def test_step_rocket_reports_evasion():
    enemy = _StubEnemy(1000, 1000)
    enemy.flares_remaining = 0
    enemy.bfm_mode = "MISSILE_DEFENSE"
    rocket = _SteppableRocket(1019, 1075, target=enemy)
    step = missile_defense.step_rocket(rocket, [enemy], rng=_FixedRng([0.0]))
    assert step.flares == []
    assert step.popup == "EVADED"
    assert rocket.target is None


def test_step_rocket_frozen_skips_all_defenses():
    enemy = _StubEnemy(1000, 1000)
    enemy.bfm_mode = "MISSILE_DEFENSE"
    rocket = _SteppableRocket(1019, 1075, target=enemy)
    step = missile_defense.step_rocket(rocket, [enemy], rng=_FixedRng([]), frozen=True)
    assert step.flares == [] and step.popup is None and step.popup_pos is None
    assert rocket.target is enemy


def test_rocket_can_fuse():
    rocket = _StubRocket(0, 0)
    assert missile_defense.rocket_can_fuse(rocket) is True
    rocket.decoyed = True
    assert missile_defense.rocket_can_fuse(rocket) is False
    rocket.decoyed = False
    rocket.used = True
    assert missile_defense.rocket_can_fuse(rocket) is False
