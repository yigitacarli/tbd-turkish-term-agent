from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class LauncherTests(unittest.TestCase):
    def setUp(self):
        self.apple = (ROOT / "BASLAT_MAC.command").read_text(encoding="utf-8")
        self.windows = (ROOT / "BASLAT_WINDOWS.bat").read_text(encoding="utf-8")

    def test_daily_launchers_start_the_app(self):
        self.assertIn('run.py "$@"', self.apple)
        self.assertIn("run.py", self.windows)

    def test_launchers_prefer_the_virtualenv_interpreter(self):
        self.assertIn(".venv/bin/python3", self.apple)
        self.assertIn(r".venv\Scripts\python.exe", self.windows)

    def test_launchers_check_dependencies_before_starting(self):
        """Temiz bir bilgisayarda ham ImportError yerine Türkçe açıklama çıkmalı."""
        for script in (self.apple, self.windows):
            self.assertIn("import pdfplumber, openpyxl", script)
            self.assertIn("pip install -e .", script)
        self.assertIn("Gerekli kütüphaneler kurulu değil", self.apple)
        self.assertIn("Gerekli kutuphaneler kurulu degil", self.windows)

    def test_launchers_check_the_python_version(self):
        for script in (self.apple, self.windows):
            self.assertIn("sys.version_info >= (3, 9)", script)

    def test_windows_launcher_does_not_read_errorlevel_inside_a_block(self):
        """`%errorlevel%` bir parantez bloğunun içinde erken genişler; bu hata tekrarlanmamalı."""
        depth = 0
        for line_number, line in enumerate(self.windows.splitlines(), 1):
            if depth > 0 and "%errorlevel%" in line.casefold():
                self.fail(
                    "Satır {}: %errorlevel% parantez bloğu içinde okunuyor".format(line_number)
                )
            depth += line.count("(") - line.count(")")
            depth = max(depth, 0)

    def test_windows_launcher_is_ascii_only(self):
        """Komut istemi varsayılan kod sayfasında Türkçe karakterler bozuk görünür."""
        self.windows.encode("ascii")


if __name__ == "__main__":
    unittest.main()
