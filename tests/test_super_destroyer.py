"""Tests for SuperDestroyerView core layout, viewport and Patriotism Index HUD (Issue #57)."""

import os
from unittest.mock import MagicMock, patch
import pygame
import pytest

from eagle1.story import (
    DIALOGUE_DATABASE,
    HUB_ZONES,
    PATRIOTISM_COLOR_DISSIDENT,
    PATRIOTISM_COLOR_NOMINAL,
    PATRIOTISM_COLOR_ZEALOT,
    PATRIOTISM_LABEL_DISSIDENT,
    PATRIOTISM_LABEL_NOMINAL,
    PATRIOTISM_LABEL_ZEALOT,
    SHIP_NPC_PROFILES,
    VIPER_DIALOGUE_TREES,
    ZONE_BRIDGE,
    ZONE_HANGAR,
    ZONE_METADATA,
    ZONE_READY_ROOM,
    CampaignSaveManager,
    ShipNPCProfile,
    StoryManager,
    SuperDestroyerView,
    get_dialogue_node,
    get_ship_npc_profile,
    validate_dialogue_database,
)


@pytest.fixture(autouse=True)
def headless_pygame():
    """Ensure headless pygame initialization for all tests."""
    old_video = os.environ.get("SDL_VIDEODRIVER")
    old_audio = os.environ.get("SDL_AUDIODRIVER")
    os.environ["SDL_VIDEODRIVER"] = "dummy"
    os.environ["SDL_AUDIODRIVER"] = "dummy"
    pygame.init()
    if not pygame.font.get_init():
        pygame.font.init()
    yield
    if old_video is not None:
        os.environ["SDL_VIDEODRIVER"] = old_video
    else:
        os.environ.pop("SDL_VIDEODRIVER", None)
    if old_audio is not None:
        os.environ["SDL_AUDIODRIVER"] = old_audio
    else:
        os.environ.pop("SDL_AUDIODRIVER", None)


@pytest.fixture
def story_mgr(tmp_path):
    """Provide a StoryManager instance isolated in tmp_path."""
    save_mgr = CampaignSaveManager(data_dir=tmp_path)
    return StoryManager(save_manager=save_mgr)


def test_super_destroyer_view_initializes_in_bridge_zone(story_mgr):
    """Verify SuperDestroyerView initializes in Bridge zone with cached surfaces."""
    view = SuperDestroyerView(story_manager=story_mgr)
    assert view.active_zone == ZONE_BRIDGE
    assert HUB_ZONES == (ZONE_BRIDGE, ZONE_READY_ROOM, ZONE_HANGAR)
    assert ZONE_BRIDGE in ZONE_METADATA
    assert ZONE_READY_ROOM in ZONE_METADATA
    assert ZONE_HANGAR in ZONE_METADATA

    # Verify cached surfaces are pre-allocated
    assert isinstance(view.orbital_bg_surface, pygame.Surface)
    assert view.orbital_bg_surface.get_size() == (1280, 720)
    assert isinstance(view.top_hud_bg_surface, pygame.Surface)
    assert isinstance(view.content_panel_bg_surface, pygame.Surface)
    assert isinstance(view.footer_bg_surface, pygame.Surface)


def test_patriotism_index_ratio_and_status_colors_across_thresholds(story_mgr):
    """Verify Patriotism Index ratio and status colors across defined thresholds."""
    view = SuperDestroyerView(story_manager=story_mgr)

    # Zealot state (>= 90.0)
    story_mgr.loyalty = 90.0
    assert view.get_patriotism_bar_ratio() == pytest.approx(0.9, rel=1e-4)
    label, color = view.get_patriotism_status_label_and_color()
    assert label == PATRIOTISM_LABEL_ZEALOT
    assert color == PATRIOTISM_COLOR_ZEALOT

    story_mgr.loyalty = 100.0
    assert view.get_patriotism_bar_ratio() == pytest.approx(1.0, rel=1e-4)
    label, color = view.get_patriotism_status_label_and_color()
    assert label == PATRIOTISM_LABEL_ZEALOT
    assert color == PATRIOTISM_COLOR_ZEALOT

    # Nominal state (15.0 < loyalty < 90.0)
    story_mgr.loyalty = 89.9
    assert view.get_patriotism_bar_ratio() == pytest.approx(0.899, rel=1e-4)
    label, color = view.get_patriotism_status_label_and_color()
    assert label == PATRIOTISM_LABEL_NOMINAL
    assert color == PATRIOTISM_COLOR_NOMINAL

    story_mgr.loyalty = 50.0
    assert view.get_patriotism_bar_ratio() == pytest.approx(0.5, rel=1e-4)
    label, color = view.get_patriotism_status_label_and_color()
    assert label == PATRIOTISM_LABEL_NOMINAL
    assert color == PATRIOTISM_COLOR_NOMINAL

    story_mgr.loyalty = 15.1
    assert view.get_patriotism_bar_ratio() == pytest.approx(0.151, rel=1e-4)
    label, color = view.get_patriotism_status_label_and_color()
    assert label == PATRIOTISM_LABEL_NOMINAL
    assert color == PATRIOTISM_COLOR_NOMINAL

    # Dissident state (<= 15.0)
    story_mgr.loyalty = 15.0
    assert view.get_patriotism_bar_ratio() == pytest.approx(0.15, rel=1e-4)
    label, color = view.get_patriotism_status_label_and_color()
    assert label == PATRIOTISM_LABEL_DISSIDENT
    assert color == PATRIOTISM_COLOR_DISSIDENT

    story_mgr.loyalty = 0.0
    assert view.get_patriotism_bar_ratio() == pytest.approx(0.0, rel=1e-4)
    label, color = view.get_patriotism_status_label_and_color()
    assert label == PATRIOTISM_LABEL_DISSIDENT
    assert color == PATRIOTISM_COLOR_DISSIDENT


def test_patriotism_index_clamps_out_of_range_and_nan_values(story_mgr):
    """Verify Patriotism Index clamps invalid or out-of-range loyalty cleanly."""
    view = SuperDestroyerView(story_manager=story_mgr)

    # Sub-zero
    story_mgr.loyalty = -25.0
    assert view.get_patriotism_bar_ratio() == 0.0

    # Over 100
    story_mgr.loyalty = 140.0
    assert view.get_patriotism_bar_ratio() == 1.0

    # NaN
    story_mgr.loyalty = float("nan")
    assert view.get_patriotism_bar_ratio() == 0.0
    assert view.get_patriotism_status_label_and_color() == (PATRIOTISM_LABEL_NOMINAL, PATRIOTISM_COLOR_NOMINAL)

    # Boolean trap (falls back to nominal default 70.0 -> ratio 0.7)
    story_mgr.loyalty = True  # type: ignore[assignment]
    assert view.get_patriotism_bar_ratio() == 0.7
    assert view.get_patriotism_status_label_and_color() == (PATRIOTISM_LABEL_NOMINAL, PATRIOTISM_COLOR_NOMINAL)

    # Inf
    story_mgr.loyalty = float("inf")
    assert view.get_patriotism_bar_ratio() == 1.0

    # -Inf
    story_mgr.loyalty = -float("inf")
    assert view.get_patriotism_bar_ratio() == 0.0


