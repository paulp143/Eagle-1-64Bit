"""campaign_act2.py - Act II scripted in-flight narrative cues for Sorties 3 and 4.

Declares the Act II trigger table for Sortie 3 ("The Fabricator Furnace", Outpost Demolition)
and Sortie 4 ("The Iron Colossus", Factory Strider Raid), and registers it with a
NarrativeTriggerManager.
"""

from dataclasses import dataclass
import logging
import math
from typing import TYPE_CHECKING, Any, Dict, Optional, Tuple

from eagle1.story.dialogue_data import BANTER_QUEUES, BanterLine
from eagle1.story.mission_controller import CAMPAIGN_SORTIE_REGISTRY, MAX_SORTIE_NUM, MIN_SORTIE_NUM, MissionController
from eagle1.story.narrative_trigger_manager import (
    CONDITION_CUSTOM,
    CONDITION_WAVE_REACHED,
    CombatTelemetrySnapshot,
    NarrativeTriggerManager,
    SortieEventTrigger,
)
from eagle1.story.story_manager import VALID_STANCES, StoryManager

if TYPE_CHECKING:
    from eagle1.story.comms_hud import CommsHUD
    from eagle1.systems.ground_support import GroundSupportManager

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


BRAKER_UNIT_INDEX: int = 1
BRAKER_WOUNDED_HEALTH_RATIO: float = 0.25
NEUTRAL_FABRICATOR_DAMAGE_RATIO: float = 0.5
SORTIE3_OUTCOME_EXTRA_KEY: str = "act2_sortie3_500kg"

# record_choice() applies the +12.0 stance delta; the scripted Braker casualty then
# applies StoryManager.on_helldiver_death() (-3.5), so the net LOYAL shift is +8.5.
SORTIE3_LOYAL_NET_LOYALTY_DELTA: float = 8.5

SORTIE3_OBJECTIVE_LOYAL: str = (
    "Fabricator vent destroyed. Clear the remaining Charlie-4 fabricators with precision ordnance."
)
SORTIE3_OBJECTIVE_NEUTRAL: str = (
    "Vent perimeter breached. Finish the damaged fabricator and cover Doc while he stabilizes Braker."
)
SORTIE3_OBJECTIVE_DISSIDENT: str = (
    "500kg drop aborted. Destroy the fabricator manually with cannons; keep Braker clear."
)
SORTIE4_OBJECTIVE_LOYAL: str = (
    "PRIORITY: Commit every pass to the Factory Strider's ventral core. Squad cover is secondary."
)
SORTIE4_OBJECTIVE_NEUTRAL: str = (
    "Alternate passes: Strike the Strider's leg actuators between suppression runs on its turrets."
)
SORTIE4_OBJECTIVE_DISSIDENT: str = (
    "Squad first: Silence the Strider's chin turrets pinning Viper Squad, then engage the core."
)

ACT2_CHOICE_OBJECTIVES: Dict[str, Dict[str, str]] = {
    SORTIE3_CRISIS_NODE_ID: {
        "loyal": SORTIE3_OBJECTIVE_LOYAL,
        "neutral": SORTIE3_OBJECTIVE_NEUTRAL,
        "dissident": SORTIE3_OBJECTIVE_DISSIDENT,
    },
    SORTIE4_CRISIS_NODE_ID: {
        "loyal": SORTIE4_OBJECTIVE_LOYAL,
        "neutral": SORTIE4_OBJECTIVE_NEUTRAL,
        "dissident": SORTIE4_OBJECTIVE_DISSIDENT,
    },
}

_STANCE_KEY_ALIASES: Dict[str, str] = {"1": "loyal", "2": "neutral", "3": "dissident"}


@dataclass(frozen=True)
class Sortie3CrisisOutcome:
    """Battlefield result of the Sortie 3 500kg friendly-fire crisis."""

    stance: str
    braker_survived: bool
    braker_killed_by_strike: bool
    braker_wounded: bool
    fabricator_destroyed: bool
    objective: str


def _normalize_stance(stance: object) -> Optional[str]:
    """Map "loyal", "[LOYAL]", " Loyal " or the key "1" to a canonical stance; anything else returns None."""
    if isinstance(stance, bool) or not isinstance(stance, str):
        return None
    clean = stance.strip().strip("[]").strip().lower()
    clean = _STANCE_KEY_ALIASES.get(clean, clean)
    return clean if clean in VALID_STANCES else None


def _as_ground_support(ground_support_manager: object) -> Optional[Any]:
    """Return the manager if it exposes list-typed units and enemy_fabricators, else None."""
    if ground_support_manager is None:
        return None
    units = getattr(ground_support_manager, "units", None)
    fabricators = getattr(ground_support_manager, "enemy_fabricators", None)
    if not isinstance(units, list) or not isinstance(fabricators, list):
        logger.warning("Ignoring invalid ground support manager %r", ground_support_manager)
        return None
    return ground_support_manager


