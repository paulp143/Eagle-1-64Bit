"""Tests for campaign_session helpers: mission config mapping and combat telemetry snapshots."""

import copy
import math
from types import SimpleNamespace

import pytest

from eagle1.story.campaign_session import (
    BOMB_500KG_STRIKE_TYPE,
    CAMPAIGN_SORTIE_CONFIG_KEY,
    build_campaign_mission_config,
    build_combat_telemetry,
)
from eagle1.story.mission_controller import CAMPAIGN_SORTIE_REGISTRY
from eagle1.systems.ground_support import AirStrikeType, GroundSupportManager

BASE_CONFIGS = {
    "air_superiority": {"id": "air_superiority", "name": "AIR SUPERIORITY", "has_ground": False,
                        "has_fabricators": False, "max_waves": 5},
    "base_defense": {"id": "base_defense", "name": "ORBITAL BASE DEFENSE", "has_ground": False,
                     "has_fabricators": False, "max_waves": 5},
    "outpost_demolition": {"id": "outpost_demolition", "name": "OUTPOST DEMOLITION", "has_ground": True,
                           "has_fabricators": True, "max_waves": 6, "target_fabs": 3},
    "strider_raid": {"id": "strider_raid", "name": "FACTORY STRIDER RAID", "has_ground": True,
                     "has_fabricators": False, "has_strider": True, "max_waves": 1},
}


def test_bomb_500kg_constant_matches_ground_support():
    assert BOMB_500KG_STRIKE_TYPE == AirStrikeType.BOMB_500KG


@pytest.mark.parametrize("sortie_num", [1, 2, 3, 4])
def test_build_mission_config_per_sortie(sortie_num):
    cfg = CAMPAIGN_SORTIE_REGISTRY[sortie_num]
    config = build_campaign_mission_config(cfg, BASE_CONFIGS)
    assert config["id"] == cfg.mission_mode
    assert config["name"] == cfg.title
    assert config[CAMPAIGN_SORTIE_CONFIG_KEY] == sortie_num
    if sortie_num == 4:
        assert config["max_waves"] == 1  # strider_raid is not wave driven
    else:
        assert config["max_waves"] == cfg.target_waves


def test_build_mission_config_sets_fabricator_target_for_sortie3():
    config = build_campaign_mission_config(CAMPAIGN_SORTIE_REGISTRY[3], BASE_CONFIGS)
    assert config["target_fabs"] == 3


def test_build_mission_config_does_not_mutate_base():
    snapshot = copy.deepcopy(BASE_CONFIGS)
    build_campaign_mission_config(CAMPAIGN_SORTIE_REGISTRY[1], BASE_CONFIGS)
    assert BASE_CONFIGS == snapshot


def test_build_mission_config_rejects_invalid():
    with pytest.raises(TypeError):
        build_campaign_mission_config(None, BASE_CONFIGS)
    with pytest.raises(ValueError):
        build_campaign_mission_config(CAMPAIGN_SORTIE_REGISTRY[1], {})
    with pytest.raises(ValueError):
        build_campaign_mission_config(CAMPAIGN_SORTIE_REGISTRY[1], None)


def test_telemetry_without_gsm():
    snap = build_combat_telemetry(5.0, 2, 7, None)
    assert snap.current_wave == 2
    assert snap.aerial_kills == 7
    assert snap.casualties_count == 0
    assert snap.boss_active is False


def test_telemetry_from_default_gsm():
    gsm = GroundSupportManager()
    snap = build_combat_telemetry(0.0, 1, 0, gsm)
    assert snap.helldivers_alive == 4
    assert snap.casualties_count == 0
    assert snap.fabricators_remaining == 1
    assert snap.boss_active is False


def test_telemetry_counts_casualties_and_critical():
    gsm = GroundSupportManager()
    gsm.units[0].health = 0.0
    gsm.units[0].state = "DOWNED"
    gsm.units[1].health = gsm.units[1].max_health * 0.2
    gsm.units[2].state = "EXTRACTED"
    snap = build_combat_telemetry(0.0, 1, 0, gsm)
    assert snap.casualties_count == 1  # extracted is not a loss
    assert snap.helldivers_alive == 2
    assert snap.any_helldiver_critical is True


def test_telemetry_boss_ratio():
    gsm = GroundSupportManager()
    gsm._spawn_world({"has_ground": True, "has_strider": True})
    gsm.factory_strider.health = gsm.factory_strider.max_health * 0.4
    snap = build_combat_telemetry(0.0, 1, 0, gsm)
    assert snap.boss_active is True
    assert snap.boss_hp_ratio == pytest.approx(0.4)


def test_telemetry_500kg_inbound():
    gsm = GroundSupportManager()
    gsm.active_strikes = [SimpleNamespace(type=BOMB_500KG_STRIKE_TYPE)]
    assert build_combat_telemetry(0.0, 1, 0, gsm).active_500kg_inbound is True
    gsm.active_strikes = [SimpleNamespace(type="napalm")]
    assert build_combat_telemetry(0.0, 1, 0, gsm).active_500kg_inbound is False


def test_telemetry_tolerates_garbage_gsm():
    gsm = SimpleNamespace(
        units="x",
        enemy_fabricators=None,
        factory_strider=SimpleNamespace(is_alive=True, health="?", max_health=0),
    )
    snap = build_combat_telemetry(0.0, 1, 0, gsm)
    assert snap.boss_hp_ratio == 1.0
    assert snap.casualties_count == 0


def test_telemetry_sanitizes_elapsed():
    snap = build_combat_telemetry(float("nan"), 1, 0, None)
    assert snap.elapsed_seconds == 0.0
    assert not math.isnan(snap.elapsed_seconds)