def test_zone_cycling_wraps_around_forward_and_backward(story_mgr):
    """Verify cycle_zone wraps around forward and backward across all 3 zones."""
    view = SuperDestroyerView(story_manager=story_mgr)
    assert view.active_zone == ZONE_BRIDGE

    # Forward cycling
    assert view.cycle_zone(1) == ZONE_READY_ROOM
    assert view.cycle_zone(1) == ZONE_HANGAR
    assert view.cycle_zone(1) == ZONE_BRIDGE

    # Backward cycling
    assert view.cycle_zone(-1) == ZONE_HANGAR
    assert view.cycle_zone(-1) == ZONE_READY_ROOM
    assert view.cycle_zone(-1) == ZONE_BRIDGE

    # Zero or invalid direction returns current active zone without change
    assert view.cycle_zone(0) == ZONE_BRIDGE
    assert view.cycle_zone(True) == ZONE_BRIDGE  # type: ignore


def test_select_zone_by_id_and_index_and_reject_invalid(story_mgr):
    """Verify select_zone handles strings, ints, whitespace and rejects invalid inputs."""
    view = SuperDestroyerView(story_manager=story_mgr)

    # Valid string identifiers
    assert view.select_zone("ready_room") is True
    assert view.active_zone == ZONE_READY_ROOM

    assert view.select_zone("  HANGAR  ") is True
    assert view.active_zone == ZONE_HANGAR

    # Valid integer index
    assert view.select_zone(0) is True
    assert view.active_zone == ZONE_BRIDGE

    # Invalid string identifier
    assert view.select_zone("engine_room") is False
    assert view.active_zone == ZONE_BRIDGE

    # Invalid integer indices
    assert view.select_zone(-1) is False
    assert view.select_zone(99) is False
    assert view.active_zone == ZONE_BRIDGE

    # Boolean input guard
    assert view.select_zone(True) is False
    assert view.select_zone(False) is False
    assert view.active_zone == ZONE_BRIDGE


def test_keyboard_navigation_ad_arrows_direct_keys_and_escape(story_mgr):
    """Verify handle_event supports A/D, arrows, direct numbers and ESC."""
    view = SuperDestroyerView(story_manager=story_mgr)
    assert view.active_zone == ZONE_BRIDGE

    # 'D' cycles forward
    event_d = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_d)
    res = view.handle_event(event_d)
    assert res == {"action": "select_zone", "zone": ZONE_READY_ROOM}
    assert view.active_zone == ZONE_READY_ROOM

    # Right arrow cycles forward
    event_right = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RIGHT)
    res = view.handle_event(event_right)
    assert res == {"action": "select_zone", "zone": ZONE_HANGAR}
    assert view.active_zone == ZONE_HANGAR

    # 'A' cycles backward
    event_a = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_a)
    res = view.handle_event(event_a)
    assert res == {"action": "select_zone", "zone": ZONE_READY_ROOM}
    assert view.active_zone == ZONE_READY_ROOM

    # Left arrow cycles backward
    event_left = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_LEFT)
    res = view.handle_event(event_left)
    assert res == {"action": "select_zone", "zone": ZONE_BRIDGE}
    assert view.active_zone == ZONE_BRIDGE

    # Direct number 3 selects HANGAR
    event_3 = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_3)
    res = view.handle_event(event_3)
    assert res == {"action": "select_zone", "zone": ZONE_HANGAR}
    assert view.active_zone == ZONE_HANGAR

    # Direct number 2 selects READY_ROOM
    event_2 = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_2)
    res = view.handle_event(event_2)
    assert res == {"action": "select_zone", "zone": ZONE_READY_ROOM}
    assert view.active_zone == ZONE_READY_ROOM

    # Direct number 1 selects BRIDGE
    event_1 = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_1)
    res = view.handle_event(event_1)
    assert res == {"action": "select_zone", "zone": ZONE_BRIDGE}
    assert view.active_zone == ZONE_BRIDGE

    # ESC returns main_menu action
    event_esc = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE)
    res = view.handle_event(event_esc)
    assert res == {"action": "main_menu"}


def test_mouse_click_and_hover_on_zone_tabs(story_mgr):
    """Verify mouse motion sets hovered_zone and click selects zone tab."""
    audio_mock = MagicMock()
    view = SuperDestroyerView(story_manager=story_mgr, audio_manager=audio_mock)

    ready_tab_rect = view.zone_tab_rects[ZONE_READY_ROOM]
    hover_pos = (ready_tab_rect.centerx, ready_tab_rect.centery)

    # Mouse motion hover
    motion_event = pygame.event.Event(pygame.MOUSEMOTION, pos=hover_pos)
    view.handle_event(motion_event)
    assert view.hovered_zone == ZONE_READY_ROOM
    audio_mock.play_sfx.assert_called_with("ui_hover")

    # Mouse click selection
    audio_mock.reset_mock()
    click_event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=hover_pos)
    res = view.handle_event(click_event)
    assert res == {"action": "select_zone", "zone": ZONE_READY_ROOM}
    assert view.active_zone == ZONE_READY_ROOM
    audio_mock.play_sfx.assert_called_with("ui_click")

    # Click on Hangar tab
    hangar_tab_rect = view.zone_tab_rects[ZONE_HANGAR]
    click_hangar = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=hangar_tab_rect.center)
    res = view.handle_event(click_hangar)
    assert res == {"action": "select_zone", "zone": ZONE_HANGAR}
    assert view.active_zone == ZONE_HANGAR


def test_draw_executes_without_per_frame_surface_allocations(story_mgr):
    """Verify draw() runs cleanly and does not allocate pygame.Surface in per-frame render loop."""
    view = SuperDestroyerView(story_manager=story_mgr)
    target_surface = pygame.Surface((1280, 720))

    # Warmup frame to establish initial caches across all 3 zones
    for zone in (ZONE_BRIDGE, ZONE_READY_ROOM, ZONE_HANGAR):
        view.select_zone(zone)
        view.update(1.0 / 60.0)
        view.draw(target_surface, mouse_pos=(200, 100))

    # Monitor Surface creation during subsequent frames across all zones
    allocated_surfaces = []
    real_surface_cls = pygame.Surface

    def tracking_surface(*args, **kwargs):
        allocated_surfaces.append(args)
        return real_surface_cls(*args, **kwargs)

    with patch("eagle1.story.super_destroyer_view.pygame.Surface", side_effect=tracking_surface):
        for zone in (ZONE_BRIDGE, ZONE_READY_ROOM, ZONE_HANGAR):
            view.select_zone(zone)
            for _ in range(20):
                view.update(1.0 / 60.0)
                view.draw(target_surface, mouse_pos=(200, 100))

    # Assert no dynamic surfaces allocated during steady-state rendering
    assert len(allocated_surfaces) == 0, f"Detected unexpected surface allocations: {allocated_surfaces}"


