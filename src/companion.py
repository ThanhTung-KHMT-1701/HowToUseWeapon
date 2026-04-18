"""
companion.py - Companion bot HelpMe
Duoc goi bang lenh 'HelpMe' qua SPACE console.
Su dung sung, tu dong di chuyen den enemy gan nhat va ban.
"""

import pygame
import math
import random


class Obstacle:
    """
    Chuong ngai vat dang buc tuong pixel art.
    Nguoi choi va enemy bi chan lai khi cham.
    """
    WIDTH  = 80
    HEIGHT = 140

    # Palette pixel art (vat lieu da/kim loai khoa hoc vien tuong)
    _COLORS = [
        (60,  80, 110),   # xanh dam
        (80, 100, 130),   # xanh nhat
        (50,  60,  90),   # vien ngoai
        (100, 120, 150),  # soc sang
        (40,  50,  80),   # bong toi
    ]

    def __init__(self, x, y):
        """x, y: toa do goc trai duoi (dat len san)"""
        self.x = x
        self.y = y  # day duoi cua buc tuong
        self._surf = self._build_surface()

    def _build_surface(self):
        surf = pygame.Surface((self.WIDTH, self.HEIGHT), pygame.SRCALPHA)
        c0, c1, c2, c3, c4 = self._COLORS

        # Nen chinh
        pygame.draw.rect(surf, (*c0, 230), (0, 0, self.WIDTH, self.HEIGHT))

        # Khoi gach ngang (moi 28px)
        for row in range(0, self.HEIGHT, 28):
            offset = 20 if (row // 28) % 2 == 0 else 0
            for col in range(-20, self.WIDTH + 20, 40):
                bx = col + offset
                pygame.draw.rect(surf, (*c1, 180),
                                 (bx + 2, row + 2, 36, 24))
                # Vien sac
                pygame.draw.rect(surf, (*c2, 200),
                                 (bx + 1, row + 1, 38, 26), 1)

        # Soc sang ben trai
        pygame.draw.rect(surf, (*c3, 120), (2, 2, 8, self.HEIGHT - 4))
        # Vien ngoai
        pygame.draw.rect(surf, (*c2, 255), (0, 0, self.WIDTH, self.HEIGHT), 2)
        # Bong toi ben phai + duoi
        pygame.draw.rect(surf, (*c4, 180),
                         (self.WIDTH - 6, 4, 6, self.HEIGHT - 4))
        pygame.draw.rect(surf, (*c4, 180),
                         (4, self.HEIGHT - 6, self.WIDTH - 8, 6))
        return surf

    def get_rect(self):
        return pygame.Rect(self.x, self.y - self.HEIGHT,
                           self.WIDTH, self.HEIGHT)

    def draw(self, surface):
        surface.blit(self._surf, (self.x, self.y - self.HEIGHT))

    def collide_point(self, x, y, margin=10):
        r = self.get_rect().inflate(margin, margin)
        return r.collidepoint(x, y)

    def push_out(self, entity_x, entity_y, entity_w=40):
        """
        Day entity ra ngoai chuong ngai vat.
        Tra ve (new_x, new_y) da dieu chinh.
        """
        r = self.get_rect()
        half = entity_w // 2
        ex1 = entity_x - half
        ex2 = entity_x + half

        # Kiem tra chong leng
        if not (ex1 < r.right and ex2 > r.left and
                entity_y > r.top and entity_y < r.bottom + 30):
            return entity_x, entity_y

        # Day sang trai hoac phai
        push_left  = r.right - ex1
        push_right = ex2 - r.left
        if push_left < push_right:
            return entity_x - push_left - 2, entity_y
        else:
            return entity_x + push_right + 2, entity_y


class Companion:
    """
    Companion bot HelpMe - AI co ban.
    Tu dong tim enemy gan nhat, di chuyen den va ban.
    """
    HP_MAX    = 150
    SPEED     = 3
    FIRE_RATE = 20      # frames giua 2 lan ban
    FIRE_RANGE = 450    # px, khoang cach toi da de ban
    WIDTH     = 40
    HEIGHT    = 60

    # Mau bo ngoai
    _BODY_COL  = (60, 200, 120)
    _SHINE_COL = (100, 255, 160)
    _EDGE_COL  = (30, 120, 80)
    _EYE_COL   = (50, 230, 255)
    _GUN_COL   = (180, 180, 200)

    def __init__(self, x, y, projectile_sprites, effect_manager, sound_manager):
        self.x = float(x)
        self.y = float(y)
        self.hp = self.HP_MAX
        self.alive = True
        self._sprites = projectile_sprites
        self._em      = effect_manager
        self._sm      = sound_manager
        self._fire_cd = 0
        self._face_dir = 1   # 1 = phai, -1 = trai
        self._anim_t   = 0
        self._projectiles = []   # dan ban ra
        self._hurt_flash  = 0

        # Tao surface body
        self._surf = self._build_surface()

    def _build_surface(self):
        surf = pygame.Surface((self.WIDTH + 20, self.HEIGHT + 10), pygame.SRCALPHA)
        w, h = self.WIDTH, self.HEIGHT
        ox, oy = 10, 0

        # Than robot hinh chu nhat co goc tron
        pygame.draw.rect(surf, (*self._BODY_COL, 220),
                         (ox, oy + h // 4, w, h * 3 // 4), border_radius=8)
        # Dau
        pygame.draw.ellipse(surf, (*self._BODY_COL, 230),
                            (ox + 6, oy, w - 12, h // 2))
        # Soc sang
        pygame.draw.rect(surf, (*self._SHINE_COL, 130),
                         (ox + 4, oy + h // 4 + 4, 8, h // 2))
        # Mat phat sang
        pygame.draw.circle(surf, (*self._EYE_COL, 255),
                           (ox + w // 2 - 6, oy + h // 3), 5)
        pygame.draw.circle(surf, (*self._EYE_COL, 255),
                           (ox + w // 2 + 6, oy + h // 3), 5)
        # Vien ngoai
        pygame.draw.rect(surf, (*self._EDGE_COL, 255),
                         (ox, oy + h // 4, w, h * 3 // 4), width=2, border_radius=8)
        pygame.draw.ellipse(surf, (*self._EDGE_COL, 255),
                            (ox + 6, oy, w - 12, h // 2), 2)
        # Sung
        pygame.draw.rect(surf, (*self._GUN_COL, 220),
                         (ox + w - 2, oy + h // 2 - 5, 18, 8), border_radius=3)
        return surf

    def get_rect(self):
        return pygame.Rect(self.x - self.WIDTH // 2,
                           self.y - self.HEIGHT,
                           self.WIDTH, self.HEIGHT)

    def take_damage(self, dmg):
        self.hp = max(0, self.hp - dmg)
        self._hurt_flash = 8
        if self.hp <= 0:
            self.alive = False

    def update(self, enemies, obstacles, screen_w, screen_h,
               player_x=None, player_y=None, projectiles=None):
        if not self.alive:
            return

        self._anim_t += 1
        if self._fire_cd > 0:
            self._fire_cd -= 1
        if self._hurt_flash > 0:
            self._hurt_flash -= 1

        # --- Né đạn (alien projectile / fire breath) ---
        dodge_vx, dodge_vy = 0.0, 0.0
        if projectiles:
            for p in projectiles:
                alive = p.alive if hasattr(p, 'alive') else p.get('alive', True)
                if not alive:
                    continue
                px = p.x if hasattr(p, 'x') else p.get('x', 0)
                py = p.y if hasattr(p, 'y') else p.get('y', 0)
                dx = self.x - px
                dy = self.y - py
                d = max(1, math.sqrt(dx*dx + dy*dy))
                if d < 120:
                    # Lực đẩy tỉ lệ nghịch khoảng cách
                    strength = (120 - d) / 120 * 5
                    dodge_vx += (dx / d) * strength
                    dodge_vy += (dy / d) * strength

        # Tim enemy gan nhat
        alive_enemies = [e for e in enemies if e.alive]
        target = None
        min_d  = float('inf')
        for e in alive_enemies:
            d = math.dist((self.x, self.y), (e.x, e.y))
            if d < min_d:
                min_d = d
                target = e

        if target:
            dx = target.x - self.x
            dy = target.y - self.y
            dist = max(1, math.sqrt(dx*dx + dy*dy))
            self._face_dir = 1 if dx > 0 else -1

            # Di chuyen den enemy neu con xa hon 200px
            if dist > 200:
                self.x += (dx / dist) * self.SPEED
                self.y += (dy / dist) * self.SPEED
        else:
            # Khong co enemy, nhay nhe
            bob = math.sin(self._anim_t * 0.08) * 2
            self.y += bob * 0.1

        # --- Bám theo player (không đi quá xa 300px) ---
        if player_x is not None and player_y is not None:
            dx_p = self.x - player_x
            dy_p = self.y - player_y
            dist_p = math.sqrt(dx_p*dx_p + dy_p*dy_p)
            if dist_p > 300:
                self.x -= (dx_p / dist_p) * self.SPEED * 1.5
                self.y -= (dy_p / dist_p) * self.SPEED * 1.5

        # Áp dụng lực né đạn
        self.x += dodge_vx
        self.y += dodge_vy

        # Giu trong man hinh
        self.x = max(30, min(screen_w - 30, self.x))
        self.y = max(200, min(screen_h * 0.85, self.y))

        # Tranh chuong ngai vat
        if obstacles:
            for obs in obstacles:
                self.x, self.y = obs.push_out(self.x, self.y, self.WIDTH)

        # Ban khi trong tam
        if target:
            dx = target.x - self.x
            dy = target.y - self.y
            dist = max(1, math.sqrt(dx*dx + dy*dy))
            if dist < self.FIRE_RANGE and self._fire_cd == 0:
                self._shoot(target, screen_w, screen_h)

        # Cap nhat dan ban
        for p in self._projectiles:
            p['x'] += p['vx']
            p['y'] += p['vy']
            p['ttl'] -= 1
            if p['ttl'] <= 0:
                p['alive'] = False
            # Kiem tra enemy
            for e in alive_enemies:
                if (abs(p['x'] - e.x) < 20 and abs(p['y'] - e.y) < 30
                        and e.alive):
                    e.take_damage(p['dmg'])
                    p['alive'] = False
                    self._sm.play('gun_hit')
                    self._sm.play('enemy_hit')
                    try:
                        from src.effects import ImpactEffect
                        self._em.add_effect(
                            ImpactEffect(int(p['x']), int(p['y']), 'gun'))
                        self._em.add_damage_number(
                            int(e.x), int(e.y) - 20, p['dmg'],
                            (100, 255, 160))
                    except Exception:
                        pass
                    break
        self._projectiles = [p for p in self._projectiles if p.get('alive', True)]

    def _shoot(self, target, screen_w, screen_h):
        dx = target.x - self.x
        dy = target.y - self.y
        dist = max(1, math.sqrt(dx*dx + dy*dy))
        speed = 16
        self._projectiles.append({
            'x': self.x, 'y': self.y - self.HEIGHT // 2,
            'vx': dx / dist * speed,
            'vy': dy / dist * speed,
            'dmg': 12,
            'ttl': 60,
            'alive': True,
        })
        self._fire_cd = self.FIRE_RATE
        self._sm.play('gunshot')

    def draw(self, surface):
        if not self.alive:
            return

        bob_y = int(math.sin(self._anim_t * 0.08) * 3)
        draw_x = int(self.x) - self.WIDTH // 2 - 10
        draw_y = int(self.y) - self.HEIGHT + bob_y

        # Hurt flash: do len
        if self._hurt_flash > 0:
            flash_surf = self._surf.copy()
            flash_surf.fill((255, 80, 80, 120), special_flags=pygame.BLEND_RGBA_ADD)
            surface.blit(flash_surf, (draw_x, draw_y))
        else:
            surface.blit(self._surf, (draw_x, draw_y))

        # Thanh HP nho ben tren
        hp_w = 40
        hp_x = int(self.x) - hp_w // 2
        hp_y = int(self.y) - self.HEIGHT - 12 + bob_y
        pygame.draw.rect(surface, (60, 60, 60),
                         (hp_x, hp_y, hp_w, 5), border_radius=2)
        fill = int(hp_w * self.hp / self.HP_MAX)
        if fill > 0:
            pygame.draw.rect(surface, (60, 220, 100),
                             (hp_x, hp_y, fill, 5), border_radius=2)

        # Label
        try:
            f = pygame.font.SysFont('Arial', 12, bold=True)
            lbl = f.render('HelpMe', True, (100, 255, 160))
            surface.blit(lbl, (int(self.x) - lbl.get_width() // 2,
                               hp_y - 14))
        except Exception:
            pass

        # Ve dan ban
        for p in self._projectiles:
            pygame.draw.circle(surface, (100, 255, 160),
                               (int(p['x']), int(p['y'])), 4)
            pygame.draw.circle(surface, (200, 255, 220),
                               (int(p['x']), int(p['y'])), 2)


class SpaceConsole:
    """
    Console overlay mo/dong bang SPACE.
    Nhan 'HelpMe' + Enter => spawn companion.
    """
    WIDTH  = 500
    HEIGHT = 120

    def __init__(self, screen_w, screen_h):
        self.screen_w = screen_w
        self.screen_h = screen_h
        self.open    = False
        self.text    = ''
        self.history = []   # lich su lenh
        self._font   = None
        self._blink  = 0
        self._result_msg   = ''
        self._result_timer = 0

    def _get_font(self):
        if self._font is None:
            try:
                self._font = pygame.font.SysFont('Courier New', 20, bold=True)
            except Exception:
                self._font = pygame.font.SysFont(None, 20)
        return self._font

    def toggle(self):
        self.open = not self.open
        if self.open:
            self.text = ''

    def handle_event(self, event):
        """
        Xu ly phim ban phim khi console mo.
        Tra ve lenh duoc submit (str) hoac None.
        """
        if not self.open:
            return None
        if event.type != pygame.KEYDOWN:
            return None

        if event.key == pygame.K_RETURN or event.key == pygame.K_KP_ENTER:
            cmd = self.text.strip()
            self.history.append(cmd)
            self.text = ''
            self.open = False
            return cmd

        elif event.key == pygame.K_BACKSPACE:
            self.text = self.text[:-1]

        elif event.key == pygame.K_ESCAPE:
            self.open = False

        elif event.unicode and event.unicode.isprintable():
            if len(self.text) < 40:
                self.text += event.unicode

        return None

    def show_result(self, msg):
        self._result_msg   = msg
        self._result_timer = 180  # 3 giay @ 60fps

    def update(self):
        self._blink += 1
        if self._result_timer > 0:
            self._result_timer -= 1

    def draw(self, surface):
        self.update()

        # Ve ket qua popup neu co
        if self._result_timer > 0 and self._result_msg:
            f   = self._get_font()
            lbl = f.render(self._result_msg, True, (100, 255, 160))
            alpha = min(255, self._result_timer * 3)
            lbl.set_alpha(alpha)
            cx = self.screen_w // 2 - lbl.get_width() // 2
            cy = self.screen_h // 2 - 150
            bg = pygame.Surface((lbl.get_width() + 20, lbl.get_height() + 10),
                                pygame.SRCALPHA)
            bg.fill((0, 0, 0, 160))
            surface.blit(bg, (cx - 10, cy - 5))
            surface.blit(lbl, (cx, cy))

        if not self.open:
            return

        # Nen console
        cx = self.screen_w // 2 - self.WIDTH // 2
        cy = self.screen_h // 2 - self.HEIGHT // 2

        bg = pygame.Surface((self.WIDTH, self.HEIGHT), pygame.SRCALPHA)
        bg.fill((10, 10, 30, 220))
        pygame.draw.rect(bg, (60, 200, 120, 255),
                         (0, 0, self.WIDTH, self.HEIGHT), 2, border_radius=8)
        surface.blit(bg, (cx, cy))

        f = self._get_font()
        # Tieu de
        title = f.render('> SPACE CONSOLE', True, (60, 200, 120))
        surface.blit(title, (cx + 10, cy + 8))

        # Goi y
        hint = f.render('Type: HelpMe | Auto  then  Enter', True, (100, 150, 120))
        try:
            hint_small = pygame.font.SysFont('Courier New', 14).render(
                'Type: HelpMe | Auto  then  Enter', True, (80, 130, 100))
            surface.blit(hint_small, (cx + 10, cy + 30))
        except Exception:
            pass

        # Input text + cursor
        cursor = '|' if (self._blink // 20) % 2 == 0 else ' '
        display_text = '> ' + self.text + cursor
        inp = f.render(display_text, True, (200, 255, 200))
        surface.blit(inp, (cx + 10, cy + 55))

        # Huong dan phim
        try:
            small_f = pygame.font.SysFont('Arial', 13)
            esc_lbl = small_f.render('ESC to close  |  Enter to submit',
                                     True, (100, 120, 100))
            surface.blit(esc_lbl, (cx + 10, cy + self.HEIGHT - 20))
        except Exception:
            pass
