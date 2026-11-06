"""Tests that homing rockets only lock onto and engage aerial targets."""

from eagle1.app import game
from eagle1.systems import missile_defense
from eagle1.systems.academy_briefing import AcademyTargetBunker, AcademyTargetDrone
from eagle1.systems.ground_support import EnemyFabricator, EnemyGroundUnit


def test_light_enemy_bomber_and_drone_are_air_targets():
    assert missile_defense.is_air_target(game.Light_Enemy(x=1000, y=1000))
    assert missile_defense.is_air_target(game.BomberEnemy(1000, 1000))
    assert missile_defense.is_air_target(AcademyTargetDrone(1000, 1000))


def test_ground_unit_and_bunker_are_not_air_targets():
    assert not missile_defense.is_air_target(EnemyGroundUnit(EnemyGroundUnit.TYPE_TROOPER, 1000, 1000))
    assert not missile_defense.is_air_target(EnemyFabricator(1000, 1000))
    assert not missile_defense.is_air_target(AcademyTargetBunker(1000, 1000))


def test_rocket_lock_on_ignores_ground_units():
    rocket = game.Player.Rocket(1000, 1000, 0.0)
    ground = EnemyGroundUnit(EnemyGroundUnit.TYPE_TROOPER, 1000, 900)
    enemy = game.Light_Enemy(x=980, y=700)
    rocket.lock_on([ground, enemy])
    assert rocket.target is enemy


def test_rocket_lock_on_with_only_ground_units_has_no_target():
    rocket = game.Player.Rocket(1000, 1000, 0.0)
    ground = EnemyGroundUnit(EnemyGroundUnit.TYPE_TROOPER, 1000, 900)
    rocket.lock_on([ground])
    assert rocket.target is None


def test_get_rocket_targets_excludes_ground_entities():
    orig_enemies = list(game.wave_manager.enemies)
    orig_ground = list(game.ground_support_manager.enemy_ground_units)
    orig_fabs = list(game.ground_support_manager.enemy_fabricators)
    orig_bombers = list(game.bomber_enemies)
    try:
        enemy = game.Light_Enemy(x=1000, y=1000)
        game.wave_manager.enemies[:] = [enemy]
        game.ground_support_manager.enemy_ground_units[:] = [
            EnemyGroundUnit(EnemyGroundUnit.TYPE_TROOPER, 1200, 1200)
        ]
        game.ground_support_manager.enemy_fabricators[:] = [EnemyFabricator(1300, 1300)]
        game.bomber_enemies[:] = []
        assert game.get_rocket_targets() == [enemy]
    finally:
        game.wave_manager.enemies[:] = orig_enemies
        game.ground_support_manager.enemy_ground_units[:] = orig_ground
        game.ground_support_manager.enemy_fabricators[:] = orig_fabs
        game.bomber_enemies[:] = orig_bombers
