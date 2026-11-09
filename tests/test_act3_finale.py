"""Act III finale wiring (#77): dispatcher, flight, hub and branch tables."""

from types import SimpleNamespace

import pygame
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
from eagle1.story.campaign_act3 import (
    ACT3_OUTRO_SECONDS,
    SORTIE5B_LANDING_MIN_DELAY_SECONDS,
    SORTIE5B_SURRENDER_NODE_ID,
    SORTIE5C_ABORT_NODE_ID,
)
from eagle1.story.campaign_save import CampaignSaveManager
from eagle1.story import SuperDestroyerView
from eagle1.story.campaign_session import CampaignSortieSession, build_campaign_mission_config
from eagle1.story.mission_controller import CAMPAIGN_SORTIE_REGISTRY
from eagle1.story.cinematic_player import CinematicPlayer, validate_cinematic_sequence
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


# ---------------------------------------------------------------- Task 2: flight in CampaignSortieSession

FRAME_DT = 1.0 / 60.0
MAX_FRAMES = 6000
BASE_CONFIGS = {
    "air_superiority": {"id": "air_superiority", "has_ground": False, "has_base": False, "max_waves": 5},
    "base_defense": {"id": "base_defense", "has_ground": False, "has_base": True, "has_bombers": True, "max_waves": 5},
}


def _pump(session, seconds, gsm=None):
    for _ in range(round(seconds / FRAME_DT)):
        session.update(FRAME_DT, 1, 0, gsm)


def _pump_until_node(session, story, node_id):
    for _ in range(MAX_FRAMES):
        session.update(FRAME_DT, 1, 0, None)
        if story.active_dialogue is not None and story.active_dialogue.node_id == node_id:
            return True
    return False


@pytest.mark.parametrize("branch", ALL_BRANCHES)
def test_pending_launch_starts_branch_sortie(tmp_path, branch):
    story = make_finale_story(tmp_path, branch)
    session = CampaignSortieSession(story_manager=story)
    cfg = session.launch_sortie()
    assert cfg is ACT3_SORTIE_CONFIGS[branch]
    assert session.is_act3_flight
    assert session.active_sortie_num == 5
    assert story.current_sortie == 5
    assert session.mission_controller.get_active_objective_text() == cfg.initial_objective
    ids = {t.trigger_id for t in session.trigger_manager.get_triggers_for_sortie(5)}
    expected = {
        BRANCH_OBEDIENCE_PURGE: ACT3A_TRIGGERS,
        BRANCH_DISSIDENT_SURRENDER: ACT3B_TRIGGERS,
        BRANCH_COLD_PROTOCOL: ACT3C_TRIGGERS,
    }[branch]
    assert ids == {t.trigger_id for t in expected}


def test_launch_without_act2_flag_stays_sortie4_replay(tmp_path):
    story = StoryManager(save_manager=CampaignSaveManager(data_dir=tmp_path))
    story.advance_sortie(act=3, sortie=4)
    session = CampaignSortieSession(story_manager=story)
    cfg = session.launch_sortie()
    assert session.is_replay is True
    assert cfg.sortie_num == 4
    assert not session.is_act3_flight


def test_launch_after_finale_replays_sortie4(tmp_path):
    story = make_finale_story(tmp_path, BRANCH_COLD_PROTOCOL)
    story.extra["campaign_finale_completed"] = True
    session = CampaignSortieSession(story_manager=story)
    session.launch_sortie()
    assert session.is_replay is True
    assert session.active_sortie_num == 4
    assert not session.is_act3_flight


@pytest.mark.parametrize("branch", ALL_BRANCHES)
def test_act3_mission_config_overrides(branch):
    cfg = ACT3_SORTIE_CONFIGS[branch]
    mission = build_campaign_mission_config(cfg, BASE_CONFIGS)
    assert mission["has_ground"] is ACT3_MISSION_OVERRIDES[cfg.sortie_id]["has_ground"]
    assert mission["has_base"] is False
    assert mission["has_bombers"] is False
    assert mission["max_waves"] == 99
    assert mission["campaign_sortie"] == 5


