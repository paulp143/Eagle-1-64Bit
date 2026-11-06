# Agent Guidelines — Eagle-1-64Bit

## Project Overview

**Eagle-1-64Bit** is a 2D top-down arcade space combat and close-air-support game developed in Python using **Pygame** (`pygame` / `pygame-ce`). The player pilots the combat spacecraft *Eagle-1* across a 3000×3000 scrolling battlefield, dogfighting aerial Automaton forces while providing Close Air Support (CAS) to an allied ground squad of Helldivers against hostile Automaton ground troops, fabricators, and heavy boss fortresses.

---

## Codebase Architecture & File Roles

```text
Eagle-1-64Bit/
├── run_game.py               # Repository-root launcher (also: `python -m eagle1`).
├── main.py, ground_support.py, help_menu.py, settings_menu.py,
│   powerup_system.py, audio_manager.py, academy_briefing.py,
│   generate_audio_assets.py  # Thin compatibility shims re-exporting src/eagle1/* and tools/*.
├── src/eagle1/
│   ├── app/game.py           # Game loop (60 FPS), camera, Player, aerial combat, WaveManager,
│   │                         # mission configs (MissionType), state machine, rendering pipeline, HUD.
│   ├── systems/
│   │   ├── ground_support.py # Helldivers (Viper 1-4), Automaton ground units, fabricators,
│   │   │                     # Factory Strider boss, stratagems, CAS beacons, supply drops, reticle.
│   │   ├── powerups.py       # 8 abilities across 3 rarities, drops with pity counter, drones, micro-missiles.
│   │   ├── audio_manager.py  # 16-channel mixer, procedural SFX & dynamic combat music, persistence.
│   │   ├── academy_briefing.py   # Academy tutorial drills and graduation ceremony.
│   │   └── hangar_cinematic.py   # Orbital rearm cinematic (gantry hoist, wing arms, checklist) + Stratagem Hero.
│   ├── story/                # Campaign: Super Destroyer hub view, MissionController, StoryManager,
│   │                         # comms HUD, cinematic player, dialogue data/DB, campaign save.
│   ├── ui/                   # "Military Terminal" design system and every screen:
│   │                         # theme.py (palette, type scale, bundled-font loader), widgets.py (allocation-free
│   │                         # panels/bars/TextCache), menu_nav.py (MenuButton/MenuNavigator), hud.py + hud_layout.py
│   │                         # (HUD renderer and non-overlapping zones), controls_reference.py (single key-binding
│   │                         # list), help/settings/mission-select/enlistment/debriefing screens, gameplay_settings.py.
│   ├── data/player_profile.py# Player profile persistence (class-level revision counter for change detection).
│   ├── effects.py            # Visual combat effects.
│   └── paths.py              # PROJECT_ROOT, asset dirs, platform-aware user data dir.
├── tools/                    # generate_audio_assets.py, portrait/icon generators, macOS packaging,
│                             # capture_screenshots.py (headless README screenshots).
├── tests/                    # Headless pytest suite (conftest.py sets dummy SDL drivers and an isolated user data dir).
├── data/                     # audio_settings.json, gameplay_settings.json, highscores, player_profile.json,
│                             # campaign_save.json (user data, never overwrite).
├── assets/fonts/             # Bundled OFL fonts (Chakra Petch, Share Tech Mono) + license texts.
├── images/, audio/           # Sprites, backgrounds, portraits, screenshots/; WAV assets (music/ and sfx/).
├── docs/                     # Local design notes (intent.md, spec.md, story.md); git-ignored.
└── frontend/                 # Project website (deployed via GitHub Pages).
```

Newer subsystems: the story campaign (`story/`), the Naval Academy tutorial (`MissionType.ACADEMY_TUTORIAL`), enlistment and mission debriefing screens, and the Super Destroyer hub between sorties.

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
- **8 Stratagems** (pick 4 in the pre-mission loadout with `1`–`8`/arrows + `Enter`, deploy with `Space`; in flight `1`–`5`/wheel select the quickbar slot (1 = cannons, 2–5 = equipped stratagems), hold/release `Space` aims and drops, `C` calls the equipped strike, arsenal overlay `V`/`TAB`):
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
- State machine managed in `src/eagle1/app/game.py` (`game_state`): `"main_menu"`, `"mission_select"`, `"stratagem_select"`, `"settings_menu"`, `"help_menu"`, `"pause_menu"`, `"enlistment"`, `"mission_debriefing"`, `"super_destroyer"`; the empty string `""` means active gameplay (game over is `""` with `player.health <= 0`).
- Main-menu and game-over key handling live in `handle_main_menu_keydown` / `handle_gameover_keydown` (ESC/Q pressed twice quits from the main menu). The arcade `mission_select` list is opened from the debriefing screen (`MISSIONS`); the campaign runs through the Super Destroyer hub.
- 6 operational modes (`MissionType`): *Academy Tutorial*, *Air Superiority*, *Orbital Base Defense*, *Factory Strider Boss Raid*, *Outpost Demolition*, and *Endless War*.
- Always ensure `respawn()` properly resets wave timers, mission goals, entity lists, and HUD state.

