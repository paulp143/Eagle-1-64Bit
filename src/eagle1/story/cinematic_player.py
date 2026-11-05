"""cinematic_player.py - Scripted cutscene sequencer, keyframe renderer & letterbox subtitle engine.

Plays deterministic, timed keyframe slides for the three tragic campaign endings:
procedural scene canvases with camera pan/zoom, fade transitions, letterbox framing,
synchronized subtitles, one-shot audio cues, skip support and a final epilogue
statistics screen. All fonts and reusable surfaces are cached outside draw().
"""

from dataclasses import dataclass
import logging
import math
from typing import Any, Callable, Dict, List, Optional, Tuple

from eagle1.story.story_manager import (
    BRANCH_COLD_PROTOCOL,
    BRANCH_DISSIDENT_SURRENDER,
    BRANCH_OBEDIENCE_PURGE,
    DEFAULT_LOYALTY,
    MAX_LOYALTY,
    MIN_LOYALTY,
)

logger = logging.getLogger(__name__)

CINEMATIC_LETTERBOX_HEIGHT: int = 72
CINEMATIC_EPILOGUE_CONFIRM_DELAY: float = 0.4
CINEMATIC_ACTION_RETURN_MAIN_MENU: str = "return_main_menu"

CINEMATIC_PHASE_IDLE: str = "idle"
CINEMATIC_PHASE_PLAYING: str = "playing"
CINEMATIC_PHASE_EPILOGUE: str = "epilogue"
CINEMATIC_PHASE_FINISHED: str = "finished"

CINEMATIC_SCENE_SUICIDE_DIVE: str = "suicide_dive"
CINEMATIC_SCENE_HANGAR_CLONES: str = "hangar_clones"
CINEMATIC_SCENE_SCRAP_YARD_EXECUTION: str = "scrap_yard_execution"
CINEMATIC_SCENE_OBSERVATION_DECK_FUNERAL: str = "observation_deck_funeral"
CINEMATIC_SCENE_EPILOGUE_CARD: str = "epilogue_card"

VALID_CINEMATIC_SCENE_TYPES: Tuple[str, ...] = (
    CINEMATIC_SCENE_SUICIDE_DIVE,
    CINEMATIC_SCENE_HANGAR_CLONES,
    CINEMATIC_SCENE_SCRAP_YARD_EXECUTION,
    CINEMATIC_SCENE_OBSERVATION_DECK_FUNERAL,
    CINEMATIC_SCENE_EPILOGUE_CARD,
)

DEFAULT_SUBTITLE_COLOR: Tuple[int, int, int] = (235, 240, 250)
DEFAULT_CAMERA: Tuple[float, float, float] = (0.0, 0.0, 1.0)
UNKNOWN_PILOT_STATUS: str = "UNKNOWN"
SUBTITLE_MAX_LINES: int = 2
EPILOGUE_MAX_LINES: int = 8

ENDING_BRANCH_LABELS: Dict[str, str] = {
    BRANCH_OBEDIENCE_PURGE: "OBEDIENCE PURGE",
    BRANCH_DISSIDENT_SURRENDER: "DISSIDENT SURRENDER",
    BRANCH_COLD_PROTOCOL: "COLD PROTOCOL",
}


def _is_finite_number(value: Any) -> bool:
    """Return True for finite int/float values that are not bools."""
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _sanitize_dt(value: Any) -> float:
    """Coerce a frame delta to a finite, non-negative float; bool/NaN/inf/negative/garbage -> 0.0."""
    if not _is_finite_number(value):
        return 0.0
    numeric = float(value)
    return numeric if numeric > 0.0 else 0.0


def _sanitize_count(value: Any) -> int:
    """Coerce a counter to a non-negative int; bools, NaN, inf, strings -> 0; floats are truncated."""
    if not _is_finite_number(value):
        return 0
    return max(0, int(value))


def _sanitize_loyalty(value: Any) -> float:
    """Clamp loyalty into [MIN_LOYALTY, MAX_LOYALTY]; bool/NaN/inf/garbage -> DEFAULT_LOYALTY."""
    if not _is_finite_number(value):
        return DEFAULT_LOYALTY
    return max(MIN_LOYALTY, min(MAX_LOYALTY, float(value)))


def _sanitize_text(value: Any, default: str = "") -> str:
    """Return a stripped string; non-strings and blank strings return default."""
    if not isinstance(value, str) or not value.strip():
        return default
    return value.strip()


