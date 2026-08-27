import pygame 
import os,random,math


GAME_WIDTH=1280
GAME_HEIGHT=720

MAP_WIDTH=3000
MAP_HEIGHT=3000

PLAYER_Y=1470
PLAYER_X=1476
PLAYER_WIDTH=48
PLAYER_HEIGHT=61
PLAYER_MAX_HEALTH=5
PLAYER_MAX_BULLETS=200
PLAYER_RELOAD_TIME=5000
PLAYER_ATTACK_DAMAGE_KAMIKAZE=4
PLAYER_INVINCIBLE_TIME=1000
PLAYER_MAX_SHIELD=20
PLAYER_MOVEMENT_SPEED_Y=6
PLAYER_MOVEMENT_SPEED_X=6
PLAYER_MIN_SPEED=2.0
PLAYER_MAX_SPEED=12.0
PLAYER_ACCELERATION=0.15
PLAYER_TURN_RATE=3
PLAYER_BULLET_DAMAGE=1

BULLET_WIDTH=9
BULLET_HEIGHT=12
BULLET_VELOCITY_Y=8
BULLET_UI_WIDTH = BULLET_WIDTH / 2  # 4 px
BULLET_UI_HEIGHT =BULLET_HEIGHT / 2
BULLET_SHOOTING_TIMER=100

SHIELD_UI_WIDTH=12
SHIELD_UI_HEIGHT=8
SHIELD_REGENERATION_TIME=2000

BORDER_TICK_DAMAGE=0.1

LIGHT_ENEMY_WIDTH=50
LIGHT_ENEMY_HEIGHT=46
LIGHT_ENEMY_HEALTH=4
LIGHT_ENEMY_EXPLOSION_DAMAGE=5
LIGHT_ENEMY_EXPLOSION_WIDTH=50
LIGHT_ENEMY_EXPLOSION_HEIGHT=46
LIGHT_ENEMY_EXPLOSION_TIME=500
LIGHT_ENEMY_BULLET_VELOCITY_Y=4
LIGHT_ENEMY_BULLET_DAMAGE=1


FRAME_MULTIPLIKATOR=2
FRAME_SPEED=0.4

HEALTH_WIDTH=16
HEALTH_HEIGHT=4


try:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    if os.path.exists(os.path.join(current_dir, "images")):
        BASE_DIR = current_dir
    else:
        BASE_DIR = r"C:\Users\paul\OneDrive\Desktop\Python\Pygame\Eagle-1-64Bit"
except Exception:
    BASE_DIR = r"C:\Users\paul\OneDrive\Desktop\Python\Pygame\Eagle-1-64Bit"

HIGHSCORE_FILE = os.path.join(BASE_DIR, "data", "highscore.txt")

def load_image(image_path, scale=None):
    if not os.path.isabs(image_path):
        candidate = os.path.join(BASE_DIR, image_path)
        if not os.path.exists(candidate) and not image_path.startswith("images"):
            candidate = os.path.join(BASE_DIR, "images", image_path)
        image = pygame.image.load(candidate)
    else:
        image = pygame.image.load(image_path)
        
    if scale is not None:
        image = pygame.transform.scale(image, scale)
    return image

def load_highscore(filepath=HIGHSCORE_FILE):
    try:
        with open(filepath, "r") as file:
            return int(file.read().strip())
    except (FileNotFoundError, ValueError):
        return 0
    
def add_highscore(new_highscore,filepath=HIGHSCORE_FILE):
    try:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath,"w") as file:
            file.write(str(new_highscore))
    except Exception as e:
        print(f"Error saving highscore: {e}")
            
class Spritesheet:
    def __init__(self,image_name,cols):
        self.sheet=load_image(image_name)
        self.cols=cols
        self.frame_width=self.sheet.get_width()/cols
        self.frame_height=self.sheet.get_height()
        self.frames=self.extract_frames()

    def extract_frames(self):
        frames=[]
        for i in range (self.cols):
            rect=pygame.Rect(
                int(i*self.frame_width),0,int(self.frame_width),self.frame_height
            )
            frame=self.sheet.subsurface(rect)
            frame=pygame.transform.scale(
                frame,(int(self.frame_width*FRAME_MULTIPLIKATOR),int(self.frame_height*FRAME_MULTIPLIKATOR))
            )
            frames.append(frame)
        return frames

