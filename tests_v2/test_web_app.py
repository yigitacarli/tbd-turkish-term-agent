import io
import json
import tempfile
import unittest
from pathlib import Path

from terim_etmeni_v2.config import Settings
from terim_etmeni_v2.service import AnalysisService
from terim_etmeni_v2.web_app import (
    acceptance_from_fields,
    dictionary_html,
    evaluation_html,
    evaluation_label_html,
    index_html,
    result_html,
    Handler,
    validate_bind_host,
)


class WebAppTests(unittest.TestCase):
    def test_server_rejects_non_loopback_bind_addresses(self):
        self.assertEqual(validate_bind_host("localhost"), "localhost")
        self.assertEqual(validate_bind_host("127.0.0.1"), "127.0.0.1")
        self.assertEqual(validate_bind_host("::1"), "::1")
        for host in ("0.0.0.0", "::", "192.168.1.10", "server.example"):
            with self.subTest(host=host), self.assertRaisesRegex(
                ValueError, "yalnız localhost"
            ):
                validate_bind_host(host)

    def test_health_endpoint_is_minimal_and_has_security_headers(self):
        handler = object.__new__(Handler)
        statuses = []
        headers = {}
        handler.send_response = statuses.append
        handler.send_header = headers.__setitem__
        handler.end_headers = lambda: None
        handler.wfile = io.BytesIO()

        handler._health()

        self.assertEqual(statuses, [200])
        self.assertEqual(json.loads(handler.wfile.getvalue()), {"status": "ok"})
        self.assertEqual(headers["X-Frame-Options"], "DENY")
        self.assertEqual(headers["X-Content-Type-Options"], "nosniff")
        self.assertIn(
            "frame-ancestors 'none'", headers["Content-Security-Policy"]
        )

    def service(self, root):
        dictionary = root / "dictionary.json"
        dictionary.write_text(
            json.dumps({"metadata": {"version": "2026-08-13"}, "terms": [{"en": "AI", "tr": "YZ"}]}),
            encoding="utf-8",
        )
        abbreviations = root / "abbreviations.json"
        abbreviations.write_text(
            json.dumps(
                {
                    "metadata": {"version": "2025-03-17"},
                    "abbreviations": [
                        {
                            "abbreviation": "AI",
                            "expansion": "Artificial Intelligence",
                            "turkish": "yapay zekâ",
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        settings = Settings(
            bootstrap_dictionary=dictionary,
            bootstrap_abbreviations=abbreviations,
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
        self.assertIn("Ayrı kısaltma kaynağı", rendered)
        self.assertIn("Ana sözlüğe birleştirilmez", rendered)

    def test_result_separates_abbreviation_source_from_dictionary_matches(self):
        rendered = result_html(
            {
                "analysis_status": "complete",
                "dictionary_version": "v1",
                "model": "test",
                "missing_terms": [],
                "dictionary_matches": [],
                "possible_matches": [
                    {
                        "term": "DNS",
                        "pages": [1],
                        "occurrence_count": 2,
                        "match_source": "tbd_abbreviations",
                        "possible_dictionary_terms": [
                            {"en": "Domain Name System", "tr": "alan adı sistemi"}
                        ],
                    }
                ],
            },
            {"json": "a.json", "csv": "a.csv", "xlsx": "a.xlsx"},
        )
        self.assertIn("Kısaltma kaynağında", rendered)
        self.assertIn("Domain Name System", rendered)
        self.assertIn("alan adı sistemi", rendered)

    def test_internal_evaluation_page_accepts_multiple_json_reports(self):
        rendered = evaluation_html()
        self.assertIn("İç değerlendirme kümesi", rendered)
        self.assertIn('name="v1_reports"', rendered)
        self.assertIn('name="v2_reports"', rendered)
        self.assertIn("multiple", rendered)
        self.assertIn("uzman onayı değildir", rendered)

    def test_label_page_requires_one_of_three_decisions_for_every_term(self):
        rendered = evaluation_label_html(
            {
                "documents": [
                    {
                        "document": "article.pdf",
                        "terms": [
                            {
                                "term": "machine learning",
                                "label": "",
                                "observed_in": ["v2:dictionary_matches"],
                                "evidence": [
                                    {
                                        "source": "v2:dictionary_matches",
                                        "pages": [2, 4],
                                        "occurrence_count": 3,
                                    }
                                ],
                            }
                        ],
                    }
                ]
            }
        )
        self.assertIn("machine learning", rendered)
        self.assertIn("Sözlükte var", rendered)
        self.assertIn("Gerçek sözlük açığı", rendered)
        self.assertIn("Gürültü", rendered)
        self.assertIn("Kanıt sayfaları: 2, 4", rendered)
        self.assertIn("Sistem grubunu göster", rendered)
        self.assertIn('name="label_0"', rendered)
        self.assertIn("required", rendered)

    def test_internal_review_export_is_marked_and_grouped_by_document(self):
        result = acceptance_from_fields(
            {
                "candidate_count": "2",
                "document_0": "article.pdf",
                "term_0": "machine learning",
                "label_0": "dictionary_match",
                "observed_0": '["v1:dictionary_matches"]',
                "evidence_0": '[{"source":"v1:dictionary_matches","pages":[1]}]',
                "document_1": "article.pdf",
                "term_1": "new protocol",
                "label_1": "missing_term",
                "observed_1": '["v2:missing_terms"]',
                "evidence_1": '[{"source":"v2:missing_terms","pages":[3]}]',
            }
        )
        self.assertEqual(result["review_status"], "internal_review")
        self.assertEqual(len(result["documents"]), 1)
        self.assertEqual(len(result["documents"][0]["terms"]), 2)
        self.assertEqual(
            result["documents"][0]["terms"][1]["evidence"][0]["pages"], [3]
        )

    def test_internal_review_export_rejects_an_unlabelled_term(self):
        with self.assertRaisesRegex(ValueError, "Bütün adaylar"):
            acceptance_from_fields(
                {
                    "candidate_count": "1",
                    "document_0": "article.pdf",
                    "term_0": "machine learning",
                    "label_0": "",
                }
            )

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
