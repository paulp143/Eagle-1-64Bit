"""academy_briefing.py - Super Earth Naval Academy Flight Training Subsystem.

Encapsulates the basic flight certification, weapon targeting qualification,
radar operations, and Close Air Support (CAS) training drills under
Flight Drill Instructor Commander Vance.
"""

import math
import pygame
from typing import List, Optional, Tuple

from eagle1.data.player_profile import PlayerProfileManager

try:
    from eagle1.systems.audio_manager import get_audio_manager
except Exception:
    get_audio_manager = None


def _get_font(name: str, size: int, bold: bool = False) -> pygame.font.Font:
    """Safe font loader with Fallback for headless environments."""
    if not pygame.font.get_init():
        try:
            pygame.font.init()
        except Exception:
            pass
    try:
        return pygame.font.SysFont(name, size, bold=bold)
    except Exception:
        return pygame.font.Font(None, size)


# Academy Training Drill States
DRILL_BRIEFING = "briefing"
DRILL_STEERING = "steering"
DRILL_THROTTLE = "throttle"
DRILL_BORDER_SAFETY = "border_safety"
DRILL_CANNONS = "cannons"
DRILL_RADAR_ROCKETS = "radar_rockets"
DRILL_STRATAGEM = "stratagem"
DRILL_GRADUATION = "graduation"
DRILL_COMPLETE = "complete"

DRILL_SEQUENCE = [
    DRILL_BRIEFING,
    DRILL_STEERING,
    DRILL_THROTTLE,
    DRILL_BORDER_SAFETY,
    DRILL_CANNONS,
    DRILL_RADAR_ROCKETS,
    DRILL_STRATAGEM,
    DRILL_GRADUATION,
    DRILL_COMPLETE,
]


class AcademyWaypointGate:
    """Holographic energy gate requiring player navigation alignment."""

    def __init__(self, x: float, y: float, radius: float = 85.0, label: str = "ALPHA"):
        self.x = float(x)
        self.y = float(y)
        self.radius = float(radius)
        self.label = label
        self.cleared = False
        self.pulse_phase = 0.0

    def check_collision(self, player_x: float, player_y: float) -> bool:
        """Return True if player passes within the gate threshold radius."""
        if self.cleared:
            return False
        dist = math.hypot(player_x - self.x, player_y - self.y)
        if dist <= self.radius:
            self.cleared = True
            return True
        return False

    def draw(self, surface: pygame.Surface, camera_x: float, camera_y: float, font: pygame.font.Font):
        """Render pulsating energy ring in world space."""
        if self.cleared:
            return

        screen_x = int(self.x - camera_x)
        screen_y = int(self.y - camera_y)

        # Pulse radius
        self.pulse_phase = (self.pulse_phase + 0.05) % (2 * math.pi)
        pulse_r = int(self.radius + math.sin(self.pulse_phase) * 6)

        # Draw outer glowing ring
        pygame.draw.circle(surface, (0, 180, 240), (screen_x, screen_y), pulse_r, width=3)
        pygame.draw.circle(surface, (0, 240, 255), (screen_x, screen_y), max(1, pulse_r - 8), width=1)

        # Gate Label
        label_surf = font.render(f"GATE {self.label}", True, (255, 215, 0))
        surface.blit(label_surf, label_surf.get_rect(center=(screen_x, screen_y - pulse_r - 16)))


