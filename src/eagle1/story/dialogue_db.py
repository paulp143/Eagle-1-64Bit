"""dialogue_db.py - Narrative Dialogue Trees and Script Database for Eagle-1.

Defines dataclasses for tripartite dialogue choices ([LOYAL], [NEUTRAL], [DISSIDENT]),
script nodes across Act I, and validation helpers.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional
import pygame


@dataclass(frozen=True)
class DialogueOption:
    """A single ideological stance choice presented to the pilot."""

    stance: str  # "loyal", "neutral", "dissident"
    key_name: str  # "1", "2", "3"
    key_code: int  # pygame.K_1, pygame.K_2, pygame.K_3
    label: str
    loyalty_delta: float
    response: str
    speaker_reaction: Optional[str] = None


@dataclass(frozen=True)
class DialogueNode:
    """A dialogue beat occurring in-flight or on the Super Destroyer deck."""

    node_id: str
    speaker: str
    location: str
    prompt: str
    options: Dict[str, DialogueOption]
    portrait: Optional[str] = None
    audio_cue: Optional[str] = None
    act: int = 1
    sortie: int = 1


DIALOGUE_DATABASE: Dict[str, DialogueNode] = {
    "sortie_1_briefing": DialogueNode(
        node_id="sortie_1_briefing",
        speaker="Democracy Officer Karl Reiner",
        location="SES Leviathan of Truth - Bridge",
        prompt=(
            "Lieutenant Val. Viper Squad is in the hellpod tubes. Your Eagle is racked with quad-cannons. "
            "Remember: You are the wings of Super Earth. When the Helldivers look to the sky, they see "
            "the undeniable hand of Managed Democracy. How does the spirit feel prior to launch, Lieutenant?"
        ),
        options={
            "loyal": DialogueOption(
                stance="loyal",
                key_name="1",
                key_code=pygame.K_1,
                label="[1. LOYAL] My spirit belongs to Super Earth, Officer. I will rain holy fire.",
                loyalty_delta=+8.0,
                response="Splendid, Val. The Federation thrives on such unyielding steel. Dismissed to the cockpit.",
            ),
            "neutral": DialogueOption(
                stance="neutral",
                key_name="2",
                key_code=pygame.K_2,
                label="[2. NEUTRAL] Pre-flight diagnostics are 100% nominal. Weapons calibrated to standard specs.",
                loyalty_delta=0.0,
                response="Efficient and clinical, Lieutenant. See that your kill ratios match your telemetry.",
            ),
            "dissident": DialogueOption(
                stance="dissident",
                key_name="3",
                key_code=pygame.K_3,
                label="[3. DISSIDENT] Sky is thick with flak. Throwing Viper Squad in without recon is suicide.",
                loyalty_delta=-8.0,
                response="A Helldiver fears only dying without purpose. Do not confuse pragmatism with treason.",
            ),
        },
        act=1,
        sortie=1,
    ),
    "sortie_1_inflight": DialogueNode(
        node_id="sortie_1_inflight",
        speaker="Officer Reiner vs Viper Squad",
        location="In-Flight Radio Comms",
        prompt=(
            "Eagle-1, Automaton jamming beacons detected on the perimeter. Maintain priority on high-value targets. "
            "Ignore secondary squad retreat requests."
        ),
        options={
            "loyal": DialogueOption(
                stance="loyal",
                key_name="1",
                key_code=pygame.K_1,
                label="[1. LOYAL] Understood, Command. Mission objectives supersede squad comfort.",
                loyalty_delta=+6.0,
                response="Apex: 'That's the spirit, Eagle! We'll hold the line with our bare teeth if we have to!'",
            ),
            "neutral": DialogueOption(
                stance="neutral",
                key_name="2",
                key_code=pygame.K_2,
                label="[2. NEUTRAL] Acknowledged. Proceeding in accordance with Fleet CAS Manual Section 4.",
                loyalty_delta=0.0,
                response="Braker: 'Copy that... just another number on a clipboard.'",
            ),
            "dissident": DialogueOption(
                stance="dissident",
                key_name="3",
                key_code=pygame.K_3,
                label="[3. DISSIDENT] Negative, Command! Viper 4 is calling for suppression—breaking vector to cover flank!",
                loyalty_delta=-6.0,
                response="Braker: 'Damn... someone up there actually gives a damn about us. Thanks, Val.'",
            ),
        },
        act=1,
        sortie=1,
    ),
    "sortie_1_hangar_debrief": DialogueNode(
        node_id="sortie_1_hangar_debrief",
        speaker="Viper Squad & Chief Ortiz",
        location="SES Leviathan of Truth - Hangar Deck",
        prompt=(
            "Doc: 'I had to use field-solder to seal private Miller's chest plate before he bled out. "
            "He was nineteen. He kept calling for his mother. Do they put that in the news broadcasts?' "
            "Apex: 'Miller died a hero of Freedom, kid! His name will be on the Pillar of Liberty!'"
        ),
        options={
            "loyal": DialogueOption(
                stance="loyal",
                key_name="1",
                key_code=pygame.K_1,
                label="[1. LOYAL] Apex is right, Doc. We don't mourn soldiers who die for the Federation. We avenge them.",
                loyalty_delta=+10.0,
                response="Doc: '...Right. Of course. For Democracy.' Braker: 'Easy to say from four thousand feet, flygirl.'",
            ),
            "neutral": DialogueOption(
                stance="neutral",
                key_name="2",
                key_code=pygame.K_2,
                label="[2. NEUTRAL] Casualty quotas are set by Logistics, Doc. Discussing them doesn't change the schedule.",
                loyalty_delta=+1.0,
                response="Ortiz: 'Ice water in your veins, Val. Don't lose that. Out here, feelings get you killed.'",
            ),
            "dissident": DialogueOption(
                stance="dissident",
                key_name="3",
                key_code=pygame.K_3,
                label="[3. DISSIDENT] No, Doc. They don't put it in broadcasts. They wipe the blood off and issue it to the next kid.",
                loyalty_delta=-10.0,
                response="Braker: 'Truth hurts, don't it? Better get used to the taste.' Apex: 'Watch your tongue, Lieutenant.'",
            ),
        },
        act=1,
        sortie=1,
    ),
}


def get_dialogue_node(node_id: str) -> Optional[DialogueNode]:
    """Retrieve a dialogue node by its identifier."""
    return DIALOGUE_DATABASE.get(node_id)


def get_nodes_for_act_and_sortie(act: int, sortie: int) -> List[DialogueNode]:
    """Retrieve all dialogue nodes assigned to a specific act and sortie."""
    return [
        node for node in DIALOGUE_DATABASE.values()
        if node.act == act and node.sortie == sortie
    ]


def validate_dialogue_database(db: Dict[str, DialogueNode]) -> bool:
    """Validate that every dialogue node strictly conforms to tripartite narrative specifications.

    Raises:
        ValueError: If any node lacks the required options or invalid loyalty deltas.
    """
    for node_id, node in db.items():
        if not node.node_id or not node.prompt.strip():
            raise ValueError(f"DialogueNode '{node_id}' has empty id or prompt.")

        required_stances = {"loyal", "neutral", "dissident"}
        if set(node.options.keys()) != required_stances:
            raise ValueError(
                f"DialogueNode '{node_id}' must contain 'loyal', 'neutral', and 'dissident' options."
            )

        loyal_opt = node.options["loyal"]
        if loyal_opt.loyalty_delta <= 0.0:
            raise ValueError(f"Loyal option must have positive delta in node '{node_id}'.")

        dissident_opt = node.options["dissident"]
        if dissident_opt.loyalty_delta >= 0.0:
            raise ValueError(f"Dissident option must have negative delta in node '{node_id}'.")

        for stance, opt in node.options.items():
            if not opt.label.strip() or not opt.response.strip():
                raise ValueError(f"Option '{stance}' in node '{node_id}' has empty label or response.")

    return True

