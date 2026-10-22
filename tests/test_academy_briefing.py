"""Tests for AcademyTutorialManager, waypoint gates, drill progression, and Commander Vance comms."""

import pygame

from eagle1.systems.academy_briefing import (
    AcademyTutorialManager,
    AcademyWaypointGate,
    AcademyTargetDrone,
    AcademyTargetBunker,
    CommsHUDBox,
    DRILL_BRIEFING,
    DRILL_STEERING,
    DRILL_THROTTLE,
    DRILL_BORDER_SAFETY,
    DRILL_CANNONS,
    DRILL_RADAR_ROCKETS,
    DRILL_STRATAGEM,
    DRILL_GRADUATION,
    DRILL_COMPLETE,
)


class MockPlayer:
    """Mock Player object for headless academy testing."""
    def __init__(self, x=1500.0, y=1500.0):
        self.pos_x = float(x)
        self.pos_y = float(y)
        self.x = int(x)
        self.y = int(y)
        self.angle = 0.0
        self.velocity_x = 0.0
        self.velocity_y = 4.0
        self.speed = 4.0
        self.score = 0
        self.health = 5.0
        self.max_health = 5.0
        self.shield = 20.0
        self.used_bullets = 0
        self.max_bullets = 200
        self.bullets = []
        self.rockets = []
        self.radar_mode = "CONE"

    def get_forward_speed(self):
        import math
        return math.hypot(self.velocity_x, self.velocity_y)


def test_academy_manager_initial_state():
    """Verify default initial state of AcademyTutorialManager."""
    manager = AcademyTutorialManager()
    assert manager.state == DRILL_BRIEFING
    assert manager.is_completed is False
    assert manager.graduated is False
    assert "BRIEFING" in manager.get_active_drill_title().upper()
    assert "VANCE" in manager.comms_box.speaker_title.upper()


def test_waypoint_gate_collision():
    """Verify AcademyWaypointGate detection and radius checks."""
    gate = AcademyWaypointGate(x=1500.0, y=1500.0, radius=80.0, label="ALPHA")
    assert gate.cleared is False

    # Miss: too far
    assert gate.check_collision(1200.0, 1200.0) is False
    assert gate.cleared is False

    # Hit: inside gate radius
    assert gate.check_collision(1520.0, 1510.0) is True
    assert gate.cleared is True


def test_target_drone_damage_and_destruction():
    """Verify target drone takes damage and is destroyed."""
    drone = AcademyTargetDrone(x=1000.0, y=1000.0, max_health=50.0, label="DRONE-1")
    assert drone.is_alive is True

    drone.take_damage(20.0)
    assert drone.health == 30.0
    assert drone.is_alive is True

    drone.take_damage(35.0)
    assert drone.health <= 0.0
    assert drone.is_alive is False


def test_target_bunker_damage_and_destruction():
    """Verify target bunker takes air strike damage."""
    bunker = AcademyTargetBunker(x=1200.0, y=1200.0, max_health=100.0, label="TARGET FOUNDRY")
    assert bunker.is_alive is True

    bunker.take_damage(120.0)
    assert bunker.health <= 0.0
    assert bunker.is_alive is False


def test_drill_state_advancement_sequence():
    """Verify sequential advancement through all academy drills."""
    manager = AcademyTutorialManager()
    player = MockPlayer()

    assert manager.state == DRILL_BRIEFING
    manager.advance_drill(player)
    assert manager.state == DRILL_STEERING
    manager.advance_drill(player)
    assert manager.state == DRILL_THROTTLE
    manager.advance_drill(player)
    assert manager.state == DRILL_BORDER_SAFETY
    manager.advance_drill(player)
    assert manager.state == DRILL_CANNONS
    manager.advance_drill(player)
    assert manager.state == DRILL_RADAR_ROCKETS
    manager.advance_drill(player)
    assert manager.state == DRILL_STRATAGEM
    manager.advance_drill(player)
    assert manager.state == DRILL_GRADUATION
    manager.advance_drill(player)
    assert manager.state == DRILL_COMPLETE
    assert manager.is_completed is True


