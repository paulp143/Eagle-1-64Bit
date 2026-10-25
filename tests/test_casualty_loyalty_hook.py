"""test_casualty_loyalty_hook.py - Verifies Helldiver casualties trigger StoryManager loyalty erosion."""

import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import pygame

pygame.init()

from eagle1.story.campaign_save import CampaignSaveManager
from eagle1.story.story_manager import StoryManager
from eagle1.systems.ground_support import GroundSupportManager, HelldiverUnit


class TestCasualtyLoyaltyHook(unittest.TestCase):
    """Test suite connecting ground support casualties to StoryManager."""

    def setUp(self):
        self.mock_audio = MagicMock()
        self.tmpdir = tempfile.TemporaryDirectory()
        self.save_manager = CampaignSaveManager(data_dir=Path(self.tmpdir.name))
        self.story_manager = StoryManager(audio_manager=self.mock_audio, save_manager=self.save_manager)
        self.ground_support = GroundSupportManager()
        self.ground_support.set_story_manager(self.story_manager)

    def tearDown(self):
        self.tmpdir.cleanup()

        # Initialize mock squad of 4 Helldivers
        self.ground_support.units = [
            HelldiverUnit(0, 1000, 1000),
            HelldiverUnit(1, 1030, 1000),
            HelldiverUnit(2, 1060, 1000),
            HelldiverUnit(3, 1090, 1000),
        ]
        self.ground_support.survivors_count = 4

    def test_single_casualty_erodes_loyalty(self):
        """Downing one Helldiver should reduce loyalty by -3.5."""
        initial_loyalty = self.story_manager.loyalty
        initial_casualties = self.story_manager.total_casualties

        # Down the first Helldiver
        self.ground_support.units[0].take_damage(999.0)
        self.assertEqual(self.ground_support.units[0].state, "DOWNED")

        # Mock player and empty targets to run update
        mock_player = MagicMock()
        mock_player.pos_x = 1000
        mock_player.pos_y = 1000
        mock_player.x = 1000
        mock_player.y = 1000
        mock_player.score = 500

        self.ground_support.update(0.016, mock_player, [], pygame.sprite.Group(), [])

        self.assertEqual(self.story_manager.total_casualties, initial_casualties + 1)
        self.assertAlmostEqual(self.story_manager.loyalty, initial_loyalty - 3.5, places=2)

    def test_squad_wipe_triggers_additional_wipe_penalty(self):
        """Downing all 4 Helldivers should erode 4 * 3.5 + 8.0 = 22.0 loyalty."""
        initial_loyalty = self.story_manager.loyalty

        for u in self.ground_support.units:
            u.take_damage(999.0)

        mock_player = MagicMock()
        mock_player.pos_x = 1000
        mock_player.pos_y = 1000
        mock_player.x = 1000
        mock_player.y = 1000
        mock_player.score = 500

        self.ground_support.update(0.016, mock_player, [], pygame.sprite.Group(), [])

        # 4 casualties (-14.0) + squad wipe (-8.0) = -22.0
        expected_loyalty = max(0.0, initial_loyalty - 22.0)
        self.assertAlmostEqual(self.story_manager.loyalty, expected_loyalty, places=2)


if __name__ == "__main__":
    unittest.main()
