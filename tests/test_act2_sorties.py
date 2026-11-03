"""Tests for the Act II campaign (#70): Sortie 3 and Sortie 4 dialogue, triggers, 500kg crisis and casualty check."""

import pytest

from eagle1.story.mission_controller import CAMPAIGN_SORTIE_REGISTRY, validate_sortie_registry
from eagle1.story.campaign_act1 import register_act1_triggers
from eagle1.story.campaign_act2 import (
    ACT2_CHOICE_OBJECTIVES,
    ACT2_TRIGGERS,
    BRAKER_UNIT_INDEX,
    CASUALTY_CHECK_FLAWLESS_BRAKER,
    CASUALTY_CHECK_FLAWLESS_MEMORIAL,
    CASUALTY_CHECK_PARTIAL_BRAKER,
    CASUALTY_CHECK_PARTIAL_MEMORIAL,
    CASUALTY_CHECK_WIPED,
    SORTIE3_CRISIS_NODE_ID,
    SORTIE3_EXTRACTION_WAVE,
    SORTIE3_LOYAL_NET_LOYALTY_DELTA,
    SORTIE3_OBJECTIVE_DISSIDENT,
    SORTIE3_OBJECTIVE_LOYAL,
    SORTIE3_OBJECTIVE_NEUTRAL,
    SORTIE3_OUTCOME_EXTRA_KEY,
    SORTIE4_CRISIS_NODE_ID,
    SORTIE4_EXTRACTION_WAVE,
    SORTIE4_OBJECTIVE_DISSIDENT,
    SORTIE4_OBJECTIVE_LOYAL,
    SORTIE4_OBJECTIVE_NEUTRAL,
    apply_sortie4_choice_effect,
    emit_sortie4_casualty_check,
    get_sortie3_braker_survived,
    get_sortie4_casualty_check_banter,
    get_sortie4_casualty_check_category,
    register_act2_triggers,
    resolve_act2_choice,
    resolve_sortie3_500kg_choice,
)
from eagle1.story.campaign_save import CampaignSaveManager
from eagle1.story.comms_hud import CommsHUD
from eagle1.story.mission_controller import MissionController
from eagle1.story.narrative_trigger_manager import (
    CombatTelemetrySnapshot,
    NarrativeTriggerManager,
    validate_sortie_event_trigger,
)
from eagle1.systems.ground_support import GroundSupportManager
from eagle1.story.story_manager import DEFAULT_LOYALTY, VALID_STANCES, StoryManager
from eagle1.story.dialogue_data import BANTER_QUEUES, get_contextual_banter, validate_viper_dialogue_data
from eagle1.story.dialogue_db import (
    DIALOGUE_DATABASE,
    get_dialogue_node,
    get_nodes_for_act_and_sortie,
    validate_dialogue_database,
)


# -----------------------------------------------------------------------------
# 1. Act II dialogue nodes
# -----------------------------------------------------------------------------

ACT2_NODE_IDS = (
    ("sortie_3_briefing", 3),
    ("sortie_3_500kg_crisis", 3),
    ("sortie_3_hangar_debrief", 3),
    ("sortie_4_briefing", 4),
    ("sortie_4_strider_crisis", 4),
    ("sortie_4_hangar_debrief", 4),
)


def test_act2_dialogue_database_is_valid():
    """The full dialogue database, including Act II nodes, passes validation."""
    assert validate_dialogue_database(DIALOGUE_DATABASE) is True


@pytest.mark.parametrize("node_id, expected_sortie", ACT2_NODE_IDS)
def test_act2_required_nodes_exist(node_id, expected_sortie):
    """Each Act II node resolves and carries the correct act and sortie."""
    node = get_dialogue_node(node_id)
    assert node is not None
    assert node.act == 2
    assert node.sortie == expected_sortie


@pytest.mark.parametrize(
    "sortie, expected",
    [
        (3, {"sortie_3_briefing", "sortie_3_500kg_crisis", "sortie_3_hangar_debrief"}),
        (4, {"sortie_4_briefing", "sortie_4_strider_crisis", "sortie_4_hangar_debrief"}),
    ],
)
def test_act2_nodes_listed_per_sortie(sortie, expected):
    """get_nodes_for_act_and_sortie(2, n) lists the Act II nodes of that sortie."""
    node_ids = {n.node_id for n in get_nodes_for_act_and_sortie(act=2, sortie=sortie)}
    assert expected <= node_ids


