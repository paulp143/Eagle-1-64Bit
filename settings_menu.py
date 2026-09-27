"""
settings_menu.py - Extensible Settings & Configuration Menu for Eagle-1-64Bit

Provides a modular, tabbed Settings menu featuring:
- Audio tab: Master, Music, SFX volume sliders, Mute toggle, and SFX test.
- Gameplay tab: Screen shake, speedometer, alert notifications.
- Controls tab: Keybindings summary and input sensitivity.
Designed to be easily extended with future categories and settings options.
"""

import pygame
from audio_manager import get_audio_manager

# Color Palette matching sci-fi UI theme
COLOR_BG_OVERLAY = (10, 14, 22, 245)
COLOR_PANEL_BG = (18, 24, 38)
COLOR_PANEL_BORDER = (45, 65, 95)
COLOR_TEXT_WHITE = (245, 245, 250)
COLOR_TEXT_MUTED = (160, 175, 200)
COLOR_TEXT_ACCENT = (0, 210, 255)       # Cyber Cyan
COLOR_TEXT_GOLD = (255, 195, 50)        # Accent Gold
COLOR_TEXT_GREEN = (46, 204, 113)       # Enabled Green
COLOR_TEXT_RED = (255, 75, 75)          # Muted/Disabled Red

COLOR_TAB_INACTIVE_BG = (22, 30, 48)
COLOR_TAB_INACTIVE_BORDER = (50, 70, 105)
COLOR_TAB_HOVER_BG = (35, 50, 80)
COLOR_TAB_ACTIVE_BG = (0, 120, 180)
COLOR_TAB_ACTIVE_BORDER = (0, 220, 255)

COLOR_SLIDER_BG = (30, 40, 60)
COLOR_SLIDER_FILL = (0, 180, 230)
COLOR_SLIDER_KNOB = (220, 245, 255)
COLOR_SLIDER_KNOB_HOVER = (0, 240, 255)


