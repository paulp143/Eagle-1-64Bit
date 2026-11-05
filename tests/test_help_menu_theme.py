"""Tests for the re-themed HelpMenu: no overflow, cached pages, keyboard handling."""

import pygame

from eagle1.ui import help_menu as hm
from eagle1.ui.help_menu import HelpMenu
from eagle1.ui.layout import validate_rects_no_overlap


def _key(key, mod=0):
    return pygame.event.Event(pygame.KEYDOWN, key=key, mod=mod)


def test_tab_labels_fit_their_tabs():
    menu = HelpMenu(1280, 720)
    for name, rect in zip(menu.TAB_NAMES, menu.tab_rects):
        assert menu.font_subtitle.size(name)[0] <= rect.w - 16


def test_tabs_and_close_button_do_not_overlap():
    menu = HelpMenu(1280, 720)
    assert validate_rects_no_overlap(menu.tab_rects + [menu.close_btn_rect]) == []


def test_second_draw_reuses_cached_page(dummy_surface):
    menu = HelpMenu(1280, 720)
    menu.draw(dummy_surface)
    page = menu._page_cache[menu.active_tab]
    menu.draw(dummy_surface)
    assert menu._page_cache[menu.active_tab] is page


def test_draw_all_tabs_allocates_no_surfaces_after_warmup(dummy_surface, monkeypatch):
    menu = HelpMenu(1280, 720)
    for tab in range(len(menu.TAB_NAMES)):
        menu.active_tab = tab
        menu.draw(dummy_surface, (100, 100))

    def _raise(*args, **kwargs):
        raise AssertionError("allocation in draw")

    monkeypatch.setattr(pygame, "Surface", _raise)
    monkeypatch.setattr(pygame.font, "SysFont", _raise)
    for _ in range(2):
        for tab in range(len(menu.TAB_NAMES)):
            menu.active_tab = tab
            menu.draw(dummy_surface, (100, 100))


def test_intel_cards_fit_without_clipping():
    menu = HelpMenu(1280, 720)
    rect = pygame.Rect(0, 0, *menu.content_rect.size)
    col_w = (rect.width - 24) // 2
    start_y = rect.y + 56
    card_h = (rect.height - (start_y - rect.y) - 14 - 10) // 2
    for card in hm.WAVE_CARDS + hm.SQUAD_CARDS:
        assert menu.measure_intel_card(card, col_w) <= card_h, card["title"]


def test_controls_tab_fits_and_lists_all_bindings():
    menu = HelpMenu(1280, 720)
    available = menu.content_rect.height - 76
    assert menu.controls_page_height_needed() <= available
    assert menu.system_notes_height_needed() <= available


def test_ability_text_is_not_truncated():
    menu = HelpMenu(1280, 720)
    col_w = (menu.content_rect.width - 24) // 2
    for item in hm.ABILITY_COLUMN_1 + hm.ABILITY_COLUMN_2:
        assert menu.font_heading.size(item["stats"])[0] <= col_w - 28, item["name"]
        assert len(menu.__class__.__mro__) and len(item["desc"]) > 0


def test_weapon_cards_fit_vertically():
    menu = HelpMenu(1280, 720)
    last_bottom = 56 + len(hm.WEAPONS) * (100 + 5)
    assert last_bottom <= menu.content_rect.height


def test_shift_tab_goes_back_and_wraps():
    menu = HelpMenu(1280, 720)
    assert menu.handle_event(_key(pygame.K_TAB, pygame.KMOD_SHIFT)) == "tab_changed"
    assert menu.active_tab == 5


def test_clicking_active_tab_returns_none():
    menu = HelpMenu(1280, 720)
    pos = menu.tab_rects[menu.active_tab].center
    click = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=pos)
    assert menu.handle_event(click, pos) is None


def test_number_keys_and_close():
    menu = HelpMenu(1280, 720)
    assert menu.handle_event(_key(pygame.K_4)) == "tab_changed"
    assert menu.active_tab == menu.TAB_CONTROLS
    assert menu.handle_event(_key(pygame.K_ESCAPE)) == "close"


def test_intel_card_footers_are_not_truncated():
    menu = HelpMenu(1280, 720)
    col_w = (menu.content_rect.width - 24) // 2
    for card in hm.WAVE_CARDS + hm.SQUAD_CARDS:
        footer = card["footer"]
        assert menu.font_body.size(footer)[0] <= col_w - 40, footer
