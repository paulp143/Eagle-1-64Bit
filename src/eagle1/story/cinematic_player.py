"""cinematic_player.py - Scripted cutscene sequencer, keyframe renderer & letterbox subtitle engine.

Plays deterministic, timed keyframe slides for the three tragic campaign endings:
procedural scene canvases with camera pan/zoom, fade transitions, letterbox framing,
synchronized subtitles, one-shot audio cues, skip support and a final epilogue
statistics screen. All fonts and reusable surfaces are cached outside draw().
"""

from dataclasses import dataclass
import logging
import math
import random
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

import pygame

from eagle1.ui import theme, widgets
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
CINEMATIC_SCENE_TRENCH_STRIKE: str = "trench_strike"
CINEMATIC_SCENE_WHITE_FLASH: str = "white_flash"
CINEMATIC_SCENE_SCRAP_PLAIN: str = "scrap_plain"
CINEMATIC_SCENE_HELLPOD_DROP: str = "hellpod_drop"

VALID_CINEMATIC_SCENE_TYPES: Tuple[str, ...] = (
    CINEMATIC_SCENE_SUICIDE_DIVE,
    CINEMATIC_SCENE_HANGAR_CLONES,
    CINEMATIC_SCENE_SCRAP_YARD_EXECUTION,
    CINEMATIC_SCENE_OBSERVATION_DECK_FUNERAL,
    CINEMATIC_SCENE_EPILOGUE_CARD,
    CINEMATIC_SCENE_TRENCH_STRIKE,
    CINEMATIC_SCENE_WHITE_FLASH,
    CINEMATIC_SCENE_SCRAP_PLAIN,
    CINEMATIC_SCENE_HELLPOD_DROP,
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
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:
        return False


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


_COLOR_LETTERBOX: Tuple[int, int, int] = (0, 0, 0)
_COLOR_CAPTION: Tuple[int, int, int] = theme.ACCENT
_COLOR_SPEAKER: Tuple[int, int, int] = theme.ACCENT
_COLOR_PROMPT: Tuple[int, int, int] = theme.TEXT_MUTED
_COLOR_EPILOGUE_TITLE: Tuple[int, int, int] = theme.ACCENT
_COLOR_EPILOGUE_STAT: Tuple[int, int, int] = theme.TEXT
_COLOR_EPILOGUE_TEXT: Tuple[int, int, int] = theme.TEXT
_SUBTITLE_MAX_WIDTH: int = 1040
_EPILOGUE_TEXT_MAX_WIDTH: int = 900
_SKIP_PROMPT_TEXT: str = "[ESC / SPACE] SKIP"
_EPILOGUE_PROMPT_TEXT: str = "[ENTER / SPACE / ESC] RETURN TO MAIN MENU"
_EPILOGUE_HEADER_TEXT: str = "CAMPAIGN COMPLETE"
_STAR_COUNT: int = 140
_STAR_SEED: int = 73
_SURFACE_TYPE = pygame.Surface


class CinematicPlayer:
    """Plays a CinematicSequence at 60 FPS and finishes on the epilogue statistics screen."""

    def __init__(self, screen_w: int = 1280, screen_h: int = 720, audio_manager: Optional[Any] = None) -> None:
        self.screen_w = max(320, min(7680, int(screen_w))) if _is_finite_number(screen_w) and screen_w > 0 else 1280
        self.screen_h = max(240, min(4320, int(screen_h))) if _is_finite_number(screen_h) and screen_h > 0 else 720
        self.audio = audio_manager
        self.on_audio_cue: Optional[Callable[[str], None]] = None

        self.phase: str = CINEMATIC_PHASE_IDLE
        self.sequence: Optional[CinematicSequence] = None
        self.stats: Optional[EpilogueSummaryStats] = None
        self.allow_skip: bool = True
        self.keyframe_index: int = 0
        self.keyframe_elapsed: float = 0.0
        self.total_elapsed: float = 0.0
        self.epilogue_elapsed: float = 0.0
        self.camera: Tuple[float, float, float] = DEFAULT_CAMERA
        self.fade_alpha: int = 0
        self.fired_audio_cues: List[str] = []
        self._fired_cue_indices: Set[int] = set()
        self.skipped: bool = False

        # Text caches (rebuilt only on state transitions, never inside draw()).
        self._caption_surf: Optional[pygame.Surface] = None
        self._subtitle_cache: Dict[int, Tuple[Optional[pygame.Surface], List[pygame.Surface]]] = {}
        self._epilogue_header_surf: Optional[pygame.Surface] = None
        self._epilogue_title_surf: Optional[pygame.Surface] = None
        self._epilogue_stat_surfs: List[pygame.Surface] = []
        self._epilogue_line_surfs: List[pygame.Surface] = []
        self._skip_prompt_surf: Optional[pygame.Surface] = None
        self._epilogue_prompt_surf: Optional[pygame.Surface] = None

        self._font_retry_done: bool = False
        self._scene_renderers: Dict[str, Callable[[pygame.Surface], None]] = {
            CINEMATIC_SCENE_SUICIDE_DIVE: self._draw_scene_suicide_dive,
            CINEMATIC_SCENE_HANGAR_CLONES: self._draw_scene_hangar_clones,
            CINEMATIC_SCENE_SCRAP_YARD_EXECUTION: self._draw_scene_scrap_yard_execution,
            CINEMATIC_SCENE_OBSERVATION_DECK_FUNERAL: self._draw_scene_observation_deck_funeral,
            CINEMATIC_SCENE_EPILOGUE_CARD: self._draw_scene_epilogue_card,
            CINEMATIC_SCENE_TRENCH_STRIKE: self._draw_scene_trench_strike,
            CINEMATIC_SCENE_WHITE_FLASH: self._draw_scene_white_flash,
            CINEMATIC_SCENE_SCRAP_PLAIN: self._draw_scene_scrap_plain,
            CINEMATIC_SCENE_HELLPOD_DROP: self._draw_scene_hellpod_drop,
        }

        self._init_fonts()
        self._init_surfaces()
        self._init_starfield()

    # ------------------------------------------------------------------
    # State queries
    # ------------------------------------------------------------------
    @property
    def is_active(self) -> bool:
        return self.phase in (CINEMATIC_PHASE_PLAYING, CINEMATIC_PHASE_EPILOGUE)

    @property
    def is_playing(self) -> bool:
        return self.phase == CINEMATIC_PHASE_PLAYING

    @property
    def is_epilogue(self) -> bool:
        return self.phase == CINEMATIC_PHASE_EPILOGUE

    @property
    def current_keyframe(self) -> Optional[CinematicKeyframe]:
        if self.phase != CINEMATIC_PHASE_PLAYING or self.sequence is None:
            return None
        return self.sequence.keyframes[self.keyframe_index]

    def get_camera_state(self) -> Tuple[float, float, float]:
        return self.camera

    def get_fade_alpha(self) -> int:
        return self.fade_alpha

    def get_active_subtitles(self) -> Tuple[CinematicSubtitle, ...]:
        kf = self.current_keyframe
        if kf is None:
            return ()
        return tuple(sub for sub in kf.subtitles if sub.is_active_at(self.keyframe_elapsed))

    def _active_subtitle_index(self) -> Optional[int]:
        """Index of the active subtitle that started latest (ties go to the higher index)."""
        kf = self.current_keyframe
        if kf is None:
            return None
        best: Optional[Tuple[float, int]] = None
        for idx, sub in enumerate(kf.subtitles):
            if sub.is_active_at(self.keyframe_elapsed):
                key = (sub.start_time, idx)
                if best is None or key > best:
                    best = key
        return None if best is None else best[1]

    def get_active_subtitle(self) -> Optional[CinematicSubtitle]:
        kf = self.current_keyframe
        idx = self._active_subtitle_index()
        if kf is None or idx is None:
            return None
        return kf.subtitles[idx]

    def get_epilogue_lines(self) -> Tuple[str, ...]:
        if self.stats is not None and self.stats.epilogue_lines:
            return self.stats.epilogue_lines
        if self.sequence is not None:
            return self.sequence.epilogue_lines
        return ()

    # ------------------------------------------------------------------
    # Control
    # ------------------------------------------------------------------
    def start_sequence(self, sequence: CinematicSequence, stats: EpilogueSummaryStats, allow_skip: bool = True) -> None:
        self.reset()
        self.allow_skip = allow_skip is True
        valid = validate_cinematic_sequence(sequence)
        self.sequence = sequence if valid else None

        if isinstance(stats, EpilogueSummaryStats):
            self.stats = stats
        else:
            src = sequence if isinstance(sequence, CinematicSequence) else None
            self.stats = EpilogueSummaryStats(
                ending_branch=getattr(src, "ending_branch", ""),
                ending_title=getattr(src, "title", ""),
                final_loyalty=DEFAULT_LOYALTY,
                total_casualties=0,
                sorties_completed=0,
                pilot_status=UNKNOWN_PILOT_STATUS,
                epilogue_lines=getattr(src, "epilogue_lines", ()),
            )

        if not valid:
            logger.warning("CinematicPlayer: invalid sequence, jumping straight to epilogue")
            self._enter_epilogue()
            return

        self.phase = CINEMATIC_PHASE_PLAYING
        self._enter_keyframe(0)

    def update(self, dt: float) -> None:
        remaining = _sanitize_dt(dt)
        if self.phase == CINEMATIC_PHASE_PLAYING and self.sequence is not None:
            keyframes = self.sequence.keyframes
            while self.phase == CINEMATIC_PHASE_PLAYING:
                kf = keyframes[self.keyframe_index]
                time_left = float(kf.duration) - self.keyframe_elapsed
                if remaining < time_left:
                    self.keyframe_elapsed += remaining
                    self.total_elapsed += remaining
                    remaining = 0.0
                    break
                remaining -= time_left
                self.total_elapsed += time_left
                self.keyframe_elapsed = float(kf.duration)
                if self.keyframe_index + 1 < len(keyframes):
                    self._enter_keyframe(self.keyframe_index + 1)
                else:
                    self._enter_epilogue()
        if self.phase == CINEMATIC_PHASE_EPILOGUE:
            self.epilogue_elapsed += remaining
        if self.phase == CINEMATIC_PHASE_PLAYING:
            self._refresh_interpolation()

    def skip_to_epilogue(self) -> None:
        if self.phase == CINEMATIC_PHASE_PLAYING:
            self.skipped = True
            self._enter_epilogue()

    def reset(self) -> None:
        """Return to IDLE and clear timeline and per-sequence caches (fonts and surfaces are kept)."""
        self.phase = CINEMATIC_PHASE_IDLE
        self.sequence = None
        self.stats = None
        self.allow_skip = True
        self.keyframe_index = 0
        self.keyframe_elapsed = 0.0
        self.total_elapsed = 0.0
        self.epilogue_elapsed = 0.0
        self.camera = DEFAULT_CAMERA
        self.fade_alpha = 0
        self.fired_audio_cues = []
        self._fired_cue_indices = set()
        self.skipped = False
        self._caption_surf = None
        self._subtitle_cache = {}
        self._epilogue_title_surf = None
        self._epilogue_stat_surfs = []
        self._epilogue_line_surfs = []

    # ------------------------------------------------------------------
    # Initialisation helpers
    # ------------------------------------------------------------------
    def _init_fonts(self) -> None:
        self.font_title = None
        self.font_speaker = None
        self.font_subtitle = None
        self.font_epilogue = None
        self.font_prompt = None
        self._fonts_ready = False
        try:
            # theme.get_font initialises the font module on demand and returns None when it is unavailable.
            self.font_title = theme.get_font("display")
            self.font_speaker = theme.get_font("mono")
            self.font_subtitle = theme.get_font("subtitle")
            self.font_epilogue = theme.get_font("subtitle")
            self.font_prompt = theme.get_font("mono_small")
        except (pygame.error, OSError) as exc:
            logger.warning("CinematicPlayer fonts unavailable, rendering without text: %s", exc)
            self.font_title = None
        if None in (self.font_title, self.font_speaker, self.font_subtitle, self.font_epilogue, self.font_prompt):
            logger.warning("CinematicPlayer fonts unavailable, rendering without text")
            self.font_title = None
            self.font_speaker = None
            self.font_subtitle = None
            self.font_epilogue = None
            self.font_prompt = None
            return
        self._fonts_ready = True
        self._skip_prompt_surf = self._render_text(self.font_prompt, _SKIP_PROMPT_TEXT, _COLOR_PROMPT)
        self._epilogue_prompt_surf = self._render_text(self.font_prompt, _EPILOGUE_PROMPT_TEXT, _COLOR_PROMPT)
        self._epilogue_header_surf = self._render_text(self.font_speaker, _EPILOGUE_HEADER_TEXT, theme.ACCENT)

    def _init_surfaces(self) -> None:
        self._letterbox_surf = pygame.Surface((self.screen_w, CINEMATIC_LETTERBOX_HEIGHT))
        self._letterbox_surf.fill(_COLOR_LETTERBOX)
        self._fade_surf = pygame.Surface((self.screen_w, self.screen_h))
        self._fade_surf.fill((0, 0, 0))
        panel_w = max(1, min(1000, self.screen_w - 80))
        panel_h = max(1, min(560, self.screen_h - 80))
        self._epilogue_panel = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        self._epilogue_panel.fill(theme.with_alpha(theme.PANEL, 220))
        widgets.draw_panel(
            self._epilogue_panel, self._epilogue_panel.get_rect(), None, theme.ACCENT_DIM, _COLOR_EPILOGUE_TITLE
        )

    def _init_starfield(self) -> None:
        rng = random.Random(_STAR_SEED)
        self._stars: List[Tuple[float, float, int]] = [
            (rng.uniform(0, self.screen_w), rng.uniform(0, self.screen_h), rng.choice((1, 1, 2)))
            for _ in range(_STAR_COUNT)
        ]

    def _render_text(self, font: Optional[Any], text: str, color: Tuple[int, int, int]) -> Optional[pygame.Surface]:
        if font is None or not text:
            return None
        try:
            return font.render(text, True, color)
        except pygame.error as exc:
            logger.warning("CinematicPlayer text render failed: %s", exc)
            return None

    def _measure(self, font: Optional[Any], text: str) -> int:
        if font is None:
            return len(text) * 10
        try:
            return int(font.size(text)[0])
        except pygame.error:
            return len(text) * 10

    # ------------------------------------------------------------------
    # Timeline internals
    # ------------------------------------------------------------------
    def _enter_keyframe(self, index: int) -> None:
        self.keyframe_index = index
        self.keyframe_elapsed = 0.0
        kf = self.sequence.keyframes[index]
        if kf.audio_cue and index not in self._fired_cue_indices:
            self._fired_cue_indices.add(index)
            self._dispatch_audio_cue(kf.audio_cue.strip())
        self._rebuild_keyframe_text_cache()
        self._refresh_interpolation()

    def _enter_epilogue(self) -> None:
        self.phase = CINEMATIC_PHASE_EPILOGUE
        self.epilogue_elapsed = 0.0
        self.camera = DEFAULT_CAMERA
        self.fade_alpha = 0
        self._caption_surf = None
        self._subtitle_cache.clear()
        self._build_epilogue_cache()

    def _refresh_interpolation(self) -> None:
        if self.phase != CINEMATIC_PHASE_PLAYING:
            return
        kf = self.sequence.keyframes[self.keyframe_index]
        duration = float(kf.duration)
        t = max(0.0, min(1.0, self.keyframe_elapsed / duration))
        eased = t * t * (3.0 - 2.0 * t)
        self.camera = tuple(
            float(a) + (float(b) - float(a)) * eased for a, b in zip(kf.camera_start, kf.camera_end)
        )
        el = self.keyframe_elapsed
        if kf.fade_in > 0 and el < kf.fade_in:
            alpha = 255.0 * (1.0 - el / kf.fade_in)
        elif kf.fade_out > 0 and el > duration - kf.fade_out:
            alpha = 255.0 * ((el - (duration - kf.fade_out)) / kf.fade_out)
        else:
            alpha = 0.0
        self.fade_alpha = max(0, min(255, int(round(alpha))))

    def _dispatch_audio_cue(self, cue: str) -> None:
        self.fired_audio_cues.append(cue)
        if callable(self.on_audio_cue):
            try:
                self.on_audio_cue(cue)
            except Exception as exc:
                logger.warning("Cinematic audio cue callback failed for %r: %s", cue, exc)
            return
        if self.audio is None:
            return
        try:
            if cue.startswith("music:"):
                track = cue[len("music:"):].strip()
                play_music = getattr(self.audio, "play_music", None)
                if track and callable(play_music):
                    play_music(track, loop=True, fade_ms=600)
            elif cue == "stop_music":
                stop_music = getattr(self.audio, "stop_music", None)
                if callable(stop_music):
                    stop_music(fade_ms=600)
            else:
                play_sfx = getattr(self.audio, "play_sfx", None)
                if callable(play_sfx):
                    play_sfx(cue)
        except (pygame.error, TypeError, ValueError, AttributeError, OSError) as exc:
            logger.warning("Cinematic audio cue %r failed: %s", cue, exc)

    def _rebuild_keyframe_text_cache(self) -> None:
        self._subtitle_cache.clear()
        if self.sequence is None or self.keyframe_index >= len(self.sequence.keyframes):
            return
        kf = self.sequence.keyframes[self.keyframe_index]
        caption = kf.title_caption.strip()
        self._caption_surf = self._render_text(self.font_title, caption, _COLOR_CAPTION) if caption else None
        for idx, sub in enumerate(kf.subtitles):
            speaker = sub.speaker.strip().upper()
            speaker_surf = self._render_text(self.font_speaker, speaker, _COLOR_SPEAKER) if speaker else None
            lines = wrap_cinematic_text(sub.text, _SUBTITLE_MAX_WIDTH,
                                        lambda s: self._measure(self.font_subtitle, s))
            if len(lines) > SUBTITLE_MAX_LINES:
                lines = lines[:SUBTITLE_MAX_LINES]
                lines[-1] = lines[-1].rstrip(".") + "..."
            line_surfs = [
                surf for surf in (self._render_text(self.font_subtitle, ln, sub.color) for ln in lines)
                if surf is not None
            ]
            self._subtitle_cache[idx] = (speaker_surf, line_surfs)

    def _build_epilogue_cache(self) -> None:
        title = self.stats.ending_title or format_ending_branch_label(self.stats.ending_branch)
        self._epilogue_title_surf = self._render_text(self.font_title, title.upper(), _COLOR_EPILOGUE_TITLE)
        self._epilogue_stat_surfs = [
            surf for surf in (
                self._render_text(self.font_epilogue, ln, _COLOR_EPILOGUE_STAT)
                for ln in build_epilogue_stat_lines(self.stats)
            ) if surf is not None
        ]
        wrapped: List[str] = []
        for line in self.get_epilogue_lines():
            wrapped.extend(wrap_cinematic_text(line, _EPILOGUE_TEXT_MAX_WIDTH,
                                               lambda s: self._measure(self.font_epilogue, s)))
        wrapped = wrapped[:EPILOGUE_MAX_LINES]
        self._epilogue_line_surfs = [
            surf for surf in (self._render_text(self.font_epilogue, ln, _COLOR_EPILOGUE_TEXT) for ln in wrapped)
            if surf is not None
        ]

    # ------------------------------------------------------------------
    # Input
    # ------------------------------------------------------------------
    def handle_event(self, event: Any) -> Optional[str]:
        if getattr(event, "type", None) != pygame.KEYDOWN:
            return None
        key = getattr(event, "key", None)
        if self.phase == CINEMATIC_PHASE_PLAYING:
            if self.allow_skip and key in (pygame.K_ESCAPE, pygame.K_SPACE):
                self.skip_to_epilogue()
            return None
        if self.phase == CINEMATIC_PHASE_EPILOGUE:
            confirm_keys = (pygame.K_ESCAPE, pygame.K_SPACE, pygame.K_RETURN, pygame.K_KP_ENTER)
            if key in confirm_keys and self.epilogue_elapsed >= CINEMATIC_EPILOGUE_CONFIRM_DELAY:
                self.phase = CINEMATIC_PHASE_FINISHED
                return CINEMATIC_ACTION_RETURN_MAIN_MENU
        return None

    # ------------------------------------------------------------------
    # Rendering (no font or Surface allocation in this call chain)
    # ------------------------------------------------------------------
    def draw(self, surface: pygame.Surface) -> None:
        if not isinstance(surface, _SURFACE_TYPE):
            return
        if self.phase not in (CINEMATIC_PHASE_PLAYING, CINEMATIC_PHASE_EPILOGUE):
            return
        if not self._fonts_ready and not self._font_retry_done and pygame.font.get_init():
            # One-time lazy retry if fonts were unavailable at construction time.
            self._font_retry_done = True
            self._init_fonts()
            if self._fonts_ready:
                if self.phase == CINEMATIC_PHASE_PLAYING:
                    self._rebuild_keyframe_text_cache()
                else:
                    self._build_epilogue_cache()
        try:
            if self.phase == CINEMATIC_PHASE_PLAYING:
                kf = self.current_keyframe
                if kf is not None:
                    self._draw_scene(surface, kf)
                if self._caption_surf is not None:
                    cw = self._caption_surf.get_width()
                    surface.blit(self._caption_surf, ((self.screen_w - cw) // 2, CINEMATIC_LETTERBOX_HEIGHT + 24))
                if self.fade_alpha > 0:
                    self._fade_surf.set_alpha(self.fade_alpha)
                    surface.blit(self._fade_surf, (0, 0))
                self._draw_letterbox_and_subtitles(surface)
            else:
                self._draw_epilogue(surface)
        except (pygame.error, ValueError, OverflowError) as exc:
            logger.warning("CinematicPlayer draw failed: %s", exc)

    def _project(self, wx: float, wy: float) -> Tuple[int, int]:
        pan_x, pan_y, zoom = self.camera
        return (
            int(self.screen_w / 2 + (wx - pan_x) * zoom),
            int(self.screen_h / 2 + (wy - pan_y) * zoom),
        )

    def _scale(self, length: float) -> int:
        return max(1, int(length * self.camera[2]))

    def _draw_starfield(self, surface: pygame.Surface, parallax: float) -> None:
        for sx, sy, radius in self._stars:
            x = int((sx - self.camera[0] * parallax) % self.screen_w)
            y = int((sy - self.camera[1] * parallax) % self.screen_h)
            pygame.draw.circle(surface, (200, 205, 220), (x, y), radius)

    def _draw_scene(self, surface: pygame.Surface, keyframe: CinematicKeyframe) -> None:
        renderer = self._scene_renderers.get(keyframe.scene_type)
        if renderer is None:
            surface.fill((0, 0, 0))
            return
        renderer(surface)

    def _draw_scene_suicide_dive(self, surface: pygame.Surface) -> None:
        surface.fill((18, 10, 14))
        self._draw_starfield(surface, 0.3)
        radius = self._scale(170)
        pygame.draw.circle(surface, (90, 30, 30), self._project(0, -40), self._scale(150))
        pygame.draw.circle(surface, (200, 60, 40), self._project(0, -40), radius, width=min(3, radius))
        silhouette = [self._project(x, y) for x, y in [(0, 230), (-38, 300), (0, 282), (38, 300)]]
        pygame.draw.polygon(surface, (220, 225, 235), silhouette)
        for tip in [(-14, 380), (0, 400), (14, 380)]:
            pygame.draw.line(surface, (255, 140, 40), self._project(0, 300), self._project(*tip), self._scale(3))

    def _draw_scene_hangar_clones(self, surface: pygame.Surface) -> None:
        surface.fill((20, 24, 30))
        pygame.draw.line(surface, (70, 80, 95), self._project(-600, 140), self._project(600, 140), self._scale(2))
        for row in range(3):
            for col in range(7):
                cx = -330 + col * 110
                cy = -110 + row * 110
                pygame.draw.circle(surface, (150, 160, 175), self._project(cx, cy - 26), self._scale(12))
                pos = self._project(cx - 14, cy - 12)
                pygame.draw.rect(surface, (110, 120, 135), (*pos, self._scale(28), self._scale(48)))

    def _draw_scene_scrap_yard_execution(self, surface: pygame.Surface) -> None:
        surface.fill((26, 20, 16))
        pygame.draw.line(surface, (170, 40, 30), self._project(-700, 60), self._project(700, 60), self._scale(2))
        pygame.draw.polygon(surface, (60, 50, 42), [self._project(x, y) for x, y in [(-520, 60), (-420, -40), (-300, 60)]])
        pygame.draw.polygon(surface, (60, 50, 42), [self._project(x, y) for x, y in [(260, 60), (380, -70), (520, 60)]])
        pygame.draw.circle(surface, (200, 190, 170), self._project(0, 10), self._scale(11))
        kneeling_pos = self._project(-12, 22)
        pygame.draw.rect(surface, (150, 140, 120), (*kneeling_pos, self._scale(24), self._scale(30)))
        for x in (-90, 90):
            frame_pos = self._project(x - 16, -40)
            pygame.draw.rect(surface, (40, 40, 46), (*frame_pos, self._scale(32), self._scale(80)))
            pygame.draw.circle(surface, (255, 40, 30), self._project(x, -28), self._scale(4))

    def _draw_scene_observation_deck_funeral(self, surface: pygame.Surface) -> None:
        surface.fill((8, 10, 20))
        self._draw_starfield(surface, 0.15)
        pygame.draw.circle(surface, (40, 70, 120), self._project(260, -120), self._scale(120))
        frame_pos = self._project(-560, -220)
        pygame.draw.rect(
            surface, (60, 70, 85), (*frame_pos, self._scale(1120), self._scale(380)), width=self._scale(6)
        )
        pygame.draw.line(surface, (60, 70, 85), self._project(0, -220), self._project(0, 160), self._scale(6))
        for x in (-270, -90, 90, 270):
            coffin_pos = self._project(x - 60, 190)
            pygame.draw.rect(surface, (70, 60, 50), (*coffin_pos, self._scale(120), self._scale(36)))
            flag_pos = self._project(x - 60, 202)
            pygame.draw.rect(surface, (255, 215, 0), (*flag_pos, self._scale(120), self._scale(8)))

    def _draw_scene_epilogue_card(self, surface: pygame.Surface) -> None:
        surface.fill((5, 5, 8))

    def _draw_scene_trench_strike(self, surface: pygame.Surface) -> None:
        """Ash-grey valley, Viper Squad's trench with four blue beacons and the falling 500kg."""
        surface.fill((58, 58, 62))
        valley = [self._project(x, y) for x, y in [(-700, 120), (-260, 40), (260, 40), (700, 120), (700, 400), (-700, 400)]]
        pygame.draw.polygon(surface, (44, 40, 38), valley)
        pygame.draw.line(surface, (24, 22, 20), self._project(-220, 90), self._project(220, 90), self._scale(14))
        for x in (-120, -40, 40, 120):
            pygame.draw.circle(surface, (60, 140, 255), self._project(x, 80), self._scale(7))
        pygame.draw.line(surface, (255, 40, 30), self._project(0, -360), self._project(0, 80), max(1, self._scale(2)))
        bomb = [self._project(x, y) for x, y in [(0, -150), (-12, -180), (-12, -230), (12, -230), (12, -180)]]
        pygame.draw.polygon(surface, (30, 30, 34), bomb)

    def _draw_scene_white_flash(self, surface: pygame.Surface) -> None:
        surface.fill((255, 255, 255))

    def _draw_scene_scrap_plain(self, surface: pygame.Surface) -> None:
        """Fog-bound scrap yard: wrecks, oil drums, landed Eagle-1 and silent red-eyed Automatons."""
        surface.fill((34, 28, 24))
        ground = [self._project(x, y) for x, y in [(-700, 80), (700, 80), (700, 400), (-700, 400)]]
        pygame.draw.polygon(surface, (52, 42, 34), ground)
        for wreck in ([(-560, 80), (-470, -10), (-360, 80)], [(320, 80), (430, -30), (560, 80)], [(-250, 80), (-210, 40), (-150, 80)]):
            pygame.draw.polygon(surface, (66, 56, 46), [self._project(x, y) for x, y in wreck])
        for x in (-320, -290, 250, 280):
            drum_pos = self._project(x, 52)
            pygame.draw.rect(surface, (110, 70, 30), (*drum_pos, self._scale(22), self._scale(30)))
        eagle = [self._project(x, y) for x, y in [(0, 30), (-70, 80), (0, 66), (70, 80)]]
        pygame.draw.polygon(surface, (150, 155, 165), eagle)
        for i in range(9):
            x = -360 + i * 90
            body_pos = self._project(x - 10, -70)
            pygame.draw.rect(surface, (30, 30, 36), (*body_pos, self._scale(20), self._scale(48)))
            pygame.draw.circle(surface, (255, 40, 30), self._project(x, -60), self._scale(3))
        for y in (-110, -20, 120):
            pygame.draw.line(surface, (84, 78, 72), self._project(-700, y), self._project(700, y + 20), self._scale(2))

    def _draw_scene_hellpod_drop(self, surface: pygame.Surface) -> None:
        """Scrap plain with four black Hellpods slammed into the dirt around Eagle-1."""
        self._draw_scene_scrap_plain(surface)
        for x, y in ((-170, 60), (170, 60), (-110, 130), (110, 130)):
            pygame.draw.circle(surface, (255, 140, 40), self._project(x, y + 18), self._scale(34), max(1, self._scale(3)))
            pod = [self._project(px, py) for px, py in [(x, y - 50), (x - 18, y - 20), (x - 18, y + 18), (x + 18, y + 18), (x + 18, y - 20)]]
            pygame.draw.polygon(surface, (12, 12, 14), pod)

    def _draw_letterbox_and_subtitles(self, surface: pygame.Surface) -> None:
        h = CINEMATIC_LETTERBOX_HEIGHT
        surface.blit(self._letterbox_surf, (0, 0))
        surface.blit(self._letterbox_surf, (0, self.screen_h - h))
        if self.allow_skip and self._skip_prompt_surf is not None:
            sw, sh = self._skip_prompt_surf.get_size()
            surface.blit(self._skip_prompt_surf, (self.screen_w - sw - 24, (h - sh) // 2))
        idx = self._active_subtitle_index()
        if idx is None or idx not in self._subtitle_cache:
            return
        speaker_surf, line_surfs = self._subtitle_cache[idx]
        y = self.screen_h - h + 4
        if speaker_surf is not None:
            surface.blit(speaker_surf, ((self.screen_w - speaker_surf.get_width()) // 2, y))
            y += speaker_surf.get_height()
        for line in line_surfs:
            surface.blit(line, ((self.screen_w - line.get_width()) // 2, y))
            y += line.get_height()

    def _blit_centered(self, surface: pygame.Surface, surf: Optional[pygame.Surface], y: int) -> None:
        if surf is None:
            return
        surface.blit(surf, ((self.screen_w - surf.get_width()) // 2, y))

    def _draw_epilogue(self, surface: pygame.Surface) -> None:
        surface.fill(theme.BG_DEEP)
        pw, ph = self._epilogue_panel.get_size()
        px = (self.screen_w - pw) // 2
        py = (self.screen_h - ph) // 2
        surface.blit(self._epilogue_panel, (px, py))

        y = py + 24
        self._blit_centered(surface, self._epilogue_header_surf, y)
        if self._epilogue_header_surf is not None:
            y += self._epilogue_header_surf.get_height() + 9
        self._blit_centered(surface, self._epilogue_title_surf, y)
        if self._epilogue_title_surf is not None:
            y += self._epilogue_title_surf.get_height() + 8
        for surf in self._epilogue_stat_surfs:
            self._blit_centered(surface, surf, y)
            y += surf.get_height() + 6
        y += 14
        for surf in self._epilogue_line_surfs:
            self._blit_centered(surface, surf, y)
            y += surf.get_height() + 4
        if self.epilogue_elapsed >= CINEMATIC_EPILOGUE_CONFIRM_DELAY:
            self._blit_centered(surface, self._epilogue_prompt_surf, py + ph - 32)
