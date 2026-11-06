"""Integration tests for the rocket rework through the real game loop (game.move / game.draw)."""

import pytest

from eagle1.app import game
from eagle1.app.game import MISSION_CONFIGS, MissionType
from eagle1.systems import missile_defense


class _ScriptedRng:
    """Deterministic stand-in for missile_defense._RNG; repeats the last value when exhausted."""

    def __init__(self, *values):
        self._values = list(values)

    def random(self):
        if len(self._values) > 1:
            return self._values.pop(0)
        return self._values[0]


@pytest.fixture(autouse=True)
def air_superiority(tmp_path, monkeypatch):
    """Fresh Air Superiority sortie with no enemies; restores shared game globals afterwards."""
    monkeypatch.setenv("EAGLE1_USER_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(game, "HIGHSCORE_FILE", str(tmp_path / "highscore.txt"))
    orig_mission = game.active_mission_config
    orig_state = game.game_state

    game.respawn(mission_config=MISSION_CONFIGS[MissionType.AIR_SUPERIORITY])
    game.game_state = ""
    game.wave_manager.enemies.clear()
    game.bomber_enemies.clear()
    game.active_flares.clear()
    game.ground_support_manager.floating_popups.clear()
    game.powerup_manager.enemy_frozen_timer = 0
    p = game.player
    p.pos_x, p.pos_y = 1500.0, 1500.0
    p.x, p.y = 1500, 1500
    p.angle = 0.0

    yield

    game.wave_manager.enemies.clear()
    game.bomber_enemies.clear()
    game.active_flares.clear()
    game.player.rockets.clear()
    game.powerup_manager.enemy_frozen_timer = 0
    game.active_mission_config = orig_mission
    game.game_state = orig_state


def _fighter(cx, cy):
    enemy = game.Light_Enemy(x=cx - game.LIGHT_ENEMY_WIDTH / 2, y=cy - game.LIGHT_ENEMY_HEIGHT / 2)
    enemy.state = "AGRO"
    game.wave_manager.enemies.append(enemy)
    return enemy


def _rocket_at(cx, cy, target=None):
    rocket = game.Player.Rocket(cx - game.ROCKET_WIDTH / 2, cy - game.ROCKET_HEIGHT / 2, 0.0, target=target)
    game.player.rockets.append(rocket)
    return rocket


def _popup_texts():
    return [p["text"] for p in game.ground_support_manager.floating_popups]


# --- Decoyed rockets never fuse --------------------------------------------------------------

def test_decoyed_rocket_passes_through_fighter_without_damage():
    fighter = _fighter(1500, 1100)
    rocket = _rocket_at(1500, 1110)
    rocket.decoyed = True
    game.move()
    assert fighter.health == game.LIGHT_ENEMY_HEALTH
    assert rocket.used is False


def test_decoyed_rocket_passes_through_bomber_without_damage():
    bomber = game.BomberEnemy(1500 - 32, 1100 - 26)
    game.bomber_enemies.append(bomber)
    rocket = _rocket_at(1500, 1110)
    rocket.decoyed = True
    game.move()
    assert bomber.health == bomber.max_health
    assert rocket.used is False


def test_locked_rocket_still_hits_fighter():
    fighter = _fighter(1500, 1100)
    fighter.flares_remaining = 0
    rocket = _rocket_at(1500, 1110, target=fighter)
    game.move()
    assert fighter.health < game.LIGHT_ENEMY_HEALTH
    assert rocket.used is True


# --- Countermeasure branches in move() -------------------------------------------------------

def test_flare_decoy_in_move_spawns_flares_and_popup(monkeypatch):
    monkeypatch.setattr(missile_defense, "_RNG", _ScriptedRng(0.0))
    fighter = _fighter(1500, 1100)
    rocket = _rocket_at(1500, 1300, target=fighter)
    game.move()
    assert len(game.active_flares) == missile_defense.FLARES_PER_SALVO
    assert fighter.flares_remaining == 0
    assert rocket.decoyed is True
    assert "MISSILE DECOYED" in _popup_texts()


def test_flares_without_decoy_in_move_shows_flares_popup(monkeypatch):
    monkeypatch.setattr(missile_defense, "_RNG", _ScriptedRng(0.0, 0.99))
    fighter = _fighter(1500, 1100)
    rocket = _rocket_at(1500, 1300, target=fighter)
    game.move()
    assert "FLARES" in _popup_texts()
    assert rocket.target is fighter


def test_evasion_in_move_shows_popup_and_fighter_survives(monkeypatch):
    monkeypatch.setattr(missile_defense, "_RNG", _ScriptedRng(0.0))
    fighter = _fighter(1500, 1100)
    fighter.flares_remaining = 0
    fighter.bfm_mode = "MISSILE_DEFENSE"
    rocket = _rocket_at(1500, 1180, target=fighter)
    game.move()
    assert "EVADED" in _popup_texts()
    assert rocket.target is None
    for _ in range(10):
        game.move()
    assert fighter.health == game.LIGHT_ENEMY_HEALTH


def test_frozen_fighter_cannot_flare_in_move(monkeypatch):
    monkeypatch.setattr(missile_defense, "_RNG", _ScriptedRng(0.0))
    game.powerup_manager.enemy_frozen_timer = 5.0
    fighter = _fighter(1500, 1100)
    _rocket_at(1500, 1300, target=fighter)
    game.move()
    assert game.active_flares == []
    assert fighter.flares_remaining == missile_defense.LIGHT_ENEMY_FLARES
    assert "FLARES" not in _popup_texts() and "MISSILE DECOYED" not in _popup_texts()


def test_smoke_blinded_bomber_cannot_flare_and_flag_resets(monkeypatch):
    monkeypatch.setattr(missile_defense, "_RNG", _ScriptedRng(0.0))
    bomber = game.BomberEnemy(1500 - 32, 1100 - 26)
    bomber.smoke_blinded = True
    game.bomber_enemies.append(bomber)
    _rocket_at(1500, 1300, target=bomber)
    game.move()
    assert bomber.flares_remaining == missile_defense.BOMBER_FLARES
    assert bomber.smoke_blinded is False


# --- Flare lifecycle and enemy wiring in move() ----------------------------------------------

def test_move_updates_and_prunes_flares():
    expiring = missile_defense.Flare(800.0, 800.0, 0.0, 0.0)
    expiring.frames_left = 1
    fresh = missile_defense.Flare(900.0, 900.0, 3.0, 0.0)
    game.active_flares.extend([expiring, fresh])
    start_x = fresh.center()[0]
    game.move()
    assert game.active_flares == [fresh]
    assert fresh.center()[0] > start_x


def test_move_feeds_rockets_to_fighter_evasion():
    fighter = _fighter(1500, 800)
    fighter.flares_remaining = 0
    _rocket_at(1500, 1100, target=fighter)
    for _ in range(missile_defense.MISSILE_REACTION_DELAY_FRAMES):
        game.move()
    assert fighter.bfm_mode != "MISSILE_DEFENSE"
    game.move()
    assert fighter.bfm_mode == "MISSILE_DEFENSE"


# --- Rendering ------------------------------------------------------------------------------

def test_draw_puts_lock_brackets_on_bomber(monkeypatch, dummy_surface):
    calls = []
    monkeypatch.setattr(game, "draw_lock_brackets", lambda surface, rect, label=None: calls.append(rect.size))
    pcx = game.player.pos_x + game.PLAYER_WIDTH / 2
    pcy = game.player.pos_y + game.PLAYER_HEIGHT / 2
    bomber = game.BomberEnemy(pcx - 32, pcy - 350 - 26)
    game.bomber_enemies.append(bomber)
    game.draw(mouse_pos=(640, 360))
    assert calls == [(bomber.width, bomber.height)]


def test_draw_skips_brackets_when_nothing_is_locked(monkeypatch, dummy_surface):
    calls = []
    monkeypatch.setattr(game, "draw_lock_brackets", lambda surface, rect, label=None: calls.append(rect.size))
    pcx = game.player.pos_x + game.PLAYER_WIDTH / 2
    pcy = game.player.pos_y + game.PLAYER_HEIGHT / 2
    game.bomber_enemies.append(game.BomberEnemy(pcx - 32, pcy + 350 - 26))  # behind the ship
    game.draw(mouse_pos=(640, 360))
    assert calls == []


@pytest.mark.parametrize("angle", [0.0, 90.0, 237.0])
def test_draw_omni_minimap_arc_renders(angle, dummy_surface):
    game.player.radar_mode = "OMNI"
    game.player.angle = angle
    game.active_flares.append(missile_defense.Flare(1520.0, 1400.0, 0.0, 0.0))
    game.draw(mouse_pos=(640, 360))
