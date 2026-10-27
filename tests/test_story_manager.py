"""Tests for StoryManager State Machine, Loyalty Vector, and Dialogue Hooks."""

import logging
import math
from pathlib import Path
import tempfile
import pytest

from eagle1.story.campaign_save import CampaignSaveManager
from eagle1.story.dialogue_db import DIALOGUE_DATABASE, get_dialogue_node
from eagle1.story.story_manager import (
    BRANCH_COLD_PROTOCOL,
    BRANCH_DISSIDENT_SURRENDER,
    BRANCH_OBEDIENCE_PURGE,
    DECISION_TIME_DILATION,
    DEFAULT_LOYALTY,
    ENDING_BRANCH_COLD_PROTOCOL,
    ENDING_BRANCH_DISSIDENT_SURRENDER,
    ENDING_BRANCH_OBEDIENCE_PURGE,
    MAX_LOYALTY,
    MIN_LOYALTY,
    NORMAL_TIME_DILATION,
    StoryManager,
    THRESHOLD_DISSIDENT_SURRENDER,
    THRESHOLD_OBEDIENCE_PURGE,
    VALID_STANCES,
)


@pytest.fixture
def temp_campaign_dir():
    """Create an isolated temporary directory for story manager tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


def test_story_manager_constants():
    """Verify core constants match Issue #51 and Issue #54 specifications."""
    assert DEFAULT_LOYALTY == 70.0
    assert MIN_LOYALTY == 0.0
    assert MAX_LOYALTY == 100.0
    assert DECISION_TIME_DILATION == 0.4
    assert NORMAL_TIME_DILATION == 1.0

    assert THRESHOLD_OBEDIENCE_PURGE == 90.0
    assert THRESHOLD_DISSIDENT_SURRENDER == 15.0

    assert BRANCH_OBEDIENCE_PURGE == "OBEDIENCE_PURGE"
    assert BRANCH_DISSIDENT_SURRENDER == "DISSIDENT_SURRENDER"
    assert BRANCH_COLD_PROTOCOL == "COLD_PROTOCOL"

    assert ENDING_BRANCH_OBEDIENCE_PURGE == "OBEDIENCE_PURGE"
    assert ENDING_BRANCH_DISSIDENT_SURRENDER == "DISSIDENT_SURRENDER"
    assert ENDING_BRANCH_COLD_PROTOCOL == "COLD_PROTOCOL"

    assert VALID_STANCES == ("loyal", "neutral", "dissident")


def test_story_manager_initial_defaults(temp_campaign_dir):
    """Verify default initial state of StoryManager."""
    save_mgr = CampaignSaveManager(data_dir=temp_campaign_dir)
    story = StoryManager(save_manager=save_mgr)

    assert story.loyalty == 70.0
    assert story.current_act == 1
    assert story.current_sortie == 1
    assert story.total_casualties == 0
    assert story.active_dialogue is None
    assert story.dialogue_history == []
    assert story.time_dilation == 1.0


def test_modify_loyalty_clamping(temp_campaign_dir):
    """Ensure loyalty is strictly clamped within [0.0, 100.0]."""
    save_mgr = CampaignSaveManager(data_dir=temp_campaign_dir)
    story = StoryManager(save_manager=save_mgr)

    # Test positive overflow clamping
    story.modify_loyalty(+50.0)
    assert story.loyalty == 100.0

    # Test negative underflow clamping
    story.modify_loyalty(-150.0)
    assert story.loyalty == 0.0

    # Test normal adjustment
    story.modify_loyalty(+45.5)
    assert story.loyalty == pytest.approx(45.5)


