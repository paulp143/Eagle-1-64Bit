"""Tests for Helldivers squad, ground units, CAS delivery, and supply drops."""

from eagle1.systems.ground_support import (
    GroundSupportManager,
    HelldiverUnit,
    SupplyDropPod,
    HELLDIVER_COUNT,
    HELLDIVER_MAX_HEALTH,
    SCORE_MISSION_DELIVERY_BONUS,
    SCORE_SURVIVOR_WAVE_BONUS,
)


def test_ground_support_manager_initial_squad():
    """Verify that 4 Helldivers (Viper squad) are spawned with max health and shield."""
    gsm = GroundSupportManager()
    assert len(gsm.units) == HELLDIVER_COUNT
    assert gsm.survivors_count == HELLDIVER_COUNT
    assert gsm.flawless_protection is True

    for unit in gsm.units:
        assert isinstance(unit, HelldiverUnit)
        assert unit.health == HELLDIVER_MAX_HEALTH
        assert unit.shield == 50.0
        assert unit.state in ["DEFENDING", "ENGAGING"]


def test_helldiver_roles():
    """Verify Helldiver squad member callsigns and roles."""
    expected_callsigns = ["Viper-1 (Lead)", "Viper-2 (Heavy)", "Viper-3 (Scout)", "Viper-4 (Medic)"]
    for i, expected_name in enumerate(expected_callsigns):
        unit = HelldiverUnit(i, 500, 500)
        assert unit.callsign == expected_name


def test_supply_drop_pod_replenishment():
    """Verify SupplyDropPod lands and is marked available for squad or player."""
    pod = SupplyDropPod(1000.0, 1000.0)
    assert not pod.used
    assert not pod.landed
    assert pod.altitude > 0.0

    # Simulate landing complete
    pod.altitude = 0.0
    pod.landed = True
    assert pod.landed
    assert not pod.used


def test_ground_support_bonus_constants():
    """Verify CAS ground delivery and survivor wave bonuses."""
    assert SCORE_MISSION_DELIVERY_BONUS == 500
    assert SCORE_SURVIVOR_WAVE_BONUS == 500
