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


def test_helldiver_extraction_no_kia():
    """Verify Helldivers boarding Pelican-1 are marked EXTRACTED without KIA penalty."""
    class MockPlayer:
        def __init__(self):
            self.pos_x = 500.0
            self.pos_y = 500.0
            self.score = 1000

    gsm = GroundSupportManager()
    assert gsm.flawless_protection is True
    assert gsm.survivors_count == 4

    # Setup extraction beacon with Pelican landed
    gsm.beacon.active = True
    gsm.beacon.pelican_arrived = True
    gsm.beacon.pelican_departed = False
    gsm.beacon.pelican_altitude = 0.0
    gsm.beacon.x = 500.0
    gsm.beacon.y = 500.0

    # Place Helldiver 0 right at the beacon
    lead = gsm.units[0]
    lead.pos_x = 500.0
    lead.pos_y = 500.0

    # Run update
    player = MockPlayer()
    gsm.update(0.016, player, [], [], 0)

    # Unit 0 must have boarded Pelican-1
    assert lead.state == "EXTRACTED"
    # Flawless protection must be retained
    assert gsm.flawless_protection is True
    # Extracted Helldivers must count as survivors
    assert gsm.survivors_count == 4
    # Check popups: must have EXTRACTED! and must NOT have KIA
    popup_texts = [p["text"] for p in gsm.floating_popups]
    assert any("EXTRACTED!" in t for t in popup_texts)
    assert not any("KIA" in t for t in popup_texts)
    # Score should not have casualty penalty applied
    assert player.score >= 1000

