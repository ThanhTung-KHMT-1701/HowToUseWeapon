"""
loading_screen.py - Màn hình loading hiển thị thông tin sinh viên
Hiển thị trong khi game khởi tạo (load model, camera, assets)
"""

import pygame
import math
import os
import threading


# ── Thông tin sinh viên ──────────────────────────────────────────────────────
STUDENT_INFO = [
    ("University",  "Dai Nam University"),
    ("Faculty",     "Faculty of Information Technology"),
    ("Student ID",  "1771040029"),
    ("Full Name",   "Luu Thanh Tung"),
    ("Course",      "Computer Vision"),
]


def _make_space_bg(w, h):
    """Tạo nền không gian tĩnh cho loading screen"""
    import numpy as np
    surf = pygame.Surface((w, h))
    surf.fill((4, 6, 22))

    rng = np.random.default_rng(42)
    for _ in range(300):
        x = rng.integers(0, w)
        y = rng.integers(0, h)
        b = rng.integers(100, 255)
        r = int(b * rng.uniform(0.7, 1.0))
        g = int(b * rng.uniform(0.7, 1.0))
        size = rng.choice([1, 1, 1, 2])
        if size == 1:
            surf.set_at((x, y), (r, g, b))
        else:
            pygame.draw.circle(surf, (r, g, b), (x, y), 2)

    for i in range(200):
        x = rng.integers(0, w)
        y = rng.integers(h // 4, h * 3 // 4)
        a = rng.integers(20, 60)
        glow = pygame.Surface((4, 4), pygame.SRCALPHA)
        glow.fill((60, 60, 120, a))
        surf.blit(glow, (x - 2, y - 2))

    return surf


def _render_fit(font_list, text, color, max_w):
    """
    Thử render text từ font lớn → nhỏ cho đến khi vừa max_w.
    font_list: list[pygame.font.Font] sắp xếp từ lớn đến nhỏ.
    Trả về Surface đã render.
    """
    for f in font_list:
        s = f.render(text, True, color)
        if s.get_width() <= max_w:
            return s
    # Nếu vẫn quá rộng, dùng font nhỏ nhất và chấp nhận
    return font_list[-1].render(text, True, color)


class LoadingScreen:
    """
    Màn hình loading với thông tin sinh viên, progress bar và nhạc nền.
    Dùng background thread để chạy hàm init thực sự, và cập nhật progress.
    """

    def __init__(self, screen_w, screen_h):
        self.screen_w = screen_w
        self.screen_h = screen_h

        # Fonts — title
        self.font_title   = pygame.font.SysFont('Arial', 52, bold=True)
        self.font_subtitle = pygame.font.SysFont('Arial', 18)

        # Fonts — card header
        self.font_hdr     = pygame.font.SysFont('Arial', 22, bold=True)

        # Fonts cho label cột trái (cố định)
        self.font_label   = pygame.font.SysFont('Arial', 22, bold=True)

        # Fonts cho value — từ lớn đến nhỏ để auto-fit
        self.font_val_list = [
            pygame.font.SysFont('Arial', 26, bold=True),
            pygame.font.SysFont('Arial', 22, bold=True),
            pygame.font.SysFont('Arial', 19, bold=True),
            pygame.font.SysFont('Arial', 16, bold=True),
        ]

        self.font_step    = pygame.font.SysFont('Courier New', 20)
        self.font_hint    = pygame.font.SysFont('Arial', 18)

        # Background
        self.bg = _make_space_bg(screen_w, screen_h)

        # Trạng thái
        self.progress       = 0.0
        self.current_step   = ""
        self.done           = False
        self._t             = 0
        self._info_alpha    = [0] * len(STUDENT_INFO)

        # Âm nhạc — hỗ trợ nhiều định dạng, thử load lần lượt theo thứ tự
        # (pygame.mixer có thể không hỗ trợ webm/mp4 trên mọt số hệ điều hành)
        self._music_started = False
        _assets_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets')
        _MUSIC_EXTS = ['.ogg', '.mp3', '.wav', '.webm', '.mp4']
        # Thu collect tat ca file ton tai theo thu tu uu tien
        self._music_candidates = []
        for _ext in _MUSIC_EXTS:
            _candidate = os.path.join(_assets_dir, f'loading_music{_ext}')
            if os.path.exists(_candidate):
                self._music_candidates.append(_candidate)
        # _music_path se duoc xac dinh khi thu load lan luot trong update()
        self._music_path = None

        # Thread
        self._thread = None
        self._lock   = threading.Lock()

    # ── Khởi chạy init thread ────────────────────────────────────────────────
    def start(self, init_fn):
        def runner():
            init_fn(self._set_progress)
            with self._lock:
                self.done = True

        self._thread = threading.Thread(target=runner, daemon=True)
        self._thread.start()

    def _set_progress(self, frac: float, step_text: str = ""):
        with self._lock:
            self.progress     = min(1.0, max(0.0, frac))
            self.current_step = step_text

    def is_done(self):
        with self._lock:
            return self.done

    # ── Cập nhật mỗi frame ──────────────────────────────────────────────────
    def update(self):
        self._t += 1

        if not self._music_started and self._music_candidates:
            for _candidate in self._music_candidates:
                try:
                    pygame.mixer.music.load(_candidate)
                    pygame.mixer.music.set_volume(0.55)
                    pygame.mixer.music.play(-1)
                    self._music_path = _candidate   # luu lai file da load thanh cong
                    self._music_started = True
                    break  # load thanh cong, dung thu tiep
                except Exception:
                    continue  # format khong ho tro, thu file tiep theo
            if not self._music_started:
                self._music_started = True  # danh dau da thu het, khong thu lai

        for i in range(len(STUDENT_INFO)):
            target_start = 30 + i * 40
            if self._t >= target_start:
                self._info_alpha[i] = min(255, self._info_alpha[i] + 8)

    # ── Vẽ ──────────────────────────────────────────────────────────────────
    def draw(self, surface):
        surface.blit(self.bg, (0, 0))

        cx = self.screen_w // 2
        t  = self._t

        # ── Logo ──────────────────────────────────────────────────────────────
        glow_pulse = int(200 + 55 * math.sin(t * 0.06))
        title1 = self.font_title.render("VibeGaming", True, (glow_pulse, 180, 255))
        shadow  = self.font_title.render("VibeGaming", True, (20, 20, 80))
        surface.blit(shadow, (cx - title1.get_width() // 2 + 3, 53))
        surface.blit(title1, (cx - title1.get_width() // 2, 50))

        sub = self.font_subtitle.render(
            "Gesture Combat — Powered by MediaPipe", True, (120, 140, 200))
        surface.blit(sub, (cx - sub.get_width() // 2, 112))

        # ── Card thông tin sinh viên ──────────────────────────────────────────
        # card_w đủ rộng để chứa text dài nhất
        # layout: padding_left(20) + label_col(180) + gap(16) + value_col(max) + padding_right(20)
        LABEL_COL   = 180   # px — cột nhãn
        VALUE_COL   = 340   # px — cột giá trị (đủ chứa "Faculty of Information Technology" ở font 19)
        PAD         = 24
        card_w      = PAD + LABEL_COL + 16 + VALUE_COL + PAD   # = 604 px
        ROW_H       = 44
        HEADER_H    = 50
        card_h      = HEADER_H + len(STUDENT_INFO) * ROW_H + 16

        card_x = cx - card_w // 2
        card_y = self.screen_h // 2 - card_h // 2 - 50

        # Vẽ card
        card_surf = pygame.Surface((card_w, card_h), pygame.SRCALPHA)
        card_surf.fill((10, 14, 50, 210))
        pygame.draw.rect(card_surf, (60, 80, 180, 140),
                         (0, 0, card_w, card_h), border_radius=16)
        pygame.draw.rect(card_surf, (80, 120, 255, 200),
                         (0, 0, card_w, card_h), 2, border_radius=16)
        surface.blit(card_surf, (card_x, card_y))

        # Header
        hdr = self.font_hdr.render("STUDENT INFORMATION", True, (160, 180, 255))
        surface.blit(hdr, (cx - hdr.get_width() // 2, card_y + 14))
        pygame.draw.line(surface, (60, 80, 160),
                         (card_x + 16, card_y + HEADER_H - 4),
                         (card_x + card_w - 16, card_y + HEADER_H - 4), 1)

        # Các dòng thông tin
        val_max_w = VALUE_COL  # chiều rộng tối đa cho value text
        for i, (label_txt, value_txt) in enumerate(STUDENT_INFO):
            alpha = self._info_alpha[i]
            if alpha <= 0:
                continue

            row_y = card_y + HEADER_H + i * ROW_H + 6

            # Label (cố định font)
            lbl_surf = self.font_label.render(f"{label_txt}:", True, (140, 160, 220))
            lbl_surf.set_alpha(alpha)
            surface.blit(lbl_surf, (card_x + PAD, row_y))

            # Value — auto-fit font
            if label_txt == "Full Name":
                val_color = (255, 220, 80)
            elif label_txt == "Student ID":
                val_color = (100, 230, 180)
            else:
                val_color = (220, 230, 255)

            val_surf = _render_fit(self.font_val_list, value_txt, val_color, val_max_w)
            val_surf.set_alpha(alpha)
            val_x = card_x + PAD + LABEL_COL + 16
            # căn giữa theo chiều dọc so với label
            val_y = row_y + (self.font_label.get_height() - val_surf.get_height()) // 2
            surface.blit(val_surf, (val_x, val_y))

        # ── Progress bar ──────────────────────────────────────────────────────
        bar_y = card_y + card_h + 24
        bar_w = card_w
        bar_h = 18
        bar_x = card_x

        pygame.draw.rect(surface, (20, 24, 60), (bar_x, bar_y, bar_w, bar_h), border_radius=9)
        pygame.draw.rect(surface, (40, 50, 100), (bar_x, bar_y, bar_w, bar_h), 1, border_radius=9)

        fill_w = int(bar_w * self.progress)
        if fill_w > 4:
            fill_surf = pygame.Surface((fill_w, bar_h), pygame.SRCALPHA)
            for px_i in range(fill_w):
                frac = px_i / max(1, fill_w - 1)
                r = int(60  + frac * (180 - 60))
                g = int(200 + frac * (80  - 200))
                b = int(255 + frac * (200 - 255))
                pygame.draw.line(fill_surf, (r, g, b, 255), (px_i, 0), (px_i, bar_h))
            mask = pygame.Surface((fill_w, bar_h), pygame.SRCALPHA)
            pygame.draw.rect(mask, (255, 255, 255, 255), (0, 0, fill_w, bar_h), border_radius=9)
            fill_surf.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
            surface.blit(fill_surf, (bar_x, bar_y))
            shine = pygame.Surface((fill_w, bar_h // 2), pygame.SRCALPHA)
            shine.fill((255, 255, 255, 35))
            surface.blit(shine, (bar_x, bar_y))

        pct_txt = self.font_hint.render(f"{int(self.progress * 100)}%", True, (180, 200, 255))
        surface.blit(pct_txt, (bar_x + bar_w + 12, bar_y - 1))

        # ── Bước hiện tại ─────────────────────────────────────────────────────
        step_y = bar_y + bar_h + 12
        step_surf = self.font_step.render(self.current_step, True, (100, 180, 120))
        surface.blit(step_surf, (bar_x, step_y))

        # ── Dấu chấm nhấp nháy ────────────────────────────────────────────────
        if self.progress < 1.0:
            for i in range(3):
                blink = int(128 + 127 * math.sin(t * 0.1 - i * 1.2))
                dx = cx - 20 + i * 20
                dy = self.screen_h - 40
                pygame.draw.circle(surface, (80, 120, blink), (dx, dy), 5)

        if self.progress >= 1.0:
            hint = self.font_hint.render(
                "Loading complete — starting game...", True, (80, 220, 120))
            surface.blit(hint, (cx - hint.get_width() // 2, step_y + 28))

    # ── Kết thúc nhạc ────────────────────────────────────────────────────────
    def stop_music(self):
        try:
            pygame.mixer.music.fadeout(800)
        except Exception:
            pass
