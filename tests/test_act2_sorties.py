"""Tests for the Act II campaign (#70): Sortie 3 and Sortie 4 dialogue, triggers, 500kg crisis and casualty check."""

import pytest

from eagle1.story.mission_controller import CAMPAIGN_SORTIE_REGISTRY, validate_sortie_registry
from eagle1.story.campaign_act1 import register_act1_triggers
from eagle1.story.campaign_act2 import (
    ACT2_TRIGGERS,
    SORTIE3_EXTRACTION_WAVE,
    SORTIE4_EXTRACTION_WAVE,
    register_act2_triggers,
)
from eagle1.story.campaign_save import CampaignSaveManager
from eagle1.story.comms_hud import CommsHUD
from eagle1.story.mission_controller import MissionController
from eagle1.story.narrative_trigger_manager import (
    CombatTelemetrySnapshot,
    NarrativeTriggerManager,
    validate_sortie_event_trigger,
)
from eagle1.systems.ground_support import GroundSupportManager
from eagle1.story.story_manager import StoryManager
from eagle1.story.dialogue_data import BANTER_QUEUES, get_contextual_banter, validate_viper_dialogue_data
from eagle1.story.dialogue_db import (
    DIALOGUE_DATABASE,
    get_dialogue_node,
    get_nodes_for_act_and_sortie,
    validate_dialogue_database,
)


# -----------------------------------------------------------------------------
# 1. Act II dialogue nodes
# -----------------------------------------------------------------------------

ACT2_NODE_IDS = (
    ("sortie_3_briefing", 3),
    ("sortie_3_500kg_crisis", 3),
    ("sortie_3_hangar_debrief", 3),
    ("sortie_4_briefing", 4),
    ("sortie_4_strider_crisis", 4),
    ("sortie_4_hangar_debrief", 4),
)


def test_act2_dialogue_database_is_valid():
    """The full dialogue database, including Act II nodes, passes validation."""
    assert validate_dialogue_database(DIALOGUE_DATABASE) is True


@pytest.mark.parametrize("node_id, expected_sortie", ACT2_NODE_IDS)
def test_act2_required_nodes_exist(node_id, expected_sortie):
    """Each Act II node resolves and carries the correct act and sortie."""
    node = get_dialogue_node(node_id)
    assert node is not None
    assert node.act == 2
    assert node.sortie == expected_sortie


@pytest.mark.parametrize(
    "sortie, expected",
    [
        (3, {"sortie_3_briefing", "sortie_3_500kg_crisis", "sortie_3_hangar_debrief"}),
        (4, {"sortie_4_briefing", "sortie_4_strider_crisis", "sortie_4_hangar_debrief"}),
    ],
)
def test_act2_nodes_listed_per_sortie(sortie, expected):
    """get_nodes_for_act_and_sortie(2, n) lists the Act II nodes of that sortie."""
    node_ids = {n.node_id for n in get_nodes_for_act_and_sortie(act=2, sortie=sortie)}
    assert expected <= node_ids


@pytest.mark.parametrize(
    "node_id, loyal, neutral, dissident",
    [
        ("sortie_3_500kg_crisis", 12.0, 0.0, -12.0),
        ("sortie_4_strider_crisis", 10.0, 0.0, -10.0),
    ],
)
def test_act2_inflight_loyalty_deltas(node_id, loyal, neutral, dissident):
    """In-flight Act II nodes carry the documented loyalty deltas."""
    node = get_dialogue_node(node_id)
    assert node.options["loyal"].loyalty_delta == pytest.approx(loyal)
    assert node.options["neutral"].loyalty_delta == pytest.approx(neutral)
    assert node.options["dissident"].loyalty_delta == pytest.approx(dissident)


def test_500kg_crisis_option_labels_match_issue():
    """The 500kg crisis options use the labels specified in issue #70."""
    node = get_dialogue_node("sortie_3_500kg_crisis")
    assert "Acceptable collateral damage" in node.options["loyal"].label
    assert "15 meters east" in node.options["neutral"].label
    assert "Aborting drop" in node.options["dissident"].label


# -----------------------------------------------------------------------------
# 2. Sortie registry
# -----------------------------------------------------------------------------

