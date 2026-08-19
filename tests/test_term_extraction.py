import unittest

from terim_etmeni.models import ExtractedTerm, PageText, TextChunk

from terim_etmeni.term_extraction import (
    extract_terms_from_chunks,
    find_context,
    locate_term,
    normalize_term,
    surface_variants,
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
        from terim_etmeni.term_extraction import (
            MAX_TERMS_PER_CHUNK,
            SYSTEM_PROMPT,
            USER_TASK,
        )

        # Tavanın kendisi ADR-040 ile belirlenir; burada istemin tavanı taşıdığı sınanır.
        self.assertIn("at most {} terms".format(MAX_TERMS_PER_CHUNK), SYSTEM_PROMPT)
        self.assertIn("dictionary headword", SYSTEM_PROMPT)
        self.assertIn("Hypothetical scenario participants", SYSTEM_PROMPT)
        self.assertIn("Ordinary single English words", SYSTEM_PROMPT)
        self.assertIn("Narrative descriptions", SYSTEM_PROMPT)
        self.assertIn("no more than {} terms".format(MAX_TERMS_PER_CHUNK), USER_TASK)
        self.assertIn("Hypothetical scenario actors", USER_TASK)

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


class ChunkCapTests(unittest.TestCase):
    def test_prompts_carry_the_configured_candidate_cap(self):
        from terim_etmeni.term_extraction import (
            MAX_TERMS_PER_CHUNK,
            SYSTEM_PROMPT,
            USER_TASK,
        )

        self.assertEqual(MAX_TERMS_PER_CHUNK, 16)
        self.assertIn("at most 16 terms", SYSTEM_PROMPT)
        self.assertIn("no more than 16 terms", USER_TASK)
        # Yer tutucu istemde kalmamalı, aksi hâlde .format() KeyError verir
        self.assertNotIn("{max_terms}", SYSTEM_PROMPT)
        self.assertNotIn("{max_terms}", USER_TASK)
        self.assertIn("deneme metni", USER_TASK.format(text="deneme metni"))


class SurfaceFormTests(unittest.TestCase):
    def test_term_is_located_through_its_plural_surface_form(self):
        pages = [PageText(1, "Modern block ciphers resist known attacks.")]
        self.assertEqual(term_occurrences("block cipher", pages)[0], 0)
        occurrences, page_set, found_form = locate_term("block cipher", pages)
        self.assertEqual(occurrences, 1)
        self.assertEqual(page_set, {1})
        self.assertEqual(found_form, "block ciphers")

    def test_term_is_located_when_split_by_line_break_hyphen(self):
        pages = [PageText(1, "The paper studies homomorphic compu-\ntation in depth.")]
        self.assertEqual(term_occurrences("homomorphic computation", pages)[0], 0)
        occurrences, _, found_form = locate_term("homomorphic computation", pages)
        self.assertEqual(occurrences, 1)
        self.assertEqual(found_form, "homomorphic computation")

    def test_context_is_returned_for_line_break_hyphenated_match(self):
        pages = [PageText(1, "The paper studies homomorphic compu-\ntation in depth.")]
        self.assertIn("homomorphic computation", find_context("homomorphic computation", pages))

    def test_genuine_hyphenated_term_still_matches_across_a_line_break(self):
        pages = [PageText(1, "We evaluate privacy-\npreserving computation here.")]
        occurrences, _, found_form = locate_term("privacy-preserving computation", pages)
        self.assertEqual(occurrences, 1)
        self.assertEqual(found_form, "privacy-preserving computation")

    def test_absent_term_stays_absent(self):
        pages = [PageText(1, "A distributed ledger records transactions.")]
        self.assertEqual(locate_term("quantum annealing", pages), (0, set(), "quantum annealing"))

    def test_surface_variants_only_inflect_the_last_word(self):
        self.assertIn("block ciphers", surface_variants("block cipher"))
        self.assertIn("dictionaries", surface_variants("dictionary"))
        # Yeni kavram uretilmemeli: ilk sozcuk hic degismez
        self.assertTrue(all(v.startswith("block ") for v in surface_variants("block cipher")))


if __name__ == "__main__":
    unittest.main()
