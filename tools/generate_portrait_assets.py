"""generate_portrait_assets.py - Procedural 64x64 Helldiver Portrait Generator.

Generates deterministic pixel-art style tactical helmet portraits for the
members of Viper Squad (Apex, Braker, Ghost, Doc) saved into images/portraits/.
"""

from __future__ import annotations

import os
from pathlib import Path
import sys
from typing import Dict, Optional

# Add src to sys.path so eagle1 package is discoverable when run standalone
SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import pygame

# Initialize headless dummy display driver for headless environments
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from eagle1.paths import IMAGES_DIR


def _draw_base_helmet(surface: pygame.Surface, accent_color: tuple, badge_type: str = "crest") -> None:
    """Render stylized Helldiver combat helmet onto a 64x64 surface."""
    # 1. Dark tactical background
    surface.fill((14, 20, 28, 240))

    # Outer border frame
    pygame.draw.rect(surface, (30, 45, 60), (0, 0, 64, 64), width=1)
    pygame.draw.rect(surface, accent_color, (1, 1, 62, 62), width=1)

    # Corner brackets
    for x, y, dx, dy in [(2, 2, 1, 1), (61, 2, -1, 1), (2, 61, 1, -1), (61, 61, -1, -1)]:
        pygame.draw.line(surface, accent_color, (x, y), (x + dx * 6, y), 2)
        pygame.draw.line(surface, accent_color, (x, y), (x, y + dy * 6), 2)

    # 2. Helmet Dome (Dark charcoal composite armor)
    dome_color = (42, 48, 58)
    shadow_color = (26, 30, 38)
    highlight_color = (68, 76, 90)

    # Main dome arc
    pygame.draw.ellipse(surface, dome_color, (14, 10, 36, 40))
    pygame.draw.ellipse(surface, highlight_color, (16, 11, 32, 16), width=1)

    # Cheek guards and lower jaw
    points_jaw = [(16, 32), (20, 52), (44, 52), (48, 32), (42, 28), (22, 28)]
    pygame.draw.polygon(surface, shadow_color, points_jaw)
    pygame.draw.polygon(surface, dome_color, [(18, 32), (22, 50), (42, 50), (46, 32)])

    # 3. Signature Helldiver T-Visier (Glowing in character theme color)
    # Horizontal visor slit
    pygame.draw.rect(surface, (15, 18, 22), (20, 24, 24, 7))
    pygame.draw.rect(surface, accent_color, (22, 25, 20, 5))
    # Vertical nose slit (T-shape)
    pygame.draw.rect(surface, (15, 18, 22), (29, 29, 6, 12))
    pygame.draw.rect(surface, accent_color, (30, 29, 4, 11))

    # Glow highlight on visor
    pygame.draw.line(surface, (255, 255, 255), (24, 26), (32, 26), 1)

    # 4. Specialized Role Badges
    if badge_type == "crest":
        # Apex: Vanguard Gold Crest & Eagle Winglet
        pygame.draw.polygon(surface, accent_color, [(32, 6), (28, 12), (36, 12)])
        pygame.draw.line(surface, (255, 255, 220), (32, 7), (32, 12), 1)
    elif badge_type == "tally":
        # Braker: Autocannon battle scars (white tally marks on right cheek)
        for i in range(4):
            pygame.draw.line(surface, (220, 230, 240), (41 + i * 2, 38), (41 + i * 2, 44), 1)
        pygame.draw.line(surface, (240, 100, 100), (40, 44), (48, 38), 1)  # Diagonal cross-tally
    elif badge_type == "optic":
        # Ghost: Green sniper scope lens on left eye
        pygame.draw.circle(surface, (20, 40, 30), (24, 27), 4)
        pygame.draw.circle(surface, (80, 255, 160), (24, 27), 3)
        pygame.draw.circle(surface, (255, 255, 255), (23, 26), 1)
    elif badge_type == "medic_cross":
        # Doc: White Combat Medic Cross on helmet brow
        pygame.draw.rect(surface, (255, 255, 255), (30, 12, 4, 10))
        pygame.draw.rect(surface, (255, 255, 255), (27, 15, 10, 4))
        pygame.draw.rect(surface, (230, 40, 40), (31, 13, 2, 8))
        pygame.draw.rect(surface, (230, 40, 40), (28, 16, 8, 2))


def generate_viper_portraits(output_dir: Optional[Path] = None) -> Dict[str, Path]:
    """Generate 64x64 tactical helmet portraits for Viper Squad members."""
    pygame.init()

    if output_dir is None:
        target_dir = IMAGES_DIR / "portraits"
    else:
        target_dir = Path(output_dir)

    target_dir.mkdir(parents=True, exist_ok=True)

    configs = {
        "viper_1_apex": {"color": (255, 215, 0), "badge": "crest"},
        "viper_2_braker": {"color": (52, 152, 219), "badge": "tally"},
        "viper_3_ghost": {"color": (46, 204, 113), "badge": "optic"},
        "viper_4_doc": {"color": (231, 76, 60), "badge": "medic_cross"},
    }

    generated_paths = {}

    for name, cfg in configs.items():
        surf = pygame.Surface((64, 64), pygame.SRCALPHA)
        _draw_base_helmet(surf, cfg["color"], cfg["badge"])
        out_path = target_dir / f"{name}.png"
        pygame.image.save(surf, str(out_path))
        generated_paths[name] = out_path

    return generated_paths


if __name__ == "__main__":
    paths = generate_viper_portraits()
    for k, p in paths.items():
        print(f"Generated {k}: {p}")
