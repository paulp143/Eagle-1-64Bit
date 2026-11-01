"""Unit and regression tests for CampaignSortieConfig and MissionController (Issue #67)."""

import dataclasses
from typing import Any
import pytest

from eagle1.story import (
    BRANCH_COLD_PROTOCOL,
    BRANCH_DISSIDENT_SURRENDER,
    BRANCH_OBEDIENCE_PURGE,
    CAMPAIGN_SORTIE_REGISTRY,
    MAX_SORTIE_NUM,
    MIN_SORTIE_NUM,
    SORTIE_BRIEFING_METADATA,
    SORTIE_MISSION_MAP,
    VALID_CAMPAIGN_MISSION_MODES,
    CampaignSaveManager,
    CampaignSortieConfig,
    MissionController,
    StoryManager,
    get_sortie_config,
    validate_sortie_registry,
)


@pytest.fixture
def story_mgr(tmp_path):
    """Fixture providing an isolated StoryManager backed by a temporary directory."""
    save_mgr = CampaignSaveManager(data_dir=tmp_path)
    return StoryManager(save_manager=save_mgr)


# -----------------------------------------------------------------------------
# 1. Registry Completeness & Hub Metadata Synchronization Tests
# -----------------------------------------------------------------------------

def test_campaign_sortie_registry_completeness_and_sync_with_hub_metadata():
    """Verify CAMPAIGN_SORTIE_REGISTRY defines sorties 1-4 matching SuperDestroyerView metadata."""
    assert validate_sortie_registry() is True
    assert set(CAMPAIGN_SORTIE_REGISTRY.keys()) == {1, 2, 3, 4}

    for s_num in range(MIN_SORTIE_NUM, MAX_SORTIE_NUM + 1):
        cfg = CAMPAIGN_SORTIE_REGISTRY[s_num]
        assert isinstance(cfg, CampaignSortieConfig)
        assert cfg.sortie_num == s_num
        assert cfg.mission_mode in VALID_CAMPAIGN_MISSION_MODES

        # Verify exact synchronization with SORTIE_MISSION_MAP
        assert cfg.mission_mode == SORTIE_MISSION_MAP[s_num]

        # Verify exact synchronization with SORTIE_BRIEFING_METADATA
        briefing = cfg.to_briefing_dict()
        expected = SORTIE_BRIEFING_METADATA[s_num]
        assert briefing["mission_id"] == expected["mission_id"]
        assert briefing["title"] == expected["title"]
        assert briefing["operation"] == expected["operation"]
        assert briefing["objective"] == expected["objective"]
        assert briefing["threat"] == expected["threat"]


# -----------------------------------------------------------------------------
# 2. Registry Validation & Integrity Tests
# -----------------------------------------------------------------------------

