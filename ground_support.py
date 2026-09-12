"""
ground_support.py - Allied Helldivers, Hostile Enemy Ground Forces, Air Strike Arsenal,
and Predictive Weapon Aiming Reticle for Eagle-1-64Bit.

Features:
1. Allied Helldiver Squad: 4-member squad with tactical AI, obstacle avoidance,
   overhead health/shield bars, and anti-air / ground combat tracer fire.
2. Hostile Enemy Ground Forces:
   - Automaton Troopers (light cyber-infantry firing red laser blasters).
   - Heavy Armored Walkers (bipedal hulks firing twin kinetic cannons).
   - Destructible Enemy Fabricator Outposts spawning hostile ground reinforcements.
3. Air Strike Weapon Arsenal (8 Stratagems):
   - Machine Gun Dive, Eagle 500kg Bomb, Cluster Bomb, Napalm Strike,
     Gas Strike, Rocket Pods, EMS Stun Strike, Smoke Screen.
4. Helldiver Tactical CAS Call-in Missions:
   - Helldivers throw red beacons calling for Close Air Support (compatible with ALL air strikes).
   - High-priority HUD waypoint guides Eagle-1 to fly in and deploy the payload on target.
5. Dual Aiming Reticle (Guns + Predictive Bomb / Strike Impact):
   - Gun aim pip showing cannon bullet trajectory.
   - Predictive bomb impact reticle dynamically showing exact ground-zero blast footprint
     customized for each weapon type, with target lock-on brackets.
6. Tactical Supply Drops & Pelican-1 Extraction.
"""

import math
import random
import pygame

# =====================================================================
# CONFIGURATION CONSTANTS
# =====================================================================

MAP_WIDTH = 3000
MAP_HEIGHT = 3000

# Helldiver Squad Tuning
HELLDIVER_COUNT = 4
HELLDIVER_MAX_HEALTH = 100.0
HELLDIVER_SPEED = 1.6
HELLDIVER_ENGAGE_RADIUS = 420.0
HELLDIVER_BULLET_DAMAGE = 0.8
HELLDIVER_BULLET_SPEED = 14.0
HELLDIVER_FIRE_COOLDOWN_MS = 320
HELLDIVER_SEPARATION_RADIUS = 36.0

# Enemy Ground Units Tuning
ENEMY_TROOPER_MAX_HEALTH = 35.0
ENEMY_TROOPER_SPEED = 1.1
ENEMY_WALKER_MAX_HEALTH = 120.0
ENEMY_WALKER_SPEED = 0.7
ENEMY_FABRICATOR_MAX_HEALTH = 220.0
ENEMY_GROUND_ENGAGE_RADIUS = 380.0
ENEMY_LASER_DAMAGE = 8.0
ENEMY_LASER_SPEED = 11.0

# Stratagem Cooldowns (seconds)
COOLDOWN_STRAFING_RUN = 12.0
COOLDOWN_500KG_BOMB = 35.0
COOLDOWN_CLUSTER_BOMB = 18.0
COOLDOWN_NAPALM_STRIKE = 22.0
COOLDOWN_GAS_STRIKE = 18.0
COOLDOWN_ROCKET_PODS = 20.0
COOLDOWN_EMS_STUN = 24.0
COOLDOWN_SMOKE_SCREEN = 22.0
COOLDOWN_SUPPLY_DROP = 30.0

# Scoring Constants
SCORE_CAS_KILL_BONUS = 100
SCORE_SURVIVOR_WAVE_BONUS = 500
SCORE_FLAWLESS_MULTIPLIER = 1.5
SCORE_EXTRACTION_BONUS = 2500
SCORE_CASUALTY_PENALTY = 250
SCORE_MISSION_DELIVERY_BONUS = 500

# Danger Zone Alert Proximity
DANGER_ALERT_RADIUS = 680.0


# =====================================================================
# AIR STRIKE STRATAGEM DEFINITIONS
# =====================================================================

class AirStrikeType:
    STRAFE = "strafe"
    BOMB_500KG = "bomb_500kg"
    CLUSTER = "cluster"
    NAPALM = "napalm"
    GAS = "gas"
    ROCKETS = "rockets"
    EMS = "ems"
    SMOKE = "smoke"

    DATA = {
        STRAFE: {
            "id": STRAFE,
            "key": "1",
            "name": "Machine Gun Dive",
            "subtitle": "Eagle Strafing Run",
            "cooldown": COOLDOWN_STRAFING_RUN,
            "color": (255, 200, 50),
            "border_color": (255, 220, 80),
            "symbol": "MG",
            "desc": "Eagle-1 sweeps in low, unloading a dense line of 20mm rotary cannon fire along the attack path.",
            "stats": {"Damage": "High DPS", "Radius": "Straight Line", "Type": "Kinetic Penetration"},
        },
        BOMB_500KG: {
            "id": BOMB_500KG,
            "key": "2",
            "name": "Eagle 500kg Bomb",
            "subtitle": "High Explosive Munition",
            "cooldown": COOLDOWN_500KG_BOMB,
            "color": (255, 60, 40),
            "border_color": (255, 100, 70),
            "symbol": "500",
            "desc": "The ultimate explosive ordnance. Massive ground zero blast annihilating anything in its radius.",
            "stats": {"Damage": "Massive (16.0)", "Radius": "320px Blast", "Type": "Heavy Ordnance"},
        },
        CLUSTER: {
            "id": CLUSTER,
            "key": "3",
            "name": "Cluster Bomb",
            "subtitle": "Area Saturation Munitions",
            "cooldown": COOLDOWN_CLUSTER_BOMB,
            "color": (255, 140, 20),
            "border_color": (255, 175, 60),
            "symbol": "CB",
            "desc": "Blankets a broad zone with dozens of explosive sub-munitions, tearing apart swarms of hostiles.",
            "stats": {"Damage": "Medium (3.8x8)", "Radius": "280px Spread", "Type": "Saturation"},
        },
        NAPALM: {
            "id": NAPALM,
            "key": "4",
            "name": "Napalm Strike",
            "subtitle": "Incendiary Wall of Fire",
            "cooldown": COOLDOWN_NAPALM_STRIKE,
            "color": (255, 80, 20),
            "border_color": (255, 120, 40),
            "symbol": "NP",
            "desc": "Drops incendiary canisters creating a blazing wall of fire that ignites and burns all targets over 6.5s.",
            "stats": {"Damage": "Lingering Burn", "Radius": "300px Line", "Type": "Fire Damage"},
        },
        GAS: {
            "id": GAS,
            "key": "5",
            "name": "Gas Strike",
            "subtitle": "Corrosive Chemical Cloud",
            "cooldown": COOLDOWN_GAS_STRIKE,
            "color": (46, 204, 113),
            "border_color": (80, 230, 140),
            "symbol": "GAS",
            "desc": "Releases an expanding toxic cloud that corrodes hostiles rapidly and impairs flight control.",
            "stats": {"Damage": "Corrosive DOT", "Radius": "240px Cloud", "Type": "Chemical Toxic"},
        },
        ROCKETS: {
            "id": ROCKETS,
            "key": "6",
            "name": "Rocket Pods",
            "subtitle": "Anti-Armor Guided Salvo",
            "cooldown": COOLDOWN_ROCKET_PODS,
            "color": (0, 190, 255),
            "border_color": (80, 220, 255),
            "symbol": "RP",
            "desc": "Launches 3 guided anti-tank rockets that aggressively home in on high-threat hostile targets.",
            "stats": {"Damage": "Heavy (4.5x3)", "Radius": "Homing Single", "Type": "Target Seeking"},
        },
        EMS: {
            "id": EMS,
            "key": "7",
            "name": "EMS Stun Strike",
            "subtitle": "Electromagnetic Pulse",
            "cooldown": COOLDOWN_EMS_STUN,
            "color": (155, 110, 255),
            "border_color": (190, 150, 255),
            "symbol": "EMS",
            "desc": "Discharges an electromagnetic field that temporarily freezes enemy flight systems and engines for 4.5s.",
            "stats": {"Damage": "Stun / EMP", "Radius": "280px Pulse", "Type": "Disabling Field"},
        },
        SMOKE: {
            "id": SMOKE,
            "key": "8",
            "name": "Smoke Screen",
            "subtitle": "Tactical Countermeasures",
            "cooldown": COOLDOWN_SMOKE_SCREEN,
            "color": (180, 195, 210),
            "border_color": (215, 225, 235),
            "symbol": "SMK",
            "desc": "Deploys thick radar-absorbing smoke that breaks enemy agro and shields allied forces from attack.",
            "stats": {"Damage": "Concealment", "Radius": "280px Screen", "Type": "Defense / Stealth"},
        },
    }

    ORDER = [STRAFE, BOMB_500KG, CLUSTER, NAPALM, GAS, ROCKETS, EMS, SMOKE]


# =====================================================================
# OBSTACLES & EXTRACTION BEACON
# =====================================================================

