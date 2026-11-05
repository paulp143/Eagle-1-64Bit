"""Tests for the re-themed DebriefingScreen."""

import pygame

from eagle1.ui.debriefing_screen import DebriefingScreen

FULL_RESULTS = {
    "mission_name": "Outpost Demolition",
    "final_score": 12345,
    "highscore": 12345,
    "is_new_highscore": True,
    "duration_seconds": 754,
    "waves_cleared": 6,
    "aerial_kills": 42,
    "bomber_kills": 3,
    "cas_kills": 17,
    "fabricators_destroyed": 4,
    "strider_destroyed": True,
    "survivors_count": 4,
    "casualties_count": 0,
    "squad_wiped": False,
    "hull_ratio": 1.0,
    "flawless_squad": True,
    "hero_score": 900,
}


def _key(key):
    return pygame.event.Event(pygame.KEYDOWN, key=key)


def _screen():
    screen = DebriefingScreen(1280, 720)
    screen.set_results(dict(FULL_RESULTS))
    return screen


def test_stat_blits_stay_inside_stats_box():
    screen = _screen()
    box = screen.stats_box
    for surf, pos in screen._static_blits:
        rect = pygame.Rect(pos, surf.get_size())
        if rect.y >= box.y + 40 and rect.x >= box.x:
            assert box.contains(rect), (pos, surf.get_size())


def test_long_rows_do_not_overlap_each_other():
    screen = _screen()
    box = screen.stats_box
    rects = [pygame.Rect(pos, s.get_size()) for s, pos in screen._static_blits if pos[1] >= box.y + 52 and pos[0] >= box.x]
    for i, a in enumerate(rects):
        for b in rects[i + 1:]:
            assert not a.colliderect(b), (a, b)


def test_draw_allocates_no_surfaces_per_frame(dummy_surface, monkeypatch):
    screen = _screen()
    screen.draw(dummy_surface, (640, 360))

    def _raise(*args, **kwargs):
        raise AssertionError("allocation in draw")

    monkeypatch.setattr(pygame, "Surface", _raise)
    monkeypatch.setattr(pygame.font, "SysFont", _raise)
    for _ in range(3):
        screen.draw(dummy_surface, (640, 360))


def test_left_right_and_enter_use_focused_action():
    screen = _screen()
    assert screen.handle_event(_key(pygame.K_RETURN)) == "super_destroyer"
    screen.handle_event(_key(pygame.K_LEFT))
    assert screen.handle_event(_key(pygame.K_RETURN)) == "replay"
    screen.handle_event(_key(pygame.K_RIGHT))
    screen.handle_event(_key(pygame.K_RIGHT))
    assert screen.handle_event(_key(pygame.K_RETURN)) == "mission_select"


def test_inactive_screen_ignores_events():
    screen = DebriefingScreen(1280, 720)
    assert screen.handle_event(_key(pygame.K_RETURN)) is None


def test_button_labels_are_not_truncated():
    screen = _screen()
    for button in screen._buttons:
        label = button.text.upper()
        badge_w = button._key_font.size(button.hotkey.upper())[0] + 22
        assert button._font.size(label)[0] <= button.rect.w - 40 - badge_w, label


def test_sfx_played_on_enter_when_audio_manager_given():
    calls = []

    class _Audio:
        def play_sfx(self, name, *args, **kwargs):
            calls.append(name)

    screen = DebriefingScreen(1280, 720, audio_manager=_Audio())
    screen.set_results(dict(FULL_RESULTS))
    screen.handle_event(_key(pygame.K_RETURN))
    assert "ui_click" in calls