class AcademyTargetDrone(pygame.Rect):
    """Automaton training target drone for Quad-Cannon and Missile drills."""

    def __init__(self, x: float, y: float, max_health: float = 50.0, label: str = "DRONE-1", is_mobile: bool = False):
        super().__init__(int(x - 24), int(y - 24), 48, 48)
        self.pos_x = float(x)
        self.pos_y = float(y)
        self.max_health = float(max_health)
        self.health = float(max_health)
        self.label = label
        self.is_mobile = is_mobile
        self.exploding = False
        self.move_angle = 0.0

    @property
    def is_alive(self) -> bool:
        return self.health > 0.0 and not self.exploding

    def take_damage(self, amount: float) -> bool:
        """Apply damage and return True if destroyed by this hit."""
        if not self.is_alive:
            return False
        self.health -= amount
        if self.health <= 0.0:
            self.health = 0.0
            self.exploding = True
            return True
        return False

    def update(self, dt: float):
        """Hover or maneuver training drone."""
        if self.is_mobile and self.is_alive:
            self.move_angle = (self.move_angle + 1.2 * dt) % (2 * math.pi)
            self.pos_x += math.cos(self.move_angle) * 1.5
            self.pos_y += math.sin(self.move_angle) * 1.5
            self.x = int(self.pos_x - 24)
            self.y = int(self.pos_y - 24)

    def draw(self, surface: pygame.Surface, camera_x: float, camera_y: float, font: pygame.font.Font):
        """Render target drone and health bracket in world space."""
        if not self.is_alive:
            return

        screen_x = int(self.pos_x - camera_x)
        screen_y = int(self.pos_y - camera_y)

        # Drone diamond chassis
        points = [
            (screen_x, screen_y - 22),
            (screen_x + 22, screen_y),
            (screen_x, screen_y + 22),
            (screen_x - 22, screen_y),
        ]
        pygame.draw.polygon(surface, (180, 40, 40), points)
        pygame.draw.polygon(surface, (255, 80, 80), points, width=2)
        pygame.draw.circle(surface, (255, 200, 0), (screen_x, screen_y), 6)

        # Health bar
        bar_w = 44
        bar_h = 6
        bar_x = screen_x - bar_w // 2
        bar_y = screen_y - 32
        pct = max(0.0, min(1.0, self.health / self.max_health))
        pygame.draw.rect(surface, (40, 10, 10), (bar_x, bar_y, bar_w, bar_h))
        pygame.draw.rect(surface, (255, 50, 50), (bar_x, bar_y, int(bar_w * pct), bar_h))
        pygame.draw.rect(surface, (100, 100, 100), (bar_x, bar_y, bar_w, bar_h), width=1)


class AcademyTargetBunker(pygame.Rect):
    """Automaton simulated training foundry bunker for Stratagem Air Strike drill."""

    def __init__(self, x: float, y: float, max_health: float = 100.0, label: str = "TRAINING FOUNDRY"):
        super().__init__(int(x - 50), int(y - 50), 100, 100)
        self.pos_x = float(x)
        self.pos_y = float(y)
        self.max_health = float(max_health)
        self.health = float(max_health)
        self.label = label
        self.exploding = False

    @property
    def is_alive(self) -> bool:
        return self.health > 0.0 and not self.exploding

    def take_damage(self, amount: float) -> bool:
        """Apply damage and return True if destroyed."""
        if not self.is_alive:
            return False
        self.health -= amount
        if self.health <= 0.0:
            self.health = 0.0
            self.exploding = True
            return True
        return False

    def draw(self, surface: pygame.Surface, camera_x: float, camera_y: float, font: pygame.font.Font):
        """Render heavy target structure in world space."""
        if not self.is_alive:
            return

        screen_x = int(self.pos_x - camera_x)
        screen_y = int(self.pos_y - camera_y)

        b_rect = pygame.Rect(screen_x - 50, screen_y - 50, 100, 100)
        pygame.draw.rect(surface, (45, 50, 60), b_rect, border_radius=6)
        pygame.draw.rect(surface, (255, 60, 60), b_rect, width=3, border_radius=6)

        # Danger cross
        pygame.draw.line(surface, (255, 80, 80), (b_rect.left + 15, b_rect.top + 15), (b_rect.right - 15, b_rect.bottom - 15), 3)
        pygame.draw.line(surface, (255, 80, 80), (b_rect.right - 15, b_rect.top + 15), (b_rect.left + 15, b_rect.bottom - 15), 3)

        # CAS Beacon Target Reticle
        pygame.draw.circle(surface, (255, 215, 0), (screen_x, screen_y), 65, width=2)
        pygame.draw.circle(surface, (255, 0, 0), (screen_x, screen_y), 8)

        lbl = font.render(self.label, True, (255, 215, 0))
        surface.blit(lbl, lbl.get_rect(center=(screen_x, screen_y - 65)))