class SliderWidget:
    """Interactive horizontal slider widget supporting mouse drag and step adjustments."""

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

    def draw(self, surface, mouse_pos, font_label, font_val):
        knob_pos = self.get_knob_center()
        is_hovered = self.rect.inflate(20, 20).collidepoint(mouse_pos) if mouse_pos else False

        # 1. Label and Value text
        label_surf = font_label.render(self.label, True, COLOR_TEXT_WHITE)
        val_text = self.format_fn(self.value)
        val_surf = font_val.render(val_text, True, COLOR_TEXT_ACCENT if (is_hovered or self.dragging) else COLOR_TEXT_MUTED)

        surface.blit(label_surf, (self.rect.x, self.rect.y - 24))
        surface.blit(val_surf, (self.rect.right - val_surf.get_width(), self.rect.y - 24))

        # 2. Slider Track
        track_h = 8
        track_rect = pygame.Rect(self.rect.x, self.rect.centery - track_h // 2, self.rect.width, track_h)
        pygame.draw.rect(surface, COLOR_SLIDER_BG, track_rect, border_radius=4)
        pygame.draw.rect(surface, COLOR_PANEL_BORDER, track_rect, width=1, border_radius=4)

        # 3. Fill bar
        fill_w = max(0, knob_pos[0] - self.rect.x)
        if fill_w > 0:
            fill_rect = pygame.Rect(self.rect.x, self.rect.centery - track_h // 2, fill_w, track_h)
            pygame.draw.rect(surface, COLOR_SLIDER_FILL, fill_rect, border_radius=4)

        # 4. Draggable Knob
        knob_color = COLOR_SLIDER_KNOB_HOVER if (is_hovered or self.dragging) else COLOR_SLIDER_KNOB
        pygame.draw.circle(surface, knob_color, knob_pos, self.knob_radius)
        pygame.draw.circle(surface, (20, 35, 60), knob_pos, self.knob_radius, width=2)


class ToggleWidget:
    """Interactive toggle switch / checkbox widget."""

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

    def draw(self, surface, mouse_pos, font_label, font_status):
        is_hovered = self.rect.collidepoint(mouse_pos) if mouse_pos else False

        # Outer card/button
        bg_color = COLOR_TAB_HOVER_BG if is_hovered else COLOR_PANEL_BG
        border_color = COLOR_TEXT_ACCENT if is_hovered else COLOR_PANEL_BORDER
        pygame.draw.rect(surface, bg_color, self.rect, border_radius=8)
        pygame.draw.rect(surface, border_color, self.rect, width=1, border_radius=8)

        # Label text
        label_surf = font_label.render(self.label, True, COLOR_TEXT_WHITE)
        surface.blit(label_surf, (self.rect.x + 18, self.rect.centery - label_surf.get_height() // 2))

        # Switch pill on right
        switch_w = 56
        switch_h = 26
        switch_x = self.rect.right - switch_w - 18
        switch_y = self.rect.centery - switch_h // 2
        switch_rect = pygame.Rect(switch_x, switch_y, switch_w, switch_h)

        pill_color = (30, 80, 50) if self.state else (50, 30, 35)
        pill_border = COLOR_TEXT_GREEN if self.state else COLOR_TEXT_RED
        pygame.draw.rect(surface, pill_color, switch_rect, border_radius=13)
        pygame.draw.rect(surface, pill_border, switch_rect, width=1, border_radius=13)

        # Knob inside pill
        knob_r = 10
        knob_cx = switch_x + switch_w - knob_r - 3 if self.state else switch_x + knob_r + 3
        knob_cy = switch_y + switch_h // 2
        pygame.draw.circle(surface, COLOR_TEXT_WHITE, (knob_cx, knob_cy), knob_r)

        # Text inside pill
        status_txt = "ON" if self.state else "OFF"
        status_color = COLOR_TEXT_GREEN if self.state else COLOR_TEXT_RED
        txt_surf = font_status.render(status_txt, True, status_color)
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

    def __init__(self, width=1280, height=720):
        self.width = width
        self.height = height
        self.active_tab = self.TAB_AUDIO
        self.audio_manager = get_audio_manager()

        if not pygame.font.get_init():
            pygame.font.init()

        self.font_title = pygame.font.SysFont("arial", 28, bold=True)
        self.font_subtitle = pygame.font.SysFont("arial", 18, bold=True)
        self.font_label = pygame.font.SysFont("arial", 15, bold=True)
        self.font_body = pygame.font.SysFont("arial", 13, bold=False)
        self.font_val = pygame.font.SysFont("arial", 14, bold=True)
        self.font_tag = pygame.font.SysFont("arial", 11, bold=True)

        # Tab button rectangles
        self.tab_rects = []
        self._init_tab_rects()

        # Close button rect (top right)
        self.close_btn_rect = pygame.Rect(self.width - 150, 20, 120, 36)

        # Main content panel
        self.panel_rect = pygame.Rect(40, 72, self.width - 80, self.height - 96)

        # Initialize Audio Tab Widgets
        self._init_audio_widgets()

        # Initialize Gameplay Tab Widgets
        self._init_gameplay_widgets()

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

        # Master Volume Slider
        self.slider_master = SliderWidget(
            slider_x, start_y, slider_w, slider_h,
            label="Master Volume",
            initial_val=self.audio_manager.get_master_volume(),
            on_change=lambda val: self.audio_manager.set_master_volume(val)
        )

        # Music Volume Slider
        self.slider_music = SliderWidget(
            slider_x, start_y + spacing_y, slider_w, slider_h,
            label="Music Volume",
            initial_val=self.audio_manager.get_music_volume(),
            on_change=lambda val: self.audio_manager.set_music_volume(val)
        )

        # SFX Volume Slider
        self.slider_sfx = SliderWidget(
            slider_x, start_y + spacing_y * 2, slider_w, slider_h,
            label="SFX Volume",
            initial_val=self.audio_manager.get_sfx_volume(),
            on_change=lambda val: self.audio_manager.set_sfx_volume(val)
        )

        # Mute Audio Toggle
        self.toggle_mute = ToggleWidget(
            slider_x, start_y + spacing_y * 3 + 10, slider_w, 48,
            label="Mute Audio Output (M)",
            initial_state=self.audio_manager.is_muted(),
            on_toggle=lambda state: self.audio_manager.set_mute(state)
        )

        # Test SFX Button
        self.test_sfx_rect = pygame.Rect(slider_x, start_y + spacing_y * 4 + 16, 210, 40)

        # Reset Defaults Button
        self.reset_audio_rect = pygame.Rect(slider_x + 230, start_y + spacing_y * 4 + 16, 230, 40)

    def _init_gameplay_widgets(self):
        gx = 90
        gy = 165
        gw = 520
        gh = 48
        spacing = 60

        self.toggle_screen_shake = ToggleWidget(
            gx, gy, gw, gh,
            label="Tactical Screen Shake",
            initial_state=True
        )

        self.toggle_speedometer = ToggleWidget(
            gx, gy + spacing, gw, gh,
            label="Display Speedometer HUD",
            initial_state=True
        )

        self.toggle_warnings = ToggleWidget(
            gx, gy + spacing * 2, gw, gh,
            label="Boundary & Missile Warning Alerts",
            initial_state=True
        )

    def sync_from_manager(self):
        """Synchronizes widget values with current AudioManager settings."""
        self.slider_master.set_value(self.audio_manager.get_master_volume())
        self.slider_music.set_value(self.audio_manager.get_music_volume())
        self.slider_sfx.set_value(self.audio_manager.get_sfx_volume())
        self.toggle_mute.set_state(self.audio_manager.is_muted())

    def show_feedback(self, msg):
        self.feedback_message = msg
        self.feedback_time = pygame.time.get_ticks()

    def handle_event(self, event, mouse_pos=None):
        """
        Processes events for the settings menu.
        Returns:
            "close": Return to previous screen.
            "tab_changed": Switched active tab.
            None: Otherwise.
        """
        # Mouse Click handling
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if mouse_pos:
                # Check Close button
                if self.close_btn_rect.collidepoint(mouse_pos):
                    self.audio_manager.play_sfx("ui_click")
                    return "close"

                # Check Tab buttons
                for i, rect in enumerate(self.tab_rects):
                    if rect.collidepoint(mouse_pos):
                        if self.active_tab != i:
                            self.active_tab = i
                            self.audio_manager.play_sfx("ui_click")
                            return "tab_changed"

        # Tab Specific Event Processing
        if self.active_tab == self.TAB_AUDIO:
            self.slider_master.handle_event(event, mouse_pos)
            self.slider_music.handle_event(event, mouse_pos)
            self.slider_sfx.handle_event(event, mouse_pos)
            if self.toggle_mute.handle_event(event, mouse_pos):
                self.audio_manager.play_sfx("ui_click")

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and mouse_pos:
                if self.test_sfx_rect.collidepoint(mouse_pos):
                    self.audio_manager.play_sfx("laser_player")
                    self.show_feedback("Playing Test Laser Sound")
                elif self.reset_audio_rect.collidepoint(mouse_pos):
                    self.audio_manager.set_master_volume(0.8)
                    self.audio_manager.set_music_volume(0.6)
                    self.audio_manager.set_sfx_volume(0.8)
                    self.audio_manager.set_mute(False)
                    self.sync_from_manager()
                    self.audio_manager.play_sfx("ui_click")
                    self.show_feedback("Audio settings reset to default")

        elif self.active_tab == self.TAB_GAMEPLAY:
            if self.toggle_screen_shake.handle_event(event, mouse_pos):
                self.audio_manager.play_sfx("ui_click")
            if self.toggle_speedometer.handle_event(event, mouse_pos):
                self.audio_manager.play_sfx("ui_click")
            if self.toggle_warnings.handle_event(event, mouse_pos):
                self.audio_manager.play_sfx("ui_click")

        # Global Hotkeys within Settings Menu
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_ESCAPE, pygame.K_o, pygame.K_p):
                self.audio_manager.play_sfx("ui_click")
                return "close"
            elif event.key == pygame.K_1:
                self.active_tab = self.TAB_AUDIO
                self.audio_manager.play_sfx("ui_click")
                return "tab_changed"
            elif event.key == pygame.K_2:
                self.active_tab = self.TAB_GAMEPLAY
                self.audio_manager.play_sfx("ui_click")
                return "tab_changed"
            elif event.key == pygame.K_3:
                self.active_tab = self.TAB_CONTROLS
                self.audio_manager.play_sfx("ui_click")
                return "tab_changed"
            elif event.key == pygame.K_m:
                is_muted = self.audio_manager.toggle_mute()
                self.toggle_mute.set_state(is_muted)
                self.audio_manager.play_sfx("ui_click")
                self.show_feedback(f"Audio {'MUTED' if is_muted else 'UNMUTED'}")

        return None

    def draw(self, surface, mouse_pos=None):
        # 1. Dark semi-transparent backdrop overlay
        overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        overlay.fill(COLOR_BG_OVERLAY)
        surface.blit(overlay, (0, 0))

        # 2. Main content container panel
        pygame.draw.rect(surface, COLOR_PANEL_BG, self.panel_rect, border_radius=10)
        pygame.draw.rect(surface, COLOR_PANEL_BORDER, self.panel_rect, width=2, border_radius=10)

        # 3. Draw Tab Buttons across the header
        for i, (name, rect) in enumerate(zip(self.TAB_NAMES, self.tab_rects)):
            is_active = (i == self.active_tab)
            is_hover = rect.collidepoint(mouse_pos) if mouse_pos else False

            bg_color = COLOR_TAB_ACTIVE_BG if is_active else (COLOR_TAB_HOVER_BG if is_hover else COLOR_TAB_INACTIVE_BG)
            border_color = COLOR_TAB_ACTIVE_BORDER if is_active else (COLOR_TEXT_ACCENT if is_hover else COLOR_TAB_INACTIVE_BORDER)

            pygame.draw.rect(surface, bg_color, rect, border_radius=6)
            pygame.draw.rect(surface, border_color, rect, width=2 if is_active else 1, border_radius=6)

            txt_color = COLOR_TEXT_WHITE if is_active else (COLOR_TEXT_ACCENT if is_hover else COLOR_TEXT_MUTED)
            txt_surf = self.font_label.render(name, True, txt_color)
            surface.blit(txt_surf, (rect.centerx - txt_surf.get_width() // 2, rect.centery - txt_surf.get_height() // 2))

        # 4. Close Button [ESC]
        close_hover = self.close_btn_rect.collidepoint(mouse_pos) if mouse_pos else False
        close_bg = (160, 40, 40) if close_hover else (60, 25, 30)
        close_border = COLOR_TEXT_RED if close_hover else (120, 50, 60)
        pygame.draw.rect(surface, close_bg, self.close_btn_rect, border_radius=6)
        pygame.draw.rect(surface, close_border, self.close_btn_rect, width=1, border_radius=6)
        close_surf = self.font_label.render("Back [ESC]", True, COLOR_TEXT_WHITE)
        surface.blit(close_surf, (self.close_btn_rect.centerx - close_surf.get_width() // 2, self.close_btn_rect.centery - close_surf.get_height() // 2))

        # 5. Draw Content based on Active Tab
        if self.active_tab == self.TAB_AUDIO:
            self._draw_audio_tab(surface, mouse_pos)
        elif self.active_tab == self.TAB_GAMEPLAY:
            self._draw_gameplay_tab(surface, mouse_pos)
        elif self.active_tab == self.TAB_CONTROLS:
            self._draw_controls_tab(surface, mouse_pos)

        # 6. Feedback Toast Message
        if self.feedback_message and (pygame.time.get_ticks() - self.feedback_time < 2200):
            toast_surf = self.font_label.render(self.feedback_message, True, COLOR_TEXT_ACCENT)
            toast_rect = toast_surf.get_rect(center=(self.width // 2, self.height - 45))
            pad_rect = toast_rect.inflate(24, 12)
            pygame.draw.rect(surface, (12, 20, 32), pad_rect, border_radius=6)
            pygame.draw.rect(surface, COLOR_TEXT_ACCENT, pad_rect, width=1, border_radius=6)
            surface.blit(toast_surf, toast_rect)

    def _draw_audio_tab(self, surface, mouse_pos):
        # Section Title & Description
        title_surf = self.font_title.render("AUDIO CONFIGURATION", True, COLOR_TEXT_ACCENT)
        desc_surf = self.font_body.render("Adjust master output, dynamic background music, and tactical sound effects.", True, COLOR_TEXT_MUTED)
        surface.blit(title_surf, (90, 100))
        surface.blit(desc_surf, (90, 136))

        # Draw Sliders & Mute Toggle
        self.slider_master.draw(surface, mouse_pos, self.font_label, self.font_val)
        self.slider_music.draw(surface, mouse_pos, self.font_label, self.font_val)
        self.slider_sfx.draw(surface, mouse_pos, self.font_label, self.font_val)
        self.toggle_mute.draw(surface, mouse_pos, self.font_label, self.font_val)

        # Test SFX Button
        t_hover = self.test_sfx_rect.collidepoint(mouse_pos) if mouse_pos else False
        t_bg = (0, 100, 150) if t_hover else (15, 45, 75)
        t_border = COLOR_TEXT_ACCENT if t_hover else COLOR_PANEL_BORDER
        pygame.draw.rect(surface, t_bg, self.test_sfx_rect, border_radius=6)
        pygame.draw.rect(surface, t_border, self.test_sfx_rect, width=1, border_radius=6)
        t_txt = self.font_label.render("TEST SOUND (SFX)", True, COLOR_TEXT_WHITE)
        surface.blit(t_txt, (self.test_sfx_rect.centerx - t_txt.get_width() // 2, self.test_sfx_rect.centery - t_txt.get_height() // 2))

        # Reset Audio Defaults Button
        r_hover = self.reset_audio_rect.collidepoint(mouse_pos) if mouse_pos else False
        r_bg = (70, 50, 20) if r_hover else (40, 30, 15)
        r_border = COLOR_TEXT_GOLD if r_hover else COLOR_PANEL_BORDER
        pygame.draw.rect(surface, r_bg, self.reset_audio_rect, border_radius=6)
        pygame.draw.rect(surface, r_border, self.reset_audio_rect, width=1, border_radius=6)
        r_txt = self.font_label.render("RESET DEFAULTS", True, COLOR_TEXT_GOLD)
        surface.blit(r_txt, (self.reset_audio_rect.centerx - r_txt.get_width() // 2, self.reset_audio_rect.centery - r_txt.get_height() // 2))

        # Right Side Information / Info Card
        card_rect = pygame.Rect(630, 160, 560, 390)
        pygame.draw.rect(surface, (14, 20, 32), card_rect, border_radius=8)
        pygame.draw.rect(surface, COLOR_PANEL_BORDER, card_rect, width=1, border_radius=8)

        card_title = self.font_subtitle.render("AUDIO ENGINE FEATURES", True, COLOR_TEXT_GOLD)
        surface.blit(card_title, (card_rect.x + 24, card_rect.y + 20))

        bullet_points = [
            ("Centralized 16-Channel Mixer", "Allocates dedicated low-latency voices for weapons, alarms, engine & UI."),
            ("Voice Limiting & Anti-Clipping", "Prevents volume stacking and audio distortion during intense bullet swarms."),
            ("Dynamic Combat Music Intensity", "Smoothly transitions between ambient and high-threat themes during combat."),
            ("Velocity-Modulated Engine Hum", "Jet thruster pitch and volume adjust continuously with your flight speed."),
            ("Persistent Configuration", "Volume levels and mute preferences are saved automatically to data storage."),
            ("Instant Mute Shortcut", "Press 'M' during gameplay or menus to toggle mute immediately.")
        ]

        by = card_rect.y + 60
        for b_title, b_desc in bullet_points:
            pygame.draw.circle(surface, COLOR_TEXT_ACCENT, (card_rect.x + 30, by + 8), 4)
            t_surf = self.font_label.render(b_title, True, COLOR_TEXT_WHITE)
            surface.blit(t_surf, (card_rect.x + 44, by))
            d_surf = self.font_body.render(b_desc, True, COLOR_TEXT_MUTED)
            surface.blit(d_surf, (card_rect.x + 44, by + 20))
            by += 48

    def _draw_gameplay_tab(self, surface, mouse_pos):
        title_surf = self.font_title.render("GAMEPLAY & HUD PREFERENCES", True, COLOR_TEXT_ACCENT)
        desc_surf = self.font_body.render("Configure display feedback, HUD telemetry, and accessibility options.", True, COLOR_TEXT_MUTED)
        surface.blit(title_surf, (90, 100))
        surface.blit(desc_surf, (90, 136))

        self.toggle_screen_shake.draw(surface, mouse_pos, self.font_label, self.font_val)
        self.toggle_speedometer.draw(surface, mouse_pos, self.font_label, self.font_val)
        self.toggle_warnings.draw(surface, mouse_pos, self.font_label, self.font_val)

        # Right Side Info Box
        card_rect = pygame.Rect(650, 165, 540, 380)
        pygame.draw.rect(surface, (14, 20, 32), card_rect, border_radius=8)
        pygame.draw.rect(surface, COLOR_PANEL_BORDER, card_rect, width=1, border_radius=8)

        card_title = self.font_subtitle.render("FUTURE SETTINGS MODULES", True, COLOR_TEXT_GOLD)
        surface.blit(card_title, (card_rect.x + 24, card_rect.y + 20))

        info_lines = [
            "This settings architecture is designed for effortless future extension.",
            "Developers can register new setting options, sliders, and toggles by simply",
            "adding widgets to this menu.",
            "",
            "Planned future additions:",
            "- Graphics Quality & Particle Density",
            "- Minimap Scale & Transparency",
            "- Custom Crosshair Colors",
            "- Full Key Rebinding System",
        ]
        iy = card_rect.y + 60
        for line in info_lines:
            color = COLOR_TEXT_ACCENT if line.startswith("-") else COLOR_TEXT_MUTED
            surf = self.font_body.render(line, True, color)
            surface.blit(surf, (card_rect.x + 24, iy))
            iy += 24

    def _draw_controls_tab(self, surface, mouse_pos):
        title_surf = self.font_title.render("FLIGHT CONTROLS & KEYBINDINGS", True, COLOR_TEXT_ACCENT)
        desc_surf = self.font_body.render("Primary flight, targeting, and tactical support keybindings.", True, COLOR_TEXT_MUTED)
        surface.blit(title_surf, (90, 100))
        surface.blit(desc_surf, (90, 136))

        controls_list = [
            ("W / S (or Up / Down)", "Thrust Acceleration / Deceleration"),
            ("A / D (or Left / Right)", "Turn Heading Left / Right"),
            ("SPACE / Left Click", "Fire Primary Cannons"),
            ("E / F / Right Click", "Launch Homing Rocket"),
            ("Q", "Toggle Radar Mode (CONE / OMNI)"),
            ("1 - 5 / Mouse Wheel", "Cycle Equipped Weapon / Stratagem"),
            ("V / TAB", "Open Stratagem Tactical Wheel"),
            ("C / X", "Quick Deploy Air Strike / Supply Pod"),
            ("P", "Pause Game"),
            ("H", "Open In-Game Help Manual"),
            ("O", "Open Settings & Audio Menu"),
            ("M", "Instant Mute / Unmute Audio"),
        ]

        start_x = 90
        start_y = 175
        col_w = 540
        row_h = 36

        for i, (key, action) in enumerate(controls_list):
            col = i // 6
            row = i % 6
            rx = start_x + col * (col_w + 30)
            ry = start_y + row * (row_h + 12)

            box_rect = pygame.Rect(rx, ry, col_w, row_h)
            pygame.draw.rect(surface, COLOR_PANEL_BG, box_rect, border_radius=6)
            pygame.draw.rect(surface, COLOR_PANEL_BORDER, box_rect, width=1, border_radius=6)

            key_surf = self.font_label.render(key, True, COLOR_TEXT_ACCENT)
            action_surf = self.font_body.render(action, True, COLOR_TEXT_WHITE)

            surface.blit(key_surf, (rx + 16, ry + (row_h - key_surf.get_height()) // 2))
            surface.blit(action_surf, (rx + 220, ry + (row_h - action_surf.get_height()) // 2))
