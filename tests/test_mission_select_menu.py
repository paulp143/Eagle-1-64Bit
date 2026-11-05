"""Tests for the extracted MissionSelectMenu."""

import pygame

from eagle1.app import game
from eagle1.ui.layout import validate_rects_no_overlap

menu = game.mission_select_menu


def _key(key):
    return pygame.event.Event(pygame.KEYDOWN, key=key)


def test_hotkeys_return_configs_in_order():
    for i, m_id in enumerate(menu.order):
        assert menu.handle_event(_key(pygame.K_1 + i)) is game.MISSION_CONFIGS[m_id]


def test_escape_returns_back_to_menu():
    assert menu.handle_event(_key(pygame.K_ESCAPE)) == "back_to_menu"


def test_arrows_and_enter_select_focused_config_with_wrap():
    menu.focus_index = 0
    menu.handle_event(_key(pygame.K_UP))
    assert menu.focus_index == len(menu.order) - 1
    assert menu.handle_event(_key(pygame.K_RETURN)) is game.MISSION_CONFIGS[menu.order[-1]]
    menu.focus_index = 0


def test_click_on_card_returns_config():
    m_id = menu.order[2]
    pos = menu.card_rects[m_id].center
    click = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=pos)
    assert menu.handle_event(click, pos) is game.MISSION_CONFIGS[m_id]
    assert menu.handle_event(click, (5, 5)) is None


def test_cards_do_not_overlap_and_fit_screen():
    rects = list(menu.card_rects.values())
    assert validate_rects_no_overlap(rects) == []
    screen = pygame.Rect(0, 0, game.GAME_WIDTH, game.GAME_HEIGHT)
    assert all(screen.contains(r) for r in rects)


def test_draw_allocates_no_surfaces_or_sysfonts(dummy_surface, monkeypatch):
    menu.draw(dummy_surface, (640, 300))

    def _raise(*args, **kwargs):
        raise AssertionError("allocation in draw")

    monkeypatch.setattr(pygame, "Surface", _raise)
    monkeypatch.setattr(pygame.font, "SysFont", _raise)
    for _ in range(3):
        menu.draw(dummy_surface, (640, 300))
