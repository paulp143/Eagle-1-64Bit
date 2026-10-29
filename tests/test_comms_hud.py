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
from eagle1.story.dialogue_data import VIPER_DIALOGUE_TREES
from eagle1.story.dialogue_db import DIALOGUE_DATABASE
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

    def test_trigger_callout_non_interactive_no_slow_mo(self):
        """Callouts should activate HUD, display prompt, stay at 1.0 time dilation, and auto-dismiss."""
        success = self.hud.trigger_callout(
            speaker='Viper-1 "Apex"',
            text="CAS beacon planted! Bring the rain!",
            portrait="images/portraits/viper_1_apex.png",
            duration=1.5,
        )
        self.assertTrue(success)
        self.assertTrue(self.hud.is_active)
        self.assertEqual(self.hud.get_time_dilation(), 1.0)
        self.assertFalse(self.hud.is_waiting_for_choice)

        # Fast forward typewriter
        self.hud.typewriter_chars = 999.0
        self.hud.update(dt=0.1)
        self.assertEqual(self.hud.get_time_dilation(), 1.0)
        self.assertFalse(self.hud.is_waiting_for_choice)

        # Advance past duration
        for _ in range(20):
            self.hud.update(dt=0.1)

        self.assertFalse(self.hud.is_active)

    def test_callout_does_not_interrupt_active_choice(self):
        """Non-interactive callout must return False and not overwrite pending 3-way choices."""
        self.hud.trigger_transmission("sortie_1_briefing")
        self.hud.typewriter_chars = len(self.hud.current_node.prompt)
        self.hud.update(0.1)
        self.assertTrue(self.hud.is_waiting_for_choice)

        # Attempt to trigger background banter while player choice is pending
        rejected = self.hud.trigger_callout(
            speaker='Viper-4 "Doc"',
            text="I need supplies!",
            portrait="images/portraits/viper_4_doc.png",
        )
        self.assertFalse(rejected)
        # Original interactive node remains untouched
        self.assertEqual(self.hud.current_node.node_id, "sortie_1_briefing")
        self.assertTrue(self.hud.is_waiting_for_choice)

    def test_portrait_loading_and_caching(self):
        """Speaker portrait surfaces should load from disk, cache, and render cleanly."""
        portrait_path = "images/portraits/viper_1_apex.png"
        surf = self.hud._get_portrait_surface(portrait_path)
        self.assertIsNotNone(surf)
        self.assertEqual(surf.get_size(), (64, 64))

        # Second lookup should return cached surface
        surf_cached = self.hud._get_portrait_surface(portrait_path)
        self.assertIs(surf, surf_cached)

        # Render with portrait
        canvas = pygame.Surface((1280, 720))
        self.hud.trigger_callout(
            speaker='Viper-1 "Apex"',
            text="Holding the line!",
            portrait=portrait_path,
        )
        self.hud.render(canvas)

        # Invalid portrait fallback
        none_surf = self.hud._get_portrait_surface("images/portraits/non_existent.png")
        self.assertIsNone(none_surf)

    def test_non_interactive_callout_never_intercepts_gameplay_keys(self):
        """Callouts must never swallow SPACE, ESCAPE, RETURN, or combat keys."""
        self.hud.trigger_callout(
            speaker='Viper-1 "Apex"',
            text="CAS beacon planted! Bring the rain!",
            duration=3.0,
        )
        self.assertTrue(self.hud.is_active)

        # Test during typewriter playback
        self.hud.typewriter_chars = 5.0
        for key in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_ESCAPE, pygame.K_1, pygame.K_w):
            ev = pygame.event.Event(pygame.KEYDOWN, {"key": key})
            self.assertFalse(self.hud.handle_event(ev))
            self.assertTrue(self.hud.is_active)

        # Test after typewriter text has completed
        self.hud.typewriter_chars = 999.0
        for key in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_ESCAPE, pygame.K_1, pygame.K_w):
            ev = pygame.event.Event(pygame.KEYDOWN, {"key": key})
            self.assertFalse(self.hud.handle_event(ev))
            self.assertTrue(self.hud.is_active)

    def test_render_caches_text_surfaces_without_reallocation(self):
        """HUD render method should reuse pre-cached font surfaces without per-frame re-rendering."""
        canvas = pygame.Surface((1280, 720))
        self.hud.trigger_transmission("sortie_1_briefing")
        self.hud.typewriter_chars = float(len(self.hud.current_node.prompt))
        self.hud.is_waiting_for_choice = True

        # First frame render
        self.hud.render(canvas)
        speaker_surf = self.hud._cached_speaker_surf
        loc_surf = self.hud._cached_loc_surf
        body_surfs = list(self.hud._cached_body_surfs)
        option_cards = dict(self.hud._cached_option_cards)

        self.assertIsNotNone(speaker_surf)
        self.assertIsNotNone(loc_surf)
        self.assertGreater(len(body_surfs), 0)
        self.assertIn("loyal", option_cards)

        # Subsequent frame render
        self.hud.render(canvas)
        self.assertIs(self.hud._cached_speaker_surf, speaker_surf)
        self.assertIs(self.hud._cached_loc_surf, loc_surf)
        self.assertEqual(len(self.hud._cached_body_surfs), len(body_surfs))
        for s1, s2 in zip(self.hud._cached_body_surfs, body_surfs):
            self.assertIs(s1, s2)
        self.assertIs(self.hud._cached_option_cards["loyal"][0], option_cards["loyal"][0])
        self.assertIs(self.hud._cached_option_cards["loyal"][1], option_cards["loyal"][1])

    def test_all_dialogue_prompts_and_responses_wrap_without_truncation(self):
        """All registered Act I, Viper Squad, and hub dialogue prompts and responses must wrap without truncation."""
        canvas = pygame.Surface((1280, 720))
        all_nodes = {**DIALOGUE_DATABASE, **VIPER_DIALOGUE_TREES}
        max_available_width = self.hud.box_width - 92 - 14  # 754 px

        for node_id, node in all_nodes.items():
            with self.subTest(node_id=node_id):
                self.hud.trigger_transmission(node)
                self.hud.typewriter_chars = float(len(node.prompt))
                self.hud.render(canvas)

                # Verify full prompt is preserved across wrapped lines without dropping trailing words
                reconstructed = " ".join(self.hud._cached_body_lines)
                self.assertEqual(
                    reconstructed,
                    node.prompt,
                    f"Prompt truncated for node '{node_id}': got '{reconstructed}'",
                )
                self.assertLessEqual(len(self.hud._cached_body_surfs), self.hud.max_body_lines)
                self.assertEqual(len(self.hud._cached_body_surfs), len(self.hud._cached_body_lines))

                for surf in self.hud._cached_body_surfs:
                    self.assertLessEqual(surf.get_width(), max_available_width)

                # Check all option responses for this node as well
                for stance, opt in node.options.items():
                    resp_text = f"[{node.speaker}]: {opt.response}"
                    wrapped_resp = self.hud._wrap_body_lines(resp_text)
                    self.assertEqual(" ".join(wrapped_resp), resp_text)

        # Explicitly verify sortie_1_briefing fits in 3 lines and retains its closing question
        self.hud.trigger_transmission("sortie_1_briefing")
        self.hud.typewriter_chars = float(len(self.hud.current_node.prompt))
        self.hud.render(canvas)
        self.assertEqual(len(self.hud._cached_body_lines), 3)
        self.assertTrue(
            self.hud._cached_body_lines[-1].endswith("spirit feel prior to launch, Lieutenant?")
        )

    def test_wrap_body_lines_edge_cases(self):
        """Verify _wrap_body_lines handles empty strings, single long tokens, and 4-line clamping."""
        self.assertEqual(self.hud._wrap_body_lines(""), [])
        long_token = "A" * 120
        self.assertEqual(self.hud._wrap_body_lines(long_token), [long_token])
        five_lines_text = " ".join(["word" * 20] * 5)
        self.assertEqual(len(self.hud._wrap_body_lines(five_lines_text)), self.hud.max_body_lines)


if __name__ == "__main__":
    unittest.main()
