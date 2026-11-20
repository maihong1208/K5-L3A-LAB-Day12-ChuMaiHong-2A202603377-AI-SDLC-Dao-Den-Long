"""Phase 3 (Ticket-03 / Test Contract v1.2) regression tests."""
import unittest

from src.game_headless import FUEL_MAX_60, Game, TUNING


class TestPhase3Fuel(unittest.TestCase):
    def game(self, scenario=None, night=1):
        return Game(7, night, scenario)

    def test_lit_scenario_defaults_to_full_fuel_and_remembers_light(self):
        game = self.game({"lanterns": [{"id": "L1", "lit": True}]})
        lantern = game.lanterns_by_id["L1"]
        self.assertEqual(lantern["fuel_60"], FUEL_MAX_60)
        self.assertTrue(lantern["ever_lit"])

    def test_fuel_decay_uses_integer_sixtieths(self):
        game = self.game({"lanterns": [{"id": "L1", "lit": True, "fuel": 50}]})
        for _ in range(60):
            game.step()
        self.assertEqual(game._fuel_display(game.lanterns_by_id["L1"]["fuel_60"]), 49.0)

    def test_empty_lantern_goes_out_and_resets_deposit(self):
        game = self.game({"lanterns": [{"id": "L1", "lit": True, "fuel": 0.1, "deposited": 8}]})
        events = []
        for _ in range(6):  # 0.1 fuel = 6 đơn vị 1/60, hao 1/tick -> tắt sau 6 tick
            events += game.step()
        lantern = game.lanterns_by_id["L1"]
        self.assertFalse(lantern["lit"])
        self.assertEqual(lantern["fuel_60"], 0)
        self.assertEqual(lantern["deposited"], 0)
        self.assertTrue(lantern["ever_lit"])
        self.assertIn("lantern_out", [event["name"] for event in events])

    def test_refuel_rounds_mote_use_up_and_awards_points(self):
        game = self.game({
            "player": {"pos": [0, 0, 25], "carried": 2},
            "lanterns": [{"id": "L1", "pos": [0, 0, 25], "lit": True, "fuel": 81}],
        })
        game.apply_input({"interact": True})
        events = game.step()
        lantern = game.lanterns_by_id["L1"]
        self.assertEqual(lantern["fuel_60"], FUEL_MAX_60)
        self.assertEqual(game.player_carried, 0)
        self.assertEqual(game.score, 10)
        refuel = next(event for event in events if event["name"] == "refuel")
        self.assertEqual(refuel["data"]["amount"], 2)
        self.assertEqual(refuel["data"]["fuel"], 100.0)

    def test_first_light_then_relight_costs_and_capacity(self):
        game = self.game({
            "player": {"pos": [0, 0, 25], "carried": 10},
            "lanterns": [{"id": "L1", "pos": [0, 0, 25]}],
        })
        game.apply_input({"interact": True})
        events = game.step()
        lantern = game.lanterns_by_id["L1"]
        self.assertTrue(lantern["lit"])
        self.assertEqual(game.successful_lights, 1)
        self.assertEqual(game._capacity(), 12)
        self.assertEqual(game.score, 150)
        self.assertEqual(next(e for e in events if e["name"] == "lantern_lit")["data"]["relight"], False)

    def test_relight_cost_and_score(self):
        game = self.game({
            "player": {"pos": [0, 0, 25], "carried": 5},
            "lanterns": [{"id": "L1", "pos": [0, 0, 25], "ever_lit": True}],
        })
        game.apply_input({"interact": True})
        events = game.step()
        lantern = game.lanterns_by_id["L1"]
        self.assertTrue(lantern["lit"])
        self.assertEqual(lantern["relit_count"], 1)
        self.assertEqual(game.score, 65)
        self.assertTrue(next(e for e in events if e["name"] == "lantern_lit")["data"]["relight"])


