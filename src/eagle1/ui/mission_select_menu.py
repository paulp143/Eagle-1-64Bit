"""mission_select_menu.py - Operation selection list (Military Terminal style)."""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Sequence, Union

import pygame

from eagle1.ui import theme, widgets

MissionConfig = Dict[str, Any]

CARD_HEIGHT = 92
CARD_GAP = 10
CARD_TOP = 112
CARD_MARGIN_X = 160

_DIFFICULTY_COLORS = {"MEDIUM": theme.SUCCESS, "HARD": theme.WARNING}


class MissionSelectMenu:
    """Tactical operation selector with hotkeys 1-5, arrow focus and mouse support."""

    def __init__(
        self,
        mission_configs: Dict[Any, MissionConfig],
        mission_order: Sequence[Any],
        width: int = 1280,
        height: int = 720,
        on_sfx: Optional[Callable[[str], None]] = None,
    ) -> None:
        self.configs = mission_configs
        self.order: List[Any] = list(mission_order)
        self.width = width
        self.height = height
        self._on_sfx = on_sfx
        self.focus_index = 0
        self.card_rects: Dict[Any, pygame.Rect] = {}

        self._font_title = theme.get_font("title")
        self._font_name = theme.get_font("heading")
        self._font_small = theme.get_font("mono_small")
        self._font_body = theme.get_font("body_small")
        self._cache = widgets.TextCache(256)
        self._overlay = widgets.make_overlay((width, height), theme.OVERLAY_RGBA)

        card_w = width - 2 * CARD_MARGIN_X
        for i, m_id in enumerate(self.order):
            self.card_rects[m_id] = pygame.Rect(
                CARD_MARGIN_X, CARD_TOP + i * (CARD_HEIGHT + CARD_GAP), card_w, CARD_HEIGHT
            )

        self._desc_lines: Dict[Any, List[str]] = {}
        if self._font_body is not None:
            for m_id in self.order:
                desc = str(self.configs[m_id].get("desc", ""))
                self._desc_lines[m_id] = widgets.wrap_text_px(self._font_body, desc, card_w - 380, max_lines=2)

    def _set_focus(self, index: int) -> None:
        if 0 <= index < len(self.order) and index != self.focus_index:
            self.focus_index = index
            if self._on_sfx is not None:
                self._on_sfx("ui_hover")

    def handle_event(self, event: pygame.event.Event, mouse_pos=None) -> Optional[Union[MissionConfig, str]]:
        if event.type == pygame.KEYDOWN:
            if pygame.K_1 <= event.key <= pygame.K_9:
                idx = event.key - pygame.K_1
                if idx < len(self.order):
                    return self.configs[self.order[idx]]
            elif event.key == pygame.K_UP:
                self._set_focus((self.focus_index - 1) % len(self.order))
            elif event.key == pygame.K_DOWN:
                self._set_focus((self.focus_index + 1) % len(self.order))
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                return self.configs[self.order[self.focus_index]]
            elif event.key == pygame.K_ESCAPE:
                return "back_to_menu"
        elif event.type == pygame.MOUSEMOTION and mouse_pos is not None:
            for i, m_id in enumerate(self.order):
                if self.card_rects[m_id].collidepoint(mouse_pos):
                    self._set_focus(i)
                    break
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and mouse_pos is not None:
            for m_id, rect in self.card_rects.items():
                if rect.collidepoint(mouse_pos):
                    return self.configs[m_id]
        return None

    def draw(self, surface: pygame.Surface, mouse_pos=None) -> None:
        surface.blit(self._overlay, (0, 0))
        if self._font_title is None or self._font_name is None or self._font_small is None:
            return
        title = self._cache.render(self._font_title, "OPERATION SELECT", theme.ACCENT)
        surface.blit(title, (self.width // 2 - title.get_width() // 2, 40))
        sub = self._cache.render(
            self._font_small, "CHOOSE AN OPERATION — 1-5, UP/DOWN + ENTER OR CLICK", theme.TEXT_MUTED
        )
        surface.blit(sub, (self.width // 2 - sub.get_width() // 2, 82))

        for idx, m_id in enumerate(self.order):
            config = self.configs[m_id]
            rect = self.card_rects[m_id]
            hovered = bool(mouse_pos and rect.collidepoint(mouse_pos))
            focused = hovered or idx == self.focus_index
            accent = config.get("icon_color", theme.ACCENT)
            if focused:
                widgets.draw_panel(surface, rect, theme.PANEL_HOVER, theme.BORDER_STRONG, accent)
                widgets.draw_focus_bar(surface, rect, accent)
            else:
                widgets.draw_panel(surface, rect, theme.PANEL_RAISED, theme.BORDER, brackets=False)

            widgets.draw_key_badge(surface, self._cache, self._font_small, str(idx + 1), (rect.x + 16, rect.y + 16))
            name = self._cache.render(self._font_name, str(config.get("name", "")).upper(), theme.TEXT)
            surface.blit(name, (rect.x + 64, rect.y + 14))
            cat = self._cache.render(self._font_small, str(config.get("category", "")), accent)
            surface.blit(cat, (rect.x + 64, rect.y + 48))

            if self._font_body is not None:
                step = self._font_body.get_linesize()
                for i, line in enumerate(self._desc_lines.get(m_id, [])):
                    surf = self._cache.render(self._font_body, line, theme.TEXT_MUTED)
                    surface.blit(surf, (rect.x + 340, rect.y + 16 + i * step))

            diff = str(config.get("difficulty", ""))
            diff_surf = self._cache.render(
                self._font_small, f"DIFFICULTY: {diff}", _DIFFICULTY_COLORS.get(diff, theme.DANGER)
            )
            surface.blit(diff_surf, (rect.right - 16 - diff_surf.get_width(), rect.bottom - 16 - diff_surf.get_height()))

        widgets.draw_key_badge(surface, self._cache, self._font_small, "ESC", (CARD_MARGIN_X, self.height - 48))
        back = self._cache.render(self._font_small, "BACK TO MAIN MENU", theme.TEXT_MUTED)
        surface.blit(back, (CARD_MARGIN_X + 52, self.height - 46))
