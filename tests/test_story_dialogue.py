"""Tests for Dialogue Data Structures and Act I Narrative Script Matrix."""

import pygame
import pytest

from eagle1.story.dialogue_db import (
    DIALOGUE_DATABASE,
    DialogueNode,
    DialogueOption,
    get_dialogue_node,
    get_nodes_for_act_and_sortie,
    validate_dialogue_database,
)


def test_dialogue_option_dataclass():
    """Verify DialogueOption fields and immutability."""
    opt = DialogueOption(
        stance="loyal",
        key_name="1",
        key_code=pygame.K_1,
        label="[1. LOYAL] Test option",
        loyalty_delta=8.0,
        response="Good soldier.",
    )
    assert opt.stance == "loyal"
    assert opt.loyalty_delta == 8.0
    assert opt.key_name == "1"
    assert opt.key_code == pygame.K_1
    assert opt.response == "Good soldier."


def test_dialogue_node_dataclass():
    """Verify DialogueNode encapsulation and 3-way option structure."""
    opt_loyal = DialogueOption("loyal", "1", pygame.K_1, "Loyal label", 8.0, "Affirmative")
    opt_neutral = DialogueOption("neutral", "2", pygame.K_2, "Neutral label", 0.0, "Acknowledged")
    opt_dissident = DialogueOption("dissident", "3", pygame.K_3, "Dissident label", -8.0, "Stand down")

    node = DialogueNode(
        node_id="test_node",
        speaker="Test Speaker",
        location="Bridge",
        prompt="Test Prompt?",
        options={
            "loyal": opt_loyal,
            "neutral": opt_neutral,
            "dissident": opt_dissident,
        },
        act=1,
        sortie=1,
    )

    assert node.node_id == "test_node"
    assert len(node.options) == 3
    assert node.options["loyal"].loyalty_delta == 8.0
    assert node.options["neutral"].loyalty_delta == 0.0
    assert node.options["dissident"].loyalty_delta == -8.0


def test_database_validation_passes():
    """Verify built-in DIALOGUE_DATABASE satisfies all narrative schema rules."""
    assert validate_dialogue_database(DIALOGUE_DATABASE) is True


def test_act_1_required_nodes_exist():
    """Verify Act I core scenes are populated with tripartite stances."""
    required_nodes = [
        "sortie_1_briefing",
        "sortie_1_inflight",
        "sortie_1_hangar_debrief",
    ]
    for node_id in required_nodes:
        node = get_dialogue_node(node_id)
        assert node is not None, f"Node {node_id} must exist in DIALOGUE_DATABASE"
        assert set(node.options.keys()) == {"loyal", "neutral", "dissident"}
        assert node.options["loyal"].loyalty_delta > 0.0
        assert node.options["dissident"].loyalty_delta < 0.0
        assert len(node.prompt.strip()) > 0
        assert len(node.options["loyal"].response.strip()) > 0


def test_get_nodes_for_act_and_sortie():
    """Verify node retrieval filtered by act and sortie."""
    sortie_1_nodes = get_nodes_for_act_and_sortie(act=1, sortie=1)
    node_ids = [n.node_id for n in sortie_1_nodes]
    assert "sortie_1_briefing" in node_ids
    assert "sortie_1_inflight" in node_ids
    assert "sortie_1_hangar_debrief" in node_ids


def test_validation_detects_invalid_database():
    """Verify validation catches malformed nodes (missing options or invalid deltas)."""
    # Missing dissident option
    bad_db = {
        "bad_node": DialogueNode(
            node_id="bad_node",
            speaker="Officer",
            location="Bridge",
            prompt="Prompt",
            options={
                "loyal": DialogueOption("loyal", "1", pygame.K_1, "L", 8.0, "Resp"),
                "neutral": DialogueOption("neutral", "2", pygame.K_2, "N", 0.0, "Resp"),
            },
        )
    }
    with pytest.raises(ValueError, match="must contain 'loyal', 'neutral', and 'dissident'"):
        validate_dialogue_database(bad_db)

    # Inverted loyal delta (should be > 0)
    bad_db_delta = {
        "bad_delta": DialogueNode(
            node_id="bad_delta",
            speaker="Officer",
            location="Bridge",
            prompt="Prompt",
            options={
                "loyal": DialogueOption("loyal", "1", pygame.K_1, "L", -5.0, "Resp"),
                "neutral": DialogueOption("neutral", "2", pygame.K_2, "N", 0.0, "Resp"),
                "dissident": DialogueOption("dissident", "3", pygame.K_3, "D", -5.0, "Resp"),
            },
        )
    }
    with pytest.raises(ValueError, match="Loyal option must have positive delta"):
        validate_dialogue_database(bad_db_delta)

