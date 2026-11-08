"""Act III finale wiring (#77): dispatcher, flight, hub and branch tables."""

from types import SimpleNamespace

import pytest

from eagle1.story.campaign_act3 import (
    ACT3_BRIEFING_NPC_IDS,
    ACT3_MISSION_OVERRIDES,
    ACT3_SORTIE_CONFIGS,
    ACT3A_PILOT_STATUS,
    ACT3A_SEQUENCE_ID,
    ACT3A_TRIGGERS,
    ACT3B_CONFRONTATION_NODE_ID,
    ACT3B_PILOT_STATUS,
    ACT3B_SEQUENCE_ID,
    ACT3B_TRIGGERS,
    ACT3C_BRIEFING_NODE_ID,
    ACT3C_PILOT_STATUS,
    ACT3C_SEQUENCE_ID,
    ACT3C_TRIGGERS,
    SORTIE5A_TRENCH_NODE_ID,
    SORTIE5C_INITIAL_OBJECTIVE,
    SORTIE_5A_CONFIG,
    SORTIE_5B_CONFIG,
    SORTIE_5C_CONFIG,
    build_ending_cinematic,
    get_locked_ending_branch,
    get_act3_sortie_config,
    is_act3_finale_pending,
    is_act3_climax_already_resolved,
    has_recorded_act3_briefing,
    mark_campaign_finale_completed,
    register_act3_triggers_for_branch,
    resolve_act3_choice,
)
from eagle1.story.campaign_save import CampaignSaveManager
from eagle1.story.cinematic_player import validate_cinematic_sequence
from eagle1.story.dialogue_db import get_dialogue_node
from eagle1.story.narrative_trigger_manager import NarrativeTriggerManager
from eagle1.story.story_manager import (
    BRANCH_COLD_PROTOCOL,
    BRANCH_DISSIDENT_SURRENDER,
    BRANCH_OBEDIENCE_PURGE,
    StoryManager,
)

BRANCH_LOYALTY = {BRANCH_OBEDIENCE_PURGE: 95.0, BRANCH_DISSIDENT_SURRENDER: 10.0, BRANCH_COLD_PROTOCOL: 55.0}
ALL_BRANCHES = tuple(BRANCH_LOYALTY)


def make_finale_story(tmp_path, branch):
    """StoryManager in the state MissionController leaves after Sortie 4 (isolated save dir)."""
    story = StoryManager(save_manager=CampaignSaveManager(data_dir=tmp_path))
    story.loyalty = BRANCH_LOYALTY[branch]
    story.extra["act2_completed"] = True
    story.extra["ending_branch"] = branch
    story.extra["completed_sorties"] = [1, 2, 3, 4]
    story.advance_sortie(act=3, sortie=4)
    return story


def make_player():
    return SimpleNamespace(
        used_bullets=0, max_bullets=200, used_rockets=0, max_rockets=4,
        shooting=False, rocket_shooting=False, reloading=False, rocket_reloading=False,
    )


# ---------------------------------------------------------------- Task 1: dispatcher

@pytest.mark.parametrize("raw", [None, 5, "BOGUS"])
def test_invalid_locked_branch_falls_back_to_loyalty(tmp_path, raw):
    story = make_finale_story(tmp_path, BRANCH_DISSIDENT_SURRENDER)
    story.extra["ending_branch"] = raw
    assert get_locked_ending_branch(story) == BRANCH_DISSIDENT_SURRENDER


def test_locked_branch_wins_over_loyalty(tmp_path):
    story = make_finale_story(tmp_path, BRANCH_COLD_PROTOCOL)
    story.loyalty = 95.0
    assert get_locked_ending_branch(story) == BRANCH_COLD_PROTOCOL


def test_locked_branch_without_story_is_cold_protocol():
    assert get_locked_ending_branch(None) == BRANCH_COLD_PROTOCOL


@pytest.mark.parametrize("branch", ALL_BRANCHES)
def test_build_ending_cinematic_per_branch(tmp_path, branch):
    story = make_finale_story(tmp_path, branch)
    sequence, stats = build_ending_cinematic(story)
    assert validate_cinematic_sequence(sequence)
    expected_sequence_id = {
        BRANCH_OBEDIENCE_PURGE: ACT3A_SEQUENCE_ID,
        BRANCH_DISSIDENT_SURRENDER: ACT3B_SEQUENCE_ID,
        BRANCH_COLD_PROTOCOL: ACT3C_SEQUENCE_ID,
    }[branch]
    assert sequence.sequence_id == expected_sequence_id
    assert stats.ending_branch == branch
    expected_status = {
        BRANCH_OBEDIENCE_PURGE: ACT3A_PILOT_STATUS,
        BRANCH_DISSIDENT_SURRENDER: ACT3B_PILOT_STATUS,
        BRANCH_COLD_PROTOCOL: ACT3C_PILOT_STATUS,
    }[branch]
    assert stats.pilot_status == expected_status


def test_build_ending_cinematic_uses_locked_branch_not_loyalty(tmp_path):
    story = make_finale_story(tmp_path, BRANCH_COLD_PROTOCOL)
    story.loyalty = 95.0
    sequence, _ = build_ending_cinematic(story)
    assert sequence.sequence_id == ACT3C_SEQUENCE_ID


