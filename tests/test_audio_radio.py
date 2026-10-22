"""test_audio_radio.py - Unit and Integration Tests for Radio Audio SFX."""

import os
import unittest
from unittest.mock import MagicMock

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import pygame

pygame.init()

from eagle1.systems.audio_manager import AudioManager


class TestAudioRadio(unittest.TestCase):
    """Test suite for radio squelch, beep, and comms audio triggers."""

    def setUp(self):
        self.audio = AudioManager.get_instance()

    def test_play_radio_squelch_method_exists(self):
        """AudioManager must provide play_radio_squelch without raising AttributeError."""
        self.assertTrue(hasattr(self.audio, "play_radio_squelch"))
        # Must execute safely in headless mode
        self.audio.play_radio_squelch(volume_scale=0.8)

    def test_play_radio_beep_method_exists(self):
        """AudioManager must provide play_radio_beep without raising AttributeError."""
        self.assertTrue(hasattr(self.audio, "play_radio_beep"))
        # Must execute safely in headless mode
        self.audio.play_radio_beep(volume_scale=0.7)

    def test_radio_squelch_calls_play_sfx(self):
        """play_radio_squelch should delegate to play_sfx with appropriate volume."""
        mock_audio = AudioManager.get_instance()
        original_play_sfx = mock_audio.play_sfx
        mock_audio.play_sfx = MagicMock()
        try:
            mock_audio.play_radio_squelch(volume_scale=0.9)
            mock_audio.play_sfx.assert_called_once()
            args, kwargs = mock_audio.play_sfx.call_args
            self.assertIn("radio", args[0])
            self.assertEqual(kwargs.get("volume_scale"), 0.9)
        finally:
            mock_audio.play_sfx = original_play_sfx

    def test_radio_beep_calls_play_sfx(self):
        """play_radio_beep should delegate to play_sfx with appropriate volume."""
        mock_audio = AudioManager.get_instance()
        original_play_sfx = mock_audio.play_sfx
        mock_audio.play_sfx = MagicMock()
        try:
            mock_audio.play_radio_beep(volume_scale=0.75)
            mock_audio.play_sfx.assert_called_once()
            args, kwargs = mock_audio.play_sfx.call_args
            self.assertTrue(args[0] in ("radio_beep", "ui_click"))
            self.assertEqual(kwargs.get("volume_scale"), 0.75)
        finally:
            mock_audio.play_sfx = original_play_sfx


if __name__ == "__main__":
    unittest.main()
