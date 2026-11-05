"""
debriefing_screen.py - Mission Accomplished & After-Action Debriefing Screen.

Renders an interactive, comprehensive post-mission tactical debriefing interface
displaying mission performance stats, combat rank, high scores, squad survival,
and navigation options (Replay, Hub, Mission Select, Main Menu).

All text is rendered once in ``set_results`` (static cache); ``draw`` only blits, draws
panels and handles hover/focus, so there is no per-frame text or surface work.
"""

import math
from typing import List, Tuple

import pygame

from eagle1.ui import theme, widgets
from eagle1.ui.layout import VerticalStackLayout
from eagle1.ui.menu_nav import MenuButton, MenuNavigator, VARIANT_DANGER, VARIANT_PRIMARY

RANK_CITATIONS = {
    "S": "Heroic service to Super Earth. Flawless CAS.",
    "A": "Exemplary air-ground tactical coordination.",
    "B": "Combat objectives achieved with squad support.",
    "C": "Operation survived under heavy attrition.",
}

ACTION_REPLAY = "replay"
ACTION_HUB = "super_destroyer"
ACTION_SELECT = "mission_select"
ACTION_MENU = "main_menu"
# Visual left-to-right order of the bottom buttons.
BUTTON_ACTIONS = (ACTION_REPLAY, ACTION_HUB, ACTION_SELECT, ACTION_MENU)
DEFAULT_FOCUS_INDEX = 1  # ENTER keeps returning to the hub


