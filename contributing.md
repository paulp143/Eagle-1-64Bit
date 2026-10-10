# Contributing to Eagle-1-64Bit

Thank you for your interest in contributing to **Eagle-1-64Bit**! This project is a Python/Pygame 2D space-combat game featuring dogfighting, ground support, air strikes, and Helldiver rescue missions.

This guide explains how to set up a development environment, make changes, test them, and submit a contribution.

## Code of Conduct

All contributors and participants in the Eagle-1-64Bit community are expected to uphold our [Code of Conduct](CODE_OF_CONDUCT.md). Please be respectful, constructive, and welcoming in issues, pull requests, and discussions. For reporting concerns or Code of Conduct violations, refer to the procedures in [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) or contact [paul@schep.de](mailto:paul@schep.de).

## Getting Started

### Prerequisites

- Python 3.9 or newer
- Git
- A working desktop environment capable of running Pygame

The project currently supports Python versions through the development versions documented in `README.md`. Pygame (`pygame-ce` or `pygame`) is the primary runtime dependency.

### Clone the Repository

```bash
git clone https://github.com/paulp143/Eagle-1-64Bit.git
cd Eagle-1-64Bit
```

### Create a Virtual Environment

Using a virtual environment is recommended so project dependencies do not interfere with other Python projects.

**Windows PowerShell:**

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**Windows Command Prompt:**

```cmd
python -m venv venv
venv\Scripts\activate.bat
```

**Linux/macOS:**

```bash
python3 -m venv venv
source venv/bin/activate
```

### Install Dependencies

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
python -m pip install -e .
```

### Run the Game

Run the game from the repository root:

```bash
python run_game.py
# Alternatively: python -m eagle1 (or eagle1 if installed in editable mode)
```

## Project Structure

The project follows a standard `src/` layout with modular packages:

- `src/eagle1/app/game.py` — game initialization, player aircraft, combat loop, UI, waves, and persistence.
- `src/eagle1/systems/ground_support.py` — Helldiver units, Automaton ground forces, fabricators, air strikes, supply drops, and CAS missions.
- `src/eagle1/systems/powerups.py` — power-up drops, abilities, escort drones, and homing micro-missiles.
- `src/eagle1/systems/audio_manager.py` — 16-channel mixer, procedural SFX & dynamic combat music, persistence.
- `src/eagle1/ui/help_menu.py` — in-game tactical help menu and its six information tabs.
- `src/eagle1/ui/settings_menu.py` — tabbed settings interface.
- `tools/generate_audio_assets.py` — standalone audio synthesis tool.
- `tools/build_macos_icon.py` — synthesizes Apple `.icns` multi-resolution icon bundle.
- `tools/build_macos_dmg.py` — packages `Eagle-1.app` into a drag-and-drop `.dmg` disk image.
- `tools/package_macos.py` — complete macOS standalone packaging pipeline (.app, .dmg, .zip).
- `tests/` — automated headless test suite running under `pytest`.
- `images/` — sprites, backgrounds, explosions, and interface assets.
- `data/` — runtime data such as high scores and audio settings.
- Root scripts (`run_game.py`, `main.py`, etc.) provide convenient launchers and compatibility shims.

Read the relevant module and existing tests before changing behavior. Prefer extending existing systems over duplicating logic.

## Development Workflow

1. Create or select an issue describing the change or bug.
2. Fork the repository if you do not have direct write access.
3. Create a focused branch from `main`:

   ```bash
   git checkout main
   git pull origin main
   git checkout -b feature/short-description
   ```

4. Make the smallest coherent change that addresses the issue.
5. Add or update tests where practical.
6. Run the test suite and manually verify gameplay-related changes.
7. Commit your work with a clear message.
8. Push your branch and open a pull request.

Suggested branch names:

- `feature/add-new-stratagem`
- `fix/rocket-lock-on`
- `docs/update-controls`
- `test/ground-support-cases`

## Coding Guidelines

- Follow the existing Python style and naming conventions.
- Use clear, descriptive names for variables, functions, classes, and constants.
- Keep functions focused and avoid unrelated refactoring in feature or bug-fix pull requests.
- Add docstrings to new public classes and functions.
- Add comments where collision, physics, targeting, timing, or state-transition logic is not self-explanatory.
- Preserve the existing gameplay feel unless the issue specifically requests a balance change.
- Use constants for tunable gameplay values instead of scattering numeric literals throughout the code.
- Keep asset paths compatible with running the game from the repository root.
- Avoid committing generated files, local virtual environments, caches, editor settings, or personal high-score changes.

## Testing

Run the automated test suite before submitting a pull request:

```bash
python -m pytest
```

You can also run pytest with verbose output:

```bash
pytest -v
```

To run lint checks:

```bash
ruff check .
```

When adding a feature, consider tests for:

- Initialization and default state
- Input handling and state transitions
- Collision and damage behavior
- Cooldowns, timers, and reloads
- Boundary and edge cases
- Rendering code that can be exercised without a display
- Interactions with existing gameplay systems

For changes involving Pygame rendering or input, use the existing headless-test patterns where possible and manually test the game window as well.

## Manual Verification

Before opening a pull request, manually check the areas affected by your change. For gameplay changes, verify that:

- The game starts from a clean checkout.
- The main menu, pause menu, and game-over flow still work.
- The relevant controls work with both keyboard and mouse alternatives where applicable.
- Assets load correctly when running `python main.py` from the repository root.
- The high score and other persistent data continue to behave correctly.
- No visible errors or unexpected performance regressions occur during gameplay.

## Documentation Changes

Update documentation when behavior, controls, configuration, installation, or project structure changes. Relevant documentation includes:

- `README.md` for player-facing setup, controls, gameplay, and troubleshooting information.
- `DEVELOPMENT.md` for detailed developer setup and workflows, when available.
- `ARCHITECTURE.md` for system design and module relationships, when available.
- `GAMEPLAY.md` for detailed mechanics and strategy, when available.
- `ASSETS.md` for asset sources and attribution, when available.

Use screenshots or GIFs only when they clearly improve the explanation, and include appropriate attribution for third-party assets.

## Commit Messages

Use concise commit messages that describe the change. Examples:

```text
Add tests for fabricator reinforcement spawning
Fix homing rocket target filtering
Improve local development instructions
Update controls documentation for CAS missions
```

Keep commits focused. If a change has multiple independent parts, consider splitting it into separate commits.

## Pull Requests

A pull request should:

- Explain what changed and why.
- Reference the related issue, such as `Closes #7` when appropriate.
- Include tests that were added or run.
- Mention any manual verification performed.
- Include screenshots or recordings for meaningful visual or gameplay changes.
- Call out known limitations, compatibility concerns, or follow-up work.

