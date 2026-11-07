"""campaign_act3.py - Act III campaign endings.

Act III-A "The Path of Blind Obedience" (OBEDIENCE_PURGE, docs/story.md Section 6):
Scene 3A.1 encrypted Priority Red order (Vermilion-Nine), Sortie 5A trench purge of
Viper Squad, Scene 3A.2 hangar clone interlude and the Sortie 6A terminal dive.

The ending is a tragedy without an exit: whatever the pilot answers, the resolvers keep
loyalty at zealot level (>= THRESHOLD_OBEDIENCE_PURGE) so the branch can never flip.
"""

from dataclasses import dataclass
import logging
import math
from typing import TYPE_CHECKING, Any, Optional, Tuple

from eagle1.story.cinematic_player import (
    CINEMATIC_SCENE_EPILOGUE_CARD,
    CINEMATIC_SCENE_HANGAR_CLONES,
    CINEMATIC_SCENE_SUICIDE_DIVE,
    CINEMATIC_SCENE_TRENCH_STRIKE,
    CINEMATIC_SCENE_WHITE_FLASH,
    CinematicKeyframe,
    CinematicSequence,
    CinematicSubtitle,
    EpilogueSummaryStats,
)
from eagle1.story.dialogue_data import BANTER_QUEUES
from eagle1.story.mission_controller import (
    MAX_STORY_SORTIE_NUM,
    MIN_SORTIE_NUM,
    CampaignSortieConfig,
    MissionController,
)
from eagle1.story.narrative_trigger_manager import (
    CONDITION_ELAPSED_TIME,
    NarrativeTriggerManager,
    SortieEventTrigger,
)
from eagle1.story.story_manager import (
    BRANCH_OBEDIENCE_PURGE,
    MAX_LOYALTY,
    THRESHOLD_OBEDIENCE_PURGE,
    VALID_STANCES,
    StoryManager,
)
from eagle1.ui import theme

if TYPE_CHECKING:
    from eagle1.story.comms_hud import CommsHUD
    from eagle1.systems.ground_support import GroundSupportManager

logger = logging.getLogger(__name__)

ACT3_NUM: int = 3
SORTIE5A_NUM: int = 5
SORTIE6A_NUM: int = 6

ACT3A_SEQUENCE_ID: str = "act3a_obedience_purge"
ACT3A_ORDER_NODE_ID: str = "act3a_encrypted_order"
SORTIE5A_TRENCH_NODE_ID: str = "sortie_5a_trench_lock"

ACT3A_MIN_LOYALTY: float = THRESHOLD_OBEDIENCE_PURGE
ACT3A_ORDER_LOYAL_LOYALTY: float = MAX_LOYALTY

ACT3A_DETONATION_THREAT: str = (
    "Refusal triggers remote detonation of your craft's engine reactor in three... two..."
)
ACT3A_APEX_FINAL_WORDS: str = BANTER_QUEUES["act3a_s5_apex_final"][0].text
ACT3A_REINER_COMMENDATION: str = BANTER_QUEUES["act3a_s5_reiner_commendation"][0].text
ACT3A_REINER_SPEAKER: str = BANTER_QUEUES["act3a_s5_reiner_commendation"][0].speaker

VIPER_SQUAD_INDICES: Tuple[int, ...] = (0, 1, 2, 3)
VIPER_SQUAD_CALLSIGNS: Tuple[str, ...] = ("Apex", "Braker", "Ghost", "Doc")
VIPER_SQUAD_SIZE: int = len(VIPER_SQUAD_INDICES)

VIPER_SQUAD_PURGED_EXTRA_KEY: str = "viper_squad_purged"
ACT3A_OUTCOME_EXTRA_KEY: str = "act3a_trench_strike"
ACT3A_ORDER_EXTRA_KEY: str = "act3a_order_compliance"
ACT3A_ORDER_LOYAL: str = "loyal"
ACT3A_ORDER_FORCED: str = "forced"

