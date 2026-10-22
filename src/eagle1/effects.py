"""Shared visual effect helpers, screen shake, wingtip contrails, hit sparks, and explosion sprite classes."""

import math
import random

import pygame

FRAME_MULTIPLIKATOR = 2
FRAME_SPEED = 0.4


class ScreenShake:
    """Lightweight camera shake controller for weapon recoil, missile blasts, and collisions."""

    def __init__(self):
        self.intensity = 0.0
        self.remaining_frames = 0
        self.total_frames = 1

    def trigger(self, intensity: float, duration_frames: int = 6):
        """Trigger or amplify screen shake if new intensity is >= current active shake."""
        current_effective = self.intensity * (
            self.remaining_frames / max(1, self.total_frames)
        )
        if intensity >= current_effective or self.remaining_frames <= 0:
            self.intensity = float(intensity)
            self.remaining_frames = max(1, int(duration_frames))
            self.total_frames = self.remaining_frames

    def update(self):
        """Advance shake decay by one frame."""
        if self.remaining_frames > 0:
            self.remaining_frames -= 1
            if self.remaining_frames <= 0:
                self.intensity = 0.0

    def get_offset(self) -> tuple[int, int]:
        """Return integer pixel offset (dx, dy) for the current frame."""
        if self.remaining_frames <= 0 or self.intensity <= 0.0:
            return (0, 0)
        decay = self.remaining_frames / max(1, self.total_frames)
        mag = self.intensity * decay
        ox = int(round(random.uniform(-mag, mag)))
        oy = int(round(random.uniform(-mag, mag)))
        return (ox, oy)

    def reset(self):
        self.intensity = 0.0
        self.remaining_frames = 0
        self.total_frames = 1