class GroundObstacle:
    """Represents a terrain feature or structure that ground units steer around."""
    def __init__(self, x, y, width, height, kind="bunker"):
        self.rect = pygame.Rect(int(x), int(y), int(width), int(height))
        self.kind = kind
        self.x = float(x)
        self.y = float(y)
        self.width = width
        self.height = height

    def draw(self, surface, camera_x, camera_y):
        screen_x = self.x - camera_x
        screen_y = self.y - camera_y

        if -100 <= screen_x <= 1380 and -100 <= screen_y <= 820:
            rect = pygame.Rect(int(screen_x), int(screen_y), self.width, self.height)
            if self.kind == "bunker":
                pygame.draw.rect(surface, (35, 45, 60), rect, border_radius=6)
                pygame.draw.rect(surface, (65, 85, 115), rect, 2, border_radius=6)
                for i in range(4, self.width - 4, 12):
                    pygame.draw.line(surface, (50, 65, 90), (screen_x + i, screen_y + 4), (screen_x + i, screen_y + self.height - 4), 1)
            elif self.kind == "barricade":
                pygame.draw.rect(surface, (60, 50, 40), rect, border_radius=3)
                pygame.draw.rect(surface, (110, 95, 75), rect, 2, border_radius=3)
            elif self.kind == "relay":
                pygame.draw.rect(surface, (25, 30, 42), rect, border_radius=4)
                pygame.draw.rect(surface, (0, 180, 230), rect, 1, border_radius=4)
                pulse = (pygame.time.get_ticks() // 400) % 2
                col = (0, 255, 180) if pulse else (0, 120, 90)
                pygame.draw.circle(surface, col, (int(screen_x + self.width // 2), int(screen_y + 8)), 4)
            else:
                pygame.draw.ellipse(surface, (40, 42, 50), rect)
                pygame.draw.ellipse(surface, (70, 75, 88), rect, 2)


class ExtractionBeacon:
    """Extraction Beacon & Landing Zone where Pelican-1 evacuates the Helldivers."""
    def __init__(self, x, y):
        self.x = float(x)
        self.y = float(y)
        self.radius = 160.0
        self.active = False
        self.countdown = 30.0
        self.extracted = False
        self.pelican_arrived = False
        self.pelican_altitude = 500.0
        self.pelican_departed = False

    def activate(self):
        self.active = True
        self.countdown = 30.0

    def update(self, dt):
        if self.active and not self.pelican_arrived:
            self.countdown = max(0.0, self.countdown - dt)
            if self.countdown <= 0:
                self.pelican_arrived = True

        if self.pelican_arrived and self.pelican_altitude > 0:
            self.pelican_altitude = max(0.0, self.pelican_altitude - 220.0 * dt)

        if self.extracted and self.pelican_altitude < 600:
            self.pelican_altitude += 280.0 * dt
            if self.pelican_altitude >= 600:
                self.pelican_departed = True

    def draw(self, surface, camera_x, camera_y):
        screen_x = self.x - camera_x
        screen_y = self.y - camera_y

        if -300 <= screen_x <= 1580 and -300 <= screen_y <= 1020:
            now = pygame.time.get_ticks()
            pulse = math.sin(now * 0.006)

            ring_surf = pygame.Surface((int(self.radius * 2), int(self.radius * 2)), pygame.SRCALPHA)
            pygame.draw.circle(ring_surf, (0, 180, 255, 30) if not self.active else (255, 140, 0, 45), (int(self.radius), int(self.radius)), int(self.radius))
            pygame.draw.circle(ring_surf, (0, 220, 255, 180) if not self.active else (255, 200, 50, 220), (int(self.radius), int(self.radius)), int(self.radius), 2)
            surface.blit(ring_surf, (screen_x - self.radius, screen_y - self.radius))

            base_rect = pygame.Rect(int(screen_x - 16), int(screen_y - 16), 32, 32)
            pygame.draw.rect(surface, (20, 30, 45), base_rect, border_radius=5)
            pygame.draw.rect(surface, (0, 200, 255) if not self.active else (255, 160, 0), base_rect, 2, border_radius=5)

            beam_surf = pygame.Surface((32, 240), pygame.SRCALPHA)
            beam_alpha = int(100 + 70 * pulse)
            beam_col = (0, 220, 255, beam_alpha) if not self.active else (255, 180, 40, beam_alpha)
            pygame.draw.polygon(beam_surf, beam_col, [(12, 240), (20, 240), (26, 0), (6, 0)])
            surface.blit(beam_surf, (screen_x - 16, screen_y - 240))

            pygame.draw.circle(surface, (255, 255, 255), (int(screen_x), int(screen_y)), 6)
            pygame.draw.circle(surface, (0, 230, 255) if not self.active else (255, 190, 50), (int(screen_x), int(screen_y)), int(10 + 3 * pulse), 1)

            if self.pelican_arrived and not self.pelican_departed:
                p_y = screen_y - self.pelican_altitude
                scale = max(0.5, 1.0 - (self.pelican_altitude / 1000.0))
                self._draw_pelican(surface, screen_x, p_y, scale)

    def _draw_pelican(self, surface, x, y, scale):
        w = int(72 * scale)
        h = int(90 * scale)
        pel_surf = pygame.Surface((w * 2, h * 2), pygame.SRCALPHA)
        cx, cy = w, h

        pts = [
            (cx, cy - h // 2),
            (cx + w // 2, cy + h // 3),
            (cx + w // 3, cy + h // 2),
            (cx - w // 3, cy + h // 2),
            (cx - w // 2, cy + h // 3),
        ]
        pygame.draw.polygon(pel_surf, (30, 42, 58), pts)
        pygame.draw.polygon(pel_surf, (80, 110, 145), pts, 2)
        pygame.draw.polygon(pel_surf, (0, 220, 255), [(cx, cy - h // 3), (cx + w // 6, cy - h // 6), (cx - w // 6, cy - h // 6)])
        glow_r = int(6 * scale)
        pygame.draw.circle(pel_surf, (0, 200, 255), (cx - w // 4, cy + h // 2), glow_r)
        pygame.draw.circle(pel_surf, (0, 200, 255), (cx + w // 4, cy + h // 2), glow_r)
        surface.blit(pel_surf, (x - w, y - h))


# =====================================================================
# ALLIED HELLDIVER GROUND UNIT
# =====================================================================

class HelldiverBullet(pygame.Rect):
    """Tracer bullet fired by Helldivers at aerial or ground hostiles."""
    def __init__(self, x, y, target_x, target_y, damage=HELLDIVER_BULLET_DAMAGE):
        pygame.Rect.__init__(self, int(x - 2), int(y - 2), 5, 5)
        self.pos_x = float(x)
        self.pos_y = float(y)
        self.damage = damage
        self.used = False

        dx = target_x - x
        dy = target_y - y
        dist = max(1.0, math.hypot(dx, dy))
        self.vx = (dx / dist) * HELLDIVER_BULLET_SPEED
        self.vy = (dy / dist) * HELLDIVER_BULLET_SPEED
        self.lifetime = 1200  # ms
        self.spawn_time = pygame.time.get_ticks()

    def update(self):
        self.pos_x += self.vx
        self.pos_y += self.vy
        self.x = int(self.pos_x)
        self.y = int(self.pos_y)
        if pygame.time.get_ticks() - self.spawn_time > self.lifetime:
            self.used = True

    def draw(self, surface, camera_x, camera_y):
        sx = self.pos_x - camera_x
        sy = self.pos_y - camera_y
        pygame.draw.circle(surface, (255, 240, 100), (int(sx), int(sy)), 2)
        pygame.draw.line(surface, (255, 180, 50), (int(sx), int(sy)), (int(sx - self.vx * 1.5), int(sy - self.vy * 1.5)), 1)


class HelldiverUnit:
    """Individual tactical Helldiver soldier on the ground."""
    ROLES = [
        {"name": "Viper-1 (Lead)", "role": "Squad Leader", "color": (255, 215, 0), "cape": (255, 200, 0)},
        {"name": "Viper-2 (Heavy)", "role": "Heavy Gunner", "color": (52, 152, 219), "cape": (41, 128, 185)},
        {"name": "Viper-3 (Scout)", "role": "DMR Marksman", "color": (46, 204, 113), "cape": (39, 174, 96)},
        {"name": "Viper-4 (Medic)", "role": "Combat Medic", "color": (231, 76, 60), "cape": (192, 57, 43)},
    ]

    def __init__(self, index, x, y):
        self.index = index
        info = self.ROLES[index % len(self.ROLES)]
        self.callsign = info["name"]
        self.role = info["role"]
        self.theme_color = info["color"]
        self.cape_color = info["cape"]

        self.pos_x = float(x)
        self.pos_y = float(y)
        self.x = int(x)
        self.y = int(y)
        self.width = 18
        self.height = 18

        self.max_health = HELLDIVER_MAX_HEALTH
        self.health = HELLDIVER_MAX_HEALTH
        self.state = "DEFENDING"  # "DEFENDING", "ENGAGING", "SUPPLYING", "EXTRACTING", "DOWNED", "EXTRACTED"
        self.aim_angle = 0.0
        self.last_fire_time = 0
        self.fire_cooldown = HELLDIVER_FIRE_COOLDOWN_MS + random.randint(-40, 40)

        self.formation_offset = (random.uniform(-40, 40), random.uniform(-40, 40))
        self.target_waypoint = (self.pos_x, self.pos_y)
        self.muzzle_flash_timer = 0
        self.shield = 25.0
        self.max_shield = 25.0

    @property
    def is_alive(self):
        return self.health > 0 and self.state != "DOWNED" and self.state != "EXTRACTED"

    @property
    def rect(self):
        return pygame.Rect(int(self.pos_x), int(self.pos_y), self.width, self.height)

    def take_damage(self, amount):
        if not self.is_alive:
            return
        if self.shield > 0:
            if self.shield >= amount:
                self.shield -= amount
                return
            else:
                amount -= self.shield
                self.shield = 0.0

        self.health = max(0.0, self.health - amount)
        if self.health <= 0:
            self.state = "DOWNED"

    def heal(self, amount):
        if self.is_alive:
            self.health = min(self.max_health, self.health + amount)
            self.shield = self.max_shield

    def update_ai(self, dt, squad_center, enemies, obstacles, bullets_list, supply_pods=None, beacon=None, enemy_ground=None):
        if not self.is_alive:
            return

        now = pygame.time.get_ticks()

        # Check nearest target: either enemy ground unit or airborne enemy
        nearest_target = None
        min_dist = float("inf")

        # Check ground enemies first (direct immediate perimeter threat)
        if enemy_ground:
            for eg in enemy_ground:
                if eg.is_alive:
                    d = math.hypot(eg.pos_x - self.pos_x, eg.pos_y - self.pos_y)
                    if d < min_dist:
                        min_dist = d
                        nearest_target = (eg.pos_x + eg.width / 2, eg.pos_y + eg.height / 2)

        # Check aerial enemies
        if enemies:
            living_aerial = [e for e in enemies if not getattr(e, 'exploding', False) and getattr(e, 'health', 0) > 0]
            for enemy in living_aerial:
                d = math.hypot(enemy.x + 18 - self.pos_x, enemy.y + 18 - self.pos_y)
                if d < min_dist:
                    min_dist = d
                    nearest_target = (enemy.x + 18, enemy.y + 18)

        # Tactical waypoint decision
        if beacon and beacon.active and beacon.pelican_arrived and not beacon.pelican_departed:
            self.state = "EXTRACTING"
            self.target_waypoint = (beacon.x + self.formation_offset[0] * 0.4, beacon.y + self.formation_offset[1] * 0.4)
            dist_to_beacon = math.hypot(beacon.x - self.pos_x, beacon.y - self.pos_y)
            if dist_to_beacon < 35.0:
                self.state = "EXTRACTED"
                return

        elif self.health < 45.0 and supply_pods:
            nearest_pod = min(supply_pods, key=lambda p: math.hypot(p.x - self.pos_x, p.y - self.pos_y))
            self.state = "SUPPLYING"
            self.target_waypoint = (nearest_pod.x, nearest_pod.y)

        elif nearest_target and min_dist <= HELLDIVER_ENGAGE_RADIUS:
            self.state = "ENGAGING"
            self.target_waypoint = (squad_center[0] + self.formation_offset[0], squad_center[1] + self.formation_offset[1])
        else:
            self.state = "DEFENDING"
            self.target_waypoint = (squad_center[0] + self.formation_offset[0], squad_center[1] + self.formation_offset[1])

        # Steering
        tx, ty = self.target_waypoint
        move_dx = tx - self.pos_x
        move_dy = ty - self.pos_y
        dist_to_target = math.hypot(move_dx, move_dy)

        vx, vy = 0.0, 0.0
        if dist_to_target > 8.0:
            speed = HELLDIVER_SPEED * (1.3 if self.state in ("EXTRACTING", "SUPPLYING") else 1.0)
            vx = (move_dx / dist_to_target) * speed
            vy = (move_dy / dist_to_target) * speed

        # Obstacle avoidance
        for obs in obstacles:
            if obs.rect.inflate(24, 24).collidepoint(self.pos_x + vx * 6, self.pos_y + vy * 6):
                cx, cy = obs.rect.centerx, obs.rect.centery
                diff_x, diff_y = self.pos_x - cx, self.pos_y - cy
                d = max(1.0, math.hypot(diff_x, diff_y))
                vx += (diff_x / d) * 2.0
                vy += (diff_y / d) * 2.0

        # Boundary containment
        margin = 150
        if self.pos_x < margin:
            vx += 2.0
        elif self.pos_x > MAP_WIDTH - margin:
            vx -= 2.0
        if self.pos_y < margin:
            vy += 2.0
        elif self.pos_y > MAP_HEIGHT - margin:
            vy -= 2.0

        self.pos_x += vx
        self.pos_y += vy
        self.x = int(self.pos_x)
        self.y = int(self.pos_y)

        # Firing at target
        if nearest_target and min_dist <= HELLDIVER_ENGAGE_RADIUS:
            target_x, target_y = nearest_target
            dx = target_x - self.pos_x
            dy = target_y - self.pos_y
            self.aim_angle = math.degrees(math.atan2(dx, dy))

            if now - self.last_fire_time >= self.fire_cooldown:
                self.last_fire_time = now
                self.muzzle_flash_timer = 4
                bullet = HelldiverBullet(self.pos_x, self.pos_y, target_x, target_y)
                bullets_list.append(bullet)
        else:
            dx = squad_center[0] - self.pos_x
            dy = squad_center[1] - self.pos_y
            if math.hypot(dx, dy) > 1.0:
                self.aim_angle = math.degrees(math.atan2(dx, dy))

    def draw(self, surface, camera_x, camera_y, font):
        if self.state == "EXTRACTED":
            return

        screen_x = self.pos_x - camera_x
        screen_y = self.pos_y - camera_y

        if -60 <= screen_x <= 1340 and -60 <= screen_y <= 780:
            if not self.is_alive:
                pygame.draw.line(surface, (150, 40, 40), (screen_x - 6, screen_y - 6), (screen_x + 6, screen_y + 6), 2)
                pygame.draw.line(surface, (150, 40, 40), (screen_x + 6, screen_y - 6), (screen_x - 6, screen_y + 6), 2)
                dead_lbl = font.render("K.I.A.", True, (255, 80, 80))
                surface.blit(dead_lbl, (screen_x - dead_lbl.get_width() // 2, screen_y - 18))
                return

            rad = math.radians(self.aim_angle)
            cape_dx = -math.sin(rad) * 6
            cape_dy = -math.cos(rad) * 6

            # Cape & Torso
            pygame.draw.circle(surface, self.cape_color, (int(screen_x + cape_dx), int(screen_y + cape_dy)), 7)
            pygame.draw.circle(surface, (28, 35, 48), (int(screen_x), int(screen_y)), 7)
            pygame.draw.circle(surface, self.theme_color, (int(screen_x), int(screen_y)), 7, 1)

            # Helmet Visor
            visor_x = screen_x + math.sin(rad) * 5
            visor_y = screen_y + math.cos(rad) * 5
            pygame.draw.circle(surface, (0, 220, 255), (int(visor_x), int(visor_y)), 3)

            # Weapon barrel & muzzle flash
            gun_x = screen_x + math.sin(rad) * 11
            gun_y = screen_y + math.cos(rad) * 11
            pygame.draw.line(surface, (120, 130, 145), (screen_x, screen_y), (gun_x, gun_y), 2)
            if self.muzzle_flash_timer > 0:
                self.muzzle_flash_timer -= 1
                pygame.draw.circle(surface, (255, 230, 100), (int(gun_x), int(gun_y)), 4)

            # Overhead Health & Shield Bar
            bar_w = 26
            bar_h = 3
            bar_x = screen_x - bar_w // 2
            bar_y = screen_y - 14

            pygame.draw.rect(surface, (10, 15, 25), (bar_x, bar_y, bar_w, bar_h))
            hp_w = max(0, int((self.health / self.max_health) * bar_w))
            hp_col = (46, 204, 113) if self.health > 50 else ((241, 196, 15) if self.health > 25 else (231, 76, 60))
            pygame.draw.rect(surface, hp_col, (bar_x, bar_y, hp_w, bar_h))

            if self.shield > 0:
                sh_w = max(0, int((self.shield / self.max_shield) * bar_w))
                pygame.draw.rect(surface, (0, 200, 255), (bar_x, bar_y - 2, sh_w, 2))

            if self.state in ("ENGAGING", "SUPPLYING", "EXTRACTING"):
                tag_col = (255, 180, 50) if self.state == "ENGAGING" else (0, 220, 255)
                lbl = font.render(self.state, True, tag_col)
                surface.blit(lbl, (screen_x - lbl.get_width() // 2, bar_y - 10))


# =====================================================================
# HOSTILE ENEMY GROUND UNITS & FABRICATORS
# =====================================================================

class EnemyLaserBullet(pygame.Rect):
    """Red laser bolt fired by enemy ground forces at Helldivers."""
    def __init__(self, x, y, target_x, target_y, damage=ENEMY_LASER_DAMAGE):
        pygame.Rect.__init__(self, int(x - 3), int(y - 3), 6, 6)
        self.pos_x = float(x)
        self.pos_y = float(y)
        self.damage = damage
        self.used = False

        dx = target_x - x
        dy = target_y - y
        dist = max(1.0, math.hypot(dx, dy))
        self.vx = (dx / dist) * ENEMY_LASER_SPEED
        self.vy = (dy / dist) * ENEMY_LASER_SPEED
        self.lifetime = 1100
        self.spawn_time = pygame.time.get_ticks()

    def update(self):
        self.pos_x += self.vx
        self.pos_y += self.vy
        self.x = int(self.pos_x)
        self.y = int(self.pos_y)
        if pygame.time.get_ticks() - self.spawn_time > self.lifetime:
            self.used = True

    def draw(self, surface, camera_x, camera_y):
        sx = self.pos_x - camera_x
        sy = self.pos_y - camera_y
        pygame.draw.circle(surface, (255, 60, 60), (int(sx), int(sy)), 3)
        pygame.draw.line(surface, (255, 120, 120), (int(sx), int(sy)), (int(sx - self.vx * 1.5), int(sy - self.vy * 1.5)), 2)


class EnemyGroundUnit:
    """Hostile ground unit (Automaton Trooper or Heavy Armored Walker)."""
    TYPE_TROOPER = "trooper"
    TYPE_WALKER = "walker"

    def __init__(self, kind, x, y):
        self.kind = kind
        self.pos_x = float(x)
        self.pos_y = float(y)
        self.x = int(x)
        self.y = int(y)

        if kind == self.TYPE_WALKER:
            self.width = 32
            self.height = 32
            self.max_health = ENEMY_WALKER_MAX_HEALTH
            self.speed = ENEMY_WALKER_SPEED
            self.fire_rate_ms = 900
            self.score_value = 60
        else:
            self.width = 18
            self.height = 18
            self.max_health = ENEMY_TROOPER_MAX_HEALTH
            self.speed = ENEMY_TROOPER_SPEED
            self.fire_rate_ms = 600
            self.score_value = 25

        self.health = self.max_health
        self.last_fire_time = pygame.time.get_ticks() + random.randint(100, 600)
        self.aim_angle = 0.0
        self.exploding = False

    @property
    def is_alive(self):
        return self.health > 0 and not self.exploding

    @property
    def rect(self):
        return pygame.Rect(int(self.pos_x), int(self.pos_y), self.width, self.height)

    def colliderect(self, other):
        return self.rect.colliderect(getattr(other, 'rect', other))

    def take_damage(self, amount):
        if not self.is_alive:
            return
        self.health = max(0.0, self.health - amount)
        if self.health <= 0:
            self.exploding = True

    def update(self, dt, target_squad, lasers_list):
        if not self.is_alive:
            return

        now = pygame.time.get_ticks()

        # Find closest living Helldiver
        living_targets = [u for u in target_squad if u.is_alive]
        if not living_targets:
            return

        nearest_target = min(living_targets, key=lambda u: math.hypot(u.pos_x - self.pos_x, u.pos_y - self.pos_y))
        tx = nearest_target.pos_x
        ty = nearest_target.pos_y
        dx = tx - self.pos_x
        dy = ty - self.pos_y
        dist = math.hypot(dx, dy)

        # Aim towards target
        self.aim_angle = math.degrees(math.atan2(dx, dy))

        # Advance if outside firing sweetspot
        if dist > 140.0:
            self.pos_x += (dx / dist) * self.speed
            self.pos_y += (dy / dist) * self.speed
            self.x = int(self.pos_x)
            self.y = int(self.pos_y)

        # Shoot red lasers at Helldivers
        if dist <= ENEMY_GROUND_ENGAGE_RADIUS and now - self.last_fire_time >= self.fire_rate_ms:
            self.last_fire_time = now
            laser = EnemyLaserBullet(self.pos_x + self.width / 2, self.pos_y + self.height / 2, tx, ty)
            lasers_list.append(laser)

    def draw(self, surface, camera_x, camera_y):
        if not self.is_alive:
            return

        screen_x = self.pos_x - camera_x
        screen_y = self.pos_y - camera_y

        if -60 <= screen_x <= 1340 and -60 <= screen_y <= 780:
            cx = int(screen_x + self.width / 2)
            cy = int(screen_y + self.height / 2)
            rad = math.radians(self.aim_angle)

            if self.kind == self.TYPE_WALKER:
                # Heavy Armored Walker
                pygame.draw.rect(surface, (50, 55, 65), (cx - 14, cy - 14, 28, 28), border_radius=5)
                pygame.draw.rect(surface, (255, 60, 40), (cx - 14, cy - 14, 28, 28), 2, border_radius=5)

                # Twin gun barrels
                b1_x = cx + math.sin(rad) * 18 - math.cos(rad) * 8
                b1_y = cy + math.cos(rad) * 18 + math.sin(rad) * 8
                b2_x = cx + math.sin(rad) * 18 + math.cos(rad) * 8
                b2_y = cy + math.cos(rad) * 18 - math.sin(rad) * 8
                pygame.draw.line(surface, (180, 40, 40), (cx - math.cos(rad) * 8, cy + math.sin(rad) * 8), (b1_x, b1_y), 3)
                pygame.draw.line(surface, (180, 40, 40), (cx + math.cos(rad) * 8, cy - math.sin(rad) * 8), (b2_x, b2_y), 3)

                # Red core eye
                pygame.draw.circle(surface, (255, 30, 30), (cx, cy), 5)
            else:
                # Cyber Trooper
                pygame.draw.circle(surface, (45, 48, 55), (cx, cy), 8)
                pygame.draw.circle(surface, (255, 70, 70), (cx, cy), 8, 1)
                # Red eye visor
                vx = cx + math.sin(rad) * 5
                vy = cy + math.cos(rad) * 5
                pygame.draw.circle(surface, (255, 40, 40), (int(vx), int(vy)), 3)
                # Gun arm
                gx = cx + math.sin(rad) * 12
                gy = cy + math.cos(rad) * 12
                pygame.draw.line(surface, (180, 50, 50), (cx, cy), (int(gx), int(gy)), 2)

            # Overhead Health Bar
            bar_w = self.width + 8
            bar_h = 3
            bx = cx - bar_w // 2
            by = screen_y - 8
            pygame.draw.rect(surface, (15, 15, 20), (bx, by, bar_w, bar_h))
            hp_w = max(0, int((self.health / self.max_health) * bar_w))
            pygame.draw.rect(surface, (255, 60, 60), (bx, by, hp_w, bar_h))


class EnemyFabricator:
    """Destructible enemy foundry structure that continuously spawns ground reinforcements."""
    def __init__(self, x, y):
        self.pos_x = float(x)
        self.pos_y = float(y)
        self.x = int(x)
        self.y = int(y)
        self.width = 64
        self.height = 64
        self.max_health = ENEMY_FABRICATOR_MAX_HEALTH
        self.health = self.max_health
        self.exploding = False
        self.spawn_timer = 5.0
        self.spawn_interval = 8.0  # Spawns trooper/walker every 8s

    @property
    def is_alive(self):
        return self.health > 0 and not self.exploding

    @property
    def rect(self):
        return pygame.Rect(int(self.pos_x), int(self.pos_y), self.width, self.height)

    def colliderect(self, other):
        return self.rect.colliderect(getattr(other, 'rect', other))

    def take_damage(self, amount):
        if not self.is_alive:
            return
        self.health = max(0.0, self.health - amount)
        if self.health <= 0:
            self.exploding = True

    def update(self, dt, enemy_ground_list):
        if not self.is_alive:
            return
        self.spawn_timer -= dt
        if self.spawn_timer <= 0:
            self.spawn_timer = self.spawn_interval
            # Spawn reinforcement
            kind = EnemyGroundUnit.TYPE_WALKER if random.random() < 0.35 else EnemyGroundUnit.TYPE_TROOPER
            sx = self.pos_x + random.uniform(-20, self.width + 20)
            sy = self.pos_y + self.height + 10
            enemy_ground_list.append(EnemyGroundUnit(kind, sx, sy))

    def draw(self, surface, camera_x, camera_y):
        if not self.is_alive:
            return

        screen_x = self.pos_x - camera_x
        screen_y = self.pos_y - camera_y

        if -100 <= screen_x <= 1380 and -100 <= screen_y <= 820:
            rect = pygame.Rect(int(screen_x), int(screen_y), self.width, self.height)
            # Fortress Body
            pygame.draw.rect(surface, (35, 38, 48), rect, border_radius=6)
            pygame.draw.rect(surface, (255, 60, 40), rect, 2, border_radius=6)

            # Glowing Red Foundry Vents
            pulse = int(140 + 70 * math.sin(pygame.time.get_ticks() * 0.008))
            vent_col = (255, pulse // 3, 20)
            pygame.draw.rect(surface, vent_col, (screen_x + 12, screen_y + 14, 16, 24), border_radius=3)
            pygame.draw.rect(surface, vent_col, (screen_x + 36, screen_y + 14, 16, 24), border_radius=3)

            # Overhead Health Bar
            bar_w = self.width
            bar_h = 4
            bx = screen_x
            by = screen_y - 10
            pygame.draw.rect(surface, (10, 15, 20), (bx, by, bar_w, bar_h))
            hp_w = max(0, int((self.health / self.max_health) * bar_w))
            pygame.draw.rect(surface, (255, 60, 60), (bx, by, hp_w, bar_h))


# =====================================================================
# HELLDIVER AIR STRIKE CALL-IN MISSION (COMPATIBLE WITH ALL WEAPONS)
# =====================================================================

class SquadAirStrikeRequest:
    """Helldiver squad active request for Close Air Support ordnance at a specific ground coordinate."""
    def __init__(self, target_x, target_y, requested_strike_type=AirStrikeType.BOMB_500KG):
        self.target_x = float(target_x)
        self.target_y = float(target_y)
        self.requested_type = requested_strike_type
        self.data = AirStrikeType.DATA[requested_strike_type]
        self.active = True
        self.spawn_time = pygame.time.get_ticks()
        self.lifetime = 45.0  # 45s mission window
        self.radius = 180.0
        self.delivered = False

    def update(self, dt):
        self.lifetime -= dt
        if self.lifetime <= 0:
            self.active = False

    def draw(self, surface, camera_x, camera_y, font_small):
        if not self.active or self.delivered:
            return

        screen_x = self.target_x - camera_x
        screen_y = self.target_y - camera_y

        if -250 <= screen_x <= 1530 and -250 <= screen_y <= 970:
            now = pygame.time.get_ticks()
            pulse = math.sin(now * 0.012)
            strike_color = self.data["color"]

            # Pulsing target landing rings
            ring_r = int(self.radius + 8 * pulse)
            pygame.draw.circle(surface, (*strike_color[:3], 90), (int(screen_x), int(screen_y)), ring_r, 2)
            pygame.draw.circle(surface, (255, 60, 40), (int(screen_x), int(screen_y)), 10)

            # High-intensity beacon beam
            beam_surf = pygame.Surface((28, 280), pygame.SRCALPHA)
            alpha = int(140 + 80 * pulse)
            pygame.draw.polygon(beam_surf, (*strike_color[:3], alpha), [(10, 280), (18, 280), (24, 0), (4, 0)])
            surface.blit(beam_surf, (screen_x - 14, screen_y - 280))

            # HUD Label over beacon
            lbl = font_small.render(f"CAS TARGET: {self.data['name'].upper()}", True, (255, 230, 80))
            surface.blit(lbl, (screen_x - lbl.get_width() // 2, screen_y - 32))


# =====================================================================
# PREDICTIVE AIMING RETICLE (GUN PIP + WEAPON IMPACT PREDICTOR)
# =====================================================================

class AimingReticle:
    """Projects dynamic gun convergence pip and weapon-specific air strike impact zones."""
    def __init__(self):
        self.gun_dist = 180.0
        self.strike_base_dist = 320.0

    def calculate_gun_target(self, player):
        rad = math.radians(player.angle)
        gx = player.pos_x + 18 - math.sin(rad) * self.gun_dist
        gy = player.pos_y + 18 - math.cos(rad) * self.gun_dist
        return gx, gy

    def calculate_strike_impact(self, player):
        rad = math.radians(player.angle)
        lead = self.strike_base_dist + getattr(player, 'velocity_x', 5.0) * 8.0
        ix = player.pos_x + 18 - math.sin(rad) * lead
        iy = player.pos_y + 18 - math.cos(rad) * lead
        return ix, iy

    def draw(self, surface, camera_x, camera_y, player, selected_strike_type, is_target_locked=False):
        # 1. Gun Aim Pip (180px ahead)
        gx, gy = self.calculate_gun_target(player)
        sgx = gx - camera_x
        sgy = gy - camera_y

        if 0 <= sgx <= 1280 and 0 <= sgy <= 720:
            # Subtle cyan gun crosshair
            pygame.draw.circle(surface, (0, 220, 255), (int(sgx), int(sgy)), 4, 1)
            pygame.draw.line(surface, (0, 220, 255), (sgx - 7, sgy), (sgx + 7, sgy), 1)
            pygame.draw.line(surface, (0, 220, 255), (sgx, sgy - 7), (sgx, sgy + 7), 1)

        # 2. Predictive Air Strike Impact Reticle
        ix, iy = self.calculate_strike_impact(player)
        six = ix - camera_x
        siy = iy - camera_y

        if -100 <= six <= 1380 and -100 <= siy <= 820:
            strike_data = AirStrikeType.DATA.get(selected_strike_type, AirStrikeType.DATA[AirStrikeType.BOMB_500KG])
            ret_col = (255, 60, 60) if is_target_locked else strike_data["color"]
            rad = math.radians(player.angle)

            # Different visual footprint based on weapon profile
            if selected_strike_type == AirStrikeType.STRAFE:
                # Directional strafing lane rectangle
                corridor_len = 160
                corridor_w = 28
                dx = -math.sin(rad) * corridor_len
                dy = -math.cos(rad) * corridor_len
                pygame.draw.line(surface, ret_col, (six, siy), (six + dx, siy + dy), 2)
                pygame.draw.circle(surface, ret_col, (int(six), int(siy)), 8, 1)
                pygame.draw.circle(surface, ret_col, (int(six + dx), int(siy + dy)), 8, 1)

            elif selected_strike_type == AirStrikeType.NAPALM:
                # Wide perpendicular incendiary bar
                bar_len = 120
                px = math.cos(rad) * (bar_len / 2)
                py = -math.sin(rad) * (bar_len / 2)
                pygame.draw.line(surface, ret_col, (six - px, siy - py), (six + px, siy + py), 3)
                pygame.draw.circle(surface, ret_col, (int(six), int(siy)), 12, 1)

            elif selected_strike_type == AirStrikeType.BOMB_500KG:
                # Colossal blast ring with crosshairs
                pygame.draw.circle(surface, ret_col, (int(six), int(siy)), 42, 2)
                pygame.draw.circle(surface, (255, 255, 255), (int(six), int(siy)), 4)
                pygame.draw.line(surface, ret_col, (six - 52, siy), (six + 52, siy), 1)
                pygame.draw.line(surface, ret_col, (six, siy - 52), (six, siy + 52), 1)

            elif selected_strike_type == AirStrikeType.CLUSTER:
                # Cluster scatter circles
                pygame.draw.circle(surface, ret_col, (int(six), int(siy)), 34, 1)
                for i in range(5):
                    ang = i * (math.pi * 2 / 5)
                    sub_x = six + math.sin(ang) * 18
                    sub_y = siy + math.cos(ang) * 18
                    pygame.draw.circle(surface, ret_col, (int(sub_x), int(sub_y)), 3)

            else:
                # Standard targeting reticle
                pygame.draw.circle(surface, ret_col, (int(six), int(siy)), 26, 2)
                pygame.draw.circle(surface, (255, 255, 255), (int(six), int(siy)), 3)

            # Lock brackets & label when locked on target
            if is_target_locked:
                bracket_size = 32
                pygame.draw.rect(surface, (255, 60, 60), (six - bracket_size, siy - bracket_size, bracket_size * 2, bracket_size * 2), 2)


# =====================================================================
# TACTICAL SUPPLY DROP POD & ACTIVE STRIKES
# =====================================================================

class SupplyDropPod:
    """Orbital drop pod delivering health, shield, and ammo resupply."""
    def __init__(self, x, y):
        self.x = float(x)
        self.y = float(y)
        self.altitude = 450.0
        self.landed = False
        self.used = False
        self.despawn_timer = 20.0

    def update(self, dt):
        if not self.landed:
            self.altitude = max(0.0, self.altitude - 380.0 * dt)
            if self.altitude <= 0:
                self.landed = True
        else:
            self.despawn_timer -= dt
            if self.despawn_timer <= 0:
                self.used = True

    def draw(self, surface, camera_x, camera_y):
        if self.used:
            return

        screen_x = self.x - camera_x
        screen_y = self.y - camera_y

        if -60 <= screen_x <= 1340 and -60 <= screen_y <= 780:
            if not self.landed:
                pulse = (pygame.time.get_ticks() // 150) % 2
                col = (0, 220, 255) if pulse else (0, 140, 220)
                pygame.draw.circle(surface, col, (int(screen_x), int(screen_y)), 18, 1)
                pygame.draw.line(surface, (0, 200, 255, 150), (screen_x, screen_y), (screen_x, screen_y - 200), 2)

                pod_y = screen_y - self.altitude
                pygame.draw.rect(surface, (0, 180, 255), (screen_x - 7, pod_y - 14, 14, 28), border_radius=4)
                pygame.draw.polygon(surface, (255, 160, 50), [(screen_x - 4, pod_y + 14), (screen_x + 4, pod_y + 14), (screen_x, pod_y + 24)])
            else:
                crate_rect = pygame.Rect(int(screen_x - 12), int(screen_y - 12), 24, 24)
                pygame.draw.rect(surface, (18, 30, 48), crate_rect, border_radius=4)
                pygame.draw.rect(surface, (0, 220, 255), crate_rect, 2, border_radius=4)

                pygame.draw.line(surface, (0, 255, 180), (screen_x - 5, screen_y), (screen_x + 5, screen_y), 3)
                pygame.draw.line(surface, (0, 255, 180), (screen_x, screen_y - 5), (screen_x, screen_y + 5), 3)
                r = int(18 + 4 * math.sin(pygame.time.get_ticks() * 0.008))
                pygame.draw.circle(surface, (0, 220, 255), (int(screen_x), int(screen_y)), r, 1)


class ActiveAirStrike:
    """Represents an in-flight air strike execution."""
    def __init__(self, strike_type, target_x, target_y, player_angle=0.0):
        self.type = strike_type
        self.target_x = float(target_x)
        self.target_y = float(target_y)
        self.angle = float(player_angle)
        self.data = AirStrikeType.DATA[strike_type]

        self.spawn_time = pygame.time.get_ticks()
        self.beacon_duration = 900
        self.impacted = False
        self.finished = False

        self.effect_timer = 0.0
        self.sub_projectiles = []
        self.lingering_zones = []

        if strike_type == AirStrikeType.STRAFE:
            self.beacon_duration = 500
            self.strafe_shots = 26
            self.strafe_fired = 0
            self.strafe_interval = 28
        elif strike_type == AirStrikeType.BOMB_500KG:
            self.beacon_duration = 1000
        elif strike_type == AirStrikeType.CLUSTER:
            self.beacon_duration = 800
        elif strike_type == AirStrikeType.NAPALM:
            self.beacon_duration = 750
        elif strike_type == AirStrikeType.GAS:
            self.beacon_duration = 850
        elif strike_type == AirStrikeType.ROCKETS:
            self.beacon_duration = 600
        elif strike_type == AirStrikeType.EMS:
            self.beacon_duration = 700
        elif strike_type == AirStrikeType.SMOKE:
            self.beacon_duration = 650

    def update(self, dt, enemies, ground_enemies, explosion_group, frames, score_callback=None):
        now = pygame.time.get_ticks()

        if not self.impacted:
            if now - self.spawn_time >= self.beacon_duration:
                self.impacted = True
                self._detonate(enemies, ground_enemies, explosion_group, frames, score_callback)
            return

        self.effect_timer += dt

        # Update lingering zones (Gas, Napalm, EMS)
        for zone in self.lingering_zones:
            zone["lifetime"] -= dt
            if zone["lifetime"] <= 0:
                continue

            zx = zone["x"]
            zy = zone["y"]
            zr = zone["radius"]

            if zone["kind"] == "gas":
                for enemy in enemies:
                    if not getattr(enemy, 'exploding', False) and getattr(enemy, 'health', 0) > 0:
                        if math.hypot(enemy.x + 18 - zx, enemy.y + 18 - zy) <= zr:
                            enemy.health -= 0.18
                            if score_callback and enemy.health <= 0:
                                score_callback(enemy, "Gas Strike")
                for ge in ground_enemies:
                    if ge.is_alive and math.hypot(ge.pos_x + ge.width / 2 - zx, ge.pos_y + ge.height / 2 - zy) <= zr:
                        ge.take_damage(0.25)
                        if score_callback and not ge.is_alive:
                            score_callback(ge, "Gas Strike")

            elif zone["kind"] == "napalm":
                for enemy in enemies:
                    if not getattr(enemy, 'exploding', False) and getattr(enemy, 'health', 0) > 0:
                        if math.hypot(enemy.x + 18 - zx, enemy.y + 18 - zy) <= zr:
                            enemy.health -= 0.28
                            if score_callback and enemy.health <= 0:
                                score_callback(enemy, "Napalm Strike")
                for ge in ground_enemies:
                    if ge.is_alive and math.hypot(ge.pos_x + ge.width / 2 - zx, ge.pos_y + ge.height / 2 - zy) <= zr:
                        ge.take_damage(0.4)
                        if score_callback and not ge.is_alive:
                            score_callback(ge, "Napalm Strike")

            elif zone["kind"] == "ems":
                for enemy in enemies:
                    if not getattr(enemy, 'exploding', False):
                        if math.hypot(enemy.x + 18 - zx, enemy.y + 18 - zy) <= zr:
                            enemy.speed = 0.0
                for ge in ground_enemies:
                    if ge.is_alive and math.hypot(ge.pos_x + ge.width / 2 - zx, ge.pos_y + ge.height / 2 - zy) <= zr:
                        ge.speed = 0.0

        self.lingering_zones = [z for z in self.lingering_zones if z["lifetime"] > 0]

        # Sequential Strafe firing
        if self.type == AirStrikeType.STRAFE and self.strafe_fired < self.strafe_shots:
            step = self.strafe_fired - self.strafe_shots // 2
            rad = math.radians(self.angle)
            spread_dist = step * 24.0
            sx = self.target_x - math.sin(rad) * spread_dist
            sy = self.target_y - math.cos(rad) * spread_dist

            self.sub_projectiles.append({"x": sx, "y": sy, "timer": 0.18})
            self.strafe_fired += 1

            for enemy in enemies:
                if not getattr(enemy, 'exploding', False) and getattr(enemy, 'health', 0) > 0:
                    if math.hypot(enemy.x + 18 - sx, enemy.y + 18 - sy) <= 35.0:
                        enemy.health -= 1.8
                        if score_callback and enemy.health <= 0:
                            score_callback(enemy, "Machine Gun Dive")

            for ge in ground_enemies:
                if ge.is_alive and math.hypot(ge.pos_x + ge.width / 2 - sx, ge.pos_y + ge.height / 2 - sy) <= 35.0:
                    ge.take_damage(2.2)
                    if score_callback and not ge.is_alive:
                        score_callback(ge, "Machine Gun Dive")

        for p in self.sub_projectiles:
            p["timer"] -= dt
        self.sub_projectiles = [p for p in self.sub_projectiles if p["timer"] > 0]

        if self.impacted and len(self.lingering_zones) == 0 and len(self.sub_projectiles) == 0 and self.effect_timer >= 1.0:
            self.finished = True

    def _detonate(self, enemies, ground_enemies, explosion_group, frames, score_callback):
        tx, ty = self.target_x, self.target_y

        if self.type == AirStrikeType.BOMB_500KG:
            radius = 320.0
            damage = 16.0
            self._apply_area_blast(tx, ty, radius, damage, enemies, ground_enemies, score_callback)
            self._spawn_cluster_explosions(tx, ty, 5, 60.0, explosion_group, frames)

        elif self.type == AirStrikeType.CLUSTER:
            radius = 280.0
            for _ in range(8):
                cx = tx + random.uniform(-140, 140)
                cy = ty + random.uniform(-140, 140)
                self._apply_area_blast(cx, cy, 110.0, 3.8, enemies, ground_enemies, score_callback)
                self._spawn_cluster_explosions(cx, cy, 1, 0, explosion_group, frames)

        elif self.type == AirStrikeType.NAPALM:
            rad = math.radians(self.angle + 90)
            for i in range(-3, 4):
                fx = tx + math.sin(rad) * (i * 45.0)
                fy = ty + math.cos(rad) * (i * 45.0)
                self.lingering_zones.append({"kind": "napalm", "x": fx, "y": fy, "radius": 75.0, "lifetime": 6.5})
                self._apply_area_blast(fx, fy, 80.0, 2.5, enemies, ground_enemies, score_callback)
                self._spawn_cluster_explosions(fx, fy, 1, 0, explosion_group, frames)

        elif self.type == AirStrikeType.GAS:
            self.lingering_zones.append({"kind": "gas", "x": tx, "y": ty, "radius": 240.0, "lifetime": 7.0})
            self._apply_area_blast(tx, ty, 200.0, 1.5, enemies, ground_enemies, score_callback)

        elif self.type == AirStrikeType.ROCKETS:
            # Target closest aerial or ground hostiles
            all_targets = []
            for e in enemies:
                if not getattr(e, 'exploding', False) and getattr(e, 'health', 0) > 0:
                    all_targets.append((e.x + 18, e.y + 18, e))
            for ge in ground_enemies:
                if ge.is_alive:
                    all_targets.append((ge.pos_x + ge.width / 2, ge.pos_y + ge.height / 2, ge))

            all_targets.sort(key=lambda t: math.hypot(t[0] - tx, t[1] - ty))
            for i in range(min(3, len(all_targets))):
                gx, gy, target = all_targets[i]
                if hasattr(target, 'take_damage'):
                    target.take_damage(4.5)
                else:
                    target.health -= 4.5
                self._spawn_cluster_explosions(gx, gy, 1, 0, explosion_group, frames)
                if score_callback and ((hasattr(target, 'is_alive') and not target.is_alive) or (getattr(target, 'health', 1) <= 0)):
                    score_callback(target, "Rocket Pods")

        elif self.type == AirStrikeType.EMS:
            self.lingering_zones.append({"kind": "ems", "x": tx, "y": ty, "radius": 280.0, "lifetime": 4.5})
            for enemy in enemies:
                if not getattr(enemy, 'exploding', False):
                    if math.hypot(enemy.x + 18 - tx, enemy.y + 18 - ty) <= 280.0:
                        enemy.speed = 0.0
            for ge in ground_enemies:
                if ge.is_alive and math.hypot(ge.pos_x + ge.width / 2 - tx, ge.pos_y + ge.height / 2 - ty) <= 280.0:
                    ge.speed = 0.0

        elif self.type == AirStrikeType.SMOKE:
            for i in range(-2, 3):
                sx = tx + random.uniform(-50, 50) + i * 40
                sy = ty + random.uniform(-50, 50)
                self.lingering_zones.append({"kind": "smoke", "x": sx, "y": sy, "radius": 130.0, "lifetime": 9.0})

    def _apply_area_blast(self, x, y, radius, damage, enemies, ground_enemies, score_callback):
        for enemy in enemies:
            if not getattr(enemy, 'exploding', False) and getattr(enemy, 'health', 0) > 0:
                dist = math.hypot(enemy.x + 18 - x, enemy.y + 18 - y)
                if dist <= radius:
                    falloff = max(0.2, 1.0 - (dist / radius))
                    enemy.health -= damage * falloff
                    if score_callback and enemy.health <= 0:
                        score_callback(enemy, self.data["name"])

        for ge in ground_enemies:
            if ge.is_alive:
                dist = math.hypot(ge.pos_x + ge.width / 2 - x, ge.pos_y + ge.height / 2 - y)
                if dist <= radius:
                    falloff = max(0.2, 1.0 - (dist / radius))
                    ge.take_damage(damage * falloff)
                    if score_callback and not ge.is_alive:
                        score_callback(ge, self.data["name"])

    def _spawn_cluster_explosions(self, x, y, count, spread, explosion_group, frames):
        if explosion_group is None or frames is None:
            return
        from main import Large_explosion_a
        for _ in range(count):
            ex = x + random.uniform(-spread, spread)
            ey = y + random.uniform(-spread, spread)
            explosion_group.add(Large_explosion_a(ex, ey, frames, speed=0.5))

    def draw(self, surface, camera_x, camera_y):
        tx = self.target_x - camera_x
        ty = self.target_y - camera_y

        now = pygame.time.get_ticks()

        if not self.impacted:
            pulse = math.sin(now * 0.015)
            beam_color = self.data["color"]
            beam_surf = pygame.Surface((24, 300), pygame.SRCALPHA)
            alpha = int(140 + 80 * pulse)
            pygame.draw.polygon(beam_surf, (*beam_color[:3], alpha), [(8, 300), (16, 300), (22, 0), (2, 0)])
            surface.blit(beam_surf, (tx - 12, ty - 300))

            reticle_r = int(24 + 6 * pulse)
            pygame.draw.circle(surface, beam_color, (int(tx), int(ty)), reticle_r, 2)
            pygame.draw.circle(surface, (255, 255, 255), (int(tx), int(ty)), 4)
            return

        for zone in self.lingering_zones:
            zx = zone["x"] - camera_x
            zy = zone["y"] - camera_y
            zr = int(zone["radius"])

            if zone["kind"] == "gas":
                gas_surf = pygame.Surface((zr * 2, zr * 2), pygame.SRCALPHA)
                alpha = int(120 * min(1.0, zone["lifetime"] / 2.0))
                pygame.draw.circle(gas_surf, (46, 204, 113, alpha), (zr, zr), zr)
                pygame.draw.circle(gas_surf, (100, 240, 150, alpha + 30), (zr, zr), int(zr * 0.7))
                surface.blit(gas_surf, (zx - zr, zy - zr))

            elif zone["kind"] == "napalm":
                fire_surf = pygame.Surface((zr * 2, zr * 2), pygame.SRCALPHA)
                alpha = int(150 * min(1.0, zone["lifetime"] / 1.5))
                pygame.draw.circle(fire_surf, (255, 80, 20, alpha), (zr, zr), zr)
                pygame.draw.circle(fire_surf, (255, 200, 50, alpha + 40), (zr, zr), int(zr * 0.5))
                surface.blit(fire_surf, (zx - zr, zy - zr))

            elif zone["kind"] == "ems":
                ems_surf = pygame.Surface((zr * 2, zr * 2), pygame.SRCALPHA)
                alpha = int(110 * min(1.0, zone["lifetime"] / 1.0))
                pygame.draw.circle(ems_surf, (155, 110, 255, alpha), (zr, zr), zr, 3)
                pygame.draw.circle(ems_surf, (200, 170, 255, alpha + 20), (zr, zr), int(zr * 0.6), 1)
                surface.blit(ems_surf, (zx - zr, zy - zr))

            elif zone["kind"] == "smoke":
                smoke_surf = pygame.Surface((zr * 2, zr * 2), pygame.SRCALPHA)
                alpha = int(130 * min(1.0, zone["lifetime"] / 2.0))
                pygame.draw.circle(smoke_surf, (180, 195, 210, alpha), (zr, zr), zr)
                surface.blit(smoke_surf, (zx - zr, zy - zr))

        for p in self.sub_projectiles:
            px = p["x"] - camera_x
            py = p["y"] - camera_y
            pygame.draw.circle(surface, (255, 230, 80), (int(px), int(py)), 8)
            pygame.draw.circle(surface, (255, 100, 30), (int(px), int(py)), 14, 1)


# =====================================================================
# AIR STRIKE WEAPON MENU UI
# =====================================================================

class AirStrikeWeaponMenu:
    """Interactive Stratagem / Weapon Menu for selecting between 8 Air Strikes."""
    def __init__(self, width=1280, height=720):
        self.width = width
        self.height = height
        self.is_open = False
        self.selected_type = AirStrikeType.STRAFE

        self.cooldowns = {st: 0.0 for st in AirStrikeType.ORDER}
        self.card_rects = {}
        self._init_layout()

    def _init_layout(self):
        card_w = 210
        card_h = 175
        pad_x = 20
        pad_y = 20
        total_w = 4 * card_w + 3 * pad_x
        start_x = (self.width - total_w) // 2
        start_y = 170

        for idx, st in enumerate(AirStrikeType.ORDER):
            col = idx % 4
            row = idx // 4
            x = start_x + col * (card_w + pad_x)
            y = start_y + row * (card_h + pad_y)
            self.card_rects[st] = pygame.Rect(x, y, card_w, card_h)

    def toggle(self):
        self.is_open = not self.is_open

    def update(self, dt):
        for st in self.cooldowns:
            if self.cooldowns[st] > 0:
                self.cooldowns[st] = max(0.0, self.cooldowns[st] - dt)

    def select(self, strike_type):
        if strike_type in AirStrikeType.DATA:
            self.selected_type = strike_type

    def is_ready(self, strike_type=None):
        st = strike_type if strike_type is not None else self.selected_type
        return self.cooldowns.get(st, 0.0) <= 0.0

    def trigger_strike(self, strike_type=None):
        st = strike_type if strike_type is not None else self.selected_type
        if self.is_ready(st):
            max_cd = AirStrikeType.DATA[st]["cooldown"]
            self.cooldowns[st] = max_cd
            return True
        return False

    def handle_event(self, event, mouse_pos=None):
        if event.type == pygame.KEYDOWN:
            key_map = {
                pygame.K_1: AirStrikeType.STRAFE,
                pygame.K_2: AirStrikeType.BOMB_500KG,
                pygame.K_3: AirStrikeType.CLUSTER,
                pygame.K_4: AirStrikeType.NAPALM,
                pygame.K_5: AirStrikeType.GAS,
                pygame.K_6: AirStrikeType.ROCKETS,
                pygame.K_7: AirStrikeType.EMS,
                pygame.K_8: AirStrikeType.SMOKE,
            }
            if event.key in key_map:
                self.selected_type = key_map[event.key]
                return "selected"

            if event.key in (pygame.K_v, pygame.K_TAB):
                self.toggle()
                return "toggled"

            if event.key == pygame.K_ESCAPE and self.is_open:
                self.is_open = False
                return "closed"

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.is_open and mouse_pos:
                for st, rect in self.card_rects.items():
                    if rect.collidepoint(mouse_pos):
                        self.selected_type = st
                        return "selected"

        return None

    def draw(self, surface, mouse_pos, font_title, font_sub, font_body, font_small):
        if not self.is_open:
            return

        overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        overlay.fill((8, 12, 20, 220))
        surface.blit(overlay, (0, 0))

        title_surf = font_title.render("EAGLE-1 CLOSE AIR SUPPORT ARSENAL", True, (255, 220, 80))
        surface.blit(title_surf, (self.width // 2 - title_surf.get_width() // 2, 85))

        hint_surf = font_sub.render("Select Active Air Strike with [1-8] or Click. Fire with [C]. Close with [V] or [ESC].", True, (160, 190, 220))
        surface.blit(hint_surf, (self.width // 2 - hint_surf.get_width() // 2, 125))

        for st, rect in self.card_rects.items():
            data = AirStrikeType.DATA[st]
            is_sel = (st == self.selected_type)
            is_hov = (mouse_pos is not None and rect.collidepoint(mouse_pos))
            cd = self.cooldowns[st]
            is_ready = (cd <= 0)

            bg_col = (26, 36, 52) if is_sel else ((20, 28, 42) if is_hov else (14, 20, 32))
            pygame.draw.rect(surface, bg_col, rect, border_radius=8)

            border_col = data["border_color"] if is_sel else ((100, 140, 180) if is_hov else (40, 55, 75))
            border_w = 3 if is_sel else 1
            pygame.draw.rect(surface, border_col, rect, border_w, border_radius=8)

            badge_rect = pygame.Rect(rect.x + 8, rect.y + 8, 26, 22)
            pygame.draw.rect(surface, (30, 42, 60), badge_rect, border_radius=4)
            pygame.draw.rect(surface, (80, 110, 145), badge_rect, 1, border_radius=4)
            key_txt = font_small.render(f"[{data['key']}]", True, (255, 230, 100))
            surface.blit(key_txt, (badge_rect.centerx - key_txt.get_width() // 2, badge_rect.centery - key_txt.get_height() // 2))

            if is_ready:
                status_txt = font_small.render("READY", True, (46, 204, 113))
            else:
                status_txt = font_small.render(f"{cd:.1f}s", True, (255, 140, 40))
            surface.blit(status_txt, (rect.right - status_txt.get_width() - 10, rect.y + 11))

            name_col = (255, 255, 255) if is_ready else (170, 180, 195)
            name_txt = font_sub.render(data["name"], True, name_col)
            surface.blit(name_txt, (rect.x + 10, rect.y + 38))

            sub_txt = font_small.render(data["subtitle"], True, data["color"])
            surface.blit(sub_txt, (rect.x + 10, rect.y + 60))

            stat_str = f"Type: {data['stats']['Type']}"
            stat_txt = font_small.render(stat_str, True, (140, 160, 185))
            surface.blit(stat_txt, (rect.x + 10, rect.y + 82))

            bar_x = rect.x + 10
            bar_y = rect.bottom - 16
            bar_w = rect.width - 20
            bar_h = 6
            pygame.draw.rect(surface, (25, 32, 45), (bar_x, bar_y, bar_w, bar_h), border_radius=2)
            if not is_ready:
                max_cd = data["cooldown"]
                fill_w = int((1.0 - (cd / max_cd)) * bar_w)
                pygame.draw.rect(surface, (255, 140, 0), (bar_x, bar_y, fill_w, bar_h), border_radius=2)
            else:
                pygame.draw.rect(surface, (46, 204, 113), (bar_x, bar_y, bar_w, bar_h), border_radius=2)

    def draw_hud_quickbar(self, surface, x, y, font_sub, font_small):
        data = AirStrikeType.DATA[self.selected_type]
        cd = self.cooldowns[self.selected_type]
        is_ready = (cd <= 0)

        box_w = 260
        box_h = 56
        pygame.draw.rect(surface, (16, 22, 34), (x, y, box_w, box_h), border_radius=6)
        pygame.draw.rect(surface, (60, 85, 120), (x, y, box_w, box_h), 1, border_radius=6)

        title_col = data["color"] if is_ready else (180, 190, 205)
        title_txt = font_sub.render(f"[C] {data['name']}", True, title_col)
        surface.blit(title_txt, (x + 8, y + 6))

        status_str = "READY [FIRE: C]" if is_ready else f"REARMING: {cd:.1f}s"
        status_col = (46, 204, 113) if is_ready else (255, 140, 40)
        status_txt = font_small.render(status_str, True, status_col)
        surface.blit(status_txt, (x + 8, y + 26))

        menu_hint = font_small.render("[V] Arsenal Menu [1-8] Swap", True, (130, 150, 175))
        surface.blit(menu_hint, (x + 8, y + 40))


# =====================================================================
# SQUAD & GROUND SUPPORT MANAGER
# =====================================================================

class GroundSupportManager:
    """Master controller managing Allied Helldivers, Hostile Enemy Ground Units,
    Fabricator Outposts, Air Strikes, Aiming Reticles, Supply Drops, and CAS Missions.
    """
    def __init__(self):
        self.units = []
        self.obstacles = []
        self.enemy_ground_units = []
        self.enemy_fabricators = []
        self.active_strikes = []
        self.supply_pods = []
        self.bullets = []
        self.enemy_lasers = []

        self.outpost_center = (MAP_WIDTH / 2 - 300, MAP_HEIGHT / 2 + 200)
        self.beacon = ExtractionBeacon(self.outpost_center[0], self.outpost_center[1])

        self.weapon_menu = AirStrikeWeaponMenu(1280, 720)
        self.reticle = AimingReticle()
        self.supply_cooldown = 0.0

        # Helldiver Strategic Air Strike Call-In Request
        self.active_callout = None
        self.callout_timer = 20.0  # First callout triggers after 20 seconds

        self.objective_phase = "DEFEND"
        self.danger_alert_timer = 0
        self.danger_alert_text = ""
        self.floating_popups = []

        self.flawless_protection = True
        self.total_cas_kills = 0
        self.survivors_count = HELLDIVER_COUNT

        self._spawn_world()

    def _spawn_world(self):
        cx, cy = self.outpost_center

        # 1. Friendly Helldivers
        self.units.clear()
        for i in range(HELLDIVER_COUNT):
            ox = cx + (i - 1.5) * 35.0
            oy = cy + random.uniform(-20, 20)
            self.units.append(HelldiverUnit(i, ox, oy))

        # 2. Friendly Outpost Obstacles
        self.obstacles.clear()
        self.obstacles.append(GroundObstacle(cx - 90, cy - 70, 70, 45, "bunker"))
        self.obstacles.append(GroundObstacle(cx + 40, cy - 65, 55, 40, "bunker"))
        self.obstacles.append(GroundObstacle(cx - 30, cy - 90, 50, 22, "barricade"))
        self.obstacles.append(GroundObstacle(cx - 80, cy + 50, 45, 20, "barricade"))
        self.obstacles.append(GroundObstacle(cx + 60, cy + 45, 50, 20, "barricade"))
        self.obstacles.append(GroundObstacle(cx + 110, cy - 20, 24, 60, "relay"))

        # 3. Enemy Ground Fabricators & Initial Ground Forces
        self.enemy_fabricators.clear()
        self.enemy_ground_units.clear()

        # Enemy fabricator camp ~700px northeast of Helldivers
        fab_x = cx + 650.0
        fab_y = cy - 400.0
        self.enemy_fabricators.append(EnemyFabricator(fab_x, fab_y))

        # Initial enemy ground wave
        for j in range(4):
            ex = fab_x + (j - 1.5) * 30.0
            ey = fab_y + 80.0 + random.uniform(-10, 10)
            self.enemy_ground_units.append(EnemyGroundUnit(EnemyGroundUnit.TYPE_TROOPER, ex, ey))
        self.enemy_ground_units.append(EnemyGroundUnit(EnemyGroundUnit.TYPE_WALKER, fab_x + 30.0, fab_y + 110.0))

    def reset(self):
        self._spawn_world()
        self.active_strikes.clear()
        self.supply_pods.clear()
        self.bullets.clear()
        self.enemy_lasers.clear()
        self.floating_popups.clear()
        self.supply_cooldown = 0.0
        self.objective_phase = "DEFEND"
        self.flawless_protection = True
        self.total_cas_kills = 0
        self.survivors_count = HELLDIVER_COUNT
        self.beacon = ExtractionBeacon(self.outpost_center[0], self.outpost_center[1])
        self.weapon_menu = AirStrikeWeaponMenu(1280, 720)
        self.active_callout = None
        self.callout_timer = 20.0

    def trigger_air_strike(self, player):
        """Fires the selected Air Strike at the predicted impact coordinates."""
        if not self.weapon_menu.is_ready():
            return False

        ix, iy = self.reticle.calculate_strike_impact(player)
        tx = max(100, min(MAP_WIDTH - 100, ix))
        ty = max(100, min(MAP_HEIGHT - 100, iy))

        # Check if deployed on a Helldiver requested strike beacon
        if self.active_callout and self.active_callout.active and not self.active_callout.delivered:
            d_to_callout = math.hypot(tx - self.active_callout.target_x, ty - self.active_callout.target_y)
            if d_to_callout <= self.active_callout.radius + 80.0:
                self.active_callout.delivered = True
                self.active_callout.active = False
                player.score += SCORE_MISSION_DELIVERY_BONUS
                self.add_combat_popup(f"SQUAD CAS DELIVERED! +{SCORE_MISSION_DELIVERY_BONUS}", tx, ty, (0, 255, 180))

        if self.weapon_menu.trigger_strike():
            strike = ActiveAirStrike(self.weapon_menu.selected_type, tx, ty, player.angle)
            self.active_strikes.append(strike)
            self.add_combat_popup("STRATAGEM DEPLOYED", tx, ty, (255, 215, 0))
            return True
        return False

    def trigger_supply_drop(self, player):
        if self.supply_cooldown > 0:
            return False

        self.supply_cooldown = COOLDOWN_SUPPLY_DROP
        living = [u for u in self.units if u.is_alive]
        if living:
            sx = sum(u.pos_x for u in living) / len(living)
            sy = sum(u.pos_y for u in living) / len(living)
        else:
            sx, sy = player.pos_x, player.pos_y

        self.supply_pods.append(SupplyDropPod(sx + random.uniform(-30, 30), sy + random.uniform(-30, 30)))
        self.add_combat_popup("SUPPLY POD CALLED", sx, sy, (0, 220, 255))
        return True

    def add_combat_popup(self, text, x, y, color=(255, 255, 255)):
        self.floating_popups.append({
            "text": text,
            "x": float(x),
            "y": float(y),
            "color": color,
            "timer": 1.4,
        })

    def update(self, dt, player, enemies, explosion_group, frames):
        self.weapon_menu.update(dt)
        if self.supply_cooldown > 0:
            self.supply_cooldown = max(0.0, self.supply_cooldown - dt)

        living_units = [u for u in self.units if u.is_alive]
        self.survivors_count = len(living_units)

        if living_units:
            squad_cx = sum(u.pos_x for u in living_units) / len(living_units)
            squad_cy = sum(u.pos_y for u in living_units) / len(living_units)
        else:
            squad_cx, squad_cy = self.outpost_center
            if self.objective_phase != "FAILED":
                self.objective_phase = "FAILED"
                self.flawless_protection = False
                player.score = max(0, player.score - SCORE_CASUALTY_PENALTY)
                self.add_combat_popup("ALLIED SQUAD ELIMINATED! -250", player.pos_x, player.pos_y, (255, 60, 60))

        # Check Helldiver Tactical Air Strike Call-in Mission Generation
        if self.active_callout:
            self.active_callout.update(dt)
            if not self.active_callout.active:
                self.active_callout = None
        else:
            self.callout_timer -= dt
            # Trigger callout when timer elapses and there are enemy ground forces
            living_ge = [ge for ge in self.enemy_ground_units if ge.is_alive]
            if self.callout_timer <= 0 and (living_ge or len(self.enemy_fabricators) > 0):
                self.callout_timer = 40.0
                # Choose target coordinate near enemy cluster
                if living_ge:
                    target_ge = living_ge[0]
                    cx, cy = target_ge.pos_x + target_ge.width / 2, target_ge.pos_y + target_ge.height / 2
                else:
                    fab = self.enemy_fabricators[0]
                    cx, cy = fab.pos_x + fab.width / 2, fab.pos_y + fab.height / 2

                # Helldivers request an appropriate strike (500kg, Napalm, Cluster, Strafe, Gas, Rockets)
                candidate_types = [
                    AirStrikeType.BOMB_500KG,
                    AirStrikeType.NAPALM,
                    AirStrikeType.CLUSTER,
                    AirStrikeType.STRAFE,
                    AirStrikeType.GAS,
                    AirStrikeType.ROCKETS,
                ]
                req_type = random.choice(candidate_types)
                self.active_callout = SquadAirStrikeRequest(cx, cy, req_type)
                # Auto-prepare strike in player weapon menu for rapid deployment
                self.weapon_menu.select(req_type)
                self.weapon_menu.cooldowns[req_type] = 0.0
                self.add_combat_popup(f"SQUAD CALLING IN {AirStrikeType.DATA[req_type]['name'].upper()}!", squad_cx, squad_cy, (255, 60, 40))

        # Extraction Beacon
        self.beacon.update(dt)
        if self.beacon.pelican_departed and self.objective_phase != "COMPLETE":
            self.objective_phase = "COMPLETE"
            bonus = SCORE_EXTRACTION_BONUS
            if self.flawless_protection:
                bonus = int(bonus * SCORE_FLAWLESS_MULTIPLIER)
            player.score += bonus
            self.add_combat_popup(f"EXTRACTION COMPLETE! +{bonus}", player.pos_x, player.pos_y, (0, 255, 180))

        # Update Helldivers AI (engages aerial and enemy ground units)
        for unit in self.units:
            prev_alive = unit.is_alive
            unit.update_ai(dt, (squad_cx, squad_cy), enemies, self.obstacles, self.bullets, self.supply_pods, self.beacon, self.enemy_ground_units)
            if prev_alive and not unit.is_alive:
                self.flawless_protection = False
                player.score = max(0, player.score - SCORE_CASUALTY_PENALTY)
                self.add_combat_popup(f"CASUALTY: {unit.callsign} KIA!", unit.pos_x, unit.pos_y, (255, 75, 75))

        # Update Enemy Fabricators
        for fab in self.enemy_fabricators:
            fab.update(dt, self.enemy_ground_units)

        # Update Enemy Ground Units (Troopers & Walkers)
        for ge in self.enemy_ground_units:
            ge.update(dt, self.units, self.enemy_lasers)

        # Update Enemy Lasers
        for laser in self.enemy_lasers:
            laser.update()
            if not laser.used:
                # Check hits against Helldivers
                for unit in self.units:
                    if unit.is_alive and laser.colliderect(pygame.Rect(int(unit.pos_x), int(unit.pos_y), unit.width, unit.height)):
                        laser.used = True
                        unit.take_damage(laser.damage)
                        break
                # Check hits against player
                if not laser.used and player and getattr(player, 'health', 0) > 0:
                    if laser.colliderect(player):
                        laser.used = True
                        player.take_damage(laser.damage)

        self.enemy_lasers = [l for l in self.enemy_lasers if not l.used and 0 <= l.x <= MAP_WIDTH and 0 <= l.y <= MAP_HEIGHT]

        # Update Helldiver Bullets (damage aerial hostiles and ground enemies)
        for b in self.bullets:
            b.update()
            if not b.used:
                # Ground enemy hit
                for ge in self.enemy_ground_units:
                    if ge.is_alive and b.colliderect(ge):
                        b.used = True
                        ge.take_damage(b.damage)
                        break
                # Aerial enemy hit
                if not b.used:
                    for enemy in enemies:
                        if not getattr(enemy, 'exploding', False) and getattr(enemy, 'health', 0) > 0:
                            if b.colliderect(enemy):
                                b.used = True
                                enemy.health -= b.damage
                                break

        self.bullets = [b for b in self.bullets if not b.used and 0 <= b.x <= MAP_WIDTH and 0 <= b.y <= MAP_HEIGHT]

        # Update Supply Pods
        for pod in self.supply_pods:
            pod.update(dt)
            if pod.landed and not pod.used:
                for unit in self.units:
                    if unit.is_alive and math.hypot(unit.pos_x - pod.x, unit.pos_y - pod.y) <= 45.0:
                        unit.heal(60.0)

                if math.hypot(player.pos_x + 18 - pod.x, player.pos_y + 18 - pod.y) <= 60.0:
                    player.used_bullets = 0
                    player.used_rockets = 0
                    player.health = min(player.max_health, player.health + 2)
                    player.shield = min(player.max_shield, player.shield + 10.0)
                    self.add_combat_popup("RESUPPLY COMPLETE!", player.pos_x, player.pos_y, (0, 255, 180))

        self.supply_pods = [p for p in self.supply_pods if not p.used]

        # Update Active Air Strikes (damages aerial hostiles AND enemy ground units/fabricators)
        all_ground_targets = list(self.enemy_ground_units) + list(self.enemy_fabricators)

        def on_strike_kill(target, weapon_name):
            val = getattr(target, 'score_value', 25)
            player.score += val
            self.total_cas_kills += 1
            tx = getattr(target, 'x', getattr(target, 'pos_x', 0))
            ty = getattr(target, 'y', getattr(target, 'pos_y', 0))
            self.add_combat_popup(f"{weapon_name} KILL +{val}", tx, ty, (255, 200, 50))

        for strike in self.active_strikes:
            strike.update(dt, enemies, all_ground_targets, explosion_group, frames, score_callback=on_strike_kill)

        self.active_strikes = [s for s in self.active_strikes if not s.finished]

        # Clean destroyed ground enemies and fabricators with explosions
        for ge in list(self.enemy_ground_units):
            if not ge.is_alive:
                self.enemy_ground_units.remove(ge)
                if explosion_group and frames:
                    from main import Large_explosion_a
                    explosion_group.add(Large_explosion_a(ge.pos_x + ge.width / 2, ge.pos_y + ge.height / 2, frames, speed=0.6))

        for fab in list(self.enemy_fabricators):
            if not fab.is_alive:
                self.enemy_fabricators.remove(fab)
                player.score += 150
                self.add_combat_popup("FABRICATOR DESTROYED! +150", fab.pos_x, fab.pos_y, (255, 140, 40))
                if explosion_group and frames:
                    from main import Large_explosion_a
                    for _ in range(3):
                        explosion_group.add(Large_explosion_a(
                            fab.pos_x + random.uniform(10, fab.width - 10),
                            fab.pos_y + random.uniform(10, fab.height - 10),
                            frames, speed=0.4
                        ))

        # Danger Zone Alert Detection (tracks aerial and ground threats near squad)
        threat_count = 0
        for enemy in enemies:
            if not getattr(enemy, 'exploding', False) and getattr(enemy, 'health', 0) > 0:
                if math.hypot(enemy.x + 18 - squad_cx, enemy.y + 18 - squad_cy) <= DANGER_ALERT_RADIUS:
                    threat_count += 1
        for ge in self.enemy_ground_units:
            if ge.is_alive and math.hypot(ge.pos_x - squad_cx, ge.pos_y - squad_cy) <= DANGER_ALERT_RADIUS:
                threat_count += 1

        if threat_count > 0:
            self.danger_alert_timer = 90
            self.danger_alert_text = f"DANGER: {threat_count} HOSTILES CLOSING ON SQUAD!"
        elif self.danger_alert_timer > 0:
            self.danger_alert_timer -= 1

        for pop in self.floating_popups:
            pop["timer"] -= dt
            pop["y"] -= 22.0 * dt
        self.floating_popups = [p for p in self.floating_popups if p["timer"] > 0]

    def on_player_kill_enemy(self, enemy, player):
        living = [u for u in self.units if u.is_alive]
        if not living:
            return
        ex = getattr(enemy, 'x', getattr(enemy, 'pos_x', 0)) + 18
        ey = getattr(enemy, 'y', getattr(enemy, 'pos_y', 0)) + 18
        near_ally = any(math.hypot(ex - u.pos_x, ey - u.pos_y) <= 420.0 for u in living)
        if near_ally:
            bonus = SCORE_CAS_KILL_BONUS
            player.score += bonus
            self.total_cas_kills += 1
            self.add_combat_popup(f"CLOSE AIR SUPPORT! +{bonus}", ex, ey, (0, 255, 180))

    def on_wave_cleared(self, wave_num, player):
        living_count = len([u for u in self.units if u.is_alive])
        if living_count > 0:
            survivor_bonus = living_count * SCORE_SURVIVOR_WAVE_BONUS
            if self.flawless_protection:
                survivor_bonus = int(survivor_bonus * SCORE_FLAWLESS_MULTIPLIER)
            player.score += survivor_bonus
            self.add_combat_popup(f"SQUAD SURVIVAL BONUS! +{survivor_bonus}", player.pos_x, player.pos_y, (255, 215, 0))

        if wave_num >= 3 and not self.beacon.active:
            self.beacon.activate()
            self.objective_phase = "EXTRACTION"
            self.add_combat_popup("EXTRACTION BEACON ACTIVATED!", self.beacon.x, self.beacon.y, (0, 220, 255))

    def draw_world_entities(self, surface, camera_x, camera_y, font):
        for obs in self.obstacles:
            obs.draw(surface, camera_x, camera_y)

        self.beacon.draw(surface, camera_x, camera_y)

        for fab in self.enemy_fabricators:
            fab.draw(surface, camera_x, camera_y)

        for ge in self.enemy_ground_units:
            ge.draw(surface, camera_x, camera_y)

        for unit in self.units:
            unit.draw(surface, camera_x, camera_y, font)

        for pod in self.supply_pods:
            pod.draw(surface, camera_x, camera_y)

        for laser in self.enemy_lasers:
            laser.draw(surface, camera_x, camera_y)

        for b in self.bullets:
            b.draw(surface, camera_x, camera_y)

        if self.active_callout:
            self.active_callout.draw(surface, camera_x, camera_y, font)

        for strike in self.active_strikes:
            strike.draw(surface, camera_x, camera_y)

        for pop in self.floating_popups:
            sx = pop["x"] - camera_x
            sy = pop["y"] - camera_y
            if -50 <= sx <= 1330 and -50 <= sy <= 770:
                txt = font.render(pop["text"], True, pop["color"])
                surface.blit(txt, (sx - txt.get_width() // 2, sy))

    def draw_reticle(self, surface, camera_x, camera_y, player):
        """Draws the predictive gun and bomb impact aiming reticle ahead of the ship."""
        ix, iy = self.reticle.calculate_strike_impact(player)

        # Check target lock (is bomb reticle over enemy ground units, fabricator, or callout beacon?)
        is_locked = False
        if self.active_callout and self.active_callout.active:
            if math.hypot(ix - self.active_callout.target_x, iy - self.active_callout.target_y) <= self.active_callout.radius + 60.0:
                is_locked = True
        if not is_locked:
            for ge in self.enemy_ground_units:
                if ge.is_alive and math.hypot(ix - (ge.pos_x + ge.width / 2), iy - (ge.pos_y + ge.height / 2)) <= 70.0:
                    is_locked = True
                    break
        if not is_locked:
            for fab in self.enemy_fabricators:
                if fab.is_alive and math.hypot(ix - (fab.pos_x + fab.width / 2), iy - (fab.pos_y + fab.height / 2)) <= 80.0:
                    is_locked = True
                    break

        self.reticle.draw(surface, camera_x, camera_y, player, self.weapon_menu.selected_type, is_target_locked=is_locked)

    def draw_minimap(self, minimap_surface, scale):
        bx = int(self.beacon.x * scale)
        by = int(self.beacon.y * scale)
        br = max(3, int(self.beacon.radius * scale))
        zone_col = (0, 220, 255) if not self.beacon.active else (255, 180, 0)
        pygame.draw.circle(minimap_surface, zone_col, (bx, by), br, 1)

        # Enemy Fabricators (Red Squares)
        for fab in self.enemy_fabricators:
            if fab.is_alive:
                fx = int(fab.pos_x * scale)
                fy = int(fab.pos_y * scale)
                pygame.draw.rect(minimap_surface, (255, 40, 40), (fx, fy, 4, 4))

        # Enemy Ground Units (Red Dots)
        for ge in self.enemy_ground_units:
            if ge.is_alive:
                gx = int(ge.pos_x * scale)
                gy = int(ge.pos_y * scale)
                pygame.draw.circle(minimap_surface, (255, 60, 60), (gx, gy), 2)

        # Helldivers (Cyan Dots)
        for unit in self.units:
            if unit.is_alive and unit.state != "EXTRACTED":
                ux = int(unit.pos_x * scale)
                uy = int(unit.pos_y * scale)
                pygame.draw.circle(minimap_surface, (0, 240, 255), (ux, uy), 3)

        # Active Callout Beacon (Flashing Yellow/Red)
        if self.active_callout and self.active_callout.active:
            cx = int(self.active_callout.target_x * scale)
            cy = int(self.active_callout.target_y * scale)
            pulse = int(5 + 3 * math.sin(pygame.time.get_ticks() * 0.02))
            pygame.draw.circle(minimap_surface, (255, 220, 40), (cx, cy), pulse, 1)

        # Supply Pods
        for pod in self.supply_pods:
            if not pod.used:
                px = int(pod.x * scale)
                py = int(pod.y * scale)
                pygame.draw.circle(minimap_surface, (0, 255, 120), (px, py), 2)

        # Danger zone pulse
        if self.danger_alert_timer > 0:
            pulse = int(14 + 6 * math.sin(pygame.time.get_ticks() * 0.02))
            living = [u for u in self.units if u.is_alive]
            if living:
                cx = int((sum(u.pos_x for u in living) / len(living)) * scale)
                cy = int((sum(u.pos_y for u in living) / len(living)) * scale)
                pygame.draw.circle(minimap_surface, (255, 40, 40), (cx, cy), pulse, 1)

    def draw_hud(self, surface, screen_w, screen_h, font, font_title, font_sub, font_small, player, mouse_pos=None):
        # 1. Squad Status Panel
        panel_x = 65
        panel_y = 76
        panel_w = 205
        panel_h = 74
        pygame.draw.rect(surface, (14, 20, 32), (panel_x, panel_y, panel_w, panel_h), border_radius=6)
        pygame.draw.rect(surface, (50, 75, 110), (panel_x, panel_y, panel_w, panel_h), 1, border_radius=6)

        header_str = f"HELLDIVERS: {self.survivors_count}/{HELLDIVER_COUNT} ALIVE"
        header_col = (0, 220, 255) if self.survivors_count > 0 else (255, 70, 70)
        header_lbl = font_small.render(header_str, True, header_col)
        surface.blit(header_lbl, (panel_x + 8, panel_y + 4))

        row_y = panel_y + 20
        for i, unit in enumerate(self.units):
            ux = panel_x + 8 + (i % 2) * 96
            uy = row_y + (i // 2) * 24
            name_txt = font_small.render(f"V{i+1}:", True, (180, 200, 220))
            surface.blit(name_txt, (ux, uy))

            bar_w = 58
            bar_h = 5
            bx = ux + 24
            by = uy + 4
            pygame.draw.rect(surface, (20, 25, 38), (bx, by, bar_w, bar_h))
            if unit.is_alive:
                hp_w = max(0, int((unit.health / unit.max_health) * bar_w))
                hp_col = (46, 204, 113) if unit.health > 50 else (241, 196, 15)
                pygame.draw.rect(surface, hp_col, (bx, by, hp_w, bar_h))
            else:
                kia_txt = font_small.render("K.I.A.", True, (255, 75, 75))
                surface.blit(kia_txt, (bx, by - 3))

        # 2. Objective Status Banner
        obj_y = 66
        if self.active_callout and self.active_callout.active:
            req_name = self.active_callout.data["name"].upper()
            rem = int(self.active_callout.lifetime)
            obj_str = f"SQUAD CAS REQUEST: {req_name} ({rem:02d}s) - DEPLOY [C]!"
            obj_col = (255, 215, 0)
        elif self.beacon.active and not self.beacon.pelican_departed:
            rem = int(self.beacon.countdown)
            obj_str = f"EXTRACTION PELICAN INBOUND: {rem:02d}s" if rem > 0 else "PELICAN-1 LANDED - BOARD SHUTTLE!"
            obj_col = (255, 200, 50) if rem > 0 else (0, 255, 180)
        elif self.objective_phase == "FAILED":
            obj_str = "OBJECTIVE FAILED: ALL ALLIES ELIMINATED"
            obj_col = (255, 70, 70)
        else:
            obj_str = "OBJECTIVE: DEFEND OUTPOST & ELIMINATE ENEMY GROUND FORCES"
            obj_col = (0, 220, 255)

        obj_txt = font_small.render(obj_str, True, obj_col)
        surface.blit(obj_txt, (screen_w // 2 - obj_txt.get_width() // 2, obj_y))

        # 3. Off-Screen Compass Pointer to Active Callout or Squad
        target_point = None
        target_tag = "SQUAD"
        if self.active_callout and self.active_callout.active:
            target_point = (self.active_callout.target_x, self.active_callout.target_y)
            target_tag = "CAS TARGET"
        else:
            living = [u for u in self.units if u.is_alive]
            if living:
                target_point = (sum(u.pos_x for u in living) / len(living), sum(u.pos_y for u in living) / len(living))

        if target_point:
            scx, scy = target_point
            camera_x = max(0, min(MAP_WIDTH - screen_w, player.pos_x + 18 - screen_w / 2))
            camera_y = max(0, min(MAP_HEIGHT - screen_h, player.pos_y + 18 - screen_h / 2))
            screen_scx = scx - camera_x
            screen_scy = scy - camera_y

            margin = 55
            if not (margin <= screen_scx <= screen_w - margin and margin <= screen_scy <= screen_h - margin):
                arrow_cx = max(margin, min(screen_w - margin, screen_scx))
                arrow_cy = max(margin, min(screen_h - margin, screen_scy))
                angle_to_tgt = math.atan2(scy - (player.pos_y + 18), scx - (player.pos_x + 18))

                arrow_len = 16
                arrow_col = (255, 215, 0) if target_tag == "CAS TARGET" else (0, 220, 255)
                p1 = (arrow_cx + math.cos(angle_to_tgt) * arrow_len, arrow_cy + math.sin(angle_to_tgt) * arrow_len)
                p2 = (arrow_cx + math.cos(angle_to_tgt + 2.5) * (arrow_len * 0.6), arrow_cy + math.sin(angle_to_tgt + 2.5) * (arrow_len * 0.6))
                p3 = (arrow_cx + math.cos(angle_to_tgt - 2.5) * (arrow_len * 0.6), arrow_cy + math.sin(angle_to_tgt - 2.5) * (arrow_len * 0.6))
                pygame.draw.polygon(surface, arrow_col, [p1, p2, p3])

                dist_m = int(math.hypot(scx - player.pos_x, scy - player.pos_y) / 10.0)
                dist_txt = font_small.render(f"{target_tag} {dist_m}m", True, arrow_col)
                surface.blit(dist_txt, (arrow_cx - dist_txt.get_width() // 2, arrow_cy + 10))

        # 4. Danger Alert Warning Banner
        if self.danger_alert_timer > 0:
            banner_w = 440
            banner_h = 28
            bx = screen_w // 2 - banner_w // 2
            by = 88
            pulse = int(180 + 75 * math.sin(pygame.time.get_ticks() * 0.015))
            pygame.draw.rect(surface, (65, 15, 15), (bx, by, banner_w, banner_h), border_radius=4)
            pygame.draw.rect(surface, (255, 60, 60), (bx, by, banner_w, banner_h), 1, border_radius=4)
            alert_lbl = font_small.render(f"⚠️  {self.danger_alert_text}  ⚠️", True, (255, pulse, pulse))
            surface.blit(alert_lbl, (screen_w // 2 - alert_lbl.get_width() // 2, by + 6))

        # 5. Stratagem Quickbar
        qb_x = screen_w - 280
        qb_y = screen_h - 130
        self.weapon_menu.draw_hud_quickbar(surface, qb_x, qb_y, font_sub, font_small)

        supply_ready = (self.supply_cooldown <= 0)
        sup_col = (0, 220, 255) if supply_ready else (160, 175, 190)
        sup_str = "[X] Resupply Pod (READY)" if supply_ready else f"[X] Resupply ({self.supply_cooldown:.1f}s)"
        sup_txt = font_small.render(sup_str, True, sup_col)
        surface.blit(sup_txt, (qb_x + 8, qb_y + 60))

        # 6. Weapon Menu (if open)
        self.weapon_menu.draw(surface, mouse_pos, font_title, font_sub, font, font_small)
