"""Tests for eagle1.story.cinematic_player (cutscene sequencer, letterbox subtitles, epilogue)."""

import dataclasses

import pygame
import pytest

from eagle1.story.cinematic_player import (
    CINEMATIC_ACTION_RETURN_MAIN_MENU,
    CINEMATIC_LETTERBOX_HEIGHT,
    CINEMATIC_PHASE_EPILOGUE,
    CINEMATIC_PHASE_FINISHED,
    CINEMATIC_PHASE_IDLE,
    CINEMATIC_PHASE_PLAYING,
    CINEMATIC_SCENE_EPILOGUE_CARD,
    CINEMATIC_SCENE_HANGAR_CLONES,
    CINEMATIC_SCENE_SUICIDE_DIVE,
    UNKNOWN_PILOT_STATUS,
    VALID_CINEMATIC_SCENE_TYPES,
    CinematicKeyframe,
    CinematicPlayer,
    CinematicSequence,
    CinematicSubtitle,
    EpilogueSummaryStats,
    build_epilogue_stat_lines,
    format_ending_branch_label,
    validate_cinematic_sequence,
    wrap_cinematic_text,
)
from eagle1.story.story_manager import BRANCH_OBEDIENCE_PURGE, DEFAULT_LOYALTY


def _make_sequence(**overrides):
    kf_a = CinematicKeyframe(
        keyframe_id="kf_a",
        duration=2.0,
        scene_type=CINEMATIC_SCENE_SUICIDE_DIVE,
        title_caption="THE LAST DIVE",
        camera_start=(0.0, 0.0, 1.0),
        camera_end=(100.0, -50.0, 2.0),
        fade_in=0.5,
        fade_out=0.5,
        audio_cue="cue_a",
        subtitles=(CinematicSubtitle(0.2, 1.5, "VIPER-1", "Hold the line, Eagle. We are not leaving."),),
    )
    kf_b = CinematicKeyframe(
        keyframe_id="kf_b",
        duration=1.0,
        scene_type=CINEMATIC_SCENE_HANGAR_CLONES,
        fade_in=0.0,
        fade_out=0.0,
    )
    kf_c = CinematicKeyframe(
        keyframe_id="kf_c",
        duration=1.5,
        scene_type=CINEMATIC_SCENE_EPILOGUE_CARD,
        title_caption="FOR SUPER EARTH",
        audio_cue="music:act3_finale",
    )
    fields = dict(
        sequence_id="seq_test",
        ending_branch=BRANCH_OBEDIENCE_PURGE,
        title="Obedience",
        keyframes=(kf_a, kf_b, kf_c),
        epilogue_lines=("Line one.", "Line two."),
    )
    fields.update(overrides)
    return CinematicSequence(**fields)


def _make_stats(**overrides):
    fields = dict(
        ending_branch=BRANCH_OBEDIENCE_PURGE,
        ending_title="The Purge",
        final_loyalty=87.5,
        total_casualties=6,
        sorties_completed=9,
        pilot_status="mia",
        epilogue_lines=("Stats line.",),
    )
    fields.update(overrides)
    return EpilogueSummaryStats(**fields)


def _single_keyframe_sequence(**kf_overrides):
    fields = dict(
        keyframe_id="kf_only",
        duration=2.0,
        scene_type=CINEMATIC_SCENE_SUICIDE_DIVE,
        fade_in=0.0,
        fade_out=0.0,
    )
    fields.update(kf_overrides)
    return _make_sequence(keyframes=(CinematicKeyframe(**fields),))


def test_keyframe_and_sequence_coerce_lists_to_tuples():
    sub = CinematicSubtitle(0.0, 1.0, "VIPER-2", "Copy.")
    kf = CinematicKeyframe(
        keyframe_id="kf",
        duration=1.0,
        scene_type=CINEMATIC_SCENE_SUICIDE_DIVE,
        camera_start=[1.0, 2.0, 1.0],
        subtitles=[sub],
    )
    seq = CinematicSequence(
        sequence_id="seq",
        ending_branch=BRANCH_OBEDIENCE_PURGE,
        title="T",
        keyframes=[kf],
        epilogue_lines=["a", 3, None, "b"],
    )
    assert kf.camera_start == (1.0, 2.0, 1.0)
    assert kf.subtitles == (sub,)
    assert seq.keyframes == (kf,)
    assert seq.epilogue_lines == ("a", "b")


