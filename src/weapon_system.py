"""
weapon_system.py - State machine vũ khí
Trạng thái: idle → equipped → attack → cooldown → equipped
"""

import pygame
import math
import random
import numpy as np
from src.effects import SummonEffect, ImpactEffect, ChargeEffect, TrailEffect, PunchImpact, MineExplosion


class Projectile:
    """Dan / ten bay"""
    def __init__(self, x, y, vx, vy, sprite, weapon_type, damage):
        self.x = float(x)
        self.y = float(y)
        self.vx = vx
        self.vy = vy
        self.sprite = sprite
        self.weapon_type = weapon_type
        self.damage = damage
        self.alive = True
        self.exploded = False   # danh dau da no (grenade)
        self.trail_points = []
        self.angle = math.degrees(math.atan2(-vy, vx))
        # Luu dan: fuse timer 120 frames (~2 giay @ 60fps)
        self.fuse_timer = 120 if weapon_type == 'grenade' else None
        # Grenade scale animation: bat dau nho (0.2) tang dan theo toc do
        self._scale = 0.2 if weapon_type == 'grenade' else 1.0
        self._base_size = 18  # kich thuoc goc cua sprite

    def update(self, screen_w, screen_h):
        self.x += self.vx
        self.y += self.vy
        # Kiem tra tam bay toi da cho ten (arrow)
        if self.weapon_type == 'arrow':
            max_r = getattr(self, '_max_range', 1000)
            sx    = getattr(self, '_start_x', self.x)
            sy    = getattr(self, '_start_y', self.y)
            if math.sqrt((self.x - sx)**2 + (self.y - sy)**2) > max_r:
                self.alive = False
        # Luu dan co trong luc va bounce nhe khi cham san
        if self.weapon_type == 'grenade':
            self.vy += 0.35
            # Bounce khi cham san (y > screen_h - 162 = FLOOR_Y uoc tinh)
            floor_approx = screen_h * 0.85
            if self.y >= floor_approx and abs(self.vy) > 1:
                self.vy = -abs(self.vy) * 0.45
                self.vx *= 0.85
                self.y = floor_approx
            self.angle = math.degrees(math.atan2(-self.vy, self.vx))
            # Fuse countdown
            if self.fuse_timer is not None:
                self.fuse_timer -= 1
                if self.fuse_timer <= 0 and not self.exploded:
                    self.exploded = True   # kich hoat no trong WeaponSystem.update
        self.trail_points.append((int(self.x), int(self.y)))
        if len(self.trail_points) > 12:
            self.trail_points.pop(0)
        # Out of bounds (chi cho dan thuong, grenade chi het khi fuse=0)
        if self.weapon_type != 'grenade':
            if self.x < -50 or self.x > screen_w + 50 or self.y < -50 or self.y > screen_h + 100:
                self.alive = False
        else:
            if self.x < -200 or self.x > screen_w + 200 or self.y > screen_h + 200:
                self.alive = False

    def draw(self, surface):
        if not self.alive:
            return
        # Trail
        if len(self.trail_points) > 1:
            trail_surf = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
            colors = {
                'arrow': (150, 220, 150, 120),
                'bullet': (255, 220, 50, 150),
                'grenade': (100, 200, 100, 80),
            }
            tc = colors.get(self.weapon_type, (200, 200, 200, 100))
            for i in range(len(self.trail_points) - 1):
                alpha = int(tc[3] * (i / len(self.trail_points)))
                pygame.draw.line(
                    trail_surf,
                    (*tc[:3], alpha),
                    self.trail_points[i],
                    self.trail_points[i + 1],
                    2
                )
            surface.blit(trail_surf, (0, 0))

        # Sprite xoay theo huong bay
        if self.weapon_type == 'grenade' and self._scale < 1.0:
            # Scale animation: tang dan theo toc do
            speed = math.sqrt(self.vx ** 2 + self.vy ** 2)
            # Toc do max khoang 13-15 px/frame => scale day = 1.0
            self._scale = min(1.0, speed / 12.0)
            # Clamp: khong de qua nho
            self._scale = max(0.15, self._scale)
            orig_w = self.sprite.get_width()
            orig_h = self.sprite.get_height()
            new_w = max(4, int(orig_w * self._scale))
            new_h = max(4, int(orig_h * self._scale))
            scaled_sprite = pygame.transform.scale(self.sprite, (new_w, new_h))
            rotated = pygame.transform.rotate(scaled_sprite, self.angle)
        else:
            rotated = pygame.transform.rotate(self.sprite, self.angle)
        rect = rotated.get_rect(center=(int(self.x), int(self.y)))
        surface.blit(rotated, rect)

    def get_rect(self):
        return pygame.Rect(self.x - 8, self.y - 8, 16, 16)