class CommsHUDBox:
    """Typewriter tactical radio transmission display from Commander Vance."""

    def __init__(self, x: int = 80, y: int = 70, w: int = 640, h: int = 110):
        self.rect = pygame.Rect(x, y, w, h)
        self.speaker_title = "CDR. VANCE // NAVAL ACADEMY CHIEF INSTRUCTOR"
        self.full_text = ""
        self.displayed_chars = 0
        self.chars_per_second = 38.0
        self.is_finished = False

        self.font_title = _get_font("arial", 13, bold=True)
        self.font_msg = _get_font("arial", 16)
        self.audio = get_audio_manager() if get_audio_manager else None

    def set_message(self, text: str, sfx_cue: Optional[str] = "ui_click"):
        """Queue and begin typewriter rendering of dialogue."""
        self.full_text = text
        self.displayed_chars = 0
        self.is_finished = False
        if sfx_cue and self.audio:
            self.audio.play_sfx(sfx_cue)

    def update(self, dt: float):
        """Advance typewriter characters."""
        if not self.is_finished:
            self.displayed_chars += self.chars_per_second * dt
            if self.displayed_chars >= len(self.full_text):
                self.displayed_chars = len(self.full_text)
                self.is_finished = True

    def draw(self, surface: pygame.Surface):
        """Render comms HUD frame."""
        if not self.full_text:
            return

        # Semi-transparent background
        box_surf = pygame.Surface((self.rect.w, self.rect.h), pygame.SRCALPHA)
        box_surf.fill((12, 18, 28, 230))
        surface.blit(box_surf, self.rect.topleft)

        # Golden hazard border
        pygame.draw.rect(surface, (220, 180, 50), self.rect, width=2, border_radius=6)

        # Speaker badge
        badge_rect = pygame.Rect(self.rect.x + 8, self.rect.y + 6, self.rect.w - 16, 22)
        pygame.draw.rect(surface, (25, 35, 55), badge_rect, border_radius=4)
        title_surf = self.font_title.render(self.speaker_title, True, (0, 230, 255))
        surface.blit(title_surf, (badge_rect.x + 8, badge_rect.y + 3))

        # Typewriter text content
        current_len = int(self.displayed_chars)
        visible_text = self.full_text[:current_len]

        # Word wrap rendering
        words = visible_text.split(" ")
        lines = []
        cur_line = ""
        max_w = self.rect.w - 32

        for w in words:
            test = f"{cur_line} {w}".strip()
            if self.font_msg.size(test)[0] <= max_w:
                cur_line = test
            else:
                if cur_line:
                    lines.append(cur_line)
                cur_line = w
        if cur_line:
            lines.append(cur_line)

        y_offset = self.rect.y + 36
        for line in lines[:3]:
            msg_surf = self.font_msg.render(line, True, (245, 245, 255))
            surface.blit(msg_surf, (self.rect.x + 16, y_offset))
            y_offset += 21


