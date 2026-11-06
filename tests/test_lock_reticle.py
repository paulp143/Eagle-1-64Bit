"""Tests for the allocation-free target-lock brackets."""

import pygame

from eagle1.ui import theme
from eagle1.ui.lock_reticle import LOCK_BRACKET_PAD, LOCK_LABEL_GAP, draw_lock_brackets


def _surface():
    surface = pygame.Surface((100, 100))
    surface.fill((0, 0, 0))
    return surface


def test_draw_lock_brackets_paints_corner_in_danger_color():
    surface = _surface()
    draw_lock_brackets(surface, pygame.Rect(20, 20, 40, 40))
    corner = (20 - LOCK_BRACKET_PAD, 20 - LOCK_BRACKET_PAD)
    assert tuple(surface.get_at(corner))[:3] == theme.DANGER


def test_draw_lock_brackets_without_label_does_not_raise():
    surface = _surface()
    draw_lock_brackets(surface, pygame.Rect(20, 20, 40, 40), None)
    # Center of the target stays untouched (brackets only mark the corners).
    assert tuple(surface.get_at((40, 40)))[:3] == (0, 0, 0)


def test_draw_lock_brackets_blits_label_above():
    surface = _surface()
    label = pygame.Surface((10, 4))
    label.fill((255, 255, 255))
    draw_lock_brackets(surface, pygame.Rect(20, 30, 40, 40), label)
    label_y = 30 - LOCK_BRACKET_PAD - LOCK_LABEL_GAP
    assert tuple(surface.get_at((40, label_y + 1)))[:3] == (255, 255, 255)
