"""Unit and headless integration tests for Act I Sortie 1 & 2 narrative cues (Issue #69)."""

import pytest

from eagle1.story.campaign_act1 import (
    ACT1_CHOICE_OBJECTIVES,
    ACT1_TRIGGERS,
    SORTIE1_INFLIGHT_NODE_ID,
    SORTIE1_OBJECTIVE_DISSIDENT,
    SORTIE1_OBJECTIVE_LOYAL,
    SORTIE1_OBJECTIVE_NEUTRAL,
    SORTIE2_EXTRACTION_WAVE,
    SORTIE2_INFLIGHT_NODE_ID,
    SORTIE2_PERIMETER_OBJECTIVE,
    SORTIE2_OBJECTIVE_DISSIDENT,
    SORTIE2_OBJECTIVE_LOYAL,
    SORTIE2_OBJECTIVE_NEUTRAL,
    apply_sortie1_choice_effect,
    apply_sortie2_choice_effect,
    register_act1_triggers,
    resolve_act1_choice,
)
from eagle1.story.campaign_save import CampaignSaveManager
from eagle1.story.comms_hud import CommsHUD
from eagle1.story.mission_controller import CAMPAIGN_SORTIE_REGISTRY, MissionController, validate_sortie_registry
from eagle1.story.narrative_trigger_manager import (
    CombatTelemetrySnapshot,
    NarrativeTriggerManager,
    validate_sortie_event_trigger,
)
from eagle1.story.story_manager import DEFAULT_LOYALTY, StoryManager
from eagle1.story.dialogue_data import BANTER_QUEUES, get_contextual_banter, validate_viper_dialogue_data
from eagle1.story.dialogue_db import (
    DIALOGUE_DATABASE,
    get_dialogue_node,
    get_nodes_for_act_and_sortie,
    validate_dialogue_database,
)


# -----------------------------------------------------------------------------
# 1. Act I dialogue nodes
# -----------------------------------------------------------------------------

def test_act1_dialogue_database_is_valid():
    """The full dialogue database, including the new Sortie 2 nodes, passes validation."""
    assert validate_dialogue_database(DIALOGUE_DATABASE) is True


@pytest.mark.parametrize(
    ("node_id", "expected_sortie"),
    [
        ("sortie_1_inflight", 1),
        ("sortie_2_briefing", 2),
        ("sortie_2_inflight", 2),
        ("sortie_2_hangar_debrief", 2),
    ],
)
def test_act1_required_nodes_exist(node_id, expected_sortie):
    """Each required Act I node exists, belongs to Act 1 and offers all three stances."""
    node = get_dialogue_node(node_id)
    assert node is not None
    assert node.act == 1
    assert node.sortie == expected_sortie
    assert set(node.options) == {"loyal", "neutral", "dissident"}


def test_sortie_2_nodes_listed_for_act1_sortie2():
    """get_nodes_for_act_and_sortie(1, 2) returns the three new Sortie 2 nodes."""
    node_ids = {n.node_id for n in get_nodes_for_act_and_sortie(act=1, sortie=2)}
    assert {"sortie_2_briefing", "sortie_2_inflight", "sortie_2_hangar_debrief"} <= node_ids


@pytest.mark.parametrize(
    ("node_id", "loyal", "neutral", "dissident"),
    [
        ("sortie_1_inflight", 8.0, 0.0, -8.0),
        ("sortie_2_inflight", 8.0, 0.0, -8.0),
    ],
)
def test_inflight_loyalty_deltas(node_id, loyal, neutral, dissident):
    """In-flight stance deltas match the Issue #69 specification."""
    node = get_dialogue_node(node_id)
    assert node.options["loyal"].loyalty_delta == pytest.approx(loyal)
    assert node.options["neutral"].loyalty_delta == pytest.approx(neutral)
    assert node.options["dissident"].loyalty_delta == pytest.approx(dissident)


# -----------------------------------------------------------------------------
# 2. Sortie registry wiring
# -----------------------------------------------------------------------------

