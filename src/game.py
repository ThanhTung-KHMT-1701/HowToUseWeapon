"""
game.py - Game loop chính
Full màn hình 1920×1080, vũ khí vẽ theo tay thật
"""

import pygame
import cv2
import sys
import math
import random

from src.sprites import (make_space_background, make_arrow_sprite,
                          make_bullet_sprite, make_grenade_projectile,
                          make_explosion_frames, WEAPON_ICONS)
from src.effects import EffectManager, FireOrbManager
from src.sound_manager import SoundManager
from src.gesture_detector import GestureDetector
from src.weapon_system import WeaponSystem
from src.weapon_renderer import WeaponRenderer
from src.player import Player
from src.enemy import EnemyManager
from src.hud import HUD, GameOverScreen
from src.loading_screen import LoadingScreen
from src.checking_weapon_screen import CheckingWeaponScreen
from src.story_screen import StoryScreen
from src.companion import Obstacle, Companion, SpaceConsole


# ─── Kích thước màn hình ─────────────────────────────────────────────────
SCREEN_W  = 1920
SCREEN_H  = 1080
FPS       = 60
FLOOR_Y   = int(SCREEN_H * 0.85)

# Kích thước camera (MediaPipe xử lý ở độ phân giải này)
CAM_W = 640
CAM_H = 480

# Parallax scroll
scroll_x = [0.0, 0.0]


def make_stars(w, h, n, speed_label, seed):
    """Tạo lớp ngôi sao cho parallax"""
    import numpy as np
    surf = pygame.Surface((w * 2, h), pygame.SRCALPHA)
    rng = np.random.default_rng(seed)
    xs = rng.integers(0, w * 2, n)
    ys = rng.integers(0, h, n)
    sizes = rng.choice([1, 1, 2], n)
    brights = rng.integers(120, 255, n)
    for x, y, s, b in zip(xs, ys, sizes, brights):
        alpha = b
        if s == 1:
            surf.set_at((int(x), int(y)), (b, b, min(255, b + 20), alpha))
        else:
            pygame.draw.circle(surf, (b, b, min(255, b + 20), alpha),
                               (int(x), int(y)), s)
    return surf


def draw_parallax_bg(surface, bg_base, star1, star2, t, _sx=None):
    """Vẽ nền parallax cuộn. _sx: list[float, float] override scroll_x nếu cần."""
    sx = _sx if _sx is not None else scroll_x
    surface.blit(bg_base, (0, 0))
    ox1 = int(sx[0]) % (SCREEN_W * 2)
    surface.blit(star1, (-ox1, 0))
    if ox1 > 0:
        surface.blit(star1, (SCREEN_W * 2 - ox1, 0))
    ox2 = int(sx[1]) % (SCREEN_W * 2)
    surface.blit(star2, (-ox2, 0))
    if ox2 > 0:
        surface.blit(star2, (SCREEN_W * 2 - ox2, 0))

    # Sàn không gian
    floor_surf = pygame.Surface((SCREEN_W, SCREEN_H - FLOOR_Y + 20),
                                pygame.SRCALPHA)
    floor_surf.fill((10, 10, 40, 180))
    for i in range(0, SCREEN_W, 60):
        bright = 30 + int(15 * math.sin(t * 0.03 + i * 0.06))
        pygame.draw.line(floor_surf, (bright, bright, bright + 20, 80),
                         (i, 0), (i + 30, 0), 1)
    surface.blit(floor_surf, (0, FLOOR_Y - 10))
    pygame.draw.line(surface, (60, 80, 160),
                     (0, FLOOR_Y), (SCREEN_W, FLOOR_Y), 2)


