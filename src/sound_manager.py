"""
sound_manager.py - Tạo âm thanh SFX bằng numpy (không cần file ngoài)
Dùng numpy để synthesize âm thanh 8-bit cho mọi hiệu ứng
"""

import pygame
import numpy as np


def make_sound(freq_list, duration_ms=200, volume=0.5, wave_type='square', sample_rate=44100):
    """Tổng hợp âm thanh 8-bit từ danh sách tần số"""
    num_samples = int(sample_rate * duration_ms / 1000)
    t = np.linspace(0, duration_ms / 1000, num_samples, False)
    wave = np.zeros(num_samples)

    for i, (freq, dur_frac) in enumerate(freq_list):
        start = int(num_samples * sum(f[1] for f in freq_list[:i]))
        end = int(start + num_samples * dur_frac)
        if start >= num_samples:
            break
        end = min(end, num_samples)
        t_seg = np.linspace(0, dur_frac * duration_ms / 1000, end - start, False)
        if wave_type == 'square':
            seg = np.sign(np.sin(2 * np.pi * freq * t_seg))
        elif wave_type == 'sine':
            seg = np.sin(2 * np.pi * freq * t_seg)
        elif wave_type == 'sawtooth':
            seg = 2 * (freq * t_seg - np.floor(0.5 + freq * t_seg))
        elif wave_type == 'noise':
            seg = np.random.uniform(-1, 1, len(t_seg))
        else:
            seg = np.sign(np.sin(2 * np.pi * freq * t_seg))

        # envelope: fade out cuối đoạn
        fade = np.linspace(1.0, 0.1, len(seg))
        wave[start:end] += seg * fade

    # Normalize
    peak = np.max(np.abs(wave))
    if peak > 0:
        wave = wave / peak * volume

    # Convert to int16
    audio = (wave * 32767).astype(np.int16)

    # Stereo
    stereo = np.column_stack([audio, audio])
    return pygame.sndarray.make_sound(stereo)


def make_punch_sound():
    """Tiếng đấm nặng - low thud"""
    return make_sound(
        [(180, 0.3), (120, 0.4), (80, 0.3)],
        duration_ms=180, volume=0.6, wave_type='square'
    )


def make_sword_swing_sound():
    """Tiếng vung kiếm - whoosh"""
    return make_sound(
        [(800, 0.1), (600, 0.2), (400, 0.3), (200, 0.4)],
        duration_ms=200, volume=0.5, wave_type='sawtooth'
    )


def make_sword_hit_sound():
    """Tiếng kiếm chạm - clang"""
    return make_sound(
        [(1200, 0.1), (900, 0.2), (600, 0.3), (400, 0.4)],
        duration_ms=250, volume=0.7, wave_type='square'
    )


def make_bow_draw_sound():
    """Tiếng kéo cung - creak"""
    return make_sound(
        [(300, 0.3), (350, 0.4), (380, 0.3)],
        duration_ms=400, volume=0.4, wave_type='sawtooth'
    )


def make_bow_release_sound():
    """Tiếng nhả cung - twang"""
    return make_sound(
        [(600, 0.15), (400, 0.25), (200, 0.3), (100, 0.3)],
        duration_ms=300, volume=0.6, wave_type='sine'
    )


def make_arrow_hit_sound():
    """Tiếng tên trúng"""
    return make_sound(
        [(500, 0.2), (300, 0.3), (150, 0.5)],
        duration_ms=200, volume=0.5, wave_type='square'
    )


def make_grenade_throw_sound():
    """Tiếng ném lựu đạn"""
    return make_sound(
        [(200, 0.5), (150, 0.5)],
        duration_ms=150, volume=0.3, wave_type='sine'
    )


def make_explosion_sound():
    """Tiếng nổ lớn"""
    return make_sound(
        [(100, 0.2), (80, 0.3), (60, 0.3), (40, 0.2)],
        duration_ms=600, volume=0.8, wave_type='noise'
    )


def make_mine_explosion_sound():
    """Tiếng nổ mìn - nặng hơn, kéo dài hơn, bass sâu"""
    num_samples = int(44100 * 0.9)  # 900ms
    t = np.linspace(0, 0.9, num_samples, False)
    # Bass rumble (low freq noise + sine)
    bass = np.sin(2 * np.pi * 40 * t) * 0.5
    bass += np.sin(2 * np.pi * 60 * t) * 0.3
    # Noise burst (decay nhanh)
    noise = np.random.uniform(-1, 1, num_samples)
    noise_env = np.exp(-t * 6)
    # Mid crunch
    mid = np.sign(np.sin(2 * np.pi * 120 * t)) * 0.2
    mid_env = np.exp(-t * 4)
    # Combine
    wave = bass * np.exp(-t * 2) + noise * noise_env * 0.7 + mid * mid_env
    peak = np.max(np.abs(wave))
    if peak > 0:
        wave = wave / peak * 0.9
    audio = (wave * 32767).astype(np.int16)
    stereo = np.column_stack([audio, audio])
    return pygame.sndarray.make_sound(stereo)


