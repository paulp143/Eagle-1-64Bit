"""Tests for campaign_session helpers: mission config mapping and combat telemetry snapshots."""

import copy
import math
from types import SimpleNamespace

import pygame
import pytest

from eagle1.story.campaign_act1 import ACT1_CHOICE_OBJECTIVES
from eagle1.story.campaign_act2 import BRAKER_UNIT_INDEX, get_sortie4_casualty_check_banter
from eagle1.story.campaign_save import CampaignSaveManager
from eagle1.story.campaign_session import (
    BOMB_500KG_STRIKE_TYPE,
    CAMPAIGN_SORTIE_CONFIG_KEY,
    DIALOGUE_CHOICE_KEYS,
    CampaignSortieSession,
    build_campaign_mission_config,
    build_combat_telemetry,
)
from eagle1.story.comms_hud import CommsHUD
from eagle1.story.mission_controller import CAMPAIGN_SORTIE_REGISTRY
from eagle1.story.story_manager import StoryManager
from eagle1.systems.ground_support import AirStrikeType, GroundSupportManager

BASE_CONFIGS = {
    "air_superiority": {"id": "air_superiority", "name": "AIR SUPERIORITY", "has_ground": False,
                        "has_fabricators": False, "max_waves": 5},
    "base_defense": {"id": "base_defense", "name": "ORBITAL BASE DEFENSE", "has_ground": False,
                     "has_fabricators": False, "max_waves": 5},
    "outpost_demolition": {"id": "outpost_demolition", "name": "OUTPOST DEMOLITION", "has_ground": True,
                           "has_fabricators": True, "max_waves": 6, "target_fabs": 3},
    "strider_raid": {"id": "strider_raid", "name": "FACTORY STRIDER RAID", "has_ground": True,
                     "has_fabricators": False, "has_strider": True, "max_waves": 1},
}


def test_bomb_500kg_constant_matches_ground_support():
    assert BOMB_500KG_STRIKE_TYPE == AirStrikeType.BOMB_500KG


@pytest.mark.parametrize("sortie_num", [1, 2, 3, 4])
def test_build_mission_config_per_sortie(sortie_num):
    cfg = CAMPAIGN_SORTIE_REGISTRY[sortie_num]
    config = build_campaign_mission_config(cfg, BASE_CONFIGS)
    assert config["id"] == cfg.mission_mode
    assert config["name"] == cfg.title
    assert config[CAMPAIGN_SORTIE_CONFIG_KEY] == sortie_num
    if sortie_num == 4:
        assert config["max_waves"] == 1  # strider_raid is not wave driven
    else:
        assert config["max_waves"] == cfg.target_waves


def test_build_mission_config_sets_fabricator_target_for_sortie3():
    config = build_campaign_mission_config(CAMPAIGN_SORTIE_REGISTRY[3], BASE_CONFIGS)
    assert config["target_fabs"] == 3


def test_build_mission_config_does_not_mutate_base():
    snapshot = copy.deepcopy(BASE_CONFIGS)
    build_campaign_mission_config(CAMPAIGN_SORTIE_REGISTRY[1], BASE_CONFIGS)
    assert BASE_CONFIGS == snapshot


def test_build_mission_config_rejects_invalid():
    with pytest.raises(TypeError):
        build_campaign_mission_config(None, BASE_CONFIGS)
    with pytest.raises(ValueError):
        build_campaign_mission_config(CAMPAIGN_SORTIE_REGISTRY[1], {})
    with pytest.raises(ValueError):
        build_campaign_mission_config(CAMPAIGN_SORTIE_REGISTRY[1], None)


def test_telemetry_without_gsm():
    snap = build_combat_telemetry(5.0, 2, 7, None)
    assert snap.current_wave == 2
    assert snap.aerial_kills == 7
    assert snap.casualties_count == 0
    assert snap.boss_active is False


def test_telemetry_from_default_gsm():
    gsm = GroundSupportManager()
    snap = build_combat_telemetry(0.0, 1, 0, gsm)
    assert snap.helldivers_alive == 4
    assert snap.casualties_count == 0
    assert snap.fabricators_remaining == 1
    assert snap.boss_active is False


def test_telemetry_counts_casualties_and_critical():
    gsm = GroundSupportManager()
    gsm.units[0].health = 0.0
    gsm.units[0].state = "DOWNED"
    gsm.units[1].health = gsm.units[1].max_health * 0.2
    gsm.units[2].state = "EXTRACTED"
    snap = build_combat_telemetry(0.0, 1, 0, gsm)
    assert snap.casualties_count == 1  # extracted is not a loss
    assert snap.helldivers_alive == 2
    assert snap.any_helldiver_critical is True


