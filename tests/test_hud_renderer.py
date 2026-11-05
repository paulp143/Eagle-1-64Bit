"""Tests for the HudRenderer (status cluster, banners, objectives, score)."""

import pygame

from eagle1.ui import hud_layout, theme
from eagle1.ui.hud import HudRenderer


def _status(hud, surface, **overrides):
    args = dict(shield=20, max_shield=20, overshield=False, hull=5, max_hull=5, critical_hull=2,
                wave=3, max_waves=5, hostiles=2)
    args.update(overrides)
    hud.draw_status_panel(surface, args["shield"], args["max_shield"], args["overshield"],
                          args["hull"], args["max_hull"], args["critical_hull"],
                          args["wave"], args["max_waves"], args["hostiles"])


def test_full_shield_draws_info_color_inside_bar(dummy_surface):
    dummy_surface.fill((0, 0, 0))
    hud = HudRenderer()
    _status(hud, dummy_surface)
    rect = hud_layout.STATUS_PANEL
    # shield bar: x=rect.x+12.., y=rect.y+4+21 .. +8; sample a point inside the filled part
    assert tuple(dummy_surface.get_at((rect.x + 14, rect.y + 25 + 4)))[:3] == theme.INFO


def test_hull_bar_turns_danger_at_critical(dummy_surface):
    dummy_surface.fill((0, 0, 0))
    hud = HudRenderer()
    _status(hud, dummy_surface, hull=2)
    rect = hud_layout.STATUS_PANEL
    assert tuple(dummy_surface.get_at((rect.x + 14, rect.y + 34 + 21 + 4)))[:3] == theme.DANGER


def test_unlimited_waves_do_not_show_999():
    surface = pygame.Surface((1280, 720))
    hud = HudRenderer()
    _status(hud, surface, wave=3, max_waves=999)
    keys = [k[1] for k in hud._cache._items]
    assert "WAVE 3" in keys
    assert not any("/999" in k for k in keys)


def test_academy_hides_wave_row():
    surface = pygame.Surface((1280, 720))
    hud = HudRenderer()
    _status(hud, surface, wave=None, max_waves=None, hostiles=None)
    assert not any(str(k[1]).startswith("WAVE") for k in hud._cache._items)


def test_wave_banner_rebuilt_only_on_text_change(dummy_surface):
    hud = HudRenderer()
    hud.draw_wave_banner(dummy_surface, "WAVE 1")
    first = hud._banner_surf
    hud.draw_wave_banner(dummy_surface, "WAVE 1")
    assert hud._banner_surf is first
    hud.draw_wave_banner(dummy_surface, "WAVE 2")
    assert hud._banner_surf is not first


def test_hud_draws_allocate_nothing_after_warmup(dummy_surface, monkeypatch):
    hud = HudRenderer()
    objective = hud._cache.render(hud._font_label, "> TEST", theme.TEXT)

    def frame():
        hud.draw_score(dummy_surface, 1200, 5000)
        _status(hud, dummy_surface)
        hud.draw_adrenaline(dummy_surface, 1000)
        hud.draw_wave_banner(dummy_surface, "WAVE 1")
        hud.draw_objective_banner(dummy_surface, "OBJECTIVE: TEST", theme.ACCENT)
        hud.draw_campaign_objective(dummy_surface, objective)

    frame()

    def _raise(*args, **kwargs):
        raise AssertionError("allocation in HUD draw")

    monkeypatch.setattr(pygame, "Surface", _raise)
    monkeypatch.setattr(pygame.font, "SysFont", _raise)
    for _ in range(60):
        frame()


def test_adrenaline_and_objective_use_hud_zones(dummy_surface):
    dummy_surface.fill((0, 0, 0))
    hud = HudRenderer()
    hud.draw_adrenaline(dummy_surface, 0)
    rect = hud_layout.ADRENALINE_RECT
    assert tuple(dummy_surface.get_at((rect.x, rect.centery)))[:3] == theme.DANGER


def test_weapon_panel_shows_reloading_text_when_reloading(dummy_surface):
    hud = HudRenderer()
    hud.draw_weapon_panel(dummy_surface, 0, 200, True, 0, 4, 0.5, "CONE")
    keys = [k[1] for k in hud._cache._items]
    assert keys.count("RELOADING") >= 1


def test_minimap_surface_is_reused_and_base_built_once():
    hud = HudRenderer()
    bg = pygame.Surface((68, 68))
    bg.fill((10, 20, 30))
    first = hud.get_minimap_surface(bg)
    base = hud._minimap_base
    second = hud.get_minimap_surface(bg)
    assert first is second
    assert hud._minimap_base is base


def test_minimap_surface_resets_blips_each_call():
    hud = HudRenderer()
    bg = pygame.Surface((68, 68))
    bg.fill((10, 20, 30))
    surf = hud.get_minimap_surface(bg)
    pygame.draw.circle(surf, (255, 0, 0), (80, 80), 5)
    surf = hud.get_minimap_surface(bg)
    assert tuple(surf.get_at((80, 80)))[:3] != (255, 0, 0)


def test_overlay_helpers_are_cached():
    hud = HudRenderer()
    assert hud.get_slowmo_overlay() is hud.get_slowmo_overlay()
    assert hud.get_frost_overlay((20, 20)) is hud.get_frost_overlay((20, 20))
    assert hud.get_lock_label("CONE LOCK") is hud.get_lock_label("CONE LOCK")


def test_weapon_speed_hint_minimap_allocate_nothing_after_warmup(dummy_surface, monkeypatch):
    hud = HudRenderer()
    bg = pygame.Surface((68, 68))

    def frame():
        hud.draw_weapon_panel(dummy_surface, 120, 200, False, 3, 4, None, "OMNI")
        hud.draw_speed(dummy_surface, 3.5, 7.0)
        hud.draw_controls_hint(dummy_surface)
        hud.get_minimap_surface(bg)
        hud.draw_minimap_frame(dummy_surface)

    frame()

    def _raise(*args, **kwargs):
        raise AssertionError("allocation in HUD draw")

    monkeypatch.setattr(pygame, "Surface", _raise)
    for _ in range(30):
        frame()


def test_game_draw_has_no_hud_surface_allocations_left():
    import inspect

    from eagle1.app import game

    source = inspect.getsource(game.draw)
    assert "vignette_surf = pygame.Surface" not in source
    assert "ice_surf = pygame.Surface" not in source
    assert "minimap_surface = pygame.Surface" not in source
    assert "dim_overlay = pygame.Surface" not in source
