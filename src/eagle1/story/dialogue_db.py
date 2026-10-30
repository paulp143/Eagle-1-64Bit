"""dialogue_db.py - Narrative Dialogue Trees and Script Database for Eagle-1.

Defines dataclasses for tripartite dialogue choices ([LOYAL], [NEUTRAL], [DISSIDENT]),
script nodes across Act I, and validation helpers.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import pygame


@dataclass(frozen=True)
class ShipNPCProfile:
    """Character profile definition for shipboard personnel on the Super Destroyer."""

    npc_id: str
    name: str
    role: str
    zone: str
    theme_color: Tuple[int, int, int]
    portrait_path: str
    bio: str
    default_node_id: str

    @property
    def callsign(self) -> str:
        """Compatibility alias returning the character's display name."""
        return self.name


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
        portrait="images/portraits/npc_reiner.png",
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
                loyalty_delta=+8.0,
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
                loyalty_delta=-8.0,
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
        portrait="images/portraits/npc_ortiz.png",
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
    "bridge_vance_logistics": DialogueNode(
        node_id="bridge_vance_logistics",
        speaker="Ship Master Cynthia Vance",
        location="SES Leviathan of Truth - Bridge",
        portrait="images/portraits/npc_vance.png",
        prompt=(
            "Lieutenant Val. My job is to keep this destroyer in low orbit and keep the munitions "
            "elevators greased. Orbital battery fire in Sector 7 is burning through our thruster reserves, "
            "and Fleet Command just cut our drop pod allocation by twelve percent. How are you managing "
            "your ordnance expenditure down in the mud?"
        ),
        options={
            "loyal": DialogueOption(
                stance="loyal",
                key_name="1",
                key_code=pygame.K_1,
                label="[1. LOYAL] Super Earth provides all the steel we need, Commander. Faith makes up the margin.",
                loyalty_delta=+8.0,
                response="Vance: 'Faith doesn't refuel orbital thrusters, Lieutenant, but Officer Reiner will be pleased to hear it.'",
            ),
            "neutral": DialogueOption(
                stance="neutral",
                key_name="2",
                key_code=pygame.K_2,
                label="[2. NEUTRAL] Maintaining strict adherence to Fleet Ordnance Table 4-B. Zero unscheduled drops.",
                loyalty_delta=0.0,
                response="Vance: 'Good. Stick to the timetable and keep my airframe intact. I don't look at the dirt, just the numbers.'",
            ),
            "dissident": DialogueOption(
                stance="dissident",
                key_name="3",
                key_code=pygame.K_3,
                label="[3. DISSIDENT] Cutting drop pods while Viper Squad is bleeding out down there is a death sentence, Vance.",
                loyalty_delta=-8.0,
                response="Vance: 'Lower your voice, Val. I don't write the casualty quotas—I just sign the cargo manifests.'",
            ),
        },
        act=1,
        sortie=1,
    ),
    "bridge_reiner_scrutiny": DialogueNode(
        node_id="bridge_reiner_scrutiny",
        speaker="Democracy Officer Karl Reiner",
        location="SES Leviathan of Truth - Bridge",
        portrait="images/portraits/npc_reiner.png",
        prompt=(
            "Walk with me, Lieutenant. I have reviewed your cockpit audio telemetry from the recent drops. "
            "A cog in Managed Democracy does not choose when to turn, yet you calculate margins and hesitate "
            "when Viper Squad screams over the radio. Tell me: do you see brothers down there, or ammunition?"
        ),
        options={
            "loyal": DialogueOption(
                stance="loyal",
                key_name="1",
                key_code=pygame.K_1,
                label="[1. LOYAL] Humanity is a resource and Democracy is the flame, sir. My devotion has never wavered.",
                loyalty_delta=+10.0,
                response="Reiner: 'Good. Because the next phase of this campaign will require absolute ideological purity.'",
            ),
            "neutral": DialogueOption(
                stance="neutral",
                key_name="2",
                key_code=pygame.K_2,
                label="[2. NEUTRAL] I execute close air support strictly within the Flight Command Operational Envelope, sir.",
                loyalty_delta=0.0,
                response="Reiner: 'Precision without passion is merely mechanical, Val. Be careful that coldness does not mask hesitation.'",
            ),
            "dissident": DialogueOption(
                stance="dissident",
                key_name="3",
                key_code=pygame.K_3,
                label="[3. DISSIDENT] They ARE people, Karl. You sit in air-conditioned comfort while they bleed in the mud.",
                loyalty_delta=-10.0,
                response="Reiner: 'Remember that treason is a capital offense, Val. Your aircraft transponder can be detonated with a single keystroke.'",
            ),
        },
        act=2,
        sortie=2,
    ),
    "hangar_ortiz_maintenance": DialogueNode(
        node_id="hangar_ortiz_maintenance",
        speaker="Chief Engineer Rylan Ortiz",
        location="SES Leviathan of Truth - Hangar Deck",
        portrait="images/portraits/npc_ortiz.png",
        prompt=(
            "She took six 30mm flak rounds through the port stabilizer, Val. Patched her up with scrap "
            "titanium plating and a prayer while the ordnance loaders racked your 500kg bombs. "
            "Keep her alive down there, kid. Metal doesn't grow on trees, and neither do you."
        ),
        options={
            "loyal": DialogueOption(
                stance="loyal",
                key_name="1",
                key_code=pygame.K_1,
                label="[1. LOYAL] Eagle-1 is forged by Super Earth, Chief. No Automaton flak can ground Liberty's wings.",
                loyalty_delta=+8.0,
                response="Ortiz: 'Sure, kid. Tell that to the hydraulic manifold next time you dive through heavy laser fire.'",
            ),
            "neutral": DialogueOption(
                stance="neutral",
                key_name="2",
                key_code=pygame.K_2,
                label="[2. NEUTRAL] Port stabilizer trim verified. Please log the hull patch in Maintenance Form 12-A.",
                loyalty_delta=0.0,
                response="Ortiz: 'Already logged and stamped, Lieutenant. Thrusters are green across the board.'",
            ),
            "dissident": DialogueOption(
                stance="dissident",
                key_name="3",
                key_code=pygame.K_3,
                label="[3. DISSIDENT] Scrap plating and prayers while Command orders four drops a day... they're running us into the ground.",
                loyalty_delta=-8.0,
                response="Ortiz: 'Keep your voice down near the deck mics, Val. Just bring this bird back in one piece, alright?'",
            ),
        },
        act=1,
        sortie=1,
    ),
}

