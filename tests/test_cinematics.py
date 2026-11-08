import inspect

import pygame
import pytest

import eagle1.app.game as game_module
from eagle1.story import CampaignSortieSession, StoryManager
from eagle1.story.campaign_act3 import (
    ACT3_OUTRO_SECONDS,
    SORTIE5A_TRENCH_NODE_ID,
    SORTIE5C_ABORT_NODE_ID,
    build_act3c_cinematic_sequence,
    build_act3c_epilogue_stats,
)
from eagle1.story.campaign_save import CampaignSaveManager
from eagle1.story.cinematic_player import CINEMATIC_SKIP_AUDIO_FADE_MS, CinematicPlayer
from eagle1.story.story_manager import BRANCH_COLD_PROTOCOL, BRANCH_OBEDIENCE_PURGE
from eagle1.systems.audio_manager import DEFAULT_CINEMATIC_FADE_MS, AudioManager


class _FakeAudio:
    """Records audio calls made by CinematicPlayer; optionally lacks stop_cinematic_audio."""

    def __init__(self, with_stop=True, stop_error=None):
        self.sfx = []
        self.music = []
        self.stops = []
        self._stop_error = stop_error
        if with_stop:
            self.stop_cinematic_audio = self._stop_cinematic_audio

    def play_sfx(self, name, volume_scale=1.0, custom_channel=None):
        self.sfx.append(name)

    def play_music(self, track_name, loop=True, fade_ms=400):
        self.music.append(track_name)

    def stop_music(self, fade_ms=500):
        self.music.append(("stop", fade_ms))

    def _stop_cinematic_audio(self, fade_ms=DEFAULT_CINEMATIC_FADE_MS):
        if self._stop_error is not None:
            raise self._stop_error
        self.stops.append(fade_ms)


def _act3c_player(audio):
    player = CinematicPlayer(1280, 720, audio_manager=audio)
    player.start_sequence(build_act3c_cinematic_sequence(), build_act3c_epilogue_stats(None))
    return player


def _space():
    return pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE, mod=0, unicode=" ")


# ---------------------------------------------------------------- Task 3: cinematic audio cleanup

@pytest.fixture
def mixer_audio(monkeypatch):
    """AudioManager with the mixer faked as initialised; records fadeout/stop/stop_music/stop_engine calls."""
    audio = AudioManager()
    audio.enabled = True
    calls = {"fadeout": [], "stop": 0, "stop_music": [], "engine": 0}
    monkeypatch.setattr(pygame.mixer, "get_init", lambda: (44100, -16, 2))

    def fake_fadeout(ms):
        calls["fadeout"].append(ms)

    def fake_stop():
        calls["stop"] += 1

    monkeypatch.setattr(pygame.mixer, "fadeout", fake_fadeout)
    monkeypatch.setattr(pygame.mixer, "stop", fake_stop)
    monkeypatch.setattr(audio, "stop_music", lambda fade_ms=500: calls["stop_music"].append(fade_ms))
    monkeypatch.setattr(audio, "stop_engine_sound", lambda: calls.__setitem__("engine", calls["engine"] + 1))
    audio.calls = calls
    return audio


def test_stop_cinematic_audio_fades_channels_music_and_engine(mixer_audio):
    mixer_audio.stop_cinematic_audio(600)
    assert mixer_audio.calls["fadeout"] == [600]
    assert mixer_audio.calls["stop_music"] == [600]
    assert mixer_audio.calls["engine"] == 1
    assert mixer_audio.calls["stop"] == 0


@pytest.mark.parametrize("fade", [0, -5])
def test_stop_cinematic_audio_zero_fade_hard_stops(mixer_audio, fade):
    mixer_audio.stop_cinematic_audio(fade)
    assert mixer_audio.calls["stop"] == 1
    assert mixer_audio.calls["fadeout"] == []
    assert mixer_audio.calls["stop_music"] == [0]


@pytest.mark.parametrize("fade", [float("nan"), True, "x", None])
def test_stop_cinematic_audio_invalid_fade_uses_default(mixer_audio, fade):
    mixer_audio.stop_cinematic_audio(fade)
    assert mixer_audio.calls["fadeout"] == [DEFAULT_CINEMATIC_FADE_MS]


