"""
sprites.py - Tạo sprite pixel art bằng code (không cần file ngoài)
Tất cả nhân vật, vũ khí, quái vật đều được vẽ bằng pygame.Surface
"""

import pygame
import numpy as np
import math


def scale_sprite(surf, scale=2):
    w, h = surf.get_size()
    return pygame.transform.scale(surf, (w * scale, h * scale))


# ─────────────────────────────────────────────
#  HERO SPRITE (16x24 px, animated)
# ─────────────────────────────────────────────
HERO_IDLE = [
    "................",
    "......XXXX......",
    ".....X0000X.....",
    ".....X0000X.....",
    "......XXXX......",
    "....XXXXXXXX....",
    "...XXXXXXXXXX...",
    "..XX.XXXXXX.XX..",
    "...XX.XXXX.XX...",
    "....XX....XX....",
    ".....X....X.....",
    ".....X....X.....",
    "....XX....XX....",
    "...XX......XX...",
    "...X........X...",
]

HERO_ATTACK = [
    "................",
    "......XXXX......",
    ".....X0000X.....",
    ".....X0000X.....",
    "......XXXX......",
    "....XXXXXXXX....",
    "..XXXXXXXXXXXX..",
    ".XX.XXXXXXXXX...",
    "..XX.XXXXXX.....",
    "...XXXXXXXXXXX..",
    ".....X....X.....",
    ".....X....X.....",
    "....XX....XX....",
    "...XX......XX...",
    "...X........X...",
]


def draw_pixel_art(pattern, colors, size=(16, 24)):
    surf = pygame.Surface(size, pygame.SRCALPHA)
    surf.fill((0, 0, 0, 0))
    for y, row in enumerate(pattern):
        for x, ch in enumerate(row):
            if ch in colors:
                surf.set_at((x, y), colors[ch])
    return surf


def make_hero_sprite(frame=0, weapon=None):
    """Tạo sprite hero với màu sắc theo vũ khí đang cầm"""
    colors = {
        'X': (80, 120, 200),   # áo xanh
        '0': (255, 200, 150),  # mặt
    }
    if weapon == 'iron_gauntlets':
        colors['X'] = (100, 100, 120)  # xám thép
    elif weapon == 'sword':
        colors['X'] = (70, 100, 180)
    elif weapon == 'bow':
        colors['X'] = (60, 140, 80)
    elif weapon == 'grenade':
        colors['X'] = (180, 80, 60)
    elif weapon == 'gun':
        colors['X'] = (80, 80, 80)

    pattern = HERO_ATTACK if frame == 1 else HERO_IDLE
    surf = draw_pixel_art(pattern, colors, (16, 15))
    return scale_sprite(surf, 3)


# ─────────────────────────────────────────────
#  ENEMY SPRITES
# ─────────────────────────────────────────────

# Hulk-type: to lớn, xanh lá
HULK_PATTERN = [
    "..XXXXXXXXXX..",
    ".XXXXXXXXXXXX.",
    "XXXXXXXXXXXXXX",
    "XX.X0000X.XXXX",
    "XX.XXXXXX.XXXX",
    "XXXXXXXXXXXXXX",
    ".XXXXXXXXXXXX.",
    "XXXXXXXXXXXXXX",
    "XX.XXXXXXXX.XX",
    "XX..XXXXXX..XX",
    ".XXX.XXXX.XXX.",
    "..XX.XXXX.XX..",
    "...XX....XX...",
]

# Samurai: thanh mảnh, có kiếm
SAMURAI_PATTERN = [
    "....XXXX....",
    "...XXXXXX...",
    "...X0000X...",
    "...XXXXXX...",
    "..XXXXXXXX..",
    ".XXXXXXXXXX.",
    "..XXXXXXXX..",
    "...XXXXXX...",
    "...XX..XX...",
    "...XX..XX...",
    "..XXX..XXX..",
    ".XXXX..XXXX.",
]

# Space Alien: nhỏ, nhiều mắt
ALIEN_PATTERN = [
    ".....XXXXX.....",
    "....XXXXXXX....",
    "...XXXXXXXXX...",
    "...X0X.X0X.X...",
    "...XXXXXXXXX...",
    "....XXXXXXX....",
    "...XXXXXXXXX...",
    "..XXXXXXXXXXX..",
    "...X.X.X.X.X...",
    "....X.....X....",
]


