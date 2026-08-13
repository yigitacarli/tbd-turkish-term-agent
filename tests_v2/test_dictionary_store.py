import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from terim_etmeni_v2.dictionary_store import DictionaryStore


def dictionary(version, terms, digest=""):
    return {
        "metadata": {
            "version": version,
            "source": "test",
            "source_sha256": digest,
            "unique_english_term_count": len({item["en"].casefold() for item in terms}),
        },
        "terms": terms,
    }


class DictionaryStoreTests(unittest.TestCase):
    def test_bootstrap_is_used_before_a_managed_import(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bootstrap = root / "bootstrap.json"
            bootstrap.write_text(json.dumps(dictionary("v1", [{"en": "AI", "tr": "YZ"}])), encoding="utf-8")
            store = DictionaryStore(root / "state", bootstrap)
            status = store.status()
            self.assertEqual(status.version, "v1")
            self.assertFalse(status.managed)
            self.assertEqual(store.load_index().lookup("AI")[0], "exact")

    def test_valid_import_is_written_then_atomically_activated(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bootstrap = root / "bootstrap.json"
            bootstrap.write_text(json.dumps(dictionary("v1", [{"en": "AI", "tr": "YZ"}])), encoding="utf-8")
            pdf = root / "new.pdf"
            pdf.write_bytes(b"%PDF-fake")
            new_data = dictionary("v2", [{"en": "agent", "tr": "etmen"}], "abc123")
            store = DictionaryStore(root / "state", bootstrap)
            with patch("terim_etmeni_v2.dictionary_store.convert_dictionary_pdf", return_value=new_data):
                status = store.import_pdf(pdf)
            self.assertEqual(status.version, "v2")
            self.assertTrue(status.managed)
            self.assertEqual(store.load_index().lookup("agent")[0], "exact")
            self.assertTrue((root / "state" / "active.json").is_file())


if __name__ == "__main__":
    unittest.main()

