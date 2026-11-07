"""Unit tests for in-flight narrative triggers and telemetry sanitization (Issue #68)."""

import logging
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
        {"sortie_num": 7},
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


# -----------------------------------------------------------------------------
# 3. NarrativeTriggerManager: registration, evaluation, queue, dispatch, reset
# -----------------------------------------------------------------------------

from eagle1.story import CampaignSaveManager, CommsHUD, MissionController, StoryManager  # noqa: E402
from eagle1.story import narrative_trigger_manager as ntm_module  # noqa: E402
from eagle1.story.narrative_trigger_manager import NarrativeTriggerManager  # noqa: E402
from eagle1.story.story_manager import DECISION_TIME_DILATION, NORMAL_TIME_DILATION  # noqa: E402


@pytest.fixture
def story_mgr(tmp_path):
    """Isolated StoryManager backed by a temporary save directory."""
    return StoryManager(save_manager=CampaignSaveManager(data_dir=tmp_path))


@pytest.fixture
def mission_ctrl(story_mgr):
    return MissionController(story_mgr)


@pytest.fixture
def comms(story_mgr):
    return CommsHUD(story_manager=story_mgr)


@pytest.fixture
def manager(story_mgr, comms, mission_ctrl):
    mgr = NarrativeTriggerManager(story_mgr, comms_hud=comms, mission_controller=mission_ctrl)
    mgr.reset_for_sortie(1)
    return mgr


def _trigger(trigger_id, condition_type=CONDITION_AERIAL_KILLS, threshold=1, priority=0, sortie_num=1, **kwargs):
    """Build a trigger; defaults to an objective payload when no radio payload is given."""
    if "dialogue_node_id" not in kwargs and "banter_category" not in kwargs and "objective_update" not in kwargs:
        kwargs["objective_update"] = f"Objective {trigger_id}"
    return SortieEventTrigger(
        trigger_id=trigger_id,
        sortie_num=sortie_num,
        priority=priority,
        condition_type=condition_type,
        threshold=threshold,
        **kwargs,
    )


def test_constructor_rejects_invalid_story_manager():
    """A NarrativeTriggerManager requires a real StoryManager."""
    for bad in (None, True, object()):
        with pytest.raises(TypeError):
            NarrativeTriggerManager(bad)


@pytest.mark.parametrize(
    ("condition_type", "threshold", "below", "at"),
    [
        (CONDITION_ELAPSED_TIME, 30.0, {"elapsed_seconds": 29.9}, {"elapsed_seconds": 30.0}),
        (CONDITION_AERIAL_KILLS, 5, {"aerial_kills": 4}, {"aerial_kills": 5}),
        (CONDITION_WAVE_REACHED, 2, {"current_wave": 1}, {"current_wave": 2}),
        (CONDITION_FABRICATORS_DESTROYED, 1, {"fabricators_destroyed": 0}, {"fabricators_destroyed": 1}),
        (CONDITION_HELLDIVER_CASUALTIES, 2, {"casualties_count": 1}, {"casualties_count": 2}),
    ],
)
def test_each_condition_type_fires_at_threshold(manager, condition_type, threshold, below, at):
    """Standard conditions stay silent below the threshold and fire at it."""
    manager.register_trigger(_trigger("t", condition_type=condition_type, threshold=threshold))

    assert manager.evaluate(CombatTelemetrySnapshot(**below)) == ()
    assert manager.evaluate(CombatTelemetrySnapshot(**at)) == ("t",)


def test_boss_hp_below_requires_active_boss(manager):
    """boss_hp_below fires only while a boss is active and below the ratio."""
    manager.register_trigger(_trigger("boss", condition_type=CONDITION_BOSS_HP_BELOW, threshold=0.5))

    assert manager.evaluate(CombatTelemetrySnapshot(boss_active=True, boss_hp_ratio=0.5)) == ()
    assert manager.evaluate(CombatTelemetrySnapshot(boss_active=False, boss_hp_ratio=0.1)) == ()
    assert manager.evaluate(CombatTelemetrySnapshot(boss_active=True, boss_hp_ratio=0.49)) == ("boss",)


def test_custom_predicate_fires_and_exception_is_contained(manager):
    """A custom predicate drives the condition; a raising predicate is logged, not propagated."""
    manager.register_trigger(
        _trigger(
            "custom_ok",
            condition_type=CONDITION_CUSTOM,
            threshold=0,
            predicate=lambda snap: snap.active_500kg_inbound,
        )
    )
    assert manager.evaluate(CombatTelemetrySnapshot(active_500kg_inbound=True)) == ("custom_ok",)

    def _boom(_snap):
        raise RuntimeError("bad predicate")

    manager.register_trigger(
        _trigger("custom_boom", condition_type=CONDITION_CUSTOM, threshold=0, predicate=_boom)
    )
    assert manager.evaluate(CombatTelemetrySnapshot()) == ()