@pytest.mark.parametrize(
    "node_id, loyal, neutral, dissident",
    [
        ("sortie_3_500kg_crisis", 12.0, 0.0, -12.0),
        ("sortie_4_strider_crisis", 10.0, 0.0, -10.0),
    ],
)
def test_act2_inflight_loyalty_deltas(node_id, loyal, neutral, dissident):
    """In-flight Act II nodes carry the documented loyalty deltas."""
    node = get_dialogue_node(node_id)
    assert node.options["loyal"].loyalty_delta == pytest.approx(loyal)
    assert node.options["neutral"].loyalty_delta == pytest.approx(neutral)
    assert node.options["dissident"].loyalty_delta == pytest.approx(dissident)


def test_500kg_crisis_option_labels_match_issue():
    """The 500kg crisis options use the labels specified in issue #70."""
    node = get_dialogue_node("sortie_3_500kg_crisis")
    assert "Acceptable collateral damage" in node.options["loyal"].label
    assert "15 meters east" in node.options["neutral"].label
    assert "Aborting drop" in node.options["dissident"].label


# -----------------------------------------------------------------------------
# 2. Sortie registry
# -----------------------------------------------------------------------------

@pytest.mark.parametrize("sortie_num", [3, 4])
def test_sortie_registry_act2_node_ids_resolve(sortie_num):
    """Every node referenced by the Act II registry entries resolves in the dialogue database."""
    assert validate_sortie_registry() is True
    cfg = CAMPAIGN_SORTIE_REGISTRY[sortie_num]
    for node_id in (cfg.briefing_node_id, *cfg.inflight_node_ids, cfg.debrief_node_id):
        assert get_dialogue_node(node_id) is not None


def test_sortie_registry_uses_act2_nodes():
    """Sorties 3 and 4 point at their Act II briefing, in-flight and debrief nodes."""
    sortie3 = CAMPAIGN_SORTIE_REGISTRY[3]
    assert sortie3.briefing_node_id == "sortie_3_briefing"
    assert sortie3.inflight_node_ids == ("sortie_3_500kg_crisis",)
    assert sortie3.debrief_node_id == "sortie_3_hangar_debrief"

    sortie4 = CAMPAIGN_SORTIE_REGISTRY[4]
    assert sortie4.briefing_node_id == "sortie_4_briefing"
    assert sortie4.inflight_node_ids == ("sortie_4_strider_crisis",)
    assert sortie4.debrief_node_id == "sortie_4_hangar_debrief"


# -----------------------------------------------------------------------------
# 3. Act II banter categories
# -----------------------------------------------------------------------------

ACT2_BANTER_CATEGORIES = (
    "act2_s3_approach_ghost",
    "act2_s3_extraction_pelican",
    "act2_s4_strider_arrival_ghost",
    "act2_s4_extraction_pelican",
    "act2_s4_check_flawless_braker",
    "act2_s4_check_flawless_memorial",
    "act2_s4_check_partial_braker",
    "act2_s4_check_partial_memorial",
    "act2_s4_check_wiped",
)


@pytest.mark.parametrize("category", ACT2_BANTER_CATEGORIES)
def test_act2_banter_categories_have_single_line(category):
    """Each Act II banter category holds exactly one deterministic line."""
    assert category in BANTER_QUEUES
    lines = BANTER_QUEUES[category]
    assert len(lines) == 1
    assert lines[0].category == category
    assert lines[0].line_id == f"{category}_01"


@pytest.mark.parametrize("category", ACT2_BANTER_CATEGORIES)
def test_act2_banter_is_deterministic(category):
    """Selection ignores the index for single-line categories."""
    assert get_contextual_banter(category, selection_index=0) is get_contextual_banter(category, selection_index=7)


def test_viper_dialogue_data_still_valid():
    """The Viper dialogue data, including Act II banter, still validates."""
    assert validate_viper_dialogue_data() is True


