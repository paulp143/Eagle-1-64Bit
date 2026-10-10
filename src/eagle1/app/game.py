import math
import os
import random

import pygame

from eagle1.effects import Large_explosion_a, Spritesheet
from eagle1.paths import PROJECT_ROOT, get_user_data_dir, image_search_dirs
from eagle1.systems.audio_manager import get_audio_manager
from eagle1.systems.ground_support import (
    GroundSupportManager,
    PLAYER_STEERING_SLOW_MO_FACTOR,
    SLOW_MO_TIME_SCALE,
    SCORE_EXTRACTION_BONUS,
    StratagemSelectMenu,
)
from eagle1.systems.powerups import (
    DAMAGE_BOOST_MULTIPLIER,
    RAPID_FIRE_COOLDOWN_MS,
    RAPID_FIRE_RELOAD_MS,
    SHIELD_BUBBLE_BONUS,
    PowerUpManager,
)
from eagle1.ui.help_menu import HelpMenu
from eagle1.ui.settings_menu import SettingsMenu
from eagle1.ui.debriefing_screen import DebriefingScreen
from eagle1.systems.hangar_cinematic import (
    PHASE_ASCENT,
    PHASE_HANGAR,
    PHASE_DESCENT,
)

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
PLAYER_ATTACK_DAMAGE_KAMIKAZE = 4
PLAYER_INVINCIBLE_TIME = 1000
PLAYER_MAX_SHIELD = 20
PLAYER_MIN_SPEED = 2.0
PLAYER_MAX_SPEED = 7.0
PLAYER_MOVEMENT_SPEED_Y = PLAYER_MAX_SPEED / 2
PLAYER_MOVEMENT_SPEED_X = PLAYER_MAX_SPEED / 2
PLAYER_ACCELERATION = 0.15
PLAYER_TURN_RATE = 3
PLAYER_BULLET_DAMAGE = 1

BULLET_WIDTH = 9
BULLET_HEIGHT = 12
BULLET_VELOCITY_Y = 8
BULLET_UI_WIDTH = BULLET_WIDTH / 2  # 4 px
BULLET_UI_HEIGHT = BULLET_HEIGHT / 2
BULLET_SHOOTING_TIMER = 100

# Raketen-Parameter (Homing Rocket System)
ROCKET_WIDTH = 12
ROCKET_HEIGHT = 16
ROCKET_VELOCITY = 7.0
ROCKET_TURN_RATE = 2.0         
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
PLAYER_ROCKET_RELOAD_TIME = 25000

SHIELD_UI_WIDTH = 12
SHIELD_UI_HEIGHT = 8
SHIELD_REGENERATION_TIME = 2000

BORDER_TICK_DAMAGE = 0.1

LIGHT_ENEMY_WIDTH = 50
LIGHT_ENEMY_HEIGHT = 46
LIGHT_ENEMY_HEALTH = 4
LIGHT_ENEMY_EXPLOSION_DAMAGE = 5
LIGHT_ENEMY_EXPLOSION_WIDTH = 50
LIGHT_ENEMY_EXPLOSION_HEIGHT = 46
LIGHT_ENEMY_EXPLOSION_TIME = 500
LIGHT_ENEMY_BULLET_VELOCITY_Y = 5
LIGHT_ENEMY_BULLET_SPEED = 5.0
LIGHT_ENEMY_BULLET_DAMAGE = 1
LIGHT_ENEMY_SPEED = 2.5
LIGHT_ENEMY_TURN_RATE = 2.0
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


def load_image(image_path, scale=None):
    if os.path.isabs(image_path) and os.path.exists(image_path):
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

        found = next((path for path in candidates if os.path.exists(path)), None)
        if found is None:
            raise FileNotFoundError(f"Image not found: {image_path}")
        image = pygame.image.load(found)

    if scale is not None:
        image = pygame.transform.scale(image, scale)
    return image


def load_highscore(filepath=HIGHSCORE_FILE):
    try:
        with open(filepath, "r") as file:
            return int(file.read().strip())
    except (FileNotFoundError, ValueError):
        return 0


def add_highscore(new_highscore, filepath=HIGHSCORE_FILE):
    try:
        dir_name = os.path.dirname(filepath)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)
        with open(filepath, "w") as file:
            file.write(str(new_highscore))
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
        self.rect_kwargs = rect_kwargs
        self.update_surface()

    def update_surface(self):
        self.text_surface = self.font.render(self.text, True, self.text_color)
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

    def get_hitbox(self):
        return self.bg_rect if self.bg_rect is not None else self.text_rect

    def is_hovered(self, mouse_pos):
        if mouse_pos is None:
            return False
        return self.get_hitbox().collidepoint(mouse_pos)

    def is_clicked(self, event, mouse_pos):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            clicked = self.is_hovered(mouse_pos)
            if clicked:
                audio_manager.play_sfx("ui_click")
            return clicked
        return False

    def draw(self, surface, mouse_pos=None):
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
light_enemy_image = load_image(os.path.join("images", "enemy1.png"), (LIGHT_ENEMY_WIDTH, LIGHT_ENEMY_HEIGHT))
enemy_bullet_image = load_image(os.path.join("images", "enemy_bullet.png"), (BULLET_WIDTH, BULLET_HEIGHT))
main_menu_image = load_image(os.path.join("images", "20260820_085135933_iOS.webp"), (GAME_WIDTH, GAME_HEIGHT))
backround_image = load_image(os.path.join("images", "newbackround.png"), (GAME_WIDTH, GAME_HEIGHT))

minimap_bg_image = pygame.transform.scale(backround_image, (MINIMAP_BG_WIDTH, MINIMAP_BG_HEIGHT))
light_enemy_explosion_image = load_image(os.path.join("images", "light_enemy_explosion.png"), (LIGHT_ENEMY_WIDTH, LIGHT_ENEMY_HEIGHT))
health_image = load_image(os.path.join("images", "health.png"), (HEALTH_WIDTH, HEALTH_HEIGHT))
bullet_ui_image = load_image(os.path.join("images", "bullet_ui.png"), (BULLET_UI_WIDTH, BULLET_UI_HEIGHT))
large_explosion_a_spritesheet = Spritesheet(load_image(os.path.join("images", "LargeExplosionA_spritesheet.png")), 23)


pygame.init()
try:
    if pygame.mixer.get_init():
        pygame.mixer.set_num_channels(16)
except Exception:
    pass
font = pygame.font.SysFont("arial", 24, bold=True)
title_font = pygame.font.SysFont("arial", 48, bold=True)
speed_font = pygame.font.SysFont("arial", 18, bold=True)
hud_small_font = pygame.font.SysFont("arial", 13, bold=True)
clock = pygame.time.Clock()
window = pygame.display.set_mode((GAME_WIDTH, GAME_HEIGHT), pygame.RESIZABLE)
canvas = pygame.Surface((GAME_WIDTH, GAME_HEIGHT))
frame_number = 23
frame_width = large_explosion_a_spritesheet.sheet.get_width() / 23
frame_height = large_explosion_a_spritesheet.sheet.get_height()
game_state = "main_menu"
pygame.display.set_caption("Eagle 1 64Bit")

powerup_manager = PowerUpManager()
ground_support_manager = GroundSupportManager()
help_menu = HelpMenu(GAME_WIDTH, GAME_HEIGHT)
settings_menu = SettingsMenu(GAME_WIDTH, GAME_HEIGHT)
debriefing_screen = DebriefingScreen(GAME_WIDTH, GAME_HEIGHT)
previous_game_state = "main_menu"

# Mission Performance Tracking Variables
mission_start_time = pygame.time.get_ticks()
mission_air_kills = 0
mission_bomber_kills = 0

