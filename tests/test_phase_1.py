"""
Test cho Phase 1 (PRD-0 + Test Contract v1.0).
Chạy: python -m pytest tests/test_phase_1.py -v
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest

HEADLESS = [sys.executable, "src/game_headless.py"]
CWD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def run_headless(seed, ticks, scenario=None, inputs=None, snapshot_every=10):
    with tempfile.TemporaryDirectory() as td:
        out_path = os.path.join(td, "out.jsonl")
        cmd = HEADLESS + [
            "--seed", str(seed),
            "--night", "1",
            "--ticks", str(ticks),
            "--out", out_path,
            "--snapshot-every", str(snapshot_every),
        ]
        if scenario:
            sc_path = os.path.join(td, "scenario.json")
            with open(sc_path, "w", encoding="utf-8") as f:
                json.dump(scenario, f)
            cmd += ["--scenario", sc_path]
        if inputs:
            in_path = os.path.join(td, "inputs.json")
            with open(in_path, "w", encoding="utf-8") as f:
                json.dump(inputs, f)
            cmd += ["--inputs", in_path]
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=CWD)
        lines = []
        if os.path.exists(out_path):
            with open(out_path, "r", encoding="utf-8") as f:
                lines = [json.loads(line) for line in f if line.strip()]
        return result.returncode, lines, result.stderr


class TestPhase1Headless(unittest.TestCase):
    def test_headless_runs_ok(self):
        rc, lines, err = run_headless(seed=42, ticks=120)
        self.assertEqual(rc, 0, msg=err)
        self.assertGreater(len(lines), 0)
        self.assertEqual(lines[0]["type"], "snapshot")
        self.assertEqual(lines[0]["tick"], 0)
        self.assertEqual(lines[-1]["type"], "end")
        self.assertIn(lines[-1]["state"], ("playing", "won", "lost"))

    def test_deterministic_output(self):
        scenario = {
            "motes": [[5, 0, 5], [10, 0, 10]],
            "shades": [{"pos": [30, 0, 0]}],
            "lanterns": [{"id": "L1", "pos": [0, 0, 25], "deposited": 0}],
        }
        inputs = {
            "frames": [
                {"tick": 0, "move": [1, 0], "cam_yaw_deg": 0},
                {"tick": 60, "interact": True},
                {"tick": 120, "pulse": True},
                {"tick": 121, "pulse": False},
            ]
        }
        _, lines1, _ = run_headless(seed=7, ticks=300, scenario=scenario, inputs=inputs)
        _, lines2, _ = run_headless(seed=7, ticks=300, scenario=scenario, inputs=inputs)
        self.assertEqual(lines1, lines2)

    def test_snapshot_has_required_fields(self):
        # Cập nhật theo Test Contract v1.1 (Phase 2): snapshot không còn field
        # "motes_active" (v1.0), thay bằng "motes" và các entity mới
        # (drifters, charms, wind).
        rc, lines, _ = run_headless(seed=1, ticks=60)
        self.assertEqual(rc, 0)
        snap = lines[0]
        for field in ("type", "tick", "sim_tick", "state", "time_left_s", "score",
                      "player", "lanterns", "shades", "motes", "drifters", "charms"):
            self.assertIn(field, snap)
        self.assertIn("pos", snap["player"])
        self.assertIn("flames", snap["player"])
        self.assertIn("carried", snap["player"])

    def test_end_line_is_last(self):
        rc, lines, _ = run_headless(seed=1, ticks=60)
        self.assertEqual(rc, 0)
        self.assertEqual(lines[-1]["type"], "end")
        self.assertIn("ticks", lines[-1])
        self.assertIn("state", lines[-1])
        self.assertIn("score", lines[-1])

    def test_coordinates_rounded_3_decimals(self):
        rc, lines, _ = run_headless(seed=1, ticks=10)
        self.assertEqual(rc, 0)
        snap = lines[0]
        for L in snap["lanterns"]:
            for coord in L["pos"]:
                self.assertEqual(coord, round(coord, 3))
        p = snap["player"]["pos"]
        for coord in p:
            self.assertEqual(coord, round(coord, 3))

    def test_movement_changes_position(self):
        inputs = {
            "frames": [
                {"tick": 0, "move": [1, 0], "cam_yaw_deg": 0},
            ]
        }
        _, lines_start, _ = run_headless(seed=1, ticks=1, inputs=inputs)
        _, lines_end, _ = run_headless(seed=1, ticks=60, inputs=inputs)
        pos_0 = lines_start[0]["player"]["pos"]
        last_snap = lines_end[-2] if lines_end[-1]["type"] == "end" else lines_end[-1]
        pos_60 = last_snap["player"]["pos"]
        self.assertNotEqual(pos_0, pos_60)

    def test_pickup_mote(self):
        scenario = {"motes": [[2, 0, 0]]}
        inputs = {
            "frames": [
                {"tick": 0, "interact": True},
            ]
        }
        rc, lines, _ = run_headless(seed=1, ticks=2, scenario=scenario, inputs=inputs)
        self.assertEqual(rc, 0)
        events = [l for l in lines if l["type"] == "event"]
        picked = [e for e in events if e["name"] == "mote_picked"]
        self.assertGreaterEqual(len(picked), 0)

    def test_deposit_and_light_lantern(self):
        scenario = {
            # Contract v1.1 tăng lantern_cost từ 1 lên 10.
            "player": {"pos": [0, 0, 25], "carried": 10, "flames": 3},
            "lanterns": [{"id": "L1", "pos": [0, 0, 25], "deposited": 0}],
        }
        inputs = {
            "frames": [
                {"tick": 0, "interact": True},
            ]
        }
        rc, lines, _ = run_headless(seed=1, ticks=2, scenario=scenario, inputs=inputs)
        self.assertEqual(rc, 0)
        events = [l for l in lines if l["type"] == "event"]
        lit = [e for e in events if e["name"] == "lantern_lit"]
        self.assertGreaterEqual(len(lit), 1, f"Expected lantern_lit event, got: {events}")

    def test_all_lanterns_lit_wins(self):
        scenario = {
            "lanterns": [
                {"id": "L1", "pos": [0, 0, 1], "deposited": 0, "lit": False},
                {"id": "L2", "pos": [0, 0, 2], "deposited": 0, "lit": False},
                {"id": "L3", "pos": [0, 0, 3], "deposited": 0, "lit": False},
                {"id": "L4", "pos": [0, 0, 4], "deposited": 0, "lit": False},
                {"id": "L5", "pos": [0, 0, 5], "deposited": 0, "lit": False},
            ],
            # Contract v1.1: năm đèn, mỗi đèn cần 10 motes.
            "player": {"pos": [0, 0, 3], "carried": 50, "flames": 3},
        }
        # Cần interact 5 lần (1 cho mỗi đèn), mỗi lần phải bật/tắt (edge-triggered)
        inputs = {
            "frames": [
                {"tick": 0, "interact": True},
                {"tick": 1, "interact": False},
                {"tick": 2, "interact": True},
                {"tick": 3, "interact": False},
                {"tick": 4, "interact": True},
                {"tick": 5, "interact": False},
                {"tick": 6, "interact": True},
                {"tick": 7, "interact": False},
                {"tick": 8, "interact": True},
            ]
        }
        rc, lines, _ = run_headless(seed=1, ticks=15, scenario=scenario, inputs=inputs)
        self.assertEqual(rc, 0)
        end = lines[-1]
        self.assertEqual(end["state"], "won")

    def test_lantern_count_night1_is_5(self):
        rc, lines, _ = run_headless(seed=1, ticks=1)
        self.assertEqual(rc, 0)
        lanterns = lines[0]["lanterns"]
        self.assertEqual(len(lanterns), 5)
        ids = {L["id"] for L in lanterns}
        self.assertEqual(ids, {"L1", "L2", "L3", "L4", "L5"})


if __name__ == "__main__":
    unittest.main()