# -----------------------------------------------------------------------------
# 4. Scripted casualty hook
# -----------------------------------------------------------------------------

def test_apply_scripted_casualty_downs_living_unit():
    """A scripted casualty downs a living Helldiver and clears the flawless flag."""
    gsm = GroundSupportManager()
    assert gsm.apply_scripted_casualty(1) is True
    unit = next(u for u in gsm.units if u.index == 1)
    assert unit.state == "DOWNED"
    assert unit.health == 0.0
    assert not unit.is_alive
    assert 1 in gsm._downed_unit_ids
    assert gsm.flawless_protection is False


def test_apply_scripted_casualty_is_not_reported_twice(tmp_path):
    """The downed unit is pre-marked so update() does not notify the StoryManager again."""
    story = StoryManager(save_manager=CampaignSaveManager(data_dir=tmp_path))
    gsm = GroundSupportManager()
    gsm.set_story_manager(story)
    assert gsm.apply_scripted_casualty(1) is True
    assert story.total_casualties == 0
    assert 1 in gsm._downed_unit_ids


@pytest.mark.parametrize("bad_index", [1, 99, True, "1"])
def test_apply_scripted_casualty_rejects_dead_or_unknown(bad_index):
    """Unknown, non-int and already downed indices are rejected without mutation."""
    gsm = GroundSupportManager()
    gsm.apply_scripted_casualty(1)
    assert gsm.apply_scripted_casualty(bad_index) is False


# -----------------------------------------------------------------------------
# 5. Act II trigger table and registration
# -----------------------------------------------------------------------------

@pytest.fixture
def story_mgr(tmp_path):
    """Isolated StoryManager backed by a temporary save directory."""
    return StoryManager(save_manager=CampaignSaveManager(data_dir=tmp_path))


@pytest.fixture
def mission_ctrl(story_mgr):
    return MissionController(story_mgr)


@pytest.fixture
def comms(story_mgr):
    return CommsHUD(story_manager=story_mgr)


@pytest.fixture
def manager(story_mgr, comms, mission_ctrl):
    """NarrativeTriggerManager with all Act II triggers registered."""
    mgr = NarrativeTriggerManager(story_mgr, comms_hud=comms, mission_controller=mission_ctrl)
    register_act2_triggers(mgr)
    return mgr


def _predicate(trigger_id):
    return next(t.predicate for t in ACT2_TRIGGERS if t.trigger_id == trigger_id)


def test_act2_triggers_are_valid():
    """Every Act II trigger passes the trigger validator."""
    for trigger in ACT2_TRIGGERS:
        validate_sortie_event_trigger(trigger)


def test_act2_trigger_ids_unique_and_scoped():
    """Trigger ids are unique and each id prefix matches its sortie."""
    ids = [t.trigger_id for t in ACT2_TRIGGERS]
    assert len(ids) == len(set(ids))
    for trigger in ACT2_TRIGGERS:
        expected = 3 if trigger.trigger_id.startswith("act2_s3_") else 4
        assert trigger.trigger_id.startswith(f"act2_s{expected}_")
        assert trigger.sortie_num == expected


def test_act2_priorities_follow_story_order():
    """Within each sortie, priorities strictly decrease in story order."""
    for sortie_num in (3, 4):
        priorities = [t.priority for t in ACT2_TRIGGERS if t.sortie_num == sortie_num]
        assert priorities == sorted(priorities, reverse=True)
        assert len(set(priorities)) == len(priorities)


def test_register_act2_triggers_returns_count(story_mgr):
    """Registration reports six triggers, three per sortie."""
    mgr = NarrativeTriggerManager(story_mgr)
    assert register_act2_triggers(mgr) == 6
    assert len(mgr.get_triggers_for_sortie(3)) == 3
    assert len(mgr.get_triggers_for_sortie(4)) == 3


def test_register_act2_triggers_twice_is_rejected_atomically(manager):
    """A second registration fails and leaves the trigger count unchanged."""
    with pytest.raises(ValueError, match="already registered"):
        register_act2_triggers(manager)
    assert len(manager.get_triggers_for_sortie(3)) == 3
    assert len(manager.get_triggers_for_sortie(4)) == 3


