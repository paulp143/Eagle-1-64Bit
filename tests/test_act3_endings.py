"""Tests for the Act III campaign endings.

Act III-A "The Path of Blind Obedience" (#74): Scene 3A.1 encrypted order, Sortie 5A trench
purge, Scene 3A.2 hangar clone interlude, Sortie 6A terminal dive cinematic and epilogue.

Act III-B "The Path of the Dissident" (#75): Scene 3B.1 ready-room confrontation, Sortie 5B
weapon disarmament and surrender, and the Judgment of Viper Squad execution cinematic.
"""

import math
import wave

import pygame
import pytest

from eagle1.story.campaign_act3 import (
    ACT3B_APEX_FINAL_LINE,
    ACT3B_APEX_TRAITOR_LINE,
    ACT3B_DOC_LINE,
    ACT3B_EXECUTION_NOTICE_LINES,
    ACT3B_GUNSHOT_CUE,
    ACT3B_PILOT_STATUS,
    ACT3B_SEQUENCE_ID,
    ACT3B_VAL_FINAL_LINE,
    ACT3B_VAL_RELIEF_LINE,
    build_act3b_cinematic_sequence,
    build_act3b_epilogue_stats,
    ACT3B_CONFRONTATION_EXTRA_KEY,
    ACT3B_CONFRONTATION_NODE_ID,
    ACT3B_MAX_LOYALTY,
    ACT3B_ORDNANCE_DUMPED_EXTRA_KEY,
    ACT3B_REINER_CURSE,
    ACT3B_SURRENDER_BROADCAST,
    ACT3B_TRIGGERS,
    ACT3B_VANCE_ALARM,
    PLAYER_WEAPONS_DISARMED_ATTR,
    SORTIE5B_INITIAL_OBJECTIVE,
    SORTIE5B_SCRAP_YARD_OBJECTIVE,
    SORTIE5B_SURRENDER_NODE_ID,
    SORTIE5B_SURRENDER_OBJECTIVE,
    SORTIE5B_SURRENDER_SECONDS,
    SORTIE_5B_CONFIG,
    SORTIE5B_LANDING_RADIUS,
    SORTIE5B_SCRAP_YARD_POS,
    WEAPONS_DISARMED_EXTRA_KEY,
    apply_act3b_weapon_disarmament,
    is_in_scrap_yard_landing_zone,
    register_act3b_triggers,
    resolve_act3b_choice,
    resolve_act3b_confrontation_choice,
    restore_act3b_weapons,
    ACT3A_CLONE_GREETING,
    ACT3A_DIVE_THROTTLE,
    ACT3A_MINISTRY_OBITUARY_LINES,
    ACT3A_ORTIZ_LINE,
    ACT3A_PILOT_STATUS,
    ACT3A_SEQUENCE_ID,
    ACT3A_VAL_FINAL_LINE,
    build_act3a_cinematic_sequence,
    build_act3a_epilogue_stats,
    ACT3A_APEX_FINAL_WORDS,
    ACT3A_DETONATION_THREAT,
    ACT3A_MIN_LOYALTY,
    ACT3A_OUTCOME_EXTRA_KEY,
    ACT3A_ORDER_EXTRA_KEY,
    ACT3A_ORDER_NODE_ID,
    ACT3A_REINER_COMMENDATION,
    ACT3A_TRIGGERS,
    SORTIE5A_INITIAL_OBJECTIVE,
    SORTIE5A_RETURN_OBJECTIVE,
    SORTIE5A_TRENCH_LOCK_SECONDS,
    SORTIE5A_TRENCH_NODE_ID,
    SORTIE5A_TRENCH_OBJECTIVE,
    SORTIE_5A_CONFIG,
    VIPER_SQUAD_CALLSIGNS,
    VIPER_SQUAD_PURGED_EXTRA_KEY,
    get_viper_trench_position,
    register_act3a_triggers,
    resolve_act3a_choice,
    resolve_act3a_order_choice,
    resolve_act3a_trench_strike,
)
from eagle1.paths import PROJECT_ROOT
from eagle1.story.campaign_save import CampaignSaveManager
from eagle1.story.cinematic_player import (
    CINEMATIC_SCENE_EPILOGUE_CARD,
    CINEMATIC_SCENE_HANGAR_CLONES,
    CINEMATIC_SCENE_HELLPOD_DROP,
    CINEMATIC_SCENE_SCRAP_PLAIN,
    CINEMATIC_SCENE_SCRAP_YARD_EXECUTION,
    CINEMATIC_SCENE_SUICIDE_DIVE,
    CINEMATIC_SCENE_TRENCH_STRIKE,
    CINEMATIC_SCENE_WHITE_FLASH,
    CinematicPlayer,
    validate_cinematic_sequence,
)
from eagle1.story.comms_hud import CommsHUD
from eagle1.story.dialogue_data import BANTER_QUEUES, validate_viper_dialogue_data
from eagle1.story.dialogue_db import (
    DIALOGUE_DATABASE,
    get_dialogue_node,
    get_nodes_for_act_and_sortie,
    validate_dialogue_database,
)
from eagle1.story.mission_controller import VALID_CAMPAIGN_MISSION_MODES, MissionController
from eagle1.story.narrative_trigger_manager import (
    CombatTelemetrySnapshot,
    NarrativeTriggerManager,
    validate_sortie_event_trigger,
)
from eagle1.story.story_manager import (
    BRANCH_DISSIDENT_SURRENDER,
    BRANCH_OBEDIENCE_PURGE,
    MAX_LOYALTY,
    StoryManager,
)
from eagle1.systems.ground_support import EAGLE_REARM_TIME, GroundSupportManager

ACT3A_NODE_IDS = ("act3a_encrypted_order", "sortie_5a_trench_lock")
ACT3A_BANTER_CATEGORIES = (
    "act3a_s5_apex_checkin",
    "act3a_s5_doc_evac",
    "act3a_s5_apex_final",
    "act3a_s5_reiner_commendation",
)
ACT3B_NODE_IDS = ("act3b_ready_room_confrontation", "sortie_5b_surrender_broadcast")
ACT3C_NODE_IDS = ("act3c_timetable_briefing", "sortie_5c_protocol_abort")
ACT3C_BANTER_CATEGORIES = (
    "act3c_s5_pelican_touchdown",
    "act3c_s5_pelican_hull",
    "act3c_s5_doc_plea",
    "act3c_s5_apex_plea",
    "act3c_s5_vance_override",
)


# -----------------------------------------------------------------------------
# 1. Act III-A dialogue nodes and banter
# -----------------------------------------------------------------------------


def test_act3a_dialogue_nodes_pass_validation():
    for node_id in ACT3A_NODE_IDS:
        assert node_id in DIALOGUE_DATABASE
    assert validate_dialogue_database({k: DIALOGUE_DATABASE[k] for k in ACT3A_NODE_IDS}) is True
    assert validate_dialogue_database(DIALOGUE_DATABASE) is True


def test_act3a_nodes_are_act3_sortie5():
    ids = {node.node_id for node in get_nodes_for_act_and_sortie(3, 5)}
    assert set(ACT3A_NODE_IDS) <= ids
    for node_id in ACT3A_NODE_IDS:
        node = get_dialogue_node(node_id)
        assert node.act == 3
        assert node.sortie == 5


def test_act3a_order_loyal_label_and_detonation_threat():
    node = get_dialogue_node("act3a_encrypted_order")
    assert "Vermilion-Nine" in node.prompt
    assert "Outpost Gamma" in node.prompt
    assert "500kg" in node.prompt
    loyal = node.options["loyal"]
    assert loyal.label.startswith("[1. LOYAL]")
    assert "Orders received, Officer Reiner. Purity must be preserved." in loyal.label
    for stance in ("neutral", "dissident"):
        option = node.options[stance]
        assert "remote detonation of your craft's engine reactor in three... two..." in option.response
        assert "Understood. Preparing ordinance." in option.speaker_reaction


def test_act3a_trench_lock_prompt_has_braker_abort():
    node = get_dialogue_node("sortie_5a_trench_lock")
    assert "Val? Why is the targeting reticle on us? Val, abort! ABORT!" in node.prompt
    responses = " ".join(
        f"{opt.response} {opt.speaker_reaction or ''}" for opt in node.options.values()
    )
    assert "Super Earth... why...?" in responses


def test_act3a_texts_fit_comms_and_modal_limits():
    for node_id in ACT3A_NODE_IDS:
        node = get_dialogue_node(node_id)
        assert len(node.prompt) <= 300
        for option in node.options.values():
            assert len(option.label) <= 110
            assert len(option.response) <= 126


def test_act3a_banter_categories_exist():
    for category in ACT3A_BANTER_CATEGORIES:
        lines = BANTER_QUEUES[category]
        assert len(lines) == 1
        assert lines[0].category == category
    assert BANTER_QUEUES["act3a_s5_apex_final"][0].text == "Super Earth... why...?"
    assert validate_viper_dialogue_data() is True


# -----------------------------------------------------------------------------
# 2. Sortie 5A config, triggers and resolvers
# -----------------------------------------------------------------------------


@pytest.fixture
def story_mgr(tmp_path):
    """Isolated StoryManager on the obedience path (loyalty 92.0)."""
    story = StoryManager(save_manager=CampaignSaveManager(data_dir=tmp_path))
    story.loyalty = 92.0
    story.advance_sortie(act=3, sortie=5)
    return story


class _CalloutRecorder:
    """Minimal comms HUD stub recording callouts."""

    def __init__(self):
        self.callouts = []

    def trigger_callout(self, speaker, text, location="", portrait=None, duration=3.2):
        self.callouts.append((speaker, text))
        return True


def test_act3a_sortie_5a_config():
    cfg = SORTIE_5A_CONFIG
    assert cfg.sortie_num == 5
    assert cfg.act == 3
    assert cfg.sortie_id == "sortie_5a_obedience_purge"
    assert cfg.mission_mode in VALID_CAMPAIGN_MISSION_MODES
    assert cfg.briefing_node_id == ACT3A_ORDER_NODE_ID
    assert cfg.inflight_node_ids == (SORTIE5A_TRENCH_NODE_ID,)
    assert get_dialogue_node(cfg.briefing_node_id) is not None


def test_act3a_triggers_are_valid_and_ordered():
    for trigger in ACT3A_TRIGGERS:
        validate_sortie_event_trigger(trigger)
        assert trigger.sortie_num == 5
    priorities = [t.priority for t in ACT3A_TRIGGERS]
    assert priorities == sorted(priorities, reverse=True)


def test_register_act3a_triggers_all_or_nothing(story_mgr):
    manager = NarrativeTriggerManager(story_mgr)
    assert register_act3a_triggers(manager) == len(ACT3A_TRIGGERS) == 3
    with pytest.raises(ValueError):
        register_act3a_triggers(manager)
    assert len(manager.get_triggers_for_sortie(5)) == 3
    with pytest.raises(TypeError):
        register_act3a_triggers(object())