---

## Engineering Guidelines for Modifications

1. **Targeted, Incremental Changes**:
   - `src/eagle1/app/game.py` (~3,500 lines) and `src/eagle1/systems/ground_support.py` (~3,250 lines) are very large. Do not rewrite or restructure entire sections when making localized fixes or features.
   - Prefer extending modular managers (`GroundSupportManager`, `PowerUpManager`, `AudioManager`, `SettingsMenu`, `HelpMenu`) or adding a focused new module rather than appending ad-hoc logic into `game.py`.
   - Edit code under `src/eagle1/`, not the root-level compatibility shims.
2. **Path Resolution & Portability**:
   - Never hardcode absolute file paths (e.g. `C:\Users\...`).
   - Use `eagle1.paths` (`PROJECT_ROOT`, asset dirs, `get_user_data_dir()`) with `pathlib` for assets and configs.
3. **Performance & 60 FPS Frame Budget**:
   - Do not perform file I/O, heavy surface allocations, or font re-creations inside the render/update loop.
   - Cache fonts and pre-render text or transparent surfaces where applicable.
   - UI code follows the rules in `contributing.md` ("UI and Theme Rules"): colors and fonts only from `eagle1.ui.theme`, sharp corners, `widgets.TextCache` for dynamic text, HUD elements inside `eagle1.ui.hud_layout` zones, key hints from `eagle1.ui.controls_reference`, and no `◄ ► ★ ✖ ✚ ⚠` glyphs (missing from the bundled fonts). `tests/test_ui_consistency.py` enforces them.
4. **Entity Safety**:
   - Always guard against empty collections, dead entities, or `None` targets before dereferencing properties.
   - Cleanly remove dead/expired entities from tracking lists (`[e for e in enemies if e.is_alive]`).
5. **Preserve User Data**:
   - Never overwrite or reset `data/highscore.txt`, `data/stratagem_hero_highscore.txt`, `data/player_profile.json` or `data/campaign_save.json` with dummy test data.
   - `tests/conftest.py` redirects `EAGLE1_USER_DATA_DIR` to a temp dir for the whole suite; scripts you run outside pytest (renders, experiments) must set it too, as `tools/capture_screenshots.py` does.
   - Ensure `data/audio_settings.json` handles missing keys gracefully with fallback defaults.
   - Do not swallow errors with bare `except Exception: pass`; catch concrete exceptions (`OSError`, `ValueError`, `pygame.error`) and log them.
6. **Proactive Improvement Suggestions**:
   - Whenever you identify code, architecture, performance, test coverage, gameplay balancing, or usability that could be improved, **proactively state your observations and recommendations to the user**.
   - Outline the rationale, expected benefits, and possible implementation approach clearly, without performing unrequested invasive refactors.
7. **Strict English in Code & Documentation, User-Language in Chat**:
   - **Code, Comments, Docstrings & Documentation in English**: All variable names, class/function/method names, constants, code comments, docstrings, and repository documentation MUST be written strictly in English, regardless of what language the user uses in their prompt.
   - **Chat Responses Match User Language**: Always reply to the user in the language they used to write their prompt (e.g., if the user writes in German, respond to them in German; if they write in English, respond in English).


---

## Testing & Verification Workflow

### 1. Tests & Lint (same as CI)
```bash
python -m pip install -r requirements-dev.txt && python -m pip install -e .
python -m pytest tests/
ruff check .
```
CI runs the suite headless on Python 3.10–3.12; the project supports Python >= 3.9 (no `X | Y` type unions or `match` statements). The suite has ~980 tests.

### 2. Headless Execution
When running automated scripts or test checks in environments without a physical display or audio hardware, configure headless dummy drivers before initializing Pygame:
```python
import os
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
import pygame
pygame.init()
```

### 3. README Screenshots
After visible UI changes, regenerate the README images (headless, user data redirected to a temp dir):
```bash
python tools/capture_screenshots.py
```

### 4. Audio Asset Generation
If audio assets are missing or modified:
```bash
python tools/generate_audio_assets.py
```

