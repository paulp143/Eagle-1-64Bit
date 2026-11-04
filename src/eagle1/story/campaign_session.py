"""campaign_session.py - Runtime bridge between the game loop and the campaign story systems.

Builds the per-sortie mission configuration and the per-frame combat telemetry snapshot
that the Narrative Trigger Manager evaluates. Duck-typed on the ground support manager
so this module never imports eagle1.systems at runtime (import cycle via eagle1.story).
"""

from typing import Any, Dict, FrozenSet, Mapping, Optional

from eagle1.story.mission_controller import CampaignSortieConfig
from eagle1.story.narrative_trigger_manager import CombatTelemetrySnapshot

CAMPAIGN_SORTIE_CONFIG_KEY: str = "campaign_sortie"
BOMB_500KG_STRIKE_TYPE: str = "bomb_500kg"  # mirrors AirStrikeType.BOMB_500KG (asserted in tests)
HELLDIVER_CRITICAL_HEALTH_RATIO: float = 0.35  # mirrors GroundSupportManager low-health banter threshold
WAVE_DRIVEN_MISSION_MODES: FrozenSet[str] = frozenset({"air_superiority", "base_defense", "outpost_demolition"})


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