@pytest.mark.parametrize("sortie_num", [1, 2])
def test_sortie_registry_act1_node_ids_resolve(sortie_num):
    """Every node id referenced by an Act I sortie config resolves to a dialogue node."""
    cfg = CAMPAIGN_SORTIE_REGISTRY[sortie_num]
    for node_id in (cfg.briefing_node_id, *cfg.inflight_node_ids, cfg.debrief_node_id):
        assert get_dialogue_node(node_id) is not None, node_id


def test_sortie_2_registry_uses_act1_nodes():
    """Sortie 2 briefing and debrief point at the new Act I nodes; the registry stays valid."""
    cfg = CAMPAIGN_SORTIE_REGISTRY[2]
    assert cfg.briefing_node_id == "sortie_2_briefing"
    assert cfg.inflight_node_ids == ("sortie_2_inflight",)
    assert cfg.debrief_node_id == "sortie_2_hangar_debrief"
    assert validate_sortie_registry() is True


# -----------------------------------------------------------------------------
# 3. Act I radio cue banter categories
# -----------------------------------------------------------------------------

ACT1_BANTER_CATEGORIES = (
    "act1_s1_checkin_eagle",
    "act1_s1_checkin_apex",
    "act1_s1_vanguard_doc",
    "act1_s1_radar_braker",
    "act1_s2_perimeter_ghost",
    "act1_s2_extraction_pelican",
)


@pytest.mark.parametrize("category", ACT1_BANTER_CATEGORIES)
def test_act1_banter_categories_have_single_line(category):
    """Each Act I cue category holds exactly one line tagged with its own category."""
    assert len(BANTER_QUEUES[category]) == 1
    assert BANTER_QUEUES[category][0].category == category


@pytest.mark.parametrize("category", ACT1_BANTER_CATEGORIES)
def test_act1_banter_is_deterministic(category):
    """Selection index does not change which Act I line is delivered."""
    assert get_contextual_banter(category, selection_index=0) is get_contextual_banter(category, selection_index=7)


def test_viper_dialogue_data_still_valid():
    """Adding Act I categories keeps the Viper dialogue data valid."""
    assert validate_viper_dialogue_data() is True


# -----------------------------------------------------------------------------
# 4. Act I trigger table and registration
# -----------------------------------------------------------------------------

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
    """NarrativeTriggerManager with all Act I triggers registered."""
    mgr = NarrativeTriggerManager(story_mgr, comms_hud=comms, mission_controller=mission_ctrl)
    register_act1_triggers(mgr)
    return mgr


def _predicate(trigger_id):
    return next(t.predicate for t in ACT1_TRIGGERS if t.trigger_id == trigger_id)


def test_act1_triggers_are_valid():
    """Every Act I trigger passes the trigger validator."""
    for trigger in ACT1_TRIGGERS:
        validate_sortie_event_trigger(trigger)


def test_act1_trigger_ids_unique_and_scoped():
    """Trigger ids are unique, prefixed with act1_, and cover Sorties 1 and 2 only."""
    ids = [t.trigger_id for t in ACT1_TRIGGERS]
    assert len(set(ids)) == len(ids)
    assert all(i.startswith("act1_") for i in ids)
    assert {t.sortie_num for t in ACT1_TRIGGERS} == {1, 2}


def test_act1_priorities_follow_story_order():
    """Within each sortie, priorities strictly decrease in table order."""
    for sortie_num in (1, 2):
        prios = [t.priority for t in ACT1_TRIGGERS if t.sortie_num == sortie_num]
        assert all(a > b for a, b in zip(prios, prios[1:]))


def test_register_act1_triggers_returns_count(story_mgr):
    """A fresh manager receives all Act I triggers, in story order per sortie."""
    mgr = NarrativeTriggerManager(story_mgr)
    assert register_act1_triggers(mgr) == len(ACT1_TRIGGERS) == 8
    assert [t.trigger_id for t in mgr.get_triggers_for_sortie(1)] == [
        "act1_s1_checkin_eagle",
        "act1_s1_checkin_apex",
        "act1_s1_vanguard_doc",
        "act1_s1_radar_braker",
        "act1_s1_reiner_override",
    ]
    assert [t.trigger_id for t in mgr.get_triggers_for_sortie(2)] == [
        "act1_s2_perimeter_breach",
        "act1_s2_supply_dilemma",
        "act1_s2_extraction",
    ]


