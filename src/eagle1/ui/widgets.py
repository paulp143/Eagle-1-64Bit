"""widgets.py - Allocation-free drawing primitives for the Military Terminal UI.

Everything here draws with ``pygame.draw`` / blits and never creates fonts or surfaces
per call. ``make_overlay`` is the only surface allocator and must be called at init time.
"""

from __future__ import annotations

from collections import OrderedDict
from typing import List, Optional, Sequence, Tuple

import pygame

from eagle1.ui import theme

ELLIPSIS = "…"


def make_overlay(size: Tuple[int, int], rgba: Tuple[int, int, int, int]) -> pygame.Surface:
    """Create a filled SRCALPHA surface. Call at init time only, never per frame."""
    surf = pygame.Surface(size, pygame.SRCALPHA)
    surf.fill(rgba)
    return surf


def draw_brackets(
    surface: pygame.Surface,
    rect: pygame.Rect,
    color: theme.RGB = theme.ACCENT,
    length: int = theme.BRACKET_LENGTH,
    thickness: int = theme.BRACKET_THICKNESS,
) -> None:
    """Draw L-shaped corner brackets inside ``rect``."""
    if rect.w <= 0 or rect.h <= 0:
        return
    length = max(1, min(length, rect.w // 2, rect.h // 2))
    t = thickness
    x0, y0, x1, y1 = rect.left, rect.top, rect.right, rect.bottom
    for cx, sx in ((x0, 1), (x1, -1)):
        for cy, sy in ((y0, 1), (y1, -1)):
            hx = cx if sx > 0 else cx - length
            hy = cy if sy > 0 else cy - t
            pygame.draw.rect(surface, color, (hx, hy, length, t))
            vx = cx if sx > 0 else cx - t
            vy = cy if sy > 0 else cy - length
            pygame.draw.rect(surface, color, (vx, vy, t, length))


def draw_panel(
    surface: pygame.Surface,
    rect: pygame.Rect,
    fill: Optional[theme.RGB] = theme.PANEL,
    border: Optional[theme.RGB] = theme.BORDER,
    accent: Optional[theme.RGB] = theme.ACCENT,
    brackets: bool = True,
) -> None:
    """Draw a sharp-cornered panel with optional border and accent brackets."""
    if fill is not None:
        pygame.draw.rect(surface, fill, rect)
    if border is not None:
        pygame.draw.rect(surface, border, rect, theme.BORDER_WIDTH)
    if brackets and accent is not None:
        draw_brackets(surface, rect, accent)


def draw_bar(
    surface: pygame.Surface,
    rect: pygame.Rect,
    ratio: float,
    fill: theme.RGB,
    bg: theme.RGB = theme.PANEL_RAISED,
    border: Optional[theme.RGB] = theme.BORDER,
    segments: int = 0,
) -> None:
    """Draw a horizontal gauge; ``ratio`` is clamped to 0..1 (NaN counts as 0)."""
    ratio = 0.0 if ratio != ratio else max(0.0, min(1.0, float(ratio)))
    pygame.draw.rect(surface, bg, rect)
    fill_w = int(rect.w * ratio)
    if fill_w > 0:
        pygame.draw.rect(surface, fill, (rect.x, rect.y, fill_w, rect.h))
    if segments > 1:
        for i in range(1, segments):
            sx = rect.x + rect.w * i // segments
            pygame.draw.rect(surface, theme.BG_DEEP, (sx, rect.y, 1, rect.h))
    if border is not None:
        pygame.draw.rect(surface, border, rect, theme.BORDER_WIDTH)


def draw_focus_bar(surface: pygame.Surface, rect: pygame.Rect, color: theme.RGB = theme.ACCENT) -> None:
    """Draw the vertical focus marker on the left edge of ``rect``."""
    pygame.draw.rect(surface, color, (rect.x, rect.y, theme.FOCUS_BAR_WIDTH, rect.h))


def fit_text(font: pygame.font.Font, text: str, max_width: int) -> str:
    """Return ``text`` shortened with an ellipsis so it fits ``max_width`` pixels."""
    if font.size(text)[0] <= max_width:
        return text
    trimmed = text
    while trimmed:
        trimmed = trimmed[:-1]
        if font.size(trimmed + ELLIPSIS)[0] <= max_width:
            return trimmed.rstrip() + ELLIPSIS
    return ELLIPSIS if font.size(ELLIPSIS)[0] <= max_width else ""


def wrap_text_px(
    font: pygame.font.Font, text: str, max_width: int, max_lines: Optional[int] = None
) -> List[str]:
    """Greedy pixel-based word wrap. Over-long single words stay unbroken."""
    lines: List[str] = []
    for paragraph in text.split("\n"):
        words = paragraph.split()
        if not words:
            lines.append("")
            continue
        current = words[0]
        for word in words[1:]:
            candidate = current + " " + word
            if font.size(candidate)[0] <= max_width:
                current = candidate
            else:
                lines.append(current)
                current = word
        lines.append(current)
    if max_lines is not None and len(lines) > max_lines:
        lines = lines[:max_lines]
        last = lines[-1]
        if not last.endswith(ELLIPSIS):
            lines[-1] = fit_text(font, last + ELLIPSIS, max_width)
    return lines


class TextCache:
    """LRU cache of rendered text surfaces keyed by (font, text, color)."""

    def __init__(self, max_entries: int = 512) -> None:
        self._max_entries = max(1, int(max_entries))
        self._items: "OrderedDict[Tuple[int, str, Tuple[int, ...]], pygame.Surface]" = OrderedDict()

    def render(self, font: pygame.font.Font, text: str, color: Sequence[int]) -> pygame.Surface:
        key = (id(font), text, tuple(color))
        surf = self._items.get(key)
        if surf is not None:
            self._items.move_to_end(key)
            return surf
        surf = font.render(text, True, tuple(color))
        self._items[key] = surf
        while len(self._items) > self._max_entries:
            self._items.popitem(last=False)
        return surf

    def clear(self) -> None:
        self._items.clear()

    def __len__(self) -> int:
        return len(self._items)


def draw_key_badge(
    surface: pygame.Surface,
    cache: TextCache,
    font: pygame.font.Font,
    key: str,
    topleft: Tuple[int, int],
    color: theme.RGB = theme.ACCENT,
) -> pygame.Rect:
    """Draw a small boxed key label and return its rect."""
    label = cache.render(font, key.upper(), color)
    rect = label.get_rect().inflate(10, 4)
    rect.topleft = topleft
    pygame.draw.rect(surface, theme.PANEL_RAISED, rect)
    pygame.draw.rect(surface, color, rect, 1)
    surface.blit(label, label.get_rect(center=rect.center))
    return rect
