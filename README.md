# Eagle-1-64Bit

A 2D top-down space combat arcade game built in Python using Pygame. The game features an expansive 3000×3000 scrolling arena, inertia-driven flight mechanics with full 360-degree rotational steering, quad-cannon salvos, secondary homing rockets with dual-mode radar lock-on, a dynamic 8-ability power-up system with pity mechanics and milestone airdrops, rechargeable energy shields, animated explosions, radar minimap tracking, and persistent local highscores.

---

## Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [Power-Up System](#power-up-system)
- [Homing Rockets & Radar System](#homing-rockets--radar-system)
- [Gameplay Description](#gameplay-description)
- [Controls](#controls)
- [Requirements](#requirements)
- [Dependencies](#dependencies)
- [Installation Instructions](#installation-instructions)
- [Development Setup](#development-setup)
- [Build Instructions](#build-instructions)
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

**Eagle-1-64Bit** is an arcade space dogfighting game where players pilot a combat spacecraft across an expansive 3000×3000 pixel starfield. The game is engineered around a 60 FPS update loop rendered to an internal fixed-resolution canvas of 1280×720 pixels, which is dynamically scaled to fit resizable application windows.

A custom 2D camera tracks the player ship across the map, clamping to world borders and rendering seamless starfield background tiles. Combat combines primary quad-cannon salvos with secondary steerable homing rockets guided by switchable radar targeting (`CONE` and `OMNI` modes). Players battle descending hostile fighters (`Light_Enemy`), collect tactical power-up drops with rarity tiers and magnetic draw, trigger milestone supply drops, and manage shield/hull integrity to build an all-time highscore stored locally on disk.

---

## Key Features

- **Large Continuous World Arena:** 3000×3000 pixel world with seamless background tiling and camera viewport clamping.
- **Out-of-Bounds Hazard Zone:** World boundaries are highlighted with a 4-pixel red border. Flying beyond boundary coordinates (0 to 3000 on either axis) inflicts continuous boundary damage (0.1 per tick), eroding shields and health.
- **Inertia & Momentum Flight Dynamics:** Ships maintain continuous forward movement in their heading direction. Players can adjust velocity smoothly between minimum (2.0) and maximum (7.0, boostable to 11.0) speeds with acceleration/deceleration controls and 360-degree rotational steering (3° per frame).
- **Quad-Cannon Primary Fire:** Each primary attack unloads 4 bullets simultaneously from distinct wing-mounted offsets, rotated dynamically to match the ship's current heading.
- **Secondary Homing Rockets:** Players can launch steerable homing missiles that lock onto enemy targets within radar coverage, featuring smooth turning curves, exhaust trails, and 4.0 explosive damage.
- **Dual Radar Lock-On Modes:** Switch between directional long-range forward cone radar (`CONE`) and 360-degree close-range perimeter radar (`OMNI`), complete with on-screen lock-on reticles and real-time minimap radar coverage visualization.
- **Modular Power-Up Subsystem:** 8 distinct abilities across Common, Rare, and Epic tiers, featuring drop chances with bad-luck pity protection, magnetic proximity pull, floating glow animations, and timer countdown bars.
- **Guaranteed Score Milestone Airdrops:** Reaching 1k, 5k, 10k, 25k, and 50k points automatically summons guaranteed tactical supply crates with on-screen alert banners.
- **Dual Defense System (Shield + Health):** 20-point energy shield capacity that absorbs incoming damage before health is impacted. Shields passively regenerate 1 point every 2000 ms. Taking damage triggers a 1000 ms invulnerability grace period.
- **Tactical Ramming / Kamikaze Damage:** Direct physical collisions with enemy ships deal 4 attack damage to the enemy while inflicting 5 explosion damage on the player ship.
- **Autonomous Enemy Aircraft:** Hostile `Light_Enemy` units spawn at randomized top coordinates, descend vertically, fire projectiles every 1200 ms, and respawn at the top if destroyed or upon reaching the bottom boundary.
- **Score Penalties & Incentives:** Players earn +1 point per second of active survival and +5 points per enemy kill. If an enemy slips past the bottom boundary into the void, a -5 point penalty is deducted.
- **Animated Explosions:** Spritesheet-driven 23-frame explosion animations loaded dynamically and scaled during enemy destruction.
- **Interactive UI System:** Interactive buttons with mouse hover highlights and click handling on the Main Menu, Pause Menu, and Game Over screens, with automatic coordinate scaling for resizable windows.
- **Comprehensive HUD & Radar Minimap:**
  - 160×160 radar minimap rendering world starfield, active camera viewport boundaries, active radar cone/circle coverage, player position (green indicator), enemy position (red indicator), and power-up drops (color-coded by rarity).
  - Real-time speedometer gauge displaying current speed and a proportional progress bar.
  - Hull integrity segment display, remaining primary ammo counter, and secondary rocket ammo counter with reload gauge.
  - Centered shield gauge displaying remaining energy shield percentage (including temporary overcharge).
  - Active power-up buff timers and duration cooldown bars.
  - Current score and persistent highscore overlay.
- **Highscore Persistence & Reset:** Highscores automatically persist to `data/highscore.txt` upon death or game termination. Highscores can be cleared directly from the main menu via a key combination.
- **Flexible Display Scaling:** Window is resizable; the 1280×720 internal rendering canvas is automatically scaled to match any window aspect ratio or dimension.

---

## Power-Up System

The game incorporates a dedicated power-up subsystem (`powerup_system.py`) providing 8 unique abilities divided into three rarity tiers.

### Abilities Table

| Ability | Symbol | Category | Rarity | Duration | Effect |
| :--- | :---: | :--- | :--- | :---: | :--- |
| **Rapid Fire** | `RF` | Offensive | **Common** | 10.0s | Cannon fire delay halved (100ms $\rightarrow$ 50ms); reload delay reduced by 40% (5000ms $\rightarrow$ 3000ms). |
| **Shield Bubble** | `SB` | Defensive | **Common** | 10.0s | Grants +15 temporary overcharge shield (up to 35 total) and doubles shield passive regeneration rate. |
| **Thruster Overdrive** | `TO` | Utility | **Common** | 10.0s | Boosts max speed to 11.0 (+57%), acceleration to 0.25 (+66%), and turning rate to 4.5°/frame (+50%). |
| **Chrono Slip** | `CS` | Utility | **Rare** | 8.0s | Time dilation: enemy flight speed and enemy projectile speed are slowed by 50%. |
| **Cryo Frostbite** | `CF` | Offensive / Utility | **Rare** | 10.0s | Rounds chill the enemy, slowing speed by 60%. Landing 3 hits freezes the enemy solid (0 speed, weapons disabled) for 1.5s with an ice crystal visual. |
| **Damage Multiplier** | `DM` | Offensive | **Rare** | 10.0s | Doubles primary cannon bullet damage from 1 to 2 (+100% damage) with a golden projectile aura. |
| **Vanguard Drone** | `VD` | Defensive / Offensive | **Epic** | 20.0s | Deploys an autonomous escort drone orbiting Eagle-1 at an 80px radius that intercepts incoming enemy bullets and fires auto-targeting pulse lasers. |
| **Swarm Homing Pods**| `HP` | Offensive | **Epic** | 12.0s | Automatically launches self-guided micro-missiles (2 per second) tracking enemy craft and dealing 2.0 damage per missile with exhaust trails. |

### Drop & Spawn Mechanics
- **Enemy Kill Drops:** Defeating an enemy has a base drop chance of **8%** (`POWERUP_DROP_BASE_CHANCE = 0.08`).
- **Pity Counter:** Every kill without a drop adds **+3%** to the drop chance (`POWERUP_PITY_INCREMENT = 0.03`). Upon any successful drop, the pity counter resets to 0.
- **Rarity Weights:** Common drops occur 70% of the time, Rare drops 20%, and Epic drops 10%.
- **Drop Entity Lifecycle:** Drops float in space with bobbing animations, a pulsing glow ring, and rarity color indicators. Drops persist for 12 seconds (`POWERUP_LIFETIME_SECONDS = 12.0`), blinking rapidly in their final 3 seconds before despawning.
- **Magnetic Draw:** When the player flies within 130 pixels (`POWERUP_MAGNET_RADIUS = 130.0`), the drop is magnetically attracted and pulled toward the ship.
- **Score Milestones:** Crossing score thresholds at **1,000**, **5,000**, **10,000**, **25,000**, and **50,000** points triggers a guaranteed tactical airdrop directly in the player's vicinity, accompanied by an on-screen HUD banner.

---

## Homing Rockets & Radar System

### Secondary Homing Rockets (`Player.Rocket`)
- **Capacity & Reload:** Carries up to 4 rockets (`PLAYER_MAX_ROCKETS = 4`). Reloads automatically over 25 seconds (`PLAYER_ROCKET_RELOAD_TIME = 25000`) when depleted.
- **Fire Controls:** Triggered using **Right Mouse Button**, `E`, `F`, or `Left Control` (`LCTRL`).
- **Flight Dynamics:** Rockets travel at velocity 7.0 with realistic smooth turning physics (`turn_rate = 2.0`), maximum flight time of 2.5 seconds (1200px range), and explosive kinetic impact dealing 4.0 damage.

### Dual Radar Modes (Toggle with `Q`)
- **`CONE` Mode (Long-Range Intercept):**
  - Directional forward-facing search arc of $\pm 25^\circ$ (50° total angle) extending from 300px up to 1050px.
  - Ideal for locking onto distant targets ahead of the flight path.
- **`OMNI` Mode (Close-Quarter Defense):**
  - Full $360^\circ$ circular perimeter scan up to 420px around the ship.
  - Ideal for dogfighting when circling or evading enemies at close range.
- **HUD Reticle & Minimap Visualization:**
  - An animated target reticle (`CONE LOCK` / `OMNI LOCK`) appears over hostile targets within radar coverage.
  - The radar cone or circle is dynamically projected and rendered on the 160×160 minimap.

---

## Gameplay Description

### Objectives
1. **Survive:** Pilot your ship across the 3000×3000 arena while staying within the boundary perimeter. Every second survived adds +1 to your score.
2. **Eliminate Threats:** Intercept descending `Light_Enemy` fighters with quad cannons and homing rockets (+5 score per destruction).
3. **Collect Power-Ups:** Collect floating tactical crates to gain temporary offensive, defensive, and mobility enhancements.
4. **Prevent Breaches:** Do not let enemy fighters pass the bottom map boundary, or a -5 score penalty will be assessed.
5. **Surpass Highscores:** Beat your personal best, saved automatically to disk.

### Combat & Flight Mechanics
- **Continuous Velocity:** The ship is always in motion along its facing angle. You cannot come to a complete standstill; throttle keys adjust velocity between 2.0 and 7.0 (or up to 11.0 with Thruster Overdrive).
- **Quad Salvos:** Pressing Space fires 4 bullets simultaneously from 4 wing offsets. A 100 ms cooldown (50 ms with Rapid Fire) prevents rapid-fire exploits.
- **Shield Absorption:** Incoming projectile damage (1 damage per enemy bullet) or boundary damage drains shield points first. If damage exceeds remaining shields, residual damage reduces ship health and triggers temporary invincibility (1000 ms).
- **Reload Downtime:** Firing consumes 4 rounds per volley. Once 200 bullets are spent, firing is disabled for 5 seconds (3 seconds with Rapid Fire) while weapons automatically reload.
- **Ramming:** You can intentionally or accidentally ram enemies to deal 4 damage to them, but you will absorb 5 explosion damage in return.

### Game States
```
               [ Launch Application ]
                         │
                         ▼
                 ┌───────────────┐
                 │   Main Menu   │◄────────────────┐
                 │  (Starblast)  │                 │
                 └───────┬───────┘                 │
                         │ Shift / Click           │
                         ▼                         │
                 ┌───────────────┐                 │
                 │     Active    │─── P ──►┌───────────────┐
                 │    Gameplay   │◄── P ───│  Pause Menu   │
                 └───────┬───────┘         └───────┬───────┘
                         │                         │ ESC / Click
                         │ Health <= 0             │
                         ▼                         │
                 ┌───────────────┐                 │
                 │   Game Over   │─────────────────┘
                 │ (Respawn / R) │     Space / Click
                 └───────┬───────┘
                         │
                         │ R / Click
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
| **Toggle Radar Mode (`CONE` / `OMNI`)**| `Q` | — | Active Gameplay |
| **Pause Game** | `P` | — | Active Gameplay |
| **Resume Game** | `P` | Click `CONTINUE` | Pause Menu |
| **Return to Main Menu** | `Escape` (`ESC`) | Click `MAIN MENU` | Pause Menu |
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
     venv\Scripts\activate.bat
     ```
   - **Windows (PowerShell):**
     ```bash
     venv\Scripts\Activate.ps1
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

```
┌─────────────────────────────────────────────────────────────┐
│                          main.py                            │
├──────────────────────────────┬──────────────────────────────┤
│ Configuration Constants      │ Game dimensions, stats, HUD  │
├──────────────────────────────┼──────────────────────────────┤
│ Asset Loader & Path Resolver │ get_base_dir(), load_image() │
├──────────────────────────────┼──────────────────────────────┤
│ Persistence Layer            │ load_highscore, add_highscore│
├──────────────────────────────┼──────────────────────────────┤
│ Interactive UI System        │ TextBox (hover & click)      │
├──────────────────────────────┼──────────────────────────────┤
│ Animation & Sprite Handling  │ Spritesheet, Large_explosion │
├──────────────────────────────┼──────────────────────────────┤
│ Entity Classes               │ Player (with Bullet & Rocket)│
│                              │ Light_Enemy (with Bullet)    │
├──────────────────────────────┼──────────────────────────────┤
│ Radar Targeting Subsystem    │ CONE and OMNI mode checks,   │
│                              │ lock reticle, minimap radar  │
├──────────────────────────────┼──────────────────────────────┤
│ Game Systems                 │ move() (physics, collisions) │
│                              │ respawn() (state resets)     │
│                              │ draw() (camera, tiling, HUD) │
├──────────────────────────────┼──────────────────────────────┤
│ Screen Renderers             │ main_menu(), pause_menu()    │
├──────────────────────────────┼──────────────────────────────┤
│ Main Game Loop               │ Event pump, input polling,   │
│                              │ canvas scaling, clock tick   │
└──────────────────────────────┴──────────────────────────────┘
                               ▲
                               │ imports
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                     powerup_system.py                       │
├──────────────────────────────┬──────────────────────────────┤
│ Configurable Constants       │ Drop rates, pity, durations  │
├──────────────────────────────┼──────────────────────────────┤
│ Rarity & Ability Tables      │ Common, Rare, Epic schemas   │
├──────────────────────────────┼──────────────────────────────┤
│ PowerUpDrop Entity           │ Floating animation, halo,    │
│                              │ magnetic attraction to ship  │
├──────────────────────────────┼──────────────────────────────┤
│ DroneCompanion Entity        │ Orbiting escort, bullet bloc,│
│                              │ auto-targeting pulse lasers  │
├──────────────────────────────┼──────────────────────────────┤
│ HomingMicroMissile Entity    │ Swarm pod self-guided rocket │
├──────────────────────────────┼──────────────────────────────┤
│ PowerUpManager               │ Pity counter, rolls, active  │
│                              │ timers, milestone airdrops,  │
│                              │ HUD timer bars and banners   │
└──────────────────────────────┴──────────────────────────────┘
```

---

## Folder Structure Overview

```
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
├── main.py
└── powerup_system.py
```

### File and Directory Descriptions

| Path | Type | Description |
| :--- | :--- | :--- |
| `main.py` | Python Script | Primary application entry point, game systems, entities, radar logic, and main loop. |
| `powerup_system.py` | Python Script | Dedicated power-up subsystem: drop rolling, pity counter, abilities, drones, and milestone alerts. |
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
| `data/highscore.txt` | Plain Text | Contains a single integer representing the all-time highscore. Read at startup and written upon highscore defeat or exit. |
| `data.csv` | CSV Text | Contains header `name,hightscore` and default row `Paul,0`. Not actively loaded by `main.py`. |

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
| `PLAYER_MIN_SPEED`, `_MAX_SPEED`| `2.0`, `7.0` | Base minimum and maximum player flight velocities. |
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
| `RADAR_CONE_ANGLE` | `50` | Total search arc in degrees for `CONE` radar mode ($\pm 25^\circ$). |
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
| `SCORE_MILESTONE_THRESHOLDS`| `[1000, 5000, 10000, 25000, 50000]` | Score thresholds triggering guaranteed supply airdrops. |
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
- **Cause:** `canvas` uses a fixed 16:9 base aspect ratio (1280×720) and scales directly to the window's dimensions via `pygame.transform.scale(canvas, window.get_size())`.
- **Solution:** Maintain a 16:9 window aspect ratio when resizing, or run at the native resolution of 1280×720.

### 4. Highscore Does Not Save
- **Cause:** Insufficient write permissions in the `data/` directory.
- **Solution:** Ensure the executing user account has write permissions to the repository directory. `main.py` automatically attempts to create the directory using `os.makedirs(os.path.dirname(filepath), exist_ok=True)`.

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
