"""Headless tests for the Act III finale: cinematic audio cleanup, game state wiring and E2E flow (#77)."""

import pygame
import pytest

from eagle1.story.campaign_act3 import build_act3c_cinematic_sequence, build_act3c_epilogue_stats
from eagle1.story.cinematic_player import CINEMATIC_SKIP_AUDIO_FADE_MS, CinematicPlayer
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