@pytest.mark.parametrize("bad_manager", [None, "mgr", object()])
def test_register_act2_triggers_rejects_invalid_manager(bad_manager):
    """Anything that is not a NarrativeTriggerManager is rejected with TypeError."""
    with pytest.raises(TypeError):
        register_act2_triggers(bad_manager)


def test_act1_and_act2_triggers_coexist(story_mgr):
    """Act I and Act II triggers register side by side without id clashes."""
    mgr = NarrativeTriggerManager(story_mgr)
    register_act1_triggers(mgr)
    register_act2_triggers(mgr)
    assert [len(mgr.get_triggers_for_sortie(n)) for n in (1, 2, 3, 4)] == [5, 3, 3, 3]


def test_extraction_waves_match_registry():
    """Extraction callouts fire on the registry's final wave for each sortie."""
    assert SORTIE3_EXTRACTION_WAVE == 4
    assert SORTIE4_EXTRACTION_WAVE == 5


def test_sortie3_crisis_predicate():
    """The 500kg crisis fires on a fabricator kill, an inbound strike, or wave 2."""
    predicate = _predicate("act2_s3_500kg_crisis")
    assert predicate(CombatTelemetrySnapshot(current_wave=1)) is False
    assert predicate(CombatTelemetrySnapshot(current_wave=1, fabricators_destroyed=1)) is True
    assert predicate(CombatTelemetrySnapshot(current_wave=1, active_500kg_inbound=True)) is True
    assert predicate(CombatTelemetrySnapshot(current_wave=2)) is True


def test_sortie4_predicates():
    """Strider arrival and crisis predicates follow boss activity and HP."""
    arrival = _predicate("act2_s4_strider_arrival")
    crisis = _predicate("act2_s4_strider_crisis")
    assert arrival(CombatTelemetrySnapshot(boss_active=False)) is False
    assert arrival(CombatTelemetrySnapshot(boss_active=True)) is True

    assert crisis(CombatTelemetrySnapshot(boss_active=True, boss_hp_ratio=0.5)) is False
    assert crisis(CombatTelemetrySnapshot(boss_active=True, boss_hp_ratio=0.49)) is True
    assert crisis(CombatTelemetrySnapshot(boss_active=True, boss_hp_ratio=0.9, any_helldiver_critical=True)) is True
    assert crisis(CombatTelemetrySnapshot(boss_active=False, boss_hp_ratio=0.1)) is False


# -----------------------------------------------------------------------------
# 6. 500kg crisis and Sortie 4 choice effects
# -----------------------------------------------------------------------------

def _fresh_gsm():
    return GroundSupportManager()


def _braker(gsm):
    return next(u for u in gsm.units if u.index == BRAKER_UNIT_INDEX)


def test_choice_objectives_cover_all_stances():
    """Both in-flight Act II nodes map every stance to a non-empty HUD objective."""
    for node_id in (SORTIE3_CRISIS_NODE_ID, SORTIE4_CRISIS_NODE_ID):
        choices = ACT2_CHOICE_OBJECTIVES[node_id]
        assert set(choices) == set(VALID_STANCES)
        for text in choices.values():
            assert text.strip()
            assert len(text) <= 250


def test_500kg_loyal_with_live_gsm(story_mgr, mission_ctrl):
    """LOYAL destroys the fabricator, kills Braker and nets +8.5 loyalty after the casualty."""
    gsm = _fresh_gsm()
    fab = gsm.enemy_fabricators[0]
    story_mgr.record_choice(SORTIE3_CRISIS_NODE_ID, "loyal")
    outcome = resolve_sortie3_500kg_choice("loyal", story_mgr, gsm, mission_ctrl)
    assert outcome.fabricator_destroyed
    assert not fab.is_alive
    assert outcome.braker_killed_by_strike
    assert not outcome.braker_survived
    assert not _braker(gsm).is_alive
    assert BRAKER_UNIT_INDEX in gsm._downed_unit_ids
    assert story_mgr.total_casualties == 1
    assert story_mgr.loyalty == pytest.approx(DEFAULT_LOYALTY + SORTIE3_LOYAL_NET_LOYALTY_DELTA)
    assert SORTIE3_LOYAL_NET_LOYALTY_DELTA == pytest.approx(12.0 - 3.5)
    assert mission_ctrl.current_objective == SORTIE3_OBJECTIVE_LOYAL
    assert get_sortie3_braker_survived(story_mgr) is False


