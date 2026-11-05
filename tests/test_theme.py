"""Tests for the bundled UI fonts and the central UI theme."""

import pygame
import pytest

from eagle1.paths import FONTS_DIR
from eagle1.ui import theme

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


@pytest.fixture(autouse=True)
def _reset_font_cache():
    theme.clear_font_cache()
    yield
    theme.clear_font_cache()


def test_get_font_returns_cached_instance():
    assert theme.get_font("body") is theme.get_font("body")


def test_get_font_unknown_style_raises():
    with pytest.raises(ValueError):
        theme.get_font("nope")


def test_load_font_clamps_min_size():
    assert theme.load_font(theme.ROLE_BODY, 6) is theme.load_font(theme.ROLE_BODY, 12)


def test_load_font_falls_back_when_file_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(theme, "FONTS_DIR", tmp_path)
    font = theme.load_font(theme.ROLE_BODY, 15)
    assert isinstance(font, pygame.font.Font)


def test_load_font_returns_none_when_font_module_unavailable(monkeypatch):
    def _raise():
        raise pygame.error("no font")

    monkeypatch.setattr(pygame.font, "get_init", lambda: False)
    monkeypatch.setattr(pygame.font, "init", _raise)
    assert theme.load_font(theme.ROLE_BODY, 15) is None


def test_type_scale_respects_min_size():
    assert all(size >= theme.MIN_FONT_SIZE for _, size in theme.TYPE_SCALE.values())


def test_palette_values_are_int_tuples():
    colors = [v for k, v in vars(theme).items() if k.isupper() and isinstance(v, tuple) and len(v) in (3, 4)]
    assert colors
    for color in colors:
        if all(isinstance(c, int) for c in color):
            assert all(0 <= c <= 255 for c in color)


def test_with_alpha_and_lerp_color():
    assert theme.with_alpha((1, 2, 3), 300) == (1, 2, 3, 255)
    assert theme.lerp_color((0, 0, 0), (255, 255, 255), 0.5) == (128, 128, 128)
    assert theme.lerp_color((10, 10, 10), (20, 20, 20), -1) == (10, 10, 10)
    assert theme.lerp_color((10, 10, 10), (20, 20, 20), 2) == (20, 20, 20)