SHIP_NPC_PROFILES: Dict[str, ShipNPCProfile] = {
    "npc_reiner": ShipNPCProfile(
        npc_id="npc_reiner",
        name="Democracy Officer Karl Reiner",
        role="Ministry of Truth Commissar",
        zone="bridge",
        theme_color=(255, 215, 50),
        portrait_path="images/portraits/npc_reiner.png",
        bio="Political commissar stationed on the bridge. Evaluates ideological purity and treats execution orders like cargo manifests.",
        default_node_id="sortie_1_briefing",
    ),
    "npc_vance": ShipNPCProfile(
        npc_id="npc_vance",
        name="Ship Master Cynthia Vance",
        role="Operational Commander",
        zone="bridge",
        theme_color=(0, 220, 255),
        portrait_path="images/portraits/npc_vance.png",
        bio="Exhausted naval commander of the SES Leviathan of Truth focused on orbital timetables, fuel margins, and munitions quotas.",
        default_node_id="bridge_vance_logistics",
    ),
    "viper_1": ShipNPCProfile(
        npc_id="viper_1",
        name='Viper-1 "Apex"',
        role="Squad Leader",
        zone="ready_room",
        theme_color=(255, 215, 0),
        portrait_path="images/portraits/viper_1_apex.png",
        bio="Veteran vanguard commander who quotes the Federation handbook constantly and believes Helldivers never die.",
        default_node_id="viper_1_deck_briefing",
    ),
    "viper_2": ShipNPCProfile(
        npc_id="viper_2",
        name='Viper-2 "Braker"',
        role="Heavy Munitions",
        zone="ready_room",
        theme_color=(52, 152, 219),
        portrait_path="images/portraits/viper_2_braker.png",
        bio="Battle-scarred autocannon specialist who etches tally marks onto his breastplate for every fallen comrade.",
        default_node_id="viper_2_deck_briefing",
    ),
    "viper_3": ShipNPCProfile(
        npc_id="viper_3",
        name='Viper-3 "Ghost"',
        role="Recon & Sniper",
        zone="ready_room",
        theme_color=(46, 204, 113),
        portrait_path="images/portraits/viper_3_ghost.png",
        bio="Quiet recon marksman who monitors radar pings and spots tactical discrepancies in High Command telemetry.",
        default_node_id="viper_3_deck_briefing",
    ),
    "viper_4": ShipNPCProfile(
        npc_id="viper_4",
        name='Viper-4 "Doc"',
        role="Combat Medic",
        zone="ready_room",
        theme_color=(231, 76, 60),
        portrait_path="images/portraits/viper_4_doc.png",
        bio="Youngest squad member who frantically applies tourniquets under fire and pleads for medical resupply pods.",
        default_node_id="viper_4_deck_briefing",
    ),
    "npc_ortiz": ShipNPCProfile(
        npc_id="npc_ortiz",
        name="Chief Engineer Rylan Ortiz",
        role="Senior Flight Deck Mechanic",
        zone="hangar",
        theme_color=(243, 156, 18),
        portrait_path="images/portraits/npc_ortiz.png",
        bio="Gruff senior flight deck mechanic with a cybernetic welding forearm who keeps Eagle-1 flying with scrap plating and prayers.",
        default_node_id="hangar_ortiz_maintenance",
    ),
}