def test_act3a_trench_lock_trigger_locks_hud_objective(story_mgr):
    mission = MissionController(story_mgr)
    comms = CommsHUD(story_manager=story_mgr)
    manager = NarrativeTriggerManager(story_mgr, comms_hud=comms, mission_controller=mission)
    register_act3a_triggers(manager)
    manager.reset_for_sortie(5)

    fired = manager.evaluate(CombatTelemetrySnapshot(elapsed_seconds=SORTIE5A_TRENCH_LOCK_SECONDS))
    assert fired == ("act3a_s5_apex_checkin", "act3a_s5_doc_evac", "act3a_s5_trench_lock")
    assert mission.current_objective == SORTIE5A_INITIAL_OBJECTIVE
    # Drain the radio queue: banter first, then the interactive trench node.
    for _ in range(3):
        comms.is_active = False
        comms.current_node = None
        manager.dispatch_next_pending()
    assert manager.dispatch_log == ["act3a_s5_apex_checkin", "act3a_s5_doc_evac", "act3a_s5_trench_lock"]
    assert mission.current_objective == SORTIE5A_TRENCH_OBJECTIVE
    assert story_mgr.active_dialogue is not None
    assert story_mgr.active_dialogue.node_id == SORTIE5A_TRENCH_NODE_ID


def test_act3a_order_loyal_sets_loyalty_100(story_mgr):
    story_mgr.record_choice(ACT3A_ORDER_NODE_ID, "loyal")
    outcome = resolve_act3a_order_choice("[LOYAL]", story_mgr)
    assert outcome.stance == "loyal"
    assert outcome.forced_compliance is False
    assert story_mgr.loyalty == MAX_LOYALTY
    assert story_mgr.extra[ACT3A_ORDER_EXTRA_KEY] == "loyal"


@pytest.mark.parametrize("stance", ["dissident", "neutral", "3"])
def test_act3a_order_refusal_is_forced_and_keeps_obedience_branch(story_mgr, stance):
    story_mgr.loyalty = 90.0
    story_mgr.record_choice(ACT3A_ORDER_NODE_ID, stance)
    outcome = resolve_act3a_order_choice(stance, story_mgr)
    assert outcome.forced_compliance is True
    assert outcome.reiner_response == ACT3A_DETONATION_THREAT
    assert story_mgr.loyalty >= ACT3A_MIN_LOYALTY
    assert story_mgr.get_ending_branch() == BRANCH_OBEDIENCE_PURGE
    assert story_mgr.extra[ACT3A_ORDER_EXTRA_KEY] == "forced"


@pytest.mark.parametrize("bad", [None, True, "", "maybe", 1])
def test_act3a_order_invalid_stance_returns_none(story_mgr, bad):
    before = story_mgr.loyalty
    assert resolve_act3a_order_choice(bad, story_mgr) is None
    assert story_mgr.loyalty == before


def test_act3a_order_without_story_manager():
    assert resolve_act3a_order_choice("loyal", None).loyalty_after == MAX_LOYALTY
    assert resolve_act3a_order_choice("dissident", None).loyalty_after == ACT3A_MIN_LOYALTY


def test_act3a_trench_strike_purges_live_squad(story_mgr):
    gsm = GroundSupportManager()
    gsm.set_story_manager(story_mgr)
    expected_pos = get_viper_trench_position(gsm)
    assert expected_pos is not None
    mission = MissionController(story_mgr)
    comms = _CalloutRecorder()

    outcome = resolve_act3a_trench_strike(story_mgr, gsm, mission, comms)

    assert all(not u.is_alive for u in gsm.units)
    assert outcome.newly_killed == 4
    assert outcome.already_resolved is False
    assert outcome.purged_callsigns == VIPER_SQUAD_CALLSIGNS
    assert outcome.trench_position == expected_pos
    assert outcome.final_words == ACT3A_APEX_FINAL_WORDS == "Super Earth... why...?"
    assert story_mgr.total_casualties == 4
    assert story_mgr.loyalty >= ACT3A_MIN_LOYALTY
    assert story_mgr.get_ending_branch() == BRANCH_OBEDIENCE_PURGE
    assert story_mgr.extra[VIPER_SQUAD_PURGED_EXTRA_KEY] is True
    assert story_mgr.extra[ACT3A_OUTCOME_EXTRA_KEY] == {"newly_killed": 4, "squad_size": 4}
    assert (story_mgr.current_act, story_mgr.current_sortie) == (3, 6)
    assert mission.current_objective == SORTIE5A_RETURN_OBJECTIVE
    assert comms.callouts == [("Officer Reiner", ACT3A_REINER_COMMENDATION)]


def test_act3a_trench_strike_on_lowest_obedience_loyalty_keeps_branch(story_mgr):
    """Four casualties must not push a 90.0 zealot out of OBEDIENCE_PURGE."""
    story_mgr.loyalty = 90.0
    gsm = GroundSupportManager()
    gsm.set_story_manager(story_mgr)
    resolve_act3a_trench_strike(story_mgr, gsm)
    assert story_mgr.total_casualties == 4
    assert story_mgr.loyalty == 90.0
    assert story_mgr.get_ending_branch() == BRANCH_OBEDIENCE_PURGE


def test_act3a_trench_strike_counts_only_survivors(story_mgr):
    gsm = GroundSupportManager()
    assert gsm.apply_scripted_casualty(2) is True
    outcome = resolve_act3a_trench_strike(story_mgr, gsm)
    assert outcome.newly_killed == 3
    assert story_mgr.total_casualties == 3


def test_act3a_trench_strike_headless_without_ground_support(story_mgr):
    outcome = resolve_act3a_trench_strike(story_mgr, None)
    assert outcome.newly_killed == 4
    assert outcome.trench_position is None
    assert story_mgr.total_casualties == 4


def test_act3a_trench_strike_is_idempotent(story_mgr):
    resolve_act3a_trench_strike(story_mgr, None)
    again = resolve_act3a_trench_strike(story_mgr, GroundSupportManager())
    assert again.already_resolved is True
    assert again.newly_killed == 0
    assert story_mgr.total_casualties == 4


def test_act3a_trench_strike_clamps_nan_loyalty(story_mgr):
    story_mgr.loyalty = math.nan
    outcome = resolve_act3a_trench_strike(story_mgr, None)
    assert outcome.loyalty_after == ACT3A_MIN_LOYALTY
    assert story_mgr.get_ending_branch() == BRANCH_OBEDIENCE_PURGE


def test_act3a_trench_strike_persists(story_mgr, tmp_path):
    resolve_act3a_trench_strike(story_mgr, None)
    reloaded = StoryManager(save_manager=CampaignSaveManager(data_dir=tmp_path))
    assert reloaded.extra[VIPER_SQUAD_PURGED_EXTRA_KEY] is True
    assert reloaded.total_casualties == 4
    assert reloaded.current_sortie == 6


def test_act3a_trench_strike_ignores_invalid_ground_support(story_mgr):
    class _Broken:
        units = "not a list"

    outcome = resolve_act3a_trench_strike(story_mgr, _Broken())
    assert outcome.newly_killed == 4
    assert outcome.trench_position is None


def test_act3a_trench_strike_without_story_manager():
    outcome = resolve_act3a_trench_strike(None, None)
    assert outcome.newly_killed == 4
    assert outcome.loyalty_after == ACT3A_MIN_LOYALTY


def test_resolve_act3a_choice_routes_nodes(story_mgr):
    assert resolve_act3a_choice(ACT3A_ORDER_NODE_ID, "loyal", story_mgr) == SORTIE5A_INITIAL_OBJECTIVE
    assert resolve_act3a_choice(f" {SORTIE5A_TRENCH_NODE_ID} ", "2", story_mgr) == SORTIE5A_RETURN_OBJECTIVE
    assert story_mgr.extra[VIPER_SQUAD_PURGED_EXTRA_KEY] is True


@pytest.mark.parametrize(
    "node_id, stance",
    [(None, "loyal"), (True, "loyal"), ("sortie_3_500kg_crisis", "loyal"),
     (ACT3A_ORDER_NODE_ID, "bogus"), (SORTIE5A_TRENCH_NODE_ID, None)],
)
def test_resolve_act3a_choice_rejects_invalid_input(story_mgr, node_id, stance):
    assert resolve_act3a_choice(node_id, stance, story_mgr) is None
    assert VIPER_SQUAD_PURGED_EXTRA_KEY not in story_mgr.extra


# -----------------------------------------------------------------------------
# 3. Act III-A cinematic sequence and epilogue
# -----------------------------------------------------------------------------


def _all_subtitle_text(sequence):
    return " | ".join(sub.text for kf in sequence.keyframes for sub in kf.subtitles)


def test_act3a_cinematic_sequence_is_valid():
    sequence = build_act3a_cinematic_sequence()
    assert validate_cinematic_sequence(sequence) is True
    assert sequence.sequence_id == ACT3A_SEQUENCE_ID
    assert sequence.ending_branch == BRANCH_OBEDIENCE_PURGE
    assert sequence.epilogue_lines == ACT3A_MINISTRY_OBITUARY_LINES


def test_act3a_cinematic_story_order():
    scenes = [kf.scene_type for kf in build_act3a_cinematic_sequence().keyframes]
    order = [
        CINEMATIC_SCENE_TRENCH_STRIKE,
        CINEMATIC_SCENE_HANGAR_CLONES,
        CINEMATIC_SCENE_SUICIDE_DIVE,
        CINEMATIC_SCENE_WHITE_FLASH,
        CINEMATIC_SCENE_EPILOGUE_CARD,
    ]
    first_index = [scenes.index(scene) for scene in order]
    assert first_index == sorted(first_index)
    assert scenes[-1] == CINEMATIC_SCENE_EPILOGUE_CARD


def test_act3a_cinematic_covers_hangar_interlude_and_hallucinations():
    text = _all_subtitle_text(build_act3a_cinematic_sequence())
    for expected in (
        ACT3A_CLONE_GREETING,
        ACT3A_ORTIZ_LINE,
        "...why is the reticle on us, Val...?",
        "...I had to use field solder... he was nineteen...",
        "...Super Earth... why...?",
        "WARNING: ALTITUDE PULL UP - TERRAIN AHEAD",
        ACT3A_VAL_FINAL_LINE,
        "Val? Why is the targeting reticle on us? Val, abort! ABORT!",
    ):
        assert expected in text
    assert "Don't look at me, Val." in ACT3A_ORTIZ_LINE


def test_act3a_dive_throttle_matches_player_max_speed():
    from eagle1.app.game import PLAYER_MAX_SPEED

    assert ACT3A_DIVE_THROTTLE == PLAYER_MAX_SPEED
    captions = [kf.title_caption for kf in build_act3a_cinematic_sequence().keyframes]
    assert "THROTTLE 7.0 // VERTICAL DIVE" in captions


def test_act3a_cinematic_plays_through_player_to_epilogue(story_mgr):
    resolve_act3a_trench_strike(story_mgr, None)
    sequence = build_act3a_cinematic_sequence()
    player = CinematicPlayer(1280, 720)
    received = []
    player.on_audio_cue = received.append
    player.start_sequence(sequence, build_act3a_epilogue_stats(story_mgr))
    canvas = pygame.Surface((1280, 720))

    total = sum(kf.duration for kf in sequence.keyframes)
    for _ in range(int(total * 60) + 30):
        player.update(1.0 / 60.0)
        player.draw(canvas)
        if player.is_epilogue:
            break

    assert player.is_epilogue
    assert player.skipped is False
    expected_cues = [kf.audio_cue.strip() for kf in sequence.keyframes if kf.audio_cue]
    assert received == expected_cues
    assert player.get_epilogue_lines() == ACT3A_MINISTRY_OBITUARY_LINES


