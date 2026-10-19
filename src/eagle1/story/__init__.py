"""Campaign Story and Interactive Dialogue System for Eagle-1-64Bit."""

from eagle1.story.campaign_save import CampaignSaveManager, CampaignSaveState
from eagle1.story.dialogue_db import (
    DIALOGUE_DATABASE,
    DialogueNode,
    DialogueOption,
    get_dialogue_node,
    get_nodes_for_act_and_sortie,
    validate_dialogue_database,
)
from eagle1.story.story_manager import StoryManager

__all__ = [
    "CampaignSaveManager",
    "CampaignSaveState",
    "DIALOGUE_DATABASE",
    "DialogueNode",
    "DialogueOption",
    "StoryManager",
    "get_dialogue_node",
    "get_nodes_for_act_and_sortie",
    "validate_dialogue_database",
]