# -----------------------------------------------------------------------------
# Issue #58: Shipboard NPC Profiles, Hub Dialogue Trees & Squad Morale Tests
# -----------------------------------------------------------------------------
def test_ship_npc_profiles_registry_and_lookup_safety():
    """Verify ShipNPCProfile specifications, registry completeness, and lookup fallbacks."""
    required_ids = {"npc_reiner", "npc_vance", "npc_ortiz", "viper_1", "viper_2", "viper_3", "viper_4"}
    assert required_ids.issubset(set(SHIP_NPC_PROFILES.keys()))

    # Verify Bridge NPCs
    reiner = SHIP_NPC_PROFILES["npc_reiner"]
    assert isinstance(reiner, ShipNPCProfile)
    assert reiner.zone == ZONE_BRIDGE
    assert "Karl Reiner" in reiner.name
    assert reiner.default_node_id == "sortie_1_briefing"
    assert reiner.portrait_path == "images/portraits/npc_reiner.png"
    assert reiner.callsign == reiner.name

    vance = SHIP_NPC_PROFILES["npc_vance"]
    assert isinstance(vance, ShipNPCProfile)
    assert vance.zone == ZONE_BRIDGE
    assert "Cynthia Vance" in vance.name
    assert vance.default_node_id == "bridge_vance_logistics"
    assert vance.portrait_path == "images/portraits/npc_vance.png"

    # Verify Hangar NPC
    ortiz = SHIP_NPC_PROFILES["npc_ortiz"]
    assert isinstance(ortiz, ShipNPCProfile)
    assert ortiz.zone == ZONE_HANGAR
    assert "Rylan Ortiz" in ortiz.name
    assert ortiz.default_node_id == "hangar_ortiz_maintenance"
    assert ortiz.portrait_path == "images/portraits/npc_ortiz.png"

    # Verify Ready Room NPCs
    for i in range(1, 5):
        vid = f"viper_{i}"
        prof = SHIP_NPC_PROFILES[vid]
        assert prof.zone == ZONE_READY_ROOM
        assert prof.default_node_id == f"viper_{i}_deck_briefing"

    # Verify alias lookup
    assert get_ship_npc_profile("reiner") == reiner
    assert get_ship_npc_profile("vance") == vance
    assert get_ship_npc_profile("ortiz") == ortiz
    assert get_ship_npc_profile("apex") == SHIP_NPC_PROFILES["viper_1"]
    assert get_ship_npc_profile("braker") == SHIP_NPC_PROFILES["viper_2"]
    assert get_ship_npc_profile("ghost") == SHIP_NPC_PROFILES["viper_3"]
    assert get_ship_npc_profile("doc") == SHIP_NPC_PROFILES["viper_4"]

    # Verify defensive handling of invalid inputs
    assert get_ship_npc_profile("unknown_npc") is None
    assert get_ship_npc_profile("") is None
    assert get_ship_npc_profile(None) is None  # type: ignore[arg-type]
    assert get_ship_npc_profile(True) is None  # type: ignore[arg-type]
    assert get_ship_npc_profile(42) is None  # type: ignore[arg-type]


def test_get_zone_npcs_returns_expected_personnel_per_zone(story_mgr):
    """Verify get_zone_npcs returns expected ShipNPCProfile lists for each deck zone."""
    view = SuperDestroyerView(story_manager=story_mgr)

    # Bridge: Reiner & Vance
    bridge_npcs = view.get_zone_npcs(ZONE_BRIDGE)
    bridge_ids = [npc.npc_id for npc in bridge_npcs]
    assert bridge_ids == ["npc_reiner", "npc_vance"]

    # Ready Room: Viper 1-4
    ready_npcs = view.get_zone_npcs(ZONE_READY_ROOM)
    ready_ids = [npc.npc_id for npc in ready_npcs]
    assert ready_ids == ["viper_1", "viper_2", "viper_3", "viper_4"]

    # Hangar: Ortiz
    hangar_npcs = view.get_zone_npcs(ZONE_HANGAR)
    hangar_ids = [npc.npc_id for npc in hangar_npcs]
    assert hangar_ids == ["npc_ortiz"]

    # Default zone when zone_id is None matches active_zone
    assert view.active_zone == ZONE_BRIDGE
    assert [npc.npc_id for npc in view.get_zone_npcs()] == bridge_ids

    # Invalid zone inputs return empty list safely
    assert view.get_zone_npcs("engine_room") == []
    assert view.get_zone_npcs("") == []
    assert view.get_zone_npcs(True) == []  # type: ignore[arg-type]
    assert view.get_zone_npcs(123) == []  # type: ignore[arg-type]


def test_hub_dialogue_trees_pass_tripartite_schema_validation():
    """Verify all new shipboard hub dialogue trees pass strict tripartite schema validation."""
    assert validate_dialogue_database(DIALOGUE_DATABASE) is True
    assert validate_dialogue_database(VIPER_DIALOGUE_TREES) is True

    # Validate specific hub nodes
    required_hub_nodes = [
        "bridge_vance_logistics",
        "bridge_reiner_scrutiny",
        "hangar_ortiz_maintenance",
        "sortie_1_briefing",
        "sortie_1_hangar_debrief",
    ]
    for node_id in required_hub_nodes:
        assert node_id in DIALOGUE_DATABASE
        node = get_dialogue_node(node_id)
        assert node is not None
        assert set(node.options.keys()) == {"loyal", "neutral", "dissident"}

        loyal_opt = node.options["loyal"]
        neutral_opt = node.options["neutral"]
        dissident_opt = node.options["dissident"]

        assert 8.0 <= loyal_opt.loyalty_delta <= 12.0
        assert -1.0 <= neutral_opt.loyalty_delta <= 1.0
        assert -12.0 <= dissident_opt.loyalty_delta <= -8.0
        assert len(node.prompt.strip()) > 0
        assert len(loyal_opt.response.strip()) > 0


def test_resolve_npc_dialogue_across_zones_acts_and_unknown_ids(story_mgr):
    """Verify resolve_npc_dialogue dynamically resolves dialogue beats by act and sortie."""
    view = SuperDestroyerView(story_manager=story_mgr)

    # Act 1, Sortie 1 initial state
    assert story_mgr.current_act == 1
    assert story_mgr.current_sortie == 1

    # Reiner serves sortie_1_briefing in Sortie 1
    reiner_node = view.resolve_npc_dialogue("npc_reiner")
    assert reiner_node is not None
    assert reiner_node.node_id == "sortie_1_briefing"

    # Vance serves bridge_vance_logistics
    vance_node = view.resolve_npc_dialogue("npc_vance")
    assert vance_node is not None
    assert vance_node.node_id == "bridge_vance_logistics"

    # Ortiz serves hangar_ortiz_maintenance
    ortiz_node = view.resolve_npc_dialogue("npc_ortiz")
    assert ortiz_node is not None
    assert ortiz_node.node_id == "hangar_ortiz_maintenance"

    # Viper 1 serves viper_1_deck_briefing before sortie stats exist
    v1_node = view.resolve_npc_dialogue("viper_1")
    assert v1_node is not None
    assert v1_node.node_id == "viper_1_deck_briefing"

    # Advance sortie: Reiner transitions to bridge_reiner_scrutiny
    story_mgr.advance_sortie(act=2, sortie=2)
    reiner_s2 = view.resolve_npc_dialogue("npc_reiner")
    assert reiner_s2 is not None
    assert reiner_s2.node_id == "bridge_reiner_scrutiny"

    # Unknown or invalid NPC IDs return None safely
    assert view.resolve_npc_dialogue("unknown_mechanic") is None
    assert view.resolve_npc_dialogue("") is None
    assert view.resolve_npc_dialogue(None) is None  # type: ignore[arg-type]
    assert view.resolve_npc_dialogue(True) is None  # type: ignore[arg-type]