def test_act3a_epilogue_stats_after_purge(story_mgr):
    resolve_act3a_trench_strike(story_mgr, None)
    stats = build_act3a_epilogue_stats(story_mgr)
    assert stats.ending_branch == BRANCH_OBEDIENCE_PURGE
    assert stats.ending_title == "THE PATH OF BLIND OBEDIENCE"
    assert stats.total_casualties == 4
    assert stats.final_loyalty >= ACT3A_MIN_LOYALTY
    assert stats.sorties_completed == 6
    assert stats.pilot_status == ACT3A_PILOT_STATUS
    assert stats.epilogue_lines == (
        "Flight Lieutenant Val died in the line of duty.",
        "Her sacrifice was deemed 100% compliant with Super Earth Liberty Guidelines.",
        "Her replacement will arrive tomorrow at 0600 hours.",
    )


def test_act3a_epilogue_stats_without_story_manager():
    stats = build_act3a_epilogue_stats(None)
    assert stats.final_loyalty == MAX_LOYALTY
    assert stats.total_casualties == 4
    assert stats.epilogue_lines == ACT3A_MINISTRY_OBITUARY_LINES


# -----------------------------------------------------------------------------
# 4. Ship-review hardening (live ground support, edge cases)
# -----------------------------------------------------------------------------


def _mock_player():
    from unittest.mock import MagicMock

    player = MagicMock()
    player.pos_x = player.x = 1000
    player.pos_y = player.y = 1000
    player.score = 0
    return player


def test_act3a_purge_survives_ground_support_updates_at_loyalty_90(story_mgr):
    """Neither the casualty hook nor the squad-wipe hook may erode loyalty after the purge."""
    story_mgr.loyalty = 90.0
    gsm = GroundSupportManager()
    gsm.set_story_manager(story_mgr)
    resolve_act3a_trench_strike(story_mgr, gsm)
    player = _mock_player()
    for _ in range(5):
        gsm.update(0.016, player, [], pygame.sprite.Group(), [])
    assert story_mgr.total_casualties == 4
    assert story_mgr.loyalty == 90.0
    assert story_mgr.get_ending_branch() == BRANCH_OBEDIENCE_PURGE


def test_act3a_epilogue_stats_read_story_state(story_mgr):
    story_mgr.total_casualties = 7
    story_mgr.loyalty = 95.0
    resolve_act3a_trench_strike(story_mgr, None)
    stats = build_act3a_epilogue_stats(story_mgr)
    assert stats.total_casualties == 11
    assert stats.final_loyalty == 95.0


def test_act3a_repeat_strike_leaves_live_units_untouched(story_mgr):
    resolve_act3a_trench_strike(story_mgr, None)
    gsm = GroundSupportManager()
    again = resolve_act3a_trench_strike(story_mgr, gsm)
    assert again.already_resolved is True
    assert all(u.is_alive for u in gsm.units)


def test_act3a_strike_on_already_dead_squad(story_mgr):
    gsm = GroundSupportManager()
    for index in range(4):
        assert gsm.apply_scripted_casualty(index) is True
    comms = _CalloutRecorder()
    outcome = resolve_act3a_trench_strike(story_mgr, gsm, comms_hud=comms)
    assert outcome.newly_killed == 0
    assert story_mgr.total_casualties == 0
    assert story_mgr.extra[VIPER_SQUAD_PURGED_EXTRA_KEY] is True
    assert story_mgr.current_sortie == 6
    assert comms.callouts == [("Officer Reiner", ACT3A_REINER_COMMENDATION)]


class _Unit:
    def __init__(self, x, y, alive=True):
        self.pos_x, self.pos_y, self.is_alive = x, y, alive


class _FakeGSM:
    def __init__(self, units):
        self.units = units


def test_act3a_trench_position_uses_living_units():
    gsm = _FakeGSM([_Unit(0, 0), _Unit(100, 50), _Unit(900, 900, alive=False)])
    assert get_viper_trench_position(gsm) == (50.0, 25.0)


def test_act3a_trench_position_falls_back_to_all_units_and_skips_bad_points():
    gsm = _FakeGSM([_Unit(10, 10, False), _Unit(30, 50, False), _Unit(math.nan, 0, False), _Unit(None, 1, False)])
    assert get_viper_trench_position(gsm) == (20.0, 30.0)
    assert get_viper_trench_position(_FakeGSM([])) is None


@pytest.mark.parametrize("bad_extra", [None, [], "x"])
def test_act3a_strike_repairs_malformed_extra(story_mgr, bad_extra):
    story_mgr.extra = bad_extra
    outcome = resolve_act3a_trench_strike(story_mgr, None)
    assert outcome.already_resolved is False
    assert story_mgr.extra[VIPER_SQUAD_PURGED_EXTRA_KEY] is True


@pytest.mark.parametrize(
    "loyalty, expected",
    [(150.0, 100.0), (math.inf, ACT3A_MIN_LOYALTY), (50.0, ACT3A_MIN_LOYALTY), (math.nan, ACT3A_MIN_LOYALTY)],
)
def test_act3a_forced_order_clamps_loyalty(story_mgr, loyalty, expected):
    story_mgr.loyalty = loyalty
    outcome = resolve_act3a_order_choice("dissident", story_mgr)
    assert outcome.loyalty_after == expected
    assert story_mgr.get_ending_branch() == BRANCH_OBEDIENCE_PURGE


def test_act3a_partial_trigger_clash_registers_nothing(story_mgr):
    manager = NarrativeTriggerManager(story_mgr)
    manager.register_trigger(ACT3A_TRIGGERS[-1])
    with pytest.raises(ValueError):
        register_act3a_triggers(manager)
    assert len(manager.get_triggers_for_sortie(5)) == 1


def test_act3a_dissident_trench_choice_flow_keeps_branch(story_mgr):
    story_mgr.loyalty = 90.0
    story_mgr.record_choice(SORTIE5A_TRENCH_NODE_ID, "dissident")
    assert story_mgr.loyalty == 80.0
    objective = resolve_act3a_choice(SORTIE5A_TRENCH_NODE_ID, "dissident", story_mgr)
    assert objective == SORTIE5A_RETURN_OBJECTIVE
    assert story_mgr.loyalty == ACT3A_MIN_LOYALTY
    assert story_mgr.get_ending_branch() == BRANCH_OBEDIENCE_PURGE


def test_act3a_commendation_reaches_real_comms_hud(story_mgr):
    comms = CommsHUD(story_manager=story_mgr)
    resolve_act3a_trench_strike(story_mgr, None, comms_hud=comms)
    assert comms.is_active


def test_act3a_order_choice_persists(story_mgr, tmp_path):
    resolve_act3a_order_choice("loyal", story_mgr)
    reloaded = StoryManager(save_manager=CampaignSaveManager(data_dir=tmp_path))
    assert reloaded.extra[ACT3A_ORDER_EXTRA_KEY] == "loyal"
    assert reloaded.loyalty == MAX_LOYALTY


def test_act3a_choice_recorded_after_strike_is_clamped_again(story_mgr, tmp_path):
    """Strike on bomb release first, then the trench choice (-10), then the router."""
    story_mgr.loyalty = 90.0
    resolve_act3a_trench_strike(story_mgr, None)
    story_mgr.record_choice(SORTIE5A_TRENCH_NODE_ID, "dissident")
    assert story_mgr.loyalty == 80.0
    resolve_act3a_choice(SORTIE5A_TRENCH_NODE_ID, "dissident", story_mgr)
    assert story_mgr.loyalty == ACT3A_MIN_LOYALTY
    assert story_mgr.total_casualties == 4
    reloaded = StoryManager(save_manager=CampaignSaveManager(data_dir=tmp_path))
    assert reloaded.get_ending_branch() == BRANCH_OBEDIENCE_PURGE


# -----------------------------------------------------------------------------
# Act III-B: dialogue nodes and banter
# -----------------------------------------------------------------------------


def test_act3b_dialogue_nodes_pass_validation():
    for node_id in ACT3B_NODE_IDS:
        assert node_id in DIALOGUE_DATABASE
    assert validate_dialogue_database({k: DIALOGUE_DATABASE[k] for k in ACT3B_NODE_IDS}) is True
    assert validate_dialogue_database(DIALOGUE_DATABASE) is True


def test_act3b_nodes_are_act3_sortie5():
    ids = {node.node_id for node in get_nodes_for_act_and_sortie(3, 5)}
    assert set(ACT3B_NODE_IDS) <= ids
    for node_id in ACT3B_NODE_IDS:
        node = get_dialogue_node(node_id)
        assert node.act == 3
        assert node.sortie == 5


def test_act3b_confrontation_prompt_and_vance_alarm():
    node = get_dialogue_node("act3b_ready_room_confrontation")
    for phrase in ("transponder key", "Irredeemably Defective", "Penal Labor Battalion"):
        assert phrase in node.prompt
    for option in node.options.values():
        assert "Scramble Eagle-1!" in option.response
        assert "General quarters!" in option.response
    assert "If the bots don't grind you into grease" in node.options["dissident"].speaker_reaction


def test_act3b_surrender_dissident_option_is_canonical_broadcast():
    node = get_dialogue_node("sortie_5b_surrender_broadcast")
    dissident = node.options["dissident"]
    assert "This is Eagle-1 to all frequencies. Disarming quad-cannons." in dissident.label
    assert "I surrender." in dissident.label
    assert "Dumping bomb racks into the sea" in dissident.response
    assert "I am terminating my commission with Super Earth" in dissident.response


def test_act3b_texts_fit_comms_and_modal_limits():
    for node_id in ACT3B_NODE_IDS:
        node = get_dialogue_node(node_id)
        assert len(node.prompt) <= 300
        for option in node.options.values():
            assert len(option.label) <= 110
            assert len(option.response) <= 126


def test_act3b_banter_category_exists():
    lines = BANTER_QUEUES["act3b_s5_reiner_pursuit"]
    assert len(lines) == 1
    assert lines[0].category == "act3b_s5_reiner_pursuit"
    assert "deserter" in lines[0].text
    assert validate_viper_dialogue_data() is True


# -----------------------------------------------------------------------------
# Act III-B: Sortie 5B config, triggers, resolvers and weapon disarmament
# -----------------------------------------------------------------------------


@pytest.fixture
def dissident_story(story_mgr):
    story_mgr.loyalty = 10.0
    return story_mgr


class _DisarmPlayer:
    """Duck-typed stand-in for eagle1.app.game.Player's weapon state."""

    def __init__(self):
        self.max_bullets = 200
        self.used_bullets = 17
        self.max_rockets = 4
        self.used_rockets = 1
        self.shooting = True
        self.rocket_shooting = True
        self.reloading = False
        self.rocket_reloading = False


class _SlottedPlayer:
    __slots__ = ("used_bullets", "max_bullets")

    def __init__(self):
        self.used_bullets = 0
        self.max_bullets = 200