# =====================================================================
# MISSION SELECTION SYSTEM & FOCUSED OPERATION CONFIGURATIONS
# =====================================================================

class MissionType:
    AIR_SUPERIORITY = "air_superiority"
    BASE_DEFENSE = "base_defense"
    STRIDER_RAID = "strider_raid"
    OUTPOST_DEMOLITION = "outpost_demolition"
    ENDLESS_WAR = "endless_war"

MISSION_CONFIGS = {
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

    def update(self, target_pos=(1500, 1500), speed_factor=1.0):
        if self.exploding:
            return
        tx, ty = target_pos
        dx = tx - (self.pos_x + 32)
        dy = ty - (self.pos_y + 26)
        dist = max(1.0, math.hypot(dx, dy))

        desired_angle = math.degrees(math.atan2(-dx, -dy)) % 360
        self.angle = desired_angle

        self.pos_x += (dx / dist) * self.speed * speed_factor
        self.pos_y += (dy / dist) * self.speed * speed_factor
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


class MissionSelectMenu:
    """Tactical Operational Mission Selection Interface."""
    def __init__(self):
        self.card_rects = {}

    def handle_event(self, event, mouse_pos=None):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_1:
                return MISSION_CONFIGS[MissionType.AIR_SUPERIORITY]
            elif event.key == pygame.K_2:
                return MISSION_CONFIGS[MissionType.BASE_DEFENSE]
            elif event.key == pygame.K_3:
                return MISSION_CONFIGS[MissionType.STRIDER_RAID]
            elif event.key == pygame.K_4:
                return MISSION_CONFIGS[MissionType.OUTPOST_DEMOLITION]
            elif event.key == pygame.K_5:
                return MISSION_CONFIGS[MissionType.ENDLESS_WAR]
            elif event.key == pygame.K_ESCAPE:
                return "back_to_menu"

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and mouse_pos:
            for m_id, rect in self.card_rects.items():
                if rect.collidepoint(mouse_pos):
                    return MISSION_CONFIGS[m_id]

        return None

    def draw(self, surface, mouse_pos=None):
        bg_surf = pygame.Surface((GAME_WIDTH, GAME_HEIGHT), pygame.SRCALPHA)
        bg_surf.fill((10, 14, 22, 245))
        surface.blit(bg_surf, (0, 0))

        title_font_lg = pygame.font.SysFont("arial", 28, bold=True)
        sub_font = pygame.font.SysFont("arial", 13)
        title_txt = title_font_lg.render("TACTICAL OPERATION SELECTOR", True, (0, 220, 255))
        surface.blit(title_txt, (GAME_WIDTH // 2 - title_txt.get_width() // 2, 25))

        sub_txt = sub_font.render("SELECT A FOCUSED OPERATION TO DEPLOY (HOTKEYS 1-5 OR CLICK CARD)", True, (160, 185, 210))
        surface.blit(sub_txt, (GAME_WIDTH // 2 - sub_txt.get_width() // 2, 58))

        card_w = 360
        card_h = 160
        card_positions = [
            (240, 95, MissionType.AIR_SUPERIORITY),
            (680, 95, MissionType.BASE_DEFENSE),
            (240, 275, MissionType.STRIDER_RAID),
            (680, 275, MissionType.OUTPOST_DEMOLITION),
            (460, 455, MissionType.ENDLESS_WAR),
        ]

        self.card_rects.clear()

        for idx, (cx, cy, m_id) in enumerate(card_positions):
            config = MISSION_CONFIGS[m_id]
            rect = pygame.Rect(cx, cy, card_w, card_h)
            self.card_rects[m_id] = rect

            is_hover = mouse_pos and rect.collidepoint(mouse_pos)
            bg_col = (25, 34, 48) if not is_hover else (38, 52, 75)
            border_col = config["icon_color"] if is_hover else (70, 95, 130)

            pygame.draw.rect(surface, bg_col, rect, border_radius=8)
            pygame.draw.rect(surface, border_col, rect, 2 if not is_hover else 3, border_radius=8)

            key_txt = hud_small_font.render(f"[{idx+1}]", True, (255, 215, 0))
            surface.blit(key_txt, (cx + 12, cy + 10))

            cat_txt = hud_small_font.render(config["category"], True, config["icon_color"])
            surface.blit(cat_txt, (cx + 42, cy + 10))

            name_txt = font.render(config["name"], True, (255, 255, 255))
            surface.blit(name_txt, (cx + 12, cy + 28))

            diff_col = (46, 204, 113) if config["difficulty"] == "MEDIUM" else (241, 196, 15) if config["difficulty"] == "HARD" else (231, 76, 60)
            diff_txt = hud_small_font.render(f"DIFFICULTY: {config['difficulty']}", True, diff_col)
            surface.blit(diff_txt, (cx + card_w - diff_txt.get_width() - 12, cy + 10))

            words = config["desc"].split(" ")
            line1 = " ".join(words[:len(words)//2 + 1])
            line2 = " ".join(words[len(words)//2 + 1:])
            l1_surf = hud_small_font.render(line1, True, (190, 210, 230))
            l2_surf = hud_small_font.render(line2, True, (190, 210, 230))
            surface.blit(l1_surf, (cx + 12, cy + 65))
            surface.blit(l2_surf, (cx + 12, cy + 82))

            btn_col = (0, 220, 255) if is_hover else (120, 150, 180)
            btn_txt = hud_small_font.render("CLICK TO DEPLOY MISSION ▶", True, btn_col)
            surface.blit(btn_txt, (cx + card_w // 2 - btn_txt.get_width() // 2, cy + card_h - 22))

        esc_txt = sub_font.render("PRESS ESC TO RETURN TO MAIN MENU", True, (140, 160, 180))
        surface.blit(esc_txt, (GAME_WIDTH // 2 - esc_txt.get_width() // 2, GAME_HEIGHT - 30))


mission_select_menu = MissionSelectMenu()
stratagem_select_menu = StratagemSelectMenu()
pending_mission_config = None
bomber_enemies = []
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


# UI TextBoxes & Buttons vorbereiten
title_box = TextBox(
    "Eagle 1 64Bit",
    title_font,
    bg_color="Black",
    padding=(40, 40),
    border_radius=8,
    centerx=GAME_WIDTH/2,
    bottom=GAME_HEIGHT*0.2
)

menu_play_box = TextBox(
    "To play press SHIFT",
    font,
    bg_color=(20, 25, 35),
    hover_bg_color=(40, 60, 100),
    border_color=(80, 100, 140),
    hover_border_color=(0, 200, 255),
    padding=(30, 16),
    border_radius=8,
    centerx=GAME_WIDTH/2,
    bottom=GAME_HEIGHT/2+35
)

menu_help_box = TextBox(
    "Help & Weapons Guide: Press H",
    font,
    bg_color=(20, 25, 35),
    hover_bg_color=(20, 70, 110),
    border_color=(80, 100, 140),
    hover_border_color=(0, 220, 255),
    padding=(26, 14),
    border_radius=8,
    centerx=GAME_WIDTH/2,
    bottom=GAME_HEIGHT/2+90
)

menu_settings_box = TextBox(
    "Settings & Audio: Press O",
    font,
    bg_color=(20, 25, 35),
    hover_bg_color=(20, 70, 110),
    border_color=(80, 100, 140),
    hover_border_color=(0, 220, 255),
    padding=(26, 14),
    border_radius=8,
    centerx=GAME_WIDTH/2,
    bottom=GAME_HEIGHT/2+145
)

menu_reset_box = TextBox(
    "Hold L-SHIFT + R-SHIFT + R to reset Highscore",
    font,
    bg_color=(20, 25, 35),
    hover_bg_color=(80, 30, 30),
    border_color=(80, 100, 140),
    hover_border_color=(255, 80, 80),
    padding=(24, 12),
    border_radius=8,
    centerx=GAME_WIDTH/2,
    bottom=GAME_HEIGHT/2+200
)

pause_title_box = TextBox(
    "Pause",
    font,
    bg_color=(30, 35, 50),
    padding=(30, 14),
    border_radius=8,
    centerx=GAME_WIDTH/2,
    bottom=GAME_HEIGHT*0.2
)

pause_continue_box = TextBox(
    "To continue press P",
    font,
    bg_color=(20, 25, 35),
    hover_bg_color=(40, 60, 100),
    border_color=(80, 100, 140),
    hover_border_color=(0, 200, 255),
    padding=(30, 16),
    border_radius=8,
    centerx=GAME_WIDTH/2,
    bottom=GAME_HEIGHT*0.48
)

pause_help_box = TextBox(
    "Help & Weapons Guide: Press H",
    font,
    bg_color=(20, 25, 35),
    hover_bg_color=(20, 70, 110),
    border_color=(80, 100, 140),
    hover_border_color=(0, 220, 255),
    padding=(28, 14),
    border_radius=8,
    centerx=GAME_WIDTH/2,
    bottom=GAME_HEIGHT*0.48+60
)

pause_settings_box = TextBox(
    "Settings & Audio: Press O",
    font,
    bg_color=(20, 25, 35),
    hover_bg_color=(20, 70, 110),
    border_color=(80, 100, 140),
    hover_border_color=(0, 220, 255),
    padding=(28, 14),
    border_radius=8,
    centerx=GAME_WIDTH/2,
    bottom=GAME_HEIGHT*0.48+120
)

pause_menu_box = TextBox(
    "To return to main menu press ESC",
    font,
    bg_color=(20, 25, 35),
    hover_bg_color=(40, 60, 100),
    border_color=(80, 100, 140),
    hover_border_color=(0, 200, 255),
    padding=(30, 16),
    border_radius=8,
    centerx=GAME_WIDTH/2,
    bottom=GAME_HEIGHT*0.48+180
)

gameover_respawn_box = TextBox(
    "Press R to Respawn",
    font,
    bg_color=(20, 25, 35),
    hover_bg_color=(30, 80, 45),
    border_color=(80, 100, 140),
    hover_border_color=(0, 255, 120),
    padding=(30, 16),
    border_radius=8,
    centerx=GAME_WIDTH/2,
    bottom=GAME_HEIGHT/2 - 25
)

gameover_help_box = TextBox(
    "Press H for Help & Weapons Guide",
    font,
    bg_color=(20, 25, 35),
    hover_bg_color=(20, 70, 110),
    border_color=(80, 100, 140),
    hover_border_color=(0, 220, 255),
    padding=(26, 14),
    border_radius=8,
    centerx=GAME_WIDTH/2,
    bottom=GAME_HEIGHT/2 + 35
)

gameover_lobby_box = TextBox(
    "Press SPACE to go back to the Main Menu",
    font,
    bg_color=(20, 25, 35),
    hover_bg_color=(40, 60, 100),
    border_color=(80, 100, 140),
    hover_border_color=(0, 200, 255),
    padding=(30, 16),
    border_radius=8,
    centerx=GAME_WIDTH/2,
    bottom=GAME_HEIGHT/2 + 95
)

score_box = TextBox("Score: 0", font, centerx=GAME_WIDTH//2, bottom=GAME_HEIGHT-10)
highscore_box = TextBox("highscore: 0", font, centerx=GAME_WIDTH//2, bottom=GAME_HEIGHT-30)
speed_box = TextBox("Speed: 0.0 / 0.0", speed_font, topleft=(20, GAME_HEIGHT - MINIMAP_SIZE - 50))

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
            rad = math.radians(angle)
            self.dx = -math.sin(rad) * self.speed
            self.dy = -math.cos(rad) * self.speed

        def update_position(self):
            self.pos_x += self.dx
            self.pos_y += self.dy
            self.x = int(self.pos_x)
            self.y = int(self.pos_y)

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

            if targets is not None:
                if not self.target or getattr(self.target, 'exploding', False) or getattr(self.target, 'health', 0) <= 0:
                    self.lock_on(targets, player=player)

            if self.target and not getattr(self.target, 'exploding', False) and getattr(self.target, 'health', 0) > 0:
                tx = self.target.x + getattr(self.target, 'width', LIGHT_ENEMY_WIDTH) / 2
                ty = self.target.y + getattr(self.target, 'height', LIGHT_ENEMY_HEIGHT) / 2
                cx = self.pos_x + ROCKET_WIDTH / 2
                cy = self.pos_y + ROCKET_HEIGHT / 2

                diff_x = tx - cx
                diff_y = ty - cy

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

    def toggle_radar_mode(self):
        """Wechselt zwischen CONE (Geradeaus-Fernbereich) und OMNI (360°-Nahbereich)."""
        if self.radar_mode == "CONE":
            self.radar_mode = "OMNI"
        else:
            self.radar_mode = "CONE"
        audio_manager.play_sfx("rocket_lock")

    def is_enemy_in_lock_zone(self, enemy):
        """Prüft, ob sich der Gegner im aktiven Radar-Lock-Bereich befindet."""
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
            return dist <= RADAR_OMNI_RANGE

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
        pygame.Rect.__init__(self, int(x), int(y), LIGHT_ENEMY_WIDTH, LIGHT_ENEMY_HEIGHT)
        self.pos_x = float(x)
        self.pos_y = float(y)
        self.x = int(x)
        self.y = int(y)
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
        self.orbit_direction = orbit_direction
        self.orbit_radius = orbit_radius
        self.formation_offset = formation_offset
        self.orbit_angle = math.degrees(math.atan2(self.pos_x - MAP_WIDTH / 2, self.pos_y - MAP_HEIGHT / 2))

    def trigger_agro(self, enemies=None):
        self.state = "AGRO"
        if enemies:
            for other in enemies:
                if getattr(other, 'squadron_id', None) == self.squadron_id and not getattr(other, 'exploding', False):
                    other.state = "AGRO"

    def update(self, target_player=None, enemies=None, speed_factor=1.0):
        if self.exploding:
            return

        # Status effects: EMS stun & smoke screen blindness
        if getattr(self, "stun_timer", 0) > 0:
            self.stun_timer = max(0.0, self.stun_timer - 0.016 * speed_factor)
            return

        if getattr(self, "smoke_blinded", False):
            self.state = "PATROL"
            self.smoke_blinded = False

        target = target_player if target_player is not None else player
        if target is not None and target.health > 0:
            cx = self.pos_x + LIGHT_ENEMY_WIDTH / 2
            cy = self.pos_y + LIGHT_ENEMY_HEIGHT / 2
            pcx = target.pos_x + PLAYER_WIDTH / 2
            pcy = target.pos_y + PLAYER_HEIGHT / 2
            dist_to_player = math.hypot(pcx - cx, pcy - cy)

            # Check Agro Radius
            if self.state == "PATROL":
                if dist_to_player <= ENEMY_AGRO_RADIUS:
                    self.trigger_agro(enemies)
            elif self.state == "AGRO":
                if dist_to_player > ENEMY_DEAGRO_RADIUS:
                    self.state = "PATROL"

            # Determine target angle & speed by state
            if self.state == "AGRO":
                dx = pcx - cx
                dy = pcy - cy
                if dist_to_player < 180.0:
                    # Break-away evasive flight: strafe pass rather than head-on suicide ramming
                    evade_sign = getattr(self, "orbit_direction", 1)
                    target_angle = (math.degrees(math.atan2(dx, dy)) + evade_sign * 75.0) % 360
                    self.speed = ENEMY_AGRO_SPEED * 1.2
                else:
                    self.speed = ENEMY_AGRO_SPEED
                    target_angle = math.degrees(math.atan2(dx, dy))
            else:
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

            # Rotate enemy sprite so it turns to face heading
            angle_diff = (target_angle - self.angle + 180) % 360 - 180
            effective_turn_rate = self.turn_rate * speed_factor
            if abs(angle_diff) <= effective_turn_rate:
                self.angle = target_angle
            elif angle_diff > 0:
                self.angle += effective_turn_rate
            else:
                self.angle -= effective_turn_rate
            self.angle = (self.angle + 180) % 360 - 180

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
        self.wave_announcement = "WAVE 1"
        self.announcement_timer = 180
        self.spawn_wave(1)

    def spawn_wave(self, wave_num):
        max_w = active_mission_config.get("max_waves", MAX_WAVE_LEVEL)
        self.wave = min(wave_num, max_w)
        self.enemies.clear()
        self.state = "ACTIVE"
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
        "flawless_squad": ground_support_manager.flawless_protection,
        "hero_score": ground_support_manager.hero_score,
    }
    debriefing_screen.set_results(results)
    game_state = "mission_debriefing"
    audio_manager.stop_engine_sound()
    audio_manager.play_music("menu_theme")


def move():
    global light_enemy, wave_manager, health_drops
    global explosion_group
    global mission_air_kills, mission_bomber_kills
    if player.health <= 0 or game_state == "mission_debriefing":
        return

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

    # Update power-up subsystem (buff timers, drops, drone, micro-missiles, popups)
    powerup_manager.update(1.0 / 60.0, player, primary_enemy)

    # Update ground support subsystem (Helldivers, airstrikes, supply drops, danger alerts)
    all_air_targets = list(wave_manager.enemies) + list(bomber_enemies)
    ground_support_manager.update(1.0 / 60.0, player, all_air_targets, explosion_group, large_explosion_a_spritesheet.frames)

    if ground_support_manager.objective_phase == "COMPLETE":
        trigger_mission_complete()
        return

    # Update Bomber Enemies & Orbital Base Defense
    if active_mission_config.get("has_bombers"):
        target_pt = (orbital_base.pos_x + 60, orbital_base.pos_y + 60) if (orbital_base and orbital_base.is_alive) else (player.pos_x, player.pos_y)
        for bomber in list(bomber_enemies):
            if not bomber.exploding:
                b_speed_mult = SLOW_MO_TIME_SCALE if ground_support_manager.is_slow_mo else 1.0
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
                enemy.health -= bullet_dmg
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

    # Rocket Update & Collision across all targets (aerial enemies, bombers, ground units, fabricators, strider)
    all_combat_targets = list(wave_manager.enemies) + list(bomber_enemies) + [g for g in ground_support_manager.enemy_ground_units if g.is_alive] + [f for f in ground_support_manager.enemy_fabricators if f.is_alive]
    if ground_support_manager.factory_strider and ground_support_manager.factory_strider.is_alive:
        all_combat_targets.append(ground_support_manager.factory_strider)

    for rocket in player.rockets:
        rocket.update_position(all_combat_targets, player=player)
        if rocket.used:
            range_explosion = Large_explosion_a(
                rocket.x + ROCKET_WIDTH // 2,
                rocket.y + ROCKET_HEIGHT // 2,
                large_explosion_a_spritesheet.frames,
                speed=0.6
            )
            explosion_group.add(range_explosion)
            audio_manager.play_sfx("explosion_small")
        else:
            for enemy in wave_manager.enemies:
                if rocket.colliderect(enemy) and not enemy.exploding:
                    rocket.used = True
                    enemy.health -= rocket.damage
                    enemy.trigger_agro(wave_manager.enemies)
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

            if not rocket.used:
                for ge in ground_support_manager.enemy_ground_units:
                    if ge.is_alive and rocket.colliderect(ge):
                        rocket.used = True
                        ge.take_damage(rocket.damage)
                        if not ge.is_alive:
                            score_val = getattr(ge, 'score_value', 25)
                            player.score += score_val
                            ground_support_manager.add_combat_popup(f"+{score_val} PTS", ge.pos_x, ge.pos_y, (255, 215, 0))
                            audio_manager.play_sfx("enemy_defeat")
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
                for fab in ground_support_manager.enemy_fabricators:
                    if fab.is_alive and rocket.colliderect(fab):
                        rocket.used = True
                        fab.take_damage(rocket.damage)
                        hit_explosion = Large_explosion_a(
                            rocket.x + ROCKET_WIDTH // 2,
                            rocket.y + ROCKET_HEIGHT // 2,
                            large_explosion_a_spritesheet.frames,
                            speed=0.6
                        )
                        explosion_group.add(hit_explosion)
                        audio_manager.play_sfx("explosion")
                        break

    # Player Kamikaze Collision (Absorbed by Shields first, with separation recoil)
    for enemy in wave_manager.enemies:
        if not enemy.exploding and player.colliderect(enemy):
            enemy.health -= player.kamikaze_attack_damage
            player.take_damage(12.0)
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

    # Enemy and enemy bullet movement affected by Time Slow, Frost/Freeze, and Stratagem Aiming Slow-Mo
    slow_mo_mult = SLOW_MO_TIME_SCALE if ground_support_manager.is_slow_mo else 1.0
    speed_factor = powerup_manager.modify_enemy_speed(1.0) * slow_mo_mult
    bullet_speed_factor = powerup_manager.modify_enemy_bullet_speed(1.0) * slow_mo_mult

    for enemy in wave_manager.enemies:
        if not enemy.exploding:
            enemy.update(player, wave_manager.enemies, speed_factor=speed_factor)
        
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

    # Update Wave progression
    wave_manager.update(player)


def respawn(mission_config=None, selected_stratagems=None):
    global active_mission_config, bomber_enemies, orbital_base
    if mission_config is not None:
        active_mission_config = mission_config

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
    player.bullets.clear()
    player.rockets.clear()
    player.used_rockets = 0
    player.rocket_shooting = False
    player.rocket_reloading = False
    player.radar_mode = "CONE"

    player.score = 0
    global wave_manager, health_drops, light_enemy, ground_support_manager
    global mission_start_time, mission_air_kills, mission_bomber_kills
    mission_start_time = pygame.time.get_ticks()
    mission_air_kills = 0
    mission_bomber_kills = 0
    health_drops.clear()
    bomber_enemies.clear()
    wave_manager = WaveManager()

    if active_mission_config.get("has_base"):
        orbital_base = OrbitalBase(1500, 1500)
    else:
        orbital_base = None

    light_enemy = wave_manager.enemies[0] if wave_manager.enemies else None
    player.shield = PLAYER_MAX_SHIELD
    explosion_group.empty()
    powerup_manager.reset(player)
    ground_support_manager.reset(active_mission_config, selected_stratagems=selected_stratagems)
    audio_manager.play_music("gameplay_normal")


def main_menu(mouse_pos=None):
    canvas.fill((0, 0, 0))
    canvas.blit(main_menu_image, (0, 0))

    title_box.draw(canvas, mouse_pos)
    menu_play_box.draw(canvas, mouse_pos)
    menu_help_box.draw(canvas, mouse_pos)
    menu_settings_box.draw(canvas, mouse_pos)
    menu_reset_box.draw(canvas, mouse_pos)


def pause_menu(mouse_pos=None):
    canvas.fill((0, 0, 0))
    canvas.blit(backround_image, (0, 0))

    pause_title_box.draw(canvas, mouse_pos)
    pause_continue_box.draw(canvas, mouse_pos)
    pause_help_box.draw(canvas, mouse_pos)
    pause_settings_box.draw(canvas, mouse_pos)
    pause_menu_box.draw(canvas, mouse_pos)


def draw(mouse_pos=None):
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
        gameover_respawn_box.draw(canvas, mouse_pos)
        gameover_help_box.draw(canvas, mouse_pos)
        gameover_lobby_box.draw(canvas, mouse_pos)
        
    else:
        # Draw ground support world entities (Helldivers, obstacles, beacon, airstrikes, supply pods)
        ground_support_manager.draw_world_entities(canvas, camera_x, camera_y, hud_small_font)

        # Draw Orbital Base if present
        if orbital_base and orbital_base.is_alive:
            orbital_base.draw(canvas, camera_x, camera_y, font)

        # Draw Bomber Enemies
        for bomber in bomber_enemies:
            bomber.draw(canvas, camera_x, camera_y)

        # Player rendered relative to camera
        screen_player_x = player.x - camera_x
        screen_player_y = player.y - camera_y
        rotated_player_image = pygame.transform.rotate(player.original_image, player.angle)
        player_rect = rotated_player_image.get_rect(center=(screen_player_x + PLAYER_WIDTH // 2, screen_player_y + PLAYER_HEIGHT // 2))
        canvas.blit(rotated_player_image, player_rect.topleft)

        # Draw player bullets with camera offset
        for bullet in player.bullets:
            b_screen_x = bullet.x - camera_x
            b_screen_y = bullet.y - camera_y
            bullet_rect = bullet.image.get_rect(center=(b_screen_x + BULLET_WIDTH // 2, b_screen_y + BULLET_HEIGHT // 2))
            canvas.blit(bullet.image, bullet_rect.topleft)
            # Subtle visual aura when Damage Multiplier is active
            if powerup_manager.is_active("damage_boost"):
                pygame.draw.circle(canvas, (255, 140, 0), (int(b_screen_x + BULLET_WIDTH // 2), int(b_screen_y + BULLET_HEIGHT // 2)), 6, 1)

        # Draw power-up world drops, escort drone, and swarm micro-missiles
        powerup_manager.draw_world_entities(canvas, camera_x, camera_y, player)

        # Draw player rockets with camera offset
        for rocket in player.rockets:
            r_screen_x = rocket.x - camera_x
            r_screen_y = rocket.y - camera_y
            rocket_rect = rocket.image.get_rect(center=(r_screen_x + ROCKET_WIDTH // 2, r_screen_y + ROCKET_HEIGHT // 2))
            canvas.blit(rocket.image, rocket_rect.topleft)

        # Draw health drops
        for drop in health_drops:
            if not drop.used:
                hx = drop.x - camera_x
                hy = drop.y - camera_y
                canvas.blit(drop.image, (hx, hy))
                pulse_r = int(14 + 3 * math.sin(pygame.time.get_ticks() * 0.008))
                pygame.draw.circle(canvas, (50, 255, 100), (hx + 12, hy + 12), pulse_r, 1)

        # Draw enemy bullets with camera offset across all wave enemies
        for enemy in wave_manager.enemies:
            for bullet in enemy.bullets:
                b_screen_x = bullet.x - camera_x
                b_screen_y = bullet.y - camera_y
                bullet_rect = bullet.image.get_rect(center=(b_screen_x + BULLET_WIDTH // 2, b_screen_y + BULLET_HEIGHT // 2))
                canvas.blit(bullet.image, bullet_rect.topleft)

        # Draw all wave enemies with camera offset & Lock-on Reticles
        primary_enemy = wave_manager.get_closest_enemy(player)
        for enemy in wave_manager.enemies:
            if not enemy.exploding:
                enemy_screen_x = enemy.x - camera_x
                enemy_screen_y = enemy.y - camera_y
                enemy_rect = enemy.image.get_rect(center=(enemy_screen_x + LIGHT_ENEMY_WIDTH // 2, enemy_screen_y + LIGHT_ENEMY_HEIGHT // 2))
                canvas.blit(enemy.image, enemy_rect.topleft)

                # Frost / Freeze visual overlay
                if powerup_manager.is_enemy_frozen() and enemy == primary_enemy:
                    ice_surf = pygame.Surface((LIGHT_ENEMY_WIDTH, LIGHT_ENEMY_HEIGHT), pygame.SRCALPHA)
                    ice_surf.fill((100, 210, 255, 130))
                    pygame.draw.rect(ice_surf, (220, 245, 255), (0, 0, LIGHT_ENEMY_WIDTH, LIGHT_ENEMY_HEIGHT), 2)
                    canvas.blit(ice_surf, (enemy_screen_x, enemy_screen_y))
                elif powerup_manager.is_enemy_frosted() and enemy == primary_enemy:
                    frost_rect = pygame.Rect(enemy_screen_x, enemy_screen_y, LIGHT_ENEMY_WIDTH, LIGHT_ENEMY_HEIGHT)
                    pygame.draw.rect(canvas, (120, 220, 255), frost_rect, 2)

                # Target Lock-on HUD Reticle
                if player.is_enemy_in_lock_zone(enemy):
                    if -80 <= enemy_screen_x <= GAME_WIDTH + 80 and -80 <= enemy_screen_y <= GAME_HEIGHT + 80:
                        ret_pad = 6
                        ret_len = 8
                        ret_x = enemy_screen_x - ret_pad
                        ret_y = enemy_screen_y - ret_pad
                        ret_w = LIGHT_ENEMY_WIDTH + ret_pad * 2
                        ret_h = LIGHT_ENEMY_HEIGHT + ret_pad * 2

                        ret_color = (255, 60, 60)
                        pygame.draw.line(canvas, ret_color, (ret_x, ret_y), (ret_x + ret_len, ret_y), 2)
                        pygame.draw.line(canvas, ret_color, (ret_x, ret_y), (ret_x, ret_y + ret_len), 2)
                        pygame.draw.line(canvas, ret_color, (ret_x + ret_w, ret_y), (ret_x + ret_w - ret_len, ret_y), 2)
                        pygame.draw.line(canvas, ret_color, (ret_x + ret_w, ret_y), (ret_x + ret_w, ret_y + ret_len), 2)
                        pygame.draw.line(canvas, ret_color, (ret_x, ret_y + ret_h), (ret_x + ret_len, ret_y + ret_h), 2)
                        pygame.draw.line(canvas, ret_color, (ret_x, ret_y + ret_h), (ret_x, ret_y + ret_h - ret_len), 2)
                        pygame.draw.line(canvas, ret_color, (ret_x + ret_w, ret_y + ret_h), (ret_x + ret_w - ret_len, ret_y + ret_h), 2)
                        pygame.draw.line(canvas, ret_color, (ret_x + ret_w, ret_y + ret_h), (ret_x + ret_w, ret_y + ret_h - ret_len), 2)

                        mode_tag = "CONE LOCK" if player.radar_mode == "CONE" else "OMNI LOCK"
                        lock_text = hud_small_font.render(mode_tag, True, (255, 80, 80))
                        canvas.blit(lock_text, (ret_x + ret_w // 2 - lock_text.get_width() // 2, ret_y - 14))

        # Draw explosions with camera offset
        explosion_group.update()
        for explosion in explosion_group:
            exp_screen_x = explosion.rect.x - camera_x
            exp_screen_y = explosion.rect.y - camera_y
            canvas.blit(explosion.image, (exp_screen_x, exp_screen_y))

        # Draw dynamic gun pip & predictive air strike impact reticle
        if player.health > 0:
            ground_support_manager.draw_reticle(canvas, camera_x, camera_y, player)

        # UI elements (Screen space, fixed overlay)
        score_box.set_text(f"Score: {player.score}")
        score_box.draw(canvas)

        highscore_box.set_text(f"highscore: {player.highscore}")
        highscore_box.draw(canvas)

        # Wave Counter HUD Box
        # Modern Prominent Health & Shield Gauges (Upper Left, x=24)
        gauge_x = 24
        gauge_y = 18
        gauge_w = 210
        gauge_h = 13

        # Shield Gauge
        pygame.draw.rect(canvas, (14, 20, 32), (gauge_x, gauge_y, gauge_w, gauge_h), border_radius=4)
        pygame.draw.rect(canvas, (50, 75, 110), (gauge_x, gauge_y, gauge_w, gauge_h), 1, border_radius=4)
        sh_pct = max(0.0, min(1.0, player.shield / PLAYER_MAX_SHIELD))
        sh_col = (255, 180, 0) if player.shield > PLAYER_MAX_SHIELD else (0, 220, 255)
        pygame.draw.rect(canvas, sh_col, (gauge_x + 1, gauge_y + 1, int((gauge_w - 2) * sh_pct), gauge_h - 2), border_radius=3)
        sh_lbl = hud_small_font.render(f"SHIELD: {int(player.shield)}/{PLAYER_MAX_SHIELD}", True, (255, 255, 255))
        canvas.blit(sh_lbl, (gauge_x + gauge_w // 2 - sh_lbl.get_width() // 2, gauge_y - 1))

        # Hull Armor Gauge
        hull_y = gauge_y + gauge_h + 5
        pygame.draw.rect(canvas, (14, 20, 32), (gauge_x, hull_y, gauge_w, gauge_h), border_radius=4)
        pygame.draw.rect(canvas, (50, 75, 110), (gauge_x, hull_y, gauge_w, gauge_h), 1, border_radius=4)
        hp_pct = max(0.0, min(1.0, player.health / player.max_health))
        hp_col = (46, 204, 113) if player.health > 2 else (255, 60, 60)
        pygame.draw.rect(canvas, hp_col, (gauge_x + 1, hull_y + 1, int((gauge_w - 2) * hp_pct), gauge_h - 2), border_radius=3)
        hp_lbl = hud_small_font.render(f"HULL ARMOR: {int(player.health)}/{player.max_health}", True, (255, 255, 255))
        canvas.blit(hp_lbl, (gauge_x + gauge_w // 2 - hp_lbl.get_width() // 2, hull_y - 1))

        # Wave Counter HUD Box (Adjacent to Gauges at x=248)
        living_count = len([e for e in wave_manager.enemies if not getattr(e, 'exploding', False)])
        wave_box_w = 165
        wave_box_h = 42
        wave_box_x = 248
        wave_box_y = 16
        pygame.draw.rect(canvas, (18, 24, 36), (wave_box_x, wave_box_y, wave_box_w, wave_box_h), border_radius=6)
        pygame.draw.rect(canvas, (60, 90, 130), (wave_box_x, wave_box_y, wave_box_w, wave_box_h), 1, border_radius=6)

        wave_label = font.render(f"WAVE {wave_manager.wave}/{MAX_WAVE_LEVEL}", True, (255, 215, 0))
        canvas.blit(wave_label, (wave_box_x + 8, wave_box_y + 3))

        hostiles_label = hud_small_font.render(f"HOSTILES: {living_count}", True, (255, 100, 100) if living_count > 0 else (100, 255, 100))
        canvas.blit(hostiles_label, (wave_box_x + 8, wave_box_y + 24))

        # Adrenaline Overdrive HUD indicator (displayed when player is at critical HP)
        if 0 < player.health <= ADRENALINE_HEALTH_THRESHOLD:
            adren_pulse = int(180 + 75 * math.sin(pygame.time.get_ticks() * 0.01))
            adren_surf = hud_small_font.render("! ADRENALINE OVERDRIVE !", True, (255, adren_pulse, 50))
            adren_bg = pygame.Rect(wave_box_x, wave_box_y + wave_box_h + 6, wave_box_w, 20)
            pygame.draw.rect(canvas, (60, 15, 15), adren_bg, border_radius=4)
            pygame.draw.rect(canvas, (255, 80, 50), adren_bg, 1, border_radius=4)
            canvas.blit(adren_surf, (wave_box_x + wave_box_w // 2 - adren_surf.get_width() // 2, wave_box_y + wave_box_h + 9))

        # Wave announcement banner (centered in upper third of canvas)
        if wave_manager.announcement_timer > 0:
            banner_surf = title_font.render(wave_manager.wave_announcement, True, (255, 230, 80))
            banner_bg = banner_surf.get_rect(center=(GAME_WIDTH // 2, GAME_HEIGHT // 3))
            pad_x, pad_y = 30, 15
            bg_rect = banner_bg.inflate(pad_x * 2, pad_y * 2)
            banner_surface = pygame.Surface((bg_rect.width, bg_rect.height), pygame.SRCALPHA)
            banner_surface.fill((10, 15, 25, 210))
            pygame.draw.rect(banner_surface, (255, 200, 50), (0, 0, bg_rect.width, bg_rect.height), 2, border_radius=10)
            canvas.blit(banner_surface, bg_rect.topleft)
            canvas.blit(banner_surf, banner_bg.topleft)

        # Warning Feedback: Vignettes (Zero per-frame allocations) & Heartbeat Audio
        if player.health <= 2 and player.health > 0:
            pulse = int(140 + 80 * math.sin(pygame.time.get_ticks() * 0.008))
            vignette_health_surf.fill((0, 0, 0, 0))
            pygame.draw.rect(vignette_health_surf, (220, 20, 20, max(25, min(90, pulse // 3))), (0, 0, GAME_WIDTH, GAME_HEIGHT), width=20)
            canvas.blit(vignette_health_surf, (0, 0))
            audio_manager.play_sfx("low_health")
        elif player.shield <= 5 and player.shield > 0:
            vignette_shield_surf.fill((0, 0, 0, 0))
            pygame.draw.rect(vignette_shield_surf, (0, 200, 255, 30), (0, 0, GAME_WIDTH, GAME_HEIGHT), width=12)
            canvas.blit(vignette_shield_surf, (0, 0))
            audio_manager.play_sfx("low_shield")

        # Bullet Ammo UI (Rechte Seite)
        bg_height = int(BULLET_UI_HEIGHT * (player.max_bullets / 10))
        pygame.draw.rect(
            canvas, "black", (GAME_WIDTH - 32, 32, BULLET_UI_WIDTH, bg_height)
        )
        remaining_icons = int((player.max_bullets - player.used_bullets) // 10)
        for i in range(remaining_icons):
            canvas.blit(bullet_ui_image, (GAME_WIDTH - 32, 32 + i * BULLET_UI_HEIGHT))

        # Controls & Radar Mode Hint
        mode_str = "CONE [FAR]" if player.radar_mode == "CONE" else "360° OMNI [CLOSE]"
        controls_hint = hud_small_font.render(f"[SPACE] Gun  [E/RMB] Missile  [Q] Radar: {mode_str}  [1-5] Weapons  [R] Rearm  [X] Supply", True, (210, 230, 255))
        canvas.blit(controls_hint, (int(GAME_WIDTH / 2 - controls_hint.get_width() / 2), 38))

        # --- ROCKET HUD UI ---
        rocket_ui_x = GAME_WIDTH - 190
        rocket_ui_y = 32
        rocket_box_w = 145
        rocket_box_h = 56

        pygame.draw.rect(canvas, (18, 24, 36), (rocket_ui_x, rocket_ui_y, rocket_box_w, rocket_box_h), border_radius=6)
        pygame.draw.rect(canvas, (60, 90, 130), (rocket_ui_x, rocket_ui_y, rocket_box_w, rocket_box_h), 1, border_radius=6)

        rem_rockets = max(0, player.max_rockets - player.used_rockets)
        if player.rocket_reloading:
            now = pygame.time.get_ticks()
            elapsed = now - player.rocket_reload_start_time
            progress = min(1.0, elapsed / player.rocket_reloading_time)
            reload_surf = hud_small_font.render("RELOADING...", True, (255, 160, 50))
            canvas.blit(reload_surf, (rocket_ui_x + 8, rocket_ui_y + 5))
            
            bar_w = rocket_box_w - 16
            pygame.draw.rect(canvas, (40, 45, 60), (rocket_ui_x + 8, rocket_ui_y + 22, bar_w, 10), border_radius=3)
            pygame.draw.rect(canvas, (255, 140, 0), (rocket_ui_x + 8, rocket_ui_y + 22, int(bar_w * progress), 10), border_radius=3)
        else:
            label_surf = hud_small_font.render(f"ROCKETS: {rem_rockets}/{player.max_rockets}", True, (200, 225, 255))
            canvas.blit(label_surf, (rocket_ui_x + 8, rocket_ui_y + 5))
            
            pip_w = 9
            pip_h = 12
            spacing = 13
            for r_idx in range(player.max_rockets):
                pip_x = rocket_ui_x + 8 + r_idx * spacing
                pip_y = rocket_ui_y + 21
                if r_idx < rem_rockets:
                    pygame.draw.rect(canvas, (255, 90, 30), (pip_x, pip_y, pip_w, pip_h), border_radius=2)
                    pygame.draw.polygon(canvas, (255, 210, 50), [(pip_x, pip_y + 3), (pip_x + pip_w // 2, pip_y), (pip_x + pip_w, pip_y + 3)])
                else:
                    pygame.draw.rect(canvas, (50, 60, 80), (pip_x, pip_y, pip_w, pip_h), 1, border_radius=2)

        mode_col = (0, 220, 200) if player.radar_mode == "CONE" else (255, 170, 40)
        mode_label = hud_small_font.render(f"RADAR: {player.radar_mode}", True, mode_col)
        canvas.blit(mode_label, (rocket_ui_x + 8, rocket_ui_y + 38))

        # --- SPEEDOMETER UI ---
        mm_size = MINIMAP_SIZE
        speed_x = 20
        speed_y = GAME_HEIGHT - mm_size - 50
        
        bar_width = mm_size
        bar_height = 10
        fill_width = max(0, min(bar_width, int((player.velocity_x / player.max_speed) * bar_width)))
        
        speed_box.set_text(f"Speed: {player.velocity_x:.1f} / {player.max_speed:.1f}")
        speed_box.draw(canvas)

        pygame.draw.rect(canvas, (0, 0, 0), (speed_x, speed_y + 22, bar_width, bar_height))
        pygame.draw.rect(canvas, (255, 180, 0), (speed_x, speed_y + 22, fill_width, bar_height))
        pygame.draw.rect(canvas, (100, 120, 160), (speed_x, speed_y + 22, bar_width, bar_height), 1)

        # --- MINIMAP UI ---
        mm_x = 20
        mm_y = GAME_HEIGHT - mm_size - 20
        
        minimap_surface = pygame.Surface((mm_size, mm_size), pygame.SRCALPHA)

        start_col = 0
        end_col = int(math.ceil(MAP_WIDTH / bg_w))
        start_row = 0
        end_row = int(math.ceil(MAP_HEIGHT / bg_h))
        for col in range(start_col, end_col):
            for row in range(start_row, end_row):
                bx = col * MINIMAP_BG_WIDTH
                by = row * MINIMAP_BG_HEIGHT
                if bx < mm_size and by < mm_size:
                    minimap_surface.blit(minimap_bg_image, (bx, by))

        dim_overlay = pygame.Surface((mm_size, mm_size), pygame.SRCALPHA)
        dim_overlay.fill((0, 0, 0, 90))
        minimap_surface.blit(dim_overlay, (0, 0))

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
            omni_r_mm = int(RADAR_OMNI_RANGE * MINIMAP_SCALE)
            pygame.draw.circle(minimap_surface, (255, 140, 40, 190), (int(player_mm_x), int(player_mm_y)), omni_r_mm, 1)

        # Power-ups as glowing dots on minimap
        powerup_manager.draw_minimap_blips(minimap_surface, MINIMAP_SCALE)

        # Helldiver squad and beacon blips on minimap
        ground_support_manager.draw_minimap(minimap_surface, MINIMAP_SCALE)

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

        # Minimap frame border
        pygame.draw.rect(minimap_surface, (100, 120, 160), (0, 0, mm_size, mm_size), 2)
        
        canvas.blit(minimap_surface, (mm_x, mm_y))

        # --- POWER-UP HUD OVERLAY ---
        powerup_manager.draw_hud(canvas, GAME_WIDTH, GAME_HEIGHT)

        # --- GROUND SUPPORT HUD OVERLAY & WEAPON ARSENAL ---
        ground_support_manager.draw_hud(canvas, GAME_WIDTH, GAME_HEIGHT, font, title_font, speed_font, hud_small_font, player, mouse_pos)

        # --- MISSION OBJECTIVE HUD BANNER ---
        obj_text = f"OBJECTIVE: {active_mission_config['name']}"
        if active_mission_config["id"] == MissionType.BASE_DEFENSE and orbital_base:
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
                obj_text = f"OBJECTIVE: AIR SUPERIORITY [WAVE {wave_manager.wave}/5]"

        obj_surf = hud_small_font.render(obj_text, True, active_mission_config.get("icon_color", (255, 220, 80)))
        obj_bg = pygame.Rect(GAME_WIDTH // 2 - obj_surf.get_width() // 2 - 12, 8, obj_surf.get_width() + 24, 22)
        pygame.draw.rect(canvas, (14, 20, 32), obj_bg, border_radius=6)
        pygame.draw.rect(canvas, active_mission_config.get("icon_color", (0, 220, 255)), obj_bg, 1, border_radius=6)
        canvas.blit(obj_surf, (GAME_WIDTH // 2 - obj_surf.get_width() // 2, 12))

        # --- SLOW-MOTION VIGNETTE OVERLAY ---
        if ground_support_manager.is_slow_mo:
            vignette_surf = pygame.Surface((GAME_WIDTH, GAME_HEIGHT), pygame.SRCALPHA)
            pygame.draw.rect(vignette_surf, (0, 200, 255, 35), (0, 0, GAME_WIDTH, GAME_HEIGHT), 8)
            pygame.draw.rect(vignette_surf, (0, 150, 220, 20), (8, 8, GAME_WIDTH - 16, GAME_HEIGHT - 16), 8)
            canvas.blit(vignette_surf, (0, 0))


player = Player()
wave_manager = WaveManager()
health_drops = []
ground_support_manager = GroundSupportManager()
light_enemy = wave_manager.enemies[0] if wave_manager.enemies else Light_Enemy()
player.bullets = []
player.rockets = []
explosion_group = pygame.sprite.Group()


def run_game():
    global window, game_state, light_enemy, wave_manager, health_drops, ground_support_manager, pending_mission_config
    running = True
    last_wheel_time = 0
    while running:
        canvas_mouse_pos = get_canvas_mouse_pos()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                if player.score > player.highscore:
                    add_highscore(player.score)
                running = False
                break
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
                player.used_bullets = 0
                player.reloading = False
            if event.type == ROCKET_RELOAD_END:
                player.used_rockets = 0
                player.rocket_reloading = False
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
                if game_state == "" and player.health > 0:
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

                elif game_state == "main_menu":
                    if menu_play_box.is_clicked(event, canvas_mouse_pos):
                        game_state = "mission_select"
                    elif menu_help_box.is_clicked(event, canvas_mouse_pos):
                        previous_game_state = "main_menu"
                        game_state = "help_menu"
                    elif menu_settings_box.is_clicked(event, canvas_mouse_pos):
                        previous_game_state = "main_menu"
                        settings_menu.sync_from_manager()
                        game_state = "settings_menu"
                    elif menu_reset_box.is_clicked(event, canvas_mouse_pos):
                        player.highscore = 0
                        add_highscore(player.highscore)
                        highscore_box.set_text("highscore: 0")

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
                    if pause_continue_box.is_clicked(event, canvas_mouse_pos):
                        game_state = ""
                    elif pause_help_box.is_clicked(event, canvas_mouse_pos):
                        previous_game_state = "pause_menu"
                        game_state = "help_menu"
                    elif pause_settings_box.is_clicked(event, canvas_mouse_pos):
                        previous_game_state = "pause_menu"
                        settings_menu.sync_from_manager()
                        game_state = "settings_menu"
                    elif pause_menu_box.is_clicked(event, canvas_mouse_pos):
                        game_state = "main_menu"

                elif game_state == "mission_debriefing":
                    action = debriefing_screen.handle_event(event, canvas_mouse_pos)
                    if action == "replay":
                        respawn()
                        game_state = ""
                    elif action == "mission_select":
                        game_state = "mission_select"
                    elif action == "main_menu":
                        game_state = "main_menu"

                elif game_state == "":
                    if player.health <= 0:
                        if gameover_respawn_box.is_clicked(event, canvas_mouse_pos):
                            respawn()
                        elif gameover_help_box.is_clicked(event, canvas_mouse_pos):
                            previous_game_state = ""
                            game_state = "help_menu"
                        elif gameover_lobby_box.is_clicked(event, canvas_mouse_pos):
                            game_state = "main_menu"
                    else:
                        if ground_support_manager.weapon_menu.is_open:
                            ground_support_manager.weapon_menu.handle_event(event, canvas_mouse_pos)
                        elif event.button == 1:
                            if ground_support_manager.equipped_slot > 0:
                                ground_support_manager.start_aiming()
                        elif event.button == 3:
                            ground_support_manager.stop_aiming()
                            targets = list(wave_manager.enemies) + [g for g in ground_support_manager.enemy_ground_units if g.is_alive] + [f for f in ground_support_manager.enemy_fabricators if f.is_alive]
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
                        window = pygame.display.set_mode((0, 0), pygame.FULLSCREEN | pygame.RESIZABLE)
                    else:
                        window = pygame.display.set_mode((GAME_WIDTH, GAME_HEIGHT), pygame.RESIZABLE)
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
                    if event.key in (pygame.K_LSHIFT, pygame.K_RSHIFT):
                        game_state = "mission_select"
                    elif event.key == pygame.K_h:
                        previous_game_state = "main_menu"
                        game_state = "help_menu"
                    elif event.key == pygame.K_o:
                        previous_game_state = "main_menu"
                        settings_menu.sync_from_manager()
                        game_state = "settings_menu"
                    elif event.key == pygame.K_m:
                        is_muted = audio_manager.toggle_mute()
                        status_str = "MUTED" if is_muted else "UNMUTED"
                        ground_support_manager.add_combat_popup(f"AUDIO {status_str}", player.pos_x, player.pos_y, (255, 80, 80) if is_muted else (80, 255, 120))

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
                    if event.key == pygame.K_p:
                        game_state = ""
                    elif event.key == pygame.K_h:
                        previous_game_state = "pause_menu"
                        game_state = "help_menu"
                    elif event.key == pygame.K_o:
                        previous_game_state = "pause_menu"
                        settings_menu.sync_from_manager()
                        game_state = "settings_menu"
                    elif event.key == pygame.K_ESCAPE:
                        game_state = "main_menu"
                    elif event.key == pygame.K_m:
                        is_muted = audio_manager.toggle_mute()
                        status_str = "MUTED" if is_muted else "UNMUTED"
                        ground_support_manager.add_combat_popup(f"AUDIO {status_str}", player.pos_x, player.pos_y, (255, 80, 80) if is_muted else (80, 255, 120))

                elif game_state == "mission_debriefing":
                    action = debriefing_screen.handle_event(event, canvas_mouse_pos)
                    if action == "replay":
                        respawn()
                        game_state = ""
                    elif action == "mission_select":
                        game_state = "mission_select"
                    elif action == "main_menu":
                        game_state = "main_menu"
                    elif event.key == pygame.K_m:
                        is_muted = audio_manager.toggle_mute()
                        status_str = "MUTED" if is_muted else "UNMUTED"
                        ground_support_manager.add_combat_popup(f"AUDIO {status_str}", player.pos_x, player.pos_y, (255, 80, 80) if is_muted else (80, 255, 120))

                elif game_state == "":
                    if player.health <= 0:
                        if event.key == pygame.K_r:
                            respawn()
                        elif event.key == pygame.K_h:
                            previous_game_state = ""
                            game_state = "help_menu"
                        elif event.key == pygame.K_o:
                            previous_game_state = ""
                            settings_menu.sync_from_manager()
                            game_state = "settings_menu"
                        elif event.key == pygame.K_SPACE:
                            game_state = "main_menu"
                    else:
                        if ground_support_manager.objective_phase == "COMPLETE":
                            if event.key == pygame.K_r:
                                respawn()
                            elif event.key == pygame.K_ESCAPE:
                                game_state = "main_menu"

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

        keys = pygame.key.get_pressed()

        if game_state == "main_menu":
            main_menu(canvas_mouse_pos)
            if keys[pygame.K_LSHIFT] and keys[pygame.K_RSHIFT] and keys[pygame.K_r]:
                player.highscore = 0
                add_highscore(player.highscore)
                highscore_box.set_text("highscore: 0")

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

        elif game_state == "":
            if player.health > 0:
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
                    turn_rate = player.turn_rate * (0.75 if ground_support_manager.is_slow_mo else 1.0)
                    if keys[pygame.K_a] or keys[pygame.K_LEFT]:
                        player.angle += turn_rate
                    if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
                        player.angle -= turn_rate

                    rad = math.radians(player.angle)
                    dx = -math.sin(rad)
                    dy = -math.cos(rad)

                    if keys[pygame.K_w] or keys[pygame.K_UP]:
                        player.velocity_x = min(player.max_speed, player.velocity_x + player.acceleration)
                        player.velocity_y = min(player.max_speed, player.velocity_y + player.acceleration)
                    elif keys[pygame.K_s] or keys[pygame.K_DOWN]:
                        player.velocity_x = max(player.min_speed, player.velocity_x - player.acceleration)
                        player.velocity_y = max(player.min_speed, player.velocity_y - player.acceleration)

                    steering_factor = PLAYER_STEERING_SLOW_MO_FACTOR if ground_support_manager.is_slow_mo else 1.0
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
                        targets = list(wave_manager.enemies) + [g for g in ground_support_manager.enemy_ground_units if g.is_alive] + [f for f in ground_support_manager.enemy_fabricators if f.is_alive]
                        player.set_shoot_rocket(targets)

                    move()
                    draw(canvas_mouse_pos)
            else:
                draw(canvas_mouse_pos)
                if (keys[pygame.K_m]):
                    is_muted = audio_manager.toggle_mute()
                    status_str = "MUTED" if is_muted else "UNMUTED"
                    ground_support_manager.add_combat_popup(f"AUDIO {status_str}", player.pos_x, player.pos_y, (255, 80, 80) if is_muted else (80, 255, 120))

        # Background Music & Engine Audio Loop Updates
        if game_state in ("main_menu", "mission_select", "stratagem_select", "mission_debriefing"):
            audio_manager.play_music("menu_theme")
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