def _coerce_tuple(value: Any) -> tuple:
    """Convert list/tuple to tuple; anything else (None, str, dict, ...) becomes ()."""
    if isinstance(value, (list, tuple)):
        return tuple(value)
    return ()


def _coerce_text_lines(value: Any) -> Tuple[str, ...]:
    """Keep only str entries of a list/tuple (unchanged, not stripped); everything else -> ()."""
    return tuple(item for item in _coerce_tuple(value) if isinstance(item, str))


@dataclass(frozen=True)
class CinematicSubtitle:
    """A timed subtitle line; times are seconds relative to the owning keyframe's start."""

    start_time: float
    end_time: float
    speaker: str
    text: str
    color: Tuple[int, int, int] = DEFAULT_SUBTITLE_COLOR

    def is_active_at(self, t: float) -> bool:
        """Return True when t lies inside the closed window [start_time, end_time]."""
        if not (_is_finite_number(t) and _is_finite_number(self.start_time) and _is_finite_number(self.end_time)):
            return False
        return self.start_time <= t <= self.end_time


@dataclass(frozen=True)
class CinematicKeyframe:
    """One timed slide of a cutscene with camera move, fades, audio cue and subtitles."""

    keyframe_id: str
    duration: float
    scene_type: str
    title_caption: str = ""
    camera_start: Tuple[float, float, float] = DEFAULT_CAMERA
    camera_end: Tuple[float, float, float] = DEFAULT_CAMERA
    fade_in: float = 0.5
    fade_out: float = 0.5
    audio_cue: Optional[str] = None
    subtitles: Tuple[CinematicSubtitle, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "camera_start", _coerce_tuple(self.camera_start))
        object.__setattr__(self, "camera_end", _coerce_tuple(self.camera_end))
        object.__setattr__(self, "subtitles", _coerce_tuple(self.subtitles))


@dataclass(frozen=True)
class CinematicSequence:
    """An ordered cutscene for one campaign ending branch."""

    sequence_id: str
    ending_branch: str
    title: str
    keyframes: Tuple[CinematicKeyframe, ...]
    epilogue_lines: Tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "keyframes", _coerce_tuple(self.keyframes))
        object.__setattr__(self, "epilogue_lines", _coerce_text_lines(self.epilogue_lines))


@dataclass(frozen=True)
class EpilogueSummaryStats:
    """Final campaign statistics shown on the epilogue screen (all fields sanitized)."""

    ending_branch: str
    ending_title: str
    final_loyalty: float
    total_casualties: int
    sorties_completed: int
    pilot_status: str
    epilogue_lines: Tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "ending_branch", _sanitize_text(self.ending_branch))
        object.__setattr__(self, "ending_title", _sanitize_text(self.ending_title))
        object.__setattr__(self, "final_loyalty", _sanitize_loyalty(self.final_loyalty))
        object.__setattr__(self, "total_casualties", _sanitize_count(self.total_casualties))
        object.__setattr__(self, "sorties_completed", _sanitize_count(self.sorties_completed))
        object.__setattr__(self, "pilot_status", _sanitize_text(self.pilot_status, UNKNOWN_PILOT_STATUS))
        object.__setattr__(self, "epilogue_lines", _coerce_text_lines(self.epilogue_lines))


def wrap_cinematic_text(text: Any, max_width: int, measure: Callable[[str], int]) -> List[str]:
    """Greedy word-wrap text so every line's measured width is <= max_width.

    Whitespace runs collapse to single spaces. Words wider than max_width are hard-split
    character by character. Non-str or blank text and max_width <= 0 return [].
    """
    if not isinstance(text, str) or not text.strip():
        return []
    if isinstance(max_width, bool) or not isinstance(max_width, int) or max_width <= 0:
        return []

    words = text.split()
    lines: List[str] = []
    current = ""
    for word in words:
        if measure(word) > max_width:
            if current:
                lines.append(current)
                current = ""
            chunk = ""
            for ch in word:
                if chunk and measure(chunk + ch) > max_width:
                    lines.append(chunk)
                    chunk = ch
                else:
                    chunk += ch
            current = chunk
            continue
        candidate = word if not current else current + " " + word
        if measure(candidate) <= max_width:
            current = candidate
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def format_ending_branch_label(branch: Any) -> str:
    """Human readable branch label, e.g. 'OBEDIENCE_PURGE' -> 'OBEDIENCE PURGE'; unknown -> 'UNKNOWN'."""
    text = _sanitize_text(branch)
    if not text:
        return UNKNOWN_PILOT_STATUS
    return ENDING_BRANCH_LABELS.get(text, text.replace("_", " ").upper())