def _find_unit(gsm: "GroundSupportManager", index: int) -> Optional[Any]:
    """Return the first unit whose index matches, or None."""
    return next((u for u in gsm.units if getattr(u, "index", None) == index), None)


def _first_living_fabricator(gsm: "GroundSupportManager") -> Optional[Any]:
    """Return the first fabricator that is still alive, or None."""
    return next((f for f in gsm.enemy_fabricators if getattr(f, "is_alive", False)), None)


def _apply_choice_objective(node_id: str, canonical: str, mission_controller: Optional[MissionController]) -> str:
    """Set the mapped objective when a MissionController is wired; always return the mapped text."""
    text = ACT2_CHOICE_OBJECTIVES[node_id][canonical]
    if isinstance(mission_controller, MissionController):
        mission_controller.set_active_objective_text(text)
    return text


def resolve_sortie3_500kg_choice(
    stance: str,
    story_manager: Optional[StoryManager],
    ground_support_manager: Optional["GroundSupportManager"] = None,
    mission_controller: Optional[MissionController] = None,
) -> Optional[Sortie3CrisisOutcome]:
    """Apply the battlefield consequences of the pilot's 500kg crisis answer.

    Call after StoryManager.record_choice("sortie_3_500kg_crisis", stance), which applies
    the stance loyalty delta. This function only adds the scripted Braker casualty
    (StoryManager.on_helldiver_death, -3.5) on LOYAL, so the net LOYAL shift is
    SORTIE3_LOYAL_NET_LOYALTY_DELTA (+8.5), or +12.0 if Braker was already down.

    Without a ground support manager Braker is assumed alive and no entity is mutated.

    Returns:
        The outcome, or None if stance is invalid.
    """
    canonical = _normalize_stance(stance)
    if canonical is None:
        logger.warning("Ignoring invalid stance %r for Act II node '%s'", stance, SORTIE3_CRISIS_NODE_ID)
        return None

    story = story_manager if isinstance(story_manager, StoryManager) else None
    gsm = _as_ground_support(ground_support_manager)

    if gsm is None:
        braker = None
        braker_alive_before = True
        fabricator = None
    else:
        braker = _find_unit(gsm, BRAKER_UNIT_INDEX)
        braker_alive_before = braker is not None and bool(braker.is_alive)
        fabricator = _first_living_fabricator(gsm)

    braker_killed = False
    braker_wounded = False
    fabricator_destroyed = False

    if canonical == "loyal":
        if fabricator is not None:
            fabricator.take_damage(fabricator.health)
            fabricator_destroyed = not fabricator.is_alive
        if braker_alive_before:
            braker_killed = True if gsm is None else bool(gsm.apply_scripted_casualty(BRAKER_UNIT_INDEX))
        if braker_killed and story is not None:
            story.on_helldiver_death(BRAKER_UNIT_INDEX)
    elif canonical == "neutral":
        if fabricator is not None:
            fabricator.take_damage(fabricator.max_health * NEUTRAL_FABRICATOR_DAMAGE_RATIO)
            fabricator_destroyed = not fabricator.is_alive
        if gsm is None:
            braker_wounded = True
        elif braker is not None and braker_alive_before:
            braker.shield = 0.0
            braker.health = min(braker.health, max(1.0, braker.max_health * BRAKER_WOUNDED_HEALTH_RATIO))
            braker_wounded = True

    braker_survived = braker_alive_before and not braker_killed
    objective = _apply_choice_objective(SORTIE3_CRISIS_NODE_ID, canonical, mission_controller)

    if story is not None:
        if not isinstance(story.extra, dict):
            story.extra = {}
        story.extra[SORTIE3_OUTCOME_EXTRA_KEY] = {"stance": canonical, "braker_survived": braker_survived}
        story.save_campaign_state()

    logger.info(
        "Sortie 3 500kg crisis resolved: stance=%s braker_survived=%s fabricator_destroyed=%s",
        canonical,
        braker_survived,
        fabricator_destroyed,
    )
    return Sortie3CrisisOutcome(
        stance=canonical,
        braker_survived=braker_survived,
        braker_killed_by_strike=braker_killed,
        braker_wounded=braker_wounded,
        fabricator_destroyed=fabricator_destroyed,
        objective=objective,
    )


def get_sortie3_braker_survived(story_manager: Optional[StoryManager]) -> bool:
    """Return whether Braker survived the Sortie 3 crisis; True when no outcome is recorded."""
    if not isinstance(story_manager, StoryManager) or not isinstance(story_manager.extra, dict):
        return True
    record = story_manager.extra.get(SORTIE3_OUTCOME_EXTRA_KEY)
    if not isinstance(record, dict):
        return True
    value = record.get("braker_survived")
    return value if isinstance(value, bool) else True


