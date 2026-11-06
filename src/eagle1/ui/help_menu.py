"""
help_menu.py - In-Game Help and Tactical Guide for Eagle-1-64Bit

Provides an interactive, multi-tab help menu detailing:
- Weapons: Specific damages, ranges, velocities, cooldowns, and capacities.
- Abilities: 8 tactical power-ups across Common, Rare, and Epic tiers, plus passives.
- Radar Modes: Comprehensive explanation of CONE vs OMNI targeting with visual diagrams.
- Flight Controls: Keybinding reference generated from eagle1.ui.controls_reference.
- Enemy Intel and Helldivers/Stratagem guides.

Every tab is a static page: it is rendered once into a cached surface on first visit and then
only blitted, so no text or surface work happens per frame.
"""

import math
from typing import List

import pygame

from eagle1.ui import theme, widgets
from eagle1.ui.controls_reference import CATEGORY_ORDER, bindings_by_category

try:
    from eagle1.systems.audio_manager import get_audio_manager
except ImportError:
    get_audio_manager = None

# Color palette (aliases of the central theme tokens; names kept for compatibility)
COLOR_BG_OVERLAY = theme.OVERLAY_RGBA
COLOR_PANEL_BG = theme.PANEL_RAISED
COLOR_PANEL_BORDER = theme.BORDER
COLOR_TEXT_WHITE = theme.TEXT
COLOR_TEXT_MUTED = theme.TEXT_MUTED
COLOR_TEXT_ACCENT = theme.INFO
COLOR_TEXT_GOLD = theme.ACCENT
COLOR_TEXT_GREEN = theme.SUCCESS
COLOR_TEXT_BLUE = (52, 152, 219)        # Rare tier (data color)
COLOR_TEXT_PURPLE = (175, 100, 240)     # Epic tier (data color)
COLOR_TEXT_RED = theme.DANGER

COLOR_TAB_INACTIVE_BG = theme.PANEL_RAISED
COLOR_TAB_HOVER_BG = theme.PANEL_HOVER
COLOR_TAB_ACTIVE_BG = theme.PANEL_HOVER

VALUE_TEXT = theme.lerp_color(theme.TEXT, theme.ACCENT, 0.35)

FLOW_STEP = 18

# ---------------------------------------------------------------------------
# Static help content (data only)
# ---------------------------------------------------------------------------

WEAPONS = [
    {
        "name": "Main Autocannon (Quad-Barrel)",
        "type": "Primary Weapon (Kinetic Ballistic)",
        "trigger": "SPACE (Hold or Tap)",
        "damage": "1 per round  (4 DMG per quad-volley)  |  Boosted: 2 per round (8 DMG)",
        "range": "Full Map Bounds (0-3000 px)  |  Velocity: 8.0 px/frame (480 px/s)",
        "cooldown": "100 ms between volleys  (50 ms under Rapid Fire)",
        "capacity": "200 rounds (50 quad volleys)  |  Reload: 5.0s (3.0s under Rapid Fire)",
        "notes": "Fires 4 parallel projectiles simultaneously from wing and fuselage hardpoints. Bullets persist until hitting enemies or map borders.",
        "color": (255, 210, 80),
    },
    {
        "name": "Eagle Homing Rockets",
        "type": "Secondary Ordnance (Guided Kinetic Warhead)",
        "trigger": "E / F / Left-CTRL or Right-Click",
        "damage": "20 DMG (one-shots light fighters, 4 hits on bombers)",
        "range": "1200 px max tracking range  |  2.5s maximum flight lifetime",
        "cooldown": "350 ms firing delay  |  Velocity: 11.5 px/frame  |  Agility: 5.5°/frame",
        "capacity": "4 rockets  |  Reload: 12.0s when all 4 rockets are exhausted",
        "notes": "Air-to-air only. Requires radar lock (CONE or OMNI forward arc). Enemies may break perpendicular to the missile or eject flares that can decoy it; EMS-stunned targets cannot defend.",
        "color": (255, 120, 60),
    },
    {
        "name": "Swarm Micro-Missiles",
        "type": "Autonomous Ability Weapon (Swarm Homing Pods)",
        "trigger": "Auto-fired every 0.8s during Swarm Homing Pods buff (12s)",
        "damage": "2.0 DMG per micro-missile",
        "range": "~900 px effective range  |  Velocity: 7.5 px/frame  |  Agility: 4.0°/frame",
        "cooldown": "Continuous 0.8s auto-salvo interval",
        "capacity": "Autonomous salvo during buff lifetime",
        "notes": "High-maneuverability self-guided micro-projectiles launched automatically from dorsal pods to relentlessly track enemies.",
        "color": (200, 100, 255),
    },
    {
        "name": "Vanguard Drone Pulse Laser",
        "type": "Autonomous Escort Weapon (Vanguard Drone)",
        "trigger": "Automatic firing by orbiting Vanguard Drone (20s duration)",
        "damage": "1.0 DMG per focused laser pulse",
        "range": "350 px engagement perimeter centered around player ship",
        "cooldown": "Fires once every 0.6 seconds when enemy is within 350 px",
        "capacity": "Unlimited during drone deployment",
        "notes": "Drone physically intercepts and eliminates incoming enemy bullets while systematically attacking nearby hostiles.",
        "color": (120, 220, 255),
    },
    {
        "name": "Hull Impact Collision",
        "type": "Emergency Melee Contact",
        "trigger": "Ramming into an enemy aircraft (Light enemies will strafe to evade)",
        "damage": "25 DMG (One-Hit Elimination) dealt to enemy aircraft  |  Self-Damage: 12 DMG absorbed by shield first",
        "range": "0 px (Direct physical contact; causes physical separation recoil)",
        "cooldown": "Immediate upon contact  |  Triggers 1.0s temporary invincibility",
        "capacity": "Absorbed by shield pool (20 max) before damaging hull structure",
        "notes": "Light hostiles break away at <180px. Impact drains shield with recoil push to prevent multi-hits.",
        "color": (255, 80, 80),
    },
]

