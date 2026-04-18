"""
player.py - Nhân vật người chơi
"""

import pygame
import math
from src.sprites import make_hero_sprite


class Player:
    def __init__(self, x, y):
        self.x = float(x)
        self.y = float(y)
        self.hp = 100
        self.max_hp = 100
        self.alive = True
        self.current_weapon = None
        self.hurt_timer = 0
        self.invincible_timer = 0  # bất tử tạm thời sau khi bị đánh
        self.INVINCIBLE_DURATION = 60
        self.score = 0

        # Sprites theo từng vũ khí
        self._sprites_cache = {}

    def get_sprite(self, frame=0):
        key = (self.current_weapon, frame)
        if key not in self._sprites_cache:
            self._sprites_cache[key] = make_hero_sprite(frame, self.current_weapon)
        return self._sprites_cache[key]

    def take_damage(self, damage):
        if self.invincible_timer > 0 or not self.alive:
            return False
        self.hp -= damage
        self.hurt_timer = 20
        self.invincible_timer = self.INVINCIBLE_DURATION
        if self.hp <= 0:
            self.hp = 0
            self.alive = False
        return True

    def heal(self, amount):
        self.hp = min(self.max_hp, self.hp + amount)

    def add_score(self, points):
        self.score += points

    def update(self):
        if self.hurt_timer > 0:
            self.hurt_timer -= 1
        if self.invincible_timer > 0:
            self.invincible_timer -= 1

    def get_pos(self):
        return (int(self.x), int(self.y))

    def get_rect(self):
        return pygame.Rect(self.x - 24, self.y - 45, 48, 45)

    def draw(self, surface):
        frame = 0
        sprite = self.get_sprite(frame)
        w, h = sprite.get_size()

        # Nhấp nháy khi bị đánh
        if self.hurt_timer > 0 and self.hurt_timer % 4 < 2:
            tinted = sprite.copy()
            tinted.fill((255, 100, 100, 150), special_flags=pygame.BLEND_RGBA_MULT)
            sprite = tinted

        # Nhấp nháy khi bất tử
        elif self.invincible_timer > 0 and self.invincible_timer % 6 < 3:
            sprite = sprite.copy()
            sprite.set_alpha(120)

        surface.blit(sprite, (int(self.x) - w // 2, int(self.y) - h))

        # Hào quang vũ khí nhỏ dưới chân
        if self.current_weapon:
            colors = {
                'iron_gauntlets': (180, 180, 220),
                'sword': (150, 200, 255),
                'bow': (50, 220, 150),
                'grenade': (200, 120, 50),
                'gun': (160, 160, 200),
            }
            c = colors.get(self.current_weapon, (200, 200, 200))
            glow = pygame.Surface((60, 10), pygame.SRCALPHA)
            pygame.draw.ellipse(glow, (*c, 60), (0, 0, 60, 10))
            surface.blit(glow, (int(self.x) - 30, int(self.y) - 4))