def test_500kg_neutral_with_live_gsm(story_mgr, mission_ctrl):
    """NEUTRAL halves the fabricator and wounds Braker without killing him."""
    gsm = _fresh_gsm()
    fab = gsm.enemy_fabricators[0]
    story_mgr.record_choice(SORTIE3_CRISIS_NODE_ID, "neutral")
    outcome = resolve_sortie3_500kg_choice("neutral", story_mgr, gsm, mission_ctrl)
    assert fab.health == pytest.approx(fab.max_health * 0.5)
    assert fab.is_alive
    assert not outcome.fabricator_destroyed
    braker = _braker(gsm)
    assert braker.is_alive
    assert braker.health == pytest.approx(braker.max_health * 0.25)
    assert braker.shield == 0.0
    assert outcome.braker_wounded
    assert outcome.braker_survived
    assert story_mgr.total_casualties == 0
    assert story_mgr.loyalty == pytest.approx(DEFAULT_LOYALTY)
    assert mission_ctrl.current_objective == SORTIE3_OBJECTIVE_NEUTRAL
    assert get_sortie3_braker_survived(story_mgr) is True


def test_500kg_neutral_keeps_lower_braker_health(story_mgr):
    """NEUTRAL never heals Braker when he already has less health than the wound level."""
    gsm = _fresh_gsm()
    _braker(gsm).health = 10.0
    resolve_sortie3_500kg_choice("neutral", story_mgr, gsm)
    assert _braker(gsm).health == pytest.approx(10.0)


def test_500kg_dissident_with_live_gsm(story_mgr, mission_ctrl):
    """DISSIDENT aborts the drop: no entity changes and loyalty drops by 12."""
    gsm = _fresh_gsm()
    fab = gsm.enemy_fabricators[0]
    braker = _braker(gsm)
    health_before = braker.health
    shield_before = braker.shield
    story_mgr.record_choice(SORTIE3_CRISIS_NODE_ID, "dissident")
    outcome = resolve_sortie3_500kg_choice("dissident", story_mgr, gsm, mission_ctrl)
    assert fab.health == pytest.approx(fab.max_health)
    assert braker.health == pytest.approx(health_before)
    assert braker.shield == pytest.approx(shield_before)
    assert outcome.braker_survived
    assert story_mgr.loyalty == pytest.approx(DEFAULT_LOYALTY - 12.0)
    assert mission_ctrl.current_objective == SORTIE3_OBJECTIVE_DISSIDENT
    assert story_mgr.total_casualties == 0


def test_500kg_loyal_does_not_double_kill_dead_braker(story_mgr):
    """A LOYAL drop on an already downed Braker records no second casualty."""
    gsm = _fresh_gsm()
    gsm.apply_scripted_casualty(BRAKER_UNIT_INDEX)
    story_mgr.record_choice(SORTIE3_CRISIS_NODE_ID, "loyal")
    outcome = resolve_sortie3_500kg_choice("loyal", story_mgr, gsm)
    assert not outcome.braker_killed_by_strike
    assert not outcome.braker_survived
    assert story_mgr.total_casualties == 0
    assert story_mgr.loyalty == pytest.approx(DEFAULT_LOYALTY + 12.0)


@pytest.mark.parametrize(
    "stance, killed, wounded, casualties",
    [
        ("loyal", True, False, 1),
        ("neutral", False, True, 0),
        ("dissident", False, False, 0),
    ],
)
def test_500kg_without_gsm(story_mgr, stance, killed, wounded, casualties):
    """Without a ground support manager Braker is assumed alive and no entity is touched."""
    outcome = resolve_sortie3_500kg_choice(stance, story_mgr, None)
    assert outcome.braker_killed_by_strike is killed
    assert outcome.braker_wounded is wounded
    assert outcome.fabricator_destroyed is False
    assert story_mgr.total_casualties == casualties