def test_throttle_drill_evaluation():
    """Verify throttle accumulator advances when high and low speed thresholds are maintained."""
    manager = AcademyTutorialManager()
    player = MockPlayer()
    manager.state = DRILL_THROTTLE

    # Simulate fast throttle (v = 7.0)
    player.velocity_y = 7.0
    keys_high = {pygame.K_w: True, pygame.K_s: False}

    # Step for 2.1 seconds at 60 FPS
    for _ in range(130):
        manager.update_throttle_drill(dt=1.0 / 60.0, player=player, keys=keys_high)

    assert manager.throttle_high_completed is True

    # Simulate air brakes / slow throttle (v = 2.0)
    player.velocity_y = 2.0
    keys_low = {pygame.K_w: False, pygame.K_s: True}
    for _ in range(130):
        manager.update_throttle_drill(dt=1.0 / 60.0, player=player, keys=keys_low)

    assert manager.throttle_low_completed is True


def test_headless_world_and_hud_draw(dummy_surface):
    """Verify draw_world and draw_hud execute cleanly in headless environment."""
    manager = AcademyTutorialManager()
    player = MockPlayer()
    manager.reset(player)

    manager.draw_world(dummy_surface, camera_x=0, camera_y=0)
    manager.draw_hud(dummy_surface, player=player)


def test_celebration_particle_mechanics():
    """Verify celebration particles decay and update positions cleanly."""
    from eagle1.systems.academy_briefing import AcademyCelebrationParticle
    p = AcademyCelebrationParticle(500.0, 300.0)
    assert p.is_alive is True
    init_life = p.lifetime

    p.update(0.1)
    assert p.lifetime < init_life
    assert p.is_alive is True

    # Advance until expiration
    p.update(3.0)
    assert p.is_alive is False


def test_graduation_ceremony_and_badge_draw(dummy_surface, tmp_path, monkeypatch):
    """Verify graduation ceremony triggers celebration, profile progression, and badge rendering."""
    from eagle1.data.player_profile import PlayerProfileManager
    monkeypatch.setenv("EAGLE1_USER_DATA_DIR", str(tmp_path))

    # Pre-create profile
    prof_mgr = PlayerProfileManager()
    prof = prof_mgr.create_profile("TEST-CADET", "E")
    assert prof.academy_completed is False

    manager = AcademyTutorialManager()
    player = MockPlayer()

    # Advance to graduation drill
    manager.state = DRILL_STRATAGEM
    manager.advance_drill(player)

    assert manager.state == DRILL_GRADUATION
    assert manager.graduated is True
    assert len(manager.celebration_particles) > 0

    # Profile updated
    reloaded = prof_mgr.load_profile()
    assert reloaded.academy_completed is True
    assert reloaded.active_mission == "air_superiority"
    assert reloaded.missions_cleared >= 1
    assert 3 in reloaded.unlocked_stratagems
    assert 4 in reloaded.unlocked_stratagems

    # Render HUD with graduation badge
    manager.draw_hud(dummy_surface, player=player)


def test_vance_comms_typewriter_and_audio():
    """Verify CommsHUDBox typewriter pacing and message setting."""
    box = CommsHUDBox()
    box.set_message("Test transmission for Cadet.", sfx_cue="radio_chatter")
    assert box.displayed_chars == 0
    assert box.is_finished is False

    box.update(0.5)
    assert box.displayed_chars > 0
    assert box.displayed_chars < len(box.full_text)

    # Complete text
    box.update(2.0)
    assert box.is_finished is True
    assert box.displayed_chars == len(box.full_text)


def test_academy_audio_assets_exist():
    """Verify that procedural audio generator produces required Phase 5 WAV files."""
    from eagle1.paths import PROJECT_ROOT
    audio_sfx_dir = PROJECT_ROOT / "audio" / "sfx"
    required = ["radio_chatter.wav", "gate_pass.wav", "drill_complete.wav", "ceremony_fanfare.wav"]
    for fname in required:
        assert (audio_sfx_dir / fname).is_file(), f"Missing audio asset {fname}"


