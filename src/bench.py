#!/usr/bin/env python3
"""Benchmark chế độ chơi thật (TICKET-04 §1).

Lệnh:  python src/bench.py --seed 42 --duration 30 --out bench.json

Cảnh chuẩn (mọi bài giống nhau, Ticket-04 §1):
- Cửa sổ 1280x720, không toàn màn hình, vsync tắt.
- Đêm 1, 200 Bóng Mực wander + 100 đom đóm, đèn L1–L3 sáng (fuel 100).
- Tắt sinh thêm, sát thương, nhặt đom, hao dầu, kết thúc Đêm; Bóng Mực
  vẫn wander bình thường. Không input người chơi; Mây đứng yên tại (0,0,0).
- Camera bay vòng tròn tâm (0,0,0), bán kính 30 m, cao Y=15 m, nhìn (0,0,0),
  khởi đầu góc 0 (điểm (30,15,0)), quay ngược chiều kim đồng hồ, 15 s/vòng.
- 3 s khởi động (không đo), sau đó đo đúng --duration s rồi tự thoát mã 0.

Output bench.json theo schema Contract v1.3. Đo trên máy chấm của giảng viên
để đạt ngưỡng (avg_fps>=60, p1_low_fps>=30, load_ms<=10000).
"""

import argparse
import json
import math
import os
import sys
import time

# Ghi nhãn process khởi điểm để đo load_ms đúng.
PROCESS_START = time.perf_counter()

import pygame

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from benchmark_stats import summarize_frame_times  # noqa: E402
from game_headless import Game, TUNING, dist2d  # noqa: E402
from scene_render import Renderer, Camera, SKY, GROUND, FOV_DEG  # noqa: E402
import settings_store  # noqa: E402

W, H = 1280, 720
WARMUP_S = 3.0
ORBIT_RADIUS = 30.0
ORBIT_HEIGHT = 15.0
ORBIT_PERIOD_S = 15.0
ORBIT_START_RAD = math.radians(90.0)   # điểm (30, 15, 0)


def _rss_mb():
    try:
        import psutil
        return psutil.Process().memory_info().rss / (1024 * 1024)
    except Exception:
        return None


def build_bench_world(seed):
    """Xây cảnh chuẩn: Game + 200 Bóng Mực wander + 100 đom đóm + L1–L3 sáng.

    Tắt mọi tác động gameplay (không gọi game.step()); mỗi khung chỉ cập nhật
    vị trí wander của Bóng Mực để giữ cảnh "đầy đủ như lúc chơi thật".
    """
    rng = __import__("random").Random(seed)
    game = Game(seed, 1, {"motes": [], "shades": []})
    # 100 đom đóm rải đều (vượt trần gameplay được phép trong bench).
    game.motes = []
    for i in range(100):
        a = rng.uniform(0, 2 * math.pi)
        r = rng.uniform(3.0, 38.0)
        game.motes.append({"id": f"BM{i}", "pos": [r * math.cos(a), 0.0, r * math.sin(a)],
                          "kind": "random", "ttl_s": 0})
    # 200 Bóng Mực wander rải đều trên đảo.
    game.shades = []
    for i in range(200):
        a = rng.uniform(0, 2 * math.pi)
        r = rng.uniform(2.0, 38.0)
        game.shades.append({
            "id": f"BS{i}", "pos": [r * math.cos(a), 0.0, r * math.sin(a)],
            "state": "wander", "state_ticks_left": 0,
            "recoil_dir": [0.0, 0.0], "recoil_ticks_left": 0,
            "drain_lantern_id": None, "drain_progress_ticks": 0,
            "safe_push_ticks": 0, "safe_push_dir": [0.0, 0.0],
            "safe_push_lantern_id": None, "target_lantern_id": None,
        })
    # L1–L3 sáng, fuel 100 (đặt sẵn bằng scenario logic của engine).
    for lid in ("L1", "L2", "L3"):
        L = game.lanterns_by_id[lid]
        L["lit"] = True
        L["fuel_60"] = 6000
        L["ever_lit"] = True
    game.player_pos = [0.0, 0.0, 0.0]
    game._bench_rng = rng
    return game


def advance_wander(game, dt):
    """Chỉ chuyển động wander (tốc 0.5x), không sinh/hai/thương (Ticket-04 §1)."""
    rng = game._bench_rng
    speed = TUNING["shade_speed"] * 0.5 * dt
    for S in game.shades:
        a = rng.uniform(0, 2 * math.pi)
        S["pos"][0] += math.cos(a) * speed
        S["pos"][2] += math.sin(a) * speed


def cam_azimuth(elapsed):
    return ORBIT_START_RAD + 2 * math.pi * (elapsed % ORBIT_PERIOD_S) / ORBIT_PERIOD_S


def run_benchmark(args):
    settings = settings_store.load_settings()
    palette = settings_store.palette(settings)

    # VsYNC TẮT: pygame chỉ bật vsync khi truyền flag trong set_mode; không dùng
    # -> chế độ mặc định SDL (vsync off), cửa sổ 1280x720 không toàn màn hình.
    # Ghi rõ trong README (Ticket-04 §1).
    pygame.init()
    window = pygame.display.set_mode((W, H))
    pygame.display.set_caption("Đảo Đèn Lồng — Benchmark (vsync off, not fullscreen)")

    game = build_bench_world(args.seed)
    renderer = Renderer(W, H)
    vsync_off = True

    load_ms = None
    peak_mb = _rss_mb()
    dt_ms_list = []        # dt_i (ms) của các khung trong khoảng đo
    last_measure_time = None

    t0 = time.perf_counter()
    total_end = t0 + WARMUP_S + args.duration
    while time.perf_counter() < total_end:
        elapsed = time.perf_counter() - t0
        az = cam_azimuth(elapsed)
        renderer.cam.set_orbit(ORBIT_RADIUS, ORBIT_HEIGHT, az, [0.0, 0.0, 0.0])
        advance_wander(game, 1.0 / 60.0)
        renderer.render(window, game, palette,
                        reduce_motion=settings.get("reduce_motion", False))
        pygame.display.flip()

        if load_ms is None:  # khung hình đầu tiên của cảnh bench
            load_ms = (time.perf_counter() - PROCESS_START) * 1000.0

        # Chỉ đo dt_i sau 3 s khởi động (Ticket-04 §1).
        if elapsed >= WARMUP_S:
            now = time.perf_counter()
            if last_measure_time is not None:
                dt_ms_list.append((now - last_measure_time) * 1000.0)
            last_measure_time = now
        else:
            last_measure_time = None

        cur = _rss_mb()
        if cur is not None:
            peak_mb = max(peak_mb, cur)

    stats = summarize_frame_times(dt_ms_list)

    result = {
        "contract_version": "1.3",
        "avg_fps": round(stats["avg_fps"], 1),
        "p1_low_fps": round(stats["p1_low_fps"], 1),
        "frame_ms_p95": round(stats["frame_ms_p95"], 1),
        "frames": stats["frames"],
        "load_ms": int(round(load_ms)) if load_ms is not None else 0,
        "peak_mem_mb": int(round(peak_mb)) if peak_mb is not None else None,
        "vsync_off": vsync_off,
        "renderer": f"pygame-ce {getattr(pygame.version, 'ver', 'unknown')} (SDL2) — 2D perspective-3D projection, depth-sorted sprites",
        "os": sys.platform,
    }

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    print(json.dumps(result, indent=2))
    pygame.quit()
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--duration", type=float, default=30.0)
    ap.add_argument("--out", default="bench.json")
    args = ap.parse_args()
    return run_benchmark(args)


if __name__ == "__main__":
    sys.exit(main())