def test_validate_sortie_registry_rejects_malformed_configs():
    """Verify validate_sortie_registry strictly rejects invalid types, empty registries, or bad fields."""
    with pytest.raises(ValueError, match="non-empty dictionary"):
        validate_sortie_registry({})

    with pytest.raises(ValueError, match="non-empty dictionary"):
        validate_sortie_registry("invalid")  # type: ignore

    base_cfg = CAMPAIGN_SORTIE_REGISTRY[1]

    # Invalid act for sortie 1 (Sortie 1 must be act 1)
    bad_act = dict(CAMPAIGN_SORTIE_REGISTRY)
    bad_act[1] = dataclasses.replace(base_cfg, act=2)
    with pytest.raises(ValueError, match="must be Act 1"):
        validate_sortie_registry(bad_act)

    # Invalid act for sortie 3 (Sortie 3 must be act 2)
    bad_act_3 = dict(CAMPAIGN_SORTIE_REGISTRY)
    bad_act_3[3] = dataclasses.replace(CAMPAIGN_SORTIE_REGISTRY[3], act=1)
    with pytest.raises(ValueError, match="must be Act 2"):
        validate_sortie_registry(bad_act_3)

    # Invalid mission mode
    bad_mode = dict(CAMPAIGN_SORTIE_REGISTRY)
    bad_mode[1] = dataclasses.replace(base_cfg, mission_mode="orbital_strike")
    with pytest.raises(ValueError, match="invalid mission_mode"):
        validate_sortie_registry(bad_mode)

    # Empty string field
    bad_title = dict(CAMPAIGN_SORTIE_REGISTRY)
    bad_title[1] = dataclasses.replace(base_cfg, title="")
    with pytest.raises(ValueError, match="empty or non-string"):
        validate_sortie_registry(bad_title)

    # Target waves <= 0
    bad_waves = dict(CAMPAIGN_SORTIE_REGISTRY)
    bad_waves[1] = dataclasses.replace(base_cfg, target_waves=0)
    with pytest.raises(ValueError, match="target_waves must be > 0"):
        validate_sortie_registry(bad_waves)

    # Required fabricators < 0
    bad_fabs = dict(CAMPAIGN_SORTIE_REGISTRY)
    bad_fabs[1] = dataclasses.replace(base_cfg, required_fabricators=-1)
    with pytest.raises(ValueError, match="required_fabricators must be >= 0"):
        validate_sortie_registry(bad_fabs)

    # Empty inflight node IDs
    bad_nodes = dict(CAMPAIGN_SORTIE_REGISTRY)
    bad_nodes[1] = dataclasses.replace(base_cfg, inflight_node_ids=())
    with pytest.raises(ValueError, match="inflight_node_ids"):
        validate_sortie_registry(bad_nodes)


# -----------------------------------------------------------------------------
# 3. get_sortie_config Boundary & Type Safety Tests
# -----------------------------------------------------------------------------

@pytest.mark.parametrize(
    "invalid_key",
    [0, 5, -1, 100, 1.5, True, False, None, "1", "sortie_1", float("nan"), float("inf"), float("-inf"), [], {}],
)
def test_get_sortie_config_boundary_and_invalid_inputs(invalid_key: Any):
    """Verify get_sortie_config returns None for out-of-range, non-int, or non-finite inputs."""
    assert get_sortie_config(invalid_key) is None


def test_get_sortie_config_valid_keys():
    """Verify get_sortie_config retrieves expected configs for integer keys 1 through 4."""
    for s_num in range(MIN_SORTIE_NUM, MAX_SORTIE_NUM + 1):
        cfg = get_sortie_config(s_num)
        assert cfg is not None
        assert cfg.sortie_num == s_num


# -----------------------------------------------------------------------------
# 4. MissionController Initialization & Objective Tracking Tests
# -----------------------------------------------------------------------------

def test_mission_controller_init_and_objective_tracking(story_mgr):
    """Verify MissionController initialization, objective getters/setters, and extraction updates."""
    with pytest.raises(TypeError, match="story_manager must be a valid StoryManager"):
        MissionController(None)  # type: ignore

    with pytest.raises(TypeError, match="story_manager must be a valid StoryManager"):
        MissionController(True)  # type: ignore

    ctrl = MissionController(story_mgr)
    assert ctrl.active_sortie_num == 1
    assert ctrl.is_sortie_active is False
    assert ctrl.get_active_objective_text() == CAMPAIGN_SORTIE_REGISTRY[1].initial_objective

    # Test dynamic objective update
    ctrl.set_active_objective_text("Intercept Automaton Gunship Wing Alpha")
    assert ctrl.get_active_objective_text() == "Intercept Automaton Gunship Wing Alpha"

    # Test invalid objective text inputs are safely ignored
    for bad_text in ["", "   ", None, True, 123]:  # type: ignore
        ctrl.set_active_objective_text(bad_text)
    assert ctrl.get_active_objective_text() == "Intercept Automaton Gunship Wing Alpha"

    # Test extraction objective switch
    ext_obj = ctrl.advance_to_extraction_objective()
    assert ext_obj == CAMPAIGN_SORTIE_REGISTRY[1].extraction_objective
    assert ctrl.get_active_objective_text() == CAMPAIGN_SORTIE_REGISTRY[1].extraction_objective


# -----------------------------------------------------------------------------
# 5. Sequential Progression & Persistence Tests (Sorties 1 -> 4 -> Act III)
# -----------------------------------------------------------------------------