@pytest.mark.parametrize("branch", ALL_BRANCHES)
def test_inflight_choice_resolves_climax(tmp_path, branch):
    story = make_finale_story(tmp_path, branch)
    session = CampaignSortieSession(story_manager=story)
    cfg = session.launch_sortie()
    player = make_player()
    session.attach_player(player)
    node_id = cfg.inflight_node_ids[0]
    assert _pump_until_node(session, story, node_id)
    assert session.is_act3_resolved is False
    assert session.resolve_choice(node_id, "neutral") is not None
    assert session.is_act3_resolved is True
    if branch == BRANCH_DISSIDENT_SURRENDER:
        assert player.weapons_disarmed is True


def test_briefing_choice_in_flight_does_not_resolve(tmp_path):
    story = make_finale_story(tmp_path, BRANCH_COLD_PROTOCOL)
    session = CampaignSortieSession(story_manager=story)
    session.launch_sortie()
    assert session.resolve_choice(ACT3C_BRIEFING_NODE_ID, "neutral") == SORTIE5C_INITIAL_OBJECTIVE
    assert session.is_act3_resolved is False


def test_attached_player_used_for_disarmament(tmp_path):
    story = make_finale_story(tmp_path, BRANCH_DISSIDENT_SURRENDER)
    session = CampaignSortieSession(story_manager=story)
    session.launch_sortie()
    player = make_player()
    session.attach_player(player)
    session.resolve_choice(SORTIE5B_SURRENDER_NODE_ID, "neutral")
    assert player.weapons_disarmed is True


@pytest.mark.parametrize("branch", [BRANCH_OBEDIENCE_PURGE, BRANCH_COLD_PROTOCOL])
def test_outro_completion_obedience_and_cold(tmp_path, branch):
    story = make_finale_story(tmp_path, branch)
    session = CampaignSortieSession(story_manager=story)
    cfg = session.launch_sortie()
    session.resolve_choice(cfg.inflight_node_ids[0], "neutral", None, make_player())
    assert session.is_act3_climax_complete(0.0, 0.0, 0.0, 0.0, True) is False
    _pump(session, ACT3_OUTRO_SECONDS + 0.1)
    assert session.is_act3_climax_complete(0.0, 0.0, 0.0, 0.0, True) is True


def test_dead_player_completes_only_after_resolution(tmp_path):
    story = make_finale_story(tmp_path, BRANCH_COLD_PROTOCOL)
    session = CampaignSortieSession(story_manager=story)
    session.launch_sortie()
    assert session.is_act3_climax_complete(0.0, 0.0, 0.0, 0.0, False) is False
    session.resolve_choice(SORTIE5C_ABORT_NODE_ID, "neutral", None, make_player())
    assert session.is_act3_climax_complete(0.0, 0.0, 0.0, 0.0, False) is True


def test_dissident_landing_rules(tmp_path):
    story = make_finale_story(tmp_path, BRANCH_DISSIDENT_SURRENDER)
    session = CampaignSortieSession(story_manager=story)
    session.launch_sortie()
    session.resolve_choice(SORTIE5B_SURRENDER_NODE_ID, "neutral", None, make_player())
    cx, cy = 1500.0, 1500.0
    assert session.is_act3_climax_complete(cx, cy, 2.0, 2.0, True) is False
    _pump(session, SORTIE5B_LANDING_MIN_DELAY_SECONDS + 0.1)
    assert session.is_act3_climax_complete(cx, cy, 2.0, 2.0, True) is True
    assert session.is_act3_climax_complete(100.0, 100.0, 2.0, 2.0, True) is False
    assert session.is_act3_climax_complete(cx, cy, 5.0, 2.0, True) is False
    assert session.is_act3_climax_complete(cx, cy, float("nan"), 2.0, True) is False


def test_extraction_timer_text(tmp_path):
    story = make_finale_story(tmp_path, BRANCH_COLD_PROTOCOL)
    session = CampaignSortieSession(story_manager=story)
    session.launch_sortie()
    assert session.get_act3_extraction_timer_text() == "00:45"
    _pump(session, 40.5)  # 7.5 s left; a float-sum just below 40.0 would round up to 00:09
    assert session.get_act3_extraction_timer_text() == "00:08"
    assert session.is_act3_extraction_timer_urgent() is True
    session.resolve_choice(SORTIE5C_ABORT_NODE_ID, "neutral", None, make_player())
    assert session.get_act3_extraction_timer_text() is None


