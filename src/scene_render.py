"""Trình vẽ 3D (góc nhìn thứ ba) cho Đảo Đèn Lồng bằng pygame + toán chiếu phối cảnh.

Dùng chung cho chế độ chơi (game_gui.py) và benchmark (bench.py) để mọi bài đo
trên CÙNG một cảnh renderer ("đầy đủ hiệu ứng và ánh sáng như lúc chơi thật").

Hệ toạ độ: x (trái-phải), y (lên-xuống, mặt đất y=0), z (sâu).
Mọi thứ chỉ đọc trạng thái mô phỏng, không thay đổi luật/đầu ra headless.
"""

import math

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
        pygame.draw.rect(screen, SKY, screen.get_rect())
        # mặt đất: một ô chữ nhật phủ phần dưới
        horizon = int(self.h * 0.55)
        pygame.draw.rect(screen, GROUND, (0, horizon, self.w, self.h - horizon))

    def _draw_island(self, screen):
        # vòng tròn đảo (mặt đất) chiếu thành elip bằng cách nối các điểm biên.
        pts = []
        n = 32
        for i in range(n):
            a = i * 2 * math.pi / n
            p = self.project([40 * math.cos(a), 0.0, 40 * math.sin(a)])
            if p:
                pts.append((p[0], p[1]))
        if len(pts) >= 3:
            pygame.draw.polygon(screen, (30, 38, 52), pts, 3)
            pygame.draw.polygon(screen, (40, 52, 66), pts, 1)

    def _draw_light(self, screen, proj, radius_world, glow, strength):
        sx, sy, zc, scale = proj
        r = max(2, int(radius_world * scale))
        if r < 2 or r > 2000:
            return
        glow = pygame.transform.scale(glow, (r * 2, r * 2))
        glow.set_alpha(max(1, int(90 * strength)))
        screen.blit(glow, (sx - r, sy - r), special_flags=pygame.BLEND_RGB_ADD)

    def render(self, screen, game, palette, reduce_motion=False):
        self._fill_sky_ground(screen)
        self._draw_island(screen)

        items = []  # (depth, draw_fn)

        # Đèn lồng + ánh sáng
        for L in game.lanterns:
            proj = self.project([L["pos"][0], 1.2, L["pos"][2]])
            if not proj:
                continue
            sx, sy, zc, scale = proj
            items.append((zc, lambda p=proj, L=L: self._draw_lantern(screen, p, L, palette)))
            if L["lit"]:
                fuel_frac = max(0.0, min(1.0, L["fuel_60"] / 6000.0))
                items.append((zc, lambda p=proj, ff=fuel_frac: self._draw_light(screen, p, 4.0, self.glow, ff)))

        # Đom đóm
        for m in game.motes:
            proj = self.project([m["pos"][0], 0.6, m["pos"][2]])
            if proj:
                items.append((proj[2], lambda p=proj: self._draw_mote(screen, p)))

        # Bóng Mực
        for S in game.shades:
            proj = self.project([S["pos"][0], 1.0, S["pos"][2]])
            if proj:
                items.append((proj[2], lambda p=proj, S=S: self._draw_shade(screen, p, S, palette, reduce_motion)))

        # Người chơi
        pp = game.player_pos
        proj = self.project([pp[0], 1.4, pp[2]])
        if proj:
            items.append((proj[2], lambda p=proj: self._draw_player(screen, p)))

        items.sort(key=lambda it: -it[0])  # vẽ từ xa tới gần
        for _, fn in items:
            fn()

    def _draw_lantern(self, screen, proj, L, palette):
        sx, sy, zc, scale = proj
        w = max(2, int(0.8 * scale))
        top = int(2.4 * scale)
        color = (255, 200, 110) if L["lit"] else (90, 80, 70)
        pygame.draw.rect(screen, color, (sx - w, sy - top - w, w * 2, top + w))
        pygame.draw.circle(screen, color, (sx, sy - top - w), max(2, w + 1))

    def _draw_mote(self, screen, proj):
        sx, sy, zc, scale = proj
        r = max(1, int(0.35 * scale))
        pygame.draw.circle(screen, (255, 230, 150), (sx, sy), r)

    def _draw_shade(self, screen, proj, S, palette, reduce_motion):
        sx, sy, zc, scale = proj
        r = max(2, int(1.2 * scale))
        pygame.draw.circle(screen, (12, 8, 22), (sx, sy), r)
        pygame.draw.circle(screen, palette["shade_outline"], (sx, sy), r, max(1, min(3, r // 8)))
        # mắt
        ex, ey = int(r * 0.4), int(r * 0.15)
        pygame.draw.circle(screen, (255, 60, 60), (sx - ex, sy - ey), max(1, r // 5))
        pygame.draw.circle(screen, (255, 60, 60), (sx + ex, sy - ey), max(1, r // 5))
        # nhấp nháy khi đang drain (trừ khi giảm chuyển động)
        if S["state"] == "drain" and not reduce_motion:
            pygame.draw.circle(screen, palette["warning"], (sx, sy - r * 1.4), max(2, r // 4), 2)

    def _draw_player(self, screen, proj):
        sx, sy, zc, scale = proj
        h = int(1.4 * scale)
        color = (220, 235, 255)
        pygame.draw.rect(screen, color, (sx - 2, sy - h, 4, h))
        pygame.draw.circle(screen, (255, 210, 120), (sx, sy - h - 2), max(3, int(0.4 * scale)))
