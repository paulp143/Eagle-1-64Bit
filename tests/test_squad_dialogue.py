"""test_squad_dialogue.py - Unit tests for Viper Squad character profiles, banter, and dialogue trees."""

import os
import unittest

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import pygame
pygame.init()

from eagle1.story.dialogue_db import get_dialogue_node, validate_dialogue_database
from eagle1.story.dialogue_data import (
    VIPER_SQUAD_PROFILES,
    BANTER_QUEUES,
    VIPER_DIALOGUE_TREES,
    ViperCharacterProfile,
    BanterLine,
    get_viper_profile,
    get_contextual_banter,
    get_debrief_dialogue_node,
    validate_viper_dialogue_data,
)


class TestViperSquadDialogue(unittest.TestCase):
    """Test suite covering Viper Squad narrative profiles, banter, and dialogue trees."""

    def test_viper_squad_profiles_complete(self):
        """Verify all 4 Viper Squad members have complete profile specifications."""
        expected_members = ["viper_1", "viper_2", "viper_3", "viper_4"]
        self.assertEqual(sorted(VIPER_SQUAD_PROFILES.keys()), expected_members)

        # Viper 1: Apex
        apex = VIPER_SQUAD_PROFILES["viper_1"]
        self.assertIsInstance(apex, ViperCharacterProfile)
        self.assertEqual(apex.nickname, "Apex")
        self.assertEqual(apex.unit_index, 0)
        self.assertEqual(apex.role, "Squad Leader")
        self.assertEqual(apex.preferred_stance, "loyal")
        self.assertEqual(apex.theme_color, (255, 215, 0))
        self.assertTrue(apex.portrait_path.endswith("viper_1_apex.png"))
        self.assertTrue(len(apex.bio) > 0)

        # Viper 2: Braker
        braker = VIPER_SQUAD_PROFILES["viper_2"]
        self.assertEqual(braker.nickname, "Braker")
        self.assertEqual(braker.unit_index, 1)
        self.assertEqual(braker.role, "Heavy Munitions")
        self.assertEqual(braker.preferred_stance, "dissident")
        self.assertEqual(braker.theme_color, (52, 152, 219))
        self.assertTrue(braker.portrait_path.endswith("viper_2_braker.png"))

        # Viper 3: Ghost
        ghost = VIPER_SQUAD_PROFILES["viper_3"]
        self.assertEqual(ghost.nickname, "Ghost")
        self.assertEqual(ghost.unit_index, 2)
        self.assertEqual(ghost.role, "Recon & Sniper")
        self.assertEqual(ghost.preferred_stance, "neutral")
        self.assertEqual(ghost.theme_color, (46, 204, 113))
        self.assertTrue(ghost.portrait_path.endswith("viper_3_ghost.png"))

        # Viper 4: Doc
        doc = VIPER_SQUAD_PROFILES["viper_4"]
        self.assertEqual(doc.nickname, "Doc")
        self.assertEqual(doc.unit_index, 3)
        self.assertEqual(doc.role, "Combat Medic")
        self.assertEqual(doc.preferred_stance, "dissident")
        self.assertEqual(doc.theme_color, (231, 76, 60))
        self.assertTrue(doc.portrait_path.endswith("viper_4_doc.png"))

    def test_get_viper_profile_by_id_index_and_nickname(self):
        """Verify profile resolution across string IDs, integer indices, and nicknames."""
        # By key
        self.assertEqual(get_viper_profile("viper_1"), VIPER_SQUAD_PROFILES["viper_1"])
        # By index
        self.assertEqual(get_viper_profile(0), VIPER_SQUAD_PROFILES["viper_1"])
        self.assertEqual(get_viper_profile(1), VIPER_SQUAD_PROFILES["viper_2"])
        self.assertEqual(get_viper_profile(2), VIPER_SQUAD_PROFILES["viper_3"])
        self.assertEqual(get_viper_profile(3), VIPER_SQUAD_PROFILES["viper_4"])

        # By nickname (case insensitive)
        self.assertEqual(get_viper_profile("Apex"), VIPER_SQUAD_PROFILES["viper_1"])
        self.assertEqual(get_viper_profile("braker"), VIPER_SQUAD_PROFILES["viper_2"])
        self.assertEqual(get_viper_profile("GHOST"), VIPER_SQUAD_PROFILES["viper_3"])
        self.assertEqual(get_viper_profile("doc"), VIPER_SQUAD_PROFILES["viper_4"])

        # Edge cases & invalid inputs
        self.assertIsNone(get_viper_profile(99))
        self.assertIsNone(get_viper_profile(-1))
        self.assertIsNone(get_viper_profile("unknown"))
        self.assertIsNone(get_viper_profile(None))

    def test_all_viper_dialogue_trees_valid_tripartite(self):
        """Verify all interactive dialogue trees for Viper Squad conform to tripartite schema."""
        self.assertTrue(validate_viper_dialogue_data())
        self.assertTrue(validate_dialogue_database(VIPER_DIALOGUE_TREES))

        # Check required story nodes exist
        required_nodes = [
            "viper_1_deck_briefing",
            "viper_2_deck_briefing",
            "viper_3_deck_briefing",
            "viper_4_deck_briefing",
            "viper_inflight_cas_crisis",
            "viper_debrief_flawless",
            "viper_debrief_casualties",
            "viper_debrief_replacements",
        ]
        for node_id in required_nodes:
            self.assertIn(node_id, VIPER_DIALOGUE_TREES)
            node = VIPER_DIALOGUE_TREES[node_id]
            self.assertEqual(set(node.options.keys()), {"loyal", "neutral", "dissident"})
            self.assertGreater(node.options["loyal"].loyalty_delta, 0.0)
            self.assertLess(node.options["dissident"].loyalty_delta, 0.0)
            self.assertTrue(len(node.prompt.strip()) > 0)

    def test_contextual_banter_retrieval_and_fallbacks(self):
        """Verify retrieval across all banter categories with member filtering and fallbacks."""
        required_categories = [
            "pre_mission_briefing",
            "cas_beacon_request",
            "low_ammo",
            "low_health",
            "near_miss_bomb",
            "stratagem_drop",
            "kill_streak",
            "casualty",
            "supply_pod",
        ]
        for cat in required_categories:
            self.assertIn(cat, BANTER_QUEUES)
            self.assertGreater(len(BANTER_QUEUES[cat]), 0)
            line = get_contextual_banter(cat)
            self.assertIsNotNone(line)
            self.assertIsInstance(line, BanterLine)
            self.assertTrue(len(line.text.strip()) > 0)
            self.assertTrue(len(line.speaker.strip()) > 0)

        # Filter by member_id
        doc_line = get_contextual_banter("low_health", member_id="viper_4")
        self.assertIsNotNone(doc_line)
        self.assertEqual(doc_line.member_id, "viper_4")

        # Unknown category safe fallback
        self.assertIsNone(get_contextual_banter("non_existent_category"))
        self.assertIsNone(get_contextual_banter(""))

    def test_dynamic_debrief_adapts_to_casualties(self):
        """Verify get_debrief_dialogue_node adapts dynamically to casualty counts and squad wipes."""
        # 0 casualties: flawless
        node_flawless = get_debrief_dialogue_node(casualties_count=0, squad_wiped=False)
        self.assertEqual(node_flawless.node_id, "viper_debrief_flawless")

        # Negative casualty count safety check
        node_neg = get_debrief_dialogue_node(casualties_count=-2, squad_wiped=False)
        self.assertEqual(node_neg.node_id, "viper_debrief_flawless")

        # 1-3 casualties: wounded/somber debrief
        for count in [1, 2, 3]:
            node_cas = get_debrief_dialogue_node(casualties_count=count, squad_wiped=False)
            self.assertEqual(node_cas.node_id, "viper_debrief_casualties")

        # 4+ casualties: replacement recruits
        node_replacements = get_debrief_dialogue_node(casualties_count=4, squad_wiped=False)
        self.assertEqual(node_replacements.node_id, "viper_debrief_replacements")

        # Squad wipe even with fewer reported counts
        node_wiped = get_debrief_dialogue_node(casualties_count=2, squad_wiped=True)
        self.assertEqual(node_wiped.node_id, "viper_debrief_replacements")

    def test_dialogue_database_contains_viper_nodes(self):
        """Verify get_dialogue_node resolves Viper Squad dialogue nodes seamlessly."""
        self.assertIsNotNone(get_dialogue_node("viper_1_deck_briefing"))
        self.assertIsNotNone(get_dialogue_node("viper_debrief_flawless"))


if __name__ == "__main__":
    unittest.main()
