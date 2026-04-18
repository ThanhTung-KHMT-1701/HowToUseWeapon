"""
checking_weapon_screen.py - Phong tap vu khi (Training Room)

Giao dien giong game that: nen khong gian, muc tieu dummy, HUD.
- Nguoi choi dung tay that de thu vu khi.
- Khong co bot demo.
- HP bat tu (khong giam xuong duoi 1).
- Phim Left/Right hoac A/D: chuyen vu khi.
- Phim ESC: thoat vao game chinh.
"""

import pygame
import math
import random
import os
from src.sprites import get_gif_frames


# ── Du lieu mo ta tung vu khi ─────────────────────────────────────────────────
WEAPON_DATA = [
    {
        "id":     "iron_gauntlets",
        "name":   "IRON GAUNTLETS",
        "color":  (200, 200, 240),
        "equip":  "Both fists far apart (boxing stance), hold 0.35s",
        "attack": "Move fist fast (velocity > 8px/frame)",
        "tip":    "Fast burst damage at close range!",
    },
    {
        "id":     "sword",
        "name":   "SWORD",
        "color":  (150, 200, 255),
        "equip":  "Both fists close together (same Y), hold 0.35s, then pull apart",
        "attack": "Swing hand fast in any direction (velocity > 7px/frame)",
        "tip":    "Wide arc that hits multiple enemies!",
    },
    {
        "id":     "bow",
        "name":   "BOW",
        "color":  (50, 220, 150),
        "equip":  "Both fists close, one hand HIGHER than the other, hold 0.35s, pull apart",
        "attack": "Extend index finger only (middle finger stays down) to release",
        "tip":    "Pull hands further apart for stronger arrow!",
    },
    {
        "id":     "grenade",
        "name":   "GRENADE",
        "color":  (220, 130, 50),
        "equip":  "One fist only (keep other hand out of frame), hold 0.35s",
        "attack": "Open hand (3+ fingers) + fast throw motion (velocity > 7px/frame)",
        "tip":    "Explosive area damage - great vs groups!",
    },
    {
        "id":     "gun",
        "name":   "GUN",
        "color":  (160, 180, 220),
        "equip":  "Both hands: index + middle fingers up, ring + pinky down, hold 0.35s",
        "attack": "Close fist to shoot (open -> fist transition)",
        "tip":    "Fastest fire rate - keep your distance!",
    },
    {
        "id":     "mine",
        "name":   "MINE",
        "color":  (200, 80, 80),
        "equip":  "Both hands: thumb + index up on both hands, touch thumbtips together, hold 0.35s",
        "attack": "Keep thumbtips touching for 0.35s - mine is placed at your feet",
        "tip":    "AoE 200px, 150 damage, destroys obstacles! Fuse: 3 seconds.",
    },
]


# ── Particle nho cho hieu ung ────────────────────────────────────────────────
class _FxParticle:
    __slots__ = ('x', 'y', 'vx', 'vy', 'color', 'life', 'max_life', 'size', 'gravity')

    def __init__(self, x, y, vx, vy, color, life, size=4, gravity=0.15):
        self.x, self.y   = float(x), float(y)
        self.vx, self.vy = float(vx), float(vy)
        self.color       = color
        self.life        = life
        self.max_life    = life
        self.size        = size
        self.gravity     = gravity

    def update(self):
        self.x  += self.vx
        self.y  += self.vy
        self.vy += self.gravity
        self.life -= 1

    def draw(self, surf):
        if self.life <= 0:
            return
        alpha = int(255 * self.life / self.max_life)
        r = max(1, int(self.size * self.life / self.max_life))
        s = pygame.Surface((r * 2 + 1, r * 2 + 1), pygame.SRCALPHA)
        pygame.draw.circle(s, (*self.color[:3], alpha), (r, r), r)
        surf.blit(s, (int(self.x) - r, int(self.y) - r))


