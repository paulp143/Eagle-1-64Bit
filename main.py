import pygame 
import os, sys, random, math


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
PLAYER_MOVEMENT_SPEED_Y = 6
PLAYER_MOVEMENT_SPEED_X = 6
PLAYER_MIN_SPEED = 2.0
PLAYER_MAX_SPEED = 7.0
PLAYER_ACCELERATION = 0.15
PLAYER_TURN_RATE = 3
PLAYER_BULLET_DAMAGE = 1

BULLET_WIDTH = 9
BULLET_HEIGHT = 12
BULLET_VELOCITY_Y = 8
BULLET_UI_WIDTH = BULLET_WIDTH / 2  # 4 px
BULLET_UI_HEIGHT = BULLET_HEIGHT / 2
BULLET_SHOOTING_TIMER = 100

# Raketen-Parameter (debuffed)
ROCKET_WIDTH = 12
ROCKET_HEIGHT = 16
ROCKET_VELOCITY = 7.0
ROCKET_TURN_RATE = 2.0         
ROCKET_DAMAGE = 4
ROCKET_SHOOTING_TIMER = 350
ROCKET_MAX_FLIGHT_TIME = 2500  
ROCKET_MAX_RANGE = 1200       

# Radar & Lock-on Modi
RADAR_CONE_ANGLE = 50          
RADAR_CONE_RANGE = 1050
RADAR_CONE_MIN_RANGE=300        
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
LIGHT_ENEMY_BULLET_VELOCITY_Y = 4
LIGHT_ENEMY_BULLET_DAMAGE = 1
LIGHT_ENEMY_VELOCITY_X = 2
LIGHT_ENEMY_VELOCITY_Y = 2

MINIMAP_SIZE = 160
MINIMAP_SCALE = MINIMAP_SIZE / MAP_WIDTH
MINIMAP_BG_WIDTH = int(GAME_WIDTH * MINIMAP_SCALE)
MINIMAP_BG_HEIGHT = int(GAME_HEIGHT * MINIMAP_SCALE)

FRAME_MULTIPLIKATOR = 2
FRAME_SPEED = 0.4

HEALTH_WIDTH = 16
HEALTH_HEIGHT = 4


def get_base_dir():
    candidates = []
    try:
        candidates.append(os.path.dirname(os.path.abspath(__file__)))
    except Exception:
        pass
    candidates.append(os.getcwd())
    candidates.append(os.path.join(os.getcwd(), "Eagle-1-64Bit"))
    candidates.append(r"C:\Users\paul\OneDrive\Desktop\Python\Pygame\Eagle-1-64Bit")
    candidates.append(r"C:\Users\paul\OneDrive\Desktop\Python\Pygame")
    candidates.append(r"C:\Users\paul\.gemini\antigravity\worktrees\Eagle-1-64Bit\implement_homing_rocket_class")

    for c in candidates:
        if c and os.path.exists(os.path.join(c, "images")):
            return c
    return os.getcwd()

BASE_DIR = get_base_dir()
HIGHSCORE_FILE = os.path.join(BASE_DIR, "data", "highscore.txt")

def load_image(image_path, scale=None):
    if os.path.isabs(image_path) and os.path.exists(image_path):
        image = pygame.image.load(image_path)
    else:
        basename = os.path.basename(image_path)
        candidates = [
            os.path.join(BASE_DIR, image_path),
            os.path.join(BASE_DIR, "images", image_path),
            os.path.join(BASE_DIR, "images", basename),
            os.path.join(os.getcwd(), image_path),
            os.path.join(os.getcwd(), "images", image_path),
            os.path.join(os.getcwd(), "images", basename),
            os.path.join(os.getcwd(), "Eagle-1-64Bit", "images", basename),
            os.path.join(r"C:\Users\paul\OneDrive\Desktop\Python\Pygame\Eagle-1-64Bit", "images", basename),
        ]
        found = None
        for path in candidates:
            if os.path.exists(path):
                found = path
                break

        if found is not None:
            image = pygame.image.load(found)
        else:
            image = pygame.image.load(os.path.join(BASE_DIR, image_path))
        
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
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w") as file:
            file.write(str(new_highscore))
    except Exception as e:
        print(f"Error saving highscore: {e}")
            
