# Tasks: Cross-Platform Compatibility (Linux & macOS)

## Phase 1: Core Foundation & Path Portability

- [x] Task 1: Refactor `src/eagle1/paths.py` for PyInstaller bundle awareness and platform-standard user data directory
  - **Description:** Implement `get_base_dir()` (supporting `sys._MEIPASS` when frozen) and `get_user_data_dir()` adhering to XDG on Linux (`~/.local/share/Eagle-1`), macOS (`~/Library/Application Support/Eagle-1`), and Windows (`%APPDATA%/Eagle-1`), falling back to local `data/` for portable/dev runs. Update all callers in `game.py`, `audio_manager.py`, `ground_support.py`, and `hangar_cinematic.py` to use `get_user_data_dir()`.
  - **Acceptance criteria:**
    - `paths.py` handles frozen (`sys._MEIPASS`) and development paths seamlessly.
    - User highscores and audio settings persist in user data directory without requiring write permissions to program directory.
    - Automatic migration or fallback from local `data/` if existing files exist.
  - **Verification:** New tests in `tests/test_paths.py` verifying path resolution and mock frozen execution.
  - **Dependencies:** None
  - **Files likely touched:** `src/eagle1/paths.py`, `src/eagle1/app/game.py`, `src/eagle1/systems/audio_manager.py`, `src/eagle1/systems/ground_support.py`, `src/eagle1/systems/hangar_cinematic.py`, `tests/test_paths.py`
  - **Estimated scope:** Medium (3-5 files)

- [ ] Task 2: Audit and enforce case sensitivity for all asset loading
  - **Description:** On case-sensitive Linux filesystems (ext4/btrfs), mismatched asset filenames fail silently or crash. Scan all asset filenames under `images/` and `audio/` and verify all string literals in code (`.png`, `.wav`) match exact disk casing. Add an automated test that asserts all loaded asset filenames exist with exact case.
  - **Acceptance criteria:**
    - Zero case discrepancies between code asset references and filesystem entries.
    - Automated test catches any future case discrepancies.
  - **Verification:** Run `pytest tests/test_asset_casing.py`.
  - **Dependencies:** Task 1
  - **Files likely touched:** `tests/test_asset_casing.py`, and any asset-referencing files if mismatches found.
  - **Estimated scope:** Small (1-2 files)

- [x] Task 3: Platform keybindings and input ergonomics
  - **Description:** On macOS, users commonly expect Command (`K_LMETA`/`K_RMETA`) or Right Control alongside Left Control for primary/secondary weapon triggers. Audit input handling in `game.py` and ensure ergonomic missile/stratagem inputs across Mac and Linux keyboards.
  - **Acceptance criteria:**
    - Rocket firing checks include `K_LMETA` and `K_RMETA` (Command keys) when on macOS or universally without conflicting with existing binds.
    - Documented in help menu and tooltips.
  - **Verification:** Unit tests verifying modifier key mapping.
  - **Dependencies:** None
  - **Files likely touched:** `src/eagle1/app/game.py`, `src/eagle1/ui/help_menu.py`, `tests/test_ui_and_menus.py`
  - **Estimated scope:** Small (2-3 files)

## Checkpoint: Foundation
- [x] All unit and regression tests pass (`python -m pytest tests/`).
- [x] Path resolution and user data directory functioning across simulated platforms.

---

## Phase 2: CI/CD Multi-OS Pipeline

- [x] Task 4: Expand CI test matrix to include macOS
  - **Description:** Add `macos-latest` to the GitHub Actions test matrix in `.github/workflows/ci.yml`. Configure environment variables (`SDL_VIDEODRIVER: "dummy"`, `SDL_AUDIODRIVER: "dummy"`) and verify Python 3.10, 3.11, 3.12 compatibility on all three operating systems (Ubuntu, Windows, macOS).
  - **Acceptance criteria:**
    - `.github/workflows/ci.yml` matrix includes `[ubuntu-latest, windows-latest, macos-latest]`.
    - Headless audio generation tool step runs cleanly on macOS runner.
  - **Verification:** Validate workflow syntax with actionlint / local inspection.
  - **Dependencies:** Task 1, Task 2
  - **Files likely touched:** `.github/workflows/ci.yml`
  - **Estimated scope:** Small (1 file)

- [x] Task 5: Upgrade release packaging workflow for Linux and macOS binaries
  - **Description:** Extend `.github/workflows/build-exe.yml` into a cross-platform release workflow matrix (`build-binaries`). Build:
    1. Windows: `Eagle-1-Windows.zip` (standalone directory executable)
    2. Linux: `Eagle-1-Linux.tar.gz` (standalone directory binary, POSIX `:` separator for PyInstaller `--add-data`)
    3. macOS: `Eagle-1-macOS.zip` (standalone `.app` bundle with `Info.plist` high-DPI support)
    Attach all 3 packages to GitHub Releases and artifacts.
  - **Acceptance criteria:**
    - Linux and macOS jobs added with appropriate PyInstaller arguments (`--windowed`, `--onedir`, `:` data separator).
    - Release step publishes `Eagle-1-Windows.zip`, `Eagle-1-Linux.tar.gz`, and `Eagle-1-macOS.zip`.
  - **Verification:** Workflow structure review and dry-run syntax validation.
  - **Dependencies:** Task 1, Task 4
  - **Files likely touched:** `.github/workflows/build-exe.yml`
  - **Estimated scope:** Small (1 file)

## Checkpoint: CI/CD & Build Matrix
- [x] CI and build workflow YAML schemas are valid.
- [x] All 3 platforms covered in both test runs and release packaging pipelines.

---

## Phase 3: Documentation & Web Distribution

- [x] Task 6: Synchronize documentation and installation instructions
  - **Description:** Update `README.md`, `contributing.md`, and in-game manuals (`help_menu.py`) with platform-specific instructions for Linux (installing system SDL2 packages `libsdl2-dev` / `libsdl2-mixer-dev` if needed) and macOS (Homebrew setup, Gatekeeper quarantine bypass `xattr -d com.apple.quarantine Eagle-1.app` for unsigned indie apps).
  - **Acceptance criteria:**
    - Clear installation and run commands for Linux, macOS, and Windows.
    - Updated troubleshooting section for Linux audio (PulseAudio/PipeWire) and macOS app launching.
  - **Verification:** Documentation review for clarity and accuracy.
  - **Dependencies:** Task 5
  - **Files likely touched:** `README.md`, `contributing.md`, `src/eagle1/ui/help_menu.py`
  - **Estimated scope:** Small (3 files)


- [ ] Task 7: Update frontend landing page with cross-platform download links
  - **Description:** Update `frontend/index.html` and `frontend/main.js` to provide download buttons for Windows (`.zip`), Linux (`.tar.gz`), and macOS (`.zip`), optionally auto-detecting the user's OS via `navigator.userAgent` or `navigator.userAgentData`.
  - **Acceptance criteria:**
    - Landing page displays download options for Windows, macOS, and Linux.
    - Links point to corresponding release asset artifacts.
  - **Verification:** Inspect `frontend/index.html` in browser / visual check.
  - **Dependencies:** Task 5
  - **Files likely touched:** `frontend/index.html`, `frontend/main.js`, `frontend/style.css`
  - **Estimated scope:** Small (2-3 files)

## Checkpoint: Complete
- [ ] Full regression test suite passes.
- [ ] Cross-platform implementation fully specified and tracked.
- [ ] Ready for execution.