def test_extraction_timer_hidden_outside_cold_protocol(tmp_path):
    story = make_finale_story(tmp_path, BRANCH_OBEDIENCE_PURGE)
    session = CampaignSortieSession(story_manager=story)
    session.launch_sortie()
    assert session.get_act3_extraction_timer_text() is None


def test_restart_act3_flight_uses_act3_config(tmp_path):
    story = make_finale_story(tmp_path, BRANCH_OBEDIENCE_PURGE)
    session = CampaignSortieSession(story_manager=story)
    session.launch_sortie()
    session.resolve_choice(SORTIE5A_TRENCH_NODE_ID, "neutral", None, make_player())
    cfg = session.restart_flight()
    assert cfg is SORTIE_5A_CONFIG
    assert session.is_act3_flight
    assert session.is_act3_resolved is False


def test_complete_act3_climax_ends_flight(tmp_path):
    story = make_finale_story(tmp_path, BRANCH_OBEDIENCE_PURGE)
    session = CampaignSortieSession(story_manager=story)
    session.launch_sortie()
    assert session.complete_act3_climax() == BRANCH_OBEDIENCE_PURGE
    assert session.is_flight_active is False
    assert session.act3_branch is None
    assert session.complete_act3_climax() is None


def test_complete_sortie_ignored_during_act3_flight(tmp_path):
    story = make_finale_story(tmp_path, BRANCH_COLD_PROTOCOL)
    session = CampaignSortieSession(story_manager=story)
    session.launch_sortie()
    assert session.complete_sortie({}) == {}
    assert session.is_act3_flight


def test_start_act3_climax_cinematic_plays_branch(tmp_path):
    story = make_finale_story(tmp_path, BRANCH_COLD_PROTOCOL)
    session = CampaignSortieSession(story_manager=story)
    session.launch_sortie()
    player = CinematicPlayer(1280, 720)
    assert session.start_act3_climax_cinematic(player) == BRANCH_COLD_PROTOCOL
    assert player.is_playing
    assert player.sequence.ending_branch == BRANCH_COLD_PROTOCOL
    assert session.is_flight_active is False
    with pytest.raises(TypeError):
        session.start_act3_climax_cinematic(object())


def test_resolve_hub_choice_clamps_loyalty(tmp_path):
    story = make_finale_story(tmp_path, BRANCH_COLD_PROTOCOL)
    story.loyalty = 88.0
    session = CampaignSortieSession(story_manager=story)
    story.record_choice(ACT3C_BRIEFING_NODE_ID, "loyal")
    assert story.loyalty > 89.0
    assert session.resolve_hub_choice(ACT3C_BRIEFING_NODE_ID, "loyal") == SORTIE5C_INITIAL_OBJECTIVE
    assert story.loyalty <= 89.0
    assert session.resolve_hub_choice("bridge_vance_logistics", "neutral") is None


def test_hub_choice_outside_finale_is_ignored(tmp_path):
    story = StoryManager(save_manager=CampaignSaveManager(data_dir=tmp_path))
    session = CampaignSortieSession(story_manager=story)
    assert session.resolve_hub_choice(ACT3C_BRIEFING_NODE_ID, "neutral") is None


def test_should_skip_to_finale_cinematic(tmp_path):
    story = make_finale_story(tmp_path, BRANCH_OBEDIENCE_PURGE)
    session = CampaignSortieSession(story_manager=story)
    assert session.should_skip_to_finale_cinematic() is False
    story.extra["viper_squad_purged"] = True
    assert session.should_skip_to_finale_cinematic() is True
    story.extra["ending_branch"] = BRANCH_DISSIDENT_SURRENDER
    assert session.should_skip_to_finale_cinematic() is False
    fresh = StoryManager(save_manager=CampaignSaveManager(data_dir=tmp_path / "fresh"))
    assert CampaignSortieSession(story_manager=fresh).should_skip_to_finale_cinematic() is False


def test_get_act3_hub_briefing(tmp_path):
    story = make_finale_story(tmp_path, BRANCH_COLD_PROTOCOL)
    session = CampaignSortieSession(story_manager=story)
    assert session.get_act3_hub_briefing() == (SORTIE_5C_CONFIG, "npc_vance")
    story.extra["act2_completed"] = False
    assert session.get_act3_hub_briefing() == (None, None)


