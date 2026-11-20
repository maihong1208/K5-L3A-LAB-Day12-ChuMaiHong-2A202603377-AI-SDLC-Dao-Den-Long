"""Trình vẽ 3D (góc nhìn thứ ba) cho Đảo Đèn Lồng bằng pygame + toán chiếu phối cảnh.

Dùng chung cho chế độ chơi (game_gui.py) và benchmark (bench.py) để mọi bài đo
trên CÙNG một cảnh renderer ("đầy đủ hiệu ứng và ánh sáng như lúc chơi thật").

Hệ toạ độ: x (trái-phải), y (lên-xuống, mặt đất y=0), z (sâu).
Mọi thứ chỉ đọc trạng thái mô phỏng, không thay đổi luật/đầu ra headless.
"""

import math
import random

import pygame

FOV_DEG = 60.0
SKY = (16, 18, 40)
GROUND = (24, 30, 40)


class Camera:
    """Camera bay vòng tròn hoặc bám sau người chơi (third-person)."""

    def __init__(self, target=None):
        self.cam = [0.0, 15.0, 30.0]
        self.target = target
        self.azimuth = 0.0          # rad, góc quay (dương = ngược chiều kim đồng hồ nhìn từ trên)
        self.pitch = math.radians(28.0)

    def set_orbit(self, radius, height, azimuth, look_at=[0.0, 0.0, 0.0]):
        """Camera bay vòng tròn (benchmark)."""
        self.cam = [
            look_at[0] + radius * math.sin(azimuth),
            height,
            look_at[2] + radius * math.cos(azimuth),
        ]
        self._look_at(look_at)

    def follow(self, player_pos, azimuth):
        """Bám sau người chơi theo góc azimuth hiện tại."""
        dist, height = 18.0, 9.0
        cx = player_pos[0] - dist * math.sin(azimuth)
        cz = player_pos[2] - dist * math.cos(azimuth)
        self.cam = [cx, height, cz]
        self._look_at([player_pos[0], 1.0, player_pos[2]])

    def _look_at(self, look_at):
        self.target = look_at
        fx, fy, fz = look_at[0] - self.cam[0], look_at[1] - self.cam[1], look_at[2] - self.cam[2]
        d = math.hypot(fx, fy, fz) or 1.0
        self._fwd = [fx / d, fy / d, fz / d]
        # right = cross(forward, up_world)
        ux, uy, uz = 0.0, 1.0, 0.0
        rx = self._fwd[1] * uz - self._fwd[2] * uy
        ry = self._fwd[2] * ux - self._fwd[0] * uz
        rz = self._fwd[0] * uy - self._fwd[1] * ux
        rd = math.hypot(rx, ry, rz) or 1.0
        self._right = [rx / rd, ry / rd, rz / rd]
        # upv = cross(right, forward)
        uxv = self._right[1] * self._fwd[2] - self._right[2] * self._fwd[1]
        yuv = self._right[2] * self._fwd[0] - self._right[0] * self._fwd[2]
        zuv = self._right[0] * self._fwd[1] - self._right[1] * self._fwd[0]
        self._upv = [uxv, yuv, zuv]


def _make_glow_sprite(size, rgb, softness=0.55):
    """Sprite phát sáng radial (trắng trong -> màu), dùng blit nhanh."""
    s = pygame.Surface((size, size), pygame.SRCALPHA)
    cx = size // 2
    for r in range(cx, 0, -1):
        t = 1.0 - r / cx
        alpha = int(255 * (t ** (2.2 / softness)))
        col = (int(rgb[0]), int(rgb[1]), int(rgb[2]), alpha)
        pygame.draw.circle(s, col, (cx, cx), r)
    return s


