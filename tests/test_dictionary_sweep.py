"""ADR-045: deterministik sözlük süpürmesi testleri.

Modelin önermediği kayıtlı çok sözcüklü başlıklar belge metninden
bulunup sözlük eşleşmelerine eklenir; halüsinasyon riski yoktur.
"""
import unittest
from pathlib import Path
from unittest.mock import patch

from terim_etmeni.models import ExtractedTerm, PageText

from terim_etmeni.pipeline import TermDictionary, analyze_pdf


class FakeExtractor:
    def __init__(self, terms):
        self.terms = [ExtractedTerm(term) for term in terms]

    def extract_terms(self, text):
        return list(self.terms)


class SweepPhraseTests(unittest.TestCase):
    def pages(self):
        return [
            PageText(
                1,
                "The system enforces access control on every request. "
                "Access control lists are evaluated first.",
            )
        ]

    def _run(self, terms):
        dictionary = TermDictionary(
            [{"en": "access control", "tr": "erişim denetimi"}],
            metadata={"version": "test"},
        )
        extractor = FakeExtractor(terms)
        with patch(
            "terim_etmeni.pipeline.read_pdf",
            return_value=self.pages(),
        ):
            return analyze_pdf(
                Path("sample.pdf"), dictionary, extractor, "test-model"
            )

    def test_sweep_finds_term_model_missed(self):
        result = self._run([])  # model hiç aday döndürmedi
        found = {item["term"] for item in result["dictionary_matches"]}
        self.assertEqual(found, {"access control"})
        entry = result["dictionary_matches"][0]
        self.assertEqual(entry["match_source"], "dictionary_sweep")
        self.assertEqual(entry["occurrence_count"], 2)
        self.assertEqual(entry["translations"], ["erişim denetimi"])

    def test_no_duplicate_when_model_reported_term(self):
        result = self._run(["access control"])
        matches = [
            item for item in result["dictionary_matches"]
            if item["term"] == "access control"
        ]
        self.assertEqual(len(matches), 1)

    def test_sweep_does_not_invent_missing_terms(self):
        # Sözlükte olmayan ifade süpürmeyle üretilmez (halüsinasyon yok).
        dictionary = TermDictionary(
            [{"en": "hash function", "tr": "özet işlevi"}],
            metadata={"version": "test"},
        )
        extractor = FakeExtractor([])
        with patch(
            "terim_etmeni.pipeline.read_pdf",
            return_value=self.pages(),
        ):
            result = analyze_pdf(
                Path("sample.pdf"), dictionary, extractor, "test-model"
            )
        self.assertEqual(result["dictionary_matches"], [])
        self.assertEqual(result["missing_terms"], [])


if __name__ == "__main__":
    unittest.main()
