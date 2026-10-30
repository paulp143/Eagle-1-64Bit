"""layout.py - Auto-layout engine and collision-prevention system for Pygame UI.

Guarantees mathematically that text boxes, buttons, and HUD panels never overlap
by managing sequential layout flow and verifying bounding-box invariants.
"""

from __future__ import annotations

from typing import List, Optional, Tuple
import pygame


def validate_rects_no_overlap(
    rects: List[pygame.Rect],
) -> List[Tuple[pygame.Rect, pygame.Rect]]:
    """Inspect a collection of rectangles and return pairs that collide."""
    collisions: List[Tuple[pygame.Rect, pygame.Rect]] = []
    num_rects = len(rects)
    for i in range(num_rects):
        r1 = rects[i]
        for j in range(i + 1, num_rects):
            r2 = rects[j]
            if r1.colliderect(r2):
                collisions.append((r1, r2))
    return collisions


class VerticalStackLayout:
    """Sequential top-to-bottom layout manager that guarantees 0 element collisions."""

    def __init__(
        self,
        bounds: pygame.Rect,
        padding: int = 16,
        default_gap: int = 10,
    ) -> None:
        self.bounds = pygame.Rect(bounds)
        self.padding = int(max(0, padding))
        self.default_gap = int(max(0, default_gap))

        self.cursor_y: int = self.bounds.y + self.padding
        self.allocated_rects: List[pygame.Rect] = []

    def remaining_height(self) -> int:
        """Return remaining vertical space inside the bounds."""
        bottom_limit = self.bounds.bottom - self.padding
        return max(0, bottom_limit - self.cursor_y)

    def add_slot(
        self,
        height: int,
        width: Optional[int] = None,
        align: str = "left",
        gap: Optional[int] = None,
    ) -> pygame.Rect:
        """Allocate a new slot strictly below the previous slot."""
        h = max(0, int(height))
        effective_gap = self.default_gap if gap is None else max(0, int(gap))

        # Apply gap if not the first element
        if self.allocated_rects:
            self.cursor_y += effective_gap

        inner_w = max(0, self.bounds.width - 2 * self.padding)
        w = inner_w if width is None else min(inner_w, max(0, int(width)))

        if align == "center":
            x = self.bounds.x + self.padding + (inner_w - w) // 2
        elif align == "right":
            x = self.bounds.right - self.padding - w
        else:
            x = self.bounds.x + self.padding

        rect = pygame.Rect(x, self.cursor_y, w, h)
        self.allocated_rects.append(rect)
        self.cursor_y += h
        return rect

    def add_text_slot(
        self,
        line_count: int,
        line_height: int,
        padding_y: int = 4,
        width: Optional[int] = None,
        align: str = "left",
        gap: Optional[int] = None,
    ) -> pygame.Rect:
        """Allocate a slot with height dynamically computed from line count and line height."""
        lines = max(1, int(line_count))
        lh = max(1, int(line_height))
        py = max(0, int(padding_y))
        total_height = lines * lh + 2 * py
        return self.add_slot(height=total_height, width=width, align=align, gap=gap)

    def assert_no_overlaps(self) -> bool:
        """Assert that no allocated rectangles intersect each other."""
        collisions = validate_rects_no_overlap(self.allocated_rects)
        if collisions:
            msg = (
                f"VerticalStackLayout overlap violation: {len(collisions)} collisions found "
                f"among {len(self.allocated_rects)} rects: {collisions}"
            )
            raise AssertionError(msg)
        return True

