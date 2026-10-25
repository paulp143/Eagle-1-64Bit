"""Campaign Story and Interactive Dialogue System for Eagle-1-64Bit."""

from eagle1.story.campaign_save import CampaignSaveManager, CampaignSaveState
from eagle1.story.comms_hud import CommsHUD
from eagle1.story.dialogue_data import (
    BANTER_QUEUES,
    VIPER_DIALOGUE_TREES,
    VIPER_SQUAD_PROFILES,
    BanterLine,
    ViperCharacterProfile,
    get_contextual_banter,
    get_debrief_dialogue_node,
    get_viper_profile,
    validate_viper_dialogue_data,
)
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
    "BANTER_QUEUES",
    "CampaignSaveManager",
    "CampaignSaveState",
    "CommsHUD",
    "DIALOGUE_DATABASE",
    "DialogueNode",
    "DialogueOption",
    "StoryManager",
    "VIPER_DIALOGUE_TREES",
    "VIPER_SQUAD_PROFILES",
    "BanterLine",
    "ViperCharacterProfile",
    "get_contextual_banter",
    "get_debrief_dialogue_node",
    "get_dialogue_node",
    "get_nodes_for_act_and_sortie",
    "get_viper_profile",
    "validate_dialogue_database",
    "validate_viper_dialogue_data",
]