def test_ready_room_morale_reflects_recent_sortie_casualties_and_replacements(story_mgr):
    """Verify Ready Room morale resolver dynamically handles flawless, casualties, and replacements."""
    view = SuperDestroyerView(story_manager=story_mgr)

    # 1. Flawless outcome: 0 casualties, not wiped
    view.set_last_sortie_stats(casualties_count=0, squad_wiped=False)
    assert view.get_ready_room_morale_state() == "flawless"
    node_flawless = view.resolve_npc_dialogue("viper_1")
    assert node_flawless is not None
    assert node_flawless.node_id == "viper_debrief_flawless"

    # 2. Casualties outcome: 2 casualties, not wiped
    view.set_last_sortie_stats(casualties_count=2, squad_wiped=False)
    assert view.get_ready_room_morale_state() == "casualties"
    node_cas = view.resolve_npc_dialogue("viper_2")
    assert node_cas is not None
    assert node_cas.node_id == "viper_debrief_casualties"

    # 3. Replacements outcome: squad wiped (even with low count)
    view.set_last_sortie_stats(casualties_count=1, squad_wiped=True)
    assert view.get_ready_room_morale_state() == "replacements"
    node_wiped = view.resolve_npc_dialogue("viper_3")
    assert node_wiped is not None
    assert node_wiped.node_id == "viper_debrief_replacements"

    # 4. Replacements outcome: 4+ casualties
    view.set_last_sortie_stats(casualties_count=4, squad_wiped=False)
    assert view.get_ready_room_morale_state() == "replacements"
    node_four = view.resolve_npc_dialogue("viper_4")
    assert node_four is not None
    assert node_four.node_id == "viper_debrief_replacements"


def test_npc_dialogue_completion_tracker_prevents_duplicate_loyalty_farming(story_mgr):
    """Verify dialogue nodes can only be answered once per sortie to prevent loyalty exploitation."""
    view = SuperDestroyerView(story_manager=story_mgr)
    initial_loyalty = story_mgr.loyalty  # 70.0

    node_id = "bridge_vance_logistics"
    assert view.is_node_completed_in_current_sortie(node_id) is False

    # First completion: applies delta (+8.0) and records completion
    opt1 = view.record_npc_choice(node_id, "loyal")
    assert opt1 is not None
    assert story_mgr.loyalty == pytest.approx(initial_loyalty + 8.0)
    assert view.is_node_completed_in_current_sortie(node_id) is True

    # Duplicate attempt in same sortie: rejected, loyalty untouched
    opt2 = view.record_npc_choice(node_id, "loyal")
    assert opt2 is None
    assert story_mgr.loyalty == pytest.approx(initial_loyalty + 8.0)

    # Advance to next sortie: completion flag resets for new sortie
    story_mgr.advance_sortie(act=1, sortie=2)
    assert view.is_node_completed_in_current_sortie(node_id) is False


def test_mouse_click_on_npc_cards_triggers_interact_npc_across_zones(story_mgr):
    """Verify clicking on active zone NPC cards triggers interact_npc action and SFX."""
    audio_mock = MagicMock()
    view = SuperDestroyerView(story_manager=story_mgr, audio_manager=audio_mock)

    # 1. Bridge: Click Reiner
    assert view.active_zone == ZONE_BRIDGE
    reiner_rect = view.npc_card_rects["npc_reiner"]
    click_reiner = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=reiner_rect.center)
    res_reiner = view.handle_event(click_reiner)
    assert res_reiner is not None
    assert res_reiner["action"] == "interact_npc"
    assert res_reiner["npc_id"] == "npc_reiner"
    assert res_reiner["node"].node_id == "sortie_1_briefing"
    audio_mock.play_sfx.assert_called_with("ui_click")
    view.close_dialogue()

    # Bridge: Click Vance
    audio_mock.reset_mock()
    vance_rect = view.npc_card_rects["npc_vance"]
    click_vance = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=vance_rect.center)
    res_vance = view.handle_event(click_vance)
    assert res_vance is not None
    assert res_vance["action"] == "interact_npc"
    assert res_vance["npc_id"] == "npc_vance"
    assert res_vance["node"].node_id == "bridge_vance_logistics"
    audio_mock.play_sfx.assert_called_with("ui_click")
    view.close_dialogue()

    # 2. Ready Room: Click Viper 1 .. 4
    view.select_zone(ZONE_READY_ROOM)
    for i in range(1, 5):
        vid = f"viper_{i}"
        card_rect = view.npc_card_rects[vid]
        click_v = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=card_rect.center)
        res_v = view.handle_event(click_v)
        assert res_v is not None
        assert res_v["action"] == "interact_npc"
        assert res_v["npc_id"] == vid
        assert res_v["node"].node_id == f"viper_{i}_deck_briefing"
        view.close_dialogue()

    # 3. Hangar: Click Ortiz
    view.select_zone(ZONE_HANGAR)
    ortiz_rect = view.npc_card_rects["npc_ortiz"]
    click_ortiz = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=ortiz_rect.center)
    res_ortiz = view.handle_event(click_ortiz)
    assert res_ortiz is not None
    assert res_ortiz["action"] == "interact_npc"
    assert res_ortiz["npc_id"] == "npc_ortiz"
    assert res_ortiz["node"].node_id == "hangar_ortiz_maintenance"
    view.close_dialogue()

    # Right clicks or clicks outside return None
    click_right = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=3, pos=ortiz_rect.center)
    assert view.handle_event(click_right) is None

    click_empty = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(10, 10))
    assert view.handle_event(click_empty) is None


def test_npc_dialogue_completion_tracker_respects_reloaded_dialogue_history(tmp_path):
    """Verify dialogue completion status persists across reloaded StoryManager instances and handles act fallbacks."""
    save_mgr = CampaignSaveManager(data_dir=tmp_path)
    story1 = StoryManager(save_manager=save_mgr)
    view1 = SuperDestroyerView(story_manager=story1)

    node_id = "bridge_vance_logistics"
    opt = view1.record_npc_choice(node_id, "loyal")
    assert opt is not None
    assert story1.loyalty == pytest.approx(78.0)
    assert view1.is_node_completed_in_current_sortie(node_id) is True

    # Reload new StoryManager and SuperDestroyerView from the persisted save
    story2 = StoryManager(save_manager=save_mgr)
    view2 = SuperDestroyerView(story_manager=story2)
    assert view2.is_node_completed_in_current_sortie(node_id) is True
    assert view2.record_npc_choice(node_id, "loyal") is None

    # Test fallback behavior when entry has 'sortie' but is missing 'act' key (defaults to Act 1)
    story2.dialogue_history.append({"node": "hangar_ortiz_maintenance", "sortie": 1})
    # In Act 1, Sortie 1, it should match
    assert view2.is_node_completed_in_current_sortie("hangar_ortiz_maintenance") is True

    # Advance to Act 2, Sortie 1 -> missing 'act' in history defaults to 1 and must NOT match Act 2
    story2.advance_sortie(act=2, sortie=1)
    assert view2.is_node_completed_in_current_sortie("hangar_ortiz_maintenance") is False


