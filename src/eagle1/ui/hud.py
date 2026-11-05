"""hud.py - In-game screen-space HUD renderer (Military Terminal style).

``HudRenderer`` owns the HUD fonts, text cache and the few surfaces the HUD needs. All widgets draw
inside the zones of ``eagle1.ui.hud_layout``. Text is rendered through a cache and surfaces are
allocated at init time or on state changes only, never per frame.
"""

from typing import List, Optional

import pygame

from eagle1.ui import hud_layout, theme, widgets

ADRENALINE_TEXT = "! ADRENALINE OVERDRIVE !"
ADRENALINE_PULSE_STEPS = 6
ADRENALINE_PULSE_MS = 120


class HudRenderer:
    """Draws the HUD status cluster, banners, objectives and score."""

    def __init__(self, width: int = 1280, height: int = 720) -> None:
        self.width = width
        self.height = height
        self._font_label = theme.get_font("label")
        self._font_small = theme.get_font("mono_small")
        self._font_mono = theme.get_font("mono")
        self._font_display = theme.get_font("display")
        self._ready = None not in (self._font_label, self._font_small, self._font_mono, self._font_display)
        self._cache = widgets.TextCache(512)

        self._banner_text = ""
        self._banner_surf: Optional[pygame.Surface] = None

        self._adrenaline_variants: List[pygame.Surface] = []
        if self._ready:
            for i in range(ADRENALINE_PULSE_STEPS):
                color = theme.lerp_color(theme.WARNING, theme.DANGER, i / (ADRENALINE_PULSE_STEPS - 1))
                self._adrenaline_variants.append(self._font_small.render(ADRENALINE_TEXT, True, color))

    # ------------------------------------------------------------ status cluster
    def draw_status_panel(
        self,
        surface: pygame.Surface,
        shield: float,
        max_shield: float,
        overshield: bool,
        hull: float,
        max_hull: float,
        critical_hull: float,
        wave: Optional[int],
        max_waves: Optional[int],
        hostiles: Optional[int],
    ) -> None:
        """Shield and hull gauges plus the wave/hostile row (wave row hidden when ``wave`` is None)."""
        if not self._ready:
            return
        rect = hud_layout.STATUS_PANEL
        widgets.draw_panel(surface, rect)
        inner_x = rect.x + 12
        inner_w = rect.w - 24
        cache = self._cache

        rows = (
            ("SHIELD", f"{int(shield)}/{int(max_shield)}", shield / max(1.0, max_shield),
             theme.ACCENT if overshield else theme.INFO, 10, rect.y + 4),
            ("HULL", f"{int(hull)}/{int(max_hull)}", hull / max(1.0, max_hull),
             theme.DANGER if hull <= critical_hull else theme.SUCCESS, max(1, int(max_hull)), rect.y + 34),
        )
        for label, value, ratio, color, segments, top in rows:
            surface.blit(cache.render(self._font_label, label, theme.TEXT_MUTED), (inner_x, top))
            value_surf = cache.render(self._font_small, value, theme.TEXT)
            surface.blit(value_surf, (rect.right - 12 - value_surf.get_width(), top + 3))
            widgets.draw_bar(surface, pygame.Rect(inner_x, top + 21, inner_w, 8), ratio, color, segments=segments)

        if wave is not None:
            wave_text = f"WAVE {wave}" if (max_waves is None or max_waves >= 999) else f"WAVE {wave}/{max_waves}"
            surface.blit(cache.render(self._font_small, wave_text, theme.ACCENT), (inner_x, rect.y + 66))
            hostile_count = hostiles or 0
            hostile_surf = cache.render(
                self._font_small, f"HOSTILES {hostile_count}", theme.DANGER if hostile_count > 0 else theme.SUCCESS
            )
            surface.blit(hostile_surf, (rect.right - 12 - hostile_surf.get_width(), rect.y + 66))

    def draw_adrenaline(self, surface: pygame.Surface, ticks_ms: int, rect: Optional[pygame.Rect] = None) -> None:
        """Pulsing warning plate shown at critical hull."""
        if not self._ready:
            return
        rect = rect or hud_layout.ADRENALINE_RECT
        widgets.draw_panel(surface, rect, theme.lerp_color(theme.PANEL, theme.DANGER, 0.25), theme.DANGER, brackets=False)
        variant = self._adrenaline_variants[(ticks_ms // ADRENALINE_PULSE_MS) % ADRENALINE_PULSE_STEPS]
        surface.blit(variant, variant.get_rect(center=rect.center))

    def draw_wave_banner(self, surface: pygame.Surface, text: str) -> None:
        """Centered wave announcement; the banner surface is rebuilt only when the text changes."""
        if not self._ready or not text:
            return
        if text != self._banner_text or self._banner_surf is None:
            label = self._font_display.render(text, True, theme.ACCENT)
            surf = pygame.Surface((label.get_width() + 60, label.get_height() + 30), pygame.SRCALPHA)
            surf.fill(theme.with_alpha(theme.PANEL, 220))
            widgets.draw_panel(surf, surf.get_rect(), None, theme.ACCENT, theme.ACCENT)
            surf.blit(label, (30, 15))
            self._banner_text = text
            self._banner_surf = surf
        surface.blit(self._banner_surf, self._banner_surf.get_rect(center=hud_layout.WAVE_BANNER_CENTER))

    # --------------------------------------------------------------- objectives
    def draw_objective_banner(self, surface: pygame.Surface, text: str, color: theme.RGB) -> None:
        """Mission objective plate at the top center."""
        if not self._ready:
            return
        label = self._cache.render(self._font_label, text, color)
        rect = pygame.Rect(0, hud_layout.OBJECTIVE_BANNER_Y, label.get_width() + 28, 24)
        rect.centerx = self.width // 2
        widgets.draw_panel(surface, rect, theme.PANEL, color, brackets=False)
        surface.blit(label, label.get_rect(center=rect.center))

    def draw_campaign_objective(self, surface: pygame.Surface, objective_surf: pygame.Surface) -> None:
        """Campaign narrative objective plate (surface supplied by the game, already cached)."""
        rect = pygame.Rect(0, hud_layout.CAMPAIGN_OBJECTIVE_Y, objective_surf.get_width() + 20, 22)
        rect.centerx = self.width // 2
        widgets.draw_panel(surface, rect, theme.PANEL, theme.BORDER_STRONG, brackets=False)
        surface.blit(objective_surf, objective_surf.get_rect(center=rect.center))

    def draw_score(self, surface: pygame.Surface, score: int, highscore: int) -> None:
        """Score and best score, stacked at the bottom center."""
        if not self._ready:
            return
        best = self._cache.render(self._font_small, f"BEST {highscore:,}", theme.TEXT_MUTED)
        score_surf = self._cache.render(self._font_mono, f"SCORE {score:,}", theme.TEXT)
        anchor_x, anchor_y = hud_layout.SCORE_ANCHOR
        best_rect = best.get_rect(midbottom=(anchor_x, anchor_y))
        surface.blit(best, best_rect)
        surface.blit(score_surf, score_surf.get_rect(midbottom=(anchor_x, best_rect.top)))
