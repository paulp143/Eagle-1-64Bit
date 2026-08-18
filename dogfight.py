import pygame 
from sys import exit
import os,random,math


GAME_WIDTH=1280
GAME_HEIGHT=720

PLAYER_Y=256
PLAYER_X=256
PLAYER_WIDTH=48
PLAYER_HEIGHT=61
PLAYER_MAX_HEALTH=5
PLAYER_MAX_BULLETS=200
PLAYER_RELOAD_TIME=5000
PLAYER_ATTACK_DAMAGE_KAMIKAZE=4
PLAYER_INVINCIBLE_TIME=1000
PLAYER_MAX_SHIELD=20
PLAYER_SPACE_LOCK_TIME=1000
PLAYER_MOVEMENT_SPEED_Y=6
PLAYER_MOVEMENT_SPEED_X=6
PLAYER_TURN_RATE=4

BULLET_WIDTH=9
BULLET_HEIGHT=12
BULLET_VELOCITY_Y=8
BULLET_UI_WIDTH = BULLET_WIDTH / 2  # 4 px
BULLET_UI_HEIGHT =BULLET_HEIGHT / 2

SHIELD_UI_WIDTH=12
SHIELD_UI_HEIGHT=8
SHIELD_REGENERATION_TIME=2000


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


def load_image(image_path, scale=None):
    if os.path.exists(image_path):
        image = pygame.image.load(image_path)
    else:
        image = pygame.image.load(os.path.join("Images", image_path))
    if scale is not None:
        image = pygame.transform.scale(image, scale)
    return image

def load_highscore(filepath=r"C:\Users\paul\OneDrive\Desktop\Python\Pygame\Dogfight\data\highscore.txt"):
    try:
        with open(filepath,"r") as file:
            return int(file.read().strip())
    except (FileNotFoundError,ValueError):
        return 0
    
def add_highscore(new_highscore,filepath=r"C:\Users\paul\OneDrive\Desktop\Python\Pygame\Dogfight\data\highscore.txt"):
    with open(filepath,"w") as file:
        
        file.write(str(new_highscore))
        
        print("it works")
            
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

player_image=load_image(r"C:\Users\paul\OneDrive\Desktop\Python\Pygame\Dogfight\images\Space-Invaders-Ship.png", (PLAYER_WIDTH,PLAYER_HEIGHT))
bullet_image=load_image(r"C:\Users\paul\OneDrive\Desktop\Python\Pygame\Dogfight\images\bullet.png", (BULLET_WIDTH,BULLET_HEIGHT))
light_enemy_image=load_image(r"C:\Users\paul\OneDrive\Desktop\Python\Pygame\Dogfight\images\enemy1.png",(LIGHT_ENEMY_WIDTH,LIGHT_ENEMY_HEIGHT))
enemy_bullet_image=load_image(r"C:\Users\paul\OneDrive\Desktop\Python\Pygame\Dogfight\images\enemy_bullet.png", (BULLET_WIDTH,BULLET_HEIGHT))
backround_image=load_image(r"C:\Users\paul\OneDrive\Desktop\Python\Pygame\Dogfight\images\backround.png",(GAME_WIDTH,GAME_HEIGHT))
light_enemy_explosion_image=load_image(r"C:\Users\paul\OneDrive\Desktop\Python\Pygame\Dogfight\images\light_enemy_explosion.png", (LIGHT_ENEMY_WIDTH,LIGHT_ENEMY_HEIGHT))
health_image=load_image(r"C:\Users\paul\OneDrive\Desktop\Python\Pygame\Images\health.png",(HEALTH_WIDTH,HEALTH_HEIGHT))
bullet_ui_image=load_image(r"C:\Users\paul\OneDrive\Desktop\Python\Pygame\Dogfight\images\bullet_ui.png",(BULLET_UI_WIDTH,BULLET_UI_HEIGHT))
large_explosion_a_spritesheet=Spritesheet(r"C:\Users\paul\OneDrive\Desktop\Python\Pygame\Dogfight\Animation\LargeExplosionA\Spritesheet\LargeExplosionA_spritesheet.png",23)


