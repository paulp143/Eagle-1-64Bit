"""Tests for MenuButton and MenuNavigator."""

import pygame

from eagle1.ui import theme, widgets
from eagle1.ui.menu_nav import MenuButton, MenuNavigator


def _buttons(sfx=None, disabled=()):
    out = []
    for i in range(4):
        out.append(MenuButton(f"B{i}", pygame.Rect(100, 100 + i * 60, 300, 48), hotkey=str(i),
                              enabled=i not in disabled, on_sfx=sfx))
    return out


def _key(key):
    return pygame.event.Event(pygame.KEYDOWN, key=key)


def test_disabled_button_not_hovered_or_clicked():
    b = MenuButton("X", pygame.Rect(0, 0, 100, 40), enabled=False)
    click = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(10, 10))
    assert b.is_hovered((10, 10)) is False
    assert b.is_clicked(click, (10, 10)) is False


def test_enabled_click_plays_sfx():
    calls = []
    b = MenuButton("X", pygame.Rect(0, 0, 100, 40), enabled=False, on_sfx=calls.append)
    b.set_enabled(True)
    click = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(10, 10))
    assert b.is_clicked(click, (10, 10)) is True
    assert calls == ["ui_click"]


def test_move_focus_skips_disabled():
    nav = MenuNavigator(_buttons(disabled=(1,)))
    nav.move_focus(1)
    assert nav.focus_index == 2


def test_wrap_and_no_wrap():
    nav = MenuNavigator(_buttons())
    nav.move_focus(-1)
    assert nav.focus_index == 3
    nav2 = MenuNavigator(_buttons(), wrap=False)
    nav2.move_focus(-1)
    assert nav2.focus_index == 0


def test_enter_returns_focus_index_and_disabled_returns_none():
    nav = MenuNavigator(_buttons())
    nav.handle_event(_key(pygame.K_DOWN))
    assert nav.handle_event(_key(pygame.K_RETURN)) == 1
    nav.buttons[1].set_enabled(False)
    assert nav.handle_event(_key(pygame.K_KP_ENTER)) is None


def test_click_returns_index_and_updates_focus():
    nav = MenuNavigator(_buttons())
    pos = nav.buttons[2].rect.center
    click = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=pos)
    assert nav.handle_event(click, pos) == 2
    assert nav.focus_index == 2


def test_mouse_motion_sets_focus():
    nav = MenuNavigator(_buttons())
    pos = nav.buttons[3].rect.center
    assert nav.handle_event(pygame.event.Event(pygame.MOUSEMOTION, pos=pos), pos) is None
    assert nav.focus_index == 3


def test_focused_draw_shows_focus_bar(dummy_surface):
    dummy_surface.fill((0, 0, 0))
    b = MenuButton("Focus", pygame.Rect(100, 100, 300, 48))
    b.draw(dummy_surface, None, focused=True)
    assert tuple(dummy_surface.get_at((101, 124)))[:3] == theme.ACCENT


def test_draw_allocates_no_surfaces_after_warmup(dummy_surface, monkeypatch):
    nav = MenuNavigator(_buttons())
    nav.draw(dummy_surface, (0, 0))

    def _raise(*args, **kwargs):
        raise AssertionError("Surface allocated")

    monkeypatch.setattr(pygame, "Surface", _raise)
    nav.draw(dummy_surface, (0, 0))


def test_empty_navigator_returns_none():
    nav = MenuNavigator([])
    assert nav.handle_event(_key(pygame.K_RETURN)) is None


def test_label_fit_is_computed_once_until_text_changes(dummy_surface, monkeypatch):
    from eagle1.ui import menu_nav

    calls = []
    real_fit = widgets.fit_text
    monkeypatch.setattr(menu_nav.widgets, "fit_text", lambda *a: calls.append(a) or real_fit(*a))
    btn = MenuButton("CONTINUE : CADET " + "W" * 18, pygame.Rect(0, 0, 360, 48), hotkey="C")
    for _ in range(5):
        btn.draw(dummy_surface)
    assert len(calls) == 1
    btn.set_text("CONTINUE : CADET ACE")
    btn.draw(dummy_surface)
    btn.draw(dummy_surface)
    assert len(calls) == 2
