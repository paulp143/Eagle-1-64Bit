"""Tests for player profile persistence, contract signing, and first-time detection."""

import os
from pathlib import Path
import tempfile
import pytest

from eagle1.data.player_profile import PlayerProfile, PlayerProfileManager


@pytest.fixture
def temp_profile_dir():
    """Create a temporary directory for isolated profile testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        old_env = os.environ.get("EAGLE1_USER_DATA_DIR")
        os.environ["EAGLE1_USER_DATA_DIR"] = tmpdir
        yield Path(tmpdir)
        if old_env is not None:
            os.environ["EAGLE1_USER_DATA_DIR"] = old_env
        else:
            os.environ.pop("EAGLE1_USER_DATA_DIR", None)


def test_no_profile_initially(temp_profile_dir):
    """Verify that when no profile exists, has_active_profile returns False."""
    manager = PlayerProfileManager()
    assert manager.has_active_profile() is False
    profile = manager.load_profile()
    assert profile.username == ""
    assert profile.contract_signed is False
    assert profile.is_enlisted is False


def test_create_and_load_profile(temp_profile_dir):
    """Verify creating an enlistment profile, saving it, and reloading it."""
    manager = PlayerProfileManager()
    profile = manager.create_profile(username="Cadet Vance", citizenship_grade="E")

    assert profile.username == "Cadet Vance"
    assert profile.citizenship_grade == "E"
    assert profile.contract_signed is True
    assert profile.is_enlisted is True
    assert profile.academy_completed is False
    assert profile.active_mission == "academy_tutorial"
    assert manager.has_active_profile() is True

    # Reload from disk
    loaded = manager.load_profile()
    assert loaded.username == "Cadet Vance"
    assert loaded.citizenship_grade == "E"
    assert loaded.contract_signed is True
    assert loaded.is_enlisted is True
    assert loaded.active_mission == "academy_tutorial"


def test_profile_empty_username_is_not_active(temp_profile_dir):
    """A profile with empty or whitespace-only username should not be considered active."""
    manager = PlayerProfileManager()
    profile = PlayerProfile(username="   ", contract_signed=True)
    manager.save_profile(profile)

    assert manager.has_active_profile() is False


def test_profile_unsigned_contract_is_not_active(temp_profile_dir):
    """A profile where contract is not signed should not be considered active."""
    manager = PlayerProfileManager()
    profile = PlayerProfile(username="ValidName", contract_signed=False)
    manager.save_profile(profile)

    assert manager.has_active_profile() is False


def test_corrupt_profile_file_fallback(temp_profile_dir):
    """A corrupted JSON profile file should gracefully return default profile and False."""
    manager = PlayerProfileManager()
    profile_path = manager.get_profile_path()
    profile_path.parent.mkdir(parents=True, exist_ok=True)
    profile_path.write_text("{invalid_json: true", encoding="utf-8")

    assert manager.has_active_profile() is False
    profile = manager.load_profile()
    assert profile.username == ""
    assert profile.contract_signed is False


def test_clear_profile(temp_profile_dir):
    """Clearing a profile deletes the file and reverts has_active_profile to False."""
    manager = PlayerProfileManager()
    manager.create_profile("Cadet Helldiver")
    assert manager.has_active_profile() is True

    manager.clear_profile()
    assert manager.has_active_profile() is False
    assert not manager.get_profile_path().exists()


def test_profile_progress_updates(temp_profile_dir):
    """Updating campaign progress and saving persists across loads."""
    manager = PlayerProfileManager()
    profile = manager.create_profile("Eagle Leader")
    profile.academy_completed = True
    profile.active_mission = "air_superiority"
    profile.missions_cleared = 1
    profile.unlocked_stratagems = [1, 2, 3]
    manager.save_profile(profile)

    reloaded = manager.load_profile()
    assert reloaded.academy_completed is True
    assert reloaded.active_mission == "air_superiority"
    assert reloaded.missions_cleared == 1
    assert reloaded.unlocked_stratagems == [1, 2, 3]

