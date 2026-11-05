"""menu_nav.py - Uniform menu buttons with keyboard focus for the Military Terminal UI."""

from __future__ import annotations

from typing import Callable, List, Optional, Sequence

import pygame

from eagle1.ui import theme, widgets

SfxCallback = Optional[Callable[[str], None]]

VARIANT_PRIMARY = "primary"
VARIANT_SECONDARY = "secondary"
VARIANT_DANGER = "danger"
BUTTON_HEIGHT = 48


class MenuButton:
    """Sharp-cornered menu button; API-compatible with the TextBox subset used by tests."""

    def __init__(
        self,
        text: str,
        rect: pygame.Rect,
        hotkey: str = "",
        variant: str = VARIANT_SECONDARY,
        enabled: bool = True,
        on_sfx: SfxCallback = None,
        text_cache: Optional[widgets.TextCache] = None,
    ) -> None:
        self.text = str(text)
        self.rect = pygame.Rect(rect)
        self.hotkey = hotkey
        self.variant = variant
        self.enabled = enabled
        self._on_sfx = on_sfx
        self._font = theme.get_font("heading")
        self._key_font = theme.get_font("mono_small")
        self._cache = text_cache if text_cache is not None else widgets.TextCache(64)
        self._was_hovered = False
        self._layout_key = None
        self._layout = ("", 0, 0)

    def _label_layout(self):
        """Return (fitted label, key badge width, key badge height), recomputed only when text or width change."""
        key = (self.text, self.rect.w, self.hotkey)
        if key != self._layout_key:
            key_w = key_h = 0
            if self.hotkey and self._key_font is not None:
                key_w = self._key_font.size(self.hotkey.upper())[0] + 10
                key_h = self._key_font.get_height() + 4
            badge_w = key_w + 12 if key_w else 0
            label = widgets.fit_text(self._font, self.text.upper(), self.rect.w - 40 - badge_w)
            self._layout = (label, key_w, key_h)
            self._layout_key = key
        return self._layout

    def set_text(self, new_text: str) -> None:
        self.text = str(new_text)

    def set_enabled(self, enabled: bool) -> None:
        self.enabled = bool(enabled)

    def get_hitbox(self) -> pygame.Rect:
        return self.rect

    def is_hovered(self, mouse_pos) -> bool:
        return bool(self.enabled and mouse_pos is not None and self.rect.collidepoint(mouse_pos))

    def is_clicked(self, event: pygame.event.Event, mouse_pos) -> bool:
        if not self.enabled:
            return False
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.is_hovered(mouse_pos):
            if self._on_sfx is not None:
                self._on_sfx("ui_click")
            return True
        return False

    def draw(self, surface: pygame.Surface, mouse_pos=None, focused: bool = False) -> None:
        hovered = self.is_hovered(mouse_pos)
        if hovered and not self._was_hovered and self._on_sfx is not None:
            self._on_sfx("ui_hover")
        self._was_hovered = hovered

        danger = self.variant == VARIANT_DANGER
        if not self.enabled:
            widgets.draw_panel(surface, self.rect, theme.PANEL, theme.BORDER, brackets=False)
            text_color = theme.TEXT_DISABLED
            key_color = theme.TEXT_DISABLED
        elif focused or hovered:
            edge = theme.DANGER if danger else theme.ACCENT
            widgets.draw_panel(surface, self.rect, theme.PANEL_HOVER, edge, edge)
            widgets.draw_focus_bar(surface, self.rect, edge)
            text_color = theme.TEXT
            key_color = edge
        else:
            edge = theme.ACCENT_DIM if self.variant == VARIANT_PRIMARY else theme.BORDER_STRONG
            widgets.draw_panel(surface, self.rect, theme.PANEL_RAISED, edge, brackets=False)
            text_color = theme.TEXT
            key_color = theme.ACCENT if self.enabled else theme.TEXT_DISABLED

        if self._font is None:
            return
        label, key_w, key_h = self._label_layout()
        label_surf = self._cache.render(self._font, label, text_color)
        surface.blit(label_surf, (self.rect.x + 20, self.rect.centery - label_surf.get_height() // 2))
        if key_w:
            widgets.draw_key_badge(
                surface,
                self._cache,
                self._key_font,
                self.hotkey,
                (self.rect.right - 12 - key_w, self.rect.centery - key_h // 2),
                key_color,
            )


class MenuNavigator:
    """Keyboard + mouse focus management over a list of MenuButtons."""

    def __init__(self, buttons: Sequence[MenuButton], wrap: bool = True, on_sfx: SfxCallback = None) -> None:
        self.buttons: List[MenuButton] = list(buttons)
        self.wrap = wrap
        self._on_sfx = on_sfx
        self.focus_index = 0
        for i, button in enumerate(self.buttons):
            if button.enabled:
                self.focus_index = i
                break

    def focus(self, index: int) -> None:
        if 0 <= index < len(self.buttons):
            self.focus_index = index

    def move_focus(self, step: int) -> None:
        count = len(self.buttons)
        if count == 0 or step == 0:
            return
        direction = 1 if step > 0 else -1
        index = self.focus_index
        for _ in range(count):
            nxt = index + direction
            if self.wrap:
                nxt %= count
            elif nxt < 0 or nxt >= count:
                return
            index = nxt
            if self.buttons[index].enabled:
                if index != self.focus_index:
                    self.focus_index = index
                    if self._on_sfx is not None:
                        self._on_sfx("ui_hover")
                return

    def handle_event(self, event: pygame.event.Event, mouse_pos=None) -> Optional[int]:
        if not self.buttons:
            return None
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP:
                self.move_focus(-1)
            elif event.key == pygame.K_DOWN:
                self.move_focus(1)
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                if self.buttons[self.focus_index].enabled:
                    if self._on_sfx is not None:
                        self._on_sfx("ui_click")
                    return self.focus_index
        elif event.type == pygame.MOUSEMOTION and mouse_pos is not None:
            for i, button in enumerate(self.buttons):
                if button.is_hovered(mouse_pos):
                    self.focus(i)
                    break
        elif event.type == pygame.MOUSEBUTTONDOWN:
            for i, button in enumerate(self.buttons):
                if button.is_clicked(event, mouse_pos):
                    self.focus(i)
                    return i
        return None

    def draw(self, surface: pygame.Surface, mouse_pos=None) -> None:
        for i, button in enumerate(self.buttons):
            button.draw(surface, mouse_pos, focused=(i == self.focus_index))
