import pygame
import math
import random
import os

# =====================================================================
# POWER-UP SYSTEM CONFIGURATION CONSTANTS
# Easily accessible tuning parameters
# =====================================================================

# Drop & Spawn Probabilities
POWERUP_DROP_BASE_CHANCE = 0.08         # 8% base drop chance on enemy kill
POWERUP_PITY_INCREMENT = 0.03           # +3% chance per kill without drop
POWERUP_LIFETIME_SECONDS = 12.0         # Seconds before a dropped item despawns
POWERUP_MAGNET_RADIUS = 130.0           # Proximity range in pixels for magnetic pull
POWERUP_MAGNET_SPEED = 320.0            # Max magnetic pull velocity towards player

# Rarity Distribution (Must sum to 1.0)
RARITY_COMMON_WEIGHT = 0.70             # 70% Common
RARITY_RARE_WEIGHT = 0.20               # 20% Rare
RARITY_EPIC_WEIGHT = 0.10               # 10% Epic

# Score Milestones for Guaranteed Tactical Airdrops
SCORE_MILESTONE_THRESHOLDS = [1000, 5000, 10000, 25000, 50000]

# Ability Durations (Seconds)
DURATION_RAPID_FIRE = 10.0
DURATION_SHIELD_BUBBLE = 10.0
DURATION_THRUSTER_BOOST = 10.0
DURATION_TIME_SLOW = 8.0
DURATION_FREEZE_BLAST = 10.0
DURATION_DAMAGE_BOOST = 10.0
DURATION_DRONE_COMPANION = 20.0
DURATION_HOMING_PODS = 12.0

# Combat & Stat Balancing Numbers
HOMING_POD_DAMAGE = 2.0                 # Rocket damage per micro-missile (clarified by user)
SHIELD_BUBBLE_BONUS = 15.0              # Temporary bonus shield added on pickup
DAMAGE_BOOST_MULTIPLIER = 2             # Bullet damage multiplier (1 -> 2)
RAPID_FIRE_COOLDOWN_MS = 50             # Firing delay during Rapid Fire (halved from 100ms)
RAPID_FIRE_RELOAD_MS = 3000             # Reload delay during Rapid Fire (cut from 5000ms)

THRUSTER_MAX_SPEED = 11.0               # Boosted max speed (normal: 7.0)
THRUSTER_ACCELERATION = 0.25            # Boosted acceleration (normal: 0.15)
THRUSTER_TURN_RATE = 4.5                # Boosted turn rate (normal: 3.0)

TIME_SLOW_FACTOR = 0.5                  # Speed factor applied to enemies and enemy bullets
FREEZE_SLOW_FACTOR = 0.4                # Speed factor when enemy is frosted
FREEZE_DURATION_SEC = 1.5               # Seconds enemy is completely frozen after 3 hits


# =====================================================================
# ABILITY DEFINITIONS & RARITY TIERS
# =====================================================================

class Rarity:
    COMMON = "Common"
    RARE = "Rare"
    EPIC = "Epic"

    COLORS = {
        COMMON: (46, 204, 113),    # Emerald Green
        RARE: (52, 152, 219),      # Sky Blue
        EPIC: (155, 89, 182),      # Royal Purple
    }

    RADAR_COLORS = {
        COMMON: (50, 220, 120),
        RARE: (70, 180, 255),
        EPIC: (200, 100, 255),
    }


