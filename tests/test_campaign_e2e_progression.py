"""End-to-end campaign progression tests: hub launch -> in-flight beats -> debrief -> hub (Sorties 1-4)."""

import inspect
from unittest.mock import MagicMock

import pygame
import pytest

import eagle1.app.game as game_module
from eagle1.story import (
    CAMPAIGN_SORTIE_REGISTRY,
    SORTIE_BRIEFING_METADATA,
    CampaignSaveManager,
    CampaignSortieSession,
    StoryManager,
)
from eagle1.story.campaign_act1 import ACT1_CHOICE_OBJECTIVES
from eagle1.story.campaign_act2 import ACT2_CHOICE_OBJECTIVES, BRAKER_UNIT_INDEX

FRAME_DT = 1.0 / 60.0
MAX_PUMP_FRAMES = 6000
INFLIGHT_NODE_BY_SORTIE = {
    1: "sortie_1_inflight",
    2: "sortie_2_inflight",
    3: "sortie_3_500kg_crisis",
    4: "sortie_4_strider_crisis",
}


@pytest.fixture
def game(monkeypatch, tmp_path):
    """Bind the game module to an isolated StoryManager and campaign session (never touches data/)."""
    story = StoryManager(save_manager=CampaignSaveManager(data_dir=tmp_path))
    session = CampaignSortieSession(story_manager=story, comms_hud=game_module.comms_hud)
    monkeypatch.setattr(game_module, "story_manager", story)
    monkeypatch.setattr(game_module, "campaign_session", session)
    monkeypatch.setattr(game_module.comms_hud, "story_manager", story)
    monkeypatch.setattr(game_module.super_destroyer_view, "story_manager", story)
    monkeypatch.setattr(game_module.ground_support_manager, "story_manager", story)
    monkeypatch.setattr(game_module, "add_highscore", lambda *args, **kwargs: None)
    game_module.comms_hud.dismiss()
    game_module.player.score = 0
    game_module.game_state = "main_menu"
    yield game_module
    game_module.comms_hud.dismiss()
    game_module.game_state = "main_menu"


def _launch_from_hub(g):
    g.enter_super_destroyer()
    g.handle_super_destroyer_action(g.super_destroyer_view.trigger_catapult_launch())


def _press(g, key):
    event = pygame.event.Event(pygame.KEYDOWN, key=key, mod=0, unicode="")
    return g.get_campaign_session().handle_comms_keydown(event, g.ground_support_manager)


def _pump(g, predicate, wave=2, kills=10):
    session = g.get_campaign_session()
    for _ in range(MAX_PUMP_FRAMES):
        session.update(FRAME_DT, wave, kills, g.ground_support_manager)
        g.comms_hud.update(FRAME_DT)
        if predicate():
            return True
    return False


def _awaiting_choice(g):
    return lambda: g.story_manager.is_dialogue_active and g.comms_hud.is_waiting_for_choice


@pytest.mark.parametrize("sortie_num", [1, 2, 3, 4])
def test_hub_launch_starts_each_sortie_with_campaign_config(game, sortie_num):
    cfg = CAMPAIGN_SORTIE_REGISTRY[sortie_num]
    if sortie_num > 1:
        game.story_manager.advance_sortie(act=cfg.act, sortie=sortie_num)
    _launch_from_hub(game)

    assert game.game_state == ""
    assert game.active_mission_config["id"] == cfg.mission_mode
    assert game.active_mission_config["campaign_sortie"] == sortie_num
    assert game.active_mission_config["name"] == cfg.title
    assert game.get_campaign_session().active_sortie_num == sortie_num
    assert game.get_campaign_session().get_objective_text() == cfg.initial_objective
    if sortie_num <= 3:
        assert game.active_mission_config["max_waves"] == cfg.target_waves
    else:
        assert game.ground_support_manager.factory_strider is not None


def test_hub_launch_ignores_stale_mission_id(game):
    game.enter_super_destroyer()
    game.handle_super_destroyer_action({"action": "launch_sortie", "mission_id": "strider_raid"})
    assert game.active_mission_config["id"] == "air_superiority"


