"""mission_controller.py - Campaign Sortie Progression and Mission Lifecycle Controller.

Defines the CampaignSortieConfig dataclass, the canonical CAMPAIGN_SORTIE_REGISTRY
for Act I and Act II (Sorties 1 to 4), and the MissionController class managing
in-flight objectives, mission state transitions, and story progression.
"""

from dataclasses import dataclass
import logging
import math
from typing import Any, Dict, List, Optional, Tuple

from eagle1.story.story_manager import StoryManager

logger = logging.getLogger(__name__)

MIN_SORTIE_NUM: int = 1
MAX_SORTIE_NUM: int = 4

VALID_CAMPAIGN_MISSION_MODES: Tuple[str, ...] = (
    "air_superiority",
    "base_defense",
    "outpost_demolition",
    "strider_raid",
)


@dataclass(frozen=True)
class CampaignSortieConfig:
    """Immutable configuration and narrative metadata for a campaign sortie."""

    sortie_num: int
    act: int
    sortie_id: str
    title: str
    operation_name: str
    mission_mode: str
    threat_level: str
    target_waves: int
    required_fabricators: int
    has_boss_strider: bool
    initial_objective: str
    extraction_objective: str
    briefing_node_id: str
    inflight_node_ids: Tuple[str, ...]
    debrief_node_id: str

    def to_briefing_dict(self) -> Dict[str, str]:
        """Return Hangar Deck compatible briefing metadata dictionary."""
        return {
            "mission_id": self.mission_mode,
            "title": self.title,
            "operation": self.operation_name,
            "objective": self.initial_objective,
            "threat": self.threat_level,
        }


# Canonical registry for campaign Sorties 1 through 4 across Act I & II.
# Note: Act I in-flight nodes (sortie_1_inflight, sortie_2_inflight) are defined in dialogue_db (#69);
# Act II in-flight nodes (sortie_3_500kg_crisis, sortie_4_strider_crisis) are defined in dialogue_db (#70).
CAMPAIGN_SORTIE_REGISTRY: Dict[int, CampaignSortieConfig] = {
    1: CampaignSortieConfig(
        sortie_num=1,
        act=1,
        sortie_id="sortie_1_baptism_of_fire",
        title="SORTIE 1 // BAPTISM OF FIRE",
        operation_name="AIR SUPERIORITY",
        mission_mode="air_superiority",
        threat_level="MODERATE // AUTOMATON INTERCEPTOR WING",
        target_waves=3,
        required_fabricators=0,
        has_boss_strider=False,
        initial_objective="Establish orbital air superiority over Vandalon Prime and intercept Automaton fighter squadrons.",
        extraction_objective="Clear landing zone for Pelican-1 extraction at Grid Alpha.",
        briefing_node_id="sortie_1_briefing",
        inflight_node_ids=("sortie_1_inflight",),
        debrief_node_id="sortie_1_hangar_debrief",
    ),
    2: CampaignSortieConfig(
        sortie_num=2,
        act=1,
        sortie_id="sortie_2_the_red_perimeter",
        title="SORTIE 2 // THE RED PERIMETER",
        operation_name="ORBITAL BASE DEFENSE",
        mission_mode="base_defense",
        threat_level="HIGH // ARMORED GROUND ASSAULT & DROPSHIPS",
        target_waves=4,
        required_fabricators=0,
        has_boss_strider=False,
        initial_objective="Provide Close Air Support to Viper Squad defending the forward orbital relay outpost.",
        extraction_objective="Hold the relay perimeter until Pelican-1 completes squad extraction.",
        briefing_node_id="sortie_2_briefing",
        inflight_node_ids=("sortie_2_inflight",),
        debrief_node_id="sortie_2_hangar_debrief",
    ),
    3: CampaignSortieConfig(
        sortie_num=3,
        act=2,
        sortie_id="sortie_3_the_fabricator_furnace",
        title="SORTIE 3 // THE FABRICATOR FURNACE",
        operation_name="OUTPOST DEMOLITION",
        mission_mode="outpost_demolition",
        threat_level="SEVERE // HEAVY AA & HULL-CUTTER BATTERIES",
        target_waves=4,
        required_fabricators=3,
        has_boss_strider=False,
        initial_objective="Deliver precision 500kg ordnance to obliterate fortified Automaton fabricator complexes.",
        extraction_objective="Eliminate remaining outpost defenses and extract Viper Squad from Grid Charlie-4.",
        briefing_node_id="sortie_3_briefing",
        inflight_node_ids=("sortie_3_500kg_crisis",),
        debrief_node_id="sortie_3_hangar_debrief",
    ),
    4: CampaignSortieConfig(
        sortie_num=4,
        act=2,
        sortie_id="sortie_4_the_iron_colossus",
        title="SORTIE 4 // THE IRON COLOSSUS",
        operation_name="FACTORY STRIDER RAID",
        mission_mode="strider_raid",
        threat_level="EXTREME // CLASS-IV MOBILE FORTRESS",
        target_waves=5,
        required_fabricators=2,
        has_boss_strider=True,
        initial_objective="Neutralize the Automaton Factory Strider command fortress threatening Viper Squad extraction.",
        extraction_objective="Destroy the Factory Strider and secure emergency Pelican-1 extraction.",
        briefing_node_id="sortie_4_briefing",
        inflight_node_ids=("sortie_4_strider_crisis",),
        debrief_node_id="sortie_4_hangar_debrief",
    ),
}


