"""Tests for StoryManager State Machine, Loyalty Vector, and Dialogue Hooks."""

from pathlib import Path
import tempfile
import pytest

from eagle1.story.campaign_save import CampaignSaveManager
from eagle1.story.dialogue_db import get_dialogue_node
from eagle1.story.story_manager import StoryManager


@pytest.fixture
def temp_campaign_dir():
    """Create an isolated temporary directory for story manager tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


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
    """Verify ending branch selection matches tripartite thresholds in spec."""
    save_mgr = CampaignSaveManager(data_dir=temp_campaign_dir)
    story = StoryManager(save_manager=save_mgr)

    # Zealot path: >= 90.0
    story.loyalty = 90.0
    assert story.get_ending_branch() == "OBEDIENCE_PURGE"
    story.loyalty = 100.0
    assert story.get_ending_branch() == "OBEDIENCE_PURGE"

    # Dissident path: <= 15.0
    story.loyalty = 15.0
    assert story.get_ending_branch() == "DISSIDENT_SURRENDER"
    story.loyalty = 0.0
    assert story.get_ending_branch() == "DISSIDENT_SURRENDER"

    # Cold protocol path: 15.1 to 89.9
    story.loyalty = 16.0
    assert story.get_ending_branch() == "COLD_PROTOCOL"
    story.loyalty = 70.0
    assert story.get_ending_branch() == "COLD_PROTOCOL"
    story.loyalty = 89.0
    assert story.get_ending_branch() == "COLD_PROTOCOL"


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

