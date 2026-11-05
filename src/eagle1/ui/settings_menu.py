"""
settings_menu.py - Extensible Settings & Configuration Menu for Eagle-1-64Bit

Provides a modular, tabbed Settings menu featuring:
- Audio tab: Master, Music, SFX volume sliders, Mute toggle, and SFX test.
- Gameplay tab: Screen shake, speedometer, low-health warnings.
- Controls tab: Keybindings summary generated from the shared controls reference.
Keyboard: LEFT/RIGHT/TAB cycle tabs, UP/DOWN move focus, +/- adjust a focused slider,
ENTER activates the focused toggle/button.
"""

import pygame

from eagle1.systems.audio_manager import get_audio_manager
from eagle1.ui import theme, widgets
from eagle1.ui.controls_reference import CATEGORY_ORDER, bindings_by_category
from eagle1.ui.gameplay_settings import load_gameplay_settings, save_gameplay_settings

# Color palette (aliases of the central theme tokens; names kept for compatibility)
COLOR_BG_OVERLAY = theme.OVERLAY_RGBA
COLOR_PANEL_BG = theme.PANEL
COLOR_PANEL_BORDER = theme.BORDER
COLOR_TEXT_WHITE = theme.TEXT
COLOR_TEXT_MUTED = theme.TEXT_MUTED
COLOR_TEXT_ACCENT = theme.INFO
COLOR_TEXT_GOLD = theme.ACCENT
COLOR_TEXT_GREEN = theme.SUCCESS
COLOR_TEXT_RED = theme.DANGER

COLOR_TAB_INACTIVE_BG = theme.PANEL_RAISED
COLOR_TAB_INACTIVE_BORDER = theme.BORDER
COLOR_TAB_HOVER_BG = theme.PANEL_HOVER
COLOR_TAB_ACTIVE_BG = theme.PANEL_HOVER
COLOR_TAB_ACTIVE_BORDER = theme.ACCENT

COLOR_SLIDER_BG = theme.PANEL_RAISED
COLOR_SLIDER_FILL = theme.INFO
COLOR_SLIDER_KNOB = theme.TEXT
COLOR_SLIDER_KNOB_HOVER = theme.ACCENT

COLOR_TOGGLE_ON = theme.lerp_color(theme.PANEL, theme.SUCCESS, 0.35)
COLOR_TOGGLE_OFF = theme.lerp_color(theme.PANEL, theme.DANGER, 0.35)

SLIDER_KEY_STEP = 0.05

_TEXT_CACHE = widgets.TextCache(768)