def test_set_last_sortie_stats_sanitizes_invalid_and_boundary_inputs(story_mgr):
    """Verify set_last_sortie_stats defensively clamps invalid, negative, NaN, and boolean values."""
    view = SuperDestroyerView(story_manager=story_mgr)

    # Negative casualties clamp to 0; hull_ratio > 1.0 clamps to 1.0
    view.set_last_sortie_stats(casualties_count=-10, hull_ratio=1.5)
    assert view.last_casualties_count == 0
    assert view.last_hull_ratio == 1.0

    # Boolean casualties fallback to 0; hull_ratio NaN fallbacks to 1.0
    view.set_last_sortie_stats(casualties_count=True, hull_ratio=float("nan"))
    assert view.last_casualties_count == 0
    assert view.last_hull_ratio == 1.0

    # Negative hull ratio clamps to 0.0
    view.set_last_sortie_stats(casualties_count=2, hull_ratio=-0.5)
    assert view.last_casualties_count == 2
    assert view.last_hull_ratio == 0.0


def test_resolve_npc_dialogue_shortcut_aliases_and_sortie_boundaries(story_mgr):
    """Verify direct debrief shortcuts and Reiner act/sortie transition boundaries."""
    view = SuperDestroyerView(story_manager=story_mgr)

    # Direct debrief shortcuts
    node_debrief = view.resolve_npc_dialogue("viper_debrief")
    assert node_debrief is not None
    assert node_debrief.node_id == "viper_debrief_flawless"

    node_ready = view.resolve_npc_dialogue("ready_room_debrief")
    assert node_ready is not None
    assert node_ready.node_id == "viper_debrief_flawless"

    node_squad = view.resolve_npc_dialogue("viper_squad")
    assert node_squad is not None
    assert node_squad.node_id == "viper_debrief_flawless"

    node_hangar = view.resolve_npc_dialogue("sortie_1_hangar_debrief")
    assert node_hangar is not None
    assert node_hangar.node_id == "sortie_1_hangar_debrief"

    # Reiner at Act 1, Sortie 2 transitions to scrutiny
    story_mgr.advance_sortie(act=1, sortie=2)
    node_r1_s2 = view.resolve_npc_dialogue("npc_reiner")
    assert node_r1_s2 is not None
    assert node_r1_s2.node_id == "bridge_reiner_scrutiny"

    # Reiner at Act 2, Sortie 1 transitions to scrutiny
    story_mgr.advance_sortie(act=2, sortie=1)
    node_r2_s1 = view.resolve_npc_dialogue("npc_reiner")
    assert node_r2_s1 is not None
    assert node_r2_s1.node_id == "bridge_reiner_scrutiny"


# -----------------------------------------------------------------------------
# Issue #59: Interactive Dialogue Modal, Typewriter & Portrait Tests
# -----------------------------------------------------------------------------

def test_dialogue_modal_opens_on_npc_click_and_blocks_zone_navigation(story_mgr):
    """Verify opening dialogue modal traps navigation hotkeys, zone tab clicks, and supports set_dialogue_open."""
    audio_mock = MagicMock()
    view = SuperDestroyerView(story_manager=story_mgr, audio_manager=audio_mock)

    # 1. Click Reiner to open dialogue modal
    reiner_rect = view.npc_card_rects["npc_reiner"]
    click_evt = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=reiner_rect.center)
    res = view.handle_event(click_evt)
    assert res is not None
    assert res["action"] == "interact_npc"
    assert view.is_dialogue_open is True
    assert view.active_npc_id == "npc_reiner"
    assert view.active_dialogue_node is not None
    assert view.active_dialogue_node.node_id == "sortie_1_briefing"

    # 2. Verify zone navigation keys and launch hotkey are strictly trapped/blocked
    for key in (pygame.K_a, pygame.K_d, pygame.K_LEFT, pygame.K_RIGHT, pygame.K_l):
        evt = pygame.event.Event(pygame.KEYDOWN, key=key)
        assert view.handle_event(evt) is None
    assert view.active_zone == ZONE_BRIDGE

    # 3. Verify clicks on zone tabs are ignored while dialogue modal is open
    ready_tab_rect = view.zone_tab_rects[ZONE_READY_ROOM]
    click_tab = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=ready_tab_rect.center)
    assert view.handle_event(click_tab) is None
    assert view.active_zone == ZONE_BRIDGE

    # 4. Issue #63: Test public set_dialogue_open API
    view.set_dialogue_open(False)
    assert view.is_dialogue_open is False
    view.set_dialogue_open(True)
    assert view.is_dialogue_open is True
    view.close_dialogue()
    assert view.is_dialogue_open is False


def test_dialogue_typewriter_advances_and_space_skips_to_full_text(story_mgr):
    """Verify typewriter advances proportionally with dt and Spacebar immediately skips to full prompt."""
    view = SuperDestroyerView(story_manager=story_mgr)
    node = view.open_npc_dialogue("npc_vance")
    assert node is not None
    assert view.is_dialogue_open is True
    assert view.typewriter_chars == 0.0
    full_len = float(len(node.prompt))

    # Advance typewriter with dt
    view.update(0.1)
    assert 0.0 < view.typewriter_chars < full_len

    # Press SPACE: skips typewriter to complete length
    evt_space = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE)
    res = view.handle_event(evt_space)
    assert res == {"action": "skip_typewriter"}
    assert view.typewriter_chars == full_len
    # Modal remains open awaiting stance choice
    assert view.is_dialogue_open is True
    assert view.selected_option is None


def test_dialogue_stance_selection_via_keyboard_and_mouse_updates_loyalty_and_shows_response(story_mgr):
    """Verify keyboard numbers [1-3] and mouse clicks choose stances, record choices, and display responses."""
    audio_mock = MagicMock()
    view = SuperDestroyerView(story_manager=story_mgr, audio_manager=audio_mock)

    # 1. Keyboard selection on Vance: Press 1 for LOYAL
    node = view.open_npc_dialogue("npc_vance")
    assert node is not None
    initial_loyalty = story_mgr.loyalty  # 70.0
    evt_1 = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_1)
    res_1 = view.handle_event(evt_1)
    assert res_1 is not None
    assert res_1["action"] == "dialogue_choice"
    assert res_1["stance"] == "loyal"
    assert res_1["loyalty_delta"] == 8.0
    assert story_mgr.loyalty == pytest.approx(initial_loyalty + 8.0)
    assert view.selected_option is not None
    assert view.selected_option.stance == "loyal"
    assert view.response_text == view.selected_option.response
    assert view.dialogue_completed_mode is True

    # Press ESC to close dialogue
    evt_esc = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE)
    res_esc = view.handle_event(evt_esc)
    assert res_esc == {"action": "close_dialogue"}
    assert view.is_dialogue_open is False

    # 2. Mouse selection on Ortiz: Click Dissident option card
    view.select_zone(ZONE_HANGAR)
    node_ortiz = view.open_npc_dialogue("npc_ortiz")
    assert node_ortiz is not None
    current_loyalty = story_mgr.loyalty  # 78.0
    dissident_rect = view.modal_option_rects["dissident"]
    click_dissident = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=dissident_rect.center)
    res_dis = view.handle_event(click_dissident)
    assert res_dis is not None
    assert res_dis["action"] == "dialogue_choice"
    assert res_dis["stance"] == "dissident"
    assert res_dis["loyalty_delta"] == -8.0
    assert story_mgr.loyalty == pytest.approx(current_loyalty - 8.0)
    assert view.selected_option.stance == "dissident"

    # Click Continue button to close modal
    click_cont = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=view.modal_continue_rect.center)
    res_cont = view.handle_event(click_cont)
    assert res_cont == {"action": "close_dialogue"}
    assert view.is_dialogue_open is False


