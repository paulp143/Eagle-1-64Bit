"""Missile countermeasures for aerial Automaton units: flares, incoming-missile
detection and beam evasion, plus air-target classification for homing rockets.

Heading conventions used in this codebase:
- Enemy convention (Light_Enemy): forward vector = (sin a, cos a).
- Player convention (Player, BomberEnemy): forward vector = (-sin a, -cos a).
"""

import math
import random
from typing import Iterable

# OMNI radar: wide forward arc instead of a 360° sphere (half-angle in degrees).
RADAR_OMNI_HALF_ANGLE = 75.0

# Flares
FLARE_SIZE = 8
FLARE_LIFETIME_FRAMES = 75            # 1.25 s at 60 FPS
FLARE_EJECT_SPEED = 3.0               # px/frame initial drift
FLARE_DRAG = 0.94                     # per-frame velocity multiplier
FLARES_PER_SALVO = 3
FLARE_TRIGGER_RANGE = 240.0           # rocket-to-target distance that triggers the flare roll
FLARE_DECOY_CHANCE = 0.55             # chance a deployed salvo pulls the rocket off target
FLARE_DETONATION_RADIUS = 16.0
FLARE_OUTER_COLOR = (255, 150, 40)    # matches theme.WARNING (world FX, not UI)
FLARE_CORE_COLOR = (255, 245, 220)

LIGHT_ENEMY_FLARES = 1
LIGHT_ENEMY_FLARE_DEPLOY_CHANCE = 0.6
BOMBER_FLARES = 2
BOMBER_FLARE_DEPLOY_CHANCE = 0.85

# Evasion (Light_Enemy only; bombers are too heavy to jink)
MISSILE_WARNING_RANGE = 420.0
MISSILE_REACTION_DELAY_FRAMES = 10
MISSILE_EVASION_TURN_MULT = 1.3

_RNG = random.Random()


def is_air_target(entity) -> bool:
    """Return True if the entity is flagged as an aerial unit homing rockets may lock."""
    if entity is None:
        return False
    return bool(getattr(entity, "is_air_target", False))


def filter_air_targets(entities: Iterable) -> list:
    """Return the living, non-exploding aerial entities from `entities`."""
    if entities is None:
        return []
    return [
        e for e in entities
        if is_air_target(e) and not getattr(e, "exploding", False) and getattr(e, "health", 1) > 0
    ]


def heading_deviation_deg(src_cx: float, src_cy: float, src_angle: float,
                          tx: float, ty: float) -> float:
    """Absolute angle in [0, 180] between the source nose (player convention) and the target."""
    desired = math.degrees(math.atan2(-(tx - src_cx), -(ty - src_cy))) % 360
    return abs((desired - src_angle + 180) % 360 - 180)


class Flare:
    """Short-lived decoy flare that can pull a homing rocket off its target."""

    def __init__(self, cx: float, cy: float, drift_x: float, drift_y: float):
        self.width = FLARE_SIZE
        self.height = FLARE_SIZE
        self.pos_x = float(cx) - FLARE_SIZE / 2
        self.pos_y = float(cy) - FLARE_SIZE / 2
        self.x = int(self.pos_x)
        self.y = int(self.pos_y)
        self.velocity = (float(drift_x), float(drift_y))
        self.speed = 0.0
        self.angle = 0.0
        self.health = 1.0
        self.exploding = False
        self.frames_left = FLARE_LIFETIME_FRAMES
        self.is_air_target = False  # flares are never radar-lockable

    @property
    def is_alive(self) -> bool:
        return self.health > 0 and self.frames_left > 0

    def center(self) -> tuple:
        return (self.pos_x + self.width / 2, self.pos_y + self.height / 2)

    def update(self, speed_factor: float = 1.0) -> None:
        if not self.is_alive:
            return
        vx, vy = self.velocity
        self.pos_x += vx * speed_factor
        self.pos_y += vy * speed_factor
        self.velocity = (vx * FLARE_DRAG, vy * FLARE_DRAG)
        self.x = int(self.pos_x)
        self.y = int(self.pos_y)
        self.frames_left -= 1
        if self.frames_left <= 0:
            self.health = 0.0
