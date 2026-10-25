"""story_manager.py - Narrative Campaign State Machine & Loyalty Vector.

Orchestrates pilot psychology, casualty-driven moral trauma, in-flight radio
dialogue queues, time dilation during decision beats, and campaign branching.
"""

import logging
from typing import Any, Dict, List, Optional

from eagle1.story.campaign_save import CampaignSaveManager, CampaignSaveState
from eagle1.story.dialogue_db import DialogueNode, DialogueOption, get_dialogue_node

logger = logging.getLogger(__name__)


class StoryManager:
    """Manages campaign story progression, loyalty tracking, and dialogue events."""

    def __init__(
        self,
        audio_manager: Optional[Any] = None,
        save_manager: Optional[CampaignSaveManager] = None,
    ):
        self.audio = audio_manager
        self.save_manager = save_manager or CampaignSaveManager()

        self.loyalty: float = 70.0
        self.current_act: int = 1
        self.current_sortie: int = 1
        self.total_casualties: int = 0
        self.active_dialogue: Optional[DialogueNode] = None
        self.dialogue_history: List[Dict[str, Any]] = []
        self.time_dilation: float = 1.0

        self.load_campaign_state()

    def load_campaign_state(self) -> None:
        """Load persistent campaign progress from disk into memory."""
        state = self.save_manager.load_campaign()
        self.loyalty = max(0.0, min(100.0, state.loyalty))
        self.current_act = state.current_act
        self.current_sortie = state.current_sortie
        self.total_casualties = state.total_casualties
        self.dialogue_history = list(state.choices_made)

    def save_campaign_state(self) -> bool:
        """Persist current campaign progress to disk."""
        state = CampaignSaveState(
            version=1,
            campaign_active=True,
            current_act=self.current_act,
            current_sortie=self.current_sortie,
            loyalty=self.loyalty,
            total_casualties=self.total_casualties,
            choices_made=list(self.dialogue_history),
        )
        return self.save_manager.save_campaign(state)

    def modify_loyalty(self, delta: float, reason: str = "") -> None:
        """Adjust pilot loyalty with strict [0.0, 100.0] bounds clamping."""
        old_val = self.loyalty
        self.loyalty = max(0.0, min(100.0, self.loyalty + delta))
        logger.info(
            "Loyalty modified: %.1f -> %.1f (delta: %+.1f, reason: '%s')",
            old_val,
            self.loyalty,
            delta,
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
        self.time_dilation = 0.4 if node is not None else 1.0

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
            "COLD_PROTOCOL" (16.0 <= Loyalty <= 89.0) -> Act III-C: The Bureaucrat
        """
        if self.loyalty >= 90.0:
            return "OBEDIENCE_PURGE"
        elif self.loyalty <= 15.0:
            return "DISSIDENT_SURRENDER"
        else:
            return "COLD_PROTOCOL"

