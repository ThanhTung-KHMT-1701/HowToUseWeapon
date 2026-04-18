"""
weapon_renderer.py - Vẽ vũ khí trực tiếp tại vị trí tay thật trên màn hình

Luồng dữ liệu:
  MediaPipe HandData (tọa độ pixel camera 640×480)
  → hand_to_screen()  (scale sang tọa độ màn hình game)
  → draw_weapon_on_hands()  (vẽ vũ khí tại đúng vị trí)

Mỗi vũ khí có cách vẽ riêng:
  iron_gauntlets : găng thép vẽ bao quanh mỗi nắm đấm
  sword          : lưỡi kiếm dài từ nắm tay, xoay theo hướng vung
  bow            : cung tại tay cầm + dây cung nối tay kéo
  grenade        : lựu đạn vẽ tại lòng bàn tay nắm
  gun            : súng vẽ dọc theo ngón trỏ
"""

import pygame
import math
import numpy as np
from src.effects import SlashTrail


# ─── Chuyển tọa độ tay (camera) → màn hình game ──────────────────────────
def hand_to_screen(hand_pts, cam_w: int, cam_h: int,
                   screen_w: int, screen_h: int) -> list[tuple[int, int]]:
    """
    hand_pts : list[(px, py)] — tọa độ pixel trong camera frame
    Trả về  : list[(sx, sy)] — tọa độ pixel trên màn hình game

    Camera feed chiếm phần giữa-dưới màn hình (không scale 1-1).
    Ta map toàn bộ camera → toàn bộ màn hình để landmark trải rộng.
    """
    sx = screen_w / cam_w
    sy = screen_h / cam_h
    return [(int(px * sx), int(py * sy)) for (px, py) in hand_pts]


def hand_center_screen(hand, cam_w, cam_h, screen_w, screen_h):
    """Tâm bàn tay (wrist + MCP trung bình) trong tọa độ màn hình"""
    # Dùng wrist (0) + MCP ngón giữa (9) để tính tâm ổn định
    pts = hand.pts   # tọa độ pixel camera
    wrist = pts[0]
    mcp   = pts[9]
    cx = (wrist[0] + mcp[0]) // 2
    cy = (wrist[1] + mcp[1]) // 2
    sx = screen_w / cam_w
    sy = screen_h / cam_h
    return (int(cx * sx), int(cy * sy))


def pt_to_screen(pt, cam_w, cam_h, screen_w, screen_h):
    sx = screen_w / cam_w
    sy = screen_h / cam_h
    return (int(pt[0] * sx), int(pt[1] * sy))


# ─── Vẽ từng vũ khí ──────────────────────────────────────────────────────