def test_500kg_without_fabricators_or_units(story_mgr):
    """A mission without ground forces yields no fabricator kill and no Braker casualty."""
    gsm = GroundSupportManager()
    gsm._spawn_world({"has_ground": False})
    outcome = resolve_sortie3_500kg_choice("loyal", story_mgr, gsm)
    assert outcome.fabricator_destroyed is False
    assert outcome.braker_killed_by_strike is False
    assert outcome.braker_survived is False
    assert story_mgr.total_casualties == 0


@pytest.mark.parametrize("bad_stance", ["", "maybe", None, 4, True])
def test_500kg_invalid_stance_mutates_nothing(story_mgr, bad_stance):
    """An invalid stance returns None and leaves world and story state untouched."""
    gsm = _fresh_gsm()
    fab_health = gsm.enemy_fabricators[0].health
    braker_health = _braker(gsm).health
    assert resolve_sortie3_500kg_choice(bad_stance, story_mgr, gsm) is None
    assert gsm.enemy_fabricators[0].health == fab_health
    assert _braker(gsm).health == braker_health
    assert SORTIE3_OUTCOME_EXTRA_KEY not in story_mgr.extra


@pytest.mark.parametrize("alias, canonical", [("1", "loyal"), ("[NEUTRAL]", "neutral"), (" Dissident ", "dissident")])
def test_500kg_accepts_aliases(story_mgr, alias, canonical):
    """Key numbers, bracketed and padded stance names normalize to the canonical stance."""
    outcome = resolve_sortie3_500kg_choice(alias, story_mgr, None)
    assert outcome.stance == canonical


def test_500kg_invalid_gsm_is_ignored(story_mgr):
    """A non-manager object is ignored and the abstract mode applies."""
    outcome = resolve_sortie3_500kg_choice("loyal", story_mgr, "gsm")
    assert outcome.braker_killed_by_strike is True


def test_500kg_without_story_manager():
    """Entity effects still apply when no StoryManager is wired."""
    gsm = _fresh_gsm()
    outcome = resolve_sortie3_500kg_choice("loyal", None, gsm)
    assert outcome.fabricator_destroyed
    assert outcome.braker_killed_by_strike


def test_500kg_outcome_is_persisted(tmp_path):
    """The Sortie 3 outcome survives a save and reload of the campaign."""
    story = StoryManager(save_manager=CampaignSaveManager(data_dir=tmp_path))
    resolve_sortie3_500kg_choice("dissident", story, None)
    reloaded = StoryManager(save_manager=CampaignSaveManager(data_dir=tmp_path))
    assert get_sortie3_braker_survived(reloaded) is True
    assert reloaded.extra[SORTIE3_OUTCOME_EXTRA_KEY]["stance"] == "dissident"


def test_get_sortie3_braker_survived_defaults_to_true(story_mgr):
    """Missing or malformed outcome records default to Braker surviving."""
    assert get_sortie3_braker_survived(None) is True
    assert get_sortie3_braker_survived(story_mgr) is True
    story_mgr.extra[SORTIE3_OUTCOME_EXTRA_KEY] = "bad"
    assert get_sortie3_braker_survived(story_mgr) is True
    story_mgr.extra[SORTIE3_OUTCOME_EXTRA_KEY] = {"braker_survived": "no"}
    assert get_sortie3_braker_survived(story_mgr) is True


@pytest.mark.parametrize(
    "stance, expected",
    [
        ("loyal", SORTIE4_OBJECTIVE_LOYAL),
        ("neutral", SORTIE4_OBJECTIVE_NEUTRAL),
        ("dissident", SORTIE4_OBJECTIVE_DISSIDENT),
    ],
)
def test_apply_sortie4_choice_effect_sets_objective(mission_ctrl, stance, expected):
    """Each Sortie 4 stance sets its HUD objective."""
    assert apply_sortie4_choice_effect(stance, mission_ctrl) == expected
    assert mission_ctrl.current_objective == expected