def test_dialogue_completed_node_opens_in_readonly_review_mode_without_farming(story_mgr):
    """Verify previously completed nodes open in read-only review mode without allowing duplicate score changes."""
    view = SuperDestroyerView(story_manager=story_mgr)

    # Complete Vance dialogue
    view.open_npc_dialogue("npc_vance")
    view.select_dialogue_stance("neutral")
    assert story_mgr.loyalty == pytest.approx(70.0)
    view.close_dialogue()

    # Re-open Vance dialogue in same sortie
    node = view.open_npc_dialogue("npc_vance")
    assert node is not None
    assert view.is_dialogue_open is True
    assert view.dialogue_completed_mode is True
    assert view.response_text is not None
    assert view.typewriter_chars == len(node.prompt)

    # Trying to pick stance 1 or clicking option card does nothing
    evt_1 = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_1)
    assert view.handle_event(evt_1) is None
    click_opt = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=view.modal_option_rects["loyal"].center)
    assert view.handle_event(click_opt) is None
    assert story_mgr.loyalty == pytest.approx(70.0)

    # Pressing SPACE or ENTER closes the completed review modal
    evt_space = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE)
    assert view.handle_event(evt_space) == {"action": "close_dialogue"}
    assert view.is_dialogue_open is False


def test_dialogue_modal_portrait_caching_and_zero_per_frame_allocations(story_mgr):
    """Verify portrait caching, procedural military fallbacks, and 0 surface allocations during modal draw."""
    view = SuperDestroyerView(story_manager=story_mgr)

    # Test portraits for all 7 NPCs
    for npc_id in ("npc_reiner", "npc_vance", "npc_ortiz", "viper_1", "viper_2", "viper_3", "viper_4"):
        prof = get_ship_npc_profile(npc_id)
        assert prof is not None
        surf = view._get_or_create_portrait_surface(prof.portrait_path, prof.npc_id, (128, 128))
        assert isinstance(surf, pygame.Surface)
        assert surf.get_size() == (128, 128)

    # Path traversal and invalid inputs fallback cleanly
    fallback_surf = view._get_or_create_portrait_surface("../../../etc/passwd", "unknown_npc", (128, 128))
    assert isinstance(fallback_surf, pygame.Surface)
    assert fallback_surf.get_size() == (128, 128)

    # Zero per-frame allocations during steady-state rendering with modal open
    view.open_npc_dialogue("npc_reiner")
    screen = pygame.Surface((1280, 720))

    # Warmup
    view.update(0.016)
    view.draw(screen)

    # Fast forward typewriter to full prompt
    view.typewriter_chars = float(len(view.active_dialogue_node.prompt))
    view.draw(screen)

    with patch("eagle1.story.super_destroyer_view.pygame.Surface") as mock_surface:
        for _ in range(30):
            view.update(0.016)
            view.draw(screen)
        assert mock_surface.call_count == 0


def test_set_last_sortie_stats_handles_nan_and_inf_casualties(story_mgr):
    """Verify set_last_sortie_stats defensively guards against NaN and Infinity casualties (Issue #64)."""
    view = SuperDestroyerView(story_manager=story_mgr)

    view.set_last_sortie_stats(casualties_count=float("nan"))
    assert view.last_casualties_count == 0

    view.set_last_sortie_stats(casualties_count=float("inf"))
    assert view.last_casualties_count == 0

    view.set_last_sortie_stats(casualties_count=float("-inf"))
    assert view.last_casualties_count == 0


def test_dialogue_modal_guarantees_zero_layout_overlaps_across_all_nodes(story_mgr):
    """Verify that all textboxes, option cards, portraits, and buttons have 0 overlapping bounding boxes."""
    from eagle1.ui.layout import validate_rects_no_overlap

    view = SuperDestroyerView(story_manager=story_mgr)
    for npc_id in ("npc_reiner", "npc_vance", "npc_ortiz", "viper_1", "viper_2", "viper_3", "viper_4"):
        view.open_npc_dialogue(npc_id)
        assert view.is_dialogue_open is True

        rects = [
            view.modal_portrait_rect,
            view.modal_prompt_rect,
            view.modal_continue_rect,
        ]
        if view.response_text and view.modal_response_rect.height > 0:
            rects.append(view.modal_response_rect)
        for opt_rect in view.modal_option_rects.values():
            rects.append(opt_rect)

        collisions = validate_rects_no_overlap(rects)
        assert collisions == [], f"Collisions detected for NPC {npc_id}: {collisions}"

        # Test also after stance choice (response visible)
        view.select_dialogue_stance("loyal")
        rects_after = [
            view.modal_portrait_rect,
            view.modal_prompt_rect,
            view.modal_continue_rect,
        ]
        if view.modal_response_rect.height > 0:
            rects_after.append(view.modal_response_rect)
        for opt_rect in view.modal_option_rects.values():
            rects_after.append(opt_rect)

        collisions_after = validate_rects_no_overlap(rects_after)
        assert collisions_after == [], f"Collisions detected after choice for NPC {npc_id}: {collisions_after}"

        # Verify option cards have clean tags and zero loyalty deltas exposed to player
        for stance in ("loyal", "neutral", "dissident"):
            tag_surf = view._modal_text_cache.get(f"opt_tag_{stance}")
            delta_surf = view._modal_text_cache.get(f"opt_delta_{stance}")
            body_surf = view._modal_text_cache.get(f"opt_body_{stance}")
            assert tag_surf is not None
            assert delta_surf is None, f"Loyalty delta badge must be hidden from player: {stance}"
            assert body_surf is not None

        # Verify Response panel has no patriotism delta exposed to player
        if view.response_text:
            hdr_surf = view._modal_text_cache.get("response_header")
            resp_delta_surf = view._modal_text_cache.get("response_delta")
            assert hdr_surf is not None
            assert resp_delta_surf is None, "Loyalty delta in response panel must be hidden from player"

        view.close_dialogue()


def test_wrap_text_to_width_clamping_and_unbroken_words(story_mgr):
    """Verify _wrap_text_to_width handles empty input, max lines clamping, and long words."""
    view = SuperDestroyerView(story_manager=story_mgr)

    # Empty text
    assert view._wrap_text_to_width("", view.font_modal_prompt, 400) == []

    # None font fallback
    assert view._wrap_text_to_width("Hello world", None, 400) == ["Hello world"]

    # Max lines clamping
    long_passage = "One two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen twenty"
    lines = view._wrap_text_to_width(long_passage, view.font_modal_prompt, max_width=150, max_lines=3)
    assert len(lines) == 3

    # Long unbroken word wider than max_width
    unbroken = "ANTIAIRSUPERDESTROYERTACCOMmsPROTOCOLOVERRIDE123456789"
    lines2 = view._wrap_text_to_width(unbroken, view.font_modal_prompt, max_width=100)
    assert len(lines2) == 1
    assert lines2[0] == unbroken


