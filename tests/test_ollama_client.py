import unittest

from unittest.mock import patch

from terim_etmeni.ollama_client import OllamaClient, OllamaError, _json_from_text


class OllamaParserTests(unittest.TestCase):
    def test_json_parser_accepts_fenced_json(self):
        result = _json_from_text('```json\n{"terms": []}\n```')
        self.assertEqual(result, {"terms": []})

    def test_json_parser_rejects_invalid_response(self):
        with self.assertRaises(OllamaError):
            _json_from_text("no structured result")

    def test_two_review_passes_are_merged_and_deduplicated(self):
        client = OllamaClient("http://localhost:11434", "fake")
        responses = [
            {"response": '{"terms":["machine learning","data fabric"]}'},
            {"response": '{"terms":["data fabric","cloud volume"]}'},
        ]
        with patch.object(client, "_request", side_effect=responses):
            terms = client.extract("machine learning, data fabric, and cloud volume")
        self.assertEqual(
            [item.term for item in terms],
            ["machine learning", "data fabric", "cloud volume"],
        )


if __name__ == "__main__":
    unittest.main()
