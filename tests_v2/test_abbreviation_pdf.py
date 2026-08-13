import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from terim_etmeni_v2.abbreviation_pdf import convert_abbreviation_pdf
from terim_etmeni_v2.dictionary_pdf import DictionaryImportError


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


def word(text, x0, x1, top, fontname="TimesNewRomanPSMT"):
    return {
        "text": text,
        "x0": x0,
        "x1": x1,
        "top": top,
        "fontname": fontname,
        "size": 10.4,
    }


class AbbreviationPdfTests(unittest.TestCase):
    def test_bold_abbreviation_rows_are_converted_and_ambiguity_is_preserved(self):
        words = [
            word("2025-03-17", 390, 450, 200),
            word("2", 390, 400, 220),
            word("kisaltma", 402, 450, 220),
            word("AI", 80, 95, 300, "TimesNewRomanPS-BoldMT"),
            word("Artificial", 110, 150, 300),
            word("Intelligence", 152, 210, 300),
            word("yapay", 110, 140, 314),
            word("zeka", 142, 170, 314),
            word("AI", 80, 95, 328, "TimesNewRomanPS-BoldMT"),
            word("Asset", 110, 140, 328),
            word("Identification", 142, 210, 328),
            word("varlik", 110, 140, 342),
            word("tanimlamasi", 142, 205, 342),
        ]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "abbreviations.pdf"
            path.write_bytes(b"%PDF-fake")
            with patch(
                "terim_etmeni_v2.abbreviation_pdf.pdfplumber.open",
                return_value=FakePdf([FakePage(words)]),
            ):
                result = convert_abbreviation_pdf(path, minimum_records=2)

        self.assertEqual(result["metadata"]["declared_record_count"], 2)
        self.assertEqual(result["metadata"]["raw_record_count"], 2)
        self.assertEqual(result["metadata"]["unique_abbreviation_count"], 1)
        self.assertEqual(
            [entry["expansion"] for entry in result["abbreviations"]],
            ["Artificial Intelligence", "Asset Identification"],
        )

    def test_large_declared_count_mismatch_is_rejected(self):
        words = [
            word("2025-03-17", 390, 450, 200),
            word("100", 390, 410, 220),
            word("kisaltma", 412, 460, 220),
            word("AI", 80, 95, 300, "TimesNewRomanPS-BoldMT"),
            word("Artificial", 110, 150, 300),
            word("Intelligence", 152, 210, 300),
            word("yapay", 110, 140, 314),
            word("zeka", 142, 170, 314),
        ]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "abbreviations.pdf"
            path.write_bytes(b"%PDF-fake")
            with patch(
                "terim_etmeni_v2.abbreviation_pdf.pdfplumber.open",
                return_value=FakePdf([FakePage(words)]),
            ):
                with self.assertRaises(DictionaryImportError):
                    convert_abbreviation_pdf(path, minimum_records=1)


if __name__ == "__main__":
    unittest.main()