def test_modify_loyalty_extreme_and_zero_deltas(temp_campaign_dir):
    """Verify extreme deltas and zero deltas per Issue #51 acceptance criteria."""
    save_mgr = CampaignSaveManager(data_dir=temp_campaign_dir)
    story = StoryManager(save_manager=save_mgr)

    # Zero delta leaves loyalty unmodified
    story.modify_loyalty(0.0, reason="zero_delta")
    assert story.loyalty == 70.0

    # Extreme positive delta (+1000.0) clamps to 100.0
    story.modify_loyalty(+1000.0, reason="extreme_pos")
    assert story.loyalty == 100.0

    # Extreme negative delta (-1000.0) clamps to 0.0
    story.modify_loyalty(-1000.0, reason="extreme_neg")
    assert story.loyalty == 0.0

    # Positive infinity clamps to 100.0
    story.modify_loyalty(float("inf"), reason="inf_pos")
    assert story.loyalty == 100.0

    # Negative infinity clamps to 0.0
    story.modify_loyalty(float("-inf"), reason="inf_neg")
    assert story.loyalty == 0.0


def test_modify_loyalty_nan_and_invalid_types(temp_campaign_dir):
    """Ensure NaN, None, and non-numeric types are rejected gracefully without state corruption."""
    save_mgr = CampaignSaveManager(data_dir=temp_campaign_dir)
    story = StoryManager(save_manager=save_mgr)

    # NaN delta
    story.modify_loyalty(float("nan"), reason="nan_delta")
    assert not math.isnan(story.loyalty)
    assert story.loyalty == 70.0

    # None delta
    story.modify_loyalty(None, reason="none_delta")  # type: ignore[arg-type]
    assert story.loyalty == 70.0

    # Invalid string delta
    story.modify_loyalty("invalid", reason="str_delta")  # type: ignore[arg-type]
    assert story.loyalty == 70.0

    # Boolean delta (True/False should not be treated as int 1/0)
    story.modify_loyalty(True, reason="bool_delta")  # type: ignore[arg-type]
    assert story.loyalty == 70.0


def test_set_active_dialogue_idempotent_none(temp_campaign_dir):
    """Setting dialogue to None when already None must safely retain time_dilation = 1.0."""
    save_mgr = CampaignSaveManager(data_dir=temp_campaign_dir)
    story = StoryManager(save_manager=save_mgr)

    assert story.active_dialogue is None
    assert story.time_dilation == 1.0

    # Set to None again
    story.set_active_dialogue(None)
    assert story.active_dialogue is None
    assert story.time_dilation == 1.0


def test_casualty_modifiers(temp_campaign_dir):
    """Verify Helldiver casualty and squad wipe modifiers per spec."""
    save_mgr = CampaignSaveManager(data_dir=temp_campaign_dir)
    story = StoryManager(save_manager=save_mgr)
    initial_loyalty = story.loyalty  # 70.0

    # Single casualty (-3.5)
    story.on_helldiver_death(helldiver_id=1)
    assert story.loyalty == pytest.approx(initial_loyalty - 3.5)
    assert story.total_casualties == 1

    # Full squad wipe (-8.0)
    story.on_squad_wipe()
    assert story.loyalty == pytest.approx(initial_loyalty - 3.5 - 8.0)
    assert story.total_casualties == 1


def test_ending_branch_thresholds(temp_campaign_dir):
    """Verify ending branch selection matches tripartite thresholds in Issue #54 spec."""
    save_mgr = CampaignSaveManager(data_dir=temp_campaign_dir)
    story = StoryManager(save_manager=save_mgr)

    # Dissident path: <= 15.0
    story.loyalty = 0.0
    assert story.get_ending_branch() == BRANCH_DISSIDENT_SURRENDER
    story.loyalty = 15.0
    assert story.get_ending_branch() == BRANCH_DISSIDENT_SURRENDER

    # Cold protocol path: 15.0 < loyalty < 90.0 (exact boundaries)
    story.loyalty = 15.0001
    assert story.get_ending_branch() == BRANCH_COLD_PROTOCOL
    story.loyalty = 15.01
    assert story.get_ending_branch() == BRANCH_COLD_PROTOCOL
    story.loyalty = 50.0
    assert story.get_ending_branch() == BRANCH_COLD_PROTOCOL
    story.loyalty = 70.0
    assert story.get_ending_branch() == BRANCH_COLD_PROTOCOL
    story.loyalty = 89.0
    assert story.get_ending_branch() == BRANCH_COLD_PROTOCOL
    story.loyalty = 89.99
    assert story.get_ending_branch() == BRANCH_COLD_PROTOCOL
    story.loyalty = 89.999
    assert story.get_ending_branch() == BRANCH_COLD_PROTOCOL

    # Zealot path: >= 90.0
    story.loyalty = 90.0
    assert story.get_ending_branch() == BRANCH_OBEDIENCE_PURGE
    story.loyalty = 100.0
    assert story.get_ending_branch() == BRANCH_OBEDIENCE_PURGE

    # Guard against NaN loyalty
    story.loyalty = float("nan")
    assert story.get_ending_branch() == BRANCH_COLD_PROTOCOL


