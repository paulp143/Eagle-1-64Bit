"""dialogue_data.py - Viper Squad Character Profiles, Banter Queues & Narrative Dialogue Trees.

Defines the character profiles for allied Helldiver strike team Viper Squad
(Apex, Braker, Ghost, Doc), in-flight contextual combat banter queues, and
tripartite story dialogue trees across sortie debriefs and deck encounters.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Union

import pygame

from eagle1.story.dialogue_db import DialogueNode, DialogueOption, validate_dialogue_database


@dataclass(frozen=True)
class ViperCharacterProfile:
    """Character profile definition for an allied member of Viper Squad."""

    member_id: str          # "viper_1", "viper_2", "viper_3", "viper_4"
    unit_index: int         # 0, 1, 2, 3 (maps directly to HelldiverUnit.index)
    callsign: str           # e.g., "Viper-1 (Lead)"
    nickname: str           # "Apex", "Braker", "Ghost", "Doc"
    role: str               # "Squad Leader", "Heavy Munitions", "Recon & Sniper", "Combat Medic"
    specialty: str          # Combat specialization description
    demeanor: str           # Psychological traits and attitude
    preferred_stance: str   # Ideological leaning: "loyal", "neutral", or "dissident"
    disliked_stance: str    # Stance that antagonizes the character
    theme_color: Tuple[int, int, int]
    portrait_path: str      # Exact case-sensitive relative asset path
    bio: str


@dataclass(frozen=True)
class BanterLine:
    """A contextual in-flight radio callout line emitted during combat."""

    line_id: str
    member_id: str          # "viper_1" .. "viper_4"
    speaker: str            # e.g., 'Viper-1 "Apex"'
    category: str           # e.g., "cas_beacon_request", "low_health", "near_miss_bomb", etc.
    text: str
    portrait_path: str
    cooldown_sec: float = 8.0


VIPER_SQUAD_PROFILES: Dict[str, ViperCharacterProfile] = {
    "viper_1": ViperCharacterProfile(
        member_id="viper_1",
        unit_index=0,
        callsign="Viper-1 (Lead)",
        nickname="Apex",
        role="Squad Leader",
        specialty="Veteran Vanguard / Assault",
        demeanor="Dogmatic, boisterous, fanatical patriot",
        preferred_stance="loyal",
        disliked_stance="dissident",
        theme_color=(255, 215, 0),
        portrait_path="images/portraits/viper_1_apex.png",
        bio=(
            "Veteran vanguard commander who quotes the Federation handbook constantly. "
            "Believes Helldivers never die—they just re-deploy to higher glory."
        ),
    ),
    "viper_2": ViperCharacterProfile(
        member_id="viper_2",
        unit_index=1,
        callsign="Viper-2 (Heavy)",
        nickname="Braker",
        role="Heavy Munitions",
        specialty="Autocannon Specialist / Anti-Armor",
        demeanor="Battle-scarred, cynical, realistic",
        preferred_stance="dissident",
        disliked_stance="loyal",
        theme_color=(52, 152, 219),
        portrait_path="images/portraits/viper_2_braker.png",
        bio=(
            "Survived three planetary campaigns through sheer stubbornness. "
            "Etches tally marks onto his autocannon breastplate for every fallen comrade."
        ),
    ),
    "viper_3": ViperCharacterProfile(
        member_id="viper_3",
        unit_index=2,
        callsign="Viper-3 (Scout)",
        nickname="Ghost",
        role="Recon & Sniper",
        specialty="DMR Marksman / Telemetry Analyst",
        demeanor="Quiet, analytical, high-strung",
        preferred_stance="neutral",
        disliked_stance="loyal",
        theme_color=(46, 204, 113),
        portrait_path="images/portraits/viper_3_ghost.png",
        bio=(
            "Recon marksman who constantly monitors radar pings and spots tactical discrepancies "
            "between orbital telemetry and actual enemy swarm counts."
        ),
    ),
    "viper_4": ViperCharacterProfile(
        member_id="viper_4",
        unit_index=3,
        callsign="Viper-4 (Medic)",
        nickname="Doc",
        role="Combat Medic",
        specialty="Field Trauma & Stim Operator",
        demeanor="Traumatized, compassionate, desperate for supplies",
        preferred_stance="dissident",
        disliked_stance="loyal",
        theme_color=(231, 76, 60),
        portrait_path="images/portraits/viper_4_doc.png",
        bio=(
            "Youngest squad member. Frantically applies tourniquets under heavy fire "
            "and pleads through static for medical resupply pods."
        ),
    ),
}


BANTER_QUEUES: Dict[str, List[BanterLine]] = {
    "pre_mission_briefing": [
        BanterLine(
            line_id="brief_apex_01",
            member_id="viper_1",
            speaker='Viper-1 "Apex"',
            category="pre_mission_briefing",
            text="Tubes sealed, Eagle-1! Give us clear skies and we will harvest the oil!",
            portrait_path="images/portraits/viper_1_apex.png",
        ),
        BanterLine(
            line_id="brief_braker_01",
            member_id="viper_2",
            speaker='Viper-2 "Braker"',
            category="pre_mission_briefing",
            text="Autocannon racked. Watch your ordnance lead, flygirl—don't shave my helmet off.",
            portrait_path="images/portraits/viper_2_braker.png",
        ),
        BanterLine(
            line_id="brief_ghost_01",
            member_id="viper_3",
            speaker='Viper-3 "Ghost"',
            category="pre_mission_briefing",
            text="Telemetry is glitching. Swarm density is triple what Command briefed us on.",
            portrait_path="images/portraits/viper_3_ghost.png",
        ),
        BanterLine(
            line_id="brief_doc_01",
            member_id="viper_4",
            speaker='Viper-4 "Doc"',
            category="pre_mission_briefing",
            text="Eagle-1, please... drop supplies early. We're already out of standard trauma stims.",
            portrait_path="images/portraits/viper_4_doc.png",
        ),
    ],
    "cas_beacon_request": [
        BanterLine(
            line_id="cas_apex_01",
            member_id="viper_1",
            speaker='Viper-1 "Apex"',
            category="cas_beacon_request",
            text="CAS beacon planted! Eagle-1, deliver the judgment of Super Earth!",
            portrait_path="images/portraits/viper_1_apex.png",
        ),
        BanterLine(
            line_id="cas_ghost_01",
            member_id="viper_3",
            speaker='Viper-3 "Ghost"',
            category="cas_beacon_request",
            text="Laser designating heavy cluster at red smoke! Confirming strike coordinates!",
            portrait_path="images/portraits/viper_3_ghost.png",
        ),
        BanterLine(
            line_id="cas_doc_01",
            member_id="viper_4",
            speaker='Viper-4 "Doc"',
            category="cas_beacon_request",
            text="They're overrunning our trench! Eagle, bring the rain right on top of our beacon!",
            portrait_path="images/portraits/viper_4_doc.png",
        ),
    ],
    "low_ammo": [
        BanterLine(
            line_id="ammo_braker_01",
            member_id="viper_2",
            speaker='Viper-2 "Braker"',
            category="low_ammo",
            text="Down to my last drum! Where is that resupply pod?!",
            portrait_path="images/portraits/viper_2_braker.png",
        ),
        BanterLine(
            line_id="ammo_ghost_01",
            member_id="viper_3",
            speaker='Viper-3 "Ghost"',
            category="low_ammo",
            text="Sniper mags depleted. Switching to sidearm. Air support needed immediately!",
            portrait_path="images/portraits/viper_3_ghost.png",
        ),
    ],
    "low_health": [
        BanterLine(
            line_id="hp_doc_01",
            member_id="viper_4",
            speaker='Viper-4 "Doc"',
            category="low_health",
            text="I'm hit! Chest seal ruptured! Doc is bleeding out, someone cover me!",
            portrait_path="images/portraits/viper_4_doc.png",
            cooldown_sec=12.0,
        ),
        BanterLine(
            line_id="hp_braker_01",
            member_id="viper_2",
            speaker='Viper-2 "Braker"',
            category="low_health",
            text="Armor breach! I can feel the shrapnel grinding! Give us suppressing fire!",
            portrait_path="images/portraits/viper_2_braker.png",
            cooldown_sec=12.0,
        ),
        BanterLine(
            line_id="hp_apex_01",
            member_id="viper_1",
            speaker='Viper-1 "Apex"',
            category="low_health",
            text="Flesh is temporary, Liberty is forever! Push through the blood, Vipers!",
            portrait_path="images/portraits/viper_1_apex.png",
            cooldown_sec=12.0,
        ),
    ],
    "near_miss_bomb": [
        BanterLine(
            line_id="near_braker_01",
            member_id="viper_2",
            speaker='Viper-2 "Braker"',
            category="near_miss_bomb",
            text="Jesus, Val! The shockwave threw me against a rock! Watch your damn drop lead!",
            portrait_path="images/portraits/viper_2_braker.png",
            cooldown_sec=10.0,
        ),
        BanterLine(
            line_id="near_doc_01",
            member_id="viper_4",
            speaker='Viper-4 "Doc"',
            category="near_miss_bomb",
            text="That bomb dropped right on our perimeter! My ears are ringing with static!",
            portrait_path="images/portraits/viper_4_doc.png",
            cooldown_sec=10.0,
        ),
    ],
    "stratagem_drop": [
        BanterLine(
            line_id="drop_apex_01",
            member_id="viper_1",
            speaker='Viper-1 "Apex"',
            category="stratagem_drop",
            text="Ordnance away! Feast on democratic steel, you soulless gears!",
            portrait_path="images/portraits/viper_1_apex.png",
        ),
        BanterLine(
            line_id="drop_ghost_01",
            member_id="viper_3",
            speaker='Viper-3 "Ghost"',
            category="stratagem_drop",
            text="Good hit, Eagle-1! Impact zone saturated, hostiles scattered!",
            portrait_path="images/portraits/viper_3_ghost.png",
        ),
    ],
    "kill_streak": [
        BanterLine(
            line_id="kill_doc_01",
            member_id="viper_4",
            speaker='Viper-4 "Doc"',
            category="kill_streak",
            text="Did you see that pass?! Eagle just turned that squad into burning scrap!",
            portrait_path="images/portraits/viper_4_doc.png",
        ),
        BanterLine(
            line_id="kill_apex_01",
            member_id="viper_1",
            speaker='Viper-1 "Apex"',
            category="kill_streak",
            text="Magnificent gunnery, Lieutenant! The skies sing of Managed Democracy!",
            portrait_path="images/portraits/viper_1_apex.png",
        ),
        BanterLine(
            line_id="kill_braker_01",
            member_id="viper_2",
            speaker='Viper-2 "Braker"',
            category="kill_streak",
            text="Five clankers dropped in one vector. Keep that up and we might actually live.",
            portrait_path="images/portraits/viper_2_braker.png",
        ),
    ],
    "casualty": [
        BanterLine(
            line_id="cas_doc_down",
            member_id="viper_4",
            speaker='Viper-4 "Doc"',
            category="casualty",
            text="Man down! Helldiver down! I need pressure bandages right now!",
            portrait_path="images/portraits/viper_4_doc.png",
            cooldown_sec=14.0,
        ),
        BanterLine(
            line_id="cas_braker_down",
            member_id="viper_2",
            speaker='Viper-2 "Braker"',
            category="casualty",
            text="Another one gone... another name carved into the dirt. Avenge them, Eagle!",
            portrait_path="images/portraits/viper_2_braker.png",
            cooldown_sec=14.0,
        ),
        BanterLine(
            line_id="cas_apex_down",
            member_id="viper_1",
            speaker='Viper-1 "Apex"',
            category="casualty",
            text="Their sacrifice is recorded on the Pillar of Liberty! Close ranks and fire!",
            portrait_path="images/portraits/viper_1_apex.png",
            cooldown_sec=14.0,
        ),
    ],
    "supply_pod": [
        BanterLine(
            line_id="sup_doc_01",
            member_id="viper_4",
            speaker='Viper-4 "Doc"',
            category="supply_pod",
            text="Supply pod secured! Stims, tourniquets, fresh batteries! Thank God!",
            portrait_path="images/portraits/viper_4_doc.png",
        ),
        BanterLine(
            line_id="sup_braker_01",
            member_id="viper_2",
            speaker='Viper-2 "Braker"',
            category="supply_pod",
            text="Autocannon boxes down! Racking fresh AP-rounds. Back in the fight!",
            portrait_path="images/portraits/viper_2_braker.png",
        ),
    ],
}


VIPER_DIALOGUE_TREES: Dict[str, DialogueNode] = {
    "viper_1_deck_briefing": DialogueNode(
        node_id="viper_1_deck_briefing",
        speaker='Viper-1 "Apex"',
        location="SES Leviathan of Truth - Ready Room",
        prompt=(
            "Lieutenant Val! Look at this strike roster. Four drops scheduled today. "
            "High Command has blessed us with the front-line interdiction sector. "
            "Tell me your quad-cannons are ready to turn those metal freaks into scrap!"
        ),
        options={
            "loyal": DialogueOption(
                stance="loyal",
                key_name="1",
                key_code=pygame.K_1,
                label="[1. LOYAL] Quad-cannons racked and primed, Apex. For Super Earth!",
                loyalty_delta=+8.0,
                response="Apex: 'Outstanding, pilot! When we hit the dirt, we follow your contrails into glory!'",
            ),
            "neutral": DialogueOption(
                stance="neutral",
                key_name="2",
                key_code=pygame.K_2,
                label="[2. NEUTRAL] Maintenance checked ordnance mounts. Operational parameters are nominal.",
                loyalty_delta=0.0,
                response="Apex: 'By-the-book precision. That discipline will keep the Helldivers standing.'",
            ),
            "dissident": DialogueOption(
                stance="dissident",
                key_name="3",
                key_code=pygame.K_3,
                label="[3. DISSIDENT] Four drops in a single day is a death sentence, Apex. We need rest.",
                loyalty_delta=-8.0,
                response="Apex: 'Rest is for citizens on the core worlds, Val. Out here, exhaustion is treason.'",
            ),
        },
        portrait="images/portraits/viper_1_apex.png",
        act=1,
        sortie=1,
    ),
    "viper_2_deck_briefing": DialogueNode(
        node_id="viper_2_deck_briefing",
        speaker='Viper-2 "Braker"',
        location="SES Leviathan of Truth - Ready Room",
        prompt=(
            "Val. Take a look at these tally marks on my armor. Thirty-four scratches. "
            "Thirty-four kids who stepped into hellpods and never climbed back into Pelican-1. "
            "They tell you upstairs we're winning. Do you actually believe that garbage?"
        ),
        options={
            "loyal": DialogueOption(
                stance="loyal",
                key_name="1",
                key_code=pygame.K_1,
                label="[1. LOYAL] Every scratch represents freedom secured, Braker. Do not dishonor their sacrifice.",
                loyalty_delta=+8.0,
                response="Braker: 'Easy to preach when you have twin turbine engines to outrun the chainsaws.'",
            ),
            "neutral": DialogueOption(
                stance="neutral",
                key_name="2",
                key_code=pygame.K_2,
                label="[2. NEUTRAL] I fly CAS to protect the roster. Philosophical debates don't alter the combat grid.",
                loyalty_delta=0.0,
                response="Braker: 'At least you're honest about being a cog in the meat grinder.'",
            ),
            "dissident": DialogueOption(
                stance="dissident",
                key_name="3",
                key_code=pygame.K_3,
                label="[3. DISSIDENT] No, Braker. It's a meat grinder. And High Command treats us like spent brass.",
                loyalty_delta=-10.0,
                response="Braker: 'Keep your voice down... but thank you for speaking the truth, Val. Watch my back down there.'",
            ),
        },
        portrait="images/portraits/viper_2_braker.png",
        act=1,
        sortie=1,
    ),
    "viper_3_deck_briefing": DialogueNode(
        node_id="viper_3_deck_briefing",
        speaker='Viper-3 "Ghost"',
        location="SES Leviathan of Truth - Ready Room",
        prompt=(
            "Lieutenant. I intercepted the reconnaissance relay from Sector 4 before the bridge scrubbed it. "
            "The Automaton factory output is increasing exponentially. Their signal patterns don't match rebellion—"
            "they match an organized planetary defense. Why would High Command hide their factory logistics?"
        ),
        options={
            "loyal": DialogueOption(
                stance="loyal",
                key_name="1",
                key_code=pygame.K_1,
                label="[1. LOYAL] High Command filters data to protect morale. Questioning intelligence aids the enemy.",
                loyalty_delta=+8.0,
                response="Ghost: '...Understood, Lieutenant. I will purge the unverified telemetry logs.'",
            ),
            "neutral": DialogueOption(
                stance="neutral",
                key_name="2",
                key_code=pygame.K_2,
                label="[2. NEUTRAL] Provide the coordinates. I will program target lead according to observed signals.",
                loyalty_delta=0.0,
                response="Ghost: 'Forwarding frequency offsets to Eagle-1 radar datalink. Target convergence updated.'",
            ),
            "dissident": DialogueOption(
                stance="dissident",
                key_name="3",
                key_code=pygame.K_3,
                label="[3. DISSIDENT] Because the war was engineered, Ghost. If we win, the Ministry loses its mandate.",
                loyalty_delta=-10.0,
                response="Ghost: 'God... you see it too. Delete that comms packet before the Democracy Officer scans your datapad.'",
            ),
        },
        portrait="images/portraits/viper_3_ghost.png",
        act=1,
        sortie=1,
    ),
    "viper_4_deck_briefing": DialogueNode(
        node_id="viper_4_deck_briefing",
        speaker='Viper-4 "Doc"',
        location="SES Leviathan of Truth - Ready Room",
        prompt=(
            "Lieutenant Val... my hands won't stop shaking. On yesterday's drop, I ran out of coagulant. "
            "I had to hold private Walker's severed artery with bare fingers while clankers advanced. "
            "I submitted an emergency requisition for sixty stim packs. Supply denied it—said stims are luxury tier."
        ),
        options={
            "loyal": DialogueOption(
                stance="loyal",
                key_name="1",
                key_code=pygame.K_1,
                label="[1. LOYAL] Helldiver willpower conquers blood loss, Doc. Trust in Super Earth's doctrine.",
                loyalty_delta=+8.0,
                response="Doc: '...Right. Doctrine will stop arterial hemorrhages. Of course, Lieutenant.'",
            ),
            "neutral": DialogueOption(
                stance="neutral",
                key_name="2",
                key_code=pygame.K_2,
                label="[2. NEUTRAL] Call in supply pods the second you land. I will deploy emergency crates directly.",
                loyalty_delta=0.0,
                response="Doc: 'Thank you, Eagle-1. We will mark the supply drop LZ with green phosphorus.'",
            ),
            "dissident": DialogueOption(
                stance="dissident",
                key_name="3",
                key_code=pygame.K_3,
                label="[3. DISSIDENT] They are denying you bandages to cut costs, Doc. It's criminal negligence.",
                loyalty_delta=-10.0,
                response="Doc: 'They treat us worse than cattle... At least someone overhead feels human pity.'",
            ),
        },
        portrait="images/portraits/viper_4_doc.png",
        act=1,
        sortie=1,
    ),
    "viper_inflight_cas_crisis": DialogueNode(
        node_id="viper_inflight_cas_crisis",
        speaker="Viper Squad vs High Command",
        location="In-Flight Tactical Radio",
        prompt=(
            "Doc: 'Eagle-1! Braker took heavy shrapnel near the heavy walker foundry! We are pinned behind scrap girders!' "
            "Command: 'Eagle-1, ignore squad extraction plea! Deliver 500kg ordnance directly on the foundry immediately!'"
        ),
        options={
            "loyal": DialogueOption(
                stance="loyal",
                key_name="1",
                key_code=pygame.K_1,
                label="[1. LOYAL] Releasing 500kg! Strategic foundry elimination is priority one!",
                loyalty_delta=+10.0,
                response="Apex: 'The foundry is burning! Victory at any cost for the Federation!'",
            ),
            "neutral": DialogueOption(
                stance="neutral",
                key_name="2",
                key_code=pygame.K_2,
                label="[2. NEUTRAL] Adjusting delivery vector 40 meters east to optimize blast dispersion.",
                loyalty_delta=0.0,
                response="Ghost: 'Foundry destroyed! Shrapnel deflected by the berm—squad intact!'",
            ),
            "dissident": DialogueOption(
                stance="dissident",
                key_name="3",
                key_code=pygame.K_3,
                label="[3. DISSIDENT] Negative, Command! I am pulling up and suppressing with quad-cannons!",
                loyalty_delta=-10.0,
                response="Braker: 'You actually broke vector for us... Remind me to buy you a drink on the hangar deck.'",
            ),
        },
        portrait="images/portraits/viper_2_braker.png",
        act=1,
        sortie=2,
    ),
    "viper_debrief_flawless": DialogueNode(
        node_id="viper_debrief_flawless",
        speaker="Viper Squad (Full Squad)",
        location="SES Leviathan of Truth - Hangar Deck",
        prompt=(
            "Apex: 'Zero casualties, Lieutenant! Every single member of Viper Squad walked up the Pelican ramp!' "
            "Braker: 'First time in six drops nobody got zippered up in a body bag. Your CAS was flawless, Val.' "
            "Doc: 'No amputations today... Thank you for dropping those supply pods right when we needed them.'"
        ),
        options={
            "loyal": DialogueOption(
                stance="loyal",
                key_name="1",
                key_code=pygame.K_1,
                label="[1. LOYAL] Precision in the name of Super Earth. When we fight together, Liberty triumphs.",
                loyalty_delta=+8.0,
                response="Apex: 'Spoken like a champion of Managed Democracy! Tomorrow we strike even deeper!'",
            ),
            "neutral": DialogueOption(
                stance="neutral",
                key_name="2",
                key_code=pygame.K_2,
                label="[2. NEUTRAL] Ordnance expenditure was 94% efficient. Mission success within tolerances.",
                loyalty_delta=0.0,
                response="Ghost: 'Efficient and surgical. That is how wars of attrition are survived.'",
            ),
            "dissident": DialogueOption(
                stance="dissident",
                key_name="3",
                key_code=pygame.K_3,
                label="[3. DISSIDENT] We survived because we watched out for each other, not because of High Command.",
                loyalty_delta=-8.0,
                response="Braker: 'Damn straight. The brass upstairs didn't pull a single trigger down in that mud.'",
            ),
        },
        portrait="images/portraits/viper_1_apex.png",
        act=1,
        sortie=1,
    ),
    "viper_debrief_casualties": DialogueNode(
        node_id="viper_debrief_casualties",
        speaker="Viper Squad (Survivors)",
        location="SES Leviathan of Truth - Hangar Deck",
        prompt=(
            "Doc: 'The blood soaked right through my gloves... We brought back tags, but not the bodies. "
            "Automaton saws tore them apart before the Pelican touched down.' "
            "Braker: 'Another fresh dent in my chestplate. Another scratch. How many more drops, Val?'"
        ),
        options={
            "loyal": DialogueOption(
                stance="loyal",
                key_name="1",
                key_code=pygame.K_1,
                label="[1. LOYAL] Their names are inscribed in history. We don't grieve—we strike with doubled fury.",
                loyalty_delta=+8.0,
                response="Apex: 'Liberty requires sacrifice! We will avenge our brothers at sunrise!'",
            ),
            "neutral": DialogueOption(
                stance="neutral",
                key_name="2",
                key_code=pygame.K_2,
                label="[2. NEUTRAL] Standard casualty replacements are already requisitioned by Sector Logistics.",
                loyalty_delta=0.0,
                response="Braker: 'Requisitions and paperwork. That's all human life is worth to you people.'",
            ),
            "dissident": DialogueOption(
                stance="dissident",
                key_name="3",
                key_code=pygame.K_3,
                label="[3. DISSIDENT] It's wrong, Doc. No one should die screaming in toxic mud for corporate propaganda.",
                loyalty_delta=-10.0,
                response="Doc: '...Thank you, Val. Sometimes I feel like I'm the only one going mad.'",
            ),
        },
        portrait="images/portraits/viper_4_doc.png",
        act=1,
        sortie=1,
    ),
    "viper_debrief_replacements": DialogueNode(
        node_id="viper_debrief_replacements",
        speaker="Viper Replacement Recruits",
        location="SES Leviathan of Truth - Hangar Deck",
        prompt=(
            "Four fresh, pristine Hellpods hiss open on the crane deck. Four replacement Helldivers step out—"
            "their armor unmarked, faces hidden beneath mirrored visors, devoid of any memory of the squad that died. "
            "New Leader: 'Greetings, Eagle-1! We are Viper Squad! Ready to spill oil for Super Earth!'"
        ),
        options={
            "loyal": DialogueOption(
                stance="loyal",
                key_name="1",
                key_code=pygame.K_1,
                label="[1. LOYAL] Welcome to the frontline, Vipers! Super Earth welcomes your unwavering dedication!",
                loyalty_delta=+10.0,
                response="New Leader: 'For Democracy! We shall eradicate the enemies of Freedom!'",
            ),
            "neutral": DialogueOption(
                stance="neutral",
                key_name="2",
                key_code=pygame.K_2,
                label="[2. NEUTRAL] Sync your telemetry transponders to Eagle-1 radar channels. Deployment in four hours.",
                loyalty_delta=0.0,
                response="New Leader: 'Transponders synchronized. Standing by for catapult launch.'",
            ),
            "dissident": DialogueOption(
                stance="dissident",
                key_name="3",
                key_code=pygame.K_3,
                label="[3. DISSIDENT] You aren't Viper Squad. You're just fresh meat to feed the machine.",
                loyalty_delta=-12.0,
                response="New Leader: 'Ideological hesitation logged. Officer Reiner will be briefed, Lieutenant.'",
            ),
        },
        portrait="images/portraits/viper_1_apex.png",
        act=1,
        sortie=1,
    ),
}


def get_viper_profile(identifier: Union[str, int]) -> Optional[ViperCharacterProfile]:
    """Retrieve a Viper Squad character profile by member_id ('viper_1'), index (0..3), or nickname."""
    if identifier is None or isinstance(identifier, bool):
        return None

    if isinstance(identifier, int):
        for prof in VIPER_SQUAD_PROFILES.values():
            if prof.unit_index == identifier:
                return prof
        return None

    if not isinstance(identifier, str):
        return None

    clean_id = identifier.strip().lower()

    # Direct key lookup
    if clean_id in VIPER_SQUAD_PROFILES:
        return VIPER_SQUAD_PROFILES[clean_id]

    # Nickname / callsign match
    for prof in VIPER_SQUAD_PROFILES.values():
        if clean_id == prof.nickname.lower() or clean_id in prof.callsign.lower():
            return prof

    return None


def get_contextual_banter(
    category: str,
    member_id: Optional[str] = None,
    selection_index: int = 0,
) -> Optional[BanterLine]:
    """Select a contextual combat banter line with optional member filtering."""
    if not category or category not in BANTER_QUEUES:
        return None

    pool = BANTER_QUEUES[category]
    if not pool:
        return None

    if member_id:
        filtered = [line for line in pool if line.member_id == member_id]
        if filtered:
            pool = filtered

    idx = abs(int(selection_index)) % len(pool)
    return pool[idx]


def get_debrief_dialogue_node(casualties_count: int, squad_wiped: bool = False) -> DialogueNode:
    """Return the dynamic post-sortie debrief DialogueNode based on sortie casualty outcomes."""
    if squad_wiped or casualties_count >= 4:
        return VIPER_DIALOGUE_TREES["viper_debrief_replacements"]

    if casualties_count <= 0:
        return VIPER_DIALOGUE_TREES["viper_debrief_flawless"]

    return VIPER_DIALOGUE_TREES["viper_debrief_casualties"]


def validate_viper_dialogue_data() -> bool:
    """Validate completeness and schema integrity of Viper Squad narrative definitions."""
    required_ids = {"viper_1", "viper_2", "viper_3", "viper_4"}
    if set(VIPER_SQUAD_PROFILES.keys()) != required_ids:
        raise ValueError("VIPER_SQUAD_PROFILES must contain exactly viper_1 through viper_4.")

    for m_id, prof in VIPER_SQUAD_PROFILES.items():
        if not prof.callsign or not prof.nickname or not prof.role or not prof.portrait_path:
            raise ValueError(f"Profile {m_id} has incomplete string fields.")
        if prof.preferred_stance not in {"loyal", "neutral", "dissident"}:
            raise ValueError(f"Profile {m_id} has invalid preferred_stance '{prof.preferred_stance}'.")

    # Validate banter queues
    for cat_name, lines in BANTER_QUEUES.items():
        if not lines:
            raise ValueError(f"Banter category '{cat_name}' is empty.")
        for line in lines:
            if not line.text.strip() or not line.speaker.strip():
                raise ValueError(f"Banter line '{line.line_id}' in '{cat_name}' has empty text or speaker.")

    # Validate dialogue trees
    validate_dialogue_database(VIPER_DIALOGUE_TREES)
    return True