def test_academy_minimap_rendering(dummy_surface):
    """Verify minimap drawing renders waypoints, boundary buffer, drones, and bunkers cleanly."""
    manager = AcademyTutorialManager()
    player = MockPlayer()
    manager.reset(player)

    # 1. Test steering waypoints
    manager.state = DRILL_STEERING
    mm_surf = pygame.Surface((170, 170), pygame.SRCALPHA)
    manager.draw_minimap(mm_surf, scale=170.0 / 3000.0)

    # 2. Test border safety boundary
    manager.state = DRILL_BORDER_SAFETY
    manager.draw_minimap(mm_surf, scale=170.0 / 3000.0)

    # 3. Test target drones
    manager.state = DRILL_CANNONS
    manager.target_drones = [
        AcademyTargetDrone(1400.0, 1200.0, max_health=40.0),
        AcademyTargetDrone(1600.0, 1200.0, max_health=40.0),
    ]
    manager.draw_minimap(mm_surf, scale=170.0 / 3000.0)

    # 4. Test target bunker
    manager.state = DRILL_STRATAGEM
    manager.target_bunker = AcademyTargetBunker(1500.0, 1100.0, max_health=100.0)
    manager.draw_minimap(mm_surf, scale=170.0 / 3000.0)

    # 5. Test graduation beacon
    manager.state = DRILL_GRADUATION
    manager.draw_minimap(mm_surf, scale=170.0 / 3000.0)


def test_compute_safe_drill_spawn_within_bounds():
    """Verify compute_safe_drill_spawn projects correctly when within map bounds."""
    from eagle1.systems.academy_briefing import compute_safe_drill_spawn, MAP_WIDTH, MAP_HEIGHT

    player = MockPlayer(1500.0, 1500.0)
    player.angle = 0.0  # North

    sx, sy = compute_safe_drill_spawn(player, forward_dist=500.0, right_offset=100.0)
    assert 0 < sx < MAP_WIDTH
    assert 0 < sy < MAP_HEIGHT
    assert sx == 1600.0
    assert sy == 1000.0


def test_compute_safe_drill_spawn_reroutes_from_borders():
    """Verify targets never spawn outside the map when player is near or facing borders."""
    from eagle1.systems.academy_briefing import compute_safe_drill_spawn, MAP_WIDTH, MAP_HEIGHT, ACADEMY_MAP_MARGIN

    # 1. Player near North border, facing North
    p_north = MockPlayer(1500.0, 100.0)
    p_north.angle = 0.0
    sx, sy = compute_safe_drill_spawn(p_north, forward_dist=500.0)
    assert ACADEMY_MAP_MARGIN <= sx <= MAP_WIDTH - ACADEMY_MAP_MARGIN
    assert ACADEMY_MAP_MARGIN <= sy <= MAP_HEIGHT - ACADEMY_MAP_MARGIN

    # 2. Player near South border, facing South
    p_south = MockPlayer(1500.0, 2900.0)
    p_south.angle = 180.0
    sx, sy = compute_safe_drill_spawn(p_south, forward_dist=500.0)
    assert ACADEMY_MAP_MARGIN <= sx <= MAP_WIDTH - ACADEMY_MAP_MARGIN
    assert ACADEMY_MAP_MARGIN <= sy <= MAP_HEIGHT - ACADEMY_MAP_MARGIN

    # 3. Player near West border, facing West
    p_west = MockPlayer(80.0, 1500.0)
    p_west.angle = 90.0
    sx, sy = compute_safe_drill_spawn(p_west, forward_dist=500.0)
    assert ACADEMY_MAP_MARGIN <= sx <= MAP_WIDTH - ACADEMY_MAP_MARGIN
    assert ACADEMY_MAP_MARGIN <= sy <= MAP_HEIGHT - ACADEMY_MAP_MARGIN

    # 4. Player near East border, facing East
    p_east = MockPlayer(2920.0, 1500.0)
    p_east.angle = 270.0
    sx, sy = compute_safe_drill_spawn(p_east, forward_dist=500.0)
    assert ACADEMY_MAP_MARGIN <= sx <= MAP_WIDTH - ACADEMY_MAP_MARGIN
    assert ACADEMY_MAP_MARGIN <= sy <= MAP_HEIGHT - ACADEMY_MAP_MARGIN


