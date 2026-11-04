"""campaign_session.py - Runtime bridge between the game loop and the campaign story systems.

Builds the per-sortie mission configuration and the per-frame combat telemetry snapshot
that the Narrative Trigger Manager evaluates. Duck-typed on the ground support manager
so this module never imports eagle1.systems at runtime (import cycle via eagle1.story).
"""

import logging
import math
from typing import TYPE_CHECKING, Any, Dict, FrozenSet, Mapping, Optional, Sequence

import pygame

from eagle1.story.campaign_act1 import register_act1_triggers, resolve_act1_choice
from eagle1.story.campaign_act2 import (
    SORTIE4_NUM,
    emit_sortie4_casualty_check,
    get_sortie3_braker_survived,
    register_act2_triggers,
    resolve_act2_choice,
)
from eagle1.story.mission_controller import (
    CAMPAIGN_SORTIE_REGISTRY,
    MAX_SORTIE_NUM,
    CampaignSortieConfig,
    MissionController,
)
from eagle1.story.narrative_trigger_manager import CombatTelemetrySnapshot, NarrativeTriggerManager
from eagle1.story.story_manager import StoryManager

if TYPE_CHECKING:
    from eagle1.story.comms_hud import CommsHUD

logger = logging.getLogger(__name__)

CAMPAIGN_SORTIE_CONFIG_KEY: str = "campaign_sortie"
BOMB_500KG_STRIKE_TYPE: str = "bomb_500kg"  # mirrors AirStrikeType.BOMB_500KG (asserted in tests)
HELLDIVER_CRITICAL_HEALTH_RATIO: float = 0.35  # mirrors GroundSupportManager low-health banter threshold
EXTRACTION_PHASE: str = "EXTRACTION"
WAVE_DRIVEN_MISSION_MODES: FrozenSet[str] = frozenset({"air_superiority", "base_defense", "outpost_demolition"})
DIALOGUE_CHOICE_KEYS: FrozenSet[int] = frozenset(
    {pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_KP1, pygame.K_KP2, pygame.K_KP3}
)


def build_campaign_mission_config(
    sortie_cfg: CampaignSortieConfig,
    base_configs: Mapping[str, Mapping[str, Any]],
) -> Dict[str, Any]:
    """Return a copy of the arcade mission config for the sortie's mode, tailored to the campaign sortie.

    Raises:
        TypeError: If sortie_cfg is not a CampaignSortieConfig.
        ValueError: If base_configs has no mapping for the sortie's mission mode.
    """
    if not isinstance(sortie_cfg, CampaignSortieConfig):
        raise TypeError("sortie_cfg must be a CampaignSortieConfig")

    base = base_configs.get(sortie_cfg.mission_mode) if isinstance(base_configs, Mapping) else None
    if not isinstance(base, Mapping):
        raise ValueError(f"No base mission config for mode '{sortie_cfg.mission_mode}'")

    config: Dict[str, Any] = dict(base)
    config["name"] = sortie_cfg.title
    config[CAMPAIGN_SORTIE_CONFIG_KEY] = sortie_cfg.sortie_num
    if sortie_cfg.mission_mode in WAVE_DRIVEN_MISSION_MODES:
        config["max_waves"] = sortie_cfg.target_waves
    if config.get("has_fabricators") and sortie_cfg.required_fabricators > 0:
        config["target_fabs"] = sortie_cfg.required_fabricators
    return config


def _list_attr(obj: Any, name: str) -> list:
    """Return obj.<name> if it is a list, otherwise an empty list."""
    value = getattr(obj, name, None)
    return value if isinstance(value, list) else []


def _non_negative_int_attr(obj: Any, name: str) -> int:
    """Return obj.<name> if it is a non-negative int (not bool), otherwise 0."""
    value = getattr(obj, name, 0)
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return 0
    return value


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _is_casualty(unit: Any) -> bool:
    """A Helldiver is a casualty when downed or out of health; extracted units are not losses."""
    if getattr(unit, "state", None) == "DOWNED":
        return True
    health = getattr(unit, "health", 0.0)
    return _is_number(health) and health <= 0


def _is_critical(unit: Any) -> bool:
    health = getattr(unit, "health", None)
    max_health = getattr(unit, "max_health", None)
    if not _is_number(health) or not _is_number(max_health) or max_health <= 0:
        return False
    return float(health) <= float(max_health) * HELLDIVER_CRITICAL_HEALTH_RATIO


