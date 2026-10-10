"""player_profile.py - Player Enlistment Profile & Story Campaign Persistence.

Manages persistent pilot records, citizenship grade, contract acceptance,
and campaign story progression for Eagle-1-64Bit.
"""

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from eagle1.paths import get_user_data_dir

logger = logging.getLogger(__name__)

DEFAULT_PROFILE_FILE = "player_profile.json"


@dataclass
class PlayerProfile:
    """Represents a pilot's service record, enlistment contract status, and story progress."""

    version: int = 1
    username: str = ""
    citizenship_grade: str = "E"
    contract_signed: bool = False
    enlisted_timestamp: str = ""
    academy_completed: bool = False
    active_mission: str = "academy_tutorial"
    missions_cleared: int = 0
    unlocked_stratagems: List[int] = field(default_factory=lambda: [1, 2])
    extra: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_enlisted(self) -> bool:
        """Return True if the pilot has a valid callsign and signed the contract."""
        return bool(self.username and self.username.strip() and self.contract_signed)

    def to_dict(self) -> Dict[str, Any]:
        """Convert the profile into a JSON-serializable dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PlayerProfile":
        """Instantiate a PlayerProfile from a dictionary with robust fallbacks."""
        if not isinstance(data, dict):
            return cls()

        campaign_data = data.get("campaign", {})
        if isinstance(campaign_data, dict):
            academy_completed = campaign_data.get("academy_completed", False)
            active_mission = campaign_data.get("active_mission", "academy_tutorial")
            missions_cleared = campaign_data.get("missions_cleared", 0)
            unlocked_stratagems = campaign_data.get("unlocked_stratagems", [1, 2])
        else:
            academy_completed = data.get("academy_completed", False)
            active_mission = data.get("active_mission", "academy_tutorial")
            missions_cleared = data.get("missions_cleared", 0)
            unlocked_stratagems = data.get("unlocked_stratagems", [1, 2])

        return cls(
            version=int(data.get("version", 1)),
            username=str(data.get("username", "")).strip(),
            citizenship_grade=str(data.get("citizenship_grade", "E")),
            contract_signed=bool(data.get("contract_signed", False)),
            enlisted_timestamp=str(data.get("enlisted_timestamp", "")),
            academy_completed=bool(academy_completed),
            active_mission=str(active_mission),
            missions_cleared=int(missions_cleared),
            unlocked_stratagems=list(unlocked_stratagems),
            extra=dict(data.get("extra", {})),
        )


class PlayerProfileManager:
    """Handles thread-safe, atomic disk persistence for PlayerProfile."""

    def __init__(self, filename: str = DEFAULT_PROFILE_FILE, data_dir: Optional[Path] = None):
        self.filename = filename
        self._custom_data_dir = data_dir

    def get_profile_path(self) -> Path:
        """Return the absolute path to the profile JSON file."""
        base_dir = self._custom_data_dir if self._custom_data_dir else get_user_data_dir()
        return base_dir / self.filename

    def has_active_profile(self) -> bool:
        """Check if an active, enlisted player profile exists on disk.

        Returns False on first launch or if the contract has not been accepted.
        """
        path = self.get_profile_path()
        if not path.is_file():
            return False

        profile = self.load_profile()
        return profile.is_enlisted

    def load_profile(self) -> PlayerProfile:
        """Load and return the player profile from disk, or a default empty profile on failure."""
        path = self.get_profile_path()
        if not path.is_file():
            return PlayerProfile()

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return PlayerProfile.from_dict(data)
        except Exception as exc:
            logger.warning("Failed to load player profile from %s: %s", path, exc)
            return PlayerProfile()

    def save_profile(self, profile: PlayerProfile) -> bool:
        """Save the player profile to disk using atomic rename for corruption resistance."""
        path = self.get_profile_path()
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp_path = path.with_suffix(".tmp")

            payload = {
                "version": profile.version,
                "username": profile.username.strip(),
                "citizenship_grade": profile.citizenship_grade,
                "contract_signed": profile.contract_signed,
                "enlisted_timestamp": profile.enlisted_timestamp,
                "campaign": {
                    "academy_completed": profile.academy_completed,
                    "active_mission": profile.active_mission,
                    "missions_cleared": profile.missions_cleared,
                    "unlocked_stratagems": profile.unlocked_stratagems,
                },
                "extra": profile.extra,
            }

            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2, ensure_ascii=False)

            # Atomic replace
            os.replace(tmp_path, path)
            return True
        except Exception as exc:
            logger.error("Failed to save player profile to %s: %s", path, exc)
            return False

    def create_profile(
        self,
        username: str,
        citizenship_grade: str = "E",
    ) -> PlayerProfile:
        """Create, persist, and return a newly enlisted pilot profile."""
        now_iso = datetime.now(timezone.utc).isoformat()
        profile = PlayerProfile(
            version=1,
            username=username.strip(),
            citizenship_grade=citizenship_grade,
            contract_signed=True,
            enlisted_timestamp=now_iso,
            academy_completed=False,
            active_mission="academy_tutorial",
            missions_cleared=0,
            unlocked_stratagems=[1, 2],
        )
        self.save_profile(profile)
        return profile

    def clear_profile(self) -> bool:
        """Remove the profile file from disk."""
        path = self.get_profile_path()
        try:
            if path.exists():
                path.unlink()
            return True
        except Exception as exc:
            logger.error("Failed to delete player profile at %s: %s", path, exc)
            return False