def test_dataclasses_are_frozen():
    seq = _make_sequence()
    stats = _make_stats()
    with pytest.raises(dataclasses.FrozenInstanceError):
        seq.keyframes[0].duration = 5.0
    with pytest.raises(dataclasses.FrozenInstanceError):
        seq.title = "other"
    with pytest.raises(dataclasses.FrozenInstanceError):
        stats.final_loyalty = 1.0
    with pytest.raises(dataclasses.FrozenInstanceError):
        seq.keyframes[0].subtitles[0].text = "changed"


@pytest.mark.parametrize(
    "raw, expected",
    [
        (True, DEFAULT_LOYALTY),
        (float("nan"), DEFAULT_LOYALTY),
        (float("inf"), DEFAULT_LOYALTY),
        (float("-inf"), DEFAULT_LOYALTY),
        (-5, 0.0),
        (150.0, 100.0),
        ("80", DEFAULT_LOYALTY),
        (42, 42.0),
    ],
)
def test_epilogue_stats_sanitizes_loyalty(raw, expected):
    assert _make_stats(final_loyalty=raw).final_loyalty == expected


@pytest.mark.parametrize(
    "raw, expected",
    [(True, 0), (-3, 0), (float("nan"), 0), (float("inf"), 0), (4.9, 4), ("7", 0), (None, 0), (12, 12)],
)
def test_epilogue_stats_sanitizes_counts(raw, expected):
    stats = _make_stats(total_casualties=raw, sorties_completed=raw)
    assert stats.total_casualties == expected
    assert stats.sorties_completed == expected


def test_epilogue_stats_sanitizes_strings():
    stats = _make_stats(pilot_status=None, ending_branch=5, ending_title="  Title  ", epilogue_lines=None)
    assert stats.pilot_status == "UNKNOWN"
    assert _make_stats(pilot_status="  ").pilot_status == "UNKNOWN"
    assert stats.ending_branch == ""
    assert stats.ending_title == "Title"
    assert stats.epilogue_lines == ()


def test_build_epilogue_stat_lines():
    assert build_epilogue_stat_lines(_make_stats()) == (
        "ENDING: OBEDIENCE PURGE",
        "FINAL LOYALTY: 87.5%",
        "HELLDIVER CASUALTIES: 6",
        "SORTIES COMPLETED: 9",
        "PILOT STATUS: MIA",
    )
    assert build_epilogue_stat_lines(None) == ()


def test_format_ending_branch_label():
    assert format_ending_branch_label("COLD_PROTOCOL") == "COLD PROTOCOL"
    assert format_ending_branch_label("some_branch") == "SOME BRANCH"
    assert format_ending_branch_label(None) == "UNKNOWN"


def test_wrap_cinematic_text_greedy():
    assert wrap_cinematic_text("aaa bbb ccc", 7, len) == ["aaa bbb", "ccc"]
    assert wrap_cinematic_text("  aaa   bbb  ", 20, len) == ["aaa bbb"]


def test_wrap_cinematic_text_hard_splits_long_words():
    assert wrap_cinematic_text("abcdefghij", 4, len) == ["abcd", "efgh", "ij"]
    assert wrap_cinematic_text("xy abcdefghij", 4, len) == ["xy", "abcd", "efgh", "ij"]


@pytest.mark.parametrize("text, width", [(None, 10), ("", 10), ("   ", 10), ("abc", 0), ("abc", -3), ("abc", True)])
def test_wrap_cinematic_text_invalid_input(text, width):
    assert wrap_cinematic_text(text, width, len) == []


def test_validate_accepts_valid_sequence():
    assert validate_cinematic_sequence(_make_sequence()) is True


@pytest.mark.parametrize("bad", [None, "seq", 42, {}])
def test_validate_rejects_non_sequence(bad):
    assert validate_cinematic_sequence(bad) is False