pygame.init()
font = pygame.font.SysFont("arial", 24, bold=True)
title_font=pygame.font.SysFont("arial",48,bold=True)
clock=pygame.time.Clock()
window=pygame.display.set_mode((GAME_WIDTH,GAME_HEIGHT), pygame.RESIZABLE)
canvas=pygame.Surface((GAME_WIDTH,GAME_HEIGHT))
frame_number=23
frame_width=large_explosion_a_spritesheet.sheet.get_width()/23
frame_height=large_explosion_a_spritesheet.sheet.get_height()
game_state="main_menu"


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

            pygame.time.set_timer(SHOOTING_END, 100, 1)

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
            

    def __init__(self, x=None, y=0):
        if x is None:
            x = random.randrange(0, GAME_WIDTH - LIGHT_ENEMY_WIDTH, LIGHT_ENEMY_WIDTH * 2)
        pygame.Rect.__init__(self, x, y, LIGHT_ENEMY_WIDTH, LIGHT_ENEMY_HEIGHT)
        self.image = light_enemy_image
        self.health = LIGHT_ENEMY_HEALTH
        self.velocity_y = 2
        self.used = False
        self.bullets = []
        self.shooting = False
        self.explosion_damage=LIGHT_ENEMY_EXPLOSION_DAMAGE
        self.exploding=False
        self.bullet_damage=LIGHT_ENEMY_BULLET_DAMAGE
        self.x=x
    def set_shoot(self):
        bullet_x = self.x + (LIGHT_ENEMY_WIDTH // 2) - (BULLET_WIDTH // 2)
        bullet_y = self.y + LIGHT_ENEMY_HEIGHT
        self.bullets.append(Light_Enemy.Bullet(bullet_x, bullet_y))

def move():
    global light_enemy
    global explosion_group
    if player.health <= 0:
        return

    if player.pos_x < 0:
        player.pos_x = 0
    if player.pos_x + PLAYER_WIDTH > GAME_WIDTH:
        player.pos_x = GAME_WIDTH - PLAYER_WIDTH
    if player.pos_y < 0:
        player.pos_y = 0
    if player.pos_y + PLAYER_HEIGHT > GAME_HEIGHT:
        player.pos_y = GAME_HEIGHT - PLAYER_HEIGHT
    player.x = int(player.pos_x)
    player.y = int(player.pos_y)

    for bullet in player.bullets:
        bullet.update_position()
        if bullet.colliderect(light_enemy) and not light_enemy.exploding:
            bullet.used = True
            light_enemy.health -= 1

    if player.colliderect(light_enemy):
        light_enemy.health-=player.kamikaze_attack_damage
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
                    and 0 <= bullet.x <= GAME_WIDTH and 0 <= bullet.y <= GAME_HEIGHT]

    light_enemy.y += light_enemy.velocity_y
    
    for bullet in light_enemy.bullets:
        bullet.y += bullet.velocity_y
        if bullet.colliderect(player):
            bullet.used = True
            player.take_damage(light_enemy.bullet_damage)

    light_enemy.bullets = [bullet for bullet in light_enemy.bullets if not bullet.used \
                           and bullet.y < GAME_HEIGHT]

    if light_enemy.y > GAME_HEIGHT:
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
    if player.score>player.highscore:
        player.highscore=player.score
        add_highscore(player.score)
    player.health=player.max_health
    player.bullets.clear()
    
    player.score=0
    light_enemy.x=random.randrange(0, GAME_WIDTH - LIGHT_ENEMY_WIDTH, LIGHT_ENEMY_WIDTH * 2)
    light_enemy.y=0
    light_enemy.health=LIGHT_ENEMY_HEALTH
    light_enemy.bullets.clear()
    player.shield=PLAYER_MAX_SHIELD
    explosion_group.empty()


def main_menu():
    canvas.fill((0,0,0))
    canvas.blit(backround_image,(0,0))
    title_surface=title_font.render("Starblast",True,(255,255,255))
    title_rect=title_surface.get_rect(centerx=GAME_WIDTH/2,bottom=GAME_HEIGHT*0.2)
    canvas.blit(title_surface,title_rect)
    play_surface=font.render("To play press SPACE",True,(255,255,255))
    play_rect=play_surface.get_rect(centerx=GAME_WIDTH/2,bottom=GAME_HEIGHT/2+50)
    canvas.blit(play_surface,play_rect)
