import io
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from terim_etmeni.config import Settings
from terim_etmeni.dictionary import DictionaryIndex
from terim_etmeni.web_app import (
    WebApplication,
    _model_display_name,
    _model_guidance,
    _multipart,
    _preferred_installed_model,
    result_html,
)


class WebApplicationTests(unittest.TestCase):
    def setUp(self):
        self.result = {
            "document": "sample.pdf",
            "model": "qwen:latest",
            "dictionary_version": "test",
            "page_count": 1,
            "counts": {
                "dictionary_matches": 1,
                "possible_matches": 1,
                "missing_terms": 1,
                "rejected_candidates": 0,
            },
            "dictionary_matches": [
                {
                    "term": "machine learning",
                    "translations": ["makine öğrenmesi"],
                    "pages": [1],
                    "occurrence_count": 1,
                }
            ],
            "possible_matches": [
                {
                    "term": "neural networks",
                    "possible_dictionary_terms": [
                        {"en": "neural network", "tr": "sinir ağı"}
                    ],
                    "pages": [1],
                    "occurrence_count": 2,
                }
            ],
            "missing_terms": [
                {
                    "term": "semantic photon router",
                    "pages": [1],
                    "occurrence_count": 1,
                }
            ],
            "rejected_candidates": [],
        }

    def test_result_page_contains_all_groups_and_downloads(self):
        rendered = result_html(self.result, "sample_terms.json", "sample_report.csv")
        self.assertIn("Sözlükte bulunanlar", rendered)
        self.assertIn("Olası eşleşmeler", rendered)
        self.assertIn("Sözlükte olmayanlar", rendered)
        self.assertIn("semantic photon router", rendered)
        self.assertIn("İnceleme sırası", rendered)
        self.assertIn("Yüksek öncelik", rendered)
        self.assertIn("Orta öncelik", rendered)
        self.assertIn("Düşük öncelik", rendered)
        self.assertIn("İnceleme CSV’sini indir", rendered)
        self.assertIn("sample_report.csv", rendered)

    def test_result_page_separates_low_priority_recovered_terms(self):
        result = dict(self.result)
        result["counts"] = dict(self.result["counts"], missing_terms=2)
        result["missing_terms"] = list(self.result["missing_terms"]) + [
            {
                "term": "DNS",
                "pages": [1],
                "occurrence_count": 2,
                "review_priority": "low",
                "reason": "single_word_review",
            }
        ]
        rendered = result_html(result, "sample_terms.json", "sample_report.csv")
        self.assertIn("Düşük öncelikli eksik adaylar (1)", rendered)
        self.assertIn("tek sözcüklü terim veya kısaltma", rendered)
        self.assertIn("geri kazanılan, bulunan ve elenen", rendered)

    def test_failed_analysis_is_not_presented_as_zero_missing_success(self):
        result = dict(self.result)
        result["analysis_status"] = "failed"
        result["failed_chunk_count"] = 5
        result["processed_chunk_count"] = 0
        result["processing_warnings"] = ["invalid JSON"]
        rendered = result_html(result, "sample_terms.json", "sample_report.csv")
        self.assertIn("Analiz eksik kaldı", rendered)
        self.assertIn("Model analizi tamamlanamadı", rendered)
        self.assertIn("“0 eksik” anlamına gelmez", rendered)

    def test_model_guidance_and_installed_fallback_are_conservative(self):
        profile, advice = _model_guidance("qwen3.5:2b")
        self.assertIn("Önerilen hafif profil", profile)
        self.assertIn("başlangıç", advice)
        self.assertEqual(
            _preferred_installed_model(["qwen3.5:9b", "qwen3.5:2b"], "missing"),
            "qwen3.5:2b",
        )
        self.assertEqual(
            _preferred_installed_model(["custom:latest"], "missing"),
            "custom:latest",
        )
        self.assertEqual(
            _model_display_name("qwen2.5:1.5b"),
            "Qwen 2.5 · 1.5B — Eski hafif model (qwen2.5:1.5b)",
        )
        self.assertEqual(
            _model_display_name("custom-model:7b"),
            "Custom Model · 7B (custom-model:7b)",
        )

    def test_index_shows_ollama_status_and_upload_form(self):
        app = object.__new__(WebApplication)
        app.settings = Settings()
        app.dictionary = DictionaryIndex(
            [{"en": "machine learning", "tr": "makine öğrenmesi"}]
        )
        with patch.object(app, "model_status", return_value=(["qwen:latest"], None)):
            rendered = app.index_html()
        self.assertIn("Ollama hazır", rendered)
        self.assertIn('type="file"', rendered)
        self.assertIn("qwen:latest", rendered)
        self.assertIn("Qwen · 4B — Eski dengeli model", rendered)
        self.assertIn('<option value="qwen:latest" selected', rendered)
        self.assertIn("İlk kurulum: işletim sisteminizi seçin", rendered)
        self.assertIn("Hangi modeli seçmeliyim?", rendered)
        self.assertIn("Standart bilgisayar · önerilen", rendered)
        self.assertIn("ollama pull qwen3.5:2b", rendered)
        self.assertIn('id="model-help"', rendered)
        self.assertIn("Büyük model zorunlu değildir", rendered)
        self.assertIn("Baslat.bat", rendered)
        self.assertIn("platform-windows", rendered)

    def test_multipart_parser_reads_pdf_and_model(self):
        boundary = "test-boundary"
        body = (
            "--{0}\r\nContent-Disposition: form-data; name=\"model\"\r\n\r\n"
            "qwen:latest\r\n"
            "--{0}\r\nContent-Disposition: form-data; name=\"pdf\"; filename=\"test.pdf\"\r\n"
            "Content-Type: application/pdf\r\n\r\n%PDF-test\r\n"
            "--{0}--\r\n"
        ).format(boundary).encode()
        handler = SimpleNamespace(
            headers={
                "Content-Length": str(len(body)),
                "Content-Type": "multipart/form-data; boundary={}".format(boundary),
            },
            rfile=io.BytesIO(body),
        )
        fields, files = _multipart(handler)
        self.assertEqual(fields["model"], "qwen:latest")
        self.assertEqual(files["pdf"], ("test.pdf", b"%PDF-test"))


if __name__ == "__main__":
    unittest.main()