def test_validate_rejects_empty_keyframes():
    assert validate_cinematic_sequence(_make_sequence(keyframes=())) is False


@pytest.mark.parametrize("duration", [0, 0.0, -1.0, float("nan"), float("inf"), True, "2"])
def test_validate_rejects_bad_duration(duration):
    assert validate_cinematic_sequence(_single_keyframe_sequence(duration=duration)) is False


@pytest.mark.parametrize("start, end", [(1.0, 1.0), (1.5, 1.0), (-0.1, 1.0), (0.0, 2.5), (float("nan"), 1.0)])
def test_validate_rejects_bad_subtitle_bounds(start, end):
    sub = CinematicSubtitle(start, end, "VIPER-1", "Text")
    assert validate_cinematic_sequence(_single_keyframe_sequence(subtitles=(sub,))) is False


def test_validate_rejects_blank_subtitle_text():
    sub = CinematicSubtitle(0.0, 1.0, "VIPER-1", "   ")
    assert validate_cinematic_sequence(_single_keyframe_sequence(subtitles=(sub,))) is False


def test_validate_rejects_unknown_scene_type():
    assert validate_cinematic_sequence(_single_keyframe_sequence(scene_type="disco")) is False


def test_validate_rejects_duplicate_keyframe_ids():
    kf = CinematicKeyframe(keyframe_id="dup", duration=1.0, scene_type=CINEMATIC_SCENE_SUICIDE_DIVE,
                           fade_in=0.0, fade_out=0.0)
    assert validate_cinematic_sequence(_make_sequence(keyframes=(kf, kf))) is False


def test_validate_rejects_fades_longer_than_duration():
    assert validate_cinematic_sequence(_single_keyframe_sequence(duration=1.0, fade_in=0.6, fade_out=0.6)) is False


@pytest.mark.parametrize("camera", [(0.0, 0.0, 0.0), (0.0, 0.0, -1.0), (0.0, 0.0), (float("nan"), 0.0, 1.0)])
def test_validate_rejects_bad_camera(camera):
    assert validate_cinematic_sequence(_single_keyframe_sequence(camera_end=camera)) is False


def test_validate_rejects_blank_audio_cue():
    assert validate_cinematic_sequence(_single_keyframe_sequence(audio_cue="  ")) is False


class _FakeAudio:
    def __init__(self, fail=False):
        self.calls = []
        self.fail = fail

    def play_sfx(self, name, volume_scale=1.0, custom_channel=None):
        if self.fail:
            raise pygame.error("mixer offline")
        self.calls.append(("sfx", name))

    def play_music(self, track_name, loop=True, fade_ms=400):
        self.calls.append(("music", track_name, loop, fade_ms))

    def stop_music(self, fade_ms=500):
        self.calls.append(("stop", fade_ms))


def _started_player(audio=None, allow_skip=True, sequence=None, stats=None):
    player = CinematicPlayer(audio_manager=audio)
    player.start_sequence(sequence or _make_sequence(), stats or _make_stats(), allow_skip=allow_skip)
    return player


def test_new_player_is_idle():
    player = CinematicPlayer()
    assert player.phase == CINEMATIC_PHASE_IDLE
    assert player.is_active is False
    assert player.current_keyframe is None
    player.update(1.0)
    assert player.total_elapsed == 0.0


def test_start_fires_first_cue_exactly_once():
    audio = _FakeAudio()
    player = _started_player(audio)
    for _ in range(5):
        player.update(0.0)
    assert player.fired_audio_cues == ["cue_a"]
    assert audio.calls == [("sfx", "cue_a")]
    assert player.phase == CINEMATIC_PHASE_PLAYING
    assert player.keyframe_index == 0


def test_update_advances_within_keyframe():
    player = _started_player()
    player.update(0.5)
    assert player.keyframe_index == 0
    assert player.keyframe_elapsed == pytest.approx(0.5)
    assert player.total_elapsed == pytest.approx(0.5)


