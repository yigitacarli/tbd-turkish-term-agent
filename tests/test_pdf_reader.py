import unittest

from terim_etmeni.pdf_reader import clean_extracted_text


class PDFTextCleaningTests(unittest.TestCase):
    def test_metadata_urls_and_references_are_removed(self):
        text = """Useful artificial intelligence content.
© 2023 Journal | ISSN: 1234
See https://example.org/cyber-security-battlefield for details.
REFERENCES
Natural language processing in a cited title.
"""
        cleaned = clean_extracted_text(text)
        self.assertIn("Useful artificial intelligence content.", cleaned)
        self.assertNotIn("ISSN", cleaned)
        self.assertNotIn("battlefield", cleaned)
        self.assertNotIn("cited title", cleaned)

    def test_low_quality_formula_and_compacted_lines_are_removed(self):
        text = (
            "Diffusionmodelshaveemergedasapowerfulnewfamilyofdeepgenerativemodelswithrecordbreakingperformance\n"
            "𝛼¯𝑡 = sigmoid(𝛾 𝜂(𝑡)) | x 0 = N(𝛼𝑡x 0)\n"
            "Valid technical paragraph with normal word spacing."
        )
        self.assertEqual(
            clean_extracted_text(text),
            "Valid technical paragraph with normal word spacing.",
        )


if __name__ == "__main__":
    unittest.main()
