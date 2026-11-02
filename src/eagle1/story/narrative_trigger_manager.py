"""narrative_trigger_manager.py - In-flight narrative event triggers for campaign sorties.

Evaluates live combat telemetry each frame, fires scripted sortie triggers in a
deterministic priority order, queues radio beats while comms are busy, and keeps
the tactical HUD objective in sync with the narrative.
"""

from dataclasses import dataclass, field
import logging
import math
from typing import Any, Callable, Optional, Tuple

from eagle1.story.dialogue_data import BANTER_QUEUES
from eagle1.story.dialogue_db import get_dialogue_node
from eagle1.story.mission_controller import MAX_SORTIE_NUM, MIN_SORTIE_NUM

logger = logging.getLogger(__name__)

CONDITION_ELAPSED_TIME: str = "elapsed_time"
CONDITION_AERIAL_KILLS: str = "aerial_kills"
CONDITION_WAVE_REACHED: str = "wave_reached"
CONDITION_FABRICATORS_DESTROYED: str = "fabricators_destroyed"
CONDITION_BOSS_HP_BELOW: str = "boss_hp_below"
CONDITION_HELLDIVER_CASUALTIES: str = "helldiver_casualties"
CONDITION_CUSTOM: str = "custom"

VALID_CONDITION_TYPES: Tuple[str, ...] = (
    CONDITION_ELAPSED_TIME,
    CONDITION_AERIAL_KILLS,
    CONDITION_WAVE_REACHED,
    CONDITION_FABRICATORS_DESTROYED,
    CONDITION_BOSS_HP_BELOW,
    CONDITION_HELLDIVER_CASUALTIES,
    CONDITION_CUSTOM,
)


def _sanitize_count(value: Any) -> int:
    """Coerce a counter to a non-negative int; bools, NaN, inf and garbage become 0."""
    if isinstance(value, bool):
        return 0
    if isinstance(value, int):
        return max(0, value)
    if isinstance(value, float):
        if not math.isfinite(value):
            return 0
        return max(0, int(value))
    return 0


def _sanitize_seconds(value: Any) -> float:
    """Coerce elapsed time to a finite, non-negative float; invalid input becomes 0.0."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return 0.0
    numeric = float(value)
    if not math.isfinite(numeric) or numeric < 0.0:
        return 0.0
    return numeric


def _sanitize_ratio(value: Any, default: float = 1.0) -> float:
    """Clamp a ratio into [0.0, 1.0]; bools, NaN and garbage return default."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return default
    numeric = float(value)
    if math.isnan(numeric):
        return default
    return max(0.0, min(1.0, numeric))


def _sanitize_flag(value: Any) -> bool:
    """Return True only for the real bool True."""
    return value is True


@dataclass
class CombatTelemetrySnapshot:
    """Sanitized snapshot of live combat state evaluated by narrative triggers."""

    elapsed_seconds: float = 0.0
    current_wave: int = 0
    aerial_kills: int = 0
    ground_kills: int = 0
    fabricators_destroyed: int = 0
    fabricators_remaining: int = 0
    boss_active: bool = False
    boss_hp_ratio: float = 1.0
    helldivers_alive: int = 0
    casualties_count: int = 0
    any_helldiver_critical: bool = False
    active_500kg_inbound: bool = False

    def __post_init__(self) -> None:
        self.elapsed_seconds = _sanitize_seconds(self.elapsed_seconds)
        self.current_wave = _sanitize_count(self.current_wave)
        self.aerial_kills = _sanitize_count(self.aerial_kills)
        self.ground_kills = _sanitize_count(self.ground_kills)
        self.fabricators_destroyed = _sanitize_count(self.fabricators_destroyed)
        self.fabricators_remaining = _sanitize_count(self.fabricators_remaining)
        self.boss_active = _sanitize_flag(self.boss_active)
        self.boss_hp_ratio = _sanitize_ratio(self.boss_hp_ratio, default=1.0)
        self.helldivers_alive = _sanitize_count(self.helldivers_alive)
        self.casualties_count = _sanitize_count(self.casualties_count)
        self.any_helldiver_critical = _sanitize_flag(self.any_helldiver_critical)
        self.active_500kg_inbound = _sanitize_flag(self.active_500kg_inbound)


