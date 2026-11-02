"""Unit tests for in-flight narrative triggers and telemetry sanitization (Issue #68)."""

import math

import pytest

from eagle1.story.narrative_trigger_manager import (
    CONDITION_AERIAL_KILLS,
    CONDITION_BOSS_HP_BELOW,
    CONDITION_CUSTOM,
    CONDITION_ELAPSED_TIME,
    CONDITION_FABRICATORS_DESTROYED,
    CONDITION_HELLDIVER_CASUALTIES,
    CONDITION_WAVE_REACHED,
    VALID_CONDITION_TYPES,
    CombatTelemetrySnapshot,
    SortieEventTrigger,
    validate_sortie_event_trigger,
)


def _make_trigger(**overrides):
    """Build a valid trigger with an objective payload; overrides replace fields."""
    fields = {
        "trigger_id": "t_valid",
        "sortie_num": 1,
        "priority": 0,
        "condition_type": CONDITION_AERIAL_KILLS,
        "threshold": 5,
        "objective_update": "Destroy the interceptors",
    }
    fields.update(overrides)
    return SortieEventTrigger(**fields)


# -----------------------------------------------------------------------------
# 1. CombatTelemetrySnapshot defaults and sanitization
# -----------------------------------------------------------------------------

def test_snapshot_defaults_are_neutral():
    """A default snapshot reports no progress and no active boss."""
    snap = CombatTelemetrySnapshot()

    assert snap.elapsed_seconds == 0.0
    assert snap.current_wave == 0
    assert snap.aerial_kills == 0
    assert snap.ground_kills == 0
    assert snap.fabricators_destroyed == 0
    assert snap.fabricators_remaining == 0
    assert snap.boss_active is False
    assert snap.boss_hp_ratio == 1.0
    assert snap.helldivers_alive == 0
    assert snap.casualties_count == 0
    assert snap.any_helldiver_critical is False
    assert snap.active_500kg_inbound is False


def test_snapshot_sanitizes_corrupted_values():
    """Corrupted telemetry is coerced to safe values without raising."""
    snap = CombatTelemetrySnapshot(
        elapsed_seconds=float("nan"),
        aerial_kills=-5,
        ground_kills=True,
        current_wave=3.9,
        fabricators_destroyed=float("inf"),
        boss_hp_ratio=float("nan"),
        boss_active=1,
        helldivers_alive="4",
    )

    assert snap.elapsed_seconds == 0.0
    assert snap.aerial_kills == 0
    assert snap.ground_kills == 0
    assert snap.current_wave == 3
    assert snap.fabricators_destroyed == 0
    assert snap.boss_hp_ratio == 1.0
    assert snap.boss_active is False
    assert snap.helldivers_alive == 0


@pytest.mark.parametrize(("raw", "expected"), [(1.7, 1.0), (-0.2, 0.0), (float("inf"), 1.0), (-float("inf"), 0.0)])
def test_snapshot_clamps_boss_hp_ratio(raw, expected):
    """Finite and infinite boss HP ratios are clamped into [0.0, 1.0]."""
    assert CombatTelemetrySnapshot(boss_hp_ratio=raw).boss_hp_ratio == expected


# -----------------------------------------------------------------------------
# 2. SortieEventTrigger validation
# -----------------------------------------------------------------------------

def test_valid_condition_types_cover_all_six_plus_custom():
    """The condition vocabulary matches the issue specification."""
    assert set(VALID_CONDITION_TYPES) == {
        CONDITION_ELAPSED_TIME,
        CONDITION_AERIAL_KILLS,
        CONDITION_WAVE_REACHED,
        CONDITION_FABRICATORS_DESTROYED,
        CONDITION_BOSS_HP_BELOW,
        CONDITION_HELLDIVER_CASUALTIES,
        CONDITION_CUSTOM,
    }


@pytest.mark.parametrize(
    "condition_type",
    [
        CONDITION_ELAPSED_TIME,
        CONDITION_AERIAL_KILLS,
        CONDITION_WAVE_REACHED,
        CONDITION_FABRICATORS_DESTROYED,
        CONDITION_HELLDIVER_CASUALTIES,
    ],
)
def test_validate_accepts_minimal_valid_trigger(condition_type):
    """Each non-custom condition accepts a trigger with an objective payload."""
    validate_sortie_event_trigger(_make_trigger(condition_type=condition_type, threshold=10))


def test_validate_accepts_boss_hp_trigger_within_unit_interval():
    """boss_hp_below accepts thresholds inside [0.0, 1.0]."""
    validate_sortie_event_trigger(_make_trigger(condition_type=CONDITION_BOSS_HP_BELOW, threshold=0.5))


def test_validate_accepts_custom_with_predicate():
    """custom condition requires a callable predicate."""
    trigger = _make_trigger(condition_type=CONDITION_CUSTOM, threshold=0, predicate=lambda snap: True)
    validate_sortie_event_trigger(trigger)


@pytest.mark.parametrize(
    "overrides",
    [
        {"trigger_id": ""},
        {"trigger_id": "   "},
        {"sortie_num": 0},
        {"sortie_num": 5},
        {"sortie_num": True},
        {"priority": True},
        {"condition_type": "bogus"},
        {"threshold": float("nan")},
        {"threshold": -1},
        {"threshold": True},
        {"condition_type": CONDITION_BOSS_HP_BELOW, "threshold": 1.5},
        {"condition_type": CONDITION_CUSTOM, "threshold": 0, "predicate": None},
        {"objective_update": None},
        {"dialogue_node_id": "no_such_node", "objective_update": None},
        {"banter_category": "no_such_category", "objective_update": None},
        {"once": "yes"},
    ],
)
def test_validate_rejects_invalid_triggers(overrides):
    """Every invalid field combination raises ValueError."""
    with pytest.raises(ValueError):
        validate_sortie_event_trigger(_make_trigger(**overrides))


def test_validate_rejects_non_trigger_type():
    """Passing anything other than a SortieEventTrigger raises TypeError."""
    with pytest.raises(TypeError):
        validate_sortie_event_trigger("not a trigger")


def test_has_radio_payload_reflects_dialogue_or_banter():
    """Only dialogue or banter payloads count as radio payloads."""
    assert _make_trigger().has_radio_payload is False
    assert _make_trigger(dialogue_node_id="sortie_1_inflight", objective_update=None).has_radio_payload is True
    assert _make_trigger(banter_category="kill_streak", objective_update=None).has_radio_payload is True
    assert math.isfinite(_make_trigger().threshold)
