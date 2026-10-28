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

    def test_story_manager_active_dialogue_auto_triggers_comms_hud(self):
        """Setting active_dialogue on StoryManager must auto-activate CommsHUD on update."""
        from eagle1.story.dialogue_db import get_dialogue_node

        node = get_dialogue_node("sortie_1_inflight")
        self.assertIsNotNone(node)
        self.story_manager.set_active_dialogue(node)
        self.assertEqual(self.story_manager.time_dilation, 0.4)

        self.comms_hud.update(dt=1.0 / 60.0)
        self.assertTrue(self.comms_hud.is_active)
        self.assertEqual(self.comms_hud.current_node.node_id, "sortie_1_inflight")

    def test_end_to_end_choice_updates_loyalty_and_persists_save(self):
        """Selecting a stance via CommsHUD must update loyalty, restore dilation, and persist to disk."""
        self.comms_hud.trigger_transmission("sortie_1_inflight")
        self.assertIsNotNone(self.story_manager.active_dialogue)
        self.assertEqual(self.story_manager.time_dilation, 0.4)

        # Complete typewriter and lerp into 0.4 time dilation
        self.comms_hud.typewriter_chars = 999.0
        for _ in range(15):
            self.comms_hud.update(dt=0.1)

        self.assertTrue(self.comms_hud.is_waiting_for_choice)
        self.assertAlmostEqual(self.comms_hud.get_time_dilation(), 0.4, places=2)

        initial_loyalty = self.story_manager.loyalty
        event_3 = pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_3, "unicode": "3"})
        handled = self.comms_hud.handle_event(event_3)

        self.assertTrue(handled)
        self.assertIsNone(self.story_manager.active_dialogue)
        self.assertEqual(self.story_manager.time_dilation, 1.0)
        self.assertLess(self.story_manager.loyalty, initial_loyalty)

        # Verify disk persistence via CampaignSaveManager
        reloaded = self.save_manager.load_campaign()
        self.assertAlmostEqual(reloaded.loyalty, self.story_manager.loyalty, places=2)
        choices = {c["node"]: c["stance"] for c in reloaded.choices_made}
        self.assertEqual(choices.get("sortie_1_inflight"), "dissident")

    def test_pause_freezes_comms_timers_and_preserves_time_dilation(self):
        """Updating CommsHUD with dt=0.0 (paused) must freeze typewriter, timers, and 0.4 dilation."""
        self.comms_hud.trigger_transmission("sortie_1_inflight")
        self.comms_hud.typewriter_chars = 999.0
        for _ in range(15):
            self.comms_hud.update(dt=0.1)

        self.assertTrue(self.comms_hud.is_waiting_for_choice)
        dilation_before = self.comms_hud.get_time_dilation()
        waveform_before = self.comms_hud.waveform_phase

        # Simulate 120 frames of pause (dt=0.0)
        for _ in range(120):
            self.comms_hud.update(dt=0.0)

        self.assertTrue(self.comms_hud.is_waiting_for_choice)
        self.assertEqual(self.comms_hud.get_time_dilation(), dilation_before)
        self.assertEqual(self.comms_hud.waveform_phase, waveform_before)

    def test_helldiver_casualty_and_squad_wipe_end_to_end_pipeline(self):
        """GroundSupportManager casualties and squad wipe must update StoryManager, save to disk, and trigger CommsHUD."""
        from eagle1.systems.ground_support import GroundSupportManager, HelldiverUnit

        gsm = GroundSupportManager()
        gsm.set_story_manager(self.story_manager)
        gsm.set_comms_hud(self.comms_hud)
        gsm.banter_cooldown = 0.0

        gsm.units = [
            HelldiverUnit(0, 1000, 1000),
            HelldiverUnit(1, 1030, 1000),
            HelldiverUnit(2, 1060, 1000),
            HelldiverUnit(3, 1090, 1000),
        ]
        gsm.survivors_count = 4

        mock_player = MagicMock()
        mock_player.pos_x = 1000
        mock_player.pos_y = 1000
        mock_player.x = 1000
        mock_player.y = 1000
        mock_player.score = 500

        initial_loyalty = self.story_manager.loyalty
        # Kill 3 Helldivers first
        for hd in gsm.units[:3]:
            hd.take_damage(999.0)
        gsm.update(0.016, mock_player, [], pygame.sprite.Group(), [])

        # 3 casualties * -3.5 = -10.5
        self.assertAlmostEqual(self.story_manager.loyalty, initial_loyalty - 10.5, places=2)
        self.assertTrue(self.comms_hud.is_active)

        # Kill the last Helldiver to trigger full squad wipe (-3.5 - 8.0 = -11.5)
        gsm.units[3].take_damage(999.0)
        gsm.update(0.016, mock_player, [], pygame.sprite.Group(), [])

        expected_final = initial_loyalty - 22.0
        self.assertAlmostEqual(self.story_manager.loyalty, expected_final, places=2)
        reloaded = self.save_manager.load_campaign()
        self.assertAlmostEqual(reloaded.loyalty, expected_final, places=2)

    def test_arcade_respawn_dismisses_comms_without_overwriting_campaign_save(self):
        """Dismissing CommsHUD on arcade respawn must restore 1.0 dilation and preserve campaign save state."""
        self.story_manager.modify_loyalty(18.0, reason="Campaign progress")
        saved_loyalty = self.story_manager.loyalty

        self.comms_hud.trigger_transmission("sortie_1_inflight")
        self.comms_hud.typewriter_chars = 999.0
        for _ in range(15):
            self.comms_hud.update(dt=0.1)
        self.assertAlmostEqual(self.comms_hud.get_time_dilation(), 0.4, places=2)

        # Simulate respawn() cleanup: dismiss CommsHUD
        self.comms_hud.dismiss()
        self.assertFalse(self.comms_hud.is_active)
        self.assertEqual(self.comms_hud.get_time_dilation(), 1.0)
        self.assertIsNone(self.story_manager.active_dialogue)
        self.assertEqual(self.story_manager.time_dilation, 1.0)

        # Campaign loyalty in memory and on disk must remain untouched
        self.assertAlmostEqual(self.story_manager.loyalty, saved_loyalty, places=2)
        reloaded = self.save_manager.load_campaign()
        self.assertAlmostEqual(reloaded.loyalty, saved_loyalty, places=2)


if __name__ == "__main__":
    unittest.main()
