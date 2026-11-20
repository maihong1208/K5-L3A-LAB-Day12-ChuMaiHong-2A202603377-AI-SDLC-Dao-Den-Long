"""Phase 4 (TICKET-04 / Test Contract v1.3) regression tests.

Kiểm tra: bảng xếp hạng (top 10, tên, thứ tự), đổi phím + phát hiện trùng
+ khôi phục mặc định, cỡ chữ UI, và schema của bench/soak (không cần chạy
thật các lệnh dài — chỉ kiểm tra hàm sinh/thống kê + cấu trúc output).
"""
import json
import unittest
from pathlib import Path

from src import leaderboard, settings_store
from src.benchmark_stats import summarize_frame_times
from src.game_gui import LanternGame, scancode_for
from src.game_headless import Game
from src.settings_store import DEFAULT_KEYBINDS, ACTIONS


class TestLeaderboard(unittest.TestCase):
    def setUp(self):
        self.path = "/tmp/lb_test_%d.json" % __import__("os").getpid()
        leaderboard.reset(self.path)

    def tearDown(self):
        import os
        try:
            os.remove(self.path)
        except OSError:
            pass

    def test_name_validation(self):
        self.assertTrue(leaderboard.name_is_valid("ABC"))
        self.assertTrue(leaderboard.name_is_valid("a_1234567890"))  # 12 ký tự
        self.assertFalse(leaderboard.name_is_valid("ab"))            # ngắn
        self.assertFalse(leaderboard.name_is_valid("a" * 13))        # dài
        self.assertFalse(leaderboard.name_is_valid("bad name!"))     # ký tự sai

    def test_top10_and_order(self):
        # 12 mục, giữ top 10; điểm cao nhất đứng trên.
        for i in range(12):
            leaderboard.add_entry(f"P{i:02d}", (i + 1) * 100, 1, 7, self.path)
        entries = leaderboard.export(self.path)["entries"]
        self.assertEqual(len(entries), 10)
        # P11 (1200) là cao nhất -> đứng đầu.
        self.assertEqual(entries[0]["name"], "P11")
        self.assertEqual(entries[0]["score"], 1200)
        # P00 (100) bị loại.
        self.assertNotIn("P00", [e["name"] for e in entries])

    def test_tie_earlier_wins(self):
        # Cùng điểm: mục đạt sớm hơn (achieved_at nhỏ) đứng trên.
        leaderboard.add_entry("AAA", 500, 1, 7, self.path, when="2026-11-01T00:00:00+07:00")
        leaderboard.add_entry("BBB", 500, 1, 7, self.path, when="2026-11-02T00:00:00+07:00")
        entries = leaderboard.export(self.path)["entries"]
        self.assertEqual([e["name"] for e in entries], ["AAA", "BBB"])

    def test_reject_invalid_nights_won(self):
        with self.assertRaises(leaderboard.LeaderboardError):
            leaderboard.add_entry("OK", 10, 4, 7, self.path)


class TestSettings(unittest.TestCase):
    def test_default_keybinds_no_conflict(self):
        s = settings_store._defaults()
        self.assertEqual(settings_store.key_conflicts(s), [])
        # Mọi ACTIONS đều có keybind.
        for act in ACTIONS:
            self.assertIn(act, s["keybinds"])

    def test_key_conflict_detected(self):
        s = settings_store._defaults()
        s["keybinds"]["up"] = "w"
        s["keybinds"]["left"] = "w"  # trùng 'w'
        self.assertEqual(settings_store.key_conflicts(s), [["left", "up"]])

    def test_reset_keybinds(self):
        s = settings_store._defaults()
        s["keybinds"]["up"] = "x"
        settings_store.reset_keybinds(s, "/tmp/never_created_reset_test.json")
        self.assertEqual(s["keybinds"], DEFAULT_KEYBINDS)

    def test_ui_font_size(self):
        self.assertEqual(settings_store.ui_font_size({"large_text": False}), 18)
        self.assertEqual(settings_store.ui_font_size({"large_text": True}), 22)  # 18*1.25


class TestGuiInput(unittest.TestCase):
    def setUp(self):
        self.gui = LanternGame.__new__(LanternGame)
        self.gui.settings = settings_store._defaults()
        self.gui.current = Game(1, 1, {
            "player": {"pos": [0, 0, 25], "carried": 15},
            "lanterns": [{"id": "L1", "pos": [0, 0, 25]}],
        })
        self.keys = [False] * 512

    def test_movement_uses_pygame_keycodes(self):
        self.keys[scancode_for("w")] = True
        frame = self.gui.read_frame(self.keys, {})
        self.assertEqual(frame["move"], [0.0, 1.0])

    def test_interaction_edge_resets_so_next_press_works(self):
        first = self.gui.read_frame(self.keys, {"interact": True})
        self.gui.current.apply_input(first)
        first_events = self.gui.current.step()
        self.assertIn("lantern_lit", [event["name"] for event in first_events])

        released = self.gui.read_frame(self.keys, {})
        self.assertFalse(released["interact"])
        self.gui.current.apply_input(released)
        self.gui.current.step()

        second = self.gui.read_frame(self.keys, {"interact": True})
        self.gui.current.apply_input(second)
        second_events = self.gui.current.step()
        self.assertIn("refuel", [event["name"] for event in second_events])

    def test_pause_edge_toggles_and_release_does_not_resume(self):
        pause = self.gui.read_frame(self.keys, {"pause": True})
        self.gui.current.apply_input(pause)
        self.gui.current.step()
        self.assertTrue(self.gui.current.paused)

        released = self.gui.read_frame(self.keys, {})
        self.gui.current.apply_input(released)
        self.gui.current.step()
        self.assertTrue(self.gui.current.paused)

        resume = self.gui.read_frame(self.keys, {"pause": True})
        self.gui.current.apply_input(resume)
        self.gui.current.step()
        self.assertFalse(self.gui.current.paused)


class TestBenchSoakStats(unittest.TestCase):
    """Kiểm tra thống kê production và contract mà không chạy benchmark dài."""

    def test_p1_low_fps_formula(self):
        stats = summarize_frame_times([16.0] * 1000)
        self.assertAlmostEqual(stats["p1_low_fps"], 62.5, places=2)
        self.assertAlmostEqual(stats["avg_fps"], 62.5, places=2)
        self.assertEqual(stats["frames"], 1000)

    def test_p95_formula(self):
        stats = summarize_frame_times([float(i) for i in range(1, 101)])
        self.assertEqual(stats["frame_ms_p95"], 95.0)

    def test_empty_benchmark_has_zero_metrics(self):
        self.assertEqual(
            summarize_frame_times([]),
            {
                "avg_fps": 0.0,
                "p1_low_fps": 0.0,
                "frame_ms_p95": 0.0,
                "frames": 0,
            },
        )

    def test_contract_matches_phase_4_commands_and_schema(self):
        contract_path = Path(__file__).resolve().parents[1] / "game.contract.json"
        with contract_path.open(encoding="utf-8") as contract_file:
            contract = json.load(contract_file)

        self.assertEqual(contract["contract_version"], "1.3")
        for command in ("bench_cmd", "soak_cmd", "export_leaderboard_cmd"):
            self.assertTrue(contract[command].startswith("python src/"))


if __name__ == "__main__":
    unittest.main()