ABILITY_COLUMN_1 = [
    {
        "tier": "COMMON TIER (70% Roll Chance)",
        "tier_color": COLOR_TEXT_GREEN,
        "name": "Rapid Fire",
        "dur": "10s Duration",
        "stats": "Cooldown: 100ms -> 50ms (2x Fire Rate)  |  Reload: 5.0s -> 3.0s (-40%)",
        "desc": "Overcharges main autocannon cyclic rate, delivering dense volleys.",
        "color": COLOR_TEXT_GREEN,
    },
    {
        "tier": "COMMON TIER (70% Roll Chance)",
        "tier_color": COLOR_TEXT_GREEN,
        "name": "Shield Bubble",
        "dur": "10s Duration",
        "stats": "+15 Overcharge Shield (Max 35)  |  Regen Rate: 2.0s -> 1.0s (2x)",
        "desc": "Instantly expands shield barrier beyond normal max and accelerates recovery.",
        "color": COLOR_TEXT_GREEN,
    },
    {
        "tier": "COMMON TIER (70% Roll Chance)",
        "tier_color": COLOR_TEXT_GREEN,
        "name": "Thruster Overdrive",
        "dur": "10s Duration",
        "stats": "Max Speed: 7.0 -> 11.0 (+57%)  |  Accel: 0.15 -> 0.25  |  Turn: 3° -> 4.5°",
        "desc": "Injects thrusters with hyper-fuel for superior dogfighting maneuverability.",
        "color": COLOR_TEXT_GREEN,
    },
    {
        "tier": "RARE TIER (20% Roll Chance)",
        "tier_color": COLOR_TEXT_BLUE,
        "name": "Chrono Slip (Time Slow)",
        "dur": "8s Duration",
        "stats": "Enemy Speed: 50% (x0.5)  |  Hostile Bullet Velocity: 50% (x0.5)",
        "desc": "Dilates localized space-time; enemies and bullets crawl while you move at normal speed.",
        "color": COLOR_TEXT_BLUE,
    },
    {
        "tier": "RARE TIER (20% Roll Chance)",
        "tier_color": COLOR_TEXT_BLUE,
        "name": "Cryo Frostbite (Freeze Blast)",
        "dur": "10s Duration",
        "stats": "Frost Slow: 60% (x0.4 speed)  |  3 Hits = 1.5s Complete Solid Freeze",
        "desc": "Rounds coat enemy hulls in liquid sub-zero cryogen. 3 hits completely freeze enemy.",
        "color": COLOR_TEXT_BLUE,
    },
]

ABILITY_COLUMN_2 = [
    {
        "tier": "RARE TIER (20% Roll Chance)",
        "tier_color": COLOR_TEXT_BLUE,
        "name": "Damage Multiplier",
        "dur": "10s Duration",
        "stats": "Cannon Damage: 1 -> 2 DMG per bullet  (4 -> 8 DMG per quad-volley)",
        "desc": "Empowers autocannon munitions with high-yield depleted uranium charges.",
        "color": COLOR_TEXT_BLUE,
    },
    {
        "tier": "EPIC TIER (10% Roll Chance)",
        "tier_color": COLOR_TEXT_PURPLE,
        "name": "Vanguard Drone Companion",
        "dur": "20s Duration",
        "stats": "Orbiting Radius: 85 px  |  Laser Damage: 1.0 DMG (350 px range, 0.6s CD)",
        "desc": "Deploys an autonomous escort drone that intercepts enemy bullets and fires lasers.",
        "color": COLOR_TEXT_PURPLE,
    },
    {
        "tier": "EPIC TIER (10% Roll Chance)",
        "tier_color": COLOR_TEXT_PURPLE,
        "name": "Swarm Homing Pods",
        "dur": "12s Duration",
        "stats": "Damage: 2.0 DMG / missile  |  Salvo: Every 0.8s  |  Tracking Range: 900 px",
        "desc": "Mounts micro-missile pods launching continuous high-agility self-guided rockets.",
        "color": COLOR_TEXT_PURPLE,
    },
    {
        "tier": "PASSIVE SHIP DEFENSES",
        "tier_color": (255, 200, 80),
        "name": "Deflector Shield & Hull Armor",
        "dur": "Permanent Passive",
        "stats": "Shield: 20 (+1 / 2.0s regen)  |  Hull: 5 HP (No passive recovery!)",
        "desc": "Shield absorbs hits before hull. Taking damage gives 1.0s immunity. Boundary: 0.1 DMG/tick.",
        "color": (100, 200, 255),
    },
    {
        "tier": "ANTI-RETREAT & LOW HP SURVIVAL",
        "tier_color": (50, 255, 120),
        "name": "Kill-to-Heal Nanites & Overdrive",
        "dur": "Active when HP <= 2",
        "stats": "+1 HP Nanite drop guaranteed on kill  |  +50% Score  |  -25% Cooldowns",
        "desc": "Fleeing at low HP is fatal! Defeat enemies to spawn green nanites and trigger Overdrive.",
        "color": (50, 255, 120),
    },
]

_WAVES_CARD_1 = {
    "title": "1. Mission Selector & Wave Scaling",
    "tag": "TACTICAL OPERATIONS [1-5]",
    "accent": COLOR_TEXT_GOLD,
    "bullets": [
        ("Tactical Mission Selector:", "Select from 5 focused operation modes: Air Superiority, Base Defense, Boss Raid, Demolition, Endless."),
        ("Focused Operational Modes:", "Play pure aerial dogfights, ground boss raids, or orbital defense without overwhelming chaos."),
        ("Tactical Squadron Formations:", "Enemies deploy in coordinated flights of 2-4 starfighters in V-formation rather than solo."),
        ("Boids Flocking Separation:", "Units maintain spatial separation (70px repulsion radius) to eliminate clipping or stacking."),
    ],
    "footer": "Wave Clear Bonus: +250 x Wave Level awarded during the 3-second intermission banner.",
}

