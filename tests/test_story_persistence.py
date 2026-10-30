"""Tests for Campaign Story Save Data Model and Persistence Layer."""

import logging
import os
from pathlib import Path
import tempfile
import pytest

from eagle1.story.campaign_save import (
    CAMPAIGN_SAVE_FILENAME,
    CAMPAIGN_SAVE_VERSION,
    DEFAULT_CAMPAIGN_FILE,
    MAX_CAMPAIGN_ACT,
    MAX_CAMPAIGN_SORTIE,
    CampaignSaveManager,
    CampaignSaveState,
)
from eagle1.story.story_manager import StoryManager


@pytest.fixture
def temp_campaign_dir():
    """Create an isolated temporary directory for campaign saves."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


def test_campaign_save_constants():
    """Verify core constants match Issue #52 and Issue #65 specifications."""
    assert CAMPAIGN_SAVE_VERSION == 1
    assert CAMPAIGN_SAVE_FILENAME == "campaign_save.json"
    assert DEFAULT_CAMPAIGN_FILE == "campaign_save.json"
    assert MAX_CAMPAIGN_ACT == 10
    assert MAX_CAMPAIGN_SORTIE == 100


def test_default_campaign_save_state():
    """Verify default campaign state conforms to spec baseline."""
    state = CampaignSaveState()
    assert state.version == 1
    assert state.campaign_active is True
    assert state.current_act == 1
    assert state.current_sortie == 1
    assert state.loyalty == 70.0
    assert state.total_casualties == 0
    assert state.choices_made == []
    assert state.extra == {}


def test_save_and_load_round_trip(temp_campaign_dir):
    """Verify state serialization and deserialization across disk round-trip."""
    manager = CampaignSaveManager(data_dir=temp_campaign_dir)
    assert not manager.get_save_path().exists()

    # Modify state and save
    state = CampaignSaveState(
        current_act=2,
        current_sortie=3,
        loyalty=58.5,
        total_casualties=4,
        choices_made=[
            {"node": "sortie_1_briefing", "choice": "neutral"},
            {"node": "sortie_1_mid", "choice": "loyal"},
        ],
    )
    success = manager.save_campaign(state)
    assert success is True
    assert manager.get_save_path().exists()

    # Load back and verify fields match exactly
    loaded = manager.load_campaign()
    assert loaded.version == 1
    assert loaded.campaign_active is True
    assert loaded.current_act == 2
    assert loaded.current_sortie == 3
    assert loaded.loyalty == pytest.approx(58.5)
    assert loaded.total_casualties == 4
    assert len(loaded.choices_made) == 2
    assert loaded.choices_made[0]["node"] == "sortie_1_briefing"
    assert loaded.choices_made[1]["choice"] == "loyal"


def test_load_missing_file_returns_default_without_warning(temp_campaign_dir, caplog):
    """When save file does not exist, return a default CampaignSaveState without logging warnings."""
    manager = CampaignSaveManager(data_dir=temp_campaign_dir)
    with caplog.at_level(logging.WARNING):
        loaded = manager.load_campaign()

    assert loaded.campaign_active is True
    assert loaded.loyalty == 70.0
    assert loaded.current_act == 1
    assert loaded.current_sortie == 1
    assert loaded.total_casualties == 0
    assert loaded.choices_made == []
    assert len(caplog.records) == 0