class CombatJuiceManager:
    """Manages kinesthetic dogfight feedback: screen shake, high-G wingtip contrails, and directional hit sparks."""

    def __init__(self, max_contrail_nodes: int = 90, max_sparks: int = 120):
        self.shake = ScreenShake()
        self.max_contrail_nodes = max_contrail_nodes
        self.max_sparks = max_sparks
        self.contrails = []
        self.sparks = []

    def reset(self):
        self.shake.reset()
        self.contrails.clear()
        self.sparks.clear()

    def trigger_shake(self, intensity: float, duration_frames: int = 6):
        self.shake.trigger(intensity, duration_frames)

    def get_camera_offset(self) -> tuple[int, int]:
        return self.shake.get_offset()

    def emit_wingtip_contrails(
        self,
        cx: float,
        cy: float,
        angle_deg: float,
        speed: float,
        angular_delta: float,
        wing_span: float = 21.0,
        tail_offset: float = 14.0,
        is_enemy: bool = False,
    ):
        """Emit aerodynamic wingtip vapor trails when pulling high-G turns."""
        if abs(angular_delta) < 1.6 or speed < 3.0:
            return

        rad = math.radians(angle_deg)
        # Compute wingtip world coordinates
        if is_enemy:
            # Light_Enemy forward is (+sin, +cos), tail is (-sin, -cos)
            fx, fy = math.sin(rad), math.cos(rad)
        else:
            # Player forward is (-sin, -cos), tail is (+sin, +cos)
            fx, fy = -math.sin(rad), -math.cos(rad)

        rx, ry = -fy, fx  # Perpendicular right wing vector
        base_x = cx - fx * tail_offset
        base_y = cy - fy * tail_offset

        color = (255, 190, 140) if is_enemy else (210, 240, 255)
        max_age = 16

        for side in (-1.0, 1.0):
            wx = base_x + rx * (wing_span * side)
            wy = base_y + ry * (wing_span * side)
            self.contrails.append(
                {
                    "x": wx,
                    "y": wy,
                    "vx": -fx * 0.35,
                    "vy": -fy * 0.35,
                    "age": 0,
                    "max_age": max_age,
                    "color": color,
                }
            )

        if len(self.contrails) > self.max_contrail_nodes:
            del self.contrails[: len(self.contrails) - self.max_contrail_nodes]

    def spawn_hit_sparks(self, x: float, y: float, damage_ratio: float = 1.0):
        """Spawn directional hit particles distinguishing armored deflection vs rear-engine critical hits."""
        if damage_ratio <= 0.60:
            kind = "deflect"
            count = 5
            color = (180, 235, 255)
            speed_min, speed_max = 2.0, 4.5
            max_age = 10
        elif damage_ratio >= 1.15:
            kind = "critical"
            count = 8
            color = (255, 145, 35)
            speed_min, speed_max = 2.5, 5.8
            max_age = 15
        else:
            kind = "normal"
            count = 6
            color = (255, 220, 90)
            speed_min, speed_max = 2.0, 4.8
            max_age = 12

        for _ in range(count):
            ang = random.uniform(0.0, math.tau)
            spd = random.uniform(speed_min, speed_max)
            self.sparks.append(
                {
                    "x": float(x),
                    "y": float(y),
                    "vx": math.cos(ang) * spd,
                    "vy": math.sin(ang) * spd,
                    "age": 0,
                    "max_age": max_age,
                    "color": color,
                    "kind": kind,
                }
            )

        if len(self.sparks) > self.max_sparks:
            del self.sparks[: len(self.sparks) - self.max_sparks]

    def update(self):
        """Update screen shake, contrail dissipation, and spark kinematics."""
        self.shake.update()

        alive_contrails = []
        for node in self.contrails:
            node["x"] += node["vx"]
            node["y"] += node["vy"]
            node["age"] += 1
            if node["age"] < node["max_age"]:
                alive_contrails.append(node)
        self.contrails = alive_contrails

        alive_sparks = []
        for sp in self.sparks:
            sp["x"] += sp["vx"]
            sp["y"] += sp["vy"]
            sp["vx"] *= 0.88
            sp["vy"] *= 0.88
            sp["age"] += 1
            if sp["age"] < sp["max_age"]:
                alive_sparks.append(sp)
        self.sparks = alive_sparks

    def draw(self, surface: pygame.Surface, camera_x: int, camera_y: int):
        """Render wingtip vapor contrails and hit sparks directly in screen space without surface allocations."""
        sw, sh = surface.get_size()

        for node in self.contrails:
            sx = int(node["x"] - camera_x)
            sy = int(node["y"] - camera_y)
            if -10 <= sx <= sw + 10 and -10 <= sy <= sh + 10:
                life_ratio = 1.0 - (node["age"] / node["max_age"])
                radius = max(1, int(3.0 * life_ratio))
                col = (
                    int(node["color"][0] * life_ratio),
                    int(node["color"][1] * life_ratio),
                    int(node["color"][2] * life_ratio),
                )
                pygame.draw.circle(surface, col, (sx, sy), radius)

        for sp in self.sparks:
            sx = int(sp["x"] - camera_x)
            sy = int(sp["y"] - camera_y)
            if -10 <= sx <= sw + 10 and -10 <= sy <= sh + 10:
                life_ratio = 1.0 - (sp["age"] / sp["max_age"])
                end_x = int(sx - sp["vx"] * 1.8)
                end_y = int(sy - sp["vy"] * 1.8)
                pygame.draw.line(surface, sp["color"], (sx, sy), (end_x, end_y), 2)
                if sp["kind"] == "critical" and life_ratio > 0.5:
                    pygame.draw.circle(surface, (255, 245, 180), (sx, sy), 2)



class Spritesheet:
    def __init__(self, image, cols):
        self.sheet = image
        self.cols = cols
        self.frame_width = self.sheet.get_width() / cols
        self.frame_height = self.sheet.get_height()
        self.frames = self.extract_frames()

    def extract_frames(self):
        frames = []
        for i in range(self.cols):
            rect = pygame.Rect(
                int(i * self.frame_width),
                0,
                int(self.frame_width),
                self.frame_height,
            )
            frame = self.sheet.subsurface(rect)
            frame = pygame.transform.scale(
                frame,
                (
                    int(self.frame_width * FRAME_MULTIPLIKATOR),
                    int(self.frame_height * FRAME_MULTIPLIKATOR),
                ),
            )
            frames.append(frame)
        return frames


class Large_explosion_a(pygame.sprite.Sprite):
    def __init__(self, x, y, frames, speed=FRAME_SPEED):
        super().__init__()
        self.frames = frames
        self.speed = speed
        self.current_frame = 0
        self.image = self.frames[0]
        self.rect = self.image.get_rect(center=(x, y))

    def update(self):
        self.current_frame += self.speed
        if self.current_frame >= len(self.frames):
            self.kill()
        else:
            self.image = self.frames[int(self.current_frame)]
