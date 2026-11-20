#!/usr/bin/env python3
"""
Headless engine cho game Đảo Đèn Lồng — Phase 1 (Đêm 1 – Đảo Bến).
Tuân thủ Test Contract v1.0: chạy không giao diện, xuất JSONL, hoàn toàn xác định (deterministic).

Cách chạy:
    python src/game_headless.py --seed 123 --night 1 --ticks 600 --out out.jsonl
    python src/game_headless.py --seed 123 --night 1 --scenario scenario.json --inputs inputs.json --ticks 600 --out out.jsonl --snapshot-every 10

Tham số bắt buộc theo Test Contract:
  --seed <int>          hạt giống ngẫu nhiên (đảm bảo deterministic)
  --night 1             chỉ hỗ trợ đêm 1 ở Phase 1
  --ticks <int>         số bước mô phỏng (60 tick = 1 giây)
  --out <file.jsonl>    file đầu ra JSONL

Tham số tùy chọn:
  --scenario <file.json>   file dựng tình huống (mặc định: scénarios bản có sẵn)
  --inputs <file.json>     file lệnh điều khiển (mặc định: người chơi đứng yên)
  --snapshot-every <int>   khoảng cách snapshot (mặc định 10)

Mã thoát:
  0   thành công
  1   lỗi chạy thời gian thực
  2   file inputs/scenario sai định dạng
"""

import argparse
import json
import math
import random
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Tuning (phải khớp game.contract.json)
# ---------------------------------------------------------------------------
TUNING = {
    "player_speed": 5.0,
    "carry_capacity": 20,
    "lantern_cost": 1,
    "lantern_count_night1": 5,
    "pickup_radius": 2.0,
    "interact_radius": 3.0,
    "pulse_cost": 0,
    "pulse_radius": 8.0,
    "night1_duration_s": 300,
    "flames": 3,
    "invuln_s": 2.0,
    "hit_drop_ratio": 0.5,
    "pulse_stun_s": 3.0,
    "pulse_push_m": 5.0,
    "pulse_cooldown_s": 5.0,
    "safe_radius": 4.0,
    "shade_speed": 3.0,
    "shade_hit_radius": 1.5,
    "fall_enabled": False,
    "score": {
        "per_mote": 10,
        "per_lantern": 100,
        "per_stun": 0,
        "per_second_left": 1,
        "per_flame_left": 50,
    },
}

TICKS_PER_SECOND = 60


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def dist2d(a, b):
    """Khoảng cách mặt phẳng XZ giữa hai điểm [x, y, z]."""
    return math.hypot(a[0] - b[0], a[2] - b[2])


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def round3(v):
    return round(float(v), 3)


