"""Tests for the restyled power-up HUD."""

import pygame

from eagle1.systems import powerups
from eagle1.systems.powerups import PowerUpManager
from eagle1.ui import hud_layout


def _manager_with_buff_and_banner():
    mgr = PowerUpManager()
    mgr.active_buffs = {"rapid_fire": 5.0}
    mgr.floating_popups = [{"text": "RAPID FIRE!", "color": (255, 255, 255), "timer": 1.0, "y_off": 10.0}]
    mgr.milestone_banner = {"title": "// MILESTONE 1,000 PTS REACHED! //", "sub": "COMMON: RAPID FIRE INCOMING!", "timer": 3.0}
    return mgr


def test_banner_surface_is_reused_across_frames(dummy_surface):
    mgr = _manager_with_buff_and_banner()
    mgr.draw_hud(dummy_surface, 1280, 720)
    first = mgr._banner_surf
    mgr.draw_hud(dummy_surface, 1280, 720)
    assert mgr._banner_surf is first


def test_draw_hud_allocates_no_surfaces_after_warmup(dummy_surface, monkeypatch):
    mgr = _manager_with_buff_and_banner()
    mgr.draw_hud(dummy_surface, 1280, 720)

    def _raise(*args, **kwargs):
        raise AssertionError("allocation in draw_hud")

    monkeypatch.setattr(pygame, "Surface", _raise)
    monkeypatch.setattr(pygame.font, "SysFont", _raise)
    for _ in range(5):
        mgr.draw_hud(dummy_surface, 1280, 720)


def test_buff_bars_start_below_squad_panel():
    assert hud_layout.BUFF_BARS_ORIGIN[1] > hud_layout.SQUAD_PANEL.bottom


def test_milestone_title_has_no_unsupported_star_glyph():
    mgr = PowerUpManager()
    mgr.check_milestones(1000, 1500.0, 1500.0)
    assert mgr.milestone_banner is not None
    assert "★" not in mgr.milestone_banner["title"]


def test_glow_and_tether_surfaces_are_cached(dummy_surface):
    a = powerups._get_glow_surface(12, (46, 204, 113), 90)
    assert powerups._get_glow_surface(12, (46, 204, 113), 90) is a
    drone = powerups.DroneCompanion()
    drone.draw(dummy_surface, 0, 0, 100, 100)
    cached = powerups._TETHER_CACHE[dummy_surface.get_size()]
    drone.draw(dummy_surface, 0, 0, 100, 100)
    assert powerups._TETHER_CACHE[dummy_surface.get_size()] is cached


def test_fonts_come_from_theme_and_are_at_least_12px():
    mgr = PowerUpManager()
    for font in (mgr.font_small, mgr.font_hud, mgr.font_banner):
        assert font is not None and font.get_height() >= 13
