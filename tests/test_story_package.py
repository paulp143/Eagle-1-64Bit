"""Tests for eagle1.story package public API exports and headless initialization."""

import os


def test_story_package_exports():
    """Verify all expected symbols are exported cleanly by eagle1.story."""
    import eagle1.story as story

    assert hasattr(story, "StoryManager")
    assert hasattr(story, "DEFAULT_LOYALTY")
    assert hasattr(story, "MIN_LOYALTY")
    assert hasattr(story, "MAX_LOYALTY")
    assert hasattr(story, "DECISION_TIME_DILATION")
    assert hasattr(story, "NORMAL_TIME_DILATION")
    assert hasattr(story, "CampaignSaveManager")
    assert hasattr(story, "CampaignSaveState")
    assert hasattr(story, "CAMPAIGN_SAVE_VERSION")
    assert hasattr(story, "CAMPAIGN_SAVE_FILENAME")
    assert hasattr(story, "DEFAULT_CAMPAIGN_FILE")
    assert hasattr(story, "DIALOGUE_DATABASE")
    assert hasattr(story, "DialogueNode")
    assert hasattr(story, "DialogueOption")
    assert hasattr(story, "get_dialogue_node")
    assert hasattr(story, "get_nodes_for_act_and_sortie")
    assert hasattr(story, "validate_dialogue_database")
    assert hasattr(story, "THRESHOLD_OBEDIENCE_PURGE")
    assert hasattr(story, "THRESHOLD_DISSIDENT_SURRENDER")
    assert hasattr(story, "BRANCH_OBEDIENCE_PURGE")
    assert hasattr(story, "BRANCH_DISSIDENT_SURRENDER")
    assert hasattr(story, "BRANCH_COLD_PROTOCOL")
    assert hasattr(story, "ENDING_BRANCH_OBEDIENCE_PURGE")
    assert hasattr(story, "ENDING_BRANCH_DISSIDENT_SURRENDER")
    assert hasattr(story, "ENDING_BRANCH_COLD_PROTOCOL")
    assert hasattr(story, "VALID_STANCES")


def test_headless_story_instantiation(tmp_path):
    """Verify StoryManager can be instantiated in headless environments without errors."""
    old_video = os.environ.get("SDL_VIDEODRIVER")
    old_audio = os.environ.get("SDL_AUDIODRIVER")
    try:
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        os.environ["SDL_AUDIODRIVER"] = "dummy"

        from eagle1.story import CampaignSaveManager, StoryManager

        save_mgr = CampaignSaveManager(data_dir=tmp_path)
        mgr = StoryManager(save_manager=save_mgr)
        assert mgr.loyalty == 70.0
        assert mgr.time_dilation == 1.0
    finally:
        if old_video is not None:
            os.environ["SDL_VIDEODRIVER"] = old_video
        if old_audio is not None:
            os.environ["SDL_AUDIODRIVER"] = old_audio

