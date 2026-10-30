"""campaign_save.py - Persistent storage for Eagle-1 narrative campaign.

Manages serialization, deserialization, and atomic disk persistence
for campaign progress, loyalty metrics, and decision history.
"""

from dataclasses import asdict, dataclass, field
import json
import logging
import math
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from eagle1.paths import get_user_data_dir

logger = logging.getLogger(__name__)

CAMPAIGN_SAVE_VERSION: int = 1
CAMPAIGN_SAVE_FILENAME: str = "campaign_save.json"
DEFAULT_CAMPAIGN_FILE: str = CAMPAIGN_SAVE_FILENAME

MAX_CAMPAIGN_ACT: int = 10
MAX_CAMPAIGN_SORTIE: int = 100


@dataclass
class CampaignSaveState:
    """Represents persistent narrative state and choices for the campaign."""

    version: int = CAMPAIGN_SAVE_VERSION
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

        raw_version = data.get("version", CAMPAIGN_SAVE_VERSION)
        if isinstance(raw_version, bool) or raw_version is None:
            version = CAMPAIGN_SAVE_VERSION
        else:
            try:
                version = max(1, int(raw_version))
            except (ValueError, TypeError, OverflowError):
                version = CAMPAIGN_SAVE_VERSION

        raw_active = data.get("campaign_active", True)
        campaign_active = raw_active if isinstance(raw_active, bool) else True

        raw_loyalty_val = data.get("loyalty", 70.0)
        if isinstance(raw_loyalty_val, bool) or raw_loyalty_val is None:
            clamped_loyalty = 70.0
        else:
            try:
                raw_loyalty = float(raw_loyalty_val)
                if math.isnan(raw_loyalty):
                    clamped_loyalty = 70.0
                else:
                    clamped_loyalty = max(0.0, min(100.0, raw_loyalty))
            except (ValueError, TypeError):
                clamped_loyalty = 70.0

        raw_act = data.get("current_act", 1)
        if isinstance(raw_act, bool) or raw_act is None:
            current_act = 1
        else:
            try:
                current_act = max(1, min(MAX_CAMPAIGN_ACT, int(raw_act)))
            except (ValueError, TypeError, OverflowError):
                current_act = 1

        raw_sortie = data.get("current_sortie", 1)
        if isinstance(raw_sortie, bool) or raw_sortie is None:
            current_sortie = 1
        else:
            try:
                current_sortie = max(1, min(MAX_CAMPAIGN_SORTIE, int(raw_sortie)))
            except (ValueError, TypeError, OverflowError):
                current_sortie = 1

        raw_casualties = data.get("total_casualties", 0)
        if isinstance(raw_casualties, bool) or raw_casualties is None:
            total_casualties = 0
        else:
            try:
                total_casualties = max(0, int(raw_casualties))
            except (ValueError, TypeError, OverflowError):
                total_casualties = 0

        raw_choices = data.get("choices_made", [])
        choices_made = (
            [dict(item) for item in raw_choices if isinstance(item, dict)]
            if isinstance(raw_choices, list)
            else []
        )

        raw_extra = data.get("extra", {})
        extra = dict(raw_extra) if isinstance(raw_extra, dict) else {}

        return cls(
            version=version,
            campaign_active=campaign_active,
            current_act=current_act,
            current_sortie=current_sortie,
            loyalty=clamped_loyalty,
            total_casualties=total_casualties,
            choices_made=choices_made,
            extra=extra,
        )


class CampaignSaveManager:
    """Handles thread-safe, atomic disk persistence for CampaignSaveState."""

    def __init__(self, filename: str = CAMPAIGN_SAVE_FILENAME, data_dir: Optional[Path] = None):
        self.filename = filename
        self._custom_data_dir = data_dir

    def get_save_path(self) -> Path:
        """Return the absolute path to the campaign save file."""
        base_dir = self._custom_data_dir if self._custom_data_dir else get_user_data_dir()
        safe_filename = Path(self.filename).name
        return base_dir / safe_filename

    def load_campaign(self) -> CampaignSaveState:
        """Load state from disk, or return default state on missing file or corruption."""
        path = self.get_save_path()
        if not path.is_file():
            return CampaignSaveState()

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                logger.warning(
                    "Invalid campaign save root type in %s (expected dict, got %s); falling back to default",
                    path,
                    type(data).__name__,
                )
                return CampaignSaveState()
            return CampaignSaveState.from_dict(data)
        except Exception as exc:
            logger.warning(
                "Failed to load campaign save from %s: %s; falling back to default",
                path,
                exc,
            )
            return CampaignSaveState()

    def save_campaign(self, state: CampaignSaveState) -> bool:
        """Atomically persist campaign state to disk using a temporary file."""
        path = self.get_save_path()
        tmp_path: Optional[Path] = None
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp_path = path.with_suffix(".tmp")

            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(state.to_dict(), f, indent=2, ensure_ascii=False)
                f.flush()
                os.fsync(f.fileno())

            os.replace(tmp_path, path)
            return True
        except Exception as exc:
            logger.error("Failed to save campaign state to %s: %s", path, exc)
            if tmp_path is not None and tmp_path.exists():
                try:
                    tmp_path.unlink()
                except OSError:
                    pass
            return False

    def reset_campaign(self) -> CampaignSaveState:
        """Reset campaign state to baseline defaults and persist to disk."""
        default_state = CampaignSaveState()
        self.save_campaign(default_state)
        return default_state