def test_register_act1_triggers_twice_is_rejected_atomically(manager):
    """A second registration fails and leaves the manager's trigger lists untouched."""
    with pytest.raises(ValueError, match="already registered"):
        register_act1_triggers(manager)
    assert len(manager.get_triggers_for_sortie(1)) == 5
    assert len(manager.get_triggers_for_sortie(2)) == 3


@pytest.mark.parametrize("bad_manager", [None, object(), "manager"])
def test_register_act1_triggers_rejects_invalid_manager(bad_manager):
    """Non-manager arguments raise TypeError."""
    with pytest.raises(TypeError):
        register_act1_triggers(bad_manager)


def test_sortie2_extraction_wave_matches_registry():
    """The Sortie 2 extraction callout uses the registry's target wave count."""
    assert SORTIE2_EXTRACTION_WAVE == CAMPAIGN_SORTIE_REGISTRY[2].target_waves == 4


def test_override_predicate():
    """Reiner's override fires on wave 2 or at 10 aerial kills, not before."""
    pred = _predicate("act1_s1_reiner_override")
    assert pred(CombatTelemetrySnapshot(aerial_kills=9, current_wave=1)) is False
    assert pred(CombatTelemetrySnapshot(aerial_kills=10)) is True
    assert pred(CombatTelemetrySnapshot(current_wave=2)) is True


def test_supply_dilemma_predicate():
    """The Sortie 2 dilemma fires on a casualty, a critical Helldiver, or wave 2."""
    pred = _predicate("act1_s2_supply_dilemma")
    assert pred(CombatTelemetrySnapshot(current_wave=1)) is False
    assert pred(CombatTelemetrySnapshot(casualties_count=1)) is True
    assert pred(CombatTelemetrySnapshot(any_helldiver_critical=True)) is True
    assert pred(CombatTelemetrySnapshot(current_wave=2)) is True


# -----------------------------------------------------------------------------
# 5. Choice effects on the HUD objective
# -----------------------------------------------------------------------------

def test_choice_objectives_cover_all_stances():
    """Both in-flight nodes map every stance to a distinct objective within the HUD length limit."""
    texts = []
    for node_id in (SORTIE1_INFLIGHT_NODE_ID, SORTIE2_INFLIGHT_NODE_ID):
        assert set(ACT1_CHOICE_OBJECTIVES[node_id]) == {"loyal", "neutral", "dissident"}
        texts.extend(ACT1_CHOICE_OBJECTIVES[node_id].values())
    assert len(set(texts)) == len(texts)
    assert all(len(text) <= 250 for text in texts)


@pytest.mark.parametrize(
    ("stance", "expected"),
    [
        ("loyal", SORTIE1_OBJECTIVE_LOYAL),
        ("neutral", SORTIE1_OBJECTIVE_NEUTRAL),
        ("dissident", SORTIE1_OBJECTIVE_DISSIDENT),
    ],
)
def test_apply_sortie1_choice_effect_sets_objective(mission_ctrl, stance, expected):
    """Sortie 1 stance sets the matching HUD objective."""
    assert apply_sortie1_choice_effect(stance, mission_ctrl) == expected
    assert mission_ctrl.current_objective == expected


@pytest.mark.parametrize(
    ("stance", "expected"),
    [
        ("loyal", SORTIE2_OBJECTIVE_LOYAL),
        ("neutral", SORTIE2_OBJECTIVE_NEUTRAL),
        ("dissident", SORTIE2_OBJECTIVE_DISSIDENT),
    ],
)
def test_apply_sortie2_choice_effect_sets_objective(mission_ctrl, stance, expected):
    """Sortie 2 stance sets the matching HUD objective."""
    assert apply_sortie2_choice_effect(stance, mission_ctrl) == expected
    assert mission_ctrl.current_objective == expected


@pytest.mark.parametrize(
    ("alias", "canonical"),
    [("1", "loyal"), ("[NEUTRAL]", "neutral"), (" Dissident ", "dissident")],
)
def test_choice_effect_accepts_stance_aliases(mission_ctrl, alias, canonical):
    """Key numbers, bracketed labels and padded or mixed-case stances normalize to canonical stances."""
    expected = ACT1_CHOICE_OBJECTIVES[SORTIE1_INFLIGHT_NODE_ID][canonical]
    assert apply_sortie1_choice_effect(alias, mission_ctrl) == expected


