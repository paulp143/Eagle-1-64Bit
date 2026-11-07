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
    "sortie_2_briefing": DialogueNode(
        node_id="sortie_2_briefing",
        speaker="Democracy Officer Karl Reiner",
        location="SES Leviathan of Truth - Bridge",
        portrait="images/portraits/npc_reiner.png",
        prompt=(
            "Lieutenant Val. The forward orbital relay on the Red Perimeter is the only uplink between "
            "Viper Squad and this destroyer. Automaton armor is massing at the ridge line. If the relay falls, "
            "Fleet Command goes deaf over Vandalon Prime. Tell me, Lieutenant: what is that relay worth to you?"
        ),
        options={
            "loyal": DialogueOption(
                stance="loyal",
                key_name="1",
                key_code=pygame.K_1,
                label="[1. LOYAL] More than any single squad, sir. The relay is the voice of Democracy. It will not fall.",
                loyalty_delta=+8.0,
                response="Reiner: 'Correct. Remember those words when the radio starts screaming.'",
            ),
            "neutral": DialogueOption(
                stance="neutral",
                key_name="2",
                key_code=pygame.K_2,
                label="[2. NEUTRAL] Relay uptime is the mission parameter. I will fly the defense profile as briefed.",
                loyalty_delta=0.0,
                response="Reiner: 'Adequate. Fly the profile and let the numbers speak for you.'",
            ),
            "dissident": DialogueOption(
                stance="dissident",
                key_name="3",
                key_code=pygame.K_3,
                label="[3. DISSIDENT] The relay is hardware, sir. Viper Squad are the ones standing in front of it.",
                loyalty_delta=-8.0,
                response="Reiner: 'Hardware that keeps eleven thousand troopers in contact with orbit. Recalibrate your sympathies, Val.'",
            ),
        },
        act=1,
        sortie=2,
    ),
    "sortie_2_inflight": DialogueNode(
        node_id="sortie_2_inflight",
        speaker="Viper-4 Doc vs Officer Reiner",
        location="In-Flight Radio Comms",
        portrait="images/portraits/viper_4_doc.png",
        prompt=(
            "Doc: 'Eagle-1, Braker is down and I am out of stims! I need a supply pod on my position and cover fire NOW!' "
            "Reiner: 'Negative, Eagle-1. Ammunition conservation is in effect. Every round you carry is reserved "
            "for the relay generator.'"
        ),
        options={
            "loyal": DialogueOption(
                stance="loyal",
                key_name="1",
                key_code=pygame.K_1,
                label="[1. LOYAL] Copy, Command. Holding ordnance for the relay generator. Doc, hold on.",
                loyalty_delta=+8.0,
                response="Apex: 'You heard the Officer! The relay stands, Viper Squad stands!'",
                speaker_reaction="Doc: '...Understood. I will make do with what I have.'",
            ),
            "neutral": DialogueOption(
                stance="neutral",
                key_name="2",
                key_code=pygame.K_2,
                label="[2. NEUTRAL] Rationing per Ordnance Table 4-B. One scheduled resupply window, no exceptions.",
                loyalty_delta=0.0,
                response="Ghost: 'Scheduled window logged. Doc, you have ninety seconds.'",
                speaker_reaction="Doc: 'Ninety seconds... okay. Okay.'",
            ),
            "dissident": DialogueOption(
                stance="dissident",
                key_name="3",
                key_code=pygame.K_3,
                label="[3. DISSIDENT] Negative, Command. Dropping supply on Doc and covering the casualty evac!",
                loyalty_delta=-8.0,
                response="Braker: 'Pod is down! You beautiful lunatic, Val!'",
                speaker_reaction="Reiner: 'This deviation has been logged, Lieutenant.'",
            ),
        },
        act=1,
        sortie=2,
    ),
    "sortie_2_hangar_debrief": DialogueNode(
        node_id="sortie_2_hangar_debrief",
        speaker="Viper Squad & Chief Ortiz",
        location="SES Leviathan of Truth - Hangar Deck",
        portrait="images/portraits/npc_ortiz.png",
        prompt=(
            "Ortiz: 'Relay is still transmitting, Val. Your cannon barrels are scorched black.' "
            "Braker: 'And I have a fresh tally mark on my breastplate. Tell me it was worth an antenna.' "
            "Apex: 'The relay held. That is all Super Earth asks of us.'"
        ),
        options={
            "loyal": DialogueOption(
                stance="loyal",
                key_name="1",
                key_code=pygame.K_1,
                label="[1. LOYAL] It was worth it, Braker. Every tally mark is a debt paid in Liberty.",
                loyalty_delta=+10.0,
                response="Apex: 'Spoken like a true patriot!' Braker: 'Spoken like someone who never carries the bodies.'",
            ),
            "neutral": DialogueOption(
                stance="neutral",
                key_name="2",
                key_code=pygame.K_2,
                label="[2. NEUTRAL] Relay uptime was ninety-six percent. Losses stayed inside projected tolerances.",
                loyalty_delta=+1.0,
                response="Ortiz: 'Tolerances. Right. I will put that on the barrel replacement form.'",
            ),
            "dissident": DialogueOption(
                stance="dissident",
                key_name="3",
                key_code=pygame.K_3,
                label="[3. DISSIDENT] No, Braker. They traded your squadmate for an antenna, and nobody up here will say it.",
                loyalty_delta=-10.0,
                response="Braker: 'Finally, someone said it.' Apex: 'Careful, Lieutenant. The deck mics are always listening.'",
            ),
        },
        act=1,
        sortie=2,
    ),
    "sortie_3_briefing": DialogueNode(
        node_id="sortie_3_briefing",
        speaker="Democracy Officer Karl Reiner",
        location="SES Leviathan of Truth - Bridge",
        portrait="images/portraits/npc_reiner.png",
        prompt=(
            "Lieutenant Val. Grid Charlie-4 hosts a fortified Automaton fabricator complex. Each furnace vent "
            "rolls out a fresh platoon every eight seconds. You will deliver 500kg ordnance down those vents, "
            "whatever stands beside them. Is that understood?"
        ),
        options={
            "loyal": DialogueOption(
                stance="loyal",
                key_name="1",
                key_code=pygame.K_1,
                label="[1. LOYAL] Understood, sir. Every vent I seal saves a thousand Helldivers tomorrow.",
                loyalty_delta=+10.0,
                response="Reiner: 'Precisely. Arithmetic is the purest form of patriotism.'",
            ),
            "neutral": DialogueOption(
                stance="neutral",
                key_name="2",
                key_code=pygame.K_2,
                label="[2. NEUTRAL] Understood. I will request danger-close clearance before each release.",
                loyalty_delta=0.0,
                response="Reiner: 'Request what you like. The vents will not wait for paperwork.'",
            ),
            "dissident": DialogueOption(
                stance="dissident",
                key_name="3",
                key_code=pygame.K_3,
                label="[3. DISSIDENT] Understood, sir. 'Whatever stands beside them' had better not be Viper Squad.",
                loyalty_delta=-10.0,
                response="Reiner: 'Your concern for four soldiers over a front of eleven thousand has been noted, Lieutenant.'",
            ),
        },
        act=2,
        sortie=3,
    ),
    "sortie_3_500kg_crisis": DialogueNode(
        node_id="sortie_3_500kg_crisis",
        speaker="Viper-4 Doc vs Officer Reiner",
        location="In-Flight Radio Comms",
        portrait="images/portraits/viper_4_doc.png",
        prompt=(
            "Doc: 'Eagle-1, hold your drop! Braker is pinned under a collapsed girder right beside the fabricator vent!' "
            "Reiner: 'Eagle-1, the vent is primed to spawn a full platoon. Release the 500kg immediately. "
            "That is a direct order.'"
        ),
        options={
            "loyal": DialogueOption(
                stance="loyal",
                key_name="1",
                key_code=pygame.K_1,
                label="[1. LOYAL] Releasing ordinance! Acceptable collateral damage.",
                loyalty_delta=+12.0,
                response="Apex: 'The vent is gone! Braker... Braker is not answering.'",
                speaker_reaction="Doc: 'You dropped it right on him, Val. Right on him.'",
            ),
            "neutral": DialogueOption(
                stance="neutral",
                key_name="2",
                key_code=pygame.K_2,
                label="[2. NEUTRAL] Adjusting impact vector by 15 meters east.",
                loyalty_delta=0.0,
                response="Ghost: 'Impact offset confirmed. Perimeter is breached, the vent is still smoking.'",
                speaker_reaction="Doc: 'Braker is alive but his legs are crushed. Stims going in now!'",
            ),
            "dissident": DialogueOption(
                stance="dissident",
                key_name="3",
                key_code=pygame.K_3,
                label="[3. DISSIDENT] Aborting drop! Coming in with cannons!",
                loyalty_delta=-12.0,
                response="Braker: 'Val, you magnificent idiot! Get that vent before it gets us!'",
                speaker_reaction="Reiner: 'Insubordination under fire. This will follow you, Lieutenant.'",
            ),
        },
        act=2,
        sortie=3,
    ),
    "sortie_3_hangar_debrief": DialogueNode(
        node_id="sortie_3_hangar_debrief",
        speaker="Viper Squad & Chief Ortiz",
        location="SES Leviathan of Truth - Hangar Deck",
        portrait="images/portraits/npc_ortiz.png",
        prompt=(
            "Ortiz: 'Bomb rack telemetry says you held a 500kg over Charlie-4 for eleven seconds, Val.' "
            "Doc: 'Eleven seconds. That is how long Braker had.' "
            "Apex: 'The furnace is cold. The complex is ours. That is the only number that matters.'"
        ),
        options={
            "loyal": DialogueOption(
                stance="loyal",
                key_name="1",
                key_code=pygame.K_1,
                label="[1. LOYAL] Apex is right. The complex fell, and Super Earth is safer for it.",
                loyalty_delta=+10.0,
                response="Apex: 'For Liberty!' Doc: '...For Liberty.'",
            ),
            "neutral": DialogueOption(
                stance="neutral",
                key_name="2",
                key_code=pygame.K_2,
                label="[2. NEUTRAL] Eleven seconds was within release tolerances. I will file the report.",
                loyalty_delta=-1.0,
                response="Ortiz: 'Tolerances again. I am running out of forms for them, Val.'",
            ),
            "dissident": DialogueOption(
                stance="dissident",
                key_name="3",
                key_code=pygame.K_3,
                label="[3. DISSIDENT] Nobody should have to choose between a vent and a squadmate. Command made that choice for me.",
                loyalty_delta=-10.0,
                response="Doc: 'Thank you for saying it.' Apex: 'Say it quieter, Lieutenant. The Officer reads every log.'",
            ),
        },
        act=2,
        sortie=3,
    ),
    "sortie_4_briefing": DialogueNode(
        node_id="sortie_4_briefing",
        speaker="Democracy Officer Karl Reiner",
        location="SES Leviathan of Truth - Bridge",
        portrait="images/portraits/npc_reiner.png",
        prompt=(
            "Lieutenant Val. A Class-IV Factory Strider is marching on Viper Squad's extraction zone. It is a walking "
            "fabricator with chin turrets and a ventral core. Destroy it, and Vandalon Prime is ours. Fail, and "
            "Pelican-1 lands in a graveyard."
        ),
        options={
            "loyal": DialogueOption(
                stance="loyal",
                key_name="1",
                key_code=pygame.K_1,
                label="[1. LOYAL] The Strider falls today, sir. Whatever it costs.",
                loyalty_delta=+10.0,
                response="Reiner: 'Whatever it costs. I will hold you to those words.'",
            ),
            "neutral": DialogueOption(
                stance="neutral",
                key_name="2",
                key_code=pygame.K_2,
                label="[2. NEUTRAL] Core first, turrets second. I will fly the attack profile as briefed.",
                loyalty_delta=0.0,
                response="Reiner: 'Efficient. Let us hope the Strider reads the same briefing.'",
            ),
            "dissident": DialogueOption(
                stance="dissident",
                key_name="3",
                key_code=pygame.K_3,
                label="[3. DISSIDENT] Viper Squad gets out alive first. The Strider is just a very large target.",
                loyalty_delta=-10.0,
                response="Reiner: 'Priorities, Lieutenant. You keep confusing yours with mine.'",
            ),
        },
        act=2,
        sortie=4,
    ),
    "sortie_4_strider_crisis": DialogueNode(
        node_id="sortie_4_strider_crisis",
        speaker="Viper-1 Apex vs Officer Reiner",
        location="In-Flight Radio Comms",
        portrait="images/portraits/viper_1_apex.png",
        prompt=(
            "Apex: 'Eagle-1, the Strider's chin turrets have us pinned! We cannot reach the extraction beacon!' "
            "Reiner: 'Eagle-1, its armor is cracking. Commit every pass to the ventral core. The squad will hold.'"
        ),
        options={
            "loyal": DialogueOption(
                stance="loyal",
                key_name="1",
                key_code=pygame.K_1,
                label="[1. LOYAL] Committing all passes to the core. Viper Squad, dig in!",
                loyalty_delta=+10.0,
                response="Reiner: 'Good. Make every pass count.'",
                speaker_reaction="Apex: 'Digging in! For Super Earth!'",
            ),
            "neutral": DialogueOption(
                stance="neutral",
                key_name="2",
                key_code=pygame.K_2,
                label="[2. NEUTRAL] Alternating passes: leg actuators, then turret suppression.",
                loyalty_delta=0.0,
                response="Ghost: 'Alternating runs logged. Turret fire dropping by half.'",
                speaker_reaction="Apex: 'Half is better than nothing, Eagle!'",
            ),
            "dissident": DialogueOption(
                stance="dissident",
                key_name="3",
                key_code=pygame.K_3,
                label="[3. DISSIDENT] Breaking off the core! Silencing those turrets first!",
                loyalty_delta=-10.0,
                response="Doc: 'Turrets are down! We are moving, we are moving!'",
                speaker_reaction="Reiner: 'You are prolonging this war, Lieutenant.'",
            ),
        },
        act=2,
        sortie=4,
    ),
    "sortie_4_hangar_debrief": DialogueNode(
        node_id="sortie_4_hangar_debrief",
        speaker="Viper Squad & Chief Ortiz",
        location="SES Leviathan of Truth - Hangar Deck",
        portrait="images/portraits/npc_ortiz.png",
        prompt=(
            "Ortiz: 'The Iron Colossus is scrap, Val. Fleet Command is already printing the posters.' "
            "Apex: 'Act Two is over, Lieutenant. Command wants to know what kind of pilot it is sending into Act Three.'"
        ),
        options={
            "loyal": DialogueOption(
                stance="loyal",
                key_name="1",
                key_code=pygame.K_1,
                label="[1. LOYAL] The kind that never hesitates. Super Earth can count on me.",
                loyalty_delta=+12.0,
                response="Apex: 'That is the pilot the posters promised!'",
            ),
            "neutral": DialogueOption(
                stance="neutral",
                key_name="2",
                key_code=pygame.K_2,
                label="[2. NEUTRAL] The kind that flies the profile and files the report.",
                loyalty_delta=0.0,
                response="Ortiz: 'Reliable. Boring. Alive. I can work with that.'",
            ),
            "dissident": DialogueOption(
                stance="dissident",
                key_name="3",
                key_code=pygame.K_3,
                label="[3. DISSIDENT] The kind that remembers every name on Braker's breastplate.",
                loyalty_delta=-12.0,
                response="Doc: 'Then remember them loudly, Val.' Apex: 'Careful. The deck mics are always listening.'",
            ),
        },
        act=2,
        sortie=4,
    ),
    # Act III-A (OBEDIENCE_PURGE, #74). Refusal is narratively overridden: whatever the
    # pilot answers, campaign_act3 clamps loyalty back to zealot level and the strike happens.
    "act3a_encrypted_order": DialogueNode(
        node_id="act3a_encrypted_order",
        speaker="Democracy Officer Karl Reiner",
        location="Eagle-1 Cockpit - Encrypted Channel 9",
        portrait="images/portraits/npc_reiner.png",
        prompt=(
            "Viper Squad is infected with anti-democratic defeatism. At Outpost Gamma you will receive "
            "coordinates for an alleged Automaton bunker. They are Viper Squad's foxhole. Deploy your 500kg "
            "ordinance directly onto that grid. Authorization code: Vermilion-Nine. Confirm understanding."
        ),
        options={
            "loyal": DialogueOption(
                stance="loyal",
                key_name="1",
                key_code=pygame.K_1,
                label="[1. LOYAL] Orders received, Officer Reiner. Purity must be preserved. Eliminating the dissidents.",
                loyalty_delta=+10.0,
                response="Exemplary, Lieutenant. You are a true daughter of Super Earth.",
            ),
            "neutral": DialogueOption(
                stance="neutral",
                key_name="2",
                key_code=pygame.K_2,
                label="[2. NEUTRAL] Requesting written confirmation of Vermilion-Nine before weapons release.",
                loyalty_delta=0.0,
                response="Refusal triggers remote detonation of your craft's engine reactor in three... two...",
                speaker_reaction="Val: '...Understood. Preparing ordinance.'",
            ),
            "dissident": DialogueOption(
                stance="dissident",
                key_name="3",
                key_code=pygame.K_3,
                label="[3. DISSIDENT] Negative. I will not drop a 500kg on my own squad.",
                loyalty_delta=-10.0,
                response="Refusal triggers remote detonation of your craft's engine reactor in three... two...",
                speaker_reaction="Val: '...Understood. Preparing ordinance.'",
            ),
        },
        act=3,
        sortie=5,
    ),
    "sortie_5a_trench_lock": DialogueNode(
        node_id="sortie_5a_trench_lock",
        speaker="Viper-2 Braker vs Officer Reiner",
        location="In-Flight Radio Comms",
        portrait="images/portraits/viper_2_braker.png",
        prompt=(
            "Braker: 'Hey... Eagle? Your targeting laser is painting our trench. "
            "Val? Why is the targeting reticle on us? Val, abort! ABORT!' "
            "Reiner: 'Vermilion-Nine is authorized, Eagle-1. Release the 500kg.'"
        ),
        options={
            "loyal": DialogueOption(
                stance="loyal",
                key_name="1",
                key_code=pygame.K_1,
                label="[1. LOYAL] Releasing ordinance on Vermilion-Nine coordinates.",
                loyalty_delta=+10.0,
                response="Apex: 'Super Earth... why...?'",
                speaker_reaction="Reiner: 'Magnificent strike, Lieutenant. A hero's reception awaits you.'",
            ),
            "neutral": DialogueOption(
                stance="neutral",
                key_name="2",
                key_code=pygame.K_2,
                label="[2. NEUTRAL] Weapons release per Authorization Vermilion-Nine. Logging the order.",
                loyalty_delta=0.0,
                response="Apex: 'Super Earth... why...?'",
                speaker_reaction="Val: 'Target... neutralized. Sector clean.'",
            ),
            "dissident": DialogueOption(
                stance="dissident",
                key_name="3",
                key_code=pygame.K_3,
                label="[3. DISSIDENT] Braker, get out of the trench! RUN!",
                loyalty_delta=-10.0,
                response="Reiner: 'Remote release engaged, Lieutenant. Vermilion-Nine does not require your consent.'",
                speaker_reaction="Apex: 'Super Earth... why...?'",
            ),
        },
        act=3,
        sortie=5,
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