ABILITIES = {
    # Common
    "rapid_fire": {
        "name": "Rapid Fire",
        "category": "Offensive",
        "rarity": Rarity.COMMON,
        "duration": DURATION_RAPID_FIRE,
        "symbol": "RF",
        "desc": "Fire rate doubled, reload time reduced by 40%",
    },
    "shield_bubble": {
        "name": "Shield Bubble",
        "category": "Defensive",
        "rarity": Rarity.COMMON,
        "duration": DURATION_SHIELD_BUBBLE,
        "symbol": "SB",
        "desc": "+15 Overcharge Shield & doubled regeneration speed",
    },
    "thruster_boost": {
        "name": "Thruster Overdrive",
        "category": "Utility",
        "rarity": Rarity.COMMON,
        "duration": DURATION_THRUSTER_BOOST,
        "symbol": "TO",
        "desc": "+33% Max Speed, +66% Accel, +50% Turn Rate",
    },

    # Rare
    "time_slow": {
        "name": "Chrono Slip",
        "category": "Utility",
        "rarity": Rarity.RARE,
        "duration": DURATION_TIME_SLOW,
        "symbol": "CS",
        "desc": "Dilates time: enemies & enemy bullets slowed by 50%",
    },
    "freeze_blast": {
        "name": "Cryo Frostbite",
        "category": "Utility/Offensive",
        "rarity": Rarity.RARE,
        "duration": DURATION_FREEZE_BLAST,
        "symbol": "CF",
        "desc": "Rounds slow enemy by 60%; 3 hits freeze enemy solid",
    },
    "damage_boost": {
        "name": "Damage Multiplier",
        "category": "Offensive",
        "rarity": Rarity.RARE,
        "duration": DURATION_DAMAGE_BOOST,
        "symbol": "DM",
        "desc": "Doubles main cannon bullet damage (1 -> 2)",
    },

    # Epic
    "drone_companion": {
        "name": "Vanguard Drone",
        "category": "Defensive/Offensive",
        "rarity": Rarity.EPIC,
        "duration": DURATION_DRONE_COMPANION,
        "symbol": "VD",
        "desc": "Autonomous escort drone intercepts fire & shoots lasers",
    },
    "homing_pods": {
        "name": "Swarm Homing Pods",
        "category": "Offensive",
        "rarity": Rarity.EPIC,
        "duration": DURATION_HOMING_PODS,
        "symbol": "HP",
        "desc": "Fires self-guided micro-missiles (2.0 damage)",
    },
}

COMMON_ABILITIES = [k for k, v in ABILITIES.items() if v["rarity"] == Rarity.COMMON]
RARE_ABILITIES = [k for k, v in ABILITIES.items() if v["rarity"] == Rarity.RARE]
EPIC_ABILITIES = [k for k, v in ABILITIES.items() if v["rarity"] == Rarity.EPIC]


# =====================================================================
# ENTITY CLASSES
# =====================================================================

class PowerUpDrop:
    """A floating, collectible power-up entity in the game world."""
    def __init__(self, x, y, ability_id):
        self.x = float(x)
        self.y = float(y)
        self.vx = random.uniform(-0.8, 0.8)
        self.vy = random.uniform(-0.8, 0.8)
        self.ability_id = ability_id
        self.info = ABILITIES[ability_id]
        self.rarity = self.info["rarity"]
        self.color = Rarity.COLORS[self.rarity]
        self.lifetime = POWERUP_LIFETIME_SECONDS
        self.radius = 16
        self.bob_timer = random.uniform(0, 6.28)
        self.picked_up = False

    def update(self, dt, player_x, player_y):
        self.lifetime -= dt
        self.bob_timer += dt * 4.0

        # Proximity magnetic attraction towards player
        dx = (player_x + 24) - self.x
        dy = (player_y + 30) - self.y
        dist = math.hypot(dx, dy)

        if 0 < dist < POWERUP_MAGNET_RADIUS:
            factor = (1.0 - (dist / POWERUP_MAGNET_RADIUS))
            pull_speed = POWERUP_MAGNET_SPEED * factor
            self.vx += (dx / dist) * pull_speed * dt
            self.vy += (dy / dist) * pull_speed * dt

        # Apply velocity with subtle dampening
        self.x += self.vx
        self.y += self.vy
        self.vx *= 0.94
        self.vy *= 0.94

        return self.lifetime > 0 and not self.picked_up

    def get_rect(self):
        return pygame.Rect(int(self.x - self.radius), int(self.y - self.radius), self.radius * 2, self.radius * 2)

    def draw(self, surface, camera_x, camera_y, font):
        screen_x = self.x - camera_x
        screen_y = self.y - camera_y

        # Do not render if far outside viewport
        if screen_x < -50 or screen_x > surface.get_width() + 50 or \
           screen_y < -50 or screen_y > surface.get_height() + 50:
            return

        # Despawn blinking effect in last 3 seconds
        if self.lifetime < 3.0:
            blink_freq = 15.0 if self.lifetime < 1.0 else 8.0
            if int(self.lifetime * blink_freq) % 2 == 0:
                return

        # Floating vertical oscillation
        draw_y = screen_y + math.sin(self.bob_timer) * 3.5

        # Outer pulsing glow halo
        pulse = (math.sin(self.bob_timer * 2.0) + 1.0) * 0.5  # 0 to 1
        glow_radius = int(self.radius + 4 + pulse * 4)
        glow_surf = pygame.Surface((glow_radius * 2, glow_radius * 2), pygame.SRCALPHA)
        glow_alpha = int(70 + pulse * 60)
        glow_color = (*self.color, glow_alpha)
        pygame.draw.circle(glow_surf, glow_color, (glow_radius, glow_radius), glow_radius)
        surface.blit(glow_surf, (int(screen_x - glow_radius), int(draw_y - glow_radius)))

        # Inner solid base orb
        pygame.draw.circle(surface, (20, 25, 35), (int(screen_x), int(draw_y)), self.radius)
        pygame.draw.circle(surface, self.color, (int(screen_x), int(draw_y)), self.radius, 2)

        # Centered symbol text
        sym_text = font.render(self.info["symbol"], True, (255, 255, 255))
        sym_rect = sym_text.get_rect(center=(int(screen_x), int(draw_y)))
        surface.blit(sym_text, sym_rect)


