"""capture_screenshots.py - Render README screenshots headlessly from the real game code.

Usage (from the repository root):
    python tools/capture_screenshots.py [--out images/screenshots]

Every screen is drawn by the same functions the game loop uses, on the internal
1280x720 canvas, with dummy SDL drivers. User data is redirected to a temporary
directory so the real ``data/`` files (profile, saves, highscores) are never touched.
"""

from __future__ import annotations

import argparse
import os
import random
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
_TMP_DATA = tempfile.mkdtemp(prefix="eagle1-shots-")
os.environ["EAGLE1_USER_DATA_DIR"] = _TMP_DATA

import pygame  # noqa: E402

pygame.init()
pygame.display.set_mode((1280, 720))

from eagle1.app import game  # noqa: E402
from eagle1.systems.hangar_cinematic import ASCENT_DURATION  # noqa: E402

DEBRIEF_RESULTS = {
    "mission_name": "OPERATION: IRON COLOSSUS",
    "final_score": 48250,
    "highscore": 48250,
    "is_new_highscore": True,
    "duration_seconds": 742.0,
    "waves_cleared": 6,
    "aerial_kills": 64,
    "bomber_kills": 9,
    "cas_kills": 31,
    "fabricators_destroyed": 3,
    "strider_destroyed": True,
    "survivors_count": 3,
    "casualties_count": 1,
    "flawless_squad": False,
    "hull_ratio": 0.6,
    "hero_score": 700,
}


def _simulate(frames: int, fire: bool = True) -> None:
    """Advance the real gameplay simulation without input (cannons fire periodically)."""
    for i in range(frames):
        if fire and i % 12 == 0 and game.player.health > 0:
            game.player.shooting = True
        game.move()
        game.player.shooting = False
        game.player.health = max(game.player.health, 3)  # keep the pilot alive for the capture


def capture_all(out_dir: Path) -> list:
    out_dir.mkdir(parents=True, exist_ok=True)
    canvas = game.canvas
    saved = []

    def save(name: str) -> None:
        path = out_dir / f"{name}.png"
        pygame.image.save(canvas, str(path))
        saved.append(path)

    random.seed(7)
    game.profile_manager.create_profile("VAL", citizenship_grade="E")
    mouse_none = None

    # Main menu with an active service record
    game.game_state = "main_menu"
    game.main_menu(mouse_none)
    save("main_menu")

    # Enlistment contract
    game.enlistment_screen.reset()
    for ch in "VAL-KYRIE":
        game.enlistment_screen.handle_event(
            pygame.event.Event(pygame.KEYDOWN, key=0, unicode=ch, mod=0), None
        )
    game.enlistment_screen.draw(canvas, mouse_none)
    save("enlistment")

    # Mission select and stratagem loadout over the menu backdrop
    game.main_menu(mouse_none)
    game.mission_select_menu.draw(canvas, mouse_none)
    save("mission_select")

    game.main_menu(mouse_none)
    game.stratagem_select_menu.focus_index = 6  # show keyboard focus on a card outside the default loadout
    game.stratagem_select_menu.draw(canvas, mouse_none)
    save("stratagem_loadout")

    # Settings and tactical manual
    game.previous_game_state = "main_menu"
    for tab, name in ((1, "settings_gameplay"), (2, "settings_controls")):
        game.settings_menu.active_tab = tab
        game.main_menu(mouse_none)
        game.settings_menu.draw(canvas, mouse_none)
        save(name)
    game.settings_menu.active_tab = 0
    for tab, name in ((0, "manual_weapons"), (5, "manual_squad")):
        game.help_menu.set_tab(tab)
        game.main_menu(mouse_none)
        game.help_menu.draw(canvas, mouse_none)
        save(name)

    # Gameplay: Endless War with air and ground forces
    game.respawn(mission_config=game.MISSION_CONFIGS[game.MissionType.ENDLESS_WAR])
    game.game_state = ""
    _simulate(900)
    game.draw(mouse_none)
    save("gameplay_hud")

    # Air-strike arsenal overlay
    game.ground_support_manager.weapon_menu.is_open = True
    game.draw(mouse_none)  # the ground-support HUD draws the open arsenal overlay itself
    save("arsenal_menu")
    game.ground_support_manager.weapon_menu.is_open = False

    # Pause menu over the frozen frame
    game.draw(mouse_none)
    game._pause_snapshot_valid = False
    game.game_state = "pause_menu"
    game.pause_menu(mouse_none)
    save("pause_menu")
    game.resume_from_pause()

    # Super Destroyer rearm cinematic (hangar phase, crane lowering then wing service)
    sdm = game.ground_support_manager.super_destroyer
    sdm.start_rearm(game.player)
    sdm.update(ASCENT_DURATION + 0.01, game.player)
    for stamp, name in ((2.6, "rearm_hoist"), (5.8, "rearm_wing_service")):
        sdm.update(stamp - sdm.phase_timer, game.player)
        sdm.draw(canvas, game.GAME_WIDTH, game.GAME_HEIGHT, game.player)
        save(name)
    sdm.update(30.0, game.player)
    sdm.update(30.0, game.player)

    # Factory Strider boss raid
    game.respawn(mission_config=game.MISSION_CONFIGS[game.MissionType.STRIDER_RAID])
    _simulate(240)
    strider = game.ground_support_manager.factory_strider
    if strider is not None:
        game.player.pos_x, game.player.pos_y = strider.pos_x - 260.0, strider.pos_y + 220.0
        game.player.x, game.player.y = int(game.player.pos_x), int(game.player.pos_y)
        game.player.angle = 45.0
    _simulate(90)
    game.draw(mouse_none)
    save("strider_raid")

    # Mission debriefing
    game.debriefing_screen.set_results(DEBRIEF_RESULTS)
    game.draw(mouse_none)
    game.debriefing_screen.draw(canvas, mouse_none)
    save("debriefing")

    # Super Destroyer hub: hangar deck and an NPC dialogue
    game.enter_super_destroyer(DEBRIEF_RESULTS)
    view = game.super_destroyer_view
    for _ in range(90):
        view.update(1.0 / 60.0)
    view.draw(canvas, mouse_none)
    save("super_destroyer_bridge")
    if view.open_npc_dialogue("npc_reiner") is not None:
        for _ in range(600):  # let the typewriter finish
            view.update(1.0 / 60.0)
        view.draw(canvas, mouse_none)
        save("super_destroyer_dialogue")
    return saved


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", default=str(ROOT / "images" / "screenshots"))
    args = parser.parse_args()
    try:
        for path in capture_all(Path(args.out)):
            print(path.relative_to(ROOT) if path.is_relative_to(ROOT) else path)
    finally:
        pygame.quit()
        shutil.rmtree(_TMP_DATA, ignore_errors=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
