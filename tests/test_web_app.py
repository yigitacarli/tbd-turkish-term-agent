import io
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from terim_etmeni.config import Settings
from terim_etmeni.dictionary import DictionaryIndex
from terim_etmeni.web_app import WebApplication, _multipart, result_html


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
        self.assertIn("sample_report.csv", rendered)

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

