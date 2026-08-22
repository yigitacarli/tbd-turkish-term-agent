"""ADR-042: eksik terimlerde kavram bazında birleştirme testleri.

Kapsam: tire/boşluk yazım farkları ve belge içinde tanımlı kısaltma ↔
açılım çiftleri tek eksik terim maddesinde birleşir; hiçbir yüzey biçimi
gizlenmez ('variants' alanı). Farklı kavramlar birleştirilmez.
"""
import unittest
from pathlib import Path
from unittest.mock import patch

from terim_etmeni.models import ExtractedTerm, PageText

from terim_etmeni.pipeline import TermDictionary, analyze_pdf
from terim_etmeni.term_extraction import document_acronyms


class FakeExtractor:
    def __init__(self, terms):
        self.terms = [ExtractedTerm(term) for term in terms]

    def extract_terms(self, text):
        return list(self.terms)


class DocumentAcronymsTests(unittest.TestCase):
    def test_collects_initial_matching_pairs(self):
        pages = [
            PageText(
                1,
                "Masked language modeling (MLM) is a pre-training task. "
                "Reinforcement learning from human feedback (RLHF) aligns models.",
            )
        ]
        pairs = document_acronyms(pages)
        self.assertEqual(pairs.get("mlm"), "masked language modeling")
        self.assertEqual(
            pairs.get("rlhf"), "reinforcement learning from human feedback"
        )

    def test_rejects_phrase_without_matching_initials(self):
        pages = [PageText(1, "Some random unrelated words (NASA) appear here.")]
        self.assertEqual(document_acronyms(pages), {})

    def test_skips_stopwords_in_expansion(self):
        pages = [PageText(1, "Proof of Work (PoW) secures the chain.")]
        pairs = document_acronyms(pages)
        self.assertEqual(pairs.get("pow"), "proof of work")


class VariantMergingTests(unittest.TestCase):
    def pages(self):
        return [
            PageText(
                1,
                "Over-fitting harms models. Severe overfitting hurts too. "
                "The masked language model (MLM) masks tokens and an MLM "
                "learns representations. Attention heads attend to tokens.",
            )
        ]

    def _run(self, terms, pages=None):
        dictionary = TermDictionary([], metadata={"version": "test"})
        extractor = FakeExtractor(terms)
        with patch(
            "terim_etmeni.pipeline.read_pdf",
            return_value=pages if pages is not None else self.pages(),
        ):
            return analyze_pdf(Path("sample.pdf"), dictionary, extractor, "test-model")

    def test_hyphen_and_spacing_variants_merge(self):
        result = self._run(["over-fitting", "overfitting"])
        missing = result["missing_terms"]
        self.assertEqual(len(missing), 1)
        entry = missing[0]
        names = {entry["term"]} | set(entry.get("variants") or [])
        self.assertEqual(names, {"over-fitting", "overfitting"})
        # İki yüzey biçimi de metinde birer kez geçiyor; sayılar harmanlanır.
        self.assertEqual(entry["occurrence_count"], 2)

    def test_document_defined_acronym_merges_with_expansion(self):
        result = self._run(["masked language model", "MLM"])
        missing = result["missing_terms"]
        self.assertEqual(len(missing), 1)
        entry = missing[0]
        # Açılım biçimi görünür ad olur; kısaltma gizlenmez.
        self.assertEqual(entry["term"], "masked language model")
        self.assertIn("MLM", entry.get("variants") or [])

    def test_distinct_concepts_stay_separate(self):
        result = self._run(["attention head", "attention"])
        terms = {item["term"] for item in result["missing_terms"]}
        self.assertEqual(terms, {"attention head", "attention"})

    def test_undefined_pair_does_not_merge(self):
        pages = [
            PageText(
                1,
                "A context window limits tokens. The model uses tokens well "
                "and tokens again.",
            )
        ]
        result = self._run(["context window", "tokens"], pages=pages)
        terms = sorted(item["term"] for item in result["missing_terms"])
        self.assertEqual(terms, ["context window", "tokens"])

    def test_merge_keeps_combined_pages_and_counts(self):
        pages = [
            PageText(1, "An over-fitting model drifts."),
            PageText(2, "Overfitting appears again on this page."),
        ]

        class PageExtractor(FakeExtractor):
            pass

        dictionary = TermDictionary([], metadata={"version": "test"})
        extractor = FakeExtractor(["over-fitting", "overfitting"])
        with patch(
            "terim_etmeni.pipeline.read_pdf", return_value=pages
        ):
            result = analyze_pdf(
                Path("sample.pdf"), dictionary, extractor, "test-model"
            )
        missing = result["missing_terms"]
        self.assertEqual(len(missing), 1)
        self.assertEqual(missing[0]["occurrence_count"], 2)
        self.assertEqual(missing[0]["pages"], [1, 2])


if __name__ == "__main__":
    unittest.main()