class Large_explosion_a(pygame.sprite.Sprite):
    def __init__(self,x,y,frames,speed=FRAME_SPEED):
        super().__init__()
        self.frames=frames
        self.speed=speed
        self.current_frame=0
        self.image=self.frames[0]
        self.rect=self.image.get_rect(center=(x,y))

    def update(self):
        self.current_frame+=self.speed
        if self.current_frame>=len(self.frames):
            self.kill()
        else:
            self.image=self.frames[int(self.current_frame)]


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


player_image=load_image(os.path.join("images", "Space-Invaders-Ship.png"), (PLAYER_WIDTH,PLAYER_HEIGHT))
bullet_image=load_image(os.path.join("images", "bullet.png"), (BULLET_WIDTH,BULLET_HEIGHT))
light_enemy_image=load_image(os.path.join("images", "enemy1.png"),(LIGHT_ENEMY_WIDTH,LIGHT_ENEMY_HEIGHT))
enemy_bullet_image=load_image(os.path.join("images", "enemy_bullet.png"), (BULLET_WIDTH,BULLET_HEIGHT))
main_menu_image=load_image(os.path.join("images", "20260820_085135933_iOS.webp"),(GAME_WIDTH,GAME_HEIGHT))
backround_image=load_image(os.path.join("images", "newbackround.png"),(GAME_WIDTH,GAME_HEIGHT))
MINIMAP_SIZE = 160
MINIMAP_SCALE = MINIMAP_SIZE / MAP_WIDTH
MINIMAP_BG_WIDTH = int(GAME_WIDTH * MINIMAP_SCALE)
MINIMAP_BG_HEIGHT = int(GAME_HEIGHT * MINIMAP_SCALE)
minimap_bg_image = pygame.transform.scale(backround_image, (MINIMAP_BG_WIDTH, MINIMAP_BG_HEIGHT))
light_enemy_explosion_image=load_image(os.path.join("images", "light_enemy_explosion.png"), (LIGHT_ENEMY_WIDTH,LIGHT_ENEMY_HEIGHT))
health_image=load_image(os.path.join("images", "health.png"),(HEALTH_WIDTH,HEALTH_HEIGHT))
bullet_ui_image=load_image(os.path.join("images", "bullet_ui.png"),(BULLET_UI_WIDTH,BULLET_UI_HEIGHT))
large_explosion_a_spritesheet=Spritesheet(os.path.join("images", "LargeExplosionA_spritesheet.png"),23)


pygame.init()
font = pygame.font.SysFont("arial", 24, bold=True)
title_font=pygame.font.SysFont("arial",48,bold=True)
speed_font = pygame.font.SysFont("arial", 18, bold=True)
clock=pygame.time.Clock()
window=pygame.display.set_mode((GAME_WIDTH,GAME_HEIGHT), pygame.RESIZABLE)
canvas=pygame.Surface((GAME_WIDTH,GAME_HEIGHT))
frame_number=23
frame_width=large_explosion_a_spritesheet.sheet.get_width()/23
frame_height=large_explosion_a_spritesheet.sheet.get_height()
game_state="main_menu"
pygame.display.set_caption("Eagle 1 64Bit")

def get_canvas_mouse_pos():
    #Skaliert die Mauskoordinaten des Fensters auf die interne Canvas-Auflösung.
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


SHOOTING_END=pygame.USEREVENT+1
ADD_SCORE=pygame.USEREVENT+2
LIGHT_ENEMY_SHOOT=pygame.USEREVENT+3
RELOAD_END=pygame.USEREVENT+4
LIGHT_ENEMY_EXPLOSION=pygame.USEREVENT+5
INVINCIBLE_END=pygame.USEREVENT+6
SHIELD_REGENERATION=pygame.USEREVENT+7

