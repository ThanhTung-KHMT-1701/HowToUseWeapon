"""
enemy.py - Các loại quái vật
"""

import pygame
import math
import random
from src.sprites import (make_hulk_sprite, make_samurai_sprite,
                         make_alien_sprite, make_dragon_sprite,
                         make_ghost_sprite, make_fast_alien_sprite,
                         make_elite_hulk_sprite, get_gif_frames)


class Enemy:
    """Base class quái vật"""
    def __init__(self, x, y, hp, speed, damage, sprite_func, enemy_type):
        self.x = float(x)
        self.y = float(y)
        self.hp = hp
        self.max_hp = hp
        self.speed = speed
        self.damage = damage
        self.enemy_type = enemy_type
        self.alive = True
        self.hit_timer = 0    # nhấp nháy khi bị đánh
        self.stagger_timer = 0
        self.vx = 0.0
        self.vy = 0.0
        self.GRAVITY = 0.3
        self.on_ground = True
        self.attack_timer = 0
        self.ATTACK_COOLDOWN = 90
        self.die_timer = 0
        self.DIE_DURATION = 30

        # Sprites (idle + hit frame)
        self.sprites = [sprite_func(0), sprite_func(1)]
        self.frame = 0
        self.anim_timer = 0

        self.rect = self.sprites[0].get_rect()

    def get_rect(self):
        w, h = self.sprites[0].get_size()
        return pygame.Rect(self.x - w // 2, self.y - h, w, h)

    def take_damage(self, damage):
        if not self.alive:
            return
        self.hp -= damage
        self.hit_timer = 12
        if self.hp <= 0:
            self.hp = 0
            self.alive = False
            self.die_timer = self.DIE_DURATION

    def knockback(self, dx, dy):
        self.vx += dx
        self.vy += dy
        self.stagger_timer = 15

    def _obstacle_ahead(self, direction_x, obstacles, look_ahead=60):
        """Kiểm tra xem có obstacle phía trước không.
        Trả về obstacle nếu có, None nếu không."""
        if not obstacles:
            return None
        check_x = self.x + direction_x * look_ahead
        check_y = self.y - 40  # kiểm tra ở tầm hông
        for obs in obstacles:
            r = obs.get_rect()
            if r.collidepoint(check_x, check_y):
                return obs
        return None

    def _avoid_obstacle(self, dx_move, obstacles, screen_w):
        """Tránh obstacle phía trước: đi vòng lên/xuống hoặc đổi hướng."""
        if not obstacles:
            return dx_move, 0
        direction = 1 if dx_move > 0 else -1
        obs = self._obstacle_ahead(direction, obstacles)
        if obs is None:
            return dx_move, 0
        # Có obstacle phía trước → đi lên trên để vòng qua
        r = obs.get_rect()
        # Nếu enemy ở trên obstacle → tiếp tục đi ngang
        if self.y - 50 < r.top:
            return dx_move, 0
        # Đi lên + sang bên để vòng qua
        return dx_move * 0.3, -self.speed * 0.8

    def move_toward(self, target_x, target_y, floor_y):
        if not self.alive or self.stagger_timer > 0:
            return
        dx = target_x - self.x
        dy = target_y - self.y
        dist = math.sqrt(dx * dx + dy * dy) or 1
        self.x += (dx / dist) * self.speed
        # Giữ trên mặt đất
        if self.y < floor_y:
            self.vy += self.GRAVITY
        else:
            self.y = floor_y
            self.vy = 0

    def update(self, player_x, player_y, floor_y, screen_w, obstacles=None):
        if not self.alive:
            if self.die_timer > 0:
                self.die_timer -= 1
            return

        if self.stagger_timer > 0:
            self.stagger_timer -= 1

        # Physics
        self.x += self.vx
        self.y += self.vy
        self.vy += self.GRAVITY if self.y < floor_y else 0
        if self.y >= floor_y:
            self.y = floor_y
            self.vy = 0
        self.vx *= 0.85  # friction

        # Clamp
        w = self.sprites[0].get_width()
        self.x = max(w // 2, min(screen_w - w // 2, self.x))

        # Chuyển động về phía player
        self.move_toward(player_x, player_y, floor_y)

        # Animation
        if self.hit_timer > 0:
            self.hit_timer -= 1
        self.anim_timer += 1
        if self.anim_timer > 20:
            self.anim_timer = 0
            self.frame = 1 - self.frame

        # Attack timer
        if self.attack_timer > 0:
            self.attack_timer -= 1

    def can_attack(self, player_x, player_y):
        dist = math.dist((self.x, self.y), (player_x, player_y))
        return dist < self.attack_range and self.attack_timer == 0 and self.alive

    def perform_attack(self):
        self.attack_timer = self.ATTACK_COOLDOWN
        return self.damage

    def draw(self, surface):
        sprite = self.sprites[self.frame]
        w, h = sprite.get_size()

        # Nhấp nháy đỏ khi bị đánh
        if self.hit_timer > 0 and self.hit_timer % 3 < 2:
            tinted = sprite.copy()
            tinted.fill((255, 80, 80, 120), special_flags=pygame.BLEND_RGBA_MULT)
            sprite = tinted

        # Fade out khi chết
        if not self.alive and self.die_timer > 0:
            alpha = int(255 * self.die_timer / self.DIE_DURATION)
            sprite = sprite.copy()
            sprite.set_alpha(alpha)
            # Vẽ xoay nghiêng
            angle = (self.DIE_DURATION - self.die_timer) * 3
            sprite = pygame.transform.rotate(sprite, angle)
            rect = sprite.get_rect(center=(int(self.x), int(self.y) - h // 2))
            surface.blit(sprite, rect)
            return

        if not self.alive:
            return

        surface.blit(sprite, (int(self.x) - w // 2, int(self.y) - h))

        # HP bar
        bar_w = w
        bar_h = 5
        bx = int(self.x) - bar_w // 2
        by = int(self.y) - h - 10
        pygame.draw.rect(surface, (80, 0, 0), (bx, by, bar_w, bar_h), border_radius=2)
        hp_frac = self.hp / self.max_hp
        pygame.draw.rect(surface, (
            int(255 * (1 - hp_frac)),
            int(255 * hp_frac),
            30
        ), (bx, by, int(bar_w * hp_frac), bar_h), border_radius=2)


class MonsterEnemy(Enemy):
    """Monster chết chóc - nhanh, né đòn khi bị đánh, cận chiến"""
    def __init__(self, x, y):
        super().__init__(
            x, y, hp=150, speed=2.8, damage=30,
            sprite_func=make_hulk_sprite,   # fallback
            enemy_type='monster'
        )
        self.attack_range = 110
        self.ATTACK_COOLDOWN = 55
        # Dùng 21_monster.gif
        self._gif_frames = get_gif_frames('21_monster.gif', (90, 90))
        self._gif_idx = 0
        self._gif_timer = 0
        # Dodge AI: khi bị đánh, né sang bên
        self._dodge_timer = 0
        self._dodge_vx = 0

    def take_damage(self, damage):
        if not self.alive:
            return
        super().take_damage(damage)
        # Né sang bên khi bị đánh
        if self.alive and self._dodge_timer <= 0:
            self._dodge_timer = 20
            self._dodge_vx = random.choice([-8, 8])

    def update(self, player_x, player_y, floor_y, screen_w, obstacles=None):
        if not self.alive:
            if self.die_timer > 0:
                self.die_timer -= 1
            return

        if self.stagger_timer > 0:
            self.stagger_timer -= 1
        else:
            # Dodge: di chuyển nhanh sang bên
            if self._dodge_timer > 0:
                self._dodge_timer -= 1
                self.x += self._dodge_vx
                self._dodge_vx *= 0.9
            else:
                # AI: di chuyển thông minh — tiến đến player nhưng zigzag
                dx = player_x - self.x
                dy = player_y - self.y
                dist = max(1, math.sqrt(dx * dx + dy * dy))
                # Zigzag: thêm chuyển động ngang sin
                zigzag = math.sin(self.anim_timer * 0.15) * 2.5
                move_x = (dx / dist) * self.speed + zigzag
                move_y = (dy / dist) * self.speed * 0.3
                # Tránh obstacle
                move_x, extra_y = self._avoid_obstacle(move_x, obstacles, screen_w)
                self.x += move_x
                self.y += move_y + extra_y

        self.x += self.vx
        self.vx *= 0.85
        self.y = min(floor_y, max(floor_y - 60, self.y))
        self.x = max(30, min(screen_w - 30, self.x))

        if self.hit_timer > 0:
            self.hit_timer -= 1
        self.anim_timer += 1
        if self.anim_timer > 14:
            self.anim_timer = 0
            self.frame = 1 - self.frame
        if self.attack_timer > 0:
            self.attack_timer -= 1
        # GIF animation
        if self._gif_frames:
            self._gif_timer += 1
            if self._gif_timer > 4:
                self._gif_timer = 0
                self._gif_idx = (self._gif_idx + 1) % len(self._gif_frames)

    def draw(self, surface):
        if self._gif_frames:
            sprite = self._gif_frames[self._gif_idx]
            w, h = sprite.get_size()
            if self.hit_timer > 0 and self.hit_timer % 3 < 2:
                sprite = sprite.copy()
                sprite.fill((255, 80, 80, 120), special_flags=pygame.BLEND_RGBA_MULT)
            if not self.alive and self.die_timer > 0:
                alpha = int(255 * self.die_timer / self.DIE_DURATION)
                sprite = sprite.copy()
                sprite.set_alpha(alpha)
                angle = (self.DIE_DURATION - self.die_timer) * 3
                sprite = pygame.transform.rotate(sprite, angle)
                rect = sprite.get_rect(center=(int(self.x), int(self.y) - h // 2))
                surface.blit(sprite, rect)
                return
            if not self.alive:
                return
            surface.blit(sprite, (int(self.x) - w // 2, int(self.y) - h))
            bar_w = w
            bar_h = 5
            bx = int(self.x) - bar_w // 2
            by = int(self.y) - h - 10
            pygame.draw.rect(surface, (80, 0, 0), (bx, by, bar_w, bar_h), border_radius=2)
            hp_frac = self.hp / self.max_hp
            pygame.draw.rect(surface, (
                int(255 * (1 - hp_frac)), int(255 * hp_frac), 30
            ), (bx, by, int(bar_w * hp_frac), bar_h), border_radius=2)
        else:
            super().draw(surface)


class BlobAlienEnemy(Enemy):
    """Blob Alien - HP cao, chậm, bao vây đi vòng qua lưng player"""
    def __init__(self, x, y):
        super().__init__(
            x, y, hp=220, speed=1.5, damage=35,
            sprite_func=make_hulk_sprite,   # fallback
            enemy_type='blob_alien'
        )
        self.attack_range = 100
        self.ATTACK_COOLDOWN = 80
        # Dùng 19_blob_alien_passive.gif (kích thước khác Ghost)
        self._gif_frames = get_gif_frames('19_blob_alien_passive.gif', (100, 100))
        self._gif_idx = 0
        self._gif_timer = 0
        # Flank AI: đi vòng qua lưng
        self._flank_side = random.choice([-1, 1])
        self._flank_timer = 0

    def update(self, player_x, player_y, floor_y, screen_w, obstacles=None):
        if not self.alive:
            if self.die_timer > 0:
                self.die_timer -= 1
            return

        if self.stagger_timer > 0:
            self.stagger_timer -= 1
        else:
            dx = player_x - self.x
            dy = player_y - self.y
            dist = max(1, math.sqrt(dx * dx + dy * dy))

            # Flank AI: nếu xa, đi vòng sang bên; nếu gần, tiến thẳng
            if dist > 200:
                # Đi vòng: di chuyển ngang + tiến gần
                move_x = self._flank_side * self.speed * 1.5
                move_y = (dy / dist) * self.speed * 0.5
                self._flank_timer += 1
                # Đổi hướng flank mỗi 120 frames
                if self._flank_timer > 120:
                    self._flank_timer = 0
                    self._flank_side *= -1
            else:
                # Gần player: lao thẳng vào
                move_x = (dx / dist) * self.speed
                move_y = (dy / dist) * self.speed * 0.3
            # Tránh obstacle
            move_x, extra_y = self._avoid_obstacle(move_x, obstacles, screen_w)
            self.x += move_x
            self.y += move_y + extra_y

        self.x += self.vx
        self.vx *= 0.85
        self.y = min(floor_y, max(floor_y - 40, self.y))
        self.x = max(30, min(screen_w - 30, self.x))

        if self.hit_timer > 0:
            self.hit_timer -= 1
        self.anim_timer += 1
        if self.anim_timer > 16:
            self.anim_timer = 0
            self.frame = 1 - self.frame
        if self.attack_timer > 0:
            self.attack_timer -= 1
        # GIF animation
        if self._gif_frames:
            self._gif_timer += 1
            if self._gif_timer > 4:
                self._gif_timer = 0
                self._gif_idx = (self._gif_idx + 1) % len(self._gif_frames)

    def draw(self, surface):
        if self._gif_frames:
            sprite = self._gif_frames[self._gif_idx]
            w, h = sprite.get_size()
            if self.hit_timer > 0 and self.hit_timer % 3 < 2:
                sprite = sprite.copy()
                sprite.fill((255, 80, 80, 120), special_flags=pygame.BLEND_RGBA_MULT)
            if not self.alive and self.die_timer > 0:
                alpha = int(255 * self.die_timer / self.DIE_DURATION)
                sprite = sprite.copy()
                sprite.set_alpha(alpha)
                angle = (self.DIE_DURATION - self.die_timer) * 3
                sprite = pygame.transform.rotate(sprite, angle)
                rect = sprite.get_rect(center=(int(self.x), int(self.y) - h // 2))
                surface.blit(sprite, rect)
                return
            if not self.alive:
                return
            surface.blit(sprite, (int(self.x) - w // 2, int(self.y) - h))
            bar_w = w
            bar_h = 5
            bx = int(self.x) - bar_w // 2
            by = int(self.y) - h - 10
            pygame.draw.rect(surface, (80, 0, 0), (bx, by, bar_w, bar_h), border_radius=2)
            hp_frac = self.hp / self.max_hp
            pygame.draw.rect(surface, (
                int(255 * (1 - hp_frac)), int(255 * hp_frac), 30
            ), (bx, by, int(bar_w * hp_frac), bar_h), border_radius=2)
        else:
            super().draw(surface)


class AlienEnemy(Enemy):
    """Alien - bay/di chuyển lên xuống, bắn đạn, HP thấp"""
    def __init__(self, x, y):
        super().__init__(
            x, y, hp=80, speed=1.8, damage=15,
            sprite_func=make_alien_sprite,
            enemy_type='alien'
        )
        self.attack_range = 350
        self.float_timer = 0
        self.base_y = float(y)
        self.ATTACK_COOLDOWN = 120
        # Load GIF frames
        self._gif_frames = get_gif_frames('18_alien_firing_animation.gif', (80, 80))
        self._gif_idx = 0
        self._gif_timer = 0

    def update(self, player_x, player_y, floor_y, screen_w, obstacles=None):
        if not self.alive:
            if self.die_timer > 0:
                self.die_timer -= 1
            return

        # Bay lên xuống
        self.float_timer += 0.05
        self.y = self.base_y + math.sin(self.float_timer) * 30

        # Di chuyển ngang
        if self.stagger_timer > 0:
            self.stagger_timer -= 1
        else:
            dx = player_x - self.x
            self.x += (dx / max(1, abs(dx))) * self.speed

        self.x += self.vx
        self.vx *= 0.85
        self.x = max(20, min(screen_w - 20, self.x))

        if self.hit_timer > 0:
            self.hit_timer -= 1
        self.anim_timer += 1
        if self.anim_timer > 15:
            self.anim_timer = 0
            self.frame = 1 - self.frame
        if self.attack_timer > 0:
            self.attack_timer -= 1
        # GIF animation
        if self._gif_frames:
            self._gif_timer += 1
            if self._gif_timer > 4:  # ~15 FPS
                self._gif_timer = 0
                self._gif_idx = (self._gif_idx + 1) % len(self._gif_frames)

    def draw(self, surface):
        if self._gif_frames:
            self._draw_gif(surface)
        else:
            super().draw(surface)

    def _draw_gif(self, surface):
        sprite = self._gif_frames[self._gif_idx]
        w, h = sprite.get_size()

        if self.hit_timer > 0 and self.hit_timer % 3 < 2:
            sprite = sprite.copy()
            sprite.fill((255, 80, 80, 120), special_flags=pygame.BLEND_RGBA_MULT)

        if not self.alive and self.die_timer > 0:
            alpha = int(255 * self.die_timer / self.DIE_DURATION)
            sprite = sprite.copy()
            sprite.set_alpha(alpha)
            angle = (self.DIE_DURATION - self.die_timer) * 3
            sprite = pygame.transform.rotate(sprite, angle)
            rect = sprite.get_rect(center=(int(self.x), int(self.y) - h // 2))
            surface.blit(sprite, rect)
            return

        if not self.alive:
            return

        surface.blit(sprite, (int(self.x) - w // 2, int(self.y) - h))

        # HP bar
        bar_w = w
        bar_h = 5
        bx = int(self.x) - bar_w // 2
        by = int(self.y) - h - 10
        pygame.draw.rect(surface, (80, 0, 0), (bx, by, bar_w, bar_h), border_radius=2)
        hp_frac = self.hp / self.max_hp
        pygame.draw.rect(surface, (
            int(255 * (1 - hp_frac)), int(255 * hp_frac), 30
        ), (bx, by, int(bar_w * hp_frac), bar_h), border_radius=2)


class AlienProjectile:
    """Đạn của Alien bắn ra"""
    def __init__(self, x, y, vx, vy):
        self.x = float(x)
        self.y = float(y)
        self.vx = vx
        self.vy = vy
        self.alive = True
        self.color = (0, 255, 180)
        self.r = 6
        self.damage = 15

    def update(self, screen_w, screen_h):
        self.x += self.vx
        self.y += self.vy
        if self.x < 0 or self.x > screen_w or self.y < 0 or self.y > screen_h:
            self.alive = False

    def draw(self, surface):
        s = pygame.Surface((self.r * 4, self.r * 4), pygame.SRCALPHA)
        pygame.draw.circle(s, (*self.color, 200), (self.r * 2, self.r * 2), self.r)
        pygame.draw.circle(s, (255, 255, 255, 180), (self.r * 2, self.r * 2), self.r // 2)
        surface.blit(s, (int(self.x) - self.r * 2, int(self.y) - self.r * 2))

    def get_rect(self):
        return pygame.Rect(self.x - self.r, self.y - self.r, self.r * 2, self.r * 2)


class FireBreath:
    """Lửa phun của Dragon - AoE hình nón, tồn tại ngắn"""
    def __init__(self, x, y, vx, vy):
        self.x = float(x)
        self.y = float(y)
        self.vx = vx
        self.vy = vy
        self.alive = True
        self.r = 10
        self.timer = 40
        self.damage = 20

    def update(self, screen_w, screen_h):
        self.x += self.vx
        self.y += self.vy
        self.r = min(18, self.r + 0.3)
        self.timer -= 1
        if self.timer <= 0:
            self.alive = False
        if self.x < 0 or self.x > screen_w or self.y < 0 or self.y > screen_h:
            self.alive = False

    def draw(self, surface):
        alpha = int(220 * (self.timer / 40.0))
        r = int(self.r)
        s = pygame.Surface((r * 4, r * 4), pygame.SRCALPHA)
        pygame.draw.circle(s, (255, 100, 20, alpha), (r * 2, r * 2), r)
        pygame.draw.circle(s, (255, 200, 50, alpha // 2), (r * 2, r * 2), max(1, r // 2))
        surface.blit(s, (int(self.x) - r * 2, int(self.y) - r * 2))

    def get_rect(self):
        r = int(self.r)
        return pygame.Rect(self.x - r, self.y - r, r * 2, r * 2)


class DragonEnemy(Enemy):
    """Dragon - bay, phun lửa AoE, HP cao"""
    def __init__(self, x, y):
        super().__init__(
            x, y, hp=250, speed=1.5, damage=30,
            sprite_func=make_dragon_sprite,
            enemy_type='dragon'
        )
        self.attack_range = 300
        self.float_timer = 0
        self.base_y = float(y) - 80
        self.ATTACK_COOLDOWN = 100
        self._swoop_timer = 0
        self._swoop_target = None

    def update(self, player_x, player_y, floor_y, screen_w, obstacles=None):
        if not self.alive:
            if self.die_timer > 0:
                self.die_timer -= 1
            return

        # Bay lên xuống kiểu rồng (biên độ lớn hơn alien)
        self.float_timer += 0.03
        target_y = self.base_y + math.sin(self.float_timer) * 50

        if self.stagger_timer > 0:
            self.stagger_timer -= 1
        else:
            # Di chuyển ngang về phía player
            dx = player_x - self.x
            self.x += (dx / max(1, abs(dx))) * self.speed

            # Swoop attack: đôi khi lao xuống gần player rồi bay lên
            if self._swoop_timer > 0:
                self._swoop_timer -= 1
                self.y += 4
                if self.y >= floor_y - 20:
                    self.y = floor_y - 20
                    self._swoop_timer = 0
            else:
                # Bay về vị trí bay bình thường
                dy = target_y - self.y
                self.y += dy * 0.05

        self.x += self.vx
        self.vx *= 0.85
        self.x = max(40, min(screen_w - 40, self.x))

        if self.hit_timer > 0:
            self.hit_timer -= 1
        self.anim_timer += 1
        if self.anim_timer > 18:
            self.anim_timer = 0
            self.frame = 1 - self.frame
        if self.attack_timer > 0:
            self.attack_timer -= 1


class GhostEnemy(Enemy):
    """Ghost - xuất hiện/biến mất, nhanh, xuyên obstacle"""
    def __init__(self, x, y):
        super().__init__(
            x, y, hp=60, speed=3.0, damage=20,
            sprite_func=make_ghost_sprite,
            enemy_type='ghost'
        )
        self.attack_range = 80
        self.ATTACK_COOLDOWN = 70
        self._phase_timer = 0
        self._visible = True
        self._phase_duration = 90  # 1.5 giây hiện, 1.5 giây ẩn
        # Load GIF frames
        self._gif_frames = get_gif_frames('19_blob_alien_passive.gif', (80, 80))
        self._gif_idx = 0
        self._gif_timer = 0

    def update(self, player_x, player_y, floor_y, screen_w, obstacles=None):
        if not self.alive:
            if self.die_timer > 0:
                self.die_timer -= 1
            return

        # Chu kỳ hiện/ẩn
        self._phase_timer += 1
        if self._phase_timer >= self._phase_duration:
            self._phase_timer = 0
            self._visible = not self._visible

        if self.stagger_timer > 0:
            self.stagger_timer -= 1
        else:
            # Di chuyển nhanh về phía player khi ẩn
            speed = self.speed * (1.5 if not self._visible else 1.0)
            dx = player_x - self.x
            dy = player_y - self.y
            dist = max(1, math.sqrt(dx*dx + dy*dy))
            self.x += (dx / dist) * speed
            self.y += (dy / dist) * speed

        # Ghost bay lơ lửng trên mặt đất
        float_offset = math.sin(self._phase_timer * 0.08) * 10
        self.y = min(floor_y - 10, self.y + float_offset * 0.1)

        self.x += self.vx
        self.vx *= 0.85
        self.x = max(20, min(screen_w - 20, self.x))

        if self.hit_timer > 0:
            self.hit_timer -= 1
        self.anim_timer += 1
        if self.anim_timer > 12:
            self.anim_timer = 0
            self.frame = 1 - self.frame
        if self.attack_timer > 0:
            self.attack_timer -= 1
        # GIF animation
        if self._gif_frames:
            self._gif_timer += 1
            if self._gif_timer > 3:  # ~20 FPS
                self._gif_timer = 0
                self._gif_idx = (self._gif_idx + 1) % len(self._gif_frames)

    def can_attack(self, player_x, player_y):
        # Chỉ tấn công khi hiện hình
        if not self._visible:
            return False
        return super().can_attack(player_x, player_y)

    def take_damage(self, damage):
        # Chỉ nhận sát thương khi hiện hình
        if not self._visible:
            return
        super().take_damage(damage)

    def draw(self, surface):
        if not self.alive and self.die_timer <= 0:
            return

        # Chon sprite: GIF frames hoac procedural
        if self._gif_frames:
            sprite = self._gif_frames[self._gif_idx]
        else:
            sprite = self.sprites[self.frame]
        w, h = sprite.get_size()

        # Ghost bán trong suốt khi ẩn
        if not self._visible and self.alive:
            ghost_alpha = 40 + int(30 * math.sin(self._phase_timer * 0.15))
            sprite = sprite.copy()
            sprite.set_alpha(ghost_alpha)
        elif self.hit_timer > 0 and self.hit_timer % 3 < 2:
            tinted = sprite.copy()
            tinted.fill((255, 80, 80, 120), special_flags=pygame.BLEND_RGBA_MULT)
            sprite = tinted

        if not self.alive and self.die_timer > 0:
            alpha = int(255 * self.die_timer / self.DIE_DURATION)
            sprite = sprite.copy()
            sprite.set_alpha(alpha)
            angle = (self.DIE_DURATION - self.die_timer) * 3
            sprite = pygame.transform.rotate(sprite, angle)
            rect = sprite.get_rect(center=(int(self.x), int(self.y) - h // 2))
            surface.blit(sprite, rect)
            return

        surface.blit(sprite, (int(self.x) - w // 2, int(self.y) - h))

        # HP bar (chỉ khi hiện hình)
        if self._visible:
            bar_w = w
            bar_h = 5
            bx = int(self.x) - bar_w // 2
            by = int(self.y) - h - 10
            pygame.draw.rect(surface, (80, 0, 0), (bx, by, bar_w, bar_h), border_radius=2)
            hp_frac = self.hp / self.max_hp
            pygame.draw.rect(surface, (
                int(255 * (1 - hp_frac)),
                int(255 * hp_frac),
                30
            ), (bx, by, int(bar_w * hp_frac), bar_h), border_radius=2)


class FastAlienEnemy(Enemy):
    """Alien nhanh - speed cao, ban 2 dan/lan"""
    def __init__(self, x, y):
        super().__init__(
            x, y, hp=80, speed=3.5, damage=12,
            sprite_func=make_fast_alien_sprite,
            enemy_type='fast_alien'
        )
        self.attack_range = 350
        self.ATTACK_COOLDOWN = 50
        self.float_timer = 0
        self.base_y = float(y)
        # Dung chung GIF voi AlienEnemy
        self._gif_frames = get_gif_frames('18_alien_firing_animation.gif', (70, 70))
        self._gif_idx = 0
        self._gif_timer = 0

    def update(self, player_x, player_y, floor_y, screen_w, obstacles=None):
        if not self.alive:
            if self.die_timer > 0:
                self.die_timer -= 1
            return
        self.float_timer += 0.06
        target_y = self.base_y + math.sin(self.float_timer) * 35
        if self.stagger_timer > 0:
            self.stagger_timer -= 1
        else:
            dx = player_x - self.x
            self.x += (dx / max(1, abs(dx))) * self.speed
            dy = target_y - self.y
            self.y += dy * 0.08
        self.x += self.vx
        self.vx *= 0.85
        self.x = max(30, min(screen_w - 30, self.x))
        if self.hit_timer > 0:
            self.hit_timer -= 1
        self.anim_timer += 1
        if self.anim_timer > 12:
            self.anim_timer = 0
            self.frame = 1 - self.frame
        if self.attack_timer > 0:
            self.attack_timer -= 1
        # GIF animation
        if self._gif_frames:
            self._gif_timer += 1
            if self._gif_timer > 3:
                self._gif_timer = 0
                self._gif_idx = (self._gif_idx + 1) % len(self._gif_frames)

    def draw(self, surface):
        if self._gif_frames:
            # Reuse AlienEnemy._draw_gif pattern
            sprite = self._gif_frames[self._gif_idx]
            w, h = sprite.get_size()
            if self.hit_timer > 0 and self.hit_timer % 3 < 2:
                sprite = sprite.copy()
                sprite.fill((255, 80, 80, 120), special_flags=pygame.BLEND_RGBA_MULT)
            if not self.alive and self.die_timer > 0:
                alpha = int(255 * self.die_timer / self.DIE_DURATION)
                sprite = sprite.copy()
                sprite.set_alpha(alpha)
                angle = (self.DIE_DURATION - self.die_timer) * 3
                sprite = pygame.transform.rotate(sprite, angle)
                rect = sprite.get_rect(center=(int(self.x), int(self.y) - h // 2))
                surface.blit(sprite, rect)
                return
            if not self.alive:
                return
            surface.blit(sprite, (int(self.x) - w // 2, int(self.y) - h))
            bar_w = w
            bar_h = 5
            bx = int(self.x) - bar_w // 2
            by = int(self.y) - h - 10
            pygame.draw.rect(surface, (80, 0, 0), (bx, by, bar_w, bar_h), border_radius=2)
            hp_frac = self.hp / self.max_hp
            pygame.draw.rect(surface, (
                int(255 * (1 - hp_frac)), int(255 * hp_frac), 30
            ), (bx, by, int(bar_w * hp_frac), bar_h), border_radius=2)
        else:
            super().draw(surface)


class EliteHulkEnemy(Enemy):
    """Hulk d'elite - nhanh hon, HP cao, damage lon"""
    def __init__(self, x, y):
        super().__init__(
            x, y, hp=350, speed=2.5, damage=40,
            sprite_func=make_elite_hulk_sprite,
            enemy_type='elite_hulk'
        )
        self.attack_range = 100
        self.ATTACK_COOLDOWN = 55
        # Boss GIF sprite
        self._gif_frames = get_gif_frames('20_boss_alien_passive.gif', (130, 130))
        self._gif_idx = 0
        self._gif_timer = 0

    def update(self, player_x, player_y, floor_y, screen_w, obstacles=None):
        if not self.alive:
            if self.die_timer > 0:
                self.die_timer -= 1
            return
        if self.stagger_timer > 0:
            self.stagger_timer -= 1
        else:
            dx = player_x - self.x
            move_x = (dx / max(1, abs(dx))) * self.speed
            # Tránh obstacle
            move_x, extra_y = self._avoid_obstacle(move_x, obstacles, screen_w)
            self.x += move_x
            if extra_y != 0:
                self.y += extra_y
            elif self.y != floor_y:
                dy = floor_y - self.y
                self.y += dy * 0.1
        self.x += self.vx
        self.vx *= 0.85
        self.x = max(30, min(screen_w - 30, self.x))
        if self.hit_timer > 0:
            self.hit_timer -= 1
        self.anim_timer += 1
        if self.anim_timer > 14:
            self.anim_timer = 0
            self.frame = 1 - self.frame
        if self.attack_timer > 0:
            self.attack_timer -= 1
        # GIF animation
        if self._gif_frames:
            self._gif_timer += 1
            if self._gif_timer > 4:
                self._gif_timer = 0
                self._gif_idx = (self._gif_idx + 1) % len(self._gif_frames)

    def draw(self, surface):
        if self._gif_frames:
            sprite = self._gif_frames[self._gif_idx]
            w, h = sprite.get_size()
            if self.hit_timer > 0 and self.hit_timer % 3 < 2:
                sprite = sprite.copy()
                sprite.fill((255, 80, 80, 120), special_flags=pygame.BLEND_RGBA_MULT)
            if not self.alive and self.die_timer > 0:
                alpha = int(255 * self.die_timer / self.DIE_DURATION)
                sprite = sprite.copy()
                sprite.set_alpha(alpha)
                angle = (self.DIE_DURATION - self.die_timer) * 3
                sprite = pygame.transform.rotate(sprite, angle)
                rect = sprite.get_rect(center=(int(self.x), int(self.y) - h // 2))
                surface.blit(sprite, rect)
                return
            if not self.alive:
                return
            surface.blit(sprite, (int(self.x) - w // 2, int(self.y) - h))
            bar_w = w
            bar_h = 5
            bx = int(self.x) - bar_w // 2
            by = int(self.y) - h - 10
            pygame.draw.rect(surface, (80, 0, 0), (bx, by, bar_w, bar_h), border_radius=2)
            hp_frac = self.hp / self.max_hp
            pygame.draw.rect(surface, (
                int(255 * (1 - hp_frac)), int(255 * hp_frac), 30
            ), (bx, by, int(bar_w * hp_frac), bar_h), border_radius=2)
        else:
            super().draw(surface)


class GifFireBreath:
    """Lửa phun GIF - dùng fire.gif thay vì vẽ hình tròn"""
    def __init__(self, x, y, vx, vy):
        self.x = float(x)
        self.y = float(y)
        self.vx = vx
        self.vy = vy
        self.alive = True
        self.timer = 50
        self.damage = 25
        self._gif_frames = get_gif_frames('fire.gif', (48, 48))
        self._gif_idx = 0
        self._gif_timer = 0
        # Tính góc quay dựa trên hướng bay
        self._angle = -math.degrees(math.atan2(vy, vx))

    def update(self, screen_w, screen_h):
        self.x += self.vx
        self.y += self.vy
        self.timer -= 1
        if self.timer <= 0:
            self.alive = False
        if self.x < 0 or self.x > screen_w or self.y < 0 or self.y > screen_h:
            self.alive = False
        # GIF animation
        if self._gif_frames:
            self._gif_timer += 1
            if self._gif_timer > 3:
                self._gif_timer = 0
                self._gif_idx = (self._gif_idx + 1) % len(self._gif_frames)

    def draw(self, surface):
        if self._gif_frames:
            sprite = self._gif_frames[self._gif_idx]
            # Xoay theo hướng bay
            rotated = pygame.transform.rotate(sprite, self._angle)
            rect = rotated.get_rect(center=(int(self.x), int(self.y)))
            alpha = int(255 * min(1.0, self.timer / 15.0))
            if alpha < 255:
                rotated = rotated.copy()
                rotated.set_alpha(alpha)
            surface.blit(rotated, rect)
        else:
            # Fallback
            pygame.draw.circle(surface, (255, 100, 20), (int(self.x), int(self.y)), 8)

    def get_rect(self):
        return pygame.Rect(self.x - 20, self.y - 20, 40, 40)


class BossAlienEnemy(Enemy):
    """Boss Alien - trung boss xuất hiện từ wave 3, phun lửa GIF"""
    def __init__(self, x, y):
        super().__init__(
            x, y, hp=300, speed=1.8, damage=35,
            sprite_func=make_elite_hulk_sprite,  # fallback
            enemy_type='boss_alien'
        )
        self.attack_range = 350
        self.ATTACK_COOLDOWN = 80
        # Dùng 20_boss_alien_passive.gif
        self._gif_frames = get_gif_frames('20_boss_alien_passive.gif', (110, 110))
        self._gif_idx = 0
        self._gif_timer = 0
        self._phase_timer = 0

    def update(self, player_x, player_y, floor_y, screen_w, obstacles=None):
        if not self.alive:
            if self.die_timer > 0:
                self.die_timer -= 1
            return
        if self.stagger_timer > 0:
            self.stagger_timer -= 1
        else:
            dx = player_x - self.x
            dy = player_y - self.y
            dist = max(1, math.sqrt(dx * dx + dy * dy))
            self._phase_timer += 1
            # AI: giữ khoảng cách 200-350px, di chuyển ngang
            if dist < 200:
                # Lùi ra xa
                move_x = -(dx / dist) * self.speed
            elif dist > 350:
                # Tiến lại gần
                move_x = (dx / dist) * self.speed
            else:
                # Giữ khoảng cách, di chuyển ngang
                strafe = math.sin(self._phase_timer * 0.03) * self.speed * 1.5
                move_x = strafe
            # Tránh obstacle
            move_x, extra_y = self._avoid_obstacle(move_x, obstacles, screen_w)
            self.x += move_x
            if extra_y != 0:
                self.y += extra_y
            elif self.y != floor_y:
                self.y += (floor_y - self.y) * 0.1

        self.x += self.vx
        self.vx *= 0.85
        self.x = max(60, min(screen_w - 60, self.x))
        if self.hit_timer > 0:
            self.hit_timer -= 1
        self.anim_timer += 1
        if self.anim_timer > 14:
            self.anim_timer = 0
            self.frame = 1 - self.frame
        if self.attack_timer > 0:
            self.attack_timer -= 1
        # GIF animation
        if self._gif_frames:
            self._gif_timer += 1
            if self._gif_timer > 4:
                self._gif_timer = 0
                self._gif_idx = (self._gif_idx + 1) % len(self._gif_frames)

    def draw(self, surface):
        if self._gif_frames:
            sprite = self._gif_frames[self._gif_idx]
            w, h = sprite.get_size()
            if self.hit_timer > 0 and self.hit_timer % 3 < 2:
                sprite = sprite.copy()
                sprite.fill((255, 80, 80, 120), special_flags=pygame.BLEND_RGBA_MULT)
            if not self.alive and self.die_timer > 0:
                alpha = int(255 * self.die_timer / self.DIE_DURATION)
                sprite = sprite.copy()
                sprite.set_alpha(alpha)
                angle = (self.DIE_DURATION - self.die_timer) * 3
                sprite = pygame.transform.rotate(sprite, angle)
                rect = sprite.get_rect(center=(int(self.x), int(self.y) - h // 2))
                surface.blit(sprite, rect)
                return
            if not self.alive:
                return
            surface.blit(sprite, (int(self.x) - w // 2, int(self.y) - h))
            bar_w = w
            bar_h = 6
            bx = int(self.x) - bar_w // 2
            by = int(self.y) - h - 12
            pygame.draw.rect(surface, (80, 0, 0), (bx, by, bar_w, bar_h), border_radius=2)
            hp_frac = self.hp / self.max_hp
            pygame.draw.rect(surface, (
                int(255 * (1 - hp_frac)), int(255 * hp_frac), 30
            ), (bx, by, int(bar_w * hp_frac), bar_h), border_radius=2)
        else:
            super().draw(surface)


class EnemyManager:
    """Quản lý toàn bộ quái vật và wave spawn"""
    WAVE_CONFIGS = [
        # wave 1: 2 alien
        [('alien', 0.2, 0.6), ('alien', 0.8, 0.6)],
        # wave 2: 1 blob_alien + 1 alien
        [('blob_alien', 0.15, 0.85), ('alien', 0.85, 0.5)],
        # wave 3: 1 boss_alien + 1 monster + 1 alien + 1 ghost
        [('boss_alien', 0.5, 0.85), ('monster', 0.9, 0.85),
         ('alien', 0.2, 0.4), ('ghost', 0.7, 0.85)],
        # wave 4: 1 blob_alien + 1 monster + 1 alien + 1 ghost
        [('blob_alien', 0.1, 0.85), ('monster', 0.85, 0.85), ('alien', 0.5, 0.3),
         ('ghost', 0.7, 0.85)],
        # wave 5: 1 dragon + 1 blob_alien + 2 ghost
        [('dragon', 0.5, 0.3), ('blob_alien', 0.2, 0.85),
         ('ghost', 0.7, 0.85), ('ghost', 0.3, 0.85)],
        # wave 6: 3 fast_alien + 1 dragon + 1 monster
        [('fast_alien', 0.15, 0.4), ('fast_alien', 0.5, 0.5),
         ('fast_alien', 0.85, 0.35), ('dragon', 0.5, 0.25),
         ('monster', 0.7, 0.85)],
        # wave 7: 1 elite_hulk + 2 fast_alien + 1 dragon + 2 ghost
        [('elite_hulk', 0.5, 0.85), ('fast_alien', 0.2, 0.4),
         ('fast_alien', 0.8, 0.45), ('dragon', 0.3, 0.25),
         ('ghost', 0.1, 0.85), ('ghost', 0.9, 0.85)],
        # wave 8+: random tăng dần
    ]

    def __init__(self, screen_w, screen_h):
        self.screen_w = screen_w
        self.screen_h = screen_h
        self.floor_y = int(screen_h * 0.85)
        self.enemies = []
        self.alien_projectiles = []   # bao gồm cả AlienProjectile và FireBreath
        self.wave = 0
        self.wave_clear = False
        self.spawn_pending = False

    def spawn_wave(self):
        self.enemies.clear()
        self.alien_projectiles.clear()
        w, h = self.screen_w, self.screen_h

        if self.wave < len(self.WAVE_CONFIGS):
            config = self.WAVE_CONFIGS[self.wave]
        else:
            # Wave tăng dần, bao gồm tất cả loại quái
            n = self.wave - len(self.WAVE_CONFIGS) + 5
            config = []
            for _ in range(n):
                t = random.choice(['blob_alien', 'monster', 'alien', 'dragon',
                                   'ghost', 'fast_alien', 'elite_hulk',
                                   'boss_alien'])
                x = random.uniform(0.05, 0.95)
                FLYING = ('alien', 'dragon', 'fast_alien')
                y = 0.85 if t not in FLYING else random.uniform(0.3, 0.6)
                config.append((t, x, y))

        for (etype, rx, ry) in config:
            ex, ey = int(w * rx), int(h * ry)
            if etype == 'blob_alien':
                self.enemies.append(BlobAlienEnemy(ex, ey))
            elif etype == 'monster':
                self.enemies.append(MonsterEnemy(ex, ey))
            elif etype == 'alien':
                self.enemies.append(AlienEnemy(ex, ey))
            elif etype == 'dragon':
                self.enemies.append(DragonEnemy(ex, ey))
            elif etype == 'ghost':
                self.enemies.append(GhostEnemy(ex, ey))
            elif etype == 'fast_alien':
                self.enemies.append(FastAlienEnemy(ex, ey))
            elif etype == 'elite_hulk':
                self.enemies.append(EliteHulkEnemy(ex, ey))
            elif etype == 'boss_alien':
                self.enemies.append(BossAlienEnemy(ex, ey))

        self.wave += 1
        self.wave_clear = False

    def update(self, player_x, player_y, obstacles=None):
        alive = [e for e in self.enemies if e.alive]
        dead_animating = [e for e in self.enemies if not e.alive and e.die_timer > 0]
        self.wave_clear = len(alive) == 0 and len(dead_animating) == 0

        for e in self.enemies:
            e.update(player_x, player_y, self.floor_y, self.screen_w,
                     obstacles=obstacles)

        # Alien bắn đạn
        for e in self.enemies:
            if isinstance(e, AlienEnemy) and e.can_attack(player_x, player_y):
                dx = player_x - e.x
                dy = player_y - e.y
                dist = max(1, math.sqrt(dx * dx + dy * dy))
                speed = 5
                self.alien_projectiles.append(AlienProjectile(
                    e.x, e.y,
                    dx / dist * speed, dy / dist * speed
                ))
                e.perform_attack()

        # Dragon phun lửa
        for e in self.enemies:
            if isinstance(e, DragonEnemy) and e.can_attack(player_x, player_y):
                dx = player_x - e.x
                dy = player_y - e.y
                dist = max(1, math.sqrt(dx * dx + dy * dy))
                speed = 4
                self.alien_projectiles.append(FireBreath(
                    e.x, e.y,
                    dx / dist * speed, dy / dist * speed
                ))
                e.perform_attack()

        # FastAlien bắn 2 đạn (spread)
        for e in self.enemies:
            if isinstance(e, FastAlienEnemy) and e.can_attack(player_x, player_y):
                dx = player_x - e.x
                dy = player_y - e.y
                dist = max(1, math.sqrt(dx * dx + dy * dy))
                speed = 6
                # 2 đạn lệch 10 độ
                angle = math.atan2(dy, dx)
                for offset in (-0.17, 0.17):  # ~10 degrees
                    a = angle + offset
                    self.alien_projectiles.append(AlienProjectile(
                        e.x, e.y,
                        math.cos(a) * speed, math.sin(a) * speed
                    ))
                e.perform_attack()

        # BossAlien phun lửa GIF (3 tia lửa spread)
        for e in self.enemies:
            if isinstance(e, BossAlienEnemy) and e.can_attack(player_x, player_y):
                dx = player_x - e.x
                dy = player_y - e.y
                dist = max(1, math.sqrt(dx * dx + dy * dy))
                speed = 4.5
                angle = math.atan2(dy, dx)
                for offset in (-0.2, 0.0, 0.2):  # 3 tia lửa
                    a = angle + offset
                    self.alien_projectiles.append(GifFireBreath(
                        e.x, e.y,
                        math.cos(a) * speed, math.sin(a) * speed
                    ))
                e.perform_attack()

        for p in self.alien_projectiles:
            p.update(self.screen_w, self.screen_h)
        # Đạn bị tường chặn
        if obstacles:
            for p in self.alien_projectiles:
                if not p.alive:
                    continue
                pr = p.get_rect()
                for obs in obstacles:
                    if pr.colliderect(obs.get_rect()):
                        p.alive = False
                        break
        self.alien_projectiles = [p for p in self.alien_projectiles if p.alive]

        # Dọn enemy đã chết xong animation
        self.enemies = [e for e in self.enemies if e.alive or e.die_timer > 0]

    def check_player_hit(self, player_x, player_y, player_radius=30):
        """Kiểm tra player bị đánh, trả về damage"""
        total_dmg = 0
        pr = pygame.Rect(player_x - player_radius, player_y - player_radius,
                         player_radius * 2, player_radius * 2)
        # Đạn alien + lửa dragon
        for p in self.alien_projectiles:
            if p.alive and pr.colliderect(p.get_rect()):
                total_dmg += p.damage
                p.alive = False
        # Enemy cận chiến (chỉ melee, bo qua ranged enemies)
        _RANGED_TYPES = (AlienEnemy, DragonEnemy, FastAlienEnemy, BossAlienEnemy)
        for e in self.enemies:
            if not e.alive:
                continue
            if isinstance(e, _RANGED_TYPES):
                continue
            if e.can_attack(player_x, player_y):
                total_dmg += e.perform_attack()
        return total_dmg

    def draw(self, surface):
        for e in self.enemies:
            e.draw(surface)
        for p in self.alien_projectiles:
            p.draw(surface)

    def get_all_alive(self):
        return [e for e in self.enemies if e.alive]