def test_dialogue_modal_zero_overlaps_all_database_nodes_and_all_stances(story_mgr):
    """Verify that every node in DIALOGUE_DATABASE across all 3 stances never violates zero-overlap invariants."""
    from eagle1.story.dialogue_db import DIALOGUE_DATABASE
    from eagle1.ui.layout import validate_rects_no_overlap

    view = SuperDestroyerView(story_manager=story_mgr)

    for node_id, node in DIALOGUE_DATABASE.items():
        # Set node directly
        view._dialogue_open = True
        view.active_npc_id = node.speaker.lower()
        view.active_dialogue_node = node
        view.typewriter_chars = float(len(node.prompt))
        view.dialogue_completed_mode = False
        view.selected_option = None
        view.selected_stance = None
        view.response_text = None
        view._rebuild_modal_cache()

        rects = [
            view.modal_portrait_rect,
            view.modal_prompt_rect,
            view.modal_continue_rect,
        ]
        for opt_rect in view.modal_option_rects.values():
            rects.append(opt_rect)

        colls = validate_rects_no_overlap(rects)
        assert colls == [], f"Collision on node {node_id} before choice: {colls}"

        # Test each stance choice
        for stance in ("loyal", "neutral", "dissident"):
            if stance in node.options:
                view.select_dialogue_stance(stance)
                rects_after = [
                    view.modal_portrait_rect,
                    view.modal_prompt_rect,
                    view.modal_continue_rect,
                ]
                if view.modal_response_rect.height > 0:
                    rects_after.append(view.modal_response_rect)
                for opt_rect in view.modal_option_rects.values():
                    rects_after.append(opt_rect)

                colls_after = validate_rects_no_overlap(rects_after)
                assert colls_after == [], f"Collision on node {node_id} with stance {stance}: {colls_after}"

        view.close_dialogue()


def test_dialogue_modal_click_priority_over_background_npc_cards(story_mgr):
    """Verify clicking on modal option cards takes strict precedence over underlying deck NPC cards."""
    view = SuperDestroyerView(story_manager=story_mgr)
    view.select_zone("bridge")
    # Open dialogue with Reiner
    view.open_npc_dialogue("npc_reiner")
    assert view.is_dialogue_open is True
    assert view.active_npc_id == "npc_reiner"

    # Click on the neutral option card (which is in the vicinity of Vance's background deck card)
    click_pos = view.modal_option_rects["neutral"].center
    event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=click_pos)
    res = view.handle_event(event)

    # Must record choice for Reiner, NOT switch to Vance!
    assert res is not None
    assert res.get("action") == "dialogue_choice"
    assert res.get("stance") == "neutral"
    assert view.active_npc_id == "npc_reiner"


def test_update_dt_inf_and_bool_safety(story_mgr):
    """Verify update defensively handles inf, nan, and boolean dt values without crashing."""
    view = SuperDestroyerView(story_manager=story_mgr)

    # These must not raise exceptions
    view.update(float("inf"))
    view.update(float("-inf"))
    view.update(float("nan"))
    view.update(True)  # type: ignore
    view.update(False)  # type: ignore
    view.update(0.016)
    assert view.ambient_timer > 0.0


def test_sortie_mission_map_and_fallback_progression(story_mgr):
    """Verify sortie numbers map cleanly to designated campaign mission types (1..4) with safe fallbacks."""
    from eagle1.story.super_destroyer_view import SORTIE_MISSION_MAP

    view = SuperDestroyerView(story_manager=story_mgr)

    # Sortie 1 -> air_superiority
    story_mgr.current_sortie = 1
    assert view.get_current_sortie_mission_id() == SORTIE_MISSION_MAP[1]
    assert view.get_current_sortie_mission_id() == "air_superiority"

    # Sortie 2 -> base_defense
    story_mgr.current_sortie = 2
    assert view.get_current_sortie_mission_id() == SORTIE_MISSION_MAP[2]
    assert view.get_current_sortie_mission_id() == "base_defense"

    # Sortie 3 -> outpost_demolition
    story_mgr.current_sortie = 3
    assert view.get_current_sortie_mission_id() == SORTIE_MISSION_MAP[3]
    assert view.get_current_sortie_mission_id() == "outpost_demolition"

    # Sortie 4 -> strider_raid
    story_mgr.current_sortie = 4
    assert view.get_current_sortie_mission_id() == SORTIE_MISSION_MAP[4]
    assert view.get_current_sortie_mission_id() == "strider_raid"

    # Fallbacks: sortie > 4
    story_mgr.current_sortie = 5
    assert view.get_current_sortie_mission_id() == "outpost_demolition"
    story_mgr.current_sortie = 99
    assert view.get_current_sortie_mission_id() == "outpost_demolition"

    # Defensive boundaries: NaN, inf, 0, bool
    story_mgr.current_sortie = float("nan")
    assert view.get_current_sortie_mission_id() == "air_superiority"
    story_mgr.current_sortie = float("inf")
    assert view.get_current_sortie_mission_id() == "air_superiority"
    story_mgr.current_sortie = 0
    assert view.get_current_sortie_mission_id() == "air_superiority"
    story_mgr.current_sortie = True
    assert view.get_current_sortie_mission_id() == "air_superiority"


def test_aircraft_diagnostics_summary_nominal_and_low_hull_warning(story_mgr):
    """Verify get_aircraft_diagnostics_summary generates status and warning when hull_ratio < 0.4."""
    view = SuperDestroyerView(story_manager=story_mgr)

    # Nominal state (100% hull)
    view.set_last_sortie_stats(casualties_count=0, hull_ratio=1.0)
    diag_nom = view.get_aircraft_diagnostics_summary()
    assert diag_nom["warning"] is False
    assert diag_nom["status_level"] == "NOMINAL"
    assert diag_nom["hull_percent"] == 100.0
    assert "CALIBRATED" in diag_nom["cannons_status"]
    assert "OPTIMAL" in diag_nom["turbines_status"]
    assert "primed for the rail" in diag_nom["ortiz_commentary"]

    # Caution state (50% hull)
    view.set_last_sortie_stats(casualties_count=0, hull_ratio=0.5)
    diag_caut = view.get_aircraft_diagnostics_summary()
    assert diag_caut["warning"] is False
    assert diag_caut["status_level"] == "CAUTION"
    assert diag_caut["hull_percent"] == 50.0

    # Warning state (< 40% hull)
    view.set_last_sortie_stats(casualties_count=2, hull_ratio=0.25)
    diag_warn = view.get_aircraft_diagnostics_summary()
    assert diag_warn["warning"] is True
    assert diag_warn["status_level"] == "WARNING"
    assert diag_warn["hull_percent"] == 25.0
    assert "CRITICAL" in diag_warn["hull_status"]
    assert "STRAINED" in diag_warn["cannons_status"]
    assert "LEAK" in diag_warn["turbines_status"]
    assert "took a beating" in diag_warn["ortiz_commentary"]

    # Casualties only (100% hull, but empty racks)
    view.set_last_sortie_stats(casualties_count=1, hull_ratio=1.0)
    diag_cas = view.get_aircraft_diagnostics_summary()
    assert diag_cas["warning"] is False
    assert "empty racks" in diag_cas["ortiz_commentary"]


