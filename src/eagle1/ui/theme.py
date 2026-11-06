"""theme.py - Central "Military Terminal" design tokens and bundled-font loader for Eagle-1.

Style guide:
- Dark navy panels with SHARP corners (no border_radius), 1 px steel borders and
  2 px L-shaped corner brackets in the accent color.
- Accent = Super-Earth yellow (focus, titles, brackets). Info = cyan.
- Labels are UPPERCASE; numbers and data use the mono role.
- Minimum font size is 12 px.
- Glyph support: Chakra Petch (display/heading/body) contains ▲ ▼ ▶ ◀ — • · … ° ±. It does NOT contain
  ◄ ► ★ ✖ ✚ ⚠. Share Tech Mono (mono) contains no arrows or symbols at all. Never render the missing
  glyphs (they show up as tofu boxes); use ARROW_GLYPHS with a heading/body font, or draw shapes.
- Fonts are created only through ``get_font`` / ``load_font`` and only at init time,
  never inside draw/render/update paths. Static text is rendered once (see widgets.TextCache).
"""

from __future__ import annotations

import logging
from typing import Dict, Optional, Tuple

import pygame

from eagle1.paths import FONTS_DIR

logger = logging.getLogger(__name__)

RGB = Tuple[int, int, int]
RGBA = Tuple[int, int, int, int]

# --- Palette ---------------------------------------------------------------
BG_DEEP: RGB = (6, 9, 14)
OVERLAY_RGBA: RGBA = (6, 9, 14, 225)
OVERLAY_LIGHT_RGBA: RGBA = (6, 9, 14, 170)
PANEL: RGB = (12, 17, 26)
PANEL_RAISED: RGB = (18, 25, 37)
PANEL_HOVER: RGB = (26, 36, 52)
BORDER: RGB = (46, 64, 88)
BORDER_STRONG: RGB = (78, 102, 132)
ACCENT: RGB = (255, 204, 0)
ACCENT_DIM: RGB = (150, 120, 20)
INFO: RGB = (0, 200, 235)
SUCCESS: RGB = (70, 210, 120)
WARNING: RGB = (255, 150, 40)
DANGER: RGB = (235, 64, 52)
TEXT: RGB = (232, 238, 245)
TEXT_MUTED: RGB = (150, 166, 186)
TEXT_DISABLED: RGB = (88, 98, 112)
TEXT_ON_ACCENT: RGB = (12, 14, 18)

# --- Typography ------------------------------------------------------------
ROLE_DISPLAY = "display"
ROLE_HEADING = "heading"
ROLE_BODY = "body"
ROLE_MONO = "mono"

FONT_FILES: Dict[str, str] = {
    ROLE_DISPLAY: "ChakraPetch-Bold.ttf",
    ROLE_HEADING: "ChakraPetch-SemiBold.ttf",
    ROLE_BODY: "ChakraPetch-Regular.ttf",
    ROLE_MONO: "ShareTechMono-Regular.ttf",
}
FALLBACK_SYSFONTS: Dict[str, Tuple[str, bool]] = {
    ROLE_DISPLAY: ("arial", True),
    ROLE_HEADING: ("arial", True),
    ROLE_BODY: ("arial", False),
    ROLE_MONO: ("couriernew,courier,monospace", True),
}
TYPE_SCALE: Dict[str, Tuple[str, int]] = {
    "display_xl": (ROLE_DISPLAY, 44),
    "display": (ROLE_DISPLAY, 32),
    "title": (ROLE_HEADING, 24),
    "heading": (ROLE_HEADING, 18),
    "label": (ROLE_HEADING, 14),
    "body": (ROLE_BODY, 15),
    "body_small": (ROLE_BODY, 13),
    "subtitle": (ROLE_BODY, 16),
    "mono": (ROLE_MONO, 15),
    "mono_small": (ROLE_MONO, 13),
    "mono_tiny": (ROLE_MONO, 12),
}
MIN_FONT_SIZE = 12

# Direction glyphs available in the Chakra Petch fonts (not in the mono font).
ARROW_GLYPHS: Dict[str, str] = {"UP": "▲", "DOWN": "▼", "LEFT": "◀", "RIGHT": "▶"}

# --- Shape metrics ---------------------------------------------------------
BRACKET_LENGTH = 14
BRACKET_THICKNESS = 2
BORDER_WIDTH = 1
FOCUS_BAR_WIDTH = 4

_FONT_CACHE: Dict[Tuple[str, int], pygame.font.Font] = {}
_warned_missing: bool = False


def load_font(role: str, size: int) -> Optional[pygame.font.Font]:
    """Return a cached font for ``role`` at ``size`` (clamped to MIN_FONT_SIZE).

    Returns None when the pygame font module is unavailable. Falls back to a system font
    (logged once) when the bundled file cannot be loaded.
    """
    global _warned_missing
    if role not in FONT_FILES:
        raise ValueError(f"Unknown font role: {role}")
    size = max(MIN_FONT_SIZE, int(size))

    if not pygame.font.get_init():
        _FONT_CACHE.clear()
        try:
            pygame.font.init()
        except pygame.error as exc:
            logger.warning("Font module unavailable: %s", exc)
            return None
        if not pygame.font.get_init():
            return None

    cached = _FONT_CACHE.get((role, size))
    if cached is not None:
        return cached

    path = FONTS_DIR / FONT_FILES[role]
    try:
        font = pygame.font.Font(str(path), size)
    except (FileNotFoundError, OSError, pygame.error) as exc:
        if not _warned_missing:
            logger.warning("Bundled font %s unavailable (%s); using system fallback", path.name, exc)
            _warned_missing = True
        name, bold = FALLBACK_SYSFONTS[role]
        try:
            font = pygame.font.SysFont(name, size, bold=bold)
        except (OSError, pygame.error):
            try:
                font = pygame.font.Font(None, size)
            except pygame.error as exc2:
                logger.warning("No usable font available: %s", exc2)
                return None

    _FONT_CACHE[(role, size)] = font
    return font


def get_font(style: str) -> Optional[pygame.font.Font]:
    """Return the cached font for a named type-scale style."""
    if style not in TYPE_SCALE:
        raise ValueError(f"Unknown type style: {style}")
    role, size = TYPE_SCALE[style]
    return load_font(role, size)


def clear_font_cache() -> None:
    """Drop all cached fonts (used by tests and after font-module re-init)."""
    _FONT_CACHE.clear()


def with_alpha(color: RGB, alpha: int) -> RGBA:
    """Return ``color`` with an alpha channel clamped to 0..255."""
    return (color[0], color[1], color[2], max(0, min(255, int(alpha))))


def lerp_color(a: RGB, b: RGB, t: float) -> RGB:
    """Linearly interpolate between two RGB colors; ``t`` is clamped to 0..1."""
    t = max(0.0, min(1.0, float(t)))
    return (
        int(round(a[0] + (b[0] - a[0]) * t)),
        int(round(a[1] + (b[1] - a[1]) * t)),
        int(round(a[2] + (b[2] - a[2]) * t)),
    )