def test_telemetry_boss_ratio():
    gsm = GroundSupportManager()
    gsm._spawn_world({"has_ground": True, "has_strider": True})
    gsm.factory_strider.health = gsm.factory_strider.max_health * 0.4
    snap = build_combat_telemetry(0.0, 1, 0, gsm)
    assert snap.boss_active is True
    assert snap.boss_hp_ratio == pytest.approx(0.4)


def test_telemetry_500kg_inbound():
    gsm = GroundSupportManager()
    gsm.active_strikes = [SimpleNamespace(type=BOMB_500KG_STRIKE_TYPE)]
    assert build_combat_telemetry(0.0, 1, 0, gsm).active_500kg_inbound is True
    gsm.active_strikes = [SimpleNamespace(type="napalm")]
    assert build_combat_telemetry(0.0, 1, 0, gsm).active_500kg_inbound is False


def test_telemetry_tolerates_garbage_gsm():
    gsm = SimpleNamespace(
        units="x",
        enemy_fabricators=None,
        factory_strider=SimpleNamespace(is_alive=True, health="?", max_health=0),
    )
    snap = build_combat_telemetry(0.0, 1, 0, gsm)
    assert snap.boss_hp_ratio == 1.0
    assert snap.casualties_count == 0


def test_telemetry_sanitizes_elapsed():
    snap = build_combat_telemetry(float("nan"), 1, 0, None)
    assert snap.elapsed_seconds == 0.0
    assert not math.isnan(snap.elapsed_seconds)


# --- CampaignSortieSession -------------------------------------------------------------

FRAME_DT = 1.0 / 60.0
MAX_PUMP_FRAMES = 6000


@pytest.fixture
def story(tmp_path):
    return StoryManager(save_manager=CampaignSaveManager(data_dir=tmp_path))


@pytest.fixture
def hud(story):
    return CommsHUD(story_manager=story)


@pytest.fixture
def session(story, hud):
    return CampaignSortieSession(story_manager=story, comms_hud=hud)


def _key(key):
    return pygame.event.Event(pygame.KEYDOWN, key=key, mod=0, unicode="")


def _pump(session, hud, predicate, gsm=None, wave=2, kills=10):
    for _ in range(MAX_PUMP_FRAMES):
        session.update(FRAME_DT, wave, kills, gsm)
        hud.update(FRAME_DT)
        if predicate():
            return True
    return False


def test_session_registers_act1_and_act2_triggers(session):
    for sortie_num in range(1, 5):
        assert len(session.trigger_manager.get_triggers_for_sortie(sortie_num)) > 0
    assert session.is_flight_active is False


def test_session_rejects_invalid_story_manager():
    with pytest.raises(TypeError):
        CampaignSortieSession(None)


def test_launch_sortie_uses_story_progress(story, session):
    story.advance_sortie(act=1, sortie=2)
    cfg = session.launch_sortie()
    assert cfg.sortie_num == 2
    assert session.active_sortie_num == 2
    assert session.trigger_manager.active_sortie_num == 2
    assert session.mission_controller.is_sortie_active is True
    assert session.get_objective_text() == cfg.initial_objective


def test_update_inactive_returns_empty(session):
    assert session.update(FRAME_DT, 5, 50) == ()


def test_update_fires_sortie1_checkin(session):
    session.launch_sortie(1)
    for _ in range(150):
        session.update(FRAME_DT, 1, 0)
    assert "act1_s1_checkin_eagle" in session.trigger_manager.fired_trigger_ids
    assert session.flight_seconds == pytest.approx(2.5)


@pytest.mark.parametrize("bad_dt", [float("nan"), -1.0, True])
def test_update_sanitizes_dt(session, bad_dt):
    session.launch_sortie(1)
    session.update(bad_dt, 1, 0)
    assert session.flight_seconds == 0.0


def test_dialogue_keys_reserved_during_typewriter(story, hud, session):
    session.launch_sortie(1)
    assert _pump(session, hud, lambda: story.is_dialogue_active)
    assert hud.is_waiting_for_choice is False
    assert session.handle_comms_keydown(_key(pygame.K_1)) is True
    assert story.is_dialogue_active is True
    assert len(story.dialogue_history) == 0
    assert session.handle_comms_keydown(_key(pygame.K_4)) is False


def test_choice_routes_act1_objective(story, hud, session):
    session.launch_sortie(1)
    assert _pump(session, hud, lambda: story.is_dialogue_active and hud.is_waiting_for_choice)
    assert session.handle_comms_keydown(_key(pygame.K_3)) is True
    assert story.dialogue_history[-1]["stance"] == "dissident"
    assert session.get_objective_text() == ACT1_CHOICE_OBJECTIVES["sortie_1_inflight"]["dissident"]