class AcademyTutorialManager:
    """Central manager driving the Super Earth Naval Academy mission progression."""

    def __init__(self):
        self.state = DRILL_BRIEFING
        self.drill_timer = 0.0
        self.is_completed = False
        self.graduated = False

        self.comms_box = CommsHUDBox()
        self.waypoint_gates: List[AcademyWaypointGate] = []
        self.target_drones: List[AcademyTargetDrone] = []
        self.target_bunker: Optional[AcademyTargetBunker] = None

        # Drill specific tracking
        self.current_gate_idx = 0
        self.throttle_high_time = 0.0
        self.throttle_low_time = 0.0
        self.throttle_high_completed = False
        self.throttle_low_completed = False
        self.border_warned = False
        self.border_cleared = False

        self.font_obj = _get_font("arial", 18, bold=True)
        self.font_sub = _get_font("arial", 14)
        self.audio = get_audio_manager() if get_audio_manager else None

        self._init_briefing_dialogue()

    def _init_briefing_dialogue(self):
        self.comms_box.set_message(
            "Welcome to the Super Earth Naval Academy, Cadet. "
            "Only the finest pilot the Eagle-1. Today we separate the patriots from the scrap metal!"
        )

    def reset(self, player=None):
        """Reset all training drills and spawn initial waypoints relative to player."""
        self.state = DRILL_BRIEFING
        self.drill_timer = 0.0
        self.is_completed = False
        self.graduated = False
        self.current_gate_idx = 0
        self.throttle_high_time = 0.0
        self.throttle_low_time = 0.0
        self.throttle_high_completed = False
        self.throttle_low_completed = False
        self.border_warned = False
        self.border_cleared = False

        px = player.pos_x if player else 1500.0
        py = player.pos_y if player else 1500.0

        # Create slalom gates Alpha, Bravo, Charlie
        self.waypoint_gates = [
            AcademyWaypointGate(px, py - 320.0, radius=85.0, label="ALPHA"),
            AcademyWaypointGate(px - 280.0, py - 600.0, radius=85.0, label="BRAVO"),
            AcademyWaypointGate(px + 240.0, py - 880.0, radius=85.0, label="CHARLIE"),
        ]

        # Reset target entities
        self.target_drones = []
        self.target_bunker = None
        self._init_briefing_dialogue()

    def get_active_drill_title(self) -> str:
        titles = {
            DRILL_BRIEFING: "PHASE 0: PRE-FLIGHT BRIEFING",
            DRILL_STEERING: "DRILL 1: YAW STEERING & WAYPOINT GATES",
            DRILL_THROTTLE: "DRILL 2: TURBINE THROTTLE & AIR BRAKES",
            DRILL_BORDER_SAFETY: "DRILL 3: HAZARD PERIMETER BOUNDARY",
            DRILL_CANNONS: "DRILL 4: QUAD-CANNON CONVERGENCE RANGE",
            DRILL_RADAR_ROCKETS: "DRILL 5: RADAR LOCK-ON & HOMING MISSILES",
            DRILL_STRATAGEM: "DRILL 6: 500KG BOMB CAS AIR STRIKE",
            DRILL_GRADUATION: "GRADUATION: SUPER EARTH WINGS OF LIBERTY",
            DRILL_COMPLETE: "MISSION COMPLETE: NAVAL AVIATOR CERTIFIED",
        }
        return titles.get(self.state, "TRAINING DRILL")

    def advance_drill(self, player=None):
        """Transition cleanly to the next drill in the sequence."""
        self.drill_timer = 0.0
        if self.state == DRILL_BRIEFING:
            self.state = DRILL_STEERING
            self.comms_box.set_message("Take the stick! Steer with [A] and [D] through Waypoint Gates Alpha, Bravo, and Charlie.")

        elif self.state == DRILL_STEERING:
            self.state = DRILL_THROTTLE
            self.throttle_high_time = 0.0
            self.throttle_low_time = 0.0
            self.comms_box.set_message("Good maneuvers! Now test thrust: hold [W] for maximum afterburners, then [S] for air brakes.")

        elif self.state == DRILL_THROTTLE:
            self.state = DRILL_BORDER_SAFETY
            self.comms_box.set_message("Heads up, Cadet! Fly toward the sector perimeter. Watch for boundary proximity warnings!")

        elif self.state == DRILL_BORDER_SAFETY:
            self.state = DRILL_CANNONS
            px = player.pos_x if player else 1500.0
            py = player.pos_y if player else 1500.0
            self.target_drones = [
                AcademyTargetDrone(px - 140.0, py - 420.0, max_health=40.0, label="DRONE-1"),
                AcademyTargetDrone(px, py - 520.0, max_health=40.0, label="DRONE-2"),
                AcademyTargetDrone(px + 140.0, py - 420.0, max_health=40.0, label="DRONE-3"),
            ]
            self.comms_box.set_message("Guns hot! Align the 180m convergence pip on the drone dummies. Fire Quad-Cannons with [SPACE]!")

        elif self.state == DRILL_CANNONS:
            self.state = DRILL_RADAR_ROCKETS
            px = player.pos_x if player else 1500.0
            py = player.pos_y if player else 1500.0
            self.target_drones = [
                AcademyTargetDrone(px - 180.0, py - 480.0, max_health=60.0, label="INTERCEPTOR-A", is_mobile=True),
                AcademyTargetDrone(px + 180.0, py - 480.0, max_health=60.0, label="INTERCEPTOR-B", is_mobile=True),
            ]
            self.comms_box.set_message("Toggle radar with [Q]. Acquire target lock brackets and launch homing rockets with [Right Click] or [E]!")

        elif self.state == DRILL_RADAR_ROCKETS:
            self.state = DRILL_STRATAGEM
            px = player.pos_x if player else 1500.0
            py = player.pos_y if player else 1500.0
            self.target_bunker = AcademyTargetBunker(px, py - 550.0, max_health=100.0, label="TRAINING FOUNDRY")
            self.comms_box.set_message("Final exam: Close Air Support! Select your 500kg Bomb with [2], align the predictive reticle, and drop with [C]!")

        elif self.state == DRILL_STRATAGEM:
            self.state = DRILL_GRADUATION
            self.graduated = True
            self.comms_box.set_message(
                "Direct hit! Outstanding flying, Pilot! By decree of Super Earth High Command, "
                "you are hereby certified as a Super Earth Naval Aviator!"
            )
            # Update user profile
            try:
                prof_mgr = PlayerProfileManager()
                if prof_mgr.has_active_profile():
                    prof = prof_mgr.load_profile()
                    prof.academy_completed = True
                    prof.missions_cleared = max(1, prof.missions_cleared)
                    prof_mgr.save_profile(prof)
            except Exception:
                pass

        elif self.state == DRILL_GRADUATION:
            self.state = DRILL_COMPLETE
            self.is_completed = True

    def update_throttle_drill(self, dt: float, player):
        """Accumulate hold duration at max and min speed thresholds."""
        if not player:
            return

        speed = player.get_forward_speed() if hasattr(player, "get_forward_speed") else 4.0

        if not self.throttle_high_completed:
            if speed >= 6.4:
                self.throttle_high_time += dt
                if self.throttle_high_time >= 2.0:
                    self.throttle_high_completed = True
                    self.comms_box.set_message("Afterburner confirmed! Now hit [S] to engage air brakes down to minimum speed.")
            else:
                self.throttle_high_time = max(0.0, self.throttle_high_time - dt * 0.5)

        elif not self.throttle_low_completed:
            if speed <= 2.6:
                self.throttle_low_time += dt
                if self.throttle_low_time >= 2.0:
                    self.throttle_low_completed = True
            else:
                self.throttle_low_time = max(0.0, self.throttle_low_time - dt * 0.5)

    def update(self, dt: float, player=None, keys=None, ground_support=None):
        """Main update tick driving drill triggers and state transitions."""
        self.drill_timer += dt
        self.comms_box.update(dt)

        if not player:
            return

        # Auto-rearm ammo during training so cadet never runs out
        if player.used_bullets >= player.max_bullets - 10:
            player.used_bullets = 0
        if player.used_rockets >= player.max_rockets - 1:
            player.used_rockets = 0

        # Update targets
        for drone in self.target_drones:
            drone.update(dt)

        # 0. BRIEFING
        if self.state == DRILL_BRIEFING:
            if self.drill_timer >= 4.5:
                self.advance_drill(player)

        # 1. STEERING DRILL
        elif self.state == DRILL_STEERING:
            if self.current_gate_idx < len(self.waypoint_gates):
                gate = self.waypoint_gates[self.current_gate_idx]
                if gate.check_collision(player.pos_x, player.pos_y):
                    self.current_gate_idx += 1
                    if self.audio:
                        self.audio.play_sfx("ui_click")
                    if self.current_gate_idx < len(self.waypoint_gates):
                        next_label = self.waypoint_gates[self.current_gate_idx].label
                        self.comms_box.set_message(f"Gate cleared! Bank toward Gate {next_label}.")
                    else:
                        self.advance_drill(player)

        # 2. THROTTLE DRILL
        elif self.state == DRILL_THROTTLE:
            self.update_throttle_drill(dt, player)
            if self.throttle_high_completed and self.throttle_low_completed:
                self.advance_drill(player)

        # 3. BORDER SAFETY DRILL
        elif self.state == DRILL_BORDER_SAFETY:
            px, py = player.pos_x, player.pos_y
            near_border = (px < 400.0 or px > 2600.0 or py < 400.0 or py > 2600.0)
            in_safe_zone = (700.0 < px < 2300.0 and 700.0 < py < 2300.0)

            if near_border and not self.border_warned:
                self.border_warned = True
                self.comms_box.set_message("PERIMETER WARNING! Turn hard back toward center before boundary hazard dampers engage!")

            if self.border_warned and in_safe_zone:
                self.border_cleared = True
                self.advance_drill(player)

        # 4. CANNONS DRILL
        elif self.state == DRILL_CANNONS:
            living_drones = [d for d in self.target_drones if d.is_alive]
            if len(living_drones) == 0:
                self.advance_drill(player)

        # 5. RADAR & HOMING ROCKETS
        elif self.state == DRILL_RADAR_ROCKETS:
            living_drones = [d for d in self.target_drones if d.is_alive]
            if len(living_drones) == 0:
                self.advance_drill(player)

        # 6. STRATAGEM AIR STRIKE
        elif self.state == DRILL_STRATAGEM:
            if ground_support and self.target_bunker and self.target_bunker.is_alive:
                for strike in getattr(ground_support, "active_strikes", []):
                    if getattr(strike, "impacted", False):
                        dist = math.hypot(strike.target_x - self.target_bunker.pos_x, strike.target_y - self.target_bunker.pos_y)
                        blast_r = 480.0 if getattr(strike, "type", 0) == 1 else 320.0
                        if dist <= blast_r:
                            self.target_bunker.take_damage(200.0)
                            break
            if self.target_bunker and not self.target_bunker.is_alive:
                self.advance_drill(player)

        # 7. GRADUATION
        elif self.state == DRILL_GRADUATION:
            if self.drill_timer >= 6.0:
                self.advance_drill(player)

    def on_stratagem_deployed(self, x: float, y: float, radius: float = 350.0, damage: float = 200.0) -> bool:
        """Called when a stratagem air strike detonates near the training bunker."""
        if self.state == DRILL_STRATAGEM and self.target_bunker and self.target_bunker.is_alive:
            dist = math.hypot(x - self.target_bunker.pos_x, y - self.target_bunker.pos_y)
            if dist <= radius:
                self.target_bunker.take_damage(damage)
                return True
        return False

    def get_combat_targets(self) -> list:
        """Expose training entities for radar lock and ballistic collisions."""
        targets = [d for d in self.target_drones if d.is_alive]
        if self.target_bunker and self.target_bunker.is_alive:
            targets.append(self.target_bunker)
        return targets

    def draw_world(self, surface: pygame.Surface, camera_x: float, camera_y: float):
        """Render all training gates, target dummies, and bunkers in world space."""
        # Gates
        if self.state == DRILL_STEERING:
            for gate in self.waypoint_gates:
                gate.draw(surface, camera_x, camera_y, self.font_obj)

        # Target drones
        if self.state in (DRILL_CANNONS, DRILL_RADAR_ROCKETS):
            for drone in self.target_drones:
                drone.draw(surface, camera_x, camera_y, self.font_obj)

        # Target Bunker
        if self.state == DRILL_STRATAGEM and self.target_bunker:
            self.target_bunker.draw(surface, camera_x, camera_y, self.font_obj)

    def draw_hud(self, surface: pygame.Surface, player=None):
        """Render objective tracker, progress gauge, and Vance comms box in screen space."""
        # Commander Vance comms
        self.comms_box.draw(surface)

        # Top Objective tracker banner
        banner_rect = pygame.Rect(surface.get_width() - 480, 70, 430, 80)
        pygame.draw.rect(surface, (14, 20, 32, 230), banner_rect, border_radius=8)
        pygame.draw.rect(surface, (0, 200, 255), banner_rect, width=2, border_radius=8)

        title_surf = self.font_obj.render(self.get_active_drill_title(), True, (255, 215, 0))
        surface.blit(title_surf, (banner_rect.x + 14, banner_rect.y + 10))

        # Dynamic sub-status
        sub_text = "Follow Commander Vance's tactical instructions."
        if self.state == DRILL_STEERING:
            sub_text = f"Waypoint Rings Cleared: [{self.current_gate_idx} / {len(self.waypoint_gates)}]"
        elif self.state == DRILL_THROTTLE:
            h_stat = "DONE" if self.throttle_high_completed else f"{int((self.throttle_high_time / 2.0) * 100)}%"
            l_stat = "DONE" if self.throttle_low_completed else f"{int((self.throttle_low_time / 2.0) * 100)}%"
            sub_text = f"Max Thrust: [{h_stat}] | Air Brakes: [{l_stat}]"
        elif self.state == DRILL_BORDER_SAFETY:
            sub_text = "STATUS: Perform 180° turnaround back to safe airspace."
        elif self.state == DRILL_CANNONS:
            left = len([d for d in self.target_drones if d.is_alive])
            sub_text = f"Cannon Targets Remaining: [{left}]"
        elif self.state == DRILL_RADAR_ROCKETS:
            left = len([d for d in self.target_drones if d.is_alive])
            sub_text = f"Radar Lock Targets Remaining: [{left}]"
        elif self.state == DRILL_STRATAGEM:
            sub_text = "STATUS: Deploy Eagle 500kg Bomb on marked Foundry!"
        elif self.state == DRILL_GRADUATION:
            sub_text = "STATUS: CERTIFIED! Returning to Fleet..."

        sub_surf = self.font_sub.render(sub_text, True, (230, 240, 255))
        surface.blit(sub_surf, (banner_rect.x + 14, banner_rect.y + 44))