def test_academy_advance_drill_never_spawns_off_map():
    """Verify that advancing drills when near borders places all enemies and bunkers inside the map."""
    from eagle1.systems.academy_briefing import MAP_WIDTH, MAP_HEIGHT

    manager = AcademyTutorialManager()
    player = MockPlayer(1500.0, 120.0)  # Near top border
    player.angle = 0.0  # Flying North

    # Advance to Cannons drill
    manager.state = DRILL_BORDER_SAFETY
    manager.advance_drill(player)
    assert manager.state == DRILL_CANNONS
    assert len(manager.target_drones) == 3
    for drone in manager.target_drones:
        assert 0 <= drone.pos_x <= MAP_WIDTH
        assert 0 <= drone.pos_y <= MAP_HEIGHT
        assert 0 <= drone.x <= MAP_WIDTH
        assert 0 <= drone.y <= MAP_HEIGHT

    # Advance to Radar Rockets drill
    manager.advance_drill(player)
    assert manager.state == DRILL_RADAR_ROCKETS
    assert len(manager.target_drones) == 2
    for drone in manager.target_drones:
        assert 0 <= drone.pos_x <= MAP_WIDTH
        assert 0 <= drone.pos_y <= MAP_HEIGHT
        assert 0 <= drone.x <= MAP_WIDTH
        assert 0 <= drone.y <= MAP_HEIGHT

    # Advance to Stratagem drill
    manager.advance_drill(player)
    assert manager.state == DRILL_STRATAGEM
    assert manager.target_bunker is not None
    assert 0 <= manager.target_bunker.pos_x <= MAP_WIDTH
    assert 0 <= manager.target_bunker.pos_y <= MAP_HEIGHT
    assert 0 <= manager.target_bunker.x <= MAP_WIDTH
    assert 0 <= manager.target_bunker.y <= MAP_HEIGHT


def test_academy_waypoint_gates_clamp_on_reset():
    """Verify reset() clamps waypoint gates when player is near edge."""
    from eagle1.systems.academy_briefing import MAP_WIDTH, MAP_HEIGHT

    manager = AcademyTutorialManager()
    player = MockPlayer(1500.0, 100.0)
    manager.reset(player)

    assert len(manager.waypoint_gates) == 3
    for gate in manager.waypoint_gates:
        assert 0 <= gate.x <= MAP_WIDTH
        assert 0 <= gate.y <= MAP_HEIGHT


def test_entity_out_of_bounds_clamping():
    """Verify entities created with out-of-bounds coordinates clamp automatically."""
    from eagle1.systems.academy_briefing import (
        AcademyWaypointGate,
        AcademyTargetDrone,
        AcademyTargetBunker,
        MAP_WIDTH,
        MAP_HEIGHT,
    )

    # Negative coordinates
    gate = AcademyWaypointGate(-500.0, -200.0, radius=85.0)
    assert gate.x >= gate.radius
    assert gate.y >= gate.radius

    drone = AcademyTargetDrone(-100.0, -100.0)
    assert drone.pos_x >= 50.0
    assert drone.pos_y >= 50.0
    assert drone.x >= 0
    assert drone.y >= 0

    bunker = AcademyTargetBunker(-50.0, -50.0)
    assert bunker.pos_x >= 80.0
    assert bunker.pos_y >= 80.0
    assert bunker.x >= 0
    assert bunker.y >= 0

    # Oversized coordinates (> 3000)
    gate_over = AcademyWaypointGate(5000.0, 5000.0, radius=85.0)
    assert gate_over.x <= MAP_WIDTH - gate_over.radius
    assert gate_over.y <= MAP_HEIGHT - gate_over.radius

    drone_over = AcademyTargetDrone(4000.0, 4000.0)
    assert drone_over.pos_x <= MAP_WIDTH - 50.0
    assert drone_over.pos_y <= MAP_HEIGHT - 50.0

    bunker_over = AcademyTargetBunker(4000.0, 4000.0)
    assert bunker_over.pos_x <= MAP_WIDTH - 80.0
    assert bunker_over.pos_y <= MAP_HEIGHT - 80.0


def test_mobile_drone_stays_in_bounds():
    """Verify mobile drone movement updates do not drift outside map boundaries."""
    from eagle1.systems.academy_briefing import AcademyTargetDrone, MAP_WIDTH, MAP_HEIGHT

    # Place drone at edge and simulate movement
    drone = AcademyTargetDrone(52.0, 52.0, is_mobile=True)
    for _ in range(500):
        drone.update(0.1)
        assert 0 <= drone.pos_x <= MAP_WIDTH
        assert 0 <= drone.pos_y <= MAP_HEIGHT
        assert 0 <= drone.x <= MAP_WIDTH
        assert 0 <= drone.y <= MAP_HEIGHT