def test_once_trigger_never_refires_in_same_sortie(manager):
    """A once=True trigger fires exactly once until the sortie is reset."""
    manager.register_trigger(_trigger("t", threshold=1))
    snap = CombatTelemetrySnapshot(aerial_kills=3)

    assert manager.evaluate(snap) == ("t",)
    assert manager.evaluate(snap) == ()
    assert manager.evaluate(snap) == ()


def test_repeatable_trigger_fires_on_rising_edge_only(manager):
    """once=False fires on each false-to-true transition of its condition."""
    manager.register_trigger(_trigger("t", threshold=1, once=False))

    assert manager.evaluate(CombatTelemetrySnapshot(aerial_kills=1)) == ("t",)
    assert manager.evaluate(CombatTelemetrySnapshot(aerial_kills=1)) == ()
    assert manager.evaluate(CombatTelemetrySnapshot(aerial_kills=0)) == ()
    assert manager.evaluate(CombatTelemetrySnapshot(aerial_kills=1)) == ("t",)


def test_simultaneous_triggers_ordered_by_priority_then_registration(manager):
    """Same-tick triggers are reported by descending priority, then registration order."""
    manager.register_triggers([
        _trigger("a", priority=1),
        _trigger("b", priority=5),
        _trigger("c", priority=5),
    ])

    assert manager.evaluate(CombatTelemetrySnapshot(aerial_kills=1)) == ("b", "c", "a")


def test_objective_only_trigger_applies_immediately(manager, mission_ctrl):
    """A trigger without a radio payload updates the HUD objective at fire time."""
    manager.register_trigger(_trigger("obj", threshold=1, objective_update="Destroy the furnace"))

    manager.evaluate(CombatTelemetrySnapshot(aerial_kills=1))

    assert mission_ctrl.get_active_objective_text() == "Destroy the furnace"


def test_dialogue_trigger_engages_time_dilation(manager, story_mgr, comms):
    """Firing a dialogue trigger starts the interactive beat with decision time dilation."""
    manager.register_trigger(_trigger("dlg", threshold=1, dialogue_node_id="sortie_1_inflight", objective_update=None))

    assert manager.evaluate(CombatTelemetrySnapshot(aerial_kills=1)) == ("dlg",)
    assert story_mgr.time_dilation == DECISION_TIME_DILATION
    assert comms.is_active is True
    assert manager.dispatch_log == ["dlg"]


def test_dialogue_triggers_queue_while_active_and_drain_after_choice(manager, story_mgr, comms):
    """A second beat waits until the first interactive dialogue is resolved and dismissed."""
    manager.register_triggers([
        _trigger("first", threshold=1, priority=5, dialogue_node_id="sortie_1_inflight", objective_update=None),
        _trigger("second", threshold=1, priority=1, dialogue_node_id="bridge_vance_logistics", objective_update=None),
    ])

    manager.evaluate(CombatTelemetrySnapshot(aerial_kills=1))
    assert manager.dispatch_log == ["first"]
    assert [t.trigger_id for t in manager.pending_queue] == ["second"]

    manager.evaluate(CombatTelemetrySnapshot(aerial_kills=1))
    assert manager.dispatch_log == ["first"]

    story_mgr.record_choice("sortie_1_inflight", "loyal")
    comms.dismiss()
    manager.evaluate(CombatTelemetrySnapshot(aerial_kills=1))

    assert manager.dispatch_log == ["first", "second"]
    assert manager.pending_queue == []


def test_banter_waits_for_active_callout(manager, comms):
    """Banter is held back while another callout is on screen and dispatched after dismissal."""
    manager.register_trigger(_trigger("banter", threshold=1, banter_category="kill_streak", objective_update=None))
    comms.trigger_callout("Other", "busy channel")

    manager.evaluate(CombatTelemetrySnapshot(aerial_kills=1))
    assert manager.dispatch_log == []

    comms.dismiss()
    manager.evaluate(CombatTelemetrySnapshot(aerial_kills=1))
    assert manager.dispatch_log == ["banter"]
    assert comms.is_active is True


