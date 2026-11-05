"""Tests for eagle1.story.cinematic_player (cutscene sequencer, letterbox subtitles, epilogue)."""

import dataclasses

import pytest

from eagle1.story.cinematic_player import (
    CINEMATIC_SCENE_EPILOGUE_CARD,
    CINEMATIC_SCENE_HANGAR_CLONES,
    CINEMATIC_SCENE_SUICIDE_DIVE,
    CinematicKeyframe,
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