Keep pull requests focused and reviewable. Avoid combining unrelated cleanup with a feature or bug fix unless it is necessary for the change.

### Pull Request Checklist

Before requesting review, confirm:

- [ ] The change addresses an existing issue or has a clear explanation.
- [ ] The code follows the project's existing style.
- [ ] New or changed behavior has tests where practical.
- [ ] The automated test suite passes.
- [ ] Manual gameplay verification is complete when relevant.
- [ ] Documentation has been updated when needed.
- [ ] No virtual environments, caches, generated files, or personal data are included.
- [ ] The pull request description explains the change and testing performed.

## Security Vulnerabilities

If you suspect or have discovered a security vulnerability, please **do not** open a public issue. Review our [Security Policy](.github/SECURITY.md) for instructions on submitting a confidential report via GitHub Security Advisories or direct maintainer email.

## Reporting Bugs

When reporting a bug, include:

- A concise title.
- Steps to reproduce the problem.
- Expected behavior.
- Actual behavior.
- Python and Pygame versions.
- Operating system.
- Relevant traceback or console output.
- Screenshots or recordings for visual issues.
- Whether the problem occurs from a clean checkout.

Please search existing issues first to avoid creating duplicates.

## Suggesting Features

Feature requests are welcome. Explain:

- The gameplay or development problem the feature solves.
- The proposed behavior and controls.
- How the feature fits the existing architecture.
- Potential performance, balance, or compatibility considerations.
- Any assets or documentation that would be required.

Small, well-scoped proposals are easier to evaluate and implement.

## Asset and License Requirements

The project is licensed under the MIT License. Contributions must be compatible with that license. Do not add copyrighted, trademarked, or third-party assets unless you have permission to redistribute them.

For new assets:

- Prefer original or appropriately licensed work.
- Record the source, creator, license, and any required attribution.
- Add attribution to the appropriate documentation file.
- Keep filenames and paths consistent with the existing asset organization.

## Questions

If you are unsure where to start, review the open issues, inspect the existing tests, or open a discussion describing your idea before making a large change.

Thank you for helping improve Eagle-1-64Bit!
