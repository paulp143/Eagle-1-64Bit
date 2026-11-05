"""hud.py - In-game screen-space HUD renderer (Military Terminal style).

``HudRenderer`` owns the HUD fonts, text cache and the few surfaces the HUD needs. All widgets draw
inside the zones of ``eagle1.ui.hud_layout``. Text is rendered through a cache and surfaces are
allocated at init time or on state changes only, never per frame.
"""

from typing import Dict, List, Optional, Tuple

import pygame

from eagle1.ui import hud_layout, theme, widgets
from eagle1.ui.controls_reference import HUD_HINT_KEYS

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

        self._minimap_size = hud_layout.MINIMAP_RECT.w
        self._minimap_surf = pygame.Surface((self._minimap_size, self._minimap_size), pygame.SRCALPHA)
        self._minimap_base: Optional[pygame.Surface] = None
        self._slowmo_overlay: Optional[pygame.Surface] = None
        self._frost_overlays: Dict[Tuple[int, int], pygame.Surface] = {}
        self._score_plate = widgets.make_overlay(hud_layout.SCORE_RECT.size, theme.with_alpha(theme.PANEL, 190))
        self._tiny_font = theme.get_font("mono_tiny")
        self._hint_surf: Optional[pygame.Surface] = self._build_hint_surface() if self._tiny_font else None

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
        surface.blit(self._score_plate, hud_layout.SCORE_RECT.topleft)
        best = self._cache.render(self._font_small, f"BEST {highscore:,}", theme.TEXT_MUTED)
        score_surf = self._cache.render(self._font_mono, f"SCORE {score:,}", theme.TEXT)
        anchor_x, anchor_y = hud_layout.SCORE_ANCHOR
        best_rect = best.get_rect(midbottom=(anchor_x, anchor_y))
        surface.blit(best, best_rect)
        surface.blit(score_surf, score_surf.get_rect(midbottom=(anchor_x, best_rect.top)))

    # ------------------------------------------------------------- weapons & speed
    def draw_weapon_panel(
        self,
        surface: pygame.Surface,
        bullets: int,
        max_bullets: int,
        reloading: bool,
        rockets: int,
        max_rockets: int,
        rocket_reload_ratio: Optional[float],
        radar_mode: str,
    ) -> None:
        """Cannon ammo, rocket pips/reload and radar mode in one panel (top right)."""
        if not self._ready:
            return
        rect = hud_layout.WEAPON_PANEL
        widgets.draw_panel(surface, rect)
        x = rect.x + 12
        w = rect.w - 24
        cache = self._cache

        surface.blit(cache.render(self._font_label, "CANNON", theme.TEXT_MUTED), (x, rect.y + 4))
        value = cache.render(
            self._font_small, "RELOADING" if reloading else f"{bullets}/{max_bullets}",
            theme.WARNING if reloading else theme.TEXT,
        )
        surface.blit(value, (rect.right - 12 - value.get_width(), rect.y + 7))
        widgets.draw_bar(
            surface, pygame.Rect(x, rect.y + 25, w, 8), bullets / max(1, max_bullets),
            theme.WARNING if reloading else theme.ACCENT,
        )

        surface.blit(cache.render(self._font_label, "ROCKETS", theme.TEXT_MUTED), (x, rect.y + 34))
        if rocket_reload_ratio is not None:
            value = cache.render(self._font_small, "RELOADING", theme.WARNING)
            widgets.draw_bar(surface, pygame.Rect(x, rect.y + 55, w, 8), rocket_reload_ratio, theme.WARNING)
        else:
            value = cache.render(self._font_small, f"{rockets}/{max_rockets}", theme.TEXT)
            for i in range(max_rockets):
                pip = pygame.Rect(x + i * 14, rect.y + 55, 10, 12)
                if i < rockets:
                    pygame.draw.rect(surface, theme.WARNING, pip)
                else:
                    pygame.draw.rect(surface, theme.BORDER_STRONG, pip, 1)
        surface.blit(value, (rect.right - 12 - value.get_width(), rect.y + 37))

        surface.blit(cache.render(self._font_small, "RADAR", theme.TEXT_MUTED), (x, rect.y + 74))
        mode = cache.render(self._font_small, radar_mode, theme.INFO if radar_mode == "CONE" else theme.WARNING)
        surface.blit(mode, (rect.right - 12 - mode.get_width(), rect.y + 74))

    def draw_speed(self, surface: pygame.Surface, speed: float, max_speed: float) -> None:
        """Compact throttle gauge above the minimap."""
        if not self._ready:
            return
        rect = hud_layout.SPEED_RECT
        widgets.draw_panel(surface, rect, theme.PANEL, theme.BORDER, brackets=False)
        surface.blit(self._cache.render(self._font_small, "SPD", theme.TEXT_MUTED), (rect.x + 8, rect.y + 1))
        value = self._cache.render(self._font_small, f"{speed:.1f}/{max_speed:.1f}", theme.TEXT)
        surface.blit(value, (rect.right - 8 - value.get_width(), rect.y + 1))
        widgets.draw_bar(
            surface, pygame.Rect(rect.x + 8, rect.bottom - 8, rect.w - 16, 4),
            speed / max(0.1, max_speed), theme.ACCENT, border=None,
        )

    # ------------------------------------------------------------------- minimap
    def get_minimap_surface(self, bg_image: pygame.Surface) -> pygame.Surface:
        """Return the minimap surface reset to its cached background (tiles + dim overlay)."""
        size = self._minimap_size
        if self._minimap_base is None:
            base = pygame.Surface((size, size), pygame.SRCALPHA)
            tile_w, tile_h = max(1, bg_image.get_width()), max(1, bg_image.get_height())
            for tx in range(0, size, tile_w):
                for ty in range(0, size, tile_h):
                    base.blit(bg_image, (tx, ty))
            base.blit(widgets.make_overlay((size, size), (0, 0, 0, 90)), (0, 0))
            self._minimap_base = base
        self._minimap_surf.fill((0, 0, 0, 0))
        self._minimap_surf.blit(self._minimap_base, (0, 0))
        return self._minimap_surf

    def draw_minimap_frame(self, surface: pygame.Surface) -> None:
        """Frame and brackets drawn over the blitted minimap."""
        widgets.draw_panel(surface, hud_layout.MINIMAP_RECT, None, theme.BORDER_STRONG, theme.ACCENT)

    # ----------------------------------------------------------- controls hint etc.
    def _build_hint_surface(self) -> pygame.Surface:
        """Render the controls hint row once (key badges + actions from the shared reference)."""
        font = self._tiny_font
        parts = []
        total = 0
        for key, action in HUD_HINT_KEYS:
            key_surf = font.render(key, True, theme.ACCENT)
            act_surf = font.render(action, True, theme.TEXT_MUTED)
            parts.append((key_surf, act_surf))
            total += key_surf.get_width() + 10 + 6 + act_surf.get_width() + 16
        height = font.get_height() + 4
        pad = 8
        surf = pygame.Surface((max(1, total - 16) + 2 * pad, height + 2 * 2), pygame.SRCALPHA)
        surf.fill(theme.with_alpha(theme.PANEL, 200))
        x = pad
        for key_surf, act_surf in parts:
            box = pygame.Rect(x, 0, key_surf.get_width() + 10, height)
            box.y = 2
            pygame.draw.rect(surf, theme.PANEL_RAISED, box)
            pygame.draw.rect(surf, theme.ACCENT_DIM, box, 1)
            surf.blit(key_surf, (box.x + 5, 4))
            surf.blit(act_surf, (box.right + 6, 4))
            x = box.right + 6 + act_surf.get_width() + 16
        return surf

    def draw_controls_hint(self, surface: pygame.Surface) -> None:
        """Bottom-row hint of the most important keys."""
        if self._hint_surf is not None:
            surface.blit(self._hint_surf, self._hint_surf.get_rect(center=hud_layout.CONTROLS_HINT_RECT.center))

    def get_slowmo_overlay(self) -> pygame.Surface:
        """Full-screen slow-motion vignette, built once."""
        if self._slowmo_overlay is None:
            surf = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
            pygame.draw.rect(surf, theme.with_alpha(theme.INFO, 35), (0, 0, self.width, self.height), 8)
            pygame.draw.rect(surf, (0, 150, 220, 20), (8, 8, self.width - 16, self.height - 16), 8)
            self._slowmo_overlay = surf
        return self._slowmo_overlay

    def get_frost_overlay(self, size: Tuple[int, int]) -> pygame.Surface:
        """Icy tint for frozen enemies, cached per sprite size."""
        surf = self._frost_overlays.get(size)
        if surf is None:
            surf = pygame.Surface(size, pygame.SRCALPHA)
            surf.fill((100, 210, 255, 130))
            pygame.draw.rect(surf, (220, 245, 255), (0, 0, size[0], size[1]), 2)
            self._frost_overlays[size] = surf
        return surf

    def get_lock_label(self, mode_tag: str) -> Optional[pygame.Surface]:
        """Cached 'CONE LOCK' / 'OMNI LOCK' label."""
        if not self._ready:
            return None
        return self._cache.render(self._font_label, mode_tag, theme.DANGER)