SORTIE5A_CHECKIN_SECONDS: float = 2.0
SORTIE5A_DOC_SECONDS: float = 6.0
SORTIE5A_TRENCH_LOCK_SECONDS: float = 11.0

SORTIE5A_INITIAL_OBJECTIVE: str = (
    "Outpost Gamma: Viper Squad is holding the dry-valley trench. Hold position overhead."
)
SORTIE5A_TRENCH_OBJECTIVE: str = (
    "VERMILION-NINE: Objective reticle locked on Viper Squad's trench. Deploy the 500kg."
)
SORTIE5A_RETURN_OBJECTIVE: str = "Target neutralized. Sector clean. Return to the Leviathan."

SORTIE_5A_CONFIG: CampaignSortieConfig = CampaignSortieConfig(
    sortie_num=SORTIE5A_NUM,
    act=ACT3_NUM,
    sortie_id="sortie_5a_obedience_purge",
    title="SORTIE 5A // THE PURGE OF VIPER SQUAD",
    operation_name="ORDER VERMILION-NINE",
    mission_mode="base_defense",
    threat_level="CLASSIFIED // PRIORITY RED",
    target_waves=2,
    required_fabricators=0,
    has_boss_strider=False,
    initial_objective=SORTIE5A_INITIAL_OBJECTIVE,
    extraction_objective=SORTIE5A_RETURN_OBJECTIVE,
    briefing_node_id=ACT3A_ORDER_NODE_ID,
    inflight_node_ids=(SORTIE5A_TRENCH_NODE_ID,),
    # Scene 3A.2 (hangar clone interlude) is a cinematic, not a dialogue node.
    debrief_node_id=ACT3A_SEQUENCE_ID,
)

# Priorities strictly decrease in story order: check-in, evac plea, then the trench lock.
ACT3A_TRIGGERS: Tuple[SortieEventTrigger, ...] = (
    SortieEventTrigger(
        trigger_id="act3a_s5_apex_checkin",
        sortie_num=SORTIE5A_NUM,
        priority=100,
        condition_type=CONDITION_ELAPSED_TIME,
        threshold=SORTIE5A_CHECKIN_SECONDS,
        banter_category="act3a_s5_apex_checkin",
        objective_update=SORTIE5A_INITIAL_OBJECTIVE,
    ),
    SortieEventTrigger(
        trigger_id="act3a_s5_doc_evac",
        sortie_num=SORTIE5A_NUM,
        priority=90,
        condition_type=CONDITION_ELAPSED_TIME,
        threshold=SORTIE5A_DOC_SECONDS,
        banter_category="act3a_s5_doc_evac",
    ),
    SortieEventTrigger(
        trigger_id="act3a_s5_trench_lock",
        sortie_num=SORTIE5A_NUM,
        priority=80,
        condition_type=CONDITION_ELAPSED_TIME,
        threshold=SORTIE5A_TRENCH_LOCK_SECONDS,
        dialogue_node_id=SORTIE5A_TRENCH_NODE_ID,
        objective_update=SORTIE5A_TRENCH_OBJECTIVE,
    ),
)

_STANCE_KEY_ALIASES = {"1": "loyal", "2": "neutral", "3": "dissident"}


@dataclass(frozen=True)
class Act3AOrderOutcome:
    """Result of the pilot's answer to the encrypted Vermilion-Nine order."""

    stance: str
    forced_compliance: bool
    loyalty_after: float
    reiner_response: str


@dataclass(frozen=True)
class Act3ATrenchStrikeOutcome:
    """Result of the Sortie 5A 500kg strike on Viper Squad's trench."""

    purged_callsigns: Tuple[str, ...]
    newly_killed: int
    already_resolved: bool
    trench_position: Optional[Tuple[float, float]]
    loyalty_after: float
    final_words: str
    commendation: str
    objective: str