def _spawn_hit_fx(particles, x, y, weapon_id):
    """Tao VFX khi don danh trung muc tieu."""
    if weapon_id == "iron_gauntlets":
        for _ in range(18):
            vx = random.uniform(-9, 9)
            vy = random.uniform(-10, 2)
            c  = random.choice([(255, 100, 40), (255, 200, 80), (240, 60, 20)])
            particles.append(_FxParticle(x, y, vx, vy, c, random.randint(14, 26), random.randint(3, 7)))
        for a in range(0, 360, 20):
            rad = math.radians(a)
            particles.append(_FxParticle(x, y, math.cos(rad) * 7, math.sin(rad) * 7,
                                          (255, 180, 80), 18, 3, gravity=0))
    elif weapon_id == "sword":
        for i in range(28):
            angle = math.radians(-20 + i * 3.5)
            sp = random.uniform(5, 14)
            c  = random.choice([(180, 220, 255), (100, 180, 255), (220, 240, 255)])
            particles.append(_FxParticle(x + random.randint(-20, 20), y + random.randint(-10, 10),
                                          math.cos(angle) * sp, math.sin(angle) * sp - 2,
                                          c, random.randint(14, 30), random.randint(2, 6)))
    elif weapon_id == "bow":
        for _ in range(14):
            particles.append(_FxParticle(x, y,
                                          random.uniform(2, 12), random.uniform(-5, 5),
                                          (50, 230, 130), random.randint(16, 28), 4))
    elif weapon_id == "grenade":
        for _ in range(55):
            sp  = random.uniform(4, 20)
            ang = math.radians(random.randint(0, 360))
            c   = random.choice([(255, 80, 30), (255, 160, 30), (255, 220, 80)])
            particles.append(_FxParticle(x + random.randint(-15, 15), y + random.randint(-15, 15),
                                          math.cos(ang) * sp, math.sin(ang) * sp,
                                          c, random.randint(20, 50), random.randint(3, 11), gravity=0.35))
    elif weapon_id == "gun":
        for _ in range(10):
            particles.append(_FxParticle(x, y,
                                          random.uniform(-6, 6), random.uniform(-8, 2),
                                          (200, 220, 255), random.randint(10, 18), 4))