def test_sequential_progression_sortie_1_through_4_and_persistence(tmp_path):
    """Verify sequential completion from Sortie 1 through 4, Act transitions, and disk persistence."""
    save_mgr = CampaignSaveManager(data_dir=tmp_path)
    story = StoryManager(save_manager=save_mgr)
    ctrl = MissionController(story)

    assert story.current_act == 1
    assert story.current_sortie == 1
    assert ctrl.is_campaign_completed() is False

    # 1. Complete Sortie 1 (Act 1 -> stays Act 1, advances to Sortie 2)
    ctrl.start_sortie(1)
    assert ctrl.is_sortie_active is True
    res1 = ctrl.complete_current_sortie(casualties_count=0, squad_wiped=False, hull_ratio=1.0)
    assert res1["completed_sortie"] == 1
    assert res1["completed_act"] == 1
    assert res1["next_sortie"] == 2
    assert res1["next_act"] == 1
    assert res1["campaign_completed"] is False
    assert res1["ending_branch"] is None
    assert story.current_act == 1
    assert story.current_sortie == 2
    assert ctrl.completed_sorties == [1]

    # 2. Complete Sortie 2 (Act 1 -> transitions to Act 2, Sortie 3)
    ctrl.start_sortie(2)
    assert ctrl.is_sortie_active is True
    res2 = ctrl.complete_current_sortie(casualties_count=2, squad_wiped=False, hull_ratio=0.8)
    assert res2["completed_sortie"] == 2
    assert res2["completed_act"] == 1
    assert res2["next_sortie"] == 3
    assert res2["next_act"] == 2
    assert res2["campaign_completed"] is False
    assert story.current_act == 2
    assert story.current_sortie == 3
    assert ctrl.completed_sorties == [1, 2]

    # 3. Complete Sortie 3 (Act 2 -> stays Act 2, advances to Sortie 4)
    ctrl.start_sortie(3)
    assert ctrl.is_sortie_active is True
    res3 = ctrl.complete_current_sortie(casualties_count=1, squad_wiped=False, hull_ratio=0.5)
    assert res3["completed_sortie"] == 3
    assert res3["completed_act"] == 2
    assert res3["next_sortie"] == 4
    assert res3["next_act"] == 2
    assert res3["campaign_completed"] is False
    assert story.current_act == 2
    assert story.current_sortie == 4
    assert ctrl.completed_sorties == [1, 2, 3]

    # 4. Complete Sortie 4 (Act 2 -> marks Act 2 complete, transitions toward Act 3)
    ctrl.start_sortie(4)
    assert ctrl.is_sortie_active is True
    res4 = ctrl.complete_current_sortie(casualties_count=0, squad_wiped=False, hull_ratio=1.0)
    assert res4["completed_sortie"] == 4
    assert res4["completed_act"] == 2
    assert res4["next_sortie"] == 4
    assert res4["next_act"] == 3
    assert res4["campaign_completed"] is True
    assert res4["ending_branch"] == BRANCH_COLD_PROTOCOL
    assert ctrl.is_campaign_completed() is True
    assert ctrl.completed_sorties == [1, 2, 3, 4]

    # Reload from disk into a fresh instance and verify persistence
    fresh_save_mgr = CampaignSaveManager(data_dir=tmp_path)
    fresh_story = StoryManager(save_manager=fresh_save_mgr)
    fresh_ctrl = MissionController(fresh_story)

    assert fresh_story.current_act == 3
    assert fresh_story.current_sortie == 4
    assert fresh_ctrl.completed_sorties == [1, 2, 3, 4]
    assert fresh_ctrl.is_campaign_completed() is True
    assert fresh_story.extra.get("act2_completed") is True
    assert fresh_story.extra.get("ending_branch") == BRANCH_COLD_PROTOCOL


# -----------------------------------------------------------------------------
# 6. Ending Branch Climax Evaluation on Sortie 4 Completion
# -----------------------------------------------------------------------------