_SHIP_NPC_ALIASES: Dict[str, str] = {
    "reiner": "npc_reiner",
    "karl_reiner": "npc_reiner",
    "vance": "npc_vance",
    "cynthia_vance": "npc_vance",
    "ortiz": "npc_ortiz",
    "rylan_ortiz": "npc_ortiz",
    "apex": "viper_1",
    "braker": "viper_2",
    "ghost": "viper_3",
    "doc": "viper_4",
    "npc_viper_1": "viper_1",
    "npc_viper_2": "viper_2",
    "npc_viper_3": "viper_3",
    "npc_viper_4": "viper_4",
}


def get_ship_npc_profile(npc_id: str) -> Optional[ShipNPCProfile]:
    """Retrieve a shipboard NPC profile by ID or common alias."""
    if npc_id is None or isinstance(npc_id, bool) or not isinstance(npc_id, str):
        return None

    clean = npc_id.strip().lower()
    if not clean:
        return None

    if clean in SHIP_NPC_PROFILES:
        return SHIP_NPC_PROFILES[clean]

    canonical = _SHIP_NPC_ALIASES.get(clean)
    if canonical and canonical in SHIP_NPC_PROFILES:
        return SHIP_NPC_PROFILES[canonical]

    return None


def get_dialogue_node(node_id: str) -> Optional[DialogueNode]:
    """Retrieve a dialogue node by its identifier."""
    if node_id is None or isinstance(node_id, bool) or not isinstance(node_id, str):
        return None

    clean_id = node_id.strip()
    if not clean_id:
        return None

    if clean_id in DIALOGUE_DATABASE:
        return DIALOGUE_DATABASE[clean_id]
    try:
        from eagle1.story.dialogue_data import VIPER_DIALOGUE_TREES
        return VIPER_DIALOGUE_TREES.get(clean_id)
    except ImportError:
        return None


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

        neutral_opt = node.options["neutral"]
        if not (-1.0 <= neutral_opt.loyalty_delta <= 1.0):
            raise ValueError(f"Neutral option delta must be within [-1.0, 1.0] in node '{node_id}'.")

        dissident_opt = node.options["dissident"]
        if dissident_opt.loyalty_delta >= 0.0:
            raise ValueError(f"Dissident option must have negative delta in node '{node_id}'.")

        for stance, opt in node.options.items():
            if not opt.label.strip() or not opt.response.strip():
                raise ValueError(f"Option '{stance}' in node '{node_id}' has empty label or response.")

    return True

