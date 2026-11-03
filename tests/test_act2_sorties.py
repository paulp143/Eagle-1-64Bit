"""Tests for the Act II campaign (#70): Sortie 3 and Sortie 4 dialogue, triggers, 500kg crisis and casualty check."""

import pytest

from eagle1.story.mission_controller import CAMPAIGN_SORTIE_REGISTRY, validate_sortie_registry
from eagle1.systems.ground_support import GroundSupportManager
from eagle1.story.campaign_save import CampaignSaveManager
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