# ── Muc tieu dummy ────────────────────────────────────────────────────────────
class _DummyTarget:
    """Muc tieu bat dong trong phong tap."""
    RESPAWN_FRAMES = 60

    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.hp      = 300
        self.max_hp  = 300
        self.alive   = True
        self._dead_timer = 0
        self._hit_timer  = 0
        # Tuong thich WeaponSystem
        self.enemy_type  = 'dummy'
        self.vx = 0.0
        self.vy = 0.0
        self.die_timer   = 0
        self.DIE_DURATION = 30
        # Su dung GIF thay vi sprite thu cong
        self._gif_frames = get_gif_frames('21_monster.gif', (120, 140))
        self._gif_idx = 0
        self._gif_timer = 0
        self._surf = self._gif_frames[0] if self._gif_frames else self._make_fallback_sprite()

    def _make_fallback_sprite(self):
        w, h = 120, 140
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.ellipse(s, (80, 200, 120, 220), (15, 35, 90, 95))
        pygame.draw.circle(s, (80, 200, 120, 220), (60, 26), 28)
        return s

    def get_rect(self):
        w, h = self._surf.get_size()
        return pygame.Rect(self.x - w // 2, self.y - h, w, h)

    def knockback(self, dx, dy):
        pass  # Dummy khong di chuyen

    def take_damage(self, dmg):
        if not self.alive:
            return False
        self.hp = max(0, self.hp - dmg)
        self._hit_timer = 12
        if self.hp <= 0:
            self.alive = False
            self._dead_timer = self.RESPAWN_FRAMES
        return True

    def update(self):
        if self._hit_timer > 0:
            self._hit_timer -= 1
        if not self.alive:
            self._dead_timer -= 1
            if self._dead_timer <= 0:
                self.hp    = self.max_hp
                self.alive = True
        # GIF animation
        if self._gif_frames:
            self._gif_timer += 1
            if self._gif_timer > 5:
                self._gif_timer = 0
                self._gif_idx = (self._gif_idx + 1) % len(self._gif_frames)
                self._surf = self._gif_frames[self._gif_idx]

    def draw(self, surface):
        w, h = self._surf.get_size()
        sprite = self._surf
        if self._hit_timer > 0 and self._hit_timer % 3 < 2:
            sprite = sprite.copy()
            sprite.fill((255, 80, 80, 100), special_flags=pygame.BLEND_RGBA_ADD)
        if not self.alive:
            alpha = max(0, int(255 * self._dead_timer / self.RESPAWN_FRAMES))
            sprite = sprite.copy()
            sprite.set_alpha(alpha)
        surface.blit(sprite, (int(self.x) - w // 2, int(self.y) - h))
        if self.alive:
            bx = int(self.x) - w // 2
            by = int(self.y) - h - 10
            pygame.draw.rect(surface, (60, 10, 10), (bx, by, w, 6), border_radius=3)
            hp_w = int(w * self.hp / self.max_hp)
            if hp_w > 0:
                pygame.draw.rect(surface, (50, 200, 100), (bx, by, hp_w, 6), border_radius=3)


# ── Phong tap ─────────────────────────────────────────────────────────────────
class CheckingWeaponScreen:
    """
    Phong tap vu khi.
    Nguoi choi tu thu vu khi bang tay that.
    Khong co bot demo.
    HP bat tu. ESC -> game chinh.
    """

    def __init__(self, screen_w, screen_h,
                 weapon_icons,
                 bg_base, star1, star2,
                 draw_bg_fn,
                 weapon_sys_factory,
                 weapon_rend,
                 effect_manager_class,
                 player_factory,
                 gesture=None,
                 unlocked_weapons=None):
        self.screen_w = screen_w
        self.screen_h = screen_h
        self.floor_y  = int(screen_h * 0.85)
        self.weapon_icons = weapon_icons

        self.bg_base = bg_base
        self.star1   = star1
        self.star2   = star2
        self.draw_bg = draw_bg_fn
        self._t      = 0

        # Fonts - chi dung ASCII, khong dung ky tu dac biet
        self.font_title  = pygame.font.SysFont('Arial', 28, bold=True)
        self.font_label  = pygame.font.SysFont('Arial', 18, bold=True)
        self.font_value  = pygame.font.SysFont('Arial', 19)
        self.font_hint   = pygame.font.SysFont('Arial', 16)
        self.font_big    = pygame.font.SysFont('Arial', 34, bold=True)
        self.font_debug  = pygame.font.SysFont('Courier New', 14)

        # Gesture detector reference
        self._gesture = gesture

        # Loc vu khi da mo khoa
        if unlocked_weapons:
            self._unlocked_ids = unlocked_weapons
        else:
            self._unlocked_ids = [w['id'] for w in WEAPON_DATA]
        self._available_weapons = [w for w in WEAPON_DATA
                                   if w['id'] in self._unlocked_ids]

        # Player (bat tu)
        self._player_factory = player_factory
        self.player = player_factory()
        self.player.hp = self.player.max_hp

        # Weapon system + renderer
        self._ws_factory  = weapon_sys_factory
        self._em_class    = effect_manager_class
        self.em           = effect_manager_class()
        self.weapon_sys   = weapon_sys_factory(
            player_pos=lambda: self.player.get_pos(),
            effect_manager=self.em
        )
        self.weapon_rend  = weapon_rend

        # Muc tieu dummy
        self._dummies: list[_DummyTarget] = []
        self._spawn_dummies()

        # Weapon index
        self.current_idx = 0
        self._apply_weapon()

        # Particles
        self._particles: list[_FxParticle] = []

        # Slide animation
        self._slide_offset = 0.0

        # Scroll stars
        self._scroll = [0.0, 0.0]

        # ── Weapon music mapping ──────────────────────────────────────────
        self._weapon_music = {
            'iron_gauntlets': os.path.join('AmThanhMinhHoa', '1_iron_gauntlets_8bit_battle_loop.ogg'),
            'sword':          os.path.join('AmThanhMinhHoa', '2_sword_battle_rpg_theme.ogg'),
            'bow':            os.path.join('AmThanhMinhHoa', '3_bow_dungeon_ambience.ogg'),
            'grenade':        os.path.join('AmThanhMinhHoa', '4_grenade_battle_intense.ogg'),
            'gun':            os.path.join('AmThanhMinhHoa', '5_gun_warplanets_space.ogg'),
            'mine':           os.path.join('AmThanhMinhHoa', '6_mine_boss_battle.ogg'),
        }
        self._play_weapon_music()

        self.done = False

    # ── Play weapon music ──────────────────────────────────────────────────────
    def _play_weapon_music(self):
        wid = self._available_weapons[self.current_idx]["id"]
        fname = self._weapon_music.get(wid)
        if fname:
            fpath = os.path.join('assets', 'audios', fname)
            if os.path.isfile(fpath):
                try:
                    pygame.mixer.music.load(fpath)
                    pygame.mixer.music.set_volume(0.4)
                    pygame.mixer.music.play(-1)
                except Exception:
                    pass

    # ── Spawn muc tieu ────────────────────────────────────────────────────────
    def _spawn_dummies(self):
        self._dummies.clear()
        cx = self.screen_w // 2
        positions = [
            (cx - 340, self.floor_y),
            (cx,       self.floor_y),
            (cx + 340, self.floor_y),
        ]
        for x, y in positions:
            self._dummies.append(_DummyTarget(x, y))

    # ── Ap dung vu khi ────────────────────────────────────────────────────────
    def _apply_weapon(self):
        wid = self._available_weapons[self.current_idx]["id"]
        self.player.current_weapon = wid
        # Dong bo vu khi vao gesture detector de nhan dien tan cong
        if self._gesture:
            self._gesture.current_weapon = wid
        self.em = self._em_class()
        self.weapon_sys = self._ws_factory(
            player_pos=lambda: self.player.get_pos(),
            effect_manager=self.em
        )
        self.weapon_sys.equip(wid)

    # ── Xu ly su kien ─────────────────────────────────────────────────────────
    def handle_event(self, event) -> bool:
        if event.type != pygame.KEYDOWN:
            return False
        if event.key == pygame.K_ESCAPE:
            self.done = True
            return True
        if event.key in (pygame.K_LEFT, pygame.K_a):
            self._navigate(-1)
        if event.key in (pygame.K_RIGHT, pygame.K_d):
            self._navigate(+1)
        return False

    def _navigate(self, direction):
        n = len(self._available_weapons)
        self.current_idx = (self.current_idx + direction) % n
        self._slide_offset = direction * self.screen_w * 0.25
        self._apply_weapon()
        self._play_weapon_music()
        self._spawn_dummies()
        self._particles.clear()

    # ── Update ────────────────────────────────────────────────────────────────
    def update(self, camera_frame=None, hands=None,
               gesture_result=None, space_pressed=False):
        self._t += 1
        self._scroll[0] += 0.3
        self._scroll[1] += 0.8

        # Slide
        if abs(self._slide_offset) > 2:
            self._slide_offset *= 0.70
        else:
            self._slide_offset = 0.0

        # HP bat tu: hoi day neu xuong duoi 1
        if self.player.hp < 1:
            self.player.hp = self.player.max_hp

        self.player.update()

        # ── Di chuyển bằng phím mũi tên ──────────────────────────────────
        keys = pygame.key.get_pressed()
        MOVE_SPEED = 5
        if keys[pygame.K_LEFT]:
            self.player.x = max(30, self.player.x - MOVE_SPEED)
        if keys[pygame.K_RIGHT]:
            self.player.x = min(self.screen_w - 30, self.player.x + MOVE_SPEED)
        if keys[pygame.K_UP]:
            self.player.y = max(200, self.player.y - MOVE_SPEED)
        if keys[pygame.K_DOWN]:
            self.player.y = min(self.floor_y, self.player.y + MOVE_SPEED)

        # ── Di chuyển bằng cử chỉ tay (tay trái thật = label 'Right') ───
        if hands:
            import math as _math
            HAND_SPEED = 7
            for h in hands:
                if h.label == 'Right':
                    wx, wy = h.pts[0]
                    mcp_pts = [h.pts[i] for i in (5, 9, 13, 17)]
                    mcx = sum(p[0] for p in mcp_pts) // 4
                    mcy = sum(p[1] for p in mcp_pts) // 4
                    dx = mcx - wx
                    dy = mcy - wy
                    dist_vec = _math.sqrt(dx*dx + dy*dy)
                    if dist_vec > 1:
                        nx = dx / dist_vec
                        ny = dy / dist_vec
                        speed = HAND_SPEED * min(2.0, max(0.5, dist_vec / 50))
                        self.player.x = max(30, min(self.screen_w - 30,
                                                    self.player.x + nx * speed))
                        self.player.y = max(200, min(self.floor_y,
                                                     self.player.y + ny * speed))
                    break

        for d in self._dummies:
            d.update()

        for p in self._particles:
            p.update()
        self._particles = [p for p in self._particles if p.life > 0]

        self.em.update()

        # Xu ly gesture nguoi dung
        if gesture_result:
            bow_draw   = gesture_result.get('bow_draw_level', 0.0)
            bow_hand   = gesture_result.get('bow_hand_pos')
            str_hand   = gesture_result.get('string_hand_pos')
            gun_firing = gesture_result.get('gun_firing', False)
            attack     = gesture_result.get('attack')
            if self.player.current_weapon == 'gun' and space_pressed:
                attack = 'shoot'
                gun_firing = True
            if attack:
                px, py = self.player.get_pos()
                self.weapon_sys.attack(
                    attack, (px, py),
                    self._dummies,
                    bow_draw_level=bow_draw,
                    bow_hand=bow_hand,
                    string_hand=str_hand
                )
                self.weapon_rend.notify_attack(attack)
                # Spawn VFX tai muc tieu gan nhat
                alive_d = [d for d in self._dummies if d.alive]
                if alive_d:
                    nearest = min(alive_d, key=lambda d: abs(d.x - px))
                    _spawn_hit_fx(self._particles, nearest.x, nearest.y - 40,
                                  self.player.current_weapon)
            self.weapon_sys.update(
                self._dummies, self.screen_w, self.screen_h,
                bow_draw_level=bow_draw,
                bow_hand=bow_hand,
                string_hand=str_hand,
                player_pos=self.player.get_pos(),
                gun_firing=gun_firing
            )
        else:
            self.weapon_sys.update(
                self._dummies, self.screen_w, self.screen_h,
                player_pos=self.player.get_pos()
            )

        self.weapon_rend.update()

    # ── Draw ─────────────────────────────────────────────────────────────────
    def draw(self, surface, camera_frame=None, hands=None,
             bow_draw=0.0, bow_hand=None, string_hand=None,
             gun_firing=False, gesture_preview=None, gesture_progress=0.0):

        self.draw_bg(surface, self.bg_base, self.star1, self.star2,
                     self._t, _sx=self._scroll)

        # Ve muc tieu dummy
        for d in self._dummies:
            d.draw(surface)

        # Ve player
        self.player.draw(surface)

        # Weapon system (dan, trail, charge cung)
        self.weapon_sys.draw(surface)

        # Weapon renderer (vu khi theo tay)
        self.weapon_rend.draw(
            surface,
            weapon     = self.player.current_weapon,
            hands      = hands or [],
            screen_w   = self.screen_w,
            screen_h   = self.screen_h,
            bow_draw_level = bow_draw,
            bow_hand   = bow_hand,
            string_hand = string_hand,
            gun_firing  = gun_firing,
        )

        # Effects
        self.em.draw(surface, self.font_debug)

        # Particles VFX
        for p in self._particles:
            p.draw(surface)

        # ── Panel thong tin vu khi (goc trai) ────────────────────────────────
        slide = int(self._slide_offset)
        self._draw_info_panel(surface, slide)

        # ── Camera feed goc duoi phai ────────────────────────────────────────
        if camera_frame is not None:
            self._draw_camera(surface, camera_frame, hands)

        # ── HP bat tu ────────────────────────────────────────────────────────
        self._draw_immortal_hp(surface)

        # ── Gesture progress bar ──────────────────────────────────────────────
        if gesture_preview and gesture_progress > 0:
            self._draw_gesture_bar(surface, gesture_preview, gesture_progress)

        # ── Tieu de ──────────────────────────────────────────────────────────
        title_surf = self.font_title.render("TRAINING ROOM", True, (200, 200, 255))
        tx = self.screen_w // 2 - title_surf.get_width() // 2
        surface.blit(title_surf, (tx, 14))

        # ── ESC hint ──────────────────────────────────────────────────────────
        esc_surf = self.font_hint.render("[ESC] Start Game", True, (100, 220, 130))
        ex = self.screen_w // 2 - esc_surf.get_width() // 2
        ey = self.screen_h - 36
        esc_bg = pygame.Surface((esc_surf.get_width() + 22, esc_surf.get_height() + 10),
                                pygame.SRCALPHA)
        esc_bg.fill((0, 0, 0, 130))
        surface.blit(esc_bg, (ex - 11, ey - 5))
        surface.blit(esc_surf, (ex, ey))

    # ── Panel thong tin ──────────────────────────────────────────────────────
    def _draw_info_panel(self, surface, slide_offset):
        wdata  = self._available_weapons[self.current_idx]
        wcolor = wdata["color"]
        t      = self._t

        panel_x = 14 + slide_offset
        panel_w = 420
        PAD     = 10

        # Dot navigator
        dot_y = 54
        for i in range(len(self._available_weapons)):
            dot_x = panel_x + 12 + i * 22
            if i == self.current_idx:
                pygame.draw.circle(surface, wcolor, (int(dot_x), dot_y), 7)
            else:
                pygame.draw.circle(surface, (60, 70, 110), (int(dot_x), dot_y), 5)
                pygame.draw.circle(surface, (90, 100, 150), (int(dot_x), dot_y), 5, 1)

        nav = self.font_hint.render("[A] / [D] switch weapon", True, (110, 120, 170))
        surface.blit(nav, (panel_x + 12 + len(self._available_weapons) * 22 + 8, dot_y - nav.get_height() // 2))

        # Ten vu khi
        name_y = dot_y + 16
        glow   = int(180 + 75 * math.sin(t * 0.06))
        name_c = (glow, wcolor[1], wcolor[2])
        name_s = self.font_big.render(wdata["name"], True, name_c)
        surface.blit(name_s, (panel_x, name_y))

        # Icon vu khi nho
        icon_fn = self.weapon_icons.get(wdata["id"])
        if icon_fn:
            icon = icon_fn(48)
            surface.blit(icon, (panel_x + name_s.get_width() + 10, name_y - 4))

        # Card thong tin
        info_y = name_y + name_s.get_height() + 8
        rows = [
            ("EQUIP",  wdata["equip"],  (180, 200, 255)),
            ("ATTACK", wdata["attack"], (255, 180, 100)),
            ("TIP",    wdata["tip"],    (100, 230, 160)),
        ]

        # Wrap text va tinh chieu cao card
        card_rows = []
        max_val_w = panel_w - PAD * 2 - 8
        for lbl, val, rc in rows:
            words = val.split()
            lines, cur = [], ""
            for word in words:
                test = (cur + " " + word).strip()
                if self.font_value.size(test)[0] > max_val_w and cur:
                    lines.append(cur)
                    cur = word
                else:
                    cur = test
            if cur:
                lines.append(cur)
            card_rows.append((lbl, rc, lines))

        label_h = 20
        row_h   = 20
        total_h = sum(label_h + len(ll) * row_h + 6 for _, _, ll in card_rows) + 8

        card_surf = pygame.Surface((panel_w, total_h), pygame.SRCALPHA)
        card_surf.fill((8, 12, 38, 210))
        pygame.draw.rect(card_surf, (*wcolor, 100),
                         (0, 0, panel_w, total_h), border_radius=10)
        pygame.draw.rect(card_surf, (*wcolor, 180),
                         (0, 0, panel_w, total_h), 1, border_radius=10)
        surface.blit(card_surf, (panel_x, info_y))

        cy = info_y + 6
        for lbl, rc, lines in card_rows:
            lbl_s = self.font_label.render(lbl + ":", True, rc)
            surface.blit(lbl_s, (panel_x + PAD, cy))
            cy += label_h
            for line in lines:
                val_s = self.font_value.render(line, True, (200, 210, 235))
                surface.blit(val_s, (panel_x + PAD + 4, cy))
                cy += row_h
            cy += 6

    # ── Camera feed ──────────────────────────────────────────────────────────
    def _draw_camera(self, surface, camera_frame, hands):
        import cv2
        cam_w, cam_h = 280, 210
        small = cv2.resize(camera_frame, (cam_w, cam_h))
        # Ve landmark
        if hands:
            CONNECTIONS = [
                (0,1),(1,2),(2,3),(3,4),
                (0,5),(5,6),(6,7),(7,8),
                (0,9),(9,10),(10,11),(11,12),
                (0,13),(13,14),(14,15),(15,16),
                (0,17),(17,18),(18,19),(19,20),
                (5,9),(9,13),(13,17),
            ]
            sx = cam_w / 640
            sy = cam_h / 480
            for hand in hands:
                if hasattr(hand, 'pts') and len(hand.pts) >= 21:
                    pts_s = [(int(p[0]*sx), int(p[1]*sy)) for p in hand.pts]
                    bc = (80, 200, 80) if hand.label == 'Right' else (200, 80, 200)
                    for a, b in CONNECTIONS:
                        cv2.line(small, pts_s[a], pts_s[b], bc, 1, cv2.LINE_AA)
                    for i, pt in enumerate(pts_s):
                        if i in {4, 8, 12, 16, 20}:
                            cv2.circle(small, pt, 4, (0, 220, 255), -1, cv2.LINE_AA)
                        else:
                            jc = (50,255,50) if hand.label=='Right' else (255,50,255)
                            cv2.circle(small, pt, 2, jc, -1, cv2.LINE_AA)
        small_rgb = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)
        cam_surf  = pygame.surfarray.make_surface(small_rgb.transpose(1, 0, 2))
        cam_surf.set_alpha(190)
        cx = self.screen_w - cam_w - 10
        cy = self.screen_h - cam_h - 80
        pygame.draw.rect(surface, (50, 50, 90), (cx-2, cy-2, cam_w+4, cam_h+4), border_radius=4)
        surface.blit(cam_surf, (cx, cy))
        lbl = self.font_hint.render("CAMERA", True, (130, 130, 190))
        surface.blit(lbl, (cx + 4, cy + 4))

    # ── HP bat tu ─────────────────────────────────────────────────────────────
    def _draw_immortal_hp(self, surface):
        bar_x, bar_y = 14, self.screen_h - 68
        bar_w, bar_h = 260, 22
        pygame.draw.rect(surface, (30, 0, 0),
                         (bar_x-2, bar_y-2, bar_w+4, bar_h+4), border_radius=5)
        pygame.draw.rect(surface, (20, 20, 20),
                         (bar_x, bar_y, bar_w, bar_h), border_radius=4)
        pygame.draw.rect(surface, (30, 200, 80),
                         (bar_x, bar_y, bar_w, bar_h), border_radius=4)
        shine = pygame.Surface((bar_w, bar_h // 2), pygame.SRCALPHA)
        shine.fill((255, 255, 255, 35))
        surface.blit(shine, (bar_x, bar_y))
        pygame.draw.rect(surface, (180, 220, 180),
                         (bar_x-2, bar_y-2, bar_w+4, bar_h+4), 1, border_radius=5)
        lbl = self.font_hint.render("HP  MAX  [IMMORTAL MODE]", True, (200, 240, 200))
        surface.blit(lbl, (bar_x + 4, bar_y + 3))

    # ── Gesture progress bar ─────────────────────────────────────────────────
    def _draw_gesture_bar(self, surface, preview, progress):
        names = {
            'iron_gauntlets': 'Iron Gauntlets',
            'sword':          'Sword',
            'bow':            'Bow',
            'grenade':        'Grenade',
            'gun':            'Gun',
            'mine':           'Mine',
        }
        label = names.get(preview, preview)
        bx = self.screen_w // 2 - 120
        by = 52
        bw, bh = 240, 28
        bg = pygame.Surface((bw + 4, bh + 4), pygame.SRCALPHA)
        bg.fill((0, 0, 0, 140))
        surface.blit(bg, (bx - 2, by - 2))
        pygame.draw.rect(surface, (30, 30, 50), (bx, by, bw, bh), border_radius=4)
        fill_c = (100, 200, 255) if progress < 1.0 else (50, 255, 150)
        pygame.draw.rect(surface, fill_c,
                         (bx, by, int(bw * progress), bh), border_radius=4)
        pygame.draw.rect(surface, (150, 150, 200), (bx, by, bw, bh), 1, border_radius=4)
        txt = self.font_hint.render(label.upper() + " - HOLD...", True, (255, 255, 255))
        surface.blit(txt, (bx + bw//2 - txt.get_width()//2,
                           by + bh//2 - txt.get_height()//2))
