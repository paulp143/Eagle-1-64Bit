"""narrative_trigger_manager.py - In-flight narrative event triggers for campaign sorties.

Evaluates live combat telemetry each frame, fires scripted sortie triggers in a
deterministic priority order, queues radio beats while comms are busy, and keeps
the tactical HUD objective in sync with the narrative.
"""

from dataclasses import dataclass, field
import logging
import math
from typing import TYPE_CHECKING, Any, Callable, Dict, Iterable, List, Optional, Sequence, Set, Tuple

from eagle1.story.dialogue_data import BANTER_QUEUES, get_contextual_banter
from eagle1.story.dialogue_db import get_dialogue_node
from eagle1.story.mission_controller import MAX_STORY_SORTIE_NUM, MIN_SORTIE_NUM, MissionController
from eagle1.story.story_manager import StoryManager

if TYPE_CHECKING:
    from eagle1.story.comms_hud import CommsHUD

logger = logging.getLogger(__name__)

CONDITION_ELAPSED_TIME: str = "elapsed_time"
CONDITION_AERIAL_KILLS: str = "aerial_kills"
CONDITION_WAVE_REACHED: str = "wave_reached"
CONDITION_FABRICATORS_DESTROYED: str = "fabricators_destroyed"
CONDITION_BOSS_HP_BELOW: str = "boss_hp_below"
CONDITION_HELLDIVER_CASUALTIES: str = "helldiver_casualties"
CONDITION_CUSTOM: str = "custom"

MAX_DISPATCH_LOG: int = 256

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
    if not MIN_SORTIE_NUM <= trigger.sortie_num <= MAX_STORY_SORTIE_NUM:
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


