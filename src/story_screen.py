"""
story_screen.py - Man hinh cot truyen (Story Screen)

Hien thi cot truyen bang tieng Anh voi hieu ung typewriter.
Xuat hien sau khi camera khoi dong xong (sau loading).
An ESC hoac SPACE de bo qua.
"""

import pygame
import math

# ── Cot truyen ────────────────────────────────────────────────────────────────
STORY_LINES = [
    "In a world overrun by alien creatures,",
    "only one warrior remains to defend humanity.",
    "",
    "Through ancient training grounds,",
    "the warrior must master six legendary weapons:",
    "",
    "  - Iron Gauntlets: raw fists of fury",
    "  - Sword: the blade of precision",
    "  - Bow: silent arrows from the shadows",
    "  - Grenade: explosive devastation",
    "  - Gun: rapid-fire annihilation",
    "  - Mine: traps for the unwary",
    "",
    "Each weapon holds a secret power,",
    "unlocked only through relentless practice.",
    "",
    "The training room awaits...",
    "Master them all, or perish trying.",
]


class StoryScreen:
    """Man hinh cot truyen voi hieu ung typewriter."""

    def __init__(self, screen_w, screen_h):
        self.screen_w = screen_w
        self.screen_h = screen_h
        self.done = False

        # Fonts
        self.font_story = pygame.font.SysFont('Courier New', 26)
        self.font_hint = pygame.font.SysFont('Arial', 18)
        self.font_title = pygame.font.SysFont('Arial', 40, bold=True)

        # Typewriter state
        self._line_idx = 0          # dong hien tai
        self._char_idx = 0          # ky tu hien tai trong dong
        self._timer = 0             # frame counter
        self._chars_per_frame = 0.6 # toc do go chu
        self._char_acc = 0.0
        self._finished = False      # da hien het chua

        # Rendered lines cache
        self._rendered_lines: list[pygame.Surface] = []
        self._all_done = False

        # Background
        self._bg = self._make_bg()
        self._t = 0

    def _make_bg(self):
        bg = pygame.Surface((self.screen_w, self.screen_h))
        bg.fill((5, 5, 20))
        import random
        rng = random.Random(42)
        for _ in range(200):
            x = rng.randint(0, self.screen_w)
            y = rng.randint(0, self.screen_h)
            r = rng.randint(1, 2)
            c = rng.randint(120, 255)
            pygame.draw.circle(bg, (c, c, c), (x, y), r)
        return bg

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_ESCAPE, pygame.K_SPACE, pygame.K_RETURN):
                if self._all_done:
                    self.done = True
                else:
                    # Bo qua typewriter, hien het ngay
                    self._skip_all()

    def _skip_all(self):
        self._rendered_lines.clear()
        for line in STORY_LINES:
            surf = self.font_story.render(line, True, (200, 220, 255))
            self._rendered_lines.append(surf)
        self._line_idx = len(STORY_LINES)
        self._all_done = True

    def update(self):
        self._t += 1

        if self._all_done:
            return

        if self._line_idx >= len(STORY_LINES):
            self._all_done = True
            return

        current_line = STORY_LINES[self._line_idx]

        if len(current_line) == 0:
            # Dong trong
            self._rendered_lines.append(
                self.font_story.render("", True, (200, 220, 255)))
            self._line_idx += 1
            self._char_idx = 0
            self._char_acc = 0.0
            return

        # Typewriter: them ky tu moi
        self._char_acc += self._chars_per_frame
        while self._char_acc >= 1.0 and self._char_idx < len(current_line):
            self._char_idx += 1
            self._char_acc -= 1.0

        if self._char_idx >= len(current_line):
            # Dong hoan thanh
            surf = self.font_story.render(current_line, True, (200, 220, 255))
            if len(self._rendered_lines) <= self._line_idx:
                self._rendered_lines.append(surf)
            else:
                self._rendered_lines[self._line_idx] = surf
            self._line_idx += 1
            self._char_idx = 0
            self._char_acc = 0.0

    def draw(self, surface):
        surface.blit(self._bg, (0, 0))

        # Title
        title = self.font_title.render("THE LEGEND BEGINS", True, (255, 215, 0))
        pulse = 1.0 + 0.05 * math.sin(self._t * 0.05)
        tw = int(title.get_width() * pulse)
        th = int(title.get_height() * pulse)
        title_scaled = pygame.transform.smoothscale(title, (tw, th))
        surface.blit(title_scaled,
                     (self.screen_w // 2 - tw // 2, 60))

        # Story lines
        y_start = 160
        line_h = 34
        for i, surf in enumerate(self._rendered_lines):
            surface.blit(surf, (self.screen_w // 2 - 360, y_start + i * line_h))

        # Dong dang go (chua hoan thanh)
        if not self._all_done and self._line_idx < len(STORY_LINES):
            partial = STORY_LINES[self._line_idx][:self._char_idx]
            # Them cursor nhap nhay
            if self._t % 30 < 20:
                partial += "_"
            psf = self.font_story.render(partial, True, (200, 220, 255))
            y = y_start + len(self._rendered_lines) * line_h
            surface.blit(psf, (self.screen_w // 2 - 360, y))

        # Hint
        if self._all_done:
            hint_text = "Press SPACE or ESC to continue..."
            alpha = int(128 + 127 * math.sin(self._t * 0.08))
            hint = self.font_hint.render(hint_text, True, (180, 180, 180))
            hint.set_alpha(alpha)
            surface.blit(hint, (self.screen_w // 2 - hint.get_width() // 2,
                                self.screen_h - 80))
