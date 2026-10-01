# Eagle-1-64Bit

A 2D top-down space combat arcade game built in Python using Pygame. The game features an expansive 3000×3000 scrolling arena, inertia-driven flight mechanics, quad-cannon combat, homing rockets, radar lock-on modes, a power-up system, friendly Helldiver ground squads, hostile Automaton ground forces, destructible fabricators, a stratagem air strike arsenal, a dynamic predictive aiming reticle, and a fully interactive 6-tab in-game help menu.

![Eagle-1-64Bit Main Menu](images/Documentation%20images/main_menu.png)


## Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [Ground Support & Helldivers Subsystem](#ground-support--helldivers-subsystem)
  - [Allied Helldiver Squad (Viper 1-4)](#allied-helldiver-squad-viper-1-4)
  - [Hostile Ground Forces & Fabricators](#hostile-ground-forces--fabricators)
  - [Air-to-Ground Combat (Cannons, Rockets & Strikes)](#air-to-ground-combat-cannons-rockets--strikes)
  - [Helldiver Tactical CAS Call-In Missions](#helldiver-tactical-cas-call-in-missions)
  - [Tactical Supply Drops (`X`)](#tactical-supply-drops-x)
  - [Objectives & Pelican-1 Extraction](#objectives--pelican-1-extraction)
  - [Scoring & CAS Multipliers](#scoring--cas-multipliers)
- [Predictive Aiming Reticle System](#predictive-aiming-reticle-system)
- [Air Strike Weapon Arsenal](#air-strike-weapon-arsenal)
- [Power-Up System](#power-up-system)
- [Homing Rockets & Radar System](#homing-rockets--radar-system)
- [Help Menu (6 Tabs)](#help-menu-6-tabs)
- [Gameplay Description](#gameplay-description)
- [Controls](#controls)
- [Game Audio & Extensible Settings Architecture](#game-audio--extensible-settings-architecture)
- [Automated Testing Suite](#automated-testing-suite)
- [Requirements & Dependencies](#requirements--dependencies)
- [Installation Instructions](#installation-instructions)
- [Development Setup](#development-setup)
- [Run Instructions](#run-instructions)
- [Usage Examples](#usage-examples)
- [Project Architecture Overview](#project-architecture-overview)
- [Folder Structure Overview](#folder-structure-overview)
- [Asset Organization](#asset-organization)
- [Configuration Explanation](#configuration-explanation)
- [Troubleshooting](#troubleshooting)
- [License & Credits](#license--credits)



## Overview

**Eagle-1-64Bit** is an arcade space dogfighting game where players pilot a combat spacecraft across an expansive 3000×3000 pixel starfield. The game is engineered around a 60 FPS update loop and includes dynamic enemy spawns, surface battlefields with allied Helldivers and hostile Automaton forces, destructible foundries, air strikes, power-ups, radar targeting, and persistent highscore tracking.

A custom 2D camera tracks the player ship across the map, clamping to world borders and rendering seamless starfield background tiles. Combat combines primary quad-cannon salvos with secondary steerable homing rockets, 8 stratagem air strikes, and close air support missions for friendly ground troops fighting against hostile Automaton forces.


## Key Features

- **Mission Selection System:** Tactical operational menu (`game_state = "mission_select"`) featuring 5 focused modes to prevent chaotic gameplay.
- **5 Focused Operational Modes:**
  - **Air Superiority:** Pure aerial dogfighting against 5 wave squadrons (ground hostiles disabled).
  - **Orbital Base Defense:** Protect a stationary friendly Orbital Defense Base against heavy **Automaton Bombers**.
  - **Factory Strider Boss Raid:** Cooperate with Helldivers to destroy a colossal 6-legged **Factory Strider** walking fortress.
  - **Outpost Demolition:** Demolish 3 Automaton Fabricator foundries defended by Troopers & Walkers, then evacuate via Pelican-1.
  - **Endless War:** Combined full-scale classic operation featuring all ground and aerial hostiles.
- **Factory Strider Boss Ground Unit:** Colossal 500 HP 6-legged walking fortress equipped with twin chin dual lasers, top anti-air cannon, and internal trooper spawn bay.
- **Automaton Heavy Bombers:** Armored aerial bombers (160 HP, 15 damage bombs) targeting orbital base structures.
- **Friendly Orbital Defense Base:** Stationed command base (300 HP + 100 Shield) with rotating radar and shield perimeter.
- **Top HUD Mission Objective Tracker Banner:** Real-time top-center HUD objective tracker displaying active mission goals, base hull integrity, and boss HP bars.
- **Large Continuous World Arena:** 3000×3000 pixel world with seamless background tiling and camera viewport clamping.
- **Out-of-Bounds Hazard Zone:** World boundaries are highlighted with a 4-pixel red border. Flying beyond boundary coordinates inflicts continuous boundary damage.
- **Inertia & Momentum Flight Dynamics:** Ships maintain continuous forward movement in their heading direction with smooth turn acceleration.
- **Quad-Cannon Primary Fire:** Each primary attack unloads 4 bullets simultaneously from distinct wing-mounted offsets.
- **Secondary Homing Rockets:** Players can launch steerable homing missiles that lock onto aerial hostiles, bombers, ground units, fabricators, and the Factory Strider.
- **Dual Radar Lock-On Modes:** Switch between directional forward cone radar (`CONE`) and 360-degree close-range perimeter radar (`OMNI`).
- **Allied Helldiver Ground Support Subsystem:** Deploy and protect a 4-trooper ground squad (Viper 1-4) with obstacle avoidance and anti-air cover fire.
- **Hostile Ground Units (Automaton Troopers & Walkers):** Enemy ground forces advancing across the terrain and engaging Helldivers with red laser fire.
- **Destructible Automaton Fabricators:** Heavy enemy foundry structures that continuously produce ground reinforcements until demolished by cannons, rockets, or bombs.
- **Air-to-Ground Combat:** Quad-cannons, homing rockets, and stratagem air strikes directly damage and eliminate ground hostiles and structures.
- **Tactical CAS Call-In Missions:** Helldivers under pressure call in Close Air Support strikes (weapon-agnostic, supporting 500kg bombs and all other stratagems), awarding +500 PTS upon delivery.
- **Dynamic Aiming Reticle:** Projects a forward gun convergence pip and a weapon-specific predictive bomb impact zone that leads the ship based on velocity and angle, highlighting target locks.
- **Air Strike Stratagem Arsenal & Weapon Menu:** Interactive selection menu (`V` / `TAB`) featuring 8 devastating air strikes fired via `C`.
- **Tactical Orbital Supply Drops:** Call in orbital supply pods (`X`) providing squad healing, ammo reloads, hull repair, and shield nanites.
- **Danger Zone Alerts & Off-Screen Compass:** Real-time threat detection and directional guidance towards endangered allies.
- **Dynamic Objectives & Pelican-1 Extraction:** Outpost defense transitioning into a 30-second extraction countdown with shuttle evacuation.
- **Modular Power-Up Subsystem:** 8 distinct abilities across Common, Rare, and Epic tiers, featuring drop chances with pity protection.
- **Guaranteed Score Milestone Airdrops:** Reaching major score milestones automatically summons guaranteed supply crates.
- **Dual Defense System (Shield + Health):** Energy shields absorb incoming damage before hull health is impacted.
- **Tactical Ramming / Kamikaze Damage:** Direct physical collisions with enemy craft deal damage to both sides.
- **Autonomous Enemy Aircraft:** Hostile `Light_Enemy` units spawn in coordinated squadrons with flocking and combat AI.
- **In-Game Help Menu (6 Tabs):** Multi-tab help overlay providing weapons, abilities, radar, controls, wave combat, and Helldiver support guidance.
- **Automated Headless Test Suite:** 25 automated pytest tests covering mission configs, ground combat, fabricators, stratagems, flight physics, persistence, and UI menus.



## Ground Support & Helldivers Subsystem

The ground support subsystem (`ground_support.py`) brings a living planetary battlefield to life. Players command Close Air Support (CAS) from Eagle-1 to protect, resupply, and evacuate an allied 4-trooper ground squad on the surface while battling hostile Automaton ground forces.

### Allied Helldiver Squad (Viper 1-4)

- **Squad Roster:**
  - **Viper-1 (Lead):** Squad Leader with balanced tactical rifle.
  - **Viper-2 (Heavy):** Heavy Gunner deploying suppressing anti-air fire.
  - **Viper-3 (Scout):** Marksman delivering long-range precision rounds.
  - **Viper-4 (Medic):** Combat Medic providing tactical squad stabilization.
- **Autonomous Tactical AI:**
  - Navigates around terrain obstacles, bunkers, and sandbag barricades.
  - Automatically engages low-flying hostile aircraft with upward tracer rounds within 420px.
  - Engages enemy Automaton ground forces in fire-fights.
  - Intelligently paths towards landed Supply Pods when injured.
  - Moves to board the Pelican-1 dropship during extraction.
- **Health & Armor Tracking:** Overhead health/shield gauges and real-time state tags: `DEFENDING`, `ENGAGING`, `SUPPLYING`, `EXTRACTING`, and `K.I.A.`.
- **Minimap Representation:** Rendered as bright cyan blips surrounded by a defensive perimeter circle.

### Hostile Ground Forces & Fabricators

- **Automaton Troopers (`EnemyGroundUnit` - Trooper):**
  - Fast-moving foot soldiers (35 HP, 25 PTS) armed with red laser blasters.
  - Form battle lines and advance towards Helldiver defensive positions.
- **Automaton Heavy Walkers (`EnemyGroundUnit` - Walker):**
  - Armored bipedal walkers (120 HP, 60 PTS) equipped with rapid dual-pulse lasers.
  - Absorb sustained fire and pose high threat to Helldiver shields.
- **Automaton Fabricators (`EnemyFabricator`):**
  - Fortified manufacturing structures (220 HP, 150 PTS) with glowing thermal exhaust ports and factory antennas.
  - Continuously construct and deploy ground reinforcements (Troopers & Walkers) every 8 seconds.
  - Can be targeted and destroyed by cannons, homing rockets, and precision air strikes, triggering multi-stage secondary explosions.

### Air-to-Ground Combat (Cannons, Rockets & Strikes)

- **Quad-Cannon Ground Strafing (`Spacebar`):**
  - Player bullets collide with and damage Automaton Troopers, Walkers, and Fabricator buildings.
  - Floating score popups (`+25 PTS`, `+60 PTS`, `+150 PTS`) indicate confirmed ground kills.
- **Homing Rockets Ground Lock-on (`Right-Click` or `E` / `F` / `LCTRL`):**
  - Homing missiles acquire ground hostiles and fabricators within radar coverage (`CONE` or `OMNI`), steering downward to detonate directly on target.
- **Stratagem Air Strikes (`C`):**
  - All 8 stratagem strikes damage both aerial hostiles and ground targets within their blast radius.

### Helldiver Tactical CAS Call-In Missions

- **Tactical CAS Requests (`SquadAirStrikeRequest`):**
  - When pressed by Automaton forces, the Helldivers deploy a tactical beacon beam and radio for Close Air Support.
  - Compatible with **all 8 stratagems** (e.g. Eagle 500kg Bomb, Napalm Strike, Cluster Bomb, Strafing Run, Gas Strike, Rocket Pods).
- **Automated Preparation:**
  - The requested stratagem is automatically prepared in the player's weapon menu with its cooldown bypassed for immediate deployment.
- **HUD Guidance:**
  - Displays a high-priority warning banner: `"TACTICAL CAS REQUESTED: DELIVER [WEAPON] TO TARGET ZONE"`.
  - An orbital beacon illuminates the coordinates, and the off-screen compass points directly toward the strike zone.
- **Delivery Reward:**
  - Releasing the requested ordnance over the target coordinates delivers the strike, granting a **`+500 PTS`** mission delivery bonus.

### Tactical Supply Drops (`X`)

- Deploy an orbital resupply pod via key **`X`** (30s cooldown).
- Lands with a deceleration thruster and deploys medical nanites and ammo crates.
- Restores shields and 60 HP to nearby Helldivers.
- Flying over the pod fully replenishes the player's quad-cannon bullets, homing rockets, energy shields, and repairs hull damage.

### Objectives & Pelican-1 Extraction

- **Phase 1: Outpost Defense (Waves 1-2):** Hold the line against hostile waves.
- **Phase 2: Pelican-1 Extraction (Wave 3+):** Extraction beacon activates with a 30-second countdown. Helldivers fall back and board the shuttle upon landing.
- **Objective Failure:** If all 4 Helldivers perish, the objective fails with score deductions.

### Scoring & CAS Multipliers

- **Close Air Support Bonus (+100 PTS):** Awarded when destroying hostiles near allied units.
- **CAS Mission Delivery Bonus (+500 PTS):** Awarded upon successfully delivering a requested strike to a Helldiver CAS beacon.
- **Fabricator Demolition (+150 PTS):** Awarded for destroying an Automaton factory.
- **Wave Survival Bonus (+500 PTS per Helldiver):** Awarded at wave clear per surviving squad member.
- **Flawless Protection Multiplier (1.5×):** Multiplies survivor bonuses by 1.5× if zero allied casualties were sustained.
- **Casualty Penalty (-250 PTS):** Deducted upon the loss of an allied Helldiver.
- **Pelican-1 Extraction (+2,500 PTS):** Awarded on successful evacuation of the ground squad.



## Predictive Aiming Reticle System

The dynamic aiming reticle (`AimingReticle` in `ground_support.py`) provides real-time fire-control projection:

1. **Gun Convergence Pip:**
   - Projects a subtle cyan crosshair pip at 180px in front of the aircraft along the current flight heading for gun strafing runs.
2. **Predictive Bomb / Strike Landing Zone:**
   - Calculates the exact projected ordnance landing coordinates ahead of the ship based on forward velocity and angle:
     $$\text{lead} = 320.0 + v \times 8.0$$
   - **Weapon-Specific Footprints:**
     - **Eagle 500kg Bomb:** Colossal circular blast perimeter with central target crosshairs.
     - **Strafing Run:** Directional rectangular corridor showing the 20mm cannon spray lane.
     - **Napalm Strike:** Wide perpendicular incendiary bar showing the firewall barrier.
     - **Cluster Bomb:** Multi-point submunition scatter pattern.
     - **Gas / EMS / Smoke:** Spherical dispersion ring matching effect radius.
3. **Target Lock Indicator:**
   - The reticle ring shifts to bright crimson with pulsing lock crosshairs whenever the predicted impact area is centered over enemy ground units, fabricators, or Helldiver CAS beacons.



## Air Strike Weapon Arsenal

Access the comprehensive stratagem arsenal by pressing **`V`** or **`TAB`** to open the interactive **Air Strike Weapon Menu**, or press number keys **`1`** through **`8`** for instant quick-selection during flight. Deploy the selected strike along your heading using **`C`**.

### Stratagem Arsenal Table

| Key | Stratagem | Cooldown | Blast Profile | Effect & Tactical Application |
| :---: | :--- | :---: | :--- | :--- |
| **`1`** | **Machine Gun Dive** | 12.0s | Straight-line stream | 26 rapid 20mm rotary cannon tracer rounds shredding targets along flight vector. |
| **`2`** | **Eagle 500kg Bomb** | 35.0s | 320px Colossal blast | High-explosive ground-zero detonation dealing massive 16.0 burst damage. |
| **`3`** | **Cluster Bomb** | 18.0s | 280px Carpet saturation | 8 explosive sub-munitions blanketing a wide circular area against swarms. |
| **`4`** | **Napalm Strike** | 22.0s | 300px Wall of fire | Line of searing incendiary canisters igniting enemies with heavy burning damage over 6.5s. |
| **`5`** | **Gas Strike** | 18.0s | 240px Corrosive cloud | Lingering chemical cloud inflicting rapid corrosive tick damage and slowing enemies for 7.0s. |
| **`6`** | **Rocket Pods** | 20.0s | 3 Guided missiles | Heavy armor-piercing guided anti-tank missiles tracking priority hostile craft. |
| **`7`** | **EMS Stun Strike** | 24.0s | 280px EMP wave | Electromagnetic pulse disabling and freezing enemy flight systems and engines for 4.5s. |
| **`8`** | **Smoke Screen** | 22.0s | 280px Radar cloud | Thick radar-absorbing smoke screen breaking enemy agro and concealing ground forces. |


## Power-Up System

The game incorporates a dedicated power-up subsystem (`powerup_system.py`) providing 8 unique abilities divided into three rarity tiers.

### Abilities Table

| Ability | Symbol | Category | Rarity | Duration | Effect |
| :--- | :---: | :--- | :--- | :---: | :--- |
| **Rapid Fire** | `RF` | Offensive | **Common** | 10.0s | Cannon fire delay halved; reload delay reduced. |
| **Shield Bubble** | `SB` | Defensive | **Common** | 10.0s | Grants temporary shield overcharge and boosts shield regeneration. |
| **Thruster Overdrive** | `TO` | Utility | **Common** | 10.0s | Boosts max speed, acceleration, and turning rate. |
| **Chrono Slip** | `CS` | Utility | **Rare** | 8.0s | Slows enemy flight and projectile speed. |
| **Cryo Frostbite** | `CF` | Offensive / Utility | **Rare** | 10.0s | Slows enemies and can freeze them after repeated hits. |
| **Damage Multiplier** | `DM` | Offensive | **Rare** | 10.0s | Doubles primary cannon damage. |
| **Vanguard Drone** | `VD` | Defensive / Offensive | **Epic** | 20.0s | Deploys an escort drone that intercepts bullets and attacks enemies. |
| **Swarm Homing Pods** | `HP` | Offensive | **Epic** | 12.0s | Automatically launches self-guided micro-missiles at enemy craft. |

### Drop & Spawn Mechanics

- **Enemy Kill Drops:** Defeating an enemy has a base drop chance of **8%**.
- **Pity Counter:** Every kill without a drop adds **+3%** to the drop chance.
- **Rarity Weights:** Common drops occur 70% of the time, Rare drops 20%, and Epic drops 10%.
- **Drop Entity Lifecycle:** Drops float with bobbing animations, a pulsing glow ring, and rarity color indicators.
- **Magnetic Draw:** When the player flies within range, the drop is attracted toward the ship.
- **Score Milestones:** Major score milestones summon guaranteed supply airdrops.



## Homing Rockets & Radar System

### Secondary Homing Rockets (`Player.Rocket`)

- **Capacity & Reload:** Carries up to 4 rockets and reloads automatically when depleted.
- **Target Acquisition:** Acquires both aerial squadrons and ground hostiles (Automaton Troopers, Walkers, Fabricators).
- **Fire Controls:** Triggered using **Right Mouse Button**, `E`, `F`, or `Left Control`.
- **Flight Dynamics:** Rockets travel with smooth turning physics and explode on impact.

### Dual Radar Modes (Toggle with `Q`)

- **`CONE` Mode (Long-Range Intercept):** Forward search arc (300px to 1050px) for head-on approaches.
- **`OMNI` Mode (Close-Quarter Defense):** Full 360-degree perimeter scan (0px to 420px) for dogfighting and ground strafing.
- **Target Lock Indicator:** Bounding lock boxes highlight tracked hostiles on HUD and minimap.



## Help Menu (6 Tabs)

Access the interactive in-game tactical manual at any time by pressing **`H`**. Navigate tabs using number keys **`1`** through **`6`** or by clicking the tab headers:

| Tab | Title | Description |
| :---: | :--- | :--- |
| **1** | **Weapons & Combat** | Damage, velocities, ranges, cooldowns, and magazine stats for quad-cannons and homing rockets. |
| **2** | **Abilities & Buffs** | Complete catalog of 8 tactical power-ups across Common, Rare, and Epic tiers. |
| **3** | **Radar Modes (Q)** | Visual guide explaining long-range `CONE` vs close-range `OMNI` target tracking. |
| **4** | **Controls Manual** | Complete flight, combat, weapon switching, and menu keybindings table. |
| **5** | **Wave Combat & Survival** | Wave enemy types, escort drones, milestone airdrops, and scoring multipliers. |
| **6** | **Helldivers & Strikes** | Ground squad roles, Automaton hostiles, fabricators, CAS call-in missions, and Pelican-1 extraction. |



## Gameplay Description

### Objectives

1. **Survive:** Pilot your ship across the arena while staying within the boundary perimeter.
2. **Eliminate Aerial Threats:** Intercept descending `Light_Enemy` fighters with quad cannons and homing rockets.
3. **Protect Helldiver Squad:** Provide Close Air Support to the 4-trooper ground squad fighting Automaton ground forces.
4. **Demolish Fabricators:** Destroy Automaton foundries to halt enemy ground reinforcement waves.
5. **Execute CAS Missions:** Answer Helldiver strike requests by delivering the designated ordnance to target beacons.
6. **Evacuate the Squad:** Defend the extraction beacon in Wave 3+ until Pelican-1 safely extracts the squad.
7. **Surpass Highscores:** Beat your personal best, saved automatically to disk.

### Combat & Flight Mechanics

- **Continuous Velocity:** The ship is always in motion along its facing angle.
- **Quad Salvos:** Pressing Space fires 4 bullets simultaneously from 4 wing offsets.
- **Shield Absorption:** Incoming damage drains shield points first.
- **Reload Downtime:** Firing consumes ammunition and forces periodic reloads.
- **Ramming:** You can ram enemies to deal collision damage, but you will take damage too.

### Game States

```text
[ Launch Application ]
          │
          ▼
  ┌───────────────┐
  │   Main Menu   │
  └───────┬───────┘
          │
          ▼
  ┌───────────────┐         ┌───────────────┐
  │   Gameplay    │ ── P ──►│  Pause Menu   │
  └───────┬───────┘         └───────┬───────┘
          │                         │
          ▼                         │
  ┌───────────────┐                 │
  │   Game Over   │◄────────────────┘
  └───────┬───────┘
          │
          ▼
 [ Respawn & Play ]
```



## Controls

| Action | Primary Key | Secondary Key | Applicable State |
| :--- | :--- | :--- | :--- |
| **Start Game** | `Left Shift` | `Right Shift` or Click `PLAY` | Main Menu |
| **Reset Highscore** | `L-Shift + R-Shift + R` (Hold) | — | Main Menu |
| **Steer Left (Counter-Clockwise)** | `A` | `Left Arrow` | Active Gameplay |
| **Steer Right (Clockwise)** | `D` | `Right Arrow` | Active Gameplay |
| **Accelerate / Increase Speed** | `W` | `Up Arrow` | Active Gameplay |
| **Decelerate / Decrease Speed** | `S` | `Down Arrow` | Active Gameplay |
| **Fire Quad Cannons** | `Spacebar` | — | Active Gameplay |
| **Fire Secondary Homing Rocket** | `Right Mouse Button` | `E`, `F`, or `LCTRL` | Active Gameplay |
| **Launch Active Air Strike** | `C` | — | Active Gameplay |
| **Call Tactical Supply Drop** | `X` | — | Active Gameplay |
| **Toggle Air Strike Weapon Menu** | `V` | `TAB` | Active Gameplay |
| **Quick-Select Stratagems (1-8)** | `1` - `8` | — | Active Gameplay / Menu |
| **Toggle Radar Mode (`CONE` / `OMNI`)** | `Q` | — | Active Gameplay |
| **Open Help Menu** | `H` | — | Main Menu / Pause Menu / Game Over |
| **Help Menu Tabs (1-6)** | `1` - `6` | Click Tabs | Help Menu |
| **Open Settings & Audio Menu** | `O` | Click `SETTINGS` | Main Menu / Pause Menu / Game Over / Gameplay |
| **Settings Menu Tabs (1-3)** | `1` - `3` | Click Tabs | Settings Menu |
| **Instant Mute / Unmute Audio** | `M` | — | All States |
| **Pause Game** | `P` | — | Active Gameplay |
| **Resume Game** | `P` | Click `CONTINUE` | Pause Menu |
| **Return to Main Menu** | `Escape` (`ESC`) | Click `MAIN MENU` | Pause Menu |
| **Close Help / Settings / Weapon Menu** | `Escape` (`ESC`) | Click `X` / close button | In Menus |
| **Respawn** | `R` | Click `RESPAWN` | Game Over (`Health <= 0`) |
| **Return to Main Menu** | `Spacebar` | Click `MAIN MENU` | Game Over (`Health <= 0`) |
## Game Audio & Extensible Settings Architecture

Eagle-1-64Bit features a centralized, 16-channel audio system (`audio_manager.py`) with procedural audio generation (`generate_audio_assets.py`), dynamic combat music adaptation, thruster engine sound modulation, anti-clipping voice limiting, and an extensible tabbed Settings Menu (`settings_menu.py`).

### Key Audio Features
- **Centralized 16-Channel Mixer**: Dedicated low-latency voices for primary cannons, rockets, enemy gunfire, hits, explosions, alarms, pickups, UI feedback, and continuous engine loop.
- **Procedural High-Fidelity Synthesis**: 17 sound effects and 4 full music loops generated at 44.1kHz 16-bit stereo PCM with zero external download dependencies (supports dropping custom `.wav`/`.ogg` assets directly into `audio/`).
- **Dynamic Combat Music**: Automatically scales musical intensity between normal synthwave combat loops and high-threat themes based on active agro enemies, bombers, Factory Striders, or low health.
- **Flight Velocity-Modulated Engine Hum**: Continuous jet thruster frequency and volume scale smoothly with player acceleration and flight speed.
- **Anti-Clipping & Voice Limiting**: Configurable minimum intervals prevent audio stacking during intense bullet storms.
- **Extensible Settings Menu**: Modular, tabbed interface (`1. Audio Settings`, `2. Gameplay & HUD`, `3. Flight Controls`) with interactive volume sliders (Master, Music, SFX), Mute toggle switch, SFX test button, and persistence to `data/audio_settings.json`. Easily extended with new categories and options.



## Automated Testing Suite

The repository includes a comprehensive, headless automated test suite powered by `pytest` and configured via `pyproject.toml`. Headless dummy video and audio drivers (`SDL_VIDEODRIVER=dummy`, `SDL_AUDIODRIVER=dummy`) are initialized automatically in `tests/conftest.py`:

```bash
python -m pytest
```

Or run `pytest` directly with detailed test reporting:

```bash
pytest -v
```

### Test Coverage Summary (25 Tests)

- **`tests/test_ground_support.py` (4 tests):**
  - Initial squad roster instantiation (Viper 1-4 with full health and shields).
  - Helldiver callsigns and role assignments (Lead, Heavy, Scout, Medic).
  - Supply drop pod parachute descent, ground landing, and replenishment availability.
  - CAS ground delivery bonus (`+500 PTS`) and survivor wave reward (`+500 PTS`) constants.
- **`tests/test_health_and_damage.py` (4 tests):**
  - Player initial health (5 HP) and shield (20 points) setup.
  - Shields-first damage absorption priority preserving hull integrity.
  - Spillover mechanics when damage exceeds current shield capacity.
  - Post-hit invulnerability state preventing overlapping damage.
- **`tests/test_math_and_physics.py` (4 tests):**
  - Flight speed boundaries clamped between `PLAYER_MIN_SPEED` (2.0) and `PLAYER_MAX_SPEED` (7.0).
  - Camera viewport coordinate clamping against map boundaries (`0 .. 3000`).
  - Dynamic predictive reticle lead formula ($\text{lead} = 320.0 + v \times 8.0$).
  - Radar operational search ranges for directional `CONE` and 360° `OMNI` modes.
- **`tests/test_persistence.py` (3 tests):**
  - Safe high score reading, writing, and corrupted-file recovery using temporary files.
  - Audio settings fallback to default values when configuration file is missing.
  - Graceful partial-key dictionary merging for missing settings.
- **`tests/test_powerups.py` (4 tests):**
  - Ability definitions catalog (8 abilities across Common, Rare, and Epic tiers).
  - Initial `PowerUpManager` state verification.
  - Power-up drop entity lifecycle, positioning, and expiration countdown.
  - Pity system probability progression and base drop constants.
- **`tests/test_ui_and_menus.py` (3 tests):**
  - Help menu 6-tab cycle, boundary wrapping, and headless render execution.
  - Settings menu 3-tab navigation, slider updates, and headless drawing.
  - Audio manager mute state toggling.
- **`tests/test_weapons_and_cooldowns.py` (3 tests):**
  - Primary quad-cannon capacity (200 rounds) and reload timer (5.0s).
  - Secondary homing rocket payload (4 missiles) and reload cycle (25.0s).
  - Stratagem definitions (8 air strikes with cooldowns, blast radii, and tactical metadata).



## Requirements & Dependencies

- **Python:** Python 3.9+ (compatible with Python 3.10, 3.11, 3.12, 3.13, 3.14)
- **Core Dependencies:**
  - `pygame-ce>=2.5.0` (or `pygame>=2.5.0`)
- **Development & Testing Dependencies:**
  - `pytest>=8.0.0`
  - `ruff>=0.5.0`
  - `pyinstaller>=6.5.0`
- **Standard Library:** `os`, `sys`, `random`, `math`, `json`, `pathlib`



## Installation Instructions

1. Clone the repository:
   ```bash
   git clone https://github.com/paulp143/Eagle-1-64Bit.git
   cd Eagle-1-64Bit
   ```

2. Install runtime dependencies:
   ```bash
   pip install -r requirements.txt
   ```

   *Alternatively, install the package in editable mode:*
   ```bash
   pip install -e .
   ```



## Development Setup

To configure an isolated virtual environment for development and testing:

1. Create a virtual environment:
   ```bash
   python -m venv venv
   ```

2. Activate the virtual environment:
   - **Windows (PowerShell):** `venv\Scripts\Activate.ps1`
   - **Windows (CMD):** `venv\Scripts\activate.bat`
   - **Linux / macOS:** `source venv/bin/activate`

3. Install development dependencies:
   ```bash
   pip install -r requirements-dev.txt
   pip install -e .
   ```

4. Run the automated test suite:
   ```bash
   python -m pytest
   ```

5. Run code linting:
   ```bash
   ruff check .
   ```

6. Generate procedural audio waveforms (if needed):
   ```bash
   python tools/generate_audio_assets.py
   ```

---

## Run Instructions

Eagle-1-64Bit can be launched through multiple interfaces:

### Option 1: Installed Console Command
If installed via `pip install -e .`:
```bash
eagle1
```

### Option 2: Python Module Execution
```bash
python -m eagle1
```

### Option 3: Repository Root Launcher
```bash
python run_game.py
```

### Option 4: Compatibility Launcher
```bash
python main.py
```



## Usage Examples

### Starting a Standard Game Session

1. Run `python main.py`.
2. Press `Shift` or click `PLAY`.
3. Steer with `A`/`D` and adjust throttle with `W`/`S`.
4. Fire quad cannons with `Spacebar`, and launch homing rockets with `Right Click` when locked on.
5. Press `V` or `1`-`8` to choose an air strike stratagem; press `C` to deploy it.
6. Check on the Helldiver squad; when they call in CAS, fly to the beacon to deliver ordnance for `+500 PTS`.
7. Destroy Automaton Fabricators to stop enemy ground reinforcement waves.
8. Call a supply drop with `X` when running low on ammo or when the ground squad is wounded.
9. Press `H` at any time to open the tactical help manual.

### Resetting the Highscore

1. Launch to the main menu.
2. Press and hold `Left Shift` + `Right Shift` + `R`.
3. The stored highscore in `data/highscore.txt` will reset to `0`.



## Project Architecture Overview

```text
src/eagle1/
├── __main__.py               # CLI entrypoint for `eagle1` and `python -m eagle1`
├── paths.py                  # Centralized cross-platform asset, data, and root path resolver
├── effects.py                # Visual FX, particle bursts, floating damage & score text
├── app/
│   └── game.py               # 60 FPS main game loop, camera, player aircraft, aerial combat,
│                             # wave management, combat state machine, rendering pipeline, HUD
├── systems/
│   ├── ground_support.py     # Helldivers (Viper 1-4), Automaton ground units, fabricators,
│   │                         # Factory Strider boss, stratagems, CAS beacon requests,
│   │                         # supply drops, predictive reticle, weapon selection menu
│   ├── powerups.py           # 8 abilities across 3 rarities, drop mechanics with pity counter,
│   │                         # magnetics, escort drones, swarm homing micro-missiles
│   └── audio_manager.py      # Centralized 16-channel mixer, procedural SFX & dynamic combat music,
│                             # thruster modulation, voice limiter, persistence
└── ui/
    ├── help_menu.py          # 6-tab tactical manual overlay (Weapons, Abilities, Radar, Controls, Waves, Helldivers)
    └── settings_menu.py      # Tabbed settings interface (Audio, Gameplay/HUD, Flight Controls)

tools/
└── generate_audio_assets.py  # Standalone procedural audio waveform generator (44.1kHz stereo PCM)

tests/                        # Automated headless pytest suite (25 unit and integration tests)
├── conftest.py               # Headless Pygame fixture & dummy rendering surface
├── test_ground_support.py    # Helldivers, ground units, CAS delivery, and supply drops
├── test_health_and_damage.py # Health, shield absorption, and invulnerability mechanics
├── test_math_and_physics.py  # Flight physics, camera clamping, and predictive reticle lead
├── test_persistence.py       # High score file I/O and audio settings fallback
├── test_powerups.py          # Power-up drops, pity system, drone companions, and abilities
├── test_ui_and_menus.py      # Help and settings menu navigation and rendering
└── test_weapons_and_cooldowns.py # Primary cannons, homing rockets, and stratagems
```

Root-level launcher scripts (`run_game.py`, `main.py`) and legacy wrappers (`ground_support.py`, `powerup_system.py`, `audio_manager.py`, `help_menu.py`, `settings_menu.py`, `generate_audio_assets.py`) provide backward compatibility delegating directly to the modular package.



## Folder Structure Overview

```text
.
├── .github/
│   ├── workflows/
│   │   ├── build-exe.yml
│   │   └── ci.yml
│   ├── ISSUE_TEMPLATE/
│   │   ├── bug_report.yml
│   │   └── feature_request.yml
│   └── PULL_REQUEST_TEMPLATE.md
├── audio/
│   ├── music/
│   └── sfx/
├── data/
│   ├── audio_settings.json
│   └── highscore.txt
├── images/
│   ├── Documentation images/
│   │   ├── game.png
│   │   └── main_menu.png
│   ├── 20260820_085135933_iOS.webp
│   ├── LargeExplosionA_spritesheet.png
│   ├── Space-Invaders-Ship.png
│   ├── a10.png
│   ├── backround.png
│   ├── bullet.png
│   ├── bullet_ui.png
│   ├── enemy1.png
│   ├── enemy_bullet.png
│   ├── health.png
│   ├── light_enemy_explosion.png
│   └── newbackround.png
├── src/
│   └── eagle1/
│       ├── app/
│       │   └── game.py
│       ├── systems/
│       │   ├── audio_manager.py
│       │   ├── ground_support.py
│       │   └── powerups.py
│       ├── ui/
│       │   ├── help_menu.py
│       │   └── settings_menu.py
│       ├── effects.py
│       ├── paths.py
│       └── __main__.py
├── tests/
│   ├── conftest.py
│   ├── test_ground_support.py
│   ├── test_health_and_damage.py
│   ├── test_math_and_physics.py
│   ├── test_persistence.py
│   ├── test_powerups.py
│   ├── test_ui_and_menus.py
│   └── test_weapons_and_cooldowns.py
├── tools/
│   └── generate_audio_assets.py
├── .gitignore
├── LICENSE
├── README.md
├── contributing.md
├── pyproject.toml
├── requirements.txt
├── requirements-dev.txt
├── run_game.py
├── main.py
├── ground_support.py
├── powerup_system.py
├── audio_manager.py
├── help_menu.py
├── settings_menu.py
└── generate_audio_assets.py
```


## Asset Organization

### Images (`images/`)

| Asset Filename | Dimensions | Runtime Role |
| :--- | :--- | :--- |
| `Space-Invaders-Ship.png` | 48×61 px | Player starship sprite. Scaled and rotated dynamically during gameplay. |
| `enemy1.png` | 50×46 px | `Light_Enemy` fighter sprite. |
| `bullet.png` | 9×12 px | Player cannon projectile sprite. |
| `enemy_bullet.png` | 9×12 px | Hostile enemy projectile sprite. |
| `LargeExplosionA_spritesheet.png` | 23 columns | Spritesheet for 23-frame animated explosions, scaled 2× upon enemy defeat. |
| `light_enemy_explosion.png` | 50×46 px | Static explosion graphic asset (loaded in initialization). |
| `newbackround.png` | 1280×720 px | In-game starfield background texture, tiled across the 3000×3000 world. |
| `backround.png` | 1280×720 px | Alternate / legacy background image. |
| `20260820_085135933_iOS.webp` | 1280×720 px | Background graphic for the main menu screen. |
| `health.png` | 16×4 px | UI segment icon for player hull health indicator. |
| `bullet_ui.png` | 4×6 px | UI icon representing available ammunition in the HUD counter. |
| `a10.png` | Variable | Unused aircraft sprite asset present in image directory. |



## Configuration Explanation

### General Gameplay & Combat Constants (`src/eagle1/app/game.py`)


| Constant | Value | Description |
| :--- | :--- | :--- |
| `GAME_WIDTH`, `GAME_HEIGHT` | `1280`, `720` | Internal rendering canvas dimensions (pixels). |
| `MAP_WIDTH`, `MAP_HEIGHT` | `3000`, `3000` | Total world map dimensions (pixels). |
| `PLAYER_MAX_HEALTH` | `5` | Maximum player hull integrity points. |
| `PLAYER_MAX_SHIELD` | `20` | Base player energy shield capacity. |
| `PLAYER_MIN_SPEED`, `_MAX_SPEED` | `2.0`, `7.0` | Base minimum and maximum player flight velocities. |
| `PLAYER_ACCELERATION` | `0.15` | Acceleration / deceleration rate per frame. |
| `PLAYER_TURN_RATE` | `3.0` | Degrees of rotational turning applied per frame. |
| `PLAYER_BULLET_DAMAGE` | `1` | Base damage per player cannon projectile hit. |
| `PLAYER_MAX_BULLETS` | `200` | Cannon magazine capacity (50 quad volleys). |
| `PLAYER_RELOAD_TIME` | `5000` | Standard cannon reload duration in milliseconds (5.0s). |
| `ROCKET_VELOCITY` | `7.0` | Secondary homing rocket travel speed. |
| `ROCKET_TURN_RATE` | `2.0` | Degrees per frame steering rate for homing rockets. |
| `ROCKET_DAMAGE` | `4` | Kinetic explosion damage dealt per rocket hit. |
| `ROCKET_MAX_RANGE` | `1200` | Maximum tracking distance for homing rockets (pixels). |
| `PLAYER_MAX_ROCKETS` | `4` | Maximum rocket capacity. |
| `PLAYER_ROCKET_RELOAD_TIME` | `25000` | Rocket reload duration in milliseconds (25.0s). |
| `RADAR_CONE_ANGLE` | `50` | Total search arc in degrees for `CONE` radar mode. |
| `RADAR_CONE_RANGE` | `1050` | Maximum range for `CONE` radar mode (pixels). |
| `RADAR_OMNI_RANGE` | `420` | Maximum search radius for `OMNI` radar mode (pixels). |
| `BORDER_TICK_DAMAGE` | `0.1` | Damage dealt per tick when flying outside map perimeter. |

### Ground Support & Stratagem Constants (`src/eagle1/systems/ground_support.py`)

| Constant | Value | Description |
| :--- | :--- | :--- |
| `HELLDIVER_COUNT` | `4` | Number of allied squad members in fireteam Viper. |
| `HELLDIVER_MAX_HEALTH` | `100.0` | Health points per Helldiver unit. |
| `HELLDIVER_ENGAGE_RADIUS` | `420.0` | Proximity range for Helldiver anti-air cover fire. |
| `ENEMY_TROOPER_MAX_HEALTH` | `35.0` | Health points for Automaton Trooper ground unit. |
| `ENEMY_WALKER_MAX_HEALTH` | `120.0` | Health points for Automaton Armored Walker ground unit. |
| `ENEMY_FABRICATOR_MAX_HEALTH` | `220.0` | Health points for Automaton Fabricator foundry structure. |
| `SCORE_CAS_KILL_BONUS` | `100` | Score bonus for destroying hostiles threatening allied troops. |
| `SCORE_MISSION_DELIVERY_BONUS`| `500` | Score bonus for delivering requested CAS strike to call-in beacon. |
| `SCORE_SURVIVOR_WAVE_BONUS` | `500` | Score bonus per surviving Helldiver at wave clear. |
| `SCORE_FLAWLESS_MULTIPLIER` | `1.5` | Multiplier if all 4 Helldivers survive without casualties. |
| `SCORE_EXTRACTION_BONUS` | `2500` | Score bonus for successfully evacuating squad on Pelican-1. |
| `SCORE_CASUALTY_PENALTY` | `250` | Score penalty when an allied Helldiver is killed. |



## Troubleshooting

### 1. `ModuleNotFoundError: No module named 'pygame'`
- **Cause:** Pygame or pygame-ce is not installed in your active Python environment.
- **Solution:** Run `pip install -r requirements.txt` (or `pip install pygame-ce`).

### 2. Assets Not Found / `pygame.error: Couldn't open images/...`
- **Cause:** Script launched from an external working directory without package installation.
- **Solution:** Launch from the repository root:
  ```bash
  cd Eagle-1-64Bit
  python run_game.py
  # Alternatively: python -m eagle1
  ```

### 3. Highscore Does Not Save
- **Cause:** Missing write permissions in the `data/` directory.
- **Solution:** Verify the user account has write permissions to `data/highscore.txt`.



## License & Credits

- **License:** Licensed under the [MIT License](LICENSE).
- **Author:** paulp143