class Game:
    def __init__(self):
        pygame.mixer.pre_init(48000, -16, 2, 2048)  # match loading_music.ogg sample rate
        pygame.init()
        pygame.mixer.init()

        # ── Chế độ hiển thị ──────────────────────────────────────────────
        info = pygame.display.Info()
        real_w, real_h = info.current_w, info.current_h

        if real_w >= 1920 and real_h >= 1080:
            self.screen = pygame.display.set_mode(
                (SCREEN_W, SCREEN_H), pygame.FULLSCREEN | pygame.HWSURFACE
            )
        else:
            scale = min(real_w / SCREEN_W, real_h / SCREEN_H)
            win_w = int(SCREEN_W * scale)
            win_h = int(SCREEN_H * scale)
            self.screen = pygame.display.set_mode((win_w, win_h))

        self._real_w = self.screen.get_width()
        self._real_h = self.screen.get_height()
        self._needs_scale = (self._real_w != SCREEN_W or self._real_h != SCREEN_H)
        self._render_surf = pygame.Surface((SCREEN_W, SCREEN_H))

        pygame.display.set_caption('VibeGaming — Gesture Combat')
        self.clock     = pygame.time.Clock()
        self.font_debug = pygame.font.SysFont('Courier New', 16)

        # ── Loading screen (tạo ngay để hiển thị ngay) ───────────────────
        self.loading_screen = LoadingScreen(SCREEN_W, SCREEN_H)
        self._game_ready    = False

        # ── Các object game — giao giá trị sau khi loading xong ──────────
        self.cap              = None
        self.camera_frame     = None
        self._space_pressed   = False
        self.gesture          = None
        self.sound            = None
        self.bg_base          = None
        self.star1            = None
        self.star2            = None
        self.projectile_sprites = {}
        self.explosion_frames = None
        self.em               = None
        self.fire_orbs        = None
        self.player           = None
        self.enemy_mgr        = None
        self.weapon_sys       = None
        self.weapon_rend      = None
        self.hud              = None
        self.game_over_screen = None
        self.checking_weapon  = None

        # ── State machine ─────────────────────────────────────────────────
        # 'loading' → 'checking_weapon' → 'playing' | 'game_over'
        self.state = 'loading'
        self.t = 0
        self.wave_transition_timer = 0
        self.WAVE_TRANSITION = 120
        self.shake_timer     = 0
        self.shake_intensity = 0

        # Cache gesture
        self._gesture_preview  = None
        self._gesture_progress = 0.0
        self._bow_draw         = 0.0
        self._bow_hand         = None
        self._string_hand      = None
        self._gun_firing       = False
        self._gun_tips_center  = None
        self._mouth_open       = False
        self._hands            = []

        # Obstacles, console, companion
        self.obstacles         = []
        self.console           = None
        self.companion         = None

        # Auto mode: tu dong tan cong khi bat
        self.auto_mode         = False

        # Weapon unlock: 2 vu khi moi wave
        # Wave 1: iron_gauntlets + sword, Wave 2: bow + grenade, Wave 3: gun + mine
        self._ALL_WEAPONS = ['iron_gauntlets', 'sword', 'bow', 'grenade', 'gun', 'mine']
        self.unlocked_weapons = ['iron_gauntlets', 'sword']

    # ── Hàm init nặng (chạy trong background thread) ─────────────────────
    def _run_init(self, set_progress):
        import time
        set_progress(0.05, "Initializing camera...")
        # Dùng DirectShow backend trên Windows để init nhanh hơn
        self.cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        if not self.cap.isOpened():
            # Fallback: thử mở không chỉ định backend
            self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            print("[WARN] Không tìm thấy camera")
            self.cap = None
        else:
            # MJPG codec giúp decode frame nhanh hơn
            self.cap.set(cv2.CAP_PROP_FOURCC,
                         cv2.VideoWriter_fourcc(*'MJPG'))
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAM_W)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAM_H)
            # 30 FPS đủ cho gesture detection, game vẫn render 60fps
            self.cap.set(cv2.CAP_PROP_FPS, 30)
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # buffer nhỏ = frame mới nhất
            # Đọc 1 frame để warm-up pipeline camera
            self.cap.read()

        set_progress(0.20, "Loading gesture model...")
        self.gesture = GestureDetector()

        set_progress(0.40, "Loading sounds...")
        self.sound = SoundManager()

        set_progress(0.55, "Building sprites...")
        self.bg_base = make_space_background(SCREEN_W, SCREEN_H, 150)
        self.star1   = make_stars(SCREEN_W, SCREEN_H, 120, 'slow', 10)
        self.star2   = make_stars(SCREEN_W, SCREEN_H,  60, 'fast', 20)
        self.projectile_sprites = {
            'arrow':   make_arrow_sprite(),
            'bullet':  make_bullet_sprite(),
            'grenade': make_grenade_projectile(),
        }
        self.explosion_frames = make_explosion_frames()
        self.projectile_sprites['explosion_frames'] = self.explosion_frames

        set_progress(0.72, "Preparing game objects...")
        self.em = EffectManager()
        self.fire_orbs = FireOrbManager()
        self.player    = Player(SCREEN_W // 2, FLOOR_Y)
        self.enemy_mgr = EnemyManager(SCREEN_W, SCREEN_H)
        self.weapon_sys = WeaponSystem(
            player_pos=lambda: self.player.get_pos(),
            effect_manager=self.em,
            sound_manager=self.sound,
            sprites=self.projectile_sprites
        )
        self.weapon_sys._obstacle_ref = self.obstacles

        set_progress(0.88, "Preparing weapons & HUD...")
        self.weapon_rend = WeaponRenderer(cam_w=CAM_W, cam_h=CAM_H)
        self.hud = HUD(SCREEN_W, SCREEN_H, WEAPON_ICONS)
        self.game_over_screen = GameOverScreen(SCREEN_W, SCREEN_H)

        set_progress(1.0, "Ready!")
        self._game_ready = True

    def _finish_loading(self):
        """Gọi từ main thread sau khi loading xong để chuyển state"""
        self.story_screen = StoryScreen(SCREEN_W, SCREEN_H)
        self.state = 'story'

    def _finish_story(self):
        """Chuyển từ story sang checking_weapon"""
        self.loading_screen.stop_music()

        def _ws_factory(player_pos, effect_manager):
            return WeaponSystem(
                player_pos=player_pos,
                effect_manager=effect_manager,
                sound_manager=self.sound,
                sprites=self.projectile_sprites
            )

        def _player_factory():
            return Player(SCREEN_W // 2, FLOOR_Y)

        self.checking_weapon = CheckingWeaponScreen(
            screen_w  = SCREEN_W,
            screen_h  = SCREEN_H,
            weapon_icons = WEAPON_ICONS,
            bg_base   = self.bg_base,
            star1     = self.star1,
            star2     = self.star2,
            draw_bg_fn = draw_parallax_bg,
            weapon_sys_factory = _ws_factory,
            weapon_rend = self.weapon_rend,
            effect_manager_class = EffectManager,
            player_factory = _player_factory,
            gesture   = self.gesture,
            unlocked_weapons = self.unlocked_weapons,
        )
        self.state = 'checking_weapon'

    def _finish_checking(self):
        """Chuyển từ checking_weapon sang playing"""
        self.enemy_mgr.spawn_wave()
        self.hud.show_wave_banner(self.enemy_mgr.wave)
        self.sound.play_bgm()
        self.state = 'playing'
        # Tao chuong ngai vat ngau nhien tren san
        self._spawn_obstacles()
        # Ket noi obstacle_ref cho mine
        if self.weapon_sys:
            self.weapon_sys._obstacle_ref = self.obstacles
        # Khoi tao SPACE console
        self.console = SpaceConsole(SCREEN_W, SCREEN_H)

    # ── Xử lý sự kiện ────────────────────────────────────────────────────
    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if self.state in ('checking_weapon',):
                        self._finish_checking()
                        return True
                    # Dong console neu dang mo
                    if self.console and self.console.open:
                        self.console.open = False
                        return True
                    return False
                if event.key == pygame.K_F11:
                    pygame.display.toggle_fullscreen()
                if event.key == pygame.K_r and self.state == 'game_over':
                    self.restart()

                # SPACE mo/dong console khi dang choi
                if self.state == 'playing' and event.key == pygame.K_SPACE:
                    if self.console:
                        self.console.toggle()

                # Phím tắt vũ khí (debug, chỉ khi đang chơi)
                if self.state == 'playing':
                    if event.key == pygame.K_1: self._equip('iron_gauntlets')
                    if event.key == pygame.K_2: self._equip('sword')
                    if event.key == pygame.K_3: self._equip('bow')
                    if event.key == pygame.K_4: self._equip('grenade')
                    if event.key == pygame.K_5: self._equip('gun')
                    if event.key == pygame.K_6: self._equip('mine')

            # Console nhan phim
            if self.state == 'playing' and self.console and self.console.open:
                cmd = self.console.handle_event(event)
                if cmd is not None:
                    self._handle_console_cmd(cmd)

            # Delegate event cho story screen
            if self.state == 'story' and hasattr(self, 'story_screen'):
                self.story_screen.handle_event(event)

            # Delegate event cho checking_weapon screen
            if self.state == 'checking_weapon' and self.checking_weapon:
                if self.checking_weapon.handle_event(event):
                    self._finish_checking()
        return True

    def _handle_console_cmd(self, cmd):
        """Xu ly lenh tu SPACE console"""
        cmd_lower = cmd.strip().lower()
        if cmd_lower == 'helpme':
            if self.companion and self.companion.alive:
                self.console.show_result('HelpMe is already here!')
            else:
                # Spawn companion canh player
                px, py = self.player.get_pos()
                sx = px + random.choice([-80, 80])
                sx = max(60, min(SCREEN_W - 60, sx))
                self.companion = Companion(
                    x=sx, y=py,
                    projectile_sprites=self.projectile_sprites,
                    effect_manager=self.em,
                    sound_manager=self.sound
                )
                self.console.show_result('HelpMe has arrived!')
        elif cmd_lower == 'auto':
            self.auto_mode = not self.auto_mode
            msg = 'Auto mode: ON' if self.auto_mode else 'Auto mode: OFF'
            self.console.show_result(msg)
        elif cmd_lower == 'obstacles':
            self._spawn_obstacles()
            self.console.show_result('Obstacles refreshed!')
        elif cmd_lower == 'unlock':
            for w in self._ALL_WEAPONS:
                if w not in self.unlocked_weapons:
                    self.unlocked_weapons.append(w)
            self.console.show_result('All weapons unlocked!')
        elif cmd_lower in ('help', '?'):
            self.console.show_result('Commands: HelpMe | Auto | obstacles | unlock')
        else:
            self.console.show_result(f'Unknown command: {cmd}')

    # ── Bo tri tuong theo tung wave ────────────────────────────────────
    def _spawn_obstacles(self):
        """Tao chuong ngai vat: wave 1 co dinh, wave 2+ ngau nhien 2-4 tuong"""
        self.obstacles = []
        wave = getattr(self.enemy_mgr, 'wave', 1) if self.enemy_mgr else 1

        if wave == 1:
            # Wave 1: 2 tường cố định
            for bx in (400, 1520):
                ox = bx + random.randint(-20, 20)
                ox = max(100, min(SCREEN_W - 100, ox))
                self.obstacles.append(Obstacle(ox, FLOOR_Y))
        else:
            # Wave 2+: sinh ngẫu nhiên 2-4 tường
            n_walls = random.randint(2, 4)
            # Chia màn hình thành vùng, tránh chồng lấn
            margin = 150         # cách mép trái/phải
            min_gap = 200        # khoảng cách tối thiểu giữa 2 tường
            usable = SCREEN_W - 2 * margin
            positions = []
            attempts = 0
            while len(positions) < n_walls and attempts < 50:
                x = random.randint(margin, SCREEN_W - margin)
                # Kiểm tra khoảng cách với các tường đã đặt
                ok = all(abs(x - px) >= min_gap for px in positions)
                if ok:
                    positions.append(x)
                attempts += 1
            for ox in positions:
                self.obstacles.append(Obstacle(ox, FLOOR_Y))

    def _equip(self, weapon):
        if weapon not in self.unlocked_weapons:
            return
        if weapon != self.player.current_weapon:
            self.player.current_weapon = weapon
            self.weapon_sys.equip(weapon)
            # Dong bo vu khi vao gesture detector de nhan dien tan cong
            if self.gesture:
                self.gesture.current_weapon = weapon

    def _unlock_weapons_for_wave(self, wave):
        """Mo khoa 2 vu khi moi wave: W1=gauntlets+sword, W2=bow+grenade, W3=gun+mine"""
        # Tinh so vu khi duoc mo = wave * 2, toi da 6
        n_unlock = min(wave * 2, len(self._ALL_WEAPONS))
        new_weapons = []
        for w in self._ALL_WEAPONS[:n_unlock]:
            if w not in self.unlocked_weapons:
                self.unlocked_weapons.append(w)
                new_weapons.append(w)
        # Hien thi thong bao mo khoa
        if new_weapons:
            weapon_names = {
                'iron_gauntlets': 'Iron Gauntlets',
                'sword': 'Sword',
                'bow': 'Bow',
                'grenade': 'Grenade',
                'gun': 'Gun',
                'mine': 'Mine',
            }
            names = ' + '.join(weapon_names.get(w, w) for w in new_weapons)
            self.hud.show_wave_banner(
                self.enemy_mgr.wave,
                extra_text=f"UNLOCKED: {names}"
            )

    def _auto_attack(self):
        """Tu dong tan cong quai vat gan nhat bang vu khi hien tai"""
        if self.weapon_sys.cooldown_timer > 0:
            return
        if self.weapon_sys.state == 'summon':
            return

        px, py = self.player.get_pos()
        enemies = self.enemy_mgr.get_all_alive()
        if not enemies:
            return

        w = self.player.current_weapon

        # Tim enemy gan nhat
        nearest = min(enemies, key=lambda e: math.dist((px, py), (e.x, e.y)))
        nx, ny = nearest.x, nearest.y

        attack_map = {
            'iron_gauntlets': 'punch_right',
            'sword':          'slash_right',
            'bow':            'release_arrow',
            'grenade':        'throw_grenade',
            'gun':            'shoot',
            'mine':           'place_mine',
        }
        attack_type = attack_map.get(w)
        if not attack_type:
            return

        # Tinh huong den enemy gan nhat
        dx = nx - px
        dy = ny - py
        dist = max(1, math.sqrt(dx * dx + dy * dy))

        # Sword: xac dinh huong chem
        if w == 'sword':
            ang = math.degrees(math.atan2(-dy, dx))
            if -60 < ang < 60:
                attack_type = 'slash_right'
            elif 120 < ang or ang < -120:
                attack_type = 'slash_left'
            elif ang > 60:
                attack_type = 'slash_up'
            else:
                attack_type = 'slash_down'

        # Bow: huong va luc
        bow_dir = (dx / dist, dy / dist)
        bow_force = 0.8

        # Grenade: goc nem
        throw_angle = math.atan2(-dy, dx)

        # Mine: dat tai vi tri player
        mine_pos = (px, py)

        self.weapon_sys.attack(
            attack_type, (px, py), enemies,
            bow_draw_level=0.8,
            bow_direction=bow_dir,
            bow_force=bow_force,
            throw_angle=throw_angle,
            mine_pos=mine_pos,
        )
        self.weapon_rend.notify_attack(attack_type)

    def restart(self):
        self.player = Player(SCREEN_W // 2, FLOOR_Y)
        self.enemy_mgr = EnemyManager(SCREEN_W, SCREEN_H)
        self.em = EffectManager()
        self.weapon_sys = WeaponSystem(
            player_pos=lambda: self.player.get_pos(),
            effect_manager=self.em,
            sound_manager=self.sound,
            sprites=self.projectile_sprites
        )
        self.game_over_screen.timer = 0
        self.state = 'playing'
        self.t = 0
        self.wave_transition_timer = 0
        self.unlocked_weapons = ['iron_gauntlets', 'sword']
        self.enemy_mgr.spawn_wave()
        self.hud.show_wave_banner(self.enemy_mgr.wave)
        self._hands = []
        self.companion = None
        self._spawn_obstacles()
        self.weapon_sys._obstacle_ref = self.obstacles  # cap nhat sau spawn
        self.auto_mode = False
        if self.console:
            self.console.open = False

    # ── Xử lý gesture ────────────────────────────────────────────────────
    def process_gesture(self, g_result):
        weapon        = g_result.get('weapon')
        weapon_changed= g_result.get('weapon_changed', False)
        attack        = g_result.get('attack')
        bow_draw      = g_result.get('bow_draw_level', 0.0)
        bow_hand      = g_result.get('bow_hand_pos')
        string_hand   = g_result.get('string_hand_pos')
        gun_firing    = g_result.get('gun_firing', False)
        gun_tips_center = g_result.get('gun_tips_center', None)
        hands         = g_result.get('hands', [])
        bow_direction = g_result.get('bow_direction', None)
        bow_force     = g_result.get('bow_force', 0.0)
        throw_angle   = g_result.get('grenade_throw_angle', None)
        mine_pos      = g_result.get('mine_pos', None)

        # Vu khi duoc chon bang phim 1-6, khong tu dong doi qua gesture

        if attack and self.player.current_weapon:
            px, py = self.player.get_pos()
            # Scale toa do tay tu camera -> man hinh
            hands_screen_pts = []
            punch_hand_pt = None
            for h in hands:
                hx = int(h.pts[9][0] * SCREEN_W / CAM_W)
                hy = int(h.pts[9][1] * SCREEN_H / CAM_H)
                hands_screen_pts.append((hx, hy))
                # Xac dinh tay dam: punch_right -> label Right, punch_left -> label Left
                if attack in ('punch_right', 'punch_left'):
                    expected_label = 'Right' if attack == 'punch_right' else 'Left'
                    if h.label == expected_label:
                        punch_hand_pt = (hx, hy)
            # Scale mine_pos tu camera -> man hinh
            mine_screen = None
            if mine_pos is not None:
                mine_screen = (
                    int(mine_pos[0] * SCREEN_W / CAM_W),
                    int(mine_pos[1] * SCREEN_H / CAM_H)
                )
            self.weapon_sys.attack(
                attack, (px, py),
                self.enemy_mgr.get_all_alive(),
                bow_draw_level=bow_draw,
                bow_hand=bow_hand,
                string_hand=string_hand,
                throw_angle=throw_angle,
                hands_screen=hands_screen_pts if hands_screen_pts else None,
                bow_direction=bow_direction,
                bow_force=bow_force,
                mine_pos=mine_screen,
                punch_hand_pt=punch_hand_pt,
            )
            self.weapon_rend.notify_attack(attack)

        # ── Di chuyển nhân vật theo hướng chung bàn tay trái ──────────
        # Luôn cập nhật liên tục khi nhận diện tay trái
        # SKIP khi đang cầm iron_gauntlets hoặc bow (2 tay bận chiến đấu)
        _cur_wpn = self.player.current_weapon if self.player else None
        if (self.state == 'playing' and self.player and self.player.alive):
            HAND_SPEED = 7
            for h in hands:
                # SAU FIX TAY: label 'Right' (MediaPipe) = tay TRAI that cua nguoi dung
                if h.label == 'Right':
                    wx, wy = h.pts[0]
                    # Tâm bàn tay = trung bình 4 MCP khớp gốc ngón
                    mcp_pts = [h.pts[i] for i in (5, 9, 13, 17)]
                    mcx = sum(p[0] for p in mcp_pts) // 4
                    mcy = sum(p[1] for p in mcp_pts) // 4
                    dx = mcx - wx
                    dy = mcy - wy
                    dist_vec = math.sqrt(dx*dx + dy*dy)
                    # Không có dead zone — luôn di chuyển theo hướng tay
                    if dist_vec > 1:
                        nx = dx / dist_vec
                        ny = dy / dist_vec
                        # Tốc độ tỉ lệ nhẹ: xa hơn = nhanh hơn, tối đa 2x
                        speed = HAND_SPEED * min(2.0, max(0.5, dist_vec / 50))
                        self.player.x = max(30, min(SCREEN_W - 30,
                                                    self.player.x + nx * speed))
                        self.player.y = max(200, min(FLOOR_Y,
                                                     self.player.y + ny * speed))
                    break

        return bow_draw, bow_hand, string_hand, gun_firing, hands, gun_tips_center

    # ── Update ───────────────────────────────────────────────────────────
    def update(self):
        if self.state != 'playing':
            return

        self.t += 1
        scroll_x[0] += 0.4
        scroll_x[1] += 1.0

        self.player.update()

        px, py = self.player.get_pos()

        # Obstacles: day player ra khi va cham
        for obs in self.obstacles:
            new_x, new_y = obs.push_out(self.player.x, self.player.y, 40)
            self.player.x = new_x
            self.player.y = new_y

        self.enemy_mgr.update(px, py, obstacles=self.obstacles)

        # Day enemy ra khi va cham chuong ngai vat (Ghost xuyên qua)
        for e in self.enemy_mgr.enemies:
            if not e.alive:
                continue
            if getattr(e, 'enemy_type', '') == 'ghost':
                continue
            for obs in self.obstacles:
                new_ex, new_ey = obs.push_out(e.x, e.y, 50)
                e.x, e.y = new_ex, new_ey

        # Cap nhat companion
        if self.companion and self.companion.alive:
            self.companion.update(
                self.enemy_mgr.get_all_alive(),
                self.obstacles,
                SCREEN_W, SCREEN_H,
                player_x=px, player_y=py,
                projectiles=self.enemy_mgr.alien_projectiles
            )
        elif self.companion and not self.companion.alive:
            self.companion = None

        dmg = self.enemy_mgr.check_player_hit(px, py)
        if dmg > 0:
            hit = self.player.take_damage(dmg)
            if hit:
                self.sound.play('player_hurt')
                self.em.add_damage_number(px, py - 50, dmg, (255, 80, 80))
                self.shake_timer     = 15
                self.shake_intensity = 8

        for e in self.enemy_mgr.enemies:
            if not e.alive and e.die_timer == e.DIE_DURATION - 1:
                pts = {
                    'blob_alien': 300, 'monster': 200, 'alien': 150,
                    'dragon': 250, 'ghost': 100, 'boss_alien': 350,
                    'fast_alien': 120, 'elite_hulk': 400,
                }.get(e.enemy_type, 100)
                self.player.add_score(pts)
                self.sound.play('enemy_die')
                # Them vang lua quay quanh nguoi choi
                self.fire_orbs.add_orb()

        if self.enemy_mgr.wave_clear:
            if self.wave_transition_timer == 0:
                self.wave_transition_timer = self.WAVE_TRANSITION
            self.wave_transition_timer -= 1
            if self.wave_transition_timer <= 0:
                # Mo khoa vu khi moi truoc khi spawn wave tiep
                self._unlock_weapons_for_wave(self.enemy_mgr.wave + 1)
                self.enemy_mgr.spawn_wave()
                self.hud.show_wave_banner(self.enemy_mgr.wave)
                # Hoi mau nguoi choi sau moi man
                heal_amount = 20
                self.player.heal(heal_amount)
                self.em.add_damage_number(
                    self.player.x, self.player.y - 60,
                    heal_amount, (80, 255, 80))
                self.wave_transition_timer = 0
        else:
            self.wave_transition_timer = 0

        self.em.update()

        # Cap nhat vang lua quay quanh nguoi choi
        px, py = self.player.get_pos()
        self.fire_orbs.update(px, py, self.enemy_mgr.get_all_alive())

        self.weapon_sys.update(
            self.enemy_mgr.get_all_alive(),
            SCREEN_W, SCREEN_H,
            bow_draw_level=self._bow_draw,
            bow_hand=self._bow_hand,
            string_hand=self._string_hand,
            player_pos=self.player.get_pos(),
            gun_firing=self._gun_firing
        )

        self.weapon_rend.update()

        # ── Auto attack: tu dong tan cong khi bat auto_mode ──────────────
        if self.auto_mode and self.player.current_weapon and self.player.alive:
            self._auto_attack()

        # ── Sword trail damage: enemy vao vung trail mat mau ─────────────
        if self.player.current_weapon == 'sword':
            trail = self.weapon_rend.get_slash_trail()
            if trail:
                segs = trail.get_active_segments()
                if segs:
                    for e in self.enemy_mgr.get_all_alive():
                        for (sx1, sy1, sx2, sy2, sw_seg) in segs:
                            # Kiem tra enemy co nam trong ban kinh segment
                            # Dung khoang cach diem -> doan thang
                            ex, ey = e.x, e.y
                            seg_dx = sx2 - sx1
                            seg_dy = sy2 - sy1
                            seg_len2 = seg_dx*seg_dx + seg_dy*seg_dy
                            if seg_len2 == 0:
                                continue
                            t_proj = max(0.0, min(1.0,
                                ((ex - sx1)*seg_dx + (ey - sy1)*seg_dy) / seg_len2))
                            closest_x = sx1 + t_proj * seg_dx
                            closest_y = sy1 + t_proj * seg_dy
                            dist_to_seg = math.sqrt((ex - closest_x)**2 + (ey - closest_y)**2)
                            hit_r = max(sw_seg, 30)  # ban kinh hit toi thieu 30px
                            if dist_to_seg < hit_r:
                                e.take_damage(5)  # 5 sat thuong/frame
                                break  # moi enemy chi nhan damage 1 lan/frame

        if self.shake_timer > 0:
            self.shake_timer -= 1

        if not self.player.alive:
            self.state = 'game_over'

    # ── Draw ─────────────────────────────────────────────────────────────
    def draw(self):
        target = self._render_surf

        # ── Loading screen ────────────────────────────────────────────────
        if self.state == 'loading':
            self.loading_screen.draw(target)
            self._blit_to_screen()
            return

        # ── Story screen ─────────────────────────────────────────────────
        if self.state == 'story':
            self.story_screen.draw(target)
            self._blit_to_screen()
            return

        # ── Checking weapon screen ────────────────────────────────────────
        if self.state == 'checking_weapon':
            self.checking_weapon.draw(
                target,
                camera_frame   = self.camera_frame,
                hands          = self._hands,
                bow_draw       = self._bow_draw,
                bow_hand       = self._bow_hand,
                string_hand    = self._string_hand,
                gun_firing     = self._gun_firing,
                gesture_preview   = self._gesture_preview,
                gesture_progress  = self._gesture_progress,
            )
            self._blit_to_screen()
            return

        # ── Game / Game over ──────────────────────────────────────────────
        off_x, off_y = 0, 0
        if self.shake_timer > 0:
            intensity = self.shake_intensity * (self.shake_timer / 15)
            off_x = random.randint(-int(intensity), int(intensity))
            off_y = random.randint(-int(intensity), int(intensity))

        if off_x != 0 or off_y != 0:
            shake_surf = pygame.Surface((SCREEN_W, SCREEN_H))
            draw_target = shake_surf
        else:
            draw_target = target

        draw_parallax_bg(draw_target, self.bg_base, self.star1, self.star2, self.t)

        # Ve chuong ngai vat (truoc enemy/player de bi che)
        for obs in self.obstacles:
            obs.draw(draw_target)

        self.enemy_mgr.draw(draw_target)
        self.player.draw(draw_target)
        # Ve vang lua quay quanh nguoi choi
        px_draw, py_draw = self.player.get_pos()
        self.fire_orbs.draw(draw_target, px_draw, py_draw)
        # Ve companion (neu co)
        if self.companion:
            self.companion.draw(draw_target)
        self.weapon_sys.draw(draw_target)

        self.weapon_rend.draw(
            draw_target,
            weapon     = self.player.current_weapon,
            hands      = self._hands,
            screen_w   = SCREEN_W,
            screen_h   = SCREEN_H,
            bow_draw_level = self._bow_draw,
            bow_hand   = self._bow_hand,
            string_hand= self._string_hand,
            gun_firing = self._gun_firing,
            player_pos = self.player.get_pos(),
            gun_tips_center = self._gun_tips_center,
        )

        self.em.draw(draw_target, self.font_debug)

        self.hud.draw(
            draw_target,
            self.player,
            self.weapon_sys,
            self.enemy_mgr.wave,
            camera_frame    = self.camera_frame,
            gesture_preview = self._gesture_preview,
            gesture_progress= self._gesture_progress,
            bow_draw_level  = self._bow_draw,
            mouth_open      = self._mouth_open,
            hands           = self._hands,
        )

        if getattr(self, 'show_debug', False) and hasattr(self.gesture, 'debug_info'):
            y = 80
            for k, v in self.gesture.debug_info.items():
                txt = self.font_debug.render(f'{k}: {v}', True, (100, 255, 100))
                draw_target.blit(txt, (10, y))
                y += 18

        if self.enemy_mgr.wave_clear and self.wave_transition_timer > 0:
            t_frac = self.wave_transition_timer / self.WAVE_TRANSITION
            msg = self.font_debug.render(
                'Wave cleared! Next wave incoming...', True, (200, 255, 180))
            alpha = int(255 * min(1.0, t_frac * 4))
            msg.set_alpha(alpha)
            draw_target.blit(msg, (SCREEN_W // 2 - msg.get_width() // 2,
                                   SCREEN_H // 2 - 30))

        if self.state == 'game_over':
            self.game_over_screen.draw(draw_target, self.player.score,
                                       self.enemy_mgr.wave)

        if off_x != 0 or off_y != 0:
            target.blit(shake_surf, (off_x, off_y))

        # Ve SPACE console (overlay tren cung)
        if self.console:
            self.console.draw(target)

        self._blit_to_screen()

    def _blit_to_screen(self):
        if self._needs_scale:
            scaled = pygame.transform.scale(
                self._render_surf, (self._real_w, self._real_h))
            self.screen.blit(scaled, (0, 0))
        else:
            self.screen.blit(self._render_surf, (0, 0))
        pygame.display.flip()

    # ── Main loop ────────────────────────────────────────────────────────
    def run(self):
        print("[Game] Khởi động... Phím: 1-5=vũ khí, D=debug, F11=fullscreen, ESC=thoát")

        # Bắt đầu loading trong background thread
        self.loading_screen.start(self._run_init)

        running = True
        while running:
            running = self.handle_events()
            if not running:
                break

            keys = pygame.key.get_pressed()

            # ── Loading state ────────────────────────────────────────────
            if self.state == 'loading':
                self.loading_screen.update()
                if self.loading_screen.is_done():
                    self._finish_loading()
                self.draw()
                self.clock.tick(FPS)
                continue

            # ── Story state ──────────────────────────────────────────────
            if self.state == 'story':
                self.story_screen.update()
                if self.story_screen.done:
                    self._finish_story()
                self.draw()
                self.clock.tick(FPS)
                continue

            # ── Checking weapon state ────────────────────────────────────
            if self.state == 'checking_weapon':
                cw = self.checking_weapon
                # Đọc camera + gesture cho phòng tập
                cw_g_result = {}
                if self.cap and self.cap.isOpened():
                    ret, frame = self.cap.read()
                    if ret:
                        frame = cv2.flip(frame, 1)
                        self.camera_frame = frame.copy()
                        cw_g_result = self.gesture.process(
                            frame, space_pressed=keys[pygame.K_SPACE])
                        self._hands = cw_g_result.get('hands', [])
                else:
                    self.camera_frame = None

                cw.update(
                    camera_frame   = self.camera_frame,
                    hands          = self._hands,
                    gesture_result = cw_g_result,
                    space_pressed  = keys[pygame.K_SPACE],
                )
                if cw.done:
                    self._finish_checking()
                self.draw()
                self.clock.tick(FPS)
                continue

            # ── Playing / Game over ──────────────────────────────────────
            self.show_debug    = keys[pygame.K_d]
            self._space_pressed= keys[pygame.K_SPACE]

            # ── Di chuyển nhân vật bằng phím mũi tên ────────────────────
            if self.state == 'playing' and self.player and self.player.alive:
                MOVE_SPEED = 5
                if keys[pygame.K_LEFT]:
                    self.player.x = max(30, self.player.x - MOVE_SPEED)
                if keys[pygame.K_RIGHT]:
                    self.player.x = min(SCREEN_W - 30, self.player.x + MOVE_SPEED)
                if keys[pygame.K_UP]:
                    self.player.y = max(200, self.player.y - MOVE_SPEED)
                if keys[pygame.K_DOWN]:
                    self.player.y = min(FLOOR_Y, self.player.y + MOVE_SPEED)

            g_result = {}
            if self.cap and self.cap.isOpened():
                ret, frame = self.cap.read()
                if ret:
                    frame = cv2.flip(frame, 1)
                    self.camera_frame = frame.copy()
                    if self.state == 'playing':
                        g_result = self.gesture.process(
                            frame, space_pressed=keys[pygame.K_SPACE])
                        self._gesture_preview  = g_result.get('gesture_preview')
                        self._gesture_progress = g_result.get('gesture_progress', 0.0)
                        (self._bow_draw,
                         self._bow_hand,
                         self._string_hand,
                         self._gun_firing,
                         self._hands,
                         self._gun_tips_center) = self.process_gesture(g_result)
                        self._mouth_open = g_result.get('mouth_open', False)
            else:
                self.camera_frame = None

            self.update()
            self.draw()
            self.clock.tick(FPS)

        self.cleanup()

    def cleanup(self):
        if self.cap:
            self.cap.release()
        if self.gesture:
            self.gesture.release()
        if self.sound:
            self.sound.stop_all()
        cv2.destroyAllWindows()
        pygame.quit()