class SliderWidget:
    """Interactive horizontal slider widget supporting mouse drag, keyboard steps and focus."""

    def __init__(self, x, y, width, height, label, min_val=0.0, max_val=1.0, initial_val=0.8, format_fn=None, on_change=None):
        self.rect = pygame.Rect(x, y, width, height)
        self.label = label
        self.min_val = float(min_val)
        self.max_val = float(max_val)
        self.value = float(initial_val)
        self.format_fn = format_fn if format_fn else (lambda v: f"{int(v * 100)}%")
        self.on_change = on_change
        self.dragging = False
        self.knob_radius = 10

    def set_value(self, val):
        val = max(self.min_val, min(self.max_val, float(val)))
        if abs(val - self.value) > 1e-4:
            self.value = val
            if self.on_change:
                self.on_change(self.value)

    def adjust(self, steps):
        """Change the value by ``steps`` keyboard increments (5 % of the range each)."""
        self.set_value(self.value + steps * SLIDER_KEY_STEP * (self.max_val - self.min_val))

    def get_knob_center(self):
        ratio = (self.value - self.min_val) / max(1e-5, (self.max_val - self.min_val))
        knob_x = self.rect.x + int(ratio * self.rect.width)
        knob_y = self.rect.centery
        return (knob_x, knob_y)

    def handle_event(self, event, mouse_pos):
        changed = False
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if mouse_pos:
                # Expanded click zone for ease of use
                hitbox = self.rect.inflate(20, 20)
                if hitbox.collidepoint(mouse_pos):
                    self.dragging = True
                    self._update_from_mouse(mouse_pos[0])
                    changed = True

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self.dragging:
                self.dragging = False
                changed = True

        elif event.type == pygame.MOUSEMOTION:
            if self.dragging and mouse_pos:
                self._update_from_mouse(mouse_pos[0])
                changed = True

        return changed

    def _update_from_mouse(self, mouse_x):
        ratio = (mouse_x - self.rect.x) / float(self.rect.width)
        ratio = max(0.0, min(1.0, ratio))
        new_val = self.min_val + ratio * (self.max_val - self.min_val)
        self.set_value(new_val)

    def draw(self, surface, mouse_pos, font_label, font_val, focused=False):
        knob_pos = self.get_knob_center()
        is_hovered = self.rect.inflate(20, 20).collidepoint(mouse_pos) if mouse_pos else False
        active = is_hovered or self.dragging or focused

        label_surf = _TEXT_CACHE.render(font_label, self.label.upper(), COLOR_TEXT_WHITE)
        val_surf = _TEXT_CACHE.render(font_val, self.format_fn(self.value), theme.ACCENT if active else COLOR_TEXT_MUTED)
        surface.blit(label_surf, (self.rect.x, self.rect.y - 26))
        surface.blit(val_surf, (self.rect.right - val_surf.get_width(), self.rect.y - 26))

        track_h = 8
        track_rect = pygame.Rect(self.rect.x, self.rect.centery - track_h // 2, self.rect.width, track_h)
        widgets.draw_bar(
            surface, track_rect, (knob_pos[0] - self.rect.x) / float(self.rect.width), COLOR_SLIDER_FILL,
            bg=COLOR_SLIDER_BG, border=COLOR_PANEL_BORDER,
        )

        knob_rect = pygame.Rect(0, 0, 10, 22)
        knob_rect.center = knob_pos
        pygame.draw.rect(surface, COLOR_SLIDER_KNOB_HOVER if active else COLOR_SLIDER_KNOB, knob_rect)
        pygame.draw.rect(surface, theme.BG_DEEP, knob_rect, 1)

        if focused:
            widgets.draw_focus_bar(surface, self.rect.inflate(0, 16).move(-14, -4))


class ToggleWidget:
    """Interactive toggle switch widget."""

    def __init__(self, x, y, width, height, label, initial_state=False, on_toggle=None):
        self.rect = pygame.Rect(x, y, width, height)
        self.label = label
        self.state = bool(initial_state)
        self.on_toggle = on_toggle

    def toggle(self):
        self.state = not self.state
        if self.on_toggle:
            self.on_toggle(self.state)

    def set_state(self, state):
        if self.state != bool(state):
            self.state = bool(state)
            if self.on_toggle:
                self.on_toggle(self.state)

    def handle_event(self, event, mouse_pos):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if mouse_pos and self.rect.collidepoint(mouse_pos):
                self.toggle()
                return True
        return False

    def draw(self, surface, mouse_pos, font_label, font_status, focused=False):
        is_hovered = self.rect.collidepoint(mouse_pos) if mouse_pos else False
        active = is_hovered or focused

        widgets.draw_panel(
            surface, self.rect,
            COLOR_TAB_HOVER_BG if active else COLOR_PANEL_BG,
            theme.ACCENT if active else COLOR_PANEL_BORDER,
            brackets=False,
        )
        if focused:
            widgets.draw_focus_bar(surface, self.rect)

        label_surf = _TEXT_CACHE.render(font_label, self.label.upper(), COLOR_TEXT_WHITE)
        surface.blit(label_surf, (self.rect.x + 18, self.rect.centery - label_surf.get_height() // 2))

        switch_w, switch_h = 64, 26
        switch_x = self.rect.right - switch_w - 18
        switch_y = self.rect.centery - switch_h // 2
        switch_rect = pygame.Rect(switch_x, switch_y, switch_w, switch_h)
        pill_border = COLOR_TEXT_GREEN if self.state else COLOR_TEXT_RED
        widgets.draw_panel(
            surface, switch_rect, COLOR_TOGGLE_ON if self.state else COLOR_TOGGLE_OFF, pill_border, brackets=False
        )

        knob_w = 20
        knob_x = switch_x + switch_w - knob_w - 3 if self.state else switch_x + 3
        pygame.draw.rect(surface, COLOR_TEXT_WHITE, (knob_x, switch_y + 3, knob_w, switch_h - 6))

        txt_surf = _TEXT_CACHE.render(font_status, "ON" if self.state else "OFF", pill_border)
        txt_x = switch_x + 8 if self.state else switch_x + switch_w - txt_surf.get_width() - 8
        surface.blit(txt_surf, (txt_x, switch_y + switch_h // 2 - txt_surf.get_height() // 2))


class SettingsMenu:
    """
    Extensible Settings Menu featuring tabbed navigation and customizable options.
    """

    TAB_AUDIO = 0
    TAB_GAMEPLAY = 1
    TAB_CONTROLS = 2

    TAB_NAMES = [
        "1. Audio Settings",
        "2. Gameplay & HUD",
        "3. Flight Controls",
    ]

    AUDIO_BULLETS = [
        ("Centralized 16-Channel Mixer", "Dedicated low-latency voices for weapons, alarms, engine & UI."),
        ("Voice Limiting & Anti-Clipping", "Prevents volume stacking and distortion during intense bullet swarms."),
        ("Dynamic Combat Music Intensity", "Smoothly transitions between ambient and high-threat themes."),
        ("Velocity-Modulated Engine Hum", "Thruster pitch and volume follow your flight speed."),
        ("Persistent Configuration", "Volume levels and mute preferences are saved automatically."),
        ("Instant Mute Shortcut", "Press 'M' during gameplay or menus to toggle mute."),
    ]

    GAMEPLAY_INFO = [
        ("SCREEN SHAKE", "Camera shake on impacts and explosions."),
        ("SPEEDOMETER", "Shows the throttle gauge above the minimap."),
        ("LOW HULL / SHIELD WARNINGS", "Red and cyan screen-edge vignettes at critical levels. The alarm audio always plays."),
    ]

    def __init__(self, width=1280, height=720):
        self.width = width
        self.height = height
        self.active_tab = self.TAB_AUDIO
        self.audio_manager = get_audio_manager()
        self.focus_index = 0

        self.font_title = theme.get_font("title")
        self.font_subtitle = theme.get_font("heading")
        self.font_label = theme.get_font("label")
        self.font_body = theme.get_font("body_small")
        self.font_val = theme.get_font("mono")
        self.font_tag = theme.get_font("mono_tiny")
        self._fonts_ready = None not in (
            self.font_title, self.font_subtitle, self.font_label, self.font_body, self.font_val, self.font_tag
        )

        self._overlay = widgets.make_overlay((self.width, self.height), COLOR_BG_OVERLAY)

        # Tab button rectangles
        self.tab_rects = []
        self._init_tab_rects()

        # Close button rect (top right)
        self.close_btn_rect = pygame.Rect(self.width - 150, 20, 120, 36)

        # Main content panel
        self.panel_rect = pygame.Rect(40, 72, self.width - 80, self.height - 96)

        self._init_audio_widgets()
        self._init_gameplay_widgets()
        self._build_static_content()

        # Feedback notification
        self.feedback_message = ""
        self.feedback_time = 0

    def _init_tab_rects(self):
        self.tab_rects = []
        tab_w = 180
        tab_h = 36
        spacing = 10
        start_x = 40
        for i in range(len(self.TAB_NAMES)):
            x = start_x + i * (tab_w + spacing)
            self.tab_rects.append(pygame.Rect(x, 20, tab_w, tab_h))

    def _init_audio_widgets(self):
        slider_x = 90
        slider_w = 460
        slider_h = 18
        start_y = 175
        spacing_y = 70

        self.slider_master = SliderWidget(
            slider_x, start_y, slider_w, slider_h,
            label="Master Volume",
            initial_val=self.audio_manager.get_master_volume(),
            on_change=lambda val: self.audio_manager.set_master_volume(val)
        )
        self.slider_music = SliderWidget(
            slider_x, start_y + spacing_y, slider_w, slider_h,
            label="Music Volume",
            initial_val=self.audio_manager.get_music_volume(),
            on_change=lambda val: self.audio_manager.set_music_volume(val)
        )
        self.slider_sfx = SliderWidget(
            slider_x, start_y + spacing_y * 2, slider_w, slider_h,
            label="SFX Volume",
            initial_val=self.audio_manager.get_sfx_volume(),
            on_change=lambda val: self.audio_manager.set_sfx_volume(val)
        )
        self.toggle_mute = ToggleWidget(
            slider_x, start_y + spacing_y * 3 + 10, slider_w, 48,
            label="Mute Audio Output (M)",
            initial_state=self.audio_manager.is_muted(),
            on_toggle=lambda state: self.audio_manager.set_mute(state)
        )
        self.test_sfx_rect = pygame.Rect(slider_x, start_y + spacing_y * 4 + 16, 210, 40)
        self.reset_audio_rect = pygame.Rect(slider_x + 230, start_y + spacing_y * 4 + 16, 230, 40)

    def _init_gameplay_widgets(self):
        gx = 90
        gy = 165
        gw = 520
        gh = 48
        spacing = 60

        saved = load_gameplay_settings()
        self.toggle_screen_shake = ToggleWidget(
            gx, gy, gw, gh, label="Tactical Screen Shake", initial_state=saved["screen_shake"],
            on_toggle=lambda _state: self._save_gameplay_toggles(),
        )
        self.toggle_speedometer = ToggleWidget(
            gx, gy + spacing, gw, gh, label="Display Speedometer HUD", initial_state=saved["show_speedometer"],
            on_toggle=lambda _state: self._save_gameplay_toggles(),
        )
        self.toggle_warnings = ToggleWidget(
            gx, gy + spacing * 2, gw, gh, label="Low Hull / Shield Warnings", initial_state=saved["show_warnings"],
            on_toggle=lambda _state: self._save_gameplay_toggles(),
        )

    def _save_gameplay_toggles(self):
        """Persist the gameplay toggles so they survive a restart."""
        save_gameplay_settings({
            "screen_shake": self.toggle_screen_shake.state,
            "show_speedometer": self.toggle_speedometer.state,
            "show_warnings": self.toggle_warnings.state,
        })

    def _build_static_content(self):
        """Pre-compute wrapped info text and the controls grid (no per-frame layout work)."""
        self._audio_bullets = []
        self._gameplay_info = []
        self._controls_rows = []
        if not self._fonts_ready:
            return
        text_w = 560 - 44 - 24
        for title, desc in self.AUDIO_BULLETS:
            self._audio_bullets.append((title, widgets.wrap_text_px(self.font_body, desc, text_w)))
        info_w = 540 - 48
        for title, desc in self.GAMEPLAY_INFO:
            self._gameplay_info.append((title, widgets.wrap_text_px(self.font_body, desc, info_w)))

        # Controls grid: two columns of (kind, text...) rows, categories keep declaration order.
        col_w = 560
        key_w = 190
        columns = [[], []]
        col_for = {"FLIGHT": 0, "WEAPONS": 0, "STRATAGEMS": 1, "SYSTEM": 1}
        for category in CATEGORY_ORDER:
            col = col_for.get(category, 1)
            columns[col].append(("header", category))
            for binding in bindings_by_category(category):
                columns[col].append(
                    ("row", binding.keys, widgets.fit_text(self.font_body, binding.action, col_w - key_w - 24))
                )
        self._controls_rows = columns
        self._controls_col_w = col_w
        self._controls_key_w = key_w

    def sync_from_manager(self):
        """Synchronizes widget values with current AudioManager settings."""
        self.slider_master.set_value(self.audio_manager.get_master_volume())
        self.slider_music.set_value(self.audio_manager.get_music_volume())
        self.slider_sfx.set_value(self.audio_manager.get_sfx_volume())
        self.toggle_mute.set_state(self.audio_manager.is_muted())

    def show_feedback(self, msg):
        self.feedback_message = msg
        self.feedback_time = pygame.time.get_ticks()

    # ------------------------------------------------------------------ focus
    def _focus_items(self):
        if self.active_tab == self.TAB_AUDIO:
            return [self.slider_master, self.slider_music, self.slider_sfx, self.toggle_mute, "test", "reset"]
        if self.active_tab == self.TAB_GAMEPLAY:
            return [self.toggle_screen_shake, self.toggle_speedometer, self.toggle_warnings]
        return []

    def _set_tab(self, index):
        self.active_tab = index % len(self.TAB_NAMES)
        self.focus_index = 0
        self.audio_manager.play_sfx("ui_click")
        return "tab_changed"

    def _do_test_sfx(self):
        self.audio_manager.play_sfx("laser_player")
        self.show_feedback("Playing Test Laser Sound")

    def _do_reset_audio(self):
        self.audio_manager.set_master_volume(0.8)
        self.audio_manager.set_music_volume(0.6)
        self.audio_manager.set_sfx_volume(0.8)
        self.audio_manager.set_mute(False)
        self.sync_from_manager()
        self.audio_manager.play_sfx("ui_click")
        self.show_feedback("Audio settings reset to default")

    def _handle_focus_key(self, key):
        items = self._focus_items()
        if not items:
            return
        self.focus_index %= len(items)
        item = items[self.focus_index]
        if key == pygame.K_UP:
            self.focus_index = (self.focus_index - 1) % len(items)
            self.audio_manager.play_sfx("ui_hover")
        elif key == pygame.K_DOWN:
            self.focus_index = (self.focus_index + 1) % len(items)
            self.audio_manager.play_sfx("ui_hover")
        elif key in (pygame.K_MINUS, pygame.K_KP_MINUS) and isinstance(item, SliderWidget):
            item.adjust(-1)
        elif key in (pygame.K_PLUS, pygame.K_EQUALS, pygame.K_KP_PLUS) and isinstance(item, SliderWidget):
            item.adjust(1)
        elif key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            if isinstance(item, ToggleWidget):
                item.toggle()
                self.audio_manager.play_sfx("ui_click")
            elif item == "test":
                self._do_test_sfx()
            elif item == "reset":
                self._do_reset_audio()

    # ----------------------------------------------------------------- events
    def handle_event(self, event, mouse_pos=None):
        """
        Processes events for the settings menu.
        Returns:
            "close": Return to previous screen.
            "tab_changed": Switched active tab.
            None: Otherwise.
        """
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if mouse_pos:
                if self.close_btn_rect.collidepoint(mouse_pos):
                    self.audio_manager.play_sfx("ui_click")
                    return "close"

                for i, rect in enumerate(self.tab_rects):
                    if rect.collidepoint(mouse_pos):
                        if self.active_tab != i:
                            return self._set_tab(i)

        if self.active_tab == self.TAB_AUDIO:
            self.slider_master.handle_event(event, mouse_pos)
            self.slider_music.handle_event(event, mouse_pos)
            self.slider_sfx.handle_event(event, mouse_pos)
            if self.toggle_mute.handle_event(event, mouse_pos):
                self.audio_manager.play_sfx("ui_click")

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and mouse_pos:
                if self.test_sfx_rect.collidepoint(mouse_pos):
                    self._do_test_sfx()
                elif self.reset_audio_rect.collidepoint(mouse_pos):
                    self._do_reset_audio()

        elif self.active_tab == self.TAB_GAMEPLAY:
            if self.toggle_screen_shake.handle_event(event, mouse_pos):
                self.audio_manager.play_sfx("ui_click")
            if self.toggle_speedometer.handle_event(event, mouse_pos):
                self.audio_manager.play_sfx("ui_click")
            if self.toggle_warnings.handle_event(event, mouse_pos):
                self.audio_manager.play_sfx("ui_click")

        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_ESCAPE, pygame.K_o, pygame.K_p):
                self.audio_manager.play_sfx("ui_click")
                return "close"
            elif event.key == pygame.K_1:
                return self._set_tab(self.TAB_AUDIO)
            elif event.key == pygame.K_2:
                return self._set_tab(self.TAB_GAMEPLAY)
            elif event.key == pygame.K_3:
                return self._set_tab(self.TAB_CONTROLS)
            elif event.key == pygame.K_RIGHT:
                return self._set_tab(self.active_tab + 1)
            elif event.key == pygame.K_LEFT:
                return self._set_tab(self.active_tab - 1)
            elif event.key == pygame.K_TAB:
                step = -1 if (event.mod & pygame.KMOD_SHIFT) else 1
                return self._set_tab(self.active_tab + step)
            elif event.key == pygame.K_m:
                is_muted = self.audio_manager.toggle_mute()
                self.toggle_mute.set_state(is_muted)
                self.audio_manager.play_sfx("ui_click")
                self.show_feedback(f"Audio {'MUTED' if is_muted else 'UNMUTED'}")
            else:
                self._handle_focus_key(event.key)

        return None

    # ------------------------------------------------------------------- draw
    def draw(self, surface, mouse_pos=None):
        surface.blit(self._overlay, (0, 0))
        if not self._fonts_ready:
            return

        widgets.draw_panel(surface, self.panel_rect)

        for i, (name, rect) in enumerate(zip(self.TAB_NAMES, self.tab_rects)):
            is_active = (i == self.active_tab)
            is_hover = rect.collidepoint(mouse_pos) if mouse_pos else False
            bg_color = COLOR_TAB_ACTIVE_BG if is_active else (COLOR_TAB_HOVER_BG if is_hover else COLOR_TAB_INACTIVE_BG)
            widgets.draw_panel(surface, rect, bg_color, COLOR_PANEL_BORDER, brackets=False)
            if is_active:
                pygame.draw.rect(surface, theme.ACCENT, (rect.x, rect.bottom - 3, rect.w, 3))
            txt_color = COLOR_TEXT_WHITE if is_active else (theme.ACCENT if is_hover else COLOR_TEXT_MUTED)
            label = widgets.fit_text(self.font_label, name.upper(), rect.w - 16)
            txt_surf = _TEXT_CACHE.render(self.font_label, label, txt_color)
            surface.blit(txt_surf, txt_surf.get_rect(center=rect.center))

        close_hover = self.close_btn_rect.collidepoint(mouse_pos) if mouse_pos else False
        widgets.draw_panel(
            surface, self.close_btn_rect,
            COLOR_TAB_HOVER_BG if close_hover else COLOR_TAB_INACTIVE_BG,
            theme.DANGER if close_hover else COLOR_PANEL_BORDER,
            brackets=False,
        )
        close_surf = _TEXT_CACHE.render(self.font_label, "BACK [ESC]", COLOR_TEXT_WHITE)
        surface.blit(close_surf, close_surf.get_rect(center=self.close_btn_rect.center))

        if self.active_tab == self.TAB_AUDIO:
            self._draw_audio_tab(surface, mouse_pos)
        elif self.active_tab == self.TAB_GAMEPLAY:
            self._draw_gameplay_tab(surface, mouse_pos)
        elif self.active_tab == self.TAB_CONTROLS:
            self._draw_controls_tab(surface, mouse_pos)

        if self.feedback_message and (pygame.time.get_ticks() - self.feedback_time < 2200):
            toast_surf = _TEXT_CACHE.render(self.font_label, self.feedback_message.upper(), COLOR_TEXT_ACCENT)
            toast_rect = toast_surf.get_rect(center=(self.width // 2, self.height - 45))
            widgets.draw_panel(surface, toast_rect.inflate(24, 12), theme.PANEL, COLOR_TEXT_ACCENT, brackets=False)
            surface.blit(toast_surf, toast_rect)

    def _draw_header(self, surface, title, desc):
        surface.blit(_TEXT_CACHE.render(self.font_title, title, COLOR_TEXT_ACCENT), (90, 96))
        surface.blit(_TEXT_CACHE.render(self.font_body, desc, COLOR_TEXT_MUTED), (90, 134))

    def _is_focused(self, item):
        items = self._focus_items()
        return bool(items) and items[self.focus_index % len(items)] is item

    def _draw_button(self, surface, rect, text, mouse_pos, color, focused):
        hover = rect.collidepoint(mouse_pos) if mouse_pos else False
        widgets.draw_panel(
            surface, rect,
            COLOR_TAB_HOVER_BG if (hover or focused) else COLOR_TAB_INACTIVE_BG,
            color if (hover or focused) else COLOR_PANEL_BORDER,
            brackets=False,
        )
        if focused:
            widgets.draw_focus_bar(surface, rect)
        txt = _TEXT_CACHE.render(self.font_label, text, color if color != COLOR_PANEL_BORDER else COLOR_TEXT_WHITE)
        surface.blit(txt, txt.get_rect(center=rect.center))

    def _draw_info_card(self, surface, rect, title, blocks, with_bullets):
        widgets.draw_panel(surface, rect, theme.PANEL, COLOR_PANEL_BORDER, theme.ACCENT_DIM)
        surface.blit(_TEXT_CACHE.render(self.font_subtitle, title, COLOR_TEXT_GOLD), (rect.x + 24, rect.y + 20))
        step = self.font_body.get_linesize()
        by = rect.y + 60
        for b_title, lines in blocks:
            if with_bullets:
                pygame.draw.rect(surface, COLOR_TEXT_ACCENT, (rect.x + 26, by + 6, 8, 8))
            t_surf = _TEXT_CACHE.render(self.font_label, b_title.upper(), COLOR_TEXT_WHITE)
            surface.blit(t_surf, (rect.x + 44, by))
            ly = by + t_surf.get_height() + 2
            for line in lines:
                surface.blit(_TEXT_CACHE.render(self.font_body, line, COLOR_TEXT_MUTED), (rect.x + 44, ly))
                ly += step
            by = ly + 12

    def _draw_audio_tab(self, surface, mouse_pos):
        self._draw_header(
            surface, "AUDIO CONFIGURATION",
            "Adjust master output, dynamic background music, and tactical sound effects.",
        )
        for item in (self.slider_master, self.slider_music, self.slider_sfx):
            item.draw(surface, mouse_pos, self.font_label, self.font_val, focused=self._is_focused(item))
        self.toggle_mute.draw(
            surface, mouse_pos, self.font_label, self.font_val, focused=self._is_focused(self.toggle_mute)
        )
        items = self._focus_items()
        focused = items[self.focus_index % len(items)]
        self._draw_button(surface, self.test_sfx_rect, "TEST SOUND (SFX)", mouse_pos, COLOR_TEXT_ACCENT, focused == "test")
        self._draw_button(surface, self.reset_audio_rect, "RESET DEFAULTS", mouse_pos, COLOR_TEXT_GOLD, focused == "reset")
        self._draw_info_card(
            surface, pygame.Rect(630, 160, 560, 390), "AUDIO ENGINE FEATURES", self._audio_bullets, True
        )

    def _draw_gameplay_tab(self, surface, mouse_pos):
        self._draw_header(
            surface, "GAMEPLAY & HUD PREFERENCES",
            "Configure display feedback, HUD telemetry, and accessibility options.",
        )
        for item in (self.toggle_screen_shake, self.toggle_speedometer, self.toggle_warnings):
            item.draw(surface, mouse_pos, self.font_label, self.font_val, focused=self._is_focused(item))
        self._draw_info_card(
            surface, pygame.Rect(650, 165, 540, 380), "WHAT THESE OPTIONS DO", self._gameplay_info, True
        )

    def _draw_controls_tab(self, surface, mouse_pos):
        self._draw_header(
            surface, "FLIGHT CONTROLS & KEYBINDINGS",
            "Primary flight, targeting, and tactical support keybindings.",
        )
        start_x = 90
        start_y = 175
        row_h = 28
        step = 32
        col_w = self._controls_col_w
        key_w = self._controls_key_w
        for col, rows in enumerate(self._controls_rows):
            rx = start_x + col * (col_w + 30)
            ry = start_y
            for entry in rows:
                if entry[0] == "header":
                    surface.blit(_TEXT_CACHE.render(self.font_label, entry[1], theme.ACCENT), (rx, ry + 4))
                else:
                    box_rect = pygame.Rect(rx, ry, col_w, row_h)
                    widgets.draw_panel(surface, box_rect, COLOR_PANEL_BG, COLOR_PANEL_BORDER, brackets=False)
                    key_surf = _TEXT_CACHE.render(self.font_val, entry[1], COLOR_TEXT_ACCENT)
                    action_surf = _TEXT_CACHE.render(self.font_body, entry[2], COLOR_TEXT_WHITE)
                    surface.blit(key_surf, (rx + 12, ry + (row_h - key_surf.get_height()) // 2))
                    surface.blit(action_surf, (rx + key_w, ry + (row_h - action_surf.get_height()) // 2))
                ry += step