def _draw_iron_gauntlets(surface, hands, cam_w, cam_h, sw, sh,
                         attack_anim: float = 0.0):
    """
    Ve gang thep bao quanh tung nam tay.
    attack_anim: 0.0->1.0 — chuyen mau xam -> cam khi dam
    """
    for hand in hands:
        center = hand_center_screen(hand, cam_w, cam_h, sw, sh)
        cx, cy = center

        wrist_s = pt_to_screen(hand.pts[0], cam_w, cam_h, sw, sh)
        mcp_s   = pt_to_screen(hand.pts[9], cam_w, cam_h, sw, sh)
        r = 40  # kich thuoc co dinh, khong phu thuoc khoang cach tay-camera

        rect_w, rect_h = int(r * 1.8), int(r * 1.4)
        bx, by = cx - rect_w // 2, cy - rect_h // 2

        flash = min(1.0, attack_anim)

        # Mau xam khi binh thuong, chuyen sang cam khi dam
        # base: (140,140,160) -> (255,140,30)
        base_col  = (int(140 + 115 * flash), int(140 - 40 * flash),
                     int(160 - 130 * flash))
        shine_col = (int(200 + 55 * flash), int(180 - 80 * flash),
                     int(160 - 130 * flash))
        edge_col  = (int(80  + 120 * flash), int(80  - 30 * flash),
                     int(100 - 80 * flash))

        gauntlet_surf = pygame.Surface((rect_w + 8, rect_h + 8), pygame.SRCALPHA)
        alpha = int(210 + 45 * flash)
        pygame.draw.rect(gauntlet_surf, (*base_col, alpha),
                         (4, 4, rect_w, rect_h), border_radius=8)
        pygame.draw.rect(gauntlet_surf, (*shine_col, 160),
                         (6, 4, rect_w - 4, rect_h // 3), border_radius=6)
        pygame.draw.rect(gauntlet_surf, (*edge_col, 255),
                         (4, 4, rect_w, rect_h), width=2, border_radius=8)

        # Khi dang dam (flash > 0.3): ve vong soc kwave nho quanh gang
        if flash > 0.3:
            glow_surf = pygame.Surface((sw, sh), pygame.SRCALPHA)
            glow_r = r + int(30 * flash)
            glow_a = int(160 * flash)
            pygame.draw.circle(glow_surf, (255, 140, 30, glow_a),
                                (cx, cy), glow_r, 4)
            surface.blit(glow_surf, (0, 0))

        # Khop ngon tay
        knuckle_y = 4
        for ki in range(3):
            kx = 4 + int(rect_w * (ki + 1) / 4)
            pygame.draw.rect(gauntlet_surf, (*shine_col, 180),
                             (kx - 2, knuckle_y, 4, rect_h // 2), border_radius=2)

        surface.blit(gauntlet_surf, (bx - 4, by - 4))


def _draw_sword(surface, hands, cam_w, cam_h, sw, sh,
                slash_angle: float = None, slash_anim: float = 0.0):
    """
    Vẽ lưỡi kiếm dài từ nắm tay.
    slash_angle : góc hướng vung (degrees). None = tính từ hướng bàn tay.
    slash_anim  : 0→1, hiệu ứng glow khi chém
    """
    if not hands:
        return

    # Dùng tay đang di chuyển (hoặc tay đầu tiên)
    hand = hands[0]
    center = hand_center_screen(hand, cam_w, cam_h, sw, sh)
    cx, cy = center

    # Hướng kiếm: từ wrist → MCP ngón giữa (hướng bàn tay)
    wrist_s = pt_to_screen(hand.pts[0],  cam_w, cam_h, sw, sh)
    mcp_s   = pt_to_screen(hand.pts[9],  cam_w, cam_h, sw, sh)
    tip_s   = pt_to_screen(hand.pts[12], cam_w, cam_h, sw, sh)   # đầu ngón giữa

    dx = tip_s[0] - wrist_s[0]
    dy = tip_s[1] - wrist_s[1]
    angle_rad = math.atan2(dy, dx)

    if slash_angle is not None:
        # Override với hướng vung thực tế
        angle_rad = math.radians(slash_angle)

    blade_len = int(min(sw, sh) * 0.22)   # ~20% chiều màn hình
    blade_w   = max(6, blade_len // 12)

    # Điểm chuôi và đầu kiếm
    hilt_x = int(cx - math.cos(angle_rad) * blade_len * 0.15)
    hilt_y = int(cy - math.sin(angle_rad) * blade_len * 0.15)
    tip_x  = int(cx + math.cos(angle_rad) * blade_len * 0.85)
    tip_y  = int(cy + math.sin(angle_rad) * blade_len * 0.85)

    # Pháp tuyến để vẽ lưỡi có chiều rộng
    nx = -math.sin(angle_rad)
    ny =  math.cos(angle_rad)

    # Glow khi chém
    glow = min(1.0, slash_anim)
    glow_r = blade_len // 2

    if glow > 0.05:
        glow_surf = pygame.Surface((sw, sh), pygame.SRCALPHA)
        glow_alpha = int(120 * glow)
        pygame.draw.line(glow_surf, (150, 220, 255, glow_alpha),
                         (hilt_x, hilt_y), (tip_x, tip_y), blade_w * 3)
        surface.blit(glow_surf, (0, 0))

    # Lưỡi kiếm (polygon taper: rộng ở chuôi, nhọn ở đầu)
    half = blade_w // 2
    blade_pts = [
        (hilt_x + nx * half,  hilt_y + ny * half),
        (hilt_x - nx * half,  hilt_y - ny * half),
        (tip_x,               tip_y),
    ]
    blade_pts = [(int(x), int(y)) for x, y in blade_pts]

    # Thân kiếm màu bạc-xanh
    blade_col = (int(180 + 60 * glow), int(210 + 40 * glow), 255)
    edge_col  = (int(120 + 80 * glow), int(170 + 60 * glow), 255)
    pygame.draw.polygon(surface, blade_col, blade_pts)
    pygame.draw.polygon(surface, edge_col,  blade_pts, 2)

    # Đường sáng giữa lưỡi
    mid_x = (hilt_x + tip_x) // 2
    mid_y = (hilt_y + tip_y) // 2
    pygame.draw.line(surface, (220, 240, 255),
                     (hilt_x, hilt_y), (mid_x, mid_y), max(1, blade_w // 3))

    # Chuôi kiếm
    guard_len = blade_w * 3
    g1 = (int(hilt_x + nx * guard_len), int(hilt_y + ny * guard_len))
    g2 = (int(hilt_x - nx * guard_len), int(hilt_y - ny * guard_len))
    pygame.draw.line(surface, (200, 160, 60), g1, g2, max(3, blade_w // 2))

    hilt_back_x = int(hilt_x - math.cos(angle_rad) * blade_len * 0.1)
    hilt_back_y = int(hilt_y - math.sin(angle_rad) * blade_len * 0.1)
    pygame.draw.line(surface, (160, 120, 40),
                     (hilt_x, hilt_y), (hilt_back_x, hilt_back_y),
                     max(3, blade_w // 2))


def _draw_bow_circle(surface, hands, cam_w, cam_h, sw, sh,
                     bow_draw_level: float = 0.0,
                     bow_hand=None, string_hand=None,
                     player_pos=None):
    """
    Bow: hien thi vong tron quanh nhan vat + mui ten huong ban.
    Khong ve hinh cung vat ly - chi ve UI vong tron + charge.
    """
    if not hands:
        return

    # Vi tri nhan vat hoac tam man hinh
    if player_pos:
        cx, cy = int(player_pos[0]), int(player_pos[1]) - 60
    else:
        cx, cy = sw // 2, sh // 2

    pull_t = max(0.0, min(1.0, bow_draw_level))

    # Vong tron ngoai: ban kinh tang theo charge
    base_r = 80
    max_r  = 140
    r = int(base_r + (max_r - base_r) * pull_t)

    ring_surf = pygame.Surface((sw, sh), pygame.SRCALPHA)

    # Vong tron chinh (trang -> vang khi charge)
    ring_r = int(100 + 155 * pull_t)
    ring_g = int(220 - 120 * pull_t)
    ring_b = int(255 - 200 * pull_t)
    ring_alpha = int(160 + 80 * pull_t)
    pygame.draw.circle(ring_surf, (ring_r, ring_g, ring_b, ring_alpha),
                       (cx, cy), r, 3)
    # Vong tron nho ben trong (nhip nhang)
    tick = pygame.time.get_ticks()
    pulse = 0.5 + 0.5 * math.sin(tick * 0.008)
    inner_r = int(r * 0.55 + pulse * 8)
    pygame.draw.circle(ring_surf, (ring_r, ring_g, ring_b, int(80 * pull_t + 40)),
                       (cx, cy), inner_r, 1)

    surface.blit(ring_surf, (0, 0))

    # Xac dinh huong ban: tu bow_hand sang string_hand (hoac tay nguoi dung)
    if bow_hand and string_hand:
        bh_s = pt_to_screen(bow_hand,    cam_w, cam_h, sw, sh)
        sh_s = pt_to_screen(string_hand, cam_w, cam_h, sw, sh)
        # Huong ban = nguoc lai vecto keo (bo ten bay ve phia doi dien)
        dx = bh_s[0] - sh_s[0]
        dy = bh_s[1] - sh_s[1]
    elif len(hands) >= 2:
        c0 = hand_center_screen(hands[0], cam_w, cam_h, sw, sh)
        c1 = hand_center_screen(hands[1], cam_w, cam_h, sw, sh)
        dx = c0[0] - c1[0]
        dy = c0[1] - c1[1]
    else:
        # Huong mac dinh: sang phai
        dx, dy = 1, 0

    dist_v = math.sqrt(dx*dx + dy*dy) or 1
    ux, uy = dx / dist_v, dy / dist_v

    # Mui ten huong ban tren vong tron
    arr_start = (int(cx + ux * r), int(cy + uy * r))
    arr_end   = (int(cx + ux * (r + 50 + 30 * pull_t)),
                 int(cy + uy * (r + 50 + 30 * pull_t)))

    arrow_col = (ring_r, ring_g, ring_b)
    pygame.draw.line(surface, arrow_col, arr_start, arr_end, 3)
    # Dau mui ten
    perp_x, perp_y = -uy, ux
    head_size = 10 + int(8 * pull_t)
    pygame.draw.polygon(surface, arrow_col, [
        arr_end,
        (int(arr_end[0] - ux*head_size + perp_x*head_size*0.5),
         int(arr_end[1] - uy*head_size + perp_y*head_size*0.5)),
        (int(arr_end[0] - ux*head_size - perp_x*head_size*0.5),
         int(arr_end[1] - uy*head_size - perp_y*head_size*0.5)),
    ])

    # Label charge
    if pull_t > 0.05:
        try:
            f = pygame.font.SysFont('Arial', 18, bold=True)
            charge_pct = int(pull_t * 100)
            lbl = f.render(f'CHARGE {charge_pct}%', True, arrow_col)
            surface.blit(lbl, (cx - lbl.get_width()//2, cy - r - 28))
        except Exception:
            pass


def _draw_grenade(surface, hands, cam_w, cam_h, sw, sh,
                  throw_anim: float = 0.0):
    """Vẽ lựu đạn tại lòng bàn tay nắm"""
    if not hands:
        return

    hand = hands[0]
    # Vị trí: giữa lòng bàn tay (wrist + palm center)
    wrist_s = pt_to_screen(hand.pts[0], cam_w, cam_h, sw, sh)
    palm_s  = pt_to_screen(hand.pts[9], cam_w, cam_h, sw, sh)
    cx = (wrist_s[0] + palm_s[0]) // 2
    cy = (wrist_s[1] + palm_s[1]) // 2

    r = max(18, int(math.dist(wrist_s, palm_s) * 0.35))

    flash = min(1.0, throw_anim)
    body_col  = (int(70 + 60 * flash), int(130 + 50 * flash), int(70 + 60 * flash))
    shine_col = (int(100 + 80 * flash), int(180 + 60 * flash), int(100 + 80 * flash))

    # Thân lựu đạn
    pygame.draw.ellipse(surface, body_col,
                        (cx - r, cy - int(r * 0.75), r * 2, int(r * 1.5)))
    pygame.draw.ellipse(surface, shine_col,
                        (cx - r + 3, cy - int(r * 0.75) + 3,
                         r - 2, int(r * 0.6)))
    pygame.draw.ellipse(surface, (40, 90, 40),
                        (cx - r, cy - int(r * 0.75), r * 2, int(r * 1.5)), 2)

    # Ngòi
    fuse_top = (cx, cy - int(r * 0.75))
    fuse_end = (cx + int(r * 0.4), cy - int(r * 1.3))
    pygame.draw.line(surface, (180, 180, 60), fuse_top, fuse_end, 3)

    # Tia lửa ngòi (nhấp nháy)
    spark_a = int(200 * (0.5 + 0.5 * math.sin(pygame.time.get_ticks() * 0.03)))
    spark_surf = pygame.Surface((20, 20), pygame.SRCALPHA)
    pygame.draw.circle(spark_surf, (255, 220, 50, spark_a), (10, 10), 5)
    surface.blit(spark_surf,
                 (fuse_end[0] - 10, fuse_end[1] - 10))

    # Khía dọc thân lựu đạn
    for ki in range(3):
        kx = cx - r + int(r * 2 * (ki + 1) / 4)
        pygame.draw.line(surface, (40, 80, 40),
                         (kx, cy - int(r * 0.6)),
                         (kx, cy + int(r * 0.6)), 1)


def _draw_gun_circle(surface, hands, cam_w, cam_h, sw, sh,
                     is_firing: bool = False,
                     player_pos=None,
                     gun_tips_center=None):
    """
    Gun: hien thi vong tron quanh nhan vat + mui ten huong ban (theo tam ngon tay).
    gun_tips_center: toa do cam (640x480) cua trung binh dau 4 ngon tay.
    Khong ve hinh sung vat ly.
    """
    if not hands:
        return

    if player_pos:
        cx, cy = int(player_pos[0]), int(player_pos[1]) - 60
    else:
        cx, cy = sw // 2, sh // 2

    tick = pygame.time.get_ticks()

    # Vong tron ngoai: mau xam kim loai, nhip nhang khi ban
    r = 90
    pulse = 0.5 + 0.5 * math.sin(tick * 0.012)
    ring_alpha = int(140 + 60 * pulse) if is_firing else 130
    fire_r = int(180 + 75 * pulse) if is_firing else 160
    fire_g = int(180 + 75 * pulse) if is_firing else 160
    fire_b = 200

    ring_surf = pygame.Surface((sw, sh), pygame.SRCALPHA)
    # Vong ngoai chinh
    pygame.draw.circle(ring_surf, (fire_r, fire_g, fire_b, ring_alpha),
                       (cx, cy), r, 3)
    # Vach chia goc (8 vach nhu la ban)
    for i in range(8):
        a = math.radians(i * 45 + tick * 0.05)
        tick_r_in  = r - 8
        tick_r_out = r + 5 if i % 2 == 0 else r + 1
        x1 = int(cx + math.cos(a) * tick_r_in)
        y1 = int(cy + math.sin(a) * tick_r_in)
        x2 = int(cx + math.cos(a) * tick_r_out)
        y2 = int(cy + math.sin(a) * tick_r_out)
        pygame.draw.line(ring_surf, (fire_r, fire_g, fire_b, 180), (x1,y1),(x2,y2), 2)
    surface.blit(ring_surf, (0, 0))

    # Tinh huong ban: vector wrist(0) -> tam dau ngon tay (tips_center)
    # Neu co gun_tips_center (tu gesture_detector) thi dung, khong thi tinh tu pts
    dx, dy = 1.0, 0.0
    for h in hands:
        wrist_s = pt_to_screen(h.pts[0], cam_w, cam_h, sw, sh)
        if gun_tips_center is not None:
            # gun_tips_center la toa do camera -> scale sang screen
            tips_s = pt_to_screen(gun_tips_center, cam_w, cam_h, sw, sh)
        elif len(h.pts) >= 21:
            # Tinh tu pts: trung binh dau ngon 8,12,16,20
            tips = [h.pts[i] for i in (8, 12, 16, 20)]
            tx = sum(p[0] for p in tips) // 4
            ty = sum(p[1] for p in tips) // 4
            tips_s = pt_to_screen((tx, ty), cam_w, cam_h, sw, sh)
        else:
            tips_s = pt_to_screen(h.pts[8], cam_w, cam_h, sw, sh)
        dx = tips_s[0] - wrist_s[0]
        dy = tips_s[1] - wrist_s[1]
        if h.label == 'Right':
            break

    dist_v = math.sqrt(dx*dx + dy*dy) or 1
    ux, uy = dx / dist_v, dy / dist_v
    perp_x, perp_y = -uy, ux

    # Mui ten huong ban
    arr_len = 55 + (20 if is_firing else 0)
    arr_start = (int(cx + ux * (r + 4)), int(cy + uy * (r + 4)))
    arr_end   = (int(cx + ux * (r + arr_len)), int(cy + uy * (r + arr_len)))

    arrow_col = (255, 230, 80) if is_firing else (fire_r, fire_g, fire_b)
    pygame.draw.line(surface, arrow_col, arr_start, arr_end, 3)
    head_sz = 14
    pygame.draw.polygon(surface, arrow_col, [
        arr_end,
        (int(arr_end[0] - ux*head_sz + perp_x*head_sz*0.5),
         int(arr_end[1] - uy*head_sz + perp_y*head_sz*0.5)),
        (int(arr_end[0] - ux*head_sz - perp_x*head_sz*0.5),
         int(arr_end[1] - uy*head_sz - perp_y*head_sz*0.5)),
    ])

    # Muzzle flash khi ban
    if is_firing:
        flash_x = int(cx + ux * (r + arr_len + 20))
        flash_y = int(cy + uy * (r + arr_len + 20))
        flash_surf = pygame.Surface((sw, sh), pygame.SRCALPHA)
        flash_alpha = int(200 * pulse)
        pygame.draw.circle(flash_surf, (255, 220, 80, flash_alpha),
                           (flash_x, flash_y), 20)
        pygame.draw.circle(flash_surf, (255, 255, 200, int(flash_alpha*0.6)),
                           (flash_x, flash_y), 32)
        surface.blit(flash_surf, (0, 0))

    # Label huong dan ban
    try:
        f = pygame.font.SysFont('Arial', 16, bold=True)
        lbl = f.render('Close fist to shoot', True, (fire_r, fire_g, fire_b))
        surface.blit(lbl, (cx - lbl.get_width()//2, cy - r - 26))
    except Exception:
        pass


def _draw_mine_indicator(surface, hands, cam_w, cam_h, sw, sh):
    """
    Mine: hien thi vong tay + 'Place mine here' khi dang giu gesture.
    """
    if not hands or len(hands) < 2:
        return

    c0 = hand_center_screen(hands[0], cam_w, cam_h, sw, sh)
    c1 = hand_center_screen(hands[1], cam_w, cam_h, sw, sh)
    cx = (c0[0] + c1[0]) // 2
    cy = (c0[1] + c1[1]) // 2

    tick = pygame.time.get_ticks()
    pulse = 0.5 + 0.5 * math.sin(tick * 0.015)
    r_outer = int(60 + 15 * pulse)
    alpha = int(180 + 60 * pulse)

    ind_surf = pygame.Surface((sw, sh), pygame.SRCALPHA)
    pygame.draw.circle(ind_surf, (200, 50, 50, alpha), (cx, cy), r_outer, 3)
    pygame.draw.circle(ind_surf, (255, 120, 80, int(alpha * 0.5)),
                       (cx, cy), int(r_outer * 0.55), 1)
    sz = 10
    pygame.draw.line(ind_surf, (255, 80, 80, alpha),
                     (cx - sz, cy - sz), (cx + sz, cy + sz), 3)
    pygame.draw.line(ind_surf, (255, 80, 80, alpha),
                     (cx + sz, cy - sz), (cx - sz, cy + sz), 3)
    surface.blit(ind_surf, (0, 0))

    try:
        f = pygame.font.SysFont('Arial', 16, bold=True)
        lbl = f.render('Place mine here', True, (255, 120, 80))
        surface.blit(lbl, (cx - lbl.get_width()//2, cy - r_outer - 24))
    except Exception:
        pass

    for c in (c0, c1):
        ring_surf = pygame.Surface((sw, sh), pygame.SRCALPHA)
        pygame.draw.circle(ring_surf, (255, 80, 80, int(140 * pulse)),
                           c, 20, 2)
        surface.blit(ring_surf, (0, 0))


# ─── API chính ────────────────────────────────────────────────────────────
class WeaponRenderer:
    """
    Vẽ vũ khí trực tiếp tại vị trí tay thật mỗi frame.
    Được gọi từ game.draw() sau khi vẽ player, trước HUD.
    """

    def __init__(self, cam_w: int = 640, cam_h: int = 480):
        self.cam_w = cam_w
        self.cam_h = cam_h

        # Trang thai animation
        self._slash_anim   = 0.0
        self._slash_angle  = None
        self._throw_anim   = 0.0
        self._punch_anim   = 0.0
        # Slash trail kieu Fruit Ninja
        self._slash_trail  = SlashTrail()

    def notify_attack(self, attack_type: str):
        """Goi khi player tan cong de kich hoat animation vu khi"""
        if attack_type in ('slash_right', 'slash_left', 'slash_up', 'slash_down'):
            self._slash_anim = 1.0
            angles = {
                'slash_right': 0,
                'slash_left': 180,
                'slash_up': -90,
                'slash_down': 90,
            }
            self._slash_angle = angles.get(attack_type, 0)
        elif attack_type in ('punch_left', 'punch_right'):
            self._punch_anim = 1.0
        elif attack_type == 'throw_grenade':
            self._throw_anim = 1.0

    def get_slash_trail(self):
        """Tra ve SlashTrail object de game.py kiem tra damage"""
        return self._slash_trail

    def update(self):
        """Giam dan cac animation moi frame"""
        self._slash_anim  = max(0.0, self._slash_anim  - 0.08)
        self._punch_anim  = max(0.0, self._punch_anim  - 0.08)
        self._throw_anim  = max(0.0, self._throw_anim  - 0.08)
        if self._slash_anim <= 0:
            self._slash_angle = None
        self._slash_trail.update()

    def draw(self, surface, weapon: str, hands: list,
             screen_w: int, screen_h: int,
             bow_draw_level: float = 0.0,
             bow_hand=None, string_hand=None,
             gun_firing: bool = False,
             player_pos=None,
             gun_tips_center=None):
        """
        Vẽ vũ khí lên surface tại vị trí tay thật.

        weapon     : tên vũ khí hiện tại
        hands      : list[HandData] từ gesture_detector
        screen_w/h : kích thước màn hình thực tế
        """
        if not weapon or not hands:
            return

        sw, sh = screen_w, screen_h
        cw, ch = self.cam_w, self.cam_h

        if weapon == 'iron_gauntlets':
            _draw_iron_gauntlets(surface, hands, cw, ch, sw, sh,
                                 attack_anim=self._punch_anim)

        elif weapon == 'sword':
            # CHI ve slash trail - khong ve hinh kiem vat ly
            # Chi lay 1 diem/tay/frame: palm center pts[9] de giam jitter
            if hands:
                for h in hands:
                    palm_s = pt_to_screen(h.pts[9], cw, ch, sw, sh)
                    self._slash_trail.add_hand_point(
                        palm_s[0], palm_s[1],
                        width=max(14, int(min(sw, sh) * 0.028))
                    )
            self._slash_trail.draw(surface)

        elif weapon == 'bow':
            _draw_bow_circle(surface, hands, cw, ch, sw, sh,
                             bow_draw_level=bow_draw_level,
                             bow_hand=bow_hand,
                             string_hand=string_hand,
                             player_pos=player_pos)

        elif weapon == 'grenade':
            # Khong ve hinh luu dan tren tay
            # Chi hien thi indicator nho de biet dang cam luu dan
            if hands:
                hand = hands[0]
                center = hand_center_screen(hand, cw, ch, sw, sh)
                cx_g, cy_g = center
                tick = pygame.time.get_ticks()
                pulse = 0.5 + 0.5 * math.sin(tick * 0.012)
                ind_r = int(18 + 6 * pulse)
                ind_alpha = int(180 + 60 * pulse)
                ind_surf = pygame.Surface((sw, sh), pygame.SRCALPHA)
                pygame.draw.circle(ind_surf, (100, 200, 80, ind_alpha),
                                   (cx_g, cy_g), ind_r, 3)
                surface.blit(ind_surf, (0, 0))
                try:
                    f = pygame.font.SysFont('Arial', 14, bold=True)
                    lbl = f.render('Ready to throw', True, (100, 200, 80))
                    surface.blit(lbl, (cx_g - lbl.get_width()//2, cy_g - ind_r - 18))
                except Exception:
                    pass

        elif weapon == 'gun':
            _draw_gun_circle(surface, hands, cw, ch, sw, sh,
                             is_firing=gun_firing,
                             player_pos=player_pos,
                             gun_tips_center=gun_tips_center)

        elif weapon == 'mine':
            _draw_mine_indicator(surface, hands, cw, ch, sw, sh)