# ---------------------------------------------------------------- Task 4: hub briefing and launch gate

def _hub(tmp_path, branch):
    story = make_finale_story(tmp_path, branch)
    return SuperDestroyerView(story_manager=story), story


def test_hub_briefing_card_shows_act3_sortie(tmp_path):
    view, _ = _hub(tmp_path, BRANCH_COLD_PROTOCOL)
    view.set_act3_briefing(SORTIE_5C_CONFIG, "npc_vance")
    briefing = view.get_current_sortie_briefing()
    assert briefing["title"] == SORTIE_5C_CONFIG.title
    assert briefing["mission_id"] == "base_defense"


@pytest.mark.parametrize("branch", ALL_BRANCHES)
def test_hub_briefing_npc_returns_branch_node(tmp_path, branch):
    view, _ = _hub(tmp_path, branch)
    cfg = ACT3_SORTIE_CONFIGS[branch]
    npc = ACT3_BRIEFING_NPC_IDS[branch]
    view.set_act3_briefing(cfg, npc)
    assert view.resolve_npc_dialogue(npc).node_id == cfg.briefing_node_id


def test_hub_other_bridge_npc_keeps_its_node(tmp_path):
    view, _ = _hub(tmp_path, BRANCH_COLD_PROTOCOL)
    view.set_act3_briefing(SORTIE_5C_CONFIG, "npc_vance")
    assert view.resolve_npc_dialogue("npc_reiner").node_id == "bridge_reiner_scrutiny"


def test_launch_opens_briefing_until_choice_recorded(tmp_path):
    view, story = _hub(tmp_path, BRANCH_COLD_PROTOCOL)
    view.set_act3_briefing(SORTIE_5C_CONFIG, "npc_vance")
    first = view.trigger_catapult_launch()
    assert first["action"] == "interact_npc"
    assert first["briefing_required"] is True
    assert view.launch_initiated is False
    assert view._dialogue_open is True
    assert view.select_dialogue_stance("neutral") is not None
    view.close_dialogue()
    second = view.trigger_catapult_launch()
    assert second["action"] == "launch_sortie"
    assert second["mission_id"] == "base_defense"
    assert story.dialogue_history[-1]["node"] == SORTIE_5C_CONFIG.briefing_node_id


def test_set_act3_briefing_none_restores_default(tmp_path):
    view, _ = _hub(tmp_path, BRANCH_COLD_PROTOCOL)
    view.set_act3_briefing(SORTIE_5C_CONFIG, "npc_vance")
    view.set_act3_briefing(None, None)
    assert view.get_current_sortie_briefing()["title"] == CAMPAIGN_SORTIE_REGISTRY[4].title
    assert view.resolve_npc_dialogue("npc_reiner").node_id == "bridge_reiner_scrutiny"


@pytest.mark.parametrize("config, npc", [("cfg", "npc_vance"), (SORTIE_5C_CONFIG, ""), (SORTIE_5C_CONFIG, None)])
def test_set_act3_briefing_rejects_bad_types(tmp_path, config, npc):
    view, _ = _hub(tmp_path, BRANCH_COLD_PROTOCOL)
    with pytest.raises(TypeError):
        view.set_act3_briefing(config, npc)


def test_hub_draw_with_act3_briefing_smoke(tmp_path):
    view, _ = _hub(tmp_path, BRANCH_COLD_PROTOCOL)
    view.set_act3_briefing(SORTIE_5C_CONFIG, "npc_vance")
    surface = pygame.Surface((1280, 720))
    view.draw(surface, (0, 0))
    view.draw(surface, (0, 0))


def test_act3_finale_api_exported():
    import eagle1.story as story_pkg
    from eagle1.story import campaign_act3, cinematic_player

    for name in ("ACT3_SORTIE_CONFIGS", "build_ending_cinematic", "get_locked_ending_branch",
                 "is_act3_finale_pending", "mark_campaign_finale_completed", "resolve_act3_choice"):
        assert name in story_pkg.__all__
        assert getattr(story_pkg, name) is getattr(campaign_act3, name)
    assert "CINEMATIC_SKIP_AUDIO_FADE_MS" in story_pkg.__all__
    assert story_pkg.CINEMATIC_SKIP_AUDIO_FADE_MS is cinematic_player.CINEMATIC_SKIP_AUDIO_FADE_MS
