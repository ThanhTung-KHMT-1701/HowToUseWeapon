"""
hud.py - Giao diện người dùng (HUD)
Hiển thị HP, vũ khí hiện tại, điểm số, wave, camera feed
"""

import pygame
import math
import cv2
import numpy as np


class HUD:
    def __init__(self, screen_w, screen_h, weapon_icons):
        self.screen_w = screen_w
        self.screen_h = screen_h
        self.weapon_icons = weapon_icons  # dict {weapon_name: Surface}
        self.font_large = pygame.font.SysFont('Courier New', 42, bold=True)
        self.font_medium = pygame.font.SysFont('Courier New', 30, bold=True)
        self.font_normal = pygame.font.SysFont('Courier New', 24, bold=True)
        self.font_small = pygame.font.SysFont('Courier New', 20)
        self.cam_alpha = 180  # độ trong suốt của camera feed

        # Wave banner
        self.wave_banner_timer = 0
        self.wave_banner_text = ''
        self.wave_banner_extra = ''

    def show_wave_banner(self, wave_num, extra_text=''):
        self.wave_banner_text = f'WAVE {wave_num}'
        self.wave_banner_extra = extra_text
        self.wave_banner_timer = 120

    def _draw_hp_bar(self, surface, player):
        bar_x, bar_y = 20, 20
        bar_w, bar_h = 300, 28
        hp_frac = player.hp / player.max_hp

        # Background
        pygame.draw.rect(surface, (40, 0, 0), (bar_x - 2, bar_y - 2, bar_w + 4, bar_h + 4), border_radius=5)
        pygame.draw.rect(surface, (20, 20, 20), (bar_x, bar_y, bar_w, bar_h), border_radius=4)

        # HP fill với gradient màu
        if hp_frac > 0:
            fill_w = int(bar_w * hp_frac)
            r = int(255 * (1 - hp_frac))
            g = int(200 * hp_frac)
            pygame.draw.rect(surface, (r, g, 30), (bar_x, bar_y, fill_w, bar_h), border_radius=4)
            # Shine
            shine = pygame.Surface((fill_w, bar_h // 2), pygame.SRCALPHA)
            shine.fill((255, 255, 255, 40))
            surface.blit(shine, (bar_x, bar_y))

        # Viền
        pygame.draw.rect(surface, (200, 200, 200), (bar_x - 2, bar_y - 2, bar_w + 4, bar_h + 4), 1, border_radius=5)

        # Text HP
        hp_text = self.font_small.render(f'HP  {player.hp}/{player.max_hp}', True, (220, 220, 220))
        surface.blit(hp_text, (bar_x + 4, bar_y + 3))

    def _draw_weapon_panel(self, surface, player, weapon_system):
        """Panel vũ khí dưới cùng giữa màn hình"""
        weapons = ['iron_gauntlets', 'sword', 'bow', 'grenade', 'gun', 'mine']
        icons_w = 72
        total_w = icons_w * len(weapons) + 28
        panel_x = self.screen_w // 2 - total_w // 2
        panel_y = self.screen_h - 100

        # Background panel
        bg = pygame.Surface((total_w, 56), pygame.SRCALPHA)
        bg.fill((0, 0, 0, 120))
        pygame.draw.rect(bg, (80, 80, 100, 180), (0, 0, total_w, 56), 1, border_radius=8)
        surface.blit(bg, (panel_x, panel_y))

        for i, w in enumerate(weapons):
            ix = panel_x + 10 + i * icons_w
            iy = panel_y + 4
            active = (player.current_weapon == w)

            # Highlight nếu active
            if active:
                glow = pygame.Surface((48, 48), pygame.SRCALPHA)
                c = {
                    'iron_gauntlets': (180, 180, 220),
                    'sword': (150, 200, 255),
                    'bow': (50, 220, 150),
                    'grenade': (200, 120, 50),
                    'gun': (160, 160, 200),
                    'mine': (220, 80, 80),
                }.get(w, (200, 200, 200))
                pygame.draw.rect(glow, (*c, 60), (0, 0, 48, 48), border_radius=6)
                pygame.draw.rect(glow, (*c, 200), (0, 0, 48, 48), 2, border_radius=6)
                surface.blit(glow, (ix, iy))

                # Summon progress bar
                prog = weapon_system.get_summon_progress()
                if prog < 1.0:
                    pb = pygame.Surface((44, 3), pygame.SRCALPHA)
                    pygame.draw.rect(pb, (80, 80, 80, 180), (0, 0, 44, 3))
                    pygame.draw.rect(pb, (*c, 255), (0, 0, int(44 * prog), 3))
                    surface.blit(pb, (ix + 2, iy + 45))

            # Icon
            icon = self.weapon_icons[w](48)
            surface.blit(icon, (ix + 8, iy + 8))

            # Label
            short_names = {
                'iron_gauntlets': 'GLOVE',
                'sword': 'SWORD',
                'bow': 'BOW',
                'grenade': 'BOMB',
                'gun': 'GUN',
                'mine': 'MINE',
            }
            label = self.font_small.render(short_names[w], True,
                                           (220, 220, 255) if active else (120, 120, 140))
            surface.blit(label, (ix + 48 // 2 - label.get_width() // 2, panel_y + 52))

    def _draw_score_wave(self, surface, player, wave):
        # Score
        score_text = self.font_medium.render(f'SCORE  {player.score:06d}', True, (220, 220, 80))
        surface.blit(score_text, (self.screen_w - score_text.get_width() - 20, 20))
        # Wave
        wave_text = self.font_medium.render(f'WAVE  {wave}', True, (180, 180, 255))
        surface.blit(wave_text, (self.screen_w - wave_text.get_width() - 20, 46))

    def _draw_gesture_indicator(self, surface, gesture_preview, gesture_progress):
        """Hiển thị thanh tiến trình khi đang giữ cử chỉ"""
        if not gesture_preview or gesture_progress <= 0:
            return
        names = {
            'iron_gauntlets': 'Iron Gauntlets',
            'sword': 'Sword',
            'bow': 'Bow',
            'bow_ready': 'Bow ready...',
            'sword_ready': 'Sword ready...',
            'grenade_ready': 'Grenade',
            'gun': 'Gun',
            'mine': 'Mine',
        }
        label = names.get(gesture_preview, gesture_preview)
        # Vị trí: góc trên giữa
        bx = self.screen_w // 2 - 120
        by = 20
        bw, bh = 240, 32

        bg = pygame.Surface((bw + 4, bh + 4), pygame.SRCALPHA)
        bg.fill((0, 0, 0, 140))
        surface.blit(bg, (bx - 2, by - 2))

        pygame.draw.rect(surface, (40, 40, 60), (bx, by, bw, bh), border_radius=4)
        fill_c = (100, 200, 255) if gesture_progress < 1.0 else (50, 255, 150)
        pygame.draw.rect(surface, fill_c, (bx, by, int(bw * gesture_progress), bh), border_radius=4)
        pygame.draw.rect(surface, (150, 150, 200), (bx, by, bw, bh), 1, border_radius=4)

        txt = self.font_small.render(label.upper(), True, (255, 255, 255))
        surface.blit(txt, (bx + bw // 2 - txt.get_width() // 2, by + bh // 2 - txt.get_height() // 2))

    def _draw_bow_charge(self, surface, bow_draw_level, player_x, player_y):
        if bow_draw_level <= 0.05:
            return
        # Vẽ thanh charge trên đầu player
        bx = int(player_x) - 25
        by = int(player_y) - 60
        pygame.draw.rect(surface, (20, 60, 40), (bx, by, 50, 6), border_radius=3)
        c_intensity = int(50 + bow_draw_level * 200)
        pygame.draw.rect(surface, (50, c_intensity, 150), (bx, by, int(50 * bow_draw_level), 6), border_radius=3)
        txt = self.font_small.render('CHARGE', True, (100, 255, 180))
        surface.blit(txt, (bx - 5, by - 14))

    def _draw_wave_banner(self, surface):
        if self.wave_banner_timer <= 0:
            return
        self.wave_banner_timer -= 1
        t = self.wave_banner_timer / 120
        alpha = int(255 * min(1, t * 3, (1 - t) * 3))
        scale = 1.0 + 0.3 * (1 - t)
        text_surf = self.font_large.render(self.wave_banner_text, True, (255, 220, 50))
        w = int(text_surf.get_width() * scale)
        h = int(text_surf.get_height() * scale)
        scaled = pygame.transform.scale(text_surf, (w, h))
        scaled.set_alpha(alpha)
        cx = self.screen_w // 2
        cy = self.screen_h // 2
        surface.blit(scaled, (cx - w // 2, cy - h // 2))
        # Hien thi dong extra (unlock notification)
        if self.wave_banner_extra:
            ext_surf = self.font_normal.render(self.wave_banner_extra, True, (120, 255, 200))
            ext_surf.set_alpha(alpha)
            surface.blit(ext_surf, (cx - ext_surf.get_width() // 2, cy + h // 2 + 10))

    # Kết nối xương landmark MediaPipe (21 điểm)
    _HAND_CONNECTIONS = [
        (0,1),(1,2),(2,3),(3,4),
        (0,5),(5,6),(6,7),(7,8),
        (0,9),(9,10),(10,11),(11,12),
        (0,13),(13,14),(14,15),(15,16),
        (0,17),(17,18),(18,19),(19,20),
        (5,9),(9,13),(13,17),
    ]

    def _draw_landmarks_on_frame(self, frame, hands, current_weapon=None):
        """Ve 21 diem landmark + xuong ngon tay len OpenCV frame (640x480 BGR)"""
        if not hands:
            return frame
        out = frame.copy()
        for hand in hands:
            if not hasattr(hand, 'pts') or len(hand.pts) < 21:
                continue
            pts = hand.pts  # list 21 tuple (x_pixel, y_pixel) trong 640×480
            # Màu theo tay: trái=xanh lam, phải=vàng xanh
            bone_color  = (80, 200, 80)   if hand.label == 'Right' else (200, 80, 200)
            joint_color = (50, 255, 50)   if hand.label == 'Right' else (255, 50, 255)
            tip_color   = (0, 220, 255)

            # Vẽ đường xương
            for a, b in self._HAND_CONNECTIONS:
                if a < len(pts) and b < len(pts):
                    p1 = (int(pts[a][0]), int(pts[a][1]))
                    p2 = (int(pts[b][0]), int(pts[b][1]))
                    cv2.line(out, p1, p2, bone_color, 1, cv2.LINE_AA)

            # Ve diem khop
            tips = {4, 8, 12, 16, 20}
            for i, pt in enumerate(pts):
                x, y = int(pt[0]), int(pt[1])
                if i in tips:
                    cv2.circle(out, (x, y), 5, tip_color, -1, cv2.LINE_AA)
                    cv2.circle(out, (x, y), 6, (255, 255, 255), 1, cv2.LINE_AA)
                elif i == 0:
                    cv2.circle(out, (x, y), 5, (255, 255, 255), -1, cv2.LINE_AA)
                else:
                    cv2.circle(out, (x, y), 3, joint_color, -1, cv2.LINE_AA)

            # Khi cam grenade: ve huong canh tay (wrist->MCP giua, keo dai)
            # Giup nguoi dung thay huong nem se ra sao
            if current_weapon == 'grenade' and len(pts) >= 10:
                import math as _math
                wx, wy = int(pts[0][0]), int(pts[0][1])
                mx, my = int(pts[9][0]), int(pts[9][1])
                dx = mx - wx
                dy = my - wy
                dist = _math.sqrt(dx*dx + dy*dy) or 1
                # Keo dai vector wrist->MCP them 80px
                ex = int(mx + dx / dist * 80)
                ey = int(my + dy / dist * 80)
                # Nen ey >= 0 (trong frame)
                ex = max(0, min(out.shape[1]-1, ex))
                ey = max(0, min(out.shape[0]-1, ey))
                # Ve duong huong nem: vang
                cv2.arrowedLine(out, (wx, wy), (ex, ey),
                                (0, 220, 255), 3, cv2.LINE_AA, tipLength=0.25)
                # Label
                lx = min(ex + 4, out.shape[1] - 80)
                ly = max(ey - 10, 12)
                cv2.putText(out, "Throw Dir", (lx, ly),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 220, 255), 1,
                            cv2.LINE_AA)
        return out

    def _draw_camera_feed(self, surface, frame, hands=None, current_weapon=None):
        """Hiển thị camera nhỏ ở góc dưới phải, có vẽ landmark nếu cung cấp hands"""
        if frame is None:
            return
        cam_w, cam_h = 320, 240  # tỉ lệ 4:3 thu nhỏ

        # Vẽ landmark lên frame 640×480 TRƯỚC khi resize
        annotated = self._draw_landmarks_on_frame(frame, hands or [],
                                                       current_weapon=current_weapon)

        small = cv2.resize(annotated, (cam_w, cam_h))
        small = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)
        small_surf = pygame.surfarray.make_surface(small.transpose(1, 0, 2))
        small_surf.set_alpha(self.cam_alpha)
        cx = self.screen_w - cam_w - 10
        cy = self.screen_h - cam_h - 80
        # Viền
        pygame.draw.rect(surface, (60, 60, 100),
                         (cx - 2, cy - 2, cam_w + 4, cam_h + 4), border_radius=4)
        surface.blit(small_surf, (cx, cy))
        # Label
        lbl = self.font_small.render('CAMERA', True, (150, 150, 200))
        surface.blit(lbl, (cx + 2, cy + 2))

    def _draw_mouth_indicator(self, surface, mouth_open, current_weapon):
        """Hiển thị indicator bắn súng (phím SPACE)"""
        if current_weapon != 'gun':
            return
        # mouth_open tái sử dụng cho space_pressed
        color = (255, 80, 80) if mouth_open else (80, 80, 100)
        icon_x, icon_y = 340, 16
        # Vẽ hình chữ nhật SPACE
        key_w, key_h = 96, 32
        pygame.draw.rect(surface, color,
                         (icon_x, icon_y, key_w, key_h), border_radius=4)
        pygame.draw.rect(surface, (200, 200, 220),
                         (icon_x, icon_y, key_w, key_h), 1, border_radius=4)
        lbl = self.font_small.render('SPACE = FIRE', True,
                                     (20, 20, 20) if mouth_open else (180, 180, 200))
        surface.blit(lbl, (icon_x + key_w // 2 - lbl.get_width() // 2,
                           icon_y + key_h // 2 - lbl.get_height() // 2))

    def draw(self, surface, player, weapon_system, wave, camera_frame=None,
             gesture_preview=None, gesture_progress=0.0,
             bow_draw_level=0.0, mouth_open=False, hands=None):
        self._draw_hp_bar(surface, player)
        self._draw_weapon_panel(surface, player, weapon_system)
        self._draw_score_wave(surface, player, wave)
        self._draw_gesture_indicator(surface, gesture_preview, gesture_progress)
        self._draw_wave_banner(surface)
        if bow_draw_level > 0:
            self._draw_bow_charge(surface, bow_draw_level, player.x, player.y)
        self._draw_mouth_indicator(surface, mouth_open, player.current_weapon)
        if camera_frame is not None:
            self._draw_camera_feed(surface, camera_frame, hands=hands,
                                   current_weapon=player.current_weapon)


class GameOverScreen:
    def __init__(self, screen_w, screen_h):
        self.screen_w = screen_w
        self.screen_h = screen_h
        self.font_big = pygame.font.SysFont('Courier New', 60, bold=True)
        self.font_med = pygame.font.SysFont('Courier New', 28, bold=True)
        self.font_small = pygame.font.SysFont('Courier New', 18)
        self.timer = 0

    def draw(self, surface, score, wave, win=False):
        self.timer += 1
        overlay = pygame.Surface((self.screen_w, self.screen_h), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, min(200, self.timer * 3)))
        surface.blit(overlay, (0, 0))

        alpha = min(255, self.timer * 5)
        title = 'VICTORY!' if win else 'GAME OVER'
        color = (50, 255, 150) if win else (255, 60, 60)
        t = self.font_big.render(title, True, color)
        t.set_alpha(alpha)
        surface.blit(t, (self.screen_w // 2 - t.get_width() // 2, self.screen_h // 2 - 80))

        s = self.font_med.render(f'Score: {score:06d}  |  Wave: {wave}', True, (220, 220, 80))
        s.set_alpha(alpha)
        surface.blit(s, (self.screen_w // 2 - s.get_width() // 2, self.screen_h // 2))

        hint = self.font_small.render('Press R to restart  |  ESC to quit', True, (160, 160, 180))
        hint.set_alpha(alpha)
        surface.blit(hint, (self.screen_w // 2 - hint.get_width() // 2, self.screen_h // 2 + 50))
