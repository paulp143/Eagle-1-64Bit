"""Tests for Dialogue Data Structures and Act I Narrative Script Matrix."""

import pygame
import pytest

from eagle1.story.dialogue_db import (
    DIALOGUE_DATABASE,
    SHIP_NPC_PROFILES,
    DialogueNode,
    DialogueOption,
    ShipNPCProfile,
    get_dialogue_node,
    get_nodes_for_act_and_sortie,
    get_ship_npc_profile,
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


def test_ship_npc_profiles_and_lookup():
    """Verify ShipNPCProfile definition, SHIP_NPC_PROFILES registry, and lookup safety."""
    required_ids = {"npc_reiner", "npc_vance", "npc_ortiz", "viper_1", "viper_2", "viper_3", "viper_4"}
    assert required_ids.issubset(set(SHIP_NPC_PROFILES.keys()))

    # Check Reiner
    reiner = SHIP_NPC_PROFILES["npc_reiner"]
    assert isinstance(reiner, ShipNPCProfile)
    assert reiner.npc_id == "npc_reiner"
    assert reiner.zone == "bridge"
    assert reiner.name == "Democracy Officer Karl Reiner"
    assert reiner.callsign == reiner.name
    assert reiner.default_node_id == "sortie_1_briefing"
    assert reiner.portrait_path == "images/portraits/npc_reiner.png"

    # Check Vance
    vance = SHIP_NPC_PROFILES["npc_vance"]
    assert isinstance(vance, ShipNPCProfile)
    assert vance.zone == "bridge"
    assert vance.default_node_id == "bridge_vance_logistics"
    assert vance.portrait_path == "images/portraits/npc_vance.png"

    # Check Ortiz
    ortiz = SHIP_NPC_PROFILES["npc_ortiz"]
    assert isinstance(ortiz, ShipNPCProfile)
    assert ortiz.zone == "hangar"
    assert ortiz.default_node_id == "hangar_ortiz_maintenance"
    assert ortiz.portrait_path == "images/portraits/npc_ortiz.png"

    # Check Ready Room Viper Squad profiles
    for i in range(1, 5):
        vid = f"viper_{i}"
        vprof = SHIP_NPC_PROFILES[vid]
        assert vprof.zone == "ready_room"
        assert vprof.default_node_id == f"viper_{i}_deck_briefing"

    # Test get_ship_npc_profile lookup and aliases
    assert get_ship_npc_profile("npc_reiner") == reiner
    assert get_ship_npc_profile("reiner") == reiner
    assert get_ship_npc_profile("  VANCE  ") == vance
    assert get_ship_npc_profile("ortiz") == ortiz
    assert get_ship_npc_profile("apex") == SHIP_NPC_PROFILES["viper_1"]
    assert get_ship_npc_profile("braker") == SHIP_NPC_PROFILES["viper_2"]
    assert get_ship_npc_profile("ghost") == SHIP_NPC_PROFILES["viper_3"]
    assert get_ship_npc_profile("doc") == SHIP_NPC_PROFILES["viper_4"]
    assert get_ship_npc_profile("npc_viper_1") == SHIP_NPC_PROFILES["viper_1"]

    # Rejection of invalid inputs
    assert get_ship_npc_profile("unknown_npc") is None
    assert get_ship_npc_profile("") is None
    assert get_ship_npc_profile(None) is None  # type: ignore[arg-type]
    assert get_ship_npc_profile(True) is None  # type: ignore[arg-type]
    assert get_ship_npc_profile(123) is None  # type: ignore[arg-type]


def test_ship_hub_dialogue_nodes_exist_and_validate():
    """Verify new tripartite hub dialogue nodes exist and conform to schema."""
    hub_nodes = [
        "bridge_vance_logistics",
        "bridge_reiner_scrutiny",
        "hangar_ortiz_maintenance",
    ]
    for node_id in hub_nodes:
        assert node_id in DIALOGUE_DATABASE
        node = get_dialogue_node(node_id)
        assert node is not None
        assert set(node.options.keys()) == {"loyal", "neutral", "dissident"}
        assert 8.0 <= node.options["loyal"].loyalty_delta <= 12.0
        assert -1.0 <= node.options["neutral"].loyalty_delta <= 1.0
        assert -12.0 <= node.options["dissident"].loyalty_delta <= -8.0
        assert len(node.prompt.strip()) > 0
        assert node.portrait is not None

    # Full database validation passes with new nodes included
    assert validate_dialogue_database(DIALOGUE_DATABASE) is True


@pytest.mark.parametrize("bad_opt,err_match", [
    (DialogueOption("neutral", "2", pygame.K_2, "N", 2.5, "Resp"), "Neutral option delta must be within"),
    (DialogueOption("neutral", "2", pygame.K_2, "N", -1.5, "Resp"), "Neutral option delta must be within"),
    (DialogueOption("dissident", "3", pygame.K_3, "D", 0.0, "Resp"), "Dissident option must have negative delta"),
    (DialogueOption("dissident", "3", pygame.K_3, "D", 2.0, "Resp"), "Dissident option must have negative delta"),
    (DialogueOption("loyal", "1", pygame.K_1, "L", 0.0, "Resp"), "Loyal option must have positive delta"),
])
def test_validation_detects_delta_boundary_violations(bad_opt, err_match):
    """Verify validation strictly enforces delta bounds for each ideological stance."""
    opts = {
        "loyal": DialogueOption("loyal", "1", pygame.K_1, "L", 8.0, "Resp"),
        "neutral": DialogueOption("neutral", "2", pygame.K_2, "N", 0.0, "Resp"),
        "dissident": DialogueOption("dissident", "3", pygame.K_3, "D", -8.0, "Resp"),
    }
    opts[bad_opt.stance] = bad_opt
    bad_db = {"node": DialogueNode("node", "Spkr", "Loc", "Prompt", opts)}
    with pytest.raises(ValueError, match=err_match):
        validate_dialogue_database(bad_db)


@pytest.mark.parametrize("bad_node,err_match", [
    (DialogueNode("", "Spkr", "Loc", "Prompt", {
        "loyal": DialogueOption("loyal", "1", pygame.K_1, "L", 8.0, "Resp"),
        "neutral": DialogueOption("neutral", "2", pygame.K_2, "N", 0.0, "Resp"),
        "dissident": DialogueOption("dissident", "3", pygame.K_3, "D", -8.0, "Resp"),
    }), "has empty id or prompt"),
    (DialogueNode("node", "Spkr", "Loc", "   ", {
        "loyal": DialogueOption("loyal", "1", pygame.K_1, "L", 8.0, "Resp"),
        "neutral": DialogueOption("neutral", "2", pygame.K_2, "N", 0.0, "Resp"),
        "dissident": DialogueOption("dissident", "3", pygame.K_3, "D", -8.0, "Resp"),
    }), "has empty id or prompt"),
    (DialogueNode("node", "Spkr", "Loc", "Prompt", {
        "loyal": DialogueOption("loyal", "1", pygame.K_1, "   ", 8.0, "Resp"),
        "neutral": DialogueOption("neutral", "2", pygame.K_2, "N", 0.0, "Resp"),
        "dissident": DialogueOption("dissident", "3", pygame.K_3, "D", -8.0, "Resp"),
    }), "has empty label or response"),
    (DialogueNode("node", "Spkr", "Loc", "Prompt", {
        "loyal": DialogueOption("loyal", "1", pygame.K_1, "L", 8.0, "Resp"),
        "neutral": DialogueOption("neutral", "2", pygame.K_2, "N", 0.0, "  "),
        "dissident": DialogueOption("dissident", "3", pygame.K_3, "D", -8.0, "Resp"),
    }), "has empty label or response"),
])
def test_validation_detects_empty_id_prompt_label_response(bad_node, err_match):
    """Verify validation rejects empty strings in node IDs, prompts, labels, and responses."""
    bad_db = {"node": bad_node}
    with pytest.raises(ValueError, match=err_match):
        validate_dialogue_database(bad_db)


def test_comms_hud_portrait_rejects_path_traversal_and_missing_files():
    """Verify CommsHUD portrait resolver safely rejects traversal paths and nonexistent files."""
    from eagle1.story.comms_hud import CommsHUD

    hud = CommsHUD()
    # Path traversal attempts
    assert hud._get_portrait_surface("../../../etc/passwd") is None
    assert hud._get_portrait_surface("/etc/hosts") is None
    assert hud._get_portrait_surface("/System/Library/CoreServices/SystemAppearance.bundle") is None

    # Invalid string inputs
    assert hud._get_portrait_surface("") is None
    assert hud._get_portrait_surface("   ") is None
    assert hud._get_portrait_surface(None) is None  # type: ignore[arg-type]
    assert hud._get_portrait_surface(True) is None  # type: ignore[arg-type]

    # Non-existent relative file
    assert hud._get_portrait_surface("images/portraits/definitely_nonexistent_portrait.png") is None



