"""super_destroyer_view.py - Super Destroyer Hub Deck Screen & Panoramic Viewport.

SES Leviathan of Truth serves as the tactical, psychological, and narrative
staging area between combat sorties over Vandalon Prime.
Provides pre-rendered 1280x720 panoramic viewport, top HUD status bar with dynamic
Super Earth Patriotism Index progress bar bound to StoryManager.loyalty, and
3-zone navigation (Bridge, Ready Room, Hangar Deck).
Zero per-frame dynamic surface allocations in draw() to preserve 60 FPS budget.
"""

from __future__ import annotations

import math
import random
from typing import Any, Dict, Optional, Tuple
import pygame

from eagle1.story.story_manager import (
    MAX_LOYALTY,
    MIN_LOYALTY,
    THRESHOLD_DISSIDENT_SURRENDER,
    THRESHOLD_OBEDIENCE_PURGE,
    StoryManager,
)

ZONE_BRIDGE: str = "bridge"
ZONE_READY_ROOM: str = "ready_room"
ZONE_HANGAR: str = "hangar"
HUB_ZONES: Tuple[str, ...] = (ZONE_BRIDGE, ZONE_READY_ROOM, ZONE_HANGAR)

PATRIOTISM_COLOR_ZEALOT: Tuple[int, int, int] = (255, 215, 50)  # Gold
PATRIOTISM_COLOR_NOMINAL: Tuple[int, int, int] = (0, 220, 255)  # Cyan
PATRIOTISM_COLOR_DISSIDENT: Tuple[int, int, int] = (231, 76, 60)  # Crimson Red

PATRIOTISM_LABEL_ZEALOT: str = "EXEMPLARY ZEALOT"
PATRIOTISM_LABEL_NOMINAL: str = "NOMINAL PATRIOTISM"
PATRIOTISM_LABEL_DISSIDENT: str = "DISSIDENT WARNING"

ZONE_METADATA: Dict[str, Dict[str, str]] = {
    ZONE_BRIDGE: {
        "title": "BRIDGE COMMAND",
        "subtitle": "STRATEGIC BRIEFING & MINISTRY OVERSIGHT",
        "deck_code": "DECK 01 // FORWARD OBSERVATION",
        "hotkey": "1",
        "description": "Orbital command center aboard the SES Leviathan of Truth overlooking Vandalon Prime.",
    },
    ZONE_READY_ROOM: {
        "title": "HELLDIVER READY ROOM",
        "subtitle": "VIPER SQUAD BARRACKS & DROP POD BAY",
        "deck_code": "DECK 02 // HELLPOD STAGING BAY",
        "hotkey": "2",
        "description": "Tactical staging quarters and orbital drop pod tubes for Viper Squad (Viper 1-4).",
    },
    ZONE_HANGAR: {
        "title": "FLIGHT HANGAR DECK",
        "subtitle": "EAGLE-1 MAINTENANCE & CATAPULT BAY",
        "deck_code": "DECK 03 // MAGNETIC LAUNCH RAIL",
        "hotkey": "3",
        "description": "Primary strike craft maintenance bay, ordnance racks, and orbital catapult launch rail.",
    },
}


