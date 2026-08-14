import unittest

from terim_etmeni.models import ExtractedTerm, PageText, TextChunk

from terim_etmeni.term_extraction import (
    extract_terms_from_chunks,
    find_context,
    normalize_term,
    term_occurrences,
)


class NormalizationTests(unittest.TestCase):
    def test_lowercase_trim_and_collapse_whitespace(self):
        self.assertEqual(normalize_term("  Agentic   Workflow "), "agentic workflow")

    def test_unicode_normalization_and_dashes_become_spaces(self):
        self.assertEqual(normalize_term("client‐server"), "client server")
        self.assertEqual(normalize_term("state-of-the-art"), "state of the art")

    def test_strips_leading_and_trailing_punctuation(self):
        self.assertEqual(normalize_term("(machine learning)"), "machine learning")
        self.assertEqual(normalize_term('"packet switching",'), "packet switching")

    def test_does_not_merge_different_concepts(self):
        self.assertNotEqual(
            normalize_term("large language model"),
            normalize_term("language model"),
        )


class ExtractionTests(unittest.TestCase):
    def test_prompt_limits_each_chunk_to_conservative_dictionary_candidates(self):
        from terim_etmeni.term_extraction import SYSTEM_PROMPT, USER_TASK

        self.assertIn("at most 8 terms", SYSTEM_PROMPT)
        self.assertIn("dictionary headword", SYSTEM_PROMPT)
        self.assertIn("no more than 8 terms", USER_TASK)

    def test_deduplicates_and_drops_invalid_candidates(self):
        class FakeExtractor:
            def extract_terms(self, text):
                return [
                    ExtractedTerm("Machine Learning"),
                    ExtractedTerm("machine-learning"),
                    ExtractedTerm("machine learning"),
                    ExtractedTerm("a"),
                    ExtractedTerm("http://example.com"),
                ]

        chunks = [TextChunk(1, 0, "text")]
        results = extract_terms_from_chunks(chunks, FakeExtractor())
        self.assertEqual([item.term for item in results], ["Machine Learning"])

    def test_failed_chunk_is_recorded_without_discarding_other_chunks(self):
        class PartlyFailingExtractor:
            def extract_terms(self, text):
                if "second" in text:
                    raise RuntimeError("malformed")
                return [ExtractedTerm("fault tolerance")]

        chunks = [TextChunk(1, 0, "first"), TextChunk(2, 1, "second")]
        warnings = []
        results = extract_terms_from_chunks(chunks, PartlyFailingExtractor(), warnings)
        self.assertEqual([item.term for item in results], ["fault tolerance"])
        self.assertEqual(len(warnings), 1)


class EvidenceTests(unittest.TestCase):
    def test_occurrences_and_context_are_found(self):
        pages = [
            PageText(1, "A distributed ledger records transactions."),
            PageText(2, "The distributed ledger is replicated."),
        ]
        count, page_set = term_occurrences("distributed ledger", pages)
        self.assertEqual(count, 2)
        self.assertEqual(page_set, {1, 2})
        context = find_context("distributed ledger", pages)
        self.assertIn("distributed ledger", context)


if __name__ == "__main__":
    unittest.main()