class NarrativeTriggerManager:
    """Evaluates sortie triggers against combat telemetry and dispatches narrative beats."""

    def __init__(
        self,
        story_manager: StoryManager,
        comms_hud: Optional["CommsHUD"] = None,
        mission_controller: Optional[MissionController] = None,
    ) -> None:
        if story_manager is None or isinstance(story_manager, bool) or not isinstance(story_manager, StoryManager):
            raise TypeError("story_manager must be a valid StoryManager instance")

        self.story_manager = story_manager
        self.comms_hud = comms_hud
        self.mission_controller = mission_controller
        self.active_sortie_num: int = MIN_SORTIE_NUM
        self.fired_trigger_ids: Set[str] = set()
        self.pending_queue: List[SortieEventTrigger] = []
        self.dispatch_log: List[str] = []
        self._triggers_by_sortie: Dict[int, List[SortieEventTrigger]] = {}
        self._registration_index: Dict[str, int] = {}
        self._condition_latched: Dict[str, bool] = {}
        self._failed_predicate_ids: Set[str] = set()
        self._dispatch_count: int = 0

    def register_trigger(self, trigger: SortieEventTrigger) -> None:
        """Validate and register a trigger for its sortie, keeping each sortie's list sorted."""
        validate_sortie_event_trigger(trigger)
        if trigger.trigger_id in self._registration_index:
            raise ValueError(f"Duplicate trigger_id '{trigger.trigger_id}'")

        self._registration_index[trigger.trigger_id] = len(self._registration_index)
        bucket = self._triggers_by_sortie.setdefault(trigger.sortie_num, [])
        bucket.append(trigger)
        bucket.sort(key=self._sort_key)

    def register_triggers(self, triggers: Iterable[SortieEventTrigger]) -> None:
        """Register several triggers; the first invalid one aborts the remaining registrations."""
        for trigger in triggers:
            self.register_trigger(trigger)

    def get_triggers_for_sortie(self, sortie_num: int) -> Tuple[SortieEventTrigger, ...]:
        """Return the registered triggers for a sortie in evaluation order."""
        if isinstance(sortie_num, bool) or not isinstance(sortie_num, int):
            return ()
        return tuple(self._triggers_by_sortie.get(sortie_num, ()))

    def reset_for_sortie(self, sortie_num: int) -> None:
        """Clear fired state and pending beats, then select the given sortie's triggers."""
        self.active_sortie_num = self._sanitize_sortie_num(sortie_num)
        self.fired_trigger_ids.clear()
        self.pending_queue.clear()
        self._condition_latched.clear()
        self._failed_predicate_ids.clear()
        self.dispatch_log.clear()
        self._dispatch_count = 0

    def is_comms_busy(self) -> bool:
        """Return True while an interactive dialogue or a comms overlay occupies the radio."""
        if self.story_manager.is_dialogue_active:
            return True
        return self.comms_hud is not None and bool(self.comms_hud.is_active)

    def is_condition_met(self, trigger: SortieEventTrigger, telemetry: CombatTelemetrySnapshot) -> bool:
        """Evaluate a trigger's condition against sanitized telemetry."""
        condition = trigger.condition_type
        if condition == CONDITION_ELAPSED_TIME:
            return telemetry.elapsed_seconds >= trigger.threshold
        if condition == CONDITION_AERIAL_KILLS:
            return telemetry.aerial_kills >= trigger.threshold
        if condition == CONDITION_WAVE_REACHED:
            return telemetry.current_wave >= trigger.threshold
        if condition == CONDITION_FABRICATORS_DESTROYED:
            return telemetry.fabricators_destroyed >= trigger.threshold
        if condition == CONDITION_BOSS_HP_BELOW:
            return telemetry.boss_active and telemetry.boss_hp_ratio < trigger.threshold
        if condition == CONDITION_HELLDIVER_CASUALTIES:
            return telemetry.casualties_count >= trigger.threshold
        if condition == CONDITION_CUSTOM:
            try:
                return bool(trigger.predicate(telemetry))
            except Exception:
                # Third-party predicates must never crash the 60 FPS loop. Log once per trigger
                # until the next sortie reset instead of flooding the log at 60 Hz.
                if trigger.trigger_id not in self._failed_predicate_ids:
                    self._failed_predicate_ids.add(trigger.trigger_id)
                    logger.warning("Custom predicate for trigger '%s' raised", trigger.trigger_id, exc_info=True)
                return False
        return False

    def evaluate(self, telemetry: CombatTelemetrySnapshot) -> Sequence[str]:
        """Evaluate the active sortie's triggers for one frame.

        Returns:
            Trigger ids that fired during this call, in priority order. Frames without
            a fired trigger return the shared empty tuple and allocate nothing.
        """
        if not isinstance(telemetry, CombatTelemetrySnapshot):
            logger.warning("evaluate() expected CombatTelemetrySnapshot, got %s", type(telemetry).__name__)
            return ()

        newly_fired: Optional[List[str]] = None
        for trigger in self._triggers_by_sortie.get(self.active_sortie_num, ()):
            tid = trigger.trigger_id
            if trigger.once and tid in self.fired_trigger_ids:
                continue

            met = self.is_condition_met(trigger, telemetry)
            if trigger.once:
                if not met:
                    continue
            else:
                was_latched = self._condition_latched.get(tid, False)
                self._condition_latched[tid] = met
                if not met or was_latched:
                    continue
                if any(queued.trigger_id == tid for queued in self.pending_queue):
                    continue

            self.fired_trigger_ids.add(tid)
            if newly_fired is None:
                newly_fired = []
            newly_fired.append(tid)
            if trigger.has_radio_payload:
                self.pending_queue.append(trigger)
            else:
                self._apply_objective(trigger)

        if newly_fired and len(self.pending_queue) > 1:
            self.pending_queue.sort(key=self._sort_key)

        self.dispatch_next_pending()
        return tuple(newly_fired) if newly_fired is not None else ()

    def dispatch_next_pending(self) -> Optional[str]:
        """Dispatch the highest-priority queued beat if the radio is free."""
        if not self.pending_queue or self.is_comms_busy():
            return None

        trigger = self.pending_queue.pop(0)
        if not self._dispatch(trigger):
            logger.warning("Narrative beat '%s' could not be delivered and was dropped", trigger.trigger_id)
            return None

        self._dispatch_count += 1
        self.dispatch_log.append(trigger.trigger_id)
        if len(self.dispatch_log) > MAX_DISPATCH_LOG:
            del self.dispatch_log[0]
        return trigger.trigger_id

    def _sort_key(self, trigger: SortieEventTrigger) -> Tuple[int, int]:
        return (-trigger.priority, self._registration_index[trigger.trigger_id])

    def _sanitize_sortie_num(self, sortie_num: Any) -> int:
        if isinstance(sortie_num, bool) or not isinstance(sortie_num, int):
            logger.warning("Invalid sortie number %r; falling back to %d", sortie_num, MIN_SORTIE_NUM)
            return MIN_SORTIE_NUM
        if not MIN_SORTIE_NUM <= sortie_num <= MAX_STORY_SORTIE_NUM:
            logger.warning("Sortie number %d out of range; falling back to %d", sortie_num, MIN_SORTIE_NUM)
            return MIN_SORTIE_NUM
        return sortie_num

    def _dispatch(self, trigger: SortieEventTrigger) -> bool:
        """Deliver a trigger's radio beat and apply its objective; return True if the beat was delivered."""
        delivered = False
        if trigger.dialogue_node_id is not None:
            if self.story_manager.start_dialogue(trigger.dialogue_node_id):
                node = get_dialogue_node(trigger.dialogue_node_id)
                if self.comms_hud is not None:
                    self.comms_hud.trigger_transmission(node)
                    delivered = True
                else:
                    # An interactive node is active in StoryManager even without a HUD;
                    # a non-interactive node would be invisible, so it counts as undelivered.
                    delivered = bool(node.options)
            else:
                logger.warning("Dialogue trigger '%s' could not start its node", trigger.trigger_id)
        elif trigger.banter_category is not None:
            if self.comms_hud is None:
                logger.debug("Skipping banter trigger '%s' without a comms HUD", trigger.trigger_id)
            else:
                line = get_contextual_banter(trigger.banter_category, selection_index=self._dispatch_count)
                if line is not None:
                    delivered = bool(self.comms_hud.trigger_callout(line.speaker, line.text, portrait=line.portrait_path))

        self._apply_objective(trigger)
        return delivered

    def _apply_objective(self, trigger: SortieEventTrigger) -> None:
        if trigger.objective_update and self.mission_controller is not None:
            self.mission_controller.set_active_objective_text(trigger.objective_update)
