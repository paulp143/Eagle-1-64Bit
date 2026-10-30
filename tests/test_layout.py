"""tests/test_layout.py - Tests for the UI Auto-Layout engine and overlap validation."""

import pygame
import pytest

from eagle1.ui.layout import VerticalStackLayout, validate_rects_no_overlap


@pytest.fixture(autouse=True)
def init_pygame():
    """Initialize pygame headless for rect operations."""
    pygame.init()


def test_vertical_stack_places_elements_without_overlap():
    """Verify sequential slots added to VerticalStackLayout never overlap."""
    container = pygame.Rect(100, 100, 800, 600)
    layout = VerticalStackLayout(container, padding=16, default_gap=12)

    r1 = layout.add_slot(height=50)
    r2 = layout.add_slot(height=80)
    r3 = layout.add_slot(height=40)

    # First slot starts at container.top + padding
    assert r1.y == container.y + 16
    assert r1.height == 50

    # Second slot is strictly below r1 with gap=12
    assert r2.y == r1.bottom + 12
    assert r2.height == 80

    # Third slot is strictly below r2 with gap=12
    assert r3.y == r2.bottom + 12
    assert r3.height == 40

    # Overlap validation must report 0 collisions
    overlaps = validate_rects_no_overlap([r1, r2, r3])
    assert overlaps == []
    assert layout.assert_no_overlaps() is True


def test_vertical_stack_text_slot_calculation():
    """Verify add_text_slot computes height dynamically from line count and line height."""
    container = pygame.Rect(0, 0, 500, 500)
    layout = VerticalStackLayout(container, padding=10, default_gap=8)

    # 4 lines with 18px line_height and 6px padding_y
    text_rect = layout.add_text_slot(line_count=4, line_height=18, padding_y=6)
    expected_height = 4 * 18 + 2 * 6  # 72 + 12 = 84
    assert text_rect.height == expected_height
    assert text_rect.y == 10

    # Next slot placed strictly below
    btn_rect = layout.add_slot(height=36)
    assert btn_rect.y == text_rect.bottom + 8
    assert not text_rect.colliderect(btn_rect)


def test_validate_rects_no_overlap_detects_intersections():
    """Verify overlap validator correctly catches intersecting rectangles."""
    box_a = pygame.Rect(10, 10, 100, 50)
    box_b = pygame.Rect(50, 30, 100, 50)  # Intersects box_a
    box_c = pygame.Rect(200, 200, 50, 50)  # Independent

    overlaps = validate_rects_no_overlap([box_a, box_b, box_c])
    assert len(overlaps) == 1
    assert overlaps[0] == (box_a, box_b)


def test_vertical_stack_remaining_height():
    """Verify remaining_height accurately tracks available space."""
    container = pygame.Rect(0, 0, 400, 300)
    layout = VerticalStackLayout(container, padding=20, default_gap=10)

    # Available initial: 300 - 2 * 20 = 260
    assert layout.remaining_height() == 260

    layout.add_slot(height=60)
    # Remaining: 260 - 60 = 200
    assert layout.remaining_height() == 200

    # Overflow clamped to 0
    layout.add_slot(height=300)
    assert layout.remaining_height() == 0


def test_vertical_stack_alignment_and_width_clamping():
    """Verify alignment modes (center, right, left) and width clamping."""
    container = pygame.Rect(100, 100, 400, 400)
    layout = VerticalStackLayout(container, padding=20)
    inner_w = 400 - 2 * 20  # 360

    # Left align with partial width
    r_left = layout.add_slot(height=30, width=100, align="left")
    assert r_left.x == 120
    assert r_left.width == 100

    # Center align
    r_center = layout.add_slot(height=30, width=100, align="center")
    assert r_center.x == 120 + (inner_w - 100) // 2
    assert r_center.width == 100

    # Right align
    r_right = layout.add_slot(height=30, width=100, align="right")
    assert r_right.right == container.right - 20
    assert r_right.width == 100

    # Oversized width gets clamped to inner_w
    r_over = layout.add_slot(height=30, width=999)
    assert r_over.width == inner_w


def test_vertical_stack_assert_no_overlaps_raises_on_collision():
    """Verify assert_no_overlaps raises AssertionError when rects intersect."""
    container = pygame.Rect(0, 0, 300, 300)
    layout = VerticalStackLayout(container)

    # Artificially inject an overlapping rect
    layout.allocated_rects.append(pygame.Rect(10, 10, 100, 100))
    layout.allocated_rects.append(pygame.Rect(50, 50, 100, 100))

    with pytest.raises(AssertionError, match="VerticalStackLayout overlap violation"):
        layout.assert_no_overlaps()


def test_validate_rects_no_overlap_boundaries():
    """Verify validate_rects_no_overlap with empty, single, and touching boundaries."""
    assert validate_rects_no_overlap([]) == []
    assert validate_rects_no_overlap([pygame.Rect(0, 0, 10, 10)]) == []

    # Touching edges are NOT considered collisions by Pygame
    r1 = pygame.Rect(0, 0, 50, 50)
    r2 = pygame.Rect(0, 50, 50, 50)  # r1.bottom == r2.top
    assert validate_rects_no_overlap([r1, r2]) == []