def test_load_corrupted_or_truncated_json_recovers_with_warning(temp_campaign_dir, caplog):
    """When save file contains corrupted, empty, truncated or non-dict JSON, log warning and return default."""
    manager = CampaignSaveManager(data_dir=temp_campaign_dir)
    save_path = manager.get_save_path()
    save_path.parent.mkdir(parents=True, exist_ok=True)

    # Test invalid JSON syntax
    save_path.write_text("{corrupt: json content [[", encoding="utf-8")
    caplog.clear()
    with caplog.at_level(logging.WARNING):
        loaded = manager.load_campaign()
    assert loaded.campaign_active is True
    assert loaded.loyalty == 70.0
    assert loaded.current_act == 1
    assert loaded.current_sortie == 1
    assert any("Failed to load campaign save" in r.message for r in caplog.records)

    # Test empty file
    save_path.write_text("", encoding="utf-8")
    caplog.clear()
    with caplog.at_level(logging.WARNING):
        loaded_empty = manager.load_campaign()
    assert loaded_empty.loyalty == 70.0
    assert any("Failed to load campaign save" in r.message for r in caplog.records)

    # Test truncated JSON
    save_path.write_text('{"loyalty": 50.0', encoding="utf-8")
    caplog.clear()
    with caplog.at_level(logging.WARNING):
        loaded_trunc = manager.load_campaign()
    assert loaded_trunc.loyalty == 70.0
    assert any("Failed to load campaign save" in r.message for r in caplog.records)

    # Test valid JSON but non-dict root (e.g. array)
    save_path.write_text("[]", encoding="utf-8")
    caplog.clear()
    with caplog.at_level(logging.WARNING):
        loaded_list = manager.load_campaign()
    assert loaded_list.loyalty == 70.0
    assert any("Invalid campaign save root type" in r.message for r in caplog.records)


def test_load_partial_and_malformed_fields_fallback_gracefully(temp_campaign_dir):
    """Ensure partial JSON and malformed field types fall back cleanly to defaults without crashes."""
    manager = CampaignSaveManager(data_dir=temp_campaign_dir)
    save_path = manager.get_save_path()
    save_path.parent.mkdir(parents=True, exist_ok=True)

    # Partial keys: only loyalty specified
    save_path.write_text('{"loyalty": 55.0}', encoding="utf-8")
    loaded = manager.load_campaign()
    assert loaded.loyalty == pytest.approx(55.0)
    assert loaded.version == 1
    assert loaded.campaign_active is True
    assert loaded.current_act == 1
    assert loaded.current_sortie == 1
    assert loaded.total_casualties == 0
    assert loaded.choices_made == []
    assert loaded.extra == {}

    # Malformed field types
    malformed_json = (
        '{"version": "invalid", "campaign_active": null, "loyalty": true, '
        '"current_act": -5, "current_sortie": "abc", "total_casualties": -10, '
        '"choices_made": [123, null, {"node": "ok"}], "extra": "not_a_dict"}'
    )
    save_path.write_text(malformed_json, encoding="utf-8")
    loaded_malformed = manager.load_campaign()
    assert loaded_malformed.version == 1
    assert loaded_malformed.campaign_active is True
    assert loaded_malformed.loyalty == 70.0
    assert loaded_malformed.current_act == 1
    assert loaded_malformed.current_sortie == 1
    assert loaded_malformed.total_casualties == 0
    assert loaded_malformed.choices_made == [{"node": "ok"}]
    assert loaded_malformed.extra == {}

    # Test NaN and infinite loyalty in dict
    nan_state = CampaignSaveState.from_dict({"loyalty": float("nan")})
    assert nan_state.loyalty == 70.0

    pos_inf_state = CampaignSaveState.from_dict({"loyalty": float("inf")})
    assert pos_inf_state.loyalty == 100.0

    neg_inf_state = CampaignSaveState.from_dict({"loyalty": float("-inf")})
    assert neg_inf_state.loyalty == 0.0

    # Test OverflowError protection on integer fields
    overflow_state = CampaignSaveState.from_dict(
        {
            "version": float("inf"),
            "current_act": float("inf"),
            "current_sortie": float("-inf"),
            "total_casualties": 1e1000,
        }
    )
    assert overflow_state.version == 1
    assert overflow_state.current_act == 1
    assert overflow_state.current_sortie == 1
    assert overflow_state.total_casualties == 0


