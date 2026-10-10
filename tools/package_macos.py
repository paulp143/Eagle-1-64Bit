#!/usr/bin/env python3
"""
package_macos.py - Complete end-to-end macOS distribution packager for Eagle-1-64Bit.

Orchestrates:
1. Icon synthesis (.icns)
2. PyInstaller standalone bundle creation (.app)
3. Info.plist Retina / Dark Mode verification
4. Ad-hoc Mach-O code signing
5. Distributable DMG image and ZIP archive generation
"""

import plistlib
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DIST_DIR = PROJECT_ROOT / "dist"
APP_BUNDLE = DIST_DIR / "Eagle-1.app"
ICNS_FILE = PROJECT_ROOT / "images" / "Eagle-1.icns"


def package_macos():
    if sys.platform != "darwin":
        print(f"[package_macos] Error: macOS packaging requires macOS (detected: {sys.platform})", file=sys.stderr)
        return 1

    # Step 1: Ensure .icns application icon exists
    if not ICNS_FILE.exists():
        print("[package_macos] Generating application icon...")
        icon_builder = PROJECT_ROOT / "tools" / "build_macos_icon.py"
        subprocess.run([sys.executable, str(icon_builder)], check=True)

    # Step 2: Run PyInstaller
    print("[package_macos] Packaging Eagle-1.app with PyInstaller...")
    pyinstaller_cmd = [
        "pyinstaller",
        "--noconfirm",
        "--onedir",
        "--windowed",
        "--name",
        "Eagle-1",
        "--icon",
        str(ICNS_FILE),
        "--add-data",
        "images:images",
        "--add-data",
        "audio:audio",
        "--add-data",
        "data:data",
        "--osx-bundle-identifier",
        "com.paulp143.eagle1",
        "run_game.py",
    ]

    subprocess.run(pyinstaller_cmd, cwd=str(PROJECT_ROOT), check=True)

    # Step 3: Inject / Validate Retina & HIG settings in Info.plist
    info_plist_path = APP_BUNDLE / "Contents" / "Info.plist"
    if info_plist_path.exists():
        print(f"[package_macos] Configuring Retina & system settings in {info_plist_path}...")
        with open(info_plist_path, "rb") as f:
            plist_data = plistlib.load(f)

        plist_data["NSHighResolutionCapable"] = True
        plist_data["CFBundleDisplayName"] = "Eagle-1 64Bit"
        plist_data["CFBundleShortVersionString"] = "0.2.0"
        plist_data["CFBundleVersion"] = "0.2.0"
        plist_data["LSMinimumSystemVersion"] = "11.0"
        plist_data["NSRequiresAquaSystemAppearance"] = False

        with open(info_plist_path, "wb") as f:
            plistlib.dump(plist_data, f)

    # Step 4: Ad-Hoc Code Sign
    print("[package_macos] Applying ad-hoc code signature to bundle...")
    subprocess.run(["codesign", "--force", "--deep", "--sign", "-", str(APP_BUNDLE)], check=True)

    # Step 5: Build DMG
    print("[package_macos] Creating DMG installer image...")
    dmg_builder = PROJECT_ROOT / "tools" / "build_macos_dmg.py"
    subprocess.run([sys.executable, str(dmg_builder)], check=True)

    # Step 6: Create Portable ZIP
    zip_path = DIST_DIR / "Eagle-1-macOS.zip"
    if zip_path.exists():
        zip_path.unlink()
    print(f"[package_macos] Creating ZIP archive: {zip_path}...")
    subprocess.run(["zip", "-r", "-y", "Eagle-1-macOS.zip", "Eagle-1.app"], cwd=str(DIST_DIR), check=True)

    print("[package_macos] macOS distribution packaging complete!")
    print(f"  - App Bundle: {APP_BUNDLE}")
    print(f"  - DMG Image:  {DIST_DIR / 'Eagle-1-macOS.dmg'}")
    print(f"  - Zip Archive: {zip_path}")
    return 0


if __name__ == "__main__":
    sys.exit(package_macos())

