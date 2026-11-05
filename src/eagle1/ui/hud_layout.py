"""hud_layout.py - Fixed, non-overlapping screen zones for the in-game HUD (1280x720).

Every HUD element draws inside its zone so panels from different systems (status cluster,
ground support, power-ups, boss bar, weapons) can never collide.
"""

import pygame

HUD_MARGIN = 16

STATUS_PANEL = pygame.Rect(16, 16, 248, 84)          # shield, hull, wave
ADRENALINE_RECT = pygame.Rect(16, 104, 248, 20)
SQUAD_PANEL = pygame.Rect(16, 130, 248, 74)          # ground-support squad panel
BUFF_BARS_ORIGIN = (16, 212)                          # power-up buff bars, 20 px step
OBJECTIVE_BANNER_Y = 12                               # mission objective, h=24
CAMPAIGN_OBJECTIVE_Y = 40                             # campaign objective, h=22
BOSS_BAR_RECT = pygame.Rect(430, 70, 420, 14)
GS_OBJECTIVE_Y = 92                                   # ground-support objective line
DANGER_BANNER_RECT = pygame.Rect(420, 112, 440, 28)
HERO_PANEL_RECT = pygame.Rect(430, 146, 420, 80)
MILESTONE_BANNER_RECT = pygame.Rect(360, 232, 560, 65)
WEAPON_PANEL = pygame.Rect(1280 - 16 - 200, 16, 200, 92)   # cannon ammo, rockets, radar
MINIMAP_RECT = pygame.Rect(16, 720 - 16 - 160, 160, 160)
SPEED_RECT = pygame.Rect(16, MINIMAP_RECT.y - 34, 160, 26)
WEAPON_DOCK_RECT = pygame.Rect(1280 - 460, 720 - 94, 444, 86)
SCORE_ANCHOR = (640, 720 - 12)                        # midbottom of the score line
SCORE_RECT = pygame.Rect(560, 672, 160, 36)
CONTROLS_HINT_RECT = pygame.Rect(200, 644, 600, 26)   # bottom row between minimap and weapon dock
WAVE_BANNER_CENTER = (640, 300)

# Zones that are on screen at the same time and therefore must never overlap.
ALL_ZONES = (
    STATUS_PANEL,
    ADRENALINE_RECT,
    SQUAD_PANEL,
    BOSS_BAR_RECT,
    DANGER_BANNER_RECT,
    HERO_PANEL_RECT,
    WEAPON_PANEL,
    MINIMAP_RECT,
    SPEED_RECT,
    WEAPON_DOCK_RECT,
    SCORE_RECT,
    CONTROLS_HINT_RECT,
)