def test_loyalty_clamping_on_load(temp_campaign_dir):
    """Ensure loyalty out-of-bounds in JSON is clamped to [0.0, 100.0]."""
    manager = CampaignSaveManager(data_dir=temp_campaign_dir)
    save_path = manager.get_save_path()
    save_path.parent.mkdir(parents=True, exist_ok=True)
    save_path.write_text('{"loyalty": 150.0, "current_act": 1}', encoding="utf-8")

    loaded = manager.load_campaign()
    assert loaded.loyalty == 100.0

    save_path.write_text('{"loyalty": -25.0, "current_act": 1}', encoding="utf-8")
    loaded2 = manager.load_campaign()
    assert loaded2.loyalty == 0.0


def test_atomic_write_leaves_no_tmp_and_preserves_existing_on_failure(
    temp_campaign_dir, monkeypatch
):
    """Verify atomic write cleans up .tmp on failure and preserves preexisting valid save."""
    manager = CampaignSaveManager(data_dir=temp_campaign_dir)
    save_path = manager.get_save_path()
    tmp_path = save_path.with_suffix(".tmp")

    # Save a valid state
    initial_state = CampaignSaveState(loyalty=82.0, current_sortie=2)
    assert manager.save_campaign(initial_state) is True
    assert save_path.exists()
    assert not tmp_path.exists()

    # Simulate atomic rename failure
    def fake_replace(src, dst):
        raise OSError("Simulated disk replacement error")

    monkeypatch.setattr(os, "replace", fake_replace)

    # Attempt save that fails during atomic replace
    failed_state = CampaignSaveState(loyalty=10.0, current_sortie=5)
    success = manager.save_campaign(failed_state)
    assert success is False

    # Ensure no leftover temporary file exists
    assert not tmp_path.exists()

    # Ensure preexisting save remains intact with original loyalty
    loaded = manager.load_campaign()
    assert loaded.loyalty == pytest.approx(82.0)
    assert loaded.current_sortie == 2


def test_save_does_not_corrupt_highscore_or_audio_settings(temp_campaign_dir):
    """Verify saving campaign state never touches highscore.txt or audio_settings.json."""
    highscore_path = temp_campaign_dir / "highscore.txt"
    audio_path = temp_campaign_dir / "audio_settings.json"

    highscore_path.write_text("99950\n", encoding="utf-8")
    audio_path.write_text('{"master_volume": 0.8}\n', encoding="utf-8")

    manager = CampaignSaveManager(data_dir=temp_campaign_dir)
    manager.save_campaign(CampaignSaveState(loyalty=45.0, current_sortie=3))
    manager.load_campaign()
    manager.reset_campaign()

    assert highscore_path.read_text(encoding="utf-8") == "99950\n"
    assert audio_path.read_text(encoding="utf-8") == '{"master_volume": 0.8}\n'


def test_story_manager_persistence_and_advance_sortie(temp_campaign_dir):
    """Verify StoryManager persistence sync and advance_sortie functionality."""
    manager = CampaignSaveManager(data_dir=temp_campaign_dir)
    story1 = StoryManager(save_manager=manager)

    assert story1.current_act == 1
    assert story1.current_sortie == 1

    # Advance sortie by 1
    assert story1.advance_sortie() is True
    assert story1.current_act == 1
    assert story1.current_sortie == 2

    # Advance to specific act and sortie coordinates
    assert story1.advance_sortie(act=2, sortie=4) is True
    assert story1.current_act == 2
    assert story1.current_sortie == 4

    # New StoryManager with same save_manager reloads advanced progress
    story2 = StoryManager(save_manager=manager)
    assert story2.current_act == 2
    assert story2.current_sortie == 4


def test_reset_campaign_overwrites_with_default(temp_campaign_dir):
    """Verify reset_campaign resets state to initial baseline and saves to disk."""
    manager = CampaignSaveManager(data_dir=temp_campaign_dir)
    manager.save_campaign(CampaignSaveState(loyalty=20.0, current_sortie=4))

    reset_state = manager.reset_campaign()
    assert reset_state.loyalty == 70.0
    assert reset_state.current_sortie == 1

    loaded = manager.load_campaign()
    assert loaded.loyalty == 70.0
    assert loaded.current_sortie == 1


