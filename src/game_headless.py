#!/usr/bin/env python3
"""
Headless engine cho game Đảo Đèn Lồng — Phase 3 (TICKET-03: Đèn cạn dầu).
Tuân thủ Test Contract v1.2: chạy không giao diện, xuất JSONL, hoàn toàn xác định (deterministic).
Mô hình nhiên liệu: đèn hao/hút dầu, có thể châm/thắp lại; thắng bằng giữ đảo sáng
đến bình minh (>= 60% đèn sáng), không còn thắng sớm.

Cách chạy:
    python src/game_headless.py --seed 42 --night 1 --ticks 600 --out out.jsonl

Tham số bắt buộc:
  --seed <int>   hạt giống ngẫu nhiên
  --night <1|2|3>   mã đêm
  --ticks <int>   số bước mô phỏng
  --out <file.jsonl>   file đầu ra JSONL

Tham số tùy chọn:
  --scenario <file.json>   file dựng tình huống
  --inputs <file.json>     file lệnh điều khiển
  --snapshot-every <int>   khoảng cách snapshot (mặc định 10)

Mã thoát: 0 = thành công, 1 = lỗi, 2 = sai định dạng file
"""

import argparse
import json
import math
import random
import sys
from pathlib import Path

try:
    from .settings_store import load_settings
except ImportError:  # chạy trực tiếp: python src/game_headless.py
    from settings_store import load_settings

# ---------------------------------------------------------------------------
# Tuning số chuẩn Phase 3 (Contract v1.2; phải khớp game.contract.json)
# ---------------------------------------------------------------------------
TUNING = {
    "player_speed": 6.0,
    "carry_capacity": 10,
    "jump_velocity": 7.0,
    "gravity": -20.0,
    "dash_speed": 14.0,
    "dash_duration_s": 0.2,
    "dash_cooldown_s": 1.5,
    "pickup_radius_xz": 1.0,
    "pickup_height_tolerance": 1.5,
    "motes_initial": 20,
    "motes_cap": 30,
    "mote_spawn_interval": 240,
    "lantern_cost": 10,
    "interact_radius": 2.0,
    "safe_radius": 6.0,
    "safe_push_ticks": 30,
    "pulse_cost": 3,
    "pulse_radius": 5.0,
    "pulse_stun_ticks": 120,
    "pulse_push_m": 4.0,
    "pulse_push_ticks": 15,
    "pulse_cooldown_s": 3.0,
    "shade_speed": 4.0,
    "shade_speed_night3": 4.5,
    "shade_detect_m": 12.0,
    "shade_lose_m": 18.0,
    "shade_hit_radius_xz": 1.0,
    "shade_hit_height_tolerance": 1.5,
    "shade_recoil_m": 2.0,
    "shade_recoil_ticks": 60,
    "shade_invuln_ticks": 90,
    # --- Phase 3 (Ticket-03, Contract v1.2) ---
    "night1_duration_s": 240,
    "night2_duration_s": 270,
    "night3_duration_s": 300,
    "flames": 3,
    "charm_speed": 7.2,
    "charm_duration_ticks": 600,
    "charm_respawn_ticks": 2700,
    # Nhiên liệu đèn (mô hình "đèn cạn dầu")
    "fuel_max": 100,
    "fuel_decay_per_s": 1.0,
    "fuel_per_mote": 10,
    "relight_cost": 5,
    "win_ratio": 0.6,
    "drain_per_s": 5,
    "low_fuel_threshold": 30,
    "drain_enter_m": 2.0,
    "drain_leave_m": 2.0,
    "drain_chase_m": 6.0,
    "capacity_max": 20,
    "score": {
        "per_mote_deposit": 5,
        "per_first_light": 100,
        "per_relight": 40,
        "per_stun": 5,
        "per_stun_drain": 15,
        "dawn_per_lantern_lit": 50,
        "dawn_per_flame_left": 50,
    },
}

TICKS_PER_SECOND = 60

# Nhiên liệu được lưu dạng nguyên đơn vị "1/60 fuel" để tránh sai số số thực;
# chỉ quy đổi (round 1 chữ số) khi xuất snapshot/sự kiện.
FUEL_MAX_60 = int(TUNING["fuel_max"]) * 60          # = 6000
FUEL_DECAY_60_PER_TICK = int(TUNING["fuel_decay_per_s"])   # 1/60 fuel/tick = 1 đơn vị
FUEL_DRAIN_60_PER_TICK = int(TUNING["drain_per_s"])        # 5/60 fuel/tick = 5 đơn vị
FUEL_PER_MOTE_60 = int(TUNING["fuel_per_mote"]) * 60       # = 600 đơn vị/đom đóm
LOW_FUEL_60 = int(TUNING["low_fuel_threshold"]) * 60       # = 1800


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def dist2d(a, b):
    return math.hypot(a[0] - b[0], a[2] - b[2])


def dist3d(a, b):
    return math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2)


def round3(v):
    return round(float(v), 3)


