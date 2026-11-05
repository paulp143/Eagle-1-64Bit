"""Tests for the restyled StratagemSelectMenu."""

import pygame

from eagle1.systems.ground_support import AirStrikeType, StratagemSelectMenu


def _key(key):
    return pygame.event.Event(pygame.KEYDOWN, key=key)


def test_number_keys_toggle_stratagems():
    menu = StratagemSelectMenu()
    before = list(menu.selected_stratagems)
    menu.handle_event(_key(pygame.K_1))
    assert AirStrikeType.ORDER[0] not in menu.selected_stratagems
    menu.handle_event(_key(pygame.K_1))
    assert AirStrikeType.ORDER[0] in menu.selected_stratagems
    assert len(menu.selected_stratagems) == len(before)


def test_arrow_keys_move_focus_within_grid():
    menu = StratagemSelectMenu()
    menu.handle_event(_key(pygame.K_LEFT))
    assert menu.focus_index == 0
    menu.handle_event(_key(pygame.K_RIGHT))
    assert menu.focus_index == 1
    menu.handle_event(_key(pygame.K_DOWN))
    assert menu.focus_index == 5
    menu.handle_event(_key(pygame.K_DOWN))
    assert menu.focus_index == 5
    menu.handle_event(_key(pygame.K_UP))
    assert menu.focus_index == 1


def test_enter_toggles_focused_card_and_returns_none():
    menu = StratagemSelectMenu()
    menu.focus_index = 0
    assert AirStrikeType.ORDER[0] in menu.selected_stratagems
    assert menu.handle_event(_key(pygame.K_RETURN)) is None
    assert AirStrikeType.ORDER[0] not in menu.selected_stratagems


def test_space_deploys_only_with_four_selected():
    menu = StratagemSelectMenu()
    result = menu.handle_event(_key(pygame.K_SPACE))
    assert result == list(menu.selected_stratagems) and len(result) == 4
    menu.toggle_stratagem(menu.selected_stratagems[0])
    assert menu.handle_event(_key(pygame.K_SPACE)) is None
    assert len(menu.selected_stratagems) == 3


def test_escape_returns_to_missions():
    assert StratagemSelectMenu().handle_event(_key(pygame.K_ESCAPE)) == "back_to_missions"


def test_draw_without_fonts_allocates_nothing_after_warmup(dummy_surface, monkeypatch):
    menu = StratagemSelectMenu()
    menu.draw(dummy_surface, (400, 300))

    def _raise(*args, **kwargs):
        raise AssertionError("allocation in draw")

    monkeypatch.setattr(pygame, "Surface", _raise)
    monkeypatch.setattr(pygame.font, "SysFont", _raise)
    for _ in range(3):
        menu.draw(dummy_surface, (400, 300))