def test_large_dt_crosses_multiple_keyframes():
    audio = _FakeAudio()
    player = _started_player(audio)
    player.update(3.25)
    assert player.keyframe_index == 2
    assert player.keyframe_elapsed == pytest.approx(0.25)
    assert player.fired_audio_cues == ["cue_a", "music:act3_finale"]
    assert ("music", "act3_finale", True, 600) in audio.calls


def test_sequence_completion_enters_epilogue_with_leftover():
    player = _started_player()
    player.update(10.0)
    assert player.phase == CINEMATIC_PHASE_EPILOGUE
    assert player.is_active is True
    assert player.epilogue_elapsed == pytest.approx(5.5)
    assert player.total_elapsed == pytest.approx(4.5)
    assert player.current_keyframe is None


def test_exact_boundary_advances():
    player = _started_player()
    player.update(2.0)
    assert player.keyframe_index == 1
    assert player.keyframe_elapsed == 0.0


@pytest.mark.parametrize("bad_dt", [True, False, float("nan"), float("inf"), float("-inf"), -1.0, None, "0.5", [1]])
def test_update_sanitizes_invalid_dt(bad_dt):
    player = _started_player()
    player.update(bad_dt)
    assert player.keyframe_elapsed == 0.0
    assert player.total_elapsed == 0.0
    assert player.fired_audio_cues == ["cue_a"]


def test_camera_interpolation_smoothstep():
    player = _started_player()
    assert player.get_camera_state() == (0.0, 0.0, 1.0)
    player.update(1.0)
    assert player.get_camera_state() == pytest.approx((50.0, -25.0, 1.5))
    player.update(0.5)
    assert player.get_camera_state() == pytest.approx((84.375, -42.1875, 1.84375))


def test_fade_alpha_in_and_out():
    player = _started_player()
    assert player.get_fade_alpha() == 255
    player.update(0.25)
    assert player.get_fade_alpha() == 128
    player.update(0.75)
    assert player.get_fade_alpha() == 0
    player.update(0.75)
    assert player.get_fade_alpha() == 128


def test_subtitle_window_is_inclusive():
    def _speaker_at(t):
        player = _started_player()
        player.update(t)
        sub = player.get_active_subtitle()
        return None if sub is None else sub.speaker

    assert _speaker_at(0.1) is None
    assert _speaker_at(0.2) == "VIPER-1"
    assert _speaker_at(1.5) == "VIPER-1"
    assert _speaker_at(1.6) is None


def test_latest_starting_subtitle_wins():
    kf = CinematicKeyframe(
        keyframe_id="subs", duration=3.0, scene_type=CINEMATIC_SCENE_EPILOGUE_CARD, fade_in=0.0, fade_out=0.0,
        subtitles=(CinematicSubtitle(0.0, 2.0, "A", "first"), CinematicSubtitle(1.0, 2.0, "B", "second")),
    )
    player = _started_player(sequence=_make_sequence(keyframes=(kf,)))
    player.update(1.5)
    assert player.get_active_subtitle().speaker == "B"
    assert len(player.get_active_subtitles()) == 2


def test_on_audio_cue_callback_overrides_audio_manager():
    audio = _FakeAudio()
    received = []
    player = CinematicPlayer(audio_manager=audio)
    player.on_audio_cue = received.append
    player.start_sequence(_make_sequence(), _make_stats())
    player.update(3.25)
    assert received == ["cue_a", "music:act3_finale"]
    assert audio.calls == []


def test_stop_music_cue():
    audio = _FakeAudio()
    seq = _make_sequence(keyframes=(CinematicKeyframe(keyframe_id="s", duration=1.0,
                                                      scene_type=CINEMATIC_SCENE_SUICIDE_DIVE,
                                                      fade_in=0.0, fade_out=0.0, audio_cue="stop_music"),))
    _started_player(audio, sequence=seq)
    assert audio.calls == [("stop", 600)]


def test_audio_failure_is_swallowed():
    player = _started_player(_FakeAudio(fail=True))
    assert player.fired_audio_cues == ["cue_a"]