pygame.time.set_timer(ADD_SCORE, 1000)
pygame.time.set_timer(LIGHT_ENEMY_SHOOT, 1200)
pygame.time.set_timer(SHIELD_REGENERATION,SHIELD_REGENERATION_TIME)


class Player (pygame.Rect):
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
        self.score=0
        self.max_bullets=PLAYER_MAX_BULLETS
        self.used_bullets=0
        self.reloading=False
        self.reloading_time=PLAYER_RELOAD_TIME
        self.kamikaze_attack_damage=PLAYER_ATTACK_DAMAGE_KAMIKAZE
        self.invincible=False
        self.invincible_time=PLAYER_INVINCIBLE_TIME
        self.shield=PLAYER_MAX_SHIELD
        self.highscore=load_highscore()
        self.min_speed=PLAYER_MIN_SPEED
        self.max_speed=PLAYER_MAX_SPEED
        self.acceleration=PLAYER_ACCELERATION
        self.velocity_y=float(PLAYER_MOVEMENT_SPEED_Y)
        self.velocity_x=float(PLAYER_MOVEMENT_SPEED_X)
        self.boundaries=False
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
    def add_score(self):
        self.score+=1
    def take_damage(self, damage):
        if self.invincible:
            return
        
        if self.shield<damage:
            self.health+=self.shield-damage
            self.shield=0
            self.health=math.ceil(self.health)
            self.invincible=True
        else:
            self.shield-=damage
            self.invincible=True

        pygame.time.set_timer(
            INVINCIBLE_END,
            self.invincible_time,
            1
        )




class Light_Enemy (pygame.Rect):
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
        self.explosion_damage=LIGHT_ENEMY_EXPLOSION_DAMAGE
        self.exploding=False
        self.bullet_damage=LIGHT_ENEMY_BULLET_DAMAGE
        self.x=int(x)
        self.y=int(y)
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
        player.boundaries=True 
        if player.shield > 0:
            player.shield = max(0.0, player.shield - damage)
        else:
            player.health = max(0.0, player.health - damage)
    
    player.boundaries=False
    player.x = int(player.pos_x)
    player.y = int(player.pos_y)

    for bullet in player.bullets:
        bullet.update_position()
        if bullet.colliderect(light_enemy) and not light_enemy.exploding:
            bullet.used = True
            light_enemy.health -= PLAYER_BULLET_DAMAGE

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
    
    player.score = 0
    global light_enemy
    light_enemy = Light_Enemy()
    light_enemy.bullets.clear()
    player.shield = PLAYER_MAX_SHIELD
    explosion_group.empty()



def main_menu(mouse_pos=None):
    canvas.fill((0,0,0))
    canvas.blit(main_menu_image,(0,0))

    title_box.draw(canvas, mouse_pos)
    menu_play_box.draw(canvas, mouse_pos)
    menu_reset_box.draw(canvas, mouse_pos)

def pause_menu(mouse_pos=None):
    canvas.fill((0,0,0))
    canvas.blit(backround_image,(0,0))

    pause_title_box.draw(canvas, mouse_pos)
    pause_continue_box.draw(canvas, mouse_pos)
    pause_menu_box.draw(canvas, mouse_pos)