# ---------------------------------------------------------------------------
# Game state
# ---------------------------------------------------------------------------
class Game:
    def __init__(self, seed, scenario=None):
        self.seed = seed
        self.rng = random.Random(seed)  # dành cho random sau này (deterministic)
        self.tick = 0
        self.state = "playing"  # playing | won | lost
        self.score = 0
        self.time_left = float(TUNING["night1_duration_s"])

        # --- Người chơi ---
        self.player_pos = [0.0, 0.0, 0.0]
        self.player_yaw = 0.0
        self.player_carried = 0
        self.player_flames = int(TUNING["flames"])
        self.player_move = [0.0, 0.0]
        self.player_interact = False
        self.player_pulse = False
        self.player_jump = False
        self._interact_prev = False
        self._pulse_prev = False
        self.invuln_timer = 0.0
        self.pulse_cooldown_timer = 0.0

        # --- Đèn Lồng Lớn (L1..L5), đặt tròn quanh gốc tọa độ ---
        radius = 25.0
        count = int(TUNING["lantern_count_night1"])
        self.lanterns = []
        for i in range(count):
            angle = 2.0 * math.pi * i / count
            self.lanterns.append({
                "id": f"L{i + 1}",
                "pos": [round3(radius * math.cos(angle)), 0.0, round3(radius * math.sin(angle))],
                "lit": False,
                "deposited": 0,
            })
        self.lanterns_by_id = {L["id"]: L for L in self.lanterns}

        # --- Đom đóm ---
        self.motes = []
        self.mote_counter = 0

        # --- Bóng Mực ---
        self.shades = []
        self.shade_counter = 0

        # Áp dụng scenario nếu có
        if scenario:
            self._apply_scenario(scenario)

    # ------------------------------------------------------------------
    def _apply_scenario(self, scenario):
        if "player" in scenario:
            p = scenario["player"]
            if "pos" in p:
                self.player_pos = [float(v) for v in p["pos"]]
            if "carried" in p:
                self.player_carried = int(p["carried"])
            if "flames" in p:
                self.player_flames = int(p["flames"])

        if "lanterns" in scenario:
            for L in scenario["lanterns"]:
                lid = L.get("id")
                if lid in self.lanterns_by_id:
                    target = self.lanterns_by_id[lid]
                    if "pos" in L:
                        target["pos"] = [float(v) for v in L["pos"]]
                    if "lit" in L:
                        target["lit"] = bool(L["lit"])
                    if "deposited" in L:
                        target["deposited"] = int(L["deposited"])

        if "motes" in scenario:
            self.motes = []
            for m in scenario["motes"]:
                self.mote_counter += 1
                # m có thể là list [x, y, z] hoặc dict {"id":..., "pos":[x,y,z]}
                if isinstance(m, dict):
                    mid = m.get("id", f"M{self.mote_counter}")
                    mpos = m.get("pos", [0, 0, 0])
                    mx, _, mz = float(mpos[0]), float(mpos[1]), float(mpos[2])
                else:
                    mid = f"M{self.mote_counter}"
                    mx, _, mz = float(m[0]), float(m[1]), float(m[2])
                self.motes.append({
                    "id": mid,
                    "pos": [mx, 0.0, mz],
                })

        if "shades" in scenario:
            self.shades = []
            for s in scenario["shades"]:
                self.shade_counter += 1
                self.shades.append({
                    "id": s.get("id", f"S{self.shade_counter}"),
                    "pos": [float(s["pos"][0]), 0.0, float(s["pos"][2])],
                    "state": "chase",
                    "stun_timer": 0.0,
                })

        if "time_left_s" in scenario:
            self.time_left = float(scenario["time_left_s"])

    # ------------------------------------------------------------------
    def apply_input(self, frame):
        """Áp dụng lệnh điều khiển của 1 tick (theo Test Contract §C)."""
        if "move" in frame:
            mx, mz = float(frame["move"][0]), float(frame["move"][1])
            length = math.hypot(mx, mz)
            if length > 1.0:
                mx /= length
                mz /= length
            theta = math.radians(self.player_yaw)
            wx = mx * math.cos(theta) + mz * math.sin(theta)
            wz = -mx * math.sin(theta) + mz * math.cos(theta)
            self.player_move = [wx, wz]
        if "cam_yaw_deg" in frame:
            self.player_yaw = float(frame["cam_yaw_deg"])
        if "interact" in frame:
            self.player_interact = bool(frame["interact"])
        if "pulse" in frame:
            self.player_pulse = bool(frame["pulse"])
        if "jump" in frame:
            self.player_jump = bool(frame["jump"])


    # ------------------------------------------------------------------
    def step(self):
        """Chạy 1 tick (1/60 giây). Trả về danh sách sự kiện (events)."""
        events = []
        dt = 1.0 / TICKS_PER_SECOND

        if self.state != "playing":
            return events

        # Cập nhật bộ đếm thời gian
        self.time_left -= dt
        if self.invuln_timer > 0:
            self.invuln_timer -= dt
        if self.pulse_cooldown_timer > 0:
            self.pulse_cooldown_timer -= dt

        # --- Di chuyển người chơi ---
        mv = self.player_move
        if mv[0] != 0.0 or mv[1] != 0.0:
            step_len = TUNING["player_speed"] * dt
            self.player_pos[0] += mv[0] * step_len
            self.player_pos[2] += mv[1] * step_len

        # --- Tỏa sáng (rising edge) ---
        pulse_triggered = self.player_pulse and not self._pulse_prev
        self._pulse_prev = self.player_pulse

        if pulse_triggered and self.pulse_cooldown_timer <= 0:
            self.pulse_cooldown_timer = TUNING["pulse_cooldown_s"]
            stunned_ids = []
            for shade in self.shades:
                if shade["state"] == "stunned":
                    continue
                if dist2d(self.player_pos, shade["pos"]) <= TUNING["pulse_radius"]:
                    shade["state"] = "stunned"
                    shade["stun_timer"] = TUNING["pulse_stun_s"]
                    dx = shade["pos"][0] - self.player_pos[0]
                    dz = shade["pos"][2] - self.player_pos[2]
                    d = math.hypot(dx, dz)
                    if d > 0:
                        shade["pos"][0] += (dx / d) * TUNING["pulse_push_m"]
                        shade["pos"][2] += (dz / d) * TUNING["pulse_push_m"]
                    stunned_ids.append(shade["id"])
            if stunned_ids:
                events.append({
                    "tick": self.tick + 1,
                    "name": "pulse",
                    "data": {"stunned_ids": stunned_ids},
                })


        # --- Tương tác (rising edge): nhặt đom đóm / nạp ánh sáng vào đèn ---
        interact_triggered = self.player_interact and not self._interact_prev
        self._interact_prev = self.player_interact

        if interact_triggered:
            for mote in self.motes[:]:
                if dist2d(self.player_pos, mote["pos"]) <= TUNING["pickup_radius"]:
                    if self.player_carried < TUNING["carry_capacity"]:
                        self.motes.remove(mote)
                        self.player_carried += 1
                        self.score += int(TUNING["score"]["per_mote"])
                        events.append({
                            "tick": self.tick + 1,
                            "name": "mote_picked",
                            "data": {"carried": self.player_carried},
                        })

            if self.player_carried > 0:
                for L in self.lanterns:
                    if L["lit"]:
                        continue
                    if dist2d(self.player_pos, L["pos"]) <= TUNING["interact_radius"]:
                        needed = TUNING["lantern_cost"] - L["deposited"]
                        deposit_amount = min(self.player_carried, needed)
                        if deposit_amount > 0:
                            L["deposited"] += deposit_amount
                            self.player_carried -= deposit_amount
                            events.append({
                                "tick": self.tick + 1,
                                "name": "deposit",
                                "data": {
                                    "lantern_id": L["id"],
                                    "amount": deposit_amount,
                                    "deposited": L["deposited"],
                                },
                            })
                            if L["deposited"] >= TUNING["lantern_cost"] and not L["lit"]:
                                L["lit"] = True
                                events.append({
                                    "tick": self.tick + 1,
                                    "name": "lantern_lit",
                                    "data": {"lantern_id": L["id"]},
                                })
                                self.score += int(TUNING["score"]["per_lantern"])
                        break

        # --- AI Bóng Mực ---
        for shade in self.shades:
            if shade["stun_timer"] > 0:
                shade["stun_timer"] -= dt
                if shade["stun_timer"] <= 0:
                    shade["state"] = "chase"
                    shade["stun_timer"] = 0.0
                continue

            shade["state"] = "chase"

            near_safe_lantern = any(
                L["lit"] and dist2d(shade["pos"], L["pos"]) <= TUNING["safe_radius"]
                for L in self.lanterns
            )

            if not near_safe_lantern:
                dx = self.player_pos[0] - shade["pos"][0]
                dz = self.player_pos[2] - shade["pos"][2]
                d = math.hypot(dx, dz)
                if d > 0:
                    step_len = TUNING["shade_speed"] * dt
                    shade["pos"][0] += (dx / d) * step_len
                    shade["pos"][2] += (dz / d) * step_len

            if dist2d(shade["pos"], self.player_pos) <= TUNING["shade_hit_radius"]:
                if self.invuln_timer <= 0:
                    self.player_flames -= 1
                    dropped = int(self.player_carried * TUNING["hit_drop_ratio"])
                    self.player_carried = max(0, self.player_carried - dropped)
                    self.invuln_timer = TUNING["invuln_s"]
                    events.append({
                        "tick": self.tick + 1,
                        "name": "player_hit",
                        "data": {
                            "by": "shade",
                            "flames": self.player_flames,
                            "dropped": dropped,
                        },
                    })
                    if self.player_flames <= 0:
                        self.state = "lost"

        if all(L["lit"] for L in self.lanterns) and self.state == "playing":
            self.state = "won"
            events.append({
                "tick": self.tick + 1,
                "name": "game_over",
                "data": {"result": "won", "reason": "all_lit"},
            })

        if self.time_left <= 0.0 and self.state == "playing":
            self.state = "lost"
            events.append({
                "tick": self.tick + 1,
                "name": "game_over",
                "data": {"result": "lost", "reason": "dawn"},
            })

        self.tick += 1
        return events


    # ------------------------------------------------------------------
    def snapshot(self):
        """Tạo ảnh chụp trạng thái (theo Test Contract §E)."""
        return {
            "type": "snapshot",
            "tick": self.tick,
            "sim_tick": self.tick,
            "state": self.state,
            "time_left_s": round3(max(0.0, self.time_left)),
            "score": self.score,
            "player": {
                "pos": [
                    round3(self.player_pos[0]),
                    round3(self.player_pos[1]),
                    round3(self.player_pos[2]),
                ],
                "flames": self.player_flames,
                "carried": self.player_carried,
            },
            "lanterns": [
                {
                    "id": L["id"],
                    "pos": [
                        round3(L["pos"][0]),
                        round3(L["pos"][1]),
                        round3(L["pos"][2]),
                    ],
                    "lit": L["lit"],
                    "deposited": L["deposited"],
                }
                for L in self.lanterns
            ],
            "shades": [
                {
                    "id": S["id"],
                    "pos": [
                        round3(S["pos"][0]),
                        round3(S["pos"][1]),
                        round3(S["pos"][2]),
                    ],
                    "state": S["state"],
                }
                for S in self.shades
            ],
            "motes_active": len(self.motes),
        }


