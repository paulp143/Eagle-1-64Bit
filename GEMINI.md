# Antigravity Agent Guidelines — Eagle-1-64Bit

## Project Overview

**Eagle-1-64Bit** is a 2D top-down arcade space combat and close-air-support game developed in Python using **Pygame** (`pygame` / `pygame-ce`). The player pilots the combat spacecraft *Eagle-1* across a 3000×3000 scrolling battlefield, dogfighting aerial Automaton forces while providing Close Air Support (CAS) to an allied ground squad of Helldivers against hostile Automaton ground troops, fabricators, and heavy boss fortresses.

---

## Codebase Architecture & File Roles

```text
Eagle-1-64Bit/
├── main.py                   # Game loop (60 FPS), camera, player aircraft, aerial combat,
│                             # wave management, state machine, rendering pipeline, HUD.
├── ground_support.py         # Helldivers (Viper 1-4), Automaton ground units, fabricators,
│                             # Factory Strider boss, stratagem air strikes, CAS beacon requests,
│                             # supply drops, predictive reticle, weapon selection menu.
├── powerup_system.py         # 8 abilities across 3 rarities, drop mechanics with pity counter,
│                             # magnetics, escort drones, swarm homing micro-missiles.
├── audio_manager.py          # Centralized 16-channel mixer, procedural SFX & dynamic combat music,
│                             # thruster modulation, voice limiter, persistence.
├── generate_audio_assets.py  # Standalone procedural audio waveform generator (44.1kHz stereo PCM).
├── help_menu.py              # 6-tab in-game tactical manual overlay (Weapons, Abilities,
│                             # Radar, Controls, Wave Combat, Helldivers).
├── settings_menu.py          # Tabbed settings interface (Audio, Gameplay/HUD, Flight Controls).
├── data/
│   ├── audio_settings.json   # Persistent volume & mute configuration.
│   └── highscore.txt         # Persistent high score tracker (do not corrupt with test runs).
├── images/                   # Sprites, spritesheets, backgrounds, and documentation screenshots.
└── audio/                    # Synthesized and custom WAV audio assets (music/ and sfx/).
```

---

## Coordinate Systems & Camera Transforms

Always keep coordinate spaces strictly separated:

1. **World Space (`0 .. 3000`, `0 .. 3000`)**:
   - `MAP_WIDTH = 3000`, `MAP_HEIGHT = 3000`.
   - All gameplay entities (Player, Enemies, Helldivers, Fabricators, Projectiles, Drops) exist and calculate collisions in world coordinates.
2. **Camera Viewport Clamping**:
   - `camera_x = clamp(player.x - GAME_WIDTH / 2, 0, MAP_WIDTH - GAME_WIDTH)`
   - `camera_y = clamp(player.y - GAME_HEIGHT / 2, 0, MAP_HEIGHT - GAME_HEIGHT)`
3. **Screen / Render Space (`0 .. 1280`, `0 .. 720`)**:
   - `screen_x = world_x - camera_x`, `screen_y = world_y - camera_y`.
   - UI elements, HUD overlays, crosshairs, and menus draw directly in screen space.

---

## Core Gameplay Systems & Conventions

### 1. Flight Dynamics & Health Model
- **Continuous Inertia**: The ship maintains constant forward movement (`PLAYER_MIN_SPEED = 2.0` to `PLAYER_MAX_SPEED = 7.0`) along its facing angle. Throttle (`W`/`S`) adjusts speed; steering (`A`/`D`) adjusts heading angle.
- **Shields-First Damage**: Incoming damage is absorbed by `player.shield` (`PLAYER_MAX_SHIELD = 20`) before depleting `player.health` (`PLAYER_MAX_HEALTH = 5`).
- **Invulnerability**: Post-hit invincibility frames (`PLAYER_INVINCIBLE_TIME = 1000` ms) prevent instant death from overlapping hits.
- **Hazard Perimeter**: Flying outside the 3000×3000 boundary inflicts periodic tick damage (`BORDER_TICK_DAMAGE = 0.1`).

### 2. Weapons & Fire Control
- **Quad-Cannons (`Spacebar`)**: 4 wing-offset projectiles per volley. Consumes ammo from `PLAYER_MAX_BULLETS = 200` with periodic reloads (`PLAYER_RELOAD_TIME = 5000` ms).
- **Homing Rockets (`Right Click` / `E` / `F` / `LCTRL`)**: Capacity of 4 missiles. Locks onto aerial or ground targets within radar coverage, navigating with turning physics.
- **Radar Modes (`Q`)**:
  - `CONE`: Forward intercept arc (50° angle, 300–1050 px).
  - `OMNI`: 360° close-quarters perimeter scan (0–420 px).
