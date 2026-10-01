"""Tests for HelpMenu, SettingsMenu, and user interface navigation."""

from eagle1.ui.help_menu import HelpMenu
from eagle1.ui.settings_menu import SettingsMenu
from eagle1.systems.audio_manager import AudioManager


def test_help_menu_tabs_and_navigation(dummy_surface):
    """Verify HelpMenu tab cycle and rendering across all 6 tabs."""
    menu = HelpMenu(1280, 720)
    assert len(menu.TAB_NAMES) == 6
    assert menu.active_tab == 0

    # Cycle forwards
    for i in range(1, 6):
        menu.next_tab()
        assert menu.active_tab == i
        menu.draw(dummy_surface)

    # Wrap around
    menu.next_tab()
    assert menu.active_tab == 0

    # Cycle backwards
    menu.prev_tab()
    assert menu.active_tab == 5


def test_settings_menu_navigation_and_render(dummy_surface):
    """Verify SettingsMenu tab cycle and headless drawing."""
    menu = SettingsMenu(1280, 720)
    assert len(menu.TAB_NAMES) == 3
    assert menu.active_tab == 0

    for i in range(len(menu.TAB_NAMES)):
        menu.active_tab = i
        menu.draw(dummy_surface)


def test_audio_manager_mute_toggle(tmp_path):
    """Verify audio manager mute toggle functions without mutating user settings."""
    am = AudioManager()
    am.settings_file = str(tmp_path / "test_audio_settings.json")
    original_mute = am.is_muted()
    am.toggle_mute()
    assert am.is_muted() != original_mute
    am.toggle_mute()
    assert am.is_muted() == original_mute