def test_catapult_launch_button_click_and_hotkey_and_modal_block(story_mgr):
    """Verify catapult launch triggers action payload via click and L hotkey, blocked during dialogue."""
    audio_mock = MagicMock()
    view = SuperDestroyerView(story_manager=story_mgr, audio_manager=audio_mock)
    view.select_zone("hangar")
    assert view.active_zone == "hangar"

    story_mgr.current_act = 1
    story_mgr.current_sortie = 2

    # 1. Hotkey L in Hangar
    key_l = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_l)
    res_key = view.handle_event(key_l)
    assert res_key is not None
    assert res_key["action"] == "launch_sortie"
    assert res_key["mission_id"] == "base_defense"
    assert res_key["act"] == 1
    assert res_key["sortie"] == 2
    audio_mock.play_sfx.assert_called_with("ui_click")

    # 2. Click on btn_launch_rect in Hangar
    audio_mock.reset_mock()
    click_pos = view.btn_launch_rect.center
    click_event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=click_pos)
    res_click = view.handle_event(click_event)
    assert res_click is not None
    assert res_click["action"] == "launch_sortie"
    assert res_click["mission_id"] == "base_defense"
    audio_mock.play_sfx.assert_called_with("ui_click")

    # 3. Blocked when on other zones
    view.select_zone("bridge")
    res_bridge = view.handle_event(click_event)
    assert res_bridge is None
    res_bridge_key = view.handle_event(key_l)
    assert res_bridge_key is None

    # 4. Strict Modality: Blocked when dialogue modal is open
    view.select_zone("hangar")
    view.open_npc_dialogue("npc_ortiz")
    assert view.is_dialogue_open is True
    res_modal_click = view.handle_event(click_event)
    assert res_modal_click is None
    res_modal_key = view.handle_event(key_l)
    assert res_modal_key is None
    assert view.trigger_catapult_launch() is None


def test_hangar_deck_layout_zero_overlaps_and_zero_per_frame_allocations(story_mgr):
    """Verify Hangar deck elements do not overlap and steady-state draw has 0 surface allocations."""
    from eagle1.ui.layout import validate_rects_no_overlap

    view = SuperDestroyerView(story_manager=story_mgr)
    view.select_zone("hangar")

    # Overlap validation among hangar elements
    rects = [
        view.npc_card_rects["npc_ortiz"],
        view.hangar_diagnostics_rect,
        view.hangar_briefing_rect,
        view.btn_launch_rect,
    ]
    overlaps = validate_rects_no_overlap(rects)
    assert overlaps == [], f"Overlaps detected on Hangar deck: {overlaps}"

    # Zero per-frame allocations during draw in Hangar zone
    screen = pygame.Surface((1280, 720))
    view.update(0.016)
    view.draw(screen, mouse_pos=(100, 100))

    with patch("eagle1.story.super_destroyer_view.pygame.Surface") as mock_surface:
        for _ in range(30):
            view.update(0.016)
            view.draw(screen, mouse_pos=(100, 100))
        assert mock_surface.call_count == 0


def test_hangar_deck_supplemental_boundaries_and_briefing_card(story_mgr):
    """Verify briefing metadata structure, exact threshold boundaries, K_f launch key, and launch state reset."""
    view = SuperDestroyerView(story_manager=story_mgr)

    # 1. Direct get_current_sortie_briefing verification across sorties & fallbacks
    for sortie_num, expected_mission in [(1, "air_superiority"), (2, "base_defense"), (3, "outpost_demolition"), (4, "strider_raid")]:
        story_mgr.current_sortie = sortie_num
        briefing = view.get_current_sortie_briefing()
        assert briefing["mission_id"] == expected_mission
        assert all(k in briefing for k in ("title", "operation", "objective", "threat", "mission_id"))

    # Fallback briefing (sortie > 4 and NaN)
    story_mgr.current_sortie = 99
    assert view.get_current_sortie_briefing()["mission_id"] == "outpost_demolition"
    story_mgr.current_sortie = float("nan")
    assert view.get_current_sortie_briefing()["mission_id"] == "air_superiority"

    # 2. Exact diagnostics threshold boundaries (0.40 and 0.75)
    diag_399 = view.get_aircraft_diagnostics_summary(hull_ratio=0.399)
    assert diag_399["status_level"] == "WARNING"
    assert diag_399["warning"] is True

    diag_400 = view.get_aircraft_diagnostics_summary(hull_ratio=0.40)
    assert diag_400["status_level"] == "CAUTION"
    assert diag_400["warning"] is False

    diag_749 = view.get_aircraft_diagnostics_summary(hull_ratio=0.749)
    assert diag_749["status_level"] == "CAUTION"

    diag_750 = view.get_aircraft_diagnostics_summary(hull_ratio=0.75)
    assert diag_750["status_level"] == "NOMINAL"

    # Direct NaN / Inf arguments to get_aircraft_diagnostics_summary
    diag_nan = view.get_aircraft_diagnostics_summary(hull_ratio=float("nan"), casualties_count=float("inf"))
    assert diag_nan["hull_ratio"] == 1.0
    assert diag_nan["status_level"] == "NOMINAL"

    # 3. Secondary launch hotkey K_f
    view.select_zone("hangar")
    key_f = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_f)
    res_f = view.handle_event(key_f)
    assert res_f is not None and res_f["action"] == "launch_sortie"
    assert view.launch_initiated is True

    # 4. Zone cycling resets launch_initiated
    view.select_zone("bridge")
    assert view.launch_initiated is False


def test_top_hud_bar_patriotism_hidden_from_player(story_mgr):
    """Verify that patriotism loyalty score and progress bar are completely hidden from player in HUD."""
    view = SuperDestroyerView(story_manager=story_mgr)
    screen = pygame.Surface((1280, 720))
    view.draw(screen)

    # Status title in HUD must be neutral fleet command, not patriotism score
    fleet_hdr = view._cached_static_texts.get("fleet_status_title")
    assert fleet_hdr is not None

    # Verify patriotism_status is not populated in dynamic surfaces during HUD draw
    assert "patriotism_status" not in view._cached_dynamic_surfaces

    # Underlying calculation methods remain available for internal logic
    assert view.get_patriotism_bar_ratio() >= 0.0
    label, _ = view.get_patriotism_status_label_and_color()
    assert label in (PATRIOTISM_LABEL_NOMINAL, PATRIOTISM_LABEL_ZEALOT, PATRIOTISM_LABEL_DISSIDENT)


def test_sanitized_act_sortie_in_hud_and_dialogue_resolution(story_mgr):
    """Verify resolve_npc_dialogue and _draw_top_hud_bar safely handle NaN and Inf."""
    view = SuperDestroyerView(story_manager=story_mgr)
    story_mgr.current_act = float("nan")
    story_mgr.current_sortie = float("inf")

    # Should not crash on Reiner dialogue resolution
    node = view.resolve_npc_dialogue("npc_reiner")
    assert node is not None

    # Should not throw or thrash dynamic cache on draw
    screen = pygame.Surface((1280, 720))
    view.draw(screen)
    cached_badge = view._cached_dynamic_surfaces.get("campaign_badge")
    assert cached_badge is not None
    assert cached_badge[0] == (1, 1)






