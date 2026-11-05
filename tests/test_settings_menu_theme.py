"""Tests for the re-themed SettingsMenu (keyboard navigation, wiring, no per-frame allocations)."""

import pygame

from eagle1.app import game
from eagle1.ui.controls_reference import CONTROL_BINDINGS
from eagle1.ui.layout import validate_rects_no_overlap
from eagle1.ui.settings_menu import SettingsMenu


def _key(key, mod=0):
    return pygame.event.Event(pygame.KEYDOWN, key=key, mod=mod)


def test_tab_names_unchanged():
    assert len(SettingsMenu.TAB_NAMES) == 3


def test_arrows_and_tab_cycle_tabs():
    menu = SettingsMenu(1280, 720)
    assert menu.handle_event(_key(pygame.K_RIGHT)) == "tab_changed"
    assert menu.active_tab == SettingsMenu.TAB_GAMEPLAY
    assert menu.handle_event(_key(pygame.K_LEFT)) == "tab_changed"
    assert menu.active_tab == SettingsMenu.TAB_AUDIO
    assert menu.handle_event(_key(pygame.K_LEFT)) == "tab_changed"
    assert menu.active_tab == SettingsMenu.TAB_CONTROLS
    assert menu.handle_event(_key(pygame.K_TAB)) == "tab_changed"
    assert menu.active_tab == SettingsMenu.TAB_AUDIO


def test_focus_down_then_plus_raises_slider():
    menu = SettingsMenu(1280, 720)
    menu.slider_music.on_change = None  # never persist audio settings from tests
    menu.slider_music.set_value(0.5)
    menu.handle_event(_key(pygame.K_DOWN))
    menu.handle_event(_key(pygame.K_EQUALS))
    assert abs(menu.slider_music.value - 0.55) < 1e-6
    menu.handle_event(_key(pygame.K_MINUS))
    assert abs(menu.slider_music.value - 0.5) < 1e-6


def test_enter_toggles_focused_gameplay_toggle():
    menu = SettingsMenu(1280, 720)
    menu.handle_event(_key(pygame.K_2))
    assert menu.toggle_screen_shake.state is True
    menu.handle_event(_key(pygame.K_RETURN))
    assert menu.toggle_screen_shake.state is False
    menu.handle_event(_key(pygame.K_DOWN))
    menu.handle_event(_key(pygame.K_RETURN))
    assert menu.toggle_speedometer.state is False


def test_escape_closes():
    assert SettingsMenu(1280, 720).handle_event(_key(pygame.K_ESCAPE)) == "close"


def test_draw_every_tab_allocates_no_surfaces_after_warmup(dummy_surface, monkeypatch):
    menu = SettingsMenu(1280, 720)
    for tab in range(3):
        menu.active_tab = tab
        menu.draw(dummy_surface, (300, 300))

    def _raise(*args, **kwargs):
        raise AssertionError("allocation in draw")

    monkeypatch.setattr(pygame, "Surface", _raise)
    for tab in range(3):
        menu.active_tab = tab
        menu.draw(dummy_surface, (300, 300))


def test_controls_tab_lists_every_binding():
    menu = SettingsMenu(1280, 720)
    keys = [e[1] for col in menu._controls_rows for e in col if e[0] == "row"]
    assert keys == [b.keys for b in sorted(CONTROL_BINDINGS, key=lambda b: ("FLIGHT", "WEAPONS", "STRATAGEMS", "SYSTEM").index(b.category))]


def test_tab_and_close_rects_do_not_overlap():
    menu = SettingsMenu(1280, 720)
    assert validate_rects_no_overlap(menu.tab_rects + [menu.close_btn_rect]) == []


class _RecordingSurface(pygame.Surface):
    """Surface that records fill() calls so a test can tell whether a vignette was drawn."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fills = 0

    def fill(self, *args, **kwargs):
        self.fills += 1
        return super().fill(*args, **kwargs)


def _draw_critical_frame(monkeypatch, warnings_on, speedometer_on):
    """Draw one gameplay frame at critical hull and report (vignette drawn, sfx played, speed drawn)."""
    game.respawn()
    game.player.health = 1
    vignette = _RecordingSurface((game.GAME_WIDTH, game.GAME_HEIGHT), pygame.SRCALPHA)
    sfx, speed_calls = [], []
    monkeypatch.setattr(game, "vignette_health_surf", vignette)
    monkeypatch.setattr(game.audio_manager, "play_sfx", lambda name, *a, **k: sfx.append(name))
    monkeypatch.setattr(game.hud_renderer, "draw_speed", lambda *a, **k: speed_calls.append(a))
    monkeypatch.setattr(game.settings_menu.toggle_warnings, "state", warnings_on)
    monkeypatch.setattr(game.settings_menu.toggle_speedometer, "state", speedometer_on)
    game.draw((640, 360))
    return vignette.fills > 0, "low_health" in sfx, bool(speed_calls)


def test_warning_toggle_hides_vignette_but_keeps_alarm_audio(monkeypatch):
    assert _draw_critical_frame(monkeypatch, True, True)[:2] == (True, True)
    assert _draw_critical_frame(monkeypatch, False, True)[:2] == (False, True)


def test_speedometer_toggle_controls_speed_gauge(monkeypatch):
    assert _draw_critical_frame(monkeypatch, True, True)[2] is True
    assert _draw_critical_frame(monkeypatch, True, False)[2] is False


def test_controls_grid_stays_inside_the_panel_with_equal_margins():
    from eagle1.ui.settings_menu import CONTROLS_COL_GAP, CONTROLS_COL_W, CONTROLS_MARGIN_X

    menu = SettingsMenu(1280, 720)
    left = menu.panel_rect.x + CONTROLS_MARGIN_X
    right = left + 2 * CONTROLS_COL_W + CONTROLS_COL_GAP
    assert menu.panel_rect.right - right in (CONTROLS_MARGIN_X, CONTROLS_MARGIN_X + 1)
