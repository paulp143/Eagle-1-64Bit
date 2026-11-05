"""Tests for the restyled ground-support HUD and arsenal menu."""

import pygame

from eagle1.systems.ground_support import AirStrikeWeaponMenu, GroundSupportManager
from eagle1.ui import hud_layout


class _Player:
    pos_x = 1500.0
    pos_y = 1500.0
    reloading = False


def _manager():
    return GroundSupportManager()


def test_draw_reticle_while_aiming_never_creates_fonts(dummy_surface, monkeypatch):
    from eagle1.app import game

    game.respawn()
    mgr = game.ground_support_manager
    mgr.equipped_slot = 1
    mgr.aiming_active = True
    mgr.slow_mo_energy = 2.0
    cam_x = max(0, min(game.MAP_WIDTH - 1280, game.player.pos_x - 640))
    cam_y = max(0, min(game.MAP_HEIGHT - 720, game.player.pos_y - 360))
    mgr.draw_reticle(dummy_surface, cam_x, cam_y, game.player)  # warm-up (fills the text cache)

    def _raise(*args, **kwargs):
        raise AssertionError("font created in draw")

    monkeypatch.setattr(pygame.font, "SysFont", _raise)
    monkeypatch.setattr(pygame.font, "Font", _raise)
    mgr.draw_reticle(dummy_surface, cam_x, cam_y, game.player)
    texts = [k[1] for k in mgr._hud_cache._items]
    assert "RELEASE TO DEPLOY" in texts


def test_arsenal_menu_text_has_no_stale_1_8_hint(dummy_surface):
    menu = AirStrikeWeaponMenu()
    menu.is_open = True
    menu.draw(dummy_surface, (10, 10))
    keys = [k[1] for k in menu._cache._items]
    assert not any("1-8" in k for k in keys)
    assert any("CLICK A STRATAGEM" in k for k in keys)


def test_draw_hud_twice_allocates_no_surfaces_after_warmup(dummy_surface, monkeypatch):
    mgr = _manager()
    player = _Player()
    font = None
    mgr.draw_hud(dummy_surface, 1280, 720, font, font, font, font, player, (10, 10))

    def _raise(*args, **kwargs):
        raise AssertionError("allocation in draw_hud")

    monkeypatch.setattr(pygame, "Surface", _raise)
    monkeypatch.setattr(pygame.font, "SysFont", _raise)
    for _ in range(3):
        mgr.draw_hud(dummy_surface, 1280, 720, font, font, font, font, player, (10, 10))


def test_danger_banner_has_no_emoji_variation_selector(dummy_surface):
    mgr = _manager()
    mgr.danger_alert_timer = 1.0
    mgr.danger_alert_text = "ENEMY AIRCRAFT CLOSING"
    mgr.draw_hud(dummy_surface, 1280, 720, None, None, None, None, _Player(), None)
    for _, text, _ in mgr._hud_cache._items:
        assert "️" not in text and "⚠" not in text


def test_hero_panel_uses_supported_arrow_glyphs(dummy_surface):
    mgr = _manager()
    mgr.weapon_menu.is_rearming = True
    mgr.hero_sequence = ["UP", "DOWN", "LEFT", "RIGHT"]
    mgr.hero_index = 1
    mgr.draw_hud(dummy_surface, 1280, 720, None, None, None, None, _Player(), None)
    texts = [k[1] for k in mgr._hud_cache._items]
    assert "◀" in texts and "▶" in texts
    assert "◄" not in texts and "►" not in texts


def test_dock_and_panels_stay_inside_their_zones(dummy_surface):
    mgr = _manager()
    mgr.draw_hud(dummy_surface, 1280, 720, None, None, None, None, _Player(), None)
    assert hud_layout.SQUAD_PANEL.top > hud_layout.STATUS_PANEL.bottom
    assert not hud_layout.SQUAD_PANEL.colliderect(hud_layout.STATUS_PANEL)