def build_combat_telemetry(
    elapsed_seconds: float,
    current_wave: int,
    aerial_kills: int,
    ground_support_manager: Optional[Any] = None,
) -> CombatTelemetrySnapshot:
    """Build the sanitized telemetry snapshot evaluated by NarrativeTriggerManager for one frame."""
    gsm = ground_support_manager
    if gsm is None:
        return CombatTelemetrySnapshot(
            elapsed_seconds=elapsed_seconds,
            current_wave=current_wave,
            aerial_kills=aerial_kills,
        )

    units = _list_attr(gsm, "units")
    fabricators = _list_attr(gsm, "enemy_fabricators")
    strikes = _list_attr(gsm, "active_strikes")
    alive_units = [u for u in units if getattr(u, "is_alive", False)]
    casualties = sum(1 for u in units if _is_casualty(u))

    boss = getattr(gsm, "factory_strider", None)
    boss_active = boss is not None and bool(getattr(boss, "is_alive", False))
    boss_ratio = 1.0
    if boss_active:
        health = getattr(boss, "health", None)
        max_health = getattr(boss, "max_health", None)
        if _is_number(health) and _is_number(max_health) and max_health > 0:
            boss_ratio = float(health) / float(max_health)

    return CombatTelemetrySnapshot(
        elapsed_seconds=elapsed_seconds,
        current_wave=current_wave,
        aerial_kills=aerial_kills,
        ground_kills=_non_negative_int_attr(gsm, "total_cas_kills"),
        fabricators_destroyed=_non_negative_int_attr(gsm, "destroyed_fabs_count"),
        fabricators_remaining=sum(1 for f in fabricators if getattr(f, "is_alive", False)),
        boss_active=boss_active,
        boss_hp_ratio=boss_ratio,
        helldivers_alive=len(alive_units),
        casualties_count=casualties,
        any_helldiver_critical=any(_is_critical(u) for u in alive_units),
        active_500kg_inbound=any(getattr(s, "type", None) == BOMB_500KG_STRIKE_TYPE for s in strikes),
    )