def test_objective_of_radio_trigger_applies_on_dispatch_not_on_fire(manager, mission_ctrl, comms):
    """A radio trigger's objective change waits until its transmission is actually dispatched."""
    before = mission_ctrl.get_active_objective_text()
    comms.trigger_callout("Other", "busy channel")
    manager.register_trigger(
        _trigger("dlg", threshold=1, dialogue_node_id="sortie_1_inflight", objective_update="Hold the line")
    )

    manager.evaluate(CombatTelemetrySnapshot(aerial_kills=1))
    assert mission_ctrl.get_active_objective_text() == before

    comms.dismiss()
    manager.evaluate(CombatTelemetrySnapshot(aerial_kills=1))
    assert mission_ctrl.get_active_objective_text() == "Hold the line"


def test_reset_for_sortie_clears_state_and_switches_triggers(manager):
    """reset_for_sortie purges fired state and selects the new sortie's triggers."""
    manager.register_trigger(_trigger("s1", threshold=1))
    manager.register_trigger(_trigger("s2", threshold=1, sortie_num=2))
    snap = CombatTelemetrySnapshot(aerial_kills=1)

    assert manager.evaluate(snap) == ("s1",)
    manager.reset_for_sortie(1)
    assert manager.fired_trigger_ids == set()
    assert manager.pending_queue == []
    assert manager.dispatch_log == []
    assert manager.evaluate(snap) == ("s1",)

    assert manager.evaluate(snap) == ()
    manager.reset_for_sortie(2)
    assert manager.evaluate(snap) == ("s2",)


@pytest.mark.parametrize("bad_sortie", [True, 0, 99, "2", None])
def test_reset_for_sortie_sanitizes_invalid_input(manager, bad_sortie):
    """Invalid sortie numbers fall back to sortie 1."""
    manager.reset_for_sortie(bad_sortie)
    assert manager.active_sortie_num == 1


def test_duplicate_trigger_id_rejected(manager):
    """Registering the same trigger_id twice is an error."""
    manager.register_trigger(_trigger("dup"))
    with pytest.raises(ValueError):
        manager.register_trigger(_trigger("dup"))


def test_evaluate_with_invalid_telemetry_returns_empty(manager):
    """Non-snapshot telemetry is ignored instead of raising."""
    assert manager.evaluate(None) == ()


def test_manager_works_without_comms_and_mission_controller(story_mgr):
    """Dialogue triggers still start the beat and banter is skipped without a HUD."""
    manager = NarrativeTriggerManager(story_mgr)
    manager.reset_for_sortie(1)
    manager.register_trigger(_trigger("dlg", threshold=1, dialogue_node_id="sortie_1_inflight", objective_update=None))
    manager.register_trigger(_trigger("banter", threshold=1, banter_category="kill_streak", objective_update=None))

    manager.evaluate(CombatTelemetrySnapshot(aerial_kills=1))

    assert story_mgr.is_dialogue_active is True
    assert story_mgr.time_dilation == DECISION_TIME_DILATION
    assert NORMAL_TIME_DILATION != DECISION_TIME_DILATION


def test_public_api_exports():
    """The narrative trigger API is re-exported from the eagle1.story package."""
    import eagle1.story as story_pkg

    expected = {
        "CONDITION_AERIAL_KILLS",
        "CONDITION_BOSS_HP_BELOW",
        "CONDITION_CUSTOM",
        "CONDITION_ELAPSED_TIME",
        "CONDITION_FABRICATORS_DESTROYED",
        "CONDITION_HELLDIVER_CASUALTIES",
        "CONDITION_WAVE_REACHED",
        "VALID_CONDITION_TYPES",
        "CombatTelemetrySnapshot",
        "NarrativeTriggerManager",
        "SortieEventTrigger",
        "validate_sortie_event_trigger",
    }
    assert expected <= set(story_pkg.__all__)
    for name in expected:
        assert hasattr(story_pkg, name)


# -----------------------------------------------------------------------------
# 4. Ship-review hardening: queue ordering, latching, logging and delivery
# -----------------------------------------------------------------------------

def _banter(trigger_id, **kwargs):
    """Build a once-only banter trigger without an objective payload."""
    return _trigger(trigger_id, banter_category="kill_streak", objective_update=None, **kwargs)


def test_late_high_priority_beat_jumps_queue(manager, comms):
    """A higher-priority beat that fires on a later frame is dispatched before older queued beats."""
    manager.register_triggers([
        _banter("low", threshold=1, priority=1),
        _banter("high", threshold=2, priority=9),
    ])
    comms.trigger_callout("Other", "busy channel")

    manager.evaluate(CombatTelemetrySnapshot(aerial_kills=1))
    manager.evaluate(CombatTelemetrySnapshot(aerial_kills=2))
    assert [t.trigger_id for t in manager.pending_queue] == ["high", "low"]

    comms.dismiss()
    manager.evaluate(CombatTelemetrySnapshot(aerial_kills=2))
    assert manager.dispatch_log == ["high"]