@pytest.mark.parametrize("bad_stance", [None, True, "", "heroic", 1])
def test_choice_effect_rejects_invalid_stance(mission_ctrl, bad_stance):
    """Invalid stances apply nothing and leave the current objective unchanged."""
    before = mission_ctrl.current_objective
    assert apply_sortie1_choice_effect(bad_stance, mission_ctrl) is None
    assert mission_ctrl.current_objective == before


def test_choice_effect_without_mission_controller():
    """Missing MissionController is tolerated and reports nothing applied."""
    assert apply_sortie2_choice_effect("loyal", None) is None


def test_resolve_act1_choice_routes_and_ignores_foreign_nodes(mission_ctrl):
    """resolve_act1_choice routes Act I nodes and ignores everything else."""
    assert resolve_act1_choice("sortie_1_inflight", "loyal", mission_ctrl) == SORTIE1_OBJECTIVE_LOYAL
    assert resolve_act1_choice(" sortie_2_inflight ", "dissident", mission_ctrl) == SORTIE2_OBJECTIVE_DISSIDENT

    before = mission_ctrl.current_objective
    for node_id in ["sortie_1_briefing", "unknown", None, 42]:
        assert resolve_act1_choice(node_id, "loyal", mission_ctrl) is None
        assert mission_ctrl.current_objective == before


# -----------------------------------------------------------------------------
# 6. Headless integration: Sortie 1 and Sortie 2 from launch to extraction
# -----------------------------------------------------------------------------

def _start(mission_ctrl, manager, sortie_num):
    """Start a sortie on the controller and select its triggers on the manager."""
    mission_ctrl.start_sortie(sortie_num)
    manager.reset_for_sortie(sortie_num)


def _finish_callout(comms):
    """Dismiss a finished non-interactive callout so the next queued beat can dispatch."""
    if comms.is_active and comms.current_node is not None and not comms.current_node.options:
        comms.dismiss()


def _pump(manager, comms, telemetry, frames=10):
    """Simulate frames: close finished callouts and evaluate; returns all fired ids in order."""
    fired = []
    for _ in range(frames):
        _finish_callout(comms)
        fired.extend(manager.evaluate(telemetry))
    return fired


def _answer(story_mgr, comms, mission_ctrl, node_id, stance):
    """Record the pilot's choice like CommsHUD does, close the overlay and apply the Act I effect."""
    option = story_mgr.record_choice(node_id, stance)
    comms.dismiss()
    resolve_act1_choice(node_id, stance, mission_ctrl)
    return option


def test_sortie1_no_beats_before_checkin(mission_ctrl, manager):
    """No Sortie 1 beat fires before the two-second check-in."""
    _start(mission_ctrl, manager, 1)
    assert manager.evaluate(CombatTelemetrySnapshot(elapsed_seconds=1.9)) == ()
    assert manager.dispatch_log == []


def test_sortie1_progression_launch_to_override(story_mgr, mission_ctrl, comms, manager):
    """Sortie 1 beats fire in story order: check-ins, vanguard banter, then Reiner's override."""
    _start(mission_ctrl, manager, 1)

    _pump(manager, comms, CombatTelemetrySnapshot(elapsed_seconds=2.0, current_wave=1))
    assert manager.dispatch_log == ["act1_s1_checkin_eagle", "act1_s1_checkin_apex"]

    _pump(manager, comms, CombatTelemetrySnapshot(elapsed_seconds=20.0, current_wave=1, aerial_kills=5))
    assert manager.dispatch_log[-2:] == ["act1_s1_vanguard_doc", "act1_s1_radar_braker"]
    assert story_mgr.is_dialogue_active is False

    _pump(manager, comms, CombatTelemetrySnapshot(elapsed_seconds=40.0, current_wave=1, aerial_kills=10))
    assert manager.dispatch_log[-1] == "act1_s1_reiner_override"
    assert story_mgr.active_dialogue.node_id == "sortie_1_inflight"
    assert comms.current_node.node_id == "sortie_1_inflight"


