"""test_comms_hud.py - Unit and Integration Tests for In-Flight Radio Comms HUD.

Verifies:
1. CommsHUD initialization and state variables.
2. Triggering transmissions and queueing nodes from dialogue_db.
3. Time dilation transitions (1.0 -> 0.4 when choice pending).
4. Keyboard input handling ([1], [2], [3] for loyal, neutral, dissident).
5. Audio squelch triggers and story_manager loyalty modification callbacks.
6. Headless rendering safety without surface allocation leaks.
"""

import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock

# Configure dummy video/audio drivers for headless test runner
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import pygame

pygame.init()
pygame.display.set_mode((1280, 720))

from eagle1.story.campaign_save import CampaignSaveManager
from eagle1.story.comms_hud import CommsHUD
from eagle1.story.story_manager import StoryManager


class TestCommsHUD(unittest.TestCase):
    """Test suite for in-flight radio transceiver HUD."""

    def setUp(self):
        self.mock_audio = MagicMock()
        self.tmpdir = tempfile.TemporaryDirectory()
        self.save_manager = CampaignSaveManager(data_dir=Path(self.tmpdir.name))
        self.story_manager = StoryManager(audio_manager=self.mock_audio, save_manager=self.save_manager)
        self.hud = CommsHUD(story_manager=self.story_manager, audio_manager=self.mock_audio)

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_initial_state(self):
        """HUD should initialize inactive with nominal 1.0 time dilation."""
        self.assertFalse(self.hud.is_active)
        self.assertFalse(self.hud.is_waiting_for_choice)
        self.assertIsNone(self.hud.current_node)
        self.assertEqual(self.hud.get_time_dilation(), 1.0)

    def test_trigger_transmission_starts_active_and_plays_squelch(self):
        """Triggering a transmission should activate the HUD and play radio start SFX."""
        result = self.hud.trigger_transmission("sortie_1_briefing")
        self.assertTrue(result)
        self.assertTrue(self.hud.is_active)
        self.assertIsNotNone(self.hud.current_node)
        self.assertEqual(self.hud.current_node.node_id, "sortie_1_briefing")
        # Audio squelch should be called
        self.mock_audio.play_radio_squelch.assert_called_once()

    def test_typewriter_progresses_and_enables_choice(self):
        """Updating HUD should advance text typewriter until choice becomes pending."""
        self.hud.trigger_transmission("sortie_1_briefing")
        # Initially typewriter starts at 0
        self.assertGreaterEqual(self.hud.typewriter_chars, 0)

        # Fast forward time to finish typewriter (255 chars / 55 cps ~= 4.6s)
        for _ in range(60):
            self.hud.update(dt=0.1)

        self.assertTrue(self.hud.is_waiting_for_choice)
        self.assertAlmostEqual(self.hud.get_time_dilation(), 0.4, places=1)

    def test_handle_event_selects_loyal_option(self):
        """Pressing 1 should select loyal choice, modify loyalty, and start response."""
        self.hud.trigger_transmission("sortie_1_briefing")
        # Complete typewriter immediately for test
        self.hud.typewriter_chars = len(self.hud.current_node.prompt)
        self.hud.is_waiting_for_choice = True

        initial_loyalty = self.story_manager.loyalty
        event = pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_1, "unicode": "1"})
        handled = self.hud.handle_event(event)

        self.assertTrue(handled)
        self.assertFalse(self.hud.is_waiting_for_choice)
        self.assertEqual(self.hud.selected_stance, "loyal")
        self.assertGreater(self.story_manager.loyalty, initial_loyalty)
        self.assertIsNotNone(self.hud.response_text)

    def test_handle_event_selects_dissident_option(self):
        """Pressing 3 should select dissident choice and decrease loyalty."""
        self.hud.trigger_transmission("sortie_1_briefing")
        self.hud.typewriter_chars = len(self.hud.current_node.prompt)
        self.hud.is_waiting_for_choice = True

        initial_loyalty = self.story_manager.loyalty
        event = pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_3, "unicode": "3"})
        handled = self.hud.handle_event(event)

        self.assertTrue(handled)
        self.assertEqual(self.hud.selected_stance, "dissident")
        self.assertLess(self.story_manager.loyalty, initial_loyalty)

    def test_response_timeout_dismisses_hud(self):
        """After a choice is made and response timer elapses, HUD should close."""
        self.hud.trigger_transmission("sortie_1_briefing")
        self.hud.typewriter_chars = len(self.hud.current_node.prompt)
        self.hud.is_waiting_for_choice = True

        event = pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_2, "unicode": "2"})
        self.hud.handle_event(event)

        self.assertTrue(self.hud.is_active)
        # Advance through response duration
        for _ in range(50):
            self.hud.update(dt=0.1)

        self.assertFalse(self.hud.is_active)
        self.assertEqual(self.hud.get_time_dilation(), 1.0)

    def test_headless_render_does_not_crash(self):
        """HUD render method should draw safely onto game surface."""
        surface = pygame.Surface((1280, 720))
        self.hud.trigger_transmission("sortie_1_briefing")
        self.hud.update(0.1)
        self.hud.render(surface)


if __name__ == "__main__":
    unittest.main()
