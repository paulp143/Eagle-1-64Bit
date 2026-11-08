import math
import os
import random

import pygame

from eagle1.data.player_profile import PlayerProfileManager
from eagle1.effects import CombatJuiceManager, Large_explosion_a, Spritesheet
from eagle1.paths import PROJECT_ROOT, get_user_data_dir, image_search_dirs, verify_path_exact_casing
from eagle1.systems.audio_manager import get_audio_manager
from eagle1.systems.ground_support import (
    GroundSupportManager,
    PLAYER_STEERING_SLOW_MO_FACTOR,
    SLOW_MO_TIME_SCALE,
    SCORE_EXTRACTION_BONUS,
    StratagemSelectMenu,
)
from eagle1.systems import missile_defense
from eagle1.systems.powerups import (
    DAMAGE_BOOST_MULTIPLIER,
    RAPID_FIRE_COOLDOWN_MS,
    RAPID_FIRE_RELOAD_MS,
    SHIELD_BUBBLE_BONUS,
    PowerUpManager,
)
from eagle1.ui import hud_layout, theme, widgets
from eagle1.ui.hud import HudRenderer
from eagle1.ui.help_menu import HelpMenu
from eagle1.ui.lock_reticle import draw_lock_brackets
from eagle1.ui.mission_select_menu import MissionSelectMenu
from eagle1.ui.menu_nav import MenuButton, MenuNavigator, VARIANT_DANGER, VARIANT_PRIMARY
from eagle1.ui.settings_menu import SettingsMenu
from eagle1.ui.debriefing_screen import DebriefingScreen
from eagle1.ui.enlistment_screen import EnlistmentScreen
from eagle1.systems.academy_briefing import AcademyTutorialManager
from eagle1.systems.hangar_cinematic import (
    PHASE_ASCENT,
    PHASE_HANGAR,
    PHASE_DESCENT,
)
from eagle1.story import (
    CAMPAIGN_SORTIE_CONFIG_KEY,
    CampaignSortieSession,
    CommsHUD,
    StoryManager,
    SuperDestroyerView,
    build_campaign_mission_config,
)
from eagle1.story.campaign_act3 import (
    PLAYER_WEAPONS_DISARMED_ATTR,
    mark_campaign_finale_completed,
    restore_act3b_weapons,
)
from eagle1.story.cinematic_player import CINEMATIC_ACTION_RETURN_MAIN_MENU, CinematicPlayer

BASE_DIR = str(PROJECT_ROOT)
audio_manager = get_audio_manager()

GAME_WIDTH = 1280
GAME_HEIGHT = 720

MAP_WIDTH = 3000
MAP_HEIGHT = 3000

PLAYER_Y = 1470
PLAYER_X = 1476
PLAYER_WIDTH = 48
PLAYER_HEIGHT = 61
PLAYER_MAX_HEALTH = 5
PLAYER_MAX_BULLETS = 200
PLAYER_RELOAD_TIME = 5000
PLAYER_ATTACK_DAMAGE_KAMIKAZE = 25
PLAYER_INVINCIBLE_TIME = 1000
PLAYER_MAX_SHIELD = 20
PLAYER_MIN_SPEED = 2.0
PLAYER_MAX_SPEED = 7.0
CORNER_SPEED = 4.5
TURN_RATE_STALL_MULT = 0.80
TURN_RATE_CORNER_MULT = 1.35
TURN_RATE_MAX_SPEED_MULT = 0.75
PLAYER_MOVEMENT_SPEED_Y = PLAYER_MAX_SPEED / 2
PLAYER_MOVEMENT_SPEED_X = PLAYER_MAX_SPEED / 2
PLAYER_ACCELERATION = 0.15
PLAYER_TURN_RATE = 3.2
PLAYER_BULLET_DAMAGE = 1


def calculate_turn_rate(speed: float, base_turn_rate: float) -> float:
    """Compute effective angular turn rate using a Corner Speed aerodynamic curve.

    - At stall speed (<= PLAYER_MIN_SPEED = 2.0): multiplier is 0.80 (sluggish authority).
    - At corner speed (CORNER_SPEED = 4.5): multiplier peaks at 1.35 (maximum bite).
    - At max speed (>= PLAYER_MAX_SPEED = 7.0): multiplier drops to 0.75 (high-G wide radius).
    """
    spd = float(speed)
    if spd <= PLAYER_MIN_SPEED:
        mult = TURN_RATE_STALL_MULT
    elif spd <= CORNER_SPEED:
        t = (spd - PLAYER_MIN_SPEED) / (CORNER_SPEED - PLAYER_MIN_SPEED)
        mult = TURN_RATE_STALL_MULT + t * (TURN_RATE_CORNER_MULT - TURN_RATE_STALL_MULT)
    elif spd <= PLAYER_MAX_SPEED:
        t = (spd - CORNER_SPEED) / (PLAYER_MAX_SPEED - CORNER_SPEED)
        mult = TURN_RATE_CORNER_MULT - t * (TURN_RATE_CORNER_MULT - TURN_RATE_MAX_SPEED_MULT)
    else:
        over_t = min(1.0, (spd - PLAYER_MAX_SPEED) / 3.0)
        mult = TURN_RATE_MAX_SPEED_MULT - over_t * 0.10
    return float(base_turn_rate) * mult


COLLISION_COOLDOWN_MS = 500


def calculate_directional_gun_damage(
    base_damage: float,
    bullet_dx: float,
    bullet_dy: float,
    enemy_angle: float,
) -> float:
    """Calculate aspect-angle gun damage against an aerial fighter.

    Enemy forward unit vector is (sin(rad), cos(rad)).
    - Dot product >= +0.35 (rear ~140° tail cone / engines): 1.50x critical damage.
    - Dot product <= -0.50 (frontal 120° nose armor): 0.50x deflected damage.
    - Side / beam aspect (-0.50 < dot < +0.35): 1.15x fuselage damage.
    """
    b_mag = math.hypot(bullet_dx, bullet_dy)
    if b_mag < 1e-6:
        return float(base_damage)
    bx = bullet_dx / b_mag
    by = bullet_dy / b_mag

    rad = math.radians(enemy_angle)
    ex = math.sin(rad)
    ey = math.cos(rad)

    dot = bx * ex + by * ey
    if dot >= 0.35:
        return float(base_damage) * 1.50
    elif dot <= -0.50:
        return float(base_damage) * 0.50
    else:
        return float(base_damage) * 1.15


def compute_bfm_evade_sign(
    dx: float,
    dy: float,
    p_fx: float,
    p_fy: float,
    p_speed: float,
    default_dir: int = 1,
) -> int:
    """Return +1 or -1 to steer away from the player's projected flight path."""
    los_angle = math.degrees(math.atan2(dx, dy))
    fut_dx = dx + p_fx * (p_speed * 18.0)
    fut_dy = dy + p_fy * (p_speed * 18.0)
    rad_pos = math.radians(los_angle + 80.0)
    rad_neg = math.radians(los_angle - 80.0)
    step = CORNER_SPEED * 18.0
    dist_pos = math.hypot(fut_dx - math.sin(rad_pos) * step, fut_dy - math.cos(rad_pos) * step)
    dist_neg = math.hypot(fut_dx - math.sin(rad_neg) * step, fut_dy - math.cos(rad_neg) * step)
    if abs(dist_pos - dist_neg) > 6.0:
        return 1 if dist_pos > dist_neg else -1
    return 1 if default_dir >= 0 else -1


def resolve_aerial_collision(player_obj, enemy_obj, current_time_ms=None):
    """Resolve a mid-air collision as mutual hull trauma without any physical knockback.

    Deals lethal kamikaze impact damage to one-hit destroy standard enemy aircraft on ramming.
    Neither craft is displaced and the player keeps speed and heading: aircraft do not bounce
    off each other. The per-enemy collision cooldown prevents multi-frame damage grinding while
    the hulls still overlap.
    """
    now = current_time_ms if current_time_ms is not None else pygame.time.get_ticks()
    last_hit = getattr(enemy_obj, "last_collision_time", -99999)

    if now - last_hit >= COLLISION_COOLDOWN_MS:
        enemy_obj.last_collision_time = now
        enemy_obj.health -= getattr(player_obj, "kamikaze_attack_damage", PLAYER_ATTACK_DAMAGE_KAMIKAZE)
        player_obj.take_damage(12.0)
        return True
    return False

BULLET_WIDTH = 9
BULLET_HEIGHT = 12
BULLET_VELOCITY_Y = 9.5
BULLET_MAX_RANGE = 460.0
BULLET_UI_WIDTH = BULLET_WIDTH / 2  # 4 px
BULLET_UI_HEIGHT = BULLET_HEIGHT / 2
BULLET_SHOOTING_TIMER = 100

# Raketen-Parameter (Homing Rocket System)
ROCKET_WIDTH = 12
ROCKET_HEIGHT = 16
ROCKET_VELOCITY = 11.5
ROCKET_TURN_RATE = 5.5
ROCKET_DAMAGE = 20
ROCKET_SHOOTING_TIMER = 350
ROCKET_MAX_FLIGHT_TIME = 2500  
ROCKET_MAX_RANGE = 1200       

# Radar & Lock-on Modi
RADAR_CONE_ANGLE = 50          
RADAR_CONE_RANGE = 1050
RADAR_CONE_MIN_RANGE = 300        
RADAR_OMNI_RANGE = 420

PLAYER_MAX_ROCKETS = 4
PLAYER_ROCKET_RELOAD_TIME = 12000


def calculate_missile_intercept_point(rx: float, ry: float, r_speed: float, target) -> tuple:
    """Compute predicted lead-intercept point for a homing missile against a moving target."""
    tx = float(getattr(target, "pos_x", getattr(target, "x", 0.0))) + getattr(target, "width", LIGHT_ENEMY_WIDTH) / 2.0
    ty = float(getattr(target, "pos_y", getattr(target, "y", 0.0))) + getattr(target, "height", LIGHT_ENEMY_HEIGHT) / 2.0

    dist = math.hypot(tx - rx, ty - ry)
    t_intercept = min(35.0, dist / max(1.0, float(r_speed)))

    velocity = getattr(target, "velocity", None)
    if isinstance(velocity, tuple) and len(velocity) == 2:
        # Explicit world-space velocity (bombers, flares) is convention-independent
        v_tx, v_ty = float(velocity[0]), float(velocity[1])
    else:
        t_speed = float(getattr(target, "speed", 0.0))
        if t_speed > 0.0 and hasattr(target, "angle"):
            t_rad = math.radians(float(target.angle))
            v_tx = math.sin(t_rad) * t_speed
            v_ty = math.cos(t_rad) * t_speed
        else:
            v_tx = 0.0
            v_ty = 0.0

    return (tx + v_tx * t_intercept, ty + v_ty * t_intercept)

SHIELD_UI_WIDTH = 12
SHIELD_UI_HEIGHT = 8
SHIELD_REGENERATION_TIME = 2000

BORDER_TICK_DAMAGE = 0.1

LIGHT_ENEMY_WIDTH = 50
LIGHT_ENEMY_HEIGHT = 46
LIGHT_ENEMY_HEALTH = 20
LIGHT_ENEMY_EXPLOSION_DAMAGE = 5
LIGHT_ENEMY_EXPLOSION_WIDTH = 50
LIGHT_ENEMY_EXPLOSION_HEIGHT = 46
LIGHT_ENEMY_EXPLOSION_TIME = 500
LIGHT_ENEMY_BULLET_VELOCITY_Y = 5
LIGHT_ENEMY_BULLET_SPEED = 5.0
LIGHT_ENEMY_BULLET_DAMAGE = 1
LIGHT_ENEMY_SPEED = 2.5
LIGHT_ENEMY_TURN_RATE = 1.55
LIGHT_ENEMY_ALIGNMENT_THRESHOLD = 15.0
LIGHT_ENEMY_VELOCITY_X = 2
LIGHT_ENEMY_VELOCITY_Y = 2
LIGHT_ENEMY_DROP_CHANCES = 40

MAX_WAVE_LEVEL = 10
MAX_ENEMIES_PER_WAVE = 8
ENEMY_AGRO_RADIUS = 1000.0
ENEMY_DEAGRO_RADIUS = 1500.0
ENEMY_PATROL_SPEED = 2.0
ENEMY_AGRO_SPEED = 3.2
ENEMY_SEPARATION_RADIUS = 70.0
ENEMY_FORMATION_SPACING = 90.0
WAVE_INTERMISSION_TIME = 3000
ADRENALINE_HEALTH_THRESHOLD = 2

MINIMAP_SIZE = 160
MINIMAP_SCALE = MINIMAP_SIZE / MAP_WIDTH
MINIMAP_BG_WIDTH = int(GAME_WIDTH * MINIMAP_SCALE)
MINIMAP_BG_HEIGHT = int(GAME_HEIGHT * MINIMAP_SCALE)

FRAME_MULTIPLIKATOR = 2
FRAME_SPEED = 0.4

HEALTH_WIDTH = 16
HEALTH_HEIGHT = 4


HIGHSCORE_FILE = os.path.join(str(get_user_data_dir()), "highscore.txt")


def load_image(image_path, scale=None, colorkey=None):
    if os.path.isabs(image_path) and os.path.exists(image_path):
        if not verify_path_exact_casing(image_path):
            raise FileNotFoundError(f"Image case mismatch for: {image_path}")
        image = pygame.image.load(image_path)
    else:
        basename = os.path.basename(image_path)
        rel_path = image_path.replace("\\", "/")
        if rel_path.startswith("images/"):
            rel_path = rel_path[len("images/"):]

        candidates = [
            os.path.join(BASE_DIR, image_path),
            os.path.join(BASE_DIR, rel_path),
            os.path.join(os.getcwd(), image_path),
            os.path.join(os.getcwd(), "images", basename),
        ]

        for image_dir in image_search_dirs():
            candidates.extend([
                os.path.join(str(image_dir), rel_path),
                os.path.join(str(image_dir), basename),
            ])

        found = next((path for path in candidates if os.path.exists(path) and verify_path_exact_casing(path)), None)
        if found is None:
            raise FileNotFoundError(f"Image not found: {image_path}")
        image = pygame.image.load(found)

    if colorkey is not None:
        image.set_colorkey(colorkey)
        alpha_surf = pygame.Surface(image.get_size(), pygame.SRCALPHA)
        alpha_surf.blit(image, (0, 0))
        image = alpha_surf
    if scale is not None:
        image = pygame.transform.scale(image, scale)
    if pygame.display.get_surface() is not None:
        if (
            colorkey is not None
            or (image.get_flags() & pygame.SRCALPHA)
            or (len(image.get_masks()) >= 4 and image.get_masks()[3] != 0)
        ):
            image = image.convert_alpha()
        else:
            image = image.convert()
    return image


def load_highscore(filepath=HIGHSCORE_FILE):
    try:
        with open(filepath, "r") as file:
            return int(file.read().strip())
    except (FileNotFoundError, ValueError):
        return 0


def add_highscore(new_highscore, filepath=HIGHSCORE_FILE):
    try:
        val = max(0, int(new_highscore))
        dir_name = os.path.dirname(filepath)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)
        tmp_filepath = f"{filepath}.tmp"
        with open(tmp_filepath, "w", encoding="utf-8") as file:
            file.write(str(val))
        os.replace(tmp_filepath, filepath)
    except Exception as e:
        print(f"Error saving highscore: {e}")

class TextBox:
    """Wiederverwendbare Klasse für UI-Texte und klickbare Knöpfe mit Hover-Effekten."""
    def __init__(
        self,
        text,
        font,
        text_color=(255, 255, 255),
        bg_color=None,
        hover_bg_color=None,
        padding=(20, 10),
        border_radius=8,
        border_color=None,
        hover_border_color=None,
        border_width=2,
        enabled=True,
        disabled_text_color=(120, 130, 145),
        disabled_bg_color=(25, 28, 35),
        disabled_border_color=(50, 55, 65),
        **rect_kwargs
    ):
        self.text = str(text)
        self.font = font
        self.text_color = text_color
        self.bg_color = bg_color
        self.hover_bg_color = hover_bg_color
        self.padding = padding
        self.border_radius = border_radius
        self.border_color = border_color
        self.hover_border_color = hover_border_color
        self.border_width = border_width
        self.enabled = enabled
        self.disabled_text_color = disabled_text_color
        self.disabled_bg_color = disabled_bg_color
        self.disabled_border_color = disabled_border_color
        self.rect_kwargs = rect_kwargs
        self.update_surface()

    def update_surface(self):
        color = self.text_color if self.enabled else self.disabled_text_color
        self.text_surface = self.font.render(self.text, True, color)
        self.text_rect = self.text_surface.get_rect(**self.rect_kwargs)
        if self.bg_color is not None or self.border_color is not None or self.hover_bg_color is not None or self.hover_border_color is not None:
            self.bg_rect = self.text_rect.inflate(self.padding[0], self.padding[1])
        else:
            self.bg_rect = self.text_rect.copy()

    def set_text(self, new_text):
        new_text = str(new_text)
        if new_text != self.text:
            self.text = new_text
            self.update_surface()

    def set_enabled(self, enabled: bool):
        if self.enabled != enabled:
            self.enabled = enabled
            self.update_surface()

    def get_hitbox(self):
        return self.bg_rect if self.bg_rect is not None else self.text_rect

    def is_hovered(self, mouse_pos):
        if not self.enabled or mouse_pos is None:
            return False
        return self.get_hitbox().collidepoint(mouse_pos)

    def is_clicked(self, event, mouse_pos):
        if not self.enabled:
            return False
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            clicked = self.is_hovered(mouse_pos)
            if clicked:
                audio_manager.play_sfx("ui_click")
            return clicked
        return False

    def draw(self, surface, mouse_pos=None):
        if not self.enabled:
            if self.disabled_bg_color and self.bg_rect:
                pygame.draw.rect(surface, self.disabled_bg_color, self.bg_rect, border_radius=self.border_radius)
            if self.disabled_border_color and self.bg_rect:
                pygame.draw.rect(surface, self.disabled_border_color, self.bg_rect, width=self.border_width, border_radius=self.border_radius)
            surface.blit(self.text_surface, self.text_rect)
            return

        hovered = self.is_hovered(mouse_pos)
        if hovered and not getattr(self, "was_hovered", False):
            audio_manager.play_sfx("ui_hover")
        self.was_hovered = hovered

        current_bg = self.hover_bg_color if (hovered and self.hover_bg_color) else self.bg_color
        if current_bg and self.bg_rect:
            pygame.draw.rect(surface, current_bg, self.bg_rect, border_radius=self.border_radius)

        current_border = self.hover_border_color if (hovered and self.hover_border_color) else self.border_color
        if current_border and self.bg_rect:
            pygame.draw.rect(surface, current_border, self.bg_rect, width=self.border_width, border_radius=self.border_radius)

        surface.blit(self.text_surface, self.text_rect)


player_image = load_image(os.path.join("images", "Space-Invaders-Ship.png"), (PLAYER_WIDTH, PLAYER_HEIGHT))
bullet_image = load_image(os.path.join("images", "bullet.png"), (BULLET_WIDTH, BULLET_HEIGHT))
rocket_image = load_image(os.path.join("images", "bullet.png"), (ROCKET_WIDTH, ROCKET_HEIGHT))
light_enemy_image = load_image(
    os.path.join("images", "enemy1.png"),
    (LIGHT_ENEMY_WIDTH, LIGHT_ENEMY_HEIGHT),
    colorkey=(255, 255, 255),
)
enemy_bullet_image = load_image(os.path.join("images", "enemy_bullet.png"), (BULLET_WIDTH, BULLET_HEIGHT))
main_menu_image = load_image(os.path.join("images", "20260820_085135933_iOS.webp"), (GAME_WIDTH, GAME_HEIGHT))
backround_image = load_image(os.path.join("images", "newbackround.png"), (GAME_WIDTH, GAME_HEIGHT))

minimap_bg_image = pygame.transform.scale(backround_image, (MINIMAP_BG_WIDTH, MINIMAP_BG_HEIGHT))
light_enemy_explosion_image = load_image(
    os.path.join("images", "light_enemy_explosion.png"),
    (LIGHT_ENEMY_WIDTH, LIGHT_ENEMY_HEIGHT),
)
health_image = load_image(
    os.path.join("images", "health.png"),
    (HEALTH_WIDTH, HEALTH_HEIGHT),
    colorkey=(0, 0, 0),
)
bullet_ui_image = load_image(os.path.join("images", "bullet_ui.png"), (BULLET_UI_WIDTH, BULLET_UI_HEIGHT))
large_explosion_a_spritesheet = Spritesheet(load_image(os.path.join("images", "LargeExplosionA_spritesheet.png")), 23)