def make_gunshot_sound():
    """Tiếng bắn súng"""
    return make_sound(
        [(800, 0.05), (400, 0.1), (200, 0.15), (100, 0.7)],
        duration_ms=150, volume=0.7, wave_type='noise'
    )


def make_gun_hit_sound():
    """Tiếng đạn trúng"""
    return make_sound(
        [(600, 0.2), (300, 0.4), (150, 0.4)],
        duration_ms=180, volume=0.5, wave_type='square'
    )


def make_summon_sound(weapon):
    """Tiếng triệu hồi vũ khí"""
    if weapon == 'iron_gauntlets':
        return make_sound(
            [(200, 0.2), (300, 0.3), (400, 0.3), (500, 0.2)],
            duration_ms=350, volume=0.5, wave_type='square'
        )
    elif weapon == 'sword':
        return make_sound(
            [(600, 0.2), (800, 0.3), (1000, 0.3), (800, 0.2)],
            duration_ms=400, volume=0.5, wave_type='sine'
        )
    elif weapon == 'bow':
        return make_sound(
            [(400, 0.3), (500, 0.3), (400, 0.2), (300, 0.2)],
            duration_ms=350, volume=0.4, wave_type='sawtooth'
        )
    elif weapon == 'grenade':
        return make_sound(
            [(300, 0.3), (250, 0.4), (200, 0.3)],
            duration_ms=300, volume=0.4, wave_type='square'
        )
    elif weapon == 'gun':
        return make_sound(
            [(150, 0.3), (200, 0.4), (250, 0.3)],
            duration_ms=250, volume=0.4, wave_type='noise'
        )
    return make_sound([(400, 1.0)], duration_ms=200)


def make_enemy_hit_sound():
    return make_sound(
        [(300, 0.3), (200, 0.4), (150, 0.3)],
        duration_ms=200, volume=0.5, wave_type='square'
    )


def make_enemy_hit_punch_sound():
    """Tieng trung dam - thud nang, bass sau"""
    return make_sound(
        [(150, 0.2), (100, 0.3), (70, 0.3), (50, 0.2)],
        duration_ms=250, volume=0.6, wave_type='square'
    )


def make_enemy_hit_sword_sound():
    """Tieng kiem chem trung - sac, kim loai"""
    return make_sound(
        [(1000, 0.1), (700, 0.2), (500, 0.3), (300, 0.4)],
        duration_ms=220, volume=0.6, wave_type='sawtooth'
    )


def make_enemy_hit_bow_sound():
    """Tieng ten cam trung - thud + rung"""
    return make_sound(
        [(400, 0.15), (250, 0.25), (180, 0.3), (120, 0.3)],
        duration_ms=200, volume=0.5, wave_type='sine'
    )


def make_enemy_hit_grenade_sound():
    """Tieng no luu dan trung - bung no lon"""
    num_samples = int(44100 * 0.5)  # 500ms
    t = np.linspace(0, 0.5, num_samples, False)
    bass = np.sin(2 * np.pi * 60 * t) * 0.4
    noise = np.random.uniform(-1, 1, num_samples)
    noise_env = np.exp(-t * 8)
    crunch = np.sign(np.sin(2 * np.pi * 150 * t)) * 0.3
    crunch_env = np.exp(-t * 5)
    wave = bass * np.exp(-t * 3) + noise * noise_env * 0.6 + crunch * crunch_env
    peak = np.max(np.abs(wave))
    if peak > 0:
        wave = wave / peak * 0.7
    audio = (wave * 32767).astype(np.int16)
    stereo = np.column_stack([audio, audio])
    return pygame.sndarray.make_sound(stereo)


def make_enemy_hit_gun_sound():
    """Tieng dan sung trung - nhon, nhanh"""
    return make_sound(
        [(800, 0.1), (500, 0.2), (250, 0.3), (100, 0.4)],
        duration_ms=150, volume=0.55, wave_type='noise'
    )


def make_enemy_hit_mine_sound():
    """Tieng min no trung - cuc manh, bass rumble"""
    num_samples = int(44100 * 0.7)  # 700ms
    t = np.linspace(0, 0.7, num_samples, False)
    bass = np.sin(2 * np.pi * 35 * t) * 0.5 + np.sin(2 * np.pi * 55 * t) * 0.3
    noise = np.random.uniform(-1, 1, num_samples)
    noise_env = np.exp(-t * 5)
    mid = np.sign(np.sin(2 * np.pi * 100 * t)) * 0.3
    mid_env = np.exp(-t * 3)
    wave = bass * np.exp(-t * 2) + noise * noise_env * 0.5 + mid * mid_env
    peak = np.max(np.abs(wave))
    if peak > 0:
        wave = wave / peak * 0.8
    audio = (wave * 32767).astype(np.int16)
    stereo = np.column_stack([audio, audio])
    return pygame.sndarray.make_sound(stereo)