@pytest.mark.parametrize(
    ("loyalty_score", "expected_ending"),
    [
        (95.0, BRANCH_OBEDIENCE_PURGE),
        (90.0, BRANCH_OBEDIENCE_PURGE),
        (89.9, BRANCH_COLD_PROTOCOL),
        (50.0, BRANCH_COLD_PROTOCOL),
        (15.1, BRANCH_COLD_PROTOCOL),
        (15.0, BRANCH_DISSIDENT_SURRENDER),
        (5.0, BRANCH_DISSIDENT_SURRENDER),
    ],
)
def test_complete_sortie_4_evaluates_all_three_ending_branches(tmp_path, loyalty_score, expected_ending):
    """Verify completing Sortie 4 computes the exact narrative climax based on Loyalty."""
    save_mgr = CampaignSaveManager(data_dir=tmp_path)
    story = StoryManager(save_manager=save_mgr)
    story.loyalty = loyalty_score
    ctrl = MissionController(story)

    ctrl.start_sortie(4)
    res = ctrl.complete_current_sortie(casualties_count=0, squad_wiped=False, hull_ratio=1.0)

    assert res["campaign_completed"] is True
    assert res["ending_branch"] == expected_ending
    assert story.extra.get("ending_branch") == expected_ending


# -----------------------------------------------------------------------------
# 7. Start and Abort Sortie Mechanics
# -----------------------------------------------------------------------------

def test_start_and_abort_sortie_behavior(story_mgr):
    """Verify start_sortie activates mission state and abort_sortie cleanly restores initial objective."""
    ctrl = MissionController(story_mgr)

    # Start Sortie 3
    cfg3 = ctrl.start_sortie(3)
    assert cfg3.sortie_num == 3
    assert ctrl.active_sortie_num == 3
    assert ctrl.is_sortie_active is True
    assert story_mgr.current_act == 2
    assert story_mgr.current_sortie == 3
    assert ctrl.get_active_objective_text() == cfg3.initial_objective

    # Modify objective
    ctrl.set_active_objective_text("Mid-mission objective update")
    assert ctrl.get_active_objective_text() == "Mid-mission objective update"

    # Abort
    ctrl.abort_sortie()
    assert ctrl.is_sortie_active is False
    assert ctrl.get_active_objective_text() == cfg3.initial_objective
    assert ctrl.completed_sorties == []


# -----------------------------------------------------------------------------
# 8. Complete Sortie Robustness & NaN/Inf/Bool Sanitization
# -----------------------------------------------------------------------------

def test_complete_current_sortie_sanitizes_nan_inf_and_invalid_metrics(story_mgr):
    """Verify complete_current_sortie safely sanitizes NaN, infinite, boolean, and boundary metrics."""
    ctrl = MissionController(story_mgr)
    ctrl.start_sortie(1)

    # Corrupted float NaN / Inf
    res_nan = ctrl.complete_current_sortie(
        casualties_count=float("nan"),  # type: ignore
        squad_wiped="invalid",  # type: ignore
        hull_ratio=float("-inf"),  # type: ignore
    )
    assert res_nan["casualties_count"] == 0
    assert res_nan["squad_wiped"] is False
    assert res_nan["hull_ratio"] == 1.0

    # Upper boundary clamping
    ctrl.start_sortie(2)
    res_bound = ctrl.complete_current_sortie(
        casualties_count=4,
        squad_wiped=False,
        hull_ratio=2.5,
    )
    assert res_bound["casualties_count"] == 4
    # 4 casualties implies squad wipe automatically
    assert res_bound["squad_wiped"] is True
    assert res_bound["hull_ratio"] == 1.0

    # Negative values
    ctrl.start_sortie(3)
    res_neg = ctrl.complete_current_sortie(
        casualties_count=-10,
        squad_wiped=True,
        hull_ratio=-0.5,
    )
    assert res_neg["casualties_count"] == 0
    assert res_neg["squad_wiped"] is True
    assert res_neg["hull_ratio"] == 0.0


# -----------------------------------------------------------------------------
# 9. Pre-existing completed_sorties Sanitization & Reset Synchronization
# -----------------------------------------------------------------------------