def test_invalid_sequence_jumps_to_epilogue_with_fallback_stats():
    player = CinematicPlayer()
    player.start_sequence(_make_sequence(keyframes=()), None)
    assert player.phase == CINEMATIC_PHASE_EPILOGUE
    assert player.stats.pilot_status == UNKNOWN_PILOT_STATUS
    assert player.stats.ending_title == "Obedience"
    assert player.get_epilogue_lines() == ("Line one.", "Line two.")


def test_none_sequence_does_not_crash():
    player = CinematicPlayer()
    player.start_sequence(None, None)
    assert player.phase == CINEMATIC_PHASE_EPILOGUE
    assert player.stats.ending_branch == ""
    assert player.get_epilogue_lines() == ()


def test_epilogue_lines_prefer_stats():
    player = _started_player()
    player.update(10.0)
    assert player.get_epilogue_lines() == ("Stats line.",)


def test_restart_resets_cues_and_timeline():
    player = _started_player()
    player.update(3.25)
    player.start_sequence(_make_sequence(), _make_stats())
    assert player.keyframe_index == 0
    assert player.fired_audio_cues == ["cue_a"]
    assert player.skipped is False


def _key(key):
    return pygame.event.Event(pygame.KEYDOWN, key=key)


def test_escape_skips_to_epilogue_without_firing_remaining_cues():
    audio = _FakeAudio()
    player = _started_player(audio)
    assert player.handle_event(_key(pygame.K_ESCAPE)) is None
    assert player.phase == CINEMATIC_PHASE_EPILOGUE
    assert player.skipped is True
    assert player.fired_audio_cues == ["cue_a"]


def test_space_skips_to_epilogue():
    player = _started_player()
    assert player.handle_event(_key(pygame.K_SPACE)) is None
    assert player.phase == CINEMATIC_PHASE_EPILOGUE


def test_skip_disabled_ignores_escape_and_space():
    player = _started_player(allow_skip=False)
    player.handle_event(_key(pygame.K_ESCAPE))
    player.handle_event(_key(pygame.K_SPACE))
    assert player.phase == CINEMATIC_PHASE_PLAYING


def test_epilogue_confirm_respects_delay():
    player = _started_player()
    player.handle_event(_key(pygame.K_ESCAPE))
    assert player.handle_event(_key(pygame.K_ESCAPE)) is None
    assert player.phase == CINEMATIC_PHASE_EPILOGUE
    player.update(0.39)
    assert player.handle_event(_key(pygame.K_ESCAPE)) is None
    player.update(0.02)
    assert player.handle_event(_key(pygame.K_ESCAPE)) == CINEMATIC_ACTION_RETURN_MAIN_MENU
    assert player.phase == CINEMATIC_PHASE_FINISHED
    assert player.is_active is False


@pytest.mark.parametrize("key", [pygame.K_ESCAPE, pygame.K_SPACE, pygame.K_RETURN, pygame.K_KP_ENTER])
def test_epilogue_confirm_keys(key):
    player = _started_player()
    player.update(10.0)
    assert player.handle_event(_key(key)) == CINEMATIC_ACTION_RETURN_MAIN_MENU


def test_irrelevant_events_return_none():
    player = _started_player()
    events = [
        pygame.event.Event(pygame.KEYUP, key=pygame.K_ESCAPE),
        pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1),
        _key(pygame.K_a),
        object(),
        None,
    ]
    for event in events:
        assert player.handle_event(event) is None
    assert player.phase == CINEMATIC_PHASE_PLAYING


@pytest.mark.parametrize("scene_type", VALID_CINEMATIC_SCENE_TYPES)
def test_draw_every_scene_type_headless(dummy_surface, scene_type):
    seq = _single_keyframe_sequence(
        scene_type=scene_type,
        subtitles=(CinematicSubtitle(0.0, 2.0, "VIPER-2", "Copy that."),),
    )
    player = _started_player(sequence=seq)
    player.update(1.0)
    player.draw(dummy_surface)
    player.update(5.0)
    player.draw(dummy_surface)


