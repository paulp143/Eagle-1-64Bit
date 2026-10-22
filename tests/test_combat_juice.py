"""Unit tests for Task 5: Combat Juice & Kinesthetic Feedback."""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from eagle1.effects import CombatJuiceManager, ScreenShake


def test_screen_shake_triggers_and_decays_to_zero():
    """ScreenShake should generate non-zero camera offsets when triggered and decay cleanly to (0, 0)."""
    shake = ScreenShake()
    assert shake.get_offset() == (0, 0)

    # Trigger cannon micro-shake (subtle)
    shake.trigger(intensity=2.5, duration_frames=4)
    assert shake.remaining_frames == 4
    assert shake.intensity == 2.5

    ox, oy = shake.get_offset()
    assert -3 <= ox <= 3
    assert -3 <= oy <= 3

    # Stronger impact overrides weaker active shake
    shake.trigger(intensity=9.0, duration_frames=12)
    assert shake.intensity == 9.0
    assert shake.remaining_frames == 12

    # Advance through all frames until decay completes
    for _ in range(12):
        shake.update()
    assert shake.remaining_frames == 0
    assert shake.get_offset() == (0, 0)


def test_wingtip_contrails_spawn_on_high_g_turn_and_stay_bounded():
    """Wingtip vapor contrails should emit when turning near Corner Speed and respect max particle bounds."""
    juice = CombatJuiceManager(max_contrail_nodes=40, max_sparks=80)
    assert len(juice.contrails) == 0

    # Straight flight (angular_delta = 0.0) should NOT emit high-G wingtip vapor
    juice.emit_wingtip_contrails(
        cx=1500.0, cy=1500.0, angle_deg=0.0, speed=4.5, angular_delta=0.0
    )
    assert len(juice.contrails) == 0

    # High-G turn near Corner Speed (speed = 4.5, angular_delta = 3.5 deg) emits 2 wingtip nodes
    juice.emit_wingtip_contrails(
        cx=1500.0, cy=1500.0, angle_deg=45.0, speed=4.5, angular_delta=3.5
    )
    assert len(juice.contrails) == 2

    # Emit repeatedly to verify hard cap prevents unbounded list growth
    for i in range(30):
        juice.emit_wingtip_contrails(
            cx=1500.0 + i, cy=1500.0, angle_deg=45.0, speed=4.5, angular_delta=3.5
        )
    assert len(juice.contrails) <= 40

    # Advance frames and verify contrails age and expire
    for _ in range(25):
        juice.update()
    assert len(juice.contrails) == 0


def test_directional_hit_sparks_distinguish_deflection_vs_critical_engine_hit():
    """Hit sparks should distinguish armored nose deflections (cyan/white) from rear critical hits (orange/fire)."""
    juice = CombatJuiceManager(max_contrail_nodes=40, max_sparks=60)

    # 1. Armored deflection (damage_ratio <= 0.60)
    juice.spawn_hit_sparks(x=1000.0, y=1000.0, damage_ratio=0.50)
    assert len(juice.sparks) > 0
    deflect_spark = juice.sparks[0]
    assert deflect_spark["kind"] == "deflect"
    # Deflection sparks have high blue/white channel
    assert deflect_spark["color"][2] >= 200

    juice.reset()
    assert len(juice.sparks) == 0

    # 2. Rear engine critical hit (damage_ratio >= 1.15)
    juice.spawn_hit_sparks(x=1000.0, y=1000.0, damage_ratio=1.25)
    assert len(juice.sparks) > 0
    crit_spark = juice.sparks[0]
    assert crit_spark["kind"] == "critical"
    # Critical engine fire sparks are bright red/orange/gold (R >= 240, B <= 100)
    assert crit_spark["color"][0] >= 240
    assert crit_spark["color"][2] <= 100


def test_combat_juice_headless_render_succeeds():
    """Drawing contrails and hit sparks onto a Pygame surface should execute cleanly with camera offsets."""
    pygame.init()
    surface = pygame.Surface((1280, 720))
    juice = CombatJuiceManager()

    juice.emit_wingtip_contrails(cx=500.0, cy=400.0, angle_deg=90.0, speed=4.5, angular_delta=3.8)
    juice.spawn_hit_sparks(x=520.0, y=410.0, damage_ratio=1.25)
    juice.spawn_hit_sparks(x=480.0, y=390.0, damage_ratio=0.50)

    juice.draw(surface, camera_x=100, camera_y=100)
    juice.update()
    assert len(juice.contrails) > 0
    assert len(juice.sparks) > 0


def test_screen_shake_clamps_extreme_intensity():
    """Shake intensity should clamp safely to MAX_OFFSET_PIXELS to prevent camera disorientation."""
    shake = ScreenShake()
    shake.trigger(intensity=999.0, duration_frames=10)
    assert shake.intensity == ScreenShake.MAX_OFFSET_PIXELS
    ox, oy = shake.get_offset()
    assert abs(ox) <= ScreenShake.MAX_OFFSET_PIXELS * 1.2
    assert abs(oy) <= ScreenShake.MAX_OFFSET_PIXELS * 1.2


def test_screen_shake_phase_advancement_and_reset():
    """Harmonic phase advances every update and clears on reset."""
    shake = ScreenShake()
    shake.trigger(intensity=10.0, duration_frames=8)
    initial_phase = shake.phase
    shake.update()
    assert shake.phase == initial_phase + shake.frequency

    shake.reset()
    assert shake.phase == 0.0
    assert shake.intensity == 0.0
    assert shake.remaining_frames == 0
    assert shake.get_offset() == (0, 0)

