"""
help_menu.py - In-Game Help and Tactical Guide for Eagle-1-64Bit

Provides an interactive, multi-tab help menu detailing:
- Weapons: Specific damages, ranges, velocities, cooldowns, and capacities.
- Abilities: 8 tactical power-ups across Common, Rare, and Epic tiers, plus passives.
- Radar Modes: Comprehensive explanation of CONE vs OMNI targeting with visual diagrams.
- Flight Controls: Complete keybinding reference.
"""

import math
import pygame

# Color Palette (consistent with game UI & sci-fi theme)
COLOR_BG_OVERLAY = (10, 14, 22, 240)
COLOR_PANEL_BG = (18, 24, 38)
COLOR_PANEL_BORDER = (45, 65, 95)
COLOR_TEXT_WHITE = (245, 245, 250)
COLOR_TEXT_MUTED = (160, 175, 200)
COLOR_TEXT_ACCENT = (0, 210, 255)       # Cyber Cyan
COLOR_TEXT_GOLD = (255, 195, 50)        # Weapons Gold
COLOR_TEXT_GREEN = (46, 204, 113)       # Common / Success
COLOR_TEXT_BLUE = (52, 152, 219)        # Rare
COLOR_TEXT_PURPLE = (175, 100, 240)     # Epic
COLOR_TEXT_RED = (255, 75, 75)          # Danger / Hostile

COLOR_TAB_INACTIVE_BG = (22, 30, 48)
COLOR_TAB_INACTIVE_BORDER = (50, 70, 105)
COLOR_TAB_HOVER_BG = (35, 50, 80)
COLOR_TAB_ACTIVE_BG = (0, 120, 180)
COLOR_TAB_ACTIVE_BORDER = (0, 220, 255)