_WAVES_CARD_2 = {
    "title": "2. 1000px Agro Perimeter & Map Circling",
    "tag": "AGRO: 1000px | DE-AGRO: 1500px",
    "accent": COLOR_TEXT_ACCENT,
    "bullets": [
        ("Patrol State (Holding Fire):", "Outside 1000px, squadrons orbit the map center at 2.0 px/frame without shooting."),
        ("Squadron Alert Network:", "Breaching 1000px or damaging any plane immediately alerts the ENTIRE squadron."),
        ("Pursuit Acceleration:", "Alerted hostiles enter AGRO state and accelerate to 3.2 px/frame (60% speed increase)."),
        ("Minimap Tactical Blips:", "Minimap radar displays patrolling squadrons as ORANGE dots and alerted pursuers as RED dots."),
    ],
    "footer": "Note: Attacking an orbiting formation triggers pursuit from all wingmen!",
}

_WAVES_CARD_3 = {
    "title": "3. Smart Combat AI & Directional Ballistics",
    "tag": "AIM GATE: ±15° | TURN: 2.0°/F",
    "accent": (255, 130, 60),
    "bullets": [
        ("Line-of-Sight Tracking:", "Calculates true angle to player via atan2 math, turning smoothly at 2.0° per frame."),
        ("Alignment-Gated Firing:", "Hostiles hold fire until nose is aligned within ±15° of line of sight (no blind spam)."),
        ("True 2D Vector Ballistics:", "Enemy bullets fire from the nose carrying directional velocity (dx, dy) towards player."),
        ("Debuff Susceptibility:", "Enemy turn rate, thrust, and bullets are realistically impaired by Time Slow & Cryo Freeze."),
    ],
    "footer": "Evasion Tip: Banking 90° across the enemy's nose breaks their ±15° firing alignment!",
}

_WAVES_CARD_4 = {
    "title": "4. Anti-Retreat Dynamics & Adrenaline Overdrive",
    "tag": "CRITICAL HP <= 2 | HEAL ON KILL",
    "accent": (50, 255, 120),
    "bullets": [
        ("The Low-HP Dilemma:", "Shields passively recover, but Hull HP NEVER regenerates. Running at low HP is fatal."),
        ("High-Speed Pursuit:", "Enemies hunt at 3.2 px/frame in AGRO; you cannot easily outrun alerted squadrons."),
        ("Kill-to-Heal Nanites:", "When at critical hull (<= 2 HP), every defeated enemy drops a guaranteed +1 HP Nanite!"),
        ("Adrenaline Overdrive:", "Operating at <= 2 HP grants +50% score bonus and 25% faster weapon cyclic fire & reload."),
    ],
    "footer": "Doctrine: Never flee when damaged! Turn into hostiles, kill, and harvest nanites.",
}

WAVE_CARDS = [_WAVES_CARD_1, _WAVES_CARD_2, _WAVES_CARD_3, _WAVES_CARD_4]

_SQUAD_CARD_1 = {
    "title": "Allied Helldiver Squad",
    "tag": "ALLIED GROUND UNITS",
    "accent": (46, 204, 113),
    "bullets": [
        ("Tactical 4-Man Squad:", "Viper 1-4 (Lead, Heavy, Scout, Medic) guarding the outpost with individual shields & HP."),
        ("Tactical AI & Cover Fire:", "Helldivers navigate around obstacles and actively fire upward anti-air tracer rounds at hostiles."),
        ("Minimap Tracking:", "Represented as bright cyan blips with an active tactical defense perimeter circle on the radar."),
        ("Status Indicators:", "Overhead health/shield bars and real-time state tags: DEFENDING, ENGAGING, SUPPLYING, K.I.A."),
    ],
    "footer": "TIP: Stay near the squad when danger alerts fire to intercept hostile strafing runs.",
}

_SQUAD_CARD_2 = {
    "title": "Air Strike Stratagem Arsenal",
    "tag": "TACTICAL 5-SLOT DOCK",
    "accent": (255, 200, 50),
    "bullets": [
        ("Charges & Operational Delay:", "Stratagems have discrete stocks (e.g. 500kg x1, Strafe x3) and fast operational delays."),
        ("Eagle Rearm [R]:", "Eagle-1 blasts into orbit aboard the Super Destroyer (15s); ground combat freezes and Helldivers are safe."),
        ("Stratagem Hero:", "Input arrow/WASD codes on the hangar arcade terminal to score bonus points and climb the Hero leaderboard!"),
        ("Re-entry:", "Eagle-1 returns with full charges and 1.0s invulnerability."),
        ("500kg Bomb:", "480px blast radius, 38 heavy DMG: wrecks fabricators and bosses."),
    ],
    "footer": "TACTICAL DOCK: Quickbar displays live charges, operational cooldowns, and rearm status.",
}

_SQUAD_CARD_3 = {
    "title": "Tactical Supply Drops & Alerts",
    "tag": "[X] RESUPPLY POD",
    "accent": (0, 200, 255),
    "bullets": [
        ("Supply Drop [X]:", "Calls down an orbital pod delivering medical nanites, full ammo reload, and rockets (30s CD)."),
        ("Ground Resupply:", "Allied Helldivers move to nearby landed supply pods when wounded to restore shields and health."),
        ("Danger Zone Alerts:", "Audible and visual flashing alert banner appears when enemy aircraft close in within 680px."),
        ("Off-Screen Compass:", "Cyan directional pointer at screen borders indicates distance and bearing to the squad."),
    ],
    "footer": "CRITICAL: Drop pods near the squad before heavy waves to keep them alive.",
}

