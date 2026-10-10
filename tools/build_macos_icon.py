#!/usr/bin/env python3
"""
build_macos_icon.py - Automated generation of Apple .icns application icons.

Uses macOS built-in tools (sips & iconutil) to convert Space-Invaders-Ship.png
into a multi-resolution Apple .icns icon bundle for macOS Finder and Dock.
"""

import shutil
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SOURCE_IMAGE = PROJECT_ROOT / "images" / "Space-Invaders-Ship.png"
OUTPUT_ICNS = PROJECT_ROOT / "images" / "Eagle-1.icns"

ICON_SIZES = [
    ("icon_16x16.png", 16),
    ("icon_16x16@2x.png", 32),
    ("icon_32x32.png", 32),
    ("icon_32x32@2x.png", 64),
    ("icon_128x128.png", 128),
    ("icon_128x128@2x.png", 256),
    ("icon_256x256.png", 256),
    ("icon_256x256@2x.png", 512),
    ("icon_512x512.png", 512),
    ("icon_512x512@2x.png", 1024),
]


def build_icon():
    if sys.platform != "darwin":
        print(f"[build_macos_icon] Skipping .icns build on non-macOS platform ({sys.platform}).")
        return 0

    if not SOURCE_IMAGE.is_file():
        print(f"[build_macos_icon] Error: Source image not found at {SOURCE_IMAGE}", file=sys.stderr)
        return 1

    iconset_dir = PROJECT_ROOT / "dist" / "Eagle-1.iconset"
    if iconset_dir.exists():
        shutil.rmtree(iconset_dir)
    iconset_dir.mkdir(parents=True, exist_ok=True)

    temp_squared = iconset_dir / "temp_squared.png"

    try:
        # Step 1: Make source image square using sips pad to largest dimension
        # Determine max dimension
        probe = subprocess.run(
            ["sips", "-g", "pixelWidth", "-g", "pixelHeight", str(SOURCE_IMAGE)],
            check=True,
            capture_output=True,
            text=True,
        )
        w, h = 611, 611
        for line in probe.stdout.splitlines():
            line = line.strip()
            if line.startswith("pixelWidth:"):
                w = int(line.split(":")[1].strip())
            elif line.startswith("pixelHeight:"):
                h = int(line.split(":")[1].strip())
        max_dim = max(w, h)

        subprocess.run(
            ["sips", "-p", str(max_dim), str(max_dim), str(SOURCE_IMAGE), "--out", str(temp_squared)],
            check=True,
            capture_output=True,
        )

        # Step 2: Generate each icon size in the iconset
        for filename, size in ICON_SIZES:
            target_path = iconset_dir / filename
            subprocess.run(
                ["sips", "-z", str(size), str(size), str(temp_squared), "--out", str(target_path)],
                check=True,
                capture_output=True,
            )

        if temp_squared.exists():
            temp_squared.unlink()

        # Step 3: Compile .iconset to .icns using iconutil
        OUTPUT_ICNS.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            ["iconutil", "-c", "icns", str(iconset_dir), "-o", str(OUTPUT_ICNS)],
            check=True,
            capture_output=True,
        )

        print(f"[build_macos_icon] Successfully generated {OUTPUT_ICNS} ({OUTPUT_ICNS.stat().st_size} bytes)")
        return 0

    except subprocess.CalledProcessError as e:
        print(f"[build_macos_icon] Error running icon tool: {e.stderr.decode() if e.stderr else e}", file=sys.stderr)
        return 1
    finally:
        if iconset_dir.exists():
            shutil.rmtree(iconset_dir, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(build_icon())

