"""
effects.py - VFX: particles, trails, flash, impact, summon effects
"""

import pygame
import math
import random
from src.sprites import get_gif_frames


class Particle:
    def __init__(self, x, y, vx, vy, color, lifetime, size=3, gravity=0.0, fade=True):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.color = list(color)
        self.lifetime = lifetime
        self.max_lifetime = lifetime
        self.size = size
        self.gravity = gravity
        self.fade = fade
        self.alive = True

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vy += self.gravity
        self.vx *= 0.92
        self.lifetime -= 1
        if self.lifetime <= 0:
            self.alive = False

    def draw(self, surface):
        if not self.alive:
            return
        alpha = int(255 * (self.lifetime / self.max_lifetime)) if self.fade else 255
        size = max(1, int(self.size * (self.lifetime / self.max_lifetime)))
        color = (
            min(255, self.color[0]),
            min(255, self.color[1]),
            min(255, self.color[2]),
            alpha
        )
        s = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
        pygame.draw.circle(s, color, (size, size), size)
        surface.blit(s, (int(self.x) - size, int(self.y) - size))


class TrailEffect:
    """Vệt trail cho kiếm chém"""
    def __init__(self, color=(200, 220, 255), max_points=12):
        self.points = []
        self.color = color
        self.max_points = max_points

    def add_point(self, x, y):
        self.points.append((x, y, pygame.time.get_ticks()))
        if len(self.points) > self.max_points:
            self.points.pop(0)

    def draw(self, surface):
        if len(self.points) < 2:
            return
        now = pygame.time.get_ticks()
        for i in range(len(self.points) - 1):
            x1, y1, t1 = self.points[i]
            x2, y2, t2 = self.points[i + 1]
            age = now - t1
            alpha = max(0, 255 - age * 8)
            width = max(1, 4 - i // 3)
            if alpha > 0:
                color = (*self.color[:3], alpha)
                s = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
                pygame.draw.line(s, color, (int(x1), int(y1)), (int(x2), int(y2)), width)
                surface.blit(s, (0, 0))

    def clear(self):
        self.points.clear()


class FlashEffect:
    """Flash sáng khi kích hoạt vũ khí"""
    def __init__(self, x, y, color, radius=60, duration=15):
        self.x = x
        self.y = y
        self.color = color
        self.radius = radius
        self.duration = duration
        self.timer = duration
        self.alive = True

    def update(self):
        self.timer -= 1
        if self.timer <= 0:
            self.alive = False

    def draw(self, surface):
        if not self.alive:
            return
        t = self.timer / self.duration
        r = int(self.radius * (1 - t * 0.5))
        alpha = int(200 * t)
        s = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
        pygame.draw.circle(s, (*self.color[:3], alpha), (r, r), r)
        surface.blit(s, (self.x - r, self.y - r))


class SummonRing:
    """Vòng tròn triệu hồi vũ khí"""
    def __init__(self, x, y, color, duration=30, max_radius=80):
        self.x = x
        self.y = y
        self.color = color
        self.duration = duration
        self.timer = duration
        self.max_radius = max_radius
        self.alive = True

    def update(self):
        self.timer -= 1
        if self.timer <= 0:
            self.alive = False

    def draw(self, surface):
        if not self.alive:
            return
        t = 1 - self.timer / self.duration
        r = int(self.max_radius * t)
        alpha = int(255 * (1 - t))
        width = max(1, int(5 * (1 - t)))
        if r > 0:
            s = pygame.Surface((r * 2 + 10, r * 2 + 10), pygame.SRCALPHA)
            pygame.draw.circle(s, (*self.color[:3], alpha), (r + 5, r + 5), r, width)
            surface.blit(s, (self.x - r - 5, self.y - r - 5))


class ImpactEffect:
    """Va chạm khi đánh trúng"""
    def __init__(self, x, y, weapon_type='punch'):
        self.x = x
        self.y = y
        self.weapon_type = weapon_type
        self.particles = []
        self.timer = 0
        self.alive = True
        self._spawn_particles()

    def _spawn_particles(self):
        if self.weapon_type == 'iron_gauntlets':
            # tia lửa kim loại cam-vàng
            for _ in range(20):
                angle = random.uniform(0, math.pi * 2)
                speed = random.uniform(2, 8)
                self.particles.append(Particle(
                    self.x, self.y,
                    math.cos(angle) * speed, math.sin(angle) * speed,
                    (255, random.randint(100, 200), 20),
                    random.randint(10, 20), size=random.randint(2, 5),
                    gravity=0.3
                ))
            # shockwave
            self.flash = FlashEffect(self.x, self.y, (255, 180, 80), radius=50, duration=8)

        elif self.weapon_type == 'sword':
            # tia sáng bạc
            for _ in range(15):
                angle = random.uniform(-math.pi / 3, math.pi / 3)
                speed = random.uniform(3, 10)
                self.particles.append(Particle(
                    self.x, self.y,
                    math.cos(angle) * speed, math.sin(angle) * speed,
                    (random.randint(180, 255), random.randint(200, 255), 255),
                    random.randint(8, 18), size=random.randint(1, 4)
                ))
            self.flash = FlashEffect(self.x, self.y, (200, 230, 255), radius=40, duration=6)

        elif self.weapon_type == 'bow':
            # vòng năng lượng xanh ngọc
            for _ in range(12):
                angle = random.uniform(0, math.pi * 2)
                speed = random.uniform(1, 5)
                self.particles.append(Particle(
                    self.x, self.y,
                    math.cos(angle) * speed, math.sin(angle) * speed,
                    (50, random.randint(200, 255), random.randint(180, 220)),
                    random.randint(10, 20), size=random.randint(2, 4)
                ))
            self.flash = FlashEffect(self.x, self.y, (50, 255, 200), radius=35, duration=8)

        elif self.weapon_type == 'grenade':
            # vụ nổ lớn
            for _ in range(40):
                angle = random.uniform(0, math.pi * 2)
                speed = random.uniform(2, 12)
                color = random.choice([
                    (255, 100, 20), (255, 200, 50), (200, 50, 10), (255, 255, 150)
                ])
                self.particles.append(Particle(
                    self.x, self.y,
                    math.cos(angle) * speed, math.sin(angle) * speed,
                    color, random.randint(20, 35), size=random.randint(3, 8),
                    gravity=0.4
                ))
            self.flash = FlashEffect(self.x, self.y, (255, 150, 30), radius=90, duration=15)

        elif self.weapon_type == 'gun':
            for _ in range(8):
                angle = random.uniform(-0.3, 0.3)
                speed = random.uniform(4, 10)
                self.particles.append(Particle(
                    self.x, self.y,
                    math.cos(angle) * speed, math.sin(angle) * speed,
                    (255, 220, 100), random.randint(6, 14), size=random.randint(1, 3)
                ))
            self.flash = FlashEffect(self.x, self.y, (255, 230, 150), radius=25, duration=5)

        else:
            self.flash = None

    def update(self):
        self.timer += 1
        for p in self.particles:
            p.update()
        self.particles = [p for p in self.particles if p.alive]
        if self.flash:
            self.flash.update()
        if not self.particles and (not self.flash or not self.flash.alive):
            self.alive = False

    def draw(self, surface):
        if self.flash:
            self.flash.draw(surface)
        for p in self.particles:
            p.draw(surface)


class SummonEffect:
    """Hiệu ứng triệu hồi vũ khí - chạy 1 lần"""
    COLORS = {
        'iron_gauntlets': (180, 180, 220),
        'sword': (150, 200, 255),
        'bow': (50, 220, 150),
        'grenade': (200, 120, 50),
        'gun': (150, 150, 180),
        'mine': (200, 60, 60),
    }

    def __init__(self, x, y, weapon_type):
        self.x = x
        self.y = y
        self.weapon_type = weapon_type
        self.color = self.COLORS.get(weapon_type, (200, 200, 200))
        self.rings = [SummonRing(x, y, self.color, duration=25, max_radius=70 + i * 20) for i in range(2)]
        self.flash = FlashEffect(x, y, self.color, radius=80, duration=20)
        self.particles = []
        self.alive = True
        # burst particles
        for _ in range(25):
            angle = random.uniform(0, math.pi * 2)
            speed = random.uniform(2, 6)
            self.particles.append(Particle(
                x, y,
                math.cos(angle) * speed, math.sin(angle) * speed,
                self.color, random.randint(20, 35), size=random.randint(2, 5)
            ))

    def update(self):
        for r in self.rings:
            r.update()
        self.flash.update()
        for p in self.particles:
            p.update()
        self.particles = [p for p in self.particles if p.alive]
        self.rings = [r for r in self.rings if r.alive]
        if not self.rings and not self.flash.alive and not self.particles:
            self.alive = False

    def draw(self, surface):
        for r in self.rings:
            r.draw(surface)
        self.flash.draw(surface)
        for p in self.particles:
            p.draw(surface)


class ChargeEffect:
    """Hiệu ứng charge cung - liên tục khi đang kéo"""
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.particles = []
        self.level = 0.0
        self.timer = 0

    def update(self, x, y, level):
        self.x = x
        self.y = y
        self.level = level
        self.timer += 1
        # sinh particle theo mức charge
        if self.timer % max(1, int(5 - level * 3)) == 0:
            angle = random.uniform(0, math.pi * 2)
            r = random.uniform(10, 30 + level * 20)
            vx = -math.cos(angle) * random.uniform(0.5, 2)
            vy = -math.sin(angle) * random.uniform(0.5, 2)
            color_g = int(200 + level * 55)
            self.particles.append(Particle(
                x + math.cos(angle) * r,
                y + math.sin(angle) * r,
                vx, vy,
                (50, color_g, 150 + int(level * 100)),
                random.randint(10, 20), size=random.randint(2, 4)
            ))
        for p in self.particles:
            p.update()
        self.particles = [p for p in self.particles if p.alive]

    def draw(self, surface):
        for p in self.particles:
            p.draw(surface)
        # vòng tròn charge
        if self.level > 0.1:
            r = int(15 + self.level * 25)
            alpha = int(120 * self.level)
            s = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
            pygame.draw.circle(s, (50, 220, 180, alpha), (r, r), r, 2)
            surface.blit(s, (self.x - r, self.y - r))


class DamageNumber:
    """Số damage bay lên khi đánh trúng"""
    def __init__(self, x, y, damage, color=(255, 80, 80)):
        self.x = float(x)
        self.y = float(y)
        self.damage = damage
        self.color = color
        self.vy = -2.5
        self.timer = 50
        self.alive = True
        self.font = None

    def update(self):
        self.y += self.vy
        self.vy *= 0.95
        self.timer -= 1
        if self.timer <= 0:
            self.alive = False

    def draw(self, surface, font):
        alpha = min(255, self.timer * 5)
        text = font.render(str(self.damage), True, self.color)
        text.set_alpha(alpha)
        surface.blit(text, (int(self.x) - text.get_width() // 2, int(self.y)))


class SlashTrail:
    """
    Vet chem kiem kieu Fruit Ninja: luu toa do tay thuc trong 3 giay.
    - 1 diem/tay/frame (palm center pts[9])
    - Width tỉ le voi velocity giua cac diem: clamp(vel*0.5, 4, 30)
    - Exponential smoothing de giam jitter
    - Ve bang gradient opacity + width giam dan tu goc den dau
    - Toi uu: dung 1 Surface duy nhat cho toan bo trail
    - Catmull-Rom interpolation giua cac diem de duong cong muot hon
    """
    TRAIL_DURATION_MS = 3000   # 3 giay = 180 frames @ 60fps

    def __init__(self):
        # Moi phan tu: (x, y, timestamp_ms, width)
        self._pts: list[tuple[int,int,int,int]] = []
        self._base_color = (180, 230, 255)    # xanh trang phat sang
        self._glow_color = (100, 200, 255)
        self.active = False   # True khi dang trong trang thai san sang chem
        # Smoothing: luu toa do cuoi de EMA
        self._smooth_x: float | None = None
        self._smooth_y: float | None = None

    def add_hand_point(self, screen_x: int, screen_y: int, width: int = 18):
        """
        Them toa do tay thuc (da scale sang man hinh) vao trail.
        Ap dung exponential smoothing truoc khi luu.
        """
        now = pygame.time.get_ticks()
        # Exponential smoothing (alpha=0.55: can bang giua muot va do nhanh)
        ALPHA = 0.55
        if self._smooth_x is None:
            sx, sy = float(screen_x), float(screen_y)
        else:
            sx = ALPHA * screen_x + (1 - ALPHA) * self._smooth_x
            sy = ALPHA * screen_y + (1 - ALPHA) * self._smooth_y
        self._smooth_x = sx
        self._smooth_y = sy
        self._pts.append((int(sx), int(sy), now, width))

    def clear(self):
        self._pts.clear()
        self._smooth_x = None
        self._smooth_y = None

    def update(self):
        """Loai bo cac diem qua TRAIL_DURATION_MS."""
        now = pygame.time.get_ticks()
        cutoff = now - self.TRAIL_DURATION_MS
        self._pts = [(x, y, t, w) for (x, y, t, w) in self._pts if t > cutoff]

    def get_active_segments(self):
        """
        Tra ve list segment [(x1,y1,x2,y2,width)] cua trail dang active.
        Dung de kiem tra va cham voi enemy trong game.py.
        """
        segs = []
        if len(self._pts) < 2:
            return segs
        now = pygame.time.get_ticks()
        for i in range(len(self._pts) - 1):
            x1, y1, t1, _ = self._pts[i]
            x2, y2, t2, _ = self._pts[i + 1]
            age = now - t1
            if age < self.TRAIL_DURATION_MS:
                vel = math.sqrt((x2-x1)**2 + (y2-y1)**2)
                w = int(max(4, min(30, vel * 0.5)))
                segs.append((x1, y1, x2, y2, w))
        return segs

    def _catmull_rom(self, p0, p1, p2, p3, t):
        """Catmull-Rom spline interpolation giua p1 va p2"""
        t2 = t * t
        t3 = t2 * t
        x = 0.5 * ((2 * p1[0]) +
                    (-p0[0] + p2[0]) * t +
                    (2*p0[0] - 5*p1[0] + 4*p2[0] - p3[0]) * t2 +
                    (-p0[0] + 3*p1[0] - 3*p2[0] + p3[0]) * t3)
        y = 0.5 * ((2 * p1[1]) +
                    (-p0[1] + p2[1]) * t +
                    (2*p0[1] - 5*p1[1] + 4*p2[1] - p3[1]) * t2 +
                    (-p0[1] + 3*p1[1] - 3*p2[1] + p3[1]) * t3)
        return (int(x), int(y))

    def draw(self, surface):
        """Ve vet chem gradient: dau trail mo, cuoi trail sang.
        Dung 1 Surface duy nhat de toi uu hieu nang."""
        if len(self._pts) < 2:
            return
        now = pygame.time.get_ticks()
        n = len(self._pts)

        # Tao 1 Surface duy nhat cho toan bo trail
        trail_surf = pygame.Surface(surface.get_size(), pygame.SRCALPHA)

        # Xay dung danh sach diem voi Catmull-Rom interpolation
        interp_pts = []
        INTERP_STEPS = 3  # so diem noi suy giua moi cap diem goc

        for i in range(n):
            x_i, y_i, t_i, w_i = self._pts[i]
            interp_pts.append((x_i, y_i, t_i))

            # Chen diem noi suy giua diem i va i+1 (Catmull-Rom)
            if i < n - 1:
                p0 = self._pts[max(0, i-1)][:2]
                p1 = (x_i, y_i)
                p2 = self._pts[i+1][:2]
                p3 = self._pts[min(n-1, i+2)][:2]
                t_next = self._pts[i+1][2]
                for s in range(1, INTERP_STEPS):
                    frac = s / INTERP_STEPS
                    ix, iy = self._catmull_rom(p0, p1, p2, p3, frac)
                    it = int(t_i + (t_next - t_i) * frac)
                    interp_pts.append((ix, iy, it))

        total = len(interp_pts)
        if total < 2:
            return

        # Ve tung doan tren 1 Surface duy nhat
        for i in range(total - 1):
            x1, y1, t1 = interp_pts[i]
            x2, y2, t2 = interp_pts[i + 1]

            # Age-based alpha: diem cu = mo, diem moi = sang
            age1 = now - t1
            frac1 = max(0.0, 1.0 - age1 / self.TRAIL_DURATION_MS)
            # Progress-based: cuoi trail (i lon) sang hon
            prog  = (i + 1) / total
            alpha = int(255 * frac1 * prog)
            if alpha < 8:
                continue

            # Width theo velocity
            vel = math.sqrt((x2 - x1)**2 + (y2 - y1)**2)
            width_vel = int(max(4, min(30, vel * 0.8)))
            width = max(1, int(width_vel * frac1 * (0.3 + 0.7 * prog)))

            # Lop glow (rong hon, mo hon)
            glow_alpha = alpha // 3
            if glow_alpha > 5:
                pygame.draw.line(trail_surf,
                                 (*self._glow_color, glow_alpha),
                                 (x1, y1), (x2, y2), width * 3)
            # Lop chinh
            pygame.draw.line(trail_surf,
                             (*self._base_color, alpha),
                             (x1, y1), (x2, y2), width)
            # Lop core sang nhat (1px trang)
            if alpha > 80:
                pygame.draw.line(trail_surf, (255, 255, 255, alpha // 2),
                                 (x1, y1), (x2, y2), max(1, width // 3))

        surface.blit(trail_surf, (0, 0))


class MineExplosion:
    """
    Vu no min: sprite frame animation + shockwave rings + particles + pixel ripple.
    Dung explosion_frames (8 frame) tu sprites.py, scale lon phu AoE 200px.
    """
    DURATION = 50   # frames

    def __init__(self, x, y, explosion_frames=None):
        self.x = x
        self.y = y
        self.timer = 0
        self.alive = True

        # Sprite frames (scale len 200px radius = 400px diameter)
        self._frames = []
        if explosion_frames:
            for f in explosion_frames:
                scaled = pygame.transform.scale(f, (400, 400))
                self._frames.append(scaled)

        # 2 vong shockwave
        self._rings = [
            {'r': 0, 'max_r': 200, 'speed': 12, 'color': (255, 180, 60)},
            {'r': 0, 'max_r': 260, 'speed': 8, 'color': (255, 100, 30)},
        ]

        # Particles: manh vo bay ra
        self._particles = []
        for _ in range(60):
            angle = random.uniform(0, math.pi * 2)
            speed = random.uniform(3, 14)
            color = random.choice([
                (255, 120, 20), (255, 200, 50), (200, 60, 10),
                (255, 255, 150), (80, 80, 80),
            ])
            self._particles.append(Particle(
                x, y,
                math.cos(angle) * speed, math.sin(angle) * speed,
                color, random.randint(25, 45),
                size=random.randint(3, 9), gravity=0.35,
            ))

        # Flash trung tam
        self._flash = FlashEffect(x, y, (255, 220, 100), radius=120, duration=20)

        # Pixel ripple grid: luoi pixel bi day boi song lan
        self._ripple_pixels = []
        PIXEL_SIZE = 6
        GRID_RADIUS = 250  # ban kinh vung ripple
        for gx in range(-GRID_RADIUS, GRID_RADIUS + 1, PIXEL_SIZE * 2):
            for gy in range(-GRID_RADIUS, GRID_RADIUS + 1, PIXEL_SIZE * 2):
                dist = math.sqrt(gx * gx + gy * gy)
                if dist < GRID_RADIUS and dist > 30:
                    color = random.choice([
                        (255, 140, 30), (255, 200, 60), (200, 80, 20),
                        (255, 120, 10), (180, 60, 10),
                    ])
                    self._ripple_pixels.append({
                        'ox': gx, 'oy': gy,       # vi tri goc (offset tu tam)
                        'dist': dist,               # khoang cach den tam
                        'color': color,
                        'size': PIXEL_SIZE,
                    })

    def update(self):
        self.timer += 1
        # Particles
        for p in self._particles:
            p.update()
        self._particles = [p for p in self._particles if p.alive]
        # Rings
        for ring in self._rings:
            ring['r'] += ring['speed']
        # Flash
        self._flash.update()
        if self.timer >= self.DURATION:
            self.alive = False

    def draw(self, surface):
        if not self.alive:
            return
        t = self.timer / self.DURATION

        # --- Pixel ripple effect (song lan pixel) ---
        wave_speed = 400.0   # toc do song lan (px/s tuong duong)
        wave_front = self.timer * (wave_speed / 60.0)  # vi tri dau song
        wave_width = 80.0    # do rong cua song
        ripple_surf = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        for px_info in self._ripple_pixels:
            dist = px_info['dist']
            # Chi ve pixel nam trong vung song dang di qua
            dist_to_wave = abs(dist - wave_front)
            if dist_to_wave > wave_width:
                continue
            # Tinh do dich chuyen theo sin
            wave_phase = (dist - wave_front) / wave_width * math.pi
            displacement = math.sin(wave_phase) * 12 * max(0, 1 - t * 1.5)
            # Huong day: ra xa tam
            angle = math.atan2(px_info['oy'], px_info['ox'])
            dx = math.cos(angle) * displacement
            dy = math.sin(angle) * displacement
            # Alpha giam dan theo thoi gian va khoang cach
            alpha = int(200 * max(0, 1 - dist_to_wave / wave_width) * max(0, 1 - t * 1.2))
            if alpha < 5:
                continue
            rx = int(self.x + px_info['ox'] + dx)
            ry = int(self.y + px_info['oy'] + dy)
            sz = px_info['size']
            c = px_info['color']
            pygame.draw.rect(ripple_surf, (*c, alpha), (rx, ry, sz, sz))
        surface.blit(ripple_surf, (0, 0))

        # --- Sprite frame animation ---
        if self._frames:
            n = len(self._frames)
            idx = min(n - 1, int(t * n))
            frame = self._frames[idx]
            # Fade out cuoi animation
            if t > 0.5:
                frame = frame.copy()
                frame.set_alpha(int(255 * (1 - (t - 0.5) * 2)))
            rect = frame.get_rect(center=(self.x, self.y))
            surface.blit(frame, rect)

        # --- Shockwave rings ---
        for ring in self._rings:
            r = int(ring['r'])
            if r <= 0 or r > ring['max_r'] * 1.5:
                continue
            alpha = max(0, int(200 * (1 - r / (ring['max_r'] * 1.2))))
            if alpha < 5:
                continue
            ring_surf = pygame.Surface((r * 2 + 10, r * 2 + 10), pygame.SRCALPHA)
            c = ring['color']
            pygame.draw.circle(ring_surf, (*c, alpha),
                               (r + 5, r + 5), r, max(2, 6 - int(t * 5)))
            surface.blit(ring_surf,
                         (self.x - r - 5, self.y - r - 5))

        # --- Screen flash (vung sang trung tam) ---
        self._flash.draw(surface)

        # --- Particles ---
        for p in self._particles:
            p.draw(surface)

        # --- Hieu ung vet chay tren mat dat ---
        if t > 0.3:
            scorch_alpha = max(0, int(120 * (1 - (t - 0.3) / 0.7)))
            if scorch_alpha > 5:
                scorch_surf = pygame.Surface((300, 30), pygame.SRCALPHA)
                pygame.draw.ellipse(scorch_surf, (30, 20, 10, scorch_alpha),
                                    (0, 0, 300, 30))
                surface.blit(scorch_surf,
                             (self.x - 150, self.y - 5))


class PunchImpact:
    """
    Hieu ung dau tay khi dau trung: vong shockwave + dau tay + vung AoE.
    """
    def __init__(self, x: int, y: int, side: str = 'right'):
        """
        x, y : vi tri nhan vat (toa do man hinh game)
        side : 'left' or 'right' - tay dau
        """
        self.x = x
        self.y = y
        self.side = side
        self.timer = 0
        self.DURATION = 45   # frames
        self.alive = True
        self._particles: list[Particle] = []
        self._spawn_particles()

    def _spawn_particles(self):
        for _ in range(30):
            angle = random.uniform(0, math.pi * 2)
            speed = random.uniform(3, 10)
            color = random.choice([
                (255, 160, 40),
                (255, 200, 80),
                (200, 100, 20),
                (255, 255, 150),
            ])
            self._particles.append(Particle(
                self.x, self.y,
                math.cos(angle) * speed, math.sin(angle) * speed,
                color, random.randint(15, 30),
                size=random.randint(3, 7),
                gravity=0.2,
            ))

    def update(self):
        self.timer += 1
        for p in self._particles:
            p.update()
        self._particles = [p for p in self._particles if p.alive]
        if self.timer >= self.DURATION:
            self.alive = False

    def draw(self, surface):
        if not self.alive:
            return
        t = self.timer / self.DURATION   # 0.0 -> 1.0

        # --- Vong shockwave mo rong ---
        shock_r = int(50 + 120 * t)
        shock_alpha = int(220 * (1 - t))
        if shock_alpha > 5:
            shock_surf = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
            pygame.draw.circle(shock_surf,
                               (255, 180, 60, shock_alpha),
                               (self.x, self.y), shock_r, 4)
            pygame.draw.circle(shock_surf,
                               (255, 120, 20, shock_alpha // 2),
                               (self.x, self.y), max(1, shock_r - 15), 2)
            surface.blit(shock_surf, (0, 0))

        # --- Vung AoE hinh tron ban trong (radius 120px) ---
        aoe_r = 120
        aoe_alpha = int(70 * (1 - t))
        if aoe_alpha > 5:
            aoe_surf = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
            pygame.draw.circle(aoe_surf,
                               (255, 140, 40, aoe_alpha),
                               (self.x, self.y), aoe_r)
            pygame.draw.circle(aoe_surf,
                               (255, 200, 80, aoe_alpha + 30),
                               (self.x, self.y), aoe_r, 3)
            surface.blit(aoe_surf, (0, 0))

        # --- Dau in hinh ban tay (5 hinh tron = ngon tay + 1 hinh lon = long ban tay) ---
        stamp_alpha = int(200 * max(0, 1 - t * 2))  # bien mat nhanh hon
        if stamp_alpha > 10:
            # Xac dinh vi tri ngon tay theo side
            mirror = -1 if self.side == 'left' else 1
            # Vi tri 5 ngon tay quanh toa do impact
            finger_offsets = [
                (mirror * -40, -55),   # pinky
                (mirror * -20, -70),   # ring
                (mirror *   5, -75),   # middle
                (mirror *  28, -65),   # index
                (mirror *  45, -40),   # thumb
            ]
            stamp_surf = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
            # Long ban tay
            pygame.draw.ellipse(stamp_surf,
                                (255, 160, 40, stamp_alpha),
                                (self.x - 30, self.y - 35, 60, 50))
            # Ngon tay
            for (fx, fy) in finger_offsets:
                pygame.draw.circle(stamp_surf,
                                   (255, 160, 40, stamp_alpha),
                                   (self.x + fx, self.y + fy), 11)
                pygame.draw.circle(stamp_surf,
                                   (255, 220, 100, stamp_alpha // 2),
                                   (self.x + fx, self.y + fy), 7)
            surface.blit(stamp_surf, (0, 0))

        # Particles
        for p in self._particles:
            p.draw(surface)


class FireOrb:
    """
    Vang lua quay quanh nguoi choi. Tieu diet quai khi cham vao.
    Su dung fire.gif lam hinh anh.
    """
    ORBIT_RADIUS = 80    # ban kinh quy dao quay
    ORBIT_SPEED  = 0.04  # rad/frame (~2.4 rad/s @ 60fps)
    DAMAGE       = 50
    HIT_RADIUS   = 25    # ban kinh va cham

    _fire_frames = None   # cache GIF frames (class-level)

    def __init__(self, angle_offset=0.0):
        self.angle = angle_offset
        self.alive = True
        # Load fire GIF frames (chi load 1 lan)
        if FireOrb._fire_frames is None:
            FireOrb._fire_frames = get_gif_frames('fire.gif', target_size=(40, 40))
            if not FireOrb._fire_frames:
                # Fallback: tao surface lua don gian
                s = pygame.Surface((40, 40), pygame.SRCALPHA)
                pygame.draw.circle(s, (255, 140, 30, 220), (20, 20), 16)
                pygame.draw.circle(s, (255, 220, 80, 180), (20, 20), 10)
                pygame.draw.circle(s, (255, 255, 200, 150), (20, 20), 5)
                FireOrb._fire_frames = [s]
        self._anim_timer = random.randint(0, 100)

    def get_world_pos(self, player_x, player_y):
        """Tra ve toa do hien tai tren man hinh"""
        ox = player_x + math.cos(self.angle) * self.ORBIT_RADIUS
        oy = (player_y - 30) + math.sin(self.angle) * self.ORBIT_RADIUS * 0.5  # oval
        return ox, oy

    def update(self):
        self.angle += self.ORBIT_SPEED
        if self.angle > math.pi * 2:
            self.angle -= math.pi * 2
        self._anim_timer += 1

    def draw(self, surface, player_x, player_y):
        if not self.alive:
            return
        ox, oy = self.get_world_pos(player_x, player_y)
        frames = FireOrb._fire_frames
        if frames:
            idx = (self._anim_timer // 4) % len(frames)
            frame = frames[idx]
            rect = frame.get_rect(center=(int(ox), int(oy)))
            surface.blit(frame, rect)
        # Glow xung quanh
        glow_surf = pygame.Surface((60, 60), pygame.SRCALPHA)
        pygame.draw.circle(glow_surf, (255, 120, 20, 40), (30, 30), 28)
        surface.blit(glow_surf, (int(ox) - 30, int(oy) - 30))


class FireOrbManager:
    """Quan ly tat ca vang lua quay quanh nguoi choi"""
    def __init__(self):
        self.orbs: list[FireOrb] = []

    def add_orb(self):
        """Them 1 vang lua moi. Goc bat dau cach deu cac orb hien tai."""
        if len(self.orbs) == 0:
            angle = 0.0
        else:
            # Dat goc cach deu
            angle = max(o.angle for o in self.orbs) + math.pi * 2 / (len(self.orbs) + 1)
        self.orbs.append(FireOrb(angle_offset=angle))
        # Phan phoi lai goc deu cho tat ca orb
        n = len(self.orbs)
        for i, orb in enumerate(self.orbs):
            orb.angle = (i * 2 * math.pi / n)

    def update(self, player_x, player_y, enemies):
        """Cap nhat va kiem tra va cham voi enemy"""
        for orb in self.orbs:
            orb.update()
            if not orb.alive:
                continue
            ox, oy = orb.get_world_pos(player_x, player_y)
            for e in enemies:
                if not e.alive:
                    continue
                dist = math.sqrt((ox - e.x) ** 2 + (oy - e.y) ** 2)
                if dist < FireOrb.HIT_RADIUS + 20:
                    e.take_damage(FireOrb.DAMAGE)
                    e.knockback((e.x - ox) * 0.3, -4)
        self.orbs = [o for o in self.orbs if o.alive]

    def draw(self, surface, player_x, player_y):
        for orb in self.orbs:
            orb.draw(surface, player_x, player_y)


class EffectManager:
    """Quản lý tất cả hiệu ứng trên màn hình"""
    def __init__(self):
        self.effects = []
        self.trails = {}
        self.damage_numbers = []

    def add_effect(self, effect):
        self.effects.append(effect)

    def add_trail(self, name, color=(200, 220, 255)):
        if name not in self.trails:
            self.trails[name] = TrailEffect(color)
        return self.trails[name]

    def get_trail(self, name):
        return self.trails.get(name)

    def add_damage_number(self, x, y, damage, color=(255, 80, 80)):
        self.damage_numbers.append(DamageNumber(x, y, damage, color))

    def clear_trail(self, name):
        if name in self.trails:
            self.trails[name].clear()

    def update(self):
        self.effects = [e for e in self.effects if e.alive]
        for e in self.effects:
            e.update()
        self.damage_numbers = [d for d in self.damage_numbers if d.alive]
        for d in self.damage_numbers:
            d.update()

    def draw(self, surface, font=None):
        for e in self.effects:
            e.draw(surface)
        for trail in self.trails.values():
            trail.draw(surface)
        if font:
            for d in self.damage_numbers:
                d.draw(surface, font)