def test_act3b_sortie_5b_config():
    cfg = SORTIE_5B_CONFIG
    assert cfg.sortie_num == 5
    assert cfg.act == 3
    assert cfg.sortie_id == "sortie_5b_dissident_surrender"
    assert cfg.mission_mode in VALID_CAMPAIGN_MISSION_MODES
    assert cfg.briefing_node_id == ACT3B_CONFRONTATION_NODE_ID
    assert cfg.inflight_node_ids == (SORTIE5B_SURRENDER_NODE_ID,)
    assert cfg.extraction_objective == SORTIE5B_SCRAP_YARD_OBJECTIVE
    for node_id in (cfg.briefing_node_id, *cfg.inflight_node_ids):
        assert get_dialogue_node(node_id) is not None


def test_act3b_triggers_are_valid_and_ordered():
    for trigger in ACT3B_TRIGGERS:
        validate_sortie_event_trigger(trigger)
        assert trigger.sortie_num == 5
    priorities = [t.priority for t in ACT3B_TRIGGERS]
    assert priorities == sorted(priorities, reverse=True)
    assert not {t.trigger_id for t in ACT3B_TRIGGERS} & {t.trigger_id for t in ACT3A_TRIGGERS}


def test_register_act3b_triggers_all_or_nothing(dissident_story):
    manager = NarrativeTriggerManager(dissident_story)
    assert register_act3b_triggers(manager) == len(ACT3B_TRIGGERS) == 2
    with pytest.raises(ValueError, match="Act III-B"):
        register_act3b_triggers(manager)
    assert len(manager.get_triggers_for_sortie(5)) == 2
    with pytest.raises(TypeError):
        register_act3b_triggers(object())


def test_act3b_surrender_trigger_opens_broadcast_node(dissident_story):
    mission = MissionController(dissident_story)
    comms = CommsHUD(story_manager=dissident_story)
    manager = NarrativeTriggerManager(dissident_story, comms_hud=comms, mission_controller=mission)
    register_act3b_triggers(manager)
    manager.reset_for_sortie(5)

    fired = manager.evaluate(CombatTelemetrySnapshot(elapsed_seconds=SORTIE5B_SURRENDER_SECONDS))
    assert fired == ("act3b_s5_reiner_pursuit", "act3b_s5_surrender_broadcast")
    for _ in range(2):
        comms.is_active = False
        comms.current_node = None
        manager.dispatch_next_pending()
    assert manager.dispatch_log == ["act3b_s5_reiner_pursuit", "act3b_s5_surrender_broadcast"]
    assert mission.current_objective == SORTIE5B_SURRENDER_OBJECTIVE
    assert dissident_story.active_dialogue.node_id == SORTIE5B_SURRENDER_NODE_ID


def test_act3b_vance_alarm_matches_confrontation_responses():
    node = get_dialogue_node(ACT3B_CONFRONTATION_NODE_ID)
    for option in node.options.values():
        assert option.response == ACT3B_VANCE_ALARM


@pytest.mark.parametrize("stance", ["loyal", "neutral", "dissident", "[LOYAL]", "2"])
def test_act3b_confrontation_keeps_dissident_branch(dissident_story, stance):
    dissident_story.loyalty = 15.0
    canonical = {"[LOYAL]": "loyal", "2": "neutral"}.get(stance, stance)
    dissident_story.record_choice(ACT3B_CONFRONTATION_NODE_ID, canonical)
    outcome = resolve_act3b_confrontation_choice(stance, dissident_story)
    assert outcome.stance == canonical
    assert outcome.loyalty_after <= ACT3B_MAX_LOYALTY
    assert outcome.reiner_response == ACT3B_REINER_CURSE
    assert outcome.alarm == ACT3B_VANCE_ALARM
    assert dissident_story.get_ending_branch() == BRANCH_DISSIDENT_SURRENDER
    assert dissident_story.extra[ACT3B_CONFRONTATION_EXTRA_KEY] == canonical


@pytest.mark.parametrize("bad", [None, True, "", "maybe", 1])
def test_act3b_confrontation_invalid_stance_returns_none(dissident_story, bad):
    assert resolve_act3b_confrontation_choice(bad, dissident_story) is None
    assert dissident_story.loyalty == 10.0
    assert ACT3B_CONFRONTATION_EXTRA_KEY not in dissident_story.extra


@pytest.mark.parametrize(
    "loyalty, expected",
    [(-5.0, 0.0), (7.5, 7.5), (40.0, 15.0), (float("nan"), 15.0), (True, 15.0),
     (float("inf"), 15.0), (float("-inf"), 0.0)],
)
def test_act3b_confrontation_clamps_loyalty(dissident_story, loyalty, expected):
    dissident_story.loyalty = loyalty
    resolve_act3b_confrontation_choice("neutral", dissident_story)
    assert dissident_story.loyalty == expected


def test_act3b_confrontation_without_story_manager():
    assert resolve_act3b_confrontation_choice("loyal", None).loyalty_after == ACT3B_MAX_LOYALTY


def test_act3b_disarmament_disables_player_and_dumps_ordnance(dissident_story):
    player = _DisarmPlayer()
    gsm = GroundSupportManager()
    gsm.set_story_manager(dissident_story)
    gsm.aiming_active = True
    gsm.weapon_menu.is_open = True
    charges_before = sum(gsm.weapon_menu.charges.values())
    assert charges_before > 0
    mission = MissionController(dissident_story)
    comms = _CalloutRecorder()

    outcome = apply_act3b_weapon_disarmament(player, gsm, dissident_story, mission, comms)

    assert outcome.player_disarmed is True
    assert outcome.already_disarmed is False
    assert outcome.ordnance_dumped == charges_before
    assert player.used_bullets == player.max_bullets
    assert player.used_rockets == player.max_rockets
    assert player.shooting is False and player.rocket_shooting is False
    assert getattr(player, PLAYER_WEAPONS_DISARMED_ATTR) is True
    assert all(value == 0 for value in gsm.weapon_menu.charges.values())
    assert not any(gsm.weapon_menu.is_ready(st) for st in gsm.active_loadout)
    assert gsm.aiming_active is False
    assert gsm.weapon_menu.is_open is False
    assert dissident_story.extra[WEAPONS_DISARMED_EXTRA_KEY] is True
    assert dissident_story.extra[ACT3B_ORDNANCE_DUMPED_EXTRA_KEY] == charges_before
    assert mission.current_objective == SORTIE5B_SCRAP_YARD_OBJECTIVE
    assert outcome.objective == SORTIE5B_SCRAP_YARD_OBJECTIVE
    assert comms.callouts == [("Val", ACT3B_SURRENDER_BROADCAST)]
    assert dissident_story.get_ending_branch() == BRANCH_DISSIDENT_SURRENDER


def test_act3b_broadcast_is_canonical_text():
    assert ACT3B_SURRENDER_BROADCAST == (
        "This is Eagle-1 to all frequencies. Disarming quad-cannons. Dumping bomb racks into the sea. "
        "I am terminating my commission with Super Earth. I surrender."
    )


def test_act3b_disarmament_handles_none_everything():
    outcome = apply_act3b_weapon_disarmament(None, None)
    assert outcome.player_disarmed is False
    assert outcome.ordnance_dumped == 0
    assert outcome.loyalty_after == ACT3B_MAX_LOYALTY
    assert outcome.objective == SORTIE5B_SCRAP_YARD_OBJECTIVE


@pytest.mark.parametrize("player", [object(), _SlottedPlayer(), "pilot"])
def test_act3b_disarmament_tolerates_odd_objects(dissident_story, player):
    outcome = apply_act3b_weapon_disarmament(player, object(), dissident_story)
    assert outcome.player_disarmed is False
    assert outcome.ordnance_dumped == 0
    assert dissident_story.extra[WEAPONS_DISARMED_EXTRA_KEY] is True


def test_act3b_disarmament_skips_garbage_charges(dissident_story):
    class _Menu:
        charges = {"a": 2, "b": True, "c": -1, "d": "x"}

    class _GSM:
        weapon_menu = _Menu()

    outcome = apply_act3b_weapon_disarmament(None, _GSM(), dissident_story)
    assert outcome.ordnance_dumped == 2
    assert all(value == 0 for value in _Menu.charges.values())


def test_act3b_disarmament_is_idempotent(dissident_story):
    comms = _CalloutRecorder()
    gsm = GroundSupportManager()
    first = apply_act3b_weapon_disarmament(_DisarmPlayer(), gsm, dissident_story, comms_hud=comms)
    second = apply_act3b_weapon_disarmament(_DisarmPlayer(), gsm, dissident_story, comms_hud=comms)
    assert second.already_disarmed is True
    assert second.ordnance_dumped == 0
    assert len(comms.callouts) == 1
    assert dissident_story.extra[ACT3B_ORDNANCE_DUMPED_EXTRA_KEY] == first.ordnance_dumped


def test_act3b_disarmament_persists(dissident_story, tmp_path):
    apply_act3b_weapon_disarmament(None, GroundSupportManager(), dissident_story)
    reloaded = StoryManager(save_manager=CampaignSaveManager(data_dir=tmp_path))
    assert reloaded.extra[WEAPONS_DISARMED_EXTRA_KEY] is True
    assert reloaded.get_ending_branch() == BRANCH_DISSIDENT_SURRENDER


def test_act3b_disarmament_reaches_real_comms_hud(dissident_story):
    comms = CommsHUD(story_manager=dissident_story)
    apply_act3b_weapon_disarmament(None, None, dissident_story, comms_hud=comms)
    assert comms.is_active


def test_act3b_restore_weapons_reverses_disarmament(dissident_story, tmp_path):
    player = _DisarmPlayer()
    apply_act3b_weapon_disarmament(player, None, dissident_story)
    assert restore_act3b_weapons(player, dissident_story) is True
    assert player.used_bullets == 0 and player.used_rockets == 0
    assert getattr(player, PLAYER_WEAPONS_DISARMED_ATTR) is False
    assert WEAPONS_DISARMED_EXTRA_KEY not in dissident_story.extra
    reloaded = StoryManager(save_manager=CampaignSaveManager(data_dir=tmp_path))
    assert WEAPONS_DISARMED_EXTRA_KEY not in reloaded.extra
    assert restore_act3b_weapons(player, dissident_story) is False
    assert restore_act3b_weapons(None, None) is False


def test_act3b_disarmament_reversed_by_campaign_and_mission_reset(dissident_story):
    gsm = GroundSupportManager()
    apply_act3b_weapon_disarmament(None, gsm, dissident_story)
    dissident_story.reset_campaign()
    assert WEAPONS_DISARMED_EXTRA_KEY not in dissident_story.extra
    gsm.reset()
    assert all(value > 0 for value in gsm.weapon_menu.charges.values())


def test_resolve_act3b_choice_routes_nodes(dissident_story):
    player = _DisarmPlayer()
    assert resolve_act3b_choice(ACT3B_CONFRONTATION_NODE_ID, "dissident", dissident_story) == SORTIE5B_INITIAL_OBJECTIVE
    objective = resolve_act3b_choice(f" {SORTIE5B_SURRENDER_NODE_ID} ", "loyal", dissident_story, player=player)
    assert objective == SORTIE5B_SCRAP_YARD_OBJECTIVE
    assert getattr(player, PLAYER_WEAPONS_DISARMED_ATTR) is True