class SuperDestroyerView:
    """Foundational view for the Super Destroyer hub deck scene."""

    def __init__(
        self,
        story_manager: StoryManager,
        audio_manager: Optional[Any] = None,
        screen_width: int = 1280,
        screen_height: int = 720,
    ) -> None:
        self.story_manager = story_manager
        self.audio = audio_manager
        self.screen_width = int(screen_width)
        self.screen_height = int(screen_height)

        self._zone_index: int = 0
        self.hovered_zone: Optional[str] = None
        self.ambient_timer: float = 0.0
        self._dialogue_open: bool = False

        # Post-sortie statistics placeholder for upcoming sub-issues
        self.last_casualties_count: int = 0
        self.last_squad_wiped: bool = False
        self.last_hull_ratio: float = 1.0

        # Geometry & Layout
        self._init_layout_rects()

        # Fonts & Rendering Cache
        self._init_fonts()
        self._init_cached_surfaces()

    @property
    def active_zone(self) -> str:
        """Return the identifier of the currently active deck zone."""
        return HUB_ZONES[self._zone_index]

    @property
    def is_dialogue_open(self) -> bool:
        """Return whether an interactive dialogue modal is active."""
        return self._dialogue_open

    def _init_layout_rects(self) -> None:
        """Pre-compute layout geometry in screen coordinates."""
        self.top_hud_rect = pygame.Rect(0, 0, self.screen_width, 68)
        self.patriotism_bar_rect = pygame.Rect(self.screen_width - 450, 24, 420, 16)

        tab_y = 78
        tab_h = 50
        tab_total_w = self.screen_width - 80
        tab_w = tab_total_w // len(HUB_ZONES)
        self.zone_tab_rects: Dict[str, pygame.Rect] = {}
        for idx, zone_id in enumerate(HUB_ZONES):
            rx = 40 + idx * tab_w
            self.zone_tab_rects[zone_id] = pygame.Rect(rx, tab_y, tab_w - 10, tab_h)

        self.content_panel_rect = pygame.Rect(40, 140, self.screen_width - 80, 510)
        self.footer_rect = pygame.Rect(0, self.screen_height - 56, self.screen_width, 56)

    def _init_fonts(self) -> None:
        """Initialize and cache fonts safely across desktop and headless environments."""
        if not pygame.font.get_init():
            try:
                pygame.font.init()
            except Exception:
                pass

        def _safe_sys_font(names: str, size: int, bold: bool = False) -> pygame.font.Font:
            try:
                f = pygame.font.SysFont(names, size, bold=bold)
                if f:
                    return f
            except Exception:
                pass
            try:
                return pygame.font.Font(None, size)
            except Exception:
                return None  # type: ignore

        self.font_ship_name = _safe_sys_font("impact,arialblack,arial", 22, bold=True)
        self.font_sector = _safe_sys_font("consolas,courier,monospace", 13, bold=True)
        self.font_badge = _safe_sys_font("consolas,courier,monospace", 12, bold=True)
        self.font_patriotism_title = _safe_sys_font("consolas,courier,monospace", 11, bold=True)
        self.font_patriotism_status = _safe_sys_font("consolas,courier,monospace", 12, bold=True)
        self.font_tab_title = _safe_sys_font("impact,arialblack,arial", 17, bold=True)
        self.font_tab_sub = _safe_sys_font("consolas,courier,monospace", 10, bold=False)
        self.font_deck_code = _safe_sys_font("consolas,courier,monospace", 14, bold=True)
        self.font_deck_desc = _safe_sys_font("arial,sans-serif", 15)
        self.font_footer = _safe_sys_font("consolas,courier,monospace", 12, bold=True)

    def _init_cached_surfaces(self) -> None:
        """Pre-allocate all static background surfaces and panels to ensure 60 FPS."""
        # 1. Orbital Viewport Panoramic Vista (Vandalon Prime + Starfield + Bridge Framing)
        self.orbital_bg_surface = pygame.Surface((self.screen_width, self.screen_height))
        self.orbital_bg_surface.fill((6, 9, 16))

        # Starfield using deterministic seed
        rng = random.Random(42)
        star_colors = [(180, 200, 220), (220, 235, 255), (130, 160, 190), (255, 230, 180)]
        for _ in range(160):
            sx = rng.randint(0, self.screen_width - 1)
            sy = rng.randint(0, self.screen_height - 1)
            col = rng.choice(star_colors)
            self.orbital_bg_surface.set_at((sx, sy), col)
            if rng.random() < 0.15:
                # Slight star glow
                if sx + 1 < self.screen_width:
                    self.orbital_bg_surface.set_at((sx + 1, sy), (col[0] // 2, col[1] // 2, col[2] // 2))
                if sy + 1 < self.screen_height:
                    self.orbital_bg_surface.set_at((sx, sy + 1), (col[0] // 2, col[1] // 2, col[2] // 2))

        # Vandalon Prime Horizon Curves (Rust/Crimson planetary arc)
        planet_center_x = self.screen_width // 2
        planet_center_y = self.screen_height + 420
        radii_layers = [
            (680, (65, 18, 16)),
            (660, (110, 32, 22)),
            (640, (165, 54, 28)),
            (620, (220, 95, 45)),
        ]
        for radius, color in radii_layers:
            pygame.draw.circle(self.orbital_bg_surface, color, (planet_center_x, planet_center_y), radius)

        # Atmospheric Corona Rim
        pygame.draw.circle(self.orbital_bg_surface, (255, 160, 90), (planet_center_x, planet_center_y), 682, width=2)
        pygame.draw.circle(self.orbital_bg_surface, (120, 40, 25), (planet_center_x, planet_center_y), 685, width=1)

        # Structural Bridge Framing (SES Leviathan of Truth armored struts)
        frame_col_dark = (20, 26, 38)
        frame_col_mid = (36, 46, 64)
        frame_col_edge = (60, 80, 105)

        # Left & Right diagonal observation trusses
        pygame.draw.polygon(self.orbital_bg_surface, frame_col_dark, [(0, 0), (90, 0), (35, self.screen_height), (0, self.screen_height)])
        pygame.draw.line(self.orbital_bg_surface, frame_col_edge, (90, 0), (35, self.screen_height), 2)

        pygame.draw.polygon(
            self.orbital_bg_surface,
            frame_col_dark,
            [(self.screen_width, 0), (self.screen_width - 90, 0), (self.screen_width - 35, self.screen_height), (self.screen_width, self.screen_height)],
        )
        pygame.draw.line(self.orbital_bg_surface, frame_col_edge, (self.screen_width - 90, 0), (self.screen_width - 35, self.screen_height), 2)

        # Horizontal support bulkheads
        pygame.draw.line(self.orbital_bg_surface, frame_col_mid, (0, 70), (self.screen_width, 70), 2)
        pygame.draw.line(self.orbital_bg_surface, frame_col_mid, (0, self.screen_height - 60), (self.screen_width, self.screen_height - 60), 2)

        # 2. Pre-rendered Top HUD Bar Background
        self.top_hud_bg_surface = pygame.Surface((self.top_hud_rect.width, self.top_hud_rect.height), pygame.SRCALPHA)
        self.top_hud_bg_surface.fill((10, 15, 24, 230))
        pygame.draw.line(self.top_hud_bg_surface, (255, 215, 50), (0, self.top_hud_rect.height - 2), (self.top_hud_rect.width, self.top_hud_rect.height - 2), 2)
        pygame.draw.line(self.top_hud_bg_surface, (50, 75, 105), (0, self.top_hud_rect.height - 1), (self.top_hud_rect.width, self.top_hud_rect.height - 1), 1)

        # 3. Pre-rendered Content Panel Background
        self.content_panel_bg_surface = pygame.Surface((self.content_panel_rect.width, self.content_panel_rect.height), pygame.SRCALPHA)
        self.content_panel_bg_surface.fill((12, 18, 28, 205))
        pygame.draw.rect(self.content_panel_bg_surface, (45, 75, 105), (0, 0, self.content_panel_rect.width, self.content_panel_rect.height), width=1)
        # Gold corner brackets
        cw = 18
        w, h = self.content_panel_rect.width, self.content_panel_rect.height
        pygame.draw.lines(self.content_panel_bg_surface, (255, 215, 50), False, [(0, cw), (0, 0), (cw, 0)], 2)
        pygame.draw.lines(self.content_panel_bg_surface, (255, 215, 50), False, [(w - cw, 0), (w - 1, 0), (w - 1, cw)], 2)
        pygame.draw.lines(self.content_panel_bg_surface, (255, 215, 50), False, [(0, h - cw), (0, h - 1), (cw, h - 1)], 2)
        pygame.draw.lines(self.content_panel_bg_surface, (255, 215, 50), False, [(w - cw, h - 1), (w - 1, h - 1), (w - 1, h - cw)], 2)

        # 4. Pre-rendered Footer Bar Background
        self.footer_bg_surface = pygame.Surface((self.footer_rect.width, self.footer_rect.height), pygame.SRCALPHA)
        self.footer_bg_surface.fill((10, 15, 24, 230))
        pygame.draw.line(self.footer_bg_surface, (45, 75, 105), (0, 0), (self.footer_rect.width, 0), 1)

        # Pre-render static text surfaces
        self._cached_static_texts: Dict[str, pygame.Surface] = {}
        if self.font_ship_name:
            self._cached_static_texts["ship_name"] = self.font_ship_name.render("SES LEVIATHAN OF TRUTH", True, (255, 215, 50))
        if self.font_sector:
            self._cached_static_texts["sector"] = self.font_sector.render("SECTOR 7-C // VANDALON REACH", True, (150, 185, 210))
        if self.font_patriotism_title:
            self._cached_static_texts["patriotism_title"] = self.font_patriotism_title.render("SUPER EARTH PATRIOTISM INDEX", True, (170, 195, 220))
        if self.font_footer:
            self._cached_static_texts["footer_hint"] = self.font_footer.render(
                "[A / D / ARROWS] SWITCH ZONE   |   [1-3] DIRECT SELECT   |   [ESC] MAIN MENU",
                True,
                (140, 175, 205),
            )

        # Dynamic text caches (keyed by state)
        self._cached_dynamic_surfaces: Dict[str, Tuple[Any, pygame.Surface]] = {}

    def _get_sanitized_loyalty(self) -> float:
        """Read and sanitize story_manager.loyalty with bounds and NaN safety."""
        raw = getattr(self.story_manager, "loyalty", 70.0)
        if isinstance(raw, bool) or not isinstance(raw, (int, float)):
            return 70.0
        val = float(raw)
        if math.isnan(val):
            return 0.0
        if math.isinf(val):
            return MAX_LOYALTY if val > 0 else MIN_LOYALTY
        return max(MIN_LOYALTY, min(MAX_LOYALTY, val))

    def get_patriotism_bar_ratio(self) -> float:
        """Return the patriotism ratio strictly clamped to [0.0, 1.0]."""
        sanitized = self._get_sanitized_loyalty()
        return max(0.0, min(1.0, sanitized / MAX_LOYALTY))

    def get_patriotism_status_label_and_color(self) -> Tuple[str, Tuple[int, int, int]]:
        """Compute patriotism tier label and color based on loyalty score."""
        raw = getattr(self.story_manager, "loyalty", 70.0)
        if isinstance(raw, bool) or not isinstance(raw, (int, float)) or math.isnan(float(raw)):
            return PATRIOTISM_LABEL_NOMINAL, PATRIOTISM_COLOR_NOMINAL

        val = self._get_sanitized_loyalty()
        if val >= THRESHOLD_OBEDIENCE_PURGE:
            return PATRIOTISM_LABEL_ZEALOT, PATRIOTISM_COLOR_ZEALOT
        elif val <= THRESHOLD_DISSIDENT_SURRENDER:
            return PATRIOTISM_LABEL_DISSIDENT, PATRIOTISM_COLOR_DISSIDENT
        else:
            return PATRIOTISM_LABEL_NOMINAL, PATRIOTISM_COLOR_NOMINAL

    def _draw_top_hud_bar(self, surface: pygame.Surface) -> None:
        """Render ship designation, sector info, campaign badge, and Patriotism Index."""
        surface.blit(self.top_hud_bg_surface, (0, 0))

        # Ship name & Sector
        ship_surf = self._cached_static_texts.get("ship_name")
        if ship_surf:
            surface.blit(ship_surf, (24, 12))

        sector_surf = self._cached_static_texts.get("sector")
        if sector_surf:
            surface.blit(sector_surf, (26, 40))

        # Campaign progression badge
        act = getattr(self.story_manager, "current_act", 1)
        sortie = getattr(self.story_manager, "current_sortie", 1)
        badge_key = (act, sortie)
        cached_badge = self._cached_dynamic_surfaces.get("campaign_badge")
        if cached_badge and cached_badge[0] == badge_key:
            badge_surf = cached_badge[1]
        else:
            text = f"ACT {act} // SORTIE {sortie}"
            badge_surf = self.font_badge.render(text, True, (0, 220, 255)) if self.font_badge else None
            if badge_surf:
                self._cached_dynamic_surfaces["campaign_badge"] = (badge_key, badge_surf)

        if badge_surf:
            badge_box = pygame.Rect(460, 20, 160, 28)
            pygame.draw.rect(surface, (16, 26, 40), badge_box)
            pygame.draw.rect(surface, (0, 180, 230), badge_box, width=1)
            bx = badge_box.centerx - badge_surf.get_width() // 2
            by = badge_box.centery - badge_surf.get_height() // 2
            surface.blit(badge_surf, (bx, by))

        # Super Earth Patriotism Index
        title_surf = self._cached_static_texts.get("patriotism_title")
        if title_surf:
            surface.blit(title_surf, (self.patriotism_bar_rect.x, 8))

        label_str, color = self.get_patriotism_status_label_and_color()
        ratio = self.get_patriotism_bar_ratio()
        loyalty_val = self._get_sanitized_loyalty()

        status_key = (label_str, color, round(loyalty_val, 1))
        cached_status = self._cached_dynamic_surfaces.get("patriotism_status")
        if cached_status and cached_status[0] == status_key:
            status_surf = cached_status[1]
        else:
            text = f"{label_str} [{loyalty_val:5.1f}%]"
            status_surf = self.font_patriotism_status.render(text, True, color) if self.font_patriotism_status else None
            if status_surf:
                self._cached_dynamic_surfaces["patriotism_status"] = (status_key, status_surf)

        if status_surf:
            sx = self.patriotism_bar_rect.right - status_surf.get_width()
            surface.blit(status_surf, (sx, 8))

        # Progress bar frame & fill
        pygame.draw.rect(surface, (18, 24, 34), self.patriotism_bar_rect)
        fill_w = int(self.patriotism_bar_rect.width * ratio)
        if fill_w > 0:
            fill_rect = pygame.Rect(self.patriotism_bar_rect.x, self.patriotism_bar_rect.y, fill_w, self.patriotism_bar_rect.height)
            pygame.draw.rect(surface, color, fill_rect)

        # Threshold markers (15% Dissident and 90% Zealot lines)
        dissident_x = self.patriotism_bar_rect.x + int(self.patriotism_bar_rect.width * (THRESHOLD_DISSIDENT_SURRENDER / MAX_LOYALTY))
        zealot_x = self.patriotism_bar_rect.x + int(self.patriotism_bar_rect.width * (THRESHOLD_OBEDIENCE_PURGE / MAX_LOYALTY))
        pygame.draw.line(surface, PATRIOTISM_COLOR_DISSIDENT, (dissident_x, self.patriotism_bar_rect.top - 2), (dissident_x, self.patriotism_bar_rect.bottom + 2), 1)
        pygame.draw.line(surface, PATRIOTISM_COLOR_ZEALOT, (zealot_x, self.patriotism_bar_rect.top - 2), (zealot_x, self.patriotism_bar_rect.bottom + 2), 1)

        pygame.draw.rect(surface, (80, 110, 140), self.patriotism_bar_rect, width=1)

    # -------------------------------------------------------------------------
    # Zone Navigation & Event Engine (Task 2 Implementation)
    # -------------------------------------------------------------------------
    def select_zone(self, zone_id_or_index: str | int) -> bool:
        """Select a deck zone by its identifier string or 0-based index."""
        if isinstance(zone_id_or_index, bool):
            return False

        target_index: Optional[int] = None
        if isinstance(zone_id_or_index, int):
            if 0 <= zone_id_or_index < len(HUB_ZONES):
                target_index = zone_id_or_index
            else:
                return False
        elif isinstance(zone_id_or_index, str):
            cleaned = zone_id_or_index.strip().lower()
            if cleaned in HUB_ZONES:
                target_index = HUB_ZONES.index(cleaned)
            else:
                return False
        else:
            return False

        if target_index is not None and target_index != self._zone_index:
            self._zone_index = target_index
            self._play_ui_sound("ui_click")
            return True
        elif target_index == self._zone_index:
            return True

        return False

    def cycle_zone(self, direction: int) -> str:
        """Cycle deck zone sequentially forward (+1) or backward (-1)."""
        if isinstance(direction, bool) or not isinstance(direction, int) or direction == 0:
            return self.active_zone

        self._zone_index = (self._zone_index + direction) % len(HUB_ZONES)
        self._play_ui_sound("ui_click")
        return self.active_zone

    def _play_ui_sound(self, sound_name: str) -> None:
        """Safely trigger UI sound effects through AudioManager if available."""
        if self.audio and hasattr(self.audio, "play_sfx"):
            try:
                self.audio.play_sfx(sound_name)
            except Exception:
                pass

    def update(self, dt: float) -> None:
        """Advance ambient animations and UI timers."""
        if dt > 0.0 and not math.isnan(dt):
            self.ambient_timer = (self.ambient_timer + float(dt)) % 3600.0

    def handle_event(
        self,
        event: pygame.event.Event,
        mouse_pos: Optional[Tuple[int, int]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Process keyboard hotkeys and mouse clicks for hub navigation."""
        if self._dialogue_open:
            return None

        pos = mouse_pos if mouse_pos is not None else getattr(event, "pos", None)

        if event.type == pygame.MOUSEMOTION and pos is not None:
            new_hover = None
            for zone_id, rect in self.zone_tab_rects.items():
                if rect.collidepoint(pos):
                    new_hover = zone_id
                    break
            if new_hover != self.hovered_zone:
                self.hovered_zone = new_hover
                if new_hover is not None:
                    self._play_ui_sound("ui_hover")

        elif event.type == pygame.MOUSEBUTTONDOWN and getattr(event, "button", 1) == 1 and pos is not None:
            for zone_id, rect in self.zone_tab_rects.items():
                if rect.collidepoint(pos):
                    self.select_zone(zone_id)
                    return {"action": "select_zone", "zone": self.active_zone}

        elif event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_a, pygame.K_LEFT):
                new_zone = self.cycle_zone(-1)
                return {"action": "select_zone", "zone": new_zone}
            elif event.key in (pygame.K_d, pygame.K_RIGHT):
                new_zone = self.cycle_zone(1)
                return {"action": "select_zone", "zone": new_zone}
            elif event.key in (pygame.K_1, pygame.K_KP1):
                self.select_zone(ZONE_BRIDGE)
                return {"action": "select_zone", "zone": self.active_zone}
            elif event.key in (pygame.K_2, pygame.K_KP2):
                self.select_zone(ZONE_READY_ROOM)
                return {"action": "select_zone", "zone": self.active_zone}
            elif event.key in (pygame.K_3, pygame.K_KP3):
                self.select_zone(ZONE_HANGAR)
                return {"action": "select_zone", "zone": self.active_zone}
            elif event.key == pygame.K_ESCAPE:
                return {"action": "main_menu"}

        return None

    def _draw_zone_tabs(self, surface: pygame.Surface) -> None:
        """Render the 3 interactive deck zone selector tabs."""
        for zone_id, rect in self.zone_tab_rects.items():
            is_active = zone_id == self.active_zone
            is_hovered = zone_id == self.hovered_zone

            meta = ZONE_METADATA.get(zone_id, {})
            title = meta.get("title", zone_id.upper())
            hotkey = meta.get("hotkey", "")
            subtitle = meta.get("subtitle", "")

            # Background fill
            bg_col = (20, 30, 48, 220) if is_active else ((14, 22, 34, 180) if not is_hovered else (24, 38, 58, 200))
            pygame.draw.rect(surface, bg_col[:3], rect)

            # Border
            if is_active:
                border_col = (255, 215, 50)  # Gold
                border_w = 2
                # Highlight bar
                pygame.draw.rect(surface, (255, 215, 50), (rect.x, rect.bottom - 4, rect.width, 4))
            elif is_hovered:
                border_col = (0, 210, 255)  # Cyan
                border_w = 1
            else:
                border_col = (45, 68, 92)
                border_w = 1
            pygame.draw.rect(surface, border_col, rect, width=border_w)

            # Tab text
            tab_title_key = (zone_id, is_active, is_hovered)
            cache_key = f"tab_{zone_id}"
            cached_tab = self._cached_dynamic_surfaces.get(cache_key)
            if cached_tab and cached_tab[0] == tab_title_key:
                tsurf, subsurf = cached_tab[1]  # type: ignore
            else:
                title_col = (255, 225, 120) if is_active else ((220, 240, 255) if is_hovered else (160, 185, 210))
                tsurf = self.font_tab_title.render(f"[{hotkey}] {title}", True, title_col) if self.font_tab_title else None
                subsurf = self.font_tab_sub.render(subtitle, True, (120, 150, 175)) if self.font_tab_sub else None
                self._cached_dynamic_surfaces[cache_key] = (tab_title_key, (tsurf, subsurf))  # type: ignore

            if tsurf:
                surface.blit(tsurf, (rect.x + 14, rect.y + 8))
            if subsurf:
                surface.blit(subsurf, (rect.x + 16, rect.y + 30))

    def _draw_active_zone_deck(self, surface: pygame.Surface) -> None:
        """Render main deck panel content for the active zone."""
        surface.blit(self.content_panel_bg_surface, self.content_panel_rect)

        meta = ZONE_METADATA.get(self.active_zone, {})
        deck_code = meta.get("deck_code", "")
        desc = meta.get("description", "")

        # Deck header banner
        deck_key = (self.active_zone,)
        cached_deck = self._cached_dynamic_surfaces.get("deck_banner")
        if cached_deck and cached_deck[0] == deck_key:
            code_surf, desc_surf = cached_deck[1]  # type: ignore
        else:
            code_surf = self.font_deck_code.render(deck_code, True, (0, 220, 255)) if self.font_deck_code else None
            desc_surf = self.font_deck_desc.render(desc, True, (200, 220, 240)) if self.font_deck_desc else None
            self._cached_dynamic_surfaces["deck_banner"] = (deck_key, (code_surf, desc_surf))  # type: ignore

        rx = self.content_panel_rect.x + 24
        ry = self.content_panel_rect.y + 18
        if code_surf:
            surface.blit(code_surf, (rx, ry))
        if desc_surf:
            surface.blit(desc_surf, (rx, ry + 24))

        # Tactical deck wireframe accents (drawn directly onto surface, 0 allocation)
        inner_rect = pygame.Rect(
            self.content_panel_rect.x + 20,
            self.content_panel_rect.y + 60,
            self.content_panel_rect.width - 40,
            self.content_panel_rect.height - 80,
        )
        pygame.draw.rect(surface, (25, 40, 60), inner_rect, width=1)

        # Subtle zone-specific tactical markings
        if self.active_zone == ZONE_BRIDGE:
            # Observation reticle & tactical grid lines
            cx = inner_rect.centerx
            cy = inner_rect.centery
            pygame.draw.line(surface, (35, 60, 85), (cx - 120, cy), (cx + 120, cy), 1)
            pygame.draw.line(surface, (35, 60, 85), (cx, cy - 80), (cx, cy + 80), 1)
            pygame.draw.circle(surface, (45, 80, 115), (cx, cy), 50, width=1)
        elif self.active_zone == ZONE_READY_ROOM:
            # 4 Pod staging slots wireframe
            slot_w = (inner_rect.width - 60) // 4
            for i in range(4):
                slot_x = inner_rect.x + 12 + i * (slot_w + 12)
                slot_rect = pygame.Rect(slot_x, inner_rect.y + 40, slot_w, inner_rect.height - 80)
                pygame.draw.rect(surface, (28, 48, 70), slot_rect, width=1)
        elif self.active_zone == ZONE_HANGAR:
            # Catapult rail guide stripes
            cy = inner_rect.centery
            pygame.draw.line(surface, (255, 215, 50), (inner_rect.x + 40, cy - 20), (inner_rect.right - 40, cy - 20), 2)
            pygame.draw.line(surface, (255, 215, 50), (inner_rect.x + 40, cy + 20), (inner_rect.right - 40, cy + 20), 2)

    def _draw_footer_bar(self, surface: pygame.Surface) -> None:
        """Render the bottom control and shortcut prompt bar."""
        surface.blit(self.footer_bg_surface, self.footer_rect)
        hint_surf = self._cached_static_texts.get("footer_hint")
        if hint_surf:
            hx = self.footer_rect.centerx - hint_surf.get_width() // 2
            hy = self.footer_rect.centery - hint_surf.get_height() // 2
            surface.blit(hint_surf, (hx, hy))

    def draw(
        self,
        surface: pygame.Surface,
        mouse_pos: Optional[Tuple[int, int]] = None,
    ) -> None:
        """Draw the entire Super Destroyer view onto the provided target surface."""
        if mouse_pos is not None:
            self.hovered_zone = None
            for zone_id, rect in self.zone_tab_rects.items():
                if rect.collidepoint(mouse_pos):
                    self.hovered_zone = zone_id
                    break

        # 1. Blit static pre-rendered orbital panoramic vista
        surface.blit(self.orbital_bg_surface, (0, 0))

        # 2. Orbital Reticle animation (using ambient_timer, zero allocation)
        reticle_x = int(self.screen_width * 0.5 + math.sin(self.ambient_timer * 0.4) * 40)
        reticle_y = int(self.screen_height * 0.45 + math.cos(self.ambient_timer * 0.3) * 15)
        pygame.draw.circle(surface, (0, 180, 230), (reticle_x, reticle_y), 18, width=1)
        pygame.draw.line(surface, (0, 180, 230), (reticle_x - 24, reticle_y), (reticle_x + 24, reticle_y), 1)
        pygame.draw.line(surface, (0, 180, 230), (reticle_x, reticle_y - 24), (reticle_x, reticle_y + 24), 1)

        # 3. Top HUD Bar (Ship info, Sector, Act/Sortie, Patriotism Index)
        self._draw_top_hud_bar(surface)

        # 4. Zone Navigation Tabs
        self._draw_zone_tabs(surface)

        # 5. Active Zone Deck Frame
        self._draw_active_zone_deck(surface)

        # 6. Bottom Footer Bar
        self._draw_footer_bar(surface)