def test_mission_controller_init_sanitizes_corrupt_completed_sorties(tmp_path):
    """Verify MissionController sanitizes booleans, invalid types, and out-of-range sorties from extra."""
    save_mgr = CampaignSaveManager(data_dir=tmp_path)
    story = StoryManager(save_manager=save_mgr)
    story.extra = {
        "completed_sorties": [True, False, 1, 2, 2, 5, -1, 0, "3", 3.5, None],
    }
    ctrl = MissionController(story)
    # Only valid distinct ints in range [1, 4] must survive (1 and 2)
    assert ctrl.completed_sorties == [1, 2]

    # Non-dict extra safety
    story.extra = "corrupt_string"  # type: ignore
    ctrl_fallback = MissionController(story)
    assert ctrl_fallback.completed_sorties == []


def test_mission_controller_sync_and_reset_on_campaign_reset(tmp_path):
    """Verify MissionController.reset and sync_from_story_manager re-sync when StoryManager resets."""
    save_mgr = CampaignSaveManager(data_dir=tmp_path)
    story = StoryManager(save_manager=save_mgr)
    ctrl = MissionController(story)

    # Complete Sortie 1
    ctrl.start_sortie(1)
    ctrl.complete_current_sortie()
    assert ctrl.completed_sorties == [1]

    # Reset campaign
    story.reset_campaign()
    assert story.current_sortie == 1
    assert story.extra.get("completed_sorties") is None

    # Reset controller
    ctrl.reset()
    assert ctrl.completed_sorties == []
    assert ctrl.active_sortie_num == 1
    assert ctrl.is_campaign_completed() is False


# -----------------------------------------------------------------------------
# 10. start_sortie Defaults and State Machine Inactive Protection
# -----------------------------------------------------------------------------

def test_start_sortie_with_default_none_and_completion_inactive_protection(story_mgr):
    """Verify start_sortie() with no arguments defaults to current sortie, and inactive calls are rejected."""
    ctrl = MissionController(story_mgr)
    story_mgr.advance_sortie(act=1, sortie=2)

    # Calling start_sortie() with None should resolve to current_sortie (2)
    cfg = ctrl.start_sortie(None)
    assert cfg.sortie_num == 2
    assert ctrl.active_sortie_num == 2
    assert ctrl.is_sortie_active is True

    # Complete sortie 2
    res2 = ctrl.complete_current_sortie(casualties_count=0, squad_wiped=False, hull_ratio=1.0)
    assert res2["completed_sortie"] == 2
    assert ctrl.is_sortie_active is False
    assert ctrl.active_sortie_num == 3

    # Call complete_current_sortie when NOT active: must be ignored and return {}
    res_inactive = ctrl.complete_current_sortie(casualties_count=1, squad_wiped=False, hull_ratio=0.9)
    assert res_inactive == {}
    assert ctrl.active_sortie_num == 3
    assert 3 not in ctrl.completed_sorties


# -----------------------------------------------------------------------------
# 11. Type Confusion (Bools-as-Ints), OverflowError & Casualties Invariants
# -----------------------------------------------------------------------------

def test_complete_current_sortie_type_confusion_and_boundary_invariants(story_mgr):
    """Verify boolean-as-int type confusion, overflow safety, and casualty boundary invariants."""
    ctrl = MissionController(story_mgr)

    # Type confusion: bool passed where int/float expected
    ctrl.start_sortie(1)
    res_bool = ctrl.complete_current_sortie(
        casualties_count=True,  # type: ignore (bool is int subclass)
        squad_wiped=1,          # type: ignore (truthy int instead of bool)
        hull_ratio=True,        # type: ignore (bool is int subclass)
    )
    assert res_bool["casualties_count"] == 0
    assert res_bool["squad_wiped"] is False
    assert res_bool["hull_ratio"] == 1.0

    # Boundary: casualties == 3 does not automatically wipe squad
    ctrl.start_sortie(2)
    res_c3 = ctrl.complete_current_sortie(casualties_count=3, squad_wiped=False, hull_ratio=0.5)
    assert res_c3["casualties_count"] == 3
    assert res_c3["squad_wiped"] is False

    # NaN hull_ratio defaults to 1.0
    ctrl.start_sortie(3)
    res_nan_hull = ctrl.complete_current_sortie(hull_ratio=float("nan"))
    assert res_nan_hull["hull_ratio"] == 1.0

    # Arbitrary huge integer (10**400) handling without OverflowError
    ctrl.start_sortie(4)
    res_huge = ctrl.complete_current_sortie(casualties_count=10**400)
    assert res_huge["casualties_count"] == 10**400
    assert res_huge["squad_wiped"] is True