def test_active_dialogue_controls_time_dilation(temp_campaign_dir):
    """Verify setting active dialogue slows down time (0.4) and clearing restores to 1.0."""
    save_mgr = CampaignSaveManager(data_dir=temp_campaign_dir)
    story = StoryManager(save_manager=save_mgr)

    node = get_dialogue_node("sortie_1_briefing")
    assert node is not None

    story.set_active_dialogue(node)
    assert story.active_dialogue == node
    assert story.time_dilation == 0.4

    story.set_active_dialogue(None)
    assert story.active_dialogue is None
    assert story.time_dilation == 1.0


def test_record_choice_applies_delta_and_persists(temp_campaign_dir):
    """Verify recording a player choice applies loyalty delta, logs history, and saves."""
    save_mgr = CampaignSaveManager(data_dir=temp_campaign_dir)
    story = StoryManager(save_manager=save_mgr)

    node = get_dialogue_node("sortie_1_briefing")
    story.set_active_dialogue(node)

    # Choose 'loyal' (+8.0)
    opt = story.record_choice("sortie_1_briefing", "loyal")
    assert opt is not None
    assert opt.stance == "loyal"
    assert story.loyalty == pytest.approx(78.0)
    assert story.active_dialogue is None
    assert story.time_dilation == 1.0
    assert len(story.dialogue_history) == 1
    assert story.dialogue_history[0]["node"] == "sortie_1_briefing"
    assert story.dialogue_history[0]["stance"] == "loyal"

    # Verify state was saved to disk
    persisted = save_mgr.load_campaign()
    assert persisted.loyalty == pytest.approx(78.0)
    assert len(persisted.choices_made) == 1