def register_act3a_triggers(manager: NarrativeTriggerManager) -> int:
    """Register every Act III-A trigger with the given manager (all-or-nothing).

    Returns:
        Number of triggers registered.

    Raises:
        TypeError: If manager is not a NarrativeTriggerManager.
        ValueError: If any Act III-A trigger id is already registered with the manager.
    """
    if not isinstance(manager, NarrativeTriggerManager):
        raise TypeError("manager must be a NarrativeTriggerManager instance")

    registered_ids = {
        trigger.trigger_id
        for sortie_num in range(MIN_SORTIE_NUM, MAX_STORY_SORTIE_NUM + 1)
        for trigger in manager.get_triggers_for_sortie(sortie_num)
    }
    clashes = sorted(registered_ids.intersection(trigger.trigger_id for trigger in ACT3A_TRIGGERS))
    if clashes:
        raise ValueError(f"Act III-A triggers already registered: {', '.join(clashes)}")

    manager.register_triggers(ACT3A_TRIGGERS)
    logger.debug("Registered %d Act III-A narrative triggers", len(ACT3A_TRIGGERS))
    return len(ACT3A_TRIGGERS)


def _normalize_stance(stance: object) -> Optional[str]:
    """Map "loyal", "[LOYAL]", " Loyal " or the key "1" to a canonical stance; anything else returns None."""
    if isinstance(stance, bool) or not isinstance(stance, str):
        return None
    clean = stance.strip().strip("[]").strip().lower()
    clean = _STANCE_KEY_ALIASES.get(clean, clean)
    return clean if clean in VALID_STANCES else None


def _clamp_zealot(value: Any) -> float:
    """Clamp loyalty into [ACT3A_MIN_LOYALTY, MAX_LOYALTY]; bools, NaN, inf and garbage become the minimum."""
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        return ACT3A_MIN_LOYALTY
    return min(MAX_LOYALTY, max(ACT3A_MIN_LOYALTY, float(value)))


def _as_story(story_manager: object) -> Optional[StoryManager]:
    """Return the StoryManager with a dict-typed extra, or None."""
    if not isinstance(story_manager, StoryManager):
        return None
    if not isinstance(story_manager.extra, dict):
        story_manager.extra = {}
    return story_manager


def _as_ground_support(ground_support_manager: object) -> Optional[Any]:
    """Return the manager if it exposes a list of units, else None."""
    if ground_support_manager is None:
        return None
    if not isinstance(getattr(ground_support_manager, "units", None), list):
        logger.warning("Ignoring invalid ground support manager %r", ground_support_manager)
        return None
    return ground_support_manager


def get_viper_trench_position(ground_support_manager: object) -> Optional[Tuple[float, float]]:
    """Return the world position of Viper Squad's trench (centroid of the squad).

    Living Helldivers define the trench; if all are down, every unit is used.
    Returns None without a valid ground support manager or without units.
    """
    gsm = _as_ground_support(ground_support_manager)
    if gsm is None:
        return None
    units = [u for u in gsm.units if getattr(u, "is_alive", False)] or list(gsm.units)
    points = []
    for unit in units:
        x, y = getattr(unit, "pos_x", None), getattr(unit, "pos_y", None)
        if isinstance(x, (int, float)) and isinstance(y, (int, float)) and math.isfinite(x) and math.isfinite(y):
            points.append((float(x), float(y)))
    if not points:
        return None
    return (sum(p[0] for p in points) / len(points), sum(p[1] for p in points) / len(points))


