import tempfile
import unittest
from pathlib import Path

from terim_etmeni_v2.config import Settings, _positive_int_env
from terim_etmeni_v2.service import AnalysisBusyError, AnalysisService


class ServiceConcurrencyTests(unittest.TestCase):
    def settings(self, root: Path, limit: int = 1) -> Settings:
        return Settings(
            bootstrap_dictionary=root / "dictionary.json",
            bootstrap_abbreviations=root / "abbreviations.json",
            dictionary_state_dir=root / "state",
            output_dir=root / "output",
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
            finally:
                service._analysis_slots.release()

    def test_non_positive_or_invalid_environment_limit_uses_safe_default(self):
        from unittest.mock import patch

        for value in ("0", "-2", "invalid"):
            with self.subTest(value=value), patch.dict(
                "os.environ", {"TEST_ANALYSIS_LIMIT": value}
            ):
                self.assertEqual(_positive_int_env("TEST_ANALYSIS_LIMIT", 1), 1)


if __name__ == "__main__":
    unittest.main()
