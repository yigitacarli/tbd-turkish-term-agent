import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from terim_etmeni.config import Settings, _positive_int_env
from terim_etmeni.service import AnalysisBusyError, AnalysisService


class ServiceConcurrencyTests(unittest.TestCase):
    def settings(self, root: Path, limit: int = 1) -> Settings:
        return Settings(
            bootstrap_dictionary=root / "dictionary.json",
            bootstrap_abbreviations=root / "abbreviations.json",
            dictionary_state_dir=root / "state",
            output_dir=root / "output",
            provider_config_file=root / "provider.json",
            max_concurrent_analyses=limit,
        )

    def write_sources(self, root: Path) -> None:
        (root / "dictionary.json").write_text(
            '{"metadata":{"version":"test"},"terms":[{"en":"system","tr":"dizge"}]}',
            encoding="utf-8",
        )
        (root / "abbreviations.json").write_text(
            '{"metadata":{"version":"test"},"abbreviations":[{"abbreviation":"AI","en":"artificial intelligence","tr":"yapay zeka"}]}',
            encoding="utf-8",
        )

    def test_busy_service_rejects_a_second_analysis_without_calling_ollama(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write_sources(root)
            service = AnalysisService(self.settings(root))
            self.assertTrue(service._analysis_slots.acquire(blocking=False))
            try:
                with self.assertRaisesRegex(AnalysisBusyError, "kapasitesi dolu"):
                    service.analyze_upload("article.pdf", b"%PDF-test", "qwen-test")
                with self.assertRaisesRegex(AnalysisBusyError, "kapasitesi dolu"):
                    service.analyze_path(root / "dictionary.json", "qwen-test")
            finally:
                service._analysis_slots.release()

    def test_tempfile_is_cleaned_up_on_successful_and_failed_analysis(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write_sources(root)
            service = AnalysisService(self.settings(root))

            # 1. Successful run: mock _analyze and capture the created tempfile path
            captured_paths = []
            def mock_analyze_success(pdf_path, model, display_name):
                captured_paths.append(pdf_path)
                self.assertTrue(pdf_path.is_file(), "Tempfile should exist during _analyze")
                return ({"analysis_status": "complete", "document": display_name, "model": model}, Path("a.json"), Path("a.csv"), Path("a.xlsx"))

            service._analyze = mock_analyze_success
            res, _, _, _ = service.analyze_upload("paper.pdf", b"%PDF-1.4 content", "test-model")
            self.assertEqual(res["analysis_status"], "complete")
            self.assertEqual(len(captured_paths), 1)
            self.assertFalse(captured_paths[0].exists(), "Tempfile should be deleted after analysis")
            # Verify slot is free
            self.assertTrue(service._analysis_slots.acquire(blocking=False))
            service._analysis_slots.release()

            # 2. Failed run: _analyze raises RuntimeError -> tempfile still unlinked and slot released
            failed_captured_paths = []
            def mock_analyze_fail(pdf_path, model, display_name):
                failed_captured_paths.append(pdf_path)
                self.assertTrue(pdf_path.is_file())
                raise RuntimeError("Ollama connection broke during inference")

            service._analyze = mock_analyze_fail
            with self.assertRaisesRegex(RuntimeError, "Ollama connection broke"):
                service.analyze_upload("paper.pdf", b"%PDF-1.4 content", "test-model")

            self.assertEqual(len(failed_captured_paths), 1)
            self.assertFalse(failed_captured_paths[0].exists(), "Tempfile must be cleaned up on failure")
            # Verify slot is released despite failure
            self.assertTrue(service._analysis_slots.acquire(blocking=False))
            service._analysis_slots.release()

    def test_non_positive_or_invalid_environment_limit_uses_safe_default(self):
        for value in ("0", "-2", "invalid"):
            with self.subTest(value=value), patch.dict(
                "os.environ", {"TEST_ANALYSIS_LIMIT": value}
            ):
                self.assertEqual(_positive_int_env("TEST_ANALYSIS_LIMIT", 1), 1)


if __name__ == "__main__":
    unittest.main()