@dataclass(frozen=True)
class SortieEventTrigger:
    """Declarative narrative beat fired when a telemetry condition is met during a sortie."""

    trigger_id: str
    sortie_num: int
    priority: int
    condition_type: str
    threshold: float
    dialogue_node_id: Optional[str] = None
    banter_category: Optional[str] = None
    objective_update: Optional[str] = None
    once: bool = True
    predicate: Optional[Callable[[CombatTelemetrySnapshot], bool]] = field(default=None, compare=False)

    @property
    def has_radio_payload(self) -> bool:
        """Return True if the trigger dispatches a dialogue node or banter callout."""
        return bool(self.dialogue_node_id) or bool(self.banter_category)


def _is_nonblank_str(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def validate_sortie_event_trigger(trigger: SortieEventTrigger) -> None:
    """Validate a trigger definition.

    Raises:
        TypeError: If trigger is not a SortieEventTrigger.
        ValueError: If any field is missing, out of range, or references unknown content.
    """
    if not isinstance(trigger, SortieEventTrigger):
        raise TypeError("trigger must be a SortieEventTrigger")

    if not _is_nonblank_str(trigger.trigger_id):
        raise ValueError("trigger_id must be a non-empty string")
    tid = trigger.trigger_id

    if isinstance(trigger.sortie_num, bool) or not isinstance(trigger.sortie_num, int):
        raise ValueError(f"Trigger '{tid}': sortie_num must be an int")
    if not MIN_SORTIE_NUM <= trigger.sortie_num <= MAX_SORTIE_NUM:
        raise ValueError(f"Trigger '{tid}': sortie_num {trigger.sortie_num} is out of range")

    if isinstance(trigger.priority, bool) or not isinstance(trigger.priority, int):
        raise ValueError(f"Trigger '{tid}': priority must be an int")

    if trigger.condition_type not in VALID_CONDITION_TYPES:
        raise ValueError(f"Trigger '{tid}': unknown condition_type '{trigger.condition_type}'")

    threshold = trigger.threshold
    if isinstance(threshold, bool) or not isinstance(threshold, (int, float)):
        raise ValueError(f"Trigger '{tid}': threshold must be numeric")
    if not math.isfinite(threshold) or threshold < 0:
        raise ValueError(f"Trigger '{tid}': threshold must be finite and non-negative")

    if trigger.condition_type == CONDITION_BOSS_HP_BELOW and not 0.0 <= threshold <= 1.0:
        raise ValueError(f"Trigger '{tid}': boss_hp_below threshold must be within [0.0, 1.0]")

    if trigger.condition_type == CONDITION_CUSTOM and not callable(trigger.predicate):
        raise ValueError(f"Trigger '{tid}': custom condition requires a callable predicate")

    for name, value in (
        ("dialogue_node_id", trigger.dialogue_node_id),
        ("banter_category", trigger.banter_category),
        ("objective_update", trigger.objective_update),
    ):
        if value is not None and not _is_nonblank_str(value):
            raise ValueError(f"Trigger '{tid}': {name} must be a non-empty string or None")

    if trigger.dialogue_node_id is None and trigger.banter_category is None and trigger.objective_update is None:
        raise ValueError(f"Trigger '{tid}': needs a dialogue, banter or objective payload")

    if trigger.dialogue_node_id is not None and get_dialogue_node(trigger.dialogue_node_id) is None:
        raise ValueError(f"Trigger '{tid}': unknown dialogue_node_id '{trigger.dialogue_node_id}'")

    if trigger.banter_category is not None and trigger.banter_category not in BANTER_QUEUES:
        raise ValueError(f"Trigger '{tid}': unknown banter_category '{trigger.banter_category}'")

    if not isinstance(trigger.once, bool):
        raise ValueError(f"Trigger '{tid}': once must be a bool")
