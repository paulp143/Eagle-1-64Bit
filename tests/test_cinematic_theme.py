"""Tests for the re-themed CinematicPlayer layout (letterbox-safe subtitles, epilogue fit)."""

import pytest

from eagle1.story.cinematic_player import (
    CINEMATIC_LETTERBOX_HEIGHT,
    CinematicPlayer,
)


@pytest.fixture
def player():
    return CinematicPlayer(1280, 720)


def test_fonts_are_at_least_12px(player):
    for font in (player.font_title, player.font_speaker, player.font_subtitle,
                 player.font_epilogue, player.font_prompt):
        assert font is not None and font.get_height() >= 13


def test_subtitle_block_fits_inside_letterbox_bar(player):
    block = 4 + player.font_speaker.get_height() + 2 * player.font_subtitle.get_height()
    assert block <= CINEMATIC_LETTERBOX_HEIGHT


def test_epilogue_content_fits_inside_panel(player):
    # Mirror _draw_epilogue's vertical arithmetic with the real fonts.
    header_h = player.font_speaker.get_height() + 9
    title_h = player.font_title.get_height() + 8
    stat_h = 5 * (player.font_epilogue.get_height() + 6)
    lines_h = 8 * (player.font_epilogue.get_height() + 4)
    panel_h = player._epilogue_panel.get_height()
    prompt_top = panel_h - 32
    assert 24 + header_h + title_h + stat_h + 14 + lines_h <= prompt_top
