"""
gesture_detector.py - Nhận diện cử chỉ tay bằng MediaPipe Tasks API
Tương thích mediapipe >= 0.10.14 (Tasks API, không dùng mp.solutions)

Quy ước landmark (21 điểm mỗi tay):
  0: Wrist
  1-4: Thumb   5-8: Index   9-12: Middle   13-16: Ring   17-20: Pinky

Gesture => Vũ khí:
  Iron Gauntlets : 2 nắm tay xa nhau (boxing stance)
  Sword          : 2 nắm tay gần, ngang hàng theo trục X => kéo ra
  Bow            : 2 nắm tay gần, lệch trục Y rõ ràng => kéo ra
  Grenade        : 1 tay nắm đấm
  Gun            : 2 tay: ngón trỏ + ngón giữa duỗi
"""

import cv2
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision as mp_vision

import numpy as np
import time
import math
import os
import urllib.request


# ─── Tải model hand_landmarker.task (tự động 1 lần) ──────────────────────
_MODEL_URL  = (
    "https://storage.googleapis.com/mediapipe-models/"
    "hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"
)
_MODEL_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "assets", "hand_landmarker.task"
)

def _ensure_model():
    if os.path.exists(_MODEL_PATH):
        return
    os.makedirs(os.path.dirname(_MODEL_PATH), exist_ok=True)
    print("[GestureDetector] Dang tai model hand_landmarker.task (~8 MB)...")
    urllib.request.urlretrieve(_MODEL_URL, _MODEL_PATH)
    print(f"[GestureDetector] Da luu: {_MODEL_PATH}")


# ─── HandData: bọc kết quả Tasks API ────────────────────────────────────
class HandData:
    """
    Dong goi 21 landmark cua 1 ban tay.
    landmarks_list : list[NormalizedLandmark] tu Tasks API
    label          : 'Left' hoac 'Right'
    img_shape      : (h, w) cua frame
    """
    def __init__(self, landmarks_list, label: str, img_shape):
        self.label = label
        h, w = img_shape[:2]
        self.h, self.w = h, w
        # Toa do pixel
        self.pts = [(int(lm.x * w), int(lm.y * h)) for lm in landmarks_list]
        # Toa do chuan hoa (x, y, z)
        self.pts_norm = [(lm.x, lm.y, lm.z) for lm in landmarks_list]

    # ── Tien ich ngon tay ─────────────────────────────────────────────────
    _TIPS = {'thumb': 4, 'index': 8, 'middle': 12, 'ring': 16, 'pinky': 20}
    _PIPS = {'index': 6, 'middle': 10, 'ring': 14, 'pinky': 18}

    def tip(self, finger):
        return self.pts[self._TIPS[finger]]

    def is_finger_up(self, finger: str) -> bool:
        if finger == 'thumb':
            tip_x = self.pts_norm[4][0]
            ip_x  = self.pts_norm[3][0]
            return tip_x < ip_x if self.label == 'Right' else tip_x > ip_x
        tip_y = self.pts_norm[self._TIPS[finger]][1]
        pip_y = self.pts_norm[self._PIPS[finger]][1]
        return tip_y < pip_y - 0.04

    def is_fist(self) -> bool:
        return not any(self.is_finger_up(f) for f in ['index', 'middle', 'ring', 'pinky'])

    def finger_count_up(self) -> int:
        return sum(self.is_finger_up(f) for f in ['thumb', 'index', 'middle', 'ring', 'pinky'])

    def hand_center(self):
        xs = [p[0] for p in self.pts]
        ys = [p[1] for p in self.pts]
        return (int(np.mean(xs)), int(np.mean(ys)))

    def bbox_area(self) -> float:
        """Dien tich bounding box cua 21 landmark (pixel^2)"""
        xs = [p[0] for p in self.pts]
        ys = [p[1] for p in self.pts]
        return float((max(xs) - min(xs)) * (max(ys) - min(ys)))

    def wrist_to_mcp_vec(self):
        """Vector tu wrist(0) den MCP ngon giua(9) - uoc tinh huong canh tay"""
        wx, wy = self.pts[0]
        mx, my = self.pts[9]
        return (mx - wx, my - wy)