class Spritesheet:
    def __init__(self, image_name, cols):
        self.sheet = load_image(image_name)
        self.cols = cols
        self.frame_width = self.sheet.get_width() / cols
        self.frame_height = self.sheet.get_height()
        self.frames = self.extract_frames()

    def extract_frames(self):
        frames = []
        for i in range(self.cols):
            rect = pygame.Rect(
                int(i * self.frame_width), 0, int(self.frame_width), self.frame_height
            )
            frame = self.sheet.subsurface(rect)
            frame = pygame.transform.scale(
                frame, (int(self.frame_width * FRAME_MULTIPLIKATOR), int(self.frame_height * FRAME_MULTIPLIKATOR))
            )
            frames.append(frame)
        return frames

class Large_explosion_a(pygame.sprite.Sprite):
    def __init__(self, x, y, frames, speed=FRAME_SPEED):
        super().__init__()
        self.frames = frames
        self.speed = speed
        self.current_frame = 0
        self.image = self.frames[0]
        self.rect = self.image.get_rect(center=(x, y))

    def update(self):
        self.current_frame += self.speed
        if self.current_frame >= len(self.frames):
            self.kill()
        else:
            self.image = self.frames[int(self.current_frame)]


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
            return self.is_hovered(mouse_pos)
        return False

    def draw(self, surface, mouse_pos=None):
        hovered = self.is_hovered(mouse_pos)
        
        # Hintergrund (mit Hover-Effekt)
        current_bg = self.hover_bg_color if (hovered and self.hover_bg_color) else self.bg_color
        if current_bg and self.bg_rect:
            pygame.draw.rect(surface, current_bg, self.bg_rect, border_radius=self.border_radius)

        # Rahmen (mit Hover-Effekt)
        current_border = self.hover_border_color if (hovered and self.hover_border_color) else self.border_color
        if current_border and self.bg_rect:
            pygame.draw.rect(surface, current_border, self.bg_rect, width=self.border_width, border_radius=self.border_radius)

        # Text
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
large_explosion_a_spritesheet = Spritesheet(os.path.join("images", "LargeExplosionA_spritesheet.png"), 23)


pygame.init()
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

def get_canvas_mouse_pos():
    """Skaliert die Mauskoordinaten des Fensters auf die interne Canvas-Auflösung."""
    win_w, win_h = window.get_size()
    if win_w == 0 or win_h == 0:
        return pygame.mouse.get_pos()
    mx, my = pygame.mouse.get_pos()
    return (mx * (GAME_WIDTH / win_w), my * (GAME_HEIGHT / win_h))


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
    bottom=GAME_HEIGHT/2+50
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
    bottom=GAME_HEIGHT/2+110
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
    bottom=GAME_HEIGHT*0.5
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
    bottom=GAME_HEIGHT*0.5+65
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
    bottom=GAME_HEIGHT/2
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
    bottom=GAME_HEIGHT/2+60
)

