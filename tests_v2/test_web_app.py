import json
import tempfile
import unittest
from pathlib import Path

from terim_etmeni_v2.config import Settings
from terim_etmeni_v2.service import AnalysisService
from terim_etmeni_v2.web_app import dictionary_html, index_html, result_html


class WebAppTests(unittest.TestCase):
    def service(self, root):
        dictionary = root / "dictionary.json"
        dictionary.write_text(
            json.dumps({"metadata": {"version": "2026-08-13"}, "terms": [{"en": "AI", "tr": "YZ"}]}),
            encoding="utf-8",
        )
        settings = Settings(
            bootstrap_dictionary=dictionary,
            dictionary_state_dir=root / "state",
            output_dir=root / "output",
        )
        service = AnalysisService(settings)
        service.installed_models = lambda: (["test-model"], "")
        return service

    def test_main_page_keeps_dictionary_and_article_flow_simple(self):
        with tempfile.TemporaryDirectory() as directory:
            rendered = index_html(self.service(Path(directory)))
        self.assertIn("Güncel sözlük: 2026-08-13", rendered)
        self.assertIn("Makale PDF'si", rendered)
        self.assertIn("Eksik terimleri bul", rendered)

    def test_dictionary_management_is_a_separate_page(self):
        with tempfile.TemporaryDirectory() as directory:
            rendered = dictionary_html(self.service(Path(directory)))
        self.assertIn("TBD sitesini kontrol et", rendered)
        self.assertIn("Sözlük PDF'sini elle yükle", rendered)

    def test_result_warns_when_analysis_is_partial(self):
        rendered = result_html(
            {
                "analysis_status": "partial",
                "dictionary_version": "v1",
                "model": "test",
                "missing_terms": [],
                "possible_matches": [],
                "dictionary_matches": [],
            },
            {"json": "a.json", "csv": "a.csv", "xlsx": "a.xlsx"},
        )
        self.assertIn("0 eksik terim", rendered)
        self.assertIn("Analiz kısmi tamamlandı", rendered)


if __name__ == "__main__":
    unittest.main()