def test_finale_pending_states(tmp_path):
    assert is_act3_finale_pending(None) is False
    story = make_finale_story(tmp_path, BRANCH_COLD_PROTOCOL)
    assert is_act3_finale_pending(story) is True
    story.extra["campaign_finale_completed"] = True
    assert is_act3_finale_pending(story) is False
    story.extra.pop("campaign_finale_completed")
    story.extra["act2_completed"] = "yes"
    assert is_act3_finale_pending(story) is False


def test_mark_campaign_finale_completed_persists(tmp_path):
    story = make_finale_story(tmp_path, BRANCH_OBEDIENCE_PURGE)
    assert mark_campaign_finale_completed(story) is True
    reloaded = StoryManager(save_manager=CampaignSaveManager(data_dir=tmp_path))
    assert reloaded.extra.get("campaign_finale_completed") is True
    assert mark_campaign_finale_completed(None) is False


def test_climax_already_resolved_per_branch(tmp_path):
    story = make_finale_story(tmp_path, BRANCH_OBEDIENCE_PURGE)
    assert is_act3_climax_already_resolved(story, BRANCH_OBEDIENCE_PURGE) is False
    story.extra["viper_squad_purged"] = True
    assert is_act3_climax_already_resolved(story, BRANCH_OBEDIENCE_PURGE) is True
    story.extra["protocol_84c_enforced"] = True
    assert is_act3_climax_already_resolved(story, BRANCH_COLD_PROTOCOL) is True
    assert is_act3_climax_already_resolved(story, BRANCH_DISSIDENT_SURRENDER) is False
    assert is_act3_climax_already_resolved(None, BRANCH_OBEDIENCE_PURGE) is False


def test_has_recorded_act3_briefing(tmp_path):
    story = make_finale_story(tmp_path, BRANCH_COLD_PROTOCOL)
    assert has_recorded_act3_briefing(story, BRANCH_COLD_PROTOCOL) is False
    story.record_choice(ACT3C_BRIEFING_NODE_ID, "neutral")
    assert has_recorded_act3_briefing(story, BRANCH_COLD_PROTOCOL) is True


@pytest.mark.parametrize(
    "branch, triggers",
    [
        (BRANCH_OBEDIENCE_PURGE, ACT3A_TRIGGERS),
        (BRANCH_DISSIDENT_SURRENDER, ACT3B_TRIGGERS),
        (BRANCH_COLD_PROTOCOL, ACT3C_TRIGGERS),
    ],
)
def test_register_triggers_for_branch_only_registers_that_branch(tmp_path, branch, triggers):
    story = make_finale_story(tmp_path, branch)
    manager = NarrativeTriggerManager(story)
    assert register_act3_triggers_for_branch(manager, branch) == len(triggers)
    assert {t.trigger_id for t in manager.get_triggers_for_sortie(5)} == {t.trigger_id for t in triggers}


def test_register_triggers_for_unknown_branch_raises(tmp_path):
    manager = NarrativeTriggerManager(make_finale_story(tmp_path, BRANCH_COLD_PROTOCOL))
    with pytest.raises(ValueError):
        register_act3_triggers_for_branch(manager, "BOGUS")
    with pytest.raises(ValueError):
        register_act3_triggers_for_branch(manager, None)


def test_resolve_act3_choice_routes_by_branch(tmp_path):
    story = make_finale_story(tmp_path, BRANCH_COLD_PROTOCOL)
    assert resolve_act3_choice(
        BRANCH_COLD_PROTOCOL, ACT3C_BRIEFING_NODE_ID, "neutral", story
    ) == SORTIE5C_INITIAL_OBJECTIVE
    assert resolve_act3_choice(BRANCH_OBEDIENCE_PURGE, ACT3C_BRIEFING_NODE_ID, "neutral", story) is None
    assert resolve_act3_choice("BOGUS", ACT3C_BRIEFING_NODE_ID, "neutral", story) is None


def test_mission_overrides_cover_all_act3_sorties():
    assert set(ACT3_MISSION_OVERRIDES) == {cfg.sortie_id for cfg in ACT3_SORTIE_CONFIGS.values()}
    assert ACT3_MISSION_OVERRIDES[SORTIE_5A_CONFIG.sortie_id]["has_ground"] is True
    assert ACT3_MISSION_OVERRIDES[SORTIE_5B_CONFIG.sortie_id]["has_ground"] is False
    assert ACT3_MISSION_OVERRIDES[SORTIE_5C_CONFIG.sortie_id]["has_ground"] is True


def test_briefing_npc_matches_node_speaker():
    assert "Reiner" in get_dialogue_node(SORTIE_5A_CONFIG.briefing_node_id).speaker
    assert "Vance" in get_dialogue_node(SORTIE_5C_CONFIG.briefing_node_id).speaker
    assert ACT3_BRIEFING_NPC_IDS[BRANCH_COLD_PROTOCOL] == "npc_vance"
    assert ACT3_BRIEFING_NPC_IDS[BRANCH_OBEDIENCE_PURGE] == "npc_reiner"


def test_sortie_config_lookup():
    assert get_act3_sortie_config(BRANCH_COLD_PROTOCOL) is SORTIE_5C_CONFIG
    assert get_act3_sortie_config("BOGUS") is None
    assert SORTIE5A_TRENCH_NODE_ID in SORTIE_5A_CONFIG.inflight_node_ids
    assert ACT3B_CONFRONTATION_NODE_ID == SORTIE_5B_CONFIG.briefing_node_id
