"""test_squad_dialogue.py - Unit tests for Viper Squad character profiles, banter, and dialogue trees."""

import os
import unittest
from unittest.mock import MagicMock, patch

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import pygame
pygame.init()

from eagle1.story.comms_hud import CommsHUD
from eagle1.story.story_manager import StoryManager
from eagle1.systems.ground_support import AirStrikeType, GroundSupportManager, HelldiverUnit
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

    def test_ground_support_low_health_triggers_banter(self):
        """When a Helldiver drops below 35% health, a low_health banter callout should emit."""
        mock_audio = MagicMock()
        hud = CommsHUD(audio_manager=mock_audio)
        gsm = GroundSupportManager()
        gsm.set_comms_hud(hud)

        # 4 healthy units
        gsm.units = [
            HelldiverUnit(0, 1000, 1000),
            HelldiverUnit(1, 1030, 1000),
            HelldiverUnit(2, 1060, 1000),
            HelldiverUnit(3, 1090, 1000),
        ]

        # Wound unit 3 (Doc) down to 20% health (< 35%)
        gsm.units[3].health = 0.20 * gsm.units[3].max_health

        mock_player = MagicMock()
        mock_player.pos_x = 1000
        mock_player.pos_y = 1000
        mock_player.x = 1000
        mock_player.y = 1000
        mock_player.score = 0

        gsm.update(0.016, mock_player, [], pygame.sprite.Group(), [])
        self.assertTrue(hud.is_active)
        self.assertEqual(hud.current_node.node_id, "banter_callout")

    def test_ground_support_near_miss_bomb_triggers_banter(self):
        """Explosive air strike targeted near living Helldivers should trigger near_miss_bomb banter."""
        mock_audio = MagicMock()
        hud = CommsHUD(audio_manager=mock_audio)
        gsm = GroundSupportManager()
        gsm.set_comms_hud(hud)

        # Place Helldiver at (1500, 1500) (Unit 1 is Braker)
        gsm.units = [HelldiverUnit(1, 1500, 1500)]

        mock_player = MagicMock()
        mock_player.pos_x = 1500
        mock_player.pos_y = 1500
        mock_player.x = 1500
        mock_player.y = 1500
        mock_player.angle = 0
        mock_player.velocity_x = 0
        mock_player.velocity_y = 0

        # Equip 500kg bomb
        gsm.weapon_menu.select(AirStrikeType.BOMB_500KG)
        # Mock reticle impact at 1550, 1500 (within 180px distance)
        gsm.reticle.calculate_strike_impact = MagicMock(return_value=(1550, 1500))

        success = gsm.trigger_air_strike(mock_player)
        self.assertTrue(success)
        self.assertTrue(hud.is_active)
        self.assertIn("Braker", hud.current_node.speaker)

    def test_ground_support_kill_streak_and_cas_callout(self):
        """CAS kill streak of 5 should trigger kill_streak banter from Viper Squad."""
        mock_audio = MagicMock()
        hud = CommsHUD(audio_manager=mock_audio)
        gsm = GroundSupportManager()
        gsm.set_comms_hud(hud)
        gsm.units = [HelldiverUnit(0, 1000, 1000)]

        mock_player = MagicMock()
        mock_player.score = 0

        mock_enemy = MagicMock()
        mock_enemy.x = 1020
        mock_enemy.y = 1020

        # Simulate 5 consecutive kills near ally
        for _ in range(5):
            gsm.on_player_kill_enemy(mock_enemy, mock_player)

        self.assertTrue(hud.is_active)
        self.assertIn("Apex", hud.current_node.speaker)

    def test_ground_support_post_sortie_debrief_selection(self):
        """get_post_sortie_debrief_node should return appropriate debrief node based on casualties."""
        gsm = GroundSupportManager()
        gsm.units = [HelldiverUnit(i, 1000 + i * 30, 1000) for i in range(4)]

        # No casualties
        node_0 = gsm.get_post_sortie_debrief_node()
        self.assertEqual(node_0.node_id, "viper_debrief_flawless")

        # 2 casualties
        gsm._downed_unit_ids = {0, 1}
        node_2 = gsm.get_post_sortie_debrief_node()
        self.assertEqual(node_2.node_id, "viper_debrief_casualties")

        # Squad wipe
        gsm._squad_wipe_reported = True
        node_wipe = gsm.get_post_sortie_debrief_node()
        self.assertEqual(node_wipe.node_id, "viper_debrief_replacements")

    def test_ground_support_reset_preserves_story_and_comms_managers(self):
        """gsm.reset() must not wipe story_manager or comms_hud instances."""
        mock_audio = MagicMock()
        story_mgr = StoryManager(audio_manager=mock_audio)
        hud = CommsHUD(story_manager=story_mgr, audio_manager=mock_audio)
        gsm = GroundSupportManager()

        gsm.set_story_manager(story_mgr)
        gsm.set_comms_hud(hud)

        # Trigger reset
        gsm.reset()

        self.assertIs(gsm.story_manager, story_mgr)
        self.assertIs(gsm.comms_hud, hud)

    def test_low_health_banter_uses_damaged_unit_profile(self):
        """When unit 1 (Braker) drops below 35% HP, Braker should transmit the distress call."""
        mock_audio = MagicMock()
        hud = CommsHUD(audio_manager=mock_audio)
        gsm = GroundSupportManager()
        gsm.set_comms_hud(hud)
        # Unit 1 is Braker
        gsm.units = [HelldiverUnit(i, 1000 + i * 30, 1000) for i in range(4)]
        braker = gsm.units[1]
        braker.health = 40.0  # < 35% of 150 (52.5)

        mock_player = MagicMock()
        mock_player.pos_x = 1000
        mock_player.pos_y = 1000
        mock_player.score = 0

        gsm.update(0.016, mock_player, [], None, None)

        self.assertTrue(hud.is_active)
        self.assertIn("Braker", hud.current_node.speaker)

    def test_no_ghost_banter_when_units_empty_in_aerial_missions(self):
        """In pure aerial missions where units is empty, no ground squad chatter should trigger."""
        mock_audio = MagicMock()
        hud = CommsHUD(audio_manager=mock_audio)
        gsm = GroundSupportManager()
        gsm.set_comms_hud(hud)
        gsm.units = []

        self.assertFalse(gsm.emit_squad_banter("pre_mission_briefing"))
        self.assertFalse(gsm.emit_squad_banter("kill_streak"))
        self.assertFalse(gsm.emit_squad_banter("cas_beacon_request"))
        self.assertFalse(hud.is_active)

    def test_get_viper_profile_rejects_booleans(self):
        """get_viper_profile must explicitly reject boolean inputs."""
        self.assertIsNone(get_viper_profile(True))
        self.assertIsNone(get_viper_profile(False))

    def test_dead_member_banter_aborted_when_no_living_alternative_exists(self):
        """When target member is dead and living members lack lines in category, comms must abort."""
        mock_audio = MagicMock()
        hud = CommsHUD(audio_manager=mock_audio)
        gsm = GroundSupportManager()
        gsm.set_comms_hud(hud)
        # Only Ghost (index 2) is alive
        gsm.units = [HelldiverUnit(i, 1000 + i * 30, 1000) for i in range(4)]
        gsm.units[0].state = "DOWNED"
        gsm.units[0].health = 0
        gsm.units[1].state = "DOWNED"
        gsm.units[1].health = 0
        gsm.units[3].state = "DOWNED"
        gsm.units[3].health = 0

        dead_line = BanterLine(
            line_id="test_dead",
            member_id="viper_1",
            speaker='Viper-1 "Apex"',
            category="custom_test",
            text="Test dead line",
            portrait_path="images/portraits/viper_1_apex.png",
        )
        with patch("eagle1.systems.ground_support.get_contextual_banter") as mock_banter:
            # First call returns dead_line, fallback query for living member (viper_3) returns None
            mock_banter.side_effect = [dead_line, None]

            result = gsm.emit_squad_banter("custom_test", member_id="viper_1", force=True)
            self.assertFalse(result)
            self.assertFalse(hud.is_active)

    def test_low_health_warning_resets_on_unit_healing_hysteresis(self):
        """Helldiver recovering above 60% HP must clear warned status, allowing subsequent warnings."""
        mock_audio = MagicMock()
        hud = CommsHUD(audio_manager=mock_audio)
        gsm = GroundSupportManager()
        gsm.set_comms_hud(hud)
        gsm.units = [HelldiverUnit(i, 1000 + i * 30, 1000) for i in range(4)]
        braker = gsm.units[1]

        mock_player = MagicMock()
        mock_player.pos_x = 1000
        mock_player.pos_y = 1000
        mock_player.score = 0

        # 1. Damage Braker below 35% HP (40 / 150 = 26.6%)
        braker.health = 40.0
        gsm.update(0.016, mock_player, [], None, None)
        self.assertIn(1, gsm._low_health_warned_units)
        self.assertTrue(hud.is_active)

        # 2. Dismiss and heal above 60% HP (100 / 150 = 66.6%)
        hud.dismiss()
        gsm._banter_cooldown = 0.0
        braker.health = 100.0
        gsm.update(0.016, mock_player, [], None, None)
        self.assertNotIn(1, gsm._low_health_warned_units)

        # 3. Damage Braker again below 35% HP
        braker.health = 30.0
        gsm.update(0.016, mock_player, [], None, None)
        self.assertIn(1, gsm._low_health_warned_units)
        self.assertTrue(hud.is_active)
        self.assertIn("Braker", hud.current_node.speaker)


if __name__ == "__main__":
    unittest.main()