def build_epilogue_stat_lines(stats: Any) -> Tuple[str, ...]:
    """Return the five fixed statistics rows for the epilogue screen (pure, render-free)."""
    if not isinstance(stats, EpilogueSummaryStats):
        return ()
    return (
        f"ENDING: {format_ending_branch_label(stats.ending_branch)}",
        f"FINAL LOYALTY: {stats.final_loyalty:.1f}%",
        f"HELLDIVER CASUALTIES: {stats.total_casualties}",
        f"SORTIES COMPLETED: {stats.sorties_completed}",
        f"PILOT STATUS: {stats.pilot_status.upper()}",
    )


def validate_cinematic_sequence(sequence: Any) -> bool:
    """Return True when the sequence is structurally playable; logs the first problem at WARNING."""
    if not isinstance(sequence, CinematicSequence):
        logger.warning("Invalid cinematic sequence: not a CinematicSequence (%r)", type(sequence).__name__)
        return False
    seq_id = sequence.sequence_id

    def _fail(reason: str) -> bool:
        logger.warning("Invalid cinematic sequence %r: %s", seq_id, reason)
        return False

    if not _sanitize_text(sequence.sequence_id):
        return _fail("empty sequence_id")
    if not isinstance(sequence.ending_branch, str) or not isinstance(sequence.title, str):
        return _fail("ending_branch and title must be strings")
    if len(sequence.keyframes) < 1:
        return _fail("no keyframes")

    seen_ids: set = set()
    for kf in sequence.keyframes:
        if not isinstance(kf, CinematicKeyframe):
            return _fail("keyframe is not a CinematicKeyframe")
        kf_id = _sanitize_text(kf.keyframe_id)
        if not kf_id or kf_id in seen_ids:
            return _fail(f"blank or duplicate keyframe_id {kf.keyframe_id!r}")
        seen_ids.add(kf_id)
        if not (_is_finite_number(kf.duration) and kf.duration > 0):
            return _fail(f"keyframe {kf_id!r}: duration must be finite and > 0")
        if kf.scene_type not in VALID_CINEMATIC_SCENE_TYPES:
            return _fail(f"keyframe {kf_id!r}: unknown scene_type {kf.scene_type!r}")
        if not isinstance(kf.title_caption, str):
            return _fail(f"keyframe {kf_id!r}: title_caption must be a string")
        for cam in (kf.camera_start, kf.camera_end):
            if len(cam) != 3 or not all(_is_finite_number(v) for v in cam) or cam[2] <= 0:
                return _fail(f"keyframe {kf_id!r}: camera must be (x, y, zoom>0) finite values")
        if not (_is_finite_number(kf.fade_in) and kf.fade_in >= 0):
            return _fail(f"keyframe {kf_id!r}: fade_in must be finite and >= 0")
        if not (_is_finite_number(kf.fade_out) and kf.fade_out >= 0):
            return _fail(f"keyframe {kf_id!r}: fade_out must be finite and >= 0")
        if kf.fade_in + kf.fade_out > kf.duration:
            return _fail(f"keyframe {kf_id!r}: fades longer than duration")
        if kf.audio_cue is not None and _sanitize_text(kf.audio_cue) == "":
            return _fail(f"keyframe {kf_id!r}: blank audio_cue")
        for sub in kf.subtitles:
            if not isinstance(sub, CinematicSubtitle):
                return _fail(f"keyframe {kf_id!r}: subtitle is not a CinematicSubtitle")
            if not (_is_finite_number(sub.start_time) and sub.start_time >= 0):
                return _fail(f"keyframe {kf_id!r}: subtitle start_time invalid")
            if not (_is_finite_number(sub.end_time) and sub.end_time > sub.start_time
                    and sub.end_time <= kf.duration):
                return _fail(f"keyframe {kf_id!r}: subtitle window invalid")
            if not isinstance(sub.speaker, str):
                return _fail(f"keyframe {kf_id!r}: subtitle speaker must be a string")
            if _sanitize_text(sub.text) == "":
                return _fail(f"keyframe {kf_id!r}: blank subtitle text")
            color = sub.color
            if not (isinstance(color, tuple) and len(color) == 3
                    and all(isinstance(c, int) and not isinstance(c, bool) and 0 <= c <= 255 for c in color)):
                return _fail(f"keyframe {kf_id!r}: subtitle color must be an RGB int tuple")
    return True