def test_apply_sortie4_choice_effect_rejects_invalid(mission_ctrl):
    """Invalid stances and a missing controller apply nothing."""
    assert apply_sortie4_choice_effect("maybe", mission_ctrl) is None
    assert apply_sortie4_choice_effect("loyal", None) is None


def test_resolve_act2_choice_routes_and_ignores_foreign_nodes(story_mgr, mission_ctrl):
    """The Act II router dispatches to its two in-flight nodes and ignores everything else."""
    assert resolve_act2_choice(SORTIE3_CRISIS_NODE_ID, "dissident", story_mgr, None, mission_ctrl) == SORTIE3_OBJECTIVE_DISSIDENT
    assert resolve_act2_choice(SORTIE4_CRISIS_NODE_ID, "neutral", story_mgr, None, mission_ctrl) == SORTIE4_OBJECTIVE_NEUTRAL
    for foreign in ("sortie_1_inflight", "  ", None, True):
        assert resolve_act2_choice(foreign, "loyal", story_mgr, None, mission_ctrl) is None


# -----------------------------------------------------------------------------
# 7. Sortie 4 casualty check
# -----------------------------------------------------------------------------

@pytest.mark.parametrize(
    "casualties, braker_survived, expected",
    [
        (0, True, CASUALTY_CHECK_FLAWLESS_BRAKER),
        (0, False, CASUALTY_CHECK_FLAWLESS_MEMORIAL),
        (1, True, CASUALTY_CHECK_PARTIAL_BRAKER),
        (3, True, CASUALTY_CHECK_PARTIAL_BRAKER),
        (2, False, CASUALTY_CHECK_PARTIAL_MEMORIAL),
        (4, True, CASUALTY_CHECK_WIPED),
        (4, False, CASUALTY_CHECK_WIPED),
        (7, True, CASUALTY_CHECK_WIPED),
    ],
)
def test_casualty_check_categories(casualties, braker_survived, expected):
    """Casualty counts and the Sortie 3 outcome select the matching banter category."""
    assert get_sortie4_casualty_check_category(casualties, braker_survived) == expected


@pytest.mark.parametrize("bad_count", [-1, True, float("nan"), float("inf"), "3", None])
def test_casualty_check_sanitizes_counts(bad_count):
    """Garbage counts fall back to zero casualties."""
    assert get_sortie4_casualty_check_category(bad_count) == CASUALTY_CHECK_FLAWLESS_BRAKER


def test_casualty_check_truncates_float_counts():
    """Fractional counts truncate toward zero."""
    assert get_sortie4_casualty_check_category(2.9) == CASUALTY_CHECK_PARTIAL_BRAKER


def test_casualty_check_invalid_braker_flag_defaults_to_survived():
    """A non-bool braker flag is treated as Braker surviving."""
    assert get_sortie4_casualty_check_category(0, "no") == CASUALTY_CHECK_FLAWLESS_BRAKER


@pytest.mark.parametrize("casualties", [1, 2, 3, 4])
def test_casualty_check_lines_are_spoken_by_pelican_after_losses(casualties):
    """After any loss Pelican-1 speaks, so no possibly fallen squad member is heard."""
    line = get_sortie4_casualty_check_banter(casualties, True)
    assert line.speaker == "Pelican-1"
    assert line.category == get_sortie4_casualty_check_category(casualties, True)


def test_casualty_check_flawless_lines_name_the_right_speaker():
    """A flawless extraction is spoken by Braker, or by Doc when Braker fell earlier."""
    assert "Braker" in get_sortie4_casualty_check_banter(0, True).speaker
    memorial = get_sortie4_casualty_check_banter(0, False)
    assert "Doc" in memorial.speaker
    assert "Braker" in memorial.text


def test_emit_casualty_check_on_comms(comms):
    """The casualty check is shown on the comms HUD with the selected line."""
    assert emit_sortie4_casualty_check(comms, 2, False) is True
    assert comms.is_active
    assert comms.current_node.prompt == get_sortie4_casualty_check_banter(2, False).text


def test_emit_casualty_check_without_comms():
    """Without a comms HUD nothing is shown."""
    assert emit_sortie4_casualty_check(None, 0) is False