def test_repeatable_radio_trigger_not_queued_twice(manager, comms):
    """A repeatable beat that re-arms while still queued does not create a duplicate queue entry."""
    manager.register_trigger(_banter("rep", threshold=1, once=False))
    comms.trigger_callout("Other", "busy channel")

    for kills in (1, 0, 1):
        manager.evaluate(CombatTelemetrySnapshot(aerial_kills=kills))

    assert [t.trigger_id for t in manager.pending_queue] == ["rep"]


def test_banter_rotates_through_pool(manager, comms):
    """Consecutive banter dispatches select different lines from the category pool."""
    manager.register_triggers([_banter("a", priority=2), _banter("b", priority=1)])
    snap = CombatTelemetrySnapshot(aerial_kills=1)

    manager.evaluate(snap)
    first_line = comms.current_node.prompt
    comms.dismiss()
    manager.evaluate(snap)
    second_line = comms.current_node.prompt

    assert first_line != second_line


def test_reset_clears_repeatable_latch(manager):
    """After a reset, a repeatable trigger whose condition stays true fires again."""
    manager.register_trigger(_trigger("rep", threshold=1, once=False))
    snap = CombatTelemetrySnapshot(aerial_kills=1)

    assert list(manager.evaluate(snap)) == ["rep"]
    assert list(manager.evaluate(snap)) == []
    manager.reset_for_sortie(1)
    assert list(manager.evaluate(snap)) == ["rep"]


def test_idle_evaluate_returns_empty_sequence(manager):
    """A frame without fired triggers returns an empty sequence."""
    manager.register_trigger(_trigger("t", threshold=5))

    assert manager.evaluate(CombatTelemetrySnapshot()) == ()


def test_failing_predicate_is_logged_once_until_reset(manager, caplog):
    """A raising predicate warns once per sortie instead of every frame."""
    def _boom(_snap):
        raise RuntimeError("bad predicate")

    manager.register_trigger(_trigger("boom", condition_type=CONDITION_CUSTOM, threshold=0, predicate=_boom))

    def _warnings():
        return sum("Custom predicate" in record.getMessage() for record in caplog.records)

    with caplog.at_level(logging.WARNING, logger="eagle1.story.narrative_trigger_manager"):
        for _ in range(5):
            manager.evaluate(CombatTelemetrySnapshot())
        assert _warnings() == 1

        manager.reset_for_sortie(1)
        manager.evaluate(CombatTelemetrySnapshot())
        assert _warnings() == 2


def test_undeliverable_beat_is_dropped_and_not_logged(story_mgr):
    """Banter without a comms HUD cannot be delivered, so it is dropped and not recorded as dispatched."""
    manager = NarrativeTriggerManager(story_mgr)
    manager.reset_for_sortie(1)
    manager.register_trigger(_banter("banter", threshold=1))

    manager.evaluate(CombatTelemetrySnapshot(aerial_kills=1))

    assert manager.dispatch_log == []
    assert manager.pending_queue == []


def test_dispatch_log_is_capped(manager, comms, monkeypatch):
    """The dispatch log keeps only the most recent MAX_DISPATCH_LOG entries."""
    monkeypatch.setattr(ntm_module, "MAX_DISPATCH_LOG", 2, raising=False)
    manager.register_triggers([_banter("a", priority=3), _banter("b", priority=2), _banter("c", priority=1)])
    snap = CombatTelemetrySnapshot(aerial_kills=1)

    for _ in range(3):
        manager.evaluate(snap)
        comms.dismiss()

    assert manager.dispatch_log == ["b", "c"]


def test_trigger_for_act3_sortie_is_accepted(manager):
    """Act III branch sorties (5) and the Act III-A terminal dive (6) may carry triggers."""
    manager.register_trigger(_trigger("act3_s5", threshold=1, sortie_num=5))
    manager.register_trigger(_trigger("act3_s6", threshold=1, sortie_num=6))
    manager.reset_for_sortie(5)
    assert manager.active_sortie_num == 5
    assert manager.evaluate(CombatTelemetrySnapshot(aerial_kills=1)) == ("act3_s5",)
    manager.reset_for_sortie(6)
    assert manager.active_sortie_num == 6


def test_trigger_sortie_beyond_story_range_rejected():
    """Sortie numbers above MAX_STORY_SORTIE_NUM stay invalid."""
    with pytest.raises(ValueError):
        validate_sortie_event_trigger(_trigger("too_far", sortie_num=7))
