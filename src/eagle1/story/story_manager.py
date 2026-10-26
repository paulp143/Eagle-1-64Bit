"""story_manager.py - Narrative Campaign State Machine & Loyalty Vector.

Orchestrates pilot psychology, casualty-driven moral trauma, in-flight radio
dialogue queues, time dilation during decision beats, and campaign branching.
"""

import logging
import math
from typing import Any, Dict, List, Optional

from eagle1.story.campaign_save import (
    CAMPAIGN_SAVE_VERSION,
    CampaignSaveManager,
    CampaignSaveState,
)
from eagle1.story.dialogue_db import DialogueNode, DialogueOption, get_dialogue_node

logger = logging.getLogger(__name__)

DEFAULT_LOYALTY: float = 70.0
MIN_LOYALTY: float = 0.0
MAX_LOYALTY: float = 100.0
DECISION_TIME_DILATION: float = 0.4
NORMAL_TIME_DILATION: float = 1.0


class StoryManager:
    """Manages campaign story progression, loyalty tracking, and dialogue events."""

    def __init__(
        self,
        audio_manager: Optional[Any] = None,
        save_manager: Optional[CampaignSaveManager] = None,
    ):
        self.audio = audio_manager
        self.save_manager = save_manager or CampaignSaveManager()

        self.loyalty: float = DEFAULT_LOYALTY
        self.current_act: int = 1
        self.current_sortie: int = 1
        self.total_casualties: int = 0
        self.campaign_active: bool = True
        self.extra: Dict[str, Any] = {}
        self.active_dialogue: Optional[DialogueNode] = None
        self.dialogue_history: List[Dict[str, Any]] = []
        self.time_dilation: float = NORMAL_TIME_DILATION

        self.load_campaign_state()

    def load_campaign_state(self) -> None:
        """Load persistent campaign progress from disk into memory."""
        state = self.save_manager.load_campaign()
        raw_loyalty = state.loyalty if not math.isnan(state.loyalty) else DEFAULT_LOYALTY
        self.loyalty = max(MIN_LOYALTY, min(MAX_LOYALTY, raw_loyalty))
        self.current_act = state.current_act
        self.current_sortie = state.current_sortie
        self.total_casualties = state.total_casualties
        self.campaign_active = state.campaign_active
        self.extra = dict(state.extra)
        self.dialogue_history = list(state.choices_made)

    def save_campaign_state(self) -> bool:
        """Persist current campaign progress to disk."""
        state = CampaignSaveState(
            version=CAMPAIGN_SAVE_VERSION,
            campaign_active=self.campaign_active,
            current_act=self.current_act,
            current_sortie=self.current_sortie,
            loyalty=self.loyalty,
            total_casualties=self.total_casualties,
            choices_made=list(self.dialogue_history),
            extra=dict(self.extra),
        )
        return self.save_manager.save_campaign(state)

    def reset_campaign(self) -> CampaignSaveState:
        """Reset campaign state to baseline defaults and persist to disk."""
        reset_state = self.save_manager.reset_campaign()
        self.load_campaign_state()
        self.active_dialogue = None
        self.time_dilation = NORMAL_TIME_DILATION
        return reset_state

    def advance_sortie(self, act: Optional[int] = None, sortie: Optional[int] = None) -> bool:
        """Advance to next sortie or specific act/sortie coordinates and persist."""
        if act is None and sortie is None:
            self.current_sortie += 1
        else:
            if act is not None and not isinstance(act, bool):
                try:
                    self.current_act = max(1, int(act))
                except (ValueError, TypeError):
                    pass
            if sortie is not None and not isinstance(sortie, bool):
                try:
                    self.current_sortie = max(1, int(sortie))
                except (ValueError, TypeError):
                    pass
        return self.save_campaign_state()

    def modify_loyalty(self, delta: float, reason: str = "") -> None:
        """Adjust pilot loyalty with strict [0.0, 100.0] bounds clamping."""
        if isinstance(delta, bool):
            logger.warning("Ignored invalid boolean loyalty delta %r (reason: '%s')", delta, reason)
            return

        try:
            numeric_delta = float(delta)
        except (TypeError, ValueError):
            logger.warning("Ignored invalid loyalty delta %r (reason: '%s')", delta, reason)
            return

        if math.isnan(numeric_delta):
            logger.warning("Ignored NaN loyalty delta (reason: '%s')", reason)
            return

        old_val = self.loyalty
        self.loyalty = max(MIN_LOYALTY, min(MAX_LOYALTY, self.loyalty + numeric_delta))
        logger.info(
            "Loyalty modified: %.1f -> %.1f (delta: %+.1f, reason: '%s')",
            old_val,
            self.loyalty,
            numeric_delta,
            reason,
        )
        self.save_campaign_state()

    def on_helldiver_death(self, helldiver_id: int) -> None:
        """Record allied Helldiver casualty, eroding pilot loyalty by -3.5."""
        self.total_casualties += 1
        self.modify_loyalty(-3.5, reason=f"helldiver_casualty:{helldiver_id}")

    def on_squad_wipe(self) -> None:
        """Record catastrophic wipe of all 4 Helldivers, eroding loyalty by -8.0."""
        self.modify_loyalty(-8.0, reason="squad_wipe")

    def set_active_dialogue(self, node: Optional[DialogueNode]) -> None:
        """Set or clear the active dialogue beat, adjusting time dilation accordingly."""
        self.active_dialogue = node
        # Slow down time to 0.4 during decision beats to permit reaction without combat stress
        self.time_dilation = DECISION_TIME_DILATION if node is not None else NORMAL_TIME_DILATION

    def record_choice(self, node_id: str, stance: str) -> Optional[DialogueOption]:
        """Record pilot choice for a dialogue node, apply delta, and resume time flow."""
        node = get_dialogue_node(node_id)
        if not node:
            logger.warning("Attempted to record choice for unknown node '%s'", node_id)
            return None

        if stance not in node.options:
            logger.warning("Stance '%s' not found in options for node '%s'", stance, node_id)
            return None

        option = node.options[stance]
        choice_record = {
            "node": node_id,
            "stance": stance,
            "loyalty_delta": option.loyalty_delta,
        }
        self.dialogue_history.append(choice_record)
        self.modify_loyalty(option.loyalty_delta, reason=f"choice:{node_id}:{stance}")

        if self.active_dialogue and self.active_dialogue.node_id == node_id:
            self.set_active_dialogue(None)

        return option

    def get_ending_branch(self) -> str:
        """Determine ending narrative climax based on final Loyalty vector.

        Returns:
            "OBEDIENCE_PURGE" (Loyalty >= 90.0) -> Act III-A: The Zealot
            "DISSIDENT_SURRENDER" (Loyalty <= 15.0) -> Act III-B: The Traitor
            "COLD_PROTOCOL" (15.0 < Loyalty < 90.0) -> Act III-C: The Bureaucrat
        """
        if self.loyalty >= 90.0:
            return "OBEDIENCE_PURGE"
        elif self.loyalty <= 15.0:
            return "DISSIDENT_SURRENDER"
        else:
            return "COLD_PROTOCOL"

