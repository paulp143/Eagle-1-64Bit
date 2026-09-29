# Antigravity Agent Instructions

## Project

Eagle-1-64Bit is a Python/Pygame 2D top-down space-combat game. The player pilots Eagle-1 through a 3000×3000 scrolling arena, fights aerial Automaton enemies, and provides Close Air Support for allied Helldivers on the ground.

Core features include inertia-based flight, quad cannons, homing rockets, radar lock-on, mission selection, Helldiver ground support, Automaton ground units, fabricators, Factory Striders, bombers, orbital-base defense, stratagem air strikes, supply drops, power-ups, audio, HUDs, menus, and high-score persistence.

## Important files

- `main.py`: Application startup, global gameplay constants, player aircraft, aerial combat, mission flow, main loop, rendering, and persistence.
- `ground_support.py`: Helldivers, ground enemies, fabricators, Factory Strider, air strikes, supply drops, CAS requests, reticles, weapon selection, and ground HUD.
- `powerup_system.py`: Power-up definitions, drops, timers, drones, homing pods, and related HUD behavior.
- `help_menu.py`: In-game tactical help menu.
- `settings_menu.py`: Audio, gameplay/HUD, and flight-control settings.
- `audio_manager.py`: Centralized music, sound effects, engine audio, and dynamic combat audio.
- `generate_audio_assets.py`: Procedural audio generation.
- `test_help_menu.py`, `test_ground_support.py`, `test_gameplay_integration.py`: Automated tests.
- `images/`: Runtime image assets.
- `audio/`: Audio assets.
- `data/highscore.txt`: Persistent high score; do not change it with personal test data.

## Operating rules

1. Inspect the relevant source and tests before editing.
2. Make the smallest focused change that solves the task.
3. Reuse existing managers, entities, constants, helpers, and rendering patterns.
4. Avoid unrelated refactors or broad rewrites, especially in `main.py`.
5. Preserve existing controls, mission flow, visual style, audio behavior, and gameplay feel unless the task explicitly changes them.
6. Put tunable gameplay values in named constants rather than scattered literals.
7. Keep world coordinates, camera coordinates, and screen/UI coordinates separate.
8. Handle dead, exploding, inactive, and out-of-range entities safely.
9. Do not add dependencies unless necessary and explicitly justified.
10. Never add new machine-specific absolute paths. Use project-root-relative asset paths.

## Python/Pygame guidance

- Maintain Python 3.8+ compatibility.
- Follow existing naming and formatting conventions.
- Add docstrings to new public classes and functions.
- Comment non-obvious physics, collision, timer, targeting, coordinate-transform, and state-machine logic.
- Preserve headless-test compatibility and avoid requiring a display or audio device during tests.
- Use existing Pygame timer/event patterns consistently.
- Respect the shield-before-hull damage model and invincibility timing.
- For weapon changes, account for ammo, cooldowns, reloads, targeting, collision, score, audio, and HUD state.
- For mission changes, integrate mission configuration, `respawn()`, wave progression, objective HUD text, success/failure, and reset behavior.
- For stratagem changes, integrate selection, cooldowns, aiming/release, reticles, effects, audio, and tests.

## Testing

Run focused tests first:

```bash
python -m unittest test_help_menu.py test_ground_support.py test_gameplay_integration.py
```

Run all unittest discovery when practical:

```bash
python -m unittest discover
```

For visible gameplay or asset-related changes, manually run from the repository root:

```bash
python main.py
```

If Pygame or a display is unavailable, report that manual verification could not be performed. Do not claim tests passed unless they were actually run.

## Documentation and assets

- Update `README.md` for user-visible controls, gameplay, missions, installation, configuration, or troubleshooting changes.
- Update `contributing.md` for development workflow or testing changes.
- Prefer original or appropriately licensed assets and record required attribution.
- Keep all contributions compatible with the MIT license.

## Completion checklist

Before finishing:

- Confirm the requested behavior works.
- Check menu, pause, game-over, respawn, scoring, audio, and HUD interactions where relevant.
- Add or update tests where practical.
- Run relevant tests and report the exact commands.
- Manually verify gameplay when applicable.
- Avoid committing caches, virtual environments, generated files, editor files, or personal high-score changes.
- Summarize changed files, tests, manual checks, and known limitations.
