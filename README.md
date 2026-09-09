# Eagle-1-64Bit

A 2D top-down space combat arcade game built in Python using Pygame. The game features an expansive 3000×3000 scrolling arena, inertia-driven flight mechanics, quad-cannon combat, homing rockets, radar lock-on modes, a power-up system, and a fully interactive in-game help menu.

---

## Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [Power-Up System](#power-up-system)
- [Homing Rockets & Radar System](#homing-rockets--radar-system)
- [Help Menu](#help-menu)
- [Gameplay Description](#gameplay-description)
- [Controls](#controls)
- [Requirements](#requirements)
- [Dependencies](#dependencies)
- [Installation Instructions](#installation-instructions)
- [Development Setup](#development-setup)
- [Run Instructions](#run-instructions)
- [Usage Examples](#usage-examples)
- [Project Architecture Overview](#project-architecture-overview)
- [Folder Structure Overview](#folder-structure-overview)
- [Asset Organization](#asset-organization)
- [Configuration Explanation](#configuration-explanation)
- [Troubleshooting](#troubleshooting)
- [Contributing Guidelines](#contributing-guidelines)
- [License](#license)
- [Credits](#credits)

---

## Overview

**Eagle-1-64Bit** is an arcade space dogfighting game where players pilot a combat spacecraft across an expansive 3000×3000 pixel starfield. The game is engineered around a 60 FPS update loop and includes dynamic enemy spawns, power-ups, radar targeting, and persistent highscore tracking.

A custom 2D camera tracks the player ship across the map, clamping to world borders and rendering seamless starfield background tiles. Combat combines primary quad-cannon salvos with secondary steerable homing rockets, while the HUD provides radar, speed, health, shield, ammo, and score readouts.

---

## Key Features

- **Large Continuous World Arena:** 3000×3000 pixel world with seamless background tiling and camera viewport clamping.
- **Out-of-Bounds Hazard Zone:** World boundaries are highlighted with a 4-pixel red border. Flying beyond boundary coordinates inflicts continuous boundary damage.
- **Inertia & Momentum Flight Dynamics:** Ships maintain continuous forward movement in their heading direction.
- **Quad-Cannon Primary Fire:** Each primary attack unloads 4 bullets simultaneously from distinct wing-mounted offsets.
- **Secondary Homing Rockets:** Players can launch steerable homing missiles that lock onto enemy targets within radar coverage.
- **Dual Radar Lock-On Modes:** Switch between directional forward cone radar (`CONE`) and 360-degree close-range perimeter radar (`OMNI`).
- **Modular Power-Up Subsystem:** 8 distinct abilities across Common, Rare, and Epic tiers, featuring drop chances with pity protection.
- **Guaranteed Score Milestone Airdrops:** Reaching major score milestones automatically summons guaranteed supply crates.
- **Dual Defense System (Shield + Health):** Energy shields absorb incoming damage before health is impacted.
- **Tactical Ramming / Kamikaze Damage:** Direct physical collisions with enemy ships deal damage to both sides.
- **Autonomous Enemy Aircraft:** Hostile `Light_Enemy` units spawn at randomized top coordinates and descend vertically.
- **Interactive UI System:** Buttons with hover highlights and click handling on menu screens.
- **Comprehensive HUD & Radar Minimap:** Radar display, speedometer, hull integrity, ammo counters, shield gauge, power-up timers, and score.
- **Highscore Persistence & Reset:** Highscores persist to disk and can be reset from the main menu.
- **Flexible Display Scaling:** Window is resizable and automatically scaled to the active window size.
- **In-Game Help Menu:** A new multi-tab help overlay provides weapons, abilities, radar, and controls guidance.

---

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
- **Score Milestones:** Score thresholds trigger guaranteed supply airdrops.

---

## Homing Rockets & Radar System

### Secondary Homing Rockets (`Player.Rocket`)

- **Capacity & Reload:** Carries up to 4 rockets and reloads automatically when depleted.
- **Fire Controls:** Triggered using **Right Mouse Button**, `E`, `F`, or `Left Control`.
- **Flight Dynamics:** Rockets travel with smooth turning physics and explode on impact.

### Dual Radar Modes (Toggle with `Q`)

- **`CONE` Mode (Long-Range Intercept):**
  - Forward-facing search arc for distant targets.
  - Best for head-on approaches and long-distance strikes.
- **`OMNI` Mode (Close-Quarter Defense):**
  - Full 360-degree circular scan around the ship.
  - Best for dogfighting and close-range evasion.
- **HUD Reticle & Minimap Visualization:**
  - Target reticles appear over hostile targets within radar coverage.
  - Radar cone or circle is displayed on the minimap.

---

## Help Menu

The game now includes an interactive in-game help menu with multiple tabs:

- **Weapons & Combat** — weapon damage, ranges, cooldowns, reloads, and rocket details.
- **Abilities & Buffs** — all power-ups and passive effects.
- **Radar Modes (Q)** — visual explanation of `CONE` vs `OMNI` targeting.
- **Controls Manual** — full flight, combat, and navigation reference.

### Help Menu Access

- Press **`H`** to open the help menu.
- The help overlay is accessible from the **Main Menu**, **Pause Menu**, and **Respawn/Game Over** contexts.
- Use the on-screen tabs or keyboard navigation to switch sections.
- Press **`ESC`** to close the help menu.

### Help Menu Tabs

| Tab | Description |
| :--- | :--- |
| **1. Weapons & Combat** | Shows damage, range, velocity, cooldown, and capacity information for core weapon systems. |
| **2. Abilities & Buffs** | Lists all tactical power-ups across Common, Rare, and Epic tiers. |
| **3. Radar Modes (Q)** | Explains the two radar systems and their targeting behavior. |
| **4. Controls Manual** | Provides a full keybinding reference and gameplay control guide. |

---

## Gameplay Description

### Objectives

1. **Survive:** Pilot your ship across the arena while staying within the boundary perimeter.
2. **Eliminate Threats:** Intercept descending `Light_Enemy` fighters with quad cannons and homing rockets.
3. **Collect Power-Ups:** Collect floating tactical crates to gain temporary enhancements.
4. **Prevent Breaches:** Do not let enemy fighters pass the bottom map boundary.
5. **Surpass Highscores:** Beat your personal best, saved automatically to disk.

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

---

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
| **Toggle Radar Mode (`CONE` / `OMNI`)** | `Q` | — | Active Gameplay |
| **Open Help Menu** | `H` | — | Main Menu / Pause Menu / Game Over |
| **Pause Game** | `P` | — | Active Gameplay |
| **Resume Game** | `P` | Click `CONTINUE` | Pause Menu |
| **Return to Main Menu** | `Escape` (`ESC`) | Click `MAIN MENU` | Pause Menu |
| **Close Help Menu** | `Escape` (`ESC`) | Click `X` / close button | Help Menu |
| **Respawn** | `R` | Click `RESPAWN` | Game Over (`Health <= 0`) |
| **Return to Main Menu** | `Spacebar` | Click `MAIN MENU` | Game Over (`Health <= 0`) |
| **Quit Game** | Window Close Button (`QUIT`) | — | All States |

---

## Requirements

- **Python:** Python 3.x (compatible with Python 3.8+)
- **Operating System:** Cross-platform (Windows, macOS, Linux)
- **Display:** Recommended minimum resolution 1280×720 (supports window resizing)

---

## Dependencies

### Third-Party Libraries

- **`pygame`** (or `pygame-ce`): Required for window creation, rendering, event handling, sprite transformations, and timing loops.

### Python Standard Library

- `os`: File path operations and directory creation.
- `sys`: System utilities and path resolution.
- `random`: Randomization of enemy spawn positions, drops, and rarity rolling.
- `math`: Trigonometric calculations for rotation vectors, radar arcs, distances, and missile steering.

> **Note:** The repository does not yet include a `requirements.txt` or `pyproject.toml` file. Dependencies must be installed directly via `pip`.

---

## Installation Instructions

1. Clone the repository:
   ```bash
   git clone https://github.com/paulp143/Eagle-1-64Bit.git
   cd Eagle-1-64Bit
   ```

2. Install the required `pygame` dependency:
   ```bash
   pip install pygame
   ```

---

## Development Setup

To configure an isolated virtual environment for local development:

1. Create a virtual environment:
   ```bash
   python -m venv venv
   ```

2. Activate the virtual environment:
   - **Linux / macOS:**
     ```bash
     source venv/bin/activate
     ```
   - **Windows (Command Prompt):**
     ```bash
     venv\\Scripts\\activate.bat
     ```
   - **Windows (PowerShell):**
     ```bash
     venv\\Scripts\\Activate.ps1
     ```

3. Install project dependencies into the environment:
   ```bash
   pip install pygame
   ```

---

## Run Instructions

Execute `main.py` directly with Python:

```bash
python main.py
```

---

## Usage Examples

### Starting a Standard Game Session

```bash
python main.py
```

1. Press `Shift` or click the `PLAY` button on the main menu.
2. Steer with `A`/`D` and regulate speed with `W`/`S`.
3. Press `Spacebar` for primary quad cannons, and use `Right Click` (or `E`/`F`) to launch homing rockets when locked on.
4. Press `Q` to switch radar modes between long-range `CONE` and close-range `OMNI`.
5. Fly close to floating colored crates to collect power-ups and overcharge your ship.
6. Press `P` at any time to pause the game.
7. If destroyed, press `R` or click `RESPAWN` to immediately restart the round.

### Resetting the Highscore

1. Launch the game to the main menu:
   ```bash
   python main.py
   ```
2. On the title screen, press and hold `Left Shift` + `Right Shift` + `R`.
3. The stored highscore in `data/highscore.txt` will be reset to `0`.

---

## Project Architecture Overview

The codebase is organized into two primary Python modules:

```text
main.py
├── Configuration Constants
├── Asset Loader & Path Resolver
├── Persistence Layer
├── Interactive UI System
├── Animation & Sprite Handling
├── Entity Classes
├── Radar Targeting Subsystem
├── Game Systems
├── Screen Renderers
└── Main Game Loop

powerup_system.py
├── Configurable Constants
├── Rarity & Ability Tables
├── PowerUpDrop Entity
├── DroneCompanion Entity
├── HomingMicroMissile Entity
└── PowerUpManager
```

---

## Folder Structure Overview

```text
.
├── .gitignore
├── LICENSE
├── README.md
├── data/
│   └── highscore.txt
├── data.csv
├── images/
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
├── help_menu.py
├── main.py
└── powerup_system.py
```

### File and Directory Descriptions

| Path | Type | Description |
| :--- | :--- | :--- |
| `main.py` | Python Script | Primary application entry point, game systems, entities, radar logic, and main loop. |
| `powerup_system.py` | Python Script | Dedicated power-up subsystem: drop rolling, pity counter, abilities, drones, and milestone alerts. |
| `help_menu.py` | Python Script | Interactive in-game help overlay with weapons, abilities, radar, and controls tabs. |
| `LICENSE` | Text File | MIT License legal terms and permissions. |
| `data/` | Directory | Data storage directory for runtime persistence. |
| `data/highscore.txt` | Text File | Stores the single highest numerical score achieved. |
| `data.csv` | CSV File | Legacy/placeholder CSV data file (`name,hightscore`). Currently unreferenced by `main.py`. |
| `images/` | Directory | Graphic assets directory containing sprites, backgrounds, spritesheets, and UI icons. |
| `README.md` | Markdown | Project documentation. |
| `.gitignore` | Git Config | Comprehensive ignore rules for Python, IDEs, caches, and build artifacts. |

---

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
| `newbackround.png` | 1280×720 px | In-game starfield background texture, tiled across the 3000×3000 world and scaled for minimap radar. |
| `backround.png` | 1280×720 px | Alternate / legacy background image (retained in asset folder). |
| `20260820_085135933_iOS.webp` | 1280×720 px | Background graphic for the main menu screen. |
| `health.png` | 16×4 px | UI segment icon for player hull health indicator. |
| `bullet_ui.png` | 4×6 px | UI icon representing available ammunition in the HUD counter. |
| `a10.png` | Variable | Unused aircraft sprite asset present in image directory. |

### Data Files (`data/`)

| Asset Filename | Format | Description |
| :--- | :--- | :--- |
| `data/highscore.txt` | Plain Text | Contains a single integer representing the all-time highscore. Read at startup and written upon highscore defeat |

---

## Configuration Explanation

Game tuning parameters and mechanics constants are exposed directly at the top of `main.py` and `powerup_system.py`:

### General Gameplay & Combat Constants (`main.py`)

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
| `BULLET_SHOOTING_TIMER` | `100` | Standard cooldown between cannon volleys (ms). |
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
| `MINIMAP_SIZE` | `160` | Width and height of radar minimap UI (pixels). |

### Power-Up Tuning Constants (`powerup_system.py`)

| Constant | Value | Description |
| :--- | :--- | :--- |
| `POWERUP_DROP_BASE_CHANCE` | `0.08` | Base probability (8%) of dropping a power-up on enemy kill. |
| `POWERUP_PITY_INCREMENT` | `0.03` | Additional drop chance (+3%) added per kill without a drop. |
| `POWERUP_LIFETIME_SECONDS` | `12.0` | Seconds before a dropped item despawns. |
| `POWERUP_MAGNET_RADIUS` | `130.0` | Proximity range (pixels) for magnetic pull toward ship. |
| `RARITY_COMMON_WEIGHT` | `0.70` | Weight for Common rarity drops (70%). |
| `RARITY_RARE_WEIGHT` | `0.20` | Weight for Rare rarity drops (20%). |
| `RARITY_EPIC_WEIGHT` | `0.10` | Weight for Epic rarity drops (10%). |
| `SCORE_MILESTONE_THRESHOLDS` | `[1000, 5000, 10000, 25000, 50000]` | Score thresholds triggering guaranteed supply airdrops. |
| `HOMING_POD_DAMAGE` | `2.0` | Micro-missile damage per rocket from Swarm Homing Pods. |
| `SHIELD_BUBBLE_BONUS` | `15.0` | Temporary shield overcharge added by Shield Bubble. |
| `DAMAGE_BOOST_MULTIPLIER` | `2` | Multiplier applied to cannon damage under Damage Multiplier. |
| `RAPID_FIRE_COOLDOWN_MS` | `50` | Firing cooldown during Rapid Fire (reduced from 100ms). |
| `RAPID_FIRE_RELOAD_MS` | `3000` | Reload duration during Rapid Fire (reduced from 5000ms). |
| `THRUSTER_MAX_SPEED` | `11.0` | Maximum speed under Thruster Overdrive (up from 7.0). |
| `TIME_SLOW_FACTOR` | `0.5` | Movement speed multiplier applied to enemy craft and bullets during Time Slow. |
| `FREEZE_DURATION_SEC` | `1.5` | Duration (seconds) an enemy remains completely frozen after 3 Cryo hits. |

---

## Troubleshooting

### 1. `ModuleNotFoundError: No module named 'pygame'`
- **Cause:** Pygame is not installed in your active Python environment.
- **Solution:** Run:
  ```bash
  pip install pygame
  ```

### 2. Assets Not Found / `pygame.error: Couldn't open images/...`
- **Cause:** `main.py` resolves `BASE_DIR` using `get_base_dir()` checking multiple relative and absolute candidates.
- **Solution:** Ensure you execute the script from the repository root directory:
  ```bash
  cd Eagle-1-64Bit
  python main.py
  ```

### 3. Display Appears Stretched When Resizing
- **Cause:** `canvas` uses a fixed 16:9 base aspect ratio and scales directly to the window's dimensions.
- **Solution:** Maintain a 16:9 window aspect ratio when resizing, or run at the native resolution of 1280×720.

### 4. Highscore Does Not Save
- **Cause:** Insufficient write permissions in the `data/` directory.
- **Solution:** Ensure the executing user account has write permissions to the repository directory.

---

## Contributing Guidelines

Unable to determine from repository contents.

*(No contributing guidelines, issue templates, or pull request guidelines are present in the repository.)*

---

## License

This project is licensed under the terms of the [MIT License](LICENSE). See the [`LICENSE`](LICENSE) file for the full copyright and permission notice.

---

## Credits

- **Repository Author:** paulp143 (inferred from repository ownership and Git commit history).
- **Third-Party Assets & Media:** Unable to determine from repository contents.
