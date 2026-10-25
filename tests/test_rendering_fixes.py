"""Tests verifying rendering fixes: opaque RGBX canvas (Amask=0), transparent asset conversion, black box elimination when overlapping textures, and VSync/camera snapping."""

import os
import pygame

from eagle1.app import game
from eagle1.app.game import (
    player_image,
    light_enemy_image,
    health_image,
    bullet_image,
    convert_all_game_assets,
    load_image,
)


def test_canvas_has_zero_alpha_mask_to_prevent_macos_overlap_black_box():
    """
    On macOS Cocoa, a 32-bit Surface with Amask != 0 and flags == 0 corrupts dstA to 0
    when an SRCALPHA surface is blitted, causing any subsequent overlapping rotated sprite
    to render a solid black bounding box. Verify canvas has Amask == 0.
    """
    assert game.canvas.get_masks()[3] == 0, (
        f"canvas must have Amask == 0 to prevent black boxes on overlap, got masks={game.canvas.get_masks()}"
    )


def test_player_overlap_with_srcalpha_surface_on_canvas_no_black_box():
    """
    Reproduce the exact overlap scenario:
    1. Fill canvas with a non-black background.
    2. Blit a semi-transparent SRCALPHA surface (like a reticle, beacon, explosion, or ground unit).
    3. Blit the rotated player ship overlapping that SRCALPHA surface.
    4. Verify the transparent corners of the rotated player ship bounding box are NOT black (0, 0, 0).
    """
    game.canvas.fill((80, 120, 160))

    overlay = pygame.Surface((160, 160), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 0))
    pygame.draw.circle(overlay, (0, 220, 255, 140), (80, 80), 70)
    game.canvas.blit(overlay, (200, 200))

    for angle in [15, 30, 45, 60, 135]:
        game.canvas.fill((80, 120, 160))
        game.canvas.blit(overlay, (200, 200))

        rotated = pygame.transform.rotate(game.player.original_image, angle)
        rect = rotated.get_rect(center=(280, 280))
        game.canvas.blit(rotated, rect.topleft)

        corners = [
            (rect.left + 1, rect.top + 1),
            (rect.right - 2, rect.top + 1),
            (rect.left + 1, rect.bottom - 2),
            (rect.right - 2, rect.bottom - 2),
        ]
        for cx, cy in corners:
            pixel = game.canvas.get_at((cx, cy))
            assert pixel[:3] != (0, 0, 0), (
                f"Black box detected at ({cx}, {cy}) at angle {angle} when overlapping SRCALPHA surface! Got {pixel}"
            )


def test_player_image_rotation_transparency_no_black_box():
    """Verify that rotating the player ship and blitting onto a texture has zero black box outside the hull."""
    test_surf = pygame.Surface((200, 200), 0, 32, (0x00FF0000, 0x0000FF00, 0x000000FF, 0))

    for angle in [0, 15, 30, 45, 90, 180, 270]:
        test_surf.fill((255, 0, 0))
        rotated = pygame.transform.rotate(player_image, angle)
        rect = rotated.get_rect(center=(100, 100))
        test_surf.blit(rotated, rect.topleft)

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
    """Verify that enemy1.png has its white background transparent, not opaque white."""
    test_surf = pygame.Surface((100, 100), 0, 32, (0x00FF0000, 0x0000FF00, 0x000000FF, 0))
    test_surf.fill((0, 0, 255))

    for angle in [0, 25, 45, 90]:
        test_surf.fill((0, 0, 255))
        rot_enemy = pygame.transform.rotate(light_enemy_image, angle)
        rect = rot_enemy.get_rect(center=(50, 50))
        test_surf.blit(rot_enemy, rect.topleft)

        corners = [
            (rect.left, rect.top),
            (rect.right - 1, rect.top),
            (rect.left, rect.bottom - 1),
            (rect.right - 1, rect.bottom - 1),
        ]
        for cx, cy in corners:
            pixel = test_surf.get_at((cx, cy))
            assert pixel[:3] == (0, 0, 255), (
                f"Corner ({cx}, {cy}) at angle {angle} was {pixel}, expected blue (0, 0, 255)"
            )


def test_health_drop_image_transparency():
    """Verify that health.png has its black background transparent, not opaque black."""
    test_surf = pygame.Surface((60, 60), 0, 32, (0x00FF0000, 0x0000FF00, 0x000000FF, 0))
    test_surf.fill((0, 255, 0))

    scaled_health = pygame.transform.scale(health_image, (24, 24))
    rect = scaled_health.get_rect(center=(30, 30))
    test_surf.blit(scaled_health, rect.topleft)

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
    assert game.player.original_image.get_flags() & pygame.SRCALPHA


def test_load_image_with_colorkey():
    """Ensure load_image supports colorkey and bakes genuine alpha=0 transparency."""
    img = load_image(os.path.join("images", "enemy1.png"), colorkey=(255, 255, 255))
    assert img.get_at((0, 0)).a == 0
