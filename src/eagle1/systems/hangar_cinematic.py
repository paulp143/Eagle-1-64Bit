"""
hangar_cinematic.py - Super Destroyer Orbital Rearm Cinematic & Stratagem Hero Subsystem.

Encapsulates the 15.0s atmospheric ascent, orbital hangar docking aboard the
Super Destroyer SES, animated robotic ordnance reloading (500kg bomb / rockets),
atmospheric descent re-entry, and the integrated Stratagem Hero arcade terminal minigame.
"""

import logging
import math
import os
import random
import pygame

from eagle1.paths import get_user_data_dir
from eagle1.ui import theme, widgets


logger = logging.getLogger(__name__)

# Rearm Phases
PHASE_NONE = 0
PHASE_ASCENT = 1     # 1.2s: Afterburner climb out of atmosphere
PHASE_HANGAR = 2     # 12.6s: Docked in orbital maintenance bay with Stratagem Hero
PHASE_DESCENT = 3    # 1.2s: Launch catapult and atmospheric re-entry burn

ASCENT_DURATION = 1.2
HANGAR_DURATION = 12.6
DESCENT_DURATION = 1.2
TOTAL_REARM_DURATION = 15.0

MAP_WIDTH = 3000
MAP_HEIGHT = 3000

# Service pad geometry (screen space) and rearm choreography (seconds into the hangar phase)
PAD_X, PAD_Y, PAD_W, PAD_H = 240, 430, 340, 210
SHIP_CX = PAD_X + PAD_W // 2
SHIP_CY = PAD_Y + 105
RAIL_Y = 36
TROLLEY_Y = 42
TROLLEY_HOME_X = SHIP_CX + 150
ARM_ROOT_Y = TROLLEY_Y + 26
ARM_HOME_Y = 150.0
ARM_DOWN_Y = float(SHIP_CY - 37)  # gripper plate top so the hoisted round hangs centered on the airframe
BOMB_W, BOMB_H = 18, 46
BOMB_LATCH_TIME = 3.5
WING_SERVICE_TIME = 5.6
WING_ARM_BASES = ((PAD_X + 12, PAD_Y + 145), (PAD_X + PAD_W - 12, PAD_Y + 145))
WING_ARM_TIPS = ((SHIP_CX - 52, SHIP_CY + 6), (SHIP_CX + 52, SHIP_CY + 6))
WING_ARM_LINKS = (84.0, 70.0)
# (label, start, done) windows for the on-screen rearm sequence checklist
REARM_STEPS = (
    ("ORDNANCE", 0.6, 4.3),
    ("WING PYLONS", 4.5, 7.5),
    ("CHARGES", 7.5, 10.5),
    ("FINAL CHECK", 10.5, 12.0),
)

# Stratagem Hero Sequences
HERO_STRATAGEM_SEQUENCES = [
    ("REINFORCE", ["UP", "DOWN", "RIGHT", "LEFT", "UP"]),
    ("500KG BOMB", ["UP", "RIGHT", "DOWN", "DOWN", "DOWN"]),
    ("ORBITAL LASER", ["RIGHT", "DOWN", "UP", "RIGHT", "DOWN"]),
    ("EAGLE STRAFE", ["UP", "RIGHT", "RIGHT"]),
    ("CLUSTER BOMB", ["UP", "RIGHT", "DOWN", "DOWN", "RIGHT"]),
    ("NAPALM STRIKE", ["UP", "RIGHT", "DOWN", "UP"]),
    ("SUPPLY DROP", ["DOWN", "DOWN", "UP", "RIGHT"]),
    ("RESUPPLY PACK", ["DOWN", "LEFT", "DOWN", "UP", "UP"]),
    ("ROCKET PODS", ["UP", "RIGHT", "UP", "LEFT"]),
    ("EMS STUN STRIKE", ["UP", "LEFT", "DOWN", "RIGHT"]),
    ("SMOKE SCREEN", ["DOWN", "UP", "DOWN", "UP"]),
]

# Direction glyphs supported by the bundled Chakra Petch fonts (see eagle1.ui.theme).
ARROW_SYMBOLS = dict(theme.ARROW_GLYPHS)


def _smooth(t):
    """Clamp ``t`` to 0..1 and apply smoothstep easing."""
    t = max(0.0, min(1.0, t))
    return t * t * (3.0 - 2.0 * t)


def _span(t, start, end):
    """Eased 0..1 progress of ``t`` through the window [start, end]."""
    return _smooth((t - start) / (end - start))


def crane_pose(t):
    """Return ``(trolley_x, gripper_y, grip_open)`` of the overhead hoist ``t`` seconds into the hangar phase."""
    slide = _span(t, 0.0, 1.0) - _span(t, 6.5, 7.5)
    trolley_x = TROLLEY_HOME_X + (SHIP_CX - TROLLEY_HOME_X) * slide
    lift = _span(t, 1.0, BOMB_LATCH_TIME) - _span(t, 4.3, 6.5)
    gripper_y = ARM_HOME_Y + (ARM_DOWN_Y - ARM_HOME_Y) * lift
    grip_open = _span(t, BOMB_LATCH_TIME, BOMB_LATCH_TIME + 0.5) - _span(t, 6.0, 6.5)
    return trolley_x, gripper_y, grip_open


def wing_arm_extension(t):
    """Return 0..1 extension of the two wing-pylon service arms ``t`` seconds into the hangar phase."""
    return _span(t, 4.5, 5.5) - _span(t, 6.6, 7.5)


def _two_link_elbow(bx, by, tx, ty, l1, l2, bend):
    """Elbow position of a two-link arm reaching from (bx, by) to (tx, ty); ``bend`` is -1 or +1."""
    dx, dy = tx - bx, ty - by
    raw = max(1e-6, math.hypot(dx, dy))
    dist = max(abs(l1 - l2) + 0.01, min(l1 + l2 - 0.01, raw))
    ux, uy = dx / raw, dy / raw
    a = (l1 * l1 - l2 * l2 + dist * dist) / (2.0 * dist)
    h = math.sqrt(max(0.0, l1 * l1 - a * a))
    return bx + ux * a - uy * h * bend, by + uy * a + ux * h * bend


def _get_audio():
    """Safely retrieves the AudioManager instance if initialized."""
    try:
        from eagle1.systems.audio_manager import AudioManager
        return AudioManager.get_instance()
    except Exception:
        return None


