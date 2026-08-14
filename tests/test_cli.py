import unittest

from terim_etmeni.cli import build_parser


class CliTests(unittest.TestCase):
    def test_serve_opens_browser_by_default_and_can_disable_it(self):
        parser = build_parser()
        self.assertFalse(parser.parse_args(["serve"]).no_browser)
        self.assertTrue(parser.parse_args(["serve", "--no-browser"]).no_browser)


if __name__ == "__main__":
    unittest.main()
