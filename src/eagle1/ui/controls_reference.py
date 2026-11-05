"""controls_reference.py - Single source of truth for key bindings shown in the UI.

Settings, Help and the in-game HUD hint all read from here so they can never disagree.
Bindings were verified against the event handling in ``eagle1.app.game``.
"""

from __future__ import annotations

from typing import List, NamedTuple, Tuple


class ControlBinding(NamedTuple):
    """One key binding row: key label, action description and category."""

    keys: str
    action: str
    category: str  # "FLIGHT" | "WEAPONS" | "STRATAGEMS" | "SYSTEM"


CONTROL_BINDINGS: Tuple[ControlBinding, ...] = (
    ControlBinding("W / S", "Throttle up / down", "FLIGHT"),
    ControlBinding("A / D", "Steer left / right", "FLIGHT"),
    ControlBinding("Q", "Toggle radar CONE / OMNI", "FLIGHT"),
    ControlBinding("SPACE / LMB", "Fire cannons / aim stratagem (hold, release)", "WEAPONS"),
    ControlBinding("E / F / LCTRL / RMB", "Fire homing rocket", "WEAPONS"),
    ControlBinding("1 – 5 / WHEEL", "Select slot (1 cannons, 2–5 stratagems)", "WEAPONS"),
    ControlBinding("C", "Call in equipped air strike", "STRATAGEMS"),
    ControlBinding("V / TAB", "Open air-strike arsenal", "STRATAGEMS"),
    ControlBinding("X", "Call supply drop", "STRATAGEMS"),
    ControlBinding("R", "Rearm at Super Destroyer", "STRATAGEMS"),
    ControlBinding("ARROWS", "Stratagem Hero inputs", "STRATAGEMS"),
    ControlBinding("ESC", "Cancel aiming / close menu", "SYSTEM"),
    ControlBinding("P", "Pause", "SYSTEM"),
    ControlBinding("O", "Settings", "SYSTEM"),
    ControlBinding("M", "Mute audio", "SYSTEM"),
)

CATEGORY_ORDER: Tuple[str, ...] = ("FLIGHT", "WEAPONS", "STRATAGEMS", "SYSTEM")

HUD_HINT_KEYS: Tuple[Tuple[str, str], ...] = (
    ("SPACE", "FIRE"),
    ("E", "ROCKET"),
    ("Q", "RADAR"),
    ("1-5", "SLOT"),
    ("C", "STRIKE"),
    ("X", "SUPPLY"),
    ("P", "PAUSE"),
)


def bindings_by_category(category: str) -> List[ControlBinding]:
    """Return the bindings of ``category`` in declaration order (unknown category -> [])."""
    return [b for b in CONTROL_BINDINGS if b.category == category]