def test_huge_integer_overflow_safety():
    """Verify get_sortie_config handles huge integers safely without OverflowError."""
    assert get_sortie_config(10**400) is None


# -----------------------------------------------------------------------------
# 12. is_campaign_completed Disjunctive Trigger Verification
# -----------------------------------------------------------------------------

def test_is_campaign_completed_individual_conditions(tmp_path):
    """Verify each independent condition of is_campaign_completed returns True."""
    save_mgr = CampaignSaveManager(data_dir=tmp_path)

    # 1. Triggered via completed_sorties containing MAX_SORTIE_NUM (4)
    story1 = StoryManager(save_manager=save_mgr)
    ctrl1 = MissionController(story1)
    ctrl1.completed_sorties = [4]
    assert ctrl1.is_campaign_completed() is True

    # 2. Triggered via act2_completed flag in extra
    story2 = StoryManager(save_manager=save_mgr)
    story2.extra = {"act2_completed": True}
    ctrl2 = MissionController(story2)
    assert ctrl2.is_campaign_completed() is True

    # 3. Triggered via current_act >= 3
    story3 = StoryManager(save_manager=save_mgr)
    story3.current_act = 3
    ctrl3 = MissionController(story3)
    assert ctrl3.is_campaign_completed() is True


# -----------------------------------------------------------------------------
# 13. validate_sortie_registry Comprehensive Error Branches
# -----------------------------------------------------------------------------

def test_validate_sortie_registry_additional_error_branches():
    """Verify validate_sortie_registry catches missing keys, non-configs, and bad fields."""
    base_cfg = CAMPAIGN_SORTIE_REGISTRY[1]

    # Partial dictionary missing required sorties
    with pytest.raises(ValueError, match="missing required sorties"):
        validate_sortie_registry({1: base_cfg})

    # Non-CampaignSortieConfig value in dictionary
    with pytest.raises(ValueError, match="not a CampaignSortieConfig"):
        bad_entries = dict(CAMPAIGN_SORTIE_REGISTRY)
        bad_entries[1] = "invalid_payload"  # type: ignore
        validate_sortie_registry(bad_entries)

    # Mismatched dictionary key and sortie_num
    with pytest.raises(ValueError, match="missing required sorties"):
        validate_sortie_registry({2: base_cfg, 3: CAMPAIGN_SORTIE_REGISTRY[3], 4: CAMPAIGN_SORTIE_REGISTRY[4], 5: CAMPAIGN_SORTIE_REGISTRY[2]})

    # Non-boolean has_boss_strider
    bad_boss = dict(CAMPAIGN_SORTIE_REGISTRY)
    bad_boss[1] = dataclasses.replace(base_cfg, has_boss_strider="yes")  # type: ignore
    with pytest.raises(ValueError, match="has_boss_strider must be a bool"):
        validate_sortie_registry(bad_boss)

    # Empty string inside inflight_node_ids tuple
    bad_node_id = dict(CAMPAIGN_SORTIE_REGISTRY)
    bad_node_id[1] = dataclasses.replace(base_cfg, inflight_node_ids=("",))
    with pytest.raises(ValueError, match="invalid inflight_node_id"):
        validate_sortie_registry(bad_node_id)


def test_set_active_objective_text_multiline_and_whitespace_normalization(story_mgr):
    """Verify set_active_objective_text strips newlines and normalizes whitespace."""
    ctrl = MissionController(story_mgr)
    ctrl.set_active_objective_text("  Engage Automaton\nFabricator\r\nComplex   ")
    assert ctrl.get_active_objective_text() == "Engage Automaton Fabricator Complex"
