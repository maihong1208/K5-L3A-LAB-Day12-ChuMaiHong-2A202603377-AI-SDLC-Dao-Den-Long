"""
Test đơn vị cho chương trình headless CP0.
Chạy: python -m pytest tests/   hoac   python -m unittest discover tests
"""

import json
import subprocess
import sys
import unittest


class TestHelloHeadless(unittest.TestCase):
    def test_headless_runs_and_returns_ok(self):
        """Chương trình headless phải chạy thành công và in status 'ok'."""
        result = subprocess.run(
            [sys.executable, "src/hello_headless.py"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)

        output = json.loads(result.stdout)
        self.assertEqual(output["status"], "ok")
        self.assertEqual(output["mode"], "headless")
        self.assertEqual(output["phase"], "CP0")

    def test_deterministic_output(self):
        """Cùng dau vao -> cung ket qua (tinh tat dinh)."""
        run1 = subprocess.run(
            [sys.executable, "src/hello_headless.py"],
            capture_output=True, text=True,
        )
        run2 = subprocess.run(
            [sys.executable, "src/hello_headless.py"],
            capture_output=True, text=True,
        )
        self.assertEqual(run1.stdout, run2.stdout)


if __name__ == "__main__":
    unittest.main()