def test_sortie1_override_fires_on_wave_two_without_kills(mission_ctrl, comms, manager):
    """The override fires on wave 2 even with zero kills; the vanguard cue does not."""
    _start(mission_ctrl, manager, 1)
    _pump(manager, comms, CombatTelemetrySnapshot(elapsed_seconds=60.0, current_wave=2, aerial_kills=0))
    assert "act1_s1_reiner_override" in manager.dispatch_log
    assert "act1_s1_vanguard_doc" not in manager.fired_trigger_ids


def test_sortie1_kill_burst_queues_beats_chronologically(mission_ctrl, comms, manager):
    """A 0 -> 12 kill jump in one frame queues vanguard, radar and override in story order."""
    _start(mission_ctrl, manager, 1)
    _pump(manager, comms, CombatTelemetrySnapshot(elapsed_seconds=5.0), frames=1)
    _pump(manager, comms, CombatTelemetrySnapshot(elapsed_seconds=5.0), frames=5)

    burst = CombatTelemetrySnapshot(elapsed_seconds=6.0, aerial_kills=12)
    fired = manager.evaluate(burst)
    assert fired == ("act1_s1_vanguard_doc", "act1_s1_radar_braker", "act1_s1_reiner_override")

    _pump(manager, comms, burst, frames=5)
    assert manager.dispatch_log[-3:] == ["act1_s1_vanguard_doc", "act1_s1_radar_braker", "act1_s1_reiner_override"]
    assert manager.pending_queue == []


@pytest.mark.parametrize(
    ("stance", "delta", "objective"),
    [
        ("loyal", 8.0, SORTIE1_OBJECTIVE_LOYAL),
        ("neutral", 0.0, SORTIE1_OBJECTIVE_NEUTRAL),
        ("dissident", -8.0, SORTIE1_OBJECTIVE_DISSIDENT),
    ],
)
def test_sortie1_choice_updates_loyalty_history_and_objective(story_mgr, mission_ctrl, comms, manager, stance, delta, objective):
    """Each Sortie 1 stance moves loyalty, records history, sets the HUD objective and clears the overlay."""
    _start(mission_ctrl, manager, 1)
    _pump(manager, comms, CombatTelemetrySnapshot(elapsed_seconds=30.0, current_wave=2, aerial_kills=10))
    assert story_mgr.is_dialogue_active is True

    _answer(story_mgr, comms, mission_ctrl, "sortie_1_inflight", stance)

    assert story_mgr.loyalty == pytest.approx(DEFAULT_LOYALTY + delta)
    assert story_mgr.dialogue_history[-1] == {
        "node": "sortie_1_inflight",
        "stance": stance,
        "loyalty_delta": delta,
        "act": 1,
        "sortie": 1,
    }
    assert mission_ctrl.get_active_objective_text() == objective
    assert story_mgr.is_dialogue_active is False
    assert comms.is_active is False


def test_sortie2_progression_perimeter_dilemma_extraction(story_mgr, mission_ctrl, comms, manager):
    """Sortie 2 runs perimeter breach, supply dilemma, then the extraction callout."""
    _start(mission_ctrl, manager, 2)

    _pump(manager, comms, CombatTelemetrySnapshot(elapsed_seconds=3.0, current_wave=1))
    assert manager.dispatch_log == ["act1_s2_perimeter_breach"]
    assert mission_ctrl.current_objective == SORTIE2_PERIMETER_OBJECTIVE

    _pump(manager, comms, CombatTelemetrySnapshot(elapsed_seconds=30.0, current_wave=1, casualties_count=1))
    assert manager.dispatch_log[-1] == "act1_s2_supply_dilemma"
    assert story_mgr.active_dialogue.node_id == "sortie_2_inflight"

    _answer(story_mgr, comms, mission_ctrl, "sortie_2_inflight", "neutral")
    assert mission_ctrl.current_objective == SORTIE2_OBJECTIVE_NEUTRAL

    _pump(manager, comms, CombatTelemetrySnapshot(elapsed_seconds=120.0, current_wave=SORTIE2_EXTRACTION_WAVE, casualties_count=1))
    assert manager.dispatch_log[-1] == "act1_s2_extraction"
    assert mission_ctrl.current_objective == CAMPAIGN_SORTIE_REGISTRY[2].extraction_objective