class HelpMenu:
    """Interactive In-Game Help Menu supporting mouse and keyboard navigation."""

    TAB_WEAPONS = 0
    TAB_ABILITIES = 1
    TAB_RADAR = 2
    TAB_CONTROLS = 3
    TAB_WAVES = 4
    TAB_HELLDIVERS = 5

    TAB_NAMES = [
        "1. Weapons & Combat",
        "2. Abilities & Buffs",
        "3. Radar Modes (Q)",
        "4. Controls Manual",
        "5. Waves & Enemy AI",
        "6. Helldivers & Strikes",
    ]

    def __init__(self, width=1280, height=720):
        self.width = width
        self.height = height
        self.active_tab = self.TAB_WEAPONS

        # Initialize fonts lazily or safely
        if not pygame.font.get_init():
            pygame.font.init()

        self.font_title = pygame.font.SysFont("arial", 28, bold=True)
        self.font_subtitle = pygame.font.SysFont("arial", 18, bold=True)
        self.font_heading = pygame.font.SysFont("arial", 16, bold=True)
        self.font_body = pygame.font.SysFont("arial", 13, bold=False)
        self.font_body_bold = pygame.font.SysFont("arial", 13, bold=True)
        self.font_small = pygame.font.SysFont("arial", 12, bold=False)
        self.font_tag = pygame.font.SysFont("arial", 11, bold=True)

        # Tab button rectangles
        self.tab_rects = []
        self._init_tab_rects()

        # Close button rect (top right)
        self.close_btn_rect = pygame.Rect(self.width - 145, 20, 115, 36)

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
                # Check Close button
                if self.close_btn_rect.collidepoint(mouse_pos):
                    return "close"

                # Check Tab buttons
                for i, rect in enumerate(self.tab_rects):
                    if rect.collidepoint(mouse_pos):
                        self.active_tab = i
                        return "tab_changed"

        elif event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_ESCAPE, pygame.K_h):
                return "close"
            elif event.key == pygame.K_1:
                self.active_tab = self.TAB_WEAPONS
                return "tab_changed"
            elif event.key == pygame.K_2:
                self.active_tab = self.TAB_ABILITIES
                return "tab_changed"
            elif event.key == pygame.K_3:
                self.active_tab = self.TAB_RADAR
                return "tab_changed"
            elif event.key == pygame.K_4:
                self.active_tab = self.TAB_CONTROLS
                return "tab_changed"
            elif event.key == pygame.K_5:
                self.active_tab = self.TAB_WAVES
                return "tab_changed"
            elif event.key == pygame.K_6:
                self.active_tab = self.TAB_HELLDIVERS
                return "tab_changed"
            elif event.key in (pygame.K_TAB, pygame.K_RIGHT):
                self.next_tab()
                return "tab_changed"
            elif event.key == pygame.K_LEFT:
                self.prev_tab()
                return "tab_changed"

        return None

    # =========================================================================
    # DRAWING & RENDERING
    # =========================================================================

    def draw(self, surface, mouse_pos=None):
        """Renders the entire help menu overlay onto the target surface."""
        # Semi-transparent dark backdrop
        overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        overlay.fill(COLOR_BG_OVERLAY)
        surface.blit(overlay, (0, 0))

        # Main window panel
        margin_x = 24
        margin_y = 15
        panel_rect = pygame.Rect(margin_x, margin_y, self.width - 2 * margin_x, self.height - 2 * margin_y)
        pygame.draw.rect(surface, (14, 18, 28), panel_rect, border_radius=10)
        pygame.draw.rect(surface, COLOR_PANEL_BORDER, panel_rect, width=2, border_radius=10)

        # Header Tabs
        self._draw_tabs(surface, mouse_pos)

        # Close Button
        self._draw_close_button(surface, mouse_pos)

        # Horizontal separator line under header
        pygame.draw.line(surface, COLOR_PANEL_BORDER, (margin_x + 10, 68), (self.width - margin_x - 10, 68), 1)

        # Content area
        content_rect = pygame.Rect(margin_x + 16, 76, self.width - 2 * margin_x - 32, self.height - margin_y - 120)

        if self.active_tab == self.TAB_WEAPONS:
            self._draw_tab_weapons(surface, content_rect)
        elif self.active_tab == self.TAB_ABILITIES:
            self._draw_tab_abilities(surface, content_rect)
        elif self.active_tab == self.TAB_RADAR:
            self._draw_tab_radar(surface, content_rect)
        elif self.active_tab == self.TAB_CONTROLS:
            self._draw_tab_controls(surface, content_rect)
        elif self.active_tab == self.TAB_WAVES:
            self._draw_tab_waves(surface, content_rect)
        elif self.active_tab == self.TAB_HELLDIVERS:
            self._draw_tab_helldivers(surface, content_rect)

        # Footer Navigation Bar
        self._draw_footer(surface)

    def _draw_tabs(self, surface, mouse_pos):
        """Draws top tab navigation buttons."""
        for i, rect in enumerate(self.tab_rects):
            is_active = (i == self.active_tab)
            is_hovered = (mouse_pos is not None and rect.collidepoint(mouse_pos))

            if is_active:
                bg = COLOR_TAB_ACTIVE_BG
                border = COLOR_TAB_ACTIVE_BORDER
                txt_color = COLOR_TEXT_WHITE
            elif is_hovered:
                bg = COLOR_TAB_HOVER_BG
                border = COLOR_TEXT_ACCENT
                txt_color = COLOR_TEXT_WHITE
            else:
                bg = COLOR_TAB_INACTIVE_BG
                border = COLOR_TAB_INACTIVE_BORDER
                txt_color = COLOR_TEXT_MUTED

            pygame.draw.rect(surface, bg, rect, border_radius=6)
            pygame.draw.rect(surface, border, rect, width=1, border_radius=6)

            label = self.font_subtitle.render(self.TAB_NAMES[i], True, txt_color)
            label_rect = label.get_rect(center=rect.center)
            surface.blit(label, label_rect)

    def _draw_close_button(self, surface, mouse_pos):
        """Draws the Close / Return button."""
        is_hovered = (mouse_pos is not None and self.close_btn_rect.collidepoint(mouse_pos))
        bg = (160, 40, 40) if is_hovered else (80, 25, 30)
        border = COLOR_TEXT_RED if is_hovered else (140, 50, 50)

        pygame.draw.rect(surface, bg, self.close_btn_rect, border_radius=6)
        pygame.draw.rect(surface, border, self.close_btn_rect, width=1, border_radius=6)

        txt = self.font_subtitle.render("Close (ESC)", True, COLOR_TEXT_WHITE)
        txt_rect = txt.get_rect(center=self.close_btn_rect.center)
        surface.blit(txt, txt_rect)

    def _draw_footer(self, surface):
        """Draws bottom bar with keybinding guidance."""
        footer_rect = pygame.Rect(34, self.height - 48, self.width - 68, 30)
        pygame.draw.rect(surface, (18, 24, 38), footer_rect, border_radius=5)
        pygame.draw.rect(surface, (35, 50, 75), footer_rect, width=1, border_radius=5)

        hints = "[1-6] Quick Tab Switch  |  [TAB / Arrows] Cycle Tabs  |  [ESC / H] Return to Game"
        txt = self.font_body.render(hints, True, COLOR_TEXT_MUTED)
        txt_rect = txt.get_rect(center=footer_rect.center)
        surface.blit(txt, txt_rect)

    # =========================================================================
    # TAB 1: WEAPONS & COMBAT
    # =========================================================================

    def _draw_tab_weapons(self, surface, rect):
        """Renders comprehensive weapon specifications, damages, and ranges."""
        # Section Title
        title = self.font_title.render("STARBLAST WEAPONRY & COMBAT SYSTEMS", True, COLOR_TEXT_GOLD)
        surface.blit(title, (rect.x + 10, rect.y + 4))

        sub = self.font_small.render("Tactical specifications, exact damages, projectile speeds, and effective engagement ranges.", True, COLOR_TEXT_MUTED)
        surface.blit(sub, (rect.x + 12, rect.y + 36))

        weapons = [
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
                "damage": "4 DMG (Heavy Kinetic Explosion)",
                "range": "1200 px max target tracking range  |  2.5s maximum flight lifetime",
                "cooldown": "350 ms firing delay  |  Velocity: 7.0 px/frame  |  Agility: 2.0°/frame",
                "capacity": "4 rockets  |  Reload: 25.0s when all 4 rockets are exhausted",
                "notes": "Requires active Radar Lock (target inside CONE or OMNI lock zone). Automatically locks closest hostile in radar zone across all active wave squadrons.",
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
                "name": "Kamikaze Hull Collision",
                "type": "Emergency Melee Contact",
                "trigger": "Ramming directly into an enemy aircraft",
                "damage": "4 DMG dealt to enemy aircraft  |  Self-Damage: 5 explosion DMG received",
                "range": "0 px (Direct physical impact)",
                "cooldown": "Immediate upon contact  |  Triggers 1.0s temporary invincibility",
                "capacity": "Limited by remaining hull integrity and shield points",
                "notes": "High-risk maneuver. Absorbed by shield if available, otherwise inflicts direct hull damage.",
                "color": (255, 80, 80),
            },
        ]

        card_y = rect.y + 58
        card_w = rect.width - 10
        card_h = 92
        spacing = 9

        for w in weapons:
            card_rect = pygame.Rect(rect.x + 5, card_y, card_w, card_h)
            pygame.draw.rect(surface, COLOR_PANEL_BG, card_rect, border_radius=6)
            pygame.draw.rect(surface, (35, 50, 75), card_rect, width=1, border_radius=6)

            # Left accent indicator bar
            pygame.draw.rect(surface, w["color"], (rect.x + 5, card_y, 4, card_h), border_top_left_radius=6, border_bottom_left_radius=6)

            # Name & Type
            name_txt = self.font_heading.render(w["name"], True, w["color"])
            surface.blit(name_txt, (rect.x + 18, card_y + 6))

            type_txt = self.font_small.render(f"[{w['type']}]", True, COLOR_TEXT_MUTED)
            surface.blit(type_txt, (rect.x + 28 + name_txt.get_width(), card_y + 8))

            trig_txt = self.font_small.render(f"Fire: {w['trigger']}", True, COLOR_TEXT_ACCENT)
            surface.blit(trig_txt, (rect.x + card_w - trig_txt.get_width() - 14, card_y + 7))

            # Row 1: Damage & Range
            dmg_label = self.font_body_bold.render("Damage: ", True, COLOR_TEXT_WHITE)
            dmg_val = self.font_body.render(w["damage"], True, (255, 235, 150))
            surface.blit(dmg_label, (rect.x + 18, card_y + 28))
            surface.blit(dmg_val, (rect.x + 18 + dmg_label.get_width(), card_y + 28))

            rng_label = self.font_body_bold.render("Range: ", True, COLOR_TEXT_WHITE)
            rng_val = self.font_body.render(w["range"], True, (160, 225, 255))
            surface.blit(rng_label, (rect.x + 18, card_y + 48))
            surface.blit(rng_val, (rect.x + 18 + rng_label.get_width(), card_y + 48))

            # Row 2: Capacity & Tactical notes
            cap_txt = self.font_small.render(f"Capacity / Cooldown: {w['capacity']}  |  {w['cooldown']}", True, (200, 210, 225))
            surface.blit(cap_txt, (rect.x + 18, card_y + 68))

            card_y += card_h + spacing

    # =========================================================================
    # TAB 2: ABILITIES & BUFFS
    # =========================================================================

    def _draw_tab_abilities(self, surface, rect):
        """Renders all 8 tactical power-ups across rarity tiers, plus passives."""
        title = self.font_title.render("TACTICAL ABILITIES & POWER-UP SUBSYSTEM", True, COLOR_TEXT_ACCENT)
        surface.blit(title, (rect.x + 10, rect.y + 4))

        meta = self.font_small.render(
            "Drops: 8% Base Chance on kill (+3% Pity per kill without drop)  |  Milestone Airdrops at 1K, 5K, 10K, 25K, 50K  |  Magnet Pull: 130 px",
            True,
            COLOR_TEXT_MUTED
        )
        surface.blit(meta, (rect.x + 12, rect.y + 34))

        col_w = (rect.width - 24) // 2
        card_h = 76
        start_y = rect.y + 54
        spacing_y = 8

        col1_items = [
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

        col2_items = [
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

        # Draw Column 1
        curr_y = start_y
        for item in col1_items:
            self._draw_ability_card(surface, rect.x + 5, curr_y, col_w, card_h, item)
            curr_y += card_h + spacing_y

        # Draw Column 2
        curr_y = start_y
        for item in col2_items:
            self._draw_ability_card(surface, rect.x + 15 + col_w, curr_y, col_w, card_h, item)
            curr_y += card_h + spacing_y

    def _draw_ability_card(self, surface, x, y, w, h, item):
        """Renders an individual ability card."""
        c_rect = pygame.Rect(x, y, w, h)
        pygame.draw.rect(surface, COLOR_PANEL_BG, c_rect, border_radius=6)
        pygame.draw.rect(surface, (35, 50, 75), c_rect, width=1, border_radius=6)

        # Left accent stripe
        pygame.draw.rect(surface, item["color"], (x, y, 4, h), border_top_left_radius=6, border_bottom_left_radius=6)

        # Header: Name + Tier + Duration
        name_txt = self.font_heading.render(item["name"], True, item["color"])
        surface.blit(name_txt, (x + 14, y + 5))

        dur_txt = self.font_small.render(f"[{item['dur']}]", True, COLOR_TEXT_WHITE)
        surface.blit(dur_txt, (x + w - dur_txt.get_width() - 10, y + 7))

        tier_txt = self.font_tag.render(item["tier"], True, item["tier_color"])
        surface.blit(tier_txt, (x + 14 + name_txt.get_width() + 10, y + 8))

        # Stats
        stats_txt = self.font_body_bold.render(item["stats"], True, (255, 235, 160))
        surface.blit(stats_txt, (x + 14, y + 27))

        # Desc
        desc_txt = self.font_small.render(item["desc"], True, COLOR_TEXT_MUTED)
        surface.blit(desc_txt, (x + 14, y + 49))

    # =========================================================================
    # TAB 3: RADAR MODES (CONE vs OMNI)
    # =========================================================================

    def _draw_tab_radar(self, surface, rect):
        """Renders thorough breakdown and visual diagrams of CONE vs OMNI radar modes."""
        title = self.font_title.render("DUAL RADAR TARGETING MODES: CONE vs OMNI", True, (50, 255, 170))
        surface.blit(title, (rect.x + 10, rect.y + 4))

        toggle_banner = self.font_heading.render(
            "HOTKEY: Press [ Q ] during flight to instantly toggle between CONE and OMNI radar modes",
            True,
            COLOR_TEXT_GOLD
        )
        surface.blit(toggle_banner, (rect.x + 12, rect.y + 34))

        col_w = (rect.width - 24) // 2
        card_h = rect.height - 76
        start_y = rect.y + 60

        # Left Column: CONE MODE
        self._draw_radar_mode_panel(
            surface,
            x=rect.x + 5,
            y=start_y,
            w=col_w,
            h=card_h,
            is_cone=True
        )

        # Right Column: OMNI MODE
        self._draw_radar_mode_panel(
            surface,
            x=rect.x + 15 + col_w,
            y=start_y,
            w=col_w,
            h=card_h,
            is_cone=False
        )

    def _draw_radar_mode_panel(self, surface, x, y, w, h, is_cone):
        """Draws radar mode details along with a live diagram illustrating the detection area."""
        p_rect = pygame.Rect(x, y, w, h)
        accent_color = (0, 220, 255) if is_cone else (255, 150, 50)

        pygame.draw.rect(surface, COLOR_PANEL_BG, p_rect, border_radius=8)
        pygame.draw.rect(surface, accent_color, p_rect, width=2, border_radius=8)

        # Top Title
        mode_title = "MODE 1: CONE (Long-Range Forward Sector)" if is_cone else "MODE 2: OMNI (360° Close-Quarters Sphere)"
        title_surf = self.font_subtitle.render(mode_title, True, accent_color)
        surface.blit(title_surf, (x + 16, y + 12))

        # Specifications & Parameters
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
                ("Search Geometry:", "Full 360° Spherical Perimeter around ship"),
                ("Minimum Arming Range:", "0 pixels (Zero blind spot point-blank lock)"),
                ("Maximum Target Range:", "420 pixels (Tight defensive perimeter)"),
                ("HUD Visualization:", "Glowing 360° circular perimeter ring around ship"),
                ("Tactical Role:", "Close Dogfighting & Defense - 360° situational awareness"),
                ("Best Situation:", "Enemies maneuvering behind you, circling, or flanking"),
                ("Limitation:", "Cannot acquire distant targets (>420 pixels)"),
            ]

        curr_y = y + 42
        for label, val in specs:
            l_surf = self.font_body_bold.render(label, True, COLOR_TEXT_WHITE)
            v_surf = self.font_body.render(val, True, COLOR_TEXT_MUTED)
            surface.blit(l_surf, (x + 16, curr_y))
            surface.blit(v_surf, (x + 16 + l_surf.get_width() + 6, curr_y))
            curr_y += 22

        # Visual Diagram Area
        diagram_rect = pygame.Rect(x + 20, curr_y + 10, w - 40, h - (curr_y - y) - 22)
        pygame.draw.rect(surface, (12, 16, 26), diagram_rect, border_radius=6)
        pygame.draw.rect(surface, (30, 45, 70), diagram_rect, width=1, border_radius=6)

        diag_cx = diagram_rect.centerx
        diag_cy = diagram_rect.y + int(diagram_rect.height * (0.75 if is_cone else 0.52))

        if is_cone:
            cone_angle = 50
            r_max = int(diagram_rect.height * 0.70)
            r_min = int(r_max * (300 / 1050))

            cone_surf = pygame.Surface((w - 40, diagram_rect.height), pygame.SRCALPHA)
            local_cx = (w - 40) // 2
            local_cy = int(diagram_rect.height * 0.75)

            points = [(local_cx, local_cy)]
            start_deg = -90 - (cone_angle / 2)
            end_deg = -90 + (cone_angle / 2)
            steps = 20
            for s in range(steps + 1):
                ang = math.radians(start_deg + (end_deg - start_deg) * (s / steps))
                px = local_cx + math.cos(ang) * r_max
                py = local_cy + math.sin(ang) * r_max
                points.append((px, py))
            pygame.draw.polygon(cone_surf, (0, 200, 255, 45), points)
            pygame.draw.lines(cone_surf, (0, 220, 255, 180), False, points, 2)

            pygame.draw.arc(cone_surf, (255, 80, 80, 180),
                            (local_cx - r_min, local_cy - r_min, r_min * 2, r_min * 2),
                            math.radians(180 - end_deg), math.radians(180 - start_deg), 2)

            surface.blit(cone_surf, (diagram_rect.x, diagram_rect.y))
            self._draw_mini_ship(surface, diag_cx, diag_cy, heading_deg=0)

            lbl1 = self.font_tag.render("LOCK ZONE: 300px - 1050px (50° Arc)", True, (0, 220, 255))
            lbl2 = self.font_tag.render("BLIND ZONE (<300px)", True, (255, 100, 100))
            surface.blit(lbl1, (diagram_rect.x + 12, diagram_rect.y + 8))
            surface.blit(lbl2, (diagram_rect.x + 12, diagram_rect.y + 24))

        else:
            r_omni = int(diagram_rect.height * 0.38)
            circle_surf = pygame.Surface((w - 40, diagram_rect.height), pygame.SRCALPHA)
            local_cx = (w - 40) // 2
            local_cy = int(diagram_rect.height * 0.52)

            pygame.draw.circle(circle_surf, (255, 160, 50, 45), (local_cx, local_cy), r_omni)
            pygame.draw.circle(circle_surf, (255, 180, 50, 200), (local_cx, local_cy), r_omni, 2)
            pygame.draw.circle(circle_surf, (255, 180, 50, 80), (local_cx, local_cy), int(r_omni * 0.6), 1)

            surface.blit(circle_surf, (diagram_rect.x, diagram_rect.y))
            self._draw_mini_ship(surface, diag_cx, diag_cy, heading_deg=0)

            lbl1 = self.font_tag.render("LOCK ZONE: 0px - 420px (Full 360° Sphere)", True, (255, 180, 50))
            lbl2 = self.font_tag.render("BLIND ZONE (>420px: Enemies out of range)", True, (255, 100, 100))
            surface.blit(lbl1, (diagram_rect.x + 12, diagram_rect.y + 8))
            surface.blit(lbl2, (diagram_rect.x + 12, diagram_rect.y + 24))

    def _draw_mini_ship(self, surface, x, y, heading_deg=0):
        """Draws a crisp triangular starship vector icon."""
        nose = (x, y - 14)
        left_wing = (x - 9, y + 10)
        right_wing = (x + 9, y + 10)
        center_aft = (x, y + 6)

        pygame.draw.polygon(surface, (0, 255, 150), [nose, left_wing, center_aft, right_wing])
        pygame.draw.polygon(surface, COLOR_TEXT_WHITE, [nose, left_wing, center_aft, right_wing], 1)
        pygame.draw.circle(surface, (255, 200, 0), (x, y + 8), 2)

    # =========================================================================
    # TAB 4: FLIGHT CONTROLS & MANUAL
    # =========================================================================

    def _draw_tab_controls(self, surface, rect):
        """Renders comprehensive keybinding and flight mechanics guide."""
        title = self.font_title.render("FLIGHT MANUAL & SYSTEM KEYBINDINGS", True, COLOR_TEXT_WHITE)
        surface.blit(title, (rect.x + 10, rect.y + 4))

        sub = self.font_small.render("Full control layout for flight maneuvering, weapon systems, radar management, and menu navigation.", True, COLOR_TEXT_MUTED)
        surface.blit(sub, (rect.x + 12, rect.y + 36))

        controls = [
            ("FLIGHT & PROPULSION", [
                ("W / UP ARROW", "Accelerate / Increase Throttle (Min: 2.0 -> Max: 7.0 px/frame)"),
                ("S / DOWN ARROW", "Decelerate / Airbrake (Down to minimum speed 2.0)"),
                ("A / LEFT ARROW", "Rotate Left / Bank Port (Turn rate: 3.0° per frame)"),
                ("D / RIGHT ARROW", "Rotate Right / Bank Starboard (Turn rate: 3.0° per frame)"),
                ("SPEEDOMETER HUD", "Bottom-left gauge monitors current vs maximum velocity"),
            ]),
            ("WEAPONS & COMBAT", [
                ("SPACEBAR", "Fire Main Quad Autocannon (200 rounds, 50 quad bursts)"),
                ("E / F / L-CTRL", "Fire Homing Rocket (Requires active Radar Lock in CONE/OMNI)"),
                ("RIGHT MOUSE CLICK", "Alternative Fire: Launch Homing Rocket"),
                ("AUTOMATIC RELOAD", "Autocannon reloads in 5.0s; Rockets reload in 25.0s when depleted"),
            ]),
            ("SYSTEMS & NAVIGATION", [
                ("Q KEY", "Toggle Radar Mode (CONE: 300-1050px forward  <->  OMNI: 360° 0-420px)"),
                ("P KEY", "Pause Game / Open In-Game Pause Menu"),
                ("H KEY", "Open Help & Tactical Guide (Accessible in Pause, Respawn, & Main Menu)"),
                ("1 - 5 KEYS", "Quick-switch tabs in Help Guide  |  TAB / Arrows cycle tabs"),
                ("WAVE HUD & MINIMAP", "Top-left HUD shows Wave & Hostiles; Radar shows Orange (patrol) & Red (agro)"),
                ("ESC KEY", "Return to Main Menu (from Pause)  /  Close Help Menu"),
                ("R KEY / SHIFT+R", "Press R to Respawn  |  L-SHIFT+R-SHIFT+R resets Highscore in Menu"),
            ]),
        ]

        section_w = (rect.width - 24) // 3
        curr_x = rect.x + 6

        for sec_title, bindings in controls:
            sec_rect = pygame.Rect(curr_x, rect.y + 60, section_w, rect.height - 76)
            pygame.draw.rect(surface, COLOR_PANEL_BG, sec_rect, border_radius=8)
            pygame.draw.rect(surface, (35, 50, 75), sec_rect, width=1, border_radius=8)

            # Section Header
            hdr = self.font_subtitle.render(sec_title, True, COLOR_TEXT_ACCENT)
            surface.blit(hdr, (curr_x + 14, rect.y + 72))
            pygame.draw.line(surface, (45, 65, 95), (curr_x + 14, rect.y + 100), (curr_x + section_w - 14, rect.y + 100), 1)

            entry_y = rect.y + 112
            for key_str, desc_str in bindings:
                badge_surf = self.font_heading.render(key_str, True, COLOR_TEXT_GOLD)
                badge_bg = pygame.Rect(curr_x + 14, entry_y, section_w - 28, 22)
                pygame.draw.rect(surface, (25, 34, 52), badge_bg, border_radius=4)
                pygame.draw.rect(surface, (50, 70, 105), badge_bg, width=1, border_radius=4)
                surface.blit(badge_surf, (curr_x + 20, entry_y + 2))

                desc_surf = self.font_body.render(desc_str, True, COLOR_TEXT_MUTED)
                surface.blit(desc_surf, (curr_x + 16, entry_y + 28))

                entry_y += 54

            curr_x += section_w + 9

    # =========================================================================
    # TAB 5: ENEMY INTEL & WAVE SYSTEM
    # =========================================================================

    def _draw_tab_waves(self, surface, rect):
        """Renders comprehensive intelligence on wave progression, squadron flight, agro radius, and combat AI."""
        title = self.font_title.render("ENEMY COMBAT INTEL, WAVE FORMATIONS & SURVIVAL TACTICS", True, (255, 90, 90))
        surface.blit(title, (rect.x + 10, rect.y + 4))

        sub = self.font_small.render(
            "Tactical intelligence on hostile squadron formations, 1000px agro awareness, alignment-gated ballistics, and anti-retreat nanite drops.",
            True,
            COLOR_TEXT_MUTED
        )
        surface.blit(sub, (rect.x + 12, rect.y + 34))

        col_w = (rect.width - 24) // 2
        card_h = (rect.height - 76) // 2
        start_y = rect.y + 54
        spacing_y = 12

        card1 = {
            "title": "1. Wave Scaling & Squadron Flocking",
            "tag": "WAVES 1 - 10 | CAP: 8 PLANES",
            "accent": COLOR_TEXT_GOLD,
            "bullets": [
                ("Wave Progression & Cap:", "Waves dynamically scale from Wave 1 up to Wave 10 (MAX_WAVE_LEVEL = 10)."),
                ("Hostile Limit (Anti-Lag):", "Max 8 simultaneous enemies per wave (MAX_ENEMIES_PER_WAVE = 8) to protect PC performance."),
                ("Tactical Squadron Formations:", "Enemies deploy in coordinated flights of 2-4 planes in V-formation rather than solo."),
                ("Boids Flocking Separation:", "Units maintain spatial separation (70px repulsion radius) to eliminate clipping or stacking."),
            ],
            "footer": "Wave Clear Bonus: +250 x Wave Level awarded during the 3-second intermission banner.",
        }

        card2 = {
            "title": "2. 1000px Agro Perimeter & Map Circling",
            "tag": "AGRO: 1000px | DE-AGRO: 1500px",
            "accent": COLOR_TEXT_ACCENT,
            "bullets": [
                ("Patrol State (Holding Fire):", "Outside 1000px, squadrons orbit the map center at 2.0 px/frame without shooting."),
                ("Squadron Alert Network:", "Breaching 1000px or damaging any plane immediately alerts the ENTIRE squadron."),
                ("Pursuit Acceleration:", "Alerted hostiles enter AGRO state and accelerate to 3.2 px/frame (60% speed increase)."),
                ("Minimap Tactical Blips:", "Minimap radar displays patrolling squadrons as ORANGE dots and alerted pursuers as RED dots."),
            ],
            "footer": "Tactical Note: Attacking an orbiting formation triggers immediate pursuit from all wingmen!",
        }

        card3 = {
            "title": "3. Smart Combat AI & Directional Ballistics",
            "tag": "AIM GATE: ±15° | TURN: 2.0°/F",
            "accent": (255, 130, 60),
            "bullets": [
                ("Line-of-Sight Tracking:", "Calculates true angle to player via atan2 math, turning smoothly at 2.0° per frame."),
                ("Alignment-Gated Firing:", "Hostiles hold fire until nose is aligned within ±15° of line of sight (no blind spam)."),
                ("True 2D Vector Ballistics:", "Enemy bullets fire from the nose carrying directional velocity (dx, dy) towards player."),
                ("Debuff Susceptibility:", "Enemy turn rate, thrust, and bullets are realistically impaired by Time Slow & Cryo Freeze."),
            ],
            "footer": "Evasion Tip: Banking sharply 90° across the enemy's nose breaks their ±15° firing alignment!",
        }

        card4 = {
            "title": "4. Anti-Retreat Dynamics & Adrenaline Overdrive",
            "tag": "CRITICAL HP <= 2 | HEAL ON KILL",
            "accent": (50, 255, 120),
            "bullets": [
                ("The Low-HP Dilemma:", "Shields passively recover, but Hull HP NEVER regenerates. Running at low HP is fatal."),
                ("High-Speed Pursuit:", "Enemies hunt at 3.2 px/frame in AGRO; you cannot easily outrun alerted squadrons."),
                ("Kill-to-Heal Nanites:", "When at critical hull (<= 2 HP), every defeated enemy drops a guaranteed +1 HP Nanite!"),
                ("Adrenaline Overdrive:", "Operating at <= 2 HP grants +50% score bonus and 25% faster weapon cyclic fire & reload."),
            ],
            "footer": "Tactical Doctrine: Never flee when damaged! Turn into hostiles, kill, and harvest health nanites.",
        }

        # Row 1
        self._draw_intel_card(surface, rect.x + 5, start_y, col_w, card_h, card1)
        self._draw_intel_card(surface, rect.x + 15 + col_w, start_y, col_w, card_h, card2)

        # Row 2
        self._draw_intel_card(surface, rect.x + 5, start_y + card_h + spacing_y, col_w, card_h, card3)
        self._draw_intel_card(surface, rect.x + 15 + col_w, start_y + card_h + spacing_y, col_w, card_h, card4)

    def _draw_intel_card(self, surface, x, y, w, h, card):
        """Renders an intel briefing card with a header badge, bullet points, and an accent bar."""
        c_rect = pygame.Rect(x, y, w, h)
        pygame.draw.rect(surface, COLOR_PANEL_BG, c_rect, border_radius=8)
        pygame.draw.rect(surface, (35, 50, 75), c_rect, width=1, border_radius=8)

        # Left accent stripe
        pygame.draw.rect(surface, card["accent"], (x, y, 5, h), border_top_left_radius=8, border_bottom_left_radius=8)

        # Header: Title & Tag
        title_surf = self.font_heading.render(card["title"], True, card["accent"])
        surface.blit(title_surf, (x + 16, y + 9))

        tag_surf = self.font_tag.render(card["tag"], True, COLOR_TEXT_WHITE)
        tag_bg = tag_surf.get_rect(topright=(x + w - 14, y + 10))
        tag_box = tag_bg.inflate(10, 4)
        pygame.draw.rect(surface, (25, 34, 52), tag_box, border_radius=4)
        pygame.draw.rect(surface, card["accent"], tag_box, width=1, border_radius=4)
        surface.blit(tag_surf, tag_bg.topleft)

        # Separator line
        pygame.draw.line(surface, (40, 55, 85), (x + 14, y + 33), (x + w - 14, y + 33), 1)

        # Bullets
        curr_y = y + 40
        line_spacing = 40
        for label, desc in card["bullets"]:
            pygame.draw.circle(surface, card["accent"], (x + 22, curr_y + 7), 3)

            lbl_surf = self.font_body_bold.render(label, True, COLOR_TEXT_WHITE)
            surface.blit(lbl_surf, (x + 32, curr_y))

            desc_surf = self.font_small.render(desc, True, COLOR_TEXT_MUTED)
            surface.blit(desc_surf, (x + 32, curr_y + 17))

            curr_y += line_spacing

        # Footer note / tip
        if "footer" in card and card["footer"]:
            foot_bg = pygame.Rect(x + 14, y + h - 28, w - 28, 20)
            pygame.draw.rect(surface, (14, 20, 32), foot_bg, border_radius=4)
            pygame.draw.rect(surface, (40, 60, 90), foot_bg, width=1, border_radius=4)
            foot_surf = self.font_small.render(card["footer"], True, (255, 230, 140))
            surface.blit(foot_surf, (x + 20, y + h - 26))

    # =========================================================================
    # TAB 6: HELLDIVERS & AIR STRIKES
    # =========================================================================

    def _draw_tab_helldivers(self, surface, rect):
        """Renders tactical guide for ground Helldivers, Air Strike Arsenal, and CAS objectives."""
        title = self.font_title.render("HELLDIVERS GROUND SUPPORT & CLOSE AIR SUPPORT (CAS)", True, (0, 220, 255))
        surface.blit(title, (rect.x + 10, rect.y + 4))

        sub = self.font_small.render(
            "Protect allied Helldiver ground forces, call in powerful stratagems, provide close air support, and secure extraction.",
            True,
            COLOR_TEXT_MUTED
        )
        surface.blit(sub, (rect.x + 12, rect.y + 36))

        start_y = rect.y + 60
        card_h = 220
        col_w = (rect.width - 20) // 2
        spacing_y = 12

        card1 = {
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

        card2 = {
            "title": "Air Strike Stratagem Arsenal",
            "tag": "[V] / [TAB] TO OPEN",
            "accent": (255, 200, 50),
            "bullets": [
                ("Arsenal Menu [V] or [TAB]:", "Opens full stratagem selection menu. Choose from 8 unique close air support strikes."),
                ("Quick-Select [1-8]:", "Instant strike swap: [1] Strafe, [2] 500kg, [3] Cluster, [4] Napalm, [5] Gas, [6] Rockets, [7] EMS, [8] Smoke."),
                ("Launch Air Strike [C]:", "Deploys a red stratagem beacon along your heading, calling down heavy ordnance after 0.8s."),
                ("Diverse Effects:", "From massive ground-zero bursts (500kg) to lingering fire lines (Napalm) and toxic clouds (Gas)."),
            ],
            "footer": "HOTKEY: Press [1-8] during flight to instantly change your active strike without opening the menu!",
        }

        card3 = {
            "title": "Tactical Supply Drops & Alerts",
            "tag": "[X] RESUPPLY POD",
            "accent": (0, 200, 255),
            "bullets": [
                ("Supply Drop [X]:", "Calls down an orbital pod delivering medical nanites, full ammo reload, and rockets (30s CD)."),
                ("Ground Resupply:", "Allied Helldivers move to nearby landed supply pods when wounded to restore shields and health."),
                ("Danger Zone Alerts:", "Audible and visual flashing alert banner appears when enemy aircraft close in within 680px."),
                ("Off-Screen Compass:", "Cyan directional pointer at screen borders indicates distance and bearing to the squad."),
            ],
            "footer": "CRITICAL: Drop supply pods near the squad before heavy wave engagements to keep them alive.",
        }

        card4 = {
            "title": "Objectives & CAS Scoring",
            "tag": "OBJECTIVES & REWARDS",
            "accent": (255, 120, 50),
            "bullets": [
                ("Outpost Defense (Waves 1-2):", "Guard the comms outpost and eliminate incoming hostile squadrons."),
                ("Pelican-1 Extraction (Wave 3+):", "Extraction beacon activates a 30s countdown. Hold the perimeter until Pelican lands!"),
                ("Close Air Support (+100 PTS):", "Eliminating enemy aircraft near allied troopers awards bonus CAS score and combat popup."),
                ("Flawless Multiplier (1.5x):", "Earn +500 PTS per survivor at wave end, multiplied by 1.5x if zero casualties were suffered."),
            ],
            "footer": "EXTRACTION: Successfully extract surviving Helldivers for a massive +2,500 point completion bonus!",
        }

        # Row 1
        self._draw_intel_card(surface, rect.x + 5, start_y, col_w, card_h, card1)
        self._draw_intel_card(surface, rect.x + 15 + col_w, start_y, col_w, card_h, card2)

        # Row 2
        self._draw_intel_card(surface, rect.x + 5, start_y + card_h + spacing_y, col_w, card_h, card3)
        self._draw_intel_card(surface, rect.x + 15 + col_w, start_y + card_h + spacing_y, col_w, card_h, card4)