def test_letterbox_bars_are_black(dummy_surface):
    player = _started_player()
    player.update(1.0)
    player.draw(dummy_surface)
    assert dummy_surface.get_at((10, 10))[:3] == (0, 0, 0)
    assert dummy_surface.get_at((10, 719 - 10))[:3] == (0, 0, 0)
    assert pygame.transform.average_color(dummy_surface, pygame.Rect(0, 100, 1280, 500))[:3] != (0, 0, 0)


def test_subtitle_renders_only_in_bottom_bar_window(dummy_surface):
    bottom = pygame.Rect(0, 720 - CINEMATIC_LETTERBOX_HEIGHT, 1280, CINEMATIC_LETTERBOX_HEIGHT)

    active = _started_player()
    active.update(1.0)
    active.draw(dummy_surface)
    assert pygame.transform.average_color(dummy_surface, bottom)[:3] != (0, 0, 0)

    inactive = _started_player()
    inactive.update(1.7)
    dummy_surface.fill((0, 0, 0))
    inactive.draw(dummy_surface)
    assert pygame.transform.average_color(dummy_surface, bottom)[:3] == (0, 0, 0)


def test_draw_allocates_no_fonts_or_surfaces_per_frame(dummy_surface, monkeypatch):
    player = _started_player()

    def _boom(*args, **kwargs):
        raise AssertionError("allocation in frame loop")

    monkeypatch.setattr(pygame.font, "SysFont", _boom)
    monkeypatch.setattr(pygame.font, "Font", _boom)
    monkeypatch.setattr(pygame, "Surface", _boom)
    for _ in range(400):
        player.update(1 / 60)
        player.draw(dummy_surface)
    assert player.phase == CINEMATIC_PHASE_EPILOGUE


def test_draw_without_fonts_is_safe(dummy_surface, monkeypatch):
    def _raise_pygame_error(*args, **kwargs):
        raise pygame.error("no font")

    monkeypatch.setattr(pygame.font, "get_init", lambda: False)
    monkeypatch.setattr(pygame.font, "init", _raise_pygame_error)
    monkeypatch.setattr(pygame.font, "SysFont", _raise_pygame_error)

    player = _started_player()
    assert player._fonts_ready is False
    player.update(1.0)
    player.draw(dummy_surface)
    player.update(10.0)
    player.draw(dummy_surface)
    assert player._subtitle_cache == {}
    assert player._epilogue_stat_surfs == []


def test_draw_noop_when_idle_or_invalid_surface(dummy_surface):
    dummy_surface.fill((1, 2, 3))
    CinematicPlayer().draw(dummy_surface)
    assert dummy_surface.get_at((640, 360))[:3] == (1, 2, 3)
    player = _started_player()
    player.draw(None)
    player.draw("x")


def test_epilogue_surfaces_cached_once(dummy_surface):
    player = _started_player()
    player.update(10.0)
    ids = [id(surf) for surf in player._epilogue_stat_surfs]
    assert len(ids) == 5
    for _ in range(3):
        player.update(1 / 60)
        player.draw(dummy_surface)
    assert [id(surf) for surf in player._epilogue_stat_surfs] == ids


def test_long_subtitle_truncated_to_two_lines():
    long_text = " ".join(["word"] * 200)
    seq = _single_keyframe_sequence(subtitles=(CinematicSubtitle(0.0, 2.0, "VIPER-1", long_text),))
    player = _started_player(sequence=seq)
    assert len(player._subtitle_cache[0][1]) == 2


def test_story_package_exports_cinematic_api():
    import eagle1.story as story

    for name in ("CinematicKeyframe", "CinematicPlayer", "CinematicSequence", "CinematicSubtitle",
                 "EpilogueSummaryStats", "validate_cinematic_sequence", "wrap_cinematic_text",
                 "build_epilogue_stat_lines", "CINEMATIC_LETTERBOX_HEIGHT", "VALID_CINEMATIC_SCENE_TYPES",
                 "CINEMATIC_ACTION_RETURN_MAIN_MENU"):
        assert name in story.__all__
        assert hasattr(story, name)
    assert story.__all__ == sorted(story.__all__)
    assert story.CinematicPlayer is CinematicPlayer
