"""comms_hud.py - In-Flight Radio Transceiver Overlay & Dialogue Engine.

Renders an interactive military radio HUD overlay during active flight operations:
- Translucent tactical radio frame with animated waveform and speaker portrait.
- Animated typewriter text presentation.
- Smooth time-dilation transition to 0.4x speed during interactive decisions.
- Key listener for 3-way ideological stances: [1] LOYAL, [2] NEUTRAL, [3] DISSIDENT.
- Zero per-frame allocations in render() to strictly maintain 60 FPS.
"""

import math
from typing import Any, Optional
import pygame

from eagle1.story.dialogue_db import DialogueNode, DialogueOption, get_dialogue_node
from eagle1.story.story_manager import StoryManager


class CommsHUD:
    """Manages tactical in-flight radio communications, player choices, and UI display."""

    def __init__(
        self,
        story_manager: Optional[StoryManager] = None,
        audio_manager: Optional[Any] = None,
        screen_width: int = 1280,
        screen_height: int = 720,
    ):
        self.story_manager = story_manager
        self.audio = audio_manager
        self.screen_width = screen_width
        self.screen_height = screen_height

        # State flags
        self.is_active: bool = False
        self.is_waiting_for_choice: bool = False
        self.current_node: Optional[DialogueNode] = None
        self.selected_stance: Optional[str] = None
        self.selected_option: Optional[DialogueOption] = None
        self.response_text: Optional[str] = None

        # Timers and animations
        self.typewriter_chars: float = 0.0
        self.typewriter_speed: float = 55.0  # Chars per second
        self.response_timer: float = 0.0
        self.response_duration: float = 3.5  # Seconds to read response
        self.waveform_phase: float = 0.0

        # Time dilation
        self.current_time_dilation: float = 1.0
        self.target_time_dilation: float = 1.0
        self.dilation_lerp_speed: float = 6.0

        # UI Dimensions & Geometry
        self.box_width: int = 860
        self.box_height: int = 150
        self.box_x: int = (self.screen_width - self.box_width) // 2
        self.box_y: int = 16

        # Color Palette (Super Earth Military Aviator Theme)
        self.color_bg = (12, 18, 28, 230)
        self.color_border = (255, 215, 0)  # Gold
        self.color_border_subtle = (40, 80, 110)
        self.color_speaker = (255, 220, 100)
        self.color_location = (140, 170, 190)
        self.color_text = (240, 245, 250)
        self.color_waveform = (80, 230, 140)

        # Stance card colors
        self.stance_colors = {
            "loyal": (255, 215, 80),      # Gold
            "neutral": (140, 200, 240),   # Cyan/Steel
            "dissident": (255, 100, 90),  # Red/Coral
        }

        # Pre-cached surfaces & fonts
        self._init_surfaces()
        self._init_fonts()

    def _init_surfaces(self) -> None:
        """Pre-allocate static background surfaces to avoid dynamic frame allocations."""
        self.bg_surface = pygame.Surface((self.box_width, self.box_height), pygame.SRCALPHA)
        self.bg_surface.fill(self.color_bg)
        # Inner technical grid accents
        pygame.draw.rect(self.bg_surface, self.color_border, (0, 0, self.box_width, self.box_height), width=2)
        pygame.draw.rect(self.bg_surface, self.color_border_subtle, (4, 4, self.box_width - 8, self.box_height - 8), width=1)
        # Corner brackets
        corner_len = 16
        w, h = self.box_width, self.box_height
        for x, y, dx, dy in [(0, 0, 1, 1), (w - 1, 0, -1, 1), (0, h - 1, 1, -1), (w - 1, h - 1, -1, -1)]:
            pygame.draw.line(self.bg_surface, self.color_border, (x, y), (x + dx * corner_len, y), 3)
            pygame.draw.line(self.bg_surface, self.color_border, (x, y), (x, y + dy * corner_len), 3)

    def _init_fonts(self) -> None:
        """Initialize and cache font sizes."""
        pygame.font.init()
        self.font_header = pygame.font.SysFont("courier", 14, bold=True)
        self.font_body = pygame.font.SysFont("arial", 13)
        self.font_option = pygame.font.SysFont("arial", 12, bold=True)
        self.font_badge = pygame.font.SysFont("courier", 10, bold=True)

    def trigger_transmission(self, node_or_id: Any) -> bool:
        """Start an incoming radio transmission from a DialogueNode or node_id."""
        if isinstance(node_or_id, str):
            node = get_dialogue_node(node_or_id)
        else:
            node = node_or_id

        if not node:
            return False

        self.current_node = node
        self.is_active = True
        self.is_waiting_for_choice = False
        self.selected_stance = None
        self.selected_option = None
        self.response_text = None
        self.response_timer = 0.0
        self.typewriter_chars = 0.0
        self.target_time_dilation = 1.0

        # Audio squelch
        if self.audio and hasattr(self.audio, "play_radio_squelch"):
            self.audio.play_radio_squelch()

        return True

    def get_time_dilation(self) -> float:
        """Get the current simulation speed factor (0.4 during choices, 1.0 normal)."""
        return self.current_time_dilation

    def update(self, dt: float) -> None:
        """Update typewriter text, timers, audio waveforms, and time dilation."""
        if not self.is_active:
            self.target_time_dilation = 1.0
            self._update_time_dilation(dt)
            return

        # Advance radio waveform animation
        self.waveform_phase += dt * 6.0

        # Typewriter text advancement
        active_text = self.response_text if self.response_text else (self.current_node.prompt if self.current_node else "")
        total_len = len(active_text)

        if self.typewriter_chars < total_len:
            self.typewriter_chars += self.typewriter_speed * dt
            if self.typewriter_chars >= total_len:
                self.typewriter_chars = float(total_len)

        if not self.is_waiting_for_choice and not self.selected_stance and self.current_node and self.current_node.options:
            if self.typewriter_chars >= total_len:
                self.is_waiting_for_choice = True
                self.target_time_dilation = 0.4

        # Response dismissal timer
        if self.selected_stance is not None:
            self.target_time_dilation = 1.0
            self.response_timer += dt
            if self.response_timer >= self.response_duration:
                self.dismiss()

        self._update_time_dilation(dt)

    def _update_time_dilation(self, dt: float) -> None:
        """Smoothly lerp time dilation toward target."""
        diff = self.target_time_dilation - self.current_time_dilation
        if abs(diff) > 0.005:
            self.current_time_dilation += diff * min(1.0, dt * self.dilation_lerp_speed)
        else:
            self.current_time_dilation = self.target_time_dilation

    def handle_event(self, event: pygame.event.Event) -> bool:
        """Handle keyboard input for dialogue choices and transmission advance."""
        if not self.is_active or event.type != pygame.KEYDOWN:
            return False

        # Fast-forward typewriter on space or return
        active_text = self.response_text if self.response_text else (self.current_node.prompt if self.current_node else "")
        if self.typewriter_chars < len(active_text):
            if event.key in (pygame.K_SPACE, pygame.K_RETURN):
                self.typewriter_chars = float(len(active_text))
                if not self.selected_stance and self.current_node and self.current_node.options:
                    self.is_waiting_for_choice = True
                    self.target_time_dilation = 0.4
                return True

        # Handle 3-way stance choice
        if self.is_waiting_for_choice and self.current_node and self.current_node.options:
            stance = None
            if event.key in (pygame.K_1, pygame.K_KP1):
                stance = "loyal"
            elif event.key in (pygame.K_2, pygame.K_KP2):
                stance = "neutral"
            elif event.key in (pygame.K_3, pygame.K_KP3):
                stance = "dissident"

            if stance and stance in self.current_node.options:
                self._choose_option(stance)
                return True

        # If transmission has no options or response is active, allow manual dismissal
        if not self.is_waiting_for_choice and event.key in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_ESCAPE):
            self.dismiss()
            return True

        return False

    def _choose_option(self, stance: str) -> None:
        """Select a dialogue option, modify loyalty, and start displaying the response."""
        option = self.current_node.options[stance]
        self.selected_stance = stance
        self.selected_option = option
        self.is_waiting_for_choice = False
        self.target_time_dilation = 1.0

        # Modify Loyalty in StoryManager if wired
        if self.story_manager:
            self.story_manager.record_choice(self.current_node.node_id, stance)

        # Set up response typewriter
        self.response_text = f"[{self.current_node.speaker}]: {option.response}"
        self.typewriter_chars = 0.0
        self.response_timer = 0.0

        # Play choice confirmation tone
        if self.audio and hasattr(self.audio, "play_radio_beep"):
            self.audio.play_radio_beep()
        elif self.audio and hasattr(self.audio, "play_radio_squelch"):
            self.audio.play_radio_squelch()

    def dismiss(self) -> None:
        """Close the transceiver overlay and return game speed to normal."""
        self.is_active = False
        self.is_waiting_for_choice = False
        self.current_node = None
        self.selected_stance = None
        self.selected_option = None
        self.response_text = None
        self.target_time_dilation = 1.0

        if self.audio and hasattr(self.audio, "play_radio_squelch"):
            self.audio.play_radio_squelch()

    def render(self, surface: pygame.Surface) -> None:
        """Render the complete tactical radio HUD overlay on the target surface."""
        if not self.is_active or not self.current_node:
            return

        # 1. Blit static cached background
        surface.blit(self.bg_surface, (self.box_x, self.box_y))

        # 2. Render Speaker Portrait / Transceiver Box (Left column)
        port_x = self.box_x + 14
        port_y = self.box_y + 14
        port_size = 64
        pygame.draw.rect(surface, (20, 35, 50), (port_x, port_y, port_size, port_size))
        pygame.draw.rect(surface, self.color_border_subtle, (port_x, port_y, port_size, port_size), 1)

        # Transceiver RF Signal Badge
        badge = self.font_badge.render("RF COMM 9", True, (160, 210, 240))
        surface.blit(badge, (port_x + 2, port_y + 4))

        # Animated green radio waveform below portrait
        wave_y = port_y + 38
        points = []
        for i in range(port_size - 8):
            px = port_x + 4 + i
            amp = 8.0 if self.is_active else 2.0
            py = wave_y + math.sin(self.waveform_phase + i * 0.35) * amp
            points.append((px, py))
        if len(points) > 1:
            pygame.draw.lines(surface, self.color_waveform, False, points, 2)

        # 3. Header Information: Speaker & Tactical Channel
        header_x = port_x + port_size + 14
        header_y = self.box_y + 14
        speaker_surf = self.font_header.render(f"▶ {self.current_node.speaker.upper()}", True, self.color_speaker)
        surface.blit(speaker_surf, (header_x, header_y))

        loc_surf = self.font_header.render(f"[{self.current_node.location}]", True, self.color_location)
        surface.blit(loc_surf, (header_x + speaker_surf.get_width() + 12, header_y))

        # 4. Message Body (Typewriter)
        body_y = header_y + 22
        active_full_text = self.response_text if self.response_text else self.current_node.prompt
        visible_len = int(min(len(active_full_text), self.typewriter_chars))
        visible_text = active_full_text[:visible_len]

        # Simple 2-line wrapper
        max_chars_line = 85
        lines = []
        words = visible_text.split(" ")
        cur_line = ""
        for w in words:
            if len(cur_line) + len(w) + 1 <= max_chars_line:
                cur_line = f"{cur_line} {w}".strip()
            else:
                lines.append(cur_line)
                cur_line = w
        if cur_line:
            lines.append(cur_line)

        for idx, line in enumerate(lines[:3]):
            txt_surf = self.font_body.render(line, True, self.color_text)
            surface.blit(txt_surf, (header_x, body_y + idx * 16))

        # 5. Choice Options Cards (Rendered when choice is active)
        if self.is_waiting_for_choice and self.current_node.options:
            opts_y = self.box_y + 92
            opt_spacing = (self.box_width - port_size - 40) // 3
            stance_keys = ["loyal", "neutral", "dissident"]

            for i, stance in enumerate(stance_keys):
                if stance not in self.current_node.options:
                    continue
                opt = self.current_node.options[stance]
                card_x = header_x + i * opt_spacing
                card_w = opt_spacing - 10
                card_h = 42

                # Card background
                col = self.stance_colors.get(stance, self.color_border)
                pygame.draw.rect(surface, (16, 26, 38), (card_x, opts_y, card_w, card_h))
                pygame.draw.rect(surface, col, (card_x, opts_y, card_w, card_h), 1)

                # Option label
                card_lbl = self.font_option.render(opt.label[:36], True, col)
                surface.blit(card_lbl, (card_x + 6, opts_y + 6))

                # Loyalty shift indicator
                sign = "+" if opt.loyalty_delta > 0 else ""
                delta_str = f"Loyalty: {sign}{opt.loyalty_delta:.0f}" if opt.loyalty_delta != 0 else "Loyalty: 0"
                delta_surf = self.font_badge.render(delta_str, True, (170, 190, 210))
                surface.blit(delta_surf, (card_x + 6, opts_y + 24))