- **Predictive Aiming Reticle**:
  - Gun convergence pip at 180 px forward along flight vector.
  - Predictive bomb impact zone dynamically computed ahead: $\text{lead} = 320.0 + v \times 8.0$.
  - Rings turn red with pulsing crosshairs when hovering over hostile targets or CAS beacons.

### 3. Stratagems & Ground Support
- **8 Stratagems** (quick-select keys `1`–`8`, menu `V`/`TAB`, deploy `C`):
  1. Machine Gun Dive (12s)
  2. Eagle 500kg Bomb (35s)
  3. Cluster Bomb (18s)
  4. Napalm Strike (22s)
  5. Gas Strike (18s)
  6. Rocket Pods (20s)
  7. EMS Stun Strike (24s)
  8. Smoke Screen (22s)
- **Allied Helldivers (Viper 1-4)**: Squad members (Lead, Heavy, Scout, Medic) fight ground hostiles, provide upward anti-air fire, path to supply pods when hurt, and board Pelican-1 during extraction.
- **CAS Call-In Requests**: Helldiver distress beacons trigger CAS delivery missions; dropping the designated stratagem grants `+500 PTS`.
- **Supply Drops (`X`)**: 30s cooldown. Landed pods heal/re-shield Helldivers and fully replenish Eagle-1 on flyover.
- **Hostile Ground Units**: Automaton Troopers (35 HP), Heavy Walkers (120 HP), and Fabricators (220 HP, spawns troops every 8s).

### 4. Mission Flow & States
- State machine managed in `main.py`: `"menu"`, `"mission_select"`, `"play"`, `"pause"`, `"game_over"`.
- 5 operational modes: *Air Superiority*, *Orbital Base Defense*, *Factory Strider Boss Raid*, *Outpost Demolition*, and *Endless War*.
- Always ensure `respawn()` properly resets wave timers, mission goals, entity lists, and HUD state.

---

## Engineering Guidelines for Modifications

1. **Targeted, Incremental Changes**:
   - `main.py` is large (~2,700 lines). Do not rewrite or restructure entire sections when making localized fixes or features.
   - Prefer extending modular managers (`GroundSupportManager`, `PowerUpManager`, `AudioManager`, `SettingsMenu`, `HelpMenu`) rather than appending ad-hoc logic into `main.py`.
2. **Path Resolution & Portability**:
   - Never hardcode absolute file paths (e.g. `C:\Users\...`).
   - Use `PROJECT_ROOT` / `BASE_DIR` with `os.path.join(...)` for assets and configs.
3. **Performance & 60 FPS Frame Budget**:
   - Do not perform file I/O, heavy surface allocations, or font re-creations inside the render/update loop.
   - Cache fonts and pre-render text or transparent surfaces where applicable.
4. **Entity Safety**:
   - Always guard against empty collections, dead entities, or `None` targets before dereferencing properties.
   - Cleanly remove dead/expired entities from tracking lists (`[e for e in enemies if e.is_alive]`).
5. **Preserve User Data**:
   - Never overwrite or reset `data/highscore.txt` with dummy test scores.
   - Ensure `data/audio_settings.json` handles missing keys gracefully with fallback defaults.

---

## Testing & Verification Workflow

### 1. Python Syntax & Import Validation
Verify syntax and imports across all modules:
```bash
python -c "import main, ground_support, powerup_system, audio_manager, generate_audio_assets, help_menu, settings_menu; print('All modules loaded successfully')"
```

### 2. Headless Execution
When running automated scripts or test checks in environments without a physical display or audio hardware, configure headless dummy drivers before initializing Pygame:
```python
import os
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
import pygame
pygame.init()
```

### 3. Audio Asset Generation
If audio assets are missing or modified:
```bash
python generate_audio_assets.py
```

### 4. Manual Gameplay Verification
Whenever making user-visible gameplay, UI, control, or physics changes:
```bash
python main.py
```
Verify:
- Clean launch to Main Menu.
- Mission selection and gameplay loop start.
- Pause menu (`P`), Settings (`O`), and Help manual (`H`).
- Weapon firing, collision detection, and score updates.
- Game over and respawn (`R`).

---

## Documentation Synchronization
- If controls, weapon statistics, stratagems, or operational modes are added or changed, update `README.md` and the relevant tab in `help_menu.py`.
- If development, installation, or test workflows change, update `contributing.md`.