def test_path_traversal_defense_in_get_save_path(temp_campaign_dir):
    """Verify that filename path traversal attempts are safely restricted to basename."""
    manager = CampaignSaveManager(filename="../../evil.json", data_dir=temp_campaign_dir)
    save_path = manager.get_save_path()
    assert save_path.parent.resolve() == temp_campaign_dir.resolve()
    assert save_path.name == "evil.json"


def test_story_manager_preserves_campaign_active_and_extra(temp_campaign_dir):
    """Verify StoryManager preserves campaign_active, extra metadata, and supports reset_campaign."""
    manager = CampaignSaveManager(data_dir=temp_campaign_dir)
    # Write custom state with extra metadata and campaign_active=False
    custom_state = CampaignSaveState(
        campaign_active=False,
        loyalty=62.0,
        extra={"mod_tag": "custom_v1", "difficulty": "hard"},
    )
    manager.save_campaign(custom_state)

    story = StoryManager(save_manager=manager)
    assert story.campaign_active is False
    assert story.extra == {"mod_tag": "custom_v1", "difficulty": "hard"}
    assert story.loyalty == pytest.approx(62.0)

    # Modify and save through StoryManager
    story.extra["checkpoint"] = "alpha"
    assert story.save_campaign_state() is True

    # Reload in fresh instance
    story2 = StoryManager(save_manager=manager)
    assert story2.campaign_active is False
    assert story2.extra == {
        "mod_tag": "custom_v1",
        "difficulty": "hard",
        "checkpoint": "alpha",
    }

    # Reset via StoryManager convenience method
    reset_state = story2.reset_campaign()
    assert reset_state.campaign_active is True
    assert reset_state.loyalty == 70.0
    assert story2.campaign_active is True
    assert story2.extra == {}
    assert story2.loyalty == 70.0
    assert story2.active_dialogue is None
    assert story2.time_dilation == 1.0


def test_campaign_save_state_from_dict_clamps_act_and_sortie_upper_bounds():
    """Ensure CampaignSaveState.from_dict clamps current_act and current_sortie to upper bounds."""
    state = CampaignSaveState.from_dict({"current_act": 25, "current_sortie": 999})
    assert state.current_act == MAX_CAMPAIGN_ACT
    assert state.current_sortie == MAX_CAMPAIGN_SORTIE

    # String-encoded integers exceeding upper bounds
    state_str = CampaignSaveState.from_dict({"current_act": "50", "current_sortie": "250"})
    assert state_str.current_act == MAX_CAMPAIGN_ACT
    assert state_str.current_sortie == MAX_CAMPAIGN_SORTIE

    # Exact boundary values remain untouched
    state_exact = CampaignSaveState.from_dict(
        {"current_act": MAX_CAMPAIGN_ACT, "current_sortie": MAX_CAMPAIGN_SORTIE}
    )
    assert state_exact.current_act == MAX_CAMPAIGN_ACT
    assert state_exact.current_sortie == MAX_CAMPAIGN_SORTIE


def test_campaign_save_state_act_and_sortie_type_defenses():
    """Ensure CampaignSaveState.from_dict falls back cleanly to 1 on booleans, None, and invalid types."""
    # Boolean values should not be treated as int 1 or 0
    state_bool = CampaignSaveState.from_dict({"current_act": True, "current_sortie": False})
    assert state_bool.current_act == 1
    assert state_bool.current_sortie == 1

    # None / null values
    state_none = CampaignSaveState.from_dict({"current_act": None, "current_sortie": None})
    assert state_none.current_act == 1
    assert state_none.current_sortie == 1

    # Malformed strings and non-numeric objects
    state_invalid = CampaignSaveState.from_dict({"current_act": "invalid", "current_sortie": []})
    assert state_invalid.current_act == 1
    assert state_invalid.current_sortie == 1

    # NaN floating point values
    state_nan = CampaignSaveState.from_dict({"current_act": float("nan"), "current_sortie": float("nan")})
    assert state_nan.current_act == 1
    assert state_nan.current_sortie == 1


