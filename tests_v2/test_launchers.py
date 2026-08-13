from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class LauncherTests(unittest.TestCase):
    def test_daily_launchers_start_v2(self):
        apple = (ROOT / "BASLAT_APPLE.command").read_text(encoding="utf-8")
        windows = (ROOT / "BASLAT_WINDOWS.bat").read_text(encoding="utf-8")

        self.assertIn('run_v2.py "$@"', apple)
        self.assertNotIn('run.py "$@"', apple)
        self.assertEqual(windows.count("run_v2.py"), 3)
        self.assertNotIn(" run.py", windows)


if __name__ == "__main__":
    unittest.main()
