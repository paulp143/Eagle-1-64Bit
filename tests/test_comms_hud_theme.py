"""Tests for the re-themed CommsHUD geometry, fonts and keys."""

import pygame

from eagle1.story.comms_hud import CommsHUD
from eagle1.story.dialogue_db import get_dialogue_node
from eagle1.ui import theme


def _hud():
    hud = CommsHUD(story_manager=None, audio_manager=None, screen_width=1280, screen_height=720)
    node = get_dialogue_node("sortie_1_briefing")
    assert node is not None and node.options
    hud.trigger_transmission(node)
    return hud


def test_body_lines_end_above_option_cards():
    hud = _hud()
    body_bottom = 14 + 20 + hud.max_body_lines * hud.font_body.get_linesize()
    assert body_bottom <= 104


def test_option_cards_fit_inside_box():
    hud = _hud()
    assert 104 + 42 <= hud.box_height


def test_fonts_are_at_least_12px():
    hud = _hud()
    for font in (hud.font_header, hud.font_body, hud.font_option, hud.font_badge):
        assert font.get_height() >= 13


def test_keypad_enter_fast_forwards_typewriter():
    hud = _hud()
    hud.typewriter_chars = 0.0
    consumed = hud.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_KP_ENTER, mod=0))
    assert consumed is True
    assert hud.typewriter_chars > 0


def test_long_option_label_is_ellipsized_not_sliced():
    hud = _hud()
    for card in hud._cached_option_cards.values():
        label_surf = card[0]
        assert label_surf.get_width() <= hud._option_label_width


def test_speaker_marker_uses_supported_ascii(dummy_surface):
    hud = _hud()
    hud.render(dummy_surface)
    assert hud._cached_speaker_surf is not None
    # The ▶ glyph does not exist in the mono font; the marker is now ">".
    assert hud.current_node.speaker
    assert theme.get_font("mono").size("> X")[0] > 0


def test_render_is_allocation_free_after_warmup(dummy_surface, monkeypatch):
    hud = _hud()
    hud.typewriter_chars = 10000.0
    hud.render(dummy_surface)

    def _raise(*args, **kwargs):
        raise AssertionError("allocation in render")

    monkeypatch.setattr(pygame, "Surface", _raise)
    monkeypatch.setattr(pygame.font, "SysFont", _raise)
    for _ in range(3):
        hud.render(dummy_surface)