def resolve_act3a_order_choice(stance: str, story_manager: Optional[StoryManager]) -> Optional[Act3AOrderOutcome]:
    """Apply the outcome of the Vermilion-Nine order after StoryManager.record_choice().

    LOYAL sets loyalty to 100.0. Any other answer is overridden by Reiner's remote
    detonation threat: compliance is forced and loyalty is clamped back to >= 90.0.

    Returns:
        The outcome, or None if stance is invalid.
    """
    canonical = _normalize_stance(stance)
    if canonical is None:
        logger.warning("Ignoring invalid stance %r for Act III-A node '%s'", stance, ACT3A_ORDER_NODE_ID)
        return None

    forced = canonical != "loyal"
    story = _as_story(story_manager)
    if story is None:
        loyalty_after = ACT3A_MIN_LOYALTY if forced else ACT3A_ORDER_LOYAL_LOYALTY
    else:
        story.loyalty = _clamp_zealot(story.loyalty) if forced else ACT3A_ORDER_LOYAL_LOYALTY
        loyalty_after = story.loyalty
        story.extra[ACT3A_ORDER_EXTRA_KEY] = ACT3A_ORDER_FORCED if forced else ACT3A_ORDER_LOYAL
        story.save_campaign_state()

    logger.info("Act III-A order resolved: stance=%s forced=%s loyalty=%.1f", canonical, forced, loyalty_after)
    return Act3AOrderOutcome(
        stance=canonical,
        forced_compliance=forced,
        loyalty_after=loyalty_after,
        reiner_response=ACT3A_DETONATION_THREAT if forced else "",
    )


def resolve_act3a_trench_strike(
    story_manager: Optional[StoryManager],
    ground_support_manager: Optional["GroundSupportManager"] = None,
    mission_controller: Optional[MissionController] = None,
    comms_hud: Optional["CommsHUD"] = None,
) -> Act3ATrenchStrikeOutcome:
    """Execute Order Vermilion-Nine: the 500kg strike that purges Viper Squad.

    Every Helldiver still alive is downed via GroundSupportManager.apply_scripted_casualty().
    Without a ground support manager all four are assumed alive. The purge is recorded in
    StoryManager.total_casualties directly (not via on_helldiver_death(), which would cost
    loyalty), loyalty is clamped to >= 90.0 so the OBEDIENCE_PURGE branch is preserved, and
    the campaign advances to Sortie 6A. A second call only re-applies the loyalty clamp
    (already_resolved=True).

    Wiring (Sub-Issue 5, #77) decides when to call this: on the trench-node choice or on the
    player's actual 500kg release. MissionController/CampaignSortieSession still clamp
    sorties to the linear 1-4 registry, so routing current_sortie 5/6 to the Act III
    configs is part of that wiring.
    """
    story = _as_story(story_manager)
    gsm = _as_ground_support(ground_support_manager)
    trench_position = get_viper_trench_position(gsm)

    if story is not None and story.extra.get(VIPER_SQUAD_PURGED_EXTRA_KEY) is True:
        logger.info("Act III-A trench strike already resolved; ignoring repeat call")
        # A trench-node choice recorded after the strike may have lowered loyalty again.
        clamped = _clamp_zealot(story.loyalty)
        if clamped != story.loyalty:
            story.loyalty = clamped
            story.save_campaign_state()
        return Act3ATrenchStrikeOutcome(
            purged_callsigns=VIPER_SQUAD_CALLSIGNS,
            newly_killed=0,
            already_resolved=True,
            trench_position=trench_position,
            loyalty_after=story.loyalty,
            final_words=ACT3A_APEX_FINAL_WORDS,
            commendation=ACT3A_REINER_COMMENDATION,
            objective=SORTIE5A_RETURN_OBJECTIVE,
        )

    if gsm is None:
        newly_killed = VIPER_SQUAD_SIZE
    else:
        newly_killed = sum(1 for index in VIPER_SQUAD_INDICES if gsm.apply_scripted_casualty(index))
        # The purge is a scripted squad wipe; on_squad_wipe() (-8.0) would flip the branch.
        mark_wipe = getattr(gsm, "mark_squad_wipe_reported", None)
        if callable(mark_wipe):
            mark_wipe()

    if story is None:
        loyalty_after = ACT3A_MIN_LOYALTY
    else:
        story.total_casualties += newly_killed
        story.loyalty = _clamp_zealot(story.loyalty)
        loyalty_after = story.loyalty
        story.extra[VIPER_SQUAD_PURGED_EXTRA_KEY] = True
        story.extra[ACT3A_OUTCOME_EXTRA_KEY] = {"newly_killed": newly_killed, "squad_size": VIPER_SQUAD_SIZE}
        story.advance_sortie(act=ACT3_NUM, sortie=SORTIE6A_NUM)

    if isinstance(mission_controller, MissionController):
        mission_controller.set_active_objective_text(SORTIE5A_RETURN_OBJECTIVE)

    if comms_hud is not None:
        comms_hud.trigger_callout(ACT3A_REINER_SPEAKER, ACT3A_REINER_COMMENDATION, portrait=None)

    logger.info("Act III-A trench strike resolved: newly_killed=%d loyalty=%.1f", newly_killed, loyalty_after)
    return Act3ATrenchStrikeOutcome(
        purged_callsigns=VIPER_SQUAD_CALLSIGNS,
        newly_killed=newly_killed,
        already_resolved=False,
        trench_position=trench_position,
        loyalty_after=loyalty_after,
        final_words=ACT3A_APEX_FINAL_WORDS,
        commendation=ACT3A_REINER_COMMENDATION,
        objective=SORTIE5A_RETURN_OBJECTIVE,
    )