_SQUAD_CARD_4 = {
    "title": "Objectives & Boss Encounters",
    "tag": "OBJECTIVES & REWARDS",
    "accent": (255, 120, 50),
    "bullets": [
        ("Factory Strider Boss (300 HP):", "Colossal walker firing heavy plasma bolts (red laser telegraph) and chin lasers."),
        ("Base Defense (5 Waves):", "Protect orbital base against 75 HP Automaton Bombers. Repel all 5 waves to extract."),
        ("Outpost Demolition (6 Waves):", "Destroy 3 Automaton Fabricator foundries; auto-triggers Pelican extraction."),
        ("Pelican-1 Evacuation (+2.5k):", "Hold perimeter until Pelican-1 lands. Surviving squad boards to secure victory!"),
    ],
    "footer": "VICTORY: Finish the primary objectives to summon Pelican-1 and extract survivors!",
}

SQUAD_CARDS = [_SQUAD_CARD_1, _SQUAD_CARD_2, _SQUAD_CARD_3, _SQUAD_CARD_4]

SYSTEM_NOTES = [
    ("Rearm [R]:", "Eagle-1 returns to the Super Destroyer for a 15 s rearm and combat freezes. "
     "Play Stratagem Hero with the arrow keys for bonus score."),
    ("Slow-Mo Aiming:", "Hold fire with a stratagem equipped to slow time (3 s max) and aim; release to deploy."),
    ("Fullscreen:", "CMD+F or F11 toggles fullscreen with the aspect ratio preserved. CMD+Q quits (Mac)."),
    ("Debriefing:", "[R] replay, [H] hub, [SPACE] mission select, [ESC] main menu."),
    ("Respawn:", "Press [R] after K.I.A. to respawn, or [SPACE] to return to the lobby."),
    ("Help Tabs:", "[1-6] jump to a tab, [TAB] / arrows cycle, [SHIFT+TAB] goes back."),
]


