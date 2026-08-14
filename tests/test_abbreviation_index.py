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