class Mine:
    """
    Min dat xuong san, no sau 180 frames (3 giay).
    AoE 200px, damage 150, co the pha obstacle.
    """
    FUSE_FRAMES = 180   # 3 giay @ 60fps
    AOE_RADIUS  = 200
    DAMAGE      = 150

    def __init__(self, x, y):
        self.x = float(x)
        self.y = float(y)
        self.fuse = self.FUSE_FRAMES
        self.alive = True
        self.exploded = False
        self._blink_t = 0

    def update(self):
        if not self.alive:
            return
        self.fuse -= 1
        self._blink_t += 1
        if self.fuse <= 0 and not self.exploded:
            self.exploded = True

    def draw(self, surface):
        if not self.alive:
            return
        import pygame, math
        cx, cy = int(self.x), int(self.y)
        # Ve hinh tron dep duoi san
        mine_surf = pygame.Surface((60, 30), pygame.SRCALPHA)
        pygame.draw.ellipse(mine_surf, (50, 50, 60), (5, 8, 50, 18))
        pygame.draw.ellipse(mine_surf, (80, 80, 90), (7, 10, 30, 12))
        pygame.draw.ellipse(mine_surf, (30, 30, 40), (5, 8, 50, 18), 2)
        # Gai (6 gai)
        for i in range(6):
            a = math.radians(i * 60)
            mx1 = int(30 + math.cos(a) * 22)
            my1 = int(17 + math.sin(a) * 8)
            mx2 = int(30 + math.cos(a) * 28)
            my2 = int(17 + math.sin(a) * 10)
            pygame.draw.line(mine_surf, (180, 40, 40), (mx1, my1), (mx2, my2), 2)
        surface.blit(mine_surf, (cx - 30, cy - 17))

        # Den nhap nhay (toc do tang khi gan no)
        blink_rate = max(4, int(20 * self.fuse / self.FUSE_FRAMES))
        if (self._blink_t // blink_rate) % 2 == 0:
            blink_surf = pygame.Surface((14, 14), pygame.SRCALPHA)
            pygame.draw.circle(blink_surf, (255, 60, 60, 220), (7, 7), 5)
            surface.blit(blink_surf, (cx - 7, cy - 7 - 8))

        # Dem nguoc: hien thi giay con lai
        try:
            f = pygame.font.SysFont('Arial', 14, bold=True)
            t_color = (255, 80, 80) if self.fuse < 60 else (255, 200, 80)
            secs = self.fuse / 60.0
            lbl = f.render(f'{secs:.1f}s', True, t_color)
            surface.blit(lbl, (cx - lbl.get_width()//2, cy - 35))
        except Exception:
            pass

        # Vong tron AoE preview (mo dan khi fuse ngan)
        if self.fuse < 90:
            aoe_alpha = int(60 * (1 - self.fuse / 90.0))
            aoe_surf = pygame.Surface((surface.get_width(), surface.get_height()), pygame.SRCALPHA)
            pygame.draw.circle(aoe_surf, (255, 80, 30, aoe_alpha),
                               (cx, cy), self.AOE_RADIUS, 2)
            surface.blit(aoe_surf, (0, 0))


class WeaponSystem:
    """
    Quản lý trạng thái vũ khí và thực hiện đòn đánh
    """
    WEAPON_COLORS = {
        'iron_gauntlets': (180, 180, 220),
        'sword':          (150, 200, 255),
        'bow':            (50, 220, 150),
        'grenade':        (200, 120, 50),
        'gun':            (160, 160, 200),
        None:             (100, 100, 100),
    }
    WEAPON_DAMAGE = {
        'iron_gauntlets': 25,
        'sword':          35,
        'bow':            30,
        'grenade':        80,
        'gun':            15,
    }
    WEAPON_RANGE = {
        'iron_gauntlets': 120,
        'sword':          150,
        'bow':            500,
        'grenade':        400,
        'gun':            600,
    }
    WEAPON_COOLDOWN = {
        'iron_gauntlets': 18,
        'sword':          25,
        'bow':            40,
        'grenade':        90,
        'gun':            8,
    }

    def __init__(self, player_pos, effect_manager, sound_manager, sprites):
        self.player_pos = player_pos
        self.em = effect_manager
        self.sm = sound_manager
        self.sprites = sprites
        self.explosion_frames = sprites.get('explosion_frames', None)

        self.current_weapon = None
        self.state = 'idle'   # idle / equipped / attack / cooldown
        self.cooldown_timer = 0
        self.summon_timer = 0
        self.SUMMON_DURATION = 20  # frames

        # Projectiles
        self.projectiles = []

        # Charge cung
        self.charge_effect = ChargeEffect(0, 0)
        self.bow_charged = False

        # Trail kiếm
        self.sword_trail = TrailEffect(color=(150, 200, 255))
        self.em.trails['sword'] = self.sword_trail

        # Trạng thái súng
        self.gun_fire_timer = 0
        self.GUN_FIRE_RATE = 8  # bắn mỗi 8 frame khi giữ

        # Luu dan: vi tri nem
        self.grenade_start_pos = None

        # Mines
        self.mines = []           # list[Mine]
        self._obstacle_ref = []   # tham chieu den game.obstacles de mine pha

        # Vu khi dang summon (de hien thi dong ho doi vu khi)
        self.pending_weapon = None

    def equip(self, weapon):
        """Trang bị vũ khí mới"""
        if weapon == self.current_weapon:
            return
        self.current_weapon = weapon
        self.state = 'summon'
        self.summon_timer = self.SUMMON_DURATION
        self.pending_weapon = weapon

        # VFX + SFX triệu hồi
        px, py = self.player_pos()
        self.em.add_effect(SummonEffect(px, py - 20, weapon))
        self.sm.play(f'summon_{weapon}')

        # Reset trail
        self.sword_trail.clear()

    def attack(self, attack_type, player_pos, enemies, bow_draw_level=0.0,
               bow_hand=None, string_hand=None, throw_angle=None,
               hands_screen=None, bow_direction=None, bow_force=0.0,
               mine_pos=None, punch_hand_pt=None):
        """Thuc hien don danh. hands_screen: list toa do tam tay tren man hinh."""
        if self.state == 'summon':
            return
        if self.cooldown_timer > 0:
            return

        px, py = player_pos
        w = self.current_weapon
        dmg = self.WEAPON_DAMAGE.get(w, 20)

        if w == 'iron_gauntlets':
            self._do_punch(attack_type, px, py, enemies, dmg,
                           hands_screen=hands_screen,
                           punch_hand_pt=punch_hand_pt)

        elif w == 'sword':
            self._do_slash(attack_type, px, py, enemies, dmg)

        elif w == 'bow':
            if attack_type == 'release_arrow':
                self._do_bow_release(px, py, bow_draw_level, enemies, dmg,
                                     bow_direction=bow_direction, bow_force=bow_force)

        elif w == 'grenade':
            if attack_type == 'throw_grenade':
                self._do_throw_grenade(px, py, enemies, dmg, throw_angle=throw_angle)

        elif w == 'gun':
            if attack_type == 'shoot':
                self._do_shoot(px, py, enemies, dmg)

        elif w == 'mine':
            if attack_type == 'place_mine':
                self._do_place_mine(px, py, mine_pos=mine_pos)

        self.cooldown_timer = self.WEAPON_COOLDOWN.get(w, 20)

    def _do_punch(self, side, px, py, enemies, dmg, hands_screen=None, punch_hand_pt=None):
        """Dam - AoE can chien. Vi tri danh = vi tri tay tren man hinh neu co."""
        rng = self.WEAPON_RANGE['iron_gauntlets']
        hit_any = False

        # Diem danh: neu co toa do tay tren man hinh thi dung, khong thi dung player pos
        if hands_screen and len(hands_screen) > 0:
            # Dam theo tung tay rieng biet
            punch_centers = hands_screen
        else:
            punch_centers = [(px, py)]

        for (hx, hy) in punch_centers:
            for e in enemies:
                if not e.alive:
                    continue
                d = math.dist((hx, hy), (e.x, e.y))
                if d < rng:
                    actual_dmg = dmg + random.randint(-5, 5)
                    e.take_damage(actual_dmg)
                    self.em.add_effect(ImpactEffect(e.x, e.y, 'iron_gauntlets'))
                    self.em.add_damage_number(e.x, e.y - 20, actual_dmg, (255, 150, 50))
                    ex_dir = e.x - hx
                    e.knockback(ex_dir * 0.3, -3)
                    hit_any = True

        if hit_any:
            self.sm.play('punch')
            self.sm.play('enemy_hit_punch')
        # Luon hien thi punch impact
        real_side = 'left' if side == 'punch_left' else 'right'
        # Dung toa do tay dam thuc su (punch_hand_pt) thay vi hands_screen[0]
        if punch_hand_pt:
            impact_x, impact_y = punch_hand_pt
        elif hands_screen:
            impact_x, impact_y = hands_screen[0]
        else:
            impact_x, impact_y = px, py - 40
        self.em.add_effect(PunchImpact(impact_x, impact_y, side=real_side))

    def _do_slash(self, attack_type, px, py, enemies, dmg):
        """Chém kiếm"""
        # Xác định vùng chém theo hướng
        slash_vectors = {
            'slash_right': (1, 0),
            'slash_left': (-1, 0),
            'slash_up': (0, -1),
            'slash_down': (0, 1),
        }
        if attack_type not in slash_vectors:
            attack_type = 'slash_right'
        dx, dy = slash_vectors[attack_type]
        rng = self.WEAPON_RANGE['sword']

        # Thêm điểm trail
        self.sword_trail.add_point(px + dx * rng, py + dy * rng)
        self.sm.play('sword_swing')

        for e in enemies:
            if not e.alive:
                continue
            ex, ey = e.x, e.y
            # Kiểm tra hướng chém
            d = math.dist((px, py), (ex, ey))
            if d < rng:
                dot = dx * (ex - px) + dy * (ey - py)
                if dot > -20:  # trong cung chém
                    actual_dmg = dmg + random.randint(-8, 8)
                    e.take_damage(actual_dmg)
                    self.em.add_effect(ImpactEffect(ex, ey, 'sword'))
                    self.em.add_damage_number(ex, ey - 20, actual_dmg, (180, 220, 255))
                    self.sm.play('sword_hit')
                    self.sm.play('enemy_hit_sword')

    def _do_bow_release(self, px, py, draw_level, enemies, dmg,
                        bow_direction=None, bow_force=0.0):
        """Ban ten theo huong tu tay phai -> tay trai, luc = khoang cach 2 tay"""
        # Toc do: luc keo cang xa = ten cang nhanh
        speed = 10 + max(draw_level, bow_force) * 10   # 10-20 pixels/frame

        if bow_direction is not None:
            # Huong ban tu gesture (tay phai -> tay trai)
            dx, dy = bow_direction
            vx = dx * speed
            vy = dy * speed
        else:
            # Fallback: ban ve phia enemy gan nhat
            target = self._nearest_enemy(px, py, enemies)
            if target:
                tx, ty = target.x, target.y
            else:
                tx, ty = px + 300, py
            ddx = tx - px
            ddy = ty - py
            dist = math.sqrt(ddx * ddx + ddy * ddy) or 1
            vx = ddx / dist * speed
            vy = ddy / dist * speed

        # Tam bay toi da: phu thuoc draw_level
        force = max(draw_level, bow_force)
        max_range = 400 + int(force * 600)  # 400-1000px

        proj = Projectile(
            px, py, vx, vy,
            self.sprites['arrow'], 'arrow',
            int(dmg * (0.5 + force * 0.5))
        )
        proj._max_range   = max_range
        proj._start_x     = px
        proj._start_y     = py
        self.projectiles.append(proj)
        self.sm.play('bow_release')

    def _do_throw_grenade(self, px, py, enemies, dmg, throw_angle=None):
        """Nem luu dan theo goc canh tay phai"""
        if throw_angle is not None:
            # Goc canh tay (radian) xac dinh huong va luc nem
            # Luc nem = do lon vector canh tay * he so, clamp [7, 16]
            # throw_angle: atan2(-vy_arm, vx_arm) => goc theo truc ngang
            base_speed = 16.0
            vx = math.cos(throw_angle) * base_speed
            vy = -math.sin(throw_angle) * base_speed  # y am = len
            # Gioi han: luon co thanh phan len (vy am)
            if vy > -3:
                vy = -3
        else:
            # Fallback: nem theo huong enemy gan nhat
            target = self._nearest_enemy(px, py, enemies)
            if target:
                tx, ty = target.x, target.y
            else:
                tx, ty = px + 200, py
            dx = tx - px
            dy = ty - py
            dist = max(1, math.sqrt(dx * dx + dy * dy))
            throw_speed = min(16, dist / 15)
            vx = dx / dist * throw_speed
            vy = -8

        proj = Projectile(
            px, py - 20, vx, vy,
            self.sprites['grenade'], 'grenade',
            dmg
        )
        self.projectiles.append(proj)
        self.sm.play('grenade_throw')

    def _do_shoot(self, px, py, enemies, dmg):
        """Bắn súng - đạn thẳng"""
        if self.gun_fire_timer > 0:
            return
        self.gun_fire_timer = self.GUN_FIRE_RATE

        target = self._nearest_enemy(px, py, enemies)
        if target:
            tx, ty = target.x, target.y
        else:
            tx, ty = px + 400, py

        dx = tx - px
        dy = ty - py
        dist = max(1, math.sqrt(dx * dx + dy * dy))
        speed = 18
        vx = dx / dist * speed
        vy = dy / dist * speed

        proj = Projectile(
            px, py, vx, vy,
            self.sprites['bullet'], 'bullet',
            dmg
        )
        self.projectiles.append(proj)
        self.sm.play('gunshot')

    def _do_place_mine(self, px, py, mine_pos=None):
        """Dat min tai vi tri trong tam 2 ban tay (hoac player pos neu khong co)"""
        if mine_pos is not None:
            mx, my = mine_pos
        else:
            mx, my = px, py
        new_mine = Mine(mx, my)
        self.mines.append(new_mine)
        self.sm.play('grenade_throw')

    def _do_mine_explode(self, mine, enemies):
        """No min: AoE 200px, damage 150, pha obstacle"""
        cx, cy = mine.x, mine.y
        for e in enemies:
            if not e.alive:
                continue
            if math.dist((cx, cy), (e.x, e.y)) < Mine.AOE_RADIUS:
                e.take_damage(Mine.DAMAGE)
                kx = (e.x - cx) * 0.5
                e.knockback(kx, -8)
        # Pha obstacle trong pham vi
        self._obstacle_ref[:] = [
            obs for obs in self._obstacle_ref
            if math.dist((cx, cy), (obs.x, obs.y)) >= Mine.AOE_RADIUS
        ]
        self.em.add_effect(MineExplosion(int(cx), int(cy), self.explosion_frames))
        self.em.add_damage_number(int(cx), int(cy) - 20, Mine.DAMAGE, (255, 80, 30))
        self.sm.play('mine_explosion')
        self.sm.play('enemy_hit_mine')
        mine.alive = False

    def _do_grenade_explode(self, p, enemies):
        """No luu dan: AoE 160px, knockback, VFX"""
        BLAST_R = 160
        for ee in enemies:
            if not ee.alive:
                continue
            if math.dist((p.x, p.y), (ee.x, ee.y)) < BLAST_R:
                ee.take_damage(p.damage)
                kx = (ee.x - p.x) * 0.5
                ee.knockback(kx, -6)
        self.em.add_effect(ImpactEffect(int(p.x), int(p.y), 'grenade'))
        self.em.add_damage_number(int(p.x), int(p.y) - 20, p.damage, (255, 120, 30))
        self.sm.play('explosion')
        self.sm.play('enemy_hit_grenade')

    def _nearest_enemy(self, px, py, enemies):
        alive = [e for e in enemies if e.alive]
        if not alive:
            return None
        return min(alive, key=lambda e: math.dist((px, py), (e.x, e.y)))

    def update(self, enemies, screen_w, screen_h, bow_draw_level=0.0,
               bow_hand=None, string_hand=None, player_pos=None, gun_firing=False):
        # Đếm cooldown
        if self.cooldown_timer > 0:
            self.cooldown_timer -= 1
        if self.gun_fire_timer > 0:
            self.gun_fire_timer -= 1

        # Summon animation
        if self.state == 'summon':
            self.summon_timer -= 1
            if self.summon_timer <= 0:
                self.state = 'equipped'
                self.pending_weapon = None

        # Súng tự động bắn
        if self.current_weapon == 'gun' and gun_firing and player_pos:
            if self.gun_fire_timer == 0:
                self._do_shoot(player_pos[0], player_pos[1], enemies, self.WEAPON_DAMAGE['gun'])

        # Charge cung
        if self.current_weapon == 'bow' and bow_hand:
            self.charge_effect.update(bow_hand[0], bow_hand[1], bow_draw_level)

        # Cập nhật projectile
        for p in self.projectiles:
            p.update(screen_w, screen_h)

        # Va cham projectile - tuong (chan dan, ten, luu dan)
        for p in self.projectiles:
            if not p.alive:
                continue
            p_rect = p.get_rect()
            for obs in self._obstacle_ref:
                if p_rect.colliderect(obs.get_rect()):
                    if p.weapon_type == 'grenade':
                        # Luu dan cham tuong => no ngay
                        p.fuse_timer = 0
                        p.exploded = True
                    else:
                        # Ten / dan bi chan
                        self.em.add_effect(ImpactEffect(int(p.x), int(p.y), p.weapon_type))
                        p.alive = False
                    break

        # Kiem tra grenade fuse no (sau 2 giay, khong can cham enemy)
        for p in self.projectiles:
            if not p.alive:
                continue
            if p.weapon_type == 'grenade' and p.exploded:
                self._do_grenade_explode(p, enemies)
                p.alive = False

        # Kiem tra va cham projectile - enemy
        for p in self.projectiles:
            if not p.alive:
                continue
            for e in enemies:
                if not e.alive:
                    continue
                if p.get_rect().colliderect(e.get_rect()):
                    if p.weapon_type == 'grenade':
                        # Cham enemy => giam them thoi gian no (no som)
                        p.fuse_timer = 0
                        p.exploded = True
                    else:
                        e.take_damage(p.damage)
                        self.em.add_effect(ImpactEffect(int(p.x), int(p.y), p.weapon_type))
                        self.em.add_damage_number(e.x, e.y - 20, p.damage)
                        if p.weapon_type == 'arrow':
                            self.sm.play('arrow_hit')
                            self.sm.play('enemy_hit_bow')
                        else:
                            self.sm.play('gun_hit')
                            self.sm.play('enemy_hit_gun')
                        p.alive = False
                    break

        self.projectiles = [p for p in self.projectiles if p.alive]

        # Cap nhat mines
        for mine in self.mines:
            mine.update()
        # No mine va don dep
        for mine in self.mines:
            if mine.exploded and mine.alive:
                self._do_mine_explode(mine, enemies)
        self.mines = [m for m in self.mines if m.alive]

        # Sword trail tu fade
        # (TrailEffect tu xu ly qua timestamp)

    def draw(self, surface):
        # Ve mines
        for mine in self.mines:
            mine.draw(surface)
        # Ve projectile
        for p in self.projectiles:
            p.draw(surface)
        # Ve charge cung
        if self.current_weapon == 'bow':
            self.charge_effect.draw(surface)
        # Trail kiem
        self.sword_trail.draw(surface)

    def get_summon_progress(self):
        if self.state == 'summon':
            return 1.0 - self.summon_timer / self.SUMMON_DURATION
        return 1.0 if self.state == 'equipped' else 0.0