score_box = TextBox("Score: 0", font, centerx=GAME_WIDTH//2, bottom=GAME_HEIGHT-10)
highscore_box = TextBox("highscore: 0", font, centerx=GAME_WIDTH//2, bottom=GAME_HEIGHT-30)
speed_box = TextBox("Speed: 0.0 / 0.0", speed_font, topleft=(20, GAME_HEIGHT - MINIMAP_SIZE - 50))


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
            self.turn_rate = float(ROCKET_TURN_RATE)  # 2.0°/Frame = realistische weite Kurven
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
                # Prüfe mit Spieler-Lock-Zone falls verfügbar
                if player is not None and not player.is_enemy_in_lock_zone(t):
                    continue

                tx = t.x + getattr(t, 'width', LIGHT_ENEMY_WIDTH) / 2
                ty = t.y + getattr(t, 'height', LIGHT_ENEMY_HEIGHT) / 2
                diff_x = tx - cx
                diff_y = ty - cy
                dist = math.hypot(diff_x, diff_y)

                # Suchkopf-Winkelbegrenzung der Rakete
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
            # 1. Maximale Flugzeit prüfen (2.5 Sekunden)
            if pygame.time.get_ticks() - self.spawn_time >= self.max_flight_time:
                self.used = True
                return

            # 2. Maximale Distanz prüfen
            self.distance_traveled += self.speed
            if self.distance_traveled >= self.max_range:
                self.used = True
                return

            if targets is not None:
                if not self.target or getattr(self.target, 'exploding', False) or getattr(self.target, 'health', 0) <= 0:
                    self.lock_on(targets, player=player)

            # 3. Sanftes Drehen bis zum maximalen Wendewinkel (2.0°/Frame)
            if self.target and not getattr(self.target, 'exploding', False) and getattr(self.target, 'health', 0) > 0:
                tx = self.target.x + getattr(self.target, 'width', LIGHT_ENEMY_WIDTH) / 2
                ty = self.target.y + getattr(self.target, 'height', LIGHT_ENEMY_HEIGHT) / 2
                cx = self.pos_x + ROCKET_WIDTH / 2
                cy = self.pos_y + ROCKET_HEIGHT / 2

                diff_x = tx - cx
                diff_y = ty - cy

                desired_angle = math.degrees(math.atan2(-diff_x, -diff_y)) % 360
                angle_diff = (desired_angle - self.angle + 180) % 360 - 180

                # Langsames, weites Drehen ohne sofortiges Einlenken
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
        self.shield = PLAYER_MAX_SHIELD
        self.highscore = load_highscore()
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
            # OMNI: Nur Nahbereich (RADAR_OMNI_RANGE = 420), dafür rundum 360°
            return dist <= RADAR_OMNI_RANGE

        elif self.radar_mode == "CONE":
            # CONE: Hohe Reichweite (RADAR_CONE_RANGE = 1050), dafür nur schmaler Kegel geradeaus (±25°)
            if dist <= RADAR_CONE_RANGE and dist>=RADAR_CONE_MIN_RANGE:
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

            pygame.time.set_timer(SHOOTING_END, BULLET_SHOOTING_TIMER, 1)

        elif self.used_bullets >= self.max_bullets:
            self.reloading = True
            pygame.time.set_timer(RELOAD_END, self.reloading_time, 1)

    def set_shoot_rocket(self, target=None):
        """Feuert eine zielsuchende Rakete ab."""
        if self.rocket_reloading:
            return

        if not self.rocket_shooting and self.used_rockets < self.max_rockets:
            self.rocket_shooting = True
            self.used_rockets += 1

            # Rakete abwechselnd von linkem und rechtem Flügel abfeuern
            wing_offset_x = 18 if (self.used_rockets % 2 == 1) else -18
            wing_offset_y = 10

            rad = math.radians(self.angle)
            cx = self.pos_x + PLAYER_WIDTH / 2
            cy = self.pos_y + PLAYER_HEIGHT / 2

            rot_x = wing_offset_x * math.cos(rad) - wing_offset_y * math.sin(rad)
            rot_y = wing_offset_x * math.sin(rad) + wing_offset_y * math.cos(rad)

            rx = cx + rot_x - ROCKET_WIDTH / 2
            ry = cy + rot_y - ROCKET_HEIGHT / 2

            # Ziel nur zuweisen, wenn es sich im aktiven Lock-Bereich befindet
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


class Light_Enemy(pygame.Rect):
    class Bullet(pygame.Rect):
        def __init__(self, x, y):
            pygame.Rect.__init__(self, x, y, BULLET_WIDTH, BULLET_HEIGHT)
            self.image = bullet_image 
            self.used = False
            self.velocity_y = LIGHT_ENEMY_BULLET_VELOCITY_Y

    def __init__(self, x=None, y=None):
        if x is None or y is None:
            if x is None:
                x = random.randrange(100, MAP_WIDTH - LIGHT_ENEMY_WIDTH - 100, LIGHT_ENEMY_WIDTH * 2)
            if y is None:
                y = random.randrange(100, 400)
        pygame.Rect.__init__(self, int(x), int(y), LIGHT_ENEMY_WIDTH, LIGHT_ENEMY_HEIGHT)
        self.image = light_enemy_image
        self.health = LIGHT_ENEMY_HEALTH
        self.velocity_y = 2
        self.used = False
        self.bullets = []
        self.shooting = False
        self.explosion_damage = LIGHT_ENEMY_EXPLOSION_DAMAGE
        self.exploding = False
        self.bullet_damage = LIGHT_ENEMY_BULLET_DAMAGE
        self.x = int(x)
        self.y = int(y)
        self.velocity_x = float(LIGHT_ENEMY_VELOCITY_X)
        self.velocity_y = float(LIGHT_ENEMY_VELOCITY_Y)
        
    def set_shoot(self):
        bullet_x = self.x + (LIGHT_ENEMY_WIDTH // 2) - (BULLET_WIDTH // 2)
        bullet_y = self.y + LIGHT_ENEMY_HEIGHT
        self.bullets.append(Light_Enemy.Bullet(bullet_x, bullet_y))


def move():
    global light_enemy
    global explosion_group
    if player.health <= 0:
        return

    # Check if player is outside map boundaries and apply damage per tick
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

    # Bullet Update & Kollision
    for bullet in player.bullets:
        bullet.update_position()
        if bullet.colliderect(light_enemy) and not light_enemy.exploding:
            bullet.used = True
            light_enemy.health -= PLAYER_BULLET_DAMAGE

    # Rocket Update & Kollision
    for rocket in player.rockets:
        rocket.update_position(light_enemy, player=player)
        if rocket.used:
            # Detonation bei Zeit- oder Reichweitenablauf
            range_explosion = Large_explosion_a(
                rocket.x + ROCKET_WIDTH // 2,
                rocket.y + ROCKET_HEIGHT // 2,
                large_explosion_a_spritesheet.frames,
                speed=0.6
            )
            explosion_group.add(range_explosion)
        elif rocket.colliderect(light_enemy) and not light_enemy.exploding:
            rocket.used = True
            light_enemy.health -= rocket.damage
            # Treffer-Explosionseffekt
            hit_explosion = Large_explosion_a(
                rocket.x + ROCKET_WIDTH // 2,
                rocket.y + ROCKET_HEIGHT // 2,
                large_explosion_a_spritesheet.frames,
                speed=0.6
            )
            explosion_group.add(hit_explosion)

    if player.colliderect(light_enemy):
        light_enemy.health -= player.kamikaze_attack_damage
        player.take_damage(light_enemy.explosion_damage)
        
    if light_enemy.health <= 0 and not light_enemy.exploding:
        light_enemy.exploding = True
        explosion = Large_explosion_a(
            light_enemy.x + LIGHT_ENEMY_WIDTH // 2, 
            light_enemy.y + LIGHT_ENEMY_HEIGHT // 2, 
            large_explosion_a_spritesheet.frames
        )
        explosion_group.add(explosion)
        player.score += 5

        pygame.time.set_timer(
            LIGHT_ENEMY_EXPLOSION,
            LIGHT_ENEMY_EXPLOSION_TIME,
            1
        )

        light_enemy.velocity_y = 0

    player.bullets = [bullet for bullet in player.bullets if not bullet.used \
                    and 0 <= bullet.x <= MAP_WIDTH and 0 <= bullet.y <= MAP_HEIGHT]

    player.rockets = [rocket for rocket in player.rockets if not rocket.used \
                    and 0 <= rocket.x <= MAP_WIDTH and 0 <= rocket.y <= MAP_HEIGHT]

    light_enemy.y += light_enemy.velocity_y
    
    for bullet in light_enemy.bullets:
        bullet.y += bullet.velocity_y
        if bullet.colliderect(player):
            bullet.used = True
            player.take_damage(light_enemy.bullet_damage)

    light_enemy.bullets = [bullet for bullet in light_enemy.bullets if not bullet.used \
                           and 0 <= bullet.y <= MAP_HEIGHT]

    if light_enemy.y > MAP_HEIGHT:
        old_bullets = light_enemy.bullets
        light_enemy = Light_Enemy()
        light_enemy.bullets = old_bullets
        player.score -= 5


def respawn():
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
    global light_enemy
    light_enemy = Light_Enemy()
    light_enemy.bullets.clear()
    player.shield = PLAYER_MAX_SHIELD
    explosion_group.empty()


def main_menu(mouse_pos=None):
    canvas.fill((0, 0, 0))
    canvas.blit(main_menu_image, (0, 0))

    title_box.draw(canvas, mouse_pos)
    menu_play_box.draw(canvas, mouse_pos)
    menu_reset_box.draw(canvas, mouse_pos)


def pause_menu(mouse_pos=None):
    canvas.fill((0, 0, 0))
    canvas.blit(backround_image, (0, 0))

    pause_title_box.draw(canvas, mouse_pos)
    pause_continue_box.draw(canvas, mouse_pos)
    pause_menu_box.draw(canvas, mouse_pos)


def draw(mouse_pos=None):
    canvas.fill((0, 0, 0))

    # Calculate camera offset bounded to map dimensions
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
        gameover_lobby_box.draw(canvas, mouse_pos)
        
    else:
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

        # Draw player rockets with camera offset
        for rocket in player.rockets:
            r_screen_x = rocket.x - camera_x
            r_screen_y = rocket.y - camera_y
            rocket_rect = rocket.image.get_rect(center=(r_screen_x + ROCKET_WIDTH // 2, r_screen_y + ROCKET_HEIGHT // 2))
            canvas.blit(rocket.image, rocket_rect.topleft)

        # Draw enemy bullets with camera offset
        for bullet in light_enemy.bullets:
            b_screen_x = bullet.x - camera_x
            b_screen_y = bullet.y - camera_y
            canvas.blit(enemy_bullet_image, (b_screen_x, b_screen_y))

        # Draw light enemy with camera offset & Lock-on Reticle
        if not light_enemy.exploding:
            enemy_screen_x = light_enemy.x - camera_x
            enemy_screen_y = light_enemy.y - camera_y
            canvas.blit(light_enemy.image, (enemy_screen_x, enemy_screen_y))

            # --- TARGET LOCK-ON HUD RETICLE (NUR WENN IM AKTIVEN LOCK-BEREICH) ---
            if player.is_enemy_in_lock_zone(light_enemy):
                if -80 <= enemy_screen_x <= GAME_WIDTH + 80 and -80 <= enemy_screen_y <= GAME_HEIGHT + 80:
                    ret_pad = 6
                    ret_len = 8
                    ret_x = enemy_screen_x - ret_pad
                    ret_y = enemy_screen_y - ret_pad
                    ret_w = LIGHT_ENEMY_WIDTH + ret_pad * 2
                    ret_h = LIGHT_ENEMY_HEIGHT + ret_pad * 2

                    ret_color = (255, 60, 60)
                    # Top-Left
                    pygame.draw.line(canvas, ret_color, (ret_x, ret_y), (ret_x + ret_len, ret_y), 2)
                    pygame.draw.line(canvas, ret_color, (ret_x, ret_y), (ret_x, ret_y + ret_len), 2)
                    # Top-Right
                    pygame.draw.line(canvas, ret_color, (ret_x + ret_w, ret_y), (ret_x + ret_w - ret_len, ret_y), 2)
                    pygame.draw.line(canvas, ret_color, (ret_x + ret_w, ret_y), (ret_x + ret_w, ret_y + ret_len), 2)
                    # Bottom-Left
                    pygame.draw.line(canvas, ret_color, (ret_x, ret_y + ret_h), (ret_x + ret_len, ret_y + ret_h), 2)
                    pygame.draw.line(canvas, ret_color, (ret_x, ret_y + ret_h), (ret_x, ret_y + ret_h - ret_len), 2)
                    # Bottom-Right
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

        # UI elements (Screen space, fixed overlay)
        score_box.set_text(f"Score: {player.score}")
        score_box.draw(canvas)

        highscore_box.set_text(f"highscore: {player.highscore}")
        highscore_box.draw(canvas)

        # Health Bar
        pygame.draw.rect(canvas, "black", (32, 32, HEALTH_WIDTH, HEALTH_HEIGHT * player.max_health))
        for i in range(int(player.max_health - player.health), player.max_health):
            canvas.blit(health_image, (32, 32 + i * HEALTH_HEIGHT, HEALTH_WIDTH, HEALTH_HEIGHT))

        # Bullet Ammo UI (Rechte Seite)
        bg_height = int(BULLET_UI_HEIGHT * (player.max_bullets / 10))
        pygame.draw.rect(
            canvas, "black", (GAME_WIDTH - 32, 32, BULLET_UI_WIDTH, bg_height)
        )
        remaining_icons = int((player.max_bullets - player.used_bullets) // 10)
        for i in range(remaining_icons):
            canvas.blit(bullet_ui_image, (GAME_WIDTH - 32, 32 + i * BULLET_UI_HEIGHT))

        # Shield Bar
        current_shield_width = max(0, (player.shield / PLAYER_MAX_SHIELD) * 238)
        shield_ui_width = SHIELD_UI_WIDTH * PLAYER_MAX_SHIELD
        shield_x = GAME_WIDTH / 2 - shield_ui_width / 2
        shield_y = 32
        pygame.draw.rect(canvas, "black", (shield_x, shield_y, shield_ui_width, SHIELD_UI_HEIGHT))
        pygame.draw.rect(canvas, "#09c8f1", (shield_x + 1, shield_y + 1, current_shield_width, 6))

        # Controls & Radar Mode Hint
        mode_str = "CONE [FAR]" if player.radar_mode == "CONE" else "360° OMNI [CLOSE]"
        controls_hint = hud_small_font.render(f"[SPACE] Gun   [E/R-Click] Missile   [T] Radar: {mode_str}", True, (0, 0, 0))
        canvas.blit(controls_hint, (int(GAME_WIDTH / 2 - controls_hint.get_width() / 2), 46))

        # --- ROCKET HUD UI ---
        rocket_ui_x = GAME_WIDTH - 190
        rocket_ui_y = 32
        rocket_box_w = 145
        rocket_box_h = 56

        # Background Box
        pygame.draw.rect(canvas, (18, 24, 36), (rocket_ui_x, rocket_ui_y, rocket_box_w, rocket_box_h), border_radius=6)
        pygame.draw.rect(canvas, (60, 90, 130), (rocket_ui_x, rocket_ui_y, rocket_box_w, rocket_box_h), 1, border_radius=6)

        rem_rockets = max(0, player.max_rockets - player.used_rockets)
        if player.rocket_reloading:
            now = pygame.time.get_ticks()
            elapsed = now - player.rocket_reload_start_time
            progress = min(1.0, elapsed / player.rocket_reloading_time)
            reload_surf = hud_small_font.render("RELOADING...", True, (255, 160, 50))
            canvas.blit(reload_surf, (rocket_ui_x + 8, rocket_ui_y + 5))
            
            # Progress bar
            bar_w = rocket_box_w - 16
            pygame.draw.rect(canvas, (40, 45, 60), (rocket_ui_x + 8, rocket_ui_y + 22, bar_w, 10), border_radius=3)
            pygame.draw.rect(canvas, (255, 140, 0), (rocket_ui_x + 8, rocket_ui_y + 22, int(bar_w * progress), 10), border_radius=3)
        else:
            label_surf = hud_small_font.render(f"ROCKETS: {rem_rockets}/{player.max_rockets}", True, (200, 225, 255))
            canvas.blit(label_surf, (rocket_ui_x + 8, rocket_ui_y + 5))
            
            # Missile Icons
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

        # Radar mode status label in HUD
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

        # Render tiled background image on minimap bounded to map
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

        # Dark overlay
        dim_overlay = pygame.Surface((mm_size, mm_size), pygame.SRCALPHA)
        dim_overlay.fill((0, 0, 0, 90))
        minimap_surface.blit(dim_overlay, (0, 0))

        # 1. Screen Viewport rectangle on minimap (Kamera-Bereich um den Spieler)
        view_x = camera_x * MINIMAP_SCALE
        view_y = camera_y * MINIMAP_SCALE
        view_w = GAME_WIDTH * MINIMAP_SCALE
        view_h = GAME_HEIGHT * MINIMAP_SCALE
        pygame.draw.rect(minimap_surface, (0, 200, 255, 220), (view_x, view_y, view_w, view_h), 1)



        # Player dot at exact position on minimap
        player_mm_x = (player.pos_x + PLAYER_WIDTH / 2) * MINIMAP_SCALE
        player_mm_y = (player.pos_y + PLAYER_HEIGHT / 2) * MINIMAP_SCALE

        # 3. Visualisierung des aktiven Lock-on Bereichs auf der Minimap
        if player.radar_mode == "CONE":
            # CONE Modus: Kegel geradeaus nach vorne (Fernbereich)
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
            # OMNI Modus: Rundum-Bereich (360°), aber strikt nur im Nahbereich
            omni_r_mm = int(RADAR_OMNI_RANGE * MINIMAP_SCALE)
            pygame.draw.circle(minimap_surface, (255, 140, 40, 190), (int(player_mm_x), int(player_mm_y)), omni_r_mm, 1)

        # Player dot (Grün)
        pygame.draw.circle(minimap_surface, (0, 255, 100), (int(player_mm_x), int(player_mm_y)), 4)

        # Enemies as RED dots on minimap
        if not light_enemy.exploding:
            enemy_mm_x = (light_enemy.x + LIGHT_ENEMY_WIDTH / 2) * MINIMAP_SCALE
            enemy_mm_y = (light_enemy.y + LIGHT_ENEMY_HEIGHT / 2) * MINIMAP_SCALE
            pygame.draw.circle(minimap_surface, (255, 30, 30), (int(enemy_mm_x), int(enemy_mm_y)), 4)

        # Minimap frame border
        pygame.draw.rect(minimap_surface, (100, 120, 160), (0, 0, mm_size, mm_size), 2)
        
        canvas.blit(minimap_surface, (mm_x, mm_y))


player = Player()
light_enemy = Light_Enemy()
player.bullets = []
player.rockets = []
explosion_group = pygame.sprite.Group()


if __name__ == "__main__":
    running = True
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
            if event.type == LIGHT_ENEMY_SHOOT and not light_enemy.exploding:
                if game_state == "":
                    light_enemy.set_shoot()
            if event.type == RELOAD_END:
                player.used_bullets = 0
                player.reloading = False
            if event.type == ROCKET_RELOAD_END:
                player.used_rockets = 0
                player.rocket_reloading = False
            if event.type == LIGHT_ENEMY_EXPLOSION:
                old_bullets = light_enemy.bullets
                light_enemy = Light_Enemy()
                light_enemy.bullets = old_bullets
            if event.type == INVINCIBLE_END:
                player.invincible = False
            if event.type == SHIELD_REGENERATION:
                if player.shield < PLAYER_MAX_SHIELD:
                    if PLAYER_MAX_SHIELD - player.shield > 1:
                        player.shield += 1
                    else:
                        player.shield = PLAYER_MAX_SHIELD

            # Maus-Klick Interaktion für Knöpfe & Raketen-Abschuss
            if event.type == pygame.MOUSEBUTTONDOWN:
                if game_state == "main_menu":
                    if menu_play_box.is_clicked(event, canvas_mouse_pos):
                        respawn()
                        game_state = ""
                    elif menu_reset_box.is_clicked(event, canvas_mouse_pos):
                        player.highscore = 0
                        add_highscore(player.highscore)
                        highscore_box.set_text("highscore: 0")

                elif game_state == "pause_menu":
                    if pause_continue_box.is_clicked(event, canvas_mouse_pos):
                        game_state = ""
                    elif pause_menu_box.is_clicked(event, canvas_mouse_pos):
                        game_state = "main_menu"

                elif game_state == "":
                    if player.health <= 0:
                        if gameover_respawn_box.is_clicked(event, canvas_mouse_pos):
                            respawn()
                        elif gameover_lobby_box.is_clicked(event, canvas_mouse_pos):
                            game_state = "main_menu"
                    else:
                        # Rechtsklick feuert Raketen im Spiel
                        if event.button == 3:
                            player.set_shoot_rocket(light_enemy)

            # Tastatur-Steuerung für Menüs & Radar-Umschaltung
            if event.type == pygame.KEYDOWN:
                if game_state == "main_menu":
                    if event.key in (pygame.K_LSHIFT, pygame.K_RSHIFT):
                        respawn()
                        game_state = ""
                elif game_state == "pause_menu":
                    if event.key == pygame.K_p:
                        game_state = ""
                    elif event.key == pygame.K_ESCAPE:
                        game_state = "main_menu"
                elif game_state == "":
                    if event.key == pygame.K_p:
                        game_state = "pause_menu"
                    elif event.key == pygame.K_t:
                        # Taster 'T': Radar-Lock-Modus umschalten (CONE <-> OMNI)
                        player.toggle_radar_mode()
                    elif player.health <= 0:
                        if event.key == pygame.K_r:
                            respawn()
                        elif event.key == pygame.K_SPACE:
                            game_state = "main_menu"

        if not running:
            break

        keys = pygame.key.get_pressed()

        if game_state == "main_menu":
            main_menu(canvas_mouse_pos)
            if keys[pygame.K_LSHIFT] and keys[pygame.K_RSHIFT] and keys[pygame.K_r]:
                player.highscore = 0
                add_highscore(player.highscore)
                highscore_box.set_text("highscore: 0")

        elif game_state == "pause_menu":
            pause_menu(canvas_mouse_pos)

        elif game_state == "":
            if player.health > 0:
                if keys[pygame.K_a] or keys[pygame.K_LEFT]:
                    player.angle += player.turn_rate
                if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
                    player.angle -= player.turn_rate

                rad = math.radians(player.angle)
                dx = -math.sin(rad)
                dy = -math.cos(rad)

                if keys[pygame.K_w] or keys[pygame.K_UP]:
                    player.velocity_x = min(player.max_speed, player.velocity_x + player.acceleration)
                    player.velocity_y = min(player.max_speed, player.velocity_y + player.acceleration)
                elif keys[pygame.K_s] or keys[pygame.K_DOWN]:
                    player.velocity_x = max(player.min_speed, player.velocity_x - player.acceleration)
                    player.velocity_y = max(player.min_speed, player.velocity_y - player.acceleration)

                player.pos_x += dx * player.velocity_x
                player.pos_y += dy * player.velocity_y

                player.angle %= 360
                player.x = int(player.pos_x)
                player.y = int(player.pos_y)

                # Geschütz abfeuern (SPACE)
                if keys[pygame.K_SPACE] and not player.reloading:
                    player.set_shoot()

                # Zielsuchende Rakete abfeuern (E, F, Q oder L-CTRL)
                if (keys[pygame.K_e] or keys[pygame.K_f] or keys[pygame.K_q] or keys[pygame.K_LCTRL]) and not player.rocket_reloading:
                    player.set_shoot_rocket(light_enemy)

                move()
                draw(canvas_mouse_pos)
            else:
                draw(canvas_mouse_pos)

        scaled_surface = pygame.transform.scale(canvas, window.get_size())
        window.blit(scaled_surface, (0, 0))

        pygame.display.update()
        clock.tick(60)

    pygame.quit()
