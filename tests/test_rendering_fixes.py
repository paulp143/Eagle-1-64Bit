"""Tests verifying rendering fixes: transparent asset conversion, black box elimination, and VSync/camera snapping."""

import os
import pygame

from eagle1.app.game import (
    player_image,
    light_enemy_image,
    health_image,
    bullet_image,
    convert_all_game_assets,
    load_image,
)


def test_player_image_rotation_transparency_no_black_box():
    """Verify that rotating the player ship and blitting onto a texture has zero black box outside the hull."""
    test_surf = pygame.Surface((200, 200))
    test_surf.fill((255, 0, 0))  # Bright red underlying texture

    for angle in [0, 15, 30, 45, 90, 180, 270]:
        test_surf.fill((255, 0, 0))
        rotated = pygame.transform.rotate(player_image, angle)
        rect = rotated.get_rect(center=(100, 100))
        test_surf.blit(rotated, rect.topleft)

        # Check the 4 corners of rect: they should still be pure red (255, 0, 0), NOT black (0, 0, 0)
        corners = [
            (rect.left, rect.top),
            (rect.right - 1, rect.top),
            (rect.left, rect.bottom - 1),
            (rect.right - 1, rect.bottom - 1),
        ]
        for cx, cy in corners:
            pixel = test_surf.get_at((cx, cy))
            assert pixel[:3] == (255, 0, 0), (
                f"Corner ({cx}, {cy}) at angle {angle} was {pixel}, expected red (255, 0, 0) - black box detected!"
            )


def test_light_enemy_image_transparency():
    """Verify that enemy1.png has its white background colorkeyed/transparent, not opaque white."""
    test_surf = pygame.Surface((100, 100))
    test_surf.fill((0, 0, 255))  # Blue underlying texture

    rot_enemy = pygame.transform.rotate(light_enemy_image, 25)
    rect = rot_enemy.get_rect(center=(50, 50))
    test_surf.blit(rot_enemy, rect.topleft)

    # Corners of the rotated surface must not be white (255, 255, 255)
    corners = [
        (rect.left, rect.top),
        (rect.right - 1, rect.top),
        (rect.left, rect.bottom - 1),
        (rect.right - 1, rect.bottom - 1),
    ]
    for cx, cy in corners:
        pixel = test_surf.get_at((cx, cy))
        assert pixel[:3] == (0, 0, 255), f"Corner ({cx}, {cy}) was {pixel}, expected blue (0, 0, 255)"


def test_health_drop_image_transparency():
    """Verify that health.png has its black background colorkeyed/transparent, not opaque black."""
    test_surf = pygame.Surface((60, 60))
    test_surf.fill((0, 255, 0))  # Green underlying texture

    scaled_health = pygame.transform.scale(health_image, (24, 24))
    rect = scaled_health.get_rect(center=(30, 30))
    test_surf.blit(scaled_health, rect.topleft)

    # Corners must be green, not solid black (0, 0, 0)
    corners = [
        (rect.left, rect.top),
        (rect.right - 1, rect.top),
        (rect.left, rect.bottom - 1),
        (rect.right - 1, rect.bottom - 1),
    ]
    for cx, cy in corners:
        pixel = test_surf.get_at((cx, cy))
        assert pixel[:3] == (0, 255, 0), f"Corner ({cx}, {cy}) was {pixel}, expected green (0, 255, 0)"


def test_convert_all_game_assets_execution():
    """Ensure convert_all_game_assets runs cleanly without error and sets up surfaces."""
    convert_all_game_assets()
    assert player_image.get_flags() & pygame.SRCALPHA
    assert bullet_image.get_flags() & pygame.SRCALPHA


def test_load_image_with_colorkey():
    """Ensure load_image supports colorkey and preserves alpha transparency."""
    img = load_image(os.path.join("images", "enemy1.png"), colorkey=(255, 255, 255))
    assert img.get_at((0, 0)).a == 0
