import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from terim_etmeni.dictionary import DictionaryIndex
from terim_etmeni.models import ExtractedTerm, PageText
from terim_etmeni.pipeline import analyze_pdf
from terim_etmeni.reporting import format_terminal_report, write_reports


class FakeProvider:
    def extract(self, text):
        return [
            ExtractedTerm("machine learning"),
            ExtractedTerm("agentic workflow"),
            ExtractedTerm("client server"),
            ExtractedTerm("task"),
        ]


class CombinedProvider:
    def extract(self, text):
        return [
            ExtractedTerm("Natural Language Processing and Knowledge Base System"),
            ExtractedTerm("travel"),
            ExtractedTerm("automotive industry"),
            ExtractedTerm("Google Translate"),
            ExtractedTerm("travel & transport"),
        ]


class PipelineTests(unittest.TestCase):
    def test_pipeline_classifies_and_writes_reports(self):
        pages = [
            PageText(
                1,
                "Machine learning supports an agentic workflow, a client server design, and a task.",
            )
        ]
        dictionary = DictionaryIndex(
            [
                {"en": "machine learning", "tr": "makine öğrenmesi"},
                {"en": "client-server", "tr": "istemci-sunucu"},
            ],
            metadata={"version": "test"},
        )

        with tempfile.TemporaryDirectory() as directory:
            temp_path = Path(directory)
            with patch("terim_etmeni.pipeline.read_pdf", return_value=pages):
                result = analyze_pdf(
                    temp_path / "sample.pdf", dictionary, FakeProvider(), "fake-model"
                )
            self.assertEqual(
                result["counts"],
                {
                    "dictionary_matches": 1,
                    "possible_matches": 1,
                    "missing_terms": 1,
                    "rejected_candidates": 1,
                },
            )
            self.assertEqual(result["missing_terms"][0]["term"], "agentic workflow")

            json_path, csv_path = write_reports(result, temp_path / "reports")
            saved = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(saved["dictionary_version"], "test")
            csv_text = csv_path.read_text(encoding="utf-8-sig")
            self.assertIn("agentic workflow", csv_text)
            self.assertIn("machine learning", csv_text)
            self.assertIn("client server", csv_text)
            self.assertIn("OLASI EŞLEŞME", csv_text)
            self.assertIn("ELENEN ADAY", csv_text)
            terminal = format_terminal_report(result)
            self.assertIn("SÖZLÜKTE BULUNANLAR", terminal)
            self.assertIn("SÖZLÜKTE OLMAYANLAR", terminal)

    def test_pipeline_recovers_dictionary_terms_and_splits_combined_candidate(self):
        pages = [
            PageText(
                1,
                "Natural Language Processing and Knowledge Base System are discussed. "
                "An intelligent agent applies heuristic search in the automotive industry and travel sector. "
                "Google Translate is listed under travel & transport.",
            )
        ]
        dictionary = DictionaryIndex(
            [
                {"en": "natural language processing", "tr": "doğal dil işleme"},
                {"en": "intelligent agent", "tr": "akıllı etmen"},
                {"en": "heuristic search", "tr": "buluşsal arama"},
            ]
        )
        with patch("terim_etmeni.pipeline.read_pdf", return_value=pages):
            result = analyze_pdf(
                Path("combined.pdf"), dictionary, CombinedProvider(), "fake-model"
            )
        found = {item["term"].casefold() for item in result["dictionary_matches"]}
        missing = {item["term"].casefold() for item in result["missing_terms"]}
        rejected = {item["term"].casefold() for item in result["rejected_candidates"]}
        self.assertTrue(
            {"natural language processing", "intelligent agent", "heuristic search"}
            <= found
        )
        self.assertIn("knowledge base system", missing)
        self.assertEqual(
            {"travel", "automotive industry", "google translate", "travel & transport"},
            rejected,
        )


if __name__ == "__main__":
    unittest.main()
