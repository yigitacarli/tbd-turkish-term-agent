import unittest
from pathlib import Path
from unittest.mock import patch

from terim_etmeni.models import ExtractedTerm, PageText

from terim_etmeni.abbreviation_index import AbbreviationIndex
from terim_etmeni.pipeline import TermDictionary, analyze_pdf


class FakeExtractor:
    def __init__(self, terms):
        self.terms = [ExtractedTerm(term) for term in terms]

    def extract_terms(self, text):
        return list(self.terms)


class DictionaryTests(unittest.TestCase):
    def test_exact_normalized_match_and_variants(self):
        dictionary = TermDictionary(
            [
                {"en": "Machine Learning", "tr": "makine öğrenmesi"},
                {"en": "client-server", "tr": "istemci-sunucu"},
                {"en": "transaction", "tr": "işlem"},
            ]
        )
        found, entries, match_type = dictionary.lookup("machine-learning")
        self.assertTrue(found)
        self.assertEqual(match_type, "exact")
        self.assertEqual(entries[0]["tr"], "makine öğrenmesi")

        found, _, match_type = dictionary.lookup("client server")
        self.assertTrue(found)
        self.assertEqual(match_type, "exact")

        # Çoğul varyant testi: transactions -> transaction (işlem)
        found, entries, match_type = dictionary.lookup("transactions")
        self.assertTrue(found)
        self.assertEqual(match_type, "singular_variant")
        self.assertEqual(entries[0]["tr"], "işlem")

        found, _, match_type = dictionary.lookup("language model")
        self.assertFalse(found)
        self.assertEqual(match_type, "missing")


class PipelineTests(unittest.TestCase):
    def pages(self):
        return [
            PageText(
                1,
                "Machine learning enables an agentic workflow. "
                "The Domain Name System (DNS) routes traffic. "
                "A context window limits tokens. "
                "Multiple agentic workflows are possible.",
            )
        ]

    def test_classifies_found_missing_and_abbreviation_matches(self):
        dictionary = TermDictionary(
            [{"en": "machine learning", "tr": "makine öğrenmesi"}],
            metadata={"version": "test"},
        )
        abbreviations = AbbreviationIndex(
            [
                {
                    "abbreviation": "DNS",
                    "expansion": "Domain Name System",
                    "turkish": "alan adı sistemi",
                }
            ]
        )
        extractor = FakeExtractor(
            ["machine learning", "agentic workflow", "agentic workflows", "DNS", "context window"]
        )
        with patch(
            "terim_etmeni.pipeline.read_pdf", return_value=self.pages()
        ):
            result = analyze_pdf(
                Path("sample.pdf"),
                dictionary,
                extractor,
                "test-model",
                abbreviations=abbreviations,
            )

        self.assertEqual(result["analysis_status"], "complete")
        found = {item["term"] for item in result["dictionary_matches"]}
        self.assertEqual(found, {"machine learning"})
        self.assertTrue(
            result["dictionary_matches"][0]["found_in_dictionary"]
        )
        missing = {item["term"] for item in result["missing_terms"]}
        # 'agentic workflow' ve 'agentic workflows' tekilleştirilmeli
        self.assertEqual(missing, {"agentic workflow", "context window"})
        self.assertFalse(
            result["missing_terms"][0]["found_in_dictionary"]
        )
        self.assertTrue(
            result["missing_terms"][0]["context"].casefold().startswith("machine")
        )
        possible = result["possible_matches"]
        self.assertEqual([item["term"] for item in possible], ["DNS"])
        self.assertEqual(possible[0]["match_source"], "tbd_abbreviations")
        self.assertEqual(result["counts"]["missing_terms"], 2)

    def test_hallucinated_terms_are_not_reported(self):
        dictionary = TermDictionary([])
        extractor = FakeExtractor(["invented technology"])
        with patch(
            "terim_etmeni.pipeline.read_pdf", return_value=self.pages()
        ):
            result = analyze_pdf(
                Path("sample.pdf"), dictionary, extractor, "test-model"
            )
        self.assertEqual(result["missing_terms"], [])
        self.assertEqual(result["candidate_count"], 1)
        # Elenen aday sessizce kaybolmamalı, izlenebilir olmalı
        self.assertEqual(result["counts"]["rejected_candidates"], 1)
        self.assertEqual(
            result["rejected_candidates"],
            [{"term": "invented technology", "reason": "not_found_in_text"}],
        )

    def test_candidate_is_kept_when_only_its_plural_occurs_in_text(self):
        dictionary = TermDictionary([], metadata={"version": "test"})
        pages = [PageText(1, "Modern block ciphers resist known attacks.")]
        extractor = FakeExtractor(["block cipher"])
        with patch("terim_etmeni.pipeline.read_pdf", return_value=pages):
            result = analyze_pdf(
                Path("sample.pdf"), dictionary, extractor, "test-model"
            )
        self.assertEqual(result["counts"]["rejected_candidates"], 0)
        missing = result["missing_terms"]
        self.assertEqual([item["term"] for item in missing], ["block cipher"])
        # Hangi yüzey biçimi üzerinden sayıldığı denetlenebilir olmalı
        self.assertEqual(missing[0]["matched_form"], "block ciphers")
        self.assertEqual(missing[0]["occurrence_count"], 1)
        self.assertIn("block ciphers", missing[0]["context"])

    def test_empty_model_output_is_flagged_instead_of_reading_as_zero_missing(self):
        dictionary = TermDictionary([], metadata={"version": "test"})
        extractor = FakeExtractor([])
        with patch("terim_etmeni.pipeline.read_pdf", return_value=self.pages()):
            result = analyze_pdf(
                Path("sample.pdf"), dictionary, extractor, "test-model"
            )
        # Analiz gerçekten tamamlandı; durum kodu bozulmamalı
        self.assertEqual(result["analysis_status"], "complete")
        self.assertEqual(result["candidate_count"], 0)
        self.assertEqual(len(result["processing_warnings"]), 1)
        self.assertIn("hiç terim adayı döndürmedi", result["processing_warnings"][0])

    def test_singular_and_plural_dictionary_matches_are_merged(self):
        dictionary = TermDictionary(
            [{"en": "context window", "tr": "bağlam penceresi"}],
            metadata={"version": "test"},
        )
        pages = [
            PageText(1, "A context window limits tokens."),
            PageText(2, "Larger context windows cost more."),
        ]
        extractor = FakeExtractor(["context window", "context windows"])
        with patch("terim_etmeni.pipeline.read_pdf", return_value=pages):
            result = analyze_pdf(
                Path("sample.pdf"), dictionary, extractor, "test-model"
            )
        self.assertEqual(result["counts"]["dictionary_matches"], 1)
        match = result["dictionary_matches"][0]
        self.assertEqual(match["term"], "context window")
        self.assertEqual(match["pages"], [1, 2])
        self.assertEqual(match["occurrence_count"], 2)

    def test_failed_extraction_is_not_presented_as_zero_missing(self):
        class FailingExtractor:
            def extract_terms(self, text):
                raise RuntimeError("model unavailable")

        dictionary = TermDictionary([])
        with patch(
            "terim_etmeni.pipeline.read_pdf", return_value=self.pages()
        ):
            result = analyze_pdf(
                Path("sample.pdf"), dictionary, FailingExtractor(), "test-model"
            )
        self.assertEqual(result["analysis_status"], "failed")
        self.assertEqual(result["processed_chunk_count"], 0)
        self.assertEqual(result["failed_chunk_count"], 1)


if __name__ == "__main__":
    unittest.main()