def test_record_choice_all_stances_and_multipliers(temp_campaign_dir):
    """Verify all dialogue nodes satisfy multiplier ranges and choice normalizations work."""
    # Verify multiplier ranges across all built-in dialogue nodes
    for node_id, node in DIALOGUE_DATABASE.items():
        loyal_delta = node.options["loyal"].loyalty_delta
        neutral_delta = node.options["neutral"].loyalty_delta
        dissident_delta = node.options["dissident"].loyalty_delta

        assert 8.0 <= loyal_delta <= 12.0, f"Loyal delta in {node_id} outside [+8.0, +12.0]: {loyal_delta}"
        assert -1.0 <= neutral_delta <= 1.0, f"Neutral delta in {node_id} outside [-1.0, +1.0]: {neutral_delta}"
        assert -12.0 <= dissident_delta <= -8.0, f"Dissident delta in {node_id} outside [-12.0, -8.0]: {dissident_delta}"

    save_mgr = CampaignSaveManager(data_dir=temp_campaign_dir)
    story = StoryManager(save_manager=save_mgr)

    # Test bracketed and uppercase stance normalization: "[LOYAL]"
    opt1 = story.record_choice("sortie_1_briefing", "[LOYAL]")
    assert opt1 is not None
    assert opt1.stance == "loyal"
    assert story.loyalty == pytest.approx(78.0)
    assert story.dialogue_history[-1]["stance"] == "loyal"

    # Test uppercase stance: "NEUTRAL"
    opt2 = story.record_choice("sortie_1_briefing", "NEUTRAL")
    assert opt2 is not None
    assert opt2.stance == "neutral"
    assert story.loyalty == pytest.approx(78.0)  # delta 0.0
    assert story.dialogue_history[-1]["stance"] == "neutral"

    # Test whitespace-padded lowercase stance: " [dissident] "
    opt3 = story.record_choice("sortie_1_briefing", " [dissident] ")
    assert opt3 is not None
    assert opt3.stance == "dissident"
    assert story.loyalty == pytest.approx(70.0)  # 78.0 - 8.0
    assert story.dialogue_history[-1]["stance"] == "dissident"

    # Test numeric key shortcut: "1" (loyal)
    opt_key1 = story.record_choice("sortie_1_briefing", "1")
    assert opt_key1 is not None
    assert opt_key1.stance == "loyal"
    assert story.loyalty == pytest.approx(78.0)
    assert story.dialogue_history[-1]["stance"] == "loyal"

    # Active dialogue matching node_id is cleared
    node_briefing = get_dialogue_node("sortie_1_briefing")
    story.set_active_dialogue(node_briefing)
    story.record_choice("sortie_1_briefing", "loyal")
    assert story.active_dialogue is None
    assert story.time_dilation == 1.0

    # Active dialogue for DIFFERENT node is preserved
    node_inflight = get_dialogue_node("sortie_1_inflight")
    story.set_active_dialogue(node_inflight)
    story.record_choice("sortie_1_briefing", "neutral")
    assert story.active_dialogue == node_inflight
    assert story.time_dilation == 0.4


def test_record_choice_invalid_inputs(temp_campaign_dir, caplog):
    """Verify invalid node_id or invalid stance safely logs warning, returns None, and preserves state."""
    save_mgr = CampaignSaveManager(data_dir=temp_campaign_dir)
    story = StoryManager(save_manager=save_mgr)
    initial_loyalty = story.loyalty

    with caplog.at_level(logging.WARNING):
        # Unknown node_id
        res_unknown_node = story.record_choice("non_existent_node_xyz", "loyal")
        assert res_unknown_node is None
        assert story.loyalty == initial_loyalty
        assert len(story.dialogue_history) == 0

        # Invalid node_id types
        assert story.record_choice(None, "loyal") is None  # type: ignore[arg-type]
        assert story.record_choice("", "loyal") is None
        assert story.record_choice(123, "loyal") is None  # type: ignore[arg-type]
        assert story.record_choice([], "loyal") is None  # type: ignore[arg-type]

        # Unknown stance on valid node
        res_unknown_stance = story.record_choice("sortie_1_briefing", "invalid_stance_123")
        assert res_unknown_stance is None
        assert story.loyalty == initial_loyalty
        assert len(story.dialogue_history) == 0

        # Invalid stance types
        assert story.record_choice("sortie_1_briefing", None) is None  # type: ignore[arg-type]
        assert story.record_choice("sortie_1_briefing", "") is None
        assert story.record_choice("sortie_1_briefing", []) is None  # type: ignore[arg-type]

    assert len(caplog.records) > 0


def test_save_and_load_persistence_sync(temp_campaign_dir):
    """Verify a newly initialized StoryManager reloads previous saved progress."""
    save_mgr = CampaignSaveManager(data_dir=temp_campaign_dir)
    story1 = StoryManager(save_manager=save_mgr)

    story1.current_act = 2
    story1.current_sortie = 3
    story1.on_helldiver_death(1)
    story1.record_choice("sortie_1_inflight", "dissident")

    # Second instance with same save manager
    story2 = StoryManager(save_manager=save_mgr)
    assert story2.current_act == 2
    assert story2.current_sortie == 3
    assert story2.total_casualties == 1
    assert story2.loyalty == pytest.approx(story1.loyalty)
    assert len(story2.dialogue_history) == 1

