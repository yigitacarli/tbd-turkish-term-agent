"""ADR-044: eksik terimlerde öncelik puanı ve sıralama testleri.

Puan yalnızca sunum sırasını belirler; hiçbir aday elenmez.
"""
import unittest
from pathlib import Path
from unittest.mock import patch

from terim_etmeni.models import ExtractedTerm, PageText

from terim_etmeni.pipeline import TermDictionary, _priority_score, analyze_pdf


class FakeExtractor:
    def __init__(self, terms):
        self.terms = [ExtractedTerm(term) for term in terms]

    def extract_terms(self, text):
        return list(self.terms)


class PriorityScoreTests(unittest.TestCase):
    def test_multi_word_scores_higher_than_single(self):
        self.assertGreater(
            _priority_score("attention head", 1), _priority_score("dropout", 1)
        )

    def test_frequency_raises_score(self):
        self.assertEqual(_priority_score("attention head", 1), 2)
        self.assertEqual(_priority_score("attention head", 2), 3)
        self.assertEqual(_priority_score("attention head", 5), 4)

    def test_single_word_never_excluded_only_lowered(self):
        # Tek sözcük kaç kez geçerse geçsin listede kalır, puanı düşük olur.
        self.assertLessEqual(_priority_score("model", 9), 1)


class PriorityOrderingTests(unittest.TestCase):
    PAGES = [
        PageText(
            1,
            "A context window limits tokens. The zebra concept is rare here. "
            "Attention heads attend to tokens and attention heads attend well.",
        )
    ]

    def _run(self, terms):
        dictionary = TermDictionary([], metadata={"version": "test"})
        extractor = FakeExtractor(terms)
        with patch(
            "terim_etmeni.pipeline.read_pdf",
            return_value=[PageText(*p) if isinstance(p, tuple) else p for p in self.PAGES],
        ):
            return analyze_pdf(
                Path("sample.pdf"), dictionary, extractor, "test-model"
            )

    def test_ordering_puts_multiword_first(self):
        result = self._run(["zebra concept", "context window", "attention heads"])
        terms = [item["term"] for item in result["missing_terms"]]
        # 'attention heads' iki kez geçiyor (puan 3) ve başa gelir;
        # puanı eşit olanlar alfabetik dizilir.
        self.assertEqual(terms[0], "attention heads")
        self.assertEqual(terms[1:], ["context window", "zebra concept"])

    def test_single_word_lands_low_but_present(self):
        result = self._run(["tokens"])
        missing = result["missing_terms"]
        self.assertEqual(len(missing), 1)
        entry = missing[0]
        # Tek sözcük, iki geçiş: puan -1 + 1 = 0 -> 'low'. Yasak değil,
        # yalnızca listenin sonuna düşer.
        self.assertEqual(entry["review_priority"], "low")
        self.assertEqual(entry["priority_score"], 0)


if __name__ == "__main__":
    unittest.main()
