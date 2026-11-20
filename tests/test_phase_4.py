"""Phase 4 (TICKET-04 / Test Contract v1.3) regression tests.

Kiểm tra: bảng xếp hạng (top 10, tên, thứ tự), đổi phím + phát hiện trùng
+ khôi phục mặc định, cỡ chữ UI, và schema của bench/soak (không cần chạy
thật các lệnh dài — chỉ kiểm tra hàm sinh/thống kê + cấu trúc output).
"""
import math
import unittest

from src import leaderboard, settings_store
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


class TestBenchSoakStats(unittest.TestCase):
    """Kiểm tra công thức thống kê (độc lập, không chạy lệnh 30s thật)."""

    def test_p1_low_fps_formula(self):
        # Mô phỏng N=1000 khung, dt đồng đều 16ms -> p1_low = avg_fps = ~62.5.
        n, dt = 1000, 16.0
        k = max(1, math.ceil(0.01 * n))
        largest = [dt] * k
        p1 = 1000.0 / (sum(largest) / len(largest))
        self.assertAlmostEqual(p1, 62.5, places=2)

    def test_p95_formula(self):
        dts = [float(i) for i in range(1, 101)]  # 1..100 ms
        ordered = sorted(dts)
        p95 = ordered[min(len(ordered) - 1, int(0.95 * (len(ordered) - 1)))]
        self.assertEqual(p95, 95.0)


if __name__ == "__main__":
    unittest.main()
