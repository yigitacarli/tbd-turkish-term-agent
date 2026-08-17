import tempfile
import unittest
from pathlib import Path

from terim_etmeni.pdf_reader import PDFReadError, clean_extracted_text, read_pdf


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

    def test_numbered_references_and_notes_are_truncated(self):
        variations = [
            "12. References\nSome cited reference text here.",
            "8. REFERENCES:\nAuthor et al. 2020.",
            "VI. REFERENCES\nAnother paper title.",
            "References and Notes\nFootnote text.",
            "Works Cited\nList of books.",
            "Bibliography\nOld papers.",
        ]
        for var in variations:
            with self.subTest(var=var.splitlines()[0]):
                full_text = f"Primary technical body about consensus algorithms.\n{var}"
                cleaned = clean_extracted_text(full_text)
                self.assertIn("Primary technical body about consensus algorithms.", cleaned)
                self.assertNotIn("Some cited reference text", cleaned)
                self.assertNotIn("Author et al", cleaned)
                self.assertNotIn("Another paper title", cleaned)
                self.assertNotIn("Footnote text", cleaned)

    def test_low_quality_formula_and_compacted_lines_are_removed(self):
        text = (
            "Diffusionmodelshaveemergedasapowerfulnewfamilyofdeepgenerativemodelswithrecordbreakingperformance\n"
            "𝛼¯𝑡 = sigmoid(𝛾 𝜂(𝑡)) | x 0 = N(𝛼𝑡x 0)\n"
            "∑√≈≤≥ x_i = y_j / z_k\n"
            "Valid technical paragraph with normal word spacing."
        )
        self.assertEqual(
            clean_extracted_text(text),
            "Valid technical paragraph with normal word spacing.",
        )

    def test_code_blocks_and_pseudo_code_are_removed(self):
        text = (
            "Standard distributed ledger consensus explanation.\n"
            "10 def selector_width(hist, val):\n"
            "11 return pair_balance(first, same)\n"
            "import numpy as np; from torch import nn\n"
            "if (x == y && z != 0) { return a -> b; }\n"
            "Next technical paragraph about Byzantine fault tolerance."
        )
        cleaned = clean_extracted_text(text)
        self.assertIn("Standard distributed ledger consensus explanation.", cleaned)
        self.assertIn("Next technical paragraph about Byzantine fault tolerance.", cleaned)
        self.assertNotIn("selector_width", cleaned)
        self.assertNotIn("pair_balance", cleaned)
        self.assertNotIn("import numpy", cleaned)

    def test_read_pdf_validates_file_existence_and_extension(self):
        with self.assertRaisesRegex(PDFReadError, "PDF bulunamadı"):
            read_pdf(Path("/nonexistent/file.pdf"))

        with tempfile.NamedTemporaryFile(suffix=".txt") as tmp:
            with self.assertRaisesRegex(PDFReadError, "Desteklenmeyen dosya türü"):
                read_pdf(Path(tmp.name))


if __name__ == "__main__":
    unittest.main()

