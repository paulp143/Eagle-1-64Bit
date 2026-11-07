"""Tests for the Act III campaign endings.

Act III-A "The Path of Blind Obedience" (#74): Scene 3A.1 encrypted order, Sortie 5A trench
purge, Scene 3A.2 hangar clone interlude, Sortie 6A terminal dive cinematic and epilogue.

Act III-B "The Path of the Dissident" (#75): Scene 3B.1 ready-room confrontation, Sortie 5B
weapon disarmament and surrender, and the Judgment of Viper Squad execution cinematic.
"""

import math

import pygame
import pytest

from eagle1.story.campaign_act3 import (
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
from eagle1.story.campaign_save import CampaignSaveManager
from eagle1.story.cinematic_player import (
    CINEMATIC_SCENE_EPILOGUE_CARD,
    CINEMATIC_SCENE_HANGAR_CLONES,
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
from eagle1.story.story_manager import BRANCH_OBEDIENCE_PURGE, MAX_LOYALTY, StoryManager
from eagle1.systems.ground_support import GroundSupportManager

ACT3A_NODE_IDS = ("act3a_encrypted_order", "sortie_5a_trench_lock")
ACT3A_BANTER_CATEGORIES = (
    "act3a_s5_apex_checkin",
    "act3a_s5_doc_evac",
    "act3a_s5_apex_final",
    "act3a_s5_reiner_commendation",
)
ACT3B_NODE_IDS = ("act3b_ready_room_confrontation", "sortie_5b_surrender_broadcast")


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
