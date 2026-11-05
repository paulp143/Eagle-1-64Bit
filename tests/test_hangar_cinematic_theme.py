"""Tests for the re-themed hangar cinematic (fonts, glyphs, zero per-frame allocations)."""

import pygame
import pytest

from eagle1.systems.hangar_cinematic import (
    ARROW_SYMBOLS,
    ASCENT_DURATION,
    HANGAR_DURATION,
    SuperDestroyerManager,
)


class _Player:
    """Lightweight player stand-in (mirrors the one in test_hangar_cinematic.py)."""

    def __init__(self):
        self.pos_x = 1500.0
        self.pos_y = 1500.0
        self.x = 1500
        self.y = 1500
        self.angle = 45.0
        self.velocity_x = 4.0
        self.velocity_y = 4.0
        self.score = 0
        self.health = 5
        self.shield = 20.0
        self.invincible = False
        self.invincible_timer = 0
        self.original_image = None


def _frames(sdm, canvas, player):
    sdm.draw(canvas, 1280, 720, player)


def test_fonts_are_at_least_12px():
    sdm = SuperDestroyerManager(1280, 720)
    for font in (sdm.font_title, sdm.font_large, sdm.font_med, sdm.font_small, sdm.font_arrow):
        assert font is not None and font.get_height() >= 13


def test_arrow_symbols_use_supported_glyphs():
    assert ARROW_SYMBOLS == {"UP": "▲", "DOWN": "▼", "LEFT": "◀", "RIGHT": "▶"}


def test_static_terminal_texts_do_not_use_unsupported_glyphs():
    sdm = SuperDestroyerManager(1280, 720)
    assert sdm._static_texts.get("hint") is not None
    assert len(sdm._marquee_variants) == 8


def test_crt_scanline_overlay_matches_crt_rect():
    sdm = SuperDestroyerManager(1280, 720)
    assert sdm.crt_scanline_surface.get_size() == (408, 438)


def test_draw_every_phase_allocates_no_surfaces_after_warmup(monkeypatch):
    sdm = SuperDestroyerManager(1280, 720)
    canvas = pygame.Surface((1280, 720))
    player = _Player()
    sdm.start_rearm(player)
    for dt, phase in ((0.05, "ascent"), (ASCENT_DURATION, "hangar"), (HANGAR_DURATION, "descent")):
        sdm.update(dt, player)
        if phase == "hangar":
            sdm._spawn_steam(900, 500, count=6)
            sdm.update(0.001, player)
        _frames(sdm, canvas, player)

    sdm.start_rearm(player)

    def _raise(*args, **kwargs):
        raise AssertionError("allocation in draw")

    monkeypatch.setattr(pygame, "Surface", _raise)
    monkeypatch.setattr(pygame.font, "SysFont", _raise)
    sdm.update(0.05, player)
    _frames(sdm, canvas, player)
    sdm.update(ASCENT_DURATION, player)
    sdm._spawn_steam(900, 500, count=4)
    sdm.update(0.001, player)
    _frames(sdm, canvas, player)
    sdm.update(HANGAR_DURATION, player)
    _frames(sdm, canvas, player)


def test_crane_pose_hoists_round_to_airframe_and_returns_home():
    from eagle1.systems.hangar_cinematic import ARM_DOWN_Y, ARM_HOME_Y, SHIP_CX, TROLLEY_HOME_X, crane_pose

    assert crane_pose(0.0) == pytest.approx((TROLLEY_HOME_X, ARM_HOME_Y, 0.0))
    assert crane_pose(3.5) == pytest.approx((SHIP_CX, ARM_DOWN_Y, 0.0))
    assert crane_pose(4.0) == pytest.approx((SHIP_CX, ARM_DOWN_Y, 1.0))
    assert crane_pose(12.0) == pytest.approx((TROLLEY_HOME_X, ARM_HOME_Y, 0.0))
    assert crane_pose(-1.0) == pytest.approx(crane_pose(0.0))


def test_crane_pose_and_wing_arms_move_continuously_and_stay_in_range():
    from eagle1.systems.hangar_cinematic import ARM_DOWN_Y, ARM_HOME_Y, crane_pose, wing_arm_extension

    prev_pose, prev_ext = crane_pose(0.0), wing_arm_extension(0.0)
    for step in range(1, 1301):
        t = step * 0.01
        pose, ext = crane_pose(t), wing_arm_extension(t)
        assert ARM_HOME_Y - 1e-6 <= pose[1] <= ARM_DOWN_Y + 1e-6
        assert -1e-9 <= pose[2] <= 1.0 + 1e-9 and -1e-9 <= ext <= 1.0 + 1e-9
        assert abs(pose[0] - prev_pose[0]) < 5.0 and abs(pose[1] - prev_pose[1]) < 5.0
        assert abs(ext - prev_ext) < 0.03
        prev_pose, prev_ext = pose, ext


def test_wing_arms_extend_only_during_service_window():
    from eagle1.systems.hangar_cinematic import wing_arm_extension

    assert wing_arm_extension(4.0) == pytest.approx(0.0)
    assert wing_arm_extension(6.0) == pytest.approx(1.0)
    assert wing_arm_extension(8.0) == pytest.approx(0.0)


def test_two_link_elbow_respects_link_lengths_and_stays_finite():
    import math

    from eagle1.systems.hangar_cinematic import _two_link_elbow

    ex, ey = _two_link_elbow(0.0, 0.0, 100.0, 0.0, 84.0, 70.0, -1)
    assert math.hypot(ex, ey) == pytest.approx(84.0, abs=0.05)
    assert math.hypot(ex - 100.0, ey) == pytest.approx(70.0, abs=0.05)
    assert ey < 0  # bend=-1 lifts the elbow above a left-to-right reach
    assert _two_link_elbow(0.0, 0.0, 100.0, 0.0, 84.0, 70.0, 1)[1] > 0
    for target in ((500.0, 0.0), (0.0, 0.0), (1.0, 1.0)):
        assert all(math.isfinite(v) for v in _two_link_elbow(0.0, 0.0, *target, 84.0, 70.0, -1))


def test_hero_highscore_saved_atomically(tmp_path, monkeypatch):
    monkeypatch.setenv("EAGLE1_USER_DATA_DIR", str(tmp_path))
    sdm = SuperDestroyerManager(1280, 720)
    assert sdm.hero_highscore == 0
    sdm.hero_highscore = 4200
    sdm._save_hero_highscore()
    assert sorted(p.name for p in tmp_path.iterdir()) == ["stratagem_hero_highscore.txt"]
    assert SuperDestroyerManager(1280, 720).hero_highscore == 4200
    (tmp_path / "stratagem_hero_highscore.txt").write_bytes(b"\xff\xfe")
    assert SuperDestroyerManager(1280, 720).hero_highscore == 0


def test_hangar_draws_every_rearm_stage_without_errors():
    sdm = SuperDestroyerManager(1280, 720)
    canvas = pygame.Surface((1280, 720))
    player = _Player()
    sdm.start_rearm(player)
    sdm.update(ASCENT_DURATION + 0.01, player)
    for stamp in (0.5, 2.5, 3.6, 4.2, 5.6, 7.0, 9.0, 12.0):
        sdm.update(stamp - sdm.phase_timer, player)
        _frames(sdm, canvas, player)
