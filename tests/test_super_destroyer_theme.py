"""Tests for the re-themed SuperDestroyerView: keyboard focus, fonts and theme colors."""

import pygame
import pytest

from eagle1.story import (
    PATRIOTISM_COLOR_DISSIDENT,
    PATRIOTISM_COLOR_NOMINAL,
    PATRIOTISM_COLOR_ZEALOT,
    ZONE_BRIDGE,
    ZONE_READY_ROOM,
    CampaignSaveManager,
    StoryManager,
    SuperDestroyerView,
)
from eagle1.ui import theme


@pytest.fixture
def view(tmp_path):
    story = StoryManager(save_manager=CampaignSaveManager(data_dir=tmp_path))
    return SuperDestroyerView(story)


def _key(key, mod=0):
    return pygame.event.Event(pygame.KEYDOWN, key=key, mod=mod)


def test_patriotism_colors_are_theme_tokens():
    assert PATRIOTISM_COLOR_ZEALOT == theme.ACCENT
    assert PATRIOTISM_COLOR_NOMINAL == theme.INFO
    assert PATRIOTISM_COLOR_DISSIDENT == theme.DANGER


def test_all_fonts_are_at_least_12px(view):
    fonts = [getattr(view, name) for name in dir(view) if name.startswith("font_")]
    assert fonts
    for font in fonts:
        assert font is not None and font.get_height() >= 13


def test_tab_cycles_npc_focus_and_e_talks_to_focused_npc(view):
    view.select_zone(ZONE_READY_ROOM)
    npcs = view.get_zone_npcs()
    assert len(npcs) > 1
    first = view.handle_event(_key(pygame.K_e))
    assert first["npc_id"] == npcs[0].npc_id
    view.close_dialogue()
    view.handle_event(_key(pygame.K_TAB))
    assert view.npc_focus_index == 1
    second = view.handle_event(_key(pygame.K_e))
    assert second["npc_id"] == npcs[1].npc_id


def test_shift_tab_wraps_focus_backwards(view):
    view.select_zone(ZONE_READY_ROOM)
    count = len(view.get_zone_npcs())
    view.handle_event(_key(pygame.K_TAB, pygame.KMOD_SHIFT))
    assert view.npc_focus_index == count - 1


def test_zone_change_resets_npc_focus(view):
    view.select_zone(ZONE_READY_ROOM)
    view.handle_event(_key(pygame.K_TAB))
    view.cycle_zone(1)
    assert view.npc_focus_index == 0


def test_cycle_zone_closes_open_dialogue(view):
    view.select_zone(ZONE_BRIDGE)
    npc = view.get_zone_npcs()[0]
    view.open_npc_dialogue(npc.npc_id)
    assert view.is_dialogue_open
    view.cycle_zone(1)
    assert not view.is_dialogue_open


def test_modal_up_down_and_enter_select_stance(view):
    view.select_zone(ZONE_BRIDGE)
    npc = view.get_zone_npcs()[0]
    view.open_npc_dialogue(npc.npc_id)
    assert view.active_dialogue_node.options
    view.typewriter_chars = float(len(view.active_dialogue_node.prompt))
    stances = view._available_stances()
    view.handle_event(_key(pygame.K_DOWN))
    assert view.hovered_stance == stances[0]
    view.handle_event(_key(pygame.K_DOWN))
    assert view.hovered_stance == stances[1 % len(stances)]
    payload = view.handle_event(_key(pygame.K_RETURN))
    assert payload["action"] == "dialogue_choice"
    assert payload["stance"] == stances[1 % len(stances)]


def test_enter_without_focus_does_not_pick_a_stance(view):
    view.select_zone(ZONE_BRIDGE)
    view.open_npc_dialogue(view.get_zone_npcs()[0].npc_id)
    view.typewriter_chars = float(len(view.active_dialogue_node.prompt))
    view.hovered_stance = None
    assert view.handle_event(_key(pygame.K_RETURN)) is None


def test_draw_with_focus_ring_allocates_no_surfaces(view, dummy_surface, monkeypatch):
    view.select_zone(ZONE_READY_ROOM)
    view.draw(dummy_surface, (0, 0))

    def _raise(*args, **kwargs):
        raise AssertionError("allocation in draw")

    monkeypatch.setattr("eagle1.story.super_destroyer_view.pygame.Surface", _raise)
    for _ in range(3):
        view.draw(dummy_surface, (0, 0))


def test_continue_button_fits_its_label(view):
    view.select_zone(ZONE_BRIDGE)
    view.open_npc_dialogue(view.get_zone_npcs()[0].npc_id)
    view.typewriter_chars = float(len(view.active_dialogue_node.prompt))
    view.select_dialogue_stance(view._available_stances()[0])
    label = view._modal_text_cache["continue_btn"]
    assert label.get_width() + 24 <= view.modal_continue_rect.width
