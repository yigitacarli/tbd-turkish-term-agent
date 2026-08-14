import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from terim_etmeni.dictionary_store import DictionaryStore
from terim_etmeni.dictionary_update import check_and_update, discover_pdf_url


class DictionaryUpdateTests(unittest.TestCase):
    def _store(self, root):
        bootstrap = root / "bootstrap.json"
        bootstrap.write_text(
            json.dumps({"metadata": {"version": "v1"}, "terms": [{"en": "AI", "tr": "YZ"}]}),
            encoding="utf-8",
        )
        return DictionaryStore(root / "state", bootstrap)

    def test_pdf_url_can_be_discovered_from_an_embed(self):
        html = b'<iframe src="/docs/latest-dictionary.pdf?raw=1"></iframe>'
        with patch("terim_etmeni.dictionary_update._request", return_value=html):
            url = discover_pdf_url("https://example.test/dictionary/")
        self.assertEqual(url, "https://example.test/docs/latest-dictionary.pdf?raw=1")

    def test_wordpress_pdf_poster_is_preferred_over_menu_reports(self):
        html = (
            '<a href="/docs/report.pdf">report</a>'
            '<div data-attributes=\'{&quot;file&quot;:&quot;https:\/\/example.test\/docs\/TBD-Bili\\u015fim-S\\u00f6zl\\u00fc\\u011f\\u00fc-2026.pdf&quot;}\'></div>'
        ).encode()
        with patch("terim_etmeni.dictionary_update._request", return_value=html):
            url = discover_pdf_url("https://example.test/dictionary/")
        self.assertIn("TBD-Bili%C5%9Fim-S%C3%B6zl%C3%BC%C4%9F%C3%BC-2026.pdf", url)

    def test_failed_remote_update_preserves_bootstrap(self):
        with tempfile.TemporaryDirectory() as directory:
            store = self._store(Path(directory))
            with patch("terim_etmeni.dictionary_update._request", side_effect=OSError("offline")):
                result = check_and_update(store, page_url="https://example.test")
            self.assertEqual(result.status, "failed")
            self.assertEqual(store.status().version, "v1")
            self.assertIn("son sağlam sözlük", result.message)


if __name__ == "__main__":
    unittest.main()
