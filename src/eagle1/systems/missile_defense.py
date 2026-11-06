"""Missile countermeasures for aerial Automaton units: flares, incoming-missile
detection and beam evasion, plus air-target classification for homing rockets.

Heading conventions used in this codebase:
- Enemy convention (Light_Enemy): forward vector = (sin a, cos a).
- Player convention (Player, BomberEnemy): forward vector = (-sin a, -cos a).
"""

import math
import random
from typing import Iterable, List, Optional

import pygame

# OMNI radar: wide forward arc instead of a 360° sphere (half-angle in degrees).
RADAR_OMNI_HALF_ANGLE = 75.0

# Flares
FLARE_SIZE = 8
FLARE_LIFETIME_FRAMES = 75            # 1.25 s at 60 FPS
FLARE_EJECT_SPEED = 3.0               # px/frame initial drift
FLARE_DRAG = 0.94                     # per-frame velocity multiplier
FLARES_PER_SALVO = 3
FLARE_TRIGGER_RANGE = 240.0           # rocket-to-target distance that triggers the flare roll
FLARE_DECOY_CHANCE = 0.45             # chance a deployed salvo pulls the rocket off target (tuned via tests/test_rocket_balance.py)
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
# The beam turn alone cannot out-turn a homing rocket, so a well-timed break
# (fighter in MISSILE_DEFENSE when the rocket closes) gets one overshoot roll.
EVASION_ROLL_RANGE = 100.0
EVASION_SUCCESS_CHANCE = 0.20

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


def entity_center(entity) -> tuple:
    """World-space center of any Rect-like entity (uses x/y/width/height)."""
    return (entity.x + entity.width / 2, entity.y + entity.height / 2)


def spawn_flare_salvo(entity) -> List[Flare]:
    """Eject FLARES_PER_SALVO flares from the entity center, evenly spread around it."""
    cx, cy = entity_center(entity)
    flares = []
    for k in range(FLARES_PER_SALVO):
        theta = 2 * math.pi * k / FLARES_PER_SALVO
        flares.append(Flare(cx, cy, math.cos(theta) * FLARE_EJECT_SPEED, math.sin(theta) * FLARE_EJECT_SPEED))
    return flares


def update_rocket_countermeasures(rocket, rng: Optional[random.Random] = None) -> List[Flare]:
    """Roll the target's flare response once per rocket when it closes inside FLARE_TRIGGER_RANGE.

    Returns the newly ejected flares (empty list if none). A successful decoy roll
    re-targets the rocket onto the first flare and marks it `decoyed`.
    """
    if rocket.used or getattr(rocket, "decoyed", False) or getattr(rocket, "countermeasure_rolled", False):
        return []

    target = rocket.target
    if (
        not is_air_target(target)
        or getattr(target, "flares_remaining", 0) <= 0
        or getattr(target, "exploding", False)
        or getattr(target, "health", 0) <= 0
        or getattr(target, "stun_timer", 0) > 0
    ):
        return []

    rx, ry = entity_center(rocket)
    tx, ty = entity_center(target)
    if math.hypot(tx - rx, ty - ry) > FLARE_TRIGGER_RANGE:
        return []

    rocket.countermeasure_rolled = True
    rng = rng or _RNG
    if rng.random() >= getattr(target, "flare_deploy_chance", 0.0):
        return []

    target.flares_remaining -= 1
    flares = spawn_flare_salvo(target)
    if rng.random() < FLARE_DECOY_CHANCE:
        rocket.target = flares[0]
        rocket.decoyed = True
    return flares


def check_flare_detonation(rocket) -> bool:
    """Detonate a decoyed rocket on its flare once inside FLARE_DETONATION_RADIUS."""
    flare = rocket.target
    if not getattr(rocket, "decoyed", False) or not isinstance(flare, Flare) or not flare.is_alive:
        return False
    rx, ry = entity_center(rocket)
    fx, fy = flare.center()
    if math.hypot(fx - rx, fy - ry) > FLARE_DETONATION_RADIUS:
        return False
    rocket.used = True
    flare.health = 0.0
    return True


def draw_flares(surface: pygame.Surface, flares: Iterable[Flare],
                camera_x: float, camera_y: float) -> None:
    """Draw every alive flare as a glowing two-tone dot in screen space."""
    for flare in flares:
        if not flare.is_alive:
            continue
        cx, cy = flare.center()
        sx = int(cx - camera_x)
        sy = int(cy - camera_y)
        pygame.draw.circle(surface, FLARE_OUTER_COLOR, (sx, sy), 5)
        pygame.draw.circle(surface, FLARE_CORE_COLOR, (sx, sy), 2)


def find_incoming_rocket(enemy, rockets: Optional[Iterable],
                         warning_range: float = MISSILE_WARNING_RANGE):
    """Closest live, non-decoyed rocket homing on `enemy` within `warning_range`, else None."""
    if not rockets:
        return None
    ex, ey = entity_center(enemy)
    closest = None
    closest_dist = warning_range
    for rocket in rockets:
        if rocket.used or getattr(rocket, "decoyed", False) or rocket.target is not enemy:
            continue
        rx, ry = entity_center(rocket)
        dist = math.hypot(rx - ex, ry - ey)
        if dist <= closest_dist:
            closest = rocket
            closest_dist = dist
    return closest


def compute_beam_heading(enemy_cx: float, enemy_cy: float, enemy_angle: float,
                         rocket_cx: float, rocket_cy: float) -> float:
    """Enemy-convention heading perpendicular to the rocket line of sight, on the side needing the smaller turn. Returns degrees in [-180, 180)."""
    los = math.degrees(math.atan2(rocket_cx - enemy_cx, rocket_cy - enemy_cy))
    candidates = (los + 90.0, los - 90.0)
    best = min(candidates, key=lambda c: abs((c - enemy_angle + 180) % 360 - 180))
    return (best + 180) % 360 - 180


def update_rocket_evasion(rocket, rng: Optional[random.Random] = None) -> bool:
    """Roll once whether a breaking fighter makes the rocket overshoot.

    Applies only while the target is in the MISSILE_DEFENSE beam break and the
    rocket is within EVASION_ROLL_RANGE. On success the rocket loses its lock
    (`decoyed = True`, `target = None`), flies on ballistically and can no
    longer hit that target. Returns True on a successful evasion.
    """
    if rocket.used or getattr(rocket, "decoyed", False) or getattr(rocket, "evasion_rolled", False):
        return False

    target = rocket.target
    if (
        not is_air_target(target)
        or getattr(target, "bfm_mode", "") != "MISSILE_DEFENSE"
        or getattr(target, "exploding", False)
        or getattr(target, "health", 0) <= 0
        or getattr(target, "stun_timer", 0) > 0
    ):
        return False

    rx, ry = entity_center(rocket)
    tx, ty = entity_center(target)
    if math.hypot(tx - rx, ty - ry) > EVASION_ROLL_RANGE:
        return False

    rocket.evasion_rolled = True
    rng = rng or _RNG
    if rng.random() >= EVASION_SUCCESS_CHANCE:
        return False
    rocket.decoyed = True
    rocket.target = None
    return True