class DroneCompanion:
    """An autonomous escort drone orbiting Eagle-1."""
    def __init__(self, orbit_radius=75.0):
        self.orbit_radius = orbit_radius
        self.angle = 0.0
        self.orbit_speed = 3.5  # rad/sec
        self.shoot_timer = 0.0
        self.shoot_interval = 0.75  # Fire every 0.75s
        self.bullets = []
        self.x = 0.0
        self.y = 0.0
        self.radius = 9

    def update(self, dt, player_cx, player_cy, enemy):
        self.angle += self.orbit_speed * dt
        self.x = player_cx + math.cos(self.angle) * self.orbit_radius
        self.y = player_cy + math.sin(self.angle) * self.orbit_radius

        # Intercept incoming enemy bullets within proximity
        if enemy and hasattr(enemy, 'bullets'):
            for b in enemy.bullets:
                if not b.used:
                    b_dist = math.hypot((b.x + 4) - self.x, (b.y + 6) - self.y)
                    if b_dist < self.radius + 8:
                        b.used = True  # Drone shield absorbs the projectile!

        # Target enemy if alive
        self.shoot_timer += dt
        if self.shoot_timer >= self.shoot_interval and enemy and not getattr(enemy, 'exploding', False):
            self.shoot_timer = 0.0
            dx = (enemy.x + enemy.width / 2) - self.x
            dy = (enemy.y + enemy.height / 2) - self.y
            dist = math.hypot(dx, dy)
            if 0 < dist < 900:
                speed = 12.0
                vx = (dx / dist) * speed
                vy = (dy / dist) * speed
                self.bullets.append({
                    "x": self.x,
                    "y": self.y,
                    "vx": vx,
                    "vy": vy,
                    "used": False,
                    "lifetime": 2.0
                })

        # Update drone's active bullets
        for b in self.bullets:
            b["x"] += b["vx"]
            b["y"] += b["vy"]
            b["lifetime"] -= dt
            # Hit check against enemy
            if not b["used"] and enemy and not getattr(enemy, 'exploding', False):
                er = pygame.Rect(enemy.x, enemy.y, enemy.width, enemy.height)
                if er.collidepoint(b["x"], b["y"]):
                    b["used"] = True
                    enemy.health -= 1.0

        self.bullets = [b for b in self.bullets if not b["used"] and b["lifetime"] > 0]

    def draw(self, surface, camera_x, camera_y, player_cx, player_cy):
        sx = self.x - camera_x
        sy = self.y - camera_y
        pcx = player_cx - camera_x
        pcy = player_cy - camera_y

        # Draw holographic energy tether to player
        tether_surf = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        pygame.draw.line(tether_surf, (155, 89, 182, 90), (int(pcx), int(pcy)), (int(sx), int(sy)), 1)
        surface.blit(tether_surf, (0, 0))

        # Drone hull
        pygame.draw.circle(surface, (40, 45, 60), (int(sx), int(sy)), self.radius)
        pygame.draw.circle(surface, (155, 89, 182), (int(sx), int(sy)), self.radius, 2)
        pygame.draw.circle(surface, (230, 160, 255), (int(sx), int(sy)), 3)

        # Drone laser projectiles
        for b in self.bullets:
            bx = b["x"] - camera_x
            by = b["y"] - camera_y
            pygame.draw.circle(surface, (220, 120, 255), (int(bx), int(by)), 3)
            pygame.draw.circle(surface, (255, 255, 255), (int(bx), int(by)), 1)