def _set_display_mode(size, flags):
    if os.environ.get("SDL_VIDEODRIVER") == "dummy":
        return pygame.display.set_mode(size, flags)
    try:
        return pygame.display.set_mode(size, flags, vsync=1)
    except Exception:
        return pygame.display.set_mode(size, flags)


pygame.init()
try:
    if pygame.mixer.get_init():
        pygame.mixer.set_num_channels(16)
except Exception:
    pass
def safe_font(name, size, bold=False):
    try:
        return pygame.font.SysFont(name, size, bold=bold)
    except Exception:
        return pygame.font.Font(None, size)

font = theme.get_font("title") or safe_font("arial", 24, bold=True)
title_font = theme.get_font("display_xl") or safe_font("arial", 48, bold=True)
speed_font = theme.get_font("heading") or safe_font("arial", 18, bold=True)
hud_small_font = theme.get_font("label") or safe_font("arial", 13, bold=True)
ui_text_cache = widgets.TextCache(1024)
hud_renderer = HudRenderer(GAME_WIDTH, GAME_HEIGHT)
profile_manager = PlayerProfileManager()
clock = pygame.time.Clock()
window = _set_display_mode((GAME_WIDTH, GAME_HEIGHT), pygame.RESIZABLE)
# Explicit 32-bit RGBX surface with Amask=0 so macOS Cocoa never zeroes dstA when compositing overlapping SRCALPHA sprites
canvas = pygame.Surface((GAME_WIDTH, GAME_HEIGHT), 0, 32, (0x00FF0000, 0x0000FF00, 0x000000FF, 0))


def convert_all_game_assets():
    """Converts all textures to matching display pixel format with clean per-pixel alpha and opaque RGBX backgrounds."""
    global player_image, bullet_image, rocket_image, light_enemy_image
    global enemy_bullet_image, main_menu_image, backround_image
    global minimap_bg_image, light_enemy_explosion_image, health_image
    global bullet_ui_image, large_explosion_a_spritesheet

    if pygame.display.get_surface() is None:
        return

    player_image = player_image.convert_alpha()
    bullet_image = bullet_image.convert_alpha()
    rocket_image = rocket_image.convert_alpha()
    light_enemy_image = light_enemy_image.convert_alpha()
    enemy_bullet_image = enemy_bullet_image.convert_alpha()
    main_menu_image = main_menu_image.convert(canvas)
    backround_image = backround_image.convert(canvas)
    minimap_bg_image = minimap_bg_image.convert(canvas)
    light_enemy_explosion_image = light_enemy_explosion_image.convert_alpha()
    health_image = health_image.convert_alpha()
    bullet_ui_image = bullet_ui_image.convert_alpha()

    if hasattr(large_explosion_a_spritesheet, "frames"):
        large_explosion_a_spritesheet.frames = [f.convert_alpha() for f in large_explosion_a_spritesheet.frames]

    if "player" in globals() and player is not None:
        player.original_image = player_image


convert_all_game_assets()
frame_number = 23
frame_width = large_explosion_a_spritesheet.sheet.get_width() / 23
frame_height = large_explosion_a_spritesheet.sheet.get_height()
game_state = "main_menu"
pygame.display.set_caption("Eagle 1 64Bit")

powerup_manager = PowerUpManager()
ground_support_manager = GroundSupportManager()
help_menu = HelpMenu(GAME_WIDTH, GAME_HEIGHT)
settings_menu = SettingsMenu(GAME_WIDTH, GAME_HEIGHT)
debriefing_screen = DebriefingScreen(GAME_WIDTH, GAME_HEIGHT, audio_manager=audio_manager)
enlistment_screen = EnlistmentScreen(GAME_WIDTH, GAME_HEIGHT)
academy_manager = AcademyTutorialManager()
previous_game_state = "main_menu"

# Mission Performance Tracking Variables
mission_start_time = pygame.time.get_ticks()
mission_air_kills = 0
mission_bomber_kills = 0

# =====================================================================
# MISSION SELECTION SYSTEM & FOCUSED OPERATION CONFIGURATIONS
# =====================================================================

class MissionType:
    ACADEMY_TUTORIAL = "academy_tutorial"
    AIR_SUPERIORITY = "air_superiority"
    BASE_DEFENSE = "base_defense"
    STRIDER_RAID = "strider_raid"
    OUTPOST_DEMOLITION = "outpost_demolition"
    ENDLESS_WAR = "endless_war"

MISSION_CONFIGS = {
    MissionType.ACADEMY_TUTORIAL: {
        "id": MissionType.ACADEMY_TUTORIAL,
        "name": "SUPER EARTH NAVAL ACADEMY",
        "category": "TRAINING OPERATIONS",
        "desc": "Basic Flight Certification & Close Air Support Qualification under Commander Vance.",
        "difficulty": "TRAINING",
        "has_ground": False,
        "has_fabricators": False,
        "has_strider": False,
        "has_bombers": False,
        "has_base": False,
        "max_waves": 1,
        "icon_color": (255, 215, 0),
    },
    MissionType.AIR_SUPERIORITY: {
        "id": MissionType.AIR_SUPERIORITY,
        "name": "AIR SUPERIORITY",
        "category": "AERIAL OPERATIONS",
        "desc": "Hold the airspace against 5 waves of Automaton fighter squadrons. Ground hostiles disabled.",
        "difficulty": "MEDIUM",
        "has_ground": False,
        "has_fabricators": False,
        "has_strider": False,
        "has_bombers": False,
        "has_base": False,
        "max_waves": 5,
        "icon_color": (0, 220, 255)
    },
    MissionType.BASE_DEFENSE: {
        "id": MissionType.BASE_DEFENSE,
        "name": "ORBITAL BASE DEFENSE",
        "category": "AERIAL OPERATIONS",
        "desc": "Protect the orbital defense station against waves of heavy Automaton Bombers.",
        "difficulty": "HARD",
        "has_ground": False,
        "has_fabricators": False,
        "has_strider": False,
        "has_bombers": True,
        "has_base": True,
        "max_waves": 5,
        "icon_color": (255, 140, 0)
    },
    MissionType.STRIDER_RAID: {
        "id": MissionType.STRIDER_RAID,
        "name": "FACTORY STRIDER RAID",
        "category": "GROUND OPERATIONS",
        "desc": "Support Helldivers to destroy a colossal 6-legged Factory Strider walking fortress.",
        "difficulty": "EXTREME",
        "has_ground": True,
        "has_fabricators": False,
        "has_strider": True,
        "has_bombers": False,
        "has_base": False,
        "max_waves": 1,
        "icon_color": (255, 60, 60)
    },
    MissionType.OUTPOST_DEMOLITION: {
        "id": MissionType.OUTPOST_DEMOLITION,
        "name": "OUTPOST DEMOLITION",
        "category": "GROUND OPERATIONS",
        "desc": "Demolish 3 Automaton Fabricator foundries and evacuate via Pelican-1.",
        "difficulty": "HARD",
        "has_ground": True,
        "has_fabricators": True,
        "has_strider": False,
        "has_bombers": False,
        "has_base": False,
        "max_waves": 6,
        "target_fabs": 3,
        "icon_color": (255, 215, 0)
    },
    MissionType.ENDLESS_WAR: {
        "id": MissionType.ENDLESS_WAR,
        "name": "ENDLESS WAR",
        "category": "TOTAL COMBAT",
        "desc": "Combined full-scale operation featuring waves, Helldivers, fabricators, and air strikes.",
        "difficulty": "CHALLENGING",
        "has_ground": True,
        "has_fabricators": True,
        "has_strider": False,
        "has_bombers": False,
        "has_base": False,
        "max_waves": 999,
        "icon_color": (180, 100, 255)
    }
}

active_mission_config = MISSION_CONFIGS[MissionType.ENDLESS_WAR]