class SuperDestroyerManager:
    """Manages the Super Destroyer orbital maintenance cinematic sequence,
    robotic ordnance reloading, combat pause state, and Stratagem Hero minigame.
    """

    def __init__(self, screen_w=1280, screen_h=720):
        self.screen_w = screen_w
        self.screen_h = screen_h

        # Phase tracking
        self.phase = PHASE_NONE
        self.phase_timer = 0.0
        self.total_timer = 0.0

        # Departure coordinates & flight vector
        self.departure_x = 0.0
        self.departure_y = 0.0
        self.departure_angle = 0.0
        self.departure_vel_x = 0.0
        self.departure_vel_y = 0.0

        # Particle containers
        self.steam_particles = []
        self.spark_particles = []
        self.speed_lines = []
        self.afterburner_particles = []

        # Robotic crane milestones (the hoist pose itself is derived from phase_timer via crane_pose)
        self.bomb_attached = False
        self.bomb_latched = False
        self.wings_serviced = False
        self.last_sfx_time = 0.0

        # Stratagem Hero Minigame state
        self.hero_sequence = []
        self.hero_sequence_name = ""
        self.hero_index = 0
        self.hero_score = 0
        self.hero_highscore = self._load_hero_highscore()
        self.hero_feedback_text = ""
        self.hero_feedback_timer = 0.0
        self.hero_feedback_color = (255, 255, 255)
        self.hero_error_flash = 0.0

        # Visual caching
        self._init_starfield()
        self._init_speed_lines()
        self.hangar_bg_surface = None
        self.crt_scanline_surface = None
        self.floodlight_surface = None
        self.fade_surface = None
        self._init_cached_surfaces()

        # Cached fonts
        self.font_title = None
        self.font_large = None
        self.font_med = None
        self.font_small = None
        self.font_arrow = None
        self._init_fonts()

    # =========================================================================
    # PERSISTENCE & INITIALIZATION
    # =========================================================================

    def _load_hero_highscore(self):
        hs_file = os.path.join(str(get_user_data_dir()), "stratagem_hero_highscore.txt")
        try:
            with open(hs_file, "r", encoding="utf-8") as f:
                content = f.read().strip()
        except FileNotFoundError:
            return 0
        except (OSError, UnicodeDecodeError) as exc:
            logger.warning("Could not read Stratagem Hero highscore: %s", exc)
            return 0
        return int(content) if content.isdigit() else 0

    def _save_hero_highscore(self):
        data_dir = get_user_data_dir()
        hs_file = os.path.join(str(data_dir), "stratagem_hero_highscore.txt")
        tmp_file = hs_file + ".tmp"
        try:
            os.makedirs(str(data_dir), exist_ok=True)
            with open(tmp_file, "w", encoding="utf-8") as f:
                f.write(str(self.hero_highscore))
            os.replace(tmp_file, hs_file)  # atomic: a crash mid-write never truncates the highscore
        except OSError as exc:
            logger.warning("Could not save Stratagem Hero highscore: %s", exc)

    def _init_fonts(self):
        """Fetch the cached theme fonts and pre-render all static terminal text."""
        self.font_title = theme.get_font("title")
        self.font_large = theme.get_font("heading")
        self.font_med = theme.get_font("mono")
        self.font_small = theme.get_font("mono_small")
        self.font_arrow = theme.get_font("title")
        self._text_cache = widgets.TextCache(256)
        self._marquee_variants = []
        self._static_texts = {}
        if self.font_title:
            for i in range(8):
                color = theme.lerp_color(theme.WARNING, theme.ACCENT, i / 7.0)
                self._marquee_variants.append(self.font_title.render("// STRATAGEM HERO //", True, color))
        if self.font_small:
            self._static_texts["hint"] = self.font_small.render("USE ARROW KEYS TO DECODE", True, theme.TEXT_MUTED)
        if self.font_med:
            self._static_texts["status_left"] = self.font_med.render(
                "SES SUPER DESTROYER // REARM DECK 04", True, theme.ACCENT
            )
            self._static_texts["status_right"] = self.font_med.render(
                "BATTLEFIELD SIMULATION FROZEN // SQUAD IN STANDBY", True, theme.SUCCESS
            )

    def _init_starfield(self):
        """Generates static background starfield for orbital view."""
        self.stars = []
        random.seed(42)
        for _ in range(130):
            sx = random.randint(0, self.screen_w)
            sy = random.randint(0, 360)
            size = random.choice([1, 1, 2, 2, 3])
            brightness = random.randint(140, 255)
            tint = random.choice([(255, 255, 255), (180, 220, 255), (255, 230, 180)])
            col = (int(tint[0] * brightness / 255), int(tint[1] * brightness / 255), int(tint[2] * brightness / 255))
            self.stars.append((sx, sy, size, col))
        random.seed()

    def _init_speed_lines(self):
        """Initializes speed streak coordinates."""
        self.speed_lines = []
        for _ in range(35):
            self.speed_lines.append({
                "x": random.randint(0, self.screen_w),
                "y": random.randint(0, self.screen_h),
                "len": random.randint(40, 140),
                "speed": random.uniform(800.0, 1600.0),
                "alpha": random.randint(100, 220),
            })

    def _init_cached_surfaces(self):
        """Pre-renders static hangar background and transparent overlays."""
        bg = pygame.Surface((self.screen_w, self.screen_h), 0, 32, (0x00FF0000, 0x0000FF00, 0x000000FF, 0))
        bg.fill((8, 11, 18))

        # Planet Horizon curvature (drawn in upper orbital aperture)
        center_x = self.screen_w // 2 - 80
        center_y = 860
        planet_radius = 650

        # Atmospheric glow
        for r_offset, alpha, col in [
            (28, 25, (0, 140, 255)),
            (18, 45, (0, 200, 255)),
            (8, 90, (120, 230, 255)),
            (0, 255, (20, 45, 80)),
        ]:
            glow_surf = pygame.Surface((self.screen_w, 360), pygame.SRCALPHA)
            pygame.draw.circle(glow_surf, (*col, alpha), (center_x, center_y), planet_radius + r_offset)
            bg.blit(glow_surf, (0, 0))

        # Stars in upper viewport
        for sx, sy, size, col in self.stars:
            if math.hypot(sx - center_x, sy - center_y) > planet_radius:
                pygame.draw.circle(bg, col, (sx, sy), size)

        # Super Destroyer Outer Structural Framework (Framing the bay)
        pygame.draw.polygon(bg, (18, 22, 32), [(0, 0), (self.screen_w, 0), (self.screen_w, 80), (0, 80)])
        pygame.draw.polygon(bg, (22, 28, 40), [(0, 0), (160, 0), (90, 360), (0, 360)])
        pygame.draw.polygon(bg, (22, 28, 40), [(self.screen_w, 0), (self.screen_w - 160, 0), (self.screen_w - 90, 360), (self.screen_w, 360)])

        # Support Girders
        for gx in [260, 520, 780, 1040]:
            pygame.draw.line(bg, (32, 40, 55), (gx, 0), (gx, 110), 6)
            pygame.draw.line(bg, (45, 56, 75), (gx, 0), (gx, 110), 2)

        # Hangar Lower Floor Deck (y: 330 to 720)
        deck_rect = pygame.Rect(0, 330, self.screen_w, self.screen_h - 330)
        pygame.draw.rect(bg, (24, 30, 42), deck_rect)
        pygame.draw.line(bg, (60, 75, 100), (0, 330), (self.screen_w, 330), 4)

        # Industrial Deck Plates & Panel Lines
        for px in range(0, self.screen_w, 120):
            pygame.draw.line(bg, (16, 20, 30), (px, 330), (px, self.screen_h), 2)
        for py in range(330, self.screen_h, 70):
            pygame.draw.line(bg, (16, 20, 30), (0, py), (self.screen_w, py), 2)

        # Hazard Yellow/Black Stripes along maintenance apron
        stripe_w = 16
        apron_y = 334
        for sx in range(0, self.screen_w, stripe_w * 2):
            pygame.draw.polygon(bg, (230, 175, 20), [
                (sx, apron_y),
                (sx + stripe_w, apron_y),
                (sx + stripe_w - 8, apron_y + 12),
                (sx - 8, apron_y + 12),
            ])

        # Hydraulic Service Platform (Octagonal Pad for Eagle-1)
        pad_x, pad_y, pad_w, pad_h = PAD_X, PAD_Y, PAD_W, PAD_H
        cut = 22
        pad_pts = [
            (pad_x + cut, pad_y), (pad_x + pad_w - cut, pad_y), (pad_x + pad_w, pad_y + cut),
            (pad_x + pad_w, pad_y + pad_h - cut), (pad_x + pad_w - cut, pad_y + pad_h),
            (pad_x + cut, pad_y + pad_h), (pad_x, pad_y + pad_h - cut), (pad_x, pad_y + cut),
        ]
        pygame.draw.polygon(bg, (36, 44, 60), pad_pts)
        pygame.draw.polygon(bg, (230, 175, 20), pad_pts, 3)

        # Overhead gantry rail carrying the ordnance hoist
        pygame.draw.rect(bg, (30, 38, 52), (120, RAIL_Y - 4, 640, 16))
        pygame.draw.rect(bg, (78, 102, 132), (120, RAIL_Y - 4, 640, 16), 1)
        pygame.draw.line(bg, (110, 135, 165), (122, RAIL_Y), (758, RAIL_Y), 1)
        for rx in range(140, 760, 40):
            pygame.draw.line(bg, (46, 64, 88), (rx, RAIL_Y + 2), (rx, RAIL_Y + 9), 1)
        for rx in (120, 744):
            pygame.draw.rect(bg, (230, 175, 20), (rx, RAIL_Y - 6, 16, 20))

        # Platform grating texture
        for gx in range(pad_x + 15, pad_x + pad_w - 15, 24):
            pygame.draw.line(bg, (26, 32, 45), (gx, pad_y + 10), (gx, pad_y + pad_h - 10), 2)

        # Super Earth / Eagle Insignia stenciled on platform
        pygame.draw.circle(bg, (48, 60, 80), (pad_x + pad_w // 2, pad_y + pad_h // 2), 48, 2)
        pygame.draw.polygon(bg, (200, 160, 30), [
            (pad_x + pad_w // 2, pad_y + pad_h // 2 - 32),
            (pad_x + pad_w // 2 + 28, pad_y + pad_h // 2 + 20),
            (pad_x + pad_w // 2, pad_y + pad_h // 2 + 10),
            (pad_x + pad_w // 2 - 28, pad_y + pad_h // 2 + 20),
        ])

        # Platform Hydraulic Pillars
        for hx in [pad_x + 30, pad_x + pad_w - 30]:
            pygame.draw.rect(bg, (50, 60, 78), (hx - 12, pad_y + pad_h - 6, 24, 70))
            pygame.draw.rect(bg, (78, 102, 132), (hx - 12, pad_y + pad_h - 6, 24, 70), 1)
            pygame.draw.line(bg, (180, 195, 215), (hx - 6, pad_y + pad_h), (hx - 6, self.screen_h - 10), 4)

        self.hangar_bg_surface = bg

        # CRT Scanline Surface for Arcade Cabinet
        scan_w, scan_h = 440 - 32, 530 - 92  # exactly the CRT rect of the terminal
        scan_surf = pygame.Surface((scan_w, scan_h), pygame.SRCALPHA)
        for sy in range(0, scan_h, 4):
            pygame.draw.line(scan_surf, (0, 0, 0, 45), (0, sy), (scan_w, sy), 1)
        self.crt_scanline_surface = scan_surf

        # Pre-rendered steam puffs per integer radius (alpha applied per blit) and descent plasma discs
        self._puff_surfaces = {}
        for radius in range(1, 42):
            puff = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(puff, (220, 230, 240, 255), (radius, radius), radius)
            self._puff_surfaces[radius] = puff
        self._plasma_surfaces = []
        for radius, col in zip([36, 26, 16], [(255, 60, 20, 120), (255, 160, 30, 160), (255, 240, 120, 200)]):
            disc = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(disc, col, (radius, radius), radius)
            self._plasma_surfaces.append((radius, disc))
        self._eagle_scaled_cache = {}
        self._bomb_surface = self._build_bomb_surface()

        # Volumetric Floodlights Surface
        flood = pygame.Surface((self.screen_w, self.screen_h), pygame.SRCALPHA)
        for fx in [280, 540]:
            pygame.draw.polygon(flood, (255, 240, 180, 18), [
                (fx, 60),
                (fx + 30, 60),
                (fx + 110, 580),
                (fx - 80, 580),
            ])
            pygame.draw.circle(flood, (255, 255, 220, 160), (fx + 15, 60), 12)
        self.floodlight_surface = flood

        # Fade Overlay Surface
        self.fade_surface = pygame.Surface((self.screen_w, self.screen_h), pygame.SRCALPHA)

    @staticmethod
    def _build_bomb_surface():
        """Pre-render the hoisted 500 kg round (nose cone, banded body, tail fins) once."""
        surf = pygame.Surface((BOMB_W, BOMB_H), pygame.SRCALPHA)
        body, dark, light, band = (74, 88, 64), (44, 54, 40), (118, 134, 104), (230, 175, 20)
        pygame.draw.polygon(surf, body, [(9, 0), (14, 12), (4, 12)])
        pygame.draw.rect(surf, body, (4, 12, 10, 24))
        pygame.draw.polygon(surf, body, [(4, 36), (14, 36), (12, 43), (6, 43)])
        pygame.draw.polygon(surf, dark, [(4, 34), (0, 45), (4, 41)])
        pygame.draw.polygon(surf, dark, [(14, 34), (17, 45), (14, 41)])
        pygame.draw.line(surf, light, (6, 12), (6, 35), 1)
        pygame.draw.line(surf, dark, (13, 12), (13, 35), 1)
        pygame.draw.rect(surf, band, (4, 19, 10, 3))
        pygame.draw.rect(surf, band, (4, 28, 10, 2))
        pygame.draw.line(surf, dark, (4, 12), (14, 12), 1)
        return surf

    # =========================================================================
    # REARM CONTROL & STATE MACHINE
    # =========================================================================

    @property
    def is_active(self):
        """Returns True if the cinematic sequence is active."""
        return self.phase != PHASE_NONE

    @property
    def is_combat_paused(self):
        """Returns True if battlefield combat and wave simulation should freeze."""
        return self.phase == PHASE_HANGAR

    @property
    def is_controls_locked(self):
        """Returns True if player controls (throttle, steering, firing) are locked."""
        return self.phase in (PHASE_ASCENT, PHASE_HANGAR, PHASE_DESCENT)

    def start_rearm(self, player):
        """Initiates the 15.0s Super Destroyer rearm cinematic."""
        if self.phase != PHASE_NONE:
            return False

        # Anchor departure coordinates
        self.departure_x = player.pos_x
        self.departure_y = player.pos_y
        self.departure_angle = player.angle
        self.departure_vel_x = player.velocity_x
        self.departure_vel_y = player.velocity_y

        self.phase = PHASE_ASCENT
        self.phase_timer = 0.0
        self.total_timer = TOTAL_REARM_DURATION

        self.bomb_attached = False
        self.bomb_latched = False
        self.wings_serviced = False
        self.hero_score = 0
        self._generate_next_hero_code()

        am = _get_audio()
        if am:
            am.play_sfx("rocket_launch")

        return True

    def _generate_next_hero_code(self):
        """Selects a new random stratagem code sequence for Stratagem Hero."""
        name, seq = random.choice(HERO_STRATAGEM_SEQUENCES)
        self.hero_sequence_name = name
        self.hero_sequence = list(seq)
        self.hero_index = 0

    def handle_hero_input(self, direction, player=None):
        """Processes arrow key input into the Stratagem Hero arcade terminal."""
        if self.phase != PHASE_HANGAR:
            return

        am = _get_audio()

        if self.hero_sequence and self.hero_index < len(self.hero_sequence):
            expected = self.hero_sequence[self.hero_index]
            if direction == expected:
                self.hero_index += 1
                if am:
                    am.play_sfx("ui_click")

                # Sequence completed!
                if self.hero_index >= len(self.hero_sequence):
                    self.hero_score += 100
                    if player:
                        player.score += 100
                    if self.hero_score > self.hero_highscore:
                        self.hero_highscore = self.hero_score
                        self._save_hero_highscore()

                    self.hero_feedback_text = "+100 HERO BONUS!"
                    self.hero_feedback_color = (0, 255, 180)
                    self.hero_feedback_timer = 0.8

                    if am:
                        am.play_sfx("powerup_pickup")
                    self._generate_next_hero_code()
            else:
                self.hero_index = 0
                self.hero_error_flash = 0.35
                self.hero_feedback_text = "INPUT ERROR!"
                self.hero_feedback_color = (255, 60, 60)
                self.hero_feedback_timer = 0.8
                if am:
                    am.play_sfx("low_shield")
                self._generate_next_hero_code()

    # =========================================================================
    # UPDATE CYCLE
    # =========================================================================

    def update(self, dt, player, weapon_menu=None):
        """Updates animation timers, particle systems, crane movement, and phase transitions."""
        if self.phase == PHASE_NONE:
            return

        self.total_timer = max(0.0, self.total_timer - dt)
        self.phase_timer += dt

        am = _get_audio()

        if self.hero_feedback_timer > 0.0:
            self.hero_feedback_timer = max(0.0, self.hero_feedback_timer - dt)
        if self.hero_error_flash > 0.0:
            self.hero_error_flash = max(0.0, self.hero_error_flash - dt)

        # ---------------------------------------------------------------------
        # PHASE 1: ATMOSPHERIC ASCENT (0.0s - 1.2s)
        # ---------------------------------------------------------------------
        if self.phase == PHASE_ASCENT:
            player.angle = 0.0
            ascent_speed = 750.0 + (self.phase_timer / ASCENT_DURATION) * 900.0
            player.pos_y -= ascent_speed * dt
            player.y = int(player.pos_y)

            if random.random() < 0.8:
                self.afterburner_particles.append({
                    "x": player.pos_x + 16 + random.uniform(-4, 4),
                    "y": player.pos_y + 40,
                    "vx": random.uniform(-15, 15),
                    "vy": random.uniform(180, 360),
                    "size": random.uniform(5, 12),
                    "color": random.choice([(255, 240, 120), (255, 140, 30), (255, 80, 20)]),
                    "life": 0.25,
                    "max_life": 0.25,
                })

            for sl in self.speed_lines:
                sl["y"] += sl["speed"] * dt
                if sl["y"] > self.screen_h:
                    sl["y"] = -sl["len"]
                    sl["x"] = random.randint(0, self.screen_w)

            if self.phase_timer >= ASCENT_DURATION:
                self.phase = PHASE_HANGAR
                self.phase_timer = 0.0
                if am:
                    am.play_sfx("hangar_ambience")

        # ---------------------------------------------------------------------
        # PHASE 2: ORBITAL HANGAR DOCKING (1.2s - 13.8s)
        # ---------------------------------------------------------------------
        elif self.phase == PHASE_HANGAR:
            # Check rearm latching milestones
            if self.phase_timer >= BOMB_LATCH_TIME and not self.bomb_latched:
                self.bomb_latched = True
                self.bomb_attached = True
                if am:
                    am.play_sfx("rearm_crane")
                self._spawn_sparks(SHIP_CX, SHIP_CY, 18)
                self._spawn_steam(SHIP_CX - 20, SHIP_CY - 10, 8)

            if self.phase_timer >= WING_SERVICE_TIME and not self.wings_serviced:
                self.wings_serviced = True
                if am:
                    am.play_sfx("rearm_crane")
                for tip_x, tip_y in WING_ARM_TIPS:
                    self._spawn_sparks(tip_x, tip_y, 10)
                self._spawn_steam(SHIP_CX, SHIP_CY + 24, 6)

            if random.random() < 0.04:
                self._spawn_steam(random.choice([WING_ARM_BASES[0][0] + 20, WING_ARM_BASES[1][0] - 20]), PAD_Y + 100, 3)

            self._update_particles(dt)

            if self.phase_timer >= HANGAR_DURATION:
                self.phase = PHASE_DESCENT
                self.phase_timer = 0.0
                player.pos_x = self.departure_x
                player.pos_y = self.departure_y - 420.0
                player.angle = self.departure_angle
                if am:
                    am.play_sfx("airstrike_siren")
                    am.play_sfx("reentry_burn")

        # ---------------------------------------------------------------------
        # PHASE 3: ATMOSPHERIC DESCENT & RE-ENTRY (13.8s - 15.0s)
        # ---------------------------------------------------------------------
        elif self.phase == PHASE_DESCENT:
            progress = min(1.0, self.phase_timer / DESCENT_DURATION)
            drop_factor = 1.0 - math.pow(1.0 - progress, 2)
            player.pos_y = (self.departure_y - 420.0) + 420.0 * drop_factor
            player.pos_x = self.departure_x
            player.y = int(player.pos_y)
            player.x = int(player.pos_x)

            for sl in self.speed_lines:
                sl["y"] -= sl["speed"] * dt
                if sl["y"] < -sl["len"]:
                    sl["y"] = self.screen_h
                    sl["x"] = random.randint(0, self.screen_w)

            if self.phase_timer >= DESCENT_DURATION or self.total_timer <= 0.0:
                self.phase = PHASE_NONE
                self.phase_timer = 0.0
                self.total_timer = 0.0

                if weapon_menu:
                    from eagle1.systems.ground_support import AirStrikeType
                    for st in weapon_menu.charges:
                        weapon_menu.charges[st] = AirStrikeType.DATA[st].get("max_charges", 1)
                    for st in weapon_menu.cooldowns:
                        weapon_menu.cooldowns[st] = 0.0
                    weapon_menu.is_rearming = False
                    weapon_menu.rearm_timer = 0.0

                player.invincible = True
                player.invincible_timer = pygame.time.get_ticks() + 1000

                if am:
                    am.play_sfx("powerup_pickup")

        alive_afterburners = []
        for ab in self.afterburner_particles:
            ab["life"] -= dt
            ab["x"] += ab["vx"] * dt
            ab["y"] += ab["vy"] * dt
            ab["size"] = max(1.0, ab["size"] - dt * 10.0)
            if ab["life"] > 0:
                alive_afterburners.append(ab)
        self.afterburner_particles = alive_afterburners

    def _spawn_sparks(self, x, y, count=15):
        """Spawns bright welding/impact spark particles."""
        for _ in range(count):
            angle = random.uniform(0, math.pi * 2)
            spd = random.uniform(80, 240)
            self.spark_particles.append({
                "x": x,
                "y": y,
                "vx": math.cos(angle) * spd,
                "vy": math.sin(angle) * spd - 60.0,
                "life": random.uniform(0.2, 0.5),
                "max_life": 0.5,
                "color": random.choice([(255, 255, 220), (255, 210, 80), (255, 140, 20)]),
            })

    def _spawn_steam(self, x, y, count=8):
        """Spawns soft pneumatic steam vent particles."""
        for _ in range(count):
            self.steam_particles.append({
                "x": x + random.uniform(-10, 10),
                "y": y + random.uniform(-5, 5),
                "vx": random.uniform(-40, 40),
                "vy": random.uniform(-80, -20),
                "radius": random.uniform(4, 8),
                "max_radius": random.uniform(22, 38),
                "life": random.uniform(0.6, 1.2),
                "max_life": 1.2,
                "alpha": random.randint(120, 180),
            })

    def _update_particles(self, dt):
        """Updates spark and steam physics."""
        alive_sparks = []
        for spk in self.spark_particles:
            spk["life"] -= dt
            spk["x"] += spk["vx"] * dt
            spk["y"] += spk["vy"] * dt
            spk["vy"] += 450.0 * dt
            if spk["life"] > 0:
                alive_sparks.append(spk)
        self.spark_particles = alive_sparks

        alive_steam = []
        for stm in self.steam_particles:
            stm["life"] -= dt
            stm["x"] += stm["vx"] * dt
            stm["y"] += stm["vy"] * dt
            prog = 1.0 - (stm["life"] / stm["max_life"])
            stm["current_radius"] = stm["radius"] + (stm["max_radius"] - stm["radius"]) * prog
            stm["current_alpha"] = int(stm["alpha"] * (stm["life"] / stm["max_life"]))
            if stm["life"] > 0:
                alive_steam.append(stm)
        self.steam_particles = alive_steam

    # =========================================================================
    # RENDERING PIPELINE
    # =========================================================================

    def draw(self, canvas, screen_w, screen_h, player=None):
        """Draws the active cinematic phase to the canvas."""
        if self.phase == PHASE_NONE:
            return

        if self.phase == PHASE_ASCENT:
            self._draw_ascent(canvas, player)
        elif self.phase == PHASE_HANGAR:
            self._draw_hangar(canvas, player)
        elif self.phase == PHASE_DESCENT:
            self._draw_descent(canvas, player)

    def _draw_ascent(self, canvas, player):
        """Draws speed lines, afterburners, and atmospheric transition fade."""
        for sl in self.speed_lines:
            sy = int(sl["y"])
            sx = int(sl["x"])
            pygame.draw.line(canvas, (200, 230, 255), (sx, sy), (sx, sy + sl["len"]), 2)

        for ab in self.afterburner_particles:
            pygame.draw.circle(canvas, ab["color"], (int(ab["x"]), int(ab["y"])), int(ab["size"]))

        if self.phase_timer > ASCENT_DURATION * 0.7:
            fade_prog = (self.phase_timer - ASCENT_DURATION * 0.7) / (ASCENT_DURATION * 0.3)
            alpha = int(min(255, fade_prog * 255))
            self.fade_surface.fill((255, 255, 255, alpha))
            canvas.blit(self.fade_surface, (0, 0))

    def _draw_hangar(self, canvas, player):
        """Draws the Super Destroyer orbital maintenance bay & Stratagem Hero terminal."""
        canvas.blit(self.hangar_bg_surface, (0, 0))
        canvas.blit(self.floodlight_surface, (0, 0))

        beacon_pulse = int(128 + 127 * math.sin(pygame.time.get_ticks() * 0.01))
        for bx in [PAD_X + 34, PAD_X + PAD_W - 34]:
            pygame.draw.rect(canvas, (beacon_pulse, 40, 20), (bx - 5, PAD_Y + 29, 10, 10))
            pygame.draw.rect(canvas, (255, 180, 100), (bx - 2, PAD_Y + 32, 4, 4))

        self._draw_docked_eagle(canvas, SHIP_CX, SHIP_CY, player)
        self._draw_airframe_scan(canvas)
        self._draw_wing_arms(canvas)
        self._draw_rearm_robotics(canvas, SHIP_CX)

        for stm in self.steam_particles:
            radius = max(1, min(41, int(stm["current_radius"])))
            puff = self._puff_surfaces[radius]
            puff.set_alpha(max(0, min(255, stm["current_alpha"])))
            canvas.blit(puff, (int(stm["x"] - radius), int(stm["y"] - radius)))

        for spk in self.spark_particles:
            pygame.draw.circle(canvas, spk["color"], (int(spk["x"]), int(spk["y"])), 2)

        self._draw_rearm_checklist(canvas)
        self._draw_stratagem_hero_terminal(canvas)
        self._draw_status_bar(canvas)

        if self.phase_timer < 0.4:
            alpha = int(255 * (1.0 - (self.phase_timer / 0.4)))
            self.fade_surface.fill((255, 255, 255, alpha))
            canvas.blit(self.fade_surface, (0, 0))

    def _draw_docked_eagle(self, canvas, cx, cy, player):
        """Draws the docked Eagle-1 aircraft on the hydraulic lift."""
        if player and getattr(player, "original_image", None):
            scaled_img = self._eagle_scaled_cache.get(id(player.original_image))
            if scaled_img is None:
                scaled_img = pygame.transform.scale(player.original_image, (72, 72))
                self._eagle_scaled_cache[id(player.original_image)] = scaled_img
            img_rect = scaled_img.get_rect(center=(cx, cy))
            canvas.blit(scaled_img, img_rect.topleft)
        else:
            pygame.draw.polygon(canvas, (210, 220, 235), [
                (cx, cy - 35),
                (cx + 28, cy + 25),
                (cx + 8, cy + 18),
                (cx, cy + 28),
                (cx - 8, cy + 18),
                (cx - 28, cy + 25),
            ])
            pygame.draw.ellipse(canvas, (0, 220, 255), (cx - 5, cy - 18, 10, 22))

        if self.bomb_attached:
            canvas.blit(self._bomb_surface, (cx - BOMB_W // 2, cy - BOMB_H // 2))

    def _draw_rearm_robotics(self, canvas, ship_cx):
        """Draw the overhead gantry hoist: trolley, telescoping arm, gripper jaws and the suspended round."""
        trolley_x, grip_y, grip_open = crane_pose(self.phase_timer)
        tx = int(trolley_x)
        gy = int(grip_y)
        steel, steel_hi, steel_dark = (96, 112, 136), (150, 168, 192), (40, 48, 65)

        # Trolley carriage riding the rail
        body = pygame.Rect(tx - 46, TROLLEY_Y, 92, 26)
        pygame.draw.rect(canvas, steel_dark, body)
        pygame.draw.rect(canvas, theme.BORDER_STRONG, body, 1)
        pygame.draw.rect(canvas, (230, 175, 20), (body.x, body.y, body.w, 3))
        for wx in (tx - 36, tx + 28):
            pygame.draw.rect(canvas, steel, (wx, RAIL_Y + 8, 8, 8))
        window_on = (pygame.time.get_ticks() // 300) % 2 == 0
        pygame.draw.rect(canvas, (14, 20, 30), (tx - 20, TROLLEY_Y + 9, 40, 10))
        pygame.draw.rect(canvas, theme.INFO if window_on else (0, 90, 105), (tx - 16, TROLLEY_Y + 12, 6, 4))

        # Telescoping arm: three nested sections, widest at the carriage
        length = max(1, gy - ARM_ROOT_Y)
        sections = (
            (22, ARM_ROOT_Y + max(30, int(length * 0.45))),
            (16, ARM_ROOT_Y + max(40, int(length * 0.75))),
            (10, gy),
        )
        for width, bottom in sections:
            bottom = max(bottom, ARM_ROOT_Y + 8)
            rect = pygame.Rect(tx - width // 2, ARM_ROOT_Y, width, bottom - ARM_ROOT_Y)
            pygame.draw.rect(canvas, steel, rect)
            pygame.draw.line(canvas, steel_hi, (rect.left + 1, rect.top), (rect.left + 1, rect.bottom), 1)
            pygame.draw.line(canvas, steel_dark, (rect.right - 1, rect.top), (rect.right - 1, rect.bottom), 1)
            pygame.draw.rect(canvas, steel_dark, (rect.left - 2, rect.bottom - 4, rect.w + 4, 4))

        # Gripper plate with two clamp jaws that open to release the round
        plate = pygame.Rect(tx - 30, gy, 60, 10)
        pygame.draw.rect(canvas, (65, 78, 100), plate)
        pygame.draw.rect(canvas, theme.BORDER_STRONG, plate, 1)
        gap = 8 + int(12 * grip_open)
        for sign in (-1, 1):
            inner, outer = tx + sign * gap, tx + sign * (gap + 6)
            pygame.draw.polygon(canvas, steel_hi, [
                (inner, gy + 10), (outer, gy + 10), (outer, gy + 32), (inner + sign * -1, gy + 36),
            ])
        lamp = theme.SUCCESS if grip_open < 0.05 else theme.WARNING
        pygame.draw.rect(canvas, lamp, (tx - 3, gy + 3, 6, 4))

        if not self.bomb_attached:
            canvas.blit(self._bomb_surface, (tx - BOMB_W // 2, gy + 14))

    def _draw_wing_arms(self, canvas):
        """Draw the two articulated pylon service arms that reach the wing roots during servicing."""
        ext = wing_arm_extension(self.phase_timer)
        if ext <= 0.01:
            return
        steel, steel_hi, steel_dark = (96, 112, 136), (150, 168, 192), (40, 48, 65)
        l1, l2 = WING_ARM_LINKS
        flicker = (pygame.time.get_ticks() // 70) % 2 == 0
        for idx, ((bx, by), (gx, gy)) in enumerate(zip(WING_ARM_BASES, WING_ARM_TIPS)):
            side = 1 if idx == 0 else -1
            rest_x, rest_y = bx + side * 40, by - 20
            tip_x = rest_x + (gx - rest_x) * ext
            tip_y = rest_y + (gy - rest_y) * ext
            elbow_x, elbow_y = _two_link_elbow(bx, by, tip_x, tip_y, l1, l2, -1 if idx == 0 else 1)
            base, elbow, tip = (int(bx), int(by)), (int(elbow_x), int(elbow_y)), (int(tip_x), int(tip_y))
            pygame.draw.rect(canvas, steel_dark, (bx - 12, by - 9, 24, 18))
            pygame.draw.rect(canvas, theme.BORDER_STRONG, (bx - 12, by - 9, 24, 18), 1)
            pygame.draw.line(canvas, steel_dark, base, elbow, 11)
            pygame.draw.line(canvas, steel, base, elbow, 7)
            pygame.draw.line(canvas, steel_dark, elbow, tip, 9)
            pygame.draw.line(canvas, steel_hi, elbow, tip, 5)
            pygame.draw.rect(canvas, (230, 175, 20), (elbow[0] - 5, elbow[1] - 5, 10, 10))
            pygame.draw.rect(canvas, steel_dark, (elbow[0] - 5, elbow[1] - 5, 10, 10), 1)
            pygame.draw.rect(canvas, steel_dark, (tip[0] - 6, tip[1] - 6, 12, 12))
            pygame.draw.rect(canvas, theme.INFO, (tip[0] - 3, tip[1] - 3, 6, 6))
            if ext > 0.95 and flicker:
                pygame.draw.circle(canvas, (255, 240, 180), tip, 4)

    def _draw_airframe_scan(self, canvas):
        """Draw the cyan scan brackets and sweep line around the docked Eagle-1 (green once serviced)."""
        t = self.phase_timer
        done = t >= REARM_STEPS[-1][2]
        color = theme.SUCCESS if done else theme.INFO
        box = pygame.Rect(SHIP_CX - 46, SHIP_CY - 46, 92, 92)
        widgets.draw_brackets(canvas, box, color, length=12, thickness=1)
        if not done:
            sweep_y = box.top + int(((t * 0.7) % 1.0) * box.h)
            pygame.draw.line(canvas, color, (box.left + 4, sweep_y), (box.right - 4, sweep_y), 1)
        if self.font_small:
            label = "AIRFRAME SYSTEMS NOMINAL" if done else "AIRFRAME SCAN // RUNNING"
            surf = self._text_cache.render(self.font_small, label, color)
            canvas.blit(surf, (SHIP_CX - surf.get_width() // 2, box.bottom + 8))

    def _draw_rearm_checklist(self, canvas):
        """Draw the rearm sequence checklist between the service pad and the arcade terminal."""
        if not (self.font_small and self.font_med):
            return
        panel = pygame.Rect(PAD_X + PAD_W + 18, PAD_Y + 10, 168, 30 + 26 * len(REARM_STEPS))
        widgets.draw_panel(canvas, panel, theme.PANEL, theme.BORDER, theme.ACCENT)
        cache = self._text_cache
        head = cache.render(self.font_small, "REARM SEQUENCE", theme.ACCENT)
        canvas.blit(head, (panel.x + 12, panel.y + 8))
        for row, (label, start, done) in enumerate(REARM_STEPS):
            if self.phase_timer >= done:
                status, color = "OK", theme.SUCCESS
            elif self.phase_timer >= start:
                status, color = "RUN", theme.INFO
            else:
                status, color = "WAIT", theme.TEXT_DISABLED
            y = panel.y + 34 + row * 26
            name = cache.render(self.font_small, label, theme.TEXT if status != "WAIT" else theme.TEXT_DISABLED)
            state = cache.render(self.font_small, status, color)
            canvas.blit(name, (panel.x + 12, y))
            canvas.blit(state, (panel.right - 12 - state.get_width(), y))
            pygame.draw.line(canvas, theme.BORDER, (panel.x + 12, y + 20), (panel.right - 12, y + 20), 1)

    def _draw_stratagem_hero_terminal(self, canvas):
        """Draws the arcade cabinet running Stratagem Hero."""
        tx, ty, tw, th = 780, 100, 440, 530
        cache = self._text_cache

        cabinet = pygame.Rect(tx, ty, tw, th)
        widgets.draw_panel(canvas, cabinet, theme.PANEL, theme.ACCENT, theme.ACCENT)

        mq_rect = pygame.Rect(tx + 12, ty + 12, tw - 24, 52)
        widgets.draw_panel(canvas, mq_rect, theme.PANEL_RAISED, theme.ACCENT_DIM, brackets=False)

        if self._marquee_variants:
            variant = self._marquee_variants[(pygame.time.get_ticks() // 90) % len(self._marquee_variants)]
            canvas.blit(variant, (mq_rect.centerx - variant.get_width() // 2, mq_rect.centery - variant.get_height() // 2))

        crt_rect = pygame.Rect(tx + 16, ty + 76, tw - 32, th - 92)
        error = self.hero_error_flash > 0.0
        widgets.draw_panel(
            canvas, crt_rect, (60, 12, 16) if error else (8, 30, 24),
            theme.DANGER if error else (0, 180, 140), brackets=False,
        )

        # Rearm Progress & Timer Bar
        rearm_rem = max(0.0, self.total_timer)
        if self.font_large:
            time_txt = cache.render(self.font_large, f"SUPER DESTROYER REARM: {rearm_rem:04.1f}s", theme.ACCENT)
            canvas.blit(time_txt, (crt_rect.centerx - time_txt.get_width() // 2, crt_rect.top + 12))

        bar_rect = pygame.Rect(crt_rect.left + 20, crt_rect.top + 48, crt_rect.width - 40, 16)
        progress = max(0.0, min(1.0, 1.0 - (self.total_timer / TOTAL_REARM_DURATION)))
        widgets.draw_bar(
            canvas, bar_rect, progress, (0, 230, 160) if progress < 0.9 else theme.ACCENT,
            bg=(18, 40, 36), border=(0, 255, 200),
        )

        # Stratagem Name Banner
        if self.font_large:
            sname_txt = cache.render(self.font_large, self.hero_sequence_name, theme.TEXT)
            canvas.blit(sname_txt, (crt_rect.centerx - sname_txt.get_width() // 2, crt_rect.top + 80))

        # Directional Key Sequence Boxes
        seq_len = len(self.hero_sequence)
        box_sz = 44
        gap = 10
        start_ax = crt_rect.centerx - (seq_len * box_sz + (seq_len - 1) * gap) // 2
        seq_y = crt_rect.top + 130

        for s_idx, direction in enumerate(self.hero_sequence):
            k_rect = pygame.Rect(start_ax + s_idx * (box_sz + gap), seq_y, box_sz, box_sz)

            if s_idx < self.hero_index:
                widgets.draw_panel(canvas, k_rect, (0, 160, 90), (0, 255, 160), brackets=False)
                arrow_col = theme.TEXT
            elif s_idx == self.hero_index:
                pulse = int(180 + 75 * math.sin(pygame.time.get_ticks() * 0.016))
                widgets.draw_panel(canvas, k_rect, (210, 140, 20), (255, pulse, 60), brackets=False)
                pygame.draw.rect(canvas, (255, pulse, 60), k_rect, 3)
                arrow_col = (255, 255, 200)
            else:
                widgets.draw_panel(canvas, k_rect, (20, 36, 42), (40, 70, 80), brackets=False)
                arrow_col = (100, 140, 150)

            if self.font_arrow:
                sym_txt = cache.render(self.font_arrow, ARROW_SYMBOLS.get(direction, "?"), arrow_col)
                canvas.blit(sym_txt, sym_txt.get_rect(center=k_rect.center))

        # Combo Score & All-Time High Score
        stats_y = crt_rect.top + 210
        if self.font_large:
            score_txt = cache.render(self.font_large, f"COMBO SCORE: {self.hero_score:04d} PTS", (0, 240, 220))
            canvas.blit(score_txt, (crt_rect.centerx - score_txt.get_width() // 2, stats_y))

        if self.font_med:
            best_txt = cache.render(self.font_med, f"PERSONAL BEST: {self.hero_highscore:04d} PTS", theme.ACCENT)
            canvas.blit(best_txt, (crt_rect.centerx - best_txt.get_width() // 2, stats_y + 34))

        if self.hero_feedback_timer > 0.0 and self.font_large:
            fb_txt = cache.render(self.font_large, self.hero_feedback_text, self.hero_feedback_color)
            canvas.blit(fb_txt, (crt_rect.centerx - fb_txt.get_width() // 2, stats_y + 78))

        hint_txt = self._static_texts.get("hint")
        if hint_txt is not None:
            canvas.blit(hint_txt, (crt_rect.centerx - hint_txt.get_width() // 2, crt_rect.bottom - 28))

        if self.crt_scanline_surface:
            canvas.blit(self.crt_scanline_surface, (crt_rect.left, crt_rect.top))

    def _draw_status_bar(self, canvas):
        """Draws the bottom tactical operational status banner."""
        bar_y = self.screen_h - 40
        pygame.draw.rect(canvas, theme.PANEL, (0, bar_y, self.screen_w, 40))
        pygame.draw.line(canvas, theme.ACCENT, (0, bar_y), (self.screen_w, bar_y), 2)

        left = self._static_texts.get("status_left")
        right = self._static_texts.get("status_right")
        if left is not None:
            canvas.blit(left, (30, bar_y + 20 - left.get_height() // 2))
        if right is not None:
            canvas.blit(right, (self.screen_w - right.get_width() - 30, bar_y + 20 - right.get_height() // 2))

    def _draw_descent(self, canvas, player):
        """Draws atmospheric re-entry fiery plasma trails and sonic boom shockwaves."""
        for sl in self.speed_lines:
            sy = int(sl["y"])
            sx = int(sl["x"])
            pygame.draw.line(canvas, (255, 180, 80), (sx, sy), (sx, sy + sl["len"]), 3)

        if player:
            cam_x = max(0, min(MAP_WIDTH - self.screen_w, self.departure_x + 24 - self.screen_w / 2))
            cam_y = max(0, min(MAP_HEIGHT - self.screen_h, self.departure_y + 30 - self.screen_h / 2))
            px = player.x - cam_x
            py = player.y - cam_y
            for radius, p_surf in self._plasma_surfaces:
                canvas.blit(p_surf, (px - radius + 16, py - radius + 16))

        if self.phase_timer < 0.3:
            alpha = int(200 * (1.0 - (self.phase_timer / 0.3)))
            self.fade_surface.fill((255, 120, 20, alpha))
            canvas.blit(self.fade_surface, (0, 0))