def get_sortie_config(sortie_num: Any) -> Optional[CampaignSortieConfig]:
    """Retrieve a campaign sortie configuration by its integer sortie number."""
    if isinstance(sortie_num, bool):
        return None

    if isinstance(sortie_num, int):
        return CAMPAIGN_SORTIE_REGISTRY.get(sortie_num)

    if isinstance(sortie_num, float):
        if math.isnan(sortie_num) or math.isinf(sortie_num):
            return None
        if sortie_num.is_integer():
            try:
                return CAMPAIGN_SORTIE_REGISTRY.get(int(sortie_num))
            except (ValueError, OverflowError):
                return None
        return None

    return None


def validate_sortie_registry(
    registry: Optional[Dict[int, CampaignSortieConfig]] = None,
) -> bool:
    """Validate that every campaign sortie configuration strictly conforms to specifications.

    Raises:
        ValueError: If the registry is empty, malformed, or violates sortie constraints.
    """
    target_reg = CAMPAIGN_SORTIE_REGISTRY if registry is None else registry
    if not isinstance(target_reg, dict) or len(target_reg) == 0:
        raise ValueError("Sortie registry must be a non-empty dictionary.")

    expected_sorties = set(range(MIN_SORTIE_NUM, MAX_SORTIE_NUM + 1))
    if set(target_reg.keys()) != expected_sorties or any(isinstance(k, bool) for k in target_reg.keys()):
        raise ValueError(
            f"Sortie registry missing required sorties. Must contain exact contiguous integer keys {expected_sorties}, got {set(target_reg.keys())}."
        )

    for key, cfg in target_reg.items():
        if not isinstance(cfg, CampaignSortieConfig):
            raise ValueError(f"Registry entry for key {key!r} is not a CampaignSortieConfig.")

        if key != cfg.sortie_num:
            raise ValueError(f"Registry key {key} does not match sortie_num {cfg.sortie_num}.")

        if cfg.sortie_num not in range(MIN_SORTIE_NUM, MAX_SORTIE_NUM + 1):
            raise ValueError(f"sortie_num {cfg.sortie_num} out of bounds [{MIN_SORTIE_NUM}, {MAX_SORTIE_NUM}].")

        # Act boundaries: Sortie 1 & 2 belong to Act 1; Sortie 3 & 4 belong to Act 2
        if cfg.sortie_num in (1, 2) and cfg.act != 1:
            raise ValueError(f"Sortie {cfg.sortie_num} must be Act 1, got Act {cfg.act}.")
        if cfg.sortie_num in (3, 4) and cfg.act != 2:
            raise ValueError(f"Sortie {cfg.sortie_num} must be Act 2, got Act {cfg.act}.")

        if cfg.mission_mode not in VALID_CAMPAIGN_MISSION_MODES:
            raise ValueError(f"Sortie {cfg.sortie_num} has invalid mission_mode '{cfg.mission_mode}'.")

        str_fields = (
            ("sortie_id", cfg.sortie_id),
            ("title", cfg.title),
            ("operation_name", cfg.operation_name),
            ("threat_level", cfg.threat_level),
            ("initial_objective", cfg.initial_objective),
            ("extraction_objective", cfg.extraction_objective),
            ("briefing_node_id", cfg.briefing_node_id),
            ("debrief_node_id", cfg.debrief_node_id),
        )
        for field_name, field_val in str_fields:
            if not isinstance(field_val, str) or not field_val.strip():
                raise ValueError(f"Sortie {cfg.sortie_num} has empty or non-string '{field_name}'.")

        if isinstance(cfg.target_waves, bool) or not isinstance(cfg.target_waves, int) or cfg.target_waves <= 0:
            raise ValueError(f"Sortie {cfg.sortie_num} target_waves must be > 0.")

        if (
            isinstance(cfg.required_fabricators, bool)
            or not isinstance(cfg.required_fabricators, int)
            or cfg.required_fabricators < 0
        ):
            raise ValueError(f"Sortie {cfg.sortie_num} required_fabricators must be >= 0.")

        if not isinstance(cfg.has_boss_strider, bool):
            raise ValueError(f"Sortie {cfg.sortie_num} has_boss_strider must be a bool.")

        if not isinstance(cfg.inflight_node_ids, tuple) or len(cfg.inflight_node_ids) == 0:
            raise ValueError(f"Sortie {cfg.sortie_num} inflight_node_ids must be a non-empty tuple.")

        for node_id in cfg.inflight_node_ids:
            if not isinstance(node_id, str) or not node_id.strip():
                raise ValueError(f"Sortie {cfg.sortie_num} has invalid inflight_node_id {node_id!r}.")

    return True


