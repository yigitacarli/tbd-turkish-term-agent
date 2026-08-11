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


class MetadataProvider:
    def extract(self, text):
        return [
            ExtractedTerm("Karen Kent"),
            ExtractedTerm("Intel Corporation"),
            ExtractedTerm("Author ORCID iDs"),
            ExtractedTerm("cloud security capabilities"),
            ExtractedTerm("platform integrity"),
            ExtractedTerm("5G systems"),
            ExtractedTerm("technical details"),
        ]


class ValidatingProvider:
    def extract(self, text):
        return [
            ExtractedTerm("multilayer perceptron"),
            ExtractedTerm("small model"),
            ExtractedTerm("DNS"),
        ]

    def validate_terms(self, terms):
        return ["multilayer perceptron"]


class RejectingProvider:
    def extract(self, text):
        return []

    def validate_terms(self, terms):
        return []


class FailingProvider:
    def extract(self, text):
        raise RuntimeError("invalid model response")


class PipelineTests(unittest.TestCase):
    def test_pipeline_marks_all_failed_model_chunks_as_failed_analysis(self):
        pages = [PageText(1, "A machine learning system is described.")]
        dictionary = DictionaryIndex(
            [{"en": "machine learning", "tr": "makine öğrenmesi"}]
        )
        with patch("terim_etmeni.pipeline.read_pdf", return_value=pages):
            result = analyze_pdf(
                Path("failed.pdf"), dictionary, FailingProvider(), "broken-model"
            )
        self.assertEqual(result["analysis_status"], "failed")
        self.assertEqual(result["processed_chunk_count"], 0)
        self.assertEqual(result["failed_chunk_count"], 1)

    def test_pipeline_retains_model_missed_deterministic_candidates_for_humans(self):
        pages = [
            PageText(
                1,
                "The Domain Name System (DNS) supports an adaptive signal router. DNS is required.",
            )
        ]
        with patch("terim_etmeni.pipeline.read_pdf", return_value=pages):
            result = analyze_pdf(
                Path("recovery.pdf"),
                DictionaryIndex([]),
                RejectingProvider(),
                "fake-model",
            )
        missing = {item["term"].casefold(): item for item in result["missing_terms"]}
        self.assertEqual(
            set(missing), {"adaptive signal router", "domain name system", "dns"}
        )
        self.assertEqual(missing["adaptive signal router"]["review_priority"], "low")
        self.assertEqual(
            missing["adaptive signal router"]["model_review"],
            "rejected_but_retained_for_human_review",
        )

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
                    "dictionary_matches": 2,
                    "possible_matches": 0,
                    "missing_terms": 2,
                    "rejected_candidates": 0,
                },
            )
            self.assertEqual(
                {item["term"] for item in result["missing_terms"]},
                {"agentic workflow", "task"},
            )
            single_word = next(
                item for item in result["missing_terms"] if item["term"] == "task"
            )
            self.assertEqual(single_word["review_priority"], "low")
            normalized = next(
                item for item in result["dictionary_matches"]
                if item["term"] == "client server"
            )
            self.assertEqual(normalized["match_type"], "normalized_variant")

            json_path, csv_path = write_reports(result, temp_path / "reports")
            saved = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(saved["dictionary_version"], "test")
            csv_text = csv_path.read_text(encoding="utf-8-sig")
            self.assertIn("agentic workflow", csv_text)
            self.assertIn("machine learning", csv_text)
            self.assertIn("client server", csv_text)
            self.assertIn("İnceleme Durumu", csv_text)
            self.assertIn("Önerilen İşlem", csv_text)
            self.assertIn("İnceleme gerekli", csv_text)
            self.assertIn("Sözlükte bulundu", csv_text)
            self.assertIn("Tek sözcüklü adayı doğrula", csv_text)
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
        self.assertEqual({"knowledge base system", "travel"}, missing)
        self.assertEqual(
            {"automotive industry", "google translate", "travel & transport"},
            rejected,
        )

    def test_pipeline_rejects_metadata_and_maps_generic_composites(self):
        pages = [
            PageText(
                1,
                "Karen Kent works at Intel Corporation. Author ORCID iDs are listed. "
                "Cloud security capabilities, platform integrity, 5G systems, and technical details are discussed.",
            )
        ]
        dictionary = DictionaryIndex(
            [{"en": "cloud security", "tr": "bulut güvenliği"}]
        )
        with patch("terim_etmeni.pipeline.read_pdf", return_value=pages):
            result = analyze_pdf(
                Path("metadata.pdf"), dictionary, MetadataProvider(), "fake-model"
            )
        found = {item["term"] for item in result["dictionary_matches"]}
        possible = {item["term"] for item in result["possible_matches"]}
        missing = {item["term"] for item in result["missing_terms"]}
        rejected = {item["term"] for item in result["rejected_candidates"]}
        self.assertIn("cloud security", found)
        self.assertNotIn("cloud security capabilities", possible)
        self.assertEqual(missing, {"5G", "platform integrity"})
        self.assertTrue(
            {"Karen Kent", "Intel Corporation", "Author ORCID iDs", "technical details"}
            <= rejected
        )

    def test_pipeline_normalizes_acronym_and_rejects_named_items(self):
        pages = [
            PageText(
                1,
                "Knowledge-Based Systems(KBS) use CAPTCHA technology. "
                "AEG bot and Cloud Volumes are examples. Erica is a named robot.",
            )
        ]
        dictionary = DictionaryIndex(
            [
                {"en": "knowledge-based system", "tr": "özbilgi tabanlı dizge"},
                {"en": "captcha", "tr": "captcha"},
            ]
        )

        class NamedProvider:
            def extract(self, text):
                return [
                    ExtractedTerm("Knowledge-Based Systems(KBS)"),
                    ExtractedTerm("CAPTCHA technology"),
                    ExtractedTerm("AEG bot"),
                    ExtractedTerm("Cloud Volumes"),
                    ExtractedTerm("Erica"),
                ]

        with patch("terim_etmeni.pipeline.read_pdf", return_value=pages):
            result = analyze_pdf(
                Path("named.pdf"), dictionary, NamedProvider(), "fake-model"
            )

        self.assertEqual(
            {"KBS"},
            {item["term"] for item in result["possible_matches"]},
        )
        self.assertIn(
            "Knowledge-Based Systems",
            {item["term"] for item in result["dictionary_matches"]},
        )
        self.assertEqual([], result["missing_terms"])
        self.assertEqual(
            {"AEG bot", "Cloud Volumes", "Erica"},
            {item["term"] for item in result["rejected_candidates"]},
        )

    def test_pipeline_uses_optional_local_technical_review(self):
        pages = [
            PageText(1, "A multilayer perceptron is compared with a small model over DNS.")
        ]
        with patch("terim_etmeni.pipeline.read_pdf", return_value=pages):
            result = analyze_pdf(
                Path("review.pdf"), DictionaryIndex([]), ValidatingProvider(), "fake-model"
            )
        self.assertEqual(
            [item["term"] for item in result["missing_terms"]],
            ["DNS", "multilayer perceptron"],
        )
        dns = next(item for item in result["missing_terms"] if item["term"] == "DNS")
        self.assertEqual(dns["review_priority"], "low")
        self.assertEqual(
            dns["model_review"], "rejected_but_retained_for_human_review"
        )
        self.assertEqual(result["rejected_candidates"][0]["reason"], "non_technical_contextual_phrase")
        self.assertEqual(result["technical_review"]["accepted_count"], 1)
        self.assertEqual(
            result["technical_review"]["candidate_terms"],
            ["multilayer perceptron", "small model", "DNS"],
        )
        self.assertEqual(result["technical_review"]["accepted_terms"], ["multilayer perceptron"])

    def test_pipeline_preserves_single_word_technical_terms(self):
        class TechTermProvider:
            def extract(self, text):
                return [
                    ExtractedTerm("Transformer"),
                    ExtractedTerm("Softmax"),
                    ExtractedTerm("Azure"),
                    ExtractedTerm("Sophia"),
                ]

        pages = [
            PageText(1, "Transformer uses Softmax and runs on Azure. Sophia is an author.")
        ]
        with patch("terim_etmeni.pipeline.read_pdf", return_value=pages):
            result = analyze_pdf(
                Path("tech.pdf"), DictionaryIndex([]), TechTermProvider(), "fake-model"
            )
        missing_terms = {item["term"] for item in result["missing_terms"]}
        rejected_reasons = {item["term"]: item.get("reason") for item in result["rejected_candidates"]}

        self.assertIn("Transformer", missing_terms)
        self.assertIn("Softmax", missing_terms)
        self.assertIn("Azure", missing_terms)
        self.assertEqual(rejected_reasons.get("Sophia"), "person_name")


if __name__ == "__main__":
    unittest.main()