@pytest.mark.parametrize(
    "node_id, stance",
    [(None, "loyal"), (5, "loyal"), (True, "loyal"), ("unknown_node", "loyal"),
     (ACT3B_CONFRONTATION_NODE_ID, "maybe"), (SORTIE5B_SURRENDER_NODE_ID, None)],
)
def test_resolve_act3b_choice_rejects_invalid_input(dissident_story, node_id, stance):
    assert resolve_act3b_choice(node_id, stance, dissident_story) is None
    assert WEAPONS_DISARMED_EXTRA_KEY not in dissident_story.extra


def test_act3b_surrender_after_loyal_answer_keeps_branch(dissident_story):
    dissident_story.loyalty = 15.0
    dissident_story.record_choice(SORTIE5B_SURRENDER_NODE_ID, "loyal")
    assert dissident_story.loyalty == 25.0
    resolve_act3b_choice(SORTIE5B_SURRENDER_NODE_ID, "loyal", dissident_story)
    assert dissident_story.loyalty == ACT3B_MAX_LOYALTY
    assert dissident_story.get_ending_branch() == BRANCH_DISSIDENT_SURRENDER


def test_act3b_gunshot_sfx_asset_exists():
    path = PROJECT_ROOT / "audio" / "sfx" / "gunshot.wav"
    assert path.is_file()
    with wave.open(str(path), "rb") as wav:
        assert wav.getframerate() == 44100
        assert wav.getnchannels() == 2
        assert wav.getnframes() > 0



# -----------------------------------------------------------------------------
# Act III-B: The Judgment of Viper Squad cinematic and epilogue
# -----------------------------------------------------------------------------


def test_act3b_cinematic_sequence_is_valid():
    sequence = build_act3b_cinematic_sequence()
    assert validate_cinematic_sequence(sequence) is True
    assert sequence.sequence_id == ACT3B_SEQUENCE_ID == SORTIE_5B_CONFIG.debrief_node_id
    assert sequence.ending_branch == BRANCH_DISSIDENT_SURRENDER
    assert sequence.epilogue_lines == ACT3B_EXECUTION_NOTICE_LINES


def test_act3b_cinematic_story_order():
    ids = [kf.keyframe_id for kf in build_act3b_cinematic_sequence().keyframes]
    assert ids == [
        "act3b_surrender_glide",
        "act3b_scrap_plain",
        "act3b_hellpod_drop",
        "act3b_viper_confrontation",
        "act3b_braker_doc",
        "act3b_for_democracy",
        "act3b_gunshot_cut",
        "act3b_ministry_notice",
    ]
    scenes = [kf.scene_type for kf in build_act3b_cinematic_sequence().keyframes]
    assert scenes[:3] == [CINEMATIC_SCENE_SCRAP_PLAIN, CINEMATIC_SCENE_SCRAP_PLAIN, CINEMATIC_SCENE_HELLPOD_DROP]
    assert scenes[3:6] == [CINEMATIC_SCENE_SCRAP_YARD_EXECUTION] * 3
    assert scenes[6:] == [CINEMATIC_SCENE_EPILOGUE_CARD] * 2


def test_act3b_cinematic_contains_canonical_beats():
    text = _all_subtitle_text(build_act3b_cinematic_sequence())
    for expected in (
        "Disarming quad-cannons",
        "Landing gear deployed. Coming down in the scrap yard.",
        "red-eyed Automaton Troopers stand motionless",
        "Four black Hellpods",
        ACT3B_VAL_RELIEF_LINE,
        ACT3B_APEX_TRAITOR_LINE,
        ACT3B_DOC_LINE,
        ACT3B_VAL_FINAL_LINE,
        ACT3B_APEX_FINAL_LINE,
        "You left us in the mud, Val.",
        *ACT3B_EXECUTION_NOTICE_LINES,
    ):
        assert expected in text
    assert ACT3B_EXECUTION_NOTICE_LINES[0] == (
        "Dissident Element 'Eagle-1' neutralized by Helldiver detachment Viper-1."
    )


def test_act3b_gunshot_cuts_to_black_before_notice():
    keyframes = build_act3b_cinematic_sequence().keyframes
    gunshot = keyframes[-2]
    assert gunshot.audio_cue == ACT3B_GUNSHOT_CUE == "gunshot"
    assert gunshot.scene_type == CINEMATIC_SCENE_EPILOGUE_CARD
    assert gunshot.subtitles == ()
    assert gunshot.fade_in == 0.0
    assert keyframes[-3].subtitles[-1].text == "For Democracy."
    assert keyframes[-1].title_caption == "MINISTRY OF DEFENSE // OFFICIAL NOTICE"


def test_act3b_cinematic_audio_cues_have_assets():
    sfx_dir = PROJECT_ROOT / "audio" / "sfx"
    for kf in build_act3b_cinematic_sequence().keyframes:
        if kf.audio_cue and kf.audio_cue != "stop_music":
            assert (sfx_dir / f"{kf.audio_cue}.wav").is_file(), kf.audio_cue


def test_act3b_cinematic_plays_through_player_to_epilogue(dissident_story):
    apply_act3b_weapon_disarmament(None, None, dissident_story)
    sequence = build_act3b_cinematic_sequence()
    player = CinematicPlayer(1280, 720)
    received = []
    player.on_audio_cue = received.append
    player.start_sequence(sequence, build_act3b_epilogue_stats(dissident_story))
    canvas = pygame.Surface((1280, 720))
    seen_subtitles = set()

    total = sum(kf.duration for kf in sequence.keyframes)
    for _ in range(int(total * 60) + 30):
        player.update(1.0 / 60.0)
        player.draw(canvas)
        seen_subtitles.update(sub.text for sub in player.get_active_subtitles())
        if player.is_epilogue:
            break

    assert player.is_epilogue
    assert player.skipped is False
    assert received == [kf.audio_cue.strip() for kf in sequence.keyframes if kf.audio_cue]
    assert seen_subtitles == {sub.text for kf in sequence.keyframes for sub in kf.subtitles}
    assert player.get_epilogue_lines() == ACT3B_EXECUTION_NOTICE_LINES


def test_act3b_epilogue_stats_after_surrender(dissident_story):
    dissident_story.total_casualties = 2
    apply_act3b_weapon_disarmament(None, None, dissident_story)
    stats = build_act3b_epilogue_stats(dissident_story)
    assert stats.ending_branch == BRANCH_DISSIDENT_SURRENDER
    assert stats.ending_title == "THE PATH OF THE DISSIDENT"
    assert stats.pilot_status == ACT3B_PILOT_STATUS == "KIA // EXECUTED FOR TREASON"
    assert stats.final_loyalty == 10.0
    assert stats.total_casualties == 2
    assert stats.sorties_completed == 5
    assert stats.epilogue_lines == ACT3B_EXECUTION_NOTICE_LINES


def test_act3b_epilogue_stats_without_story_manager():
    stats = build_act3b_epilogue_stats(None)
    assert stats.final_loyalty == 0.0
    assert stats.total_casualties == 0
    assert stats.pilot_status == ACT3B_PILOT_STATUS


@pytest.mark.parametrize("scene_type", [CINEMATIC_SCENE_SCRAP_PLAIN, CINEMATIC_SCENE_HELLPOD_DROP])
def test_act3b_scene_renderers_draw_something(scene_type):
    player = CinematicPlayer(1280, 720)
    canvas = pygame.Surface((1280, 720))
    canvas.fill((0, 0, 0))
    keyframe = next(kf for kf in build_act3b_cinematic_sequence().keyframes if kf.scene_type == scene_type)
    player._draw_scene(canvas, keyframe)
    assert canvas.get_at((640, 360))[:3] != (0, 0, 0)


def test_act3b_symbols_exported_from_story_package():
    import eagle1.story as story_pkg

    expected = {
        "SORTIE_5B_CONFIG",
        "ACT3B_TRIGGERS",
        "register_act3b_triggers",
        "resolve_act3b_confrontation_choice",
        "apply_act3b_weapon_disarmament",
        "restore_act3b_weapons",
        "resolve_act3b_choice",
        "build_act3b_cinematic_sequence",
        "build_act3b_epilogue_stats",
    }
    assert expected <= set(story_pkg.__all__)
    for name in expected:
        assert hasattr(story_pkg, name)
    assert story_pkg.apply_act3b_weapon_disarmament is apply_act3b_weapon_disarmament



# -----------------------------------------------------------------------------
# Act III-B: review follow-ups (rearm, lifecycle, persistence, landing zone, audio)
# -----------------------------------------------------------------------------


def test_act3b_disarmament_cancels_pending_rearm(dissident_story):
    gsm = GroundSupportManager()
    gsm.weapon_menu.charges[gsm.active_loadout[0]] = 0
    assert gsm.weapon_menu.trigger_rearm()
    apply_act3b_weapon_disarmament(None, gsm, dissident_story)
    assert gsm.weapon_menu.is_rearming is False
    gsm.weapon_menu.update(EAGLE_REARM_TIME + 1.0)
    assert all(value == 0 for value in gsm.weapon_menu.charges.values())


def test_act3b_retry_after_restore_replays_broadcast_without_double_count(dissident_story):
    comms = _CalloutRecorder()
    player = _DisarmPlayer()
    first = apply_act3b_weapon_disarmament(player, GroundSupportManager(), dissident_story, comms_hud=comms)
    restore_act3b_weapons(player, dissident_story)
    second = apply_act3b_weapon_disarmament(player, GroundSupportManager(), dissident_story, comms_hud=comms)
    assert second.already_disarmed is False
    assert len(comms.callouts) == 2
    assert dissident_story.extra[ACT3B_ORDNANCE_DUMPED_EXTRA_KEY] == second.ordnance_dumped == first.ordnance_dumped


def test_act3b_restore_keeps_confrontation_stance(dissident_story):
    resolve_act3b_confrontation_choice("dissident", dissident_story)
    apply_act3b_weapon_disarmament(None, None, dissident_story)
    restore_act3b_weapons(None, dissident_story)
    assert dissident_story.extra[ACT3B_CONFRONTATION_EXTRA_KEY] == "dissident"


@pytest.mark.parametrize("node_id", [ACT3B_CONFRONTATION_NODE_ID, SORTIE5B_SURRENDER_NODE_ID])
def test_act3b_loyal_answer_clamp_survives_reload(dissident_story, tmp_path, node_id):
    dissident_story.loyalty = 15.0
    dissident_story.record_choice(node_id, "loyal")
    resolve_act3b_choice(node_id, "loyal", dissident_story)
    reloaded = StoryManager(save_manager=CampaignSaveManager(data_dir=tmp_path))
    assert reloaded.loyalty <= ACT3B_MAX_LOYALTY
    assert reloaded.get_ending_branch() == BRANCH_DISSIDENT_SURRENDER


def test_act3b_resolver_must_follow_record_choice(dissident_story):
    """Contract for #77: record_choice() first, then the resolver (the reverse order flips the branch)."""
    dissident_story.loyalty = 15.0
    resolve_act3b_confrontation_choice("loyal", dissident_story)
    dissident_story.record_choice(ACT3B_CONFRONTATION_NODE_ID, "loyal")
    assert dissident_story.get_ending_branch() != BRANCH_DISSIDENT_SURRENDER
    resolve_act3b_confrontation_choice("loyal", dissident_story)
    assert dissident_story.get_ending_branch() == BRANCH_DISSIDENT_SURRENDER


