import io
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from terim_etmeni.config import Settings
from terim_etmeni.dictionary import DictionaryIndex
from terim_etmeni.web_app import (
    WebApplication,
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
        self.assertIn("semantic photon router", rendered)
        self.assertIn("Karar listesi", rendered)
        self.assertIn("İncelenecek sözlük açıkları", rendered)
        self.assertIn("Yakın sözlük eşleşmeleri", rendered)
        self.assertIn("İnceleme CSV’sini indir", rendered)
        self.assertIn("sample_report.csv", rendered)

    def test_result_page_moves_legacy_low_priority_terms_to_audit_details(self):
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
        self.assertIn("Elenen adaylar (1)", rendered)
        self.assertIn("Eksik sayısı yalnız puan eşiğini geçen", rendered)

    def test_latest_result_keeps_nested_report_path_in_download_links(self):
        with tempfile.TemporaryDirectory() as directory:
            output_dir = Path(directory)
            report_dir = output_dir / "evaluation" / "qwen35-4b" / "sample"
            report_dir.mkdir(parents=True)
            (report_dir / "sample_terms.json").write_text(
                json.dumps(self.result), encoding="utf-8"
            )
            app = object.__new__(WebApplication)
            app.settings = Settings(output_dir=output_dir)

            rendered = app.latest_result_html()

        self.assertIsNotNone(rendered)
        self.assertIn(
            "/reports/evaluation/qwen35-4b/sample/sample_terms.json",
            rendered,
        )
        self.assertIn(
            "/reports/evaluation/qwen35-4b/sample/sample_terim_raporu.xlsx",
            rendered,
        )

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

    def test_model_is_preselected_only_by_explicit_environment_setting(self):
        models = ["future-model:latest", "qwen3.5:2b"]
        self.assertEqual(_preferred_installed_model(models, ""), "")
        self.assertEqual(_preferred_installed_model(models, "missing"), "")
        self.assertEqual(
            _preferred_installed_model(models, "future-model:latest"),
            "future-model:latest",
        )

    def test_index_shows_ollama_status_and_upload_form(self):
        app = object.__new__(WebApplication)
        app.settings = Settings()
        app.dictionary = DictionaryIndex(
            [{"en": "machine learning", "tr": "makine öğrenmesi"}]
        )
        with patch.object(
            app,
            "model_status",
            return_value=(["qwen3.5:2b", "granite4.1:3b", "gemma3:4b"], None),
        ):
            rendered = app.index_html()
        self.assertIn("Ollama hazır", rendered)
        self.assertIn('type="file"', rendered)
        self.assertIn("qwen3.5:2b", rendered)
        self.assertIn("granite4.1:3b", rendered)
        self.assertIn("gemma3:4b", rendered)
        self.assertIn('<option value="" disabled selected>Bir model seçin</option>', rendered)
        self.assertNotIn('<option value="qwen3.5:2b" selected', rendered)
        self.assertIn("Kurulum ve model rehberi", rendered)
        self.assertIn("Uygulama belirli bir modele bağlı değildir", rendered)
        self.assertIn("Küçük modeller", rendered)
        self.assertIn("Orta modeller", rendered)
        self.assertIn("Büyük modeller", rendered)
        self.assertIn("Eksik terimleri bul", rendered)
        self.assertIn("Model seçin", rendered)
        self.assertNotIn('id="model-help"', rendered)

    def test_index_does_not_show_default_model_when_ollama_is_unavailable(self):
        app = object.__new__(WebApplication)
        app.settings = Settings()
        app.dictionary = DictionaryIndex([])
        with patch.object(app, "model_status", return_value=([], "connection refused")):
            rendered = app.index_html()
        self.assertIn("Ollama bağlantısı yok", rendered)
        self.assertIn("Ollama kurulmadı veya çalışmıyor", rendered)
        self.assertNotIn('<option value="qwen3.5:2b"', rendered)
        self.assertIn('<select id="model-select" name="model" required disabled>', rendered)
        self.assertIn('<button class="button" type="submit" disabled>', rendered)
        self.assertIn("Kurulum ve model rehberi", rendered)
        self.assertIn("ollama pull MODEL_ETIKETI", rendered)
        self.assertIn("macOS", rendered)
        self.assertIn("Windows", rendered)

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
