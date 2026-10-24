"""comms_hud.py - In-Flight Radio Transceiver Overlay & Dialogue Engine.

Renders an interactive military radio HUD overlay during active flight operations:
- Translucent tactical radio frame with animated waveform and speaker portrait.
- Animated typewriter text presentation.
- Smooth time-dilation transition to 0.4x speed during interactive decisions.
- Key listener for 3-way ideological stances: [1] LOYAL, [2] NEUTRAL, [3] DISSIDENT.
- Zero per-frame allocations in render() to strictly maintain 60 FPS.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple
import pygame

from eagle1.paths import get_base_dir, verify_path_exact_casing
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
        self.default_response_duration: float = 3.5  # Seconds to read response
        self.response_duration: float = self.default_response_duration
        self.waveform_phase: float = 0.0
        self._portrait_cache: Dict[str, Optional[pygame.Surface]] = {}

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

        # Zero-allocation surface caching
        self._cached_speaker_surf: Optional[pygame.Surface] = None
        self._cached_loc_surf: Optional[pygame.Surface] = None
        self._cached_option_cards: Dict[str, Tuple[pygame.Surface, pygame.Surface]] = {}
        self._cached_body_key: Tuple[str, int] = ("", -1)
        self._cached_body_surfs: List[pygame.Surface] = []
        self._waveform_points: List[Tuple[int, float]] = [(0, 0.0)] * 56

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
        self.badge_rf_surface = self.font_badge.render("RF COMM 9", True, (160, 210, 240))

    def _rebuild_node_surface_cache(self) -> None:
        """Pre-render static text surfaces for the active DialogueNode to avoid per-frame allocations."""
        self._cached_body_key = ("", -1)
        self._cached_body_surfs = []
        if not self.current_node:
            self._cached_speaker_surf = None
            self._cached_loc_surf = None
            self._cached_option_cards.clear()
            return

        self._cached_speaker_surf = self.font_header.render(
            f"▶ {self.current_node.speaker.upper()}", True, self.color_speaker
        )
        self._cached_loc_surf = self.font_header.render(
            f"[{self.current_node.location}]", True, self.color_location
        )
        self._cached_option_cards.clear()
        for stance, opt in self.current_node.options.items():
            col = self.stance_colors.get(stance, self.color_border)
            card_lbl = self.font_option.render(opt.label[:36], True, col)
            sign = "+" if opt.loyalty_delta > 0 else ""
            delta_str = f"Loyalty: {sign}{opt.loyalty_delta:.0f}" if opt.loyalty_delta != 0 else "Loyalty: 0"
            delta_surf = self.font_badge.render(delta_str, True, (170, 190, 210))
            self._cached_option_cards[stance] = (card_lbl, delta_surf)

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
        self.response_duration = self.default_response_duration
        self.typewriter_chars = 0.0
        self.target_time_dilation = 1.0

        # Audio squelch
        if self.audio and hasattr(self.audio, "play_radio_squelch"):
            self.audio.play_radio_squelch()

        self._rebuild_node_surface_cache()
        return True

    def trigger_callout(
        self,
        speaker: str,
        text: str,
        location: str = "Tactical Ground Net",
        portrait: Optional[str] = None,
        duration: float = 3.2,
    ) -> bool:
        """Trigger a non-interactive in-flight radio callout without time dilation."""
        if not text or not text.strip():
            return False

        # Protect active interactive choices from being interrupted by background banter
        if self.is_active and self.current_node and self.current_node.options:
            return False

        node = DialogueNode(
            node_id="banter_callout",
            speaker=speaker,
            location=location,
            prompt=text.strip(),
            options={},
            portrait=portrait,
        )

        self.current_node = node
        self.is_active = True
        self.is_waiting_for_choice = False
        self.selected_stance = None
        self.selected_option = None
        self.response_text = None
        self.response_timer = 0.0
        self.response_duration = max(0.5, float(duration))
        self.typewriter_chars = 0.0
        self.target_time_dilation = 1.0

        if self.audio and hasattr(self.audio, "play_radio_squelch"):
            self.audio.play_radio_squelch()

        self._rebuild_node_surface_cache()
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

        # Response or non-interactive callout dismissal timer
        if self.selected_stance is not None:
            self.target_time_dilation = 1.0
            self.response_timer += dt
            if self.response_timer >= self.response_duration:
                self.dismiss()
        elif self.current_node and not self.current_node.options:
            self.target_time_dilation = 1.0
            if self.typewriter_chars >= total_len:
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

        # Non-interactive callouts must never intercept or swallow gameplay keys
        if not self.current_node or not self.current_node.options:
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

        self._rebuild_node_surface_cache()

    def _get_portrait_surface(self, portrait_path: Optional[str]) -> Optional[pygame.Surface]:
        """Load and cache a 64x64 speaker portrait surface safely."""
        if not portrait_path:
            return None

        if portrait_path in self._portrait_cache:
            return self._portrait_cache[portrait_path]

        try:
            full_path = get_base_dir() / portrait_path
            if full_path.exists() and verify_path_exact_casing(portrait_path):
                img = pygame.image.load(str(full_path)).convert_alpha()
                if img.get_size() != (64, 64):
                    img = pygame.transform.smoothscale(img, (64, 64))
                self._portrait_cache[portrait_path] = img
                return img
        except Exception:
            pass

        self._portrait_cache[portrait_path] = None
        return None

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

        portrait_surf = self._get_portrait_surface(self.current_node.portrait)
        num_pts = min(port_size - 8, len(self._waveform_points))
        if portrait_surf:
            surface.blit(portrait_surf, (port_x, port_y))
            # Subtle waveform across lower edge of portrait
            wave_y = port_y + 54
            amp = 3.0 if self.is_active else 1.0
            wave_col = (120, 240, 160)
            wave_width = 1
        else:
            # Transceiver RF Signal Badge (pre-rendered)
            surface.blit(self.badge_rf_surface, (port_x + 2, port_y + 4))

            # Animated green radio waveform below portrait
            wave_y = port_y + 38
            amp = 8.0 if self.is_active else 2.0
            wave_col = self.color_waveform
            wave_width = 2

        for i in range(num_pts):
            px = port_x + 4 + i
            py = wave_y + math.sin(self.waveform_phase + i * 0.35) * amp
            self._waveform_points[i] = (px, py)
        if num_pts > 1:
            pygame.draw.lines(surface, wave_col, False, self._waveform_points[:num_pts], wave_width)

        # 3. Header Information: Speaker & Tactical Channel
        header_x = port_x + port_size + 14
        header_y = self.box_y + 14
        if self._cached_speaker_surf is None:
            self._rebuild_node_surface_cache()

        if self._cached_speaker_surf:
            surface.blit(self._cached_speaker_surf, (header_x, header_y))
            loc_x = header_x + self._cached_speaker_surf.get_width() + 12
            if self._cached_loc_surf:
                surface.blit(self._cached_loc_surf, (loc_x, header_y))

        # 4. Message Body (Typewriter)
        body_y = header_y + 22
        active_full_text = self.response_text if self.response_text else self.current_node.prompt
        visible_len = int(min(len(active_full_text), self.typewriter_chars))
        body_key = (active_full_text, visible_len)

        if body_key != self._cached_body_key:
            self._cached_body_key = body_key
            visible_text = active_full_text[:visible_len]
            max_chars_line = 85
            lines = []
            words = visible_text.split(" ") if visible_text else []
            cur_line = ""
            for w in words:
                if len(cur_line) + len(w) + 1 <= max_chars_line:
                    cur_line = f"{cur_line} {w}".strip()
                else:
                    lines.append(cur_line)
                    cur_line = w
            if cur_line:
                lines.append(cur_line)
            self._cached_body_surfs = [
                self.font_body.render(line, True, self.color_text) for line in lines[:3]
            ]

        for idx, txt_surf in enumerate(self._cached_body_surfs):
            surface.blit(txt_surf, (header_x, body_y + idx * 16))

        # 5. Choice Options Cards (Rendered when choice is active)
        if self.is_waiting_for_choice and self.current_node.options:
            opts_y = self.box_y + 92
            opt_spacing = (self.box_width - port_size - 40) // 3
            stance_keys = ["loyal", "neutral", "dissident"]

            for i, stance in enumerate(stance_keys):
                if stance not in self.current_node.options:
                    continue
                card_x = header_x + i * opt_spacing
                card_w = opt_spacing - 10
                card_h = 42

                # Card background
                col = self.stance_colors.get(stance, self.color_border)
                pygame.draw.rect(surface, (16, 26, 38), (card_x, opts_y, card_w, card_h))
                pygame.draw.rect(surface, col, (card_x, opts_y, card_w, card_h), 1)

                if stance in self._cached_option_cards:
                    card_lbl, delta_surf = self._cached_option_cards[stance]
                    surface.blit(card_lbl, (card_x + 6, opts_y + 6))
                    surface.blit(delta_surf, (card_x + 6, opts_y + 24))