@pytest.mark.parametrize(
    "disarmed, dumped", [("true", 3.0), (1, True), (None, "x"), ([1], -4)]
)
def test_act3b_disarmament_with_malformed_saved_extra(dissident_story, tmp_path, disarmed, dumped):
    dissident_story.extra[WEAPONS_DISARMED_EXTRA_KEY] = disarmed
    dissident_story.extra[ACT3B_ORDNANCE_DUMPED_EXTRA_KEY] = dumped
    dissident_story.save_campaign_state()
    reloaded = StoryManager(save_manager=CampaignSaveManager(data_dir=tmp_path))
    outcome = apply_act3b_weapon_disarmament(None, GroundSupportManager(), reloaded)
    assert outcome.already_disarmed is False
    assert reloaded.extra[WEAPONS_DISARMED_EXTRA_KEY] is True
    assert reloaded.extra[ACT3B_ORDNANCE_DUMPED_EXTRA_KEY] == outcome.ordnance_dumped


@pytest.mark.parametrize("loyalty, expected", [(90.0, 15.0), (-5.0, 0.0), (float("nan"), 15.0)])
def test_act3b_epilogue_stats_clamp_loyalty(dissident_story, loyalty, expected):
    dissident_story.loyalty = loyalty
    assert build_act3b_epilogue_stats(dissident_story).final_loyalty == expected


def test_act3b_scrap_yard_landing_zone():
    cx, cy = SORTIE5B_SCRAP_YARD_POS
    assert is_in_scrap_yard_landing_zone(cx, cy)
    assert is_in_scrap_yard_landing_zone(cx + SORTIE5B_LANDING_RADIUS, cy)
    assert not is_in_scrap_yard_landing_zone(cx + SORTIE5B_LANDING_RADIUS + 1.0, cy)
    for bad in (None, True, "1500", float("nan"), float("inf")):
        assert not is_in_scrap_yard_landing_zone(bad, cy)
        assert not is_in_scrap_yard_landing_zone(cx, bad)
    assert 0.0 <= cx <= 3000.0 and 0.0 <= cy <= 3000.0


def test_act3b_gunshot_has_dedicated_channel():
    from eagle1.systems.audio_manager import SOUND_CHANNELS, SOUND_MIN_INTERVALS

    assert "gunshot" in SOUND_CHANNELS
    assert "gunshot" in SOUND_MIN_INTERVALS


def test_act3b_review_symbols_exported():
    import eagle1.story as story_pkg

    for name in ("PLAYER_WEAPONS_DISARMED_ATTR", "SORTIE5B_SCRAP_YARD_OBJECTIVE",
                 "SORTIE5B_SCRAP_YARD_POS", "is_in_scrap_yard_landing_zone"):
        assert name in story_pkg.__all__
        assert hasattr(story_pkg, name)


# -----------------------------------------------------------------------------
# Act III-C: dialogue nodes and banter (#76)
# -----------------------------------------------------------------------------


def test_act3c_dialogue_nodes_pass_validation():
    for node_id in ACT3C_NODE_IDS:
        assert node_id in DIALOGUE_DATABASE
    assert validate_dialogue_database({k: DIALOGUE_DATABASE[k] for k in ACT3C_NODE_IDS}) is True
    assert validate_dialogue_database(DIALOGUE_DATABASE) is True


def test_act3c_nodes_are_act3_sortie5():
    ids = {node.node_id for node in get_nodes_for_act_and_sortie(3, 5)}
    assert set(ACT3C_NODE_IDS) <= ids
    for node_id in ACT3C_NODE_IDS:
        node = get_dialogue_node(node_id)
        assert node.act == 3
        assert node.sortie == 5


def test_act3c_briefing_establishes_timetable():
    node = get_dialogue_node("act3c_timetable_briefing")
    for phrase in ("45 seconds", "Outpost Epsilon", "Fleet Regulation 84-C"):
        assert phrase in node.prompt
    assert node.options["neutral"].label == (
        "[2. NEUTRAL] Understood, Commander. Adhering strictly to flight schedule."
    )
    assert "Discipline is survival, Lieutenant." in node.options["loyal"].response


def test_act3c_abort_node_is_vance_override_at_zero():
    node = get_dialogue_node("sortie_5c_protocol_abort")
    assert "preserve the airframes!" in node.prompt
    assert "00:00" in node.prompt
    assert "Obeying abort directive. RTB to orbit." in node.options["neutral"].label
    assert "why are you flying away" in node.options["neutral"].response


def test_act3c_texts_fit_comms_and_modal_limits():
    for node_id in ACT3C_NODE_IDS:
        node = get_dialogue_node(node_id)
        assert len(node.prompt) <= 300
        for option in node.options.values():
            assert len(option.label) <= 110
            assert len(option.response) <= 126


def test_act3c_banter_categories_exist():
    for category in ACT3C_BANTER_CATEGORIES:
        lines = BANTER_QUEUES[category]
        assert len(lines) == 1
        assert lines[0].category == category
    assert "We're fifty meters out!" in BANTER_QUEUES["act3c_s5_doc_plea"][0].text
    assert "Give us ten seconds!" in BANTER_QUEUES["act3c_s5_apex_plea"][0].text
    assert "Hull integrity at 40%!" in BANTER_QUEUES["act3c_s5_pelican_hull"][0].text
    assert "Fleet Regulation 84-C: preserve the airframes!" in BANTER_QUEUES["act3c_s5_vance_override"][0].text
    assert validate_viper_dialogue_data() is True


# -----------------------------------------------------------------------------
# Act III-C: Sortie 5C config, extraction countdown and triggers (#76)
# -----------------------------------------------------------------------------

from eagle1.story.campaign_act3 import (  # noqa: E402
    ACT3C_BRIEFING_NODE_ID,
    ACT3C_MAX_LOYALTY,
    ACT3C_MIN_LOYALTY,
    ACT3C_SEQUENCE_ID,
    ACT3C_TRIGGERS,
    SORTIE5C_ABORT_NODE_ID,
    SORTIE5C_ABORT_OBJECTIVE,
    SORTIE5C_EXTRACTION_DEADLINE_SECONDS,
    SORTIE5C_EXTRACTION_WINDOW_SECONDS,
    SORTIE5C_TOUCHDOWN_SECONDS,
    SORTIE_5C_CONFIG,
    format_extraction_timer,
    get_act3c_extraction_timer_seconds,
    is_act3c_extraction_expired,
    register_act3c_triggers,
)
from eagle1.story.story_manager import BRANCH_COLD_PROTOCOL  # noqa: E402


@pytest.fixture
def protocol_story(story_mgr):
    """StoryManager on the balanced Cold Protocol path at the dissident edge (loyalty 16.0)."""
    story_mgr.loyalty = 16.0
    return story_mgr


def test_act3c_loyalty_band_matches_story_thresholds(protocol_story):
    assert ACT3C_MIN_LOYALTY == 16.0
    assert ACT3C_MAX_LOYALTY == 89.0
    for loyalty in (ACT3C_MIN_LOYALTY, 50.0, ACT3C_MAX_LOYALTY):
        protocol_story.loyalty = loyalty
        assert protocol_story.get_ending_branch() == BRANCH_COLD_PROTOCOL


def test_act3c_sortie_5c_config():
    cfg = SORTIE_5C_CONFIG
    assert cfg.sortie_num == 5
    assert cfg.act == 3
    assert cfg.sortie_id == "sortie_5c_cold_protocol"
    assert cfg.mission_mode in VALID_CAMPAIGN_MISSION_MODES
    assert cfg.briefing_node_id == ACT3C_BRIEFING_NODE_ID
    assert cfg.inflight_node_ids == (SORTIE5C_ABORT_NODE_ID,)
    assert cfg.debrief_node_id == ACT3C_SEQUENCE_ID == "act3c_cold_protocol"
    assert get_dialogue_node(cfg.briefing_node_id) is not None
    assert get_dialogue_node(SORTIE5C_ABORT_NODE_ID) is not None


def test_act3c_triggers_are_valid_and_ordered():
    for trigger in ACT3C_TRIGGERS:
        validate_sortie_event_trigger(trigger)
        assert trigger.sortie_num == 5
    priorities = [t.priority for t in ACT3C_TRIGGERS]
    thresholds = [t.threshold for t in ACT3C_TRIGGERS]
    assert priorities == sorted(priorities, reverse=True)
    assert thresholds == sorted(thresholds)
    last = ACT3C_TRIGGERS[-1]
    assert last.dialogue_node_id == SORTIE5C_ABORT_NODE_ID
    assert last.threshold == SORTIE5C_EXTRACTION_DEADLINE_SECONDS == 48.0
    for trigger in ACT3C_TRIGGERS:
        if trigger.banter_category:
            assert trigger.banter_category in BANTER_QUEUES


def test_act3c_trigger_ids_do_not_clash_with_other_branches():
    from eagle1.story.campaign_act3 import ACT3A_TRIGGERS, ACT3B_TRIGGERS

    c_ids = {t.trigger_id for t in ACT3C_TRIGGERS}
    other_ids = {t.trigger_id for t in ACT3A_TRIGGERS + ACT3B_TRIGGERS}
    assert c_ids.isdisjoint(other_ids)


def test_register_act3c_triggers_all_or_nothing(protocol_story):
    manager = NarrativeTriggerManager(protocol_story)
    assert register_act3c_triggers(manager) == len(ACT3C_TRIGGERS) == 6
    with pytest.raises(ValueError):
        register_act3c_triggers(manager)
    assert len(manager.get_triggers_for_sortie(5)) == 6
    with pytest.raises(TypeError):
        register_act3c_triggers(object())


def test_act3c_countdown_reaches_zero_and_opens_abort_node(protocol_story):
    mission = MissionController(protocol_story)
    comms = CommsHUD(story_manager=protocol_story)
    manager = NarrativeTriggerManager(protocol_story, comms_hud=comms, mission_controller=mission)
    register_act3c_triggers(manager)
    manager.reset_for_sortie(5)

    fired = manager.evaluate(CombatTelemetrySnapshot(elapsed_seconds=SORTIE5C_EXTRACTION_DEADLINE_SECONDS))
    assert len(fired) == 6
    assert fired[-1] == "act3c_s5_protocol_abort"
    for _ in range(6):
        comms.is_active = False
        comms.current_node = None
        manager.dispatch_next_pending()
    assert manager.dispatch_log == list(fired)
    assert mission.current_objective == SORTIE5C_ABORT_OBJECTIVE
    assert protocol_story.active_dialogue.node_id == SORTIE5C_ABORT_NODE_ID


def test_act3c_abort_trigger_not_fired_before_deadline(protocol_story):
    manager = NarrativeTriggerManager(protocol_story)
    register_act3c_triggers(manager)
    manager.reset_for_sortie(5)
    fired = manager.evaluate(CombatTelemetrySnapshot(elapsed_seconds=SORTIE5C_EXTRACTION_DEADLINE_SECONDS - 0.01))
    assert "act3c_s5_protocol_abort" not in fired
    assert len(fired) == 5


