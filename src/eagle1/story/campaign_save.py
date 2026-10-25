"""campaign_save.py - Persistent storage for Eagle-1 narrative campaign.

Manages serialization, deserialization, and atomic disk persistence
for campaign progress, loyalty metrics, and decision history.
"""

from dataclasses import asdict, dataclass, field
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from eagle1.paths import get_user_data_dir

logger = logging.getLogger(__name__)

DEFAULT_CAMPAIGN_FILE = "campaign_save.json"


@dataclass
class CampaignSaveState:
    """Represents persistent narrative state and choices for the campaign."""

    version: int = 1
    campaign_active: bool = True
    current_act: int = 1
    current_sortie: int = 1
    loyalty: float = 70.0
    total_casualties: int = 0
    choices_made: List[Dict[str, Any]] = field(default_factory=list)
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert state to a JSON-serializable dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CampaignSaveState":
        """Instantiate CampaignSaveState from a dictionary with robust fallbacks."""
        if not isinstance(data, dict):
            return cls()

        try:
            raw_loyalty = float(data.get("loyalty", 70.0))
            clamped_loyalty = max(0.0, min(100.0, raw_loyalty))
        except (ValueError, TypeError):
            clamped_loyalty = 70.0

        try:
            current_act = max(1, int(data.get("current_act", 1)))
        except (ValueError, TypeError):
            current_act = 1

        try:
            current_sortie = max(1, int(data.get("current_sortie", 1)))
        except (ValueError, TypeError):
            current_sortie = 1

        try:
            total_casualties = max(0, int(data.get("total_casualties", 0)))
        except (ValueError, TypeError):
            total_casualties = 0

        raw_choices = data.get("choices_made", [])
        choices_made = raw_choices if isinstance(raw_choices, list) else []

        raw_extra = data.get("extra", {})
        extra = raw_extra if isinstance(raw_extra, dict) else {}

        return cls(
            version=int(data.get("version", 1)),
            campaign_active=bool(data.get("campaign_active", True)),
            current_act=current_act,
            current_sortie=current_sortie,
            loyalty=clamped_loyalty,
            total_casualties=total_casualties,
            choices_made=choices_made,
            extra=extra,
        )


class CampaignSaveManager:
    """Handles thread-safe, atomic disk persistence for CampaignSaveState."""

    def __init__(self, filename: str = DEFAULT_CAMPAIGN_FILE, data_dir: Optional[Path] = None):
        self.filename = filename
        self._custom_data_dir = data_dir

    def get_save_path(self) -> Path:
        """Return the absolute path to the campaign save file."""
        base_dir = self._custom_data_dir if self._custom_data_dir else get_user_data_dir()
        return base_dir / self.filename

    def load_campaign(self) -> CampaignSaveState:
        """Load state from disk, or return default state on missing file or corruption."""
        path = self.get_save_path()
        if not path.is_file():
            return CampaignSaveState()

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return CampaignSaveState.from_dict(data)
        except Exception as exc:
            logger.warning("Failed to load campaign save from %s: %s; falling back to default", path, exc)
            return CampaignSaveState()

    def save_campaign(self, state: CampaignSaveState) -> bool:
        """Atomically persist campaign state to disk using a temporary file."""
        path = self.get_save_path()
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp_path = path.with_suffix(".tmp")

            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(state.to_dict(), f, indent=2, ensure_ascii=False)

            os.replace(tmp_path, path)
            return True
        except Exception as exc:
            logger.error("Failed to save campaign state to %s: %s", path, exc)
            return False

    def reset_campaign(self) -> CampaignSaveState:
        """Reset campaign state to baseline defaults and persist to disk."""
        default_state = CampaignSaveState()
        self.save_campaign(default_state)
        return default_state