def test_replay_respawn_resets_triggers_without_advancing(game):
    _launch_from_hub(game)
    session = game.get_campaign_session()
    assert _pump(game, _awaiting_choice(game))

    game.respawn()

    assert session.is_flight_active is True
    assert session.trigger_manager.fired_trigger_ids == set()
    assert game.story_manager.current_sortie == 1
    assert game.story_manager.is_dialogue_active is False
    assert session.mission_controller.is_sortie_active is True


def test_arcade_respawn_aborts_campaign_flight(game):
    _launch_from_hub(game)
    session = game.get_campaign_session()

    game.respawn(game.MISSION_CONFIGS[game.MissionType.ENDLESS_WAR])

    assert session.is_flight_active is False
    assert session.mission_controller.is_sortie_active is False
    assert game.story_manager.current_sortie == 1


def test_get_campaign_session_rebinds_on_story_swap(game, monkeypatch, tmp_path):
    other = StoryManager(save_manager=CampaignSaveManager(data_dir=tmp_path / "swap"))
    monkeypatch.setattr(game, "story_manager", other)
    assert game.get_campaign_session().story_manager is other


def _wound_strider(g):
    strider = g.ground_support_manager.factory_strider
    if strider is not None:
        strider.health = strider.max_health * 0.4


def _normalize(text):
    return " ".join(text.split())


def test_full_campaign_progression_sorties_1_to_4(game):
    for sortie_num in range(1, 5):
        cfg = CAMPAIGN_SORTIE_REGISTRY[sortie_num]
        game.enter_super_destroyer()
        assert game.super_destroyer_view.get_current_sortie_briefing()["title"] == cfg.title
        _launch_from_hub(game)
        if sortie_num == 4:
            _wound_strider(game)
        assert _pump(game, _awaiting_choice(game))

        node_id = INFLIGHT_NODE_BY_SORTIE[sortie_num]
        assert game.story_manager.active_dialogue.node_id == node_id
        for _ in range(60):
            game.comms_hud.update(FRAME_DT)
        assert game.comms_hud.get_time_dilation() == pytest.approx(0.4, abs=0.01)

        slot_before = game.ground_support_manager.equipped_slot
        assert _press(game, pygame.K_2) is True
        assert game.ground_support_manager.equipped_slot == slot_before
        assert game.story_manager.dialogue_history[-1]["node"] == node_id
        assert game.story_manager.dialogue_history[-1]["stance"] == "neutral"
        objectives = ACT1_CHOICE_OBJECTIVES if sortie_num <= 2 else ACT2_CHOICE_OBJECTIVES
        expected = objectives[node_id]["neutral"]
        assert _normalize(game.get_campaign_session().get_objective_text()) == _normalize(expected)

        game.trigger_mission_complete()
        assert game.game_state == "mission_debriefing"
        progression = game.return_to_super_destroyer_from_debrief()
        assert game.game_state == "super_destroyer"
        assert progression["completed_sortie"] == sortie_num
        if sortie_num < 4:
            assert game.story_manager.current_sortie == sortie_num + 1
        else:
            assert progression["campaign_completed"] is True
            assert game.story_manager.current_act == 3
    assert game.story_manager.extra["completed_sorties"] == [1, 2, 3, 4]


def test_dialogue_keys_do_not_leak_during_typewriter(game):
    _launch_from_hub(game)
    assert _pump(game, lambda: game.story_manager.is_dialogue_active)
    assert game.comms_hud.is_waiting_for_choice is False
    assert _press(game, pygame.K_1) is True
    assert len(game.story_manager.dialogue_history) == 0
    assert _press(game, pygame.K_5) is False


def test_run_game_routes_keydown_through_campaign_session(game):
    source = inspect.getsource(game.run_game)
    assert "get_campaign_session().handle_comms_keydown(event, ground_support_manager)" in source
    assert "return_to_super_destroyer_from_debrief()" in source