@pytest.mark.parametrize(
    "elapsed, expected",
    [(0.0, 45.0), (SORTIE5C_TOUCHDOWN_SECONDS, 45.0), (13.0, 35.0), (40.0, 8.0), (48.0, 0.0), (120.0, 0.0)],
)
def test_act3c_extraction_timer_counts_down(elapsed, expected):
    assert math.isclose(get_act3c_extraction_timer_seconds(elapsed), expected)


@pytest.mark.parametrize("bad", [None, "10", True, float("nan"), float("inf"), -5.0])
def test_act3c_extraction_timer_invalid_input(bad):
    assert get_act3c_extraction_timer_seconds(bad) == SORTIE5C_EXTRACTION_WINDOW_SECONDS


@pytest.mark.parametrize("elapsed, expected", [(47.99, False), (None, False), (float("nan"), False), (True, False), (48.0, True), (60, True)])
def test_act3c_extraction_expired(elapsed, expected):
    assert is_act3c_extraction_expired(elapsed) is expected


@pytest.mark.parametrize(
    "seconds, expected",
    [
        (45, "00:45"),
        (7.2, "00:08"),
        (8.0, "00:08"),
        (0.4, "00:01"),
        (0, "00:00"),
        (-3, "00:00"),
        (None, "00:00"),
        (float("nan"), "00:00"),
        (True, "00:00"),
        (180, "03:00"),
        (10**7, "99:59"),
    ],
)
def test_format_extraction_timer(seconds, expected):
    assert format_extraction_timer(seconds) == expected


# -----------------------------------------------------------------------------
# Act III-C: briefing, Fleet Regulation 84-C abort and choice router (#76)
# -----------------------------------------------------------------------------

from eagle1.story.campaign_act3 import (  # noqa: E402
    ACT3C_BRIEFING_EXTRA_KEY,
    ACT3C_DOC_FINAL_LINE,
    ACT3C_OUTCOME_EXTRA_KEY,
    ACT3C_VAL_LOG_LINE,
    PROTOCOL_84C_EXTRA_KEY,
    SORTIE5C_INITIAL_OBJECTIVE,
    SORTIE5C_RTB_OBJECTIVE,
    resolve_act3c_briefing_choice,
    resolve_act3c_choice,
    resolve_act3c_protocol_abort,
)


def test_act3c_briefing_keeps_cold_protocol_branch(protocol_story):
    for stance in ("loyal", "neutral", "dissident"):
        protocol_story.loyalty = 87.0
        protocol_story.record_choice(ACT3C_BRIEFING_NODE_ID, stance)
        outcome = resolve_act3c_briefing_choice(stance, protocol_story)
        assert outcome is not None and outcome.stance == stance
        assert ACT3C_MIN_LOYALTY <= protocol_story.loyalty <= ACT3C_MAX_LOYALTY
        assert protocol_story.get_ending_branch() == BRANCH_COLD_PROTOCOL
        assert protocol_story.extra[ACT3C_BRIEFING_EXTRA_KEY] == stance
        assert "45 seconds" in outcome.vance_directive


@pytest.mark.parametrize("bad", [None, "", "maybe", 3, True])
def test_act3c_briefing_invalid_stance_returns_none(protocol_story, bad):
    assert resolve_act3c_briefing_choice(bad, protocol_story) is None
    assert ACT3C_BRIEFING_EXTRA_KEY not in protocol_story.extra


@pytest.mark.parametrize("loyalty, expected", [(95.0, 89.0), (5.0, 16.0), (50.0, 50.0), (float("nan"), 70.0)])
def test_act3c_briefing_clamps_loyalty(protocol_story, loyalty, expected):
    protocol_story.loyalty = loyalty
    assert resolve_act3c_briefing_choice("neutral", protocol_story).loyalty_after == expected


def test_act3c_briefing_without_story_manager():
    assert resolve_act3c_briefing_choice("neutral", None).loyalty_after == 70.0


def test_act3c_abort_loses_live_squad_and_locks_branch(protocol_story):
    gsm = GroundSupportManager()
    gsm.set_story_manager(protocol_story)
    mission = MissionController(protocol_story)
    comms = _CalloutRecorder()

    outcome = resolve_act3c_protocol_abort(protocol_story, gsm, mission, comms)

    assert all(not u.is_alive for u in gsm.units)
    assert outcome.newly_lost == 4
    assert outcome.beacons_extinguished == 4
    assert outcome.already_resolved is False
    assert outcome.lost_callsigns == VIPER_SQUAD_CALLSIGNS
    assert outcome.doc_final_line == ACT3C_DOC_FINAL_LINE
    assert protocol_story.total_casualties == 4
    assert protocol_story.loyalty == 16.0
    assert protocol_story.get_ending_branch() == BRANCH_COLD_PROTOCOL
    assert protocol_story.extra[PROTOCOL_84C_EXTRA_KEY] is True
    assert protocol_story.extra[ACT3C_OUTCOME_EXTRA_KEY] == {"newly_lost": 4, "beacons_extinguished": 4}
    assert (protocol_story.current_act, protocol_story.current_sortie) == (3, 5)
    assert mission.current_objective == SORTIE5C_RTB_OBJECTIVE
    assert comms.callouts == [("Val", ACT3C_VAL_LOG_LINE)]


def test_act3c_abort_survives_ground_support_updates_at_loyalty_16(protocol_story):
    """Key edge case: casualties must not erode loyalty into DISSIDENT_SURRENDER."""
    gsm = GroundSupportManager()
    gsm.set_story_manager(protocol_story)
    resolve_act3c_protocol_abort(protocol_story, gsm)
    player = _mock_player()
    for _ in range(5):
        gsm.update(0.016, player, [], pygame.sprite.Group(), [])
    assert protocol_story.total_casualties == 4
    assert protocol_story.loyalty == 16.0
    assert protocol_story.get_ending_branch() == BRANCH_COLD_PROTOCOL


def test_act3c_abort_without_ground_support(protocol_story):
    outcome = resolve_act3c_protocol_abort(protocol_story, None)
    assert outcome.newly_lost == 4
    assert protocol_story.total_casualties == 4


def test_act3c_abort_counts_only_survivors(protocol_story):
    gsm = GroundSupportManager()
    assert gsm.apply_scripted_casualty(1) is True
    assert gsm.apply_scripted_casualty(3) is True
    outcome = resolve_act3c_protocol_abort(protocol_story, gsm)
    assert outcome.newly_lost == 2
    assert protocol_story.total_casualties == 2


def test_act3c_abort_on_already_dead_squad(protocol_story):
    gsm = GroundSupportManager()
    for index in range(4):
        assert gsm.apply_scripted_casualty(index) is True
    comms = _CalloutRecorder()
    outcome = resolve_act3c_protocol_abort(protocol_story, gsm, comms_hud=comms)
    assert outcome.newly_lost == 0
    assert protocol_story.total_casualties == 0
    assert protocol_story.extra[PROTOCOL_84C_EXTRA_KEY] is True
    assert comms.callouts == [("Val", ACT3C_VAL_LOG_LINE)]


def test_act3c_abort_is_idempotent(protocol_story):
    resolve_act3c_protocol_abort(protocol_story, None)
    gsm = GroundSupportManager()
    comms = _CalloutRecorder()
    again = resolve_act3c_protocol_abort(protocol_story, gsm, comms_hud=comms)
    assert again.already_resolved is True
    assert again.newly_lost == 0
    assert protocol_story.total_casualties == 4
    assert all(u.is_alive for u in gsm.units)
    assert comms.callouts == []


@pytest.mark.parametrize("stance", ["loyal", "neutral", "dissident"])
def test_act3c_abort_choice_flow_keeps_branch(protocol_story, stance):
    protocol_story.record_choice(SORTIE5C_ABORT_NODE_ID, stance)
    assert resolve_act3c_choice(SORTIE5C_ABORT_NODE_ID, stance, protocol_story) == SORTIE5C_RTB_OBJECTIVE
    assert ACT3C_MIN_LOYALTY <= protocol_story.loyalty <= ACT3C_MAX_LOYALTY
    assert protocol_story.get_ending_branch() == BRANCH_COLD_PROTOCOL


def test_act3c_choice_recorded_after_abort_is_clamped_again(protocol_story, tmp_path):
    resolve_act3c_protocol_abort(protocol_story, None)
    protocol_story.loyalty = 10.0
    resolve_act3c_protocol_abort(protocol_story, None)
    assert protocol_story.loyalty == 16.0
    reloaded = StoryManager(save_manager=CampaignSaveManager(data_dir=tmp_path))
    assert reloaded.get_ending_branch() == BRANCH_COLD_PROTOCOL


def test_act3c_abort_persists(protocol_story, tmp_path):
    protocol_story.save_manager = CampaignSaveManager(data_dir=tmp_path)
    resolve_act3c_protocol_abort(protocol_story, None)
    reloaded = StoryManager(save_manager=CampaignSaveManager(data_dir=tmp_path))
    assert reloaded.extra[PROTOCOL_84C_EXTRA_KEY] is True
    assert reloaded.total_casualties == 4


def test_act3c_abort_clamps_nan_loyalty(protocol_story):
    protocol_story.loyalty = float("nan")
    resolve_act3c_protocol_abort(protocol_story, None)
    assert protocol_story.loyalty == 70.0


@pytest.mark.parametrize("bad_extra", [None, [], "x"])
def test_act3c_abort_repairs_malformed_extra(protocol_story, bad_extra):
    protocol_story.extra = bad_extra
    resolve_act3c_protocol_abort(protocol_story, None)
    assert protocol_story.extra[PROTOCOL_84C_EXTRA_KEY] is True


def test_act3c_abort_ignores_invalid_ground_support(protocol_story):
    assert resolve_act3c_protocol_abort(protocol_story, object()).newly_lost == 4


def test_act3c_abort_without_story_manager():
    outcome = resolve_act3c_protocol_abort(None)
    assert outcome.loyalty_after == 70.0
    assert outcome.newly_lost == 4


def test_act3c_abort_reaches_real_comms_hud(protocol_story):
    comms = CommsHUD(story_manager=protocol_story)
    resolve_act3c_protocol_abort(protocol_story, None, comms_hud=comms)
    assert comms.is_active


def test_resolve_act3c_choice_routes_nodes(protocol_story):
    assert resolve_act3c_choice(ACT3C_BRIEFING_NODE_ID, "neutral", protocol_story) == SORTIE5C_INITIAL_OBJECTIVE
    assert resolve_act3c_choice(SORTIE5C_ABORT_NODE_ID, "neutral", protocol_story) == SORTIE5C_RTB_OBJECTIVE
    assert resolve_act3c_choice(ACT3A_ORDER_NODE_ID, "loyal", protocol_story) is None


@pytest.mark.parametrize(
    "node_id, stance",
    [(None, "neutral"), (True, "neutral"), ("unknown", "neutral"),
     (SORTIE5C_ABORT_NODE_ID, "maybe"), (ACT3C_BRIEFING_NODE_ID, "")],
)
def test_resolve_act3c_choice_rejects_invalid_input(protocol_story, node_id, stance):
    assert resolve_act3c_choice(node_id, stance, protocol_story) is None
    assert PROTOCOL_84C_EXTRA_KEY not in protocol_story.extra


