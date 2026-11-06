"""Tests for the re-themed EnlistmentScreen."""

import os
import tempfile

import pygame
import pytest

from eagle1.ui.enlistment_screen import CONTRACT_HEADER_COLOR, EnlistmentScreen


@pytest.fixture
def screen():
    with tempfile.TemporaryDirectory() as tmpdir:
        old = os.environ.get("EAGLE1_USER_DATA_DIR")
        os.environ["EAGLE1_USER_DATA_DIR"] = tmpdir
        yield EnlistmentScreen(1280, 720)
        if old is not None:
            os.environ["EAGLE1_USER_DATA_DIR"] = old
        else:
            os.environ.pop("EAGLE1_USER_DATA_DIR", None)


def _key(key, char=""):
    return pygame.event.Event(pygame.KEYDOWN, key=key, unicode=char, mod=0)


def test_error_message_stays_on_screen_and_clear_of_contract(screen, dummy_surface):
    assert screen.handle_event(_key(pygame.K_RETURN), (640, 360)) is None
    screen.draw(dummy_surface, (640, 360))
    err = screen._error_rect
    assert err is not None
    assert pygame.Rect(0, 0, 1280, 720).contains(err)
    assert not err.colliderect(screen.contract_rect)
    assert not err.colliderect(screen.input_rect)


def test_tab_toggles_focus(screen):
    assert screen.input_focused is True
    screen.handle_event(_key(pygame.K_TAB), (640, 360))
    assert screen.input_focused is False
    screen.handle_event(_key(pygame.K_TAB), (640, 360))
    assert screen.input_focused is True


def test_typing_while_unfocused_refocuses_and_appends(screen):
    screen.input_focused = False
    screen.handle_event(_key(pygame.K_a, "a"), (640, 360))
    assert screen.input_focused is True
    assert screen.username == "A"


def test_header_lines_use_header_color_flag(screen):
    headers = [line for line, color in screen.wrapped_lines if color == CONTRACT_HEADER_COLOR]
    assert len(headers) >= 7
    assert all(color != CONTRACT_HEADER_COLOR for line, color in screen.wrapped_lines if line and not line[0].isdigit()
               and not line.startswith("CONTRACT"))


def test_contract_still_scrollable(screen):
    assert screen.max_scroll > 0


def test_layout_rects_inside_screen_and_buttons_disjoint(screen):
    screen_rect = pygame.Rect(0, 0, 1280, 720)
    for rect in (screen.contract_rect, screen.btn_back_rect, screen.btn_sign_rect, screen.input_rect):
        assert screen_rect.contains(rect)
    assert not screen.btn_back_rect.colliderect(screen.btn_sign_rect)
    assert not screen.contract_rect.colliderect(screen.btn_back_rect)


def test_draw_allocates_no_surfaces_after_warmup(screen, dummy_surface, monkeypatch):
    screen.draw(dummy_surface, (10, 10))

    def _raise(*args, **kwargs):
        raise AssertionError("allocation in draw")

    monkeypatch.setattr(pygame, "Surface", _raise)
    monkeypatch.setattr(pygame.font, "SysFont", _raise)
    for _ in range(3):
        screen.draw(dummy_surface, (10, 10))