def test_stop_cinematic_audio_disabled_is_noop(mixer_audio):
    mixer_audio.enabled = False
    mixer_audio.stop_cinematic_audio(600)
    assert mixer_audio.calls == {"fadeout": [], "stop": 0, "stop_music": [], "engine": 0}


def test_stop_cinematic_audio_survives_mixer_error(mixer_audio, monkeypatch):
    def broken_fadeout(ms):
        raise pygame.error("mixer offline")

    monkeypatch.setattr(pygame.mixer, "fadeout", broken_fadeout)
    mixer_audio.stop_cinematic_audio(600)
    assert mixer_audio.calls["stop_music"] == [600]


def test_first_frame_skip_stops_cue_audio():
    audio = _FakeAudio()
    player = _act3c_player(audio)
    player.handle_event(_space())
    assert player.is_epilogue
    assert audio.stops == [CINEMATIC_SKIP_AUDIO_FADE_MS]
    player.handle_event(_space())
    player.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE, mod=0, unicode=""))
    assert audio.stops == [CINEMATIC_SKIP_AUDIO_FADE_MS]


def test_skip_without_stop_method_still_reaches_epilogue():
    player = _act3c_player(_FakeAudio(with_stop=False))
    player.handle_event(_space())
    assert player.is_epilogue


def test_skip_with_failing_stop_still_reaches_epilogue():
    player = _act3c_player(_FakeAudio(stop_error=pygame.error("mixer offline")))
    player.handle_event(_space())
    assert player.is_epilogue


def test_natural_end_does_not_call_stop():
    audio = _FakeAudio()
    player = _act3c_player(audio)
    total = sum(kf.duration for kf in player.sequence.keyframes)
    for _ in range(int(total * 60) + 120):
        player.update(1.0 / 60.0)
        if player.is_epilogue:
            break
    assert player.is_epilogue
    assert audio.stops == []


# ---------------------------------------------------------------- Task 5: "cinematic" game state

FRAME_DT = 1.0 / 60.0


def _make_finale_story(data_dir, branch, loyalty):
    story = StoryManager(save_manager=CampaignSaveManager(data_dir=data_dir))
    story.loyalty = loyalty
    story.extra["act2_completed"] = True
    story.extra["ending_branch"] = branch
    story.extra["completed_sorties"] = [1, 2, 3, 4]
    story.advance_sortie(act=3, sortie=4)
    return story


@pytest.fixture
def game(monkeypatch, tmp_path):
    """Game module bound to an isolated finale StoryManager; audio fades are recorded, not played."""
    story = _make_finale_story(tmp_path, BRANCH_COLD_PROTOCOL, 55.0)
    session = CampaignSortieSession(story_manager=story, comms_hud=game_module.comms_hud)
    fades = []
    monkeypatch.setattr(game_module, "story_manager", story)
    monkeypatch.setattr(game_module, "campaign_session", session)
    monkeypatch.setattr(game_module.comms_hud, "story_manager", story)
    monkeypatch.setattr(game_module.super_destroyer_view, "story_manager", story)
    monkeypatch.setattr(game_module.ground_support_manager, "story_manager", story)
    monkeypatch.setattr(game_module, "add_highscore", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        game_module.audio_manager, "stop_cinematic_audio",
        lambda fade_ms=DEFAULT_CINEMATIC_FADE_MS: fades.append(fade_ms),
    )
    game_module.comms_hud.dismiss()
    game_module.player.health = game_module.player.max_health
    game_module.game_state = "main_menu"
    game_module.cinematic_player.reset()
    monkeypatch.setattr(game_module, "fades", fades, raising=False)
    yield game_module
    game_module.comms_hud.dismiss()
    game_module.cinematic_player.reset()
    game_module.super_destroyer_view.set_act3_briefing(None, None)
    game_module.game_state = "main_menu"


def _start_flight(g, loyalty):
    g.story_manager.loyalty = loyalty
    session = g.get_campaign_session()
    session.launch_sortie()
    return session


