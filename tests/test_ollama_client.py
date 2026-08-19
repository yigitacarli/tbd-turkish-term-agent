import unittest
from unittest.mock import patch

from terim_etmeni.ollama_client import OllamaClient, OllamaError, _json_from_text


class OllamaBudgetTests(unittest.TestCase):
    def test_output_budget_matches_cloud_client(self):
        """Yerel model bulut sağlayıcıdan daha dar bir çıktı bütçesine sıkışmamalı."""
        import inspect

        from terim_etmeni.api_client import ApiClient

        local = inspect.signature(
            OllamaClient._extract_prompt
        ).parameters["num_predict"].default
        cloud = inspect.signature(
            ApiClient._extract_prompt
        ).parameters["max_tokens"].default
        self.assertGreaterEqual(local, cloud)


class OllamaClientTests(unittest.TestCase):
    def test_json_parser_accepts_fenced_json(self):
        self.assertEqual(_json_from_text('```json\n{"terms": []}\n```'), {"terms": []})

    def test_json_parser_accepts_raw_list(self):
        self.assertEqual(_json_from_text('[{"term": "transformer"}]'), {"terms": [{"term": "transformer"}]})

    def test_json_parser_handles_preamble_and_trailing_commas(self):
        raw = 'Here is the JSON result:\n```json\n{"terms": [{"term": "attention",},],}\n```\nHope it helps!'
        self.assertEqual(_json_from_text(raw), {"terms": [{"term": "attention"}]})

    def test_json_parser_rejects_invalid_response(self):
        with self.assertRaises(OllamaError):
            _json_from_text("no structured result")


    def test_extract_terms_parses_strings_and_objects(self):
        client = OllamaClient("http://localhost:11434", "fake")
        with patch.object(
            client, "_request", return_value={"response": '{"terms": ["data fabric", {"term": "context window", "context": "..."}]}'}
        ):
            terms = client.extract_terms("data fabric and context window")
        self.assertEqual([item.term for item in terms], ["data fabric", "context window"])

    def test_invalid_json_is_retried_once(self):
        client = OllamaClient("http://localhost:11434", "fake")
        responses = [
            {"response": '{"terms":["unterminated"'},
            {"response": '{"terms":["data fabric"]}'},
        ]
        with patch.object(client, "_request", side_effect=responses) as request:
            terms = client.extract_terms("data fabric")
        self.assertEqual([item.term for item in terms], ["data fabric"])
        self.assertEqual(request.call_count, 2)

    def test_empty_model_result_is_a_valid_extraction(self):
        client = OllamaClient("http://localhost:11434", "fake")
        with patch.object(client, "_request", return_value={"response": '{"terms":[]}'}):
            terms = client.extract_terms("The authors thank the reviewers.")
        self.assertEqual(terms, [])


if __name__ == "__main__":
    unittest.main()