class HomingMicroMissile:
    """Self-guided micro-rocket dealing HOMING_POD_DAMAGE (2.0)."""
    def __init__(self, x, y, angle):
        self.x = float(x)
        self.y = float(y)
        self.angle = angle  # degrees
        self.speed = 9.0
        self.turn_rate = 5.5  # degrees per frame
        self.damage = HOMING_POD_DAMAGE  # 2.0 damage as requested
        self.lifetime = 3.5  # seconds
        self.used = False
        self.trail = []

    def update(self, dt, enemy):
        self.lifetime -= dt
        if self.lifetime <= 0:
            self.used = True
            return

        # Acquire lock and steer towards enemy
        if enemy and not getattr(enemy, 'exploding', False):
            target_x = enemy.x + enemy.width / 2
            target_y = enemy.y + enemy.height / 2
            dx = target_x - self.x
            dy = target_y - self.y
            target_angle = math.degrees(math.atan2(-dx, -dy)) % 360

            # Smooth shortest angle turn
            diff = (target_angle - self.angle + 180) % 360 - 180
            if abs(diff) > self.turn_rate:
                self.angle += math.copysign(self.turn_rate, diff)
            else:
                self.angle = target_angle

        # Move forward along heading
        rad = math.radians(self.angle)
        self.x += -math.sin(rad) * self.speed
        self.y += -math.cos(rad) * self.speed

        # Save trail point
        self.trail.append((self.x, self.y))
        if len(self.trail) > 6:
            self.trail.pop(0)

        # Check collision with enemy
        if enemy and not getattr(enemy, 'exploding', False):
            er = pygame.Rect(enemy.x, enemy.y, enemy.width, enemy.height)
            if er.collidepoint(self.x, self.y):
                self.used = True
                enemy.health -= self.damage

    def draw(self, surface, camera_x, camera_y):
        if len(self.trail) > 1:
            points = [(tx - camera_x, ty - camera_y) for tx, ty in self.trail]
            pygame.draw.lines(surface, (255, 140, 40), False, points, 2)

        sx = self.x - camera_x
        sy = self.y - camera_y
        pygame.draw.circle(surface, (255, 230, 100), (int(sx), int(sy)), 3)
        pygame.draw.circle(surface, (255, 60, 20), (int(sx), int(sy)), 1)


# =====================================================================
# POWER-UP MANAGER
# Coordinates drops, buff active states, pity counter, milestones & HUD
# =====================================================================

