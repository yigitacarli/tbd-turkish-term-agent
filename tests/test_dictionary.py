import unittest

from terim_etmeni.dictionary import DictionaryIndex, normalized_key


class DictionaryTests(unittest.TestCase):
    def test_dictionary_exact_possible_and_missing_matches(self):
        dictionary = DictionaryIndex(
            [
                {"en": "machine learning", "tr": "makine öğrenmesi"},
                {"en": "client-server", "tr": "istemci-sunucu"},
            ]
        )

        status, entries = dictionary.lookup("  Machine   Learning ")
        self.assertEqual(status, "exact")
        self.assertEqual(entries[0]["tr"], "makine öğrenmesi")
        self.assertEqual(dictionary.lookup("client server")[0], "possible")
        self.assertEqual(dictionary.lookup("machine learnings")[0], "possible")
        self.assertEqual(dictionary.lookup("agentic workflow"), ("missing", []))

    def test_normalized_key_handles_unicode_and_case(self):
        self.assertEqual(normalized_key("ＡI  MODEL"), "ai model")

    def test_dictionary_finds_multiword_terms_in_text(self):
        dictionary = DictionaryIndex(
            [
                {"en": "natural language processing", "tr": "doğal dil işleme"},
                {"en": "intelligent agent", "tr": "akıllı etmen"},
                {"en": "travel", "tr": "seyahat"},
            ]
        )
        matches = dict(
            dictionary.find_phrases(
                "Natural language processing helps an intelligent agent."
            )
        )
        self.assertEqual(matches["natural language processing"], 1)
        self.assertEqual(matches["intelligent agent"], 1)
        self.assertNotIn("travel", matches)


if __name__ == "__main__":
    unittest.main()