def draw():
    canvas.fill((0,0,0))
    canvas.blit(backround_image,(0,0))

    if player.health <= 0:
        respawn_surface=font.render("Press R to Respawn", True, (255, 255, 255))
        respawn_rect=respawn_surface.get_rect(centerx=GAME_WIDTH / 2, bottom=GAME_HEIGHT/2)
        loby_surface=font.render("Press SPACE to go back to the Main Menu",True,(255,255,255))
        loby_rect=loby_surface.get_rect(centerx=GAME_WIDTH/2,bottom=GAME_HEIGHT/2+30)
        canvas.blit(respawn_surface, respawn_rect)
        canvas.blit(loby_surface,loby_rect)
        
    else:
        rotated_player_image = pygame.transform.rotate(player.original_image, player.angle)
        player_rect = rotated_player_image.get_rect(center=(player.x + PLAYER_WIDTH // 2, player.y + PLAYER_HEIGHT // 2))
        canvas.blit(rotated_player_image, player_rect.topleft)

        for bullet in player.bullets:
            bullet_rect = bullet.image.get_rect(center=(bullet.x + BULLET_WIDTH // 2, bullet.y + BULLET_HEIGHT // 2))
            canvas.blit(bullet.image, bullet_rect.topleft)

        for bullet in light_enemy.bullets:
            canvas.blit(enemy_bullet_image,bullet)
        if not light_enemy.exploding:
            canvas.blit(light_enemy.image, (light_enemy.x,light_enemy.y))

        explosion_group.update()
        explosion_group.draw(canvas)

        score_surface = font.render(f"Score: {player.score}", True, (255, 255, 255))
        score_rect = score_surface.get_rect(centerx=GAME_WIDTH // 2, bottom=GAME_HEIGHT - 10)
        canvas.blit(score_surface, score_rect)

        highscore_surface = font.render(f"highscore: {player.highscore}", True, (255, 255, 255))
        highscore_rect = highscore_surface.get_rect(centerx=GAME_WIDTH // 2, bottom=GAME_HEIGHT - 30)
        canvas.blit(highscore_surface, highscore_rect)

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


player=Player()
light_enemy=Light_Enemy()
player.bullets=[]
explosion_group=pygame.sprite.Group()


while True:
    for event in pygame.event.get():
        if event.type==pygame.QUIT:
            if player.score>player.highscore:
                add_highscore(player.score)
            pygame.quit()
            exit()
        if event.type==SHOOTING_END:
            player.shooting=False
        if event.type==ADD_SCORE:
            player.add_score()
        if event.type==LIGHT_ENEMY_SHOOT and not light_enemy.exploding:
            light_enemy.set_shoot()
        if event.type==RELOAD_END:
            player.used_bullets=0
            player.reloading=False
        if event.type == LIGHT_ENEMY_EXPLOSION:
            old_bullets = light_enemy.bullets
            light_enemy = Light_Enemy()
            light_enemy.bullets = old_bullets
        if event.type==INVINCIBLE_END:
            player.invincible=False
        if event.type==SHIELD_REGENERATION:
            if player.shield<PLAYER_MAX_SHIELD:
                player.shield+=1



                
            
    keys=pygame.key.get_pressed()
    if player.health > 0:
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            player.angle += player.turn_rate
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            player.angle -= player.turn_rate

        rad = math.radians(player.angle)
        dx = -math.sin(rad)
        dy = -math.cos(rad)

        if keys[pygame.K_w] or keys[pygame.K_UP]:
            player.pos_x += dx * PLAYER_MOVEMENT_SPEED_X
            player.pos_y += dy * PLAYER_MOVEMENT_SPEED_Y
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:
            player.pos_x -= dx * PLAYER_MOVEMENT_SPEED_X
            player.pos_y -= dy * PLAYER_MOVEMENT_SPEED_Y

        player.angle %= 360
        player.x = int(player.pos_x)
        player.y = int(player.pos_y)

        if (keys[pygame.K_SPACE]) and not player.reloading :
            player.set_shoot()


            
    else:
        if keys[pygame.K_r]:
            respawn()
        elif keys[pygame.K_SPACE]:
            game_state="main_menu"
    if game_state=="main_menu":
        main_menu()
        if (keys[pygame.K_SPACE])  :
            respawn()
            game_state=""
        if (keys[pygame.K_LSHIFT]) and (keys[pygame.K_RSHIFT]):
            if (keys[pygame.K_r]):
                player.highscore=0
                add_highscore(player.highscore)
        

        
    else:
        move()
        draw()
    
    scaled_surface = pygame.transform.scale(canvas, window.get_size())
    window.blit(scaled_surface, (0, 0))

    pygame.display.update()
    clock.tick(60)

