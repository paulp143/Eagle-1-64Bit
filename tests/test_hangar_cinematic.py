"""
test_hangar_cinematic.py - Unit tests for the Super Destroyer Orbital Rearm Cinematic & Stratagem Hero.

Tests:
1. SuperDestroyerManager initialization and state properties.
2. Rearm initiation and departure coordinates caching.
3. 15.0s phase transitions (Ascent -> Hangar -> Descent -> None).
4. Combat pause flag during Hangar phase (protecting Helldivers).
5. Post-descent invulnerability frame and weapon charges restoration.
6. Stratagem Hero minigame arrow input handling, scoring, and high score persistence.
7. GroundSupportManager integration with the cinematic subsystem.
8. Headless rendering verification across all cinematic phases.
"""

import os
import pygame
import pytest

from eagle1.systems.hangar_cinematic import (
    SuperDestroyerManager,
    PHASE_NONE,
    PHASE_ASCENT,
    PHASE_HANGAR,
    PHASE_DESCENT,
    ASCENT_DURATION,
    HANGAR_DURATION,
    TOTAL_REARM_DURATION,
)
from eagle1.systems.ground_support import GroundSupportManager, AirStrikeType


class DummyPlayer:
    """Lightweight player mock for headless testing."""
    def __init__(self, x=1500.0, y=1500.0, angle=45.0):
        self.pos_x = x
        self.pos_y = y
        self.x = int(x)
        self.y = int(y)
        self.angle = angle
        self.velocity_x = 4.0
        self.velocity_y = 4.0
        self.score = 0
        self.health = 5
        self.shield = 20.0
        self.invincible = False
        self.invincible_timer = 0


def test_manager_initial_state():
    """Verify SuperDestroyerManager initializes in inactive state."""
    sdm = SuperDestroyerManager()
    assert sdm.phase == PHASE_NONE
    assert not sdm.is_active
    assert not sdm.is_combat_paused
    assert not sdm.is_controls_locked
    assert sdm.total_timer == 0.0


def test_start_rearm():
    """Verify start_rearm caches departure coords and starts atmospheric ascent."""
    sdm = SuperDestroyerManager()
    player = DummyPlayer(1200.0, 1800.0, 90.0)

    success = sdm.start_rearm(player)
    assert success is True
    assert sdm.phase == PHASE_ASCENT
    assert sdm.is_active is True
    assert sdm.is_controls_locked is True
    assert sdm.is_combat_paused is False
    assert sdm.departure_x == 1200.0
    assert sdm.departure_y == 1800.0
    assert sdm.departure_angle == 90.0
    assert sdm.total_timer == pytest.approx(TOTAL_REARM_DURATION, 0.01)

    # Cannot start again while active
    assert sdm.start_rearm(player) is False


def test_phase_transitions_full_cycle():
    """Verify exact 15.0s timing across all phases: Ascent -> Hangar -> Descent -> None."""
    sdm = SuperDestroyerManager()
    player = DummyPlayer(1500.0, 1500.0, 0.0)
    gsm = GroundSupportManager()
    gsm.weapon_menu.charges[AirStrikeType.STRAFE] = 0

    sdm.start_rearm(player)
    assert sdm.phase == PHASE_ASCENT

    # Advance 0.6s into Ascent (duration: 1.2s)
    sdm.update(0.6, player, gsm.weapon_menu)
    assert sdm.phase == PHASE_ASCENT
    assert sdm.is_controls_locked is True
    assert not sdm.is_combat_paused
    assert player.pos_y < 1500.0  # Climbed upward

    # Advance another 0.7s (total: 1.3s -> entered Hangar phase)
    sdm.update(0.7, player, gsm.weapon_menu)
    assert sdm.phase == PHASE_HANGAR
    assert sdm.is_combat_paused is True
    assert sdm.is_controls_locked is True

    # Advance 12.0s in Hangar (total hangar duration: 12.6s)
    sdm.update(12.0, player, gsm.weapon_menu)
    assert sdm.phase == PHASE_HANGAR
    assert sdm.is_combat_paused is True
    assert sdm.bomb_attached is True  # Ordnance attached

    # Advance another 1.0s (exceeds 12.6s -> enters Descent phase)
    sdm.update(1.0, player, gsm.weapon_menu)
    assert sdm.phase == PHASE_DESCENT
    assert sdm.is_combat_paused is False
    assert sdm.is_controls_locked is True

    # Advance 1.5s (descent completes, 15.0s total elapsed)
    sdm.update(1.5, player, gsm.weapon_menu)
    assert sdm.phase == PHASE_NONE
    assert sdm.is_active is False
    assert sdm.is_controls_locked is False
    assert sdm.is_combat_paused is False

    # Invulnerability frame granted
    assert player.invincible is True
    # Weapon charges restored
    assert gsm.weapon_menu.charges[AirStrikeType.STRAFE] == AirStrikeType.DATA[AirStrikeType.STRAFE]["max_charges"]


