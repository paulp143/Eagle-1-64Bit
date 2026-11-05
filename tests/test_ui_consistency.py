"""Repository-wide UI consistency guards for the Military Terminal theme.

These tests scan the source tree so that new code cannot silently re-introduce per-file font
loading, rounded UI corners or glyphs that the bundled fonts cannot render.
"""

from pathlib import Path

from eagle1.ui import theme

SRC = Path(__file__).resolve().parent.parent / "src" / "eagle1"

# Glyphs missing from the bundled fonts (they render as tofu boxes): ◄ ► ★ ✖ ✚ ⚠
UNSUPPORTED_GLYPHS = "◄►★✖✚⚠"

ALLOWED_SYSFONT = {
    Path("ui/theme.py"),      # fallback chain for a missing bundled font
    Path("app/game.py"),      # legacy safe_font() helper kept for compatibility
}


def _python_files():
    return sorted(p for p in SRC.rglob("*.py") if "__pycache__" not in p.parts)


def test_no_sysfont_outside_theme():
    offenders = []
    for path in _python_files():
        rel = path.relative_to(SRC)
        text = path.read_text(encoding="utf-8")
        if ("SysFont(" in text or "font.Font(" in text) and rel not in ALLOWED_SYSFONT:
            offenders.append(str(rel))
    assert offenders == [], f"Create fonts through eagle1.ui.theme only: {offenders}"


def test_no_border_radius_in_ui_modules():
    guarded = list((SRC / "ui").glob("*.py")) + [
        SRC / "story" / "comms_hud.py",
        SRC / "story" / "super_destroyer_view.py",
        SRC / "story" / "cinematic_player.py",
    ]
    offenders = []
    for path in guarded:
        if path.name == "theme.py":
            continue  # the style guide docstring mentions the rule
        if "border_radius" in path.read_text(encoding="utf-8"):
            offenders.append(str(path.relative_to(SRC)))
    assert offenders == [], f"UI uses sharp corners only: {offenders}"


def test_no_unsupported_glyphs_in_source():
    offenders = []
    for path in _python_files():
        if path.name == "theme.py":
            continue  # documents the unsupported glyphs
        text = path.read_text(encoding="utf-8")
        found = sorted({c for c in UNSUPPORTED_GLYPHS if c in text})
        if found:
            offenders.append((str(path.relative_to(SRC)), found))
    assert offenders == [], f"Glyphs missing from the bundled fonts: {offenders}"


def test_type_scale_has_no_font_below_minimum():
    assert all(size >= theme.MIN_FONT_SIZE for _, size in theme.TYPE_SCALE.values())