class HelpMenu:
    """Interactive In-Game Help Menu supporting mouse and keyboard navigation."""

    TAB_WEAPONS = 0
    TAB_ABILITIES = 1
    TAB_RADAR = 2
    TAB_CONTROLS = 3
    TAB_WAVES = 4
    TAB_HELLDIVERS = 5

    TAB_NAMES = [
        "1 WEAPONS",
        "2 ABILITIES",
        "3 RADAR",
        "4 CONTROLS",
        "5 ENEMIES",
        "6 SQUAD",
    ]

    FOOTER_TEXT = "[1-6] TAB   [TAB / ARROWS] CYCLE   [SHIFT+TAB] BACK   [ESC / H] CLOSE"

    def __init__(self, width=1280, height=720):
        self.width = width
        self.height = height
        self.active_tab = self.TAB_WEAPONS

        self.font_title = theme.get_font("title")
        self.font_subtitle = theme.get_font("heading")
        self.font_heading = theme.get_font("label")
        self.font_body = theme.get_font("body_small")
        self.font_body_bold = theme.get_font("label")
        self.font_small = theme.get_font("body_small")
        self.font_tag = theme.get_font("mono_tiny")
        self.font_mono = theme.get_font("mono")
        self._fonts_ready = None not in (
            self.font_title, self.font_subtitle, self.font_heading, self.font_body,
            self.font_tag, self.font_mono,
        )
        self._cache = widgets.TextCache(1024)
        self._overlay = widgets.make_overlay((self.width, self.height), COLOR_BG_OVERLAY)

        margin_x, margin_y = 24, 15
        self.panel_rect = pygame.Rect(margin_x, margin_y, self.width - 2 * margin_x, self.height - 2 * margin_y)
        self.content_rect = pygame.Rect(margin_x + 16, 76, self.width - 2 * margin_x - 32, self.height - margin_y - 120)
        self.footer_rect = pygame.Rect(34, self.height - 48, self.width - 68, 30)

        # Tab button rectangles
        self.tab_rects = []
        self._init_tab_rects()

        # Close button rect (top right)
        self.close_btn_rect = pygame.Rect(self.width - 145, 20, 115, 36)

        self._page_cache = {}
        self._footer_surf = None
        if self._fonts_ready:
            self._footer_surf = self.font_tag.render(self.FOOTER_TEXT, True, COLOR_TEXT_MUTED)

    def _init_tab_rects(self):
        """Pre-computes tab button layout across top header."""
        self.tab_rects = []
        tab_w = 175
        tab_h = 36
        spacing = 8
        start_x = 24

        for i in range(len(self.TAB_NAMES)):
            x = start_x + i * (tab_w + spacing)
            self.tab_rects.append(pygame.Rect(x, 20, tab_w, tab_h))

    def set_tab(self, tab_index):
        """Switches to the specified tab index."""
        if 0 <= tab_index < len(self.TAB_NAMES):
            self.active_tab = tab_index

    def next_tab(self):
        """Cycles to the next tab."""
        self.active_tab = (self.active_tab + 1) % len(self.TAB_NAMES)

    def prev_tab(self):
        """Cycles to the previous tab."""
        self.active_tab = (self.active_tab - 1) % len(self.TAB_NAMES)

    @staticmethod
    def _play_click():
        if get_audio_manager:
            get_audio_manager().play_sfx("ui_click")

    def _switch_tab(self, index):
        """Activate a tab; returns "tab_changed" only when the tab actually changed."""
        if index == self.active_tab:
            return None
        self.active_tab = index
        self._play_click()
        return "tab_changed"

    def handle_event(self, event, mouse_pos=None):
        """
        Handles keyboard and mouse inputs.
        Returns:
            "close": when the user wants to return to the previous screen.
            "tab_changed": when tab selection changes.
            None: otherwise.
        """
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if mouse_pos is not None:
                if self.close_btn_rect.collidepoint(mouse_pos):
                    self._play_click()
                    return "close"
                for i, rect in enumerate(self.tab_rects):
                    if rect.collidepoint(mouse_pos):
                        return self._switch_tab(i)

        elif event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_ESCAPE, pygame.K_h):
                self._play_click()
                return "close"
            if pygame.K_1 <= event.key <= pygame.K_6:
                return self._switch_tab(event.key - pygame.K_1)
            if event.key == pygame.K_TAB:
                shift = bool(event.mod & pygame.KMOD_SHIFT)
                return self._switch_tab((self.active_tab + (-1 if shift else 1)) % len(self.TAB_NAMES))
            if event.key == pygame.K_RIGHT:
                return self._switch_tab((self.active_tab + 1) % len(self.TAB_NAMES))
            if event.key == pygame.K_LEFT:
                return self._switch_tab((self.active_tab - 1) % len(self.TAB_NAMES))

        return None

    # =========================================================================
    # DRAWING & RENDERING
    # =========================================================================

    def draw(self, surface, mouse_pos=None):
        """Renders the entire help menu overlay onto the target surface."""
        surface.blit(self._overlay, (0, 0))
        if not self._fonts_ready:
            return

        widgets.draw_panel(surface, self.panel_rect)
        self._draw_tabs(surface, mouse_pos)
        self._draw_close_button(surface, mouse_pos)
        pygame.draw.line(surface, COLOR_PANEL_BORDER, (self.panel_rect.x + 10, 68), (self.panel_rect.right - 10, 68), 1)

        surface.blit(self._get_page(self.active_tab), self.content_rect.topleft)
        self._draw_footer(surface)

    def _get_page(self, tab):
        """Return the cached page surface for ``tab``, rendering it once on first visit."""
        page = self._page_cache.get(tab)
        if page is None:
            page = pygame.Surface(self.content_rect.size)
            page.fill(theme.PANEL)
            rect = pygame.Rect(0, 0, *self.content_rect.size)
            renderers = {
                self.TAB_WEAPONS: self._draw_tab_weapons,
                self.TAB_ABILITIES: self._draw_tab_abilities,
                self.TAB_RADAR: self._draw_tab_radar,
                self.TAB_CONTROLS: self._draw_tab_controls,
                self.TAB_WAVES: self._draw_tab_waves,
                self.TAB_HELLDIVERS: self._draw_tab_helldivers,
            }
            renderers[tab](page, rect)
            self._page_cache[tab] = page
        return page

    def _draw_tabs(self, surface, mouse_pos):
        """Draws top tab navigation buttons."""
        for i, rect in enumerate(self.tab_rects):
            is_active = (i == self.active_tab)
            is_hovered = (mouse_pos is not None and rect.collidepoint(mouse_pos))

            if is_active:
                bg, txt_color = COLOR_TAB_ACTIVE_BG, COLOR_TEXT_WHITE
            elif is_hovered:
                bg, txt_color = COLOR_TAB_HOVER_BG, COLOR_TEXT_WHITE
            else:
                bg, txt_color = COLOR_TAB_INACTIVE_BG, COLOR_TEXT_MUTED

            widgets.draw_panel(surface, rect, bg, theme.ACCENT if is_hovered else COLOR_PANEL_BORDER, brackets=False)
            if is_active:
                pygame.draw.rect(surface, theme.ACCENT, (rect.x, rect.bottom - 3, rect.w, 3))
            label = widgets.fit_text(self.font_subtitle, self.TAB_NAMES[i], rect.w - 16)
            surf = self._cache.render(self.font_subtitle, label, txt_color)
            surface.blit(surf, surf.get_rect(center=rect.center))

    def _draw_close_button(self, surface, mouse_pos):
        """Draws the Close / Return button."""
        is_hovered = (mouse_pos is not None and self.close_btn_rect.collidepoint(mouse_pos))
        widgets.draw_panel(
            surface, self.close_btn_rect,
            COLOR_TAB_HOVER_BG if is_hovered else COLOR_TAB_INACTIVE_BG,
            theme.DANGER if is_hovered else COLOR_PANEL_BORDER,
            brackets=False,
        )
        txt = self._cache.render(self.font_heading, "BACK [ESC]", COLOR_TEXT_WHITE)
        surface.blit(txt, txt.get_rect(center=self.close_btn_rect.center))

    def _draw_footer(self, surface):
        """Draws bottom bar with keybinding guidance."""
        widgets.draw_panel(surface, self.footer_rect, theme.PANEL_RAISED, theme.BORDER, brackets=False)
        if self._footer_surf is not None:
            surface.blit(self._footer_surf, self._footer_surf.get_rect(center=self.footer_rect.center))

    # ------------------------------------------------------------------ helpers
    def _text(self, surface, font, text, color, pos, max_w=None):
        """Blit single-line text, ellipsized to ``max_w`` pixels when given."""
        if max_w is not None:
            text = widgets.fit_text(font, text, max_w)
        surf = self._cache.render(font, text, color)
        surface.blit(surf, pos)
        return surf

    def _flow_split(self, label, desc, width):
        """Split ``desc`` so it flows right after ``label``; returns (label_w, first_line, rest_lines)."""
        label_w = self.font_heading.size(label + " ")[0]
        words = desc.split()
        first: List[str] = []
        while words and self.font_body.size(" ".join(first + [words[0]]))[0] <= width - label_w:
            first.append(words.pop(0))
        rest = widgets.wrap_text_px(self.font_body, " ".join(words), width) if words else []
        return label_w, " ".join(first), rest

    def _flow_height(self, label, desc, width):
        _, _, rest = self._flow_split(label, desc, width)
        return (1 + len(rest)) * FLOW_STEP

    def _draw_flow(self, surface, x, y, width, label, desc, label_color=COLOR_TEXT_WHITE, desc_color=COLOR_TEXT_MUTED):
        """Draw ``label`` followed by wrapped ``desc``; returns the consumed height."""
        label_w, first, rest = self._flow_split(label, desc, width)
        surface.blit(self._cache.render(self.font_heading, label, label_color), (x, y))
        if first:
            surface.blit(self._cache.render(self.font_body, first, desc_color), (x + label_w, y + 1))
        for i, line in enumerate(rest):
            surface.blit(self._cache.render(self.font_body, line, desc_color), (x, y + (i + 1) * FLOW_STEP + 1))
        return (1 + len(rest)) * FLOW_STEP

    def _draw_title(self, surface, rect, title, color, sub=None):
        self._text(surface, self.font_title, title, color, (rect.x + 10, rect.y + 2), rect.width - 20)
        if sub:
            self._text(surface, self.font_body, sub, COLOR_TEXT_MUTED, (rect.x + 12, rect.y + 34), rect.width - 24)

    # =========================================================================
    # TAB 1: WEAPONS & COMBAT
    # =========================================================================

    def _draw_tab_weapons(self, surface, rect):
        """Renders comprehensive weapon specifications, damages, and ranges."""
        self._draw_title(
            surface, rect, "STARBLAST WEAPONRY & COMBAT SYSTEMS", COLOR_TEXT_GOLD,
            "Tactical specifications, exact damages, projectile speeds, and effective engagement ranges.",
        )
        card_y = rect.y + 56
        card_w = rect.width - 10
        card_h = 100
        spacing = 5
        text_w = card_w - 36

        for w in WEAPONS:
            card_rect = pygame.Rect(rect.x + 5, card_y, card_w, card_h)
            widgets.draw_panel(surface, card_rect, theme.PANEL_RAISED, theme.BORDER, brackets=False)
            pygame.draw.rect(surface, w["color"], (card_rect.x, card_y, 3, card_h))

            x = rect.x + 18
            name_txt = self._text(surface, self.font_heading, w["name"].upper(), w["color"], (x, card_y + 5))
            trig = widgets.fit_text(self.font_tag, f"FIRE: {w['trigger']}", 640)
            trig_surf = self._cache.render(self.font_tag, trig, COLOR_TEXT_ACCENT)
            surface.blit(trig_surf, (card_rect.right - trig_surf.get_width() - 14, card_y + 8))
            type_x = x + name_txt.get_width() + 12
            self._text(
                surface, self.font_tag, f"[{w['type']}]", COLOR_TEXT_MUTED,
                (type_x, card_y + 8), card_rect.right - trig_surf.get_width() - 30 - type_x,
            )

            rows = (
                ("Damage:", w["damage"], VALUE_TEXT),
                ("Range:", w["range"], theme.lerp_color(theme.TEXT, theme.INFO, 0.5)),
                ("Capacity / Cooldown:", f"{w['capacity']}  |  {w['cooldown']}", COLOR_TEXT_WHITE),
            )
            ry = card_y + 26
            for label, value, color in rows:
                lbl = self._text(surface, self.font_heading, label, COLOR_TEXT_WHITE, (x, ry))
                self._text(surface, self.font_body, value, color, (x + lbl.get_width() + 6, ry + 1), text_w - lbl.get_width() - 6)
                ry += 18
            self._text(surface, self.font_body, w["notes"], COLOR_TEXT_MUTED, (x, ry + 2), text_w)

            card_y += card_h + spacing

    # =========================================================================
    # TAB 2: ABILITIES & BUFFS
    # =========================================================================

    def _draw_tab_abilities(self, surface, rect):
        """Renders all 8 tactical power-ups across rarity tiers, plus passives."""
        self._draw_title(
            surface, rect, "TACTICAL ABILITIES & POWER-UP SUBSYSTEM", COLOR_TEXT_ACCENT,
            "Drops: 8% base chance on kill (+3% pity per kill without drop)  |  Milestone airdrops at 1K, 5K, 10K, 25K, 50K  |  Magnet pull: 130 px",
        )
        col_w = (rect.width - 24) // 2
        card_h = 98
        start_y = rect.y + 56
        spacing_y = 6

        for col_x, items in ((rect.x + 5, ABILITY_COLUMN_1), (rect.x + 15 + col_w, ABILITY_COLUMN_2)):
            curr_y = start_y
            for item in items:
                self._draw_ability_card(surface, col_x, curr_y, col_w, card_h, item)
                curr_y += card_h + spacing_y

    def _draw_ability_card(self, surface, x, y, w, h, item):
        """Renders an individual ability card."""
        c_rect = pygame.Rect(x, y, w, h)
        widgets.draw_panel(surface, c_rect, theme.PANEL_RAISED, theme.BORDER, brackets=False)
        pygame.draw.rect(surface, item["color"], (x, y, 3, h))

        dur = self._cache.render(self.font_tag, f"[{item['dur']}]", COLOR_TEXT_WHITE)
        surface.blit(dur, (x + w - dur.get_width() - 10, y + 8))
        self._text(surface, self.font_heading, item["name"].upper(), item["color"], (x + 14, y + 5), w - dur.get_width() - 40)
        self._text(surface, self.font_tag, item["tier"], item["tier_color"], (x + 14, y + 25), w - 28)
        self._text(surface, self.font_heading, item["stats"], VALUE_TEXT, (x + 14, y + 41), w - 28)
        for i, line in enumerate(widgets.wrap_text_px(self.font_body, item["desc"], w - 28, max_lines=2)):
            self._text(surface, self.font_body, line, COLOR_TEXT_MUTED, (x + 14, y + 62 + i * 17))

    # =========================================================================
    # TAB 3: RADAR MODES (CONE vs OMNI)
    # =========================================================================

    def _draw_tab_radar(self, surface, rect):
        """Renders thorough breakdown and visual diagrams of CONE vs OMNI radar modes."""
        self._draw_title(surface, rect, "DUAL RADAR TARGETING MODES: CONE vs OMNI", theme.SUCCESS)
        self._text(
            surface, self.font_heading,
            "HOTKEY: Press [Q] during flight to instantly toggle between CONE and OMNI radar modes",
            COLOR_TEXT_GOLD, (rect.x + 12, rect.y + 34), rect.width - 24,
        )
        col_w = (rect.width - 24) // 2
        card_h = rect.height - 76
        start_y = rect.y + 60
        self._draw_radar_mode_panel(surface, rect.x + 5, start_y, col_w, card_h, True)
        self._draw_radar_mode_panel(surface, rect.x + 15 + col_w, start_y, col_w, card_h, False)

    def _draw_radar_mode_panel(self, surface, x, y, w, h, is_cone):
        """Draws radar mode details along with a diagram illustrating the detection area."""
        p_rect = pygame.Rect(x, y, w, h)
        accent_color = theme.INFO if is_cone else theme.WARNING
        widgets.draw_panel(surface, p_rect, theme.PANEL_RAISED, accent_color, accent_color)

        mode_title = "MODE 1: CONE (Long-Range Forward Sector)" if is_cone else "MODE 2: OMNI (Close-Range Wide Forward Arc)"
        self._text(surface, self.font_subtitle, mode_title.upper(), accent_color, (x + 16, y + 12), w - 32)

        if is_cone:
            specs = [
                ("Search Geometry:", "50° Forward Arc (±25° aligned with ship nose)"),
                ("Minimum Arming Range:", "300 pixels (Blind Zone for point-blank enemies)"),
                ("Maximum Target Range:", "1050 pixels (Deep forward radar sweep)"),
                ("HUD Visualization:", "Green/Cyan angular target cone projecting ahead"),
                ("Tactical Role:", "Sniper & Interceptor - Acquire enemies from afar"),
                ("Best Situation:", "Head-on approaches, long-distance rocket strikes"),
                ("Limitation:", "Cannot lock hostiles behind, flanking, or <300 px"),
            ]
        else:
            specs = [
                ("Search Geometry:", "150° wide forward arc (±75° around the nose)"),
                ("Minimum Arming Range:", "0 pixels (Zero blind spot point-blank lock)"),
                ("Maximum Target Range:", "420 pixels (Tight defensive perimeter)"),
                ("HUD Visualization:", "Orange arc sector on the minimap"),
                ("Tactical Role:", "Close dogfighting - snap locks on targets crossing your nose"),
                ("Best Situation:", "Turning fights and flanking targets ahead of the wing line"),
                ("Limitation:", "No locks behind the ship or beyond 420 px"),
            ]

        curr_y = y + 44
        for label, val in specs:
            curr_y += self._draw_flow(surface, x + 16, curr_y, w - 32, label, val) + 4

        diagram_rect = pygame.Rect(x + 20, curr_y + 6, w - 40, h - (curr_y - y) - 18)
        widgets.draw_panel(surface, diagram_rect, theme.PANEL, theme.BORDER, brackets=False)

        diag_cx = diagram_rect.centerx
        diag_cy = diagram_rect.y + int(diagram_rect.height * (0.75 if is_cone else 0.52))

        # One-time overlay surface for the translucent detection area (page is cached).
        area = pygame.Surface(diagram_rect.size, pygame.SRCALPHA)
        local_cx = diagram_rect.width // 2
        if is_cone:
            cone_angle = 50
            r_max = int(diagram_rect.height * 0.70)
            r_min = int(r_max * (300 / 1050))
            local_cy = int(diagram_rect.height * 0.75)

            points = [(local_cx, local_cy)]
            start_deg = -90 - (cone_angle / 2)
            end_deg = -90 + (cone_angle / 2)
            steps = 20
            for s in range(steps + 1):
                ang = math.radians(start_deg + (end_deg - start_deg) * (s / steps))
                points.append((local_cx + math.cos(ang) * r_max, local_cy + math.sin(ang) * r_max))
            pygame.draw.polygon(area, (0, 200, 255, 45), points)
            pygame.draw.lines(area, (0, 220, 255, 180), False, points, 2)
            pygame.draw.arc(area, (255, 80, 80, 180),
                            (local_cx - r_min, local_cy - r_min, r_min * 2, r_min * 2),
                            math.radians(180 - end_deg), math.radians(180 - start_deg), 2)
            labels = (("LOCK ZONE: 300px - 1050px (50° Arc)", theme.INFO), ("BLIND ZONE (<300px)", theme.DANGER))
        else:
            r_omni = int(diagram_rect.height * 0.38)
            local_cy = int(diagram_rect.height * 0.52)
            pygame.draw.circle(area, (255, 160, 50, 45), (local_cx, local_cy), r_omni)
            pygame.draw.circle(area, (255, 180, 50, 200), (local_cx, local_cy), r_omni, 2)
            pygame.draw.circle(area, (255, 180, 50, 80), (local_cx, local_cy), int(r_omni * 0.6), 1)
            labels = (
                ("LOCK ZONE: 0px - 420px (Full 360° Sphere)", theme.WARNING),
                ("BLIND ZONE (>420px: Enemies out of range)", theme.DANGER),
            )
        surface.blit(area, diagram_rect.topleft)
        self._draw_mini_ship(surface, diag_cx, diag_cy)
        for i, (text, color) in enumerate(labels):
            self._text(surface, self.font_tag, text, color, (diagram_rect.x + 12, diagram_rect.bottom - 40 + i * 16), diagram_rect.width - 24)

    def _draw_mini_ship(self, surface, x, y):
        """Draws a crisp triangular starship vector icon."""
        nose = (x, y - 14)
        left_wing = (x - 9, y + 10)
        right_wing = (x + 9, y + 10)
        center_aft = (x, y + 6)

        pygame.draw.polygon(surface, theme.SUCCESS, [nose, left_wing, center_aft, right_wing])
        pygame.draw.polygon(surface, COLOR_TEXT_WHITE, [nose, left_wing, center_aft, right_wing], 1)
        pygame.draw.circle(surface, theme.ACCENT, (x, y + 8), 2)

    # =========================================================================
    # TAB 4: FLIGHT CONTROLS & MANUAL
    # =========================================================================

    def _controls_columns(self) -> List[List[str]]:
        """Category groups per column (declaration order of the shared controls reference)."""
        return [[CATEGORY_ORDER[0], CATEGORY_ORDER[1]], [CATEGORY_ORDER[2], CATEGORY_ORDER[3]]]

    def _draw_tab_controls(self, surface, rect):
        """Renders keybindings from the shared controls reference plus system notes."""
        self._draw_title(
            surface, rect, "FLIGHT MANUAL & SYSTEM KEYBINDINGS", COLOR_TEXT_WHITE,
            "Control layout for flight, weapons, stratagems and menus. The same list is shown in Settings.",
        )
        col_w = (rect.width - 24) // 3
        key_w = 172
        row_h = 40
        top = rect.y + 60
        height = rect.height - 76
        curr_x = rect.x + 6

        for categories in self._controls_columns():
            sec_rect = pygame.Rect(curr_x, top, col_w, height)
            widgets.draw_panel(surface, sec_rect, theme.PANEL_RAISED, theme.BORDER, brackets=False)
            ry = top + 12
            for category in categories:
                self._text(surface, self.font_subtitle, category, COLOR_TEXT_ACCENT, (curr_x + 14, ry))
                ry += 28
                for binding in bindings_by_category(category):
                    self._text(surface, self.font_mono, binding.keys, COLOR_TEXT_GOLD, (curr_x + 14, ry + 2), key_w)
                    lines = widgets.wrap_text_px(self.font_body, binding.action, col_w - key_w - 28, max_lines=2)
                    for i, line in enumerate(lines):
                        self._text(surface, self.font_body, line, COLOR_TEXT_MUTED, (curr_x + 14 + key_w, ry + i * 17))
                    ry += row_h
                ry += 6
            curr_x += col_w + 9

        sec_rect = pygame.Rect(curr_x, top, col_w, height)
        widgets.draw_panel(surface, sec_rect, theme.PANEL_RAISED, theme.BORDER, brackets=False)
        self._text(surface, self.font_subtitle, "SYSTEM NOTES", COLOR_TEXT_ACCENT, (curr_x + 14, top + 12))
        ny = top + 40
        for label, desc in SYSTEM_NOTES:
            ny += self._draw_flow(surface, curr_x + 14, ny, col_w - 28, label, desc, COLOR_TEXT_GOLD) + 6

    def controls_page_height_needed(self) -> int:
        """Height the tallest controls column needs (used by layout tests)."""
        row_h, tallest = 40, 0
        for categories in self._controls_columns():
            h = 12
            for category in categories:
                h += 28 + row_h * len(bindings_by_category(category)) + 6
            tallest = max(tallest, h)
        return tallest

    def system_notes_height_needed(self) -> int:
        col_w = (self.content_rect.width - 24) // 3
        return 40 + sum(self._flow_height(label, desc, col_w - 28) + 6 for label, desc in SYSTEM_NOTES)

    # =========================================================================
    # TAB 5 / 6: INTEL CARDS (ENEMIES, SQUAD)
    # =========================================================================

    def measure_intel_card(self, card, w) -> int:
        """Height needed to show ``card`` at width ``w`` without clipping."""
        text_w = w - 32 - 14
        body = sum(self._flow_height(label, desc, text_w) + 4 for label, desc in card["bullets"])
        return 40 + body + 8 + 28

    def _draw_tab_waves(self, surface, rect):
        """Renders intelligence on wave progression, squadron flight, agro radius, and combat AI."""
        self._draw_title(
            surface, rect, "ENEMY COMBAT INTEL, WAVE FORMATIONS & SURVIVAL TACTICS", theme.DANGER,
            "Hostile formations, 1000px agro awareness, alignment-gated ballistics, and anti-retreat nanite drops.",
        )
        self._draw_intel_grid(surface, rect, WAVE_CARDS, rect.y + 56)

    def _draw_tab_helldivers(self, surface, rect):
        """Renders guide for ground Helldivers, Air Strike Arsenal, and CAS objectives."""
        self._draw_title(
            surface, rect, "HELLDIVERS GROUND SUPPORT & CLOSE AIR SUPPORT", theme.INFO,
            "Protect allied Helldiver ground forces, call in stratagems, provide close air support, and secure extraction.",
        )
        self._draw_intel_grid(surface, rect, SQUAD_CARDS, rect.y + 56)

    def _draw_intel_grid(self, surface, rect, cards, start_y):
        col_w = (rect.width - 24) // 2
        spacing_y = 10
        card_h = (rect.height - (start_y - rect.y) - 14 - spacing_y) // 2
        positions = [
            (rect.x + 5, start_y), (rect.x + 15 + col_w, start_y),
            (rect.x + 5, start_y + card_h + spacing_y), (rect.x + 15 + col_w, start_y + card_h + spacing_y),
        ]
        for card, (cx, cy) in zip(cards, positions):
            self._draw_intel_card(surface, cx, cy, col_w, card_h, card)

    def _draw_intel_card(self, surface, x, y, w, h, card):
        """Renders an intel briefing card with a header badge, flowing bullet points, and an accent bar."""
        c_rect = pygame.Rect(x, y, w, h)
        widgets.draw_panel(surface, c_rect, theme.PANEL_RAISED, theme.BORDER, brackets=False)
        pygame.draw.rect(surface, card["accent"], (x, y, 3, h))

        tag_surf = self._cache.render(self.font_tag, card["tag"], COLOR_TEXT_WHITE)
        tag_rect = tag_surf.get_rect(topright=(x + w - 14, y + 10))
        tag_box = tag_rect.inflate(10, 4)
        widgets.draw_panel(surface, tag_box, theme.PANEL, card["accent"], brackets=False)
        surface.blit(tag_surf, tag_rect.topleft)
        self._text(surface, self.font_heading, card["title"].upper(), card["accent"], (x + 16, y + 9), tag_box.x - x - 28)

        pygame.draw.line(surface, theme.BORDER, (x + 14, y + 33), (x + w - 14, y + 33), 1)

        curr_y = y + 40
        text_w = w - 32 - 14
        for label, desc in card["bullets"]:
            pygame.draw.rect(surface, card["accent"], (x + 16, curr_y + 6, 5, 5))
            curr_y += self._draw_flow(surface, x + 30, curr_y, text_w, label, desc) + 4

        if card.get("footer"):
            foot_bg = pygame.Rect(x + 14, y + h - 28, w - 28, 20)
            widgets.draw_panel(surface, foot_bg, theme.PANEL, theme.BORDER, brackets=False)
            self._text(surface, self.font_body, card["footer"], VALUE_TEXT, (x + 20, y + h - 27), w - 40)