class DebriefingScreen:
    """Displays comprehensive post-mission statistics, combat evaluation,
    and interactive replay/menu options upon mission completion.
    """

    def __init__(self, screen_w=1280, screen_h=720, audio_manager=None):
        self.screen_w = screen_w
        self.screen_h = screen_h
        self.is_active = False
        self.audio_manager = audio_manager
        sfx = audio_manager.play_sfx if audio_manager is not None else None

        self.results = {}
        self.rank_letter = "B"
        self.rank_title = "PATRIOT VANGUARD"
        self.rank_color = theme.INFO

        # Pre-allocated surfaces for 60 FPS performance
        self.overlay_surface = widgets.make_overlay((self.screen_w, self.screen_h), theme.OVERLAY_RGBA)
        self.panel_rect = pygame.Rect(90, 45, self.screen_w - 180, self.screen_h - 90)

        # Button definitions (x, y, w, h)
        by = self.panel_rect.bottom - 65
        bw = 250
        gap = 16
        start_bx = self.panel_rect.centerx - (4 * bw + 3 * gap) // 2

        self.btn_replay_rect = pygame.Rect(start_bx, by, bw, 46)
        self.btn_hub_rect = pygame.Rect(start_bx + bw + gap, by, bw, 46)
        self.btn_select_rect = pygame.Rect(start_bx + 2 * (bw + gap), by, bw, 46)
        self.btn_menu_rect = pygame.Rect(start_bx + 3 * (bw + gap), by, bw, 46)

        self._buttons = [
            MenuButton("REPLAY", self.btn_replay_rect, hotkey="R", variant=VARIANT_PRIMARY, on_sfx=sfx),
            MenuButton("RETURN TO HUB", self.btn_hub_rect, hotkey="H", on_sfx=sfx),
            MenuButton("MISSIONS", self.btn_select_rect, hotkey="SPACE", on_sfx=sfx),
            MenuButton("MAIN MENU", self.btn_menu_rect, hotkey="ESC", variant=VARIANT_DANGER, on_sfx=sfx),
        ]
        self._nav = MenuNavigator(self._buttons, wrap=True, on_sfx=sfx)
        self._nav.focus(DEFAULT_FOCUS_INDEX)

        # Fonts cache
        self.font_huge = None
        self.font_title = None
        self.font_large = None
        self.font_med = None
        self.font_small = None
        self._init_fonts()

        # Layout of the left/right columns (computed once)
        panel = self.panel_rect
        self._head_y = panel.top + 18
        self._div_y = self._head_y + 70
        col_y = self._div_y + 20
        lx = panel.left + 40
        lw = 340
        self.score_box = pygame.Rect(lx, col_y, lw, 140)
        self.rank_box = pygame.Rect(lx, col_y + 155, lw, 190)
        rx = lx + lw + 30
        self.stats_box = pygame.Rect(rx, col_y, panel.right - rx - 40, 345)

        # Static render cache (rebuilt in set_results)
        self._static_blits: List[Tuple[pygame.Surface, Tuple[int, int]]] = []
        self._record_variants: List[pygame.Surface] = []
        self._record_pos: Tuple[int, int] = (0, 0)

    def _init_fonts(self):
        """Fetches the cached theme fonts (None if the font module is unavailable)."""
        self.font_huge = theme.get_font("display_xl")
        self.font_title = theme.get_font("title")
        self.font_large = theme.get_font("heading")
        self.font_med = theme.get_font("mono")
        self.font_small = theme.get_font("mono_small")
        self._fonts_ready = None not in (
            self.font_huge, self.font_title, self.font_large, self.font_med, self.font_small
        )

    def set_results(self, results):
        """Prepares debriefing statistics and computes combat rank."""
        if not isinstance(results, dict):
            raw_results = {}
        else:
            raw_results = results

        def _safe_int(val, default=0, min_val=0):
            if isinstance(val, bool) or not isinstance(val, (int, float)):
                return default
            try:
                f_val = float(val)
                if not math.isfinite(f_val):
                    return default
                return max(min_val, int(f_val))
            except Exception:
                return default

        def _safe_float(val, default=0.0, min_val=0.0):
            if isinstance(val, bool) or not isinstance(val, (int, float)):
                return default
            try:
                f_val = float(val)
                if not math.isfinite(f_val):
                    return default
                return max(min_val, f_val)
            except Exception:
                return default

        score = _safe_int(raw_results.get("final_score", 0))
        highscore = _safe_int(raw_results.get("highscore", score))
        flawless = bool(raw_results.get("flawless_squad", False))
        survivors = max(0, min(4, _safe_int(raw_results.get("survivors_count", 0))))
        casualties = max(0, min(4, _safe_int(raw_results.get("casualties_count", 4 - survivors))))
        squad_wiped = bool(raw_results.get("squad_wiped", survivors <= 0))
        hull_ratio = min(1.0, _safe_float(raw_results.get("hull_ratio", 1.0)))

        self.results = {
            "mission_name": str(raw_results.get("mission_name", "OPERATION")),
            "final_score": score,
            "highscore": highscore,
            "is_new_highscore": bool(raw_results.get("is_new_highscore", score >= highscore and score > 0)),
            "duration_seconds": _safe_float(raw_results.get("duration_seconds", 0.0)),
            "waves_cleared": _safe_int(raw_results.get("waves_cleared", 1), min_val=1),
            "aerial_kills": _safe_int(raw_results.get("aerial_kills", 0)),
            "bomber_kills": _safe_int(raw_results.get("bomber_kills", 0)),
            "cas_kills": _safe_int(raw_results.get("cas_kills", 0)),
            "fabricators_destroyed": _safe_int(raw_results.get("fabricators_destroyed", 0)),
            "strider_destroyed": bool(raw_results.get("strider_destroyed", False)),
            "survivors_count": survivors,
            "casualties_count": casualties,
            "squad_wiped": squad_wiped,
            "hull_ratio": hull_ratio,
            "flawless_squad": flawless,
            "hero_score": _safe_int(raw_results.get("hero_score", 0)),
        }
        self.is_active = True

        # Compute Military Combat Rank
        if (flawless and score >= 6000) or score >= 10000:
            self.rank_letter = "S"
            self.rank_title = "HERO OF SUPER EARTH"
            self.rank_color = theme.ACCENT
        elif score >= 6500 or (survivors >= 3 and score >= 4500):
            self.rank_letter = "A"
            self.rank_title = "CHIEF MARSHAL"
            self.rank_color = theme.SUCCESS
        elif score >= 3500:
            self.rank_letter = "B"
            self.rank_title = "PATRIOT VANGUARD"
            self.rank_color = theme.INFO
        else:
            self.rank_letter = "C"
            self.rank_title = "COMBAT SURVIVOR"
            self.rank_color = theme.TEXT_MUTED

        self._nav.focus(DEFAULT_FOCUS_INDEX)
        self._build_static_cache()

    def close(self):
        """Deactivate debriefing screen and clear active state."""
        self.is_active = False

    # ------------------------------------------------------------------ cache
    def _stat_entries(self):
        r = self.results
        duration_s = int(r.get("duration_seconds", 0))
        strat_targets = []
        if r.get("strider_destroyed", False):
            strat_targets.append("1 Factory Strider Defeated")
        if r.get("fabricators_destroyed", 0) > 0:
            strat_targets.append(f"{r['fabricators_destroyed']} Automaton Fabricators Demolished")
        survivors = r.get("survivors_count", 0)
        if r.get("flawless_squad", False):
            squad_desc, squad_col = "4 / 4 EXTRACTED (FLAWLESS SQUAD BONUS +500)", theme.SUCCESS
        else:
            squad_desc = f"{survivors} / 4 Helldivers Extracted"
            squad_col = theme.ACCENT if survivors > 0 else theme.DANGER
        return [
            ("Operational Mission Time:", f"{duration_s // 60:02d}m {duration_s % 60:02d}s", theme.TEXT),
            ("Wave Progression:", f"{r.get('waves_cleared', 1)} Waves Completed", theme.TEXT),
            ("Automaton Aerial Hostiles Neutralized:", f"{r.get('aerial_kills', 0)} Craft Downed", theme.ACCENT),
            ("Heavy Armor-Class Bombers Neutralized:", f"{r.get('bomber_kills', 0)} Bombers Destroyed", theme.WARNING),
            ("Strategic Infrastructure:", ", ".join(strat_targets) if strat_targets else "Airspace Cleansed", theme.INFO),
            ("Close Air Support (CAS) Assists:", f"{r.get('cas_kills', 0)} Enemy Ground Forces Hit", theme.SUCCESS),
            ("Viper Helldiver Squad Status:", squad_desc, squad_col),
            ("Stratagem Hero Minigame Bonus:", f"+{r.get('hero_score', 0)} Bonus Points", theme.ACCENT),
        ]

    def _layout_stats(self, font):
        """Lay out the stat rows with ``font``; returns (blits, fits_in_box)."""
        box = self.stats_box
        inner = pygame.Rect(box.x, box.y + 28, box.w, box.h - 28)  # first row lands at box.top + 52
        layout = VerticalStackLayout(inner, padding=24, default_gap=14)
        width = inner.w - 48
        line_h = font.get_linesize()
        blits = []
        for label, value, color in self._stat_entries():
            label_surf = font.render(label, True, theme.TEXT_MUTED)
            value_w = font.size(value)[0]
            if label_surf.get_width() + value_w + 24 <= width:
                slot = layout.add_slot(line_h)
                blits.append((label_surf, (slot.x, slot.y)))
                value_surf = font.render(value, True, color)
                blits.append((value_surf, (slot.right - value_surf.get_width(), slot.y)))
            else:
                lines = widgets.wrap_text_px(font, value, width, max_lines=2)
                slot = layout.add_slot(line_h * (1 + len(lines)) + 2)
                blits.append((label_surf, (slot.x, slot.y)))
                for i, line in enumerate(lines):
                    blits.append((font.render(line, True, color), (slot.x, slot.y + (i + 1) * line_h + 2)))
        fits = layout.cursor_y <= inner.bottom - layout.padding
        return blits, fits

    def _build_static_cache(self):
        """Render every unchanging text once; called from set_results."""
        self._static_blits = []
        self._record_variants = []
        if not self._fonts_ready:
            return
        panel, score_box, rank_box, stats_box = self.panel_rect, self.score_box, self.rank_box, self.stats_box
        blits = self._static_blits

        def centered(surf, cx, y):
            blits.append((surf, (cx - surf.get_width() // 2, y)))

        status = self.font_title.render("// MISSION ACCOMPLISHED //", True, theme.SUCCESS)
        centered(status, panel.centerx, self._head_y)
        m_name = self.results.get("mission_name", "OPERATION").upper()
        sub = widgets.fit_text(self.font_large, f"SES SUPER DESTROYER // AFTER-ACTION DEBRIEFING: {m_name}", panel.w - 80)
        centered(self.font_large.render(sub, True, theme.ACCENT), panel.centerx, self._head_y + 36)

        final_score = self.results.get("final_score", 0)
        centered(self.font_small.render("FINAL OPERATIONAL SCORE", True, theme.TEXT_MUTED), score_box.centerx, score_box.top + 14)
        centered(self.font_huge.render(f"{final_score:,} PTS", True, theme.ACCENT), score_box.centerx, score_box.top + 42)
        if self.results.get("is_new_highscore", False):
            for i in range(8):
                color = theme.lerp_color(theme.WARNING, theme.ACCENT, i / 7.0)
                self._record_variants.append(self.font_large.render("// NEW ALL-TIME RECORD! //", True, color))
            self._record_pos = (
                score_box.centerx - self._record_variants[0].get_width() // 2, score_box.bottom - 34,
            )
        else:
            hs_val = self.results.get("highscore", final_score)
            centered(self.font_small.render(f"ALL-TIME BEST: {hs_val:,} PTS", True, theme.INFO), score_box.centerx, score_box.bottom - 30)

        centered(self.font_small.render("COMBAT READINESS EVALUATION", True, theme.TEXT_MUTED), rank_box.centerx, rank_box.top + 14)
        centered(self.font_huge.render(f"RANK {self.rank_letter}", True, self.rank_color), rank_box.centerx, rank_box.top + 48)
        centered(self.font_large.render(self.rank_title, True, theme.TEXT), rank_box.centerx, rank_box.top + 112)
        citation = RANK_CITATIONS.get(self.rank_letter, "Duty honored.")
        for i, line in enumerate(widgets.wrap_text_px(self.font_small, citation, rank_box.w - 24, max_lines=2)):
            centered(self.font_small.render(line, True, theme.TEXT_MUTED), rank_box.centerx, rank_box.bottom - 48 + i * 17)

        blits.append((self.font_large.render("OPERATIONAL PERFORMANCE METRICS", True, theme.INFO), (stats_box.left + 24, stats_box.top + 16)))
        stat_blits, fits = self._layout_stats(self.font_med)
        if not fits:
            stat_blits, _ = self._layout_stats(self.font_small)
        blits.extend(stat_blits)

    # ----------------------------------------------------------------- events
    def handle_event(self, event, mouse_pos=None):
        """Processes keyboard hotkeys and mouse button clicks."""
        if not self.is_active:
            return None

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_r:
                return ACTION_REPLAY
            elif event.key == pygame.K_h:
                return ACTION_HUB
            elif event.key == pygame.K_SPACE:
                return ACTION_SELECT
            elif event.key == pygame.K_ESCAPE:
                return ACTION_MENU
            elif event.key == pygame.K_LEFT:
                self._nav.move_focus(-1)
            elif event.key == pygame.K_RIGHT:
                self._nav.move_focus(1)
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                if self.audio_manager is not None:
                    self.audio_manager.play_sfx("ui_click")
                return BUTTON_ACTIONS[self._nav.focus_index]

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mpos = mouse_pos if mouse_pos is not None else pygame.mouse.get_pos()
            for action, button in zip(BUTTON_ACTIONS, self._buttons):
                if button.rect.collidepoint(mpos):
                    if self.audio_manager is not None:
                        self.audio_manager.play_sfx("ui_click")
                    return action

        return None

    # ------------------------------------------------------------------- draw
    def draw(self, canvas, mouse_pos=None):
        """Renders the comprehensive mission debriefing interface."""
        if not self.is_active:
            return

        mpos = mouse_pos if mouse_pos is not None else pygame.mouse.get_pos()
        panel = self.panel_rect

        canvas.blit(self.overlay_surface, (0, 0))
        widgets.draw_panel(canvas, panel, theme.PANEL, theme.BORDER_STRONG, theme.ACCENT)
        if not self._fonts_ready:
            return

        div_y = self._div_y
        pygame.draw.line(canvas, theme.BORDER, (panel.left + 30, div_y), (panel.right - 30, div_y), 2)
        pygame.draw.rect(canvas, theme.INFO, (panel.centerx - 4, div_y - 4, 8, 8))

        widgets.draw_panel(canvas, self.score_box, theme.PANEL_RAISED, theme.BORDER_STRONG, brackets=False)
        widgets.draw_panel(canvas, self.rank_box, theme.PANEL_RAISED, self.rank_color, self.rank_color)
        widgets.draw_panel(canvas, self.stats_box, theme.PANEL_RAISED, theme.BORDER, brackets=False)

        for surf, pos in self._static_blits:
            canvas.blit(surf, pos)
        if self._record_variants:
            variant = self._record_variants[(pygame.time.get_ticks() // 80) % len(self._record_variants)]
            canvas.blit(variant, self._record_pos)

        for i, button in enumerate(self._buttons):
            if button.is_hovered(mpos):
                self._nav.focus(i)
        self._nav.draw(canvas, mpos)
