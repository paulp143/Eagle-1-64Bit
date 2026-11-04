"""End-to-end campaign progression tests: hub launch -> in-flight beats -> debrief -> hub (Sorties 1-4)."""

import pygame
import pytest

import eagle1.app.game as game_module
from eagle1.story import CAMPAIGN_SORTIE_REGISTRY, CampaignSaveManager, CampaignSortieSession, StoryManager

FRAME_DT = 1.0 / 60.0
MAX_PUMP_FRAMES = 6000


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