class PowerUpManager:
    def __init__(self):
        self.drops = []
        self.active_buffs = {}        # {ability_id: time_remaining}
        self.pity_counter = 0
        self.achieved_milestones = set()
        self.drone = None
        self.homing_missiles = []
        self.homing_timer = 0.0

        # UI feedback elements
        self.floating_popups = []     # [{"text": str, "color": tuple, "timer": float, "y_off": float}]
        self.milestone_banner = None  # {"title": str, "sub": str, "timer": float}

        # Freeze enemy tracking state
        self.enemy_frost_timer = 0.0
        self.enemy_frost_hits = 0
        self.enemy_frozen_timer = 0.0

        # Lazy fonts
        self._font_small = None
        self._font_hud = None
        self._font_banner = None

    @property
    def font_small(self):
        if self._font_small is None:
            self._font_small = pygame.font.SysFont("arial", 13, bold=True)
        return self._font_small

    @property
    def font_hud(self):
        if self._font_hud is None:
            self._font_hud = pygame.font.SysFont("arial", 16, bold=True)
        return self._font_hud

    @property
    def font_banner(self):
        if self._font_banner is None:
            self._font_banner = pygame.font.SysFont("arial", 26, bold=True)
        return self._font_banner

    def is_active(self, ability_id):
        return ability_id in self.active_buffs and self.active_buffs[ability_id] > 0

    def get_remaining_time(self, ability_id):
        return self.active_buffs.get(ability_id, 0.0)

    # -----------------------------------------------------------------
    # Drop Rolling Logic with Pity Counter
    # -----------------------------------------------------------------
    def roll_drop(self, enemy_x, enemy_y):
        """Called when an enemy is killed. Rolls for drop with pity."""
        drop_chance = POWERUP_DROP_BASE_CHANCE + (self.pity_counter * POWERUP_PITY_INCREMENT)
        if random.random() < drop_chance:
            self.pity_counter = 0
            ability_id = self._select_random_ability()
            self.drops.append(PowerUpDrop(enemy_x, enemy_y, ability_id))
            return ability_id
        else:
            self.pity_counter += 1
            return None

    def _select_random_ability(self, min_rarity=None):
        """Rolls rarity based on configured weights, or respects min_rarity."""
        if min_rarity == Rarity.EPIC:
            return random.choice(EPIC_ABILITIES)
        elif min_rarity == Rarity.RARE:
            pool = RARE_ABILITIES + EPIC_ABILITIES
            return random.choice(pool)

        roll = random.random()
        if roll < RARITY_COMMON_WEIGHT:
            return random.choice(COMMON_ABILITIES)
        elif roll < (RARITY_COMMON_WEIGHT + RARITY_RARE_WEIGHT):
            return random.choice(RARE_ABILITIES)
        else:
            return random.choice(EPIC_ABILITIES)

    # -----------------------------------------------------------------
    # Milestone System
    # -----------------------------------------------------------------
    def check_milestones(self, current_score, player_x, player_y):
        """Checks score thresholds and triggers guaranteed tactical drops."""
        for m in SCORE_MILESTONE_THRESHOLDS:
            if current_score >= m and m not in self.achieved_milestones:
                self.achieved_milestones.add(m)
                self._trigger_milestone_airdrop(m, player_x, player_y)

    def _trigger_milestone_airdrop(self, threshold, player_x, player_y):
        """Spawns guaranteed tier airdrop near the player."""
        if threshold <= 1000:
            ability = random.choice(RARE_ABILITIES)
            tier_name = "TACTICAL SUPPLY DROP"
        elif threshold <= 5000:
            ability = random.choice(EPIC_ABILITIES)
            tier_name = "ELITE AIRDROP"
        else:
            ability = random.choice(EPIC_ABILITIES)
            tier_name = "VANGUARD REINFORCEMENTS"

        # Spawn within 120-160px radius around player
        offset_angle = random.uniform(0, 6.28)
        offset_dist = random.uniform(100, 150)
        spawn_x = player_x + math.cos(offset_angle) * offset_dist
        spawn_y = player_y + math.sin(offset_angle) * offset_dist

        self.drops.append(PowerUpDrop(spawn_x, spawn_y, ability))

        ability_name = ABILITIES[ability]["name"]
        self.milestone_banner = {
            "title": f"★ MILESTONE {threshold:,} PTS REACHED! ★",
            "sub": f"{tier_name}: {ability_name} INCOMING!",
            "timer": 4.0
        }

    # -----------------------------------------------------------------
    # Pickup Activation & Refresh Rules
    # -----------------------------------------------------------------
    def activate_pickup(self, player, ability_id):
        """Applies or refreshes a power-up on pickup."""
        info = ABILITIES[ability_id]
        duration = info["duration"]

        # Duration refresh rule (no infinite multiplying stacking)
        self.active_buffs[ability_id] = duration

        # Immediate effects
        if ability_id == "shield_bubble":
            # Temporary overcharge shield
            bonus_max = getattr(player, 'max_shield', 20) + SHIELD_BUBBLE_BONUS
            player.shield = min(bonus_max, player.shield + SHIELD_BUBBLE_BONUS)

        elif ability_id == "thruster_boost":
            player.max_speed = THRUSTER_MAX_SPEED
            player.acceleration = THRUSTER_ACCELERATION
            player.turn_rate = THRUSTER_TURN_RATE

        elif ability_id == "drone_companion":
            self.drone = DroneCompanion()

        # Visual popup notification
        self.floating_popups.append({
            "text": f"+ {info['name'].upper()} ({int(duration)}s)",
            "color": Rarity.COLORS[info["rarity"]],
            "timer": 2.2,
            "y_off": 0.0
        })

    def on_bullet_hit_enemy(self, enemy):
        """Handles on-hit debuffs like Cryo Frostbite."""
        if self.is_active("freeze_blast"):
            self.enemy_frost_timer = 3.0
            self.enemy_frost_hits += 1
            if self.enemy_frost_hits >= 3:
                self.enemy_frozen_timer = FREEZE_DURATION_SEC
                self.enemy_frost_hits = 0

    # -----------------------------------------------------------------
    # Main Per-Frame Update
    # -----------------------------------------------------------------
    def update(self, dt, player, enemy):
        # 1. Update active buff timers
        for buff in list(self.active_buffs.keys()):
            self.active_buffs[buff] -= dt
            if self.active_buffs[buff] <= 0:
                del self.active_buffs[buff]
                self._on_buff_expired(player, buff)

        # 2. Update power-up drops in world
        p_w = getattr(player, 'width', 48)
        p_h = getattr(player, 'height', 61)
        player_cx = player.pos_x + p_w / 2
        player_cy = player.pos_y + p_h / 2
        player_rect = pygame.Rect(int(player.pos_x), int(player.pos_y), p_w, p_h)

        for drop in self.drops:
            if drop.update(dt, player_cx, player_cy):
                # Check collision with player
                if player_rect.colliderect(drop.get_rect()):
                    drop.picked_up = True
                    self.activate_pickup(player, drop.ability_id)

        self.drops = [d for d in self.drops if not d.picked_up and d.lifetime > 0]

        # 3. Update Swarm Homing Pods firing
        if self.is_active("homing_pods"):
            self.homing_timer += dt
            if self.homing_timer >= 0.8:  # Fire 2 micro-missiles every 0.8s
                self.homing_timer = 0.0
                rad = math.radians(player.angle)
                # Left wing
                lx = player_cx + math.cos(rad) * (-20) - math.sin(rad) * 10
                ly = player_cy + math.sin(rad) * (-20) + math.cos(rad) * 10
                # Right wing
                rx = player_cx + math.cos(rad) * 20 - math.sin(rad) * 10
                ry = player_cy + math.sin(rad) * 20 + math.cos(rad) * 10

                self.homing_missiles.append(HomingMicroMissile(lx, ly, player.angle - 25))
                self.homing_missiles.append(HomingMicroMissile(rx, ry, player.angle + 25))

        # Update existing homing missiles
        for m in self.homing_missiles:
            m.update(dt, enemy)
        self.homing_missiles = [m for m in self.homing_missiles if not m.used]

        # 4. Update Drone Companion
        if self.is_active("drone_companion") and self.drone:
            self.drone.update(dt, player_cx, player_cy, enemy)
        else:
            self.drone = None

        # 5. Update Enemy Frost / Freeze Timers
        if self.enemy_frozen_timer > 0:
            self.enemy_frozen_timer -= dt
        if self.enemy_frost_timer > 0:
            self.enemy_frost_timer -= dt
            if self.enemy_frost_timer <= 0:
                self.enemy_frost_hits = 0

        # 6. Update Popups and Milestone Banner
        for p in self.floating_popups:
            p["timer"] -= dt
            p["y_off"] += dt * 30.0
        self.floating_popups = [p for p in self.floating_popups if p["timer"] > 0]

        if self.milestone_banner:
            self.milestone_banner["timer"] -= dt
            if self.milestone_banner["timer"] <= 0:
                self.milestone_banner = None

    def _on_buff_expired(self, player, ability_id):
        """Restores player base stats when a buff expires."""
        if ability_id == "thruster_boost":
            player.max_speed = getattr(player, "base_max_speed", 7.0)
            player.acceleration = 0.15
            player.turn_rate = 3.0

    def modify_enemy_speed(self, base_speed):
        """Applies Time Slow and Frost/Freeze debuffs to enemy velocity."""
        factor = 1.0
        if self.is_active("time_slow"):
            factor *= TIME_SLOW_FACTOR
        if self.enemy_frozen_timer > 0:
            return 0.0  # Fully frozen solid
        elif self.enemy_frost_timer > 0:
            factor *= FREEZE_SLOW_FACTOR
        return base_speed * factor

    def modify_enemy_bullet_speed(self, base_speed):
        """Applies Time Slow to enemy bullets."""
        factor = 1.0
        if self.is_active("time_slow"):
            factor *= TIME_SLOW_FACTOR
        return base_speed * factor

    def is_enemy_frozen(self):
        return self.enemy_frozen_timer > 0

    def is_enemy_frosted(self):
        return self.enemy_frost_timer > 0

    def reset(self, player):
        """Full reset on respawn or new game."""
        self.drops.clear()
        self.active_buffs.clear()
        self.pity_counter = 0
        self.achieved_milestones.clear()
        self.drone = None
        self.homing_missiles.clear()
        self.floating_popups.clear()
        self.milestone_banner = None
        self.enemy_frost_timer = 0.0
        self.enemy_frost_hits = 0
        self.enemy_frozen_timer = 0.0
        self._on_buff_expired(player, "thruster_boost")

    # -----------------------------------------------------------------
    # Rendering: In-World & HUD
    # -----------------------------------------------------------------
    def draw_world_entities(self, surface, camera_x, camera_y, player):
        """Draws drops, missiles, and drone relative to camera."""
        # Draw power-up drops
        for drop in self.drops:
            drop.draw(surface, camera_x, camera_y, self.font_small)

        # Draw homing missiles
        for m in self.homing_missiles:
            m.draw(surface, camera_x, camera_y)

        # Draw drone companion
        if self.drone:
            p_w = getattr(player, 'width', 48)
            p_h = getattr(player, 'height', 61)
            player_cx = player.pos_x + p_w / 2
            player_cy = player.pos_y + p_h / 2
            self.drone.draw(surface, camera_x, camera_y, player_cx, player_cy)

    def draw_minimap_blips(self, minimap_surface, scale):
        """Renders power-up pickup dots on the minimap."""
        for drop in self.drops:
            mm_x = drop.x * scale
            mm_y = drop.y * scale
            color = Rarity.RADAR_COLORS[drop.rarity]
            pygame.draw.circle(minimap_surface, color, (int(mm_x), int(mm_y)), 3)

    def draw_hud(self, surface, game_width, game_height):
        """Draws active buff timers, floating pickup texts, and milestone banners."""
        # 1. Active Buff Cooldown Bars (Top-Left under Health/Shield)
        hud_x = 32
        hud_y = 65
        bar_w = 130
        bar_h = 12

        for buff_id, time_left in self.active_buffs.items():
            info = ABILITIES[buff_id]
            max_duration = info["duration"]
            ratio = max(0.0, min(1.0, time_left / max_duration))
            color = Rarity.COLORS[info["rarity"]]

            # Background bar
            pygame.draw.rect(surface, (20, 25, 35), (hud_x, hud_y, bar_w, bar_h))
            # Fill bar
            pygame.draw.rect(surface, color, (hud_x, hud_y, int(bar_w * ratio), bar_h))
            # Border
            pygame.draw.rect(surface, (80, 90, 110), (hud_x, hud_y, bar_w, bar_h), 1)

            # Text
            label = f"{info['name']}: {time_left:.1f}s"
            text_surf = self.font_hud.render(label, True, (255, 255, 255))
            surface.blit(text_surf, (hud_x + bar_w + 8, hud_y - 2))

            hud_y += 20

        # 2. Floating Popups (Screen Center-Left)
        popup_x = 32
        popup_base_y = 260
        for p in self.floating_popups:
            py = popup_base_y - p["y_off"]
            txt_surf = self.font_hud.render(p["text"], True, p["color"])
            surface.blit(txt_surf, (popup_x, int(py)))

        # 3. Milestone Notification Banner (Top Center)
        if self.milestone_banner:
            banner = self.milestone_banner
            alpha_ratio = min(1.0, banner["timer"] / 0.8) if banner["timer"] < 0.8 else 1.0

            bw = 560
            bh = 65
            bx = game_width // 2 - bw // 2
            by = 48

            b_surf = pygame.Surface((bw, bh), pygame.SRCALPHA)
            b_surf.fill((15, 20, 30, int(220 * alpha_ratio)))
            pygame.draw.rect(b_surf, (243, 156, 18, int(255 * alpha_ratio)), (0, 0, bw, bh), 2)

            t_surf = self.font_banner.render(banner["title"], True, (255, 215, 0))
            s_surf = self.font_hud.render(banner["sub"], True, (220, 240, 255))

            b_surf.blit(t_surf, t_surf.get_rect(centerx=bw // 2, centery=bh // 2 - 12))
            b_surf.blit(s_surf, s_surf.get_rect(centerx=bw // 2, centery=bh // 2 + 15))

            surface.blit(b_surf, (bx, by))