class MissionController:
    """Orchestrates campaign sortie lifecycle, objective tracking, and progression."""

    def __init__(self, story_manager: StoryManager) -> None:
        if story_manager is None or isinstance(story_manager, bool) or not isinstance(story_manager, StoryManager):
            raise TypeError("story_manager must be a valid StoryManager instance")

        self.story_manager = story_manager
        self.active_sortie_num: int = self._sanitize_sortie_num(getattr(story_manager, "current_sortie", 1))
        self.is_sortie_active: bool = False
        self.completed_sorties: List[int] = []
        self.sortie_metrics: Dict[str, Any] = {}
        self.current_objective: str = ""

        self.sync_from_story_manager()

    def sync_from_story_manager(self) -> None:
        """Synchronize cached controller state with StoryManager."""
        self.active_sortie_num = self._sanitize_sortie_num(getattr(self.story_manager, "current_sortie", 1))
        self.is_sortie_active = False

        raw_extra = getattr(self.story_manager, "extra", {})
        raw_completed = raw_extra.get("completed_sorties", []) if isinstance(raw_extra, dict) else []
        self.completed_sorties = (
            sorted(
                {
                    int(x)
                    for x in raw_completed
                    if not isinstance(x, bool) and isinstance(x, int) and MIN_SORTIE_NUM <= x <= MAX_SORTIE_NUM
                }
            )
            if isinstance(raw_completed, list)
            else []
        )
        self.current_objective = self.get_current_sortie_config().initial_objective

    def reset(self) -> None:
        """Reset active sortie state and re-sync from StoryManager."""
        self.sortie_metrics.clear()
        self.sync_from_story_manager()

    def _sanitize_sortie_num(self, raw_sortie: Any, default: int = 1) -> int:
        """Sanitize raw sortie numbers with fallback and clamping."""
        try:
            safe_default = max(MIN_SORTIE_NUM, min(MAX_SORTIE_NUM, int(default)))
        except (ValueError, TypeError, OverflowError):
            safe_default = MIN_SORTIE_NUM

        if isinstance(raw_sortie, bool):
            return safe_default

        if isinstance(raw_sortie, int):
            return max(MIN_SORTIE_NUM, min(MAX_SORTIE_NUM, raw_sortie))

        if isinstance(raw_sortie, float):
            if math.isnan(raw_sortie) or math.isinf(raw_sortie):
                return safe_default
            try:
                return max(MIN_SORTIE_NUM, min(MAX_SORTIE_NUM, int(raw_sortie)))
            except (ValueError, TypeError, OverflowError):
                return safe_default

        return safe_default

    def get_sortie_config(self, sortie_num: Any) -> Optional[CampaignSortieConfig]:
        """Retrieve a sortie configuration by number."""
        return get_sortie_config(sortie_num)

    def get_current_sortie_config(self) -> CampaignSortieConfig:
        """Return the configuration for the active or currently queued sortie."""
        s_num = self._sanitize_sortie_num(getattr(self.story_manager, "current_sortie", 1))
        return CAMPAIGN_SORTIE_REGISTRY[s_num]

    def get_active_objective_text(self) -> str:
        """Return the current dynamic mission objective text for HUD display."""
        if isinstance(self.current_objective, str) and self.current_objective.strip():
            return self.current_objective
        return self.get_current_sortie_config().initial_objective

    def set_active_objective_text(self, text: str) -> None:
        """Update the active in-flight HUD objective text with single-line whitespace normalization."""
        if isinstance(text, bool) or not isinstance(text, str):
            return
        cleaned = " ".join(text.split()).strip()
        if cleaned:
            self.current_objective = cleaned[:250]

    def advance_to_extraction_objective(self) -> str:
        """Switch objective text to the sortie's Pelican-1 extraction prompt."""
        cfg = CAMPAIGN_SORTIE_REGISTRY.get(self.active_sortie_num, self.get_current_sortie_config())
        self.current_objective = cfg.extraction_objective
        return self.current_objective

    def start_sortie(self, sortie_num: Optional[int] = None) -> CampaignSortieConfig:
        """Initialize and activate a sortie deployment."""
        current_manager_sortie = self._sanitize_sortie_num(getattr(self.story_manager, "current_sortie", 1))
        if sortie_num is None:
            target_num = current_manager_sortie
        else:
            target_num = self._sanitize_sortie_num(sortie_num, default=current_manager_sortie)

        cfg = CAMPAIGN_SORTIE_REGISTRY[target_num]
        self.active_sortie_num = cfg.sortie_num
        self.is_sortie_active = True
        self.current_objective = cfg.initial_objective
        self.sortie_metrics = {
            "sortie_num": cfg.sortie_num,
            "act": cfg.act,
            "mission_mode": cfg.mission_mode,
            "casualties_count": 0,
            "squad_wiped": False,
            "hull_ratio": 1.0,
        }
        self.story_manager.advance_sortie(act=cfg.act, sortie=cfg.sortie_num)
        return cfg

    def abort_sortie(self) -> None:
        """Abort active sortie deployment and restore initial objective without progressing."""
        self.is_sortie_active = False
        self.current_objective = self.get_current_sortie_config().initial_objective

    def complete_current_sortie(
        self,
        casualties_count: int = 0,
        squad_wiped: bool = False,
        hull_ratio: float = 1.0,
    ) -> Dict[str, Any]:
        """Record sortie completion, advance campaign progression, and evaluate ending branches."""
        if not self.is_sortie_active:
            logger.warning("complete_current_sortie called when no sortie is active; ignoring.")
            return {}

        # Sanitize casualties_count (reject bool, check int first, protect against OverflowError)
        if isinstance(casualties_count, bool) or not isinstance(casualties_count, (int, float)):
            c_count = 0
        elif isinstance(casualties_count, int):
            c_count = max(0, casualties_count)
        elif math.isnan(casualties_count) or math.isinf(casualties_count):
            c_count = 0
        else:
            try:
                c_count = max(0, int(casualties_count))
            except (ValueError, TypeError, OverflowError):
                c_count = 0

        # Sanitize squad_wiped
        is_wiped = (squad_wiped if isinstance(squad_wiped, bool) else False) or (c_count >= 4)

        # Sanitize hull_ratio (reject bool, default to 1.0 on NaN/inf/invalid)
        if isinstance(hull_ratio, bool) or not isinstance(hull_ratio, (int, float)):
            h_ratio = 1.0
        elif isinstance(hull_ratio, float) and (math.isnan(hull_ratio) or math.isinf(hull_ratio)):
            h_ratio = 1.0
        else:
            try:
                h_ratio = max(0.0, min(1.0, float(hull_ratio)))
            except (ValueError, TypeError, OverflowError):
                h_ratio = 1.0

        completed_num = self.active_sortie_num
        completed_cfg = CAMPAIGN_SORTIE_REGISTRY[completed_num]
        self.is_sortie_active = False

        if completed_num not in self.completed_sorties:
            self.completed_sorties.append(completed_num)
            self.completed_sorties.sort()

        if not isinstance(getattr(self.story_manager, "extra", None), dict):
            self.story_manager.extra = {}
        self.story_manager.extra["completed_sorties"] = list(self.completed_sorties)

        if completed_num < MAX_SORTIE_NUM:
            next_sortie = completed_num + 1
            next_cfg = CAMPAIGN_SORTIE_REGISTRY[next_sortie]
            next_act = next_cfg.act
            campaign_completed = False
            ending_branch = None
            self.active_sortie_num = next_sortie
            self.current_objective = next_cfg.initial_objective
        else:
            next_sortie = MAX_SORTIE_NUM
            next_act = 3
            campaign_completed = True
            ending_branch = self.story_manager.get_ending_branch()
            self.story_manager.extra["act2_completed"] = True
            self.story_manager.extra["ending_branch"] = ending_branch
            self.active_sortie_num = MAX_SORTIE_NUM
            self.current_objective = "Campaign Complete // Awaiting Act III Directive"

        self.story_manager.advance_sortie(act=next_act, sortie=next_sortie)

        result = {
            "completed_sortie": completed_num,
            "completed_act": completed_cfg.act,
            "mission_mode": completed_cfg.mission_mode,
            "next_sortie": next_sortie,
            "next_act": next_act,
            "campaign_completed": campaign_completed,
            "ending_branch": ending_branch,
            "casualties_count": c_count,
            "squad_wiped": is_wiped,
            "hull_ratio": h_ratio,
        }
        self.sortie_metrics = dict(result)
        return result

    def is_campaign_completed(self) -> bool:
        """Return whether Act I and Act II sorties (1-4) have all been completed."""
        return (
            MAX_SORTIE_NUM in self.completed_sorties
            or bool(getattr(self.story_manager, "extra", {}).get("act2_completed", False))
            or getattr(self.story_manager, "current_act", 1) >= 3
        )