def draw(mouse_pos=None):
    canvas.fill((0,0,0))

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

        # Draw enemy bullets with camera offset
        for bullet in light_enemy.bullets:
            b_screen_x = bullet.x - camera_x
            b_screen_y = bullet.y - camera_y
            canvas.blit(enemy_bullet_image, (b_screen_x, b_screen_y))

        # Draw light enemy with camera offset
        if not light_enemy.exploding:
            enemy_screen_x = light_enemy.x - camera_x
            enemy_screen_y = light_enemy.y - camera_y
            canvas.blit(light_enemy.image, (enemy_screen_x, enemy_screen_y))

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

        pygame.draw.rect(canvas,"black",(32,32,HEALTH_WIDTH,HEALTH_HEIGHT*player.max_health))
        for i in range(int(player.max_health - player.health), player.max_health):
            canvas.blit(health_image,(32,32+i*HEALTH_HEIGHT,HEALTH_WIDTH,HEALTH_HEIGHT))

        bg_height = int(BULLET_UI_HEIGHT * (player.max_bullets / 10))
        pygame.draw.rect(
            canvas, "black", (GAME_WIDTH - 32, 32, BULLET_UI_WIDTH, bg_height)
        )
        remaining_icons = int((player.max_bullets - player.used_bullets) // 10)
        for i in range(remaining_icons):
            canvas.blit(bullet_ui_image, (GAME_WIDTH - 32, 32 + i * BULLET_UI_HEIGHT))

        current_shield_width=max(0,(player.shield/PLAYER_MAX_SHIELD)*238)
        shield_ui_width=SHIELD_UI_WIDTH*PLAYER_MAX_SHIELD
        shield_x=GAME_WIDTH/2-shield_ui_width/2
        shield_y=32
        pygame.draw.rect(canvas,"black",(shield_x,shield_y,shield_ui_width,SHIELD_UI_HEIGHT))
        pygame.draw.rect(canvas,"#09c8f1",(shield_x+1,shield_y+1,current_shield_width,6))

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

        # Screen Viewport rectangle on minimap showing active camera region inside the map
        view_x = camera_x * MINIMAP_SCALE
        view_y = camera_y * MINIMAP_SCALE
        view_w = GAME_WIDTH * MINIMAP_SCALE
        view_h = GAME_HEIGHT * MINIMAP_SCALE
        pygame.draw.rect(minimap_surface, (0, 200, 255, 220), (view_x, view_y, view_w, view_h), 1)

        # Player dot at exact position on minimap
        player_mm_x = (player.pos_x + PLAYER_WIDTH / 2) * MINIMAP_SCALE
        player_mm_y = (player.pos_y + PLAYER_HEIGHT / 2) * MINIMAP_SCALE
        pygame.draw.circle(minimap_surface, (0, 255, 100), (int(player_mm_x), int(player_mm_y)), 4)

        # Enemies as RED dots on minimap
        if not light_enemy.exploding:
            enemy_mm_x = (light_enemy.x + LIGHT_ENEMY_WIDTH / 2) * MINIMAP_SCALE
            enemy_mm_y = (light_enemy.y + LIGHT_ENEMY_HEIGHT / 2) * MINIMAP_SCALE
            pygame.draw.circle(minimap_surface, (255, 30, 30), (int(enemy_mm_x), int(enemy_mm_y)), 4)

        # Minimap frame border
        pygame.draw.rect(minimap_surface, (100, 120, 160), (0, 0, mm_size, mm_size), 2)
        
        canvas.blit(minimap_surface, (mm_x, mm_y))


player=Player()
light_enemy=Light_Enemy()
player.bullets=[]
explosion_group=pygame.sprite.Group()


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
        if event.type == ADD_SCORE:
            if game_state == "":
                player.add_score()
        if event.type == LIGHT_ENEMY_SHOOT and not light_enemy.exploding:
            if game_state == "":
                light_enemy.set_shoot()
        if event.type == RELOAD_END:
            player.used_bullets = 0
            player.reloading = False
        if event.type == LIGHT_ENEMY_EXPLOSION:
            old_bullets = light_enemy.bullets
            light_enemy = Light_Enemy()
            light_enemy.bullets = old_bullets
        if event.type == INVINCIBLE_END:
            player.invincible = False
        if event.type == SHIELD_REGENERATION:
            if player.shield < PLAYER_MAX_SHIELD:
                if PLAYER_MAX_SHIELD-player.shield>1:
                    player.shield += 1
                else:
                    player.shield=PLAYER_MAX_SHIELD

        # Maus-Klick Interaktion für Knöpfe
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
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

        # Tastatur-Steuerung für Menüs
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

            if keys[pygame.K_SPACE] and not player.reloading:
                player.set_shoot()

            move()
            draw(canvas_mouse_pos)
        else:
            draw(canvas_mouse_pos)

    scaled_surface = pygame.transform.scale(canvas, window.get_size())
    window.blit(scaled_surface, (0, 0))

    pygame.display.update()
    clock.tick(60)

pygame.quit()
