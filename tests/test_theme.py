"""Tests for the bundled UI fonts and the central UI theme."""

import pygame
import pytest

from eagle1.paths import FONTS_DIR

BUNDLED_FONTS = [
    "ChakraPetch-Regular.ttf",
    "ChakraPetch-SemiBold.ttf",
    "ChakraPetch-Bold.ttf",
    "ShareTechMono-Regular.ttf",
]
LICENSE_FILES = ["OFL-ChakraPetch.txt", "OFL-ShareTechMono.txt"]
UI_GLYPHS = "▲▼◄►★✖✚▶◀⚠—•·…"


@pytest.mark.parametrize("name", BUNDLED_FONTS + LICENSE_FILES)
def test_bundled_font_files_exist(name):
    path = FONTS_DIR / name
    assert path.is_file()
    assert path.stat().st_size > 1000


@pytest.mark.parametrize("name", BUNDLED_FONTS)
def test_bundled_fonts_cover_ui_glyphs(name):
    font = pygame.font.Font(str(FONTS_DIR / name), 16)
    assert None not in font.metrics(UI_GLYPHS)