class Renderer:
    def __init__(self, width, height, fps_cap=None):
        self.w, self.h = width, height
        self.fps_cap = fps_cap
        self.focal = (self.h * 0.5) / math.tan(math.radians(FOV_DEG) / 2.0)
        self.cam = Camera()
        self.glow = _make_glow_sprite(256, (255, 190, 90))
        self.shade_dark = _make_glow_sprite(192, (10, 8, 20))
        rng = random.Random(1204)
        self.stars = [
            (rng.randrange(width), rng.randrange(max(1, int(height * 0.42))),
             rng.choice((1, 1, 1, 2)), rng.randrange(70, 180))
            for _ in range(72)
        ]
        self.grass = [
            (rng.uniform(-38, 38), rng.uniform(-38, 38), rng.uniform(0.7, 1.8))
            for _ in range(28)
        ]
        self.background = pygame.Surface((width, height))
        self._build_background()

    def _build_background(self):
        for band in range(28):
            y0 = int(self.h * band / 28)
            y1 = int(self.h * (band + 1) / 28)
            t = band / 27
            color = (
                int(SKY[0] + (34 - SKY[0]) * t),
                int(SKY[1] + (44 - SKY[1]) * t),
                int(SKY[2] + (62 - SKY[2]) * t),
            )
            pygame.draw.rect(self.background, color, (0, y0, self.w, y1 - y0 + 1))
        for x, y, radius, alpha in self.stars:
            if y < self.h * 0.4:
                color = (min(255, 150 + alpha // 3), min(255, 170 + alpha // 3), 205)
                pygame.draw.circle(self.background, color, (x, y), radius)

    # ---------------- chiếu ----------------
    def project(self, p):
        """Trả về (screen_x, screen_y, zc, scale) hoặc None nếu sau camera."""
        dx, dy, dz = p[0] - self.cam.cam[0], p[1] - self.cam.cam[1], p[2] - self.cam.cam[2]
        zc = dx * self.cam._fwd[0] + dy * self.cam._fwd[1] + dz * self.cam._fwd[2]
        if zc < 0.15:
            return None
        xc = dx * self.cam._right[0] + dy * self.cam._right[1] + dz * self.cam._right[2]
        yc = dx * self.cam._upv[0] + dy * self.cam._upv[1] + dz * self.cam._upv[2]
        sx = self.w * 0.5 + (xc / zc) * self.focal
        sy = self.h * 0.5 - (yc / zc) * self.focal
        scale = self.focal / zc
        return (sx, sy, zc, scale)

    # ---------------- vẽ ----------------
    def _fill_sky_ground(self, screen):
        screen.blit(self.background, (0, 0))

    def _draw_island(self, screen, lights_on):
        # Fill the visible half of the island down to the near edge of the frame.
        pts = []
        n = 64
        for i in range(n):
            a = i * 2 * math.pi / n
            p = self.project([40 * math.cos(a), 0.0, 40 * math.sin(a)])
            if p:
                pts.append((int(p[0]), int(p[1])))
        if len(pts) >= 3:
            island = pts + [(self.w, self.h), (0, self.h)]
            glow = min(1.0, lights_on / 5.0)
            ground_color = (32 + int(22 * glow), 52 + int(13 * glow), 57 + int(6 * glow))
            pygame.draw.polygon(screen, ground_color, island)
            pygame.draw.lines(screen, (111, 121, 104), False, pts, 3)
            pygame.draw.line(screen, (62, 79, 78), (0, int(self.h * 0.68)),
                             (self.w, int(self.h * 0.68)), 1)

            for x, z, size in self.grass:
                projected = self.project([x, 0.05, z])
                if projected:
                    sx, sy = int(projected[0]), int(projected[1])
                    if 0 <= sx < self.w and int(self.h * 0.35) < sy < self.h - 40:
                        grass_color = (47 + int(14 * glow), 70 + int(8 * glow), 68 + int(4 * glow))
                        pygame.draw.line(screen, grass_color, (sx, sy),
                                         (sx + int(size * 2), sy - int(size * 2)), 1)

            rim_y = int(self.h * 0.91)
            pygame.draw.ellipse(screen, (21, 33, 45),
                                (-self.w * 0.12, rim_y, self.w * 1.24, self.h * 0.22))
            pygame.draw.ellipse(screen, (62, 78, 80),
                                (-self.w * 0.12, rim_y, self.w * 1.24, self.h * 0.22), 3)

    def _draw_light(self, screen, proj, radius_world, glow, strength, blinking=False):
        sx, sy, zc, scale = proj
        r = min(36, max(2, int(radius_world * scale)))
        if strength <= 0:
            return
        if blinking and (pygame.time.get_ticks() // 500) % 2:
            return
        glow = pygame.transform.scale(glow, (r * 2, r * 2))
        glow.set_alpha(max(1, int(90 * strength)))
        screen.blit(glow, (sx - r, sy - r), special_flags=pygame.BLEND_RGB_ADD)

    def render(self, screen, game, palette, reduce_motion=False):
        self._fill_sky_ground(screen)
        self._draw_island(screen, sum(1 for lantern in game.lanterns if lantern["lit"]))

        items = []  # (depth, draw_fn)

        # Đèn lồng + ánh sáng
        for L in game.lanterns:
            proj = self.project([L["pos"][0], L["pos"][1] + 1.2, L["pos"][2]])
            if not proj:
                continue
            sx, sy, zc, scale = proj
            items.append((zc, lambda p=proj, L=L: self._draw_lantern(
                screen, p, L, palette, reduce_motion)))
            if L["lit"]:
                fuel_frac = max(0.0, min(1.0, L["fuel_60"] / 6000.0))
                blinking = fuel_frac < 0.3 and not reduce_motion
                items.append((zc + 0.001, lambda p=proj, ff=fuel_frac, bl=blinking:
                              self._draw_light(screen, p, 2.2, self.glow, ff, bl)))

        # Đom đóm
        for m in game.motes:
            proj = self.project([m["pos"][0], m["pos"][1] + 0.6, m["pos"][2]])
            if proj:
                items.append((proj[2], lambda p=proj: self._draw_mote(screen, p)))

        # Bóng Mực
        for S in game.shades:
            proj = self.project([S["pos"][0], 1.0, S["pos"][2]])
            if proj:
                items.append((proj[2], lambda p=proj, S=S: self._draw_shade(screen, p, S, palette, reduce_motion)))

        # Người chơi
        pp = game.player_pos
        proj = self.project([pp[0], pp[1] + 1.4, pp[2]])
        if proj:
            items.append((proj[2], lambda p=proj: self._draw_player(screen, p)))

        items.sort(key=lambda it: -it[0])  # vẽ từ xa tới gần
        for _, fn in items:
            fn()

    def _draw_lantern(self, screen, proj, L, palette, reduce_motion=False):
        sx, sy, zc, scale = proj
        sx, sy = int(sx), int(sy)
        w = max(2, int((0.8 if L["lit"] else 0.64) * scale))
        top = int((2.4 if L["lit"] else 1.9) * scale)
        low_fuel = L["lit"] and L["fuel_60"] < 1800
        blinking = low_fuel and not reduce_motion and (pygame.time.get_ticks() // 500) % 2
        color = (255, 200, 110) if L["lit"] else (95, 92, 83)
        if blinking:
            color = (164, 119, 68)
        body = pygame.Rect(sx - w, sy - top - w, w * 2, top + w)
        pygame.draw.rect(screen, color, body, border_radius=max(1, w // 3))
        pygame.draw.rect(screen, (255, 230, 177) if L["lit"] else (55, 55, 54),
                         body, width=1, border_radius=max(1, w // 3))
        pygame.draw.circle(screen, color, (sx, sy - top - w), max(2, w + 1))
        if not L["lit"]:
            pygame.draw.line(screen, (50, 50, 50), (sx - w, sy - w),
                             (sx - 1, sy - int(w * 1.8)), max(1, w // 4))
        else:
            bar_width = max(8, int(7.5 * scale))
            bar_height = max(2, int(0.32 * scale))
            bar = pygame.Rect(sx - bar_width // 2, sy - top - w - bar_height - 3,
                              bar_width, bar_height)
            pygame.draw.rect(screen, (19, 24, 27), bar)
            fill = pygame.Rect(bar.x, bar.y,
                               int(bar.width * max(0.0, L["fuel_60"] / 6000)), bar.height)
            if not blinking:
                pygame.draw.rect(screen, (255, 194, 94), fill)

    def _draw_mote(self, screen, proj):
        sx, sy, zc, scale = proj
        r = max(1, int(0.35 * scale))
        pygame.draw.circle(screen, (255, 230, 150), (sx, sy), r)

    def _draw_shade(self, screen, proj, S, palette, reduce_motion):
        sx, sy, zc, scale = proj
        r = max(2, int(1.2 * scale))
        pygame.draw.circle(screen, (12, 8, 22), (sx, sy), r)
        pygame.draw.circle(screen, palette["shade_outline"], (sx, sy), r, max(1, min(3, r // 8)))
        # Match the outline color so colorblind mode changes both together.
        ex, ey = int(r * 0.4), int(r * 0.15)
        pygame.draw.circle(screen, palette["shade_outline"], (sx - ex, sy - ey), max(1, r // 5))
        pygame.draw.circle(screen, palette["shade_outline"], (sx + ex, sy - ey), max(1, r // 5))
        # nhấp nháy khi đang drain (trừ khi giảm chuyển động)
        if S["state"] == "drain" and not reduce_motion:
            pygame.draw.circle(screen, palette["warning"], (sx, sy - r * 1.4), max(2, r // 4), 2)

    def _draw_player(self, screen, proj):
        sx, sy, zc, scale = proj
        sx, sy = int(sx), int(sy)
        h = max(12, int(2.0 * scale))
        body_width = max(5, int(0.58 * scale))
        color = (205, 221, 231)
        pygame.draw.ellipse(screen, (17, 24, 37), (sx - body_width, sy - 3, body_width * 2, 6))
        pygame.draw.polygon(screen, color, (
            (sx - body_width, sy - h // 2),
            (sx + body_width, sy - h // 2),
            (sx + max(2, body_width // 2), sy - 2),
            (sx - max(2, body_width // 2), sy - 2),
        ))
        head_y = sy - h
        pygame.draw.circle(screen, (244, 205, 161), (sx, head_y), max(3, int(0.22 * scale)))
        hat_width = max(7, int(0.76 * scale))
        hat_height = max(3, int(0.25 * scale))
        pygame.draw.polygon(screen, (190, 145, 84), (
            (sx - hat_width, head_y - 2),
            (sx + hat_width, head_y - 2),
            (sx, head_y - hat_height - 3),
        ))
        lantern_x = sx + body_width + max(2, int(0.2 * scale))
        lantern_y = sy - h // 2
        pygame.draw.line(screen, (219, 211, 183), (sx, lantern_y - 2),
                         (lantern_x, lantern_y + max(2, int(0.2 * scale))), 1)
        pygame.draw.circle(screen, (255, 205, 108), (lantern_x, lantern_y + 3),
                           max(2, int(0.16 * scale)))
