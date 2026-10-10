"""
debriefing_screen.py - Mission Accomplished & After-Action Debriefing Screen.

Renders an interactive, comprehensive post-mission tactical debriefing interface
displaying mission performance stats, combat rank, high scores, squad survival,
and navigation options (Replay, Mission Select, Main Menu).
"""

import math
import pygame


class DebriefingScreen:
    """Displays comprehensive post-mission statistics, combat evaluation,
    and interactive replay/menu options upon mission completion.
    """

    def __init__(self, screen_w=1280, screen_h=720):
        self.screen_w = screen_w
        self.screen_h = screen_h
        self.is_active = False

        self.results = {}
        self.rank_letter = "B"
        self.rank_title = "PATRIOT VANGUARD"
        self.rank_color = (0, 200, 255)

        # Pre-allocated surfaces for 60 FPS performance
        self.overlay_surface = pygame.Surface((self.screen_w, self.screen_h), pygame.SRCALPHA)
        self.panel_rect = pygame.Rect(90, 45, self.screen_w - 180, self.screen_h - 90)

        # Button definitions (x, y, w, h)
        by = self.panel_rect.bottom - 65
        bw = 270
        gap = 40
        start_bx = self.panel_rect.centerx - (3 * bw + 2 * gap) // 2

        self.btn_replay_rect = pygame.Rect(start_bx, by, bw, 46)
        self.btn_select_rect = pygame.Rect(start_bx + bw + gap, by, bw, 46)
        self.btn_menu_rect = pygame.Rect(start_bx + 2 * (bw + gap), by, bw, 46)

        # Fonts cache
        self.font_huge = None
        self.font_title = None
        self.font_large = None
        self.font_med = None
        self.font_small = None
        self._init_fonts()

    def _init_fonts(self):
        """Initializes and caches UI fonts."""
        if not pygame.font.get_init():
            try:
                pygame.font.init()
            except Exception:
                return

        try:
            self.font_huge = pygame.font.SysFont("impact,arial", 44) or pygame.font.Font(None, 52)
            self.font_title = pygame.font.SysFont("impact,arial", 28) or pygame.font.Font(None, 34)
            self.font_large = pygame.font.SysFont("consolas,menlo,monaco,courier,arial", 20, bold=True) or pygame.font.Font(None, 26)
            self.font_med = pygame.font.SysFont("consolas,menlo,monaco,courier,arial", 15, bold=True) or pygame.font.Font(None, 20)
            self.font_small = pygame.font.SysFont("consolas,menlo,monaco,courier,arial", 13) or pygame.font.Font(None, 16)
        except Exception:
            self.font_huge = pygame.font.Font(None, 48)
            self.font_title = pygame.font.Font(None, 32)
            self.font_large = pygame.font.Font(None, 24)
            self.font_med = pygame.font.Font(None, 18)
            self.font_small = pygame.font.Font(None, 15)

    def set_results(self, results):
        """Prepares debriefing statistics and computes combat rank."""
        self.results = dict(results)
        self.is_active = True

        score = self.results.get("final_score", 0)
        flawless = self.results.get("flawless_squad", False)
        survivors = self.results.get("survivors_count", 0)

        # Compute Military Combat Rank
        if (flawless and score >= 6000) or score >= 10000:
            self.rank_letter = "S"
            self.rank_title = "HERO OF SUPER EARTH"
            self.rank_color = (255, 215, 50)
        elif score >= 6500 or (survivors >= 3 and score >= 4500):
            self.rank_letter = "A"
            self.rank_title = "CHIEF MARSHAL"
            self.rank_color = (0, 255, 180)
        elif score >= 3500:
            self.rank_letter = "B"
            self.rank_title = "PATRIOT VANGUARD"
            self.rank_color = (0, 210, 255)
        else:
            self.rank_letter = "C"
            self.rank_title = "COMBAT SURVIVOR"
            self.rank_color = (180, 200, 220)

    def handle_event(self, event, mouse_pos=None):
        """Processes keyboard hotkeys and mouse button clicks."""
        if not self.is_active:
            return None

        # Keyboard hotkeys
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_r:
                return "replay"
            elif event.key == pygame.K_SPACE:
                return "mission_select"
            elif event.key == pygame.K_ESCAPE:
                return "main_menu"

        # Mouse clicks
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mpos = mouse_pos if mouse_pos is not None else pygame.mouse.get_pos()
            if self.btn_replay_rect.collidepoint(mpos):
                return "replay"
            elif self.btn_select_rect.collidepoint(mpos):
                return "mission_select"
            elif self.btn_menu_rect.collidepoint(mpos):
                return "main_menu"

        return None

    def draw(self, canvas, mouse_pos=None):
        """Renders the comprehensive mission debriefing interface."""
        if not self.is_active:
            return

        mpos = mouse_pos if mouse_pos is not None else pygame.mouse.get_pos()

        # 1. Dark semi-transparent backdrop overlay
        self.overlay_surface.fill((8, 12, 20, 225))
        canvas.blit(self.overlay_surface, (0, 0))

        # 2. Main Debriefing Frame
        panel = self.panel_rect
        pygame.draw.rect(canvas, (16, 22, 34), panel, border_radius=12)
        pygame.draw.rect(canvas, (0, 200, 255), panel, 2, border_radius=12)

        # Subtle tactical corner accents
        c_len = 24
        for cx, cy, dx, dy in [
            (panel.left, panel.top, 1, 1),
            (panel.right, panel.top, -1, 1),
            (panel.left, panel.bottom, 1, -1),
            (panel.right, panel.bottom, -1, -1),
        ]:
            pygame.draw.line(canvas, (255, 215, 50), (cx, cy), (cx + dx * c_len, cy), 3)
            pygame.draw.line(canvas, (255, 215, 50), (cx, cy), (cx, cy + dy * c_len), 3)

        # 3. Top Banner & Header
        head_y = panel.top + 18
        if self.font_title:
            status_txt = self.font_title.render("★ MISSION ACCOMPLISHED ★", True, (0, 255, 180))
            canvas.blit(status_txt, (panel.centerx - status_txt.get_width() // 2, head_y))

        m_name = self.results.get("mission_name", "OPERATION").upper()
        if self.font_large:
            sub_txt = self.font_large.render(f"SES SUPER DESTROYER // AFTER-ACTION DEBRIEFING: {m_name}", True, (255, 215, 60))
            canvas.blit(sub_txt, (panel.centerx - sub_txt.get_width() // 2, head_y + 36))

        # Divider line
        div_y = head_y + 70
        pygame.draw.line(canvas, (40, 60, 90), (panel.left + 30, div_y), (panel.right - 30, div_y), 2)
        pygame.draw.circle(canvas, (0, 220, 255), (panel.centerx, div_y), 4)

        # 4. Left Column: Score Card & Rank Plate (x: panel.left + 40, w: 340)
        lx = panel.left + 40
        lw = 340
        col_y = div_y + 20

        # Score Plate Box
        score_box = pygame.Rect(lx, col_y, lw, 140)
        pygame.draw.rect(canvas, (22, 30, 46), score_box, border_radius=8)
        pygame.draw.rect(canvas, (60, 85, 120), score_box, 1, border_radius=8)

        if self.font_med:
            lbl_score = self.font_med.render("FINAL OPERATIONAL SCORE", True, (160, 190, 220))
            canvas.blit(lbl_score, (score_box.centerx - lbl_score.get_width() // 2, score_box.top + 14))

        final_score = self.results.get("final_score", 0)
        if self.font_huge:
            score_num = self.font_huge.render(f"{final_score:,} PTS", True, (255, 215, 50))
            canvas.blit(score_num, (score_box.centerx - score_num.get_width() // 2, score_box.top + 42))

        is_new_hs = self.results.get("is_new_highscore", False)
        if is_new_hs:
            pulse = int(180 + 75 * math.sin(pygame.time.get_ticks() * 0.015))
            if self.font_large:
                hs_badge = self.font_large.render("★ NEW ALL-TIME RECORD! ★", True, (255, pulse, 40))
                canvas.blit(hs_badge, (score_box.centerx - hs_badge.get_width() // 2, score_box.bottom - 34))
        else:
            hs_val = self.results.get("highscore", final_score)
            if self.font_med:
                hs_txt = self.font_med.render(f"ALL-TIME BEST: {hs_val:,} PTS", True, (0, 200, 255))
                canvas.blit(hs_txt, (score_box.centerx - hs_txt.get_width() // 2, score_box.bottom - 30))

        # Combat Rank Plate Box
        rank_box = pygame.Rect(lx, col_y + 155, lw, 190)
        pygame.draw.rect(canvas, (22, 30, 46), rank_box, border_radius=8)
        pygame.draw.rect(canvas, self.rank_color, rank_box, 2, border_radius=8)

        if self.font_med:
            lbl_eval = self.font_med.render("COMBAT READINESS EVALUATION", True, (160, 190, 220))
            canvas.blit(lbl_eval, (rank_box.centerx - lbl_eval.get_width() // 2, rank_box.top + 14))

        # Big Rank Badge Letter
        if self.font_huge:
            rank_char = self.font_huge.render(f"RANK {self.rank_letter}", True, self.rank_color)
            canvas.blit(rank_char, (rank_box.centerx - rank_char.get_width() // 2, rank_box.top + 48))

        if self.font_large:
            title_r = self.font_large.render(self.rank_title, True, (255, 255, 255))
            canvas.blit(title_r, (rank_box.centerx - title_r.get_width() // 2, rank_box.top + 105))

        if self.font_small:
            citations = {
                "S": "Heroic service to Super Earth. Flawless CAS.",
                "A": "Exemplary air-ground tactical coordination.",
                "B": "Combat objectives achieved with squad support.",
                "C": "Operation survived under heavy attrition.",
            }
            desc_r = self.font_small.render(citations.get(self.rank_letter, "Duty honored."), True, (140, 175, 200))
            canvas.blit(desc_r, (rank_box.centerx - desc_r.get_width() // 2, rank_box.bottom - 30))

        # 5. Right Column: Detailed Performance Stats Grid (x: lx + lw + 30, w: 630)
        rx = lx + lw + 30
        rw = panel.right - rx - 40
        stats_box = pygame.Rect(rx, col_y, rw, 345)
        pygame.draw.rect(canvas, (20, 28, 42), stats_box, border_radius=8)
        pygame.draw.rect(canvas, (50, 75, 110), stats_box, 1, border_radius=8)

        if self.font_large:
            grid_title = self.font_large.render("OPERATIONAL PERFORMANCE METRICS", True, (0, 220, 255))
            canvas.blit(grid_title, (stats_box.left + 24, stats_box.top + 16))

        # Performance items list
        duration_s = int(self.results.get("duration_seconds", 0))
        m_str = f"{duration_s // 60:02d}m {duration_s % 60:02d}s"
        waves_str = f"{self.results.get('waves_cleared', 1)} Waves Completed"
        air_kills = self.results.get("aerial_kills", 0)
        bomber_kills = self.results.get("bomber_kills", 0)
        cas_kills = self.results.get("cas_kills", 0)
        fabs = self.results.get("fabricators_destroyed", 0)
        strider = self.results.get("strider_destroyed", False)
        hero_score = self.results.get("hero_score", 0)

        strat_targets = []
        if strider:
            strat_targets.append("1 Factory Strider Defeated")
        if fabs > 0:
            strat_targets.append(f"{fabs} Automaton Fabricators Demolished")
        strat_str = ", ".join(strat_targets) if strat_targets else "Airspace Cleansed"

        survivors = self.results.get("survivors_count", 0)
        flawless = self.results.get("flawless_squad", False)
        
        if flawless:
            squad_desc = "4 / 4 EXTRACTED (FLAWLESS SQUAD BONUS +500)"
            squad_col = (0, 255, 180)
        else:
            squad_desc = f"{survivors} / 4 Helldivers Extracted"
            squad_col = (255, 200, 60) if survivors > 0 else (255, 80, 80)

        stat_entries = [
            ("Operational Mission Time:", m_str, (255, 255, 255)),
            ("Wave Progression:", waves_str, (255, 255, 255)),
            ("Automaton Aerial Hostiles Neutralized:", f"{air_kills} Craft Downed", (255, 220, 80)),
            ("Heavy Armor-Class Bombers Neutralized:", f"{bomber_kills} Bombers Destroyed", (255, 160, 60)),
            ("Strategic Infrastructure:", strat_str, (0, 230, 220)),
            ("Close Air Support (CAS) Assists:", f"{cas_kills} Enemy Ground Forces Hit", (0, 255, 180)),
            ("Viper Helldiver Squad Status:", squad_desc, squad_col),
            ("Stratagem Hero Minigame Bonus:", f"+{hero_score} Bonus Points", (255, 215, 50)),
        ]

        stat_y = stats_box.top + 52
        for label, val, val_col in stat_entries:
            if self.font_med:
                lbl_surf = self.font_med.render(label, True, (160, 180, 205))
                canvas.blit(lbl_surf, (stats_box.left + 24, stat_y))

                val_surf = self.font_med.render(val, True, val_col)
                canvas.blit(val_surf, (stats_box.right - val_surf.get_width() - 24, stat_y))
            stat_y += 33

        # 6. Bottom Navigation Action Buttons
        self._draw_button(canvas, self.btn_replay_rect, "[R] REPLAY MISSION", (0, 160, 90), (0, 240, 140), mpos)
        self._draw_button(canvas, self.btn_select_rect, "[SPACE] MISSION SELECT", (0, 120, 180), (0, 210, 255), mpos)
        self._draw_button(canvas, self.btn_menu_rect, "[ESC] MAIN MENU", (140, 40, 40), (240, 70, 70), mpos)

    def _draw_button(self, canvas, rect, label, base_col, border_col, mouse_pos):
        """Draws an interactive button with hover states and hotkey indicator."""
        is_hover = rect.collidepoint(mouse_pos)
        fill_col = tuple(min(255, c + 35) for c in base_col) if is_hover else base_col
        b_col = (255, 255, 255) if is_hover else border_col

        pygame.draw.rect(canvas, fill_col, rect, border_radius=6)
        pygame.draw.rect(canvas, b_col, rect, 2 if not is_hover else 3, border_radius=6)

        if self.font_large:
            txt_col = (255, 255, 255) if is_hover else (235, 240, 250)
            txt = self.font_large.render(label, True, txt_col)
            canvas.blit(txt, (rect.centerx - txt.get_width() // 2, rect.centery - txt.get_height() // 2))
