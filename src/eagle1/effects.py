"""Shared visual effect helpers and explosion sprite classes."""

import pygame

FRAME_MULTIPLIKATOR = 2
FRAME_SPEED = 0.4


class Spritesheet:
    def __init__(self, image, cols):
        self.sheet = image
        self.cols = cols
        self.frame_width = self.sheet.get_width() / cols
        self.frame_height = self.sheet.get_height()
        self.frames = self.extract_frames()

    def extract_frames(self):
        frames = []
        for i in range(self.cols):
            rect = pygame.Rect(
                int(i * self.frame_width),
                0,
                int(self.frame_width),
                self.frame_height,
            )
            frame = self.sheet.subsurface(rect)
            frame = pygame.transform.scale(
                frame,
                (
                    int(self.frame_width * FRAME_MULTIPLIKATOR),
                    int(self.frame_height * FRAME_MULTIPLIKATOR),
                ),
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
