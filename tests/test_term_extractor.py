import unittest

from terim_etmeni.models import ExtractedTerm, PageText, TextChunk
from terim_etmeni.term_extractor import extract_verified_terms


class FakeProvider:
    def extract(self, text):
        return [
            ExtractedTerm("Machine Learning"),
            ExtractedTerm("invented technology"),
            ExtractedTerm("neural-network"),
            ExtractedTerm("Section: This is a whole sentence presented as a term."),
            ExtractedTerm("AI in Education"),
            ExtractedTerm("Operational sequence"),
            ExtractedTerm("semantic router selects a worker"),
            ExtractedTerm("Adaptive Systems Research Note"),
            ExtractedTerm("experimental components"),
        ]


class TermExtractorTests(unittest.TestCase):
    def test_model_hallucinations_are_removed_and_evidence_is_counted(self):
        pages = [
            PageText(1, 'Machine learning uses a neural network and "quoted cache fabric".'),
            PageText(2, "Machine Learning and another neural-network. Operational sequence. A semantic router selects a worker. Adaptive Systems Research Note. Experimental components."),
        ]
        chunks = [TextChunk(1, 0, pages[0].text), TextChunk(2, 1, pages[1].text)]

        results = extract_verified_terms(chunks, pages, FakeProvider())
        by_term = {item.term: item for item in results}

        self.assertNotIn("invented technology", by_term)
        self.assertNotIn("AI in Education", by_term)
        self.assertNotIn("Operational sequence", by_term)
        self.assertNotIn("semantic router selects a worker", by_term)
        self.assertNotIn("Adaptive Systems Research Note", by_term)
        self.assertNotIn("experimental components", by_term)
        self.assertEqual(by_term["Machine Learning"].pages, {1, 2})
        self.assertEqual(by_term["Machine Learning"].occurrence_count, 2)
        self.assertEqual(by_term["neural-network"].pages, {1, 2})
        self.assertEqual(by_term["quoted cache fabric"].pages, {1})


if __name__ == "__main__":
    unittest.main()