class BomberEnemy(pygame.Rect):
    """Heavy Automaton aerial bomber targeting friendly orbital bases or structures."""
    is_air_target = True

    def __init__(self, x=None, y=None):
        rx = x if x is not None else random.randint(300, MAP_WIDTH - 300)
        ry = y if y is not None else -80.0
        pygame.Rect.__init__(self, int(rx), int(ry), 64, 52)
        self.pos_x = float(rx)
        self.pos_y = float(ry)
        self.speed = 1.8
        self.max_health = 75.0
        self.health = 75.0
        self.exploding = False
        self.score_value = 150
        self.angle = 180.0
        self.bullet_damage = 15.0
        self.velocity = (0.0, 0.0)
        self.flares_remaining = missile_defense.BOMBER_FLARES
        self.flare_deploy_chance = missile_defense.BOMBER_FLARE_DEPLOY_CHANCE

    def update(self, target_pos=(1500, 1500), speed_factor=1.0):
        if self.exploding:
            return
        tx, ty = target_pos
        dx = tx - (self.pos_x + 32)
        dy = ty - (self.pos_y + 26)
        dist = max(1.0, math.hypot(dx, dy))

        desired_angle = math.degrees(math.atan2(-dx, -dy)) % 360
        self.angle = desired_angle

        self.velocity = ((dx / dist) * self.speed * speed_factor, (dy / dist) * self.speed * speed_factor)
        self.pos_x += self.velocity[0]
        self.pos_y += self.velocity[1]
        self.x = int(self.pos_x)
        self.y = int(self.pos_y)

    def draw(self, surface, camera_x, camera_y):
        if self.exploding:
            return
        sx = self.pos_x - camera_x
        sy = self.pos_y - camera_y
        if -100 <= sx <= GAME_WIDTH + 100 and -100 <= sy <= GAME_HEIGHT + 100:
            surf = pygame.Surface((64, 52), pygame.SRCALPHA)
            pygame.draw.polygon(surf, (35, 40, 55), [(32, 0), (64, 40), (48, 52), (16, 52), (0, 40)])
            pygame.draw.polygon(surf, (255, 60, 40), [(32, 0), (64, 40), (48, 52), (16, 52), (0, 40)], 2)
            pulse = int(180 + 75 * math.sin(pygame.time.get_ticks() * 0.01))
            pygame.draw.circle(surf, (255, pulse // 3, 20), (32, 28), 6)
            rot_surf = pygame.transform.rotate(surf, self.angle)
            rect = rot_surf.get_rect(center=(sx + 32, sy + 26))
            surface.blit(rot_surf, rect.topleft)
            # Health Bar
            bar_w = 48
            bx = sx + 8
            by = sy - 8
            pygame.draw.rect(surface, (15, 20, 30), (bx, by, bar_w, 4))
            hp_w = max(0, int((self.health / self.max_health) * bar_w))
            pygame.draw.rect(surface, (255, 60, 60), (bx, by, hp_w, 4))


class OrbitalBase(pygame.Rect):
    """Stationary friendly orbital command base structure."""
    def __init__(self, x=1500, y=1500):
        pygame.Rect.__init__(self, int(x - 60), int(y - 60), 120, 120)
        self.pos_x = float(x - 60)
        self.pos_y = float(y - 60)
        self.max_health = 300.0
        self.health = 300.0
        self.max_shield = 100.0
        self.shield = 100.0

    @property
    def is_alive(self):
        return self.health > 0

    def take_damage(self, amount):
        if self.shield > 0:
            if self.shield >= amount:
                self.shield -= amount
                return
            else:
                amount -= self.shield
                self.shield = 0.0
        self.health = max(0.0, self.health - amount)

    def draw(self, surface, camera_x, camera_y, font):
        sx = self.pos_x - camera_x
        sy = self.pos_y - camera_y
        if -200 <= sx <= GAME_WIDTH + 200 and -200 <= sy <= GAME_HEIGHT + 200:
            cx, cy = sx + 60, sy + 60
            if self.shield > 0:
                pygame.draw.circle(surface, (0, 220, 255), (int(cx), int(cy)), 75, 2)
            pygame.draw.circle(surface, (28, 35, 50), (int(cx), int(cy)), 55)
            pygame.draw.circle(surface, (0, 220, 255), (int(cx), int(cy)), 55, 3)
            pygame.draw.circle(surface, (60, 80, 110), (int(cx), int(cy)), 30)
            angle = pygame.time.get_ticks() * 0.05
            rad = math.radians(angle)
            rx = cx + math.cos(rad) * 45
            ry = cy + math.sin(rad) * 45
            pygame.draw.line(surface, (0, 255, 180), (cx, cy), (rx, ry), 2)
            bar_w = 100
            bx = cx - 50
            by = sy - 18
            pygame.draw.rect(surface, (15, 20, 30), (bx, by, bar_w, 6))
            hp_w = max(0, int((self.health / self.max_health) * bar_w))
            pygame.draw.rect(surface, (46, 204, 113), (bx, by, hp_w, 6))
            if self.shield > 0:
                sh_w = max(0, int((self.shield / self.max_shield) * bar_w))
                pygame.draw.rect(surface, (0, 220, 255), (bx, by - 4, sh_w, 3))


mission_select_menu = MissionSelectMenu(
    MISSION_CONFIGS,
    [
        MissionType.AIR_SUPERIORITY,
        MissionType.BASE_DEFENSE,
        MissionType.STRIDER_RAID,
        MissionType.OUTPOST_DEMOLITION,
        MissionType.ENDLESS_WAR,
    ],
    GAME_WIDTH,
    GAME_HEIGHT,
    on_sfx=audio_manager.play_sfx,
)
stratagem_select_menu = StratagemSelectMenu()
pending_mission_config = None
bomber_enemies = []
active_flares = []
orbital_base = None

def get_display_scale_and_offset():
    """Berechnet Skalierungsfaktor und Zentrierungs-Offset für seitenverhältnistreue Darstellung (Letterboxing)."""
    win_w, win_h = window.get_size()
    if win_w == 0 or win_h == 0:
        return 1.0, 0, 0, GAME_WIDTH, GAME_HEIGHT
    scale = min(win_w / GAME_WIDTH, win_h / GAME_HEIGHT)
    scaled_w = max(1, int(GAME_WIDTH * scale))
    scaled_h = max(1, int(GAME_HEIGHT * scale))
    offset_x = (win_w - scaled_w) // 2
    offset_y = (win_h - scaled_h) // 2
    return scale, offset_x, offset_y, scaled_w, scaled_h


def get_canvas_mouse_pos():
    """Skaliert die Mauskoordinaten des Fensters auf die interne Canvas-Auflösung unter Berücksichtigung von Letterboxing."""
    scale, offset_x, offset_y, _, _ = get_display_scale_and_offset()
    if scale <= 0:
        return pygame.mouse.get_pos()
    mx, my = pygame.mouse.get_pos()
    canvas_x = (mx - offset_x) / scale
    canvas_y = (my - offset_y) / scale
    canvas_x = max(0.0, min(float(GAME_WIDTH), canvas_x))
    canvas_y = max(0.0, min(float(GAME_HEIGHT), canvas_y))
    return (canvas_x, canvas_y)


# --- Main menu (Military Terminal) ---
_MAIN_MENU_BTN_X = 96
_MAIN_MENU_BTN_W = 368
_MAIN_MENU_BTN_Y0 = 228
_MAIN_MENU_BTN_GAP = 12


def _main_menu_button(index, text, hotkey, variant=None, **kwargs):
    rect = pygame.Rect(
        _MAIN_MENU_BTN_X,
        _MAIN_MENU_BTN_Y0 + index * (48 + _MAIN_MENU_BTN_GAP),
        _MAIN_MENU_BTN_W,
        48,
    )
    return MenuButton(
        text,
        rect,
        hotkey=hotkey,
        variant=variant or "secondary",
        on_sfx=audio_manager.play_sfx,
        text_cache=ui_text_cache,
        **kwargs,
    )


menu_new_game_box = _main_menu_button(0, "NEW GAME", "N", VARIANT_PRIMARY)
menu_continue_box = _main_menu_button(1, "CONTINUE", "C")
menu_settings_box = _main_menu_button(2, "SETTINGS", "O")
menu_help_box = _main_menu_button(3, "TACTICAL MANUAL", "H")
menu_quit_box = _main_menu_button(4, "QUIT TO DESKTOP", "ESC", VARIANT_DANGER)

MAIN_MENU_ACTIONS = ("new_game", "continue", "settings", "help", "quit")
MAIN_MENU_QUIT_INDEX = 4
main_menu_nav = MenuNavigator(
    [menu_new_game_box, menu_continue_box, menu_settings_box, menu_help_box, menu_quit_box],
    wrap=True,
    on_sfx=audio_manager.play_sfx,
)

main_menu_side_overlay = widgets.make_overlay((560, GAME_HEIGHT), theme.OVERLAY_RGBA)
_mono_small_font = theme.get_font("mono_small") or hud_small_font
_mono_tiny_font = theme.get_font("mono_tiny") or hud_small_font
main_menu_title_surf = title_font.render("EAGLE-1", True, theme.ACCENT)
main_menu_subtitle_surf = _mono_small_font.render(
    "SUPER EARTH NAVAL AIR DIVISION // STORY CAMPAIGN", True, theme.TEXT_MUTED
)
main_menu_footer_surf = _mono_tiny_font.render("UP/DOWN NAVIGATE   ENTER SELECT", True, theme.TEXT_MUTED)
main_menu_hint_surf = _mono_small_font.render(
    "NO ACTIVE SERVICE RECORD — SELECT NEW GAME TO ENLIST", True, theme.WARNING
)
menu_toast_text = ""
menu_toast_until = 0

_menu_profile_state = {"key": None, "has_profile": False, "callsign": ""}


def invalidate_main_menu_profile_state():
    """Force the next main-menu frame to re-check the profile (e.g. when returning to the menu)."""
    _menu_profile_state["key"] = None


def _refresh_main_menu_profile_state():
    """Re-read the player profile only after it was saved or cleared (or the state was invalidated).

    Keyed on ``PlayerProfileManager.revision`` so the render loop does no per-frame file system access.
    """
    key = PlayerProfileManager.revision
    if key == _menu_profile_state["key"]:
        return
    has_profile = profile_manager.has_active_profile()
    _menu_profile_state["key"] = key
    _menu_profile_state["has_profile"] = has_profile
    _menu_profile_state["callsign"] = profile_manager.load_profile().username.upper() if has_profile else ""


# --- Pause menu & game-over screen (Military Terminal) ---
pause_panel_rect = pygame.Rect(GAME_WIDTH // 2 - 220, 170, 440, 380)
gameover_panel_rect = pygame.Rect(GAME_WIDTH // 2 - 220, 170, 440, 360)


def _panel_button(panel, y, text, hotkey, variant="secondary"):
    return MenuButton(
        text,
        pygame.Rect(panel.x + 36, y, panel.w - 72, 48),
        hotkey=hotkey,
        variant=variant,
        on_sfx=audio_manager.play_sfx,
        text_cache=ui_text_cache,
    )


pause_continue_box = _panel_button(pause_panel_rect, 260, "RESUME", "P", VARIANT_PRIMARY)
pause_help_box = _panel_button(pause_panel_rect, 320, "TACTICAL MANUAL", "H")
pause_settings_box = _panel_button(pause_panel_rect, 380, "SETTINGS", "O")
pause_menu_box = _panel_button(pause_panel_rect, 440, "ABORT TO MAIN MENU", "ESC", VARIANT_DANGER)
PAUSE_ACTIONS = ("resume", "help", "settings", "main_menu")
pause_nav = MenuNavigator(
    [pause_continue_box, pause_help_box, pause_settings_box, pause_menu_box],
    wrap=True,
    on_sfx=audio_manager.play_sfx,
)

gameover_respawn_box = _panel_button(gameover_panel_rect, 280, "RESPAWN", "R", VARIANT_PRIMARY)
gameover_help_box = _panel_button(gameover_panel_rect, 340, "TACTICAL MANUAL", "H")
gameover_lobby_box = _panel_button(gameover_panel_rect, 400, "MAIN MENU", "SPACE", VARIANT_DANGER)
GAMEOVER_ACTIONS = ("respawn", "help", "main_menu")
gameover_nav = MenuNavigator(
    [gameover_respawn_box, gameover_help_box, gameover_lobby_box],
    wrap=True,
    on_sfx=audio_manager.play_sfx,
)

pause_dim_overlay = widgets.make_overlay((GAME_WIDTH, GAME_HEIGHT), theme.OVERLAY_LIGHT_RGBA)
# Frozen gameplay frame shown behind the pause menu (same RGBX format as the canvas).
pause_snapshot_surf = pygame.Surface((GAME_WIDTH, GAME_HEIGHT), 0, 32, (0x00FF0000, 0x0000FF00, 0x000000FF, 0))
_pause_snapshot_valid = False
pause_title_surf = (theme.get_font("title") or font).render("OPERATION PAUSED", True, theme.ACCENT)
gameover_title_surf = (theme.get_font("display") or title_font).render("SIGNAL LOST", True, theme.DANGER)
gameover_sub_surf = _mono_small_font.render("EAGLE-1 HAS GONE DOWN", True, theme.TEXT_MUTED)


# Pre-allocated transparent surfaces for HUD vignettes to eliminate 60 FPS allocations
vignette_health_surf = pygame.Surface((GAME_WIDTH, GAME_HEIGHT), pygame.SRCALPHA)
vignette_shield_surf = pygame.Surface((GAME_WIDTH, GAME_HEIGHT), pygame.SRCALPHA)


SHOOTING_END = pygame.USEREVENT + 1
ADD_SCORE = pygame.USEREVENT + 2
LIGHT_ENEMY_SHOOT = pygame.USEREVENT + 3
RELOAD_END = pygame.USEREVENT + 4
LIGHT_ENEMY_EXPLOSION = pygame.USEREVENT + 5
INVINCIBLE_END = pygame.USEREVENT + 6
SHIELD_REGENERATION = pygame.USEREVENT + 7
ROCKET_SHOOTING_END = pygame.USEREVENT + 8
ROCKET_RELOAD_END = pygame.USEREVENT + 9

pygame.time.set_timer(ADD_SCORE, 1000)
pygame.time.set_timer(LIGHT_ENEMY_SHOOT, 1200)
pygame.time.set_timer(SHIELD_REGENERATION, SHIELD_REGENERATION_TIME)


class Player(pygame.Rect):
    class Bullet(pygame.Rect):
        def __init__(self, x, y, angle=0):
            pygame.Rect.__init__(self, int(x), int(y), BULLET_WIDTH, BULLET_HEIGHT)
            self.pos_x = float(x)
            self.pos_y = float(y)
            self.angle = angle
            self.image = pygame.transform.rotate(bullet_image, angle)
            self.used = False
            self.speed = BULLET_VELOCITY_Y
            self.max_range = float(BULLET_MAX_RANGE)
            self.distance_traveled = 0.0
            rad = math.radians(angle)
            self.dx = -math.sin(rad) * self.speed
            self.dy = -math.cos(rad) * self.speed

        def update_position(self):
            self.pos_x += self.dx
            self.pos_y += self.dy
            self.x = int(self.pos_x)
            self.y = int(self.pos_y)
            self.distance_traveled += self.speed
            if self.distance_traveled >= self.max_range:
                self.used = True

    class Rocket(pygame.Rect):
        """Zielsuchende Rakete mit sanfter Drehphysik (turn_rate=2.0) und maximaler Flugzeit."""
        def __init__(self, x, y, angle=0, target=None):
            pygame.Rect.__init__(self, int(x), int(y), ROCKET_WIDTH, ROCKET_HEIGHT)
            self.pos_x = float(x)
            self.pos_y = float(y)
            self.angle = float(angle)
            self.speed = float(ROCKET_VELOCITY)
            self.turn_rate = float(ROCKET_TURN_RATE)  # 2.0°/Frame
            self.damage = ROCKET_DAMAGE
            self.max_range = float(ROCKET_MAX_RANGE)
            self.spawn_time = pygame.time.get_ticks()
            self.max_flight_time = ROCKET_MAX_FLIGHT_TIME  # 2.5 Sekunden
            self.distance_traveled = 0.0
            self.target = target
            self.decoyed = False
            self.countermeasure_rolled = False
            self.evasion_rolled = False
            self.used = False
            self.original_image = rocket_image
            self.image = pygame.transform.rotate(self.original_image, self.angle)
            rad = math.radians(self.angle)
            self.dx = -math.sin(rad) * self.speed
            self.dy = -math.cos(rad) * self.speed

        def lock_on(self, targets, player=None):
            """Sucht das nächstgelegene lebendige Ziel im aktiven Radarbereich."""
            if isinstance(targets, (list, tuple, pygame.sprite.Group)):
                candidates = [
                    t for t in targets 
                    if t is not None and not getattr(t, 'exploding', False) and getattr(t, 'health', 1) > 0
                ]
            elif targets is not None and not getattr(targets, 'exploding', False) and getattr(targets, 'health', 1) > 0:
                candidates = [targets]
            else:
                candidates = []
            candidates = [t for t in candidates if missile_defense.is_air_target(t)]

            if not candidates:
                self.target = None
                return

            cx = self.pos_x + ROCKET_WIDTH / 2
            cy = self.pos_y + ROCKET_HEIGHT / 2

            valid_candidates = []
            for t in candidates:
                if player is not None and not player.is_enemy_in_lock_zone(t):
                    continue

                tx = t.x + getattr(t, 'width', LIGHT_ENEMY_WIDTH) / 2
                ty = t.y + getattr(t, 'height', LIGHT_ENEMY_HEIGHT) / 2
                diff_x = tx - cx
                diff_y = ty - cy
                dist = math.hypot(diff_x, diff_y)

                desired_angle = math.degrees(math.atan2(-diff_x, -diff_y)) % 360
                angle_diff = abs((desired_angle - self.angle + 180) % 360 - 180)
                if angle_diff <= 75:
                    valid_candidates.append((dist, t))

            if valid_candidates:
                valid_candidates.sort(key=lambda x: x[0])
                self.target = valid_candidates[0][1]
            else:
                self.target = None

        def update_position(self, targets=None, player=None):
            """Aktualisiert Flugzeit, Distanz, sanfte Drehung und Position."""
            if pygame.time.get_ticks() - self.spawn_time >= self.max_flight_time:
                self.used = True
                return

            self.distance_traveled += self.speed
            if self.distance_traveled >= self.max_range:
                self.used = True
                return

            if targets is not None and not self.decoyed:
                if not self.target or getattr(self.target, 'exploding', False) or getattr(self.target, 'health', 0) <= 0:
                    self.lock_on(targets, player=player)

            if self.target and not getattr(self.target, 'exploding', False) and getattr(self.target, 'health', 0) > 0:
                cx = self.pos_x + ROCKET_WIDTH / 2
                cy = self.pos_y + ROCKET_HEIGHT / 2
                lead_x, lead_y = calculate_missile_intercept_point(cx, cy, self.speed, self.target)

                diff_x = lead_x - cx
                diff_y = lead_y - cy

                desired_angle = math.degrees(math.atan2(-diff_x, -diff_y)) % 360
                angle_diff = (desired_angle - self.angle + 180) % 360 - 180

                if abs(angle_diff) <= self.turn_rate:
                    self.angle = desired_angle
                else:
                    self.angle += math.copysign(self.turn_rate, angle_diff)
                self.angle %= 360
                self.image = pygame.transform.rotate(self.original_image, self.angle)

            rad = math.radians(self.angle)
            self.dx = -math.sin(rad) * self.speed
            self.dy = -math.cos(rad) * self.speed

            self.pos_x += self.dx
            self.pos_y += self.dy
            self.x = int(self.pos_x)
            self.y = int(self.pos_y)

    def __init__(self):
        pygame.Rect.__init__(self, PLAYER_X, PLAYER_Y, PLAYER_WIDTH, PLAYER_HEIGHT)
        self.original_image = player_image
        self.image = player_image
        self.angle = 0
        self.turn_rate = PLAYER_TURN_RATE
        self.pos_x = float(PLAYER_X)
        self.pos_y = float(PLAYER_Y)
        self.max_health = PLAYER_MAX_HEALTH
        self.health = self.max_health
        self.x = PLAYER_X
        self.bullets = []
        self.shooting = False
        self.score = 0
        self.max_bullets = PLAYER_MAX_BULLETS
        self.used_bullets = 0
        self.reloading = False
        self.reloading_time = PLAYER_RELOAD_TIME

        # Raketen-System
        self.rockets = []
        self.max_rockets = PLAYER_MAX_ROCKETS
        self.used_rockets = 0
        self.rocket_shooting = False
        self.rocket_reloading = False
        self.rocket_reloading_time = PLAYER_ROCKET_RELOAD_TIME
        self.rocket_reload_start_time = 0

        # Radar Lock-on Modus: "CONE" (Fernbereich geradeaus) oder "OMNI" (Nahbereich 360°)
        self.radar_mode = "CONE"

        self.kamikaze_attack_damage = PLAYER_ATTACK_DAMAGE_KAMIKAZE
        self.invincible = False
        # Absolute pygame tick at which timed invincibility (e.g. after the orbital rearm
        # cinematic) ends; 0 means post-hit i-frames, which INVINCIBLE_END clears instead.
        self.invincible_timer = 0
        self.invincible_time = PLAYER_INVINCIBLE_TIME
        self.max_shield = PLAYER_MAX_SHIELD
        self.shield = PLAYER_MAX_SHIELD
        self.highscore = load_highscore()
        self.base_max_speed = PLAYER_MAX_SPEED
        self.min_speed = PLAYER_MIN_SPEED
        self.max_speed = PLAYER_MAX_SPEED
        self.acceleration = PLAYER_ACCELERATION
        self.velocity_y = float(PLAYER_MOVEMENT_SPEED_Y)
        self.velocity_x = float(PLAYER_MOVEMENT_SPEED_X)
        self.boundaries = False

    def get_forward_speed(self):
        """Returns the scalar forward movement speed of the ship."""
        return float(self.velocity_x)

    def get_effective_turn_rate(self):
        """Returns the speed-dependent angular turn rate peaking at CORNER_SPEED."""
        return calculate_turn_rate(self.get_forward_speed(), self.turn_rate)

    def toggle_radar_mode(self):
        """Wechselt zwischen CONE (Geradeaus-Fernbereich) und OMNI (360°-Nahbereich)."""
        if self.radar_mode == "CONE":
            self.radar_mode = "OMNI"
        else:
            self.radar_mode = "CONE"
        audio_manager.play_sfx("rocket_lock")

    def is_enemy_in_lock_zone(self, enemy):
        """Return True if the enemy is inside the active radar lock zone (CONE: long forward sector, OMNI: short wide forward arc)."""
        if not enemy or getattr(enemy, 'exploding', False) or getattr(enemy, 'health', 0) <= 0:
            return False

        cx = self.pos_x + PLAYER_WIDTH / 2
        cy = self.pos_y + PLAYER_HEIGHT / 2
        tx = enemy.x + getattr(enemy, 'width', LIGHT_ENEMY_WIDTH) / 2
        ty = enemy.y + getattr(enemy, 'height', LIGHT_ENEMY_HEIGHT) / 2
        diff_x = tx - cx
        diff_y = ty - cy
        dist = math.hypot(diff_x, diff_y)

        if self.radar_mode == "OMNI":
            if dist > RADAR_OMNI_RANGE:
                return False
            return missile_defense.heading_deviation_deg(cx, cy, self.angle, tx, ty) <= missile_defense.RADAR_OMNI_HALF_ANGLE

        elif self.radar_mode == "CONE":
            if dist <= RADAR_CONE_RANGE and dist >= RADAR_CONE_MIN_RANGE:
                desired_angle = math.degrees(math.atan2(-diff_x, -diff_y)) % 360
                angle_diff = abs((desired_angle - self.angle + 180) % 360 - 180)
                return angle_diff <= (RADAR_CONE_ANGLE / 2)
            return False

        return False

    def set_shoot(self):
        if self.reloading:
            return
        if getattr(self, PLAYER_WEAPONS_DISARMED_ATTR, False):
            return

        if not self.shooting and self.used_bullets < self.max_bullets:
            self.shooting = True
            self.used_bullets += 4
            
            if powerup_manager.is_active("rapid_fire"):
                audio_manager.play_sfx("laser_rapid")
            else:
                audio_manager.play_sfx("laser_player")

            bullet_offsets = [
                (0, 27),
                (6, 22),
                (PLAYER_WIDTH - 8, 27),
                (PLAYER_WIDTH - 14, 22)
            ]

            rad = math.radians(self.angle)
            cx = self.pos_x + PLAYER_WIDTH / 2
            cy = self.pos_y + PLAYER_HEIGHT / 2

            for ox, oy in bullet_offsets:
                rx = ox - PLAYER_WIDTH / 2
                ry = oy - PLAYER_HEIGHT / 2
                rot_rx = rx * math.cos(rad) - ry * math.sin(rad)
                rot_ry = rx * math.sin(rad) + ry * math.cos(rad)
                bx = cx + rot_rx - BULLET_WIDTH / 2
                by = cy + rot_ry - BULLET_HEIGHT / 2
                self.bullets.append(Player.Bullet(bx, by, self.angle))

            cooldown = RAPID_FIRE_COOLDOWN_MS if powerup_manager.is_active("rapid_fire") else BULLET_SHOOTING_TIMER
            if self.health <= ADRENALINE_HEALTH_THRESHOLD:
                cooldown = max(50, int(cooldown * 0.75))
            pygame.time.set_timer(SHOOTING_END, cooldown, 1)

        elif self.used_bullets >= self.max_bullets:
            self.reloading = True
            reload_delay = RAPID_FIRE_RELOAD_MS if powerup_manager.is_active("rapid_fire") else self.reloading_time
            if self.health <= ADRENALINE_HEALTH_THRESHOLD:
                reload_delay = max(1000, int(reload_delay * 0.75))
            pygame.time.set_timer(RELOAD_END, reload_delay, 1)

    def set_shoot_rocket(self, target=None):
        """Feuert eine zielsuchende Rakete ab."""
        if self.rocket_reloading:
            return
        if getattr(self, PLAYER_WEAPONS_DISARMED_ATTR, False):
            return

        if not self.rocket_shooting and self.used_rockets < self.max_rockets:
            self.rocket_shooting = True
            self.used_rockets += 1
            audio_manager.play_sfx("rocket_launch")

            wing_offset_x = 18 if (self.used_rockets % 2 == 1) else -18
            wing_offset_y = 10

            rad = math.radians(self.angle)
            cx = self.pos_x + PLAYER_WIDTH / 2
            cy = self.pos_y + PLAYER_HEIGHT / 2

            rot_x = wing_offset_x * math.cos(rad) - wing_offset_y * math.sin(rad)
            rot_y = wing_offset_x * math.sin(rad) + wing_offset_y * math.cos(rad)

            rx = cx + rot_x - ROCKET_WIDTH / 2
            ry = cy + rot_y - ROCKET_HEIGHT / 2

            if isinstance(target, (list, tuple)):
                locked = [t for t in target if self.is_enemy_in_lock_zone(t)]
                if locked:
                    locked.sort(key=lambda t: math.hypot(t.x - self.pos_x, t.y - self.pos_y))
                    target_to_lock = locked[0]
                else:
                    target_to_lock = None
            else:
                target_to_lock = target if (target and self.is_enemy_in_lock_zone(target)) else None

            new_rocket = Player.Rocket(rx, ry, self.angle, target=target_to_lock)
            self.rockets.append(new_rocket)

            pygame.time.set_timer(ROCKET_SHOOTING_END, ROCKET_SHOOTING_TIMER, 1)

            if self.used_rockets >= self.max_rockets:
                self.rocket_reloading = True
                self.rocket_reload_start_time = pygame.time.get_ticks()
                pygame.time.set_timer(ROCKET_RELOAD_END, self.rocket_reloading_time, 1)

        elif self.used_rockets >= self.max_rockets and not self.rocket_reloading:
            self.rocket_reloading = True
            self.rocket_reload_start_time = pygame.time.get_ticks()
            pygame.time.set_timer(ROCKET_RELOAD_END, self.rocket_reloading_time, 1)

    def add_score(self):
        self.score += 1

    def update_invincibility(self, now_ms):
        """End timed invincibility once its deadline (``invincible_timer``) has passed."""
        if self.invincible and self.invincible_timer > 0 and now_ms >= self.invincible_timer:
            self.invincible = False
            self.invincible_timer = 0

    def take_damage(self, damage):
        if self.invincible:
            return

        audio_manager.play_sfx("player_damage")

        if self.shield < damage:
            self.health += self.shield - damage
            self.shield = 0
            self.health = math.ceil(self.health)
            self.invincible = True
        else:
            self.shield -= damage
            self.invincible = True

        pygame.time.set_timer(
            INVINCIBLE_END,
            self.invincible_time,
            1
        )


class HealthDrop(pygame.Rect):
    def __init__(self, x, y):
        pygame.Rect.__init__(self, int(x - 12), int(y - 12), 24, 24)
        self.image = pygame.transform.scale(health_image, (24, 24))
        self.pos_x = float(x - 12)
        self.pos_y = float(y - 12)
        self.used = False
        self.spawn_time = pygame.time.get_ticks()
        self.lifetime = 15000


class Light_Enemy(pygame.Rect):
    is_air_target = True

    class Bullet(pygame.Rect):
        def __init__(self, x, y, angle=0.0, speed=LIGHT_ENEMY_BULLET_SPEED):
            pygame.Rect.__init__(self, int(x), int(y), BULLET_WIDTH, BULLET_HEIGHT)
            self.pos_x = float(x)
            self.pos_y = float(y)
            self.angle = angle
            self.speed = speed
            self.image = pygame.transform.rotate(enemy_bullet_image, angle)
            self.used = False
            rad = math.radians(angle)
            self.dx = math.sin(rad) * self.speed
            self.dy = math.cos(rad) * self.speed
            self.velocity_y = self.dy

        def update_position(self, speed_factor=1.0):
            self.pos_x += self.dx * speed_factor
            self.pos_y += self.dy * speed_factor
            self.x = int(self.pos_x)
            self.y = int(self.pos_y)

    def __init__(self, x=None, y=None, squadron_id=0, orbit_direction=1, orbit_radius=950.0, formation_offset=(0.0, 0.0)):
        if x is None or y is None:
            if x is None:
                x = random.randrange(100, MAP_WIDTH - LIGHT_ENEMY_WIDTH - 100, LIGHT_ENEMY_WIDTH * 2)
            if y is None:
                y = random.randrange(100, 400)
        safe_x = max(50.0, min(float(MAP_WIDTH - LIGHT_ENEMY_WIDTH - 50.0), float(x)))
        safe_y = max(50.0, min(float(MAP_HEIGHT - LIGHT_ENEMY_HEIGHT - 50.0), float(y)))
        pygame.Rect.__init__(self, int(safe_x), int(safe_y), LIGHT_ENEMY_WIDTH, LIGHT_ENEMY_HEIGHT)
        self.pos_x = float(safe_x)
        self.pos_y = float(safe_y)
        self.x = int(safe_x)
        self.y = int(safe_y)
        self.original_image = light_enemy_image
        self.image = light_enemy_image
        self.angle = 0.0
        self.turn_rate = LIGHT_ENEMY_TURN_RATE
        self.speed = ENEMY_PATROL_SPEED
        self.health = LIGHT_ENEMY_HEALTH
        self.used = False
        self.bullets = []
        self.shooting = False
        self.explosion_damage = LIGHT_ENEMY_EXPLOSION_DAMAGE
        self.exploding = False
        self.bullet_damage = LIGHT_ENEMY_BULLET_DAMAGE
        self.velocity_x = float(LIGHT_ENEMY_VELOCITY_X)
        self.velocity_y = float(LIGHT_ENEMY_VELOCITY_Y)

        # Squadron & AI State
        self.squadron_id = squadron_id
        self.state = "PATROL"  # "PATROL" or "AGRO"
        self.bfm_mode = "PATROL"
        self.bfm_commit_timer = 0
        self.jink_cooldown_timer = 0
        self.target_heading = 0.0
        self.orbit_direction = orbit_direction
        self.orbit_radius = orbit_radius
        self.formation_offset = formation_offset
        self.flares_remaining = missile_defense.LIGHT_ENEMY_FLARES
        self.flare_deploy_chance = missile_defense.LIGHT_ENEMY_FLARE_DEPLOY_CHANCE
        self.missile_reaction_frames = 0
        self.orbit_angle = math.degrees(math.atan2(self.pos_x - MAP_WIDTH / 2, self.pos_y - MAP_HEIGHT / 2))

    def get_effective_turn_rate(self):
        """Returns the speed-dependent angular turn rate peaking at CORNER_SPEED."""
        return calculate_turn_rate(self.speed, self.turn_rate)

    def trigger_agro(self, enemies=None):
        self.state = "AGRO"
        if enemies:
            for other in enemies:
                if getattr(other, 'squadron_id', None) == self.squadron_id and not getattr(other, 'exploding', False):
                    other.state = "AGRO"

    def update(self, target_player=None, enemies=None, speed_factor=1.0, incoming_rockets=None):
        if self.exploding:
            return

        # Status effects: EMS stun & smoke screen blindness
        if getattr(self, "stun_timer", 0) > 0:
            self.stun_timer = max(0.0, self.stun_timer - 0.016 * speed_factor)
            return

        smoke_blinded = getattr(self, "smoke_blinded", False)
        if smoke_blinded:
            self.state = "PATROL"
            self.smoke_blinded = False

        target = target_player if target_player is not None else player
        if target is not None and target.health > 0:
            cx = self.pos_x + LIGHT_ENEMY_WIDTH / 2
            cy = self.pos_y + LIGHT_ENEMY_HEIGHT / 2
            pcx = target.pos_x + PLAYER_WIDTH / 2
            pcy = target.pos_y + PLAYER_HEIGHT / 2
            dist_to_player = math.hypot(pcx - cx, pcy - cy)

            # Incoming-missile awareness (short reaction delay before the beam break).
            # Smoke-blinded or frozen (speed_factor 0) fighters cannot see the missile.
            if smoke_blinded or speed_factor <= 0:
                incoming = None
            else:
                incoming = missile_defense.find_incoming_rocket(self, incoming_rockets)
            if incoming is None:
                self.missile_reaction_frames = 0
            else:
                self.missile_reaction_frames += 1
            missile_threat = (
                incoming is not None
                and self.missile_reaction_frames > missile_defense.MISSILE_REACTION_DELAY_FRAMES
            )
            if missile_threat and self.state == "PATROL":
                self.trigger_agro(enemies)

            # Check Agro Radius
            if self.state == "PATROL":
                if dist_to_player <= ENEMY_AGRO_RADIUS:
                    self.trigger_agro(enemies)
            elif self.state == "AGRO":
                if dist_to_player > ENEMY_DEAGRO_RADIUS:
                    self.state = "PATROL"

            # Determine target angle & speed by state (BFM Pursuit Geometry)
            if self.state == "AGRO":
                dx = pcx - cx
                dy = pcy - cy
                safe_dist = max(0.001, dist_to_player)
                los_x = dx / safe_dist
                los_y = dy / safe_dist

                p_rad = math.radians(getattr(target, "angle", 0.0))
                p_fx = -math.sin(p_rad)
                p_fy = -math.cos(p_rad)
                p_speed = float(getattr(target, "velocity_x", CORNER_SPEED))

                e_rad = math.radians(self.angle)
                e_fx = math.sin(e_rad)
                e_fy = math.cos(e_rad)

                # +1.0 = pointing directly at opponent; -1.0 = pointing directly away
                enemy_closing_dot = e_fx * los_x + e_fy * los_y
                player_closing_dot = -(p_fx * los_x + p_fy * los_y)
                evade_sign = compute_bfm_evade_sign(
                    dx, dy, p_fx, p_fy, p_speed, getattr(self, "orbit_direction", 1)
                )

                if self.jink_cooldown_timer > 0:
                    self.jink_cooldown_timer -= 1

                sq_id = getattr(self, "squadron_id", 0) or 0

                if dist_to_player < 195.0 and enemy_closing_dot > -0.15:
                    # 0. Emergency close-range anti-ramming break (< 195 px from any closing aspect)
                    self.bfm_mode = "MERGE_BREAK"
                    self.bfm_commit_timer = max(self.bfm_commit_timer, 22)
                    los_angle = math.degrees(math.atan2(dx, dy))
                    self.speed = CORNER_SPEED if sq_id % 2 == 0 else CORNER_SPEED * 1.15
                    target_angle = (los_angle + evade_sign * 95.0) % 360
                elif missile_threat:
                    # MISSILE_DEFENSE: beam the incoming rocket at corner speed to force an overshoot
                    self.bfm_mode = "MISSILE_DEFENSE"
                    self.bfm_commit_timer = 0
                    self.speed = CORNER_SPEED
                    r_cx, r_cy = missile_defense.entity_center(incoming)
                    target_angle = missile_defense.compute_beam_heading(cx, cy, self.angle, r_cx, r_cy)
                elif self.bfm_commit_timer > 0:
                    # Stay committed to current break heading so enemy passes through the merge
                    # instead of orbiting in a tiny circle
                    self.bfm_commit_timer -= 1
                    target_angle = self.target_heading
                elif dist_to_player < 340.0 and enemy_closing_dot > 0.25 and player_closing_dot > 0.20:
                    # 1. MERGE_BREAK: Head-on / forward-quarter merge -> lateral pass-through slice
                    self.bfm_mode = "MERGE_BREAK"
                    self.bfm_commit_timer = 32
                    los_angle = math.degrees(math.atan2(dx, dy))
                    if sq_id % 2 == 0:
                        # 1-Circle Radius Fighter: brake to Corner Speed and cut inside the turn
                        self.speed = CORNER_SPEED
                        target_angle = (los_angle + evade_sign * 65.0) % 360
                    else:
                        # 2-Circle Rate Fighter: extend through merge at high speed for rate flow
                        self.speed = CORNER_SPEED * 1.15
                        target_angle = (los_angle + evade_sign * 80.0) % 360
                elif (
                    dist_to_player < 380.0
                    and enemy_closing_dot < -0.30
                    and player_closing_dot > 0.70
                    and self.jink_cooldown_timer <= 0
                ):
                    # 2. EVASIVE_JINK: Brief defensive jink when player first lines up on enemy's six,
                    # followed by a cooldown window so the player can track and finish the kill
                    self.bfm_mode = "EVASIVE_JINK"
                    self.bfm_commit_timer = 20
                    self.jink_cooldown_timer = 150
                    self.speed = CORNER_SPEED
                    away_angle = math.degrees(math.atan2(-dx, -dy))
                    target_angle = (away_angle + evade_sign * 65.0) % 360
                elif dist_to_player < 420.0 and player_closing_dot < -0.35:
                    # 3. WEZ_ATTACK: Slotted behind player's tail -> pull lead pursuit and throttle at close range
                    self.bfm_mode = "WEZ_ATTACK"
                    if dist_to_player < 260.0:
                        self.speed = max(PLAYER_MIN_SPEED, min(CORNER_SPEED, p_speed * 0.90))
                    else:
                        self.speed = CORNER_SPEED
                    lead_x = pcx + p_fx * 40.0
                    lead_y = pcy + p_fy * 40.0
                    target_angle = math.degrees(math.atan2(lead_x - cx, lead_y - cy))
                else:
                    # 4. TAIL_STALK: Lag pursuit behind tail, or lateral offset when approaching from the front
                    self.bfm_mode = "TAIL_STALK"
                    self.speed = CORNER_SPEED if dist_to_player < 550.0 else ENEMY_AGRO_SPEED * 1.35
                    lag_offset = min(140.0, max(75.0, dist_to_player * 0.30))
                    if player_closing_dot > 0.20:
                        perp_x = los_y * evade_sign
                        perp_y = -los_x * evade_sign
                        tail_x = pcx + perp_x * 120.0
                        tail_y = pcy + perp_y * 120.0
                    else:
                        tail_x = pcx - p_fx * lag_offset
                        tail_y = pcy - p_fy * lag_offset
                    target_angle = math.degrees(math.atan2(tail_x - cx, tail_y - cy))
            else:
                self.bfm_mode = "PATROL"
                self.speed = ENEMY_PATROL_SPEED
                angular_speed = (self.speed / max(100.0, self.orbit_radius)) * (180.0 / math.pi) * self.orbit_direction * speed_factor
                self.orbit_angle = (self.orbit_angle + angular_speed) % 360
                orbit_rad = math.radians(self.orbit_angle)

                map_cx = MAP_WIDTH / 2
                map_cy = MAP_HEIGHT / 2
                waypoint_x = map_cx + math.sin(orbit_rad) * self.orbit_radius + self.formation_offset[0]
                waypoint_y = map_cy + math.cos(orbit_rad) * self.orbit_radius + self.formation_offset[1]

                dx = waypoint_x - cx
                dy = waypoint_y - cy
                target_angle = math.degrees(math.atan2(dx, dy))

            self.target_heading = (target_angle + 180) % 360 - 180

            # Rotate enemy sprite so it turns to face heading
            prev_angle = self.angle
            angle_diff = (target_angle - self.angle + 180) % 360 - 180
            if self.bfm_mode == "MISSILE_DEFENSE":
                turn_mult = missile_defense.MISSILE_EVASION_TURN_MULT
            else:
                turn_mult = 1.85 if (self.bfm_mode == "MERGE_BREAK" and dist_to_player < 280.0) else 1.0
            effective_turn_rate = self.get_effective_turn_rate() * turn_mult * speed_factor
            if abs(angle_diff) <= effective_turn_rate:
                self.angle = target_angle
            elif angle_diff > 0:
                self.angle += effective_turn_rate
            else:
                self.angle -= effective_turn_rate
            self.angle = (self.angle + 180) % 360 - 180
            turned_delta = (self.angle - prev_angle + 180) % 360 - 180
            if "combat_juice" in globals():
                combat_juice.emit_wingtip_contrails(
                    cx=cx,
                    cy=cy,
                    angle_deg=self.angle,
                    speed=self.speed,
                    angular_delta=turned_delta,
                    wing_span=16.0,
                    tail_offset=10.0,
                    is_enemy=True,
                )

        self.image = pygame.transform.rotate(self.original_image, self.angle)

        # Move enemy forward along its facing direction
        effective_speed = self.speed * speed_factor
        rad = math.radians(self.angle)
        self.pos_x += math.sin(rad) * effective_speed
        self.pos_y += math.cos(rad) * effective_speed

        # Flocking separation from other enemies
        if enemies:
            for other in enemies:
                if other is not self and not getattr(other, 'exploding', False):
                    diff_x = self.pos_x - other.pos_x
                    diff_y = self.pos_y - other.pos_y
                    sep_dist = math.hypot(diff_x, diff_y)
                    if 0.001 < sep_dist < ENEMY_SEPARATION_RADIUS:
                        push = ((ENEMY_SEPARATION_RADIUS - sep_dist) / ENEMY_SEPARATION_RADIUS) * 1.5 * speed_factor
                        self.pos_x += (diff_x / sep_dist) * push
                        self.pos_y += (diff_y / sep_dist) * push

        # Soft containment inside map
        margin = 120
        if self.pos_x < margin:
            self.pos_x += 2.0
        elif self.pos_x > MAP_WIDTH - margin - LIGHT_ENEMY_WIDTH:
            self.pos_x -= 2.0
        if self.pos_y < margin:
            self.pos_y += 2.0
        elif self.pos_y > MAP_HEIGHT - margin - LIGHT_ENEMY_HEIGHT:
            self.pos_y -= 2.0

        self.x = int(self.pos_x)
        self.y = int(self.pos_y)

    def set_shoot(self, target_player=None):
        if self.exploding or self.state != "AGRO":
            return

        target = target_player if target_player is not None else player
        if target is None or target.health <= 0:
            return

        # Vector from enemy to player
        dx = (target.pos_x + PLAYER_WIDTH / 2) - (self.pos_x + LIGHT_ENEMY_WIDTH / 2)
        dy = (target.pos_y + PLAYER_HEIGHT / 2) - (self.pos_y + LIGHT_ENEMY_HEIGHT / 2)
        target_angle = math.degrees(math.atan2(dx, dy))

        # Check angle difference between enemy's facing angle and line of sight to player
        angle_diff = (target_angle - self.angle + 180) % 360 - 180
        if abs(angle_diff) <= LIGHT_ENEMY_ALIGNMENT_THRESHOLD:
            # Spawn bullet at enemy's nose facing the aiming angle
            rad = math.radians(self.angle)
            cx = self.pos_x + LIGHT_ENEMY_WIDTH / 2
            cy = self.pos_y + LIGHT_ENEMY_HEIGHT / 2
            nose_dist = LIGHT_ENEMY_HEIGHT / 2
            bullet_cx = cx + math.sin(rad) * nose_dist
            bullet_cy = cy + math.cos(rad) * nose_dist
            bullet_x = bullet_cx - BULLET_WIDTH / 2
            bullet_y = bullet_cy - BULLET_HEIGHT / 2
            self.bullets.append(Light_Enemy.Bullet(bullet_x, bullet_y, self.angle))
            audio_manager.play_sfx("laser_enemy")


class WaveManager:
    def __init__(self):
        self.wave = 1
        self.enemies = []
        self.state = "ACTIVE"  # "ACTIVE", "INTERMISSION"
        self.intermission_timer = 0
        if active_mission_config.get("id") == MissionType.ACADEMY_TUTORIAL:
            self.wave_announcement = ""
            self.announcement_timer = 0
        else:
            self.wave_announcement = "WAVE 1"
            self.announcement_timer = 180
        self.spawn_wave(1)

    def spawn_wave(self, wave_num):
        max_w = active_mission_config.get("max_waves", MAX_WAVE_LEVEL)
        self.wave = min(wave_num, max_w)
        self.enemies.clear()
        self.state = "ACTIVE"

        if active_mission_config.get("id") == MissionType.ACADEMY_TUTORIAL:
            self.wave_announcement = ""
            self.announcement_timer = 0
            return

        self.wave_announcement = f"WAVE {self.wave}"
        self.announcement_timer = 150

        if active_mission_config.get("has_bombers"):
            # Base defense mission: spawn heavy Automaton Bombers
            bomber_enemies.clear()
            for b_idx in range(min(4, self.wave + 1)):
                bx = random.randint(400, MAP_WIDTH - 400)
                by = random.randint(100, 400)
                bomber_enemies.append(BomberEnemy(bx, by))
            return

        if active_mission_config.get("id") == MissionType.STRIDER_RAID:
            # Factory Strider Raid: focused ground boss fight
            return

        if self.wave == 1:
            squad_configs = [3]
        elif self.wave == 2:
            squad_configs = [4]
        elif self.wave == 3:
            squad_configs = [3, 3]
        else:
            squad_configs = [4, 4]

        total_enemies = 0
        for s_idx, squad_size in enumerate(squad_configs):
            if total_enemies + squad_size > MAX_ENEMIES_PER_WAVE:
                squad_size = MAX_ENEMIES_PER_WAVE - total_enemies
            if squad_size <= 0:
                break

            angle_offset = s_idx * math.pi + (self.wave * 0.6)
            base_dist = 1000.0
            center_x = MAP_WIDTH / 2 + math.sin(angle_offset) * base_dist
            center_y = MAP_HEIGHT / 2 + math.cos(angle_offset) * base_dist
            center_x = max(200, min(MAP_WIDTH - 200, center_x))
            center_y = max(200, min(MAP_HEIGHT - 200, center_y))

            orbit_dir = 1 if s_idx % 2 == 0 else -1
            orbit_radius = 850.0 + s_idx * 150.0

            for m_idx in range(squad_size):
                row = (m_idx + 1) // 2
                col_side = -1 if (m_idx % 2 == 1) else 1
                if m_idx == 0:
                    form_x, form_y = 0.0, 0.0
                else:
                    form_x = col_side * row * 55.0
                    form_y = -row * 50.0

                ex = center_x + form_x
                ey = center_y + form_y
                enemy = Light_Enemy(
                    x=ex, y=ey,
                    squadron_id=s_idx,
                    orbit_direction=orbit_dir,
                    orbit_radius=orbit_radius,
                    formation_offset=(form_x, form_y)
                )
                self.enemies.append(enemy)
                total_enemies += 1

    def get_closest_enemy(self, player):
        living = [e for e in self.enemies if not getattr(e, 'exploding', False) and getattr(e, 'health', 0) > 0]
        if not living:
            return None
        pcx = player.pos_x + PLAYER_WIDTH / 2
        pcy = player.pos_y + PLAYER_HEIGHT / 2
        living.sort(key=lambda e: math.hypot((e.x + LIGHT_ENEMY_WIDTH / 2) - pcx, (e.y + LIGHT_ENEMY_HEIGHT / 2) - pcy))
        return living[0]

    def update(self, player):
        if self.announcement_timer > 0:
            self.announcement_timer -= 1

        if active_mission_config.get("has_bombers"):
            living_bombers = [b for b in bomber_enemies if not b.exploding]
            if self.state == "ACTIVE" and len(living_bombers) == 0:
                self.state = "INTERMISSION"
                self.intermission_timer = pygame.time.get_ticks() + WAVE_INTERMISSION_TIME
                self.wave_announcement = f"BOMBER WAVE {self.wave} REPELLED!"
                self.announcement_timer = 180
                wave_bonus = self.wave * 300
                player.score += wave_bonus
                ground_support_manager.on_wave_cleared(self.wave, player)
            elif self.state == "INTERMISSION":
                if pygame.time.get_ticks() >= self.intermission_timer:
                    next_wave = self.wave + 1
                    max_w = active_mission_config.get("max_waves", 5)
                    if next_wave <= max_w:
                        self.spawn_wave(next_wave)
                    else:
                        # All bomber waves repelled and bombers are no longer spawning!
                        self.state = "COMPLETE"
                        if not ground_support_manager.beacon.active:
                            ground_support_manager.beacon.activate(3.0)
                            ground_support_manager.objective_phase = "EXTRACTION"
                            player.score += 1500
                            ground_support_manager.add_combat_popup("BOMBERS REPELLED! FLY TO EXTRACTION BEACON", ground_support_manager.beacon.x, ground_support_manager.beacon.y, (0, 255, 180))
            return

        if active_mission_config.get("id") == MissionType.STRIDER_RAID:
            return

        living_enemies = [e for e in self.enemies if not getattr(e, 'exploding', False)]

        if self.state == "ACTIVE" and len(living_enemies) == 0:
            self.state = "INTERMISSION"
            self.intermission_timer = pygame.time.get_ticks() + WAVE_INTERMISSION_TIME
            self.wave_announcement = f"WAVE {self.wave} CLEARED!"
            self.announcement_timer = 180
            wave_bonus = self.wave * 250
            player.score += wave_bonus
            ground_support_manager.on_wave_cleared(self.wave, player)

        elif self.state == "INTERMISSION":
            if pygame.time.get_ticks() >= self.intermission_timer:
                next_wave = self.wave + 1
                max_w = active_mission_config.get("max_waves", MAX_WAVE_LEVEL)
                if next_wave <= max_w:
                    self.spawn_wave(next_wave)
                else:
                    if active_mission_config.get("id") == MissionType.AIR_SUPERIORITY:
                        if not ground_support_manager.beacon.active:
                            ground_support_manager.beacon.activate(3.0)
                            ground_support_manager.objective_phase = "EXTRACTION"
                            ground_support_manager.add_combat_popup("AIRSPACE SECURED! FLY TO EXTRACTION BEACON", ground_support_manager.beacon.x, ground_support_manager.beacon.y, (0, 255, 180))


def trigger_mission_complete():
    """Concludes mission simulation, logs statistics, and activates the debriefing screen."""
    global game_state
    if game_state == "mission_debriefing":
        return
    if get_campaign_session().is_act3_flight:
        return  # Act III ends in the ending cinematic, never in a debriefing
    if player.score > player.highscore:
        player.highscore = player.score
        add_highscore(player.score)
    duration_s = max(1.0, (pygame.time.get_ticks() - mission_start_time) / 1000.0)
    results = {
        "mission_name": active_mission_config.get("name", "OPERATION"),
        "final_score": player.score,
        "highscore": player.highscore,
        "is_new_highscore": player.score >= player.highscore and player.score > 0,
        "duration_seconds": duration_s,
        "waves_cleared": wave_manager.wave,
        "aerial_kills": mission_air_kills,
        "bomber_kills": mission_bomber_kills,
        "fabricators_destroyed": getattr(ground_support_manager, "destroyed_fabs_count", 0),
        "strider_destroyed": getattr(ground_support_manager, "strider_destroyed", False),
        "cas_kills": ground_support_manager.total_cas_kills,
        "survivors_count": ground_support_manager.survivors_count,
        "casualties_count": sum(1 for unit in ground_support_manager.units if unit.state == "DOWNED" or unit.health <= 0),
        "squad_wiped": bool(ground_support_manager.units) and ground_support_manager.survivors_count <= 0,
        "hull_ratio": max(0.0, min(1.0, float(player.health) / max(1.0, float(player.max_health)))),
        "flawless_squad": ground_support_manager.flawless_protection,
        "hero_score": ground_support_manager.hero_score,
    }
    if active_mission_config.get("id") == MissionType.ACADEMY_TUTORIAL and profile_manager.has_active_profile():
        try:
            prof = profile_manager.load_profile()
            prof.academy_completed = True
            prof.active_mission = MissionType.AIR_SUPERIORITY
            profile_manager.save_profile(prof)
        except Exception:
            pass
    player.shooting = False
    player.rocket_shooting = False
    player.reloading = False
    player.rocket_reloading = False
    ground_support_manager.stop_aiming()
    ground_support_manager.weapon_menu.is_open = False
    debriefing_screen.set_results(results)
    game_state = "mission_debriefing"
    audio_manager.stop_engine_sound()
    audio_manager.play_music("menu_theme")


def move():
    global light_enemy, wave_manager, health_drops
    global explosion_group
    global mission_air_kills, mission_bomber_kills
    if player.health <= 0 or game_state in ("mission_debriefing", "super_destroyer"):
        return

    player.update_invincibility(pygame.time.get_ticks())

    # Boundary damage
    if player.pos_x < 0 or player.pos_x + PLAYER_WIDTH > MAP_WIDTH or \
       player.pos_y < 0 or player.pos_y + PLAYER_HEIGHT > MAP_HEIGHT:
        damage = BORDER_TICK_DAMAGE
        player.boundaries = True 
        if player.shield > 0:
            player.shield = max(0.0, player.shield - damage)
        else:
            player.health = max(0.0, player.health - damage)
    
    player.boundaries = False
    player.x = int(player.pos_x)
    player.y = int(player.pos_y)

    # Check score milestones for guaranteed drops
    powerup_manager.check_milestones(player.score, player.pos_x, player.pos_y)

    # Primary enemy for single-target powerups (escort drone, lock-on)
    primary_enemy = wave_manager.get_closest_enemy(player)
    light_enemy = primary_enemy

    comms_scale = comms_hud.get_time_dilation() if comms_hud else 1.0

    # Update power-up subsystem (buff timers, drops, drone, micro-missiles, popups)
    powerup_manager.update(1.0 / 60.0 * comms_scale, player, primary_enemy)

    # Update ground support subsystem (Helldivers, airstrikes, supply drops, danger alerts)
    all_air_targets = list(wave_manager.enemies) + list(bomber_enemies)
    ground_support_manager.update(1.0 / 60.0 * comms_scale, player, all_air_targets, explosion_group, large_explosion_a_spritesheet.frames)

    if ground_support_manager.objective_phase == "COMPLETE":
        trigger_mission_complete()
        return

    session = get_campaign_session()
    if session.is_flight_active:
        session.update(1.0 / 60.0, wave_manager.wave, mission_air_kills + mission_bomber_kills, ground_support_manager)

    # Update Bomber Enemies & Orbital Base Defense
    if active_mission_config.get("has_bombers"):
        target_pt = (orbital_base.pos_x + 60, orbital_base.pos_y + 60) if (orbital_base and orbital_base.is_alive) else (player.pos_x, player.pos_y)
        for bomber in list(bomber_enemies):
            if not bomber.exploding:
                b_speed_mult = (SLOW_MO_TIME_SCALE if ground_support_manager.is_slow_mo else 1.0) * comms_scale
                bomber.update(target_pt, speed_factor=b_speed_mult)
                if orbital_base and orbital_base.is_alive and math.hypot((bomber.pos_x + 32) - target_pt[0], (bomber.pos_y + 26) - target_pt[1]) <= 65.0:
                    orbital_base.take_damage(bomber.bullet_damage)
                    bomber.exploding = True
                    explosion_group.add(Large_explosion_a(bomber.pos_x + 32, bomber.pos_y + 26, large_explosion_a_spritesheet.frames))
                    ground_support_manager.add_combat_popup("BASE UNDER ATTACK!", orbital_base.pos_x + 60, orbital_base.pos_y, (255, 60, 60))
                    audio_manager.play_sfx("explosion")

                if bomber.health <= 0 and not bomber.exploding:
                    bomber.exploding = True
                    mission_bomber_kills += 1
                    player.score += bomber.score_value
                    ground_support_manager.add_combat_popup(f"BOMBER DOWN! +{bomber.score_value}", bomber.pos_x, bomber.pos_y, (255, 200, 50))
                    explosion_group.add(Large_explosion_a(bomber.pos_x + 32, bomber.pos_y + 26, large_explosion_a_spritesheet.frames))
                    audio_manager.play_sfx("explosion")
                    audio_manager.play_sfx("enemy_defeat")

        bomber_enemies[:] = [b for b in bomber_enemies if not b.exploding and b.health > 0]

        if orbital_base and orbital_base.health <= 0 and player.health > 0:
            player.take_damage(100.0)
            ground_support_manager.add_combat_popup("BASE DESTROYED! MISSION FAILED!", player.pos_x, player.pos_y, (255, 40, 40))

    bullet_dmg = PLAYER_BULLET_DAMAGE * (DAMAGE_BOOST_MULTIPLIER if powerup_manager.is_active("damage_boost") else 1)

    # Bullet Update & Collision across aerial enemies, bombers, and hostile ground units/structures
    for bullet in player.bullets:
        bullet.update_position()
        for enemy in wave_manager.enemies:
            if bullet.colliderect(enemy) and not enemy.exploding:
                bullet.used = True
                dir_dmg = calculate_directional_gun_damage(
                    bullet_dmg, bullet.dx, bullet.dy, enemy.angle
                )
                enemy.health -= dir_dmg
                if "combat_juice" in globals():
                    combat_juice.spawn_hit_sparks(
                        bullet.pos_x + BULLET_WIDTH / 2,
                        bullet.pos_y + BULLET_HEIGHT / 2,
                        damage_ratio=dir_dmg / max(0.01, bullet_dmg),
                    )
                powerup_manager.on_bullet_hit_enemy(enemy)
                enemy.trigger_agro(wave_manager.enemies)
                audio_manager.play_sfx("hit")
                break

        if not bullet.used:
            for bomber in bomber_enemies:
                if not bomber.exploding and bullet.colliderect(bomber):
                    bullet.used = True
                    bomber.health -= bullet_dmg
                    audio_manager.play_sfx("hit")
                    break

        # Check collision with ground enemy units if bullet is still active
        if not bullet.used:
            for ge in ground_support_manager.enemy_ground_units:
                if ge.is_alive and bullet.colliderect(ge):
                    bullet.used = True
                    ge.take_damage(bullet_dmg)
                    audio_manager.play_sfx("hit")
                    if not ge.is_alive:
                        score_val = getattr(ge, 'score_value', 25)
                        player.score += score_val
                        ground_support_manager.add_combat_popup(f"+{score_val} PTS", ge.pos_x, ge.pos_y, (255, 215, 0))
                        audio_manager.play_sfx("enemy_defeat")
                    break

        # Check collision with enemy fabricator buildings
        if not bullet.used:
            for fab in ground_support_manager.enemy_fabricators:
                if fab.is_alive and bullet.colliderect(fab):
                    bullet.used = True
                    fab.take_damage(bullet_dmg)
                    audio_manager.play_sfx("hit")
                    break

        # Check collision with Academy training targets (drones, bunker)
        if not bullet.used and active_mission_config.get("id") == MissionType.ACADEMY_TUTORIAL:
            for target in academy_manager.get_combat_targets():
                if target.is_alive and bullet.colliderect(target):
                    bullet.used = True
                    target.take_damage(bullet_dmg)
                    audio_manager.play_sfx("hit")
                    if not target.is_alive:
                        audio_manager.play_sfx("explosion_small")
                        cx = getattr(target, 'centerx', getattr(target, 'pos_x', 0))
                        cy = getattr(target, 'centery', getattr(target, 'pos_y', 0))
                        explosion_group.add(Large_explosion_a(cx, cy, large_explosion_a_spritesheet.frames, speed=0.6))
                    break

    # Rocket Update & Collision across aerial targets only (fighters, bombers, academy drones)
    rocket_targets = get_rocket_targets()
    enemies_frozen = powerup_manager.is_enemy_frozen()

    for rocket in player.rockets:
        step = missile_defense.step_rocket(rocket, rocket_targets, player=player, frozen=enemies_frozen)
        if step.flares:
            active_flares.extend(step.flares)
        if step.popup is not None:
            ground_support_manager.add_combat_popup(step.popup, step.popup_pos[0], step.popup_pos[1], theme.WARNING)
        if rocket.used:
            range_explosion = Large_explosion_a(
                rocket.x + ROCKET_WIDTH // 2,
                rocket.y + ROCKET_HEIGHT // 2,
                large_explosion_a_spritesheet.frames,
                speed=0.6
            )
            explosion_group.add(range_explosion)
            audio_manager.play_sfx("explosion_small")
        elif missile_defense.rocket_can_fuse(rocket):
            # Decoyed/evaded rockets have lost their lock and can no longer fuse on a target
            for enemy in wave_manager.enemies:
                if rocket.colliderect(enemy) and not enemy.exploding:
                    rocket.used = True
                    enemy.health -= rocket.damage
                    enemy.trigger_agro(wave_manager.enemies)
                    if "combat_juice" in globals():
                        combat_juice.trigger_shake(4.5, 6)
                        combat_juice.spawn_hit_sparks(
                            rocket.x + ROCKET_WIDTH // 2,
                            rocket.y + ROCKET_HEIGHT // 2,
                            damage_ratio=1.25,
                        )
                    hit_explosion = Large_explosion_a(
                        rocket.x + ROCKET_WIDTH // 2,
                        rocket.y + ROCKET_HEIGHT // 2,
                        large_explosion_a_spritesheet.frames,
                        speed=0.6
                    )
                    explosion_group.add(hit_explosion)
                    audio_manager.play_sfx("explosion")
                    break

            if not rocket.used:
                for bomber in bomber_enemies:
                    if not bomber.exploding and rocket.colliderect(bomber):
                        rocket.used = True
                        bomber.health -= rocket.damage
                        hit_explosion = Large_explosion_a(
                            rocket.x + ROCKET_WIDTH // 2,
                            rocket.y + ROCKET_HEIGHT // 2,
                            large_explosion_a_spritesheet.frames,
                            speed=0.6
                        )
                        explosion_group.add(hit_explosion)
                        audio_manager.play_sfx("explosion")
                        break

            if not rocket.used and active_mission_config.get("id") == MissionType.ACADEMY_TUTORIAL:
                for target in missile_defense.filter_air_targets(academy_manager.get_combat_targets()):
                    if target.is_alive and rocket.colliderect(target):
                        rocket.used = True
                        target.take_damage(rocket.damage)
                        cx = getattr(target, 'centerx', getattr(target, 'pos_x', 0))
                        cy = getattr(target, 'centery', getattr(target, 'pos_y', 0))
                        hit_explosion = Large_explosion_a(
                            cx, cy,
                            large_explosion_a_spritesheet.frames,
                            speed=0.6
                        )
                        explosion_group.add(hit_explosion)
                        audio_manager.play_sfx("explosion")
                        break

    # Player Aerial Collision (mutual hull trauma; no knockback or speed loss)
    for enemy in wave_manager.enemies:
        if not enemy.exploding and player.colliderect(enemy):
            if resolve_aerial_collision(player, enemy) and "combat_juice" in globals():
                combat_juice.trigger_shake(5.5, 8)
                combat_juice.spawn_hit_sparks(
                    (player.pos_x + enemy.pos_x) * 0.5 + PLAYER_WIDTH * 0.5,
                    (player.pos_y + enemy.pos_y) * 0.5 + PLAYER_HEIGHT * 0.5,
                    damage_ratio=1.25,
                )
            enemy.trigger_agro(wave_manager.enemies)
            

    # Aerial extraction check in non-ground missions (Air Superiority, Base Defense)
    if ground_support_manager.beacon.active and not ground_support_manager.beacon.pelican_departed:
        if not active_mission_config.get("has_ground", True):
            # Guard: You can only extract if bombers are no longer spawning
            bombers_spawning = False
            if active_mission_config.get("has_bombers"):
                max_w = active_mission_config.get("max_waves", 5)
                living_bombers = [b for b in bomber_enemies if not b.exploding and b.health > 0]
                if wave_manager.wave < max_w or len(living_bombers) > 0 or wave_manager.state != "COMPLETE":
                    bombers_spawning = True

            if not bombers_spawning:
                if math.hypot((player.pos_x + PLAYER_WIDTH / 2) - ground_support_manager.beacon.x,
                              (player.pos_y + PLAYER_HEIGHT / 2) - ground_support_manager.beacon.y) <= ground_support_manager.beacon.radius:
                    ground_support_manager.beacon.pelican_departed = True
                    ground_support_manager.objective_phase = "COMPLETE"
                    bonus = SCORE_EXTRACTION_BONUS
                    player.score += bonus
                    ground_support_manager.add_combat_popup(f"EXTRACTION COMPLETE! +{bonus}", player.pos_x, player.pos_y, (0, 255, 180))
                    trigger_mission_complete()
                    return
        
    # Enemy Defeated checks
    for enemy in wave_manager.enemies:
        if enemy.health <= 0 and not enemy.exploding:
            enemy.exploding = True
            mission_air_kills += 1
            explosion = Large_explosion_a(
                enemy.x + LIGHT_ENEMY_WIDTH // 2, 
                enemy.y + LIGHT_ENEMY_HEIGHT // 2, 
                large_explosion_a_spritesheet.frames
            )
            explosion_group.add(explosion)
            audio_manager.play_sfx("explosion")
            audio_manager.play_sfx("enemy_defeat")
            # Adrenaline score bonus on kills at low HP
            kill_points = 5
            if player.health <= ADRENALINE_HEALTH_THRESHOLD:
                kill_points = int(kill_points * 1.5)
            player.score += kill_points

            # Roll power-up drop on kill
            powerup_manager.roll_drop(enemy.x + LIGHT_ENEMY_WIDTH // 2, enemy.y + LIGHT_ENEMY_HEIGHT // 2)

            # Close Air Support (CAS) bonus check
            ground_support_manager.on_player_kill_enemy(enemy, player)

            # Anti-Retreat: Guaranteed health nanite drop if player is at low health
            if player.health <= ADRENALINE_HEALTH_THRESHOLD:
                health_drops.append(HealthDrop(enemy.x + LIGHT_ENEMY_WIDTH // 2, enemy.y + LIGHT_ENEMY_HEIGHT // 2))

            enemy.speed = 0
            enemy.velocity_y = 0

    player.bullets = [bullet for bullet in player.bullets if not bullet.used \
                    and 0 <= bullet.x <= MAP_WIDTH and 0 <= bullet.y <= MAP_HEIGHT]

    player.rockets = [rocket for rocket in player.rockets if not rocket.used \
                    and 0 <= rocket.x <= MAP_WIDTH and 0 <= rocket.y <= MAP_HEIGHT]

    # Enemy and enemy bullet movement affected by Time Slow, Frost/Freeze, Stratagem Aiming, and Comms Dialogue
    slow_mo_mult = (SLOW_MO_TIME_SCALE if ground_support_manager.is_slow_mo else 1.0) * comms_scale
    speed_factor = powerup_manager.modify_enemy_speed(1.0) * slow_mo_mult
    bullet_speed_factor = powerup_manager.modify_enemy_bullet_speed(1.0) * slow_mo_mult

    for flare in active_flares:
        flare.update(speed_factor)
    active_flares[:] = [f for f in active_flares if f.is_alive]

    # Smoke blindness is re-applied every frame by the smoke zone (ground support update).
    # Fighters clear it in Light_Enemy.update; bombers have no AI that clears it, so reset it
    # here, after the rocket countermeasure rolls have read it this frame.
    for bomber in bomber_enemies:
        bomber.smoke_blinded = False

    for enemy in wave_manager.enemies:
        if not enemy.exploding:
            enemy.update(player, wave_manager.enemies, speed_factor=speed_factor, incoming_rockets=player.rockets)
        
        for bullet in enemy.bullets:
            bullet.update_position(speed_factor=bullet_speed_factor)
            if bullet.colliderect(player):
                bullet.used = True
                player.take_damage(enemy.bullet_damage)
                audio_manager.play_sfx("hit")

        enemy.bullets = [bullet for bullet in enemy.bullets if not bullet.used \
                         and 0 <= bullet.x <= MAP_WIDTH and 0 <= bullet.y <= MAP_HEIGHT]

    # Health drops update and player pickup
    now = pygame.time.get_ticks()
    for drop in health_drops:
        if not drop.used:
            if player.colliderect(drop):
                drop.used = True
                audio_manager.play_sfx("health_pickup")
                if player.health < player.max_health:
                    player.health = min(player.max_health, player.health + 1)
            elif now - drop.spawn_time >= drop.lifetime:
                drop.used = True

    health_drops = [d for d in health_drops if not d.used]
    combat_juice.update()

    # Update Wave progression or Academy Tutorial
    if active_mission_config.get("id") == MissionType.ACADEMY_TUTORIAL:
        keys = pygame.key.get_pressed()
        academy_manager.update(1.0 / 60.0 * comms_scale, player, keys, ground_support_manager)
        if academy_manager.is_completed:
            trigger_mission_complete()
            return
    else:
        wave_manager.update(player)


def get_rocket_targets() -> list:
    """Aerial entities homing rockets may lock: wave fighters, bombers, academy drones."""
    candidates = list(wave_manager.enemies) + list(bomber_enemies)
    if active_mission_config.get("id") == MissionType.ACADEMY_TUTORIAL:
        candidates.extend(academy_manager.get_combat_targets())
    return missile_defense.filter_air_targets(candidates)


def respawn(mission_config=None, selected_stratagems=None):
    global active_mission_config, bomber_enemies, orbital_base
    global wave_manager, health_drops, light_enemy, ground_support_manager
    global mission_start_time, mission_air_kills, mission_bomber_kills
    if mission_config is not None:
        active_mission_config = mission_config

    session = get_campaign_session()
    if mission_config is not None and not mission_config.get(CAMPAIGN_SORTIE_CONFIG_KEY):
        session.abort_flight()
    elif mission_config is None and session.is_flight_active:
        session.restart_flight()

    restore_act3b_weapons(player, story_manager)
    player.pos_x = float(PLAYER_X)
    player.pos_y = float(PLAYER_Y)
    player.x = PLAYER_X
    player.y = PLAYER_Y
    player.angle = 0
    player.velocity_x = float(PLAYER_MOVEMENT_SPEED_X)
    player.velocity_y = float(PLAYER_MOVEMENT_SPEED_Y)
    if player.score > player.highscore:
        player.highscore = player.score
        add_highscore(player.score)
    player.health = player.max_health
    player.invincible = False
    player.invincible_timer = 0
    player.bullets.clear()
    player.used_bullets = 0
    player.shooting = False
    player.reloading = False
    player.rockets.clear()
    active_flares.clear()
    player.used_rockets = 0
    player.rocket_shooting = False
    player.rocket_reloading = False
    player.radar_mode = "CONE"
    ground_support_manager.stop_aiming()
    ground_support_manager.weapon_menu.is_open = False

    player.score = 0
    mission_start_time = pygame.time.get_ticks()
    mission_air_kills = 0
    mission_bomber_kills = 0
    health_drops.clear()
    bomber_enemies.clear()
    wave_manager = WaveManager()

    if active_mission_config.get("id") == MissionType.ACADEMY_TUTORIAL:
        wave_manager.enemies.clear()
        wave_manager.announcement_timer = 0
        wave_manager.wave_announcement = ""
        academy_manager.reset(player)

    if active_mission_config.get("has_base"):
        orbital_base = OrbitalBase(1500, 1500)
    else:
        orbital_base = None

    light_enemy = wave_manager.enemies[0] if wave_manager.enemies else None
    player.shield = PLAYER_MAX_SHIELD
    explosion_group.empty()
    combat_juice.reset()
    if comms_hud is not None:
        comms_hud.dismiss()
    powerup_manager.reset(player)
    ground_support_manager.reset(active_mission_config, selected_stratagems=selected_stratagems)
    audio_manager.play_music("gameplay_normal")


def main_menu(mouse_pos=None):
    canvas.fill((0, 0, 0))
    canvas.blit(main_menu_image, (0, 0))
    canvas.blit(main_menu_side_overlay, (0, 0))
    pygame.draw.rect(canvas, theme.ACCENT_DIM, (560, 0, 2, GAME_HEIGHT))

    _refresh_main_menu_profile_state()
    has_active_save = bool(_menu_profile_state["has_profile"])
    if has_active_save:
        menu_continue_box.set_text(f"CONTINUE : CADET {_menu_profile_state['callsign']}")
        menu_continue_box.set_enabled(True)
    else:
        menu_continue_box.set_text("CONTINUE (NO SERVICE RECORD)")
        menu_continue_box.set_enabled(False)
        if main_menu_nav.focus_index == 1:
            main_menu_nav.move_focus(1)

    canvas.blit(main_menu_title_surf, (96, 96))
    canvas.blit(main_menu_subtitle_surf, (98, 160))
    pygame.draw.rect(canvas, theme.ACCENT, (96, 186, 368, 1))
    main_menu_nav.draw(canvas, mouse_pos)

    if not has_active_save:
        canvas.blit(main_menu_hint_surf, (96, GAME_HEIGHT - 56))
    canvas.blit(main_menu_footer_surf, (96, GAME_HEIGHT - 24 - main_menu_footer_surf.get_height()))

    _draw_menu_toast()


def _draw_menu_toast():
    """Bottom-right status toast (e.g. AUDIO MUTED) shared by the main menu and game-over screen."""
    if menu_toast_text and pygame.time.get_ticks() < menu_toast_until:
        toast = ui_text_cache.render(_mono_small_font, menu_toast_text, theme.INFO)
        canvas.blit(toast, (GAME_WIDTH - 24 - toast.get_width(), GAME_HEIGHT - 24 - toast.get_height()))


def resume_from_pause():
    """Leave the pause menu and drop the frozen backdrop so the next pause captures a fresh frame.

    ``draw()`` also invalidates the snapshot, but the hangar cinematic renders without it.
    """
    global game_state, _pause_snapshot_valid
    _pause_snapshot_valid = False
    game_state = ""


def pause_menu(mouse_pos=None):
    global _pause_snapshot_valid
    if not _pause_snapshot_valid:
        pause_snapshot_surf.blit(canvas, (0, 0))
        _pause_snapshot_valid = True
    canvas.blit(pause_snapshot_surf, (0, 0))
    canvas.blit(pause_dim_overlay, (0, 0))
    widgets.draw_panel(canvas, pause_panel_rect)
    canvas.blit(pause_title_surf, (pause_panel_rect.centerx - pause_title_surf.get_width() // 2, 196))
    pause_nav.draw(canvas, mouse_pos)


def draw(mouse_pos=None):
    global _pause_snapshot_valid
    _pause_snapshot_valid = False
    canvas.fill((0, 0, 0))

    # Calculate camera offset bounded to map dimensions
    if ground_support_manager.super_destroyer.is_active:
        target_cam_x = ground_support_manager.super_destroyer.departure_x + PLAYER_WIDTH / 2 - GAME_WIDTH / 2
        target_cam_y = ground_support_manager.super_destroyer.departure_y + PLAYER_HEIGHT / 2 - GAME_HEIGHT / 2
        camera_x = max(0, min(MAP_WIDTH - GAME_WIDTH, target_cam_x))
        camera_y = max(0, min(MAP_HEIGHT - GAME_HEIGHT, target_cam_y))
    else:
        camera_x = max(0, min(MAP_WIDTH - GAME_WIDTH, player.pos_x + PLAYER_WIDTH / 2 - GAME_WIDTH / 2))
        camera_y = max(0, min(MAP_HEIGHT - GAME_HEIGHT, player.pos_y + PLAYER_HEIGHT / 2 - GAME_HEIGHT / 2))

    # Snap camera to integer pixels; apply screen shake only if enabled in Settings
    if "settings_menu" in globals() and not settings_menu.toggle_screen_shake.state:
        shake_ox, shake_oy = 0, 0
    else:
        shake_ox, shake_oy = combat_juice.get_camera_offset()
    camera_x = int(round(camera_x)) + shake_ox
    camera_y = int(round(camera_y)) + shake_oy
    camera_x = max(0, min(MAP_WIDTH - GAME_WIDTH, camera_x))
    camera_y = max(0, min(MAP_HEIGHT - GAME_HEIGHT, camera_y))

    # Seamless background tiling inside map boundaries
    bg_w, bg_h = backround_image.get_size()
    start_col = max(0, int(camera_x // bg_w))
    end_col = min(int(math.ceil(MAP_WIDTH / bg_w)), int((camera_x + GAME_WIDTH) // bg_w) + 1)
    start_row = max(0, int(camera_y // bg_h))
    end_row = min(int(math.ceil(MAP_HEIGHT / bg_h)), int((camera_y + GAME_HEIGHT) // bg_h) + 1)

    for col in range(start_col, end_col):
        for row in range(start_row, end_row):
            world_tile_x = col * bg_w
            world_tile_y = row * bg_h
            canvas.blit(backround_image, (world_tile_x - camera_x, world_tile_y - camera_y))

    # Draw red border line around world bounds
    border_rect = pygame.Rect(-camera_x, -camera_y, MAP_WIDTH, MAP_HEIGHT)
    pygame.draw.rect(canvas, (255, 60, 60), border_rect, 4)

    if player.health <= 0:
        canvas.blit(pause_dim_overlay, (0, 0))
        widgets.draw_panel(canvas, gameover_panel_rect, accent=theme.DANGER)
        canvas.blit(gameover_title_surf, (gameover_panel_rect.centerx - gameover_title_surf.get_width() // 2, 196))
        canvas.blit(gameover_sub_surf, (gameover_panel_rect.centerx - gameover_sub_surf.get_width() // 2, 244))
        gameover_nav.draw(canvas, mouse_pos)
        _draw_menu_toast()

    else:
        # Draw ground support world entities (Helldivers, obstacles, beacon, airstrikes, supply pods)
        ground_support_manager.draw_world_entities(canvas, camera_x, camera_y, hud_small_font)

        # Draw Academy Tutorial world entities (gates, drones, bunkers)
        if active_mission_config.get("id") == MissionType.ACADEMY_TUTORIAL:
            academy_manager.draw_world(canvas, camera_x, camera_y)

        # Draw Orbital Base if present
        if orbital_base and orbital_base.is_alive:
            orbital_base.draw(canvas, camera_x, camera_y, font)

        # Draw Bomber Enemies
        for bomber in bomber_enemies:
            bomber.draw(canvas, camera_x, camera_y)

        # Draw high-G wingtip vapor contrails and directional hit sparks
        combat_juice.draw(canvas, camera_x, camera_y)

        # Player rendered relative to camera
        screen_player_x = player.pos_x - camera_x
        screen_player_y = player.pos_y - camera_y
        rotated_player_image = pygame.transform.rotate(player.original_image, player.angle)
        player_rect = rotated_player_image.get_rect(
            center=(
                int(round(screen_player_x + PLAYER_WIDTH / 2)),
                int(round(screen_player_y + PLAYER_HEIGHT / 2)),
            )
        )
        canvas.blit(rotated_player_image, player_rect.topleft)

        # Draw player bullets with camera offset
        for bullet in player.bullets:
            b_screen_x = bullet.pos_x - camera_x
            b_screen_y = bullet.pos_y - camera_y
            bullet_rect = bullet.image.get_rect(
                center=(
                    int(round(b_screen_x + BULLET_WIDTH / 2)),
                    int(round(b_screen_y + BULLET_HEIGHT / 2)),
                )
            )
            canvas.blit(bullet.image, bullet_rect.topleft)
            # Subtle visual aura when Damage Multiplier is active
            if powerup_manager.is_active("damage_boost"):
                pygame.draw.circle(
                    canvas,
                    (255, 140, 0),
                    (int(round(b_screen_x + BULLET_WIDTH / 2)), int(round(b_screen_y + BULLET_HEIGHT / 2))),
                    6,
                    1,
                )

        # Draw power-up world drops, escort drone, and swarm micro-missiles
        powerup_manager.draw_world_entities(canvas, camera_x, camera_y, player)

        # Draw player rockets with camera offset
        for rocket in player.rockets:
            r_screen_x = rocket.pos_x - camera_x
            r_screen_y = rocket.pos_y - camera_y
            rocket_rect = rocket.image.get_rect(
                center=(
                    int(round(r_screen_x + ROCKET_WIDTH / 2)),
                    int(round(r_screen_y + ROCKET_HEIGHT / 2)),
                )
            )
            canvas.blit(rocket.image, rocket_rect.topleft)

        missile_defense.draw_flares(canvas, active_flares, camera_x, camera_y)

        # Draw health drops
        for drop in health_drops:
            if not drop.used:
                hx = int(round(drop.pos_x - camera_x))
                hy = int(round(drop.pos_y - camera_y))
                canvas.blit(drop.image, (hx, hy))
                pulse_r = int(14 + 3 * math.sin(pygame.time.get_ticks() * 0.008))
                pygame.draw.circle(canvas, (50, 255, 100), (hx + 12, hy + 12), pulse_r, 1)

        # Draw enemy bullets with camera offset across all wave enemies
        for enemy in wave_manager.enemies:
            for bullet in enemy.bullets:
                b_screen_x = bullet.pos_x - camera_x
                b_screen_y = bullet.pos_y - camera_y
                bullet_rect = bullet.image.get_rect(
                    center=(
                        int(round(b_screen_x + BULLET_WIDTH / 2)),
                        int(round(b_screen_y + BULLET_HEIGHT / 2)),
                    )
                )
                canvas.blit(bullet.image, bullet_rect.topleft)

        # Draw all wave enemies with camera offset & Lock-on Reticles
        primary_enemy = wave_manager.get_closest_enemy(player)
        for enemy in wave_manager.enemies:
            if not enemy.exploding:
                enemy_screen_x = enemy.pos_x - camera_x
                enemy_screen_y = enemy.pos_y - camera_y
                enemy_rect = enemy.image.get_rect(
                    center=(
                        int(round(enemy_screen_x + LIGHT_ENEMY_WIDTH / 2)),
                        int(round(enemy_screen_y + LIGHT_ENEMY_HEIGHT / 2)),
                    )
                )
                canvas.blit(enemy.image, enemy_rect.topleft)

                # Frost / Freeze visual overlay
                if powerup_manager.is_enemy_frozen() and enemy == primary_enemy:
                    canvas.blit(hud_renderer.get_frost_overlay((LIGHT_ENEMY_WIDTH, LIGHT_ENEMY_HEIGHT)), (enemy_screen_x, enemy_screen_y))
                elif powerup_manager.is_enemy_frosted() and enemy == primary_enemy:
                    frost_rect = pygame.Rect(enemy_screen_x, enemy_screen_y, LIGHT_ENEMY_WIDTH, LIGHT_ENEMY_HEIGHT)
                    pygame.draw.rect(canvas, (120, 220, 255), frost_rect, 2)

        # Target lock-on brackets for every radar-locked aerial target (fighters, bombers, drones)
        if player.health > 0:
            mode_tag = "CONE LOCK" if player.radar_mode == "CONE" else "OMNI LOCK"
            lock_label = hud_renderer.get_lock_label(mode_tag)
            for tgt in get_rocket_targets():
                if not player.is_enemy_in_lock_zone(tgt):
                    continue
                sx = tgt.x - camera_x
                sy = tgt.y - camera_y
                if -80 <= sx <= GAME_WIDTH + 80 and -80 <= sy <= GAME_HEIGHT + 80:
                    draw_lock_brackets(canvas, pygame.Rect(int(sx), int(sy), tgt.width, tgt.height), lock_label)

        # Draw explosions with camera offset
        explosion_group.update()
        for explosion in explosion_group:
            exp_screen_x = explosion.rect.x - camera_x
            exp_screen_y = explosion.rect.y - camera_y
            canvas.blit(explosion.image, (exp_screen_x, exp_screen_y))

        # Draw dynamic gun pip & predictive air strike impact reticle
        if player.health > 0:
            extra_tgts = academy_manager.get_combat_targets() if active_mission_config.get("id") == MissionType.ACADEMY_TUTORIAL else None
            ground_support_manager.draw_reticle(canvas, camera_x, camera_y, player, extra_targets=extra_tgts)

        # UI elements (Screen space, fixed overlay)
        campaign_objective_surf = get_campaign_objective_surface()
        hud_renderer.draw_score(canvas, player.score, player.highscore)

        is_academy = active_mission_config.get("id") == MissionType.ACADEMY_TUTORIAL
        hud_renderer.draw_status_panel(
            canvas,
            player.shield, PLAYER_MAX_SHIELD, player.shield > PLAYER_MAX_SHIELD,
            player.health, player.max_health, ADRENALINE_HEALTH_THRESHOLD,
            None if is_academy else wave_manager.wave,
            active_mission_config.get("max_waves", MAX_WAVE_LEVEL),
            None if is_academy else len([e for e in wave_manager.enemies if not getattr(e, 'exploding', False)]),
        )

        # Adrenaline Overdrive HUD indicator (displayed when player is at critical HP)
        if 0 < player.health <= ADRENALINE_HEALTH_THRESHOLD:
            hud_renderer.draw_adrenaline(canvas, pygame.time.get_ticks())

        # Wave announcement banner (centered in upper third of canvas)
        if wave_manager.announcement_timer > 0 and not is_academy:
            hud_renderer.draw_wave_banner(canvas, wave_manager.wave_announcement)

        # Warning Feedback: Vignettes (Zero per-frame allocations) & Heartbeat Audio.
        # The settings toggle only hides the visual vignette; the alarm audio always plays.
        show_warnings = settings_menu.toggle_warnings.state
        if player.health <= 2 and player.health > 0:
            if show_warnings:
                pulse = int(140 + 80 * math.sin(pygame.time.get_ticks() * 0.008))
                vignette_health_surf.fill((0, 0, 0, 0))
                pygame.draw.rect(vignette_health_surf, (220, 20, 20, max(25, min(90, pulse // 3))), (0, 0, GAME_WIDTH, GAME_HEIGHT), width=20)
                canvas.blit(vignette_health_surf, (0, 0))
            audio_manager.play_sfx("low_health")
        elif player.shield <= 5 and player.shield > 0:
            if show_warnings:
                vignette_shield_surf.fill((0, 0, 0, 0))
                pygame.draw.rect(vignette_shield_surf, (0, 200, 255, 30), (0, 0, GAME_WIDTH, GAME_HEIGHT), width=12)
                canvas.blit(vignette_shield_surf, (0, 0))
            audio_manager.play_sfx("low_shield")

        # Weapons panel (cannon ammo, rockets, radar), speed gauge and controls hint
        rocket_ratio = None
        if player.rocket_reloading:
            rocket_ratio = min(1.0, (pygame.time.get_ticks() - player.rocket_reload_start_time) / player.rocket_reloading_time)
        hud_renderer.draw_weapon_panel(
            canvas, int(player.max_bullets - player.used_bullets), player.max_bullets, player.reloading,
            max(0, player.max_rockets - player.used_rockets), player.max_rockets, rocket_ratio, player.radar_mode,
        )
        if settings_menu.toggle_speedometer.state:
            hud_renderer.draw_speed(canvas, player.velocity_x, player.max_speed)
        hud_renderer.draw_controls_hint(canvas)

        # --- MINIMAP UI ---
        mm_x, mm_y = hud_layout.MINIMAP_RECT.topleft
        minimap_surface = hud_renderer.get_minimap_surface(minimap_bg_image)

        # Viewport rectangle on minimap
        view_x = camera_x * MINIMAP_SCALE
        view_y = camera_y * MINIMAP_SCALE
        view_w = GAME_WIDTH * MINIMAP_SCALE
        view_h = GAME_HEIGHT * MINIMAP_SCALE
        pygame.draw.rect(minimap_surface, (0, 200, 255, 220), (view_x, view_y, view_w, view_h), 1)

        # Player dot
        player_mm_x = (player.pos_x + PLAYER_WIDTH / 2) * MINIMAP_SCALE
        player_mm_y = (player.pos_y + PLAYER_HEIGHT / 2) * MINIMAP_SCALE

        # Radar Lock-on Visualisierung auf Minimap
        if player.radar_mode == "CONE":
            cone_len_mm = RADAR_CONE_RANGE * MINIMAP_SCALE
            half_cone = math.radians(RADAR_CONE_ANGLE / 2)
            p_rad = math.radians(player.angle)

            left_rad = p_rad + half_cone
            right_rad = p_rad - half_cone

            p1_x = player_mm_x - math.sin(left_rad) * cone_len_mm
            p1_y = player_mm_y - math.cos(left_rad) * cone_len_mm
            p2_x = player_mm_x - math.sin(right_rad) * cone_len_mm
            p2_y = player_mm_y - math.cos(right_rad) * cone_len_mm

            pygame.draw.line(minimap_surface, (0, 240, 220, 180), (player_mm_x, player_mm_y), (p1_x, p1_y), 1)
            pygame.draw.line(minimap_surface, (0, 240, 220, 180), (player_mm_x, player_mm_y), (p2_x, p2_y), 1)
            pygame.draw.line(minimap_surface, (0, 240, 220, 130), (p1_x, p1_y), (p2_x, p2_y), 1)

        elif player.radar_mode == "OMNI":
            omni_r_mm = RADAR_OMNI_RANGE * MINIMAP_SCALE
            half = math.radians(missile_defense.RADAR_OMNI_HALF_ANGLE)
            p_rad = math.radians(player.angle)
            omni_color = (255, 140, 40, 190)
            for edge in (p_rad + half, p_rad - half):
                ex = player_mm_x - math.sin(edge) * omni_r_mm
                ey = player_mm_y - math.cos(edge) * omni_r_mm
                pygame.draw.line(minimap_surface, omni_color, (player_mm_x, player_mm_y), (ex, ey), 1)
            arc_rect = pygame.Rect(
                int(player_mm_x - omni_r_mm), int(player_mm_y - omni_r_mm), int(omni_r_mm * 2), int(omni_r_mm * 2)
            )
            center_math = p_rad + math.pi / 2  # screen-forward expressed in pygame.draw.arc angle space
            pygame.draw.arc(minimap_surface, omni_color, arc_rect, center_math - half, center_math + half, 1)

        # Power-ups as glowing dots on minimap
        powerup_manager.draw_minimap_blips(minimap_surface, MINIMAP_SCALE)

        # Helldiver squad and beacon blips on minimap
        ground_support_manager.draw_minimap(minimap_surface, MINIMAP_SCALE)

        # Academy tutorial training targets and objectives on minimap
        if active_mission_config.get("id") == MissionType.ACADEMY_TUTORIAL:
            academy_manager.draw_minimap(minimap_surface, MINIMAP_SCALE)

        # Player dot (Grün)
        pygame.draw.circle(minimap_surface, (0, 255, 100), (int(player_mm_x), int(player_mm_y)), 4)

        # Enemy dots (Red for Agro, Orange for Patrol) across all wave enemies
        for enemy in wave_manager.enemies:
            if not getattr(enemy, 'exploding', False) and getattr(enemy, 'health', 0) > 0:
                enemy_mm_x = (enemy.x + LIGHT_ENEMY_WIDTH / 2) * MINIMAP_SCALE
                enemy_mm_y = (enemy.y + LIGHT_ENEMY_HEIGHT / 2) * MINIMAP_SCALE
                dot_color = (255, 40, 40) if enemy.state == "AGRO" else (255, 170, 0)
                pygame.draw.circle(minimap_surface, dot_color, (int(enemy_mm_x), int(enemy_mm_y)), 3)

        # Bomber dots (Large Flashing Red/Orange Squares)
        for bomber in bomber_enemies:
            if not bomber.exploding and bomber.health > 0:
                bx = (bomber.pos_x + 32) * MINIMAP_SCALE
                by = (bomber.pos_y + 26) * MINIMAP_SCALE
                pygame.draw.rect(minimap_surface, (255, 60, 20), (int(bx - 3), int(by - 3), 6, 6))

        # Orbital Base on minimap
        if orbital_base and orbital_base.is_alive:
            obx = (orbital_base.pos_x + 60) * MINIMAP_SCALE
            oby = (orbital_base.pos_y + 60) * MINIMAP_SCALE
            pygame.draw.circle(minimap_surface, (0, 220, 255), (int(obx), int(oby)), 5, 2)

        canvas.blit(minimap_surface, (mm_x, mm_y))
        hud_renderer.draw_minimap_frame(canvas)

        # --- POWER-UP HUD OVERLAY ---
        powerup_manager.draw_hud(canvas, GAME_WIDTH, GAME_HEIGHT)

        # --- GROUND SUPPORT HUD OVERLAY & WEAPON ARSENAL ---
        ground_support_manager.draw_hud(canvas, GAME_WIDTH, GAME_HEIGHT, font, title_font, speed_font, hud_small_font, player, mouse_pos)

        # --- ACADEMY TUTORIAL HUD OVERLAY ---
        if active_mission_config.get("id") == MissionType.ACADEMY_TUTORIAL:
            academy_manager.draw_hud(canvas, player)

        # --- MISSION OBJECTIVE HUD BANNER ---
        obj_text = f"OBJECTIVE: {active_mission_config['name']}"
        if active_mission_config["id"] == MissionType.ACADEMY_TUTORIAL:
            obj_text = f"OBJECTIVE: {academy_manager.get_active_drill_title()}"
        elif active_mission_config["id"] == MissionType.BASE_DEFENSE and orbital_base:
            if ground_support_manager.objective_phase == "EXTRACTION":
                obj_text = "OBJECTIVE: BASE DEFENDED! FLY TO EXTRACTION BEACON"
            else:
                hp_pct = max(0, int((orbital_base.health / orbital_base.max_health) * 100))
                max_w = active_mission_config.get("max_waves", 5)
                obj_text = f"OBJECTIVE: DEFEND BASE [HULL: {hp_pct}% | SHIELD: {int(orbital_base.shield)}] (WAVE {wave_manager.wave}/{max_w})"
        elif active_mission_config["id"] == MissionType.STRIDER_RAID:
            if ground_support_manager.objective_phase == "EXTRACTION":
                obj_text = "OBJECTIVE: STRIDER DESTROYED! ESCORT SQUAD TO EXTRACTION"
            elif ground_support_manager.factory_strider and ground_support_manager.factory_strider.is_alive:
                hp = int(ground_support_manager.factory_strider.health)
                obj_text = f"OBJECTIVE: DESTROY FACTORY STRIDER [HP: {hp}/300]"
            else:
                obj_text = "OBJECTIVE: FACTORY STRIDER DESTROYED!"
        elif active_mission_config["id"] == MissionType.OUTPOST_DEMOLITION:
            if ground_support_manager.objective_phase == "EXTRACTION":
                obj_text = "OBJECTIVE: OUTPOST DEMOLISHED! ESCORT SQUAD TO EXTRACTION"
            else:
                rem = len(ground_support_manager.enemy_fabricators)
                obj_text = f"OBJECTIVE: DEMOLISH FABRICATORS [{rem} REMAINING]"
        elif active_mission_config["id"] == MissionType.AIR_SUPERIORITY:
            if ground_support_manager.objective_phase == "EXTRACTION":
                obj_text = "OBJECTIVE: AIRSPACE SECURED! FLY TO EXTRACTION BEACON"
            else:
                obj_text = f"OBJECTIVE: AIR SUPERIORITY [WAVE {wave_manager.wave}/{active_mission_config.get('max_waves', 5)}]"

        hud_renderer.draw_objective_banner(canvas, obj_text, active_mission_config.get("icon_color", theme.ACCENT))

        # --- CAMPAIGN NARRATIVE OBJECTIVE (campaign sorties only) ---
        if campaign_objective_surf is not None:
            hud_renderer.draw_campaign_objective(canvas, campaign_objective_surf)

        # --- SLOW-MOTION VIGNETTE OVERLAY ---
        if ground_support_manager.is_slow_mo:
            canvas.blit(hud_renderer.get_slowmo_overlay(), (0, 0))

        # In-Flight Radio Transceiver Overlay
        if comms_hud.is_active:
            comms_hud.render(canvas)


player = Player()
wave_manager = WaveManager()
health_drops = []
ground_support_manager = GroundSupportManager()
combat_juice = CombatJuiceManager()
story_manager = StoryManager(audio_manager=audio_manager)
comms_hud = CommsHUD(story_manager=story_manager, audio_manager=audio_manager, screen_width=GAME_WIDTH, screen_height=GAME_HEIGHT)
super_destroyer_view = SuperDestroyerView(
    story_manager=story_manager,
    audio_manager=audio_manager,
    screen_width=GAME_WIDTH,
    screen_height=GAME_HEIGHT,
)
ground_support_manager.set_story_manager(story_manager)
ground_support_manager.set_comms_hud(comms_hud)
light_enemy = wave_manager.enemies[0] if wave_manager.enemies else Light_Enemy()
player.bullets = []
player.rockets = []
explosion_group = pygame.sprite.Group()


campaign_session = CampaignSortieSession(story_manager=story_manager, comms_hud=comms_hud)


def get_campaign_session():
    """Return the campaign session, rebinding it if the module-level StoryManager was replaced."""
    if campaign_session.story_manager is not story_manager:
        campaign_session.bind_story_manager(story_manager)
    if campaign_session.player is not player:
        campaign_session.attach_player(player)
    return campaign_session


cinematic_player = CinematicPlayer(GAME_WIDTH, GAME_HEIGHT, audio_manager=audio_manager)
FINALE_ENTER_AUDIO_FADE_MS = 600
FINALE_EXIT_AUDIO_FADE_MS = 400
_FINALE_CLEARED_EVENTS = [pygame.KEYDOWN, pygame.KEYUP, pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP]


def _clear_input_events():
    """Drop queued key and mouse events so a finale key press cannot fire on the next screen."""
    try:
        pygame.event.clear(_FINALE_CLEARED_EVENTS)
    except (pygame.error, AttributeError):
        pass


def _stop_flight_input():
    """Release every held flight control before a cutscene takes over the screen."""
    player.shooting = False
    player.rocket_shooting = False
    player.reloading = False
    player.rocket_reloading = False
    ground_support_manager.stop_aiming()
    ground_support_manager.weapon_menu.is_open = False


def start_campaign_finale():
    """Enter the Act III ending cinematic; returns the ending branch, or None if already playing."""
    global game_state
    if game_state == "cinematic":
        return None
    _stop_flight_input()
    comms_hud.dismiss()
    restore_act3b_weapons(player, None)
    audio_manager.stop_cinematic_audio(fade_ms=FINALE_ENTER_AUDIO_FADE_MS)
    _clear_input_events()
    branch = get_campaign_session().start_act3_climax_cinematic(cinematic_player)
    game_state = "cinematic"
    return branch


def finish_campaign_finale():
    """Leave the ending cinematic: fade the audio, mark the finale done and return to the main menu."""
    audio_manager.stop_cinematic_audio(fade_ms=FINALE_EXIT_AUDIO_FADE_MS)
    mark_campaign_finale_completed(story_manager)
    cinematic_player.reset()
    super_destroyer_view.set_act3_briefing(None, None)
    _clear_input_events()
    return_to_main_menu()


def handle_cinematic_keydown(event):
    """Route one key press during the ending cinematic; True when the pilot returned to the main menu."""
    if cinematic_player.handle_event(event) == CINEMATIC_ACTION_RETURN_MAIN_MENU:
        finish_campaign_finale()
        return True
    return False


def check_act3_finale_transition():
    """Start the ending cinematic once the resolved Act III climax may end; True if it started."""
    if game_state != "":
        return False
    session = get_campaign_session()
    if not session.is_act3_flight:
        return False
    center_x = player.pos_x + PLAYER_WIDTH / 2
    center_y = player.pos_y + PLAYER_HEIGHT / 2
    if not session.is_act3_climax_complete(center_x, center_y, player.velocity_x, player.min_speed, player.health > 0):
        return False
    start_campaign_finale()
    return True


CAMPAIGN_OBJECTIVE_MAX_CHARS = 110
CAMPAIGN_OBJECTIVE_COLOR = (200, 225, 240)
_campaign_objective_cache = {"text": None, "surface": None}


def get_campaign_objective_surface():
    """Return a cached HUD surface for the active campaign objective, or None outside campaign flights."""
    text = get_campaign_session().get_objective_text()
    if not text:
        return None
    if _campaign_objective_cache["text"] != text:
        if len(text) <= CAMPAIGN_OBJECTIVE_MAX_CHARS:
            display = text
        else:
            display = text[: CAMPAIGN_OBJECTIVE_MAX_CHARS - 3].rstrip() + "..."
        _campaign_objective_cache["text"] = text
        _campaign_objective_cache["surface"] = hud_small_font.render(f"> {display}", True, CAMPAIGN_OBJECTIVE_COLOR)
    return _campaign_objective_cache["surface"]


def return_to_main_menu():
    """Transition cleanly into the main menu state, aborting any active campaign flight."""
    global game_state
    invalidate_main_menu_profile_state()
    session = get_campaign_session()
    if session.is_flight_active:
        session.abort_flight()
    audio_manager.stop_engine_sound()
    audio_manager.play_music("menu_theme")
    game_state = "main_menu"


def enter_super_destroyer(debrief_results=None):
    """Transition cleanly into the Super Destroyer hub deck state."""
    global game_state
    audio_manager.stop_engine_sound()
    audio_manager.play_music("menu_theme")
    player.shooting = False
    player.rocket_shooting = False
    player.reloading = False
    player.rocket_reloading = False
    ground_support_manager.stop_aiming()
    ground_support_manager.weapon_menu.is_open = False
    super_destroyer_view.on_enter_hub(debrief_results)
    act3_cfg, act3_npc = get_campaign_session().get_act3_hub_briefing()
    super_destroyer_view.set_act3_briefing(act3_cfg, act3_npc)
    game_state = "super_destroyer"


def return_to_super_destroyer_from_debrief():
    """Record campaign sortie completion, then return to the Super Destroyer hub with the debrief stats."""
    raw_results = getattr(debriefing_screen, "results", None)
    debrief_data = dict(raw_results) if isinstance(raw_results, dict) else {}
    debriefing_screen.close()
    progression = get_campaign_session().complete_sortie(debrief_data)
    enter_super_destroyer(debrief_data)
    return progression


def start_new_campaign():
    """Reset the story campaign for a newly enlisted pilot (Act I, no finale, no Act III state)."""
    story_manager.reset_campaign()
    get_campaign_session().bind_story_manager(story_manager)
    cinematic_player.reset()
    super_destroyer_view.set_act3_briefing(None, None)


def handle_super_destroyer_action(action):
    """Handle structured action payloads from SuperDestroyerView."""
    global game_state
    if not isinstance(action, dict):
        return None
    act_type = action.get("action")
    if act_type == "launch_sortie":
        if get_campaign_session().should_skip_to_finale_cinematic():
            super_destroyer_view.close_dialogue()
            super_destroyer_view.launch_initiated = False
            start_campaign_finale()
            return action
        sortie_cfg = get_campaign_session().launch_sortie()
        mission_cfg = build_campaign_mission_config(sortie_cfg, MISSION_CONFIGS)
        super_destroyer_view.close_dialogue()
        super_destroyer_view.launch_initiated = False
        super_destroyer_view.hovered_launch = False
        player.shooting = False
        player.rocket_shooting = False
        player.reloading = False
        player.rocket_reloading = False
        ground_support_manager.stop_aiming()
        ground_support_manager.weapon_menu.is_open = False
        try:
            pygame.event.clear([
                pygame.KEYDOWN,
                pygame.KEYUP,
                pygame.MOUSEBUTTONDOWN,
                pygame.MOUSEBUTTONUP,
            ])
        except (pygame.error, AttributeError):
            pass
        respawn(mission_config=mission_cfg)
        game_state = ""
    elif act_type == "dialogue_choice":
        get_campaign_session().resolve_hub_choice(action.get("node_id"), action.get("stance"))
    elif act_type in ("main_menu", "exit_to_menu"):
        return_to_main_menu()
    return action


def activate_main_menu_action(action):
    """Run a main-menu action. Returns True if the game should quit."""
    global game_state, previous_game_state
    if action == "new_game":
        enlistment_screen.reset()
        game_state = "enlistment"
    elif action == "continue":
        if profile_manager.has_active_profile():
            active_prof = profile_manager.load_profile()
            if not active_prof.academy_completed:
                config = MISSION_CONFIGS.get(MissionType.ACADEMY_TUTORIAL, MISSION_CONFIGS[MissionType.ACADEMY_TUTORIAL])
                respawn(mission_config=config)
                game_state = ""
            else:
                enter_super_destroyer()
    elif action == "settings":
        previous_game_state = "main_menu"
        settings_menu.sync_from_manager()
        game_state = "settings_menu"
    elif action == "help":
        previous_game_state = "main_menu"
        game_state = "help_menu"
    elif action == "quit":
        return True
    return False


def handle_main_menu_keydown(event, mouse_pos=None):
    """Handle one KEYDOWN on the main menu. Returns True when the game should quit.

    ESC / Q first moves focus to QUIT TO DESKTOP; a second press quits.
    """
    idx = main_menu_nav.handle_event(event, mouse_pos)
    if idx is not None:
        return bool(activate_main_menu_action(MAIN_MENU_ACTIONS[idx]))
    if event.key == pygame.K_n:
        activate_main_menu_action("new_game")
    elif event.key == pygame.K_c and profile_manager.has_active_profile():
        activate_main_menu_action("continue")
    elif event.key == pygame.K_s:
        enter_super_destroyer()
    elif event.key == pygame.K_h:
        activate_main_menu_action("help")
    elif event.key == pygame.K_o:
        activate_main_menu_action("settings")
    elif event.key in (pygame.K_ESCAPE, pygame.K_q):
        if main_menu_nav.focus_index != MAIN_MENU_QUIT_INDEX:
            main_menu_nav.focus(MAIN_MENU_QUIT_INDEX)
            audio_manager.play_sfx("ui_hover")
        else:
            return True
    elif event.key == pygame.K_m:
        is_muted = audio_manager.toggle_mute()
        show_menu_toast("AUDIO MUTED" if is_muted else "AUDIO UNMUTED")
    return False


def handle_gameover_keydown(event, mouse_pos=None):
    """Handle one KEYDOWN on the game-over screen (player destroyed, game_state == "")."""
    global game_state, previous_game_state
    go_idx = gameover_nav.handle_event(event, mouse_pos)
    if go_idx is not None:
        activate_gameover_action(GAMEOVER_ACTIONS[go_idx])
    elif event.key == pygame.K_m:
        is_muted = audio_manager.toggle_mute()
        show_menu_toast("AUDIO MUTED" if is_muted else "AUDIO UNMUTED")
    elif event.key == pygame.K_r:
        respawn()
    elif event.key == pygame.K_h:
        previous_game_state = ""
        game_state = "help_menu"
    elif event.key == pygame.K_o:
        previous_game_state = ""
        settings_menu.sync_from_manager()
        game_state = "settings_menu"
    elif event.key == pygame.K_SPACE:
        return_to_main_menu()


def activate_pause_action(action):
    """Run a pause-menu action."""
    global game_state, previous_game_state
    if action == "resume":
        resume_from_pause()
    elif action == "help":
        previous_game_state = "pause_menu"
        game_state = "help_menu"
    elif action == "settings":
        previous_game_state = "pause_menu"
        settings_menu.sync_from_manager()
        game_state = "settings_menu"
    elif action == "main_menu":
        return_to_main_menu()


def activate_gameover_action(action):
    """Run a game-over screen action."""
    global game_state, previous_game_state
    if action == "respawn":
        respawn()
    elif action == "help":
        previous_game_state = ""
        game_state = "help_menu"
    elif action == "main_menu":
        return_to_main_menu()


def show_menu_toast(text, duration_ms=1500):
    """Show a short status message in the main menu (e.g. mute feedback)."""
    global menu_toast_text, menu_toast_until
    menu_toast_text = text
    menu_toast_until = pygame.time.get_ticks() + duration_ms


def on_reload_end():
    """End the cannon reload; a disarmed Eagle-1 keeps an empty magazine (Sortie 5B)."""
    if not getattr(player, PLAYER_WEAPONS_DISARMED_ATTR, False):
        player.used_bullets = 0
    player.reloading = False


def on_rocket_reload_end():
    """End the rocket reload; a disarmed Eagle-1 keeps an empty rack (Sortie 5B)."""
    if not getattr(player, PLAYER_WEAPONS_DISARMED_ATTR, False):
        player.used_rockets = 0
    player.rocket_reloading = False


def run_game():
    global window, game_state, previous_game_state, light_enemy, wave_manager, health_drops, ground_support_manager, pending_mission_config
    running = True
    last_wheel_time = 0
    while running:
        state_at_frame_start = game_state
        canvas_mouse_pos = get_canvas_mouse_pos()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                if player.score > player.highscore:
                    add_highscore(player.score)
                running = False
                break
            if game_state == "" and player.health > 0 and event.type == pygame.KEYDOWN:
                if get_campaign_session().handle_comms_keydown(event, ground_support_manager):
                    continue
            if event.type == SHOOTING_END:
                player.shooting = False
            if event.type == ROCKET_SHOOTING_END:
                player.rocket_shooting = False
            if event.type == ADD_SCORE:
                if game_state == "":
                    player.add_score()
            if event.type == LIGHT_ENEMY_SHOOT:
                if game_state == "" and not powerup_manager.is_enemy_frozen():
                    for enemy in wave_manager.enemies:
                        if not enemy.exploding and enemy.health > 0:
                            enemy.set_shoot(player)
            if event.type == RELOAD_END:
                on_reload_end()
            if event.type == ROCKET_RELOAD_END:
                on_rocket_reload_end()
            if event.type == LIGHT_ENEMY_EXPLOSION:
                pass
            if event.type == INVINCIBLE_END:
                player.invincible = False
            if event.type == SHIELD_REGENERATION:
                if powerup_manager.is_active("shield_bubble"):
                    max_s = PLAYER_MAX_SHIELD + SHIELD_BUBBLE_BONUS
                    if player.shield < max_s:
                        player.shield = min(max_s, player.shield + 2)
                        audio_manager.play_sfx("shield_regen", volume_scale=0.6)
                elif player.shield < PLAYER_MAX_SHIELD:
                    if PLAYER_MAX_SHIELD - player.shield > 1:
                        player.shield += 1
                    else:
                        player.shield = PLAYER_MAX_SHIELD
                    audio_manager.play_sfx("shield_regen", volume_scale=0.6)

            # Mouse Wheel / Trackpad Weapon Cycling with debounce for smooth Mac scrolling
            if event.type == pygame.MOUSEWHEEL:
                if game_state == "enlistment":
                    enlistment_screen.handle_event(event, canvas_mouse_pos)
                elif game_state == "" and player.health > 0:
                    now = pygame.time.get_ticks()
                    if now - last_wheel_time > 90:
                        if event.y > 0:
                            ground_support_manager.cycle_weapon(-1)
                            last_wheel_time = now
                        elif event.y < 0:
                            ground_support_manager.cycle_weapon(1)
                            last_wheel_time = now

            if event.type == pygame.MOUSEMOTION:
                if game_state == "settings_menu":
                    settings_menu.handle_event(event, canvas_mouse_pos)
                elif game_state == "enlistment":
                    enlistment_screen.handle_event(event, canvas_mouse_pos)
                elif game_state == "main_menu":
                    main_menu_nav.handle_event(event, canvas_mouse_pos)
                elif game_state == "pause_menu":
                    pause_nav.handle_event(event, canvas_mouse_pos)
                elif game_state == "mission_select":
                    mission_select_menu.handle_event(event, canvas_mouse_pos)
                elif game_state == "stratagem_select":
                    stratagem_select_menu.handle_event(event, canvas_mouse_pos)
                elif game_state == "" and player.health <= 0:
                    gameover_nav.handle_event(event, canvas_mouse_pos)
                elif game_state == "super_destroyer":
                    super_destroyer_view.handle_event(event, canvas_mouse_pos)

            if event.type == pygame.MOUSEBUTTONUP:
                if game_state == "enlistment":
                    enlistment_screen.handle_event(event, canvas_mouse_pos)

            # Maus-Klick Interaktion für Knöpfe & Raketen-Abschuss
            if event.type == pygame.MOUSEBUTTONDOWN:
                if game_state == "settings_menu":
                    action = settings_menu.handle_event(event, canvas_mouse_pos)
                    if action == "close":
                        game_state = previous_game_state

                elif game_state == "help_menu":
                    action = help_menu.handle_event(event, canvas_mouse_pos)
                    if action == "close":
                        game_state = previous_game_state

                elif game_state == "enlistment":
                    action = enlistment_screen.handle_event(event, canvas_mouse_pos)
                    if action == "start_academy":
                        start_new_campaign()
                        respawn(mission_config=MISSION_CONFIGS[MissionType.ACADEMY_TUTORIAL])
                        game_state = ""
                    elif action == "back":
                        game_state = "main_menu"

                elif game_state == "main_menu":
                    idx = main_menu_nav.handle_event(event, canvas_mouse_pos)
                    if idx is not None and activate_main_menu_action(MAIN_MENU_ACTIONS[idx]):
                        running = False

                elif game_state == "mission_select":
                    action = mission_select_menu.handle_event(event, canvas_mouse_pos)
                    if action == "back_to_menu":
                        game_state = "main_menu"
                    elif isinstance(action, dict):
                        pending_mission_config = action
                        game_state = "stratagem_select"

                elif game_state == "stratagem_select":
                    action = stratagem_select_menu.handle_event(event, canvas_mouse_pos)
                    if action == "back_to_missions":
                        game_state = "mission_select"
                    elif isinstance(action, list):
                        respawn(pending_mission_config, selected_stratagems=action)
                        game_state = ""

                elif game_state == "pause_menu":
                    idx = pause_nav.handle_event(event, canvas_mouse_pos)
                    if idx is not None:
                        activate_pause_action(PAUSE_ACTIONS[idx])

                elif game_state == "mission_debriefing":
                    action = debriefing_screen.handle_event(event, canvas_mouse_pos)
                    if action == "replay":
                        debriefing_screen.close()
                        respawn()
                        game_state = ""
                    elif action == "super_destroyer":
                        return_to_super_destroyer_from_debrief()
                    elif action == "mission_select":
                        debriefing_screen.close()
                        session = get_campaign_session()
                        if session.is_flight_active:
                            session.abort_flight()
                        game_state = "mission_select"
                    elif action == "main_menu":
                        debriefing_screen.close()
                        return_to_main_menu()

                elif game_state == "super_destroyer":
                    action = super_destroyer_view.handle_event(event, canvas_mouse_pos)
                    if action is not None:
                        handle_super_destroyer_action(action)

                elif game_state == "":
                    if player.health <= 0:
                        idx = gameover_nav.handle_event(event, canvas_mouse_pos)
                        if idx is not None:
                            activate_gameover_action(GAMEOVER_ACTIONS[idx])
                    else:
                        if ground_support_manager.weapon_menu.is_open:
                            ground_support_manager.weapon_menu.handle_event(event, canvas_mouse_pos)
                        elif event.button == 1:
                            if ground_support_manager.equipped_slot > 0:
                                ground_support_manager.start_aiming()
                        elif event.button == 3:
                            ground_support_manager.stop_aiming()
                            targets = get_rocket_targets()
                            player.set_shoot_rocket(targets)

            # Button release to deploy equipped Stratagem
            if event.type == pygame.MOUSEBUTTONUP:
                if game_state == "settings_menu":
                    settings_menu.handle_event(event, canvas_mouse_pos)
                elif game_state == "" and player.health > 0:
                    if event.button == 1 and ground_support_manager.equipped_slot > 0:
                        ground_support_manager.release_equipped_stratagem(player)

            if event.type == pygame.KEYDOWN:
                # Universal / macOS clean exit: Cmd+Q
                if event.key == pygame.K_q and (event.mod & (pygame.KMOD_META | pygame.KMOD_GUI)):
                    if player.score > player.highscore:
                        add_highscore(player.score)
                    running = False
                    break

                # Fullscreen toggle: Cmd+F or F11
                if (event.key == pygame.K_f and (event.mod & (pygame.KMOD_META | pygame.KMOD_GUI))) or event.key == pygame.K_F11:
                    is_fullscreen = not bool(window.get_flags() & pygame.FULLSCREEN)
                    if is_fullscreen:
                        window = _set_display_mode((0, 0), pygame.FULLSCREEN | pygame.RESIZABLE)
                    else:
                        window = _set_display_mode((GAME_WIDTH, GAME_HEIGHT), pygame.RESIZABLE)
                    continue

                if game_state == "settings_menu":
                    action = settings_menu.handle_event(event, canvas_mouse_pos)
                    if action == "close":
                        game_state = previous_game_state

                elif game_state == "help_menu":
                    action = help_menu.handle_event(event, canvas_mouse_pos)
                    if action == "close":
                        game_state = previous_game_state
                    elif event.key == pygame.K_m:
                        is_muted = audio_manager.toggle_mute()
                        status_str = "MUTED" if is_muted else "UNMUTED"
                        ground_support_manager.add_combat_popup(f"AUDIO {status_str}", player.pos_x, player.pos_y, (255, 80, 80) if is_muted else (80, 255, 120))

                elif game_state == "main_menu":
                    if handle_main_menu_keydown(event, canvas_mouse_pos):
                        running = False

                elif game_state == "enlistment":
                    action = enlistment_screen.handle_event(event, canvas_mouse_pos)
                    if action == "start_academy":
                        start_new_campaign()
                        respawn(mission_config=MISSION_CONFIGS[MissionType.ACADEMY_TUTORIAL])
                        game_state = ""
                    elif action == "back":
                        game_state = "main_menu"

                elif game_state == "mission_select":
                    action = mission_select_menu.handle_event(event, canvas_mouse_pos)
                    if action == "back_to_menu":
                        game_state = "main_menu"
                    elif isinstance(action, dict):
                        pending_mission_config = action
                        game_state = "stratagem_select"
                    elif event.key == pygame.K_m:
                        is_muted = audio_manager.toggle_mute()
                        status_str = "MUTED" if is_muted else "UNMUTED"
                        ground_support_manager.add_combat_popup(f"AUDIO {status_str}", player.pos_x, player.pos_y, (255, 80, 80) if is_muted else (80, 255, 120))

                elif game_state == "stratagem_select":
                    action = stratagem_select_menu.handle_event(event, canvas_mouse_pos)
                    if action == "back_to_missions":
                        game_state = "mission_select"
                    elif isinstance(action, list):
                        respawn(pending_mission_config, selected_stratagems=action)
                        game_state = ""
                    elif event.key == pygame.K_m:
                        is_muted = audio_manager.toggle_mute()
                        status_str = "MUTED" if is_muted else "UNMUTED"
                        ground_support_manager.add_combat_popup(f"AUDIO {status_str}", player.pos_x, player.pos_y, (255, 80, 80) if is_muted else (80, 255, 120))
                
                
                elif game_state == "pause_menu":
                    pause_idx = pause_nav.handle_event(event, canvas_mouse_pos)
                    if pause_idx is not None:
                        activate_pause_action(PAUSE_ACTIONS[pause_idx])
                    elif event.key == pygame.K_p:
                        resume_from_pause()
                    elif event.key == pygame.K_h:
                        previous_game_state = "pause_menu"
                        game_state = "help_menu"
                    elif event.key == pygame.K_o:
                        previous_game_state = "pause_menu"
                        settings_menu.sync_from_manager()
                        game_state = "settings_menu"
                    elif event.key == pygame.K_ESCAPE:
                        return_to_main_menu()
                    elif event.key == pygame.K_m:
                        is_muted = audio_manager.toggle_mute()
                        status_str = "MUTED" if is_muted else "UNMUTED"
                        ground_support_manager.add_combat_popup(f"AUDIO {status_str}", player.pos_x, player.pos_y, (255, 80, 80) if is_muted else (80, 255, 120))

                elif game_state == "mission_debriefing":
                    action = debriefing_screen.handle_event(event, canvas_mouse_pos)
                    if action == "replay":
                        debriefing_screen.close()
                        respawn()
                        game_state = ""
                    elif action == "super_destroyer":
                        return_to_super_destroyer_from_debrief()
                    elif action == "mission_select":
                        debriefing_screen.close()
                        session = get_campaign_session()
                        if session.is_flight_active:
                            session.abort_flight()
                        game_state = "mission_select"
                    elif action == "main_menu":
                        debriefing_screen.close()
                        return_to_main_menu()

                elif game_state == "super_destroyer":
                    action = super_destroyer_view.handle_event(event, canvas_mouse_pos)
                    if action is not None:
                        handle_super_destroyer_action(action)
                    elif event.key == pygame.K_m and not super_destroyer_view.is_dialogue_open:
                        is_muted = audio_manager.toggle_mute()
                        status_str = "MUTED" if is_muted else "UNMUTED"
                        ground_support_manager.add_combat_popup(f"AUDIO {status_str}", player.pos_x, player.pos_y, (255, 80, 80) if is_muted else (80, 255, 120))

                elif game_state == "cinematic":
                    handle_cinematic_keydown(event)

                elif game_state == "":
                    if player.health <= 0:
                        handle_gameover_keydown(event, canvas_mouse_pos)
                    else:
                        if ground_support_manager.objective_phase == "COMPLETE":
                            if event.key == pygame.K_r:
                                respawn()
                            elif event.key == pygame.K_ESCAPE:
                                return_to_main_menu()

                        sdm = ground_support_manager.super_destroyer
                        if sdm.is_active and sdm.phase == PHASE_HANGAR:
                            if event.key in (pygame.K_UP, pygame.K_w):
                                ground_support_manager.handle_hero_input("UP", player)
                            elif event.key in (pygame.K_DOWN, pygame.K_s):
                                ground_support_manager.handle_hero_input("DOWN", player)
                            elif event.key in (pygame.K_LEFT, pygame.K_a):
                                ground_support_manager.handle_hero_input("LEFT", player)
                            elif event.key in (pygame.K_RIGHT, pygame.K_d):
                                ground_support_manager.handle_hero_input("RIGHT", player)
                            elif event.key == pygame.K_p:
                                game_state = "pause_menu"
                            elif event.key == pygame.K_o:
                                previous_game_state = ""
                                settings_menu.sync_from_manager()
                                game_state = "settings_menu"
                            elif event.key == pygame.K_m:
                                is_muted = audio_manager.toggle_mute()
                                status_str = "MUTED" if is_muted else "UNMUTED"
                                ground_support_manager.add_combat_popup(f"AUDIO {status_str}", player.pos_x, player.pos_y, (255, 80, 80) if is_muted else (80, 255, 120))
                        else:
                            if event.key == pygame.K_r:
                                ground_support_manager.trigger_eagle_rearm(player)
                            elif event.key == pygame.K_UP:
                                ground_support_manager.handle_hero_input("UP", player)
                            elif event.key == pygame.K_DOWN:
                                ground_support_manager.handle_hero_input("DOWN", player)
                            elif event.key == pygame.K_LEFT:
                                ground_support_manager.handle_hero_input("LEFT", player)
                            elif event.key == pygame.K_RIGHT:
                                ground_support_manager.handle_hero_input("RIGHT", player)
                            elif event.key == pygame.K_p:
                                game_state = "pause_menu"
                            elif event.key == pygame.K_o:
                                previous_game_state = ""
                                settings_menu.sync_from_manager()
                                game_state = "settings_menu"
                            elif event.key == pygame.K_m:
                                is_muted = audio_manager.toggle_mute()
                                status_str = "MUTED" if is_muted else "UNMUTED"
                                ground_support_manager.add_combat_popup(f"AUDIO {status_str}", player.pos_x, player.pos_y, (255, 80, 80) if is_muted else (80, 255, 120))
                            elif event.key == pygame.K_q:
                                player.toggle_radar_mode()
                            elif event.key in (pygame.K_v, pygame.K_TAB):
                                ground_support_manager.weapon_menu.toggle()
                            elif event.key == pygame.K_ESCAPE:
                                if ground_support_manager.aiming_active:
                                    ground_support_manager.stop_aiming()
                                elif ground_support_manager.weapon_menu.is_open:
                                    ground_support_manager.weapon_menu.is_open = False
                            elif event.key == pygame.K_SPACE:
                                if ground_support_manager.equipped_slot > 0:
                                    ground_support_manager.start_aiming()
                            elif event.key == pygame.K_c:
                                ground_support_manager.trigger_air_strike(player)
                            elif event.key == pygame.K_x:
                                ground_support_manager.trigger_supply_drop(player)
                            elif event.key in (pygame.K_1, pygame.K_0):
                                ground_support_manager.select_weapon_slot(0)
                            elif event.key == pygame.K_2:
                                ground_support_manager.select_weapon_slot(1)
                            elif event.key == pygame.K_3:
                                ground_support_manager.select_weapon_slot(2)
                            elif event.key == pygame.K_4:
                                ground_support_manager.select_weapon_slot(3)
                            elif event.key == pygame.K_5:
                                ground_support_manager.select_weapon_slot(4)

            # Spacebar release to deploy equipped Stratagem
            if event.type == pygame.KEYUP:
                if game_state == "" and player.health > 0:
                    if event.key == pygame.K_SPACE and ground_support_manager.equipped_slot > 0:
                        ground_support_manager.release_equipped_stratagem(player)

        if not running:
            break

        check_act3_finale_transition()

        comms_hud.update(1.0 / 60.0 if (game_state == "" and player.health > 0) else 0.0)
        keys = pygame.key.get_pressed()

        if game_state == "main_menu":
            main_menu(canvas_mouse_pos)

        elif game_state == "enlistment":
            enlistment_screen.draw(canvas, canvas_mouse_pos)

        elif game_state == "mission_select":
            main_menu(None)
            mission_select_menu.draw(canvas, canvas_mouse_pos)

        elif game_state == "stratagem_select":
            main_menu(None)
            stratagem_select_menu.draw(canvas, canvas_mouse_pos)

        elif game_state == "pause_menu":
            pause_menu(canvas_mouse_pos)

        elif game_state == "settings_menu":
            if previous_game_state == "main_menu":
                main_menu(None)
            elif previous_game_state == "pause_menu":
                pause_menu(None)
            else:
                draw(None)
            settings_menu.draw(canvas, canvas_mouse_pos)

        elif game_state == "help_menu":
            if previous_game_state == "main_menu":
                main_menu(None)
            elif previous_game_state == "pause_menu":
                pause_menu(None)
            else:
                draw(None)
            help_menu.draw(canvas, canvas_mouse_pos)

        elif game_state == "mission_debriefing":
            draw(None)
            debriefing_screen.draw(canvas, canvas_mouse_pos)

        elif game_state == "super_destroyer":
            super_destroyer_view.update(1.0 / 60.0)
            super_destroyer_view.draw(canvas, canvas_mouse_pos)

        elif game_state == "cinematic":
            cinematic_player.update(1.0 / 60.0)
            cinematic_player.draw(canvas)

        elif game_state == "":
            if player.health > 0:
                if state_at_frame_start != "":
                    # Transition frame: render canvas only to prevent sticky keys from firing
                    draw(canvas_mouse_pos)
                else:
                    sdm = ground_support_manager.super_destroyer
                    if sdm.is_active:
                        if sdm.phase == PHASE_ASCENT:
                            move()
                            draw(canvas_mouse_pos)
                            sdm.draw(canvas, GAME_WIDTH, GAME_HEIGHT, player)
                        elif sdm.phase == PHASE_HANGAR:
                            # Battlefield combat simulation frozen in orbit
                            ground_support_manager.update(1.0 / 60.0, player, [], explosion_group, large_explosion_a_spritesheet.frames)
                            sdm.draw(canvas, GAME_WIDTH, GAME_HEIGHT, player)
                        elif sdm.phase == PHASE_DESCENT:
                            move()
                            draw(canvas_mouse_pos)
                            sdm.draw(canvas, GAME_WIDTH, GAME_HEIGHT, player)
                    else:
                        turn_rate = player.get_effective_turn_rate() * (0.75 if ground_support_manager.is_slow_mo else 1.0)
                        player_turned_delta = 0.0
                        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
                            player.angle += turn_rate
                            player_turned_delta += turn_rate
                        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
                            player.angle -= turn_rate
                            player_turned_delta -= turn_rate
                        if abs(player_turned_delta) > 0.0:
                            combat_juice.emit_wingtip_contrails(
                                cx=player.pos_x + PLAYER_WIDTH / 2,
                                cy=player.pos_y + PLAYER_HEIGHT / 2,
                                angle_deg=player.angle,
                                speed=player.velocity_x,
                                angular_delta=player_turned_delta,
                                wing_span=21.0,
                                tail_offset=14.0,
                                is_enemy=False,
                            )

                        rad = math.radians(player.angle)
                        dx = -math.sin(rad)
                        dy = -math.cos(rad)

                        if keys[pygame.K_w] or keys[pygame.K_UP]:
                            player.velocity_x = min(player.max_speed, player.velocity_x + player.acceleration)
                            player.velocity_y = min(player.max_speed, player.velocity_y + player.acceleration)
                        elif keys[pygame.K_s] or keys[pygame.K_DOWN]:
                            player.velocity_x = max(player.min_speed, player.velocity_x - player.acceleration)
                            player.velocity_y = max(player.min_speed, player.velocity_y - player.acceleration)

                        steering_factor = (PLAYER_STEERING_SLOW_MO_FACTOR if ground_support_manager.is_slow_mo else 1.0) * comms_hud.get_time_dilation()
                        player.pos_x += dx * player.velocity_x * steering_factor
                        player.pos_y += dy * player.velocity_y * steering_factor

                        player.angle %= 360
                        player.x = int(player.pos_x)
                        player.y = int(player.pos_y)

                        if ground_support_manager.equipped_slot == 0:
                            is_firing = keys[pygame.K_SPACE] or (pygame.mouse.get_pressed()[0] and not ground_support_manager.weapon_menu.is_open)
                            if is_firing and not player.reloading:
                                player.set_shoot()

                        if (keys[pygame.K_e] or (keys[pygame.K_f] and not (keys[pygame.K_LMETA] or keys[pygame.K_RMETA])) or keys[pygame.K_LCTRL]) and not player.rocket_reloading:
                            targets = get_rocket_targets()
                            player.set_shoot_rocket(targets)

                        move()
                        draw(canvas_mouse_pos)
            else:
                draw(canvas_mouse_pos)

        # Background Music & Engine Audio Loop Updates
        if game_state in ("main_menu", "mission_select", "stratagem_select", "mission_debriefing", "super_destroyer"):
            audio_manager.play_music("menu_theme")
            audio_manager.stop_engine_sound()
        elif game_state == "cinematic":
            audio_manager.stop_engine_sound()
        elif game_state in ("pause_menu", "settings_menu", "help_menu"):
            audio_manager.stop_engine_sound()
        elif game_state == "":
            if player.health <= 0:
                audio_manager.play_music("gameover_theme", loop=False)
                audio_manager.stop_engine_sound()
            elif ground_support_manager.super_destroyer.is_active and ground_support_manager.super_destroyer.phase == PHASE_HANGAR:
                audio_manager.stop_engine_sound()
            else:
                # Modulate engine sound with speed
                speed_ratio = (player.velocity_x - player.min_speed) / max(0.1, player.max_speed - player.min_speed)
                audio_manager.update_engine_sound(speed_ratio, is_active=True)

                # Dynamic Music Intensity
                agro_enemies = [e for e in wave_manager.enemies if e.state == "AGRO"]
                is_high_threat = (
                    len(agro_enemies) >= 3 or
                    len(bomber_enemies) > 0 or
                    (ground_support_manager.factory_strider and ground_support_manager.factory_strider.is_alive) or
                    player.health <= 2
                )
                audio_manager.update_dynamic_music("intense" if is_high_threat else "normal")

        scale, offset_x, offset_y, scaled_w, scaled_h = get_display_scale_and_offset()
        win_w, win_h = window.get_size()
        if scaled_w == win_w and scaled_h == win_h:
            scaled_surface = pygame.transform.scale(canvas, (scaled_w, scaled_h))
            window.blit(scaled_surface, (0, 0))
        else:
            window.fill((0, 0, 0))
            scaled_surface = pygame.transform.scale(canvas, (scaled_w, scaled_h))
            window.blit(scaled_surface, (offset_x, offset_y))

        pygame.display.update()
        clock.tick(60)

    pygame.quit()


if __name__ == "__main__":
    run_game()
