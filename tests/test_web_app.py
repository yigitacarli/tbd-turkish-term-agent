from __future__ import annotations

import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


from terim_etmeni.config import Settings
from terim_etmeni.provider_store import ProviderConfig
from terim_etmeni.service import AnalysisBusyError, AnalysisService
from terim_etmeni.web_app import (
    Handler,
    Server,
    dictionary_html,
    index_html,
    result_html,
    settings_html,
    validate_bind_host,
)


class WebAppTests(unittest.TestCase):
    def service(self, root: Path) -> AnalysisService:
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
            provider_config_file=root / "provider.json",
        )
        settings.output_dir.mkdir(parents=True, exist_ok=True)
        service = AnalysisService(settings)
        service.installed_models = lambda: (["test-model"], "")
        return service

    def _make_handler(self, path: str, method: str = "GET", headers: dict[str, str] | None = None, body: bytes = b"", service: AnalysisService | None = None):
        handler = object.__new__(Handler)
        handler.path = path
        handler.command = method
        handler.request_version = "HTTP/1.1"
        headers_dict = dict(headers or {})
        if body and "Content-Length" not in headers_dict:
            headers_dict["Content-Length"] = str(len(body))

        from email.message import Message
        msg = Message()
        for k, v in headers_dict.items():
            msg[k] = v
        handler.headers = msg
        handler.rfile = io.BytesIO(body)
        handler.wfile = io.BytesIO()

        statuses = []
        response_headers = {}

        def send_response(code, message=None):
            statuses.append(code)

        def send_header(keyword, value):
            response_headers[keyword] = value

        def send_error(code, message=None, explain=None):
            statuses.append(code)

        handler.send_response = send_response
        handler.send_header = send_header
        handler.end_headers = lambda: None
        handler.send_error = send_error

        server = object.__new__(Server)
        server.service = service
        handler.server = server
        return handler, statuses, response_headers

    def test_server_rejects_non_loopback_bind_addresses(self):
        self.assertEqual(validate_bind_host("localhost"), "localhost")
        self.assertEqual(validate_bind_host("127.0.0.1"), "127.0.0.1")
        self.assertEqual(validate_bind_host("::1"), "::1")
        for host in ("0.0.0.0", "::", "192.168.1.10", "10.0.0.1", "server.example", "8.8.8.8"):
            with self.subTest(host=host), self.assertRaisesRegex(
                ValueError, "yalnız localhost"
            ):
                validate_bind_host(host)

    def test_health_endpoint_is_minimal_and_has_security_headers(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            service = self.service(Path(tmp_dir))
            for path in ("/healthz", "/health", "/api/healthz"):
                with self.subTest(path=path):
                    handler, statuses, headers = self._make_handler(path, service=service)
                    handler.do_GET()
                    self.assertEqual(statuses, [200])
                    self.assertEqual(json.loads(handler.wfile.getvalue()), {"status": "ok"})
                    self.assertEqual(headers["X-Frame-Options"], "DENY")
                    self.assertEqual(headers["X-Content-Type-Options"], "nosniff")
                    self.assertEqual(headers["Referrer-Policy"], "no-referrer")
                    self.assertIn("frame-ancestors 'none'", headers["Content-Security-Policy"])
                    self.assertEqual(headers["Cache-Control"], "no-store")

    def test_get_html_endpoints_and_security_headers(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            service = self.service(Path(tmp_dir))
            for path in ("/", "/dictionary", "/settings", "/api", "/api/dictionary", "/api/settings"):
                with self.subTest(path=path):
                    handler, statuses, headers = self._make_handler(path, service=service)
                    handler.do_GET()
                    self.assertEqual(statuses, [200])
                    self.assertIn("text/html", headers["Content-Type"])
                    self.assertEqual(headers["X-Frame-Options"], "DENY")
                    self.assertEqual(headers["X-Content-Type-Options"], "nosniff")
                    self.assertEqual(headers["Referrer-Policy"], "no-referrer")
                    self.assertIn("frame-ancestors 'none'", headers["Content-Security-Policy"])

    def test_get_404_on_unknown_path(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            service = self.service(Path(tmp_dir))
            handler, statuses, _ = self._make_handler("/nonexistent_page", service=service)
            handler.do_GET()
            self.assertEqual(statuses, [404])

    def test_post_settings_save(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            service = self.service(Path(tmp_dir))
            for path in ("/settings/save", "/settings", "/api/settings"):
                with self.subTest(path=path):
                    body = b"provider=deepseek&model=deepseek-chat&api_key=sk-secret123&base_url="
                    handler, statuses, headers = self._make_handler(
                        path,
                        method="POST",
                        headers={"Content-Type": "application/x-www-form-urlencoded"},
                        body=body,
                        service=service,
                    )
                    handler.do_POST()
                    self.assertEqual(statuses, [200])
                    self.assertIn("API ayarları kaydedildi.", handler.wfile.getvalue().decode("utf-8"))
                    saved = service.provider_store.load()
                    self.assertEqual(saved.provider, "deepseek")
                    self.assertEqual(saved.api_key, "sk-secret123")

    def test_post_analyze_success(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            service = self.service(Path(tmp_dir))
            # Mock analyze_upload
            mock_result = {
                "document": "test.pdf",
                "model": "test-model",
                "dictionary_version": "2026-08-13",
                "analysis_status": "complete",
                "missing_terms": [{"term": "zero knowledge proof", "pages": [1], "occurrence_count": 2, "context": "Sample"}],
                "dictionary_matches": [],
                "possible_matches": [],
            }
            json_p = service.settings.output_dir / "test_terms.json"
            csv_p = service.settings.output_dir / "test_terim_raporu.csv"
            xlsx_p = service.settings.output_dir / "test_terim_raporu.xlsx"
            json_p.write_text("{}", encoding="utf-8")
            csv_p.write_text("a", encoding="utf-8")
            xlsx_p.write_text("b", encoding="utf-8")

            service.analyze_upload = lambda fname, content, model: (mock_result, json_p, csv_p, xlsx_p)

            boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
            body = (
                f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="pdf"; filename="test.pdf"\r\n'
                f"Content-Type: application/pdf\r\n\r\n"
                f"%PDF-1.4 mock content\r\n"
                f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="model"\r\n\r\n'
                f"test-model\r\n"
                f"--{boundary}--\r\n"
            ).encode("utf-8")

            for path in ("/analyze", "/api/analyze"):
                with self.subTest(path=path):
                    handler, statuses, headers = self._make_handler(
                        path,
                        method="POST",
                        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
                        body=body,
                        service=service,
                    )
                    handler.do_POST()
                    self.assertEqual(statuses, [200])
                    response_text = handler.wfile.getvalue().decode("utf-8")
                    self.assertIn("zero knowledge proof", response_text)
                    self.assertIn("Excel Raporunu İndir", response_text)

    def test_post_analyze_missing_file_or_invalid_pdf(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            service = self.service(Path(tmp_dir))
            boundary = "----Boundary123"
            # Missing pdf field
            body_no_pdf = (
                f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="model"\r\n\r\n'
                f"test-model\r\n"
                f"--{boundary}--\r\n"
            ).encode("utf-8")

            handler, statuses, _ = self._make_handler(
                "/analyze",
                method="POST",
                headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
                body=body_no_pdf,
                service=service,
            )
            handler.do_POST()
            self.assertEqual(statuses, [400])
            import html as htmllib
            self.assertIn("Makale PDF'sini seçin.", htmllib.unescape(handler.wfile.getvalue().decode("utf-8")))

            # Non-PDF payload
            body_bad_pdf = (
                f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="pdf"; filename="test.txt"\r\n'
                f"Content-Type: text/plain\r\n\r\n"
                f"This is not a PDF\r\n"
                f"--{boundary}--\r\n"
            ).encode("utf-8")

            handler2, statuses2, _ = self._make_handler(
                "/analyze",
                method="POST",
                headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
                body=body_bad_pdf,
                service=service,
            )
            handler2.do_POST()
            self.assertEqual(statuses2, [400])
            self.assertIn("Geçerli bir makale PDF'si seçin.", htmllib.unescape(handler2.wfile.getvalue().decode("utf-8")))


    def test_post_analyze_busy_returns_503(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            service = self.service(Path(tmp_dir))
            def mock_busy(*args, **kwargs):
                raise AnalysisBusyError("Analiz kapasitesi dolu. Devam eden çalışma bitince yeniden deneyin.")
            service.analyze_upload = mock_busy

            boundary = "----Boundary123"
            body = (
                f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="pdf"; filename="doc.pdf"\r\n'
                f"Content-Type: application/pdf\r\n\r\n"
                f"%PDF-1.4 data\r\n"
                f"--{boundary}--\r\n"
            ).encode("utf-8")

            handler, statuses, headers = self._make_handler(
                "/analyze",
                method="POST",
                headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
                body=body,
                service=service,
            )
            handler.do_POST()
            self.assertEqual(statuses, [503])
            self.assertIn("Analiz kapasitesi dolu", handler.wfile.getvalue().decode("utf-8"))

    def test_faulty_malformed_requests(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            service = self.service(Path(tmp_dir))

            # Overly large request (> 60 MB)
            handler, statuses, _ = self._make_handler(
                "/analyze",
                method="POST",
                headers={"Content-Type": "application/x-www-form-urlencoded", "Content-Length": str(70 * 1024 * 1024)},
                body=b"",
                service=service,
            )
            handler.do_POST()
            self.assertEqual(statuses, [400])

            # Invalid Content-Length
            handler2, statuses2, _ = self._make_handler(
                "/analyze",
                method="POST",
                headers={"Content-Type": "application/x-www-form-urlencoded", "Content-Length": "not-a-number"},
                body=b"abc",
                service=service,
            )
            handler2.do_POST()
            self.assertEqual(statuses2, [400])

            # Invalid content-type for urlencoded
            handler3, statuses3, _ = self._make_handler(
                "/settings/save",
                method="POST",
                headers={"Content-Type": "text/plain"},
                body=b"some text",
                service=service,
            )
            handler3.do_POST()
            self.assertEqual(statuses3, [400])

            # Unknown POST endpoint
            handler4, statuses4, _ = self._make_handler(
                "/unknown/endpoint",
                method="POST",
                body=b"",
                service=service,
            )
            handler4.do_POST()
            self.assertEqual(statuses4, [404])

    def test_reports_download_and_path_traversal_protection(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            service = self.service(Path(tmp_dir))
            out_file = service.settings.output_dir / "valid_report.xlsx"
            out_file.write_bytes(b"PK mock xlsx content")

            # 1. Valid download
            handler, statuses, headers = self._make_handler(
                "/reports/valid_report.xlsx",
                service=service,
            )
            handler.do_GET()
            self.assertEqual(statuses, [200])
            self.assertEqual(headers["Content-Type"], "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            self.assertIn("attachment", headers["Content-Disposition"])
            self.assertEqual(handler.wfile.getvalue(), b"PK mock xlsx content")

            # 2. Path traversal attempt (../../etc/passwd)
            handler_trav, statuses_trav, _ = self._make_handler(
                "/reports/..%2F..%2Fetc%2Fpasswd",
                service=service,
            )
            handler_trav.do_GET()
            self.assertEqual(statuses_trav, [404])

            # 3. Disallowed file extension (.py or .exe)
            py_file = service.settings.output_dir / "script.py"
            py_file.write_bytes(b"print(1)")
            handler_ext, statuses_ext, _ = self._make_handler(
                "/reports/script.py",
                service=service,
            )
            handler_ext.do_GET()
            self.assertEqual(statuses_ext, [404])

            # 4. Non-existent file
            handler_none, statuses_none, _ = self._make_handler(
                "/reports/non_existent.json",
                service=service,
            )
            handler_none.do_GET()
            self.assertEqual(statuses_none, [404])

    def test_main_page_keeps_dictionary_and_article_flow_simple(self):
        with tempfile.TemporaryDirectory() as directory:
            rendered = index_html(self.service(Path(directory)))
        self.assertIn("Güncel sözlük: 2026-08-13", rendered)
        self.assertIn("Makale PDF'si", rendered)
        self.assertIn("Eksik terimleri bul", rendered)

    def test_main_page_uses_api_mode_when_a_key_is_configured(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            service = self.service(root)
            service.save_provider_config(
                ProviderConfig("deepseek", "secret", "deepseek-chat")
            )
            rendered = index_html(service)
        self.assertIn("Bulut API", rendered)
        self.assertIn("deepseek", rendered)
        self.assertNotIn("Yerel analiz modeli", rendered)

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

    def test_result_shows_term_context(self):
        rendered = result_html(
            {
                "analysis_status": "complete",
                "dictionary_version": "v1",
                "model": "test",
                "missing_terms": [
                    {
                        "term": "agentic workflow",
                        "found_in_dictionary": False,
                        "context": "An agentic workflow runs here.",
                        "pages": [1],
                        "occurrence_count": 1,
                    }
                ],
                "possible_matches": [],
                "dictionary_matches": [],
            },
            {"json": "a.json", "csv": "a.csv", "xlsx": "a.xlsx"},
        )
        self.assertIn("agentic workflow", rendered)
        self.assertIn("An agentic workflow runs here.", rendered)

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

    def test_result_failed_shows_clear_guidance(self):
        rendered = result_html(
            {
                "analysis_status": "failed",
                "document": "corrupt.pdf",
                "model": "gpt-4o",
                "processing_warnings": ["429 Quota Exceeded: Daily quota reached."],
            },
            {"json": "", "csv": "", "xlsx": ""},
        )
        self.assertIn("Analiz Tamamlanamadı", rendered)
        self.assertIn("429 Quota Exceeded", rendered)
        self.assertIn("API Ayarlarını Kontrol Et", rendered)


if __name__ == "__main__":
    unittest.main()

