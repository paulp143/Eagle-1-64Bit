"""Unit and headless integration tests for Act I Sortie 1 & 2 narrative cues (Issue #69)."""

import pytest

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
