# Claude Code Instructions

## Repository overview

This repository contains Eagle-1-64Bit, a Python/Pygame 2D top-down space-combat arcade game. Eagle-1 flies through a 3000×3000 scrolling arena while engaging aerial Automaton forces and supporting a four-member Helldiver squad on the ground.

The codebase combines aerial dogfighting, inertia-driven movement, quad-cannon salvos, homing rockets, radar lock-on, mission-specific objectives, ground combat, CAS stratagems, supply drops, power-ups, audio, HUD rendering, menus, and high-score persistence.

## Architecture map

- `main.py` owns application startup, global constants, the player, aerial enemies, weapons, mission state, waves, rendering, input handling, audio integration, and the 60 FPS loop.
- `ground_support.py` owns Helldiver units, Automaton troopers and walkers, fabricators, Factory Strider behavior, air strikes, CAS missions, supply drops, predictive reticles, weapon menus, and ground-support HUD/minimap output.
- `powerup_system.py` owns power-up tables, drop logic, rarity, timed abilities, escort drones, homing micro-missiles, and power-up HUD output.
- `help_menu.py` owns the six-tab tactical manual.
- `settings_menu.py` owns audio, HUD/gameplay, and flight-control settings.
- `audio_manager.py` owns the centralized mixer, effects, music, engine loop, and threat-based music intensity.
- `generate_audio_assets.py` generates procedural audio assets.
- `test_help_menu.py`, `test_ground_support.py`, and `test_gameplay_integration.py` contain the automated test suite.
- `images/` and `audio/` contain runtime assets.
- `data/highscore.txt` stores the high score and should not be modified as part of ordinary development.

## Instructions for changes

1. Read the relevant implementation and tests before making a change.
2. Keep changes narrowly scoped and consistent with the existing architecture.
3. Prefer extending existing systems over creating duplicate managers or parallel code paths.
4. Do not rewrite `main.py` broadly for a localized bug or feature.
5. Preserve established controls, mission transitions, HUD conventions, audio feedback, and gameplay balance unless the requested change says otherwise.
6. Use named constants for new tunable values.
7. Preserve the distinction between world-space, camera-space, and screen-space coordinates.
8. Guard interactions against entities that are dead, exploding, inactive, missing, or outside valid ranges.
9. Avoid new third-party dependencies without a clear need.
10. Never introduce developer-specific absolute filesystem paths; resolve assets from the repository root.

## Implementation details to preserve

- Player damage is shield-first, then hull, with the existing invincibility timer.
- Weapon changes must update ammunition, cooldown/reload state, targeting, collisions, score, sounds, visual effects, and HUD indicators.
- Mission changes must work through mission configuration and `respawn()`, update wave/objective state, and reset cleanly.
- Stratagem changes must work with weapon selection, cooldowns, aiming and release events, predictive reticles, area effects, audio, and CAS delivery rules.
- Ground-support changes should account for squad health/state, allied casualties, CAS requests, supply drops, extraction, score bonuses/penalties, and minimap/HUD rendering.
- Pygame code should remain compatible with the repository's headless tests whenever possible.

## Testing commands

Use the focused suite:

```bash
python -m unittest test_help_menu.py test_ground_support.py test_gameplay_integration.py
```

Use unittest discovery for the complete available suite:

```bash
python -m unittest discover
```

Run the game manually from the repository root for changes affecting rendering, input, assets, audio, or gameplay:

```bash
python main.py
```

Report failures, unavailable display/audio environments, skipped checks, and manual-verification limitations accurately. Never state that a command passed unless it was executed.

## Test expectations

When adding or changing behavior, consider tests for:

- Initialization and default state.
- Keyboard and mouse input.
- Menu and game-state transitions.
- Collision and damage behavior.
- Cooldowns, timers, and reloads.
- Radar lock-on and target filtering.
- Boundary and empty-list cases.
- Headless rendering.
- Interactions among aerial combat, ground support, power-ups, audio, scoring, and mission systems.
- Respawn/reset behavior.

## Documentation and licensing

- Update `README.md` when user-facing controls, gameplay, missions, setup, configuration, or troubleshooting changes.
- Update `contributing.md` when developer workflow or test instructions change.
- Prefer original or properly licensed assets. Add source and attribution information when required.
- Maintain compatibility with the repository's MIT license.

## Final review checklist

Before completing a task:

- Verify the requested behavior and inspect affected integrations.
- Run relevant automated tests and report exact commands/results.
- Manually launch the game when appropriate.
- Check that assets resolve from a clean repository-root launch.
- Avoid unrelated cleanup and avoid modifying personal high-score data.
- Do not commit virtual environments, caches, generated temporary files, or editor settings.
- Provide a concise summary of changed files, validation performed, and known limitations.
