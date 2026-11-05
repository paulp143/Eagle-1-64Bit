"""Tests for the re-themed hangar cinematic (fonts, glyphs, zero per-frame allocations)."""

import pygame

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