def test_choice_routes_sortie3_consequence_with_gsm(story, hud, session):
    story.advance_sortie(act=2, sortie=3)
    gsm = GroundSupportManager()
    gsm._spawn_world({"has_ground": True, "has_fabricators": True})
    session.launch_sortie()
    assert _pump(session, hud, lambda: story.is_dialogue_active and hud.is_waiting_for_choice, gsm=gsm)
    assert session.handle_comms_keydown(_key(pygame.K_1), gsm) is True
    braker = next(u for u in gsm.units if u.index == BRAKER_UNIT_INDEX)
    assert braker.is_alive is False
    assert story.extra["act2_sortie3_500kg"]["braker_survived"] is False


def test_choice_not_resolved_outside_flight(session):
    assert session.resolve_choice("sortie_1_inflight", "loyal") is None


@pytest.mark.parametrize("event", [pygame.event.Event(pygame.KEYUP, key=pygame.K_1), SimpleNamespace()])
def test_non_keydown_event_ignored(session, event):
    assert session.handle_comms_keydown(event) is False


def test_dialogue_choice_keys_constant():
    assert {pygame.K_1, pygame.K_2, pygame.K_3} <= DIALOGUE_CHOICE_KEYS
    assert pygame.K_4 not in DIALOGUE_CHOICE_KEYS


def test_restart_flight_resets_without_advancing(story, session):
    session.launch_sortie(1)
    for _ in range(150):
        session.update(FRAME_DT, 1, 0)
    assert session.restart_flight() is not None
    assert session.trigger_manager.fired_trigger_ids == set()
    assert story.current_sortie == 1
    assert session.flight_seconds == 0.0
    assert session.is_flight_active is True
    fresh = CampaignSortieSession(story_manager=story)
    assert fresh.restart_flight() is None


def test_abort_flight(story, session):
    story.advance_sortie(act=1, sortie=2)
    session.launch_sortie()
    session.abort_flight()
    assert session.is_flight_active is False
    assert session.mission_controller.is_sortie_active is False
    assert story.current_sortie == 2
    assert session.get_objective_text() == ""
    session.abort_flight()


def test_complete_sortie_advances_progress(story, session):
    session.launch_sortie(1)
    res = session.complete_sortie({"casualties_count": 1, "squad_wiped": False, "hull_ratio": 0.5})
    assert res["completed_sortie"] == 1
    assert res["next_sortie"] == 2
    assert res["casualties_count"] == 1
    assert story.current_sortie == 2
    assert session.complete_sortie({}) == {}


def test_complete_sortie_without_results(session):
    session.launch_sortie(1)
    res = session.complete_sortie(None)
    assert res["casualties_count"] == 0
    assert res["hull_ratio"] == 1.0


def test_completed_campaign_launch_is_replay(story, session):
    story.advance_sortie(act=3, sortie=4)
    cfg = session.launch_sortie()
    assert cfg.sortie_num == 4
    assert session.is_replay is True
    assert story.current_act == 3
    assert session.complete_sortie({}) == {}
    assert story.current_act == 3


def test_extraction_sets_objective_and_sortie4_casualty_check(story, hud, session):
    story.advance_sortie(act=2, sortie=4)
    gsm = GroundSupportManager()
    gsm._spawn_world({"has_ground": True, "has_strider": True})
    session.launch_sortie()
    gsm.objective_phase = "EXTRACTION"
    expected = get_sortie4_casualty_check_banter(0, True).text
    assert _pump(
        session,
        hud,
        lambda: hud.is_active and hud.current_node is not None and hud.current_node.prompt == expected,
        gsm=gsm,
        wave=1,
        kills=0,
    )
    assert session.get_objective_text() == CAMPAIGN_SORTIE_REGISTRY[4].extraction_objective


def test_extraction_without_hud_drops_casualty_check(story):
    story.advance_sortie(act=2, sortie=4)
    session = CampaignSortieSession(story_manager=story, comms_hud=None)
    gsm = GroundSupportManager()
    gsm.objective_phase = "EXTRACTION"
    session.launch_sortie()
    session.update(FRAME_DT, 1, 0, gsm)
    assert session._casualty_check_pending is False


def test_bind_story_manager_rebinds(story, tmp_path, session):
    other = StoryManager(save_manager=CampaignSaveManager(data_dir=tmp_path / "other"))
    session.launch_sortie(1)
    session.bind_story_manager(other)
    assert session.story_manager is other
    assert session.is_flight_active is False
    assert session.trigger_manager.story_manager is other