@pytest.mark.parametrize("sortie_num", [3, 4])
def test_sortie_registry_act2_node_ids_resolve(sortie_num):
    """Every node referenced by the Act II registry entries resolves in the dialogue database."""
    assert validate_sortie_registry() is True
    cfg = CAMPAIGN_SORTIE_REGISTRY[sortie_num]
    for node_id in (cfg.briefing_node_id, *cfg.inflight_node_ids, cfg.debrief_node_id):
        assert get_dialogue_node(node_id) is not None


def test_sortie_registry_uses_act2_nodes():
    """Sorties 3 and 4 point at their Act II briefing, in-flight and debrief nodes."""
    sortie3 = CAMPAIGN_SORTIE_REGISTRY[3]
    assert sortie3.briefing_node_id == "sortie_3_briefing"
    assert sortie3.inflight_node_ids == ("sortie_3_500kg_crisis",)
    assert sortie3.debrief_node_id == "sortie_3_hangar_debrief"

    sortie4 = CAMPAIGN_SORTIE_REGISTRY[4]
    assert sortie4.briefing_node_id == "sortie_4_briefing"
    assert sortie4.inflight_node_ids == ("sortie_4_strider_crisis",)
    assert sortie4.debrief_node_id == "sortie_4_hangar_debrief"


# -----------------------------------------------------------------------------
# 3. Act II banter categories
# -----------------------------------------------------------------------------

ACT2_BANTER_CATEGORIES = (
    "act2_s3_approach_ghost",
    "act2_s3_extraction_pelican",
    "act2_s4_strider_arrival_ghost",
    "act2_s4_extraction_pelican",
    "act2_s4_check_flawless_braker",
    "act2_s4_check_flawless_memorial",
    "act2_s4_check_partial_braker",
    "act2_s4_check_partial_memorial",
    "act2_s4_check_wiped",
)


@pytest.mark.parametrize("category", ACT2_BANTER_CATEGORIES)
def test_act2_banter_categories_have_single_line(category):
    """Each Act II banter category holds exactly one deterministic line."""
    assert category in BANTER_QUEUES
    lines = BANTER_QUEUES[category]
    assert len(lines) == 1
    assert lines[0].category == category
    assert lines[0].line_id == f"{category}_01"


@pytest.mark.parametrize("category", ACT2_BANTER_CATEGORIES)
def test_act2_banter_is_deterministic(category):
    """Selection ignores the index for single-line categories."""
    assert get_contextual_banter(category, selection_index=0) is get_contextual_banter(category, selection_index=7)


def test_viper_dialogue_data_still_valid():
    """The Viper dialogue data, including Act II banter, still validates."""
    assert validate_viper_dialogue_data() is True


# -----------------------------------------------------------------------------
# 4. Scripted casualty hook
# -----------------------------------------------------------------------------

def test_apply_scripted_casualty_downs_living_unit():
    """A scripted casualty downs a living Helldiver and clears the flawless flag."""
    gsm = GroundSupportManager()
    assert gsm.apply_scripted_casualty(1) is True
    unit = next(u for u in gsm.units if u.index == 1)
    assert unit.state == "DOWNED"
    assert unit.health == 0.0
    assert not unit.is_alive
    assert 1 in gsm._downed_unit_ids
    assert gsm.flawless_protection is False


def test_apply_scripted_casualty_is_not_reported_twice(tmp_path):
    """The downed unit is pre-marked so update() does not notify the StoryManager again."""
    story = StoryManager(save_manager=CampaignSaveManager(data_dir=tmp_path))
    gsm = GroundSupportManager()
    gsm.set_story_manager(story)
    assert gsm.apply_scripted_casualty(1) is True
    assert story.total_casualties == 0
    assert 1 in gsm._downed_unit_ids


@pytest.mark.parametrize("bad_index", [1, 99, True, "1"])
def test_apply_scripted_casualty_rejects_dead_or_unknown(bad_index):
    """Unknown, non-int and already downed indices are rejected without mutation."""
    gsm = GroundSupportManager()
    gsm.apply_scripted_casualty(1)
    assert gsm.apply_scripted_casualty(bad_index) is False


# -----------------------------------------------------------------------------
# 5. Act II trigger table and registration
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
    """NarrativeTriggerManager with all Act II triggers registered."""
    mgr = NarrativeTriggerManager(story_mgr, comms_hud=comms, mission_controller=mission_ctrl)
    register_act2_triggers(mgr)
    return mgr