# ─── GestureDetector ─────────────────────────────────────────────────────
class GestureDetector:
    """
    Nhan dien 5 vu khi bang cu chi tay qua MediaPipe Tasks API.

    Logic equip (giu cu chi HOLD_TIME giay):
      - iron_gauntlets : 2 nam tay xa nhau (dist >= NEAR_DIST_PX)
      - sword          : 2 nam tay gan, ngang hang Y => keo ra xa
      - bow            : 2 nam tay gan, lech Y ro rang => keo ra xa
      - grenade        : 1 tay nam dau (tay con lai khong detect)
      - gun            : 2 tay: index + middle duoi

    Logic attack:
      - iron_gauntlets : dien tich bbox giam nhanh (tay day ra gan camera)
      - sword          : velocity nam tay > SWORD_VEL
      - bow            : tay giua co dinh, tay keo duoi ngon tro ra => nha ten
      - grenade        : mo tay (>=3 ngon) + velocity cao + goc canh tay tro thanh huong nem
      - gun            : phim SPACE
    """

    HOLD_TIME        = 0.35   # giay giu cu chi de kich hoat equip
    NEAR_DIST_PX     = 110    # pixel; 2 tay coi la "gan nhau"
    BOW_PULL_BASE_PX = 140    # khoang cach toi thieu de tinh charge cung
    BOW_Y_THRESH     = 0.12   # lech Y chuan hoa de phan biet bow/sword

    SWORD_VEL        = 7      # pixel/frame de kich hoat chem kiem

    # Punch: bbox detection
    PUNCH_AREA_BIG   = 6000   # px^2; bbox to = tay xa camera/ngang tay
    PUNCH_SHRINK     = 0.72   # ty le thu nho de trigger punch

    # Grenade throw
    THROW_VEL        = 6      # pixel/frame toi thieu de kich hoat nem luu dan

    def __init__(self):
        _ensure_model()

        base_options = mp_python.BaseOptions(model_asset_path=_MODEL_PATH)
        options = mp_vision.HandLandmarkerOptions(
            base_options=base_options,
            running_mode=mp_vision.RunningMode.VIDEO,
            num_hands=2,
            min_hand_detection_confidence=0.55,
            min_hand_presence_confidence=0.50,
            min_tracking_confidence=0.50,
        )
        self._landmarker = mp_vision.HandLandmarker.create_from_options(options)
        self._ts_ms = 0   # timestamp tang dan cho VIDEO mode

        # ── Trang thai equip ─────────────────────────────────────────────
        self.current_weapon   = None
        self._pending         = None
        self._gesture_t0      = 0.0
        self._locked          = False

        # Stage-2 detection (sword/bow)
        self._stage1_weapon   = None
        self._stage1_t0       = 0.0

        # ── Trang thai tan cong ──────────────────────────────────────────
        self._prev_centers    = {}     # {label: (x, y)}
        self._prev_bbox_area  = {}     # {label: float}  cho punch detection

        self.bow_draw_level   = 0.0
        self.bow_hand_pos     = None
        self.string_hand_pos  = None

        # Bow: theo doi tay cung co dinh va tay keo
        self._bow_hold_label  = None   # label cua tay giu cung (it di chuyen hon)

        # Grenade: luu vi tri bat dau canh tay de tinh goc
        self._grenade_throw_start = {}  # {label: (wx, wy)} toa do wrist luc bat dau nem

        # Optical Flow cho grenade: luu frame xam truoc va diem wrist
        self._of_prev_gray  = None   # frame xam truoc (numpy array)
        self._of_prev_pts   = None   # diem wrist truoc [[x, y]] (float32)
        self._of_wrist_vel  = (0.0, 0.0)  # velocity wrist tinh tu optical flow

        # Gun: theo doi trang thai xoe/nam de trigger ban
        self._prev_gun_open   = False  # frame truoc co ngon xoe khong

        # Mine: theo doi thoi gian giu gesture
        self._mine_hold_t0 = None

        self.debug_info = {}
        print("[GestureDetector] Khoi tao Tasks API thanh cong.")

    # ── Xu ly frame chinh ────────────────────────────────────────────────
    def process(self, bgr_frame, space_pressed: bool = False) -> dict:
        """
        Tra ve dict:
          weapon, weapon_changed, attack, bow_draw_level,
          bow_hand_pos, string_hand_pos, gun_firing,
          hands, gesture_preview, gesture_progress,
          grenade_throw_angle (goc canh tay khi nem, radian)
        """
        h_px, w_px = bgr_frame.shape[:2]
        rgb = cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2RGB)

        self._ts_ms += 16   # ~60fps (giam tu 33ms xuong 16ms)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        result   = self._landmarker.detect_for_video(mp_image, self._ts_ms)

        # Chuyen ket qua thanh list HandData
        hands: list[HandData] = []
        if result.hand_landmarks and result.handedness:
            for lm_list, hd_list in zip(result.hand_landmarks, result.handedness):
                label = hd_list[0].category_name   # 'Left' / 'Right'
                hands.append(HandData(lm_list, label, bgr_frame.shape))

        # ── Optical Flow cho grenade (truoc khi classify attack) ───────────
        if self.current_weapon == 'grenade' and hands:
            gray = cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2GRAY)
            self._update_optical_flow(gray, hands)

        # ── Vu khi duoc chon bang phim 1-6, khong auto-equip qua gesture ──
        weapon_changed = False

        # ── Detect tan cong ─────────────────────────────────────────────
        attack, bow_draw, bow_hand, str_hand, throw_angle = \
            self._classify_attack(hands, space_pressed)
        self.bow_draw_level  = bow_draw
        self.bow_hand_pos    = bow_hand
        self.string_hand_pos = str_hand

        # Cap nhat vi tri tay va bbox cho frame tiep theo
        for h in hands:
            self._prev_centers[h.label]   = h.hand_center()
            self._prev_bbox_area[h.label] = h.bbox_area()

        # Gun: tinh tam dau ngon tay (trung binh tips 8,12,16,20) de lam huong ban
        # SAU FIX TAY: label 'Left' tu MediaPipe = tay PHAI that cua nguoi dung
        # => tim tay cua nguoi dung bang label nguoc lai
        gun_tips_center = None
        for h in hands:
            # 'Left' (MediaPipe) = tay PHAI that => dung de tinh huong ban sung
            if h.label == 'Left' and len(h.pts) >= 21:
                tips = [h.pts[i] for i in (8, 12, 16, 20)]
                tx = sum(p[0] for p in tips) // 4
                ty = sum(p[1] for p in tips) // 4
                gun_tips_center = (tx, ty)
                break
        if gun_tips_center is None and hands:
            h = hands[0]
            if len(h.pts) >= 21:
                tips = [h.pts[i] for i in (8, 12, 16, 20)]
                tx = sum(p[0] for p in tips) // 4
                ty = sum(p[1] for p in tips) // 4
                gun_tips_center = (tx, ty)

        # Gun firing: trigger khi tay duoi thang (>= 3 ngon) roi nam lai
        gun_firing = False
        if self.current_weapon == 'gun':
            # Trang thai hien tai: tay duoi thang (>= 3 ngon)
            curr_gun_open = any(h.finger_count_up() >= 3 for h in hands)
            # Chi trigger ban khi frame truoc xoe, frame nay nam (transition)
            if self._prev_gun_open and not curr_gun_open and len(hands) > 0:
                gun_firing = True
            self._prev_gun_open = curr_gun_open
            if gun_firing:
                attack = 'shoot'

        self.debug_info = {
            'hands'   : len(hands),
            'weapon'  : self.current_weapon,
            'bow'     : f'{bow_draw:.2f}',
            'space'   : space_pressed,
            'attack'  : attack,
        }

        return {
            'weapon'             : self.current_weapon,
            'weapon_changed'     : weapon_changed,
            'attack'             : attack,
            'bow_draw_level'     : bow_draw,
            'bow_hand_pos'       : bow_hand,
            'string_hand_pos'    : str_hand,
            'gun_firing'         : gun_firing,
            'gun_tips_center'    : gun_tips_center,
            'hands'              : hands,
            'gesture_preview'    : None,
            'gesture_progress'   : 0.0,
            'grenade_throw_angle': throw_angle,
            'bow_direction'      : getattr(self, '_bow_direction', None),
            'bow_force'          : getattr(self, '_bow_force', 0.0),
            'mine_pos'           : getattr(self, '_mine_pos', None),
        }

    # ── Xu ly equip gesture (debounce + lock) ────────────────────────────
    def _process_equip(self, hands, w, h):
        now = time.time()
        weapon_changed   = False
        gesture_preview  = None
        gesture_progress = 0.0

        raw_gesture = self._detect_equip_gesture(hands, w, h)

        if raw_gesture is None:
            self._pending = None
            self._locked  = False
            return raw_gesture, gesture_preview, gesture_progress, weapon_changed

        if raw_gesture != self._pending:
            self._pending    = raw_gesture
            self._gesture_t0 = now
            self._locked     = False

        held = now - self._gesture_t0
        gesture_progress = min(1.0, held / self.HOLD_TIME)
        gesture_preview  = raw_gesture

        _WEAPON_MAP = {
            'iron_gauntlets': 'iron_gauntlets',
            'sword'         : 'sword',
            'bow'           : 'bow',
            'grenade'       : 'grenade',
            'gun'           : 'gun',
            'mine'          : 'mine',
        }

        if held >= self.HOLD_TIME and not self._locked and raw_gesture in _WEAPON_MAP:
            prev = self.current_weapon
            self.current_weapon = _WEAPON_MAP[raw_gesture]
            weapon_changed = (self.current_weapon != prev)
            self._locked   = True

        return raw_gesture, gesture_preview, gesture_progress, weapon_changed

    # ── Phan loai gesture equip ──────────────────────────────────────────
    def _detect_equip_gesture(self, hands, w, h):
        if len(hands) == 2:
            return self._two_hand_equip(hands[0], hands[1], w, h)
        if len(hands) == 1:
            return self._one_hand_equip(hands[0])
        self._stage1_weapon = None
        return None

    def _two_hand_equip(self, h1: HandData, h2: HandData, w: int, h: int):
        dist       = self._dist(h1, h2)
        both_fist  = h1.is_fist() and h2.is_fist()
        STAGE1_MAX = self.NEAR_DIST_PX * 1.6
        STAGE2_MIN = self.NEAR_DIST_PX * 1.4

        # ── Mine: ngon cai + ngon tro 2 tay tao vong tron (chap 2 dau ngon cai) ──
        # Dieu kien: ca 2 tay co ngon cai + ngon tro duoi, 2 tip ngon cai gan nhau
        thumb1_up = h1.is_finger_up('thumb') and h1.is_finger_up('index')
        thumb2_up = h2.is_finger_up('thumb') and h2.is_finger_up('index')
        if thumb1_up and thumb2_up:
            t1 = h1.tip('thumb')
            t2 = h2.tip('thumb')
            thumb_dist = math.sqrt((t1[0]-t2[0])**2 + (t1[1]-t2[1])**2)
            if thumb_dist < self.NEAR_DIST_PX:
                self._stage1_weapon = None
                return 'mine'

        # ── Sung: ngon tro + ngon giua duoi ca 2 tay ─────────────────────
        gun1 = (h1.is_finger_up('index') and h1.is_finger_up('middle')
                and not h1.is_finger_up('ring') and not h1.is_finger_up('pinky'))
        gun2 = (h2.is_finger_up('index') and h2.is_finger_up('middle')
                and not h2.is_finger_up('ring') and not h2.is_finger_up('pinky'))
        if gun1 and gun2:
            self._stage1_weapon = None
            return 'gun'

        if not both_fist:
            self._stage1_weapon = None
            return None

        # Stage 2: da set stage1, 2 tay keo du xa
        if self._stage1_weapon is not None and dist >= STAGE2_MIN:
            return 'sword' if self._stage1_weapon == 'sword_ready' else 'bow'

        # Stage 1: 2 tay gan nhau => phan biet sword/bow
        if dist < STAGE1_MAX:
            cy1 = h1.pts_norm[9][1]
            cy2 = h2.pts_norm[9][1]
            y_diff = abs(cy1 - cy2)
            self._stage1_weapon = 'sword_ready' if y_diff < self.BOW_Y_THRESH else 'bow_ready'
            return None

        # Vung trung gian
        if self._stage1_weapon is not None:
            return None

        # Gang tay sat: 2 tay xa ngay tu dau
        if dist >= STAGE2_MIN:
            c1, c2 = h1.hand_center(), h2.hand_center()
            in_frame = (0.07 < c1[0]/w < 0.93 and 0.07 < c1[1]/h < 0.93 and
                        0.07 < c2[0]/w < 0.93 and 0.07 < c2[1]/h < 0.93)
            if in_frame:
                return 'iron_gauntlets'

        return None

    def _one_hand_equip(self, h: HandData):
        if h.is_fist():
            return 'grenade'
        return None

    # ── Phan loai tan cong ───────────────────────────────────────────────
    def _classify_attack(self, hands: list, space_pressed: bool):
        """
        Tra ve: (attack, bow_draw, bow_hand, string_hand, throw_angle)
        throw_angle: goc (radian) cua canh tay khi nem luu dan (None neu khong co)
        """
        attack     = None
        bow_draw   = 0.0
        bow_hand   = None
        str_hand   = None
        throw_angle= None
        weapon     = self.current_weapon

        # ── Iron Gauntlets: 2 tay nam gan nhau, 1 tay bbox tang >= 30% ────
        if weapon == 'iron_gauntlets' and len(hands) == 2:
            h1, h2 = hands[0], hands[1]
            both_fist = h1.is_fist() and h2.is_fist()
            dist_2h = self._dist(h1, h2)
            if both_fist and dist_2h < self.NEAR_DIST_PX * 2:
                for h in hands:
                    curr_area = h.bbox_area()
                    prev_area = self._prev_bbox_area.get(h.label, 0)
                    # Trigger: bbox tang >= 30% (tay dam ra xa)
                    if (prev_area > 300
                            and curr_area > prev_area * 1.30
                            and curr_area > 500):
                        attack = 'punch_right' if h.label == 'Right' else 'punch_left'
                        break

        # ── Sword: velocity nam tay ───────────────────────────────────────
        elif weapon == 'sword':
            for h in hands:
                if h.label in self._prev_centers:
                    diff = (np.array(h.hand_center())
                            - np.array(self._prev_centers[h.label]))
                    spd  = np.linalg.norm(diff)
                    if spd > self.SWORD_VEL:
                        ang = math.degrees(math.atan2(-diff[1], diff[0]))
                        if   -60  < ang <  60:          attack = 'slash_right'
                        elif  120 < ang or ang < -120:  attack = 'slash_left'
                        elif  ang >  60:                attack = 'slash_up'
                        else:                           attack = 'slash_down'
                        break

        # ── Bow: cai tien theo tham khao ─────────────────────────────────
        elif weapon == 'bow' and len(hands) == 2:
            attack, bow_draw, bow_hand, str_hand = self._bow_attack(hands)

        # ── Grenade: nen + velocity + goc canh tay ───────────────────────
        elif weapon == 'grenade':
            attack, throw_angle = self._grenade_attack(hands)

        # ── Mine: giu gesture du HOLD_TIME -> dat min─────────────────────────
        elif weapon == 'mine':
            # Dieu kien: dang giu gesture mine (2 ngon cai chap) va giu >= HOLD_TIME
            attack = self._mine_attack(hands)

        # -- Gun: xu ly qua gun_firing flag tren process()
        # (attack 'shoot' duoc set trong process() neu gun_firing = True)

        return attack, bow_draw, bow_hand, str_hand, throw_angle

    # ── Bow attack: huong ban = tay phai -> tay trai, luc = khoang cach ──
    def _bow_attack(self, hands: list):
        """
        Logic bow:
        - Huong ban: duong thang tu tay PHAI that den tay TRAI that
        - Luc (draw_level): khoang cach 2 tay, clamp [0..1]
        - Trigger: tay PHAI that (label 'Left' MediaPipe) dang nam roi mo ra
        """
        bow_draw   = 0.0
        bow_hand   = None
        str_hand   = None
        attack     = None

        h1, h2 = hands[0], hands[1]
        dist = self._dist(h1, h2)

        # SAU FIX TAY: label 'Right' (MediaPipe) = tay TRAI that
        #              label 'Left'  (MediaPipe) = tay PHAI that
        left_h  = None   # tay TRAI that
        right_h = None   # tay PHAI that
        for h in hands:
            if h.label == 'Right':
                left_h = h
            elif h.label == 'Left':
                right_h = h

        if left_h is None or right_h is None:
            # Fallback: tay it di chuyen = tay trai
            vel1 = float(np.linalg.norm(
                np.array(h1.hand_center()) - np.array(self._prev_centers.get(h1.label, h1.hand_center()))))
            vel2 = float(np.linalg.norm(
                np.array(h2.hand_center()) - np.array(self._prev_centers.get(h2.label, h2.hand_center()))))
            if vel1 <= vel2:
                left_h, right_h = h1, h2
            else:
                left_h, right_h = h2, h1

        # bow_hand = tay trai (giu cung), str_hand = tay phai (keo day)
        bow_hand = left_h.hand_center()
        str_hand = right_h.hand_center()

        # Draw level: khoang cach 2 tay
        bow_draw = min(1.0, max(0.0,
                   (dist - self.BOW_PULL_BASE_PX) / 150.0))

        # Huong ban: tu tay phai -> tay trai
        rc = np.array(right_h.hand_center(), dtype=float)
        lc = np.array(left_h.hand_center(), dtype=float)
        direction = lc - rc  # vector tu tay phai den tay trai
        dir_norm = float(np.linalg.norm(direction))
        if dir_norm > 0:
            direction = direction / dir_norm
        self._bow_direction = (float(direction[0]), float(direction[1]))
        self._bow_force = bow_draw  # luc = draw level

        # Trigger: tay phai dang nam roi mo ra (fist -> open >= 3 ngon)
        right_open = right_h.finger_count_up() >= 3
        prev_right_open = getattr(self, '_prev_right_open', False)

        release = (
            bow_draw > 0.05
            and right_open
            and not prev_right_open
        )

        self._prev_right_open = right_open

        if release:
            attack   = 'release_arrow'
            bow_draw = self.bow_draw_level  # giu charge level luc nha

        return attack, bow_draw, bow_hand, str_hand

    # ── Mine attack ────────────────────────────────────────────────────────
    def _mine_attack(self, hands: list):
        """
        Dat min khi 2 ban tay chum lai (tat ca ngon khong duoi),
        vi tri = trong tam tat ca landmark 2 tay.
        """
        if len(hands) < 2:
            self._mine_hold_t0 = None
            self._mine_pos = None
            return None

        h1, h2 = hands[0], hands[1]

        # Dieu kien: ca 2 tay deu chum tat ca ngon (ke ca ngon cai)
        if not (h1.finger_count_up() == 0 and h2.finger_count_up() == 0):
            self._mine_hold_t0 = None
            self._mine_pos = None
            return None

        # 2 tay phai gan nhau
        dist_2h = self._dist(h1, h2)
        if dist_2h >= self.NEAR_DIST_PX * 1.5:
            self._mine_hold_t0 = None
            self._mine_pos = None
            return None

        # Tinh trong tam tat ca landmark 2 tay
        all_pts = h1.pts + h2.pts  # 42 diem
        cx = sum(p[0] for p in all_pts) / len(all_pts)
        cy = sum(p[1] for p in all_pts) / len(all_pts)
        self._mine_pos = (cx, cy)

        # Giu gesture du thoi gian
        now = time.time()
        if self._mine_hold_t0 is None:
            self._mine_hold_t0 = now

        held = now - self._mine_hold_t0
        if held >= self.HOLD_TIME:
            self._mine_hold_t0 = None
            return 'place_mine'

        return None

    # ── Optical Flow: cap nhat wrist velocity ────────────────────────────
    def _update_optical_flow(self, gray_frame, hands: list):
        """
        Dung cv2.calcOpticalFlowPyrLK de theo doi wrist point qua 2 frame.
        Cap nhat self._of_wrist_vel = (vx, vy) px/frame.
        """
        if not hands:
            self._of_prev_gray = gray_frame.copy()
            self._of_prev_pts  = None
            return

        # Lay wrist cua tay dau tien
        wrist_px = np.array([[hands[0].pts[0][0], hands[0].pts[0][1]]],
                             dtype=np.float32)

        if self._of_prev_gray is not None and self._of_prev_pts is not None:
            try:
                next_pts, status, _ = cv2.calcOpticalFlowPyrLK(
                    self._of_prev_gray, gray_frame,
                    self._of_prev_pts, None,
                    winSize=(21, 21), maxLevel=3,
                    criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 10, 0.03)
                )
                if status is not None and status[0][0] == 1:
                    dx = float(next_pts[0][0][0] - self._of_prev_pts[0][0][0])
                    dy = float(next_pts[0][0][1] - self._of_prev_pts[0][0][1])
                    # Smoothing: EMA
                    alpha = 0.6
                    self._of_wrist_vel = (
                        alpha * dx + (1 - alpha) * self._of_wrist_vel[0],
                        alpha * dy + (1 - alpha) * self._of_wrist_vel[1],
                    )
            except Exception:
                pass

        self._of_prev_gray = gray_frame.copy()
        self._of_prev_pts  = wrist_px

    # ── Grenade attack ────────────────────────────────────────────────────
    def _grenade_attack(self, hands: list):
        """
        Kich hoat nem:
          - Mo ban tay (>= 3 ngon)
          - Velocity center > THROW_VEL (hoac OF velocity cao)
          - Uu tien goc tu Optical Flow wrist velocity
          - Fallback: goc canh tay (wrist -> MCP ngon giua)
        """
        attack      = None
        throw_angle = None

        for h in hands:
            if h.label not in self._prev_centers:
                continue

            curr_center = np.array(h.hand_center())
            prev_center = np.array(self._prev_centers[h.label])
            vel = float(np.linalg.norm(curr_center - prev_center))

            # Kiem tra them Optical Flow velocity
            of_vx, of_vy = self._of_wrist_vel
            of_speed = math.sqrt(of_vx**2 + of_vy**2)

            open_enough = h.finger_count_up() >= 3

            if open_enough and (vel > self.THROW_VEL or of_speed > self.THROW_VEL * 0.8):
                # Uu tien Optical Flow neu co du toc do
                if of_speed > self.THROW_VEL * 0.5:
                    throw_angle = math.atan2(-of_vy, of_vx)
                else:
                    # Fallback: goc canh tay
                    vx_arm, vy_arm = h.wrist_to_mcp_vec()
                    throw_angle = math.atan2(-vy_arm, vx_arm)
                attack = 'throw_grenade'
                # Reset velocity sau khi nem
                self._of_wrist_vel = (0.0, 0.0)
                break

        return attack, throw_angle

    # ── Tien ich ─────────────────────────────────────────────────────────
    def _dist(self, h1: HandData, h2: HandData) -> float:
        c1 = np.array(h1.hand_center())
        c2 = np.array(h2.hand_center())
        return float(np.linalg.norm(c1 - c2))

    def draw_landmarks(self, frame, hands: list):
        """Ve landmark len frame de debug"""
        CONNECTIONS = [
            (0,1),(1,2),(2,3),(3,4),
            (0,5),(5,6),(6,7),(7,8),
            (0,9),(9,10),(10,11),(11,12),
            (0,13),(13,14),(14,15),(15,16),
            (0,17),(17,18),(18,19),(19,20),
            (5,9),(9,13),(13,17),
        ]
        for h in hands:
            for a, b in CONNECTIONS:
                cv2.line(frame, h.pts[a], h.pts[b], (80, 220, 80), 1)
            for (x, y) in h.pts:
                cv2.circle(frame, (x, y), 3, (0, 255, 100), -1)
        return frame

    def release(self):
        self._landmarker.close()