### 5. Manual Gameplay Verification
Whenever making user-visible gameplay, UI, control, or physics changes:
```bash
python run_game.py   # or: python -m eagle1
```
Verify:
- Clean launch to Main Menu; arrow keys + `Enter` navigate, `ESC` twice quits.
- Mission selection, stratagem loadout (`Enter` toggles, `Space` deploys) and gameplay loop start.
- Pause menu (`P`), Settings (`O`), and Help manual (`H`).
- Weapon firing, collision detection, and score updates.
- Game over and respawn (`R`).

---

## Documentation Synchronization
- If controls, weapon statistics, stratagems, or operational modes are added or changed, update `README.md`, the relevant tab in `src/eagle1/ui/help_menu.py`, and `src/eagle1/ui/controls_reference.py` (Settings, manual and HUD hint read key bindings from it).
- If a screen changes visibly, regenerate the README screenshots with `python tools/capture_screenshots.py`.
- If development, installation, or test workflows change, update `contributing.md`.

---

## Git & GitHub CLI (`gh`) User Approval Policy

> [!IMPORTANT]
> **READ-ONLY vs. MUTATING COMMANDS POLICY**:
> - **Read-Only Commands (Allowed Autonomously)**: Read-only inspection commands using `git` or `gh` may be executed autonomously without prior user approval to inspect status, gather context, review diffs, or check CI/issue/PR information.
>   - *Allowed autonomous commands include*: `git status`, `git diff`, `git log`, `git show`, `git branch` (list only), `git tag` (list only), `git rev-parse`, `gh issue list`, `gh issue view`, `gh pr list`, `gh pr view`, `gh pr diff`, `gh run list`, `gh run view`, `gh release list`, `gh auth status`, and read-only `gh api` calls.
> - **Mutating / State-Altering Commands (Strict Prior Approval Required)**: NEVER execute ANY `git` or `gh` command that alters repository state, branches, staging, commits, remote tracking, or GitHub platform resources (issues, PRs, releases, comments, labels) without explicit prior user approval.
>   - *Requires approval*: `git add`, `git commit`, `git push`, `git pull`, `git fetch`, `git merge`, `git rebase`, `git checkout` / `git switch` (changing branches or discarding files), `git reset`, `git revert`, `git clean`, `git stash`, `git branch -d`/`-m`, `gh pr create`, `gh pr merge`, `gh pr close`, `gh issue create`, `gh issue close`, `gh release create`, etc.

### User Approval Protocol for Mutating Git & `gh` Commands
Before running **ANY mutating or state-changing** `git` or `gh` command:
1. **Always ask the user for explicit permission first.**
2. **Provide a detailed, precise explanation**:
   - **Why** the command is needed right now.
   - **Why exactly this command** (and these exact flags/arguments) was chosen instead of any other command or approach.
   - **What exact impact** the command will have on files, branches, remotes, or git history.
   - Display the exact command line string that is proposed for execution.
3. **Wait for the user's explicit confirmation** before running the command. Never assume implicit consent or execute state-modifying commands speculatively.

---

## GitHub CLI (`gh`) & Repository Operations Reference

Use the GitHub CLI (`gh`) according to the following guidelines:

### Key Use Cases
1. **Autonomous Issue, PR & Build Inspection (Read-Only)**:
   - Inspect related issues, feature requirements, or bug reports without prior prompt:
     ```bash
     gh issue list
     gh issue view <issue-number> --comments
     ```
   - Review or diff existing pull requests:
     ```bash
     gh pr list
     gh pr view <pr-number>
     gh pr diff <pr-number>
     ```
   - Check workflow runs and inspect failing logs to diagnose CI test errors:
     ```bash
     gh run list --limit 5
     gh run view <run-id> --log-failed
     ```
   - Check latest releases or tags:
     ```bash
     gh release list
     ```
2. **State-Modifying Operations (Always Require Prior Approval)**:
   - Create PRs with explicit, non-interactive flags after user approval:
     ```bash
     gh pr create --title "<type>: <brief summary>" --body "<structured description>"
     ```
   - Merging, closing, or modifying issues/PRs/releases: only after explicit user approval.

### Execution Best Practices
- **Non-Interactive Execution**: Always pass necessary parameters (`--title`, `--body`, `--fill`, `-y`) so commands never block on interactive terminal prompts.
- **Structured Output**: Use `--json <fields>` or `--jq` when querying data programmatically.
- **Auth Verification**: The CLI is authenticated under `paulp143`. If permission issues arise, verify via `gh auth status`.

