import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from terim_etmeni_v2.dictionary_pdf import (
    DictionaryImportError,
    convert_dictionary_pdf,
)


class FakePage:
    def __init__(self, words):
        self.words = words

    def extract_words(self, **_kwargs):
        return list(self.words)


class FakePdf:
    def __init__(self, pages):
        self.pages = pages

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


def word(text, x0, x1, top):
    return {"text": text, "x0": x0, "x1": x1, "top": top}


class DictionaryPdfTests(unittest.TestCase):
    def test_coordinate_table_is_converted_and_versioned(self):
        words = [
            word("Güncelleme:", 370, 420, 244),
            word("2026-08-13", 423, 470, 244),
            word("machine", 220, 250, 300),
            word("learning", 252, 274, 300),
            word(":", 278, 280, 303),
            word("makine", 285, 315, 300),
            word("öğrenmesi", 317, 365, 300),
        ]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "dictionary.pdf"
            path.write_bytes(b"%PDF-fake")
            with patch("terim_etmeni_v2.dictionary_pdf.pdfplumber.open", return_value=FakePdf([FakePage(words)])):
                result = convert_dictionary_pdf(path, minimum_records=1)
        self.assertEqual(result["metadata"]["version"], "2026-08-13")
        self.assertEqual(result["metadata"]["raw_record_count"], 1)
        self.assertEqual(
            result["terms"],
            [{"en": "machine learning", "tr": "makine öğrenmesi", "source_page": 1}],
        )

    def test_suspicious_record_drop_is_rejected(self):
        words = [
            word("2026-08-13", 423, 470, 244),
            word("AI", 250, 274, 300),
            word(":", 278, 280, 303),
            word("YZ", 285, 300, 300),
        ]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "dictionary.pdf"
            path.write_bytes(b"%PDF-fake")
            with patch("terim_etmeni_v2.dictionary_pdf.pdfplumber.open", return_value=FakePdf([FakePage(words)])):
                with self.assertRaises(DictionaryImportError):
                    convert_dictionary_pdf(path, minimum_records=1, previous_record_count=100)


if __name__ == "__main__":
    unittest.main()