@pytest.mark.parametrize(
    ("stance", "delta", "objective"),
    [
        ("loyal", 8.0, SORTIE2_OBJECTIVE_LOYAL),
        ("neutral", 0.0, SORTIE2_OBJECTIVE_NEUTRAL),
        ("dissident", -8.0, SORTIE2_OBJECTIVE_DISSIDENT),
    ],
)
def test_sortie2_choice_updates_loyalty_history_and_objective(story_mgr, mission_ctrl, comms, manager, stance, delta, objective):
    """Each Sortie 2 stance moves loyalty, records history, sets the HUD objective and clears the overlay."""
    _start(mission_ctrl, manager, 2)
    _pump(manager, comms, CombatTelemetrySnapshot(elapsed_seconds=30.0, current_wave=1, any_helldiver_critical=True))
    assert story_mgr.is_dialogue_active is True

    _answer(story_mgr, comms, mission_ctrl, "sortie_2_inflight", stance)

    assert story_mgr.loyalty == pytest.approx(DEFAULT_LOYALTY + delta)
    assert story_mgr.dialogue_history[-1] == {
        "node": "sortie_2_inflight",
        "stance": stance,
        "loyalty_delta": delta,
        "act": 1,
        "sortie": 2,
    }
    assert mission_ctrl.get_active_objective_text() == objective
    assert story_mgr.is_dialogue_active is False
    assert comms.is_active is False


def test_sortie2_wave_jump_keeps_story_order(story_mgr, mission_ctrl, comms, manager):
    """A jump straight to the final wave keeps story order and holds extraction behind the open dilemma."""
    _start(mission_ctrl, manager, 2)
    snapshot = CombatTelemetrySnapshot(current_wave=SORTIE2_EXTRACTION_WAVE)

    fired = manager.evaluate(snapshot)
    assert fired == ("act1_s2_perimeter_breach", "act1_s2_supply_dilemma", "act1_s2_extraction")

    _pump(manager, comms, snapshot, frames=5)
    assert manager.dispatch_log == ["act1_s2_perimeter_breach", "act1_s2_supply_dilemma"]

    _answer(story_mgr, comms, mission_ctrl, "sortie_2_inflight", "loyal")
    _pump(manager, comms, snapshot, frames=5)
    assert manager.dispatch_log[-1] == "act1_s2_extraction"
    assert mission_ctrl.current_objective == CAMPAIGN_SORTIE_REGISTRY[2].extraction_objective


def test_sortie1_triggers_do_not_fire_in_sortie2(mission_ctrl, comms, manager):
    """Sortie 1 triggers stay silent while Sortie 2 is active."""
    _start(mission_ctrl, manager, 2)
    _pump(manager, comms, CombatTelemetrySnapshot(elapsed_seconds=10.0, aerial_kills=20))
    assert not any(tid.startswith("act1_s1_") for tid in manager.fired_trigger_ids)



# -----------------------------------------------------------------------------
# 7. Public API exports
# -----------------------------------------------------------------------------

def test_act1_public_api_exports():
    """The Act I campaign helpers are re-exported from the eagle1.story package."""
    import eagle1.story as story_pkg

    expected = {
        "ACT1_CHOICE_OBJECTIVES",
        "ACT1_TRIGGERS",
        "SORTIE1_OBJECTIVE_DISSIDENT",
        "SORTIE1_OBJECTIVE_LOYAL",
        "SORTIE1_OBJECTIVE_NEUTRAL",
        "SORTIE2_OBJECTIVE_DISSIDENT",
        "SORTIE2_OBJECTIVE_LOYAL",
        "SORTIE2_OBJECTIVE_NEUTRAL",
        "apply_sortie1_choice_effect",
        "apply_sortie2_choice_effect",
        "register_act1_triggers",
        "resolve_act1_choice",
    }
    assert expected <= set(story_pkg.__all__)
    for name in expected:
        assert hasattr(story_pkg, name)
    assert story_pkg.register_act1_triggers is register_act1_triggers