def resolve_act3a_choice(
    node_id: str,
    stance: str,
    story_manager: Optional[StoryManager],
    ground_support_manager: Optional["GroundSupportManager"] = None,
    mission_controller: Optional[MissionController] = None,
    comms_hud: Optional["CommsHUD"] = None,
) -> Optional[str]:
    """Route a recorded Act III-A choice to its effect.

    Returns:
        The HUD objective text that follows the choice, or None if node_id is not an
        Act III-A node or the stance is invalid.
    """
    if isinstance(node_id, bool) or not isinstance(node_id, str):
        return None
    clean_id = node_id.strip()
    if clean_id == ACT3A_ORDER_NODE_ID:
        outcome = resolve_act3a_order_choice(stance, story_manager)
        return SORTIE5A_INITIAL_OBJECTIVE if outcome is not None else None
    if clean_id == SORTIE5A_TRENCH_NODE_ID:
        if _normalize_stance(stance) is None:
            logger.warning("Ignoring invalid stance %r for Act III-A node '%s'", stance, clean_id)
            return None
        return resolve_act3a_trench_strike(
            story_manager, ground_support_manager, mission_controller, comms_hud
        ).objective
    return None


# -----------------------------------------------------------------------------
# Scene 3A.2 & Sortie 6A cinematic and epilogue
# -----------------------------------------------------------------------------

ACT3A_ENDING_TITLE: str = "THE PATH OF BLIND OBEDIENCE"
ACT3A_SEQUENCE_TITLE: str = "ACT III-A: " + ACT3A_ENDING_TITLE
# Full throttle for the terminal dive; mirrors eagle1.app.game.PLAYER_MAX_SPEED (asserted in tests).
ACT3A_DIVE_THROTTLE: float = 7.0
ACT3A_SORTIES_COMPLETED: int = SORTIE6A_NUM
ACT3A_PILOT_STATUS: str = "KIA - TERMINAL DIVE"
ACT3A_CLONE_GREETING: str = "Greetings, Eagle-1! We are Viper Squad! Ready to spill oil for Super Earth!"
ACT3A_ORTIZ_LINE: str = "Don't look at me, Val. Just don't look at me."
ACT3A_MEDAL_LINE: str = (
    "You have proven that loyalty is stronger than sentimentality. Tomorrow, you fly again."
)
ACT3A_VAL_FINAL_LINE: str = "No, Karl. For the first time in my life... I'm right on target."
ACT3A_MINISTRY_OBITUARY_LINES: Tuple[str, ...] = (
    "Flight Lieutenant Val died in the line of duty.",
    "Her sacrifice was deemed 100% compliant with Super Earth Liberty Guidelines.",
    "Her replacement will arrive tomorrow at 0600 hours.",
)

_ECHO_COLOR: Tuple[int, int, int] = theme.TEXT_MUTED
_ALERT_COLOR: Tuple[int, int, int] = theme.DANGER