def _key(key):
    return pygame.event.Event(pygame.KEYDOWN, key=key, mod=0, unicode="")


def test_get_campaign_session_attaches_player(game):
    assert game.get_campaign_session().player is game.player


def test_start_campaign_finale_enters_cinematic(game):
    _start_flight(game, 55.0)
    assert game.start_campaign_finale() == BRANCH_COLD_PROTOCOL
    assert game.game_state == "cinematic"
    assert game.cinematic_player.is_playing
    assert game.get_campaign_session().is_flight_active is False
    assert game.comms_hud.is_active is False
    assert game.fades == [600]
    assert game.start_campaign_finale() is None
    assert game.game_state == "cinematic"


def test_handle_cinematic_keydown_skip_then_confirm(game):
    _start_flight(game, 55.0)
    game.start_campaign_finale()
    assert game.handle_cinematic_keydown(_key(pygame.K_SPACE)) is False
    assert game.cinematic_player.is_epilogue
    game.cinematic_player.update(0.5)
    assert game.handle_cinematic_keydown(_key(pygame.K_RETURN)) is True
    assert game.game_state == "main_menu"
    assert game.story_manager.extra["campaign_finale_completed"] is True
    assert game.cinematic_player.phase == "idle"
    assert game.fades == [600, 250, 400]


def test_epilogue_confirm_is_delayed(game):
    _start_flight(game, 55.0)
    game.start_campaign_finale()
    game.handle_cinematic_keydown(_key(pygame.K_SPACE))
    assert game.handle_cinematic_keydown(_key(pygame.K_RETURN)) is False
    assert game.game_state == "cinematic"


def test_finish_clears_residual_input(game):
    _start_flight(game, 55.0)
    game.start_campaign_finale()
    game.handle_cinematic_keydown(_key(pygame.K_SPACE))
    game.cinematic_player.update(0.5)
    pygame.event.post(_key(pygame.K_SPACE))
    game.finish_campaign_finale()
    assert pygame.event.peek(pygame.KEYDOWN) is False


def test_check_transition_requires_act3_flight(game):
    game.game_state = ""
    assert game.check_act3_finale_transition() is False
    game.get_campaign_session().launch_sortie()  # Act III flight, climax not resolved yet
    assert game.check_act3_finale_transition() is False
    assert game.game_state == ""


def test_check_transition_after_outro(game):
    story = game.story_manager
    story.loyalty = 95.0
    story.extra["ending_branch"] = BRANCH_OBEDIENCE_PURGE
    session = game.get_campaign_session()
    session.launch_sortie()
    session.resolve_choice(SORTIE5A_TRENCH_NODE_ID, "neutral", None)
    for _ in range(round((ACT3_OUTRO_SECONDS + 0.1) / FRAME_DT)):
        session.update(FRAME_DT, 1, 0, None)
    game.game_state = ""
    assert game.check_act3_finale_transition() is True
    assert game.game_state == "cinematic"


def test_player_death_before_resolution_is_game_over(game):
    _start_flight(game, 55.0)
    game.game_state = ""
    game.player.health = 0
    assert game.check_act3_finale_transition() is False
    assert game.game_state == ""


def test_player_death_after_resolution_starts_finale(game):
    session = _start_flight(game, 55.0)
    session.resolve_choice(SORTIE5C_ABORT_NODE_ID, "neutral", None)
    game.game_state = ""
    game.player.health = 0
    assert game.check_act3_finale_transition() is True
    assert game.game_state == "cinematic"


def test_trigger_mission_complete_ignored_in_act3_flight(game):
    _start_flight(game, 55.0)
    game.game_state = ""
    game.trigger_mission_complete()
    assert game.game_state == ""


def test_run_game_routes_cinematic_state(game):
    source = inspect.getsource(game.run_game)
    assert "handle_cinematic_keydown(event)" in source
    assert "cinematic_player.update(1.0 / 60.0)" in source
    assert "cinematic_player.draw(canvas)" in source
    assert "check_act3_finale_transition()" in source