def make_hulk_sprite(frame=0):
    base_color = (50, 180, 80) if frame == 0 else (80, 220, 100)
    colors = {'X': base_color, '0': (255, 50, 50)}
    surf = draw_pixel_art(HULK_PATTERN, colors, (14, 13))
    return scale_sprite(surf, 4)


def make_samurai_sprite(frame=0):
    base_color = (160, 40, 40) if frame == 0 else (200, 60, 60)
    colors = {'X': base_color, '0': (255, 220, 180)}
    surf = draw_pixel_art(SAMURAI_PATTERN, colors, (12, 12))
    return scale_sprite(surf, 4)


def make_alien_sprite(frame=0):
    base_color = (80, 40, 180) if frame == 0 else (120, 60, 220)
    colors = {'X': base_color, '0': (0, 255, 200)}
    surf = draw_pixel_art(ALIEN_PATTERN, colors, (15, 10))
    return scale_sprite(surf, 4)


# Dragon: bay, phun lua, HP cao
DRAGON_PATTERN = [
    "......XX..........",
    ".....XXXX.........",
    "....XXXXXX........",
    "...X00XXXXX.......",
    "...XXXXXXXX.......",
    "..XXXXXXXXXX......",
    ".XXXXXXXXXXXXXXX..",
    "..XXXXXXXXXXXXX...",
    "...XXXXXXXXXXX....",
    "..XX...XXXX...XX..",
    ".XX.....XX.....XX.",
    "XX......XX......XX",
]

# Ghost: xuat hien/bien mat, xuyen obstacle
GHOST_PATTERN = [
    "....XXXXXX....",
    "...XXXXXXXX...",
    "..XXXXXXXXXX..",
    "..X0XX..X0XX..",
    "..XXXXXXXXXX..",
    ".XXXXXXXXXXXX.",
    ".XXXXXXXXXXXX.",
    ".XXXXXXXXXXXX.",
    "..XXXXXXXXXX..",
    "..XX.XXXX.XX..",
    "...X..XX..X...",
    "......XX......",
]


def make_dragon_sprite(frame=0):
    base_color = (200, 60, 20) if frame == 0 else (240, 80, 30)
    colors = {'X': base_color, '0': (255, 200, 0)}
    surf = draw_pixel_art(DRAGON_PATTERN, colors, (18, 12))
    return scale_sprite(surf, 4)


def make_ghost_sprite(frame=0):
    base_color = (140, 140, 180) if frame == 0 else (170, 170, 210)
    colors = {'X': base_color, '0': (200, 50, 50)}
    surf = draw_pixel_art(GHOST_PATTERN, colors, (14, 12))
    return scale_sprite(surf, 4)


def make_fast_alien_sprite(frame=0):
    """Alien nhanh - mau xanh cyan"""
    base_color = (0, 200, 220) if frame == 0 else (0, 240, 255)
    colors = {'X': base_color, '0': (255, 255, 0)}
    surf = draw_pixel_art(ALIEN_PATTERN, colors, (14, 10))
    return scale_sprite(surf, 4)


def make_elite_hulk_sprite(frame=0):
    """Hulk d'elite - mau do dam"""
    base_color = (180, 30, 30) if frame == 0 else (220, 50, 50)
    colors = {'X': base_color, '0': (255, 255, 100)}
    surf = draw_pixel_art(HULK_PATTERN, colors, (16, 16))
    return scale_sprite(surf, 4)


# ─────────────────────────────────────────────
#  WEAPON ICONS (hiển thị trên HUD)
# ─────────────────────────────────────────────

def make_gauntlet_icon(size=32):
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    surf.fill((0, 0, 0, 0))
    # nắm đấm
    pygame.draw.rect(surf, (120, 120, 140), (6, 12, 20, 14), border_radius=4)
    pygame.draw.rect(surf, (160, 160, 180), (6, 10, 20, 6), border_radius=3)
    # ngón tay
    for i in range(4):
        pygame.draw.rect(surf, (140, 140, 160), (7 + i * 4, 6, 3, 6), border_radius=2)
    # viền sáng
    pygame.draw.rect(surf, (200, 200, 255), (6, 12, 20, 14), width=1, border_radius=4)
    return surf


def make_sword_icon(size=32):
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    surf.fill((0, 0, 0, 0))
    # lưỡi kiếm
    pygame.draw.polygon(surf, (200, 220, 255), [(16, 2), (12, 26), (20, 26)])
    pygame.draw.polygon(surf, (150, 200, 255), [(16, 2), (14, 26), (16, 26)])
    # chuôi
    pygame.draw.rect(surf, (180, 140, 60), (13, 24, 6, 8), border_radius=2)
    pygame.draw.rect(surf, (220, 180, 80), (8, 23, 16, 3), border_radius=2)
    return surf


