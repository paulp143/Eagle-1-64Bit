#!/usr/bin/env python3
"""
build_macos_dmg.py - Creates a distributable macOS drag-and-drop installer DMG.

Uses macOS built-in hdiutil to bundle Eagle-1.app and an /Applications symlink
into a compressed .dmg disk image.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DIST_DIR = PROJECT_ROOT / "dist"
APP_BUNDLE = DIST_DIR / "Eagle-1.app"
OUTPUT_DMG = DIST_DIR / "Eagle-1-macOS.dmg"
STAGING_DIR = DIST_DIR / "dmg_staging"


def build_dmg():
    if sys.platform != "darwin":
        print(f"[build_macos_dmg] Skipping DMG creation on non-macOS platform ({sys.platform}).")
        return 0

    if not APP_BUNDLE.is_dir():
        print(f"[build_macos_dmg] Error: {APP_BUNDLE} does not exist. Run PyInstaller first.", file=sys.stderr)
        return 1

    if STAGING_DIR.exists():
        shutil.rmtree(STAGING_DIR)
    STAGING_DIR.mkdir(parents=True, exist_ok=True)

    try:
        # Copy Eagle-1.app into staging
        print(f"[build_macos_dmg] Copying {APP_BUNDLE.name} to staging directory...")
        target_app = STAGING_DIR / "Eagle-1.app"
        subprocess.run(["cp", "-R", str(APP_BUNDLE), str(target_app)], check=True)

        # Create Applications symlink for drag-and-drop installation
        apps_link = STAGING_DIR / "Applications"
        if not apps_link.exists():
            os.symlink("/Applications", str(apps_link))

        # Create compressed DMG image using hdiutil
        if OUTPUT_DMG.exists():
            OUTPUT_DMG.unlink()

        print(f"[build_macos_dmg] Building disk image: {OUTPUT_DMG}...")
        subprocess.run(
            [
                "hdiutil",
                "create",
                "-volname",
                "Eagle-1",
                "-srcfolder",
                str(STAGING_DIR),
                "-ov",
                "-format",
                "UDZO",
                str(OUTPUT_DMG),
            ],
            check=True,
            capture_output=True,
        )

        size_mb = OUTPUT_DMG.stat().st_size / (1024 * 1024)
        print(f"[build_macos_dmg] Successfully created {OUTPUT_DMG} ({size_mb:.2f} MB)")
        return 0

    except subprocess.CalledProcessError as e:
        print(f"[build_macos_dmg] Error building DMG: {e.stderr.decode() if e.stderr else e}", file=sys.stderr)
        return 1
    finally:
        if STAGING_DIR.exists():
            shutil.rmtree(STAGING_DIR, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(build_dmg())