class CampaignSortieSession:
    """Live campaign sortie state shared by the game loop, the comms HUD and the Super Destroyer hub."""

    def __init__(self, story_manager: StoryManager, comms_hud: Optional["CommsHUD"] = None) -> None:
        self.comms_hud = comms_hud
        self.is_flight_active: bool = False
        self.is_replay: bool = False
        self.active_sortie_num: Optional[int] = None
        self.flight_seconds: float = 0.0
        self._extraction_handled: bool = False
        self._casualty_check_pending: bool = False
        self.bind_story_manager(story_manager)

    def bind_story_manager(self, story_manager: StoryManager) -> None:
        """(Re)build the controller and trigger manager for a StoryManager and end any flight."""
        if not isinstance(story_manager, StoryManager):
            raise TypeError("story_manager must be a valid StoryManager instance")
        self.story_manager = story_manager
        self.mission_controller = MissionController(story_manager)
        self.trigger_manager = NarrativeTriggerManager(story_manager, self.comms_hud, self.mission_controller)
        register_act1_triggers(self.trigger_manager)
        register_act2_triggers(self.trigger_manager)
        self._end_flight()

    def _reset_flight_tracking(self) -> None:
        self.flight_seconds = 0.0
        self._extraction_handled = False
        self._casualty_check_pending = False

    def _end_flight(self) -> None:
        self.is_flight_active = False
        self.is_replay = False
        self.active_sortie_num = None
        self._reset_flight_tracking()

    def launch_sortie(self, sortie_num: Optional[int] = None) -> CampaignSortieConfig:
        """Start a campaign sortie; a completed campaign relaunches sortie 4 as a replay without progress."""
        if self.mission_controller.is_campaign_completed():
            cfg = CAMPAIGN_SORTIE_REGISTRY[MAX_SORTIE_NUM]
            self.is_replay = True
            self.mission_controller.current_objective = cfg.initial_objective
        else:
            cfg = self.mission_controller.start_sortie(sortie_num)
            self.is_replay = False

        self.trigger_manager.reset_for_sortie(cfg.sortie_num)
        self.story_manager.set_active_dialogue(None)
        self.active_sortie_num = cfg.sortie_num
        self.is_flight_active = True
        self._reset_flight_tracking()
        logger.info("Campaign sortie %d launched (replay=%s)", cfg.sortie_num, self.is_replay)
        return cfg

    def restart_flight(self) -> Optional[CampaignSortieConfig]:
        """Reset triggers and objective for the active sortie without advancing campaign progress."""
        if not self.is_flight_active or self.active_sortie_num is None:
            return None
        cfg = CAMPAIGN_SORTIE_REGISTRY[self.active_sortie_num]
        self.trigger_manager.reset_for_sortie(cfg.sortie_num)
        self.story_manager.set_active_dialogue(None)
        self.mission_controller.current_objective = cfg.initial_objective
        self._reset_flight_tracking()
        return cfg

    def abort_flight(self) -> None:
        """End the active flight; a non-replay sortie is marked as no longer active without progressing."""
        if not self.is_flight_active:
            return
        if not self.is_replay:
            self.mission_controller.abort_sortie()
        if self.active_sortie_num is not None:
            self.trigger_manager.reset_for_sortie(self.active_sortie_num)
        self.story_manager.set_active_dialogue(None)
        self._end_flight()

    def update(
        self,
        dt: float,
        current_wave: int,
        aerial_kills: int,
        ground_support_manager: Optional[Any] = None,
    ) -> Sequence[str]:
        """Advance the flight clock, evaluate narrative triggers and extraction beats for one frame."""
        if not self.is_flight_active:
            return ()
        if isinstance(dt, bool) or not isinstance(dt, (int, float)) or not math.isfinite(dt) or dt < 0:
            dt = 0.0
        self.flight_seconds += float(dt)
        telemetry = build_combat_telemetry(self.flight_seconds, current_wave, aerial_kills, ground_support_manager)
        fired = self.trigger_manager.evaluate(telemetry)
        self._update_extraction(telemetry, ground_support_manager)
        return fired

    def _update_extraction(self, telemetry: CombatTelemetrySnapshot, ground_support_manager: Optional[Any]) -> None:
        if not self._extraction_handled and getattr(ground_support_manager, "objective_phase", None) == EXTRACTION_PHASE:
            self._extraction_handled = True
            self.mission_controller.advance_to_extraction_objective()
            self._casualty_check_pending = self.active_sortie_num == SORTIE4_NUM

        if not self._casualty_check_pending:
            return
        if self.comms_hud is None:
            self._casualty_check_pending = False
            return
        if self.trigger_manager.is_comms_busy():
            return
        if emit_sortie4_casualty_check(
            self.comms_hud,
            telemetry.casualties_count,
            get_sortie3_braker_survived(self.story_manager),
        ):
            self._casualty_check_pending = False

    def handle_comms_keydown(self, event: Any, ground_support_manager: Optional[Any] = None) -> bool:
        """Route a key press to the comms HUD; return True if the key must not reach gameplay."""
        if getattr(event, "type", None) != pygame.KEYDOWN:
            return False

        hud = self.comms_hud
        consumed = False
        if hud is not None and hud.is_active:
            node = hud.current_node
            stance_before = hud.selected_stance
            consumed = bool(hud.handle_event(event))
            stance_after = hud.selected_stance
            if consumed and node is not None and node.options and stance_before is None and stance_after is not None:
                self.resolve_choice(node.node_id, stance_after, ground_support_manager)

        if not consumed and self.story_manager.is_dialogue_active and getattr(event, "key", None) in DIALOGUE_CHOICE_KEYS:
            return True
        return consumed

    def resolve_choice(self, node_id: str, stance: str, ground_support_manager: Optional[Any] = None) -> Optional[str]:
        """Apply the sortie-specific objective or battlefield consequence of a recorded radio choice."""
        if not self.is_flight_active:
            return None
        objective = resolve_act1_choice(node_id, stance, self.mission_controller)
        if objective is None:
            objective = resolve_act2_choice(
                node_id, stance, self.story_manager, ground_support_manager, self.mission_controller
            )
        if objective is not None:
            logger.info("Campaign choice resolved: node=%s stance=%s", node_id, stance)
        return objective

    def complete_sortie(self, debrief_results: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
        """End the flight and record campaign progress; replays and inactive flights record nothing."""
        if not self.is_flight_active:
            return {}
        was_replay = self.is_replay
        sortie_num = self.active_sortie_num
        if sortie_num is not None:
            self.trigger_manager.reset_for_sortie(sortie_num)
        self.story_manager.set_active_dialogue(None)
        self._end_flight()
        if was_replay:
            return {}

        results: Mapping[str, Any] = debrief_results if isinstance(debrief_results, Mapping) else {}
        return self.mission_controller.complete_current_sortie(
            casualties_count=results.get("casualties_count", 0),
            squad_wiped=results.get("squad_wiped", False),
            hull_ratio=results.get("hull_ratio", 1.0),
        )

    def get_objective_text(self) -> str:
        """Return the active HUD objective during a flight, otherwise an empty string."""
        return self.mission_controller.get_active_objective_text() if self.is_flight_active else ""