def _sub(start: float, end: float, speaker: str, text: str, color: Optional[Tuple[int, int, int]] = None) -> CinematicSubtitle:
    """Build a subtitle; color defaults to the player's standard subtitle color."""
    if color is None:
        return CinematicSubtitle(start, end, speaker, text)
    return CinematicSubtitle(start, end, speaker, text, color)


def build_act3a_cinematic_sequence() -> CinematicSequence:
    """Return the Act III-A cutscene: trench impact, hangar clone interlude and terminal dive."""
    keyframes = (
        CinematicKeyframe(
            keyframe_id="act3a_trench_lock",
            duration=5.0,
            scene_type=CINEMATIC_SCENE_TRENCH_STRIKE,
            title_caption="SORTIE 5A // ORDER VERMILION-NINE",
            camera_start=(0.0, -120.0, 1.0),
            camera_end=(0.0, -60.0, 1.15),
            audio_cue="radio_squelch",
            subtitles=(
                _sub(0.6, 2.6, 'Viper-2 "Braker"', "Hey... Eagle? Your targeting laser is painting our trench."),
                _sub(2.7, 4.5, 'Viper-2 "Braker"', "Val? Why is the targeting reticle on us? Val, abort! ABORT!"),
            ),
        ),
        CinematicKeyframe(
            keyframe_id="act3a_trench_impact",
            duration=7.0,
            scene_type=CINEMATIC_SCENE_TRENCH_STRIKE,
            camera_start=(0.0, -200.0, 1.0),
            camera_end=(0.0, 60.0, 1.8),
            fade_out=1.0,
            audio_cue="explosion",
            subtitles=(
                _sub(0.5, 2.3, 'Viper-1 "Apex"', ACT3A_APEX_FINAL_WORDS),
                _sub(2.6, 4.2, "Val", "Target... neutralized. Sector clean."),
                _sub(4.3, 6.0, ACT3A_REINER_SPEAKER, ACT3A_REINER_COMMENDATION),
            ),
        ),
        CinematicKeyframe(
            keyframe_id="act3a_hangar_clones",
            duration=6.0,
            scene_type=CINEMATIC_SCENE_HANGAR_CLONES,
            title_caption="SCENE 3A.2 // THE NEW FACES IN THE HANGAR",
            camera_start=(-80.0, 0.0, 1.0),
            camera_end=(80.0, 0.0, 1.1),
            audio_cue="hangar_ambience",
            subtitles=(
                _sub(1.0, 5.4, "New Helldiver", ACT3A_CLONE_GREETING),
            ),
        ),
        CinematicKeyframe(
            keyframe_id="act3a_hangar_medal",
            duration=7.0,
            scene_type=CINEMATIC_SCENE_HANGAR_CLONES,
            title_caption="MEDAL OF DEMOCRATIC PURITY",
            camera_start=(0.0, 0.0, 1.1),
            camera_end=(0.0, -20.0, 1.3),
            audio_cue="ceremony_fanfare",
            subtitles=(
                _sub(0.6, 3.0, "Chief Ortiz", ACT3A_ORTIZ_LINE, _ECHO_COLOR),
                _sub(3.2, 6.4, "Officer Reiner", ACT3A_MEDAL_LINE),
            ),
        ),
        CinematicKeyframe(
            keyframe_id="act3a_dive_hallucinations",
            duration=9.0,
            scene_type=CINEMATIC_SCENE_SUICIDE_DIVE,
            title_caption="SORTIE 6A // THE TERMINAL DIVE",
            camera_start=(0.0, 0.0, 1.0),
            camera_end=(0.0, 40.0, 1.1),
            audio_cue="radio_chatter",
            subtitles=(
                _sub(0.6, 2.4, 'Viper-3 "Ghost" (echo)', "...why is the reticle on us, Val...?", _ECHO_COLOR),
                _sub(2.5, 4.3, 'Viper-4 "Doc" (echo)', "...I had to use field solder... he was nineteen...", _ECHO_COLOR),
                _sub(4.4, 6.0, 'Viper-1 "Apex" (echo)', "..." + ACT3A_APEX_FINAL_WORDS, _ECHO_COLOR),
                _sub(6.2, 8.6, "Val", "I killed them. For a flag. For a medal. For nothing."),
            ),
        ),
        CinematicKeyframe(
            keyframe_id="act3a_dive_pull_up",
            duration=7.0,
            scene_type=CINEMATIC_SCENE_SUICIDE_DIVE,
            camera_start=(0.0, 40.0, 1.1),
            camera_end=(0.0, 120.0, 1.4),
            audio_cue="low_health",
            subtitles=(
                _sub(0.4, 2.0, "", "WARNING: ALTITUDE PULL UP - TERRAIN AHEAD", _ALERT_COLOR),
                _sub(2.1, 4.2, "Officer Reiner", "Eagle-1, you are off course. Correct heading to Sector 9 immediately."),
                _sub(4.4, 6.6, "Val", ACT3A_VAL_FINAL_LINE),
            ),
        ),
        CinematicKeyframe(
            keyframe_id="act3a_terminal_dive",
            duration=4.0,
            scene_type=CINEMATIC_SCENE_SUICIDE_DIVE,
            title_caption=f"THROTTLE {ACT3A_DIVE_THROTTLE:.1f} // VERTICAL DIVE",
            camera_start=(0.0, 120.0, 1.4),
            camera_end=(0.0, 300.0, 2.6),
            fade_in=0.2,
            fade_out=0.0,
            audio_cue="reentry_burn",
        ),
        CinematicKeyframe(
            keyframe_id="act3a_white_flash",
            duration=2.5,
            scene_type=CINEMATIC_SCENE_WHITE_FLASH,
            fade_in=0.0,
            fade_out=2.0,
            audio_cue="stop_music",
        ),
        CinematicKeyframe(
            keyframe_id="act3a_ministry_notice",
            duration=9.0,
            scene_type=CINEMATIC_SCENE_EPILOGUE_CARD,
            title_caption="MINISTRY OF TRUTH // OFFICIAL NOTICE",
            fade_in=1.0,
            fade_out=1.0,
            subtitles=(
                _sub(1.0, 3.4, "", ACT3A_MINISTRY_OBITUARY_LINES[0]),
                _sub(3.5, 5.9, "", ACT3A_MINISTRY_OBITUARY_LINES[1]),
                _sub(6.0, 8.0, "", ACT3A_MINISTRY_OBITUARY_LINES[2]),
            ),
        ),
    )
    return CinematicSequence(
        sequence_id=ACT3A_SEQUENCE_ID,
        ending_branch=BRANCH_OBEDIENCE_PURGE,
        title=ACT3A_SEQUENCE_TITLE,
        keyframes=keyframes,
        epilogue_lines=ACT3A_MINISTRY_OBITUARY_LINES,
    )


def build_act3a_epilogue_stats(story_manager: Optional[StoryManager]) -> EpilogueSummaryStats:
    """Return the Act III-A epilogue statistics with the Ministry of Truth obituary.

    Without a StoryManager the canonical path is assumed: loyalty 100.0 and the four
    purged Viper Squad members as casualties.
    """
    story = story_manager if isinstance(story_manager, StoryManager) else None
    return EpilogueSummaryStats(
        ending_branch=BRANCH_OBEDIENCE_PURGE,
        ending_title=ACT3A_ENDING_TITLE,
        final_loyalty=story.loyalty if story is not None else MAX_LOYALTY,
        total_casualties=story.total_casualties if story is not None else VIPER_SQUAD_SIZE,
        sorties_completed=ACT3A_SORTIES_COMPLETED,
        pilot_status=ACT3A_PILOT_STATUS,
        epilogue_lines=ACT3A_MINISTRY_OBITUARY_LINES,
    )
