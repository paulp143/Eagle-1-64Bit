"""Tests for the allocation-free UI widget primitives."""

import pygame

from eagle1.ui import theme, widgets


def _font():
    return theme.get_font("body")


def test_make_overlay_is_srcalpha_and_filled():
    surf = widgets.make_overlay((10, 10), (1, 2, 3, 4))
    assert surf.get_flags() & pygame.SRCALPHA
    assert tuple(surf.get_at((0, 0))) == (1, 2, 3, 4)


def test_draw_panel_draws_brackets_in_accent(dummy_surface):
    dummy_surface.fill((0, 0, 0))
    widgets.draw_panel(dummy_surface, pygame.Rect(100, 100, 200, 100))
    assert tuple(dummy_surface.get_at((100, 100)))[:3] == theme.ACCENT
    assert tuple(dummy_surface.get_at((200, 150)))[:3] == theme.PANEL


def test_draw_panel_zero_size_is_noop(dummy_surface):
    widgets.draw_panel(dummy_surface, pygame.Rect(0, 0, 0, 0))


def test_draw_bar_clamps_ratio(dummy_surface):
    rect = pygame.Rect(50, 50, 100, 10)
    widgets.draw_bar(dummy_surface, rect, 2.0, theme.SUCCESS)
    assert tuple(dummy_surface.get_at((rect.right - 2, rect.centery)))[:3] == theme.SUCCESS
    widgets.draw_bar(dummy_surface, rect, float("nan"), theme.SUCCESS)
    assert tuple(dummy_surface.get_at((rect.x + 2, rect.centery)))[:3] == theme.PANEL_RAISED


def test_fit_text_short_unchanged_and_long_ellipsized():
    font = _font()
    assert widgets.fit_text(font, "HI", 500) == "HI"
    out = widgets.fit_text(font, "A VERY LONG LABEL THAT CANNOT FIT", 80)
    assert out.endswith(widgets.ELLIPSIS)
    assert font.size(out)[0] <= 80


def test_wrap_text_px_respects_width():
    font = _font()
    lines = widgets.wrap_text_px(font, "alpha beta gamma delta epsilon zeta eta theta iota kappa", 200)
    assert len(lines) > 1
    assert all(font.size(line)[0] <= 200 for line in lines)


def test_wrap_text_px_max_lines_adds_ellipsis():
    font = _font()
    lines = widgets.wrap_text_px(font, "word " * 60, 150, max_lines=2)
    assert len(lines) == 2
    assert lines[-1].endswith(widgets.ELLIPSIS)


def test_wrap_text_px_long_token_kept_whole():
    font = _font()
    token = "X" * 80
    assert widgets.wrap_text_px(font, token, 50) == [token]


def test_text_cache_returns_same_surface_and_evicts():
    font = _font()
    cache = widgets.TextCache(max_entries=2)
    a = cache.render(font, "A", (255, 255, 255))
    assert cache.render(font, "A", (255, 255, 255)) is a
    cache.render(font, "B", (255, 255, 255))
    cache.render(font, "C", (255, 255, 255))
    assert len(cache) == 2


def test_draw_functions_allocate_no_surfaces(dummy_surface, monkeypatch):
    font = theme.get_font("mono_small")
    cache = widgets.TextCache()
    rect = pygame.Rect(10, 10, 120, 40)
    widgets.draw_key_badge(dummy_surface, cache, font, "ESC", (5, 5))

    def _raise(*args, **kwargs):
        raise AssertionError("Surface allocated")

    monkeypatch.setattr(pygame, "Surface", _raise)
    widgets.draw_panel(dummy_surface, rect)
    widgets.draw_bar(dummy_surface, rect, 0.5, theme.INFO, segments=4)
    widgets.draw_brackets(dummy_surface, rect)
    widgets.draw_focus_bar(dummy_surface, rect)
    widgets.draw_key_badge(dummy_surface, cache, font, "ESC", (5, 5))
