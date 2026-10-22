"""test_comms_game_integration.py - Integration tests for CommsHUD in the game loop.

Verifies:
1. CommsHUD integration in game state machine.
2. Event delegation during active dialogue beats.
3. Time dilation scaling affecting game delta time.
4. Canvas rendering of radio transceiver overlay above combat viewport.
"""

import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import pygame

pygame.init()
pygame.display.set_mode((1280, 720))

from eagle1.story.campaign_save import CampaignSaveManager
from eagle1.story.comms_hud import CommsHUD
from eagle1.story.story_manager import StoryManager


class TestCommsGameIntegration(unittest.TestCase):
    """Verifies that CommsHUD coordinates cleanly with game loop mechanisms."""

    def setUp(self):
        self.mock_audio = MagicMock()
        self.tmpdir = tempfile.TemporaryDirectory()
        self.save_manager = CampaignSaveManager(data_dir=Path(self.tmpdir.name))
        self.story_manager = StoryManager(audio_manager=self.mock_audio, save_manager=self.save_manager)
        self.comms_hud = CommsHUD(
            story_manager=self.story_manager,
            audio_manager=self.mock_audio,
            screen_width=1280,
            screen_height=720,
        )

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_time_dilation_scales_movement_factor(self):
        """Simulation delta factor must scale down when waiting for player choice."""
        # Baseline: normal speed
        self.assertEqual(self.comms_hud.get_time_dilation(), 1.0)

        # Trigger transmission and complete typewriter
        self.comms_hud.trigger_transmission("sortie_1_inflight")
        self.comms_hud.typewriter_chars = 999.0
        self.comms_hud.update(dt=0.1)

        self.assertTrue(self.comms_hud.is_waiting_for_choice)
        # Advance time dilation lerp
        for _ in range(10):
            self.comms_hud.update(dt=0.1)

        dilation = self.comms_hud.get_time_dilation()
        self.assertAlmostEqual(dilation, 0.4, places=1)

        # Verify a scaled step size
        base_step = 1.0 / 60.0
        scaled_step = base_step * dilation
        self.assertLess(scaled_step, base_step)

    def test_key_interception_during_active_choice(self):
        """Key presses 1, 2, 3 must be captured and consumed by CommsHUD when waiting."""
        self.comms_hud.trigger_transmission("sortie_1_inflight")
        self.comms_hud.typewriter_chars = 999.0
        self.comms_hud.is_waiting_for_choice = True

        event_1 = pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_1, "unicode": "1"})
        handled = self.comms_hud.handle_event(event_1)

        self.assertTrue(handled)
        self.assertEqual(self.comms_hud.selected_stance, "loyal")

    def test_key_passthrough_when_inactive(self):
        """When CommsHUD is inactive, handle_event must return False to allow normal gameplay."""
        self.assertFalse(self.comms_hud.is_active)
        event_space = pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_SPACE, "unicode": " "})
        handled = self.comms_hud.handle_event(event_space)
        self.assertFalse(handled)

    def test_render_overlay_on_game_canvas(self):
        """CommsHUD must render onto 1280x720 canvas surface without modifying surface dimensions."""
        canvas = pygame.Surface((1280, 720))
        self.comms_hud.trigger_transmission("sortie_1_inflight")
        self.comms_hud.typewriter_chars = 999.0
        self.comms_hud.is_waiting_for_choice = True

        self.comms_hud.render(canvas)
        self.assertEqual(canvas.get_size(), (1280, 720))


if __name__ == "__main__":
    unittest.main()
