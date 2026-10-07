# Implementation Plan: Cross-Platform Compatibility (Linux & macOS)

## Overview
Enable full first-class cross-platform support for **Eagle-1-64Bit** across Linux and macOS alongside the existing Windows platform. This encompasses:
1. Robust runtime path resolution and user data persistence adhering to OS conventions (`XDG_DATA_HOME` / `~/.local/share` on Linux, `~/Library/Application Support` on macOS, and `%APPDATA%` on Windows or portable folder fallbacks), including PyInstaller frozen bundle support (`sys._MEIPASS`).
2. Asset filesystem case-sensitivity verification and platform-friendly controls (handling macOS `Command`/`Super` and control modifier ergonomic keybindings).
3. CI/CD test automation covering `ubuntu-latest`, `windows-latest`, and `macos-latest` across Python 3.10, 3.11, and 3.12.
4. Cross-platform release packaging in GitHub Actions yielding standalone distributions: Windows (`Eagle-1-Windows.zip`), Linux (`Eagle-1-Linux.tar.gz`), and macOS (`Eagle-1-macOS.zip` app bundle).
5. Comprehensive documentation in `README.md`, `contributing.md`, and frontend landing pages.

## Architecture Decisions
- **Runtime Asset vs User Data Path Separation**:
  - Read-only game assets (`images/`, `audio/`) are resolved relative to `sys._MEIPASS` when frozen (PyInstaller executable) or `PROJECT_ROOT` when running from source.
  - Writable user data (`highscore.txt`, `stratagem_hero_highscore.txt`, `audio_settings.json`) will be resolved via a unified `get_user_data_dir()` helper in `src/eagle1/paths.py`. On installed/frozen releases, writing to the read-only application directory fails on Linux (`/opt` or read-only mounted filesystems) and macOS (`Eagle-1.app/Contents/MacOS`). Implementing standard user data paths prevents permission errors and ensures user scores/settings persist across updates.
- **PyInstaller Multi-OS Strategy**:
  - Windows: `--add-data "images;images"` (semicolon separator) -> `.zip`.
  - Linux: `--add-data "images:images"` (colon separator) -> `.tar.gz`.
  - macOS: `--add-data "images:images"` (colon separator), `--windowed` bundle (`Eagle-1.app`), with `Info.plist` CFBundleDisplayName and high-DPI `NSHighResolutionCapable=True` -> `.zip`.
  - Use GitHub Actions matrix build in `.github/workflows/build-exe.yml` (renamed or expanded to cross-platform packaging workflow) with OS-specific conditional flags or a shared build script.
- **CI Test Matrix**:
  - Extend `.github/workflows/ci.yml` matrix `os` to include `macos-latest`.
  - Run with `SDL_VIDEODRIVER=dummy` and `SDL_AUDIODRIVER=dummy`.

## Task List

### Phase 1: Foundation & Portability
- [x] Task 1: Refactor `src/eagle1/paths.py` for PyInstaller bundle awareness and platform-standard user data directory.
- [ ] Task 2: Verify and audit case-sensitivity across all asset references against physical files on disk.
- [ ] Task 3: macOS keybindings and platform input ergonomics (support `K_RMETA`/`K_LMETA`/`K_RCTRL` in secondary rocket triggers).

### Checkpoint: Foundation
- [ ] `pytest tests/` passes with all existing and newly added path/platform tests.
- [ ] User data and asset resolution verified in both normal and simulated frozen environments.

### Phase 2: CI/CD Multi-OS Pipeline
- [ ] Task 4: Expand `.github/workflows/ci.yml` to include `macos-latest` in test matrix with required environment configuration.
- [ ] Task 5: Upgrade release build workflow (`.github/workflows/build-exe.yml`) to multi-OS matrix (Windows, Linux, macOS).

### Checkpoint: CI/CD & Build Matrix
- [ ] Workflow YAML files syntax-validated and conform to GitHub Actions best practices.
- [ ] Automated headless test suite passes across platforms.

### Phase 3: Documentation & Distribution
- [ ] Task 6: Update `README.md`, `contributing.md`, and `help_menu.py` with Linux and macOS prerequisites and controls.
- [ ] Task 7: Update frontend landing page (`frontend/index.html` & `frontend/main.js`) with download options for Linux and macOS.

### Checkpoint: Complete
- [ ] All cross-platform compatibility criteria verified.
- [ ] Clean git status and ready for review.

