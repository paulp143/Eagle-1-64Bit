"""Allocation-free target-lock brackets drawn around radar-locked aerial targets."""

from typing import Optional

import pygame

from eagle1.ui import theme

LOCK_BRACKET_PAD = 6
LOCK_BRACKET_LEN = 8
LOCK_BRACKET_THICKNESS = 2
LOCK_LABEL_GAP = 14


def draw_lock_brackets(surface: pygame.Surface, screen_rect: pygame.Rect,
                       label: Optional[pygame.Surface] = None) -> None:
    """Draw four corner brackets around `screen_rect` and an optional label centered above them."""
    x = screen_rect.x - LOCK_BRACKET_PAD
    y = screen_rect.y - LOCK_BRACKET_PAD
    w = screen_rect.width + 2 * LOCK_BRACKET_PAD
    h = screen_rect.height + 2 * LOCK_BRACKET_PAD
    length = LOCK_BRACKET_LEN
    width = LOCK_BRACKET_THICKNESS
    color = theme.DANGER

    pygame.draw.line(surface, color, (x, y), (x + length, y), width)
    pygame.draw.line(surface, color, (x, y), (x, y + length), width)
    pygame.draw.line(surface, color, (x + w, y), (x + w - length, y), width)
    pygame.draw.line(surface, color, (x + w, y), (x + w, y + length), width)
    pygame.draw.line(surface, color, (x, y + h), (x + length, y + h), width)
    pygame.draw.line(surface, color, (x, y + h), (x, y + h - length), width)
    pygame.draw.line(surface, color, (x + w, y + h), (x + w - length, y + h), width)
    pygame.draw.line(surface, color, (x + w, y + h), (x + w, y + h - length), width)

    if label is not None:
        surface.blit(label, (x + w // 2 - label.get_width() // 2, y - LOCK_LABEL_GAP))