class TestPhase3Dawn(unittest.TestCase):
    def test_all_lit_does_not_end_before_dawn(self):
        game = Game(1, 1, {"lanterns": [{"id": f"L{i}", "lit": True} for i in range(1, 6)]})
        game.step()
        self.assertEqual(game.state, "playing")

    def test_dawn_threshold_wins_and_scores_remaining_fuel(self):
        game = Game(1, 1, {
            "time_left_s": 1 / 60,
            "lanterns": [{"id": f"L{i}", "lit": i <= 3, "fuel": 50} for i in range(1, 6)],
            "player": {"flames": 2},
        })
        events = game.step()
        self.assertEqual(game.state, "won")
        # Mỗi đèn hao đúng 1/60 ở tick bình minh: floor(49.9)=49.
        self.assertEqual(game.score, 3 * (50 + 49) + 2 * 50)
        self.assertEqual(next(e for e in events if e["name"] == "game_over")["data"]["reason"], "dawn_survived")

    def test_dawn_below_threshold_loses(self):
        game = Game(1, 1, {
            "time_left_s": 1 / 60,
            "lanterns": [{"id": f"L{i}", "lit": i <= 2} for i in range(1, 6)],
        })
        events = game.step()
        self.assertEqual(game.state, "lost")
        self.assertEqual(next(e for e in events if e["name"] == "game_over")["data"]["reason"], "dawn")

    def test_no_flames_takes_precedence_at_dawn(self):
        game = Game(1, 1, {
            "time_left_s": 1 / 60,
            "lanterns": [{"id": f"L{i}", "lit": True} for i in range(1, 6)],
            "player": {"flames": 0},
        })
        events = game.step()
        self.assertEqual(game.state, "lost")
        self.assertEqual(next(e for e in events if e["name"] == "game_over")["data"]["reason"], "no_flames")


class TestPhase3Drain(unittest.TestCase):
    def test_wander_shade_enters_drain_near_weak_lantern(self):
        game = Game(1, 1, {
            "player": {"pos": [100, 0, 100]},
            "lanterns": [{"id": "L1", "pos": [5, 0, 0], "lit": True, "fuel": 20}],
            "shades": [{"id": "S1", "pos": [5, 0, 0], "state": "wander"}],
        })
        game.step()
        self.assertEqual(game.shades[0]["state"], "drain")
        self.assertEqual(game.shades[0]["drain_lantern_id"], "L1")

    def test_drain_removes_five_fuel_per_second_plus_decay(self):
        # Đèn yếu (fuel < 30) mới bị hút dầu liên tục; hao 1/s + hút 5/s = 6/s.
        game = Game(1, 1, {
            "player": {"pos": [100, 0, 100]},
            "lanterns": [{"id": "L1", "pos": [5, 0, 0], "lit": True, "fuel": 25}],
            "shades": [{"id": "S1", "pos": [5, 0, 0], "state": "drain", "target_lantern_id": "L1"}],
        })
        start = game.lanterns_by_id["L1"]["fuel_60"]
        for _ in range(60):
            game.step()
        self.assertEqual(game.lanterns_by_id["L1"]["fuel_60"], start - 60 - 300)

    def test_refueling_to_threshold_pushes_shade_out_and_protects_player(self):
        game = Game(1, 1, {
            "player": {"pos": [0, 0, 25], "carried": 2},
            "lanterns": [{"id": "L1", "pos": [0, 0, 25], "lit": True, "fuel": 20}],
            "shades": [{"id": "S1", "pos": [1, 0, 25], "state": "wander"}],
        })
        game.apply_input({"interact": True})
        game.step()
        shade = game.shades[0]
        self.assertGreater(shade["safe_push_ticks"], 0)
        self.assertAlmostEqual(
            ((shade["pos"][0] - 0) ** 2 + (shade["pos"][2] - 25) ** 2) ** 0.5,
            TUNING["safe_radius"],
        )

    def test_drain_pulse_awards_fifteen_and_stuns(self):
        game = Game(1, 1, {
            "player": {"pos": [0, 0, 0], "carried": 3},
            "shades": [{"id": "S1", "pos": [1, 0, 0], "state": "drain", "target_lantern_id": "L1"}],
        })
        game.apply_input({"pulse": True})
        game.step()
        self.assertEqual(game.shades[0]["state"], "stunned")
        self.assertEqual(game.score, 15)


if __name__ == "__main__":
    unittest.main()
