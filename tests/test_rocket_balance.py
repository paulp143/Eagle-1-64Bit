"""Deterministic headless rocket-vs-fighter engagements that lock the countermeasure balance.

Rockets must stay valuable: evasion alone (beam break + overshoot roll) should rarely beat
a missile, and the full countermeasure set (evasion + flares) should keep the hit rate
inside a 50-80 % band.
"""

import math
import random

from eagle1.app import game
from eagle1.systems import missile_defense

ENGAGEMENTS = 200
MAX_FRAMES = 150


def _run_engagement(seed: int, evasion: bool, flares: bool) -> bool:
    rng = random.Random(seed)
    p = game.Player()
    p.pos_x, p.pos_y = 1500.0, 2400.0
    p.x, p.y = 1500, 2400
    p.angle = 0.0
    p.radar_mode = "CONE"

    pcx = p.pos_x + game.PLAYER_WIDTH / 2
    pcy = p.pos_y + game.PLAYER_HEIGHT / 2
    dist = rng.uniform(450.0, 850.0)
    off = math.radians(rng.uniform(-20.0, 20.0))
    ecx = pcx - math.sin(off) * dist
    ecy = pcy - math.cos(off) * dist

    enemy = game.Light_Enemy(
        x=ecx - game.LIGHT_ENEMY_WIDTH / 2, y=ecy - game.LIGHT_ENEMY_HEIGHT / 2, squadron_id=seed % 2
    )
    enemy.state = "AGRO"
    enemy.angle = rng.uniform(-180.0, 180.0)
    if not flares:
        enemy.flares_remaining = 0

    rocket = game.Player.Rocket(pcx - game.ROCKET_WIDTH / 2, pcy - game.ROCKET_HEIGHT / 2, p.angle, target=enemy)
    flare_list = []

    for _ in range(MAX_FRAMES):
        enemy.update(target_player=p, enemies=[enemy], speed_factor=1.0,
                     incoming_rockets=[rocket] if evasion else None)
        new_flares = missile_defense.update_rocket_countermeasures(rocket, rng=rng)
        flare_list += new_flares
        if not new_flares and evasion:
            missile_defense.update_rocket_evasion(rocket, rng=rng)
        for flare in flare_list:
            flare.update()
        rocket.update_position([enemy], player=p)
        missile_defense.check_flare_detonation(rocket)
        # Mirrors game.py: decoyed/evaded rockets can no longer fuse on a target
        if not rocket.used and not rocket.decoyed and rocket.colliderect(enemy):
            return True
        if rocket.used:
            return False
    return False


def _hit_rate(evasion: bool, flares: bool, n: int = ENGAGEMENTS) -> float:
    hits = sum(1 for seed in range(n) if _run_engagement(seed, evasion, flares))
    rate = hits / n
    print(f"rocket hit rate evasion={evasion} flares={flares}: {rate:.3f}")
    return rate


def test_baseline_rocket_tracking_is_reliable():
    assert _hit_rate(False, False) >= 0.90


def test_evasion_alone_does_not_neuter_rockets():
    assert 0.70 <= _hit_rate(True, False) <= 0.95


def test_full_countermeasures_hit_rate_band():
    assert 0.50 <= _hit_rate(True, True) <= 0.80