def _predicate(trigger_id):
    return next(t.predicate for t in ACT2_TRIGGERS if t.trigger_id == trigger_id)


def test_act2_triggers_are_valid():
    """Every Act II trigger passes the trigger validator."""
    for trigger in ACT2_TRIGGERS:
        validate_sortie_event_trigger(trigger)


def test_act2_trigger_ids_unique_and_scoped():
    """Trigger ids are unique and each id prefix matches its sortie."""
    ids = [t.trigger_id for t in ACT2_TRIGGERS]
    assert len(ids) == len(set(ids))
    for trigger in ACT2_TRIGGERS:
        expected = 3 if trigger.trigger_id.startswith("act2_s3_") else 4
        assert trigger.trigger_id.startswith(f"act2_s{expected}_")
        assert trigger.sortie_num == expected


def test_act2_priorities_follow_story_order():
    """Within each sortie, priorities strictly decrease in story order."""
    for sortie_num in (3, 4):
        priorities = [t.priority for t in ACT2_TRIGGERS if t.sortie_num == sortie_num]
        assert priorities == sorted(priorities, reverse=True)
        assert len(set(priorities)) == len(priorities)


def test_register_act2_triggers_returns_count(story_mgr):
    """Registration reports six triggers, three per sortie."""
    mgr = NarrativeTriggerManager(story_mgr)
    assert register_act2_triggers(mgr) == 6
    assert len(mgr.get_triggers_for_sortie(3)) == 3
    assert len(mgr.get_triggers_for_sortie(4)) == 3


def test_register_act2_triggers_twice_is_rejected_atomically(manager):
    """A second registration fails and leaves the trigger count unchanged."""
    with pytest.raises(ValueError, match="already registered"):
        register_act2_triggers(manager)
    assert len(manager.get_triggers_for_sortie(3)) == 3
    assert len(manager.get_triggers_for_sortie(4)) == 3


@pytest.mark.parametrize("bad_manager", [None, "mgr", object()])
def test_register_act2_triggers_rejects_invalid_manager(bad_manager):
    """Anything that is not a NarrativeTriggerManager is rejected with TypeError."""
    with pytest.raises(TypeError):
        register_act2_triggers(bad_manager)


def test_act1_and_act2_triggers_coexist(story_mgr):
    """Act I and Act II triggers register side by side without id clashes."""
    mgr = NarrativeTriggerManager(story_mgr)
    register_act1_triggers(mgr)
    register_act2_triggers(mgr)
    assert [len(mgr.get_triggers_for_sortie(n)) for n in (1, 2, 3, 4)] == [5, 3, 3, 3]


def test_extraction_waves_match_registry():
    """Extraction callouts fire on the registry's final wave for each sortie."""
    assert SORTIE3_EXTRACTION_WAVE == 4
    assert SORTIE4_EXTRACTION_WAVE == 5


def test_sortie3_crisis_predicate():
    """The 500kg crisis fires on a fabricator kill, an inbound strike, or wave 2."""
    predicate = _predicate("act2_s3_500kg_crisis")
    assert predicate(CombatTelemetrySnapshot(current_wave=1)) is False
    assert predicate(CombatTelemetrySnapshot(current_wave=1, fabricators_destroyed=1)) is True
    assert predicate(CombatTelemetrySnapshot(current_wave=1, active_500kg_inbound=True)) is True
    assert predicate(CombatTelemetrySnapshot(current_wave=2)) is True


def test_sortie4_predicates():
    """Strider arrival and crisis predicates follow boss activity and HP."""
    arrival = _predicate("act2_s4_strider_arrival")
    crisis = _predicate("act2_s4_strider_crisis")
    assert arrival(CombatTelemetrySnapshot(boss_active=False)) is False
    assert arrival(CombatTelemetrySnapshot(boss_active=True)) is True

    assert crisis(CombatTelemetrySnapshot(boss_active=True, boss_hp_ratio=0.5)) is False
    assert crisis(CombatTelemetrySnapshot(boss_active=True, boss_hp_ratio=0.49)) is True
    assert crisis(CombatTelemetrySnapshot(boss_active=True, boss_hp_ratio=0.9, any_helldiver_critical=True)) is True
    assert crisis(CombatTelemetrySnapshot(boss_active=False, boss_hp_ratio=0.1)) is False
