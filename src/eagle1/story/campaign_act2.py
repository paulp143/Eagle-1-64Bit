"""campaign_act2.py - Act II scripted in-flight narrative cues for Sorties 3 and 4.

Declares the Act II trigger table for Sortie 3 ("The Fabricator Furnace", Outpost Demolition)
and Sortie 4 ("The Iron Colossus", Factory Strider Raid), and registers it with a
NarrativeTriggerManager.
"""

import logging
from typing import Tuple

from eagle1.story.mission_controller import CAMPAIGN_SORTIE_REGISTRY, MAX_SORTIE_NUM, MIN_SORTIE_NUM
from eagle1.story.narrative_trigger_manager import (
    CONDITION_CUSTOM,
    CONDITION_WAVE_REACHED,
    CombatTelemetrySnapshot,
    NarrativeTriggerManager,
    SortieEventTrigger,
)

logger = logging.getLogger(__name__)

SORTIE3_NUM: int = 3
SORTIE4_NUM: int = 4

SORTIE3_CRISIS_NODE_ID: str = "sortie_3_500kg_crisis"
SORTIE4_CRISIS_NODE_ID: str = "sortie_4_strider_crisis"

SORTIE3_APPROACH_WAVE: int = 1
SORTIE3_CRISIS_FABRICATORS: int = 1
SORTIE3_CRISIS_WAVE: int = 2
SORTIE3_EXTRACTION_WAVE: int = CAMPAIGN_SORTIE_REGISTRY[SORTIE3_NUM].target_waves

SORTIE4_CRISIS_HP_RATIO: float = 0.5
SORTIE4_EXTRACTION_WAVE: int = CAMPAIGN_SORTIE_REGISTRY[SORTIE4_NUM].target_waves

SORTIE3_APPROACH_OBJECTIVE: str = (
    "Grid Charlie-4: Fly low under the AA umbrella and mark the fortified fabricator complex."
)
SORTIE4_WEAKPOINT_OBJECTIVE: str = (
    "Factory Strider on the field: Hit the ventral core and leg actuators; avoid the chin turrets."
)


def _sortie3_crisis_ready(telemetry: CombatTelemetrySnapshot) -> bool:
    """The 500kg crisis fires on the first fabricator kill, an inbound 500kg strike, or wave 2."""
    return (
        telemetry.fabricators_destroyed >= SORTIE3_CRISIS_FABRICATORS
        or telemetry.active_500kg_inbound
        or telemetry.current_wave >= SORTIE3_CRISIS_WAVE
    )


def _sortie4_arrival_ready(telemetry: CombatTelemetrySnapshot) -> bool:
    """The Factory Strider arrival callout fires as soon as the boss is on the field."""
    return telemetry.boss_active


def _sortie4_crisis_ready(telemetry: CombatTelemetrySnapshot) -> bool:
    """The Strider crisis fires below 50% boss HP or when its turrets leave a Helldiver critical."""
    return telemetry.boss_active and (
        telemetry.boss_hp_ratio < SORTIE4_CRISIS_HP_RATIO or telemetry.any_helldiver_critical
    )


# Priorities strictly decrease in story order so beats that fire in the same frame
# (e.g. the Strider spawning already below 50% HP) are queued and dispatched chronologically.
ACT2_TRIGGERS: Tuple[SortieEventTrigger, ...] = (
    SortieEventTrigger(
        trigger_id="act2_s3_approach_ghost",
        sortie_num=SORTIE3_NUM,
        priority=100,
        condition_type=CONDITION_WAVE_REACHED,
        threshold=SORTIE3_APPROACH_WAVE,
        banter_category="act2_s3_approach_ghost",
        objective_update=SORTIE3_APPROACH_OBJECTIVE,
    ),
    SortieEventTrigger(
        trigger_id="act2_s3_500kg_crisis",
        sortie_num=SORTIE3_NUM,
        priority=80,
        condition_type=CONDITION_CUSTOM,
        threshold=0.0,
        dialogue_node_id=SORTIE3_CRISIS_NODE_ID,
        predicate=_sortie3_crisis_ready,
    ),
    SortieEventTrigger(
        trigger_id="act2_s3_extraction",
        sortie_num=SORTIE3_NUM,
        priority=60,
        condition_type=CONDITION_WAVE_REACHED,
        threshold=SORTIE3_EXTRACTION_WAVE,
        banter_category="act2_s3_extraction_pelican",
        objective_update=CAMPAIGN_SORTIE_REGISTRY[SORTIE3_NUM].extraction_objective,
    ),
    SortieEventTrigger(
        trigger_id="act2_s4_strider_arrival",
        sortie_num=SORTIE4_NUM,
        priority=100,
        condition_type=CONDITION_CUSTOM,
        threshold=0.0,
        banter_category="act2_s4_strider_arrival_ghost",
        objective_update=SORTIE4_WEAKPOINT_OBJECTIVE,
        predicate=_sortie4_arrival_ready,
    ),
    SortieEventTrigger(
        trigger_id="act2_s4_strider_crisis",
        sortie_num=SORTIE4_NUM,
        priority=80,
        condition_type=CONDITION_CUSTOM,
        threshold=0.0,
        dialogue_node_id=SORTIE4_CRISIS_NODE_ID,
        predicate=_sortie4_crisis_ready,
    ),
    SortieEventTrigger(
        trigger_id="act2_s4_extraction",
        sortie_num=SORTIE4_NUM,
        priority=60,
        condition_type=CONDITION_WAVE_REACHED,
        threshold=SORTIE4_EXTRACTION_WAVE,
        banter_category="act2_s4_extraction_pelican",
        objective_update=CAMPAIGN_SORTIE_REGISTRY[SORTIE4_NUM].extraction_objective,
    ),
)


def register_act2_triggers(manager: NarrativeTriggerManager) -> int:
    """Register every Act II trigger with the given manager.

    Registration is all-or-nothing: if any Act II trigger id is already registered,
    nothing is registered.

    Returns:
        Number of triggers registered.

    Raises:
        TypeError: If manager is not a NarrativeTriggerManager.
        ValueError: If any Act II trigger id is already registered with the manager.
    """
    if not isinstance(manager, NarrativeTriggerManager):
        raise TypeError("manager must be a NarrativeTriggerManager instance")

    registered_ids = {
        trigger.trigger_id
        for sortie_num in range(MIN_SORTIE_NUM, MAX_SORTIE_NUM + 1)
        for trigger in manager.get_triggers_for_sortie(sortie_num)
    }
    clashes = sorted(registered_ids.intersection(trigger.trigger_id for trigger in ACT2_TRIGGERS))
    if clashes:
        raise ValueError(f"Act II triggers already registered: {', '.join(clashes)}")

    manager.register_triggers(ACT2_TRIGGERS)
    logger.debug("Registered %d Act II narrative triggers", len(ACT2_TRIGGERS))
    return len(ACT2_TRIGGERS)
