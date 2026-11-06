"""Tests for the HUD zone layout."""

import pygame

from eagle1.ui import hud_layout
from eagle1.ui.layout import validate_rects_no_overlap


def test_zones_do_not_overlap():
    assert validate_rects_no_overlap(list(hud_layout.ALL_ZONES)) == []


def test_zones_inside_screen():
    screen = pygame.Rect(0, 0, 1280, 720)
    assert all(screen.contains(z) for z in hud_layout.ALL_ZONES)
    assert screen.contains(hud_layout.MILESTONE_BANNER_RECT)


def test_boss_bar_is_below_objective_banners():
    assert hud_layout.BOSS_BAR_RECT.top > hud_layout.CAMPAIGN_OBJECTIVE_Y + 22


def test_buff_bars_start_below_squad_panel():
    assert hud_layout.BUFF_BARS_ORIGIN[1] > hud_layout.SQUAD_PANEL.bottom


def test_milestone_banner_clear_of_hero_panel():
    assert not hud_layout.MILESTONE_BANNER_RECT.colliderect(hud_layout.HERO_PANEL_RECT)
    assert not hud_layout.MILESTONE_BANNER_RECT.colliderect(hud_layout.DANGER_BANNER_RECT)


def test_controls_hint_row_is_clear_of_dock_minimap_and_score():
    hint = hud_layout.CONTROLS_HINT_RECT
    for other in (hud_layout.WEAPON_DOCK_RECT, hud_layout.MINIMAP_RECT, hud_layout.SPEED_RECT, hud_layout.SCORE_RECT):
        assert not hint.colliderect(other)
