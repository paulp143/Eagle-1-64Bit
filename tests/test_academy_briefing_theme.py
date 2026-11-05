"""Tests for the re-themed Academy briefing HUD (no per-frame I/O or allocations)."""

import pygame

from eagle1.data.player_profile import PlayerProfileManager
from eagle1.systems import academy_briefing as ab
from eagle1.ui import hud_layout


def _mgr():
    return ab.AcademyTutorialManager()


def test_graduation_draw_does_not_touch_the_profile_file(dummy_surface, monkeypatch):
    mgr = _mgr()
    mgr.state = ab.DRILL_GRADUATION
    mgr.draw_hud(dummy_surface)  # first frame builds the ceremony assets

    def _raise(*args, **kwargs):
        raise AssertionError("profile loaded while drawing")

    monkeypatch.setattr(PlayerProfileManager, "load_profile", _raise)
    monkeypatch.setattr(PlayerProfileManager, "has_active_profile", _raise)
    for _ in range(3):
        mgr.draw_hud(dummy_surface)


def test_graduation_draw_allocates_nothing_after_first_frame(dummy_surface, monkeypatch):
    mgr = _mgr()
    mgr.state = ab.DRILL_GRADUATION
    mgr.draw_hud(dummy_surface)

    def _raise(*args, **kwargs):
        raise AssertionError("allocation in draw")

    monkeypatch.setattr(pygame, "Surface", _raise)
    for _ in range(3):
        mgr.draw_hud(dummy_surface)


def test_comms_box_draw_allocates_nothing_per_frame(dummy_surface, monkeypatch):
    box = ab.CommsHUDBox()
    box.set_message("Welcome to the Academy, Cadet. Follow my instructions carefully.", sfx_cue=None)
    box.displayed_chars = 20
    box.draw(dummy_surface)

    def _raise(*args, **kwargs):
        raise AssertionError("allocation in comms box draw")

    monkeypatch.setattr(pygame, "Surface", _raise)
    for chars in range(20, 40):
        box.displayed_chars = chars
        box.draw(dummy_surface)


def test_comms_box_wraps_once_and_caps_lines():
    box = ab.CommsHUDBox()
    box.set_message("word " * 200, sfx_cue=None)
    assert len(box._lines) == box.MAX_LINES
    assert box._lines[-1].endswith("…")


def test_comms_box_text_fits_inside_box():
    box = ab.CommsHUDBox()
    assert 38 + box.MAX_LINES * box.font_msg.get_linesize() <= box.rect.h


def test_fonts_are_at_least_12px():
    mgr = _mgr()
    for font in (mgr.font_obj, mgr.font_sub, mgr.font_ceremony_title, mgr.font_ceremony_sub,
                 mgr.font_ceremony_name, mgr.comms_box.font_title, mgr.comms_box.font_msg):
        assert font is not None and font.get_height() >= 13


def test_academy_panels_do_not_overlap_hud_zones(dummy_surface):
    box = ab.CommsHUDBox()
    assert not box.rect.colliderect(hud_layout.STATUS_PANEL)
    assert not box.rect.colliderect(hud_layout.WEAPON_PANEL)
    banner = pygame.Rect(dummy_surface.get_width() - 16 - 404, 148, 404, 72)
    assert not banner.colliderect(hud_layout.WEAPON_PANEL)
    assert not banner.colliderect(hud_layout.STATUS_PANEL)
    assert not banner.colliderect(box.rect)


def test_graduate_callsign_is_captured_when_graduating(tmp_path, monkeypatch):
    monkeypatch.setenv("EAGLE1_USER_DATA_DIR", str(tmp_path))
    PlayerProfileManager().create_profile("SKULL-LEADER", citizenship_grade="E")
    mgr = _mgr()
    mgr.state = ab.DRILL_STRATAGEM
    mgr.advance_drill()
    assert mgr._graduate_callsign == "SKULL-LEADER"
