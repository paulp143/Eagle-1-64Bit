# CLAUDE.md — Eagle-1-64Bit

@AGENTS.md

## Claude Code specifics
- Run tests with `python -m pytest tests/` and lint with `ruff check .` (both run in CI). Tests are headless (`tests/conftest.py`, which also redirects user data to a temp dir); do not launch `python run_game.py` unless the change is user-visible and the user agrees. To check visuals without launching the game, render headlessly (`python tools/capture_screenshots.py --out <scratch dir>`).
- Game code lives in `src/eagle1/`. The root files `main.py`, `ground_support.py`, `help_menu.py`, `settings_menu.py`, `powerup_system.py`, `audio_manager.py`, `academy_briefing.py`, `generate_audio_assets.py` are thin compatibility shims; edit the modules under `src/eagle1/` (or `tools/`) instead.
- UI work follows the "Military Terminal" rules in `contributing.md` (theme tokens and fonts from `eagle1.ui.theme`, no per-frame Surface/font allocation, HUD zones from `eagle1.ui.hud_layout`, key hints from `eagle1.ui.controls_reference`); `tests/test_ui_consistency.py` enforces them.
- `src/eagle1/app/game.py` (~3,500 lines) and `src/eagle1/systems/ground_support.py` (~3,250 lines) are very large. Make localized edits, do not restructure them unless asked, and prefer putting new logic into a module of its own.
- Never edit or commit `data/highscore.txt`, `data/stratagem_hero_highscore.txt`, `data/player_profile.json`, `data/campaign_save.json` or the settings JSON files (user data). Any script run outside pytest must set `EAGLE1_USER_DATA_DIR` to a temp dir.
- Mutating `git` / `gh` commands need explicit user approval first (see AGENTS.md).
- Reply in the user's language; code, comments and docs stay in English.