def test_move_feeds_campaign_session_each_frame(game, monkeypatch):
    _launch_from_hub(game)
    game.game_state = ""
    mock_update = MagicMock(return_value=())
    monkeypatch.setattr(game.campaign_session, "update", mock_update)
    game.move()
    mock_update.assert_called_once()
    args = mock_update.call_args.args
    assert args[0] == pytest.approx(FRAME_DT)
    assert args[1] == game.wave_manager.wave
    assert args[2] == game.mission_air_kills + game.mission_bomber_kills
    assert args[3] is game.ground_support_manager


def test_move_skips_campaign_session_in_arcade(game, monkeypatch):
    game.respawn(game.MISSION_CONFIGS[game.MissionType.ENDLESS_WAR])
    game.game_state = ""
    mock_update = MagicMock(return_value=())
    monkeypatch.setattr(game.campaign_session, "update", mock_update)
    game.move()
    mock_update.assert_not_called()


def test_sortie3_loyal_choice_kills_braker_live(game):
    game.story_manager.advance_sortie(act=2, sortie=3)
    _launch_from_hub(game)
    assert _pump(game, _awaiting_choice(game))
    assert _press(game, pygame.K_1) is True
    braker = next(u for u in game.ground_support_manager.units if u.index == BRAKER_UNIT_INDEX)
    assert braker.is_alive is False
    assert game.story_manager.total_casualties == 1
    assert game.story_manager.extra["act2_sortie3_500kg"]["braker_survived"] is False


def test_hub_reflects_progression_after_return(game):
    _launch_from_hub(game)
    game.trigger_mission_complete()
    game.debriefing_screen.set_results({"casualties_count": 1, "survivors_count": 3, "hull_ratio": 0.5})
    progression = game.return_to_super_destroyer_from_debrief()
    assert progression["casualties_count"] == 1
    assert game.super_destroyer_view.get_ready_room_morale_state() == "casualties"
    assert game.super_destroyer_view.aircraft_hull_ratio == pytest.approx(0.5)
    assert game.super_destroyer_view.get_current_sortie_briefing()["title"] == CAMPAIGN_SORTIE_REGISTRY[2].title
    assert game.super_destroyer_view.resolve_npc_dialogue("npc_reiner").node_id == "bridge_reiner_scrutiny"


def test_arcade_debrief_return_does_not_advance(game):
    _launch_from_hub(game)
    game.respawn(game.MISSION_CONFIGS[game.MissionType.ENDLESS_WAR])
    game.trigger_mission_complete()
    assert game.return_to_super_destroyer_from_debrief() == {}
    assert game.story_manager.current_sortie == 1


def test_completed_campaign_relaunch_is_replay(game):
    game.story_manager.advance_sortie(act=3, sortie=4)
    _launch_from_hub(game)
    assert game.get_campaign_session().is_replay is True
    assert game.active_mission_config["id"] == "strider_raid"
    assert game.story_manager.current_act == 3
    game.trigger_mission_complete()
    assert game.return_to_super_destroyer_from_debrief() == {}
    assert game.story_manager.current_act == 3


def test_air_superiority_debrief_has_no_phantom_casualties(game):
    _launch_from_hub(game)
    game.ground_support_manager.update(
        FRAME_DT, game.player, [], game.explosion_group, game.large_explosion_a_spritesheet.frames
    )
    game.trigger_mission_complete()
    assert game.debriefing_screen.results["casualties_count"] == 0
    assert game.debriefing_screen.results["squad_wiped"] is False


def test_extracted_helldivers_are_not_casualties(game):
    game.story_manager.advance_sortie(act=2, sortie=3)
    _launch_from_hub(game)
    for unit in game.ground_support_manager.units:
        unit.state = "EXTRACTED"
    game.ground_support_manager.units[0].state = "DOWNED"
    game.ground_support_manager.units[0].health = 0.0
    game.ground_support_manager.survivors_count = 3
    game.trigger_mission_complete()
    assert game.debriefing_screen.results["casualties_count"] == 1
    assert game.debriefing_screen.results["squad_wiped"] is False


@pytest.mark.parametrize("sortie_num", [1, 2, 3, 4])
def test_sortie_registry_matches_hub_briefing_metadata(sortie_num):
    assert SORTIE_BRIEFING_METADATA[sortie_num] == CAMPAIGN_SORTIE_REGISTRY[sortie_num].to_briefing_dict()
