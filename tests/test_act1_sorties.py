"""Unit and headless integration tests for Act I Sortie 1 & 2 narrative cues (Issue #69)."""

import pytest

from eagle1.story.mission_controller import CAMPAIGN_SORTIE_REGISTRY, validate_sortie_registry
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
