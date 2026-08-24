import json
import tempfile
import unittest
from pathlib import Path

from terim_etmeni.abbreviation_index import AbbreviationIndex


class AbbreviationIndexTests(unittest.TestCase):
    def test_ambiguous_abbreviations_and_defined_expansions_remain_separate(self):
        index = AbbreviationIndex(
            [
                {"abbreviation": "AI", "expansion": "Artificial Intelligence", "turkish": "yapay zeka"},
                {"abbreviation": "AI", "expansion": "Asset Identification", "turkish": "varlik tanimlamasi"},
            ],
            metadata={"version": "2025-03-17"},
        )
        self.assertEqual(len(index.lookup("ai")), 2)
        self.assertEqual(
            index.lookup_defined("AI", "artificial intelligence")[0]["turkish"],
            "yapay zeka",
        )

    def test_written_form_lookup_ignores_ordinary_words(self):
        """ADR-049: metindeki 'set' sözcüğü TBD kısaltması 'SET' ile eşleşmemeli."""
        index = AbbreviationIndex(
            [
                {"abbreviation": "SET", "expansion": "Secure Electronic Transaction", "turkish": "guvenli elektronik islem"},
                {"abbreviation": "RAM", "expansion": "Random Access Memory", "turkish": "rastgele erisimli bellek"},
            ]
        )
        # Eski davranış: harf duyarsız eşleşme sıradan sözcükleri de yakalıyordu.
        self.assertEqual(len(index.lookup("set")), 1)
        # Yeni davranış: yalnız kayıtlı yazım eşleşir.
        self.assertEqual(index.lookup_written_form("set"), [])
        self.assertEqual(len(index.lookup_written_form("SET")), 1)
        self.assertEqual(len(index.lookup_written_form("RAM")), 1)
        self.assertEqual(index.lookup_written_form("ram"), [])

    def test_written_form_lookup_keeps_mixed_case_abbreviations(self):
        """TBD kaynağındaki 1.199 kısaltmanın 149'u tamamen büyük harf değildir."""
        index = AbbreviationIndex(
            [
                {"abbreviation": "SaaS", "expansion": "Software as a Service", "turkish": "hizmet olarak yazilim"},
                {"abbreviation": "AIoT", "expansion": "Artificial Intelligence of Things", "turkish": "nesnelerin yapay zekasi"},
                {"abbreviation": "aux", "expansion": "auxiliary", "turkish": "yardimci"},
            ]
        )
        self.assertEqual(len(index.lookup_written_form("SaaS")), 1)
        self.assertEqual(len(index.lookup_written_form("AIoT")), 1)
        # Kayıtlı yazımı zaten küçük harf olan madde küçük harfle eşleşmeye devam eder.
        self.assertEqual(len(index.lookup_written_form("aux")), 1)
        self.assertEqual(index.lookup_written_form("SAAS"), [])

    def test_json_loader_rejects_no_valid_entries_by_length(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "abbreviations.json"
            path.write_text(
                json.dumps(
                    {
                        "metadata": {"version": "test"},
                        "abbreviations": [
                            {"abbreviation": "DNS", "expansion": "Domain Name System", "turkish": "alan adi sistemi"}
                        ],
                    }
                ),
                encoding="utf-8",
            )
            index = AbbreviationIndex.load(path)
        self.assertEqual(len(index), 1)


if __name__ == "__main__":
    unittest.main()
