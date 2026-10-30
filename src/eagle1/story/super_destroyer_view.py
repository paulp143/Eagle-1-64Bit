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
from typing import Any, Dict, List, Optional, Set, Tuple
import pygame

from eagle1.paths import get_base_dir, verify_path_exact_casing
from eagle1.ui.layout import VerticalStackLayout, validate_rects_no_overlap
from eagle1.story.dialogue_data import get_debrief_dialogue_node
from eagle1.story.dialogue_db import (
    SHIP_NPC_PROFILES,
    DialogueNode,
    DialogueOption,
    ShipNPCProfile,
    get_dialogue_node,
    get_ship_npc_profile,
)
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

        # Post-sortie statistics and morale tracking
        self.last_casualties_count: int = 0
        self.last_squad_wiped: bool = False
        self.last_hull_ratio: float = 1.0
        self._post_sortie_stats_recorded: bool = False
        self._completed_nodes_by_sortie: Dict[Tuple[int, int], Set[str]] = {}
        self.npc_card_rects: Dict[str, pygame.Rect] = {}

        # Dialogue Modal State (Issue #59)
        self.active_npc_id: Optional[str] = None
        self.active_dialogue_node: Optional[DialogueNode] = None
        self.typewriter_chars: float = 0.0
        self.typewriter_speed: float = 65.0
        self.selected_option: Optional[DialogueOption] = None
        self.selected_stance: Optional[str] = None
        self.response_text: Optional[str] = None
        self.dialogue_completed_mode: bool = False
        self.hovered_stance: Optional[str] = None
        self.hovered_continue: bool = False
        self._portrait_cache: Dict[Tuple[str, str, Tuple[int, int]], pygame.Surface] = {}
        self._modal_text_cache: Dict[str, Any] = {}
        self._modal_prompt_lines: List[str] = []
        self._modal_prompt_full_lines: List[pygame.Surface] = []

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

    def set_dialogue_open(self, is_open: bool) -> None:
        """Set whether the dialogue modal is open or closed (Issue #63)."""
        open_val = bool(is_open)
        if not open_val:
            self.close_dialogue()
        else:
            self._dialogue_open = True

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

        # Pre-compute NPC interactive card rectangles per zone
        self.npc_card_rects = {}
        inner_x = self.content_panel_rect.x + 20
        inner_y = self.content_panel_rect.y + 60
        inner_w = self.content_panel_rect.width - 40
        inner_h = self.content_panel_rect.height - 80

        # Bridge: 2 stations
        card_w_b = (inner_w - 40) // 2
        self.npc_card_rects["npc_reiner"] = pygame.Rect(inner_x + 15, inner_y + 120, card_w_b, 180)
        self.npc_card_rects["npc_vance"] = pygame.Rect(inner_x + 25 + card_w_b, inner_y + 120, card_w_b, 180)

        # Ready Room: 4 pod slots
        slot_w = (inner_w - 60) // 4
        for i in range(4):
            vid = f"viper_{i+1}"
            sx = inner_x + 12 + i * (slot_w + 12)
            self.npc_card_rects[vid] = pygame.Rect(sx, inner_y + 40, slot_w, inner_h - 80)

        # Hangar: Ortiz workshop
        self.npc_card_rects["npc_ortiz"] = pygame.Rect(inner_x + 30, inner_y + 100, (inner_w - 60) // 2, 200)

        # Dialogue Modal Geometry (Issue #59: 1000x540 centered on 1280x720)
        self.modal_rect = pygame.Rect(140, 90, 1000, 540)
        self.modal_portrait_rect = pygame.Rect(self.modal_rect.x + 28, self.modal_rect.y + 24, 128, 128)
        self.modal_prompt_rect = pygame.Rect(self.modal_rect.x + 28, self.modal_rect.y + 172, self.modal_rect.width - 56, 88)
        self.modal_response_rect = pygame.Rect(self.modal_rect.x + 28, self.modal_rect.y + 268, self.modal_rect.width - 56, 52)
        self.modal_option_rects: Dict[str, pygame.Rect] = {
            "loyal": pygame.Rect(self.modal_rect.x + 28, self.modal_rect.y + 328, self.modal_rect.width - 56, 38),
            "neutral": pygame.Rect(self.modal_rect.x + 28, self.modal_rect.y + 372, self.modal_rect.width - 56, 38),
            "dissident": pygame.Rect(self.modal_rect.x + 28, self.modal_rect.y + 416, self.modal_rect.width - 56, 38),
        }
        self.modal_continue_rect = pygame.Rect(self.modal_rect.right - 240, self.modal_rect.bottom - 46, 212, 34)

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

        # Modal Fonts
        self.font_modal_title = _safe_sys_font("impact,arialblack,arial", 20, bold=True)
        self.font_modal_role = _safe_sys_font("consolas,courier,monospace", 11, bold=True)
        self.font_modal_prompt = _safe_sys_font("consolas,courier,monospace", 14)
        self.font_modal_option = _safe_sys_font("consolas,courier,monospace", 13, bold=True)
        self.font_modal_response = _safe_sys_font("consolas,courier,monospace", 13)
        self.font_modal_btn = _safe_sys_font("consolas,courier,monospace", 12, bold=True)

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

        # Pre-render static NPC labels
        for npc_id, profile in SHIP_NPC_PROFILES.items():
            if self.font_tab_title:
                self._cached_static_texts[f"npc_name_{npc_id}"] = self.font_tab_title.render(
                    profile.name, True, profile.theme_color
                )
            if self.font_tab_sub:
                self._cached_static_texts[f"npc_role_{npc_id}"] = self.font_tab_sub.render(
                    profile.role.upper(), True, (160, 190, 215)
                )

        # 5. Dialogue Modal Pre-rendered Surfaces (Issue #59)
        self.modal_backdrop_surface = pygame.Surface((self.screen_width, self.screen_height), pygame.SRCALPHA)
        self.modal_backdrop_surface.fill((6, 10, 18, 215))

        # Solid opaque modal window to prevent underlying deck text bleed-through
        self.modal_bg_surface = pygame.Surface((self.modal_rect.width, self.modal_rect.height))
        self.modal_bg_surface.fill((10, 15, 24))
        pygame.draw.rect(self.modal_bg_surface, (45, 75, 105), (0, 0, self.modal_rect.width, self.modal_rect.height), width=1)
        mcw = 20
        mw, mh = self.modal_rect.width, self.modal_rect.height
        pygame.draw.lines(self.modal_bg_surface, (255, 215, 50), False, [(0, mcw), (0, 0), (mcw, 0)], 2)
        pygame.draw.lines(self.modal_bg_surface, (255, 215, 50), False, [(mw - mcw, 0), (mw - 1, 0), (mw - 1, mcw)], 2)
        pygame.draw.lines(self.modal_bg_surface, (255, 215, 50), False, [(0, mh - mcw), (0, mh - 1), (mcw, mh - 1)], 2)
        pygame.draw.lines(self.modal_bg_surface, (255, 215, 50), False, [(mw - mcw, mh - 1), (mw - 1, mh - 1), (mw - 1, mh - mcw)], 2)

        # Dynamic text caches (keyed by state)
        self._cached_dynamic_surfaces: Dict[str, Tuple[Any, pygame.Surface]] = {}

        # Pre-warm NPC portraits
        for profile in SHIP_NPC_PROFILES.values():
            self._get_or_create_portrait_surface(profile.portrait_path, profile.npc_id, (128, 128))

    def _get_or_create_portrait_surface(
        self,
        portrait_path: Optional[str],
        npc_id: Optional[str] = None,
        size: Tuple[int, int] = (128, 128),
    ) -> pygame.Surface:
        """Retrieve cached character portrait surface or generate a procedural military insignia."""
        clean_npc = (npc_id or "").strip().lower()
        clean_path = str(portrait_path or "").strip()
        cache_key = (clean_path, clean_npc, size)
        if cache_key in self._portrait_cache:
            return self._portrait_cache[cache_key]

        surf: Optional[pygame.Surface] = None
        ALLOWED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg"}
        if clean_path:
            try:
                from pathlib import Path
                base_dir = Path(get_base_dir()).resolve()
                candidate = (base_dir / clean_path).resolve()
                if (
                    candidate.is_relative_to(base_dir)
                    and candidate.suffix.lower() in ALLOWED_IMAGE_EXTENSIONS
                    and candidate.is_file()
                    and verify_path_exact_casing(str(candidate))
                ):
                    loaded = pygame.image.load(str(candidate))
                    if loaded:
                        surf = pygame.transform.smoothscale(loaded.convert_alpha(), size)
            except Exception:
                surf = None

        if surf is None:
            surf = pygame.Surface(size, pygame.SRCALPHA)
            surf.fill((16, 24, 38, 255))
            for y in range(0, size[1], 4):
                pygame.draw.line(surf, (22, 34, 52), (0, y), (size[0], y), 1)

            profile = get_ship_npc_profile(clean_npc) if clean_npc else None
            theme_col = profile.theme_color if profile else (0, 210, 255)
            pygame.draw.rect(surf, theme_col, (0, 0, size[0], size[1]), width=2)

            f_badge = self.font_badge or (pygame.font.Font(None, 12) if pygame.font.get_init() else None)
            cx, cy = size[0] // 2, size[1] // 2

            if clean_npc == "npc_reiner":
                pts = [
                    (cx, cy - 35),
                    (cx + 30, cy - 20),
                    (cx + 25, cy + 20),
                    (cx, cy + 35),
                    (cx - 25, cy + 20),
                    (cx - 30, cy - 20),
                ]
                pygame.draw.polygon(surf, (40, 30, 10), pts)
                pygame.draw.polygon(surf, (255, 215, 50), pts, width=2)
                pygame.draw.circle(surf, (255, 215, 50), (cx, cy), 8)
                if f_badge:
                    txt = f_badge.render("COMMISSAR", True, (255, 215, 50))
                    surf.blit(txt, (cx - txt.get_width() // 2, size[1] - 20))
            elif clean_npc == "npc_vance":
                pts = [(cx, cy - 32), (cx + 28, cy), (cx, cy + 32), (cx - 28, cy)]
                pygame.draw.polygon(surf, (10, 30, 45), pts)
                pygame.draw.polygon(surf, (0, 220, 255), pts, width=2)
                pygame.draw.line(surf, (0, 220, 255), (cx, cy - 20), (cx, cy + 20), 2)
                pygame.draw.line(surf, (0, 220, 255), (cx - 20, cy), (cx + 20, cy), 2)
                if f_badge:
                    txt = f_badge.render("COMMAND", True, (0, 220, 255))
                    surf.blit(txt, (cx - txt.get_width() // 2, size[1] - 20))
            elif clean_npc == "npc_ortiz":
                pygame.draw.circle(surf, (40, 25, 10), (cx, cy), 30)
                pygame.draw.circle(surf, (243, 156, 18), (cx, cy), 30, width=2)
                for angle_deg in range(0, 360, 45):
                    rad = math.radians(angle_deg)
                    px = cx + int(math.cos(rad) * 32)
                    py = cy + int(math.sin(rad) * 32)
                    pygame.draw.circle(surf, (243, 156, 18), (px, py), 4)
                if f_badge:
                    txt = f_badge.render("CHIEF ENG", True, (243, 156, 18))
                    surf.blit(txt, (cx - txt.get_width() // 2, size[1] - 20))
            else:
                pts = [(cx, cy - 28), (cx + 24, cy), (cx, cy + 28), (cx - 24, cy)]
                pygame.draw.polygon(surf, (15, 25, 35), pts)
                pygame.draw.polygon(surf, theme_col, pts, width=2)
                if f_badge:
                    short_label = clean_npc.upper()[:8]
                    txt = f_badge.render(short_label, True, theme_col)
                    surf.blit(txt, (cx - txt.get_width() // 2, size[1] - 20))

        self._portrait_cache[cache_key] = surf
        return surf

    def _wrap_text_to_width(
        self,
        text: str,
        font: Optional[pygame.font.Font],
        max_width: int,
        max_lines: int = 6,
    ) -> List[str]:
        """Wrap text into lines fitting within max_width using the provided font."""
        if not text or not font:
            return [text] if text else []
        words = text.split(" ")
        lines: List[str] = []
        current_line: List[str] = []

        for word in words:
            test_line = " ".join(current_line + [word])
            try:
                width, _ = font.size(test_line)
            except Exception:
                width = len(test_line) * 8
            if width <= max_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(" ".join(current_line))
                    current_line = [word]
                    if len(lines) >= max_lines:
                        break
                else:
                    lines.append(word)
                    if len(lines) >= max_lines:
                        break

        if current_line and len(lines) < max_lines:
            lines.append(" ".join(current_line))

        return lines

    def _rebuild_modal_cache(self) -> None:
        """Pre-render and cache all text surfaces for the active dialogue modal using VerticalStackLayout."""
        self._modal_text_cache.clear()
        self._modal_prompt_lines = []
        self._modal_prompt_full_lines = []

        if not self.active_dialogue_node:
            return

        node = self.active_dialogue_node
        prof = get_ship_npc_profile(self.active_npc_id)
        theme_col = prof.theme_color if prof else (0, 220, 255)

        # 1. Header Area: Speaker Name & Role/Location (rendered to the right of the 128x128 portrait)
        spk_name = (prof.name if prof else node.speaker).upper()
        if self.font_modal_title:
            self._modal_text_cache["speaker_name"] = self.font_modal_title.render(spk_name, True, theme_col)

        loc_str = node.location.upper()
        role_str = f"{prof.role.upper()} // {loc_str}" if prof else loc_str
        if self.font_modal_role:
            self._modal_text_cache["speaker_role"] = self.font_modal_role.render(role_str, True, (140, 175, 205))

        # Mode status badge
        if self.dialogue_completed_mode:
            badge_text = "STATUS // ARCHIVED SORTIE DEBRIEF [READ-ONLY]"
            b_col = (140, 175, 205)
        else:
            badge_text = "STATUS // AWAITING PILOT IDEOLOGICAL DIRECTIVE"
            b_col = (255, 215, 50)
        if self.font_badge:
            self._modal_text_cache["mode_badge"] = self.font_badge.render(badge_text, True, b_col)

        # 2. Sequential Vertical Stack for Content Zone (strictly below the header divider)
        content_top = self.modal_rect.y + 168
        content_bottom = self.modal_rect.bottom - 52
        content_bounds = pygame.Rect(
            self.modal_rect.x + 28,
            content_top,
            self.modal_rect.width - 56,
            content_bottom - content_top,
        )

        stack = VerticalStackLayout(content_bounds, padding=0, default_gap=8)

        # Wrap Prompt Text into content bounds width
        prompt_w = content_bounds.width - 24
        self._modal_prompt_lines = self._wrap_text_to_width(node.prompt, self.font_modal_prompt, prompt_w, max_lines=4)
        lh_prompt = self.font_modal_prompt.get_linesize() if self.font_modal_prompt else 18
        self.modal_prompt_rect = stack.add_text_slot(
            line_count=len(self._modal_prompt_lines) or 1,
            line_height=lh_prompt,
            padding_y=8,
        )
        if self.font_modal_prompt:
            self._modal_prompt_full_lines = [
                self.font_modal_prompt.render(line, True, (220, 235, 250))
                for line in self._modal_prompt_lines
            ]

        # Response Text Slot (if active)
        if self.response_text:
            resp_w = content_bounds.width - 24
            resp_lines = self._wrap_text_to_width(self.response_text, self.font_modal_response, resp_w, max_lines=2)
            lh_resp = self.font_modal_response.get_linesize() if self.font_modal_response else 18
            resp_panel_h = 22 + (len(resp_lines) or 1) * lh_resp + 10
            self.modal_response_rect = stack.add_slot(height=resp_panel_h, gap=8)
            if self.font_modal_response:
                self._modal_text_cache["response_lines"] = [
                    self.font_modal_response.render(line, True, (240, 245, 255))
                    for line in resp_lines
                ]
            spk_hdr = f">> REACTION // {spk_name}"
            if self.font_modal_role:
                self._modal_text_cache["response_header"] = self.font_modal_role.render(spk_hdr, True, (0, 220, 255))
            if self.selected_option:
                d = self.selected_option.loyalty_delta
                d_col = (255, 215, 50) if d > 0 else ((0, 220, 255) if d == 0 else (231, 76, 60))
                d_sign = "+" if d > 0 else ""
                d_str = f"PATRIOTISM DELTA: {d_sign}{d:0.1f}%"
                if self.font_modal_btn:
                    self._modal_text_cache["response_delta"] = self.font_modal_btn.render(d_str, True, d_col)
        else:
            self.modal_response_rect = pygame.Rect(content_bounds.x, stack.cursor_y, 0, 0)

        # Stance Option Cards (Two-Row Layout: Row 1 = Tag + Delta, Row 2 = Dialogue Statement)
        option_h = 42 if self.response_text else 46
        card_gap = 5 if self.response_text else 6
        for stance in ("loyal", "neutral", "dissident"):
            opt_rect = stack.add_slot(height=option_h, gap=card_gap)
            self.modal_option_rects[stance] = opt_rect

            opt = node.options.get(stance)
            if opt:
                col = (255, 215, 50) if stance == "loyal" else ((0, 220, 255) if stance == "neutral" else (231, 76, 60))
                delta_sign = "+" if opt.loyalty_delta > 0 else ""
                delta_text = f"[{delta_sign}{opt.loyalty_delta:0.1f}% PATRIOTISM]" if opt.loyalty_delta != 0 else "[0.0% PATRIOTISM]"

                raw_label = opt.label
                if "]" in raw_label:
                    tag_part, body_part = raw_label.split("]", 1)
                    tag_text = (tag_part + "]").strip()
                    body_text = body_part.strip()
                else:
                    tag_text = f"[{opt.key_name}. {opt.stance.upper()}]"
                    body_text = raw_label.strip()

                if self.font_modal_btn:
                    self._modal_text_cache[f"opt_tag_{stance}"] = self.font_modal_btn.render(tag_text, True, col)
                    self._modal_text_cache[f"opt_delta_{stance}"] = self.font_modal_btn.render(delta_text, True, col)
                if self.font_modal_option:
                    self._modal_text_cache[f"opt_body_{stance}"] = self.font_modal_option.render(body_text, True, (220, 235, 250))

        # Continue / End Transmission Button (Bottom right)
        self.modal_continue_rect = pygame.Rect(
            self.modal_rect.right - 240,
            self.modal_rect.bottom - 46,
            212,
            34,
        )
        btn_label = (
            "[SPACE / ENTER / ESC] END TRANSMISSION"
            if (self.dialogue_completed_mode or self.selected_option is not None)
            else "[ESC] CANCEL"
        )
        if self.font_modal_btn:
            self._modal_text_cache["continue_btn"] = self.font_modal_btn.render(btn_label, True, (255, 255, 255))

        # Mathematical guarantee: zero overlaps across all dynamically allocated slots AND continue button!
        stack.assert_no_overlaps()
        btn_coll = validate_rects_no_overlap(stack.allocated_rects + [self.modal_continue_rect])
        if btn_coll:
            raise AssertionError(f"Modal continue button collision with content stack: {btn_coll}")

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
    # Shipboard NPC Profiles & Morale Engine (Issue #58)
    # -------------------------------------------------------------------------
    def get_zone_npcs(self, zone_id: Optional[str] = None) -> List[ShipNPCProfile]:
        """Retrieve character profiles located in the specified or active deck zone."""
        target_zone = self.active_zone if zone_id is None else zone_id
        if isinstance(target_zone, bool) or not isinstance(target_zone, str):
            return []
        clean_zone = target_zone.strip().lower()
        if clean_zone not in HUB_ZONES:
            return []
        return [prof for prof in SHIP_NPC_PROFILES.values() if prof.zone == clean_zone]

    def set_last_sortie_stats(
        self,
        casualties_count: int = 0,
        squad_wiped: bool = False,
        hull_ratio: float = 1.0,
    ) -> None:
        """Record post-sortie combat statistics for character morale and diagnostics."""
        if (
            isinstance(casualties_count, bool)
            or not isinstance(casualties_count, (int, float))
            or math.isnan(float(casualties_count))
            or math.isinf(float(casualties_count))
        ):
            c_count = 0
        else:
            c_count = max(0, int(casualties_count))

        self.last_casualties_count = c_count
        self.last_squad_wiped = bool(squad_wiped) or (c_count >= 4)

        if isinstance(hull_ratio, bool) or not isinstance(hull_ratio, (int, float)) or math.isnan(float(hull_ratio)):
            h_ratio = 1.0
        else:
            h_ratio = max(0.0, min(1.0, float(hull_ratio)))
        self.last_hull_ratio = h_ratio

        self._post_sortie_stats_recorded = True

    def get_ready_room_morale_state(self) -> str:
        """Determine the current Viper Squad morale state ('replacements', 'casualties', 'flawless')."""
        if self.last_squad_wiped or self.last_casualties_count >= 4:
            return "replacements"
        elif self.last_casualties_count > 0:
            return "casualties"
        else:
            return "flawless"

    def resolve_npc_dialogue(self, npc_id: str) -> Optional[DialogueNode]:
        """Resolve the active dialogue beat for an NPC based on campaign progress and morale."""
        if npc_id is None or isinstance(npc_id, bool) or not isinstance(npc_id, str):
            return None

        clean_id = npc_id.strip().lower()
        if not clean_id:
            return None

        # Direct shortcuts for Ready Room / Hangar debriefs
        if clean_id in ("viper_squad", "ready_room_debrief", "viper_debrief"):
            return get_debrief_dialogue_node(self.last_casualties_count, self.last_squad_wiped)
        if clean_id == "sortie_1_hangar_debrief":
            return get_dialogue_node("sortie_1_hangar_debrief")

        profile = get_ship_npc_profile(clean_id)
        if profile is None:
            return None

        act = max(1, int(getattr(self.story_manager, "current_act", 1)))
        sortie = max(1, int(getattr(self.story_manager, "current_sortie", 1)))

        # Bridge Personnel
        if profile.npc_id == "npc_reiner":
            if act >= 2 or sortie >= 2:
                return get_dialogue_node("bridge_reiner_scrutiny")
            return get_dialogue_node("sortie_1_briefing")

        if profile.npc_id == "npc_vance":
            return get_dialogue_node("bridge_vance_logistics")

        # Hangar Personnel
        if profile.npc_id == "npc_ortiz":
            return get_dialogue_node("hangar_ortiz_maintenance")

        # Ready Room (Viper Squad)
        if profile.zone == ZONE_READY_ROOM:
            if self.last_squad_wiped or self.last_casualties_count >= 4:
                return get_debrief_dialogue_node(self.last_casualties_count, True)
            if self.last_casualties_count > 0:
                return get_debrief_dialogue_node(self.last_casualties_count, False)
            if self._post_sortie_stats_recorded or sortie > 1:
                return get_debrief_dialogue_node(0, False)
            return get_dialogue_node(profile.default_node_id)

        return get_dialogue_node(profile.default_node_id)

    def _get_current_sortie_key(self) -> Tuple[int, int]:
        """Return the (act, sortie) tuple for current sortie tracking."""
        act = max(1, int(getattr(self.story_manager, "current_act", 1)))
        sortie = max(1, int(getattr(self.story_manager, "current_sortie", 1)))
        return (act, sortie)

    def mark_node_completed(self, node_id: str) -> None:
        """Mark a dialogue node as completed in the current sortie."""
        if isinstance(node_id, str) and node_id.strip():
            key = self._get_current_sortie_key()
            self._completed_nodes_by_sortie.setdefault(key, set()).add(node_id.strip())

    def is_node_completed_in_current_sortie(self, node_id: str) -> bool:
        """Check whether a dialogue node has already been completed in the current sortie."""
        if node_id is None or isinstance(node_id, bool) or not isinstance(node_id, str):
            return False

        clean_node_id = node_id.strip()
        if not clean_node_id:
            return False

        key = self._get_current_sortie_key()
        if clean_node_id in self._completed_nodes_by_sortie.get(key, set()):
            return True

        act, sortie = key
        history = getattr(self.story_manager, "dialogue_history", [])
        for entry in history:
            if isinstance(entry, dict) and entry.get("node") == clean_node_id:
                if "sortie" in entry:
                    entry_act = entry.get("act", 1)
                    entry_sortie = entry.get("sortie", 1)
                    if entry_act == act and entry_sortie == sortie:
                        return True
                else:
                    if (act, sortie) == (1, 1):
                        return True

        return False

    def record_npc_choice(self, node_id: str, stance: str) -> Optional[DialogueOption]:
        """Record pilot stance choice on an NPC dialogue node, guarding against duplicate farming."""
        if self.is_node_completed_in_current_sortie(node_id):
            return None

        option = self.story_manager.record_choice(node_id, stance)
        if option is not None:
            self.mark_node_completed(node_id)

        return option

    # -------------------------------------------------------------------------
    # Shipboard Dialogue Modal Controls (Issue #59)
    # -------------------------------------------------------------------------
    def open_npc_dialogue(self, npc_id: str) -> Optional[DialogueNode]:
        """Open the interactive dialogue modal for an NPC and initialize typewriter state."""
        node = self.resolve_npc_dialogue(npc_id)
        if node is None:
            return None

        prof = get_ship_npc_profile(npc_id)
        self.active_npc_id = prof.npc_id if prof else npc_id.strip().lower()
        self.active_dialogue_node = node
        self._dialogue_open = True
        self.hovered_stance = None
        self.hovered_continue = False

        if self.is_node_completed_in_current_sortie(node.node_id):
            self.dialogue_completed_mode = True
            # Find previous stance recorded in dialogue history
            prev_stance = "neutral"
            history = getattr(self.story_manager, "dialogue_history", [])
            for entry in reversed(history):
                if isinstance(entry, dict) and entry.get("node") == node.node_id:
                    prev_stance = entry.get("stance", "neutral")
                    break
            self.selected_stance = prev_stance
            self.selected_option = node.options.get(prev_stance)
            self.response_text = self.selected_option.response if self.selected_option else ""
            self.typewriter_chars = float(len(node.prompt))
        else:
            self.dialogue_completed_mode = False
            self.selected_stance = None
            self.selected_option = None
            self.response_text = None
            self.typewriter_chars = 0.0

        self._rebuild_modal_cache()
        return node

    def select_dialogue_stance(self, stance: str) -> Optional[DialogueOption]:
        """Choose an ideological stance in the active dialogue modal and apply loyalty delta."""
        if (
            not self._dialogue_open
            or self.active_dialogue_node is None
            or self.dialogue_completed_mode
            or self.selected_option is not None
        ):
            return None

        clean_stance = (stance or "").strip().lower()
        opt = self.record_npc_choice(self.active_dialogue_node.node_id, clean_stance)
        if opt is None:
            return None

        self.selected_stance = opt.stance
        self.selected_option = opt
        self.response_text = opt.response
        self.dialogue_completed_mode = True
        self.typewriter_chars = float(len(self.active_dialogue_node.prompt))
        self._play_ui_sound("ui_click")
        self._rebuild_modal_cache()
        return opt

    def close_dialogue(self) -> None:
        """Close the active dialogue modal and restore normal deck navigation."""
        self._dialogue_open = False
        self.active_npc_id = None
        self.active_dialogue_node = None
        self.selected_option = None
        self.selected_stance = None
        self.response_text = None
        self.dialogue_completed_mode = False
        self.typewriter_chars = 0.0
        self.hovered_stance = None
        self.hovered_continue = False
        self._modal_text_cache.clear()
        self._modal_prompt_lines.clear()
        self._modal_prompt_full_lines.clear()
        keys_to_clear = [k for k in self._cached_dynamic_surfaces if k.startswith("typewriter_")]
        for k in keys_to_clear:
            self._cached_dynamic_surfaces.pop(k, None)

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
            self.close_dialogue()
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
        if (
            not isinstance(dt, bool)
            and isinstance(dt, (int, float))
            and math.isfinite(dt)
            and 0.0 < dt < 10.0
        ):
            self.ambient_timer = (self.ambient_timer + float(dt)) % 3600.0
            if self._dialogue_open and self.active_dialogue_node is not None:
                target_len = float(len(self.active_dialogue_node.prompt))
                if self.typewriter_chars < target_len:
                    self.typewriter_chars = min(
                        target_len,
                        self.typewriter_chars + self.typewriter_speed * float(dt),
                    )

    def handle_event(
        self,
        event: pygame.event.Event,
        mouse_pos: Optional[Tuple[int, int]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Process keyboard hotkeys and mouse clicks for hub navigation and dialogue modal."""
        pos = mouse_pos if mouse_pos is not None else getattr(event, "pos", None)

        if self._dialogue_open:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.close_dialogue()
                    return {"action": "close_dialogue"}
                elif event.key in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_KP_ENTER):
                    if self.active_dialogue_node and self.typewriter_chars < len(self.active_dialogue_node.prompt):
                        self.typewriter_chars = float(len(self.active_dialogue_node.prompt))
                        return {"action": "skip_typewriter"}
                    elif self.dialogue_completed_mode or self.selected_option is not None:
                        self.close_dialogue()
                        return {"action": "close_dialogue"}
                    return None
                elif event.key in (pygame.K_1, pygame.K_KP1, pygame.K_2, pygame.K_KP2, pygame.K_3, pygame.K_KP3):
                    if not self.dialogue_completed_mode and self.selected_option is None:
                        stance_map = {
                            pygame.K_1: "loyal",
                            pygame.K_KP1: "loyal",
                            pygame.K_2: "neutral",
                            pygame.K_KP2: "neutral",
                            pygame.K_3: "dissident",
                            pygame.K_KP3: "dissident",
                        }
                        stance_key = stance_map.get(event.key, "neutral")
                        if self.active_dialogue_node:
                            self.typewriter_chars = float(len(self.active_dialogue_node.prompt))
                        opt = self.select_dialogue_stance(stance_key)
                        if opt is not None and self.active_dialogue_node is not None:
                            return {
                                "action": "dialogue_choice",
                                "node_id": self.active_dialogue_node.node_id,
                                "stance": opt.stance,
                                "loyalty_delta": opt.loyalty_delta,
                                "option": opt,
                            }
                    return None
                # Block all other keyboard shortcuts while modal is open
                return None

            elif event.type == pygame.MOUSEMOTION and pos is not None:
                new_stance = None
                for stance_key, rect in self.modal_option_rects.items():
                    if rect.collidepoint(pos):
                        new_stance = stance_key
                        break
                self.hovered_stance = new_stance
                self.hovered_continue = bool(self.modal_continue_rect.collidepoint(pos))

            elif event.type == pygame.MOUSEBUTTONDOWN and getattr(event, "button", 1) == 1 and pos is not None:
                # 1. Continue button click
                if (self.dialogue_completed_mode or self.selected_option is not None) and self.modal_continue_rect.collidepoint(pos):
                    self.close_dialogue()
                    return {"action": "close_dialogue"}

                # 2. Stance option card click (strict priority over any background elements)
                if not self.dialogue_completed_mode and self.selected_option is None:
                    for stance_key, rect in self.modal_option_rects.items():
                        if rect.collidepoint(pos):
                            if self.active_dialogue_node:
                                self.typewriter_chars = float(len(self.active_dialogue_node.prompt))
                            opt = self.select_dialogue_stance(stance_key)
                            if opt is not None and self.active_dialogue_node is not None:
                                return {
                                    "action": "dialogue_choice",
                                    "node_id": self.active_dialogue_node.node_id,
                                    "stance": opt.stance,
                                    "loyalty_delta": opt.loyalty_delta,
                                    "option": opt,
                                }

                # 3. Only switch NPC if clicking on a deck card strictly OUTSIDE the modal window
                if not self.modal_rect.collidepoint(pos):
                    for npc in self.get_zone_npcs():
                        if npc.npc_id != self.active_npc_id:
                            card_rect = self.npc_card_rects.get(npc.npc_id)
                            if card_rect is not None and card_rect.collidepoint(pos):
                                self._play_ui_sound("ui_click")
                                node = self.open_npc_dialogue(npc.npc_id)
                                return {
                                    "action": "interact_npc",
                                    "npc_id": npc.npc_id,
                                    "node": node,
                                }

            return None

        # --- Standard Hub Deck Event Processing (Modal closed) ---
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

            for npc in self.get_zone_npcs():
                card_rect = self.npc_card_rects.get(npc.npc_id)
                if card_rect is not None and card_rect.collidepoint(pos):
                    self._play_ui_sound("ui_click")
                    node = self.open_npc_dialogue(npc.npc_id)
                    return {
                        "action": "interact_npc",
                        "npc_id": npc.npc_id,
                        "node": node,
                    }

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
            elif event.key in (pygame.K_e,):
                zone_npcs = self.get_zone_npcs()
                if zone_npcs:
                    self._play_ui_sound("ui_click")
                    node = self.open_npc_dialogue(zone_npcs[0].npc_id)
                    return {
                        "action": "interact_npc",
                        "npc_id": zone_npcs[0].npc_id,
                        "node": node,
                    }
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
        ry = self.content_panel_rect.y + 16
        if code_surf:
            surface.blit(code_surf, (rx, ry))
            ry += code_surf.get_height() + 4
        if desc_surf:
            surface.blit(desc_surf, (rx, ry))

        # Tactical deck wireframe accents (drawn directly onto surface, 0 allocation)
        inner_rect = pygame.Rect(
            self.content_panel_rect.x + 20,
            self.content_panel_rect.y + 60,
            self.content_panel_rect.width - 40,
            self.content_panel_rect.height - 80,
        )
        pygame.draw.rect(surface, (25, 40, 60), inner_rect, width=1)

        # Subtle zone-specific tactical markings & NPC personnel cards
        if self.active_zone == ZONE_BRIDGE:
            # Observation reticle & tactical grid lines
            cx = inner_rect.centerx
            cy = inner_rect.centery
            pygame.draw.line(surface, (35, 60, 85), (cx - 120, cy), (cx + 120, cy), 1)
            pygame.draw.line(surface, (35, 60, 85), (cx, cy - 80), (cx, cy + 80), 1)
            pygame.draw.circle(surface, (45, 80, 115), (cx, cy), 50, width=1)

            # Draw Bridge NPC personnel cards
            for npc_id in ("npc_reiner", "npc_vance"):
                crect = self.npc_card_rects.get(npc_id)
                if crect:
                    pygame.draw.rect(surface, (16, 24, 38), crect)
                    pygame.draw.rect(surface, (45, 75, 105), crect, width=1)
                    card_y = crect.y + 12
                    nsurf = self._cached_static_texts.get(f"npc_name_{npc_id}")
                    rsurf = self._cached_static_texts.get(f"npc_role_{npc_id}")
                    if nsurf:
                        surface.blit(nsurf, (crect.x + 14, card_y))
                        card_y += nsurf.get_height() + 4
                    if rsurf:
                        surface.blit(rsurf, (crect.x + 16, card_y))

        elif self.active_zone == ZONE_READY_ROOM:
            # Morale badge
            morale_state = self.get_ready_room_morale_state()
            cached_morale = self._cached_dynamic_surfaces.get("ready_room_morale")
            if cached_morale and cached_morale[0] == morale_state:
                morale_surf = cached_morale[1]
            else:
                m_label = f"SQUAD MORALE // {morale_state.upper()}"
                m_col = (
                    PATRIOTISM_COLOR_ZEALOT
                    if morale_state == "flawless"
                    else (
                        PATRIOTISM_COLOR_NOMINAL
                        if morale_state == "casualties"
                        else PATRIOTISM_COLOR_DISSIDENT
                    )
                )
                morale_surf = (
                    self.font_badge.render(m_label, True, m_col) if self.font_badge else None
                )
                if morale_surf:
                    self._cached_dynamic_surfaces["ready_room_morale"] = (morale_state, morale_surf)

            if morale_surf:
                surface.blit(morale_surf, (inner_rect.x + 14, inner_rect.y + 12))

            # 4 Pod staging slots with Viper Squad personnel
            for i in range(4):
                vid = f"viper_{i+1}"
                crect = self.npc_card_rects.get(vid)
                if crect:
                    pygame.draw.rect(surface, (18, 28, 44), crect)
                    pygame.draw.rect(surface, (35, 55, 80), crect, width=1)
                    card_y = crect.y + 14
                    nsurf = self._cached_static_texts.get(f"npc_name_{vid}")
                    rsurf = self._cached_static_texts.get(f"npc_role_{vid}")
                    if nsurf:
                        surface.blit(nsurf, (crect.x + 10, card_y))
                        card_y += nsurf.get_height() + 4
                    if rsurf:
                        surface.blit(rsurf, (crect.x + 10, card_y))

        elif self.active_zone == ZONE_HANGAR:
            # Catapult rail guide stripes
            cy = inner_rect.centery
            pygame.draw.line(surface, (255, 215, 50), (inner_rect.x + 40, cy - 20), (inner_rect.right - 40, cy - 20), 2)
            pygame.draw.line(surface, (255, 215, 50), (inner_rect.x + 40, cy + 20), (inner_rect.right - 40, cy + 20), 2)

            # Draw Chief Ortiz station card
            crect = self.npc_card_rects.get("npc_ortiz")
            if crect:
                pygame.draw.rect(surface, (16, 24, 38), crect)
                pygame.draw.rect(surface, (243, 156, 18), crect, width=1)
                card_y = crect.y + 14
                nsurf = self._cached_static_texts.get("npc_name_npc_ortiz")
                rsurf = self._cached_static_texts.get("npc_role_npc_ortiz")
                if nsurf:
                    surface.blit(nsurf, (crect.x + 14, card_y))
                    card_y += nsurf.get_height() + 4
                if rsurf:
                    surface.blit(rsurf, (crect.x + 16, card_y))

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

        # 7. Dialogue Modal Overlay (Issue #59)
        if self._dialogue_open and self.active_dialogue_node is not None:
            self._draw_dialogue_modal(surface)

    def _draw_dialogue_modal(self, surface: pygame.Surface) -> None:
        """Render the 3-choice interactive dialogue modal and typewriter prompt with 0 per-frame allocations."""
        if not self._dialogue_open or self.active_dialogue_node is None:
            return

        # 1. Darkened backdrop & Modal frame
        surface.blit(self.modal_backdrop_surface, (0, 0))
        surface.blit(self.modal_bg_surface, self.modal_rect.topleft)

        prof = get_ship_npc_profile(self.active_npc_id)
        theme_col = prof.theme_color if prof else (0, 220, 255)

        # 2. Portrait
        portrait_surf = self._get_or_create_portrait_surface(
            prof.portrait_path if prof else None,
            prof.npc_id if prof else self.active_npc_id,
            (128, 128),
        )
        surface.blit(portrait_surf, self.modal_portrait_rect.topleft)
        pygame.draw.rect(surface, theme_col, self.modal_portrait_rect, width=2)

        # 3. Header info & mode status (Right of portrait)
        info_x = self.modal_portrait_rect.right + 20
        spk_surf = self._modal_text_cache.get("speaker_name")
        if spk_surf:
            surface.blit(spk_surf, (info_x, self.modal_portrait_rect.y + 4))

        role_surf = self._modal_text_cache.get("speaker_role")
        if role_surf:
            surface.blit(role_surf, (info_x, self.modal_portrait_rect.y + 32))

        badge_surf = self._modal_text_cache.get("mode_badge")
        if badge_surf:
            surface.blit(badge_surf, (info_x, self.modal_portrait_rect.y + 54))

        # Horizontal divider between header and content stack
        divider_y = self.modal_rect.y + 160
        pygame.draw.line(
            surface,
            (35, 55, 80),
            (self.modal_rect.x + 24, divider_y),
            (self.modal_rect.right - 24, divider_y),
            1,
        )

        # 4. Prompt Text Box (Tech frame + bounded text)
        pygame.draw.rect(surface, (14, 20, 30), self.modal_prompt_rect)
        pygame.draw.rect(surface, (35, 55, 78), self.modal_prompt_rect, width=1)

        lh_prompt = self.font_modal_prompt.get_linesize() if self.font_modal_prompt else 18
        vis_chars = int(self.typewriter_chars)
        py = self.modal_prompt_rect.y + 8

        rem = vis_chars
        for line_text, lsurf in zip(self._modal_prompt_lines, self._modal_prompt_full_lines):
            if rem <= 0:
                break
            if rem >= len(line_text):
                surface.blit(lsurf, (self.modal_prompt_rect.x + 12, py))
                rem -= (len(line_text) + 1)
            else:
                reveal_w = self.font_modal_prompt.size(line_text[:rem])[0] if self.font_modal_prompt else rem * 8
                clip_box = pygame.Rect(0, 0, reveal_w, lh_prompt)
                surface.blit(lsurf, (self.modal_prompt_rect.x + 12, py), area=clip_box)
                break
            py += lh_prompt

        # 5. Response Panel (if response is active)
        if self.response_text and self.modal_response_rect.height > 0:
            pygame.draw.rect(surface, (16, 26, 38), self.modal_response_rect)
            pygame.draw.rect(surface, (0, 180, 230), self.modal_response_rect, width=1)
            cw = 10
            rx, ry = self.modal_response_rect.x, self.modal_response_rect.y
            rw = self.modal_response_rect.width
            pygame.draw.lines(surface, (0, 220, 255), False, [(rx, ry + cw), (rx, ry), (rx + cw, ry)], 1)
            pygame.draw.lines(surface, (0, 220, 255), False, [(rx + rw - cw, ry), (rx + rw - 1, ry), (rx + rw - 1, ry + cw)], 1)

            # Row 1: Reaction Header (left) & Patriotism Delta (right)
            hdr_surf = self._modal_text_cache.get("response_header")
            if hdr_surf:
                surface.blit(hdr_surf, (self.modal_response_rect.x + 14, self.modal_response_rect.y + 6))

            d_surf = self._modal_text_cache.get("response_delta")
            if d_surf:
                surface.blit(
                    d_surf,
                    (self.modal_response_rect.right - d_surf.get_width() - 14, self.modal_response_rect.y + 6),
                )

            # Row 2+: Spoken dialogue response lines (below header & delta)
            lh_resp = self.font_modal_response.get_linesize() if self.font_modal_response else 18
            resp_y = self.modal_response_rect.y + 24
            resp_surfs = self._modal_text_cache.get("response_lines", [])
            for rsurf in resp_surfs:
                surface.blit(rsurf, (self.modal_response_rect.x + 14, resp_y))
                resp_y += lh_resp

        # 6. Three Option Stance Cards (Two-Row Layout: Row 1 = Tag + Delta, Row 2 = Statement Body)
        for stance, rect in self.modal_option_rects.items():
            if self.dialogue_completed_mode:
                is_selected = (stance == self.selected_stance)
                bg_col = (20, 32, 48) if is_selected else (10, 14, 22)
                border_col = (255, 215, 50) if is_selected else (25, 38, 52)
                bw = 2 if is_selected else 1
            else:
                is_hovered = (stance == self.hovered_stance)
                bg_col = (24, 38, 58) if is_hovered else (14, 22, 34)
                border_col = (0, 220, 255) if is_hovered else (45, 75, 105)
                bw = 2 if is_hovered else 1

            pygame.draw.rect(surface, bg_col, rect)
            pygame.draw.rect(surface, border_col, rect, width=bw)

            # Row 1: Stance Tag (left) & Patriotism Delta Badge (right)
            opt_tag = self._modal_text_cache.get(f"opt_tag_{stance}")
            if opt_tag:
                surface.blit(opt_tag, (rect.x + 14, rect.y + 6))

            opt_delta = self._modal_text_cache.get(f"opt_delta_{stance}")
            if opt_delta:
                surface.blit(opt_delta, (rect.right - opt_delta.get_width() - 14, rect.y + 6))

            # Row 2: Dialogue statement body
            opt_body = self._modal_text_cache.get(f"opt_body_{stance}")
            if opt_body:
                surface.blit(opt_body, (rect.x + 14, rect.y + 24))

        # 7. Continue / End Transmission Button
        c_rect = self.modal_continue_rect
        c_hover = self.hovered_continue
        c_bg = (24, 40, 62) if c_hover else (14, 22, 34)
        c_border = (255, 215, 50) if c_hover else (0, 180, 230)
        pygame.draw.rect(surface, c_bg, c_rect)
        pygame.draw.rect(surface, c_border, c_rect, width=2 if c_hover else 1)

        c_surf = self._modal_text_cache.get("continue_btn")
        if c_surf:
            cx = c_rect.centerx - c_surf.get_width() // 2
            cy = c_rect.centery - c_surf.get_height() // 2
            surface.blit(c_surf, (cx, cy))