def make_bow_icon(size=32):
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    surf.fill((0, 0, 0, 0))
    # cung
    pygame.draw.arc(surf, (140, 100, 60), (4, 4, 14, 24), math.pi * 0.1, math.pi * 0.9, 3)
    # dây cung
    pygame.draw.line(surf, (200, 180, 140), (11, 5), (11, 27), 1)
    # mũi tên
    pygame.draw.line(surf, (200, 200, 200), (12, 16), (28, 16), 2)
    pygame.draw.polygon(surf, (255, 200, 50), [(28, 16), (23, 13), (23, 19)])
    return surf


def make_grenade_icon(size=32):
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    surf.fill((0, 0, 0, 0))
    # thân lựu đạn
    pygame.draw.ellipse(surf, (80, 140, 80), (8, 14, 16, 16))
    pygame.draw.ellipse(surf, (100, 180, 100), (9, 15, 8, 8))
    # ngòi
    pygame.draw.rect(surf, (180, 180, 60), (13, 8, 6, 8), border_radius=2)
    pygame.draw.circle(surf, (255, 220, 50), (16, 7), 3)
    # viền
    pygame.draw.ellipse(surf, (50, 100, 50), (8, 14, 16, 16), 1)
    return surf


def make_gun_icon(size=32):
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    surf.fill((0, 0, 0, 0))
    # thân súng
    pygame.draw.rect(surf, (80, 80, 90), (4, 14, 20, 10), border_radius=2)
    pygame.draw.rect(surf, (100, 100, 110), (4, 14, 10, 5))
    # nòng
    pygame.draw.rect(surf, (60, 60, 70), (20, 16, 8, 4), border_radius=1)
    # cò súng
    pygame.draw.rect(surf, (90, 90, 100), (10, 22, 4, 6), border_radius=2)
    # viền
    pygame.draw.rect(surf, (160, 160, 180), (4, 14, 20, 10), width=1, border_radius=2)
    return surf


def make_mine_icon(size=32):
    """Icon mìn: hình tròn dẹt + gai xung quanh"""
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    surf.fill((0, 0, 0, 0))
    cx, cy = size // 2, size // 2 + 4
    # Than min
    pygame.draw.ellipse(surf, (60, 60, 70), (cx - 10, cy - 6, 20, 12))
    pygame.draw.ellipse(surf, (90, 90, 100), (cx - 8, cy - 4, 12, 7))
    pygame.draw.ellipse(surf, (40, 40, 50), (cx - 10, cy - 6, 20, 12), 1)
    # Gai xung quanh (6 gai)
    for i in range(6):
        angle = math.radians(i * 60)
        x1 = int(cx + math.cos(angle) * 9)
        y1 = int(cy + math.sin(angle) * 5)
        x2 = int(cx + math.cos(angle) * 13)
        y2 = int(cy + math.sin(angle) * 7)
        pygame.draw.line(surf, (200, 50, 50), (x1, y1), (x2, y2), 2)
    # Den do nhap nhay (vong tron nho o giua)
    pygame.draw.circle(surf, (255, 60, 60), (cx, cy), 3)
    # Dau noi
    pygame.draw.rect(surf, (100, 100, 110), (cx - 2, cy - 10, 4, 6), border_radius=1)
    return surf


WEAPON_ICONS = {
    'iron_gauntlets': make_gauntlet_icon,
    'sword': make_sword_icon,
    'bow': make_bow_icon,
    'grenade': make_grenade_icon,
    'gun': make_gun_icon,
    'mine': make_mine_icon,
}


# ─────────────────────────────────────────────
#  BACKGROUND: Nền không gian cuộn
# ─────────────────────────────────────────────

