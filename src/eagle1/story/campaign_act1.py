"""campaign_act1.py - Act I scripted in-flight narrative cues for Sorties 1 and 2.

Declares the Act I trigger table for Sortie 1 ("Baptism of Fire", Air Superiority) and
Sortie 2 ("The Red Perimeter", Orbital Base Defense), and registers it with a
NarrativeTriggerManager.
"""

import logging
from typing import Tuple

from eagle1.story.mission_controller import CAMPAIGN_SORTIE_REGISTRY, MAX_SORTIE_NUM, MIN_SORTIE_NUM
from eagle1.story.narrative_trigger_manager import (
    CONDITION_AERIAL_KILLS,
    CONDITION_CUSTOM,
    CONDITION_ELAPSED_TIME,
    CONDITION_WAVE_REACHED,
    CombatTelemetrySnapshot,
    NarrativeTriggerManager,
    SortieEventTrigger,
)

logger = logging.getLogger(__name__)

SORTIE1_NUM: int = 1
SORTIE2_NUM: int = 2

SORTIE1_INFLIGHT_NODE_ID: str = "sortie_1_inflight"
SORTIE2_INFLIGHT_NODE_ID: str = "sortie_2_inflight"

SORTIE1_CHECKIN_SECONDS: float = 2.0
SORTIE1_VANGUARD_KILLS: int = 5
SORTIE1_OVERRIDE_KILLS: int = 10
SORTIE1_OVERRIDE_WAVE: int = 2

SORTIE2_PERIMETER_WAVE: int = 1
SORTIE2_DILEMMA_WAVE: int = 2
SORTIE2_DILEMMA_CASUALTIES: int = 1
SORTIE2_EXTRACTION_WAVE: int = CAMPAIGN_SORTIE_REGISTRY[SORTIE2_NUM].target_waves

SORTIE2_PERIMETER_OBJECTIVE: str = (
    "Perimeter breach: suppress Automaton ground forces advancing on the orbital relay."
)


def _sortie1_override_ready(telemetry: CombatTelemetrySnapshot) -> bool:
    """Reiner's command override fires once wave 2 starts or the pilot reaches 10 aerial kills."""
    return telemetry.current_wave >= SORTIE1_OVERRIDE_WAVE or telemetry.aerial_kills >= SORTIE1_OVERRIDE_KILLS


def _sortie2_dilemma_ready(telemetry: CombatTelemetrySnapshot) -> bool:
    """The casualty and supply dilemma fires on the first casualty, a critical Helldiver, or wave 2."""
    return (
        telemetry.casualties_count >= SORTIE2_DILEMMA_CASUALTIES
        or telemetry.any_helldiver_critical
        or telemetry.current_wave >= SORTIE2_DILEMMA_WAVE
    )


# Priorities strictly decrease in story order so beats that fire in the same frame
# (e.g. 0 -> 12 aerial kills) are queued and dispatched chronologically.
ACT1_TRIGGERS: Tuple[SortieEventTrigger, ...] = (
    SortieEventTrigger(
        trigger_id="act1_s1_checkin_eagle",
        sortie_num=SORTIE1_NUM,
        priority=100,
        condition_type=CONDITION_ELAPSED_TIME,
        threshold=SORTIE1_CHECKIN_SECONDS,
        banter_category="act1_s1_checkin_eagle",
    ),
    SortieEventTrigger(
        trigger_id="act1_s1_checkin_apex",
        sortie_num=SORTIE1_NUM,
        priority=95,
        condition_type=CONDITION_ELAPSED_TIME,
        threshold=SORTIE1_CHECKIN_SECONDS,
        banter_category="act1_s1_checkin_apex",
    ),
    SortieEventTrigger(
        trigger_id="act1_s1_vanguard_doc",
        sortie_num=SORTIE1_NUM,
        priority=90,
        condition_type=CONDITION_AERIAL_KILLS,
        threshold=SORTIE1_VANGUARD_KILLS,
        banter_category="act1_s1_vanguard_doc",
    ),
    SortieEventTrigger(
        trigger_id="act1_s1_radar_braker",
        sortie_num=SORTIE1_NUM,
        priority=85,
        condition_type=CONDITION_AERIAL_KILLS,
        threshold=SORTIE1_VANGUARD_KILLS,
        banter_category="act1_s1_radar_braker",
    ),
    SortieEventTrigger(
        trigger_id="act1_s1_reiner_override",
        sortie_num=SORTIE1_NUM,
        priority=80,
        condition_type=CONDITION_CUSTOM,
        threshold=0.0,
        dialogue_node_id=SORTIE1_INFLIGHT_NODE_ID,
        predicate=_sortie1_override_ready,
    ),
    SortieEventTrigger(
        trigger_id="act1_s2_perimeter_breach",
        sortie_num=SORTIE2_NUM,
        priority=100,
        condition_type=CONDITION_WAVE_REACHED,
        threshold=SORTIE2_PERIMETER_WAVE,
        banter_category="act1_s2_perimeter_ghost",
        objective_update=SORTIE2_PERIMETER_OBJECTIVE,
    ),
    SortieEventTrigger(
        trigger_id="act1_s2_supply_dilemma",
        sortie_num=SORTIE2_NUM,
        priority=80,
        condition_type=CONDITION_CUSTOM,
        threshold=0.0,
        dialogue_node_id=SORTIE2_INFLIGHT_NODE_ID,
        predicate=_sortie2_dilemma_ready,
    ),
    SortieEventTrigger(
        trigger_id="act1_s2_extraction",
        sortie_num=SORTIE2_NUM,
        priority=60,
        condition_type=CONDITION_WAVE_REACHED,
        threshold=SORTIE2_EXTRACTION_WAVE,
        banter_category="act1_s2_extraction_pelican",
        objective_update=CAMPAIGN_SORTIE_REGISTRY[SORTIE2_NUM].extraction_objective,
    ),
)


def register_act1_triggers(manager: NarrativeTriggerManager) -> int:
    """Register every Act I trigger with the given manager.

    Registration is all-or-nothing: if any Act I trigger id is already registered,
    nothing is registered.

    Returns:
        Number of triggers registered.

    Raises:
        TypeError: If manager is not a NarrativeTriggerManager.
        ValueError: If any Act I trigger id is already registered with the manager.
    """
    if not isinstance(manager, NarrativeTriggerManager):
        raise TypeError("manager must be a NarrativeTriggerManager instance")

    registered_ids = {
        trigger.trigger_id
        for sortie_num in range(MIN_SORTIE_NUM, MAX_SORTIE_NUM + 1)
        for trigger in manager.get_triggers_for_sortie(sortie_num)
    }
    clashes = sorted(registered_ids.intersection(trigger.trigger_id for trigger in ACT1_TRIGGERS))
    if clashes:
        raise ValueError(f"Act I triggers already registered: {', '.join(clashes)}")

    manager.register_triggers(ACT1_TRIGGERS)
    logger.debug("Registered %d Act I narrative triggers", len(ACT1_TRIGGERS))
    return len(ACT1_TRIGGERS)