# ---------------------------------------------------------------------------
# Điểm vào chính
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Đảo Đèn Lồng headless (Phase 1)")
    parser.add_argument("--seed", type=int, required=True, help="hạt giống ngẫu nhiên")
    parser.add_argument("--night", type=int, required=True, help="mã đêm (chỉ 1 ở Phase 1)")
    parser.add_argument("--scenario", type=str, default=None, help="file scenario JSON")
    parser.add_argument("--inputs", type=str, default=None, help="file inputs JSON")
    parser.add_argument("--ticks", type=int, required=True, help="số bước mô phỏng")
    parser.add_argument("--out", type=str, required=True, help="file đầu ra JSONL")
    parser.add_argument("--snapshot-every", type=int, default=10,
                        help="khoảng cách snapshot (mặc định 10)")
    args = parser.parse_args()

    if args.night != 1:
        print("Chỉ hỗ trợ night 1 ở Phase 1", file=sys.stderr)
        return 1

    # --- Đọc scenario ---
    scenario = None
    if args.scenario:
        try:
            with open(args.scenario, "r", encoding="utf-8") as f:
                scenario = json.load(f)
        except Exception as exc:
            print(f"Lỗi đọc scenario: {exc}", file=sys.stderr)
            return 2

    # --- Đọc inputs ---
    inputs = {"frames": []}
    if args.inputs:
        try:
            with open(args.inputs, "r", encoding="utf-8") as f:
                inputs = json.load(f)
        except Exception as exc:
            print(f"Lỗi đọc inputs: {exc}", file=sys.stderr)
            return 2

    # Map tick -> frame
    input_by_tick = {}
    for frame in inputs.get("frames", []):
        input_by_tick[int(frame.get("tick", 0))] = frame

    # --- Khởi tạo game ---
    try:
        game = Game(args.seed, scenario)
    except Exception as exc:
        print(f"Lỗi khởi tạo game: {exc}", file=sys.stderr)
        return 2

    # --- Chạy mô phỏng ---
    lines = []

    # Snapshot tick 0
    if args.snapshot_every > 0 and game.tick % args.snapshot_every == 0:
        lines.append(json.dumps(game.snapshot(), ensure_ascii=False))

    for step in range(args.ticks):
        if game.state != "playing":
            break
        frame = input_by_tick.get(step, {})
        game.apply_input(frame)
        events = game.step()
        for ev in events:
            lines.append(json.dumps({"type": "event", **ev}, ensure_ascii=False))
        if args.snapshot_every > 0 and game.tick % args.snapshot_every == 0:
            lines.append(json.dumps(game.snapshot(), ensure_ascii=False))

    # Dòng end bắt buộc
    lines.append(json.dumps({
        "type": "end",
        "ticks": game.tick,
        "state": game.state,
        "score": game.score,
    }, ensure_ascii=False))

    # --- Ghi đầu ra ---
    try:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
    except Exception as exc:
        print(f"Lỗi ghi output: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())