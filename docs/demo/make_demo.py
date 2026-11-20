#!/usr/bin/env python3
"""Sinh video demo docs/demo/demo.mp4 (dưới 5 phút, TICKET-04 §7).

Cách chạy:
    python docs/demo/make_demo.py
Tạo demo.mp4 gồm:
- Đoạn 1 (~10 s): chế độ benchmark — camera orbit quanh đảo (cảnh chuẩn,
  thể hiện renderer "đầy đủ hiệu ứng và ánh sáng").
- Đoạn 2 (~10 s): chơi Đêm 1 bằng input ngẫu nhiên theo seed (thể hiện
  luật: nhặt đom, thắp đèn, né Bóng Mực, nhiên liệu hao/thắp lại).
Dùng ffmpeg (imageio-ffmpeg) mã hoá H.264. Không cần GUI thật — render
vào surface bằng SDL dummy driver, vẫn dùng cùng Renderer.
"""

import os
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import json
import math
import random

import pygame

import bench as bench_mod
from game_headless import Game
from scene_render import Renderer, SKY
import settings_store

FRAMES_1 = 240   # ~10 s @ 24 fps: benchmark orbit
FRAMES_2 = 240   # ~10 s @ 24 fps: chơi Đêm 1 (mô phỏng 240 tick = 4 s game)
FPS = 24


def encode(frames_dir, out_path):
    """Nén danh sách ảnh PNG thành MP4 bằng ffmpeg (imageio-ffmpeg)."""
    try:
        import imageio_ffmpeg
        ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        ffmpeg = "ffmpeg"
    pattern = os.path.join(frames_dir, "f_%04d.png")
    cmd = [ffmpeg, "-y", "-framerate", str(FPS), "-i", pattern,
           "-pix_fmt", "yuv420p", "-crf", "23", out_path]
    subprocess.run(cmd, check=True, capture_output=True)


def main():
    settings = settings_store.load_settings()
    palette = settings_store.palette(settings)
    W, H = 1280, 720
    frames_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_frames")
    os.makedirs(frames_dir, exist_ok=True)
    for f in os.listdir(frames_dir):
        os.remove(os.path.join(frames_dir, f))

    pygame.init()
    screen = pygame.display.set_mode((W, H))

    # ---- Đoạn 1: benchmark orbit ----
    game = bench_mod.build_bench_world(42)
    renderer = Renderer(W, H)
    n = 0
    for i in range(FRAMES_1):
        t = i / FPS
        az = bench_mod.cam_azimuth(t)
        renderer.cam.set_orbit(bench_mod.ORBIT_RADIUS, bench_mod.ORBIT_HEIGHT, az, [0.0, 0.0, 0.0])
        bench_mod.advance_wander(game, 1.0 / 60.0)
        screen.fill(SKY)
        renderer.render(screen, game, palette, reduce_motion=False)
        fnt = None
        pygame.image.save(screen, os.path.join(frames_dir, f"f_{n:04d}.png"))
        n += 1

    # ---- Đoạn 2: chơi Đêm 1, input ngẫu nhiên ----
    g = Game(11, 1, None)
    rng = random.Random(11)
    move = [0.0, 1.0]
    last_lantern = None
    for i in range(FRAMES_2):
        if i % 10 == 0:
            a = rng.uniform(0, 2 * math.pi)
            move = [round(math.cos(a), 3), round(math.sin(a), 3)]
        frame = {"move": move, "cam_yaw_deg": 0.0}
        if rng.random() < 0.10:
            frame["interact"] = True
        if rng.random() < 0.02:
            frame["pulse"] = True
        g.apply_input(frame)
        g.step()
        g.step()  # 2 tick/khung -> game diễn tiến rõ trong 10 s video
        renderer = Renderer(W, H)
        renderer.cam.follow([g.player_pos[0], g.player_pos[1], g.player_pos[2]],
                           math.radians(g.player_yaw))
        screen.fill(SKY)
        renderer.render(screen, g, palette, reduce_motion=False)
        # HUD tối giản
        if pygame.font is not None:
            f = pygame.font.SysFont(None, 24)
            t = int(max(0, g.time_left))
            info = f"Night {g.night}  {t}s  Flames {g.player_flames}  Motes {g.player_carried}  Score {g.score}"
            screen.blit(f.render(info, True, (255, 255, 255)), (12, 12))
        pygame.image.save(screen, os.path.join(frames_dir, f"f_{n:04d}.png"))
        n += 1

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "demo.mp4")
    encode(frames_dir, out)
    for f in os.listdir(frames_dir):
        os.remove(os.path.join(frames_dir, f))
    os.rmdir(frames_dir)
    pygame.quit()
    size = os.path.getsize(out)
    print(f"OK: {out} ({size // 1024} KB, {n} frames @ {FPS} fps, {n / FPS:.1f}s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
