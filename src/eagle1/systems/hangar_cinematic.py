"""
hangar_cinematic.py - Super Destroyer Orbital Rearm Cinematic & Stratagem Hero Subsystem.

Encapsulates the 15.0s atmospheric ascent, orbital hangar docking aboard the
Super Destroyer SES, animated robotic ordnance reloading (500kg bomb / rockets),
atmospheric descent re-entry, and the integrated Stratagem Hero arcade terminal minigame.
"""

import math
import os
import random
import pygame

from eagle1.paths import DATA_DIR


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

ARROW_SYMBOLS = {
    "UP": "▲",
    "DOWN": "▼",
    "LEFT": "◄",
    "RIGHT": "►",
}


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

        # Robotic crane animation state
        self.crane_gantry_x = 380.0
        self.crane_arm_y = 120.0
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
        hs_file = os.path.join(DATA_DIR, "stratagem_hero_highscore.txt")
        try:
            if os.path.exists(hs_file):
                with open(hs_file, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    if content.isdigit():
                        return int(content)
        except Exception:
            pass
        return 0

    def _save_hero_highscore(self):
        hs_file = os.path.join(DATA_DIR, "stratagem_hero_highscore.txt")
        try:
            os.makedirs(DATA_DIR, exist_ok=True)
            with open(hs_file, "w", encoding="utf-8") as f:
                f.write(str(self.hero_highscore))
        except Exception:
            pass

    def _init_fonts(self):
        """Initializes and caches UI fonts."""
        if not pygame.font.get_init():
            try:
                pygame.font.init()
            except Exception:
                return

        try:
            self.font_title = pygame.font.SysFont("impact,arial", 28) or pygame.font.Font(None, 34)
            self.font_large = pygame.font.SysFont("consolas,menlo,monaco,courier,arial", 22, bold=True) or pygame.font.Font(None, 28)
            self.font_med = pygame.font.SysFont("consolas,menlo,monaco,courier,arial", 16, bold=True) or pygame.font.Font(None, 20)
            self.font_small = pygame.font.SysFont("consolas,menlo,monaco,courier,arial", 13) or pygame.font.Font(None, 16)
            self.font_arrow = pygame.font.SysFont("segoeuisymbol,applesymbols,arial,symbol", 24, bold=True) or pygame.font.Font(None, 30)
        except Exception:
            self.font_title = pygame.font.Font(None, 32)
            self.font_large = pygame.font.Font(None, 26)
            self.font_med = pygame.font.Font(None, 20)
            self.font_small = pygame.font.Font(None, 16)
            self.font_arrow = pygame.font.Font(None, 28)

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
        bg = pygame.Surface((self.screen_w, self.screen_h))
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
        pad_x, pad_y, pad_w, pad_h = 240, 430, 340, 210
        pad_rect = pygame.Rect(pad_x, pad_y, pad_w, pad_h)
        pygame.draw.rect(bg, (36, 44, 60), pad_rect, border_radius=16)
        pygame.draw.rect(bg, (230, 175, 20), pad_rect, 3, border_radius=16)

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
            pygame.draw.rect(bg, (50, 60, 78), (hx - 12, pad_y + pad_h - 6, 24, 70), border_radius=4)
            pygame.draw.line(bg, (180, 195, 215), (hx - 6, pad_y + pad_h), (hx - 6, self.screen_h - 10), 4)

        self.hangar_bg_surface = bg

        # CRT Scanline Surface for Arcade Cabinet
        scan_surf = pygame.Surface((440, 530), pygame.SRCALPHA)
        for sy in range(0, 530, 4):
            pygame.draw.line(scan_surf, (0, 0, 0, 45), (0, sy), (440, sy), 1)
        self.crt_scanline_surface = scan_surf

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
        self.crane_arm_y = 120.0
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
            if self.phase_timer >= 3.5 and not self.bomb_latched:
                self.bomb_latched = True
                self.bomb_attached = True
                if am:
                    am.play_sfx("rearm_crane")
                self._spawn_sparks(410, 490, 28)
                self._spawn_steam(390, 480, 16)

            if self.phase_timer >= 7.5 and not self.wings_serviced:
                self.wings_serviced = True
                if am:
                    am.play_sfx("rearm_crane")
                self._spawn_sparks(355, 475, 20)
                self._spawn_sparks(465, 475, 20)
                self._spawn_steam(410, 500, 12)

            # Crane arm positioning
            if self.phase_timer < 3.5:
                progress = self.phase_timer / 3.5
                self.crane_arm_y = 120.0 + progress * 240.0
            elif self.phase_timer < 4.5:
                self.crane_arm_y = 360.0
            elif self.phase_timer < 7.5:
                progress = (self.phase_timer - 4.5) / 3.0
                self.crane_arm_y = 360.0 - progress * 220.0
            else:
                self.crane_arm_y = 140.0

            if random.random() < 0.06:
                self._spawn_steam(random.choice([360, 460]), 505, 4)

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

        pad_x, pad_y, pad_w = 240, 430, 340
        beacon_pulse = int(128 + 127 * math.sin(pygame.time.get_ticks() * 0.01))
        for bx in [pad_x + 12, pad_x + pad_w - 12]:
            pygame.draw.circle(canvas, (beacon_pulse, 40, 20), (bx, pad_y + 12), 6)
            pygame.draw.circle(canvas, (255, 180, 100), (bx, pad_y + 12), 2)

        ship_cx = pad_x + pad_w // 2
        ship_cy = pad_y + 105
        self._draw_docked_eagle(canvas, ship_cx, ship_cy, player)

        self._draw_rearm_robotics(canvas, ship_cx)

        for stm in self.steam_particles:
            steam_surf = pygame.Surface((int(stm["current_radius"] * 2), int(stm["current_radius"] * 2)), pygame.SRCALPHA)
            pygame.draw.circle(steam_surf, (220, 230, 240, max(0, min(255, stm["current_alpha"]))),
                               (int(stm["current_radius"]), int(stm["current_radius"])), int(stm["current_radius"]))
            canvas.blit(steam_surf, (int(stm["x"] - stm["current_radius"]), int(stm["y"] - stm["current_radius"])))

        for spk in self.spark_particles:
            pygame.draw.circle(canvas, spk["color"], (int(spk["x"]), int(spk["y"])), 2)

        self._draw_stratagem_hero_terminal(canvas)
        self._draw_status_bar(canvas)

        if self.phase_timer < 0.4:
            alpha = int(255 * (1.0 - (self.phase_timer / 0.4)))
            self.fade_surface.fill((255, 255, 255, alpha))
            canvas.blit(self.fade_surface, (0, 0))

    def _draw_docked_eagle(self, canvas, cx, cy, player):
        """Draws the docked Eagle-1 aircraft on the hydraulic lift."""
        if player and getattr(player, "original_image", None):
            scaled_img = pygame.transform.scale(player.original_image, (72, 72))
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
            pygame.draw.ellipse(canvas, (70, 85, 60), (cx - 6, cy - 8, 12, 28))
            pygame.draw.line(canvas, (255, 210, 20), (cx - 6, cy + 4), (cx + 6, cy + 4), 2)

    def _draw_rearm_robotics(self, canvas, ship_cx):
        """Draws the overhead robotic gantry crane, hydraulic pistons, and bomb hoist."""
        trolley_x = ship_cx
        trolley_y = 60
        pygame.draw.rect(canvas, (230, 175, 20), (trolley_x - 45, trolley_y, 90, 20), border_radius=4)
        pygame.draw.rect(canvas, (40, 48, 65), (trolley_x - 35, trolley_y + 4, 70, 12), border_radius=2)

        piston_bottom_y = int(self.crane_arm_y)
        pygame.draw.line(canvas, (180, 195, 215), (trolley_x - 12, trolley_y + 20), (trolley_x - 12, piston_bottom_y), 8)
        pygame.draw.line(canvas, (180, 195, 215), (trolley_x + 12, trolley_y + 20), (trolley_x + 12, piston_bottom_y), 8)

        pygame.draw.rect(canvas, (65, 78, 100), (trolley_x - 28, piston_bottom_y, 56, 18), border_radius=4)

        if not self.bomb_attached and piston_bottom_y < 360:
            bomb_y = piston_bottom_y + 18
            pygame.draw.ellipse(canvas, (75, 90, 65), (trolley_x - 8, bomb_y, 16, 36))
            pygame.draw.polygon(canvas, (55, 68, 48), [
                (trolley_x - 12, bomb_y + 26),
                (trolley_x + 12, bomb_y + 26),
                (trolley_x, bomb_y + 36),
            ])
            pygame.draw.line(canvas, (255, 210, 20), (trolley_x - 8, bomb_y + 10), (trolley_x + 8, bomb_y + 10), 3)

        pygame.draw.line(canvas, (230, 175, 20), (trolley_x - 22, piston_bottom_y + 10), (trolley_x - 12, piston_bottom_y + 30), 4)
        pygame.draw.line(canvas, (230, 175, 20), (trolley_x + 22, piston_bottom_y + 10), (trolley_x + 12, piston_bottom_y + 30), 4)

    def _draw_stratagem_hero_terminal(self, canvas):
        """Draws the arcade cabinet running Stratagem Hero."""
        tx, ty, tw, th = 780, 100, 440, 530

        pygame.draw.rect(canvas, (16, 20, 30), (tx, ty, tw, th), border_radius=12)
        pygame.draw.rect(canvas, (230, 175, 20), (tx, ty, tw, th), 3, border_radius=12)

        mq_rect = pygame.Rect(tx + 12, ty + 12, tw - 24, 52)
        pygame.draw.rect(canvas, (22, 28, 44), mq_rect, border_radius=8)
        pygame.draw.rect(canvas, (255, 210, 40), mq_rect, 2, border_radius=8)

        pulse_col = int(210 + 45 * math.sin(pygame.time.get_ticks() * 0.008))
        if self.font_title:
            mq_txt = self.font_title.render("★ STRATAGEM HERO ★", True, (255, pulse_col, 50))
            canvas.blit(mq_txt, (mq_rect.centerx - mq_txt.get_width() // 2, mq_rect.centery - mq_txt.get_height() // 2))

        crt_rect = pygame.Rect(tx + 16, ty + 76, tw - 32, th - 92)
        screen_bg = (8, 30, 24) if self.hero_error_flash <= 0.0 else (60, 12, 16)
        pygame.draw.rect(canvas, screen_bg, crt_rect, border_radius=8)
        pygame.draw.rect(canvas, (0, 180, 140) if self.hero_error_flash <= 0.0 else (220, 60, 60), crt_rect, 2, border_radius=8)

        # Rearm Progress & Timer Bar
        rearm_rem = max(0.0, self.total_timer)
        time_txt_str = f"SUPER DESTROYER REARM: {rearm_rem:04.1f}s"
        if self.font_large:
            time_txt = self.font_large.render(time_txt_str, True, (255, 220, 70))
            canvas.blit(time_txt, (crt_rect.centerx - time_txt.get_width() // 2, crt_rect.top + 16))

        bar_w = crt_rect.width - 40
        bar_h = 16
        bx = crt_rect.left + 20
        by = crt_rect.top + 48
        pygame.draw.rect(canvas, (18, 40, 36), (bx, by, bar_w, bar_h), border_radius=4)
        progress = max(0.0, min(1.0, 1.0 - (self.total_timer / TOTAL_REARM_DURATION)))
        fill_w = int(bar_w * progress)
        if fill_w > 0:
            fill_col = (0, 230, 160) if progress < 0.9 else (255, 200, 50)
            pygame.draw.rect(canvas, fill_col, (bx, by, fill_w, bar_h), border_radius=4)
        pygame.draw.rect(canvas, (0, 255, 200), (bx, by, bar_w, bar_h), 1, border_radius=4)

        # Stratagem Name Banner
        strat_y = crt_rect.top + 84
        if self.font_large:
            sname_txt = self.font_large.render(self.hero_sequence_name, True, (255, 255, 255))
            canvas.blit(sname_txt, (crt_rect.centerx - sname_txt.get_width() // 2, strat_y))

        # Directional Key Sequence Boxes
        seq_len = len(self.hero_sequence)
        box_sz = 44
        gap = 10
        start_ax = crt_rect.centerx - (seq_len * box_sz + (seq_len - 1) * gap) // 2
        seq_y = crt_rect.top + 130

        for s_idx, direction in enumerate(self.hero_sequence):
            k_rect = pygame.Rect(start_ax + s_idx * (box_sz + gap), seq_y, box_sz, box_sz)

            if s_idx < self.hero_index:
                pygame.draw.rect(canvas, (0, 160, 90), k_rect, border_radius=6)
                pygame.draw.rect(canvas, (0, 255, 160), k_rect, 2, border_radius=6)
                arrow_col = (255, 255, 255)
            elif s_idx == self.hero_index:
                pulse = int(180 + 75 * math.sin(pygame.time.get_ticks() * 0.016))
                pygame.draw.rect(canvas, (210, 140, 20), k_rect, border_radius=6)
                pygame.draw.rect(canvas, (255, pulse, 60), k_rect, 3, border_radius=6)
                arrow_col = (255, 255, 200)
            else:
                pygame.draw.rect(canvas, (20, 36, 42), k_rect, border_radius=6)
                pygame.draw.rect(canvas, (40, 70, 80), k_rect, 1, border_radius=6)
                arrow_col = (100, 140, 150)

            sym = ARROW_SYMBOLS.get(direction, "?")
            if self.font_arrow:
                sym_txt = self.font_arrow.render(sym, True, arrow_col)
                canvas.blit(sym_txt, (k_rect.centerx - sym_txt.get_width() // 2, k_rect.centery - sym_txt.get_height() // 2))

        # Combo Score & All-Time High Score
        stats_y = crt_rect.top + 210
        if self.font_large:
            score_txt = self.font_large.render(f"COMBO SCORE: {self.hero_score:04d} PTS", True, (0, 240, 220))
            canvas.blit(score_txt, (crt_rect.centerx - score_txt.get_width() // 2, stats_y))

        if self.font_med:
            best_txt = self.font_med.render(f"PERSONAL BEST: {self.hero_highscore:04d} PTS", True, (255, 210, 80))
            canvas.blit(best_txt, (crt_rect.centerx - best_txt.get_width() // 2, stats_y + 34))

        if self.hero_feedback_timer > 0.0 and self.font_large:
            fb_txt = self.font_large.render(self.hero_feedback_text, True, self.hero_feedback_color)
            canvas.blit(fb_txt, (crt_rect.centerx - fb_txt.get_width() // 2, stats_y + 78))

        if self.font_small:
            hint_txt = self.font_small.render("USE ARROW KEYS [ ▲  ▼  ◄  ► ] TO DECODE", True, (120, 180, 170))
            canvas.blit(hint_txt, (crt_rect.centerx - hint_txt.get_width() // 2, crt_rect.bottom - 28))

        if self.crt_scanline_surface:
            canvas.blit(self.crt_scanline_surface, (crt_rect.left, crt_rect.top))

    def _draw_status_bar(self, canvas):
        """Draws the bottom tactical operational status banner."""
        bar_y = self.screen_h - 40
        pygame.draw.rect(canvas, (14, 18, 26), (0, bar_y, self.screen_w, 40))
        pygame.draw.line(canvas, (230, 175, 20), (0, bar_y), (self.screen_w, bar_y), 2)

        if self.font_med:
            status_left = self.font_med.render("SES SUPER DESTROYER // REARM DECK 04", True, (255, 210, 60))
            canvas.blit(status_left, (30, bar_y + 10))

            status_right = self.font_med.render("BATTLEFIELD SIMULATION FROZEN // SQUAD IN STANDBY", True, (0, 220, 180))
            canvas.blit(status_right, (self.screen_w - status_right.get_width() - 30, bar_y + 10))

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
            plasma_colors = [(255, 60, 20, 120), (255, 160, 30, 160), (255, 240, 120, 200)]
            for radius, col in zip([36, 26, 16], plasma_colors):
                p_surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
                pygame.draw.circle(p_surf, col, (radius, radius), radius)
                canvas.blit(p_surf, (px - radius + 16, py - radius + 16))

        if self.phase_timer < 0.3:
            alpha = int(200 * (1.0 - (self.phase_timer / 0.3)))
            self.fade_surface.fill((255, 120, 20, alpha))
            canvas.blit(self.fade_surface, (0, 0))
