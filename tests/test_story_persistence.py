"""Tests for Campaign Story Save Data Model and Persistence Layer."""

from pathlib import Path
import tempfile
import pytest

from eagle1.story.campaign_save import CampaignSaveManager, CampaignSaveState


@pytest.fixture
def temp_campaign_dir():
    """Create an isolated temporary directory for campaign saves."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


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


def test_load_missing_file_returns_default(temp_campaign_dir):
    """When save file does not exist, return a pristine default CampaignSaveState."""
    manager = CampaignSaveManager(data_dir=temp_campaign_dir)
    loaded = manager.load_campaign()

    assert loaded.campaign_active is True
    assert loaded.loyalty == 70.0
    assert loaded.current_act == 1
    assert loaded.current_sortie == 1
    assert loaded.total_casualties == 0
    assert loaded.choices_made == []


def test_load_corrupted_json_recovers_gracefully(temp_campaign_dir):
    """When save file contains invalid or corrupted JSON, fall back to default state."""
    manager = CampaignSaveManager(data_dir=temp_campaign_dir)
    save_path = manager.get_save_path()
    save_path.parent.mkdir(parents=True, exist_ok=True)
    save_path.write_text("{corrupt: json content [[", encoding="utf-8")

    loaded = manager.load_campaign()
    assert loaded.campaign_active is True
    assert loaded.loyalty == 70.0
    assert loaded.current_act == 1
    assert loaded.current_sortie == 1


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