def apply_sortie4_choice_effect(stance: str, mission_controller: Optional[MissionController]) -> Optional[str]:
    """Update the HUD objective after the pilot answers the Sortie 4 Strider crisis.

    Loyalty is applied separately by StoryManager.record_choice().

    Returns:
        The objective text now shown on the HUD, or None if nothing was applied.
    """
    canonical = _normalize_stance(stance)
    if canonical is None:
        logger.warning("Ignoring invalid stance %r for Act II node '%s'", stance, SORTIE4_CRISIS_NODE_ID)
        return None
    if not isinstance(mission_controller, MissionController):
        logger.debug("No MissionController wired; skipping objective update for '%s'", SORTIE4_CRISIS_NODE_ID)
        return None

    _apply_choice_objective(SORTIE4_CRISIS_NODE_ID, canonical, mission_controller)
    return mission_controller.current_objective


def resolve_act2_choice(
    node_id: str,
    stance: str,
    story_manager: Optional[StoryManager],
    ground_support_manager: Optional["GroundSupportManager"] = None,
    mission_controller: Optional[MissionController] = None,
) -> Optional[str]:
    """Route a recorded in-flight choice to its Act II effect.

    Returns:
        The objective text mapped to the choice, or None if node_id is not an Act II
        in-flight node or the stance is invalid.
    """
    if isinstance(node_id, bool) or not isinstance(node_id, str):
        return None
    clean_id = node_id.strip()
    if clean_id == SORTIE3_CRISIS_NODE_ID:
        outcome = resolve_sortie3_500kg_choice(stance, story_manager, ground_support_manager, mission_controller)
        return outcome.objective if outcome is not None else None
    if clean_id == SORTIE4_CRISIS_NODE_ID:
        return apply_sortie4_choice_effect(stance, mission_controller)
    return None


SQUAD_SIZE: int = 4

CASUALTY_CHECK_FLAWLESS_BRAKER: str = "act2_s4_check_flawless_braker"
CASUALTY_CHECK_FLAWLESS_MEMORIAL: str = "act2_s4_check_flawless_memorial"
CASUALTY_CHECK_PARTIAL_BRAKER: str = "act2_s4_check_partial_braker"
CASUALTY_CHECK_PARTIAL_MEMORIAL: str = "act2_s4_check_partial_memorial"
CASUALTY_CHECK_WIPED: str = "act2_s4_check_wiped"


def _sanitize_casualties(value: object) -> int:
    """Coerce a casualty count to an int in [0, SQUAD_SIZE]; bools, NaN, inf and garbage become 0."""
    if isinstance(value, bool):
        return 0
    if isinstance(value, float):
        if not math.isfinite(value):
            return 0
        return max(0, min(SQUAD_SIZE, int(value)))
    if isinstance(value, int):
        return max(0, min(SQUAD_SIZE, value))
    return 0


def get_sortie4_casualty_check_category(casualties_count: int, braker_survived: bool = True) -> str:
    """Return the BANTER_QUEUES category for the Sortie 4 pre-extraction casualty check."""
    count = _sanitize_casualties(casualties_count)
    survived = braker_survived if isinstance(braker_survived, bool) else True
    if count >= SQUAD_SIZE:
        return CASUALTY_CHECK_WIPED
    if count == 0:
        return CASUALTY_CHECK_FLAWLESS_BRAKER if survived else CASUALTY_CHECK_FLAWLESS_MEMORIAL
    return CASUALTY_CHECK_PARTIAL_BRAKER if survived else CASUALTY_CHECK_PARTIAL_MEMORIAL


def get_sortie4_casualty_check_banter(casualties_count: int, braker_survived: bool = True) -> BanterLine:
    """Return the radio line acknowledging surviving or fallen Viper members before extraction.

    Args:
        casualties_count: Viper Squad casualties in Sortie 4 (0 flawless, 1..3 partial, 4 wiped).
        braker_survived: Whether Braker survived the Sortie 3 500kg crisis
            (see get_sortie3_braker_survived()).
    """
    category = get_sortie4_casualty_check_category(casualties_count, braker_survived)
    return BANTER_QUEUES[category][0]


def emit_sortie4_casualty_check(
    comms_hud: Optional["CommsHUD"],
    casualties_count: int,
    braker_survived: bool = True,
) -> bool:
    """Play the Sortie 4 casualty check on the comms HUD; return True if the callout was shown."""
    if comms_hud is None:
        logger.debug("No comms HUD wired; skipping Sortie 4 casualty check")
        return False
    line = get_sortie4_casualty_check_banter(casualties_count, braker_survived)
    return bool(comms_hud.trigger_callout(line.speaker, line.text, portrait=line.portrait_path))
