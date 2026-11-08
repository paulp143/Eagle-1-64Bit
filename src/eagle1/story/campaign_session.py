"""campaign_session.py - Runtime bridge between the game loop and the campaign story systems.

Builds the per-sortie mission configuration and the per-frame combat telemetry snapshot
that the Narrative Trigger Manager evaluates. Duck-typed on the ground support manager
so this module never imports eagle1.systems at runtime (import cycle via eagle1.story).
"""

import logging
import math
from typing import TYPE_CHECKING, Any, Dict, FrozenSet, Mapping, Optional, Sequence, Tuple

import pygame

from eagle1.story.campaign_act1 import register_act1_triggers, resolve_act1_choice
from eagle1.story.campaign_act3 import (
    ACT3_BRIEFING_NPC_IDS,
    ACT3_ENDLESS_WAVES,
    ACT3_MISSION_OVERRIDES,
    ACT3_NUM,
    ACT3_OUTRO_SECONDS,
    ACT3C_TIMER_URGENT_SECONDS,
    SORTIE5B_LANDING_MIN_DELAY_SECONDS,
    SORTIE5B_LANDING_SPEED_TOLERANCE,
    build_ending_cinematic,
    format_extraction_timer,
    get_act3c_extraction_timer_seconds,
    get_act3_sortie_config,
    get_locked_ending_branch,
    is_act3_climax_already_resolved,
    is_act3_finale_pending,
    is_in_scrap_yard_landing_zone,
    register_act3_triggers_for_branch,
    resolve_act3_choice,
)
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
from eagle1.story.story_manager import BRANCH_COLD_PROTOCOL, BRANCH_DISSIDENT_SURRENDER, StoryManager

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
    overrides = ACT3_MISSION_OVERRIDES.get(sortie_cfg.sortie_id)
    if overrides is not None:
        config.update(overrides)
        config["max_waves"] = ACT3_ENDLESS_WAVES
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
        self.player: Optional[Any] = None
        self.act3_branch: Optional[str] = None
        self.act3_config: Optional[CampaignSortieConfig] = None
        self.act3_resolved_at: Optional[float] = None
        self.bind_story_manager(story_manager)

    def bind_story_manager(self, story_manager: StoryManager) -> None:
        """(Re)build the controller and trigger manager for a StoryManager and end any flight."""
        if not isinstance(story_manager, StoryManager):
            raise TypeError("story_manager must be a valid StoryManager instance")
        self.story_manager = story_manager
        self.mission_controller = MissionController(story_manager)
        self._rebuild_trigger_manager(None)
        self._end_flight()

    def _rebuild_trigger_manager(self, branch: Optional[str]) -> None:
        """Create a fresh trigger manager with Act I/II triggers and, if given, one Act III branch set."""
        self.trigger_manager = NarrativeTriggerManager(self.story_manager, self.comms_hud, self.mission_controller)
        register_act1_triggers(self.trigger_manager)
        register_act2_triggers(self.trigger_manager)
        if branch is not None:
            register_act3_triggers_for_branch(self.trigger_manager, branch)

    def _reset_flight_tracking(self) -> None:
        self.flight_seconds = 0.0
        self._extraction_handled = False
        self._casualty_check_pending = False
        self.act3_resolved_at = None

    def _end_flight(self) -> None:
        self.is_flight_active = False
        self.is_replay = False
        self.active_sortie_num = None
        self.act3_branch = None
        self.act3_config = None
        self._reset_flight_tracking()

    def launch_sortie(self, sortie_num: Optional[int] = None) -> CampaignSortieConfig:
        """Start a campaign sortie; a completed campaign relaunches sortie 4 as a replay without progress."""
        if self.is_act3_finale_pending():
            return self._launch_act3_sortie()
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
        cfg = self.act3_config if self.is_act3_flight else CAMPAIGN_SORTIE_REGISTRY[self.active_sortie_num]
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
        if not self.is_act3_flight:
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

    def handle_comms_keydown(self, event: Any, ground_support_manager: Optional[Any] = None, player: Optional[Any] = None) -> bool:
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
                self.resolve_choice(node.node_id, stance_after, ground_support_manager, player)

        if not consumed and self.story_manager.is_dialogue_active and getattr(event, "key", None) in DIALOGUE_CHOICE_KEYS:
            return True
        return consumed

    def resolve_choice(
        self,
        node_id: str,
        stance: str,
        ground_support_manager: Optional[Any] = None,
        player: Optional[Any] = None,
    ) -> Optional[str]:
        """Apply the sortie-specific objective or battlefield consequence of a recorded radio choice."""
        if not self.is_flight_active:
            return None
        if self.is_act3_flight:
            return self._resolve_act3_choice(node_id, stance, ground_support_manager, player)
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
        if self.is_act3_flight:
            logger.warning("complete_sortie ignored during an Act III flight")
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

    # ------------------------------------------------------------------
    # Act III flight (#77)
    # ------------------------------------------------------------------
    @property
    def is_act3_flight(self) -> bool:
        return self.is_flight_active and self.act3_branch is not None

    @property
    def is_act3_resolved(self) -> bool:
        return self.is_act3_flight and self.act3_resolved_at is not None

    def attach_player(self, player: Optional[Any]) -> None:
        """Keep the player used for Act III effects such as the Sortie 5B weapon disarmament."""
        self.player = player

    def is_act3_finale_pending(self) -> bool:
        return is_act3_finale_pending(self.story_manager)

    def should_skip_to_finale_cinematic(self) -> bool:
        """True if the locked branch's climax was already resolved (e.g. the game was closed after it)."""
        if not self.is_act3_finale_pending():
            return False
        return is_act3_climax_already_resolved(self.story_manager, get_locked_ending_branch(self.story_manager))

    def get_act3_hub_briefing(self) -> Tuple[Optional[CampaignSortieConfig], Optional[str]]:
        """Return the Act III sortie config and briefing NPC for the hub, or (None, None) outside the finale."""
        if not self.is_act3_finale_pending():
            return None, None
        branch = get_locked_ending_branch(self.story_manager)
        return get_act3_sortie_config(branch), ACT3_BRIEFING_NPC_IDS.get(branch)

    def resolve_hub_choice(self, node_id: str, stance: str) -> Optional[str]:
        """Route the Act III briefing choice made in the Super Destroyer hub."""
        if not self.is_act3_finale_pending():
            return None
        branch = get_locked_ending_branch(self.story_manager)
        cfg = get_act3_sortie_config(branch)
        if cfg is None or not isinstance(node_id, str) or node_id.strip() != cfg.briefing_node_id:
            return None
        return resolve_act3_choice(branch, node_id, stance, self.story_manager)

    def _launch_act3_sortie(self) -> CampaignSortieConfig:
        branch = get_locked_ending_branch(self.story_manager)
        cfg = get_act3_sortie_config(branch)
        if cfg is None:
            raise ValueError(f"No Act III sortie for branch {branch!r}")
        self._rebuild_trigger_manager(branch)
        self.trigger_manager.reset_for_sortie(cfg.sortie_num)
        self.story_manager.set_active_dialogue(None)
        if self.story_manager.current_sortie < cfg.sortie_num:
            self.story_manager.advance_sortie(act=ACT3_NUM, sortie=cfg.sortie_num)
        self.mission_controller.is_sortie_active = False
        self.mission_controller.current_objective = cfg.initial_objective
        self.is_replay = False
        self.active_sortie_num = cfg.sortie_num
        self.is_flight_active = True
        self.act3_branch = branch
        self.act3_config = cfg
        self._reset_flight_tracking()
        logger.info("Act III sortie %s launched (branch=%s)", cfg.sortie_id, branch)
        return cfg

    def _resolve_act3_choice(
        self,
        node_id: str,
        stance: str,
        ground_support_manager: Optional[Any],
        player: Optional[Any],
    ) -> Optional[str]:
        actor = player if player is not None else self.player
        objective = resolve_act3_choice(
            self.act3_branch,
            node_id,
            stance,
            self.story_manager,
            actor,
            ground_support_manager,
            self.mission_controller,
            self.comms_hud,
        )
        clean_id = node_id.strip() if isinstance(node_id, str) else ""
        if objective is not None and self.act3_resolved_at is None and clean_id in self.act3_config.inflight_node_ids:
            self.act3_resolved_at = self.flight_seconds
            logger.info("Act III climax resolved: node=%s t=%.2f", clean_id, self.flight_seconds)
        return objective

    def get_act3_extraction_timer_text(self) -> Optional[str]:
        """HUD countdown for Sortie 5C until the abort is resolved; None elsewhere."""
        if not self.is_act3_flight or self.act3_branch != BRANCH_COLD_PROTOCOL or self.act3_resolved_at is not None:
            return None
        return format_extraction_timer(get_act3c_extraction_timer_seconds(self.flight_seconds))

    def is_act3_extraction_timer_urgent(self) -> bool:
        if self.get_act3_extraction_timer_text() is None:
            return False
        return get_act3c_extraction_timer_seconds(self.flight_seconds) <= ACT3C_TIMER_URGENT_SECONDS

    def is_act3_climax_complete(
        self,
        center_x: float,
        center_y: float,
        speed: float,
        min_speed: float,
        player_alive: bool,
    ) -> bool:
        """True once the resolved Act III climax may end: a dead pilot ends it, otherwise the branch rule applies."""
        if not self.is_act3_resolved:
            return False
        if not player_alive:
            return True
        since = self.flight_seconds - self.act3_resolved_at
        if self.act3_branch == BRANCH_DISSIDENT_SURRENDER:
            if not (_is_number(speed) and _is_number(min_speed)) or since < SORTIE5B_LANDING_MIN_DELAY_SECONDS:
                return False
            landed_slowly = float(speed) <= float(min_speed) + SORTIE5B_LANDING_SPEED_TOLERANCE
            return is_in_scrap_yard_landing_zone(center_x, center_y) and landed_slowly
        return since >= ACT3_OUTRO_SECONDS

    def complete_act3_climax(self) -> Optional[str]:
        """End the Act III flight and return its branch; None if no Act III flight is active."""
        if not self.is_act3_flight:
            return None
        branch = self.act3_branch
        self.trigger_manager.reset_for_sortie(self.active_sortie_num)
        self.story_manager.set_active_dialogue(None)
        self._end_flight()
        return branch

    def start_act3_climax_cinematic(self, cinematic_player: Any) -> str:
        """Finish the Act III flight and start the ending cinematic; returns the ending branch."""
        start = getattr(cinematic_player, "start_sequence", None)
        if not callable(start):
            raise TypeError("cinematic_player must provide start_sequence()")
        self.complete_act3_climax()
        sequence, stats = build_ending_cinematic(self.story_manager)
        start(sequence, stats, allow_skip=True)
        logger.info("Act III ending cinematic started (branch=%s)", stats.ending_branch)
        return stats.ending_branch