def make_space_background(width=800, height=600, num_stars=200):
    surf = pygame.Surface((width, height))
    surf.fill((5, 5, 20))
    rng = np.random.default_rng(42)
    xs = rng.integers(0, width, num_stars)
    ys = rng.integers(0, height, num_stars)
    sizes = rng.choice([1, 1, 1, 2], num_stars)
    brights = rng.integers(150, 255, num_stars)
    for x, y, s, b in zip(xs, ys, sizes, brights):
        c = (b, b, min(255, b + 40))
        if s == 1:
            surf.set_at((int(x), int(y)), c)
        else:
            pygame.draw.circle(surf, c, (int(x), int(y)), s)
    # Vài tinh vân mờ
    for _ in range(3):
        nx = int(rng.integers(100, width - 100))
        ny = int(rng.integers(50, height - 50))
        nebula = pygame.Surface((120, 80), pygame.SRCALPHA)
        pygame.draw.ellipse(nebula, (30, 10, 60, 40), (0, 0, 120, 80))
        surf.blit(nebula, (nx - 60, ny - 40))
    return surf


# ─────────────────────────────────────────────
#  PROJECTILE SPRITES
# ─────────────────────────────────────────────

def make_arrow_sprite():
    surf = pygame.Surface((24, 6), pygame.SRCALPHA)
    # thân tên
    pygame.draw.rect(surf, (200, 180, 120), (0, 2, 18, 2))
    # đầu mũi tên
    pygame.draw.polygon(surf, (220, 220, 100), [(18, 0), (24, 3), (18, 6)])
    # đuôi
    pygame.draw.polygon(surf, (180, 100, 60), [(0, 0), (4, 3), (0, 6)])
    return surf


def make_bullet_sprite():
    surf = pygame.Surface((10, 4), pygame.SRCALPHA)
    pygame.draw.ellipse(surf, (255, 220, 50), (0, 0, 10, 4))
    pygame.draw.ellipse(surf, (255, 255, 150), (2, 1, 5, 2))
    return surf


def make_grenade_projectile():
    surf = pygame.Surface((24, 24), pygame.SRCALPHA)
    pygame.draw.ellipse(surf, (80, 140, 80), (2, 6, 20, 16))
    pygame.draw.ellipse(surf, (100, 180, 100), (5, 8, 10, 10))
    pygame.draw.rect(surf, (200, 200, 60), (8, 0, 8, 8), border_radius=2)
    # Chi tiet: vach ngang
    pygame.draw.line(surf, (60, 110, 60), (4, 14), (20, 14), 1)
    return surf


def make_explosion_frames(radius_max=40, frames=8):
    """Tạo animation vụ nổ"""
    result = []
    for i in range(frames):
        r = int(radius_max * (i + 1) / frames)
        alpha = int(255 * (1 - i / frames))
        surf = pygame.Surface((radius_max * 2, radius_max * 2), pygame.SRCALPHA)
        # lõi trắng
        if i < 3:
            pygame.draw.circle(surf, (255, 255, 200, alpha), (radius_max, radius_max), r // 2)
        # vòng cam
        pygame.draw.circle(surf, (255, 140, 20, alpha), (radius_max, radius_max), r, max(1, r // 3))
        # vòng đỏ ngoài
        if r > 5:
            pygame.draw.circle(surf, (200, 50, 10, alpha // 2), (radius_max, radius_max), r, 2)
        result.append(surf)
    return result


# ─────────────────────────────────────────────
#  GIF SPRITE LOADER (trich xuat frames tu GIF)
# ─────────────────────────────────────────────
import os
from PIL import Image

_ASSETS_IMAGES = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "assets", "images"
)


def load_gif_frames(filename, target_size=None):
    """
    Load tat ca frame cua GIF tu assets/images/ thanh list[pygame.Surface].
    target_size: (w, h) de scale, None = giu nguyen.
    """
    path = os.path.join(_ASSETS_IMAGES, filename)
    if not os.path.exists(path):
        print(f"[sprites] WARNING: GIF not found: {path}")
        return []
    pil_img = Image.open(path)
    frames = []
    try:
        while True:
            # Chuyen frame sang RGBA
            frame_rgba = pil_img.convert("RGBA")
            w, h = frame_rgba.size
            raw = frame_rgba.tobytes()
            surf = pygame.image.fromstring(raw, (w, h), "RGBA").convert_alpha()
            if target_size:
                surf = pygame.transform.smoothscale(surf, target_size)
            frames.append(surf)
            pil_img.seek(pil_img.tell() + 1)
    except EOFError:
        pass
    return frames


# Cache GIF frames de khong load lai nhieu lan
_gif_cache = {}


def get_gif_frames(filename, target_size=None):
    """Load va cache GIF frames. Tra ve list[pygame.Surface]."""
    key = (filename, target_size)
    if key not in _gif_cache:
        _gif_cache[key] = load_gif_frames(filename, target_size)
    return _gif_cache[key]
