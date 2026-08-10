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


if __name__ == "__main__":
    unittest.main()