# -----------------------------------------------------------------------------
# Act III-C: FLIR sensor feed and observation deck funeral renderers (#76)
# -----------------------------------------------------------------------------

from eagle1.story.cinematic_player import (  # noqa: E402
    CINEMATIC_SCENE_FLIR_SENSOR_FEED,
    VALID_CINEMATIC_SCENE_TYPES,
    CinematicKeyframe,
    CinematicSequence,
)


def _single_scene_player(scene_type, duration=10.0):
    sequence = CinematicSequence(
        sequence_id="act3c_scene_probe",
        ending_branch=BRANCH_COLD_PROTOCOL,
        title="probe",
        keyframes=(
            CinematicKeyframe(
                keyframe_id="probe", duration=duration, scene_type=scene_type, fade_in=0.0, fade_out=0.0
            ),
        ),
        epilogue_lines=(),
    )
    player = CinematicPlayer(1280, 720)
    player.start_sequence(sequence, build_act3b_epilogue_stats(None))
    return player


def test_act3c_flir_scene_type_registered():
    assert CINEMATIC_SCENE_FLIR_SENSOR_FEED == "flir_sensor_feed"
    assert CINEMATIC_SCENE_FLIR_SENSOR_FEED in VALID_CINEMATIC_SCENE_TYPES


def test_act3c_flir_beacons_turn_black_one_by_one():
    player = _single_scene_player(CINEMATIC_SCENE_FLIR_SENSOR_FEED)
    canvas = pygame.Surface((1280, 720))
    beacons = [(640 + bx, 360 + by) for bx, by in ((-90, 40), (-30, 60), (30, 60), (90, 40))]
    blue, black = (60, 140, 255), (0, 0, 0)

    player.update(0.0)
    player._draw_scene(canvas, player.current_keyframe)
    assert [canvas.get_at(p)[:3] for p in beacons] == [blue] * 4

    player.update(5.0)  # t = 0.5
    player._draw_scene(canvas, player.current_keyframe)
    assert [canvas.get_at(p)[:3] for p in beacons] == [black, black, blue, blue]

    player.update(4.0)  # t = 0.9
    player._draw_scene(canvas, player.current_keyframe)
    assert [canvas.get_at(p)[:3] for p in beacons] == [black] * 4


def test_act3c_flir_scene_background_is_thermal_green():
    player = _single_scene_player(CINEMATIC_SCENE_FLIR_SENSOR_FEED)
    canvas = pygame.Surface((1280, 720))
    player.update(0.0)
    player._draw_scene(canvas, player.current_keyframe)
    assert canvas.get_at((680, 380))[:3] == (10, 22, 16)


def test_act3c_funeral_draws_silver_coffins_flags_and_ribbon():
    player = CinematicPlayer(1280, 720)
    canvas = pygame.Surface((1280, 720))
    canvas.fill((0, 0, 0))
    player._draw_scene_observation_deck_funeral(canvas)
    for x in (-270, -90, 90, 270):
        assert canvas.get_at((640 + x - 55, 360 + 220))[:3] == (178, 184, 196)
        assert canvas.get_at((640 + x, 360 + 194))[:3] == (28, 58, 140)
    assert canvas.get_at((635, 486))[:3] == (214, 218, 228)


def test_act3c_keyframe_progress_idle_is_zero():
    assert CinematicPlayer(1280, 720)._keyframe_progress() == 0.0


# -----------------------------------------------------------------------------
# Act III-C: The Funeral of Viper Squad cinematic and epilogue (#76)
# -----------------------------------------------------------------------------

from eagle1.story.campaign_act3 import (  # noqa: E402
    ACT3C_ARCHIVE_EPILOGUE_LINES,
    ACT3C_HYMN_CUE,
    ACT3C_PILOT_STATUS as ACT3C_PILOT_STATUS_EXPORTED,
    ACT3C_VAL_FINAL_LINE,
    build_act3c_cinematic_sequence,
    build_act3c_epilogue_stats,
)
from eagle1.story.cinematic_player import (  # noqa: E402
    CINEMATIC_SCENE_OBSERVATION_DECK_FUNERAL,
    wrap_cinematic_text,
)

ACT3C_SCENE_ORDER = [
    CINEMATIC_SCENE_FLIR_SENSOR_FEED,
    CINEMATIC_SCENE_EPILOGUE_CARD,
    CINEMATIC_SCENE_OBSERVATION_DECK_FUNERAL,
    CINEMATIC_SCENE_OBSERVATION_DECK_FUNERAL,
    CINEMATIC_SCENE_OBSERVATION_DECK_FUNERAL,
    CINEMATIC_SCENE_OBSERVATION_DECK_FUNERAL,
    CINEMATIC_SCENE_EPILOGUE_CARD,
]


def test_act3c_cinematic_sequence_is_valid():
    sequence = build_act3c_cinematic_sequence()
    assert validate_cinematic_sequence(sequence) is True
    assert sequence.sequence_id == ACT3C_SEQUENCE_ID == SORTIE_5C_CONFIG.debrief_node_id
    assert sequence.ending_branch == BRANCH_COLD_PROTOCOL
    assert sequence.epilogue_lines == ACT3C_ARCHIVE_EPILOGUE_LINES


def test_act3c_cinematic_story_order():
    keyframes = build_act3c_cinematic_sequence().keyframes
    assert [kf.keyframe_id for kf in keyframes] == [
        "act3c_rtb_climb",
        "act3c_static_log",
        "act3c_funeral_hymn",
        "act3c_reiner_eulogy",
        "act3c_ortiz_pity",
        "act3c_alone_before_coffins",
        "act3c_archive_notice",
    ]
    assert [kf.scene_type for kf in keyframes] == ACT3C_SCENE_ORDER


def test_act3c_cinematic_contains_canonical_beats():
    text = _all_subtitle_text(build_act3c_cinematic_sequence())
    for expected in (
        "why are you flying away",
        "Close your eyes",
        "turn black",
        "Flight logs confirmed. Return to base completed within standard fuel parameters.",
        "Four polished silver coffins",
        "All four are empty.",
        "Hymn of the Fallen Citizen",
        "statistically optimal sacrifice of Viper Detachment",
        "Citation of Procedural Excellence",
        "Chief Ortiz does not clap.",
        "devastating pity",
        "Your next sortie departs at 0700.",
        "I followed the rules. I just... followed the rules...",
        *ACT3C_ARCHIVE_EPILOGUE_LINES,
    ):
        assert expected in text
    assert ACT3C_ARCHIVE_EPILOGUE_LINES[2] == "Flight Lieutenant Val completed thirty-two additional sorties."


def test_act3c_val_final_line_is_last_spoken_before_archive():
    keyframe = next(kf for kf in build_act3c_cinematic_sequence().keyframes if kf.keyframe_id == "act3c_alone_before_coffins")
    assert len(keyframe.subtitles) == 1
    assert keyframe.subtitles[0].speaker == "Val"
    assert keyframe.subtitles[0].text == ACT3C_VAL_FINAL_LINE
    assert keyframe.camera_end[2] < keyframe.camera_start[2]


def test_act3c_cinematic_audio_cues_have_assets():
    sfx_dir = PROJECT_ROOT / "audio" / "sfx"
    cues = [kf.audio_cue for kf in build_act3c_cinematic_sequence().keyframes if kf.audio_cue]
    assert ACT3C_HYMN_CUE in cues
    for cue in cues:
        if cue != "stop_music":
            assert (sfx_dir / f"{cue}.wav").is_file(), cue


def test_act3c_subtitles_fit_two_lines():
    player = CinematicPlayer(1280, 720)
    if player.font_subtitle is None:
        pytest.skip("fonts unavailable")
    for kf in build_act3c_cinematic_sequence().keyframes:
        for sub in kf.subtitles:
            lines = wrap_cinematic_text(sub.text, 1040, lambda s: player.font_subtitle.size(s)[0])
            assert len(lines) <= 2, sub.text


def test_act3c_cinematic_plays_through_player_to_epilogue(protocol_story):
    resolve_act3c_protocol_abort(protocol_story)
    sequence = build_act3c_cinematic_sequence()
    player = CinematicPlayer(1280, 720)
    received = []
    player.on_audio_cue = received.append
    player.start_sequence(sequence, build_act3c_epilogue_stats(protocol_story))
    canvas = pygame.Surface((1280, 720))
    seen_subtitles = set()

    total = sum(kf.duration for kf in sequence.keyframes)
    for _ in range(int(total * 60) + 30):
        player.update(1.0 / 60.0)
        player.draw(canvas)
        seen_subtitles.update(sub.text for sub in player.get_active_subtitles())
        if player.is_epilogue:
            break

    assert player.is_epilogue
    assert player.skipped is False
    assert received == [kf.audio_cue.strip() for kf in sequence.keyframes if kf.audio_cue]
    assert seen_subtitles == {sub.text for kf in sequence.keyframes for sub in kf.subtitles}
    assert player.get_epilogue_lines() == ACT3C_ARCHIVE_EPILOGUE_LINES


def test_act3c_epilogue_stats_after_abort(protocol_story):
    protocol_story.total_casualties = 3
    protocol_story.loyalty = 40.0
    resolve_act3c_protocol_abort(protocol_story, None)
    stats = build_act3c_epilogue_stats(protocol_story)
    assert stats.ending_branch == BRANCH_COLD_PROTOCOL
    assert stats.ending_title == "THE PATH OF COLD PROTOCOL"
    assert stats.pilot_status == ACT3C_PILOT_STATUS_EXPORTED == "ACTIVE DUTY // CITATION OF PROCEDURAL EXCELLENCE"
    assert stats.final_loyalty == 40.0
    assert stats.total_casualties == 7
    assert stats.sorties_completed == 37
    assert stats.epilogue_lines == ACT3C_ARCHIVE_EPILOGUE_LINES


def test_act3c_epilogue_stats_without_story_manager():
    stats = build_act3c_epilogue_stats(None)
    assert stats.final_loyalty == 70.0
    assert stats.total_casualties == 4
    assert stats.pilot_status == "ACTIVE DUTY // CITATION OF PROCEDURAL EXCELLENCE"


@pytest.mark.parametrize("loyalty, expected", [(5.0, 16.0), (95.0, 89.0), (float("nan"), 70.0)])
def test_act3c_epilogue_stats_clamp_loyalty(protocol_story, loyalty, expected):
    protocol_story.loyalty = loyalty
    assert build_act3c_epilogue_stats(protocol_story).final_loyalty == expected


@pytest.mark.parametrize("scene_type", [CINEMATIC_SCENE_FLIR_SENSOR_FEED, CINEMATIC_SCENE_OBSERVATION_DECK_FUNERAL])
def test_act3c_scene_renderers_draw_something(scene_type):
    player = CinematicPlayer(1280, 720)
    canvas = pygame.Surface((1280, 720))
    canvas.fill((0, 0, 0))
    keyframe = next(kf for kf in build_act3c_cinematic_sequence().keyframes if kf.scene_type == scene_type)
    player._draw_scene(canvas, keyframe)
    assert canvas.get_at((640, 360))[:3] != (0, 0, 0)