# ---------------------------------------------------------------------------
# Game state (Phase 3)
# ---------------------------------------------------------------------------
class Game:
    def __init__(self, seed, night=1, scenario=None):
        self.seed = seed
        self.rng = random.Random(seed)
        self.night = night
        self.tick = 0
        self.sim_tick = 0
        self.state = "playing"
        self.paused = False
        self.score = 0
        self.night_duration = float(TUNING[f"night{night}_duration_s"])
        self.time_left = self.night_duration

        # --- Người chơi ---
        self.player_pos = [0.0, 0.0, 0.0]
        self.player_vel = [0.0, 0.0, 0.0]
        self.player_yaw = 0.0
        self.player_grounded = True
        self.player_carried = 0
        self.successful_lights = 0
        self.player_flames = int(TUNING["flames"])
        self.invuln_ticks = 0
        self.dash_active = False
        self.dash_remaining_ticks = 0
        self.dash_cooldown_ticks = 0
        self.pulse_cooldown_ticks = 0
        self.charm_ticks = 0

        self.player_move = [0.0, 0.0]
        self.player_interact = False
        self.player_pulse = False
        self.player_dash = False
        self.player_pause = False
        self.player_jump = False
        self._interact_prev = False
        self._pulse_prev = False
        self._dash_prev = False
        self._pause_prev = False
        self._jump_prev = False

        # --- Đèn Lồng Lớn ---
        self.lanterns = []
        self._init_lanterns()

        # --- Đom đóm ---
        self.motes = []
        self.mote_counter = 0
        self.motes_since_spawn = 0

        # --- Bóng Mực ---
        self.shades = []
        self.shade_counter = 0
        self.shade_spawn_timer = 0

        # --- Gió Lạc (Drifters) ---
        self.drifters = []
        self.drifter_counter = 0

        # --- Bùa Gió (Charms) ---
        self.charms = []
        self.charm_counter = 0

        # --- Gió (Wind) ---
        self.wind_active = False
        self.wind_dir_deg = 0.0
        self.wind_ticks_left = 0
        self.wind_next_ticks = 0

        # Đom đóm ban đầu được sinh theo seed để kết quả luôn tái lập.
        for _ in range(TUNING["motes_initial"]):
            self.mote_counter += 1
            angle = self.rng.uniform(0, 2 * math.pi)
            radius = self.rng.uniform(5.0, 35.0)
            self.motes.append({
                "id": f"M{self.mote_counter}",
                "pos": [round3(math.cos(angle) * radius), 0.0,
                        round3(math.sin(angle) * radius)],
                "kind": "random",
                "ttl_s": 0,
            })

        if scenario:
            self._apply_scenario(scenario)

    # ------------------------------------------------------------------
    def _init_lanterns(self):
        if self.night == 1:
            positions = [
                ("L1", [0.0, 0.0, 25.0]),
                ("L2", [23.8, 0.0, 7.7]),
                ("L3", [14.7, 0.0, -20.2]),
                ("L4", [-14.7, 0.0, -20.2]),
                ("L5", [-23.8, 0.0, 7.7]),
            ]
        elif self.night == 2:
            positions = [
                ("L1", [0.0, 0.0, 20.0]),
                ("L2", [17.0, 0.0, -10.0]),
                ("L3", [-17.0, 0.0, -10.0]),
                ("L4", [70.0, 0.0, 20.0]),
                ("L5", [87.0, 0.0, -10.0]),
                ("L6", [53.0, 0.0, -10.0]),
            ]
        else:
            positions = [
                ("L1", [0.0, 6.0, 6.0]),
                ("L2", [18.0, 3.0, 10.0]),
                ("L3", [-18.0, 3.0, 10.0]),
                ("L4", [35.0, 0.0, -10.0]),
                ("L5", [-35.0, 0.0, -10.0]),
                ("L6", [20.0, 0.0, -35.0]),
                ("L7", [-20.0, 0.0, -35.0]),
            ]
        for lid, pos in positions:
            self.lanterns.append({
                "id": lid,
                "pos": [round3(v) for v in pos],
                "lit": False,
                "deposited": 0,
                # Phase 3: nhiên liệu dạng nguyên (đơn vị 1/60 fuel)
                "fuel_60": 0,
                "ever_lit": False,
                "relit_count": 0,
            })
        self.lanterns_by_id = {L["id"]: L for L in self.lanterns}
        self._active_drain_ticks = {}        # shade_id -> ticks liên tục drain, phát event mỗi 60 tick
        # Setting chỉ phục vụ GUI; không tham gia mô phỏng nên không ảnh hưởng JSONL.
        self.colorblind_mode = load_settings().get("colorblind_mode", False)

    # ------------------------------------------------------------------
    @staticmethod
    def _fuel_display(fuel_60):
        """Quy đổi fuel 1/60 sang số thực 1 chữ số cho JSON."""
        return round(max(0, int(fuel_60)) / 60.0, 1)

    def _capacity(self):
        return min(TUNING["capacity_max"], TUNING["carry_capacity"] + 2 * self.successful_lights)

    def _release_shades_from_safe_push(self, L):
        """Khi đèn L đang sáng (fuel >= low_threshold), các Bóng Mực trong
        vùng 6 m bị đẩy ra mép safe_radius trong tối đa safe_push_ticks tick
        và không gây sát thương trong khoảng đó (giống khi đèn vừa thắp)."""
        for S in self.shades:
            if dist2d(S["pos"], L["pos"]) <= TUNING["drain_chase_m"]:
                dx = S["pos"][0] - L["pos"][0]
                dz = S["pos"][2] - L["pos"][2]
                d = math.hypot(dx, dz)
                S["safe_push_dir"] = [dx / d, dz / d] if d > 0 else [1.0, 0.0]
                S["safe_push_lantern_id"] = L["id"]
                S["safe_push_ticks"] = TUNING["safe_push_ticks"]
                # Di chuyển ngay tại tick châm dầu để không thể gây hit trước
                # khi timer safe-push bắt đầu ở tick tiếp theo.
                S["pos"][0] = L["pos"][0] + S["safe_push_dir"][0] * TUNING["safe_radius"]
                S["pos"][2] = L["pos"][2] + S["safe_push_dir"][1] * TUNING["safe_radius"]
                if S["state"] == "drain":
                    S["state"] = "wander"
                    S["drain_lantern_id"] = None

    def _new_shade(self, lid_suffix):
        """Tạo Bóng Mực với đầy đủ trường (Phase 2 + drain/safe-push Phase 3)."""
        self.shade_counter += 1
        return {
            "id": f"S{self.shade_counter}",
            "pos": [0.0, 0.0, 0.0],
            "state": "spawning",
            "state_ticks_left": 60,
            "recoil_dir": [0.0, 0.0],
            "recoil_ticks_left": 0,
            "drain_lantern_id": None,
            "drain_progress_ticks": 0,
            "safe_push_ticks": 0,
            "safe_push_dir": [0.0, 0.0],
            "safe_push_lantern_id": None,
            "target_lantern_id": None,
        }

    def _apply_scenario(self, scenario):
        if "player" in scenario:
            p = scenario["player"]
            if "pos" in p:
                self.player_pos = [float(v) for v in p["pos"]]
            if "carried" in p:
                self.player_carried = int(p["carried"])
            if "flames" in p:
                self.player_flames = int(p["flames"])
            if "invuln_ticks" in p:
                self.invuln_ticks = int(p["invuln_ticks"])
            if "dash_cd_ticks" in p:
                self.dash_cooldown_ticks = int(p["dash_cd_ticks"])
            if "pulse_cd_ticks" in p:
                self.pulse_cooldown_ticks = int(p["pulse_cd_ticks"])
            if "charm_ticks" in p:
                self.charm_ticks = int(p["charm_ticks"])
            if "successful_lights" in p:
                # Đèn đặt sẵn bằng scenario không được tính vào successful_lights;
                # scenario chỉ ghi nhận số lần thắp "đúng nghĩa" trước đó.
                self.successful_lights = int(p["successful_lights"])

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
                    if "ever_lit" in L:
                        target["ever_lit"] = bool(L["ever_lit"])
                    if "relit_count" in L:
                        target["relit_count"] = int(L["relit_count"])
                    if target["lit"]:
                        # lit: true mà không có fuel -> mặc định đầy (100).
                        target["fuel_60"] = int(round(float(L["fuel"]) * 60.0)) if "fuel" in L else FUEL_MAX_60
                        target["ever_lit"] = True
                    else:
                        # Đèn tắt không có nhiên liệu; giữ ever_lit/relit_count từ scenario.
                        target["fuel_60"] = 0

        if "motes" in scenario:
            self.motes = []
            for m in scenario["motes"]:
                self.mote_counter += 1
                if isinstance(m, dict):
                    mid = m.get("id", f"M{self.mote_counter}")
                    mpos = m.get("pos", [0, 0, 0])
                    kind = m.get("kind", "random")
                    ttl = float(m.get("ttl_s", 0))
                    self.motes.append({
                        "id": mid,
                        "pos": [float(mpos[0]), float(mpos[1]), float(mpos[2])],
                        "kind": kind,
                        "ttl_s": ttl,
                    })
                else:
                    self.motes.append({
                        "id": f"M{self.mote_counter}",
                        "pos": [float(m[0]), float(m[1]), float(m[2])],
                        "kind": "random",
                        "ttl_s": 0,
                    })

        if "shades" in scenario:
            self.shades = []
            for s in scenario["shades"]:
                self.shade_counter += 1
                state = s.get("state", "wander")
                self.shades.append({
                    "id": s.get("id", f"S{self.shade_counter}"),
                    "pos": [float(s["pos"][0]), float(s["pos"][1]), float(s["pos"][2])],
                    "state": state,
                    "state_ticks_left": int(s.get("state_ticks_left", 0)),
                    "recoil_dir": [0.0, 0.0],
                    "recoil_ticks_left": 0,
                    "drain_lantern_id": s.get("target_lantern_id"),
                    "drain_progress_ticks": 0,
                    "safe_push_ticks": 0,
                    "safe_push_dir": [0.0, 0.0],
                    "safe_push_lantern_id": None,
                    "target_lantern_id": s.get("target_lantern_id"),
                })

        if "drifters" in scenario:
            self.drifters = []
            for d in scenario["drifters"]:
                self.drifter_counter += 1
                self.drifters.append({
                    "id": d.get("id", f"D{self.drifter_counter}"),
                    "pos": [float(d["pos"][0]), float(d["pos"][1]), float(d["pos"][2])],
                    "state": d.get("state", "idle"),
                    "stolen": int(d.get("stolen", 0)),
                    "flee_ticks_left": 0,
                    "remove_ticks_left": 0,
                })

        if "charms" in scenario:
            self.charms = []
            for c in scenario["charms"]:
                self.charm_counter += 1
                self.charms.append({
                    "id": c.get("id", f"C{self.charm_counter}"),
                    "pos": [float(c["pos"][0]), float(c["pos"][1]), float(c["pos"][2])],
                    "available": bool(c.get("available", True)),
                    "respawn_ticks_left": int(c.get("respawn_ticks_left", 0)),
                })

        if "time_left_s" in scenario:
            self.time_left = float(scenario["time_left_s"])

    # ------------------------------------------------------------------
    def apply_input(self, frame):
        if "move" in frame:
            mx, mz = float(frame["move"][0]), float(frame["move"][1])
            length = math.hypot(mx, mz)
            if length > 1.0:
                mx /= length
                mz /= length
            self.player_move = [mx, mz]
        if "cam_yaw_deg" in frame:
            self.player_yaw = float(frame["cam_yaw_deg"])
        if "interact" in frame:
            self.player_interact = bool(frame["interact"])
        if "pulse" in frame:
            self.player_pulse = bool(frame["pulse"])
        if "dash" in frame:
            self.player_dash = bool(frame["dash"])
        if "pause" in frame:
            self.player_pause = bool(frame["pause"])
        if "jump" in frame:
            self.player_jump = bool(frame["jump"])

    # ------------------------------------------------------------------
    def step(self):
        """Chạy 1 tick (1/60 giây). Trả về danh sách sự kiện (events).
        Thứ tự xử lý theo Test Contract v1.2; fuel được cập nhật ở bước 2."""
        events = []
        dt = 1.0 / TICKS_PER_SECOND

        # --- 1. Đọc input (xử lý pause trước; nếu vừa tạm dừng thì dừng bước) ---
        pause_triggered = self.player_pause and not self._pause_prev
        self._pause_prev = self.player_pause

        if pause_triggered:
            self.paused = not self.paused
            if self.paused:
                events.append({"tick": self.tick + 1, "name": "paused", "data": {}})
            else:
                events.append({"tick": self.tick + 1, "name": "resumed", "data": {}})

        if self.paused:
            self.tick += 1
            return events

        # --- 2. Giảm các bộ đếm ---
        self.time_left -= dt
        self.sim_tick += 1

        if self.invuln_ticks > 0:
            self.invuln_ticks -= 1
        if self.dash_cooldown_ticks > 0:
            self.dash_cooldown_ticks -= 1
        if self.pulse_cooldown_ticks > 0:
            self.pulse_cooldown_ticks -= 1
        if self.charm_ticks > 0:
            self.charm_ticks -= 1
        if self.dash_remaining_ticks > 0:
            self.dash_remaining_ticks -= 1
            if self.dash_remaining_ticks <= 0:
                self.dash_active = False

        # Giảm bộ đếm đẩy ra vùng an toàn (Bóng Mực không gây sát thương trong khi đó)
        for shade in self.shades:
            if shade["safe_push_ticks"] > 0:
                shade["safe_push_ticks"] -= 1

        # Giảm TTL đom đóm rơi
        for mote in self.motes[:]:
            if mote["kind"] == "dropped" and mote["ttl_s"] > 0:
                mote["ttl_s"] -= dt
                if mote["ttl_s"] <= 0:
                    self.motes.remove(mote)

        # Giảm state_ticks_left của Bóng Mực
        for shade in self.shades:
            if shade["state_ticks_left"] > 0:
                shade["state_ticks_left"] -= 1
                if shade["state_ticks_left"] <= 0:
                    if shade["state"] == "stunned":
                        shade["state"] = "wander"
                        shade["drain_lantern_id"] = None
                    elif shade["state"] == "recoil":
                        shade["state"] = "chase"
                    elif shade["state"] == "spawning":
                        shade["state"] = "wander"

        # Giảm flee/remove ticks của Gió Lạc
        for drifter in self.drifters:
            if drifter["flee_ticks_left"] > 0:
                drifter["flee_ticks_left"] -= 1
            if drifter["remove_ticks_left"] > 0:
                drifter["remove_ticks_left"] -= 1

        # Giảm respawn_ticks_left của Bùa Gió
        for charm in self.charms:
            if not charm["available"] and charm["respawn_ticks_left"] > 0:
                charm["respawn_ticks_left"] -= 1
                if charm["respawn_ticks_left"] <= 0:
                    charm["available"] = True

        # --- 2b. Phase 3: trừ nhiên liệu (hao + bị hút), đèn hết dầu thì tắt ---
        active_drain_ids = set()
        for L in self.lanterns:
            if not L["lit"]:
                continue
            L["fuel_60"] -= FUEL_DECAY_60_PER_TICK
            # Mỗi Bóng Mực drain trừ độc lập; event fuel_drain mỗi 60 tick/shade.
            draining_here = [S for S in self.shades if S["state"] == "drain" and S["drain_lantern_id"] == L["id"]]
            for shade in draining_here:
                L["fuel_60"] -= FUEL_DRAIN_60_PER_TICK
                self._active_drain_ticks[shade["id"]] = self._active_drain_ticks.get(shade["id"], 0) + 1
                active_drain_ids.add(shade["id"])
                if self._active_drain_ticks[shade["id"]] % 60 == 0:
                    events.append({
                        "tick": self.tick + 1,
                        "name": "fuel_drain",
                        "data": {
                            "lantern_id": L["id"],
                            "shade_id": shade["id"],
                            "fuel": self._fuel_display(L["fuel_60"]),
                        },
                    })
            if L["fuel_60"] <= 0:
                L["fuel_60"] = 0
                L["lit"] = False
                L["deposited"] = 0
                events.append({
                    "tick": self.tick + 1,
                    "name": "lantern_out",
                    "data": {"lantern_id": L["id"]},
                })
        for shade_id in list(self._active_drain_ticks):
            if shade_id not in active_drain_ids:
                self._active_drain_ticks[shade_id] = 0

        # --- 3. Di chuyển Mây (nhảy, lướt, gió) ---
        jump_triggered = self.player_jump and not self._jump_prev
        self._jump_prev = self.player_jump

        if jump_triggered and self.player_grounded:
            self.player_vel[1] = TUNING["jump_velocity"]
            self.player_grounded = False

        self.player_vel[1] += TUNING["gravity"] * dt

        dash_triggered = self.player_dash and not self._dash_prev
        self._dash_prev = self.player_dash

        if dash_triggered and not self.dash_active and self.dash_cooldown_ticks <= 0:
            self.dash_active = True
            self.dash_remaining_ticks = int(TUNING["dash_duration_s"] * TICKS_PER_SECOND)
            self.dash_cooldown_ticks = int(TUNING["dash_cooldown_s"] * TICKS_PER_SECOND)
            events.append({"tick": self.tick + 1, "name": "dash", "data": {}})

        mx, mz = self.player_move
        if mx != 0.0 or mz != 0.0:
            theta = math.radians(self.player_yaw)
            wx = mx * math.cos(theta) + mz * math.sin(theta)
            wz = -mx * math.sin(theta) + mz * math.cos(theta)
        else:
            wx, wz = 0.0, 0.0

        current_speed = TUNING["charm_speed"] if self.charm_ticks > 0 else TUNING["player_speed"]

        if self.dash_active and self.dash_remaining_ticks > 0:
            step_len = TUNING["dash_speed"] * dt
            self.player_pos[0] += wx * step_len
            self.player_pos[2] += wz * step_len
        else:
            step_len = current_speed * dt
            self.player_pos[0] += wx * step_len
            self.player_pos[2] += wz * step_len

        self.player_pos[1] += self.player_vel[1] * dt

        if self.player_pos[1] <= 0.0:
            self.player_pos[1] = 0.0
            self.player_vel[1] = 0.0
            self.player_grounded = True
        else:
            self.player_grounded = False

        fell_off = self.player_pos[1] < -10.0

        # --- 4. Nhặt đom đóm và bùa (sức chứa động theo Phase 3) ---
        for mote in self.motes[:]:
            if dist2d(self.player_pos, mote["pos"]) <= TUNING["pickup_radius_xz"]:
                if abs(self.player_pos[1] - mote["pos"][1]) <= TUNING["pickup_height_tolerance"]:
                    if self.player_carried < self._capacity():
                        self.motes.remove(mote)
                        self.player_carried += 1
                        events.append({
                            "tick": self.tick + 1,
                            "name": "mote_picked",
                            "data": {"carried": self.player_carried},
                        })

        for charm in self.charms:
            if charm["available"] and dist2d(self.player_pos, charm["pos"]) <= TUNING["pickup_radius_xz"]:
                if abs(self.player_pos[1] - charm["pos"][1]) <= TUNING["pickup_height_tolerance"]:
                    charm["available"] = False
                    self.charm_ticks = TUNING["charm_duration_ticks"]
                    events.append({
                        "tick": self.tick + 1,
                        "name": "charm_picked",
                        "data": {"charm_id": charm["id"], "charm_ticks": self.charm_ticks},
                    })
                    break

        # --- 5. Tương tác đèn: thắp / thắp lại / châm dầu ---
        interact_triggered = self.player_interact and not self._interact_prev
        self._interact_prev = self.player_interact

        if interact_triggered and self.player_carried > 0:
            candidates = [
                L for L in self.lanterns
                if dist2d(self.player_pos, L["pos"]) <= TUNING["interact_radius"]
                and (not L["lit"] or L["fuel_60"] < FUEL_MAX_60)
            ]
            if candidates:
                candidates.sort(key=lambda L: (dist2d(self.player_pos, L["pos"]), L["id"]))
                L = candidates[0]
                if L["lit"]:
                    # Châm dầu: dùng = min(đang mang, ceil((100 - fuel)/10))
                    missing_60 = max(0, FUEL_MAX_60 - L["fuel_60"])
                    used = min(self.player_carried, (missing_60 + FUEL_PER_MOTE_60 - 1) // FUEL_PER_MOTE_60)
                    if used > 0:
                        old_fuel_60 = L["fuel_60"]
                        self.player_carried -= used
                        L["fuel_60"] = min(FUEL_MAX_60, L["fuel_60"] + used * FUEL_PER_MOTE_60)
                        self.score += used * int(TUNING["score"]["per_mote_deposit"])
                        events.append({
                            "tick": self.tick + 1, "name": "refuel",
                            "data": {"lantern_id": L["id"], "amount": used, "fuel": self._fuel_display(L["fuel_60"])},
                        })
                        if old_fuel_60 < LOW_FUEL_60 <= L["fuel_60"]:
                            self._release_shades_from_safe_push(L)
                else:
                    cost = TUNING["relight_cost"] if L["ever_lit"] else TUNING["lantern_cost"]
                    used = min(self.player_carried, cost)
                    if used >= cost:
                        relight = bool(L["ever_lit"])
                        self.player_carried -= used
                        L["fuel_60"] = FUEL_MAX_60
                        L["lit"] = True
                        L["ever_lit"] = True
                        L["deposited"] = 0
                        if relight:
                            L["relit_count"] += 1
                            self.score += int(TUNING["score"]["per_relight"])
                        else:
                            self.score += int(TUNING["score"]["per_first_light"])
                        self.score += used * int(TUNING["score"]["per_mote_deposit"])
                        self.successful_lights += 1
                        events.append({
                            "tick": self.tick + 1, "name": "lantern_lit",
                            "data": {"lantern_id": L["id"], "relight": relight},
                        })
                        self._release_shades_from_safe_push(L)
                    # Chưa đủ đom thì không tiêu tốn và không phát sự kiện.

        # --- 6. Cập nhật vùng an toàn (đèn fuel < 30 mất safe zone) ---
        safe_lanterns = [L for L in self.lanterns if L["lit"] and L["fuel_60"] >= LOW_FUEL_60]
        for shade in self.shades:
            if shade["state"] in ("stunned", "recoil", "drain") or shade["safe_push_ticks"] > 0:
                continue
            for L in safe_lanterns:
                if dist2d(shade["pos"], L["pos"]) <= TUNING["safe_radius"]:
                    dx = shade["pos"][0] - L["pos"][0]
                    dz = shade["pos"][2] - L["pos"][2]
                    d = math.hypot(dx, dz)
                    if d > 0:
                        shade["pos"][0] = L["pos"][0] + (dx / d) * TUNING["safe_radius"]
                        shade["pos"][2] = L["pos"][2] + (dz / d) * TUNING["safe_radius"]
                    break

        # --- 7. Tỏa Sáng ---
        pulse_triggered = self.player_pulse and not self._pulse_prev
        self._pulse_prev = self.player_pulse

        if pulse_triggered and self.pulse_cooldown_ticks <= 0 and self.player_carried >= TUNING["pulse_cost"]:
            self.pulse_cooldown_ticks = int(TUNING["pulse_cooldown_s"] * TICKS_PER_SECOND)
            self.player_carried -= TUNING["pulse_cost"]
            stunned_ids = []
            stun_score = 0
            for shade in self.shades:
                if dist3d(self.player_pos, shade["pos"]) <= TUNING["pulse_radius"]:
                    was_draining = shade["state"] == "drain"
                    if shade["state"] != "stunned":
                        shade["state"] = "stunned"
                        shade["state_ticks_left"] = TUNING["pulse_stun_ticks"]
                    else:
                        shade["state_ticks_left"] = TUNING["pulse_stun_ticks"]
                    shade["drain_lantern_id"] = None
                    stun_score += int(TUNING["score"]["per_stun_drain"] if was_draining else TUNING["score"]["per_stun"])
                    dx = shade["pos"][0] - self.player_pos[0]
                    dz = shade["pos"][2] - self.player_pos[2]
                    d = math.hypot(dx, dz)
                    if d > 0:
                        shade["pos"][0] += (dx / d) * TUNING["pulse_push_m"]
                        shade["pos"][2] += (dz / d) * TUNING["pulse_push_m"]
                    else:
                        shade["pos"][0] += TUNING["pulse_push_m"]
                    stunned_ids.append(shade["id"])
            if stunned_ids:
                events.append({
                    "tick": self.tick + 1,
                    "name": "pulse",
                    "data": {"stunned_ids": stunned_ids},
                })
            self.score += stun_score

        # --- 8. Di chuyển Bóng Mực ---
        shade_speed = TUNING["shade_speed_night3"] if self.night == 3 else TUNING["shade_speed"]
        for shade in self.shades:
            if shade["state"] in ("stunned", "recoil"):
                continue

            # Đẩy ra mép vùng an toàn (do safe_push_ticks, không gây sát thương).
            if shade["safe_push_ticks"] > 0:
                L = self.lanterns_by_id.get(shade.get("safe_push_lantern_id"))
                if L:
                    dx, dz = shade["safe_push_dir"]
                    shade["pos"][0] = L["pos"][0] + dx * TUNING["safe_radius"]
                    shade["pos"][2] = L["pos"][2] + dz * TUNING["safe_radius"]
                continue

            # Trạng thái drain: duy trì trừ khi có điều kiện thoát.
            if shade["state"] == "drain":
                target = self.lanterns_by_id.get(shade["drain_lantern_id"])
                player_near = dist2d(shade["pos"], self.player_pos) <= TUNING["drain_chase_m"]
                if (target is None or not target["lit"] or target["fuel_60"] >= LOW_FUEL_60
                        or dist2d(shade["pos"], target["pos"]) > TUNING["drain_leave_m"]
                        or player_near):
                    shade["state"] = "chase" if player_near else "wander"
                    shade["drain_lantern_id"] = None
                else:
                    continue   # Đang hút: đứng yên, tick sau xử lý tiếp

            near_player = dist2d(shade["pos"], self.player_pos) <= TUNING["shade_detect_m"]
            if near_player:
                shade["state"] = "chase"
            elif shade["state"] != "chase":
                shade["state"] = "wander"

            if shade["state"] == "chase":
                dx = self.player_pos[0] - shade["pos"][0]
                dz = shade["pos"][2] - shade["pos"][2]
                d = math.hypot(dx, dz)
                if d > 0:
                    step_len = shade_speed * dt
                    shade["pos"][0] += (dx / d) * step_len
                    shade["pos"][2] += (dz / d) * step_len
            elif shade["state"] == "wander":
                weak = [L for L in self.lanterns if L["lit"] and L["fuel_60"] < LOW_FUEL_60]
                targets = weak or [L for L in self.lanterns if not L["lit"]]
                target = min(targets, key=lambda L: (dist2d(shade["pos"], L["pos"]), L["id"])) if targets else None
                shade["target_lantern_id"] = target["id"] if target else None
                # Chỉ hút dầu (drain) với đèn SÁNG yếu (fuel < 30); đèn tắt chỉ
                # được tiến lại gần như Phase 2, không có fuel để hút.
                if target and target["lit"] and dist2d(shade["pos"], target["pos"]) <= TUNING["drain_enter_m"]:
                    shade["state"] = "drain"
                    shade["drain_lantern_id"] = target["id"]
                    shade["drain_progress_ticks"] = 0
                    continue
                if target:
                    dx = target["pos"][0] - shade["pos"][0]
                    dz = target["pos"][2] - shade["pos"][2]
                    d = math.hypot(dx, dz)
                    if d > 0:
                        step_len = shade_speed * 0.5 * dt
                        shade["pos"][0] += (dx / d) * step_len
                        shade["pos"][2] += (dz / d) * step_len
                else:
                    angle = self.rng.uniform(0, 2 * math.pi)
                    step_len = shade_speed * 0.5 * dt
                    shade["pos"][0] += math.cos(angle) * step_len
                    shade["pos"][2] += math.sin(angle) * step_len

        # --- 9. Di chuyển Gió Lạc (Drifters) ---
        for drifter in self.drifters:
            if drifter["state"] == "removed":
                continue
            if drifter["state"] == "idle":
                if self.player_carried >= 5 and dist2d(self.player_pos, drifter["pos"]) <= 15.0:
                    drifter["state"] = "chase"
                else:
                    angle = self.rng.uniform(0, 2 * math.pi)
                    step_len = 2.0 * dt
                    drifter["pos"][0] += math.cos(angle) * step_len
                    drifter["pos"][2] += math.sin(angle) * step_len
            elif drifter["state"] == "chase":
                dx = self.player_pos[0] - drifter["pos"][0]
                dz = self.player_pos[2] - drifter["pos"][2]
                d = math.hypot(dx, dz)
                if d > 0:
                    step_len = 7.0 * dt
                    drifter["pos"][0] += (dx / d) * step_len
                    drifter["pos"][2] += (dz / d) * step_len
            elif drifter["state"] == "flee":
                dx = drifter["pos"][0] - self.player_pos[0]
                dz = drifter["pos"][2] - self.player_pos[2]
                d = math.hypot(dx, dz)
                if d > 0:
                    step_len = 7.0 * dt
                    drifter["pos"][0] += (dx / d) * step_len
                    drifter["pos"][2] += (dz / d) * step_len

        # --- 10. Chạm: Gió Lạc cướp trước, rồi Bóng Mực gây hit ---
        for drifter in self.drifters:
            if drifter["state"] == "removed":
                continue
            if dist2d(self.player_pos, drifter["pos"]) <= 1.2:
                if self.player_carried > 0 and drifter["state"] != "flee":
                    stolen = min(3, self.player_carried)
                    self.player_carried -= stolen
                    drifter["stolen"] = stolen
                    drifter["state"] = "flee"
                    drifter["flee_ticks_left"] = 240
                    drifter["remove_ticks_left"] = 240
                    events.append({
                        "tick": self.tick + 1,
                        "name": "drifter_steal",
                        "data": {"drifter_id": drifter["id"], "amount": stolen, "carried": self.player_carried},
                    })

        # Bóng Mực chạm (drain/safe-push không gây sát thương)
        for shade in sorted(self.shades, key=lambda s: s["id"]):
            if shade["state"] in ("stunned", "recoil", "drain") or shade["safe_push_ticks"] > 0:
                continue
            if dist2d(self.player_pos, shade["pos"]) <= TUNING["shade_hit_radius_xz"]:
                if abs(self.player_pos[1] - shade["pos"][1]) <= TUNING["shade_hit_height_tolerance"]:
                    if self.invuln_ticks <= 0:
                        self.player_flames -= 1
                        dropped = self.player_carried // 2
                        self.player_carried -= dropped
                        for i in range(dropped):
                            angle = self.rng.uniform(0, 2 * math.pi)
                            r = self.rng.uniform(1.5, 2.5)
                            self.motes.append({
                                "id": f"M{self.mote_counter + 1 + i}",
                                "pos": [
                                    round3(self.player_pos[0] + math.cos(angle) * r),
                                    0.0,
                                    round3(self.player_pos[2] + math.sin(angle) * r),
                                ],
                                "kind": "dropped",
                                "ttl_s": 8.0,
                            })
                        self.mote_counter += dropped
                        dx = shade["pos"][0] - self.player_pos[0]
                        dz = shade["pos"][2] - self.player_pos[2]
                        d = math.hypot(dx, dz)
                        if d > 0:
                            shade["recoil_dir"] = [dx / d, dz / d]
                        else:
                            shade["recoil_dir"] = [1.0, 0.0]
                        shade["state"] = "recoil"
                        shade["recoil_ticks_left"] = TUNING["shade_recoil_ticks"]
                        self.invuln_ticks = TUNING["shade_invuln_ticks"]
                        events.append({
                            "tick": self.tick + 1,
                            "name": "player_hit",
                            "data": {
                                "by": "shade",
                                "flames": self.player_flames,
                                "dropped": dropped,
                            },
                        })
                        break

        # --- 11. Sinh đom đóm, Bóng Mực, Gió Lạc theo lịch ---
        self.motes_since_spawn += 1
        if self.motes_since_spawn >= TUNING["mote_spawn_interval"]:
            self.motes_since_spawn = 0
            if len(self.motes) < TUNING["motes_cap"]:
                angle = self.rng.uniform(0, 2 * math.pi)
                r = self.rng.uniform(5.0, 35.0)
                self.mote_counter += 1
                self.motes.append({
                    "id": f"M{self.mote_counter}",
                    "pos": [
                        round3(math.cos(angle) * r),
                        0.0,
                        round3(math.sin(angle) * r),
                    ],
                    "kind": "random",
                    "ttl_s": 0,
                })

        # Sinh Bóng Mực
        if self.night == 1:
            max_shades = 6
            spawn_interval = 480
            first_spawn = 300
            initial_count = 2
        elif self.night == 2:
            max_shades = 8
            spawn_interval = 420
            first_spawn = 300
            initial_count = 0
        else:
            max_shades = 10
            spawn_interval = 360
            first_spawn = 300
            initial_count = 0

        if self.tick == first_spawn:
            for i in range(initial_count):
                if len(self.shades) < max_shades:
                    angle = self.rng.uniform(0, 2 * math.pi)
                    r = 37.0 if self.night == 1 else (26.0 if self.night == 2 else 43.0)
                    s = self._new_shade("")
                    s["pos"] = [round3(math.cos(angle) * r), 0.0, round3(math.sin(angle) * r)]
                    self.shades.append(s)
        elif self.tick > first_spawn and (self.tick - first_spawn) % spawn_interval == 0:
            if len(self.shades) < max_shades:
                angle = self.rng.uniform(0, 2 * math.pi)
                r = 37.0 if self.night == 1 else (26.0 if self.night == 2 else 43.0)
                s = self._new_shade("")
                s["pos"] = [round3(math.cos(angle) * r), 0.0, round3(math.sin(angle) * r)]
                self.shades.append(s)

        # Sinh Gió Lạc: tick 1200, 2400, ...; tối đa 2
        if self.tick > 0 and self.tick % 1200 == 0:
            if len(self.drifters) < 2:
                angle = self.rng.uniform(0, 2 * math.pi)
                r = self.rng.uniform(10.0, 40.0)
                self.drifter_counter += 1
                self.drifters.append({
                    "id": f"D{self.drifter_counter}",
                    "pos": [
                        round3(math.cos(angle) * r),
                        0.0,
                        round3(math.sin(angle) * r),
                    ],
                    "state": "idle",
                    "stolen": 0,
                    "flee_ticks_left": 0,
                    "remove_ticks_left": 0,
                })

        # --- 12. Xét thắng/thua sau mọi cập nhật của tick (bao gồm tick bình minh) ---
        if self.state == "playing":
            result = None
            reason = None
            if self.player_flames <= 0:
                result, reason = "lost", "no_flames"
            elif self.time_left <= 0:
                lit_count = sum(1 for L in self.lanterns if L["lit"] and L["fuel_60"] > 0)
                required = math.ceil(TUNING["win_ratio"] * len(self.lanterns))
                if lit_count >= required:
                    result, reason = "won", "dawn_survived"
                    for L in self.lanterns:
                        if L["lit"] and L["fuel_60"] > 0:
                            # floor(fuel) = số đơn vị fuel nguyên (fuel_60 // 60),
                            # tính theo 1/60 để tránh sai số số thực.
                            self.score += int(TUNING["score"]["dawn_per_lantern_lit"])
                            self.score += L["fuel_60"] // 60
                    self.score += self.player_flames * int(TUNING["score"]["dawn_per_flame_left"])
                else:
                    result, reason = "lost", "dawn"
            if result:
                self.state = result
                events.append({
                    "tick": self.tick + 1,
                    "name": "game_over",
                    "data": {"result": result, "reason": reason},
                })

        self.tick += 1
        return events
    # ------------------------------------------------------------------
    def snapshot(self):
        """Tạo ảnh chụp trạng thái (theo Test Contract v1.2 §E)."""
        return {
            "type": "snapshot",
            "tick": self.tick,
            "sim_tick": self.sim_tick,
            "state": self.state,
            "night": self.night,
            "time_left_s": round3(max(0.0, self.time_left)),
            "score": self.score,
            "wind": {
                "active": self.wind_active,
                "dir_deg": round3(self.wind_dir_deg),
            },
            "player": {
                "pos": [round3(v) for v in self.player_pos],
                "vel": [round3(v) for v in self.player_vel],
                "flames": self.player_flames,
                "carried": self.player_carried,
                "capacity": self._capacity(),
                "grounded": self.player_grounded,
                "invuln": self.invuln_ticks,
                "dash_cd_s": round3(self.dash_cooldown_ticks / 60.0),
                "pulse_cd_s": round3(self.pulse_cooldown_ticks / 60.0),
                "charm_s": self.charm_ticks,
            },
            "lanterns": [
                {
                    "id": L["id"],
                    "pos": [round3(v) for v in L["pos"]],
                    "lit": L["lit"],
                    "fuel": self._fuel_display(L["fuel_60"]),
                    "deposited": L["deposited"],
                    "ever_lit": L["ever_lit"],
                    "relit_count": L["relit_count"],
                }
                for L in self.lanterns
            ],
            "shades": [
                {
                    "id": S["id"],
                    "pos": [round3(v) for v in S["pos"]],
                    "state": S["state"],
                    "target_lantern_id": S.get("target_lantern_id"),
                }
                for S in self.shades
            ],
            "motes": [
                {
                    "id": m["id"],
                    "pos": [round3(v) for v in m["pos"]],
                    "kind": m["kind"],
                    "ttl_s": round3(m["ttl_s"]),
                }
                for m in self.motes
            ],
            "drifters": [
                {
                    "id": d["id"],
                    "pos": [round3(v) for v in d["pos"]],
                    "state": d["state"],
                    "stolen": d["stolen"],
                }
                for d in self.drifters
            ],
            "charms": [
                {
                    "id": c["id"],
                    "pos": [round3(v) for v in c["pos"]],
                    "available": c["available"],
                    "respawn_s": round3(c["respawn_ticks_left"] / 60.0),
                }
                for c in self.charms
            ],
        }


# ---------------------------------------------------------------------------
# Điểm vào chính
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Đảo Đèn Lồng headless (Phase 3, Contract v1.2)")
    parser.add_argument("--seed", type=int, required=True, help="hạt giống ngẫu nhiên")
    parser.add_argument("--night", type=int, required=True, help="mã đêm (1, 2, 3)")
    parser.add_argument("--scenario", type=str, default=None, help="file scenario JSON")
    parser.add_argument("--inputs", type=str, default=None, help="file inputs JSON")
    parser.add_argument("--ticks", type=int, required=True, help="số bước mô phỏng")
    parser.add_argument("--out", type=str, required=True, help="file đầu ra JSONL")
    parser.add_argument("--snapshot-every", type=int, default=10,
                        help="khoảng cách snapshot (mặc định 10)")
    args = parser.parse_args()

    if args.night not in (1, 2, 3):
        print("Chỉ hỗ trợ night 1, 2, 3 ở Phase 3", file=sys.stderr)
        return 1

    scenario = None
    if args.scenario:
        try:
            with open(args.scenario, "r", encoding="utf-8") as f:
                scenario = json.load(f)
        except Exception as exc:
            print(f"Lỗi đọc scenario: {exc}", file=sys.stderr)
            return 2

    inputs = {"frames": []}
    if args.inputs:
        try:
            with open(args.inputs, "r", encoding="utf-8") as f:
                inputs = json.load(f)
        except Exception as exc:
            print(f"Lỗi đọc inputs: {exc}", file=sys.stderr)
            return 2

    input_by_tick = {}
    for frame in inputs.get("frames", []):
        input_by_tick[int(frame.get("tick", 0))] = frame

    try:
        game = Game(args.seed, args.night, scenario)
    except Exception as exc:
        print(f"Lỗi khởi tạo game: {exc}", file=sys.stderr)
        return 2

    lines = []
    if args.snapshot_every > 0 and game.tick % args.snapshot_every == 0:
        lines.append(json.dumps(game.snapshot(), ensure_ascii=False))

    for step in range(args.ticks):
        if game.state not in ("playing",):
            break
        frame = input_by_tick.get(step, {})
        game.apply_input(frame)
        events = game.step()
        for ev in events:
            lines.append(json.dumps(ev if isinstance(ev, dict) and "type" in ev else {"type": "event", **ev}, ensure_ascii=False))
        if args.snapshot_every > 0 and game.tick % args.snapshot_every == 0:
            lines.append(json.dumps(game.snapshot(), ensure_ascii=False))

    lines.append(json.dumps({
        "type": "end",
        "ticks": game.tick,
        "state": game.state,
        "score": game.score,
    }, ensure_ascii=False))

    try:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
    except Exception as exc:
        print(f"Lỗi ghi output: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())