def test_combat_pause_protects_helldivers():
    """Verify that during Hangar phase, GroundSupportManager does not tick ground units or damage Helldivers."""
    gsm = GroundSupportManager()
    player = DummyPlayer(1500.0, 1500.0, 0.0)

    # Empty charges to allow rearm
    for st in gsm.active_loadout:
        gsm.weapon_menu.charges[st] = 0

    assert gsm.trigger_eagle_rearm(player) is True
    assert gsm.super_destroyer.is_active is True

    # Fast forward into Hangar phase
    gsm.super_destroyer.update(ASCENT_DURATION + 0.1, player, gsm.weapon_menu)
    assert gsm.super_destroyer.is_combat_paused is True

    # Initial helldiver health
    initial_healths = [u.health for u in gsm.units]

    # Attempt updating GroundSupportManager while in orbit
    gsm.update(1.0, player, [], None, None)

    # Verify Helldivers did not take any ticks/movement during orbital pause
    for unit, initial_hp in zip(gsm.units, initial_healths):
        assert unit.health == initial_hp


def test_stratagem_hero_input_and_scoring(tmp_path, monkeypatch):
    """Verify Stratagem Hero processes arrow inputs, scores combos, and persists high score."""
    temp_hs_file = str(tmp_path / "stratagem_hero_highscore.txt")
    monkeypatch.setenv("EAGLE1_USER_DATA_DIR", str(tmp_path))

    sdm = SuperDestroyerManager()
    player = DummyPlayer()

    # Input when inactive has no effect
    sdm.handle_hero_input("UP", player)
    assert sdm.hero_score == 0

    # Start rearm and skip to Hangar phase
    sdm.start_rearm(player)
    sdm.update(ASCENT_DURATION + 0.1, player)
    assert sdm.phase == PHASE_HANGAR

    # Set deterministic test sequence
    sdm.hero_sequence = ["UP", "DOWN", "RIGHT"]
    sdm.hero_index = 0
    sdm.hero_score = 0

    # Step 1: Correct input 'UP'
    sdm.handle_hero_input("UP", player)
    assert sdm.hero_index == 1
    assert sdm.hero_score == 0

    # Step 2: Correct input 'DOWN'
    sdm.handle_hero_input("DOWN", player)
    assert sdm.hero_index == 2
    assert sdm.hero_score == 0

    # Step 3: Complete sequence with 'RIGHT'
    sdm.handle_hero_input("RIGHT", player)
    assert sdm.hero_score == 100
    assert player.score == 100
    assert sdm.hero_highscore == 100

    # Verify high score was saved to temp file
    assert os.path.exists(temp_hs_file)
    with open(temp_hs_file, "r") as f:
        assert f.read().strip() == "100"

    # Step 4: Wrong input resets sequence
    sdm.hero_sequence = ["UP", "UP"]
    sdm.hero_index = 0
    sdm.handle_hero_input("LEFT", player)
    assert sdm.hero_error_flash > 0.0


def test_ground_support_manager_rearm_guard():
    """Verify GroundSupportManager rejects rearm if stratagems are already full."""
    gsm = GroundSupportManager()
    player = DummyPlayer()

    # When all charges are at max, rearm cannot trigger
    assert gsm.trigger_eagle_rearm(player) is False
    assert not gsm.super_destroyer.is_active

    # Deplete one stratagem charge
    first_st = gsm.active_loadout[0]
    gsm.weapon_menu.charges[first_st] = 0

    # Now rearm succeeds
    assert gsm.trigger_eagle_rearm(player) is True
    assert gsm.super_destroyer.is_active is True


def test_cinematic_draw_all_phases():
    """Verify that drawing does not crash or fail in any cinematic phase."""
    sdm = SuperDestroyerManager(1280, 720)
    canvas = pygame.Surface((1280, 720))
    player = DummyPlayer()

    # Draw inactive
    sdm.draw(canvas, 1280, 720, player)

    # Draw Ascent
    sdm.start_rearm(player)
    assert sdm.phase == PHASE_ASCENT
    sdm.draw(canvas, 1280, 720, player)

    # Draw Hangar
    sdm.update(ASCENT_DURATION + 0.1, player)
    assert sdm.phase == PHASE_HANGAR
    sdm.draw(canvas, 1280, 720, player)

    # Draw Descent
    sdm.update(HANGAR_DURATION + 0.1, player)
    assert sdm.phase == PHASE_DESCENT
    sdm.draw(canvas, 1280, 720, player)