def make_enemy_die_sound():
    return make_sound(
        [(400, 0.2), (300, 0.2), (200, 0.3), (100, 0.3)],
        duration_ms=400, volume=0.6, wave_type='sawtooth'
    )


def make_player_hurt_sound():
    return make_sound(
        [(500, 0.2), (300, 0.3), (200, 0.3), (150, 0.2)],
        duration_ms=300, volume=0.6, wave_type='square'
    )


def make_bgm(bpm=120, bars=8, sample_rate=44100):
    """Tạo nhạc nền 8-bit đơn giản"""
    beat = int(sample_rate * 60 / bpm)
    total = beat * 4 * bars
    wave = np.zeros(total)
    # Melody đơn giản
    melody = [
        (440, 1), (0, 0.5), (523, 1), (0, 0.5),
        (392, 1), (0, 0.5), (349, 1.5),
        (440, 1), (0, 0.5), (494, 1), (0, 0.5),
        (523, 2),
    ]
    # Bass
    bass = [
        (110, 2), (0, 2), (98, 2), (0, 2),
        (110, 2), (0, 2), (123, 2), (0, 2),
    ]
    pos = 0
    for freq, dur_beats in melody:
        n = int(beat * dur_beats)
        if pos + n > total:
            break
        if freq > 0:
            t = np.linspace(0, dur_beats * 60 / bpm, n, False)
            seg = np.sign(np.sin(2 * np.pi * freq * t))
            fade = np.concatenate([
                np.ones(int(n * 0.7)),
                np.linspace(1, 0, n - int(n * 0.7))
            ])
            wave[pos:pos + n] += seg * fade * 0.25
        pos += n

    pos = 0
    for freq, dur_beats in bass * (bars // 2):
        n = int(beat * dur_beats)
        if pos + n > total:
            break
        if freq > 0:
            t = np.linspace(0, dur_beats * 60 / bpm, n, False)
            seg = np.sign(np.sin(2 * np.pi * freq * t))
            wave[pos:pos + n] += seg * 0.15
        pos += n

    # Normalize
    peak = np.max(np.abs(wave))
    if peak > 0:
        wave = wave / peak * 0.5
    audio = (wave * 32767).astype(np.int16)
    stereo = np.column_stack([audio, audio])
    return pygame.sndarray.make_sound(stereo)


class SoundManager:
    def __init__(self):
        pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
        self.sounds = {}
        self.bgm = None
        self._load_all()

    def _load_all(self):
        import os
        # 8bit synthesized sounds disabled — load file .ogg thay the
        self.sounds = {}
        self.bgm = None
        # Load hit sounds tu file .ogg thuc
        _hit_map = {
            'enemy_hit_punch':   'hit_iron_gauntlets.ogg',
            'enemy_hit_sword':   'hit_sword.ogg',
            'enemy_hit_bow':     'hit_bow.ogg',
            'enemy_hit_grenade': 'hit_grenade.ogg',
            'enemy_hit_gun':     'hit_gun.ogg',
            'enemy_hit_mine':    'hit_mine.ogg',
            'mine_explosion':    'hit_mine.ogg',
            'explosion':         'hit_grenade.ogg',
            'punch':             'hit_iron_gauntlets.ogg',
            'sword_hit':         'hit_sword.ogg',
            'arrow_hit':         'hit_bow.ogg',
            'gun_hit':           'hit_gun.ogg',
        }
        for key, fname in _hit_map.items():
            fpath = os.path.join('assets', 'audios', fname)
            if os.path.isfile(fpath):
                try:
                    self.sounds[key] = pygame.mixer.Sound(fpath)
                except Exception:
                    pass
        print(f"[Sound] Loaded {len(self.sounds)} .ogg sound effects")

    def play(self, name, volume=1.0):
        if name in self.sounds:
            s = self.sounds[name]
            s.set_volume(volume)
            s.play()

    def play_bgm(self, loops=-1):
        import os
        bgm_path = os.path.join('assets', 'audios', 'exotic_battle.ogg')
        if os.path.isfile(bgm_path):
            try:
                pygame.mixer.music.load(bgm_path)
                pygame.mixer.music.set_volume(0.35)
                pygame.mixer.music.play(loops=loops)
                return
            except Exception:
                pass
        # Fallback: dùng BGM tổng hợp
        if self.bgm:
            self.bgm.set_volume(0.3)
            self.bgm.play(loops=loops)

    def stop_bgm(self):
        pygame.mixer.music.stop()
        if self.bgm:
            self.bgm.stop()

    def stop_all(self):
        pygame.mixer.stop()
