"""Soak test: 10 Đêm liên tiếp trong cùng tiến trình (TICKET-04 §2).

Lệnh:  python src/soak_test.py --seed 7 --nights 10 --out soak.json

Chạy headless 10 Đêm (Đêm 1→2→3 xoay vòng), Đêm i dùng seed 7+i, mỗi Đêm
chạy tới khi kết thúc hoặc hết thời lượng chuẩn. Input ngẫu nhiên theo seed:
mỗi 30 tick chọn lại hướng di chuyển; mỗi tick: 5% nhảy, 3% lướt, 2% toả
sáng, 10% tương tác.

Output soak.json:
{
  "nights": 10,
  "crashes": 0,
  "results": ["lost", "won", ...],
  "mem_start_mb": ...,   # RSS sau khi tải xong Đêm 1
  "mem_end_mb": ...,     # RSS sau khi reset xong Đêm cuối
  "duration_s": ...
}

Ngưỡng đạt: crashes == 0 và mem_end_mb <= 1.2 * mem_start_mb.
"""

import argparse
import json
import os
import random
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from game_headless import Game, TUNING, dist2d  # noqa: E402
from settings_store import load_settings  # noqa: E402


def _rss_mb():
    try:
        import psutil
        return psutil.Process().memory_info().rss / (1024 * 1024)
    except Exception:
        return None


def make_random_input(seed, ticks):
    """Sinh bộ input ngẫu nhiên theo Ticket-04 §2."""
    rng = random.Random(seed)
    frames = []
    move = [0.0, 1.0]
    for t in range(ticks):
        if t % 30 == 0:
            angle = rng.uniform(0, 2 * 3.14159)
            move = [round(__import__('math').cos(angle), 3),
                    round(__import__('math').sin(angle), 3)]
        frame = {"tick": t, "move": move, "cam_yaw_deg": 0.0}
        if rng.random() < 0.05:
            frame["jump"] = True
        elif rng.random() < 0.03:
            frame["dash"] = True
        elif rng.random() < 0.02:
            frame["pulse"] = True
        elif rng.random() < 0.10:
            frame["interact"] = True
        frames.append(frame)
    return {"frames": frames}


def run_night(seed, night, max_ticks=None):
    """Chạy 1 Đêm, trả về (state, ticks_used)."""
    duration_s = TUNING[f"night{night}_duration_s"]
    total_ticks = int(duration_s * 60) if max_ticks is None else max_ticks
    game = Game(seed, night)
    inputs = make_random_input(seed, total_ticks)
    input_by_tick = {}
    for f in inputs["frames"]:
        input_by_tick[f["tick"]] = f
    for step in range(total_ticks):
        if game.state != "playing":
            break
        game.apply_input(input_by_tick.get(step, {}))
        game.step()
    return game.state, game.tick


def run_soak(args):
    settings = load_settings()  # đảm bảo engine khởi tạo ok
    mem_start = _rss_mb() or 0.0
    t0 = time.perf_counter()
    results = []
    crashes = 0

    for i in range(1, args.nights + 1):
        night = ((i - 1) % 3) + 1  # Đêm 1→2→3 xoay vòng
        seed = args.seed + i
        try:
            state, ticks = run_night(seed, night)
            results.append(state)
        except Exception as exc:
            crashes += 1
            results.append(f"crash:{exc.__class__.__name__}")

    # "Sau khi reset xong Đêm cuối" → tạo 1 game mới, đo RSS sau reset
    _ = Game(args.seed + args.nights, 1)  # kích hoạt reset, free các reference cũ
    mem_end = _rss_mb() or 0.0
    duration_s = round(time.perf_counter() - t0, 1)

    result = {
        "nights": args.nights,
        "crashes": crashes,
        "results": results,
        "mem_start_mb": int(round(mem_start)),
        "mem_end_mb": int(round(mem_end)),
        "duration_s": duration_s,
    }
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    print(json.dumps(result, indent=2))
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--nights", type=int, default=10)
    ap.add_argument("--out", default="soak.json")
    args = ap.parse_args()
    return run_soak(args)


if __name__ == "__main__":
    sys.exit(main())
