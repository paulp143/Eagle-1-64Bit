# CLAUDE.md — Eagle-1-64Bit

@AGENTS.md

## Claude Code specifics
- Run tests with `python -m pytest tests/` and lint with `ruff check .` (both run in CI). Tests are headless (`tests/conftest.py`); do not launch `python run_game.py` unless the change is user-visible and the user agrees.
- Game code lives in `src/eagle1/`. The root files `main.py`, `ground_support.py`, `help_menu.py`, `audio_manager.py`, `academy_briefing.py` are thin compatibility shims; edit the modules under `src/eagle1/` instead.
- `src/eagle1/app/game.py` (~3,600 lines) and `src/eagle1/systems/ground_support.py` (~3,200 lines) are very large. Make localized edits, do not restructure them unless asked, and prefer putting new logic into a module of its own.
- Never edit or commit `data/highscore.txt`, `data/stratagem_hero_highscore.txt` or `data/player_profile.json` (user data).
- Mutating `git` / `gh` commands need explicit user approval first (see AGENTS.md).
- Reply in the user's language; code, comments and docs stay in